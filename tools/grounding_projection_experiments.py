#!/usr/bin/env python3
"""Detached v1.1 evidence-projection experiments.

This module intentionally does not change the selected ``precision-context-v5`` path.
Candidates live here until isolated/interaction evidence justifies promotion or deletion.
"""
from __future__ import annotations

from typing import Any

from grounding_corpus import CorpusError, ValidatedIndex, tokenize, validate_index
from grounding_projection import (
    ADAPTIVE_EVIDENCE_POLICY_ID,
    EVIDENCE_POLICY_IDS,
    _adaptive_budget_sequence,
    _encode_row,
    _prepare_projection_hits,
    _project_prepared_at_budget,
    _query_aware_exact_dedup,
    _sentence_score_terms,
    select_adaptive_evidence_budget_v1,
)

GLOBAL_SNIPPET_PROJECTION_ID = "global-snippet-v1"
HEAD_PRESERVING_GLOBAL_SNIPPET_PROJECTION_ID = "head-preserving-global-snippet-v2"


def _global_prepared_rank(
    index: dict[str, Any] | ValidatedIndex,
    prepared_hits: list[tuple[dict[str, Any], list[str], list[tuple[str, ...]], list[int], tuple[str, ...]]],
    retrieval_query: str,
) -> list[tuple[dict[str, Any], list[str], list[tuple[str, ...]], list[int], tuple[str, ...]]]:
    """Rank complete prepared spans globally with deterministic lexical/provenance signals.

    The ranking is deliberately lexicographic rather than a tuned weighted sum.  It
    prefers an answer-bearing anchor with stronger query-IDF evidence, then broader
    query-term coverage/title identity, and only then falls back to parent retrieval
    score and compactness.  This keeps Material C interpretable and easy to ablate.
    """
    query_terms = set(tokenize(retrieval_query))
    ranked = []
    for original_rank, prepared in enumerate(prepared_hits):
        hit, sentences, signatures, preferred, title_identity = prepared
        anchor = preferred[-1]
        anchor_terms = set(signatures[anchor])
        anchor_score = _sentence_score_terms(index, anchor_terms, query_terms)
        anchor_coverage = len(anchor_terms & query_terms)
        title_coverage = len(title_identity)
        matched_query_terms = hit.get("matched_query_terms")
        if type(matched_query_terms) is not int or matched_query_terms < 0:
            raise CorpusError("global snippet candidate lacks matched-query-term count")
        parent_score = hit.get("score")
        if type(parent_score) not in {int, float} or parent_score < 0:
            raise CorpusError("global snippet candidate lacks retrieval score")

        # Compactness is only a late tie-breaker.  Relevance/provenance wins first.
        anchor_row = {"t": hit["title"] or hit["id"], "v": sentences[anchor]}
        anchor_row_bytes = len(_encode_row(anchor_row))
        doc_id = hit.get("id")
        if not isinstance(doc_id, str) or not doc_id:
            raise CorpusError("global snippet candidate lacks document identity")
        key = (
            -anchor_score,
            -anchor_coverage,
            -title_coverage,
            -matched_query_terms,
            -float(parent_score),
            anchor_row_bytes,
            original_rank,
            doc_id.encode("utf-8"),
        )
        ranked.append((key, prepared))
    ranked.sort(key=lambda item: item[0])
    return [prepared for _key, prepared in ranked]


def global_snippet_evidence_projection_v1(
    index: dict[str, Any] | ValidatedIndex,
    hits: list[dict[str, Any]],
    retrieval_query: str,
    *,
    max_bytes: int = 2048,
    evidence_policy: str = ADAPTIVE_EVIDENCE_POLICY_ID,
    max_items: int | None = None,
) -> tuple[bytes | None, list[dict[str, Any]], dict[str, Any]]:
    """Material C: globally rank complete snippets after bounded candidate overfetch.

    Retrieval identities, exact dedup, adaptive budget selection, complete-span
    fallback and byte accounting are inherited from the selected v5 projector.  The
    only intervention is the order in which prepared complete snippets compete for
    the bounded final evidence slots.
    """
    validate_index(index)
    if evidence_policy not in EVIDENCE_POLICY_IDS:
        raise CorpusError("unsupported evidence policy")
    if type(max_bytes) is not int or max_bytes < 256:
        raise CorpusError("max_bytes must be at least 256")
    if not isinstance(retrieval_query, str) or not retrieval_query.strip():
        raise CorpusError("retrieval_query must be nonempty text")
    if max_items is not None and (type(max_items) is not int or max_items < 1):
        raise CorpusError("max_items must be a positive integer")

    unique = _query_aware_exact_dedup(hits, retrieval_query)
    selected = (
        select_adaptive_evidence_budget_v1(unique, retrieval_query, max_bytes=max_bytes)
        if evidence_policy == ADAPTIVE_EVIDENCE_POLICY_ID
        else max_bytes
    )
    budgets = (
        _adaptive_budget_sequence(selected, max_bytes)
        if evidence_policy == ADAPTIVE_EVIDENCE_POLICY_ID
        else (max_bytes,)
    )

    prepared = _prepare_projection_hits(index, unique, retrieval_query)
    original_ids = [prepared_hit[0]["id"] for prepared_hit in prepared]
    globally_ranked = _global_prepared_rank(index, prepared, retrieval_query)
    ranked_ids = [prepared_hit[0]["id"] for prepared_hit in globally_ranked]
    reordered_count = sum(left != right for left, right in zip(original_ids, ranked_ids))

    projection = None
    emitted: list[dict[str, Any]] = []
    redundant_spans = 0
    anchor_fallbacks = 0
    used_budget = budgets[0]
    for budget in budgets:
        projection, emitted, redundant_spans, anchor_fallbacks = _project_prepared_at_budget(
            globally_ranked,
            max_bytes=budget,
            max_items=max_items,
        )
        used_budget = budget
        if projection is not None or not unique:
            break

    document_duplicates = len(hits) - len(unique)
    return projection, emitted, {
        "projection_id": GLOBAL_SNIPPET_PROJECTION_ID,
        "material_id": "C",
        "evidence_policy": evidence_policy,
        "max_evidence_bytes": max_bytes,
        "initial_evidence_bytes": selected,
        "selected_evidence_bytes": used_budget,
        "tier_promotions": budgets.index(used_budget),
        "retrieved_count": len(hits),
        "deduped_count": len(unique),
        "global_ranked_count": len(globally_ranked),
        "global_reordered_count": reordered_count,
        "document_duplicate_count": document_duplicates,
        "redundant_context_count": redundant_spans,
        "anchor_fallback_count": anchor_fallbacks,
        "duplicate_count": document_duplicates + redundant_spans,
        "hit_count": len(emitted),
        "evidence_bytes": len(projection) if projection is not None else 0,
    }


