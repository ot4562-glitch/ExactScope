#!/usr/bin/env python3
"""Run/score the frozen LlamaIndex-host H1 A/G public-development benchmark.

This runner never owns retrieval. It consumes a pre-frozen host retrieval JSONL,
keeps the A arm model-only, and applies the tracked `host-ranked-hybrid-h1-v0`
context projector to the same host-ranked hits for G. Gold is opened only by the
score phase after the serving output identity has been frozen.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "tools", ROOT / "benchmarks", ROOT / "adapters/bridge"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from grounding_canonical import canonical_bytes, loads  # noqa: E402
from grounding_preregister import file_sha, load_json, resolve_model, resolve_runtime  # noqa: E402
from grounding_v1_surface import (  # noqa: E402
    messages,
    model_runtime_fingerprint,
    parse_answer_object,
    surface_sha256,
)
from public_hotpot_benchmark import (  # noqa: E402
    PublicBenchmarkError,
    _f1,
    _normalize_answer,
    verify_candidate,
)
from ranked_hits import project_host_ranked_hybrid_h1  # noqa: E402
from run_grounding_benchmark import (  # noqa: E402
    BenchmarkRunError,
    calibrate_grounding_v1_contract,
    negotiate_grounding_v11_surface,
    request_grounding_v1_model,
    server_command,
    stop_server,
    wait_server,
)

RUN_FORMAT = "exactscope.public-hotpot-h1-run"
SCORE_FORMAT = "exactscope.public-hotpot-h1-summary"
FORMAT_VERSION = "0.1"
POLICY_ID = "host-ranked-hybrid-h1-v0"
TOP_K = 12
MAX_EVIDENCE_BYTES = 3072
MAX_ITEMS = 12
POLICY_PATH = ROOT / "grounding/reference-profile-v0.1/projection-policy.txt"
GENERATION_PATH = ROOT / "benchmarks/grounding-generation-config.json"


def _load_host_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise PublicBenchmarkError("host retrieval JSONL row is not an object")
            rows.append(value)
    except (OSError, ValueError, UnicodeError) as exc:
        raise PublicBenchmarkError(f"cannot read host retrieval JSONL: {path}") from exc
    return rows


def _write_cjsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(canonical_bytes(row) + b"\n" for row in rows))


def _load_cjsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_bytes().splitlines():
        value = loads(line)
        if not isinstance(value, dict):
            raise PublicBenchmarkError("run JSONL row is not an object")
        rows.append(value)
    return rows


def _load_retrieval(candidate: Path, retrieval_manifest_path: Path, retrieval_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        manifest = json.loads(retrieval_manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        raise PublicBenchmarkError("cannot read host retrieval manifest") from exc
    if not isinstance(manifest, dict):
        raise PublicBenchmarkError("host retrieval manifest root must be object")
    if manifest.get("format") != "exactscope.real-host-retrieval-freeze" or manifest.get("host_framework") != "LlamaIndex":
        raise PublicBenchmarkError("unsupported host retrieval identity")
    if manifest.get("host_owns_retrieval") is not True or manifest.get("exactscope_used_during_retrieval") is not False:
        raise PublicBenchmarkError("host retrieval ownership drift")
    if manifest.get("gold_visible_during_retrieval") is not False:
        raise PublicBenchmarkError("host retrieval violated gold isolation")
    if manifest.get("candidate_manifest_sha256") != file_sha(candidate / "manifest.json"):
        raise PublicBenchmarkError("retrieval/candidate identity drift")
    if manifest.get("retrieval_sha256") != file_sha(retrieval_path):
        raise PublicBenchmarkError("retrieval digest drift")
    if manifest.get("top_k") != TOP_K:
        raise PublicBenchmarkError("host retrieval top_k drift")
    rows = _load_host_jsonl(retrieval_path)
    if len(rows) != manifest.get("item_count"):
        raise PublicBenchmarkError("host retrieval item count drift")
    ids: set[str] = set()
    for row in rows:
        item_id = row.get("item_id")
        question = row.get("question")
        hits = row.get("hits")
        if not isinstance(item_id, str) or not isinstance(question, str) or not isinstance(hits, list) or len(hits) != TOP_K:
            raise PublicBenchmarkError("malformed host retrieval row")
        if item_id in ids:
            raise PublicBenchmarkError("duplicate host retrieval item")
        ids.add(item_id)
        for rank, hit in enumerate(hits, start=1):
            if not isinstance(hit, dict) or hit.get("rank") != rank:
                raise PublicBenchmarkError("host retrieval rank drift")
            if not isinstance(hit.get("id"), str) or not isinstance(hit.get("title"), str) or not isinstance(hit.get("text"), str):
                raise PublicBenchmarkError("malformed host retrieval hit")
            score = hit.get("score")
            if type(score) not in {int, float}:
                raise PublicBenchmarkError("host retrieval score must be numeric")
    return manifest, rows


def _runtime_inputs(args: argparse.Namespace) -> tuple[str, dict[str, Any], str, dict[str, Any], dict[str, Any]]:
    inventory_sha, model = resolve_model(args.model_inventory, args.model_id, None, args.model_path)
    runtime_sha, runtime = resolve_runtime(args.runtime_record, args.runtime_executable)
    runtime = json.loads(json.dumps(runtime))
    runtime["launch"]["port"] = args.port
    runtime["launch"]["threads"] = args.threads
    generation = load_json(GENERATION_PATH)
    return inventory_sha, model, runtime_sha, runtime, generation


def run_screen(args: argparse.Namespace) -> None:
    if args.output.exists():
        raise PublicBenchmarkError("run output exists; resume/reuse forbidden")
    candidate = args.candidate.resolve()
    manifest, questions, _corpus = verify_candidate(candidate, include_gold=False)
    retrieval_manifest_path = args.retrieval_manifest.resolve()
    retrieval_path = args.retrieval.resolve()
    retrieval_manifest, retrieval_rows = _load_retrieval(candidate, retrieval_manifest_path, retrieval_path)
    retrieval_by_id = {row["item_id"]: row for row in retrieval_rows}
    question_by_id = {row["item_id"]: row["question"] for row in questions}
    if set(retrieval_by_id) != set(question_by_id):
        raise PublicBenchmarkError("retrieval/question item set drift")
    for item_id, question in question_by_id.items():
        if retrieval_by_id[item_id]["question"] != question:
            raise PublicBenchmarkError("retrieval/question text drift")

    inventory_sha, model, runtime_sha, runtime, generation = _runtime_inputs(args)
    calibration_policy = POLICY_PATH.read_bytes()
    prereg = {
        "format": "exactscope.public-hotpot-h1-preregistration",
        "format_version": FORMAT_VERSION,
        "qualification_eligible": False,
        "publication_robustness_only": True,
        "candidate_manifest_sha256": file_sha(candidate / "manifest.json"),
        "retrieval_manifest_sha256": file_sha(retrieval_manifest_path),
        "retrieval_sha256": file_sha(retrieval_path),
        "host_framework": retrieval_manifest["host_framework"],
        "host_retriever": retrieval_manifest["host_retriever"],
        "host_owns_retrieval": True,
        "model_inventory_sha256": inventory_sha,
        "model": model,
        "runtime_record_sha256": runtime_sha,
        "runtime": runtime,
        "generation_config_sha256": file_sha(GENERATION_PATH),
        "model_surface_sha256": surface_sha256(),
        "calibration_policy_sha256": hashlib.sha256(calibration_policy).hexdigest(),
        "attach_policy": {
            "id": POLICY_ID,
            "top_k": TOP_K,
            "max_evidence_bytes": MAX_EVIDENCE_BYTES,
            "max_items": MAX_ITEMS,
            "full_ranked_documents": 1,
            "prompt_profile": "no-policy",
        },
        "arms": ["A", "G"],
        "retry_count": 0,
        "hidden_repair": False,
        "gold_visible_to_runner": False,
    }
    args.output.mkdir(parents=True)
    (args.output / "preregistration.json").write_bytes(canonical_bytes(prereg))
    status_path = args.output / "run-status.json"
    status_path.write_bytes(canonical_bytes({
        "format": RUN_FORMAT,
        "format_version": FORMAT_VERSION,
        "state": "running",
        "model_id": model["id"],
        "item_count": len(questions),
        "record_count": 0,
        "preregistration_sha256": file_sha(args.output / "preregistration.json"),
    }))

    process: subprocess.Popen[bytes] | None = None
    records: list[dict[str, Any]] = []
    log_path = args.output / "llama-server.log"
    try:
        with log_path.open("wb") as server_log:
            command = server_command(prereg)
            runtime_dir = Path(runtime["executable_path"]).resolve().parent
            process = subprocess.Popen(command, cwd=runtime_dir, stdout=server_log, stderr=subprocess.STDOUT, env=os.environ.copy())
            runtime_record = load_json(args.runtime_record)
            wait_server(process, runtime["launch"]["host"], int(runtime["launch"]["port"]), float(runtime_record["server_ready_timeout_seconds"]))
            selected_surface, negotiation = negotiate_grounding_v11_surface(prereg, generation, calibration_policy)
            if selected_surface is None:
                raise PublicBenchmarkError("runtime exposes no supported structured output surface")
            selected_contract, calibration = calibrate_grounding_v1_contract(prereg, generation, calibration_policy, selected_surface)
            (args.output / "surface-negotiation.json").write_bytes(canonical_bytes(negotiation))
            (args.output / "contract-calibration.json").write_bytes(canonical_bytes(calibration))

            for question_row in questions:
                item_id = question_row["item_id"]
                question = question_row["question"]
                host_row = retrieval_by_id[item_id]
                hits = host_row["hits"]

                a = request_grounding_v1_model(
                    prereg, generation, messages(selected_contract, question), selected_contract, selected_surface
                )
                records.append({
                    "item_id": item_id,
                    "arm": "A",
                    **a,
                    "evidence_bytes": 0,
                    "projected_titles": [],
                })

                payload, emitted, meta = project_host_ranked_hybrid_h1(
                    hits,
                    question,
                    max_bytes=MAX_EVIDENCE_BYTES,
                    full_ranked_documents=1,
                    max_items=MAX_ITEMS,
                )
                g = request_grounding_v1_model(
                    prereg, generation, messages(selected_contract, question, evidence=payload), selected_contract, selected_surface
                )
                records.append({
                    "item_id": item_id,
                    "arm": "G",
                    **g,
                    "evidence_bytes": len(payload),
                    "projected_titles": [entry["title"] for entry in emitted],
                    "projection_meta": meta,
                })
    finally:
        stop_server(process)

    _write_cjsonl(args.output / "raw-results.jsonl", records)
    status = {
        "format": RUN_FORMAT,
        "format_version": FORMAT_VERSION,
        "state": "complete",
        "model_id": model["id"],
        "item_count": len(questions),
        "record_count": len(records),
        "selected_model_contract": selected_contract,
        "selected_output_surface": selected_surface,
        "model_runtime_fingerprint": model_runtime_fingerprint(prereg),
        "raw_results_sha256": file_sha(args.output / "raw-results.jsonl"),
        "retrieval_sha256": file_sha(retrieval_path),
        "attach_policy": POLICY_ID,
        "retry_count": 0,
        "gold_visible_to_runner": False,
    }
    status_path.write_bytes(canonical_bytes(status))


def score_run(candidate: Path, retrieval_manifest_path: Path, retrieval_path: Path, run: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise PublicBenchmarkError("score output exists")
    candidate = candidate.resolve()
    manifest, questions, _corpus = verify_candidate(candidate, include_gold=False)
    retrieval_manifest, retrieval_rows = _load_retrieval(candidate, retrieval_manifest_path.resolve(), retrieval_path.resolve())
    status_raw = (run / "run-status.json").read_bytes()
    status = loads(status_raw)
    if not isinstance(status, dict) or status_raw != canonical_bytes(status):
        raise PublicBenchmarkError("noncanonical H1 run status")
    if status.get("format") != RUN_FORMAT or status.get("state") != "complete":
        raise PublicBenchmarkError("H1 run is incomplete")
    raw_path = run / "raw-results.jsonl"
    if status.get("raw_results_sha256") != file_sha(raw_path):
        raise PublicBenchmarkError("H1 raw result digest drift")
    if status.get("retrieval_sha256") != file_sha(retrieval_path):
        raise PublicBenchmarkError("H1 retrieval identity drift")
    records = _load_cjsonl(raw_path)
    expected_keys = {(row["item_id"], arm) for row in questions for arm in ("A", "G")}
    keyed = {(row.get("item_id"), row.get("arm")): row for row in records}
    if len(keyed) != len(records) or set(keyed) != expected_keys:
        raise PublicBenchmarkError("H1 A/G record identity drift")
    for row in records:
        raw_content = row.get("raw_content")
        if not isinstance(raw_content, str):
            raise PublicBenchmarkError("H1 record lacks raw content")
        valid, value = parse_answer_object(raw_content)
        if row.get("model_contract_valid") is not valid or row.get("model_contract_output") != value:
            raise PublicBenchmarkError("H1 raw/model output mismatch")
        if row["arm"] == "A" and (row.get("evidence_bytes") != 0 or row.get("projected_titles") != []):
            raise PublicBenchmarkError("H1 A arm received evidence")

    # Only after run/retrieval identities are verified may scorer-owned gold open.
    verify_candidate(candidate, include_gold=True)
    gold_rows = []
    for line in (candidate / "gold/answers.jsonl").read_bytes().splitlines():
        value = loads(line)
        if not isinstance(value, dict):
            raise PublicBenchmarkError("Hotpot gold row invalid")
        gold_rows.append(value)
    gold = {row["item_id"]: row for row in gold_rows}

    arms: dict[str, dict[str, Any]] = {}
    scored: list[dict[str, Any]] = []
    for arm in ("A", "G"):
        exact = 0
        f1_total = 0.0
        format_failures = 0
        input_tokens = output_tokens = evidence_bytes = latency_us = 0
        all_support = any_support = 0
        for question_row in questions:
            item_id = question_row["item_id"]
            row = keyed[(item_id, arm)]
            expected = gold[item_id]
            prediction = row.get("model_contract_output") if row.get("model_contract_valid") else None
            em = int(_normalize_answer(prediction) == _normalize_answer(expected["answer"]))
            _, _, _, f1 = _f1(prediction, expected["answer"])
            exact += em
            f1_total += f1
            format_failures += int(not row.get("model_contract_valid"))
            input_tokens += int(row.get("input_tokens", 0))
            output_tokens += int(row.get("output_tokens", 0))
            evidence_bytes += int(row.get("evidence_bytes", 0))
            latency_us += int(row.get("model_latency_us", 0))
            if arm == "G":
                support = set(expected["supporting_titles"])
                projected = set(row.get("projected_titles", []))
                all_support += int(support <= projected)
                any_support += int(bool(support & projected))
            scored.append({"item_id": item_id, "arm": arm, "exact_match": bool(em), "f1_milli": int(round(f1 * 1000))})
        n = len(questions)
        arms[arm] = {
            "exact_match": exact / n,
            "f1": f1_total / n,
            "format_failure_rate": format_failures / n,
            "mean_input_tokens": input_tokens / n,
            "mean_output_tokens": output_tokens / n,
            "mean_evidence_bytes": evidence_bytes / n,
            "mean_model_latency_ms": latency_us / n / 1000.0,
        }
        if arm == "G":
            arms[arm]["projected_all_support_titles"] = all_support / n
            arms[arm]["projected_any_support_title"] = any_support / n

    summary = {
        "format": SCORE_FORMAT,
        "format_version": FORMAT_VERSION,
        "publication_robustness_only": True,
        "qualification_eligible": False,
        "candidate_mode": manifest["mode"],
        "host_framework": retrieval_manifest["host_framework"],
        "host_retriever": retrieval_manifest["host_retriever"],
        "attach_policy": POLICY_ID,
        "item_count": len(questions),
        "model_id": status["model_id"],
        "arms": arms,
        "paired": {
            "exact_match_uplift": arms["G"]["exact_match"] - arms["A"]["exact_match"],
            "f1_uplift": arms["G"]["f1"] - arms["A"]["f1"],
        },
        "gold_opened_after_run_integrity": True,
        "notes": {
            "qwen_stability64_result_previously_known": status["model_id"] == "qwen35-08b-q4",
            "panel_may_not_reselect_policy": True,
            "not_ordinary_rag_incremental_proof_across_models": True,
        },
    }
    output.mkdir(parents=True)
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_cjsonl(output / "scored.jsonl", scored)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--candidate", type=Path, required=True)
    run.add_argument("--retrieval-manifest", type=Path, required=True)
    run.add_argument("--retrieval", type=Path, required=True)
    run.add_argument("--model-id", required=True)
    run.add_argument("--model-path", type=Path, required=True)
    run.add_argument("--model-inventory", type=Path, required=True)
    run.add_argument("--runtime-record", type=Path, required=True)
    run.add_argument("--runtime-executable", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--port", type=int, default=18980)
    run.add_argument("--threads", type=int, default=6)
    score = sub.add_parser("score")
    score.add_argument("--candidate", type=Path, required=True)
    score.add_argument("--retrieval-manifest", type=Path, required=True)
    score.add_argument("--retrieval", type=Path, required=True)
    score.add_argument("--run", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            run_screen(args)
            print(json.dumps(loads((args.output / "run-status.json").read_bytes()), indent=2, sort_keys=True))
        else:
            print(json.dumps(score_run(args.candidate, args.retrieval_manifest, args.retrieval, args.run, args.output), indent=2, sort_keys=True))
        return 0
    except (PublicBenchmarkError, BenchmarkRunError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ExactScope public Hotpot H1 benchmark: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
