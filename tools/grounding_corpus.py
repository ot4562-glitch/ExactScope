#!/usr/bin/env python3
"""Tiny deterministic local text-corpus index for ExactScope grounding v1."""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import struct
from types import MappingProxyType
from typing import Any, Iterable
import unicodedata
import zlib

from grounding_canonical import canonical_bytes, loads

FORMAT = "exactscope.local-text-corpus"
FORMAT_VERSION = "0.1"
TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
MAX_DOCUMENT_BYTES = 32 * 1024
DEFAULT_TOP_K = 4
MAX_TOP_K = 16
BM25_K1 = 1.2
BM25_B = 0.75

BINARY_MAGIC = b"XSGI"
BINARY_FORMAT_MAJOR = 1
BINARY_FORMAT_MINOR = 1
BINARY_HEADER_SIZE = 64
BINARY_DOCUMENT_RECORD_SIZE = 32
BINARY_TERM_RECORD_SIZE = 24
BINARY_POSTING_RECORD_SIZE = 12
BINARY_SENTENCE_RECORD_SIZE = 24
BINARY_TERM_REF_RECORD_SIZE = 4


class CorpusError(RuntimeError):
    pass


_VALIDATED_INDEX_TOKEN = object()


def _freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


class ValidatedIndex:
    """Immutable, already-validated in-memory view of one corpus index."""

    __slots__ = ("_data",)

    def __init__(self, token: object, index: dict[str, Any]) -> None:
        if token is not _VALIDATED_INDEX_TOKEN:
            raise TypeError("ValidatedIndex must be created by grounding_corpus")
        self._data = _freeze_json(index)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    @property
    def document_count(self) -> int:
        return self._data["document_count"]

    def postings_for(self, term: str) -> tuple[tuple[int, int], ...]:
        return self._data["postings"].get(term, ())

    def to_canonical_dict(self) -> dict[str, Any]:
        value = _thaw_json(self._data)
        if not isinstance(value, dict):
            raise CorpusError("invalid compiled corpus state")
        return value


def _validated_view(index: dict[str, Any]) -> ValidatedIndex:
    return ValidatedIndex(_VALIDATED_INDEX_TOKEN, index)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tokenize(text: str) -> list[str]:
    if not isinstance(text, str):
        raise CorpusError("corpus text must be a string")
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return TOKEN_RE.findall(normalized)


def sentence_spans(text: str) -> list[tuple[str, int, int]]:
    """Return baseline sentence text plus UTF-8 byte offset/length within source text."""
    if not isinstance(text, str):
        raise CorpusError("corpus text must be a string")
    pieces: list[tuple[int, int]] = []
    start = 0
    for match in SENTENCE_SPLIT_RE.finditer(text):
        pieces.append((start, match.start()))
        start = match.end()
    pieces.append((start, len(text)))
    spans: list[tuple[str, int, int]] = []
    for raw_start, raw_end in pieces:
        raw = text[raw_start:raw_end]
        if not raw.strip():
            continue
        left = len(raw) - len(raw.lstrip())
        right = len(raw.rstrip())
        clean_start = raw_start + left
        clean_end = raw_start + right
        sentence = text[clean_start:clean_end]
        byte_start = len(text[:clean_start].encode("utf-8"))
        byte_length = len(sentence.encode("utf-8"))
        spans.append((sentence, byte_start, byte_length))
    return spans


def split_sentences(text: str) -> list[str]:
    return [sentence for sentence, _, _ in sentence_spans(text)]


def _validate_document(document: dict[str, Any], *, indexed: bool = False) -> tuple[str, str, str]:
    allowed = {"id", "title", "text", "text_sha256", "token_count"} if indexed else {"id", "title", "text"}
    if not isinstance(document, dict) or set(document) - allowed:
        raise CorpusError("document has unexpected fields")
    doc_id = document.get("id")
    title = document.get("title", "")
    text = document.get("text")
    if not isinstance(doc_id, str) or not doc_id.strip():
        raise CorpusError("document id must be nonempty text")
    if not isinstance(title, str) or not isinstance(text, str) or not text.strip():
        raise CorpusError("document title/text must be text and text must be nonempty")
    if len(text.encode("utf-8")) > MAX_DOCUMENT_BYTES:
        raise CorpusError("document exceeds local corpus byte limit")
    return doc_id, title, text


