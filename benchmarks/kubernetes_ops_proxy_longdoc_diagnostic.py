#!/usr/bin/env python3
"""One bounded long-document policy diagnosis for the Kubernetes proxy dev32.

Development-only. Candidate set and selection rule are frozen before serving.
All candidate serving completes before scorer-side gold is opened.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
BENCH = ROOT / "benchmarks"
sys.path[:0] = [str(TOOLS), str(BENCH)]

import kubernetes_ops_proxy_dev_run as runmod  # noqa: E402
import kubernetes_ops_proxy_dev_score as scoremod  # noqa: E402
from grounding_canonical import canonical_bytes  # noqa: E402
from grounding_projection import _projection_term_weights, _sentence_score_terms  # noqa: E402
from grounding_text import split_sentences, tokenize  # noqa: E402
from grounding_preregister import resolve_model, resolve_runtime  # noqa: E402
from grounding_v1_surface import messages, model_runtime_fingerprint, surface_sha256  # noqa: E402
from run_grounding_benchmark import (  # noqa: E402
    calibrate_grounding_v1_contract,
    negotiate_grounding_v11_surface,
    request_grounding_v1_model,
    server_command,
    stop_server,
    wait_server,
)

PROTOCOL = BENCH / "kubernetes_ops_proxy_longdoc_diagnostic_protocol.json"
OUT = ROOT / "target/kubernetes-pod-ops-docqa-v0.1/dev32/longdoc-diagnostic-r1"
REFERENCE = ROOT / "target/kubernetes-pod-ops-docqa-v0.1/dev32/three-arm-r4"
GROUNDING_PROJECTION = TOOLS / "grounding_projection.py"
GROUNDING_TEXT = TOOLS / "grounding_text.py"
ARMS = ("C1", "C2", "RAW2560")
PREFIX = "Authorized Kubernetes documentation (host BM25, ranked):\n"


class DiagnosticError(RuntimeError):
    pass


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise DiagnosticError(f"invalid JSONL row: {path}")
            rows.append(value)
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


def _bounded_utf8(text: str, limit: int) -> str:
    if limit <= 0:
        return ""
    data = text.encode("utf-8")
    if len(data) <= limit:
        return text
    fragment = data[:limit]
    while fragment:
        try:
            return fragment.decode("utf-8")
        except UnicodeDecodeError:
            fragment = fragment[:-1]
    return ""


def _prepared_sentence_rows(hits: list[dict[str, Any]]) -> list[tuple[dict[str, Any], list[str], list[tuple[str, ...]]]]:
    rows = []
    for hit in hits:
        sentences = split_sentences(hit["text"])
        if not sentences:
            sentences = [hit["text"]]
        rows.append((hit, sentences, [tuple(tokenize(sentence)) for sentence in sentences]))
    return rows


def _contiguous_snippet(
    sentences: list[str],
    signatures: list[tuple[str, ...]],
    query_terms: set[str],
    weights: dict[str, float],
    budget: int,
) -> tuple[str, tuple[int, int]]:
    scores = [_sentence_score_terms(weights, set(signature), query_terms) for signature in signatures]
    anchor = min(range(len(sentences)), key=lambda i: (-scores[i], i))
    lo = hi = anchor

    def rendered(a: int, b: int) -> str:
        return " ".join(sentences[a : b + 1])

    current = rendered(lo, hi)
    if len(current.encode("utf-8")) > budget:
        return _bounded_utf8(current, budget), (lo, hi)

    while True:
        options: list[tuple[float, int, int, int]] = []
        if lo > 0:
            candidate = rendered(lo - 1, hi)
            if len(candidate.encode("utf-8")) <= budget:
                options.append((scores[lo - 1], 0, lo - 1, hi))
        if hi + 1 < len(sentences):
            candidate = rendered(lo, hi + 1)
            if len(candidate.encode("utf-8")) <= budget:
                options.append((scores[hi + 1], 1, lo, hi + 1))
        if not options:
            break
        _score, _tie, lo, hi = max(options, key=lambda row: (row[0], -row[1]))
    return rendered(lo, hi), (lo, hi)


def contiguous_context(hits: list[dict[str, Any]], question: str, *, max_bytes: int, max_docs: int) -> tuple[bytes, list[dict[str, Any]]]:
    sentence_rows = _prepared_sentence_rows(hits)
    query_terms = set(tokenize(question))
    weights = _projection_term_weights(None, sentence_rows, query_terms, None)
    out = bytearray(PREFIX.encode("utf-8"))
    emitted: list[dict[str, Any]] = []
    selected = sentence_rows[:max_docs]
    for index, (hit, sentences, signatures) in enumerate(selected):
        docs_left = len(selected) - index
        header = f"\n[{hit['title']} | {hit['path']}]\n"
        header_bytes = len(header.encode("utf-8"))
        remaining = max_bytes - len(out)
        if remaining <= header_bytes:
            break
        # Reserve an equal share for each remaining ranked document. This is
        # deterministic and does not inspect scorer gold.
        allocation = max(128, remaining // docs_left - header_bytes)
        snippet, span = _contiguous_snippet(sentences, signatures, query_terms, weights, allocation)
        segment = header + snippet + "\n"
        data = segment.encode("utf-8")
        remaining = max_bytes - len(out)
        if len(data) > remaining:
            segment = _bounded_utf8(segment, remaining)
            data = segment.encode("utf-8")
        if not data:
            break
        out.extend(data)
        emitted.append({"path": hit["path"], "rank": hit["rank"], "sentence_span": list(span)})
    return bytes(out), emitted


def raw_context(hits: list[dict[str, Any]], *, max_bytes: int) -> bytes:
    out = bytearray(PREFIX.encode("utf-8"))
    for hit in hits:
        segment = f"\n[{hit['title']} | {hit['path']}]\n{hit['text']}\n"
        remaining = max_bytes - len(out)
        if remaining <= 0:
            break
        out.extend(_bounded_utf8(segment, remaining).encode("utf-8"))
        if len(out) >= max_bytes:
            break
    return bytes(out)


def candidate_payload(arm: str, hits: list[dict[str, Any]], question: str) -> tuple[bytes, list[dict[str, Any]]]:
    if arm == "C1":
        return contiguous_context(hits, question, max_bytes=3072, max_docs=1)
    if arm == "C2":
        return contiguous_context(hits, question, max_bytes=3072, max_docs=2)
    if arm == "RAW2560":
        return raw_context(hits, max_bytes=2560), []
    raise DiagnosticError(f"unknown diagnostic arm: {arm}")


def validate_protocol() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    protocol = load_json(PROTOCOL)
    if protocol.get("development_only") is not True or protocol.get("qualification_eligible") is not False:
        raise DiagnosticError("diagnostic qualification boundary drift")
    expected = {
        "diagnostic_source_sha256": digest(Path(__file__)),
        "dev_protocol_sha256": digest(runmod.PROTOCOL),
        "candidate_manifest_sha256": digest(runmod.CANDIDATE / "manifest.json"),
        "retrieval_sha256": digest(runmod.RETRIEVAL),
        "reference_run_status_sha256": digest(REFERENCE / "run/status.json"),
        "reference_score_summary_sha256": digest(REFERENCE / "score/summary.json"),
        "grounding_projection_source_sha256": digest(GROUNDING_PROJECTION),
        "grounding_text_source_sha256": digest(GROUNDING_TEXT),
    }
    for key, value in expected.items():
        if protocol.get(key) != value:
            raise DiagnosticError(f"diagnostic frozen identity drift: {key}")
    if tuple(protocol.get("arms", {}).keys()) != ARMS:
        raise DiagnosticError("diagnostic candidate set drift")
    _dev_protocol, _retrieval_manifest, questions, retrieval_by_id = runmod.validate_freeze()
    return protocol, questions, retrieval_by_id


def serve(model_path: Path, runtime_path: Path, port: int) -> None:
    run_dir = OUT / "run"
    if run_dir.exists():
        raise DiagnosticError("diagnostic run output already exists")
    protocol, questions, retrieval_by_id = validate_protocol()
    inventory_sha, model = resolve_model(runmod.MODEL_INVENTORY, runmod.MODEL_ID, None, model_path)
    runtime_sha, runtime = resolve_runtime(runmod.RUNTIME_RECORD, runtime_path)
    runtime = json.loads(json.dumps(runtime))
    runtime["launch"]["port"] = port
    runtime["launch"]["threads"] = 6
    generation = load_json(runmod.GENERATION_PATH)
    policy = runmod.ANSWER_POLICY.read_bytes()
    prereg = {
        "format": "exactscope.public-proxy-longdoc-diagnostic-preregistration",
        "format_version": "0.1",
        "development_only": True,
        "qualification_eligible": False,
        "protocol_sha256": digest(PROTOCOL),
        "model_inventory_sha256": inventory_sha,
        "model": model,
        "runtime_record_sha256": runtime_sha,
        "runtime": runtime,
        "generation_config_sha256": digest(runmod.GENERATION_PATH),
        "model_surface_sha256": surface_sha256(),
        "answer_policy_sha256": digest(runmod.ANSWER_POLICY),
        "arms": protocol["arms"],
        "retry_count": 0,
        "hidden_repair": False,
        "gold_visible_to_runner": False,
        "serve_all_arms_before_scoring": True,
    }
    run_dir.mkdir(parents=True)
    (run_dir / "preregistration.json").write_bytes(canonical_bytes(prereg))
    records: list[dict[str, Any]] = []
    process = None
    selected_surface = None
    selected_contract = None
    try:
        with (run_dir / "llama-server.log").open("wb") as server_log:
            process = subprocess.Popen(
                server_command(prereg),
                cwd=runtime_path.parent,
                stdout=server_log,
                stderr=subprocess.STDOUT,
                env=os.environ.copy(),
            )
            wait_server(process, runtime["launch"]["host"], port, float(load_json(runmod.RUNTIME_RECORD)["server_ready_timeout_seconds"]))
            selected_surface, negotiation = negotiate_grounding_v11_surface(prereg, generation, policy)
            if selected_surface is None:
                raise DiagnosticError("no supported output surface")
            selected_contract, calibration = calibrate_grounding_v1_contract(prereg, generation, policy, selected_surface)
            (run_dir / "surface-negotiation.json").write_bytes(canonical_bytes(negotiation))
            (run_dir / "contract-calibration.json").write_bytes(canonical_bytes(calibration))
            for q in questions:
                item_id = q["item_id"]
                question = q["question"]
                hits = retrieval_by_id[item_id]["hits"]
                for arm in ARMS:
                    payload, emitted = candidate_payload(arm, hits, question)
                    response = request_grounding_v1_model(
                        prereg,
                        generation,
                        messages(selected_contract, question, evidence=payload, policy=policy),
                        selected_contract,
                        selected_surface,
                    )
                    records.append({
                        "item_id": item_id,
                        "arm": arm,
                        **response,
                        "evidence_bytes": len(payload),
                        "emitted": emitted,
                    })
    finally:
        stop_server(process)
    write_jsonl(run_dir / "raw-results.jsonl", records)
    status = {
        "format": "exactscope.public-proxy-longdoc-diagnostic-run",
        "format_version": "0.1",
        "state": "complete",
        "item_count": len(questions),
        "record_count": len(records),
        "arms": list(ARMS),
        "protocol_sha256": digest(PROTOCOL),
        "raw_results_sha256": digest(run_dir / "raw-results.jsonl"),
        "selected_model_contract": selected_contract,
        "selected_output_surface": selected_surface,
        "model_runtime_fingerprint": model_runtime_fingerprint(prereg),
        "retry_count": 0,
        "hidden_repair": False,
        "gold_visible_to_runner": False,
    }
    write_json(run_dir / "status.json", status)
    print(json.dumps(status, indent=2, sort_keys=True))


def _percentile(values: list[float], p: float) -> float:
    values = sorted(values)
    pos = p * (len(values) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    frac = pos - lo
    return values[lo] * (1.0 - frac) + values[hi] * frac


def score() -> None:
    score_dir = OUT / "score"
    if score_dir.exists():
        raise DiagnosticError("diagnostic score output already exists")
    protocol, questions, retrieval_by_id = validate_protocol()
    run_dir = OUT / "run"
    status = load_json(run_dir / "status.json")
    if status.get("state") != "complete" or status.get("protocol_sha256") != digest(PROTOCOL):
        raise DiagnosticError("diagnostic serving status invalid")
    if status.get("raw_results_sha256") != digest(run_dir / "raw-results.jsonl"):
        raise DiagnosticError("diagnostic raw result drift")
    rows = load_jsonl(run_dir / "raw-results.jsonl")
    keyed = {(row["item_id"], row["arm"]): row for row in rows}
    expected = {(q["item_id"], arm) for q in questions for arm in ARMS}
    if set(keyed) != expected:
        raise DiagnosticError("diagnostic observation matrix incomplete")

    # Gold is opened only after the complete diagnostic serving matrix verifies.
    gold_rows = load_jsonl(runmod.CANDIDATE / "gold/answers.jsonl")
    gold = {row["item_id"]: row for row in gold_rows}
    reference_rows = load_jsonl(REFERENCE / "score/per-item.jsonl")
    r_utility = {row["item_id"]: float(row["utility"]) for row in reference_rows if row["arm"] == "R"}
    reference_summary = load_json(REFERENCE / "score/summary.json")
    if set(r_utility) != {q["item_id"] for q in questions}:
        raise DiagnosticError("reference R utility identity drift")
    r = reference_summary["arms"]["R"]

    scored_rows: list[dict[str, Any]] = []
    arms: dict[str, dict[str, Any]] = {}
    per_item: dict[str, dict[str, float]] = {q["item_id"]: {} for q in questions}
    answerable_count = sum(gold[q["item_id"]]["truth_state"] == "answerable" for q in questions)
    disposition_count = len(questions) - answerable_count
    for arm in ARMS:
        utility_total = answerable_f1_total = 0.0
        disposition_correct = unsupported = format_fail = support_total = support_correct = 0
        input_tokens = output_tokens = evidence_bytes = latency_us = 0
        for q in questions:
            item_id = q["item_id"]
            observation = keyed[(item_id, arm)]
            g = gold[item_id]
            valid = observation.get("model_contract_valid") is True
            prediction = observation.get("model_contract_output") if valid else None
            utility = scoremod.item_utility(prediction, g) if valid else 0.0
            per_item[item_id][arm] = utility
            utility_total += utility
            if g["truth_state"] == "answerable":
                answerable_f1_total += utility
            else:
                disposition_correct += int(utility == 1.0)
            is_unsupported = bool(valid and scoremod.unsupported_assertion(prediction, g))
            unsupported += int(is_unsupported)
            format_fail += int(not valid)
            input_tokens += int(observation.get("input_tokens", 0))
            output_tokens += int(observation.get("output_tokens", 0))
            evidence_bytes += int(observation.get("evidence_bytes", 0))
            latency_us += int(observation.get("model_latency_us", 0))
            support = None
            if g["truth_state"] == "answerable":
                payload, _ = candidate_payload(arm, retrieval_by_id[item_id]["hits"], q["question"])
                support = scoremod.evidence_support(payload, g)
                support_total += 1
                support_correct += int(support)
            scored_rows.append({
                "item_id": item_id,
                "arm": arm,
                "truth_state": g["truth_state"],
                "prediction": prediction,
                "contract_valid": valid,
                "utility": utility,
                "unsupported_assertion": is_unsupported,
                "evidence_support": support,
            })
        n = len(questions)
        utility_mean = utility_total / n
        delta_pp = 100.0 * (utility_mean - float(r["primary_utility"]))
        input_reduction = 1.0 - (input_tokens / n) / float(r["mean_input_tokens"])
        evidence_reduction = 1.0 - (evidence_bytes / n) / float(r["mean_evidence_bytes"])
        candidate = {
            "primary_utility": utility_mean,
            "answerable_f1": answerable_f1_total / answerable_count,
            "disposition_accuracy": disposition_correct / disposition_count,
            "unsupported_assertion_count": unsupported,
            "format_failure_count": format_fail,
            "evidence_support_rate_answerable": support_correct / support_total,
            "mean_input_tokens": input_tokens / n,
            "mean_output_tokens": output_tokens / n,
            "mean_evidence_bytes": evidence_bytes / n,
            "mean_model_latency_ms": latency_us / n / 1000.0,
            "delta_vs_R_pp": delta_pp,
            "input_token_reduction_vs_R": input_reduction,
            "evidence_byte_reduction_vs_R": evidence_reduction,
        }
        candidate["quality_margin_pass"] = delta_pp >= -2.0
        candidate["safety_pass"] = format_fail == 0 and unsupported <= int(r["unacceptable_error_count"])
        candidate["material_advantage"] = (
            delta_pp >= 3.0
            or (delta_pp >= -2.0 and max(input_reduction, evidence_reduction) >= 0.15)
            or (delta_pp >= -2.0 and unsupported < int(r["unacceptable_error_count"]))
        )
        candidate["selection_eligible"] = bool(candidate["quality_margin_pass"] and candidate["safety_pass"] and candidate["material_advantage"])
        arms[arm] = candidate

    eligible = [arm for arm in ARMS if arms[arm]["selection_eligible"]]
    selected = None
    if eligible:
        selected = max(eligible, key=lambda arm: (arms[arm]["primary_utility"], -arms[arm]["mean_input_tokens"], -arms[arm]["mean_evidence_bytes"]))

    uncertainty = protocol["uncertainty"]
    selected_uncertainty = None
    if selected is not None:
        deltas = [per_item[item][selected] - r_utility[item] for item in sorted(per_item)]
        rng = random.Random(uncertainty["seed"])
        boots: list[float] = []
        for _ in range(uncertainty["resamples"]):
            indexes = [rng.randrange(len(deltas)) for _ in deltas]
            boots.append(100.0 * sum(deltas[i] for i in indexes) / len(deltas))
        alpha = (1.0 - uncertainty["confidence"]) / 2.0
        selected_uncertainty = {
            "method": uncertainty["method"],
            "seed": uncertainty["seed"],
            "resamples": uncertainty["resamples"],
            "confidence": uncertainty["confidence"],
            "observed_pp": arms[selected]["delta_vs_R_pp"],
            "interval_pp": [_percentile(boots, alpha), _percentile(boots, 1.0 - alpha)],
            "probability_positive": sum(v > 0 for v in boots) / len(boots),
        }

    result = {
        "format": "exactscope.public-proxy-longdoc-diagnostic-score",
        "format_version": "0.1",
        "development_only": True,
        "qualification_eligible": False,
        "protocol_sha256": digest(PROTOCOL),
        "reference_R": r,
        "arms": arms,
        "selected_arm": selected,
        "selected_uncertainty_vs_R": selected_uncertainty,
        "validation_required": selected is not None,
        "no_more_dev_policy_rounds": True,
        "note": "One bounded development32 diagnosis only. If selected_arm is null, shaping/configuration selection failed on this proxy. If non-null, freeze it before untouched validation32 and do not reselect from validation outcomes.",
    }
    score_dir.mkdir(parents=True)
    write_jsonl(score_dir / "per-item.jsonl", scored_rows)
    write_json(score_dir / "summary.json", result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    serve_p = sub.add_parser("serve")
    serve_p.add_argument("--model-path", type=Path, required=True)
    serve_p.add_argument("--runtime-path", type=Path, required=True)
    serve_p.add_argument("--port", type=int, default=18127)
    sub.add_parser("score")
    args = parser.parse_args()
    if args.command == "serve":
        serve(args.model_path, args.runtime_path, args.port)
    else:
        score()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
