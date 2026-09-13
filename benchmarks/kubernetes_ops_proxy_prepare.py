#!/usr/bin/env python3
"""Validate and prepare the Kubernetes Operations proxy development cohort.

This step is model-free. It validates scorer-side provenance, then emits a
runner-visible gold-free candidate under target/.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "benchmarks/kubernetes_ops_proxy_source.json"
DEV_ITEMS = ROOT / "benchmarks/kubernetes_ops_proxy_dev32.jsonl"
SOURCE_ROOT = ROOT / "target/kubernetes-pod-ops-docqa-v0.1/source"
DEFAULT_OUT = ROOT / "target/kubernetes-pod-ops-docqa-v0.1/dev32/candidate"
EXPECTED_STATES = {"answerable": 22, "unanswerable": 6, "ambiguous": 4}
EXPECTED_RETRIEVAL_STRESS = 6


class ProxyPrepareError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ProxyPrepareError(f"{path}:{line_no}: row is not an object")
        rows.append(value)
    return rows


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(canonical_json_bytes(row).decode("utf-8"))


def norm_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def validate_source() -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = load_json(SOURCE_MANIFEST)
    snapshot = load_json(SOURCE_ROOT / "source-snapshot.json")
    corpus = load_json(SOURCE_ROOT / "corpus-index.json")
    if manifest.get("development_only") is not True or manifest.get("qualification_eligible") is not False:
        raise ProxyPrepareError("source manifest qualification boundary drift")
    if snapshot.get("development_only") is not True or snapshot.get("qualification_eligible") is not False:
        raise ProxyPrepareError("source snapshot qualification boundary drift")
    if snapshot.get("source_manifest_sha256") != sha256_file(SOURCE_MANIFEST):
        raise ProxyPrepareError("source snapshot is not bound to current source manifest")
    if snapshot.get("commit") != manifest.get("source", {}).get("commit"):
        raise ProxyPrepareError("source commit drift")
    if corpus.get("source_snapshot_sha256") != sha256_file(SOURCE_ROOT / "source-snapshot.json"):
        raise ProxyPrepareError("corpus index source snapshot drift")
    docs = corpus.get("documents")
    if not isinstance(docs, list) or len(docs) != snapshot.get("file_count"):
        raise ProxyPrepareError("corpus document count drift")
    return snapshot, corpus


def validate_items(rows: list[dict[str, Any]], corpus: dict[str, Any]) -> dict[str, Any]:
    if len(rows) != 32:
        raise ProxyPrepareError(f"development cohort must contain 32 items, got {len(rows)}")
    item_ids = [row.get("item_id") for row in rows]
    group_ids = [row.get("group_id") for row in rows]
    if not all(isinstance(v, str) and v for v in item_ids) or len(set(item_ids)) != len(item_ids):
        raise ProxyPrepareError("item ids must be unique nonempty strings")
    if not all(isinstance(v, str) and v for v in group_ids) or len(set(group_ids)) != len(group_ids):
        raise ProxyPrepareError("development group ids must be unique nonempty strings")

    state_counts = Counter(row.get("truth_state") for row in rows)
    if dict(state_counts) != EXPECTED_STATES:
        raise ProxyPrepareError(f"truth-state allocation drift: {dict(state_counts)}")
    stress_count = sum(row.get("retrieval_stress") is True for row in rows)
    if stress_count != EXPECTED_RETRIEVAL_STRESS:
        raise ProxyPrepareError(f"retrieval-stress allocation drift: {stress_count}")

    docs = corpus["documents"]
    by_path = {doc.get("path"): doc for doc in docs}
    if len(by_path) != len(docs):
        raise ProxyPrepareError("corpus path identities are not unique")

    for row in rows:
        required = {
            "item_id",
            "group_id",
            "question",
            "truth_state",
            "answer",
            "answer_type",
            "source_paths",
            "support_substrings",
            "retrieval_stress",
        }
        if set(row) != required:
            raise ProxyPrepareError(f"{row.get('item_id')}: item keys drift")
        if not isinstance(row["question"], str) or not row["question"].strip():
            raise ProxyPrepareError(f"{row['item_id']}: empty question")
        if type(row["retrieval_stress"]) is not bool:
            raise ProxyPrepareError(f"{row['item_id']}: retrieval_stress must be bool")
        state = row["truth_state"]
        paths = row["source_paths"]
        supports = row["support_substrings"]
        if not isinstance(paths, list) or not isinstance(supports, list):
            raise ProxyPrepareError(f"{row['item_id']}: provenance lists required")
        if state == "answerable":
            if row["answer_type"] != "text" or not isinstance(row["answer"], str) or not row["answer"].strip():
                raise ProxyPrepareError(f"{row['item_id']}: invalid answerable gold")
            if not paths or not supports:
                raise ProxyPrepareError(f"{row['item_id']}: answerable item lacks provenance")
        elif state == "ambiguous":
            if row["answer_type"] != "disposition" or row["answer"] != "AMBIGUOUS" or not paths or not supports:
                raise ProxyPrepareError(f"{row['item_id']}: invalid ambiguous gold")
        elif state == "unanswerable":
            if row["answer_type"] != "disposition" or row["answer"] != "UNANSWERABLE" or paths or supports:
                raise ProxyPrepareError(f"{row['item_id']}: invalid unanswerable gold")
        else:
            raise ProxyPrepareError(f"{row['item_id']}: unsupported truth state {state!r}")

        normalized_sources: list[str] = []
        for source_path in paths:
            doc = by_path.get(source_path)
            if not isinstance(doc, dict):
                raise ProxyPrepareError(f"{row['item_id']}: source path outside frozen corpus: {source_path}")
            raw_path = SOURCE_ROOT / "materialized" / source_path
            if not raw_path.is_file() or sha256_file(raw_path) != doc.get("sha256"):
                raise ProxyPrepareError(f"{row['item_id']}: materialized source digest drift: {source_path}")
            normalized_sources.append(norm_ws(raw_path.read_text(encoding="utf-8")))
        for support in supports:
            if not isinstance(support, str) or not support.strip():
                raise ProxyPrepareError(f"{row['item_id']}: empty support substring")
            needle = norm_ws(support)
            if not any(needle in source for source in normalized_sources):
                raise ProxyPrepareError(f"{row['item_id']}: support text not found in declared source: {support!r}")

    return {
        "item_count": len(rows),
        "truth_state_counts": dict(state_counts),
        "retrieval_stress_count": stress_count,
        "unique_group_count": len(set(group_ids)),
    }


def prepare(out: Path) -> dict[str, Any]:
    snapshot, corpus = validate_source()
    rows = load_jsonl(DEV_ITEMS)
    item_summary = validate_items(rows, corpus)
    if out.exists():
        raise ProxyPrepareError(f"output already exists: {out}")

    serving_questions = [
        {
            "item_id": row["item_id"],
            "group_id": row["group_id"],
            "question": row["question"],
            "answer_contract_id": "answer-object-v4",
        }
        for row in rows
    ]
    scorer_gold = [
        {
            "item_id": row["item_id"],
            "group_id": row["group_id"],
            "truth_state": row["truth_state"],
            "answer": row["answer"],
            "answer_type": row["answer_type"],
            "source_paths": row["source_paths"],
            "support_substrings": row["support_substrings"],
            "retrieval_stress": row["retrieval_stress"],
        }
        for row in rows
    ]

    serving = out / "serving"
    gold = out / "gold"
    serving.mkdir(parents=True)
    gold.mkdir(parents=True)
    (serving / "corpus-index.json").write_bytes((SOURCE_ROOT / "corpus-index.json").read_bytes())
    write_jsonl(serving / "questions.jsonl", serving_questions)
    write_jsonl(gold / "answers.jsonl", scorer_gold)

    manifest = {
        "format": "exactscope.public-proxy-candidate",
        "format_version": "0.1",
        "proxy_id": "kubernetes-pod-ops-docqa-v0.1",
        "split": "development32",
        "development_only": True,
        "qualification_eligible": False,
        "gold_visible_to_runner": False,
        "source_commit": snapshot["commit"],
        "source_snapshot_sha256": sha256_file(SOURCE_ROOT / "source-snapshot.json"),
        "source_manifest_sha256": sha256_file(SOURCE_MANIFEST),
        "adjudicated_items_sha256": sha256_file(DEV_ITEMS),
        "corpus_index_sha256": sha256_file(serving / "corpus-index.json"),
        "questions_sha256": sha256_file(serving / "questions.jsonl"),
        "gold_sha256": sha256_file(gold / "answers.jsonl"),
        "item_count": 32,
        "truth_state_counts": item_summary["truth_state_counts"],
        "retrieval_stress_count": item_summary["retrieval_stress_count"],
        "group_disjoint_within_split": True,
        "answer_contract_id": "answer-object-v4",
    }
    write_json(out / "manifest.json", manifest)
    return {
        "status": "DEV32_PREPARED",
        "manifest_sha256": sha256_file(out / "manifest.json"),
        **item_summary,
        "output": str(out),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    out = args.output if args.output.is_absolute() else ROOT / args.output
    result = prepare(out.resolve())
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