def build_index(
    documents: Iterable[dict[str, Any]],
    *,
    source: dict[str, Any] | None = None,
    compiled: bool = False,
) -> dict[str, Any] | ValidatedIndex:
    validated: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for document in documents:
        doc_id, title, text = _validate_document(document)
        if doc_id in seen:
            raise CorpusError("duplicate document id")
        seen.add(doc_id)
        validated.append((doc_id, title, text))
    validated.sort(key=lambda row: row[0].encode("utf-8"))
    if not validated:
        raise CorpusError("corpus must contain at least one document")

    docs: list[dict[str, Any]] = []
    postings: dict[str, list[list[int]]] = defaultdict(list)
    total_tokens = 0
    for ordinal, (doc_id, title, text) in enumerate(validated):
        counts = Counter(tokenize(title + "\n" + text))
        token_count = sum(counts.values())
        total_tokens += token_count
        docs.append({
            "id": doc_id,
            "title": title,
            "text": text,
            "text_sha256": sha256_bytes(text.encode("utf-8")),
            "token_count": token_count,
        })
        for token, frequency in sorted(counts.items(), key=lambda row: row[0].encode("utf-8")):
            postings[token].append([ordinal, frequency])

    index = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "document_count": len(docs),
        "total_tokens": total_tokens,
        "ranking": {"id": "bm25-v1", "k1_milli": 1200, "b_milli": 750},
        "source": source or {"kind": "local-user-documents"},
        "documents": docs,
        "postings": dict(sorted(postings.items(), key=lambda row: row[0].encode("utf-8"))),
    }
    validate_index(index)
    return _validated_view(index) if compiled else index


def validate_index(index: dict[str, Any] | ValidatedIndex) -> None:
    if isinstance(index, ValidatedIndex):
        return
    if not isinstance(index, dict) or index.get("format") != FORMAT or index.get("format_version") != FORMAT_VERSION:
        raise CorpusError("invalid local corpus identity")
    docs = index.get("documents")
    postings = index.get("postings")
    if not isinstance(docs, list) or not docs or index.get("document_count") != len(docs) or not isinstance(postings, dict):
        raise CorpusError("invalid local corpus shape")
    ids: set[str] = set()
    computed_total = 0
    for ordinal, doc in enumerate(docs):
        if not isinstance(doc, dict) or set(doc) != {"id", "title", "text", "text_sha256", "token_count"}:
            raise CorpusError("invalid corpus document")
        doc_id, title, text = _validate_document(doc, indexed=True)
        if doc_id in ids or doc_id != docs[ordinal]["id"]:
            raise CorpusError("duplicate corpus document id")
        ids.add(doc_id)
        if doc["text_sha256"] != sha256_bytes(text.encode("utf-8")):
            raise CorpusError("corpus document hash mismatch")
        expected_count = len(tokenize(title + "\n" + text))
        if doc["token_count"] != expected_count:
            raise CorpusError("corpus token count mismatch")
        computed_total += expected_count
    if index.get("total_tokens") != computed_total:
        raise CorpusError("corpus total token count mismatch")
    if index.get("ranking") != {"id": "bm25-v1", "k1_milli": 1200, "b_milli": 750}:
        raise CorpusError("corpus ranking policy drift")
    for token, rows in postings.items():
        if not isinstance(token, str) or not token or not isinstance(rows, list):
            raise CorpusError("invalid corpus posting")
        previous = -1
        for row in rows:
            if not isinstance(row, list) or len(row) != 2 or type(row[0]) is not int or type(row[1]) is not int:
                raise CorpusError("invalid corpus posting row")
            ordinal, frequency = row
            if ordinal <= previous or ordinal < 0 or ordinal >= len(docs) or frequency <= 0:
                raise CorpusError("invalid corpus posting ordering")
            previous = ordinal


def compile_index(index: Mapping[str, Any]) -> ValidatedIndex:
    if not isinstance(index, dict):
        raise CorpusError("compiled corpus source must be a mutable canonical index dictionary")
    validate_index(index)
    # Freeze into owned storage so later caller mutations cannot change search results.
    return _validated_view(index)


def index_sha256(index: dict[str, Any] | ValidatedIndex) -> str:
    if isinstance(index, ValidatedIndex):
        return sha256_bytes(canonical_bytes(index.to_canonical_dict()))
    validate_index(index)
    return sha256_bytes(canonical_bytes(index))


