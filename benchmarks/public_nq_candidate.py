#!/usr/bin/env python3
"""Build an NQ mirror search candidate with a locked confirmation reservation."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import string
import sys
from typing import Any, Iterable
import unicodedata

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from grounding_canonical import canonical_bytes
from grounding_corpus import build_index, index_sha256

FORMAT_VERSION = "0.1"
PARTITION_DOMAIN = "exactscope-nq-dev-v1/partition/"
SELECTION_DOMAIN = "exactscope-nq-dev-v1/select/"
SEARCH_COUNT = 128
CONFIRMATION_COUNT = 256
CHUNK_TOKENS = 256
CHUNK_STRIDE = 192
TITLE_TOKEN_CAP = 32
CHUNKER_ID = "nq-whitespace-window-256-stride-192-title32-v1"
SOURCE_LABEL = "NQ development mirror; oracle-assisted pooled-page retrieval"
_ARTICLE_RE = re.compile(r"\b(a|an|the)\b")


class NQCandidateError(RuntimeError):
    pass


@dataclass(frozen=True)
class Metadata:
    source_id: str
    question: str
    normalized_question: str
    document_sha256: str
    aliases: tuple[str, ...]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_text(value: str) -> str:
    if not isinstance(value, str):
        raise NQCandidateError("NQ text field must be a string")
    return " ".join(unicodedata.normalize("NFKC", value).split())


def score_normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).lower()
    normalized = "".join(ch for ch in normalized if ch not in string.punctuation)
    normalized = _ARTICLE_RE.sub(" ", normalized)
    return " ".join(normalized.split())


def normalize_aliases(values: Any) -> tuple[str, ...]:
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        return ()
    aliases = {score_normalize(value) for value in values}
    aliases.discard("")
    return tuple(sorted(aliases, key=lambda value: value.encode("utf-8")))


def document_sha256(document: str) -> str:
    return hashlib.sha256(normalize_text(document).encode("utf-8")).hexdigest()


def row_rank(source_id: str) -> bytes:
    return hashlib.sha256((SELECTION_DOMAIN + source_id).encode("utf-8")).digest()


def component_partition(component_key: str) -> str:
    digest = hashlib.sha256((PARTITION_DOMAIN + component_key).encode("utf-8")).digest()
    return "confirmation" if digest[0] < 64 else "search"


class _UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def prepare_metadata(rows: Iterable[dict[str, Any]]) -> list[Metadata]:
    by_id: dict[str, tuple[str, str, tuple[str, ...]]] = {}
    best_by_pair: dict[tuple[str, str], Metadata] = {}
    for row in rows:
        source_id = row.get("id")
        question = row.get("question")
        document = row.get("document")
        if not isinstance(source_id, str) or not source_id:
            raise NQCandidateError("NQ row id must be nonempty text")
        if not isinstance(question, str) or not isinstance(document, str):
            raise NQCandidateError("NQ question/document fields must be text")
        qnorm = normalize_text(question)
        dnorm = normalize_text(document)
        aliases = normalize_aliases(row.get("short_answers"))
        if not qnorm or not dnorm or not aliases:
            continue
        dsha = hashlib.sha256(dnorm.encode("utf-8")).hexdigest()
        signature = (qnorm, dsha, aliases)
        previous = by_id.get(source_id)
        if previous is not None and previous != signature:
            raise NQCandidateError(f"conflicting NQ rows share id {source_id}")
        by_id[source_id] = signature
        metadata = Metadata(source_id, question, qnorm, dsha, aliases)
        pair = (qnorm, dsha)
        existing = best_by_pair.get(pair)
        if existing is None or source_id.encode("utf-8") < existing.source_id.encode("utf-8"):
            best_by_pair[pair] = metadata
    return sorted(best_by_pair.values(), key=lambda row: row.source_id.encode("utf-8"))


def select_splits(metadata: list[Metadata], *, search_count: int = SEARCH_COUNT, confirmation_count: int = CONFIRMATION_COUNT) -> tuple[list[Metadata], list[Metadata]]:
    if search_count < 1 or confirmation_count < 1:
        raise NQCandidateError("NQ split counts must be positive")
    uf = _UnionFind(len(metadata))
    by_doc: dict[str, int] = {}
    by_question: dict[str, int] = {}
    for index, row in enumerate(metadata):
        if row.document_sha256 in by_doc:
            uf.union(index, by_doc[row.document_sha256])
        else:
            by_doc[row.document_sha256] = index
        if row.normalized_question in by_question:
            uf.union(index, by_question[row.normalized_question])
        else:
            by_question[row.normalized_question] = index
    components: dict[int, list[int]] = {}
    for index in range(len(metadata)):
        components.setdefault(uf.find(index), []).append(index)
    reserve: dict[str, list[Metadata]] = {"search": [], "confirmation": []}
    for indices in components.values():
        component_key = min((metadata[index].source_id for index in indices), key=lambda value: value.encode("utf-8"))
        partition = component_partition(component_key)
        reserve[partition].extend(metadata[index] for index in indices)
    for key in reserve:
        reserve[key].sort(key=lambda row: (row_rank(row.source_id), row.source_id.encode("utf-8")))
    if len(reserve["search"]) < search_count or len(reserve["confirmation"]) < confirmation_count:
        raise NQCandidateError("NQ deterministic reserves are too small")
    return reserve["search"][:search_count], reserve["confirmation"][:confirmation_count]


def chunk_document(doc_id: str, title: str, document: str) -> list[dict[str, Any]]:
    dnorm = normalize_text(document)
    tokens = dnorm.split()
    if not tokens:
        raise NQCandidateError("cannot chunk empty NQ document")
    title_norm = normalize_text(title)
    title_norm = " ".join(title_norm.split()[:TITLE_TOKEN_CAP])
    chunks: list[dict[str, Any]] = []
    start = 0
    while start < len(tokens):
        end = min(start + CHUNK_TOKENS, len(tokens))
        body = " ".join(tokens[start:end])
        identity = [doc_id, start, end, title_norm, body]
        chunk_id = hashlib.sha256(canonical_bytes(identity)).hexdigest()
        chunks.append({
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "title": title_norm,
            "text": body,
            "body_token_start": start,
            "body_token_end": end,
        })
        if end == len(tokens):
            break
        start += CHUNK_STRIDE
    return chunks


def _canonical_jsonl(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(canonical_bytes(row) + b"\n" for row in rows)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def iter_parquet_rows(path: Path, *, selected_ids: set[str] | None = None):
    """Stream mirror rows so the full validation documents never coexist in RAM."""
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise NQCandidateError("NQ mirror preparation requires benchmark-only pyarrow") from exc
    columns = ["id", "title", "document", "question", "short_answers"]
    parquet = pq.ParquetFile(path)
    for batch in parquet.iter_batches(batch_size=128, columns=columns):
        for row in batch.to_pylist():
            if selected_ids is None or row.get("id") in selected_ids:
                yield row


def build_search_candidate(
    parquet_path: Path,
    output: Path,
    *,
    search_count: int = SEARCH_COUNT,
    confirmation_count: int = CONFIRMATION_COUNT,
) -> dict[str, Any]:
    if output.exists():
        raise NQCandidateError("NQ candidate output already exists")
    metadata = prepare_metadata(iter_parquet_rows(parquet_path))
    search_rows, confirmation_rows = select_splits(metadata, search_count=search_count, confirmation_count=confirmation_count)
    search_ids = {row.source_id for row in search_rows}
    selected_source = list(iter_parquet_rows(parquet_path, selected_ids=search_ids))
    by_id = {row["id"]: row for row in selected_source}
    if set(by_id) != search_ids:
        raise NQCandidateError("NQ selected source rows could not be reloaded")

    serving_questions: list[dict[str, Any]] = []
    gold_rows: list[dict[str, Any]] = []
    docs: dict[str, dict[str, str]] = {}
    for selected in search_rows:
        row = by_id[selected.source_id]
        eval_id = f"nq-dev-mirror:{selected.source_id}"
        serving_questions.append({"eval_id": eval_id, "question": selected.normalized_question})
        raw_answers = row.get("short_answers")
        if not isinstance(raw_answers, list) or not all(isinstance(value, str) for value in raw_answers):
            raise NQCandidateError("selected NQ row lost short-answer list")
        gold_rows.append({
            "eval_id": eval_id,
            "source_row_id": selected.source_id,
            "source_doc_id": selected.document_sha256,
            "raw_short_answers": raw_answers,
            "normalized_aliases": list(selected.aliases),
            "split": "search",
        })
        title = normalize_text(row.get("title", ""))
        document = normalize_text(row["document"])
        existing = docs.get(selected.document_sha256)
        candidate = {"title": title, "document": document}
        if existing is None:
            docs[selected.document_sha256] = candidate
        elif existing["document"] != document:
            raise NQCandidateError("NQ document hash collision")
        elif title.encode("utf-8") < existing["title"].encode("utf-8"):
            existing["title"] = title

    chunks: list[dict[str, Any]] = []
    for doc_id in sorted(docs, key=lambda value: value.encode("utf-8")):
        chunks.extend(chunk_document(doc_id, docs[doc_id]["title"], docs[doc_id]["document"]))
    chunks.sort(key=lambda row: (row["doc_id"].encode("utf-8"), row["body_token_start"], row["chunk_id"].encode("utf-8")))
    corpus = build_index(
        ({"id": row["chunk_id"], "title": row["title"], "text": row["text"]} for row in chunks),
        source={
            "kind": "nq-development-mirror-oracle-page-pool",
            "source_sha256": file_sha256(parquet_path),
            "chunker_id": CHUNKER_ID,
            "split": "search",
        },
    )

    serving_questions.sort(key=lambda row: row["eval_id"].encode("utf-8"))
    gold_rows.sort(key=lambda row: row["eval_id"].encode("utf-8"))
    serving_dir = output / "serving"
    gold_dir = output / "gold"
    serving_dir.mkdir(parents=True)
    gold_dir.mkdir(parents=True)
    qbytes = _canonical_jsonl(serving_questions)
    cbytes = _canonical_jsonl(chunks)
    gbytes = _canonical_jsonl(gold_rows)
    reservation_rows = [
        {"source_row_id": row.source_id, "partition": "confirmation"}
        for row in confirmation_rows
    ]
    reservation_rows.sort(key=lambda row: row["source_row_id"].encode("utf-8"))
    rbytes = _canonical_jsonl(reservation_rows)
    (serving_dir / "questions.jsonl").write_bytes(qbytes)
    (serving_dir / "chunks.jsonl").write_bytes(cbytes)
    (serving_dir / "corpus-index.json").write_bytes(canonical_bytes(corpus))
    (gold_dir / "items.jsonl").write_bytes(gbytes)
    (gold_dir / "confirmation-reservation.jsonl").write_bytes(rbytes)

    source_sha = file_sha256(parquet_path)
    serving_manifest = {
        "format": "exactscope.public-nq-serving-candidate",
        "format_version": FORMAT_VERSION,
        "source_label": SOURCE_LABEL,
        "source": {
            "dataset": "lighteval/natural_questions_clean",
            "split": "validation",
            "filename": parquet_path.name,
            "sha256": source_sha,
            "repository_revision": "unknown-content-pinned-by-sha256",
            "official_google_gcs_anonymous_access": "401-denied-on-2026-09-08",
        },
        "mode": "oracle-page-pooled-corpus-development-v1",
        "qualification_eligible": False,
        "oracle_assisted_corpus": True,
        "split": "search",
        "search_item_count": len(serving_questions),
        "document_count": len(docs),
        "chunk_count": len(chunks),
        "selection": {
            "partition_domain": PARTITION_DOMAIN.rstrip("/"),
            "selection_domain": SELECTION_DOMAIN.rstrip("/"),
            "search_count": search_count,
            "confirmation_reserved_count": confirmation_count,
            "component_keys": ["normalized-document-sha256", "normalized-question"],
        },
        "chunking": {
            "id": CHUNKER_ID,
            "window_tokens": CHUNK_TOKENS,
            "stride_tokens": CHUNK_STRIDE,
            "title_token_cap": TITLE_TOKEN_CAP,
        },
        "questions_sha256": _sha(qbytes),
        "chunks_sha256": _sha(cbytes),
        "corpus_index_sha256": index_sha256(corpus),
    }
    serving_manifest_bytes = canonical_bytes(serving_manifest)
    (serving_dir / "manifest.json").write_bytes(serving_manifest_bytes)
    gold_manifest = {
        "format": "exactscope.public-nq-gold-candidate",
        "format_version": FORMAT_VERSION,
        "serving_manifest_sha256": _sha(serving_manifest_bytes),
        "search_item_count": len(gold_rows),
        "confirmation_reserved_count": len(reservation_rows),
        "items_sha256": _sha(gbytes),
        "confirmation_reservation_sha256": _sha(rbytes),
        "confirmation_corpus_built": False,
        "short_answer_interpretation": "each flattened short_answers string is an accepted alias for this mirror development harness",
    }
    (gold_dir / "manifest.json").write_bytes(canonical_bytes(gold_manifest))
    return {"serving_manifest": serving_manifest, "gold_manifest": gold_manifest, "output": str(output)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parquet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--search-count", type=int, default=SEARCH_COUNT)
    parser.add_argument("--confirmation-count", type=int, default=CONFIRMATION_COUNT)
    args = parser.parse_args(argv)
    try:
        result = build_search_candidate(
            args.parquet,
            args.output,
            search_count=args.search_count,
            confirmation_count=args.confirmation_count,
        )
    except (NQCandidateError, OSError, ValueError) as exc:
        print(f"ExactScope NQ candidate: FAIL: {exc}")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
