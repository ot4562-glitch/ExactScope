#!/usr/bin/env python3
"""Build a gold-isolated FEVER pooled-corpus development candidate."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from grounding_canonical import canonical_bytes, loads
from grounding_corpus import build_index, index_sha256

SELECTION_DOMAIN = "exactscope-fever-dev-v1\0"
LABELS = ("SUPPORTS", "REFUTES", "NOT ENOUGH INFO")
DEFAULT_PER_LABEL = 50
WIKI_MEMBER_PREFIX = "wiki-pages/wiki-"
WIKI_MEMBER_SUFFIX = ".jsonl"
PARSER_ID = "fever-wiki-lines-v1"
FORMAT_VERSION = "0.1"


class FeverCandidateError(RuntimeError):
    pass


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bytes_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_jsonl(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(canonical_bytes(row) + b"\n" for row in rows)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("rb") as handle:
        for line_number, line in enumerate(handle, 1):
            line = line.rstrip(b"\r\n")
            if not line:
                continue
            try:
                value = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise FeverCandidateError(f"invalid source JSONL at line {line_number}") from exc
            if not isinstance(value, dict):
                raise FeverCandidateError(f"source JSONL row {line_number} is not an object")
            rows.append(value)
    return rows


def selection_key(source_id: int) -> tuple[bytes, int]:
    if type(source_id) is not int or source_id < 0:
        raise FeverCandidateError("FEVER source id must be a nonnegative integer")
    digest = hashlib.sha256((SELECTION_DOMAIN + str(source_id)).encode("utf-8")).digest()
    return digest, source_id


def select_balanced(rows: list[dict[str, Any]], *, per_label: int = DEFAULT_PER_LABEL) -> list[dict[str, Any]]:
    if type(per_label) is not int or per_label < 1:
        raise FeverCandidateError("per_label must be positive")
    seen: set[int] = set()
    by_label: dict[str, list[dict[str, Any]]] = {label: [] for label in LABELS}
    for row in rows:
        source_id = row.get("id")
        if type(source_id) is not int or source_id < 0 or source_id in seen:
            raise FeverCandidateError("FEVER source ids must be unique nonnegative integers")
        seen.add(source_id)
        label = row.get("label")
        if label not in by_label:
            raise FeverCandidateError(f"unsupported FEVER label: {label!r}")
        claim = row.get("claim")
        if not isinstance(claim, str) or not claim.strip():
            raise FeverCandidateError("FEVER claim must be nonempty text")
        by_label[label].append(row)
    selected: list[dict[str, Any]] = []
    for label in LABELS:
        group = sorted(by_label[label], key=lambda row: selection_key(row["id"]))
        if len(group) < per_label:
            raise FeverCandidateError(f"not enough FEVER rows for label {label}")
        selected.extend(group[:per_label])
    return sorted(selected, key=lambda row: selection_key(row["id"]))


def normalize_evidence_sets(row: dict[str, Any]) -> list[list[dict[str, Any]]]:
    label = row["label"]
    raw_groups = row.get("evidence")
    if not isinstance(raw_groups, list):
        raise FeverCandidateError("FEVER evidence must be a list")
    if label == "NOT ENOUGH INFO":
        return []
    normalized_groups: set[tuple[tuple[str, int], ...]] = set()
    for raw_group in raw_groups:
        if not isinstance(raw_group, list) or not raw_group:
            raise FeverCandidateError("verifiable FEVER evidence group must be nonempty")
        pairs: set[tuple[str, int]] = set()
        for entry in raw_group:
            if not isinstance(entry, list) or len(entry) != 4:
                raise FeverCandidateError("malformed FEVER evidence tuple")
            page = entry[2]
            sentence_id = entry[3]
            if not isinstance(page, str) or not page or type(sentence_id) is not int or sentence_id < 0:
                raise FeverCandidateError("verifiable FEVER evidence lacks page/sentence id")
            pairs.add((page, sentence_id))
        normalized_groups.add(tuple(sorted(pairs, key=lambda pair: (pair[0].encode("utf-8"), pair[1]))))
    if not normalized_groups:
        raise FeverCandidateError("verifiable FEVER row has no usable evidence group")
    ordered = sorted(normalized_groups, key=lambda group: tuple((page.encode("utf-8"), sentence_id) for page, sentence_id in group))
    return [[{"page": page, "sentence_id": sentence_id} for page, sentence_id in group] for group in ordered]


def parse_wiki_lines(page: str, value: str) -> list[dict[str, Any]]:
    if not isinstance(value, str):
        raise FeverCandidateError(f"FEVER page {page} has non-text lines field")
    seen: set[int] = set()
    rows: list[dict[str, Any]] = []
    for raw in value.splitlines():
        if not raw:
            continue
        parts = raw.split("\t")
        if len(parts) < 2:
            raise FeverCandidateError(f"FEVER page {page} has malformed sentence row")
        try:
            sentence_id = int(parts[0])
        except ValueError as exc:
            raise FeverCandidateError(f"FEVER page {page} has non-integer sentence id") from exc
        if sentence_id < 0 or sentence_id in seen:
            raise FeverCandidateError(f"FEVER page {page} has duplicate/negative sentence id")
        seen.add(sentence_id)
        text = parts[1].strip()
        if not text:
            continue
        candidate_identity = [page, sentence_id, text]
        candidate_id = hashlib.sha256(canonical_bytes(candidate_identity)).hexdigest()
        rows.append({"candidate_id": candidate_id, "page": page, "sentence_id": sentence_id, "text": text})
    return rows


def scan_required_pages(zip_path: Path, required_pages: set[str]) -> dict[str, list[dict[str, Any]]]:
    if not required_pages:
        raise FeverCandidateError("no FEVER evidence pages requested")
    found: dict[str, list[dict[str, Any]]] = {}
    duplicate_pages: set[str] = set()
    with zipfile.ZipFile(zip_path) as archive:
        members = sorted(
            name for name in archive.namelist()
            if name.startswith(WIKI_MEMBER_PREFIX) and name.endswith(WIKI_MEMBER_SUFFIX)
        )
        if not members:
            raise FeverCandidateError("FEVER wiki ZIP has no expected JSONL members")
        for member in members:
            with archive.open(member) as handle:
                for line_number, raw in enumerate(handle, 1):
                    if not raw.strip():
                        continue
                    try:
                        row = json.loads(raw.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise FeverCandidateError(f"invalid FEVER wiki JSON in {member}:{line_number}") from exc
                    if not isinstance(row, dict):
                        raise FeverCandidateError(f"invalid FEVER wiki row in {member}:{line_number}")
                    page = row.get("id")
                    if page not in required_pages:
                        continue
                    if page in found:
                        duplicate_pages.add(page)
                        continue
                    found[page] = parse_wiki_lines(page, row.get("lines"))
    if duplicate_pages:
        raise FeverCandidateError(f"duplicate FEVER page records: {sorted(duplicate_pages)[:3]}")
    missing = sorted(required_pages - found.keys(), key=lambda value: value.encode("utf-8"))
    if missing:
        raise FeverCandidateError(f"missing FEVER wiki pages: {missing[:3]}")
    return found


def build_candidate(
    paper_dev: Path,
    wiki_zip: Path,
    output: Path,
    *,
    per_label: int = DEFAULT_PER_LABEL,
) -> dict[str, Any]:
    if output.exists():
        raise FeverCandidateError("candidate output already exists")
    source_rows = read_jsonl(paper_dev)
    selected = select_balanced(source_rows, per_label=per_label)

    serving_rows: list[dict[str, Any]] = []
    gold_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    required_pages: set[str] = set()
    required_pairs: set[tuple[str, int]] = set()
    for row in selected:
        item_id = f"fever-dev:{row['id']}"
        serving_rows.append({"id": item_id, "claim": row["claim"]})
        evidence_sets = normalize_evidence_sets(row)
        gold_rows.append({"id": item_id, "label": row["label"], "evidence_sets": evidence_sets})
        audit_rows.append(row)
        for group in evidence_sets:
            for evidence in group:
                required_pages.add(evidence["page"])
                required_pairs.add((evidence["page"], evidence["sentence_id"]))

    page_rows = scan_required_pages(wiki_zip, required_pages)
    resolved_pairs = {(page, row["sentence_id"]) for page, rows in page_rows.items() for row in rows}
    missing_pairs = sorted(required_pairs - resolved_pairs, key=lambda pair: (pair[0].encode("utf-8"), pair[1]))
    if missing_pairs:
        raise FeverCandidateError(f"annotated FEVER evidence sentence did not resolve: {missing_pairs[:3]}")

    candidates = [row for page in sorted(page_rows, key=lambda value: value.encode("utf-8")) for row in page_rows[page]]
    candidates.sort(key=lambda row: (row["page"].encode("utf-8"), row["sentence_id"]))
    if not candidates:
        raise FeverCandidateError("FEVER pooled corpus is empty")
    documents = [
        {"id": row["candidate_id"], "title": row["page"], "text": row["text"]}
        for row in candidates
    ]
    corpus = build_index(
        documents,
        source={
            "kind": "fever-oracle-page-pool-development",
            "paper_dev_sha256": file_sha256(paper_dev),
            "wiki_zip_sha256": file_sha256(wiki_zip),
            "selection_domain": SELECTION_DOMAIN.rstrip("\0"),
            "per_label": per_label,
            "parser_id": PARSER_ID,
        },
    )

    serving_dir = output / "serving"
    gold_dir = output / "gold"
    serving_dir.mkdir(parents=True)
    gold_dir.mkdir(parents=True)
    serving_bytes = canonical_jsonl(serving_rows)
    candidates_bytes = canonical_jsonl(candidates)
    gold_bytes = canonical_jsonl(gold_rows)
    audit_bytes = canonical_jsonl(audit_rows)
    (serving_dir / "items.jsonl").write_bytes(serving_bytes)
    (serving_dir / "corpus-candidates.jsonl").write_bytes(candidates_bytes)
    (serving_dir / "corpus-index.json").write_bytes(canonical_bytes(corpus))
    (gold_dir / "items.jsonl").write_bytes(gold_bytes)
    (gold_dir / "source-records.jsonl").write_bytes(audit_bytes)

    paper_sha = file_sha256(paper_dev)
    wiki_sha = file_sha256(wiki_zip)
    serving_manifest = {
        "format": "exactscope.public-fever-serving-candidate",
        "format_version": FORMAT_VERSION,
        "mode": "oracle-page-pooled-corpus-development-v1",
        "qualification_eligible": False,
        "item_count": len(serving_rows),
        "label_balance_disclosed": True,
        "oracle_assisted_corpus": True,
        "source": {
            "paper_dev_sha256": paper_sha,
            "wiki_zip_sha256": wiki_sha,
            "parser_id": PARSER_ID,
        },
        "selection": {
            "domain": SELECTION_DOMAIN.rstrip("\0"),
            "per_label": per_label,
            "method": "sha256-domain-plus-decimal-source-id-v1",
        },
        "required_page_count": len(required_pages),
        "corpus_candidate_count": len(candidates),
        "items_sha256": bytes_sha256(serving_bytes),
        "corpus_candidates_sha256": bytes_sha256(candidates_bytes),
        "corpus_index_sha256": index_sha256(corpus),
    }
    serving_manifest_bytes = canonical_bytes(serving_manifest)
    (serving_dir / "manifest.json").write_bytes(serving_manifest_bytes)
    gold_manifest = {
        "format": "exactscope.public-fever-gold-candidate",
        "format_version": FORMAT_VERSION,
        "serving_manifest_sha256": bytes_sha256(serving_manifest_bytes),
        "item_count": len(gold_rows),
        "label_counts": dict(sorted(Counter(row["label"] for row in gold_rows).items())),
        "items_sha256": bytes_sha256(gold_bytes),
        "source_records_sha256": bytes_sha256(audit_bytes),
        "annotated_evidence_pair_count": len(required_pairs),
    }
    (gold_dir / "manifest.json").write_bytes(canonical_bytes(gold_manifest))
    return {
        "serving_manifest": serving_manifest,
        "gold_manifest": gold_manifest,
        "output": str(output),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper-dev", type=Path, required=True)
    parser.add_argument("--wiki-zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--per-label", type=int, default=DEFAULT_PER_LABEL)
    args = parser.parse_args(argv)
    try:
        result = build_candidate(args.paper_dev, args.wiki_zip, args.output, per_label=args.per_label)
    except (FeverCandidateError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"ExactScope FEVER candidate: FAIL: {exc}")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