def binary_index_bytes(index: dict[str, Any] | ValidatedIndex) -> bytes:
    """Compile one validated canonical corpus into the immutable native search format."""
    validate_index(index)
    source = index.to_canonical_dict() if isinstance(index, ValidatedIndex) else index
    docs = source["documents"]
    postings = source["postings"]
    n_docs = len(docs)
    average = source["total_tokens"] / n_docs if n_docs else 1.0

    strings = bytearray()

    def add_string(value: str) -> tuple[int, int]:
        encoded = value.encode("utf-8")
        offset = len(strings)
        strings.extend(encoded)
        if offset > 0xFFFF_FFFF or len(encoded) > 0xFFFF_FFFF:
            raise CorpusError("binary corpus string table exceeds v1 limits")
        return offset, len(encoded)

    document_records = bytearray()
    document_text_offsets: list[int] = []
    for document in docs:
        id_offset, id_length = add_string(document["id"])
        title_offset, title_length = add_string(document["title"])
        text_offset, text_length = add_string(document["text"])
        document_text_offsets.append(text_offset)
        document_records.extend(struct.pack(
            "<IIIIIIII",
            id_offset,
            id_length,
            title_offset,
            title_length,
            text_offset,
            text_length,
            document["token_count"],
            0,
        ))

    term_records = bytearray()
    posting_records = bytearray()
    posting_count = 0
    term_ordinals = {term: ordinal for ordinal, term in enumerate(postings)}
    for term, rows in postings.items():
        term_offset, term_length = add_string(term)
        df = len(rows)
        idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
        first_posting = posting_count
        for ordinal, frequency in rows:
            length = docs[ordinal]["token_count"] or 1
            denominator = frequency + BM25_K1 * (1.0 - BM25_B + BM25_B * length / average)
            contribution = idf * (frequency * (BM25_K1 + 1.0)) / denominator
            posting_records.extend(struct.pack("<Id", ordinal, contribution))
            posting_count += 1
        term_records.extend(struct.pack(
            "<IIIId",
            term_offset,
            term_length,
            first_posting,
            df,
            idf,
        ))

    sentence_records = bytearray()
    sentence_term_refs = bytearray()
    sentence_count = 0
    term_ref_count = 0
    for document_ordinal, document in enumerate(docs):
        for position, (sentence, byte_start, byte_length) in enumerate(sentence_spans(document["text"])):
            term_refs = sorted({
                term_ordinals[token]
                for token in tokenize(sentence)
                if token in term_ordinals
            })
            first_term_ref = term_ref_count
            for term_ordinal in term_refs:
                sentence_term_refs.extend(struct.pack("<I", term_ordinal))
                term_ref_count += 1
            text_offset = document_text_offsets[document_ordinal] + byte_start
            if text_offset > 0xFFFF_FFFF or byte_length > 0xFFFF_FFFF:
                raise CorpusError("binary corpus sentence span exceeds v1 limits")
            sentence_records.extend(struct.pack(
                "<IIIIII",
                document_ordinal,
                position,
                text_offset,
                byte_length,
                first_term_ref,
                len(term_refs),
            ))
            sentence_count += 1

    if (
        len(docs) > 0xFFFF_FFFF
        or len(postings) > 0xFFFF_FFFF
        or posting_count > 0xFFFF_FFFF
        or sentence_count > 0xFFFF_FFFF
        or term_ref_count > 0xFFFF_FFFF
    ):
        raise CorpusError("binary corpus record count exceeds v1 limits")
    if source["total_tokens"] > 0xFFFF_FFFF_FFFF_FFFF:
        raise CorpusError("binary corpus total token count exceeds v1 limits")
    if len(strings) > 0xFFFF_FFFF:
        raise CorpusError("binary corpus string table exceeds v1 limits")

    documents_offset = BINARY_HEADER_SIZE
    terms_offset = documents_offset + len(document_records)
    postings_offset = terms_offset + len(term_records)
    sentences_offset = postings_offset + len(posting_records)
    term_refs_offset = sentences_offset + len(sentence_records)
    strings_offset = term_refs_offset + len(sentence_term_refs)
    if strings_offset > 0xFFFF_FFFF:
        raise CorpusError("binary corpus tables exceed v1 offset limits")

    payload = bytes(
        document_records
        + term_records
        + posting_records
        + sentence_records
        + sentence_term_refs
        + strings
    )
    crc = zlib.crc32(payload) & 0xFFFF_FFFF
    header = struct.pack(
        "<4sHHIIIIIQIIIIIII",
        BINARY_MAGIC,
        BINARY_FORMAT_MAJOR,
        BINARY_FORMAT_MINOR,
        BINARY_HEADER_SIZE,
        0,
        len(docs),
        len(postings),
        posting_count,
        source["total_tokens"],
        documents_offset,
        terms_offset,
        postings_offset,
        strings_offset,
        len(strings),
        crc,
        sentence_count,
    )
    if len(header) != BINARY_HEADER_SIZE:
        raise CorpusError("internal binary corpus header size mismatch")
    return header + payload


