#!/usr/bin/env python3
"""Run and score a gold-isolated FEVER ExactScope development screen."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "tools", ROOT / "benchmarks"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from grounding_canonical import canonical_bytes, loads
from grounding_corpus import index_sha256, load_index, search
from grounding_projection import compact_evidence_projection
from grounding_preregister import file_sha, load_json, resolve_model, resolve_runtime
from grounding_v1_surface import messages, parse_answer_object, surface_sha256
from run_grounding_benchmark import (
    BenchmarkRunError,
    calibrate_grounding_v1_contract,
    request_grounding_v1_model,
    server_command,
    stop_server,
    wait_server,
    write_sums,
)

LABELS = ("SUPPORTS", "REFUTES", "NOT ENOUGH INFO")
QUESTION_PREFIX = (
    "Classify the following claim using only the supplied evidence. "
    "Answer SUPPORTS if the evidence supports the claim, REFUTES if it contradicts the claim, "
    "or NOT ENOUGH INFO if it establishes neither. Return exactly one JSON object with the single "
    "field a, whose value is one of those three strings. Claim: "
)
POLICY_PATH = ROOT / "grounding/reference-profile-v0.1/projection-policy.txt"
DEFAULT_TOP_K = 12
DEFAULT_MAX_EVIDENCE_BYTES = 4096
SOURCE_FILES = (
    "benchmarks/public_fever_benchmark.py",
    "benchmarks/public_fever_candidate.py",
    "benchmarks/run_grounding_benchmark.py",
    "tools/grounding_corpus.py",
    "tools/grounding_projection.py",
    "tools/grounding_v1_surface.py",
)


class FeverBenchmarkError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_cjson(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = loads(raw)
    if not isinstance(value, dict) or raw != canonical_bytes(value):
        raise FeverBenchmarkError(f"expected canonical JSON object: {path}")
    return value


def load_cjsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_bytes().splitlines():
        value = loads(line)
        if not isinstance(value, dict) or line != canonical_bytes(value):
            raise FeverBenchmarkError(f"expected canonical JSONL object row: {path}")
        rows.append(value)
    return rows


def source_hashes() -> dict[str, str]:
    return {name: file_sha(ROOT / name) for name in SOURCE_FILES}


def question_text(claim: str) -> str:
    if not isinstance(claim, str) or not claim.strip():
        raise FeverBenchmarkError("FEVER claim must be nonempty text")
    return QUESTION_PREFIX + claim


def question_template_sha256() -> str:
    return sha256_bytes(QUESTION_PREFIX.encode("utf-8"))


def normalize_label(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    translated = "".join(chr(ord(ch) - 32) if "a" <= ch <= "z" else ch for ch in stripped)
    return translated if translated in LABELS else None


def verify_serving_candidate(candidate: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    serving = candidate / "serving"
    manifest = load_cjson(serving / "manifest.json")
    if manifest.get("format") != "exactscope.public-fever-serving-candidate" or manifest.get("format_version") != "0.1":
        raise FeverBenchmarkError("FEVER serving candidate identity drift")
    if manifest.get("qualification_eligible") is not False or manifest.get("oracle_assisted_corpus") is not True:
        raise FeverBenchmarkError("FEVER development-mode disclosure drift")
    items_path = serving / "items.jsonl"
    candidates_path = serving / "corpus-candidates.jsonl"
    corpus_path = serving / "corpus-index.json"
    items = load_cjsonl(items_path)
    candidates = load_cjsonl(candidates_path)
    if len(items) != manifest.get("item_count") or len({row.get("id") for row in items}) != len(items):
        raise FeverBenchmarkError("FEVER serving item identity drift")
    if any(set(row) != {"id", "claim"} for row in items):
        raise FeverBenchmarkError("FEVER serving item contains forbidden fields")
    if len(candidates) != manifest.get("corpus_candidate_count") or len({row.get("candidate_id") for row in candidates}) != len(candidates):
        raise FeverBenchmarkError("FEVER corpus candidate identity drift")
    if any(set(row) != {"candidate_id", "page", "sentence_id", "text"} for row in candidates):
        raise FeverBenchmarkError("FEVER corpus candidate contains forbidden fields")
    if file_sha(items_path) != manifest.get("items_sha256") or file_sha(candidates_path) != manifest.get("corpus_candidates_sha256"):
        raise FeverBenchmarkError("FEVER serving file hash drift")
    corpus = load_index(corpus_path)
    if index_sha256(corpus) != manifest.get("corpus_index_sha256"):
        raise FeverBenchmarkError("FEVER corpus index hash drift")
    candidate_ids = {row["candidate_id"] for row in candidates}
    if {doc["id"] for doc in corpus["documents"]} != candidate_ids:
        raise FeverBenchmarkError("FEVER corpus index/candidate set drift")
    return manifest, items, candidates, corpus


def resolve_inputs(args: argparse.Namespace):
    inventory_sha, model = resolve_model(
        ROOT / "benchmarks/grounding-model-inventory.json", args.model_id, args.model_root, args.model_path
    )
    runtime_sha, runtime = resolve_runtime(args.runtime_record, args.runtime_executable)
    runtime = json.loads(json.dumps(runtime))
    runtime["launch"]["port"] = args.port
    runtime["launch"]["threads"] = args.threads
    generation = load_json(ROOT / "benchmarks/grounding-generation-config.json")
    return inventory_sha, model, runtime_sha, runtime, generation


def run_screen(args: argparse.Namespace) -> None:
    if args.output.exists():
        raise FeverBenchmarkError("run output exists; resume/reuse forbidden")
    if not 1 <= args.top_k <= 16:
        raise FeverBenchmarkError("top_k must be between 1 and 16")
    if not 256 <= args.max_evidence_bytes <= 4096:
        raise FeverBenchmarkError("max_evidence_bytes must be between 256 and 4096")
    candidate = args.candidate.resolve()
    manifest, items, candidates, corpus = verify_serving_candidate(candidate)
    inventory_sha, model, runtime_sha, runtime, generation = resolve_inputs(args)
    policy = POLICY_PATH.read_bytes()
    serving_manifest_path = candidate / "serving/manifest.json"
    prereg = {
        "format": "exactscope.public-fever-preregistration",
        "format_version": "0.1",
        "qualification_eligible": False,
        "candidate": {
            "serving_manifest_sha256": file_sha(serving_manifest_path),
            "items_sha256": manifest["items_sha256"],
            "corpus_candidates_sha256": manifest["corpus_candidates_sha256"],
            "corpus_index_sha256": manifest["corpus_index_sha256"],
            "item_count": manifest["item_count"],
            "mode": manifest["mode"],
        },
        "source_files": source_hashes(),
        "model_inventory_sha256": inventory_sha,
        "model": model,
        "runtime_record_sha256": runtime_sha,
        "runtime": runtime,
        "generation_config_sha256": file_sha(ROOT / "benchmarks/grounding-generation-config.json"),
        "model_surface_sha256": surface_sha256(),
        "question_template_sha256": question_template_sha256(),
        "policy_sha256": sha256_bytes(policy),
        "top_k": args.top_k,
        "max_evidence_bytes": args.max_evidence_bytes,
        "arms": ["A", "G"],
        "retry_count": 0,
        "hidden_repair": False,
        "gold_visible_to_runner": False,
    }
    args.output.mkdir(parents=True)
    (args.output / "preregistration.json").write_bytes(canonical_bytes(prereg))
    status_path = args.output / "run-status.json"
    status = {
        "format": "exactscope.public-fever-run",
        "format_version": "0.1",
        "state": "running",
        "item_count": len(items),
        "record_count": 0,
        "model_id": model["id"],
        "preregistration_sha256": file_sha(args.output / "preregistration.json"),
    }
    status_path.write_bytes(canonical_bytes(status))
    raw_path = args.output / "raw-results.jsonl"
    log_path = args.output / "llama-server.log"
    command = server_command(prereg)
    env = os.environ.copy()
    runtime_dir = str(Path(runtime["executable_path"]).resolve().parent)
    env["LD_LIBRARY_PATH"] = runtime_dir + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    process: subprocess.Popen[bytes] | None = None
    records: list[dict[str, Any]] = []
    try:
        with log_path.open("wb") as server_log:
            process = subprocess.Popen(command, cwd=runtime_dir, stdout=server_log, stderr=subprocess.STDOUT, env=env)
            runtime_record = load_json(args.runtime_record)
            wait_server(process, runtime["launch"]["host"], int(runtime["launch"]["port"]), float(runtime_record["server_ready_timeout_seconds"]))
            selected, calibration = calibrate_grounding_v1_contract(prereg, generation, policy)
            (args.output / "contract-calibration.json").write_bytes(canonical_bytes(calibration))
            with raw_path.open("wb") as raw:
                for item in items:
                    q = question_text(item["claim"])
                    a = request_grounding_v1_model(prereg, generation, messages(selected, q), selected)
                    a_record = {
                        "item_id": item["id"],
                        "arm": "A",
                        "model_contract": selected,
                        "model_contract_valid": a["model_contract_valid"],
                        "model_contract_output": a["model_contract_output"],
                        "raw_content": a["raw_content"],
                        "input_tokens": a["input_tokens"],
                        "output_tokens": a["output_tokens"],
                        "model_latency_us": a["model_latency_us"],
                        "retrieved_candidate_ids": [],
                        "projected_candidate_ids": [],
                        "evidence_bytes": 0,
                    }
                    raw.write(canonical_bytes(a_record) + b"\n")
                    records.append(a_record)

                    retrieved = search(corpus, q, top_k=args.top_k)
                    projection, emitted = compact_evidence_projection(
                        corpus, retrieved, q, max_bytes=args.max_evidence_bytes
                    )
                    g_messages = messages(selected, q, evidence=projection, policy=policy) if projection else messages(selected, q)
                    g = request_grounding_v1_model(prereg, generation, g_messages, selected)
                    g_record = {
                        "item_id": item["id"],
                        "arm": "G",
                        "model_contract": selected,
                        "model_contract_valid": g["model_contract_valid"],
                        "model_contract_output": g["model_contract_output"],
                        "raw_content": g["raw_content"],
                        "input_tokens": g["input_tokens"],
                        "output_tokens": g["output_tokens"],
                        "model_latency_us": g["model_latency_us"],
                        "retrieved_candidate_ids": [hit["id"] for hit in retrieved],
                        "projected_candidate_ids": [hit["id"] for hit in emitted],
                        "evidence_bytes": len(projection) if projection else 0,
                    }
                    raw.write(canonical_bytes(g_record) + b"\n")
                    records.append(g_record)
        stop_server(process)
        process = None
        if source_hashes() != prereg["source_files"]:
            raise FeverBenchmarkError("FEVER benchmark source hash drift during run")
        verify_serving_candidate(candidate)
        status.update({
            "state": "complete",
            "record_count": len(records),
            "selected_model_contract": selected,
            "calibration_model_requests": calibration["model_request_count"],
            "answer_model_requests": len(records),
            "total_model_requests_including_calibration": len(records) + calibration["model_request_count"],
            "model_surface_sha256": prereg["model_surface_sha256"],
        })
        status_path.write_bytes(canonical_bytes(status))
        write_sums(args.output)
    except Exception:
        stop_server(process)
        if args.output.exists():
            status["state"] = "invalid"
            status["record_count"] = len(records)
            status_path.write_bytes(canonical_bytes(status))
            write_sums(args.output)
        raise


def verify_run(candidate: Path, run: Path, item_count: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest, items, _, _ = verify_serving_candidate(candidate)
    status = load_cjson(run / "run-status.json")
    if status.get("state") != "complete" or status.get("record_count") != item_count * 2:
        raise FeverBenchmarkError("FEVER run is incomplete")
    sums: dict[str, str] = {}
    for line in (run / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        if "  " not in line:
            raise FeverBenchmarkError("invalid FEVER SHA256SUMS line")
        digest, relative = line.split("  ", 1)
        if relative in sums or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise FeverBenchmarkError("unsafe/duplicate FEVER SHA256SUMS path")
        sums[relative] = digest
    actual = {p.relative_to(run).as_posix() for p in run.rglob("*") if p.is_file() and p.name != "SHA256SUMS"}
    if set(sums) != actual or any(file_sha(run / relative) != digest for relative, digest in sums.items()):
        raise FeverBenchmarkError("FEVER run checksum mismatch")
    prereg = load_cjson(run / "preregistration.json")
    expected_candidate = {
        "serving_manifest_sha256": file_sha(candidate / "serving/manifest.json"),
        "items_sha256": manifest["items_sha256"],
        "corpus_candidates_sha256": manifest["corpus_candidates_sha256"],
        "corpus_index_sha256": manifest["corpus_index_sha256"],
        "item_count": manifest["item_count"],
        "mode": manifest["mode"],
    }
    if prereg.get("candidate") != expected_candidate or prereg.get("source_files") != source_hashes():
        raise FeverBenchmarkError("FEVER run source/candidate identity drift")
    if prereg.get("model_surface_sha256") != surface_sha256() or prereg.get("question_template_sha256") != question_template_sha256():
        raise FeverBenchmarkError("FEVER model/question surface drift")
    if prereg.get("gold_visible_to_runner") is not False or prereg.get("arms") != ["A", "G"]:
        raise FeverBenchmarkError("FEVER A/G isolation drift")
    if status.get("preregistration_sha256") != file_sha(run / "preregistration.json"):
        raise FeverBenchmarkError("FEVER preregistration/status drift")
    calibration = load_cjson(run / "contract-calibration.json")
    selected = status.get("selected_model_contract")
    if calibration.get("selected_contract") != selected or calibration.get("model_surface_sha256") != prereg["model_surface_sha256"]:
        raise FeverBenchmarkError("FEVER calibration drift")
    records = load_cjsonl(run / "raw-results.jsonl")
    if len(records) != item_count * 2 or status.get("answer_model_requests") != len(records):
        raise FeverBenchmarkError("FEVER model request accounting drift")
    expected_keys = {(item["id"], arm) for item in items for arm in ("A", "G")}
    actual_keys = {(row.get("item_id"), row.get("arm")) for row in records}
    if actual_keys != expected_keys or len(actual_keys) != len(records):
        raise FeverBenchmarkError("FEVER A/G record identity drift")
    for row in records:
        if row.get("model_contract") != selected or row.get("arm") not in {"A", "G"}:
            raise FeverBenchmarkError("FEVER model contract drift")
        valid, value = parse_answer_object(row.get("raw_content")) if isinstance(row.get("raw_content"), str) else (False, None)
        if row.get("model_contract_valid") is not valid or row.get("model_contract_output") != value:
            raise FeverBenchmarkError("FEVER raw/model output mismatch")
        if row["arm"] == "A" and (row.get("retrieved_candidate_ids") or row.get("projected_candidate_ids") or row.get("evidence_bytes") != 0):
            raise FeverBenchmarkError("FEVER A arm received retrieval evidence")
    return status, records


def evidence_groups_as_ids(gold: dict[str, Any], pair_to_id: dict[tuple[str, int], str]) -> list[set[str]]:
    groups: list[set[str]] = []
    for group in gold["evidence_sets"]:
        groups.append({pair_to_id[(entry["page"], entry["sentence_id"])] for entry in group})
    return groups


def score_run(candidate: Path, run: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise FeverBenchmarkError("score output exists")
    manifest, items, candidates, _ = verify_serving_candidate(candidate)
    status, records = verify_run(candidate, run, len(items))
    # Gold opens only after serving/run identity, source hashes and raw outputs verify.
    gold_manifest = load_cjson(candidate / "gold/manifest.json")
    if gold_manifest.get("serving_manifest_sha256") != file_sha(candidate / "serving/manifest.json"):
        raise FeverBenchmarkError("FEVER gold/serving identity drift")
    gold_rows = load_cjsonl(candidate / "gold/items.jsonl")
    if file_sha(candidate / "gold/items.jsonl") != gold_manifest.get("items_sha256"):
        raise FeverBenchmarkError("FEVER gold file hash drift")
    gold = {row["id"]: row for row in gold_rows}
    if set(gold) != {item["id"] for item in items}:
        raise FeverBenchmarkError("FEVER gold item set drift")
    pair_to_id = {(row["page"], row["sentence_id"]): row["candidate_id"] for row in candidates}
    keyed = {(row["item_id"], row["arm"]): row for row in records}

    arms: dict[str, Any] = {}
    scored: list[dict[str, Any]] = []
    for arm in ("A", "G"):
        correct = 0
        valid_labels = 0
        abstentions = 0
        invalids = 0
        class_total = Counter()
        class_correct = Counter()
        confusion = Counter()
        for item in items:
            expected = gold[item["id"]]["label"]
            row = keyed[(item["id"], arm)]
            parsed = row["model_contract_output"] if row["model_contract_valid"] else None
            normalized = normalize_label(parsed)
            if row["model_contract_valid"] and parsed is None:
                abstentions += 1
            elif normalized is None:
                invalids += 1
            else:
                valid_labels += 1
            is_correct = normalized == expected
            correct += int(is_correct)
            class_total[expected] += 1
            class_correct[expected] += int(is_correct)
            confusion[(expected, normalized or "<INVALID_OR_ABSTAIN>")] += 1
            scored.append({"item_id": item["id"], "arm": arm, "expected": expected, "predicted": normalized, "correct": is_correct})
        per_class = {label: class_correct[label] / class_total[label] for label in LABELS}
        arms[arm] = {
            "label_accuracy": correct / len(items),
            "macro_accuracy": sum(per_class.values()) / len(LABELS),
            "per_class_accuracy": per_class,
            "valid_label_rate": valid_labels / len(items),
            "abstention_rate": abstentions / len(items),
            "invalid_or_unrecognized_rate": invalids / len(items),
            "mean_input_tokens": sum(keyed[(item["id"], arm)]["input_tokens"] for item in items) / len(items),
            "confusion": {f"{expected}->{predicted}": count for (expected, predicted), count in sorted(confusion.items())},
        }

    verifiable = 0
    retrieval_any = retrieval_complete = projection_any = projection_complete = 0
    label_plus_evidence = 0
    for item in items:
        expected = gold[item["id"]]
        g = keyed[(item["id"], "G")]
        normalized = normalize_label(g["model_contract_output"] if g["model_contract_valid"] else None)
        if expected["label"] == "NOT ENOUGH INFO":
            label_plus_evidence += int(normalized == expected["label"])
            continue
        verifiable += 1
        groups = evidence_groups_as_ids(expected, pair_to_id)
        union = set().union(*groups)
        retrieved = set(g["retrieved_candidate_ids"])
        projected = set(g["projected_candidate_ids"])
        retrieval_any += int(bool(retrieved & union))
        retrieval_complete += int(any(group <= retrieved for group in groups))
        projection_any += int(bool(projected & union))
        complete_projected = any(group <= projected for group in groups)
        projection_complete += int(complete_projected)
        label_plus_evidence += int(normalized == expected["label"] and complete_projected)

    summary = {
        "format": "exactscope.public-fever-summary",
        "format_version": "0.1",
        "item_count": len(items),
        "model_id": status["model_id"],
        "selected_model_contract": status["selected_model_contract"],
        "candidate_mode": manifest["mode"],
        "arms": arms,
        "paired": {"label_accuracy_uplift": arms["G"]["label_accuracy"] - arms["A"]["label_accuracy"]},
        "evidence": {
            "verifiable_item_count": verifiable,
            "retrieval_any_gold": retrieval_any / verifiable,
            "retrieval_complete_group": retrieval_complete / verifiable,
            "projection_any_gold": projection_any / verifiable,
            "projection_complete_group": projection_complete / verifiable,
            "mean_g_evidence_bytes": sum(keyed[(item["id"], "G")]["evidence_bytes"] for item in items) / len(items),
        },
        "custom_label_plus_evidence_accuracy": label_plus_evidence / len(items),
        "notes": {
            "qualification_eligible": False,
            "official_fever_score": False,
            "oracle_assisted_pooled_page_corpus": True,
            "balanced_development_subset": True,
            "gold_opened_after_run_integrity": True,
            "parallel_latency_is_not_release_latency": True,
        },
    }
    output.mkdir(parents=True)
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "scored.jsonl").write_bytes(b"".join(canonical_bytes(row) + b"\n" for row in scored))
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--candidate", type=Path, required=True)
    run.add_argument("--model-id", required=True)
    run.add_argument("--model-root", type=Path)
    run.add_argument("--model-path", type=Path)
    run.add_argument("--runtime-record", type=Path, required=True)
    run.add_argument("--runtime-executable", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--port", type=int, default=18601)
    run.add_argument("--threads", type=int, default=6)
    run.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    run.add_argument("--max-evidence-bytes", type=int, default=DEFAULT_MAX_EVIDENCE_BYTES)
    score = sub.add_parser("score")
    score.add_argument("--candidate", type=Path, required=True)
    score.add_argument("--run", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            run_screen(args)
            print(json.dumps(load_cjson(args.output / "run-status.json"), indent=2, sort_keys=True))
        else:
            print(json.dumps(score_run(args.candidate, args.run, args.output), indent=2, sort_keys=True))
        return 0
    except (FeverBenchmarkError, BenchmarkRunError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ExactScope public FEVER benchmark: FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