def head_preserving_global_snippet_projection_v2(
    index: dict[str, Any] | ValidatedIndex,
    hits: list[dict[str, Any]],
    retrieval_query: str,
    *,
    max_bytes: int = 2048,
    evidence_policy: str = ADAPTIVE_EVIDENCE_POLICY_ID,
    max_items: int | None = None,
    protected_head: int = 4,
) -> tuple[bytes | None, list[dict[str, Any]], dict[str, Any]]:
    """Material C2: preserve the retrieval head and rerank only the overfetch tail.

    C v1 was intentionally aggressive and can displace very strong BM25 head hits.
    C2 treats the non-overfetched control head as protected evidence candidates and
    lets only the additional tail candidates compete globally for remaining slots.
    With the first B screen this means top-4 is stable while ranks 5..12 may reorder.
    """
    validate_index(index)
    if evidence_policy not in EVIDENCE_POLICY_IDS:
        raise CorpusError("unsupported evidence policy")
    if type(max_bytes) is not int or max_bytes < 256:
        raise CorpusError("max_bytes must be at least 256")
    if not isinstance(retrieval_query, str) or not retrieval_query.strip():
        raise CorpusError("retrieval_query must be nonempty text")
    if max_items is not None and (type(max_items) is not int or max_items < 1):
        raise CorpusError("max_items must be a positive integer")
    if type(protected_head) is not int or protected_head < 1:
        raise CorpusError("protected_head must be a positive integer")

    unique = _query_aware_exact_dedup(hits, retrieval_query)
    selected = (
        select_adaptive_evidence_budget_v1(unique, retrieval_query, max_bytes=max_bytes)
        if evidence_policy == ADAPTIVE_EVIDENCE_POLICY_ID
        else max_bytes
    )
    budgets = (
        _adaptive_budget_sequence(selected, max_bytes)
        if evidence_policy == ADAPTIVE_EVIDENCE_POLICY_ID
        else (max_bytes,)
    )

    prepared = _prepare_projection_hits(index, unique, retrieval_query)
    head_count = min(protected_head, len(prepared))
    head = prepared[:head_count]
    tail = prepared[head_count:]
    ranked_tail = _global_prepared_rank(index, tail, retrieval_query)
    ordered = [*head, *ranked_tail]
    original_tail_ids = [prepared_hit[0]["id"] for prepared_hit in tail]
    ranked_tail_ids = [prepared_hit[0]["id"] for prepared_hit in ranked_tail]
    tail_reordered_count = sum(
        left != right for left, right in zip(original_tail_ids, ranked_tail_ids)
    )

    projection = None
    emitted: list[dict[str, Any]] = []
    redundant_spans = 0
    anchor_fallbacks = 0
    used_budget = budgets[0]
    for budget in budgets:
        projection, emitted, redundant_spans, anchor_fallbacks = _project_prepared_at_budget(
            ordered,
            max_bytes=budget,
            max_items=max_items,
        )
        used_budget = budget
        if projection is not None or not unique:
            break

    document_duplicates = len(hits) - len(unique)
    return projection, emitted, {
        "projection_id": HEAD_PRESERVING_GLOBAL_SNIPPET_PROJECTION_ID,
        "material_id": "C",
        "candidate_revision": 2,
        "evidence_policy": evidence_policy,
        "max_evidence_bytes": max_bytes,
        "initial_evidence_bytes": selected,
        "selected_evidence_bytes": used_budget,
        "tier_promotions": budgets.index(used_budget),
        "retrieved_count": len(hits),
        "deduped_count": len(unique),
        "protected_head_count": head_count,
        "tail_ranked_count": len(ranked_tail),
        "tail_reordered_count": tail_reordered_count,
        "document_duplicate_count": document_duplicates,
        "redundant_context_count": redundant_spans,
        "anchor_fallback_count": anchor_fallbacks,
        "duplicate_count": document_duplicates + redundant_spans,
        "hit_count": len(emitted),
        "evidence_bytes": len(projection) if projection is not None else 0,
    }