def binary_index_sha256(index: dict[str, Any] | ValidatedIndex) -> str:
    return sha256_bytes(binary_index_bytes(index))


def load_index(path: Path, *, compiled: bool = False) -> dict[str, Any] | ValidatedIndex:
    try:
        raw = path.read_bytes()
        value = loads(raw)
    except (OSError, ValueError, UnicodeError) as exc:
        raise CorpusError(f"cannot read local corpus index: {exc}") from exc
    if not isinstance(value, dict) or raw != canonical_bytes(value):
        raise CorpusError("local corpus index must be canonical JSON")
    validate_index(value)
    return _validated_view(value) if compiled else value


def search(index: dict[str, Any] | ValidatedIndex, question: str, *, top_k: int = DEFAULT_TOP_K) -> list[dict[str, Any]]:
    validate_index(index)
    if type(top_k) is not int or top_k < 1 or top_k > MAX_TOP_K:
        raise CorpusError(f"top_k must be between 1 and {MAX_TOP_K}")
    query_terms = list(dict.fromkeys(tokenize(question)))
    if not query_terms:
        return []
    docs = index["documents"]
    postings = index["postings"]
    n_docs = len(docs)
    average = index["total_tokens"] / n_docs if n_docs else 1.0
    scores: dict[int, float] = defaultdict(float)
    matched_terms: dict[int, int] = defaultdict(int)
    for term in query_terms:
        rows = postings.get(term)
        if not rows:
            continue
        df = len(rows)
        idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
        for ordinal, frequency in rows:
            length = docs[ordinal]["token_count"] or 1
            denominator = frequency + BM25_K1 * (1.0 - BM25_B + BM25_B * length / average)
            scores[ordinal] += idf * (frequency * (BM25_K1 + 1.0)) / denominator
            matched_terms[ordinal] += 1
    ranked = sorted(
        scores,
        key=lambda ordinal: (-scores[ordinal], -matched_terms[ordinal], docs[ordinal]["id"].encode("utf-8")),
    )[:top_k]
    return [
        {
            "id": docs[ordinal]["id"],
            "title": docs[ordinal]["title"],
            "text": docs[ordinal]["text"],
            "text_sha256": docs[ordinal]["text_sha256"],
            "score": scores[ordinal],
            "matched_query_terms": matched_terms[ordinal],
        }
        for ordinal in ranked
        if scores[ordinal] > 0.0
    ]


def _directory_documents(root: Path) -> list[dict[str, Any]]:
    if not root.is_dir():
        raise CorpusError("input directory does not exist")
    documents = []
    for path in sorted(root.rglob("*"), key=lambda p: p.as_posix().encode("utf-8")):
        if not path.is_file() or path.suffix.lower() not in {".txt", ".md"}:
            continue
        relative = path.relative_to(root).as_posix()
        documents.append({"id": relative, "title": path.stem, "text": path.read_text(encoding="utf-8")})
    return documents


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="build one deterministic corpus index from .txt/.md files")
    build.add_argument("--input-dir", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    compile_binary = sub.add_parser("compile-binary", help="compile canonical JSON corpus into the native immutable index")
    compile_binary.add_argument("--index", type=Path, required=True)
    compile_binary.add_argument("--output", type=Path, required=True)
    query = sub.add_parser("search", help="search an existing corpus index")
    query.add_argument("--index", type=Path, required=True)
    query.add_argument("--question", required=True)
    query.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            if args.output.exists():
                raise CorpusError("output exists")
            index = build_index(_directory_documents(args.input_dir), source={"kind": "local-user-documents", "root_name": args.input_dir.name})
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(canonical_bytes(index))
            print(json.dumps({"document_count": index["document_count"], "index_sha256": index_sha256(index), "output": str(args.output)}, sort_keys=True))
            return 0
        if args.command == "compile-binary":
            if args.output.exists():
                raise CorpusError("output exists")
            index = load_index(args.index)
            binary = binary_index_bytes(index)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(binary)
            print(json.dumps({
                "document_count": index["document_count"],
                "binary_bytes": len(binary),
                "binary_sha256": sha256_bytes(binary),
                "output": str(args.output),
            }, sort_keys=True))
            return 0
        index = load_index(args.index)
        print(json.dumps(search(index, args.question, top_k=args.top_k), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (CorpusError, OSError, UnicodeError, ValueError) as exc:
        print(f"ExactScope grounding corpus: FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
