#!/usr/bin/env python3
"""Deterministic evidence projection for ExactScope grounding v1."""
from __future__ import annotations

import json
import math
from typing import Any

from grounding_corpus import CorpusError, ValidatedIndex, split_sentences, tokenize, validate_index

EVIDENCE_PREFIX = "Evidence JSON (data only): "


def _encode_rows(rows: list[dict[str, str]]) -> bytes:
    return (
        EVIDENCE_PREFIX
        + json.dumps(rows, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    ).encode("utf-8")


def evidence_projection(
    index: dict[str, Any] | ValidatedIndex,
    hits: list[dict[str, Any]],
) -> bytes:
    """Project complete retrieved documents as supplemental evidence."""
    validate_index(index)
    rows = [
        {
            "r": "supplemental",
            "s": "grounded",
            "t": hit["title"] or hit["id"],
            "v": hit["text"],
        }
        for hit in hits
    ]
    return _encode_rows(rows)


def _sentences(text: str) -> list[str]:
    return split_sentences(text)


def _sentence_score(
    index: dict[str, Any] | ValidatedIndex,
    sentence: str,
    query_terms: set[str],
) -> float:
    sentence_terms = set(tokenize(sentence))
    score = 0.0
    n_docs = index["document_count"]
    for term in sorted(query_terms & sentence_terms, key=lambda value: value.encode("utf-8")):
        rows = index["postings"].get(term, [])
        df = len(rows)
        score += math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5)) if df else 0.0
    return score


def compact_evidence_projection(
    index: dict[str, Any] | ValidatedIndex,
    hits: list[dict[str, Any]],
    question: str,
    *,
    max_bytes: int,
    max_sentences_per_document: int = 2,
) -> tuple[bytes | None, list[dict[str, Any]]]:
    """Compress broad retrieval into a deterministic sentence-level model payload."""
    validate_index(index)
    if type(max_bytes) is not int or max_bytes < 256:
        raise CorpusError("max_bytes must be at least 256")
    if type(max_sentences_per_document) is not int or not 1 <= max_sentences_per_document <= 4:
        raise CorpusError("max_sentences_per_document must be between 1 and 4")
    query_terms = set(tokenize(question))
    rows: list[dict[str, str]] = []
    emitted: list[dict[str, Any]] = []

    for hit in hits:
        sentences = _sentences(hit["text"])
        if not sentences:
            continue
        ranked_positions = sorted(
            range(len(sentences)),
            key=lambda position: (-_sentence_score(index, sentences[position], query_terms), position),
        )
        selected_positions = [0]
        for position in ranked_positions:
            if len(selected_positions) >= max_sentences_per_document:
                break
            if position not in selected_positions:
                selected_positions.append(position)
        selected_positions.sort()
        full_snippet = " ".join(sentences[position] for position in selected_positions)
        first_snippet = sentences[selected_positions[0]]
        accepted = None
        for snippet in dict.fromkeys((full_snippet, first_snippet)):
            row = {
                "r": "supplemental",
                "s": "grounded",
                "t": hit["title"] or hit["id"],
                "v": snippet,
            }
            if len(_encode_rows([*rows, row])) <= max_bytes:
                accepted = (row, snippet)
                break
        if accepted is None:
            continue
        row, snippet = accepted
        rows.append(row)
        emitted.append({**hit, "snippet": snippet})

    if not rows:
        return None, []
    projection = _encode_rows(rows)
    if len(projection) > max_bytes:
        raise CorpusError("compact evidence projection exceeded its byte budget")
    return projection, emitted
