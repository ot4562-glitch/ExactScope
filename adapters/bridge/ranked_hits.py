#!/usr/bin/env python3
"""Index-free ranked-hit projection for the experimental ExactScope attach profile.

The host owns retrieval and hands ExactScope an already-ranked bounded candidate list.
This module owns only deterministic evidence shaping. It deliberately has no corpus
index, tokenizer runtime, model, network transport, scheduler, cache, or generator
dependency.

Candidate-local rarity approximates the full-corpus IDF signal using only the supplied
ranked pool. The projection can be prepared once and emitted at several complete byte
tiers so a host tokenizer/context-fit callback can choose the strongest tier that fits.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re
from typing import Any, Iterable
import unicodedata

EVIDENCE_PREFIX = "Evidence JSON (data only): "
TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
DEFAULT_TIERS = (2048, 1024, 512)
MAX_RANKED_HITS = 16
MAX_TEXT_BYTES = 32 * 1024


class RankedHitError(ValueError):
    """Malformed or unsafe host-ranked candidate input."""


@dataclass(frozen=True, slots=True)
class PreparedHit:
    hit: dict[str, Any]
    sentences: tuple[str, ...]
    signatures: tuple[tuple[str, ...], ...]
    preferred: tuple[int, ...]
    title_identity: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PreparedRankedHits:
    retrieval_query: str
    hits: tuple[PreparedHit, ...]
    retrieved_count: int
    deduped_count: int
    weight_source: str


@dataclass(frozen=True, slots=True)
class ProjectionTier:
    max_bytes: int
    payload: bytes | None
    emitted: tuple[dict[str, Any], ...]
    evidence_bytes: int
    redundant_context_count: int
    anchor_fallback_count: int


def tokenize(text: str) -> tuple[str, ...]:
    if not isinstance(text, str):
        raise RankedHitError("text must be a string")
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return tuple(TOKEN_RE.findall(normalized))


def split_sentences(text: str) -> tuple[str, ...]:
    if not isinstance(text, str):
        raise RankedHitError("candidate text must be a string")
    pieces: list[str] = []
    start = 0
    for match in SENTENCE_SPLIT_RE.finditer(text):
        raw = text[start:match.start()].strip()
        if raw:
            pieces.append(raw)
        start = match.end()
    raw = text[start:].strip()
    if raw:
        pieces.append(raw)
    return tuple(pieces)


def _validate_hit(value: Any, index: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RankedHitError(f"ranked hit {index} must be an object")
    hit_id = value.get("id")
    title = value.get("title", "")
    text = value.get("text")
    if not isinstance(hit_id, str) or not hit_id.strip():
        raise RankedHitError(f"ranked hit {index} id must be nonempty text")
    if not isinstance(title, str) or not isinstance(text, str) or not text.strip():
        raise RankedHitError(f"ranked hit {index} title/text must be text and text must be nonempty")
    if len(text.encode("utf-8")) > MAX_TEXT_BYTES:
        raise RankedHitError(f"ranked hit {index} text exceeds attach-profile byte limit")
    return value


def _query_aware_exact_dedup(hits: list[dict[str, Any]], query_terms: set[str]) -> list[dict[str, Any]]:
    """Collapse exact body mirrors unless a later title contributes queried identity."""
    unique: list[dict[str, Any]] = []
    title_terms_by_text: dict[str, set[str]] = {}
    for hit in hits:
        relevant_title_terms = set(tokenize(hit["title"])) & query_terms
        covered = title_terms_by_text.get(hit["text"])
        if covered is not None and relevant_title_terms <= covered:
            continue
        unique.append(hit)
        if covered is None:
            title_terms_by_text[hit["text"]] = set(relevant_title_terms)
        else:
            covered.update(relevant_title_terms)
    return unique


def _candidate_local_weights(
    signatures_by_hit: list[tuple[tuple[str, ...], ...]],
    titles: list[str],
    query_terms: set[str],
) -> dict[str, float]:
    """Estimate query-term rarity only from the bounded host-supplied candidate pool."""
    n_docs = max(1, len(signatures_by_hit))
    dfs = {term: 0 for term in query_terms}
    for signatures, title in zip(signatures_by_hit, titles):
        document_terms = set(tokenize(title))
        for signature in signatures:
            document_terms.update(signature)
        for term in query_terms & document_terms:
            dfs[term] += 1
    weights: dict[str, float] = {}
    for term, df in dfs.items():
        if df:
            weights[term] = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
    return weights


def _validate_term_weights(value: Any, query_terms: set[str]) -> dict[str, float]:
    if not isinstance(value, dict) or len(value) > 64:
        raise RankedHitError("term_weights must be a bounded object")
    weights: dict[str, float] = {}
    for term, weight in value.items():
        if not isinstance(term, str) or term not in query_terms:
            raise RankedHitError("term_weights keys must be normalized retrieval-query terms")
        if type(weight) not in {int, float} or not math.isfinite(float(weight)) or float(weight) < 0:
            raise RankedHitError("term_weights values must be finite nonnegative numbers")
        weights[term] = float(weight)
    return weights


def _weights_from_doc_freqs(
    value: Any,
    document_count: int,
    query_terms: set[str],
) -> dict[str, float]:
    """Derive rarity weights from raw host-native document statistics."""
    if type(document_count) is not int or document_count < 1:
        raise RankedHitError("document_count must be a positive integer")
    if not isinstance(value, dict) or len(value) > 64:
        raise RankedHitError("term_doc_freqs must be a bounded object")
    weights: dict[str, float] = {}
    for term, df in value.items():
        if not isinstance(term, str) or term not in query_terms:
            raise RankedHitError("term_doc_freqs keys must be normalized retrieval-query terms")
        if type(df) is not int or not 1 <= df <= document_count:
            raise RankedHitError("term_doc_freqs values must be integers within document_count")
        weights[term] = math.log(1.0 + (document_count - df + 0.5) / (df + 0.5))
    return weights


def prepare_ranked_hits(
    hits: Iterable[dict[str, Any]],
    retrieval_query: str,
    *,
    term_weights: dict[str, float] | None = None,
    term_doc_freqs: dict[str, int] | None = None,
    document_count: int | None = None,
) -> PreparedRankedHits:
    """Validate/dedup/tokenize a host-ranked pool once for multi-tier projection.

    A host lexical retriever may optionally lend raw query-term document frequencies
    plus its document count, or precomputed query-term weights. Raw document statistics
    are preferred because they map directly to common search APIs and keep ExactScope's
    weighting formula local. When neither is exposed, candidate-local rarity is the
    bounded fallback.
    """
    if not isinstance(retrieval_query, str) or not retrieval_query.strip():
        raise RankedHitError("retrieval_query must be nonempty text")
    if isinstance(hits, (str, bytes, dict)):
        raise RankedHitError("ranked hits must be an iterable of objects")
    materialized = list(hits)
    if not 1 <= len(materialized) <= MAX_RANKED_HITS:
        raise RankedHitError(f"ranked hits must contain between 1 and {MAX_RANKED_HITS} entries")
    validated = [_validate_hit(hit, index) for index, hit in enumerate(materialized)]
    query_terms = set(tokenize(retrieval_query))
    unique = _query_aware_exact_dedup(validated, query_terms)

    if term_weights is not None and term_doc_freqs is not None:
        raise RankedHitError("provide either term_weights or term_doc_freqs, not both")
    if term_doc_freqs is None and document_count is not None:
        raise RankedHitError("document_count requires term_doc_freqs")

    sentence_rows: list[tuple[dict[str, Any], tuple[str, ...], tuple[tuple[str, ...], ...]]] = []
    for hit in unique:
        sentences = split_sentences(hit["text"])
        if not sentences:
            continue
        signatures = tuple(tokenize(sentence) for sentence in sentences)
        sentence_rows.append((hit, sentences, signatures))

    if term_doc_freqs is not None:
        if document_count is None:
            raise RankedHitError("term_doc_freqs require document_count")
        weights = _weights_from_doc_freqs(term_doc_freqs, document_count, query_terms)
        weight_source = "host-doc-freqs"
    elif term_weights is None:
        weights = _candidate_local_weights(
            [row[2] for row in sentence_rows],
            [row[0]["title"] for row in sentence_rows],
            query_terms,
        )
        weight_source = "candidate-local-idf"
    else:
        weights = _validate_term_weights(term_weights, query_terms)
        weight_source = "host-term-weights"
    def sentence_score(signature: tuple[str, ...]) -> float:
        score = 0.0
        for term in sorted(set(signature) & query_terms, key=lambda value: value.encode("utf-8")):
            score += weights.get(term, 0.0)
        return score

    prepared: list[PreparedHit] = []
    for hit, sentences, signatures in sentence_rows:
        anchor = min(
            range(len(sentences)),
            key=lambda position: (-sentence_score(signatures[position]), position),
        )
        if len(sentences) == 1:
            preferred = (anchor,)
        elif anchor == 0:
            preferred = (0, 1)
        else:
            preferred = (anchor - 1, anchor)
        title_identity = tuple(
            sorted(set(tokenize(hit["title"])) & query_terms, key=lambda value: value.encode("utf-8"))
        )
        prepared.append(PreparedHit(hit, sentences, signatures, preferred, title_identity))

    return PreparedRankedHits(
        retrieval_query=retrieval_query,
        hits=tuple(prepared),
        retrieved_count=len(validated),
        deduped_count=len(unique),
        weight_source=weight_source,
    )


def _encode_rows(rows: list[dict[str, Any]]) -> bytes:
    return (
        EVIDENCE_PREFIX
        + json.dumps(
            {"g": [{"r": "supplemental", "s": "grounded", "e": rows}]},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    ).encode("utf-8")


def _encode_row(row: dict[str, Any]) -> bytes:
    return json.dumps(row, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


EMPTY_ROWS_BYTES = len(_encode_rows([]))


def project_prepared(
    prepared: PreparedRankedHits,
    *,
    max_bytes: int,
    max_items: int = 8,
) -> ProjectionTier:
    if not isinstance(prepared, PreparedRankedHits):
        raise RankedHitError("prepared ranked hits have invalid type")
    if type(max_bytes) is not int or max_bytes < 256:
        raise RankedHitError("max_bytes must be an integer >= 256")
    if type(max_items) is not int or not 1 <= max_items <= 16:
        raise RankedHitError("max_items must be between 1 and 16")

    rows: list[dict[str, Any]] = []
    emitted: list[dict[str, Any]] = []
    encoded_size = EMPTY_ROWS_BYTES
    seen_contexts: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
    redundant = 0
    fallbacks = 0

    for item in prepared.hits:
        if len(rows) >= max_items:
            break
        nonempty = [item.signatures[position] for position in item.preferred if item.signatures[position]]
        if nonempty and all((signature, item.title_identity) in seen_contexts for signature in nonempty):
            redundant += 1
            continue
        anchor = item.preferred[-1]
        spans = (item.preferred, (anchor,)) if len(item.preferred) > 1 else (item.preferred,)
        accepted = None
        for positions in spans:
            snippet = " ".join(item.sentences[position] for position in positions)
            row = {"t": item.hit["title"] or item.hit["id"], "v": snippet}
            added_bytes = len(_encode_row(row)) + int(bool(rows))
            if encoded_size + added_bytes <= max_bytes:
                accepted = row, snippet, positions, added_bytes
                break
        if accepted is None:
            continue
        row, snippet, positions, added_bytes = accepted
        if len(item.preferred) > 1 and len(positions) == 1:
            fallbacks += 1
        rows.append(row)
        encoded_size += added_bytes
        emitted.append({**item.hit, "snippet": snippet, "sentence_positions": list(positions)})
        seen_contexts.update((item.signatures[position], item.title_identity) for position in positions)

    payload = _encode_rows(rows) if rows else None
    if payload is not None and (len(payload) != encoded_size or len(payload) > max_bytes):
        raise RankedHitError("ranked-hit projection byte accounting drift")
    return ProjectionTier(
        max_bytes=max_bytes,
        payload=payload,
        emitted=tuple(emitted),
        evidence_bytes=len(payload) if payload is not None else 0,
        redundant_context_count=redundant,
        anchor_fallback_count=fallbacks,
    )


def project_tiers(
    hits: Iterable[dict[str, Any]],
    retrieval_query: str,
    *,
    tiers: tuple[int, ...] = DEFAULT_TIERS,
    max_items: int = 8,
    term_weights: dict[str, float] | None = None,
    term_doc_freqs: dict[str, int] | None = None,
    document_count: int | None = None,
) -> tuple[ProjectionTier, ...]:
    """Prepare once, then emit complete candidates in host-fit preference order."""
    if (
        not isinstance(tiers, tuple)
        or not tiers
        or len(tiers) > 4
        or any(type(value) is not int or value < 256 for value in tiers)
        or any(left <= right for left, right in zip(tiers, tiers[1:]))
    ):
        raise RankedHitError("tiers must be 1-4 strictly descending integer byte budgets >= 256")
    prepared = prepare_ranked_hits(
        hits,
        retrieval_query,
        term_weights=term_weights,
        term_doc_freqs=term_doc_freqs,
        document_count=document_count,
    )
    return tuple(project_prepared(prepared, max_bytes=tier, max_items=max_items) for tier in tiers)


def _append_utf8_bounded(out: bytearray, text: str, max_bytes: int) -> None:
    remaining = max_bytes - len(out)
    if remaining <= 0:
        return
    data = text.encode("utf-8")
    if len(data) <= remaining:
        out.extend(data)
        return
    fragment = data[:remaining]
    while fragment:
        try:
            fragment.decode("utf-8")
            break
        except UnicodeDecodeError:
            fragment = fragment[:-1]
    out.extend(fragment)


def project_host_ranked_hybrid_h1(
    hits: Iterable[dict[str, Any]],
    retrieval_query: str,
    *,
    max_bytes: int = 3072,
    full_ranked_documents: int = 1,
    max_items: int = 12,
) -> tuple[bytes, tuple[dict[str, Any], ...], dict[str, Any]]:
    """Freeze the H1 attach policy: top host document full, later hits as anchors.

    Retrieval rank/order/score remain host-owned. ExactScope only shapes the supplied
    bounded ranked pool. The query-aware anchor pass intentionally mirrors the
    development `multihop-coverage-v1` coverage pass used to select H1, while the
    emitted model context is ordinary text rather than the grouped-evidence wrapper.
    No grounding-policy prompt is added by this function.
    """
    if type(max_bytes) is not int or max_bytes < 256:
        raise RankedHitError("max_bytes must be an integer >= 256")
    if type(full_ranked_documents) is not int or not 1 <= full_ranked_documents <= max_items:
        raise RankedHitError("full_ranked_documents must be between 1 and max_items")
    if type(max_items) is not int or not 1 <= max_items <= MAX_RANKED_HITS:
        raise RankedHitError("max_items must be between 1 and 16")

    materialized = list(hits)
    if not 1 <= len(materialized) <= MAX_RANKED_HITS:
        raise RankedHitError(f"ranked hits must contain between 1 and {MAX_RANKED_HITS} entries")
    validated = [_validate_hit(hit, index) for index, hit in enumerate(materialized)]
    prepared = prepare_ranked_hits(validated, retrieval_query)

    # Reproduce the two-pass multihop coverage projection that supplied H1's
    # later-hit snippets during candidate selection: first maximize document
    # coverage with one anchor sentence, then expand admitted anchors with the
    # preferred adjacent sentence when the grouped-evidence budget still fits.
    grouped_size = EMPTY_ROWS_BYTES
    seen_contexts: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
    rows: list[dict[str, Any]] = []
    selected: list[PreparedHit] = []
    snippet_by_id: dict[str, str] = {}
    positions_by_id: dict[str, tuple[int, ...]] = {}
    skipped_for_budget = 0
    redundant = 0
    for item in prepared.hits:
        if len(rows) >= max_items:
            break
        anchor = item.preferred[-1]
        signature = item.signatures[anchor]
        key = (signature, item.title_identity)
        if signature and key in seen_contexts:
            redundant += 1
            continue
        snippet = item.sentences[anchor]
        row = {"t": item.hit["title"] or item.hit["id"], "v": snippet}
        added_bytes = len(_encode_row(row)) + int(bool(rows))
        if grouped_size + added_bytes > max_bytes:
            skipped_for_budget += 1
            continue
        rows.append(row)
        selected.append(item)
        grouped_size += added_bytes
        snippet_by_id[item.hit["id"]] = snippet
        positions_by_id[item.hit["id"]] = (anchor,)
        if signature:
            seen_contexts.add(key)

    expanded = 0
    for row_index, item in enumerate(selected):
        if len(item.preferred) <= 1:
            continue
        candidate_snippet = " ".join(item.sentences[position] for position in item.preferred)
        if candidate_snippet == rows[row_index]["v"]:
            continue
        candidate_row = {"t": item.hit["title"] or item.hit["id"], "v": candidate_snippet}
        delta = len(_encode_row(candidate_row)) - len(_encode_row(rows[row_index]))
        if grouped_size + delta > max_bytes:
            continue
        rows[row_index] = candidate_row
        grouped_size += delta
        snippet_by_id[item.hit["id"]] = candidate_snippet
        positions_by_id[item.hit["id"]] = item.preferred
        expanded += 1

    prefix = b"Retrieved context (host-ranked hybrid):\n"
    if len(prefix) >= max_bytes:
        raise RankedHitError("hybrid context prefix exceeds max_bytes")
    out = bytearray(prefix)
    emitted: list[dict[str, Any]] = []
    for rank, hit in enumerate(validated[:max_items]):
        if len(out) >= max_bytes:
            break
        if rank < full_ranked_documents:
            body = hit["text"]
            source = "full"
            sentence_position = None
        else:
            body = snippet_by_id.get(hit["id"], "")
            source = "anchor"
            sentence_position = positions_by_id.get(hit["id"])
        if not body:
            continue
        before = len(out)
        segment = f"\n[{hit['title'] or hit['id']}]\n{body}\n"
        _append_utf8_bounded(out, segment, max_bytes)
        if len(out) == before:
            break
        emitted.append({
            **hit,
            "hybrid_source": source,
            "sentence_position": sentence_position,
        })

    payload = bytes(out)
    return payload, tuple(emitted), {
        "projection_id": "host-ranked-hybrid-h1-v0",
        "max_evidence_bytes": max_bytes,
        "full_ranked_documents": full_ranked_documents,
        "max_items": max_items,
        "retrieved_count": len(validated),
        "deduped_count": prepared.deduped_count,
        "anchor_candidate_count": len(snippet_by_id),
        "expanded_anchor_count": expanded,
        "coverage_pass_grouped_bytes": grouped_size,
        "skipped_for_anchor_budget": skipped_for_budget,
        "redundant_anchor_count": redundant,
        "evidence_bytes": len(payload),
        "weight_source": prepared.weight_source,
    }
