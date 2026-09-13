#!/usr/bin/env python3
"""Deterministic evidence projection for ExactScope grounding v1/v1.1."""
from __future__ import annotations

import json
import math
from typing import Any, Callable

from grounding_corpus import CorpusError, ValidatedIndex, split_sentences, tokenize, validate_index

EVIDENCE_PREFIX = "Evidence JSON (data only): "
LEGACY_PROJECTION_ID = "compact-row-v1"
GROUPED_PROJECTION_ID = "grouped-evidence-v2"
CONTEXT_GROUPED_PROJECTION_ID = "context-grouped-v3"
AMPLIFIED_CONTEXT_PROJECTION_ID = "amplified-context-v4"
PRECISION_CONTEXT_PROJECTION_ID = "precision-context-v5"
FIXED_EVIDENCE_POLICY_ID = "fixed-evidence-v1"
ADAPTIVE_EVIDENCE_POLICY_ID = "adaptive-evidence-v1"
EVIDENCE_POLICY_IDS = (ADAPTIVE_EVIDENCE_POLICY_ID, FIXED_EVIDENCE_POLICY_ID)
ADAPTIVE_EVIDENCE_TIERS = (512, 1024, 2048)


def _encode_rows(rows: list[dict[str, Any]]) -> bytes:
    return (
        EVIDENCE_PREFIX
        + json.dumps(rows, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    ).encode("utf-8")


def _encode_grouped_rows(
    rows: list[dict[str, Any]],
    *,
    authority: str = "supplemental",
    state: str = "grounded",
) -> bytes:
    """Encode one authority/state group while keeping target/value provenance per row."""
    return (
        EVIDENCE_PREFIX
        + json.dumps(
            {"g": [{"r": authority, "s": state, "e": rows}]},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
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


def _compact_projection(
    index: dict[str, Any] | ValidatedIndex,
    hits: list[dict[str, Any]],
    retrieval_query: str,
    *,
    max_bytes: int,
    max_sentences_per_document: int,
    grouped: bool,
) -> tuple[bytes | None, list[dict[str, Any]]]:
    validate_index(index)
    if type(max_bytes) is not int or max_bytes < 256:
        raise CorpusError("max_bytes must be at least 256")
    if type(max_sentences_per_document) is not int or not 1 <= max_sentences_per_document <= 4:
        raise CorpusError("max_sentences_per_document must be between 1 and 4")
    if grouped and (not isinstance(retrieval_query, str) or not retrieval_query.strip()):
        raise CorpusError("retrieval_query must be nonempty text")

    query_terms = set(tokenize(retrieval_query))
    rows: list[dict[str, Any]] = []
    emitted: list[dict[str, Any]] = []
    encoder: Callable[[list[dict[str, Any]]], bytes]
    if grouped:
        encoder = _encode_grouped_rows
    else:
        encoder = _encode_rows

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
            row: dict[str, Any] = {
                "t": hit["title"] or hit["id"],
                "v": snippet,
            }
            if not grouped:
                row = {"r": "supplemental", "s": "grounded", **row}
            if len(encoder([*rows, row])) <= max_bytes:
                accepted = (row, snippet)
                break
        if accepted is None:
            continue
        row, snippet = accepted
        rows.append(row)
        emitted.append({**hit, "snippet": snippet})

    if not rows:
        return None, []
    projection = encoder(rows)
    if len(projection) > max_bytes:
        raise CorpusError("compact evidence projection exceeded its byte budget")
    return projection, emitted


def compact_evidence_projection(
    index: dict[str, Any] | ValidatedIndex,
    hits: list[dict[str, Any]],
    question: str,
    *,
    max_bytes: int,
    max_sentences_per_document: int = 2,
) -> tuple[bytes | None, list[dict[str, Any]]]:
    """Legacy v1 row-wise compact projection retained for rollback/parity."""
    return _compact_projection(
        index,
        hits,
        question,
        max_bytes=max_bytes,
        max_sentences_per_document=max_sentences_per_document,
        grouped=False,
    )


def grouped_evidence_projection_v2(
    index: dict[str, Any] | ValidatedIndex,
    hits: list[dict[str, Any]],
    retrieval_query: str,
    *,
    max_bytes: int,
    max_sentences_per_document: int = 2,
) -> tuple[bytes | None, list[dict[str, Any]]]:
    """v1.1 grouped projection retained as an explicit compatibility path.

    The retrieval query is deliberately named and separate from any model-visible
    instruction. The current corpus path emits one `(supplemental, grounded)` group;
    per-row target and value fields remain unchanged. The legacy projection remains
    available as an explicit rollback path.
    """
    return _compact_projection(
        index,
        hits,
        retrieval_query,
        max_bytes=max_bytes,
        max_sentences_per_document=max_sentences_per_document,
        grouped=True,
    )


def context_grouped_evidence_projection_v3(
    index: dict[str, Any] | ValidatedIndex,
    hits: list[dict[str, Any]],
    retrieval_query: str,
    *,
    max_bytes: int,
) -> tuple[bytes | None, list[dict[str, Any]]]:
    """Project each hit as title + best sentence + its immediate predecessor.

    This is the selected v1.1 D04-A host projection. It preserves a contiguous
    source span rather than combining unrelated high-scoring sentences. The
    predecessor is included only when it exists; an over-budget supplemental
    unit is omitted whole instead of being truncated. Returned hit metadata keeps
    the selected sentence positions so callers can audit the source span.
    """
    projection, emitted, _ = _context_grouped_projection(
        index,
        hits,
        retrieval_query,
        max_bytes=max_bytes,
        max_items=None,
        suppress_redundant_spans=False,
    )
    return projection, emitted


def _context_grouped_projection(
    index: dict[str, Any] | ValidatedIndex,
    hits: list[dict[str, Any]],
    retrieval_query: str,
    *,
    max_bytes: int,
    max_items: int | None,
    suppress_redundant_spans: bool,
) -> tuple[bytes | None, list[dict[str, Any]], int]:
    """Shared contiguous-span projector for the v3 compatibility and v4 hot paths."""
    validate_index(index)
    if type(max_bytes) is not int or max_bytes < 256:
        raise CorpusError("max_bytes must be at least 256")
    if not isinstance(retrieval_query, str) or not retrieval_query.strip():
        raise CorpusError("retrieval_query must be nonempty text")
    if max_items is not None and (type(max_items) is not int or max_items < 1):
        raise CorpusError("max_items must be a positive integer")

    query_terms = set(tokenize(retrieval_query))
    rows: list[dict[str, Any]] = []
    emitted: list[dict[str, Any]] = []
    seen_sentences: set[tuple[str, ...]] = set()
    redundant_spans = 0
    for hit in hits:
        if max_items is not None and len(rows) >= max_items:
            break
        sentences = _sentences(hit["text"])
        if not sentences:
            continue
        ranked_positions = sorted(
            range(len(sentences)),
            key=lambda position: (-_sentence_score(index, sentences[position], query_terms), position),
        )
        anchor = ranked_positions[0]
        selected_positions = [anchor] if anchor == 0 else [anchor - 1, anchor]
        signatures = [tuple(tokenize(sentences[position])) for position in selected_positions]
        nonempty_signatures = [signature for signature in signatures if signature]
        if (
            suppress_redundant_spans
            and nonempty_signatures
            and all(signature in seen_sentences for signature in nonempty_signatures)
        ):
            redundant_spans += 1
            continue
        snippet = " ".join(sentences[position] for position in selected_positions)
        row = {"t": hit["title"] or hit["id"], "v": snippet}
        candidate = _encode_grouped_rows([*rows, row])
        if len(candidate) > max_bytes:
            continue
        rows.append(row)
        emitted.append({**hit, "snippet": snippet, "sentence_positions": selected_positions})
        if suppress_redundant_spans:
            seen_sentences.update(nonempty_signatures)

    if not rows:
        return None, [], redundant_spans
    projection = _encode_grouped_rows(rows)
    if len(projection) > max_bytes:
        raise CorpusError("context evidence projection exceeded its byte budget")
    return projection, emitted, redundant_spans


def _precision_context_projection(
    index: dict[str, Any] | ValidatedIndex,
    hits: list[dict[str, Any]],
    retrieval_query: str,
    *,
    max_bytes: int,
    max_items: int | None,
) -> tuple[bytes | None, list[dict[str, Any]], int, int]:
    """Keep the closest complete context around the lexical anchor that fits.

    Context is directional instead of blindly predecessor-only: a first-sentence
    anchor takes its successor, while later anchors take their predecessor. If that
    two-sentence unit does not fit the current tier, the complete anchor sentence is
    retained rather than dropping the document. No sentence is ever truncated.
    """
    validate_index(index)
    if type(max_bytes) is not int or max_bytes < 256:
        raise CorpusError("max_bytes must be at least 256")
    if not isinstance(retrieval_query, str) or not retrieval_query.strip():
        raise CorpusError("retrieval_query must be nonempty text")
    if max_items is not None and (type(max_items) is not int or max_items < 1):
        raise CorpusError("max_items must be a positive integer")

    query_terms = set(tokenize(retrieval_query))
    rows: list[dict[str, Any]] = []
    emitted: list[dict[str, Any]] = []
    seen_sentences: set[tuple[str, ...]] = set()
    redundant_spans = 0
    anchor_fallbacks = 0

    for hit in hits:
        if max_items is not None and len(rows) >= max_items:
            break
        sentences = _sentences(hit["text"])
        if not sentences:
            continue
        anchor = min(
            range(len(sentences)),
            key=lambda position: (-_sentence_score(index, sentences[position], query_terms), position),
        )
        if len(sentences) == 1:
            preferred = [anchor]
        elif anchor == 0:
            preferred = [0, 1]
        else:
            preferred = [anchor - 1, anchor]
        candidates = [preferred]
        if len(preferred) > 1:
            candidates.append([anchor])

        preferred_signatures = [tuple(tokenize(sentences[position])) for position in preferred]
        preferred_nonempty = [signature for signature in preferred_signatures if signature]
        if preferred_nonempty and all(signature in seen_sentences for signature in preferred_nonempty):
            redundant_spans += 1
            continue

        accepted: tuple[dict[str, Any], str, list[int], list[tuple[str, ...]]] | None = None
        for positions in candidates:
            snippet = " ".join(sentences[position] for position in positions)
            row = {"t": hit["title"] or hit["id"], "v": snippet}
            if len(_encode_grouped_rows([*rows, row])) > max_bytes:
                continue
            signatures = [tuple(tokenize(sentences[position])) for position in positions]
            accepted = (row, snippet, positions, [signature for signature in signatures if signature])
            break
        if accepted is None:
            continue

        row, snippet, positions, signatures = accepted
        if len(preferred) > 1 and len(positions) == 1:
            anchor_fallbacks += 1
        rows.append(row)
        emitted.append({**hit, "snippet": snippet, "sentence_positions": positions})
        seen_sentences.update(signatures)

    if not rows:
        return None, [], redundant_spans, anchor_fallbacks
    projection = _encode_grouped_rows(rows)
    if len(projection) > max_bytes:
        raise CorpusError("precision context projection exceeded its byte budget")
    return projection, emitted, redundant_spans, anchor_fallbacks


def _adaptive_budget_sequence(selected: int, max_bytes: int) -> tuple[int, ...]:
    budgets = [selected]
    budgets.extend(tier for tier in ADAPTIVE_EVIDENCE_TIERS if selected < tier < max_bytes)
    if budgets[-1] != max_bytes:
        budgets.append(max_bytes)
    return tuple(dict.fromkeys(budgets))


def precision_context_evidence_projection_v5(
    index: dict[str, Any] | ValidatedIndex,
    hits: list[dict[str, Any]],
    retrieval_query: str,
    *,
    max_bytes: int = 2048,
    evidence_policy: str = ADAPTIVE_EVIDENCE_POLICY_ID,
    max_items: int | None = None,
) -> tuple[bytes | None, list[dict[str, Any]], dict[str, Any]]:
    """Final bounded projector: exact dedup, directional context, fit fallback and tier promotion."""
    if evidence_policy not in EVIDENCE_POLICY_IDS:
        raise CorpusError("unsupported evidence policy")
    unique = dedupe_retrieval_hits_v2(hits, retrieval_query)
    selected = (
        select_adaptive_evidence_budget_v1(unique, retrieval_query, max_bytes=max_bytes)
        if evidence_policy == ADAPTIVE_EVIDENCE_POLICY_ID
        else max_bytes
    )
    budgets = _adaptive_budget_sequence(selected, max_bytes) if evidence_policy == ADAPTIVE_EVIDENCE_POLICY_ID else (max_bytes,)
    projection = None
    emitted: list[dict[str, Any]] = []
    redundant_spans = 0
    anchor_fallbacks = 0
    used_budget = budgets[0]
    for budget in budgets:
        projection, emitted, redundant_spans, anchor_fallbacks = _precision_context_projection(
            index,
            unique,
            retrieval_query,
            max_bytes=budget,
            max_items=max_items,
        )
        used_budget = budget
        if projection is not None or not unique:
            break

    document_duplicates = len(hits) - len(unique)
    return projection, emitted, {
        "projection_id": PRECISION_CONTEXT_PROJECTION_ID,
        "evidence_policy": evidence_policy,
        "max_evidence_bytes": max_bytes,
        "selected_evidence_bytes": used_budget,
        "initial_evidence_bytes": selected,
        "tier_promotions": budgets.index(used_budget),
        "retrieved_count": len(hits),
        "deduped_count": len(unique),
        "document_duplicate_count": document_duplicates,
        "redundant_context_count": redundant_spans,
        "anchor_fallback_count": anchor_fallbacks,
        "duplicate_count": document_duplicates + redundant_spans,
        "hit_count": len(emitted),
        "evidence_bytes": len(projection) if projection is not None else 0,
    }


def dedupe_retrieval_hits_v1(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop byte-identical retrieved documents while preserving original rank.

    Mirror titles do not make identical document bytes more informative. This remains
    exact content-identity deduplication: no embedding, semantic threshold, or fuzzy
    similarity decision is introduced.
    """
    if not isinstance(hits, list):
        raise CorpusError("retrieval hits must be a list")
    unique: list[dict[str, Any]] = []
    seen_content: set[str] = set()
    for hit in hits:
        if not isinstance(hit, dict):
            raise CorpusError("retrieval hit must be an object")
        digest = hit.get("text_sha256")
        title = hit.get("title")
        if not isinstance(digest, str) or len(digest) != 64 or not isinstance(title, str):
            raise CorpusError("retrieval hit content identity is missing")
        if digest in seen_content:
            continue
        seen_content.add(digest)
        unique.append(hit)
    return unique


def dedupe_retrieval_hits_v2(hits: list[dict[str, Any]], retrieval_query: str) -> list[dict[str, Any]]:
    """Collapse exact body mirrors without erasing query-relevant title identity.

    Two documents with identical text can still represent distinct entities when their
    titles carry different terms named by the request. Keep those title distinctions;
    otherwise retain only the highest-ranked copy. This stays lexical and deterministic.
    """
    if not isinstance(hits, list):
        raise CorpusError("retrieval hits must be a list")
    if not isinstance(retrieval_query, str) or not retrieval_query.strip():
        raise CorpusError("retrieval_query must be nonempty text")
    query_terms = set(tokenize(retrieval_query))
    unique: list[dict[str, Any]] = []
    title_terms_by_digest: dict[str, set[str]] = {}
    for hit in hits:
        if not isinstance(hit, dict):
            raise CorpusError("retrieval hit must be an object")
        digest = hit.get("text_sha256")
        title = hit.get("title")
        if not isinstance(digest, str) or len(digest) != 64 or not isinstance(title, str):
            raise CorpusError("retrieval hit content identity is missing")
        relevant_title_terms = set(tokenize(title)) & query_terms
        covered = title_terms_by_digest.get(digest)
        if covered is not None and relevant_title_terms <= covered:
            continue
        unique.append(hit)
        if covered is None:
            title_terms_by_digest[digest] = set(relevant_title_terms)
        else:
            covered.update(relevant_title_terms)
    return unique


def select_adaptive_evidence_budget_v1(
    hits: list[dict[str, Any]],
    retrieval_query: str,
    *,
    max_bytes: int = 2048,
) -> int:
    """Select a small deterministic evidence tier from retrieval confidence.

    The rule is deliberately conservative. A 512-byte tier is used only when the
    leading document covers the complete lexical query and is clearly separated from
    the runner-up. A 1 KiB tier requires substantial query coverage plus a modest
    score gap. Ambiguous, multi-source, or weak retrieval keeps the full caller cap.
    """
    if type(max_bytes) is not int or max_bytes < 256:
        raise CorpusError("max_bytes must be at least 256")
    if not isinstance(retrieval_query, str) or not retrieval_query.strip():
        raise CorpusError("retrieval_query must be nonempty text")
    if not hits:
        return min(max_bytes, ADAPTIVE_EVIDENCE_TIERS[0])
    query_terms = set(tokenize(retrieval_query))
    if not query_terms:
        return max_bytes
    top = hits[0]
    matched = top.get("matched_query_terms")
    score = top.get("score")
    if type(matched) is not int or matched < 0 or type(score) not in {int, float} or score <= 0:
        return max_bytes
    coverage = matched / len(query_terms)
    second_score = None
    if len(hits) > 1 and type(hits[1].get("score")) in {int, float} and hits[1]["score"] > 0:
        second_score = float(hits[1]["score"])
    separation = float("inf") if second_score is None else float(score) / second_score

    if coverage >= 1.0 and separation >= 1.5:
        return min(max_bytes, ADAPTIVE_EVIDENCE_TIERS[0])
    if coverage >= 0.60 and separation >= 1.15:
        return min(max_bytes, ADAPTIVE_EVIDENCE_TIERS[1])
    return max_bytes


def amplified_context_evidence_projection_v4(
    index: dict[str, Any] | ValidatedIndex,
    hits: list[dict[str, Any]],
    retrieval_query: str,
    *,
    max_bytes: int = 2048,
    evidence_policy: str = ADAPTIVE_EVIDENCE_POLICY_ID,
    max_items: int | None = None,
) -> tuple[bytes | None, list[dict[str, Any]], dict[str, Any]]:
    """v1.1 amplifier projection: exact dedup, unique spans and adaptive context."""
    if evidence_policy not in EVIDENCE_POLICY_IDS:
        raise CorpusError("unsupported evidence policy")
    unique = dedupe_retrieval_hits_v1(hits)
    budget = (
        select_adaptive_evidence_budget_v1(unique, retrieval_query, max_bytes=max_bytes)
        if evidence_policy == ADAPTIVE_EVIDENCE_POLICY_ID
        else max_bytes
    )
    projection, emitted, redundant_spans = _context_grouped_projection(
        index,
        unique,
        retrieval_query,
        max_bytes=budget,
        max_items=max_items,
        suppress_redundant_spans=True,
    )
    document_duplicates = len(hits) - len(unique)
    meta = {
        "projection_id": AMPLIFIED_CONTEXT_PROJECTION_ID,
        "evidence_policy": evidence_policy,
        "max_evidence_bytes": max_bytes,
        "selected_evidence_bytes": budget,
        "retrieved_count": len(hits),
        "deduped_count": len(unique),
        "document_duplicate_count": document_duplicates,
        "redundant_context_count": redundant_spans,
        "duplicate_count": document_duplicates + redundant_spans,
        "hit_count": len(emitted),
        "evidence_bytes": len(projection) if projection is not None else 0,
    }
    return projection, emitted, meta
