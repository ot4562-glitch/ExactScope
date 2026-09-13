#!/usr/bin/env python3
"""Gold-blind B/R/G development runner for the Kubernetes Operations proxy."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
BENCH = ROOT / "benchmarks"
sys.path[:0] = [str(TOOLS), str(BENCH)]

from grounding_canonical import canonical_bytes  # noqa: E402
from grounding_preregister import resolve_model, resolve_runtime  # noqa: E402
from grounding_projection import FIXED_EVIDENCE_POLICY_ID, precision_context_evidence_projection_v5  # noqa: E402
from grounding_v1_surface import messages, model_runtime_fingerprint, surface_sha256  # noqa: E402
from run_grounding_benchmark import (  # noqa: E402
    calibrate_grounding_v1_contract,
    negotiate_grounding_v11_surface,
    request_grounding_v1_model,
    server_command,
    stop_server,
    wait_server,
)

PROXY_ROOT = ROOT / "target/kubernetes-pod-ops-docqa-v0.1/dev32"
CANDIDATE = PROXY_ROOT / "candidate"
RETRIEVAL_ROOT = PROXY_ROOT / "host-retrieval"
RETRIEVAL = RETRIEVAL_ROOT / "retrieval.jsonl"
RETRIEVAL_MANIFEST = RETRIEVAL_ROOT / "retrieval-manifest.json"
OUT = PROXY_ROOT / "three-arm-r4"
PROTOCOL = BENCH / "kubernetes_ops_proxy_dev_protocol.json"
ANSWER_POLICY = BENCH / "kubernetes_ops_proxy_answer_policy.txt"
MODEL_INVENTORY = BENCH / "grounding-model-inventory.json"
RUNTIME_RECORD = BENCH / "grounding-runtime-llama-b10797-windows.json"
GENERATION_PATH = BENCH / "grounding-generation-config.json"
MODEL_ID = "qwen35-08b-q4"
TOP_K = 12
MAX_BYTES = 3072
MAX_ITEMS = 8


class ProxyRunError(RuntimeError):
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
                raise ProxyRunError(f"invalid JSONL row: {path}")
            rows.append(value)
    return rows


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        for row in rows:
            f.write(canonical_bytes(row) + b"\n")


def validate_freeze() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    protocol = load_json(PROTOCOL)
    retrieval_manifest = load_json(RETRIEVAL_MANIFEST)
    frozen = {
        "candidate_manifest_sha256": digest(CANDIDATE / "manifest.json"),
        "retrieval_manifest_sha256": digest(RETRIEVAL_MANIFEST),
        "retrieval_sha256": digest(RETRIEVAL),
        "model_inventory_sha256": digest(MODEL_INVENTORY),
        "runtime_record_sha256": digest(RUNTIME_RECORD),
        "generation_config_sha256": digest(GENERATION_PATH),
        "answer_policy_sha256": digest(ANSWER_POLICY),
    }
    for key, value in frozen.items():
        if protocol.get(key) != value:
            raise ProxyRunError(f"frozen identity drift: {key}")
    if protocol.get("runner_source_sha256") != digest(Path(__file__)):
        raise ProxyRunError("runner source digest drift")
    scorer_path = BENCH / "kubernetes_ops_proxy_dev_score.py"
    if protocol.get("scorer_source_sha256") != digest(scorer_path):
        raise ProxyRunError("scorer source digest drift")
    if protocol.get("development_only") is not True or protocol.get("qualification_eligible") is not False:
        raise ProxyRunError("protocol qualification boundary drift")
    if retrieval_manifest.get("host_owns_retrieval") is not True:
        raise ProxyRunError("host retrieval ownership drift")
    if retrieval_manifest.get("gold_visible_during_retrieval") is not False:
        raise ProxyRunError("retrieval gold isolation drift")
    if retrieval_manifest.get("exactscope_used_during_retrieval") is not False:
        raise ProxyRunError("ExactScope must not participate in retrieval ranking")
    questions = load_jsonl(CANDIDATE / "serving/questions.jsonl")
    retrieval_rows = load_jsonl(RETRIEVAL)
    by_id = {row["item_id"]: row for row in retrieval_rows}
    if len(by_id) != len(retrieval_rows) or set(by_id) != {row["item_id"] for row in questions}:
        raise ProxyRunError("retrieval/question identity mismatch")
    if any(len(row.get("hits", [])) != TOP_K for row in retrieval_rows):
        raise ProxyRunError("retrieval top-k drift")
    return protocol, retrieval_manifest, questions, by_id


def ordinary_context(hits: list[dict[str, Any]]) -> bytes | None:
    prefix = b"Authorized Kubernetes documentation (host BM25, ranked):\n"
    out = bytearray(prefix)
    for hit in hits:
        segment = f"\n[{hit['title']} | {hit['path']}]\n{hit['text']}\n".encode("utf-8")
        remaining = MAX_BYTES - len(out)
        if remaining <= 0:
            break
        if len(segment) <= remaining:
            out.extend(segment)
            continue
        fragment = segment[:remaining]
        while fragment:
            try:
                fragment.decode("utf-8")
                break
            except UnicodeDecodeError:
                fragment = fragment[:-1]
        out.extend(fragment)
        break
    return bytes(out) if len(out) > len(prefix) else None


def exactscope_context(hits: list[dict[str, Any]], question: str) -> tuple[bytes | None, list[dict[str, Any]], dict[str, Any]]:
    return precision_context_evidence_projection_v5(
        None,
        hits,
        question,
        max_bytes=MAX_BYTES,
        evidence_policy=FIXED_EVIDENCE_POLICY_ID,
        max_items=MAX_ITEMS,
    )


def run(model_path: Path, runtime_path: Path, port: int) -> None:
    run_dir = OUT / "run"
    if run_dir.exists():
        raise ProxyRunError("run output already exists")
    protocol, retrieval_manifest, questions, retrieval_by_id = validate_freeze()
    inventory_sha, model = resolve_model(MODEL_INVENTORY, MODEL_ID, None, model_path)
    runtime_sha, runtime = resolve_runtime(RUNTIME_RECORD, runtime_path)
    if model.get("sha256") != protocol["model"]["sha256"]:
        raise ProxyRunError("model digest differs from protocol")
    runtime = json.loads(json.dumps(runtime))
    runtime["launch"]["port"] = port
    runtime["launch"]["threads"] = 6
    generation = load_json(GENERATION_PATH)
    policy = ANSWER_POLICY.read_bytes()
    prereg = {
        "format": "exactscope.public-proxy-three-arm-preregistration",
        "format_version": "0.1",
        "development_only": True,
        "qualification_eligible": False,
        "protocol_sha256": digest(PROTOCOL),
        "candidate_manifest_sha256": digest(CANDIDATE / "manifest.json"),
        "retrieval_manifest_sha256": digest(RETRIEVAL_MANIFEST),
        "retrieval_sha256": digest(RETRIEVAL),
        "host_framework": retrieval_manifest["host_framework"],
        "host_retriever": retrieval_manifest["host_retriever"],
        "host_owns_retrieval": True,
        "model_inventory_sha256": inventory_sha,
        "model": model,
        "runtime_record_sha256": runtime_sha,
        "runtime": runtime,
        "generation_config_sha256": digest(GENERATION_PATH),
        "model_surface_sha256": surface_sha256(),
        "answer_policy_sha256": digest(ANSWER_POLICY),
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
            wait_server(process, runtime["launch"]["host"], port, float(load_json(RUNTIME_RECORD)["server_ready_timeout_seconds"]))
            selected_surface, negotiation = negotiate_grounding_v11_surface(prereg, generation, policy)
            if selected_surface is None:
                raise ProxyRunError("no supported output surface")
            selected_contract, calibration = calibrate_grounding_v1_contract(prereg, generation, policy, selected_surface)
            (run_dir / "surface-negotiation.json").write_bytes(canonical_bytes(negotiation))
            (run_dir / "contract-calibration.json").write_bytes(canonical_bytes(calibration))
            for q in questions:
                item_id = q["item_id"]
                question = q["question"]
                hits = retrieval_by_id[item_id]["hits"]
                top_paths = [hit["path"] for hit in hits]
                b = request_grounding_v1_model(prereg, generation, messages(selected_contract, question), selected_contract, selected_surface)
                records.append({"item_id": item_id, "arm": "B", **b, "evidence_bytes": 0, "host_top12_paths": top_paths})
                r_payload = ordinary_context(hits)
                r = request_grounding_v1_model(prereg, generation, messages(selected_contract, question, evidence=r_payload, policy=policy), selected_contract, selected_surface)
                records.append({"item_id": item_id, "arm": "R", **r, "evidence_bytes": len(r_payload) if r_payload else 0, "host_top12_paths": top_paths})
                g_payload, emitted, meta = exactscope_context(hits, question)
                g = request_grounding_v1_model(prereg, generation, messages(selected_contract, question, evidence=g_payload, policy=policy), selected_contract, selected_surface)
                records.append({
                    "item_id": item_id,
                    "arm": "G",
                    **g,
                    "evidence_bytes": len(g_payload) if g_payload else 0,
                    "host_top12_paths": top_paths,
                    "emitted_paths": [row.get("id") for row in emitted],
                    "projection_meta": meta,
                })
    finally:
        stop_server(process)
    write_jsonl(run_dir / "raw-results.jsonl", records)
    status = {
        "format": "exactscope.public-proxy-three-arm-run",
        "format_version": "0.1",
        "state": "complete",
        "item_count": len(questions),
        "record_count": len(records),
        "arms": ["B", "R", "G"],
        "protocol_sha256": digest(PROTOCOL),
        "candidate_manifest_sha256": digest(CANDIDATE / "manifest.json"),
        "retrieval_sha256": digest(RETRIEVAL),
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--runtime-path", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18123)
    args = parser.parse_args()
    run(args.model_path, args.runtime_path, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
