#!/usr/bin/env python3
"""Zero-inference serving dry-run and isolated gold verification for rc4 grounding."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from grounding_canonical import canonical_bytes, canonical_sha256, loads  # noqa: E402
from grounding_runtime import (  # noqa: E402
    GroundingBundle,
    LocalExactLexicalProvider,
    RetrievalProvider,
    load_bundle,
    run_grounding,
)


class DryRunError(RuntimeError):
    pass


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_cjson(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    value = loads(data)
    if not isinstance(value, dict) or data != canonical_bytes(value):
        raise DryRunError(f"noncanonical JSON: {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for number, line in enumerate(path.read_bytes().splitlines(), 1):
        if not line:
            continue
        value = loads(line)
        if not isinstance(value, dict):
            raise DryRunError(f"{path}:{number}: row is not object")
        if line != canonical_bytes(value):
            raise DryRunError(f"{path}:{number}: row is not canonical")
        rows.append(value)
    ids = [row.get("item_id") for row in rows]
    if any(not isinstance(value, str) or not value for value in ids) or len(ids) != len(set(ids)):
        raise DryRunError(f"{path}: invalid/duplicate item IDs")
    return rows


def verify_ref(base: Path, ref: dict[str, Any]) -> Path:
    if not isinstance(ref, dict) or set(ref) != {"path", "sha256", "encoding"}:
        raise DryRunError("invalid manifest reference")
    path = base / ref["path"]
    if not path.is_file() or path.is_symlink():
        raise DryRunError(f"missing manifest file: {ref['path']}")
    if file_sha(path) != ref["sha256"]:
        raise DryRunError(f"manifest digest mismatch: {ref['path']}")
    return path


class FaultProvider:
    provider_id = "local-exact-lexical"

    def __init__(self, bundle: GroundingBundle, fault: dict[str, Any] | None) -> None:
        self.bundle = bundle
        self.inner = LocalExactLexicalProvider(bundle)
        self.fault = fault

    def retrieve(self, envelope, target, binding):
        fault = self.fault
        if fault is None or fault.get("source_id") not in binding.get("source_ids", []):
            return self.inner.retrieve(envelope, target, binding)
        status = fault.get("status")
        if status not in {"timeout", "error", "denied", "budget_exceeded"}:
            raise DryRunError("invalid serving fault status")
        refs = [canonical_sha256(self.bundle.source_snapshots[source]) for source in binding["source_ids"]]
        return {
            "v": 1,
            "qid": envelope["qid"],
            "profile_sha256": self.bundle.profile_sha256,
            "security_scope_id": envelope["security_scope_id"],
            "target_key": target["target_key"],
            "provider_id": binding["provider_id"],
            "attempt": 1,
            "source_snapshot_refs": refs,
            "status": status,
            "complete": False,
            "candidates": [],
            "reason": "injected-" + status,
        }


def load_serving(candidate: Path):
    candidate = candidate.resolve()
    serving = candidate / "serving"
    manifests = candidate / "manifests"
    if not serving.is_dir() or not manifests.is_dir():
        raise DryRunError("candidate lacks serving/manifests")
    serving_manifest = read_cjson(manifests / "serving-manifest.json")
    questions_path = verify_ref(serving, serving_manifest["questions"])
    faults_path = verify_ref(serving, serving_manifest["faults"])
    bundle = load_bundle(serving / "grounding")
    if bundle.profile_sha256 != serving_manifest["grounding_profile_sha256"]:
        raise DryRunError("serving profile digest drift")
    if canonical_sha256(bundle.manifest) != serving_manifest["grounding_manifest_sha256"]:
        raise DryRunError("serving grounding manifest digest drift")
    questions = load_jsonl(questions_path)
    faults = {row["item_id"]: row for row in load_jsonl(faults_path)}
    if len(questions) != serving_manifest["item_count"]:
        raise DryRunError("serving item count drift")
    # Serving inputs must not contain scorer-only oracle keys.
    forbidden_keys = {
        "allowed_answers", "answer_expected", "expected_target_keys", "expected_states",
        "valid_evidence", "forbidden_evidence", "required_disposition", "obsolete_answer",
        "injection_bait", "auth_unresolved", "stratum", "authority_class",
    }
    for row in questions + list(faults.values()):
        if forbidden_keys.intersection(row):
            raise DryRunError("scorer-only field leaked into serving input")
    return serving_manifest, bundle, questions, faults


def serving_run(candidate: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise DryRunError("dry-run output already exists")
    manifest, bundle, questions, faults = load_serving(candidate)
    output.mkdir(parents=True)
    records = []
    for question in questions:
        item_id = question["item_id"]
        envelope = {
            "v": 1,
            "qid": item_id,
            "profile_sha256": bundle.profile_sha256,
            "q": question["question"],
            "security_scope_id": question["security_scope_id"],
        }
        result = run_grounding(bundle, envelope, FaultProvider(bundle, faults.get(item_id)))
        evidence = result["projection"]["evidence"]
        records.append(
            {
                "v": 1,
                "item_id": item_id,
                "frame": result["frame"],
                "audit": result["audit"],
                "projection_sha256": hashlib.sha256(evidence).hexdigest(),
                "projection_bytes": len(evidence),
            }
        )
    records.sort(key=lambda row: row["item_id"])
    record_bytes = b"".join(canonical_bytes(row) + b"\n" for row in records)
    records_path = output / "serving-records.jsonl"
    records_path.write_bytes(record_bytes)
    report = {
        "v": 1,
        "mode": "serving-only-zero-inference",
        "candidate_id": manifest["candidate_id"],
        "grounding_profile_sha256": bundle.profile_sha256,
        "item_count": len(records),
        "records_sha256": hashlib.sha256(record_bytes).hexdigest(),
        "model_requests": 0,
        "gold_reads": 0,
    }
    (output / "serving-report.json").write_bytes(canonical_bytes(report))
    return report


def gold_verify(candidate: Path, records_path: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise DryRunError("gold verification output already exists")
    candidate = candidate.resolve()
    gold = candidate / "gold"
    manifests = candidate / "manifests"
    gold_manifest = read_cjson(manifests / "gold-manifest.json")
    evidence_rows = {row["item_id"]: row for row in load_jsonl(verify_ref(gold, gold_manifest["expected_evidence"]))}
    class_rows = {row["item_id"]: row for row in load_jsonl(verify_ref(gold, gold_manifest["class_labels"]))}
    answer_rows = {row["item_id"]: row for row in load_jsonl(verify_ref(gold, gold_manifest["answers"]))}
    records = load_jsonl(records_path.resolve())
    if set(evidence_rows) != set(class_rows) or set(evidence_rows) != set(answer_rows) or set(evidence_rows) != {row["item_id"] for row in records}:
        raise DryRunError("gold/serving item set mismatch")

    failures = []
    stage_counts = {
        "routing_correct": 0,
        "state_correct": 0,
        "valid_evidence_only": 0,
        "no_forbidden_evidence": 0,
    }
    state_counts: dict[str, dict[str, int]] = {}
    for record in records:
        item_id = record["item_id"]
        gold_row = evidence_rows[item_id]
        frame = record["frame"]
        actual_groups = {group["target_key"]: group for group in frame["groups"]}
        expected_targets = set(gold_row["expected_target_keys"])
        routing_ok = set(actual_groups) == expected_targets
        stage_counts["routing_correct"] += int(routing_ok)
        states_ok = routing_ok and all(actual_groups[key]["state"] == state for key, state in gold_row["expected_states"].items())
        stage_counts["state_correct"] += int(states_ok)
        emitted = {
            (item["source_id"], item["item_id"], item["source_revision"])
            for group in actual_groups.values()
            for item in group["items"]
        }
        valid = {tuple(value) for value in gold_row["valid_evidence"]}
        forbidden = {tuple(value) for value in gold_row["forbidden_evidence"]}
        valid_only = emitted <= valid
        no_forbidden = not (emitted & forbidden)
        stage_counts["valid_evidence_only"] += int(valid_only)
        stage_counts["no_forbidden_evidence"] += int(no_forbidden)
        for expected_state in gold_row["expected_states"].values():
            bucket = state_counts.setdefault(expected_state, {"correct": 0, "total": 0})
            bucket["total"] += 1
            bucket["correct"] += int(states_ok)
        if not (routing_ok and states_ok and valid_only and no_forbidden):
            failures.append(
                {
                    "item_id": item_id,
                    "routing_ok": routing_ok,
                    "states_ok": states_ok,
                    "valid_only": valid_only,
                    "no_forbidden": no_forbidden,
                    "actual_states": {key: group["state"] for key, group in actual_groups.items()},
                    "expected_states": gold_row["expected_states"],
                }
            )
    total = len(records)
    report = {
        "v": 1,
        "mode": "scorer-side-zero-inference-verification",
        "item_count": total,
        "stage_counts": {key: {"numerator": value, "denominator": total} for key, value in stage_counts.items()},
        "state_counts": state_counts,
        "failure_count": len(failures),
        "failures": failures,
        "pass": not failures,
        "model_requests": 0,
    }
    output.mkdir(parents=True)
    (output / "gold-verification.json").write_bytes(canonical_bytes(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve")
    serve.add_argument("--candidate", type=Path, required=True)
    serve.add_argument("--output", type=Path, required=True)
    score = sub.add_parser("verify-gold")
    score.add_argument("--candidate", type=Path, required=True)
    score.add_argument("--records", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "serve":
        result = serving_run(args.candidate, args.output)
    else:
        result = gold_verify(args.candidate, args.records, args.output)
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("pass", True) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DryRunError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ExactScope grounding dry-run: FAIL: {exc}")
        raise SystemExit(1) from exc
