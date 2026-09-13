#!/usr/bin/env python3
"""ExactScope final bounded local-corpus projection for the v1.1 runtime."""
from __future__ import annotations

import json
import math
from typing import Any, Callable

from grounding_text import CorpusError, split_sentences, tokenize

EVIDENCE_PREFIX = "Evidence JSON (data only): "
PRECISION_CONTEXT_PROJECTION_ID = "precision-context-v5"
MULTIHOP_COVERAGE_PROJECTION_ID = "multihop-coverage-v1"
FIXED_EVIDENCE_POLICY_ID = "fixed-evidence-v1"
ADAPTIVE_EVIDENCE_POLICY_ID = "adaptive-evidence-v1"
EVIDENCE_POLICY_IDS = (ADAPTIVE_EVIDENCE_POLICY_ID, FIXED_EVIDENCE_POLICY_ID)
ADAPTIVE_EVIDENCE_TIERS = (512, 1024, 2048)


def _encode_grouped_rows(rows: list[dict[str, Any]]) -> bytes:
    return (
        EVIDENCE_PREFIX
        + json.dumps(
            {"g": [{"r": "supplemental", "s": "grounded", "e": rows}]},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    ).encode("utf-8")


EMPTY_GROUPED_BYTES = len(_encode_grouped_rows([]))


def _encode_row(row: dict[str, Any]) -> bytes:
    return json.dumps(row, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _sentence_score_terms(weights: dict[str, float], sentence_terms: set[str], query_terms: set[str]) -> float:
    score = 0.0
    for term in sorted(query_terms & sentence_terms, key=lambda value: value.encode("utf-8")):
        score += weights.get(term, 0.0)
    return score


def _projection_term_weights(
    index: Any | None,
    sentence_rows: list[tuple[dict[str, Any], list[str], list[tuple[str, ...]]]],
    query_terms: set[str],
    term_weights: dict[str, float] | None,
    term_doc_freqs: dict[str, int] | None = None,
    document_count: int | None = None,
) -> dict[str, float]:
    if term_weights is not None and term_doc_freqs is not None:
        raise CorpusError("provide either term_weights or term_doc_freqs, not both")
    if term_doc_freqs is None and document_count is not None:
        raise CorpusError("document_count requires term_doc_freqs")
    if term_weights is not None:
        if len(term_weights) > 64:
            raise CorpusError("term_weights exceed bounded query size")
        weights = {}
        for term, weight in term_weights.items():
            if term not in query_terms or type(weight) not in {int, float} or not math.isfinite(float(weight)) or weight < 0:
                raise CorpusError("invalid query-scoped term weight")
            weights[term] = float(weight)
        return weights
    if term_doc_freqs is not None:
        if type(document_count) is not int or document_count < 1 or len(term_doc_freqs) > 64:
            raise CorpusError("invalid host document-frequency bounds")
        dfs = {}
        for term, df in term_doc_freqs.items():
            if term not in query_terms or type(df) is not int or not 1 <= df <= document_count:
                raise CorpusError("invalid query-scoped document frequency")
            dfs[term] = df
        return {
            term: math.log(1.0 + (document_count - df + 0.5) / (df + 0.5))
            for term, df in dfs.items()
        }
    if index is not None:
        from grounding_corpus import validate_index

        validate_index(index)
        n_docs = index["document_count"]
        return {
            term: math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
            for term in query_terms
            if (df := len(index["postings"].get(term, ())))
        }
    n_docs = max(1, len(sentence_rows))
    dfs = {term: 0 for term in query_terms}
    for hit, _sentences, signatures in sentence_rows:
        document_terms = set(tokenize(hit["title"]))
        for signature in signatures:
            document_terms.update(signature)
        for term in query_terms & document_terms:
            dfs[term] += 1
    return {
        term: math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
        for term, df in dfs.items()
        if df
    }


def dedupe_retrieval_hits_v1(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop byte-identical documents without fuzzy or semantic guessing."""
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


def _query_aware_exact_dedup(
    hits: list[dict[str, Any]], retrieval_query: str, *, allow_text_identity: bool = False
) -> list[dict[str, Any]]:
    """Collapse exact body mirrors only when a later title adds no queried identity."""
    if not isinstance(retrieval_query, str) or not retrieval_query.strip():
        raise CorpusError("retrieval_query must be nonempty text")
    query_terms = set(tokenize(retrieval_query))
    unique: list[dict[str, Any]] = []
    title_terms_by_body: dict[str, set[str]] = {}
    for hit in hits:
        if not isinstance(hit, dict):
            raise CorpusError("retrieval hit must be an object")
        digest = hit.get("text_sha256")
        title = hit.get("title")
        text = hit.get("text")
        if not isinstance(title, str):
            raise CorpusError("retrieval hit title is missing")
        if isinstance(digest, str) and len(digest) == 64:
            body = digest
        elif allow_text_identity and isinstance(text, str) and text:
            body = text
        else:
            raise CorpusError("retrieval hit content identity is missing")
        relevant_title_terms = set(tokenize(title)) & query_terms
        covered = title_terms_by_body.get(body)
        if covered is not None and relevant_title_terms <= covered:
            continue
        unique.append(hit)
        if covered is None:
            title_terms_by_body[body] = set(relevant_title_terms)
        else:
            covered.update(relevant_title_terms)
    return unique


def select_adaptive_evidence_budget_v1(
    hits: list[dict[str, Any]],
    retrieval_query: str,
    *,
    max_bytes: int = 2048,
) -> int:
    """Choose the smallest conservative evidence tier justified by retrieval confidence."""
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


def _adaptive_budget_sequence(selected: int, max_bytes: int) -> tuple[int, ...]:
    budgets = [selected]
    budgets.extend(tier for tier in ADAPTIVE_EVIDENCE_TIERS if selected < tier < max_bytes)
    if budgets[-1] != max_bytes:
        budgets.append(max_bytes)
    return tuple(dict.fromkeys(budgets))


def _prepare_projection_hits(
    index: Any | None,
    hits: list[dict[str, Any]],
    retrieval_query: str,
    *,
    term_weights: dict[str, float] | None = None,
    term_doc_freqs: dict[str, int] | None = None,
    document_count: int | None = None,
) -> list[tuple[dict[str, Any], list[str], list[tuple[str, ...]], list[int], tuple[str, ...]]]:
    """Pay sentence splitting/tokenization/anchor scoring once across evidence tiers."""
    if not isinstance(retrieval_query, str) or not retrieval_query.strip():
        raise CorpusError("retrieval_query must be nonempty text")
    query_terms = set(tokenize(retrieval_query))
    sentence_rows = []
    for hit in hits:
        sentences = split_sentences(hit["text"])
        if sentences:
            sentence_rows.append((hit, sentences, [tuple(tokenize(sentence)) for sentence in sentences]))
    weights = _projection_term_weights(
        index,
        sentence_rows,
        query_terms,
        term_weights,
        term_doc_freqs,
        document_count,
    )
    prepared = []
    for hit, sentences, signatures in sentence_rows:
        anchor = min(
            range(len(sentences)),
            key=lambda position: (-_sentence_score_terms(weights, set(signatures[position]), query_terms), position),
        )
        preferred = [anchor] if len(sentences) == 1 else ([0, 1] if anchor == 0 else [anchor - 1, anchor])
        title_identity = tuple(sorted(set(tokenize(hit["title"])) & query_terms, key=lambda value: value.encode("utf-8")))
        prepared.append((hit, sentences, signatures, preferred, title_identity))
    return prepared


def _project_prepared_at_budget(
    prepared_hits: list[tuple[dict[str, Any], list[str], list[tuple[str, ...]], list[int], tuple[str, ...]]],
    *,
    max_bytes: int,
    max_items: int | None,
) -> tuple[bytes | None, list[dict[str, Any]], int, int]:
    """Apply only byte/item decisions to already-scored projection candidates."""
    if type(max_bytes) is not int or max_bytes < 256:
        raise CorpusError("max_bytes must be at least 256")
    if max_items is not None and (type(max_items) is not int or max_items < 1):
        raise CorpusError("max_items must be a positive integer")

    rows: list[dict[str, Any]] = []
    emitted: list[dict[str, Any]] = []
    encoded_size = EMPTY_GROUPED_BYTES
    seen_contexts: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
    redundant_spans = 0
    anchor_fallbacks = 0

    for hit, sentences, signatures, preferred, title_identity in prepared_hits:
        if max_items is not None and len(rows) >= max_items:
            break
        nonempty_preferred = [signatures[position] for position in preferred if signatures[position]]
        if nonempty_preferred and all((signature, title_identity) in seen_contexts for signature in nonempty_preferred):
            redundant_spans += 1
            continue

        anchor = preferred[-1]
        spans = (preferred, [anchor]) if len(preferred) > 1 else (preferred,)
        accepted = None
        for positions in spans:
            snippet = " ".join(sentences[position] for position in positions)
            row = {"t": hit["title"] or hit["id"], "v": snippet}
            added_bytes = len(_encode_row(row)) + int(bool(rows))
            if encoded_size + added_bytes <= max_bytes:
                accepted = row, snippet, positions, added_bytes
                break
        if accepted is None:
            continue

        row, snippet, positions, added_bytes = accepted
        if len(preferred) > 1 and len(positions) == 1:
            anchor_fallbacks += 1
        rows.append(row)
        encoded_size += added_bytes
        emitted.append({**hit, "snippet": snippet, "sentence_positions": positions})
        seen_contexts.update((signatures[position], title_identity) for position in positions)

    if not rows:
        return None, [], redundant_spans, anchor_fallbacks
    projection = _encode_grouped_rows(rows)
    if len(projection) != encoded_size or len(projection) > max_bytes:
        raise CorpusError("precision context projection byte accounting drift")
    return projection, emitted, redundant_spans, anchor_fallbacks


def precision_context_evidence_projection_v5(
    index: Any,
    hits: list[dict[str, Any]],
    retrieval_query: str,
    *,
    max_bytes: int = 2048,
    evidence_policy: str = ADAPTIVE_EVIDENCE_POLICY_ID,
    max_items: int | None = None,
) -> tuple[bytes | None, list[dict[str, Any]], dict[str, Any]]:
    """Bounded final projector: exact dedup, directional context, fit fallback and tier promotion."""
    if evidence_policy not in EVIDENCE_POLICY_IDS:
        raise CorpusError("unsupported evidence policy")
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

    prepared_hits = _prepare_projection_hits(index, unique, retrieval_query)
    projection = None
    emitted: list[dict[str, Any]] = []
    redundant_spans = 0
    anchor_fallbacks = 0
    used_budget = budgets[0]
    for budget in budgets:
        projection, emitted, redundant_spans, anchor_fallbacks = _project_prepared_at_budget(
            prepared_hits,
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
        "initial_evidence_bytes": selected,
        "selected_evidence_bytes": used_budget,
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


def multihop_coverage_evidence_projection_v1(
    index: Any,
    hits: list[dict[str, Any]],
    retrieval_query: str,
    *,
    max_bytes: int = 2048,
    max_items: int = 12,
) -> tuple[bytes | None, list[dict[str, Any]], dict[str, Any]]:
    """Preserve ranked document coverage before spending bytes on adjacent context.

    This is a fixed workload policy for multi-hop evidence composition, not a
    per-query router. Pass one admits at most one anchor sentence from each
    distinct ranked hit. Pass two enriches already-admitted anchors with the
    same directional adjacent context used by the precision projector only
    when the remaining byte budget permits it; an admitted document is never
    evicted merely to make another snippet longer.
    """
    if type(max_bytes) is not int or max_bytes < 256:
        raise CorpusError("max_bytes must be at least 256")
    if type(max_items) is not int or not 1 <= max_items <= 16:
        raise CorpusError("max_items must be between 1 and 16")

    unique = _query_aware_exact_dedup(hits, retrieval_query)
    prepared = _prepare_projection_hits(index, unique, retrieval_query)
    rows: list[dict[str, Any]] = []
    emitted: list[dict[str, Any]] = []
    selected: list[tuple[dict[str, Any], list[str], list[tuple[str, ...]], list[int], tuple[str, ...]]] = []
    encoded_size = EMPTY_GROUPED_BYTES
    seen_contexts: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
    skipped_for_budget = 0
    redundant_spans = 0

    # Coverage pass: one answer-seeking anchor sentence per distinct ranked hit.
    for item in prepared:
        if len(rows) >= max_items:
            break
        hit, sentences, signatures, preferred, title_identity = item
        anchor = preferred[-1]
        signature = signatures[anchor]
        key = (signature, title_identity)
        if signature and key in seen_contexts:
            redundant_spans += 1
            continue
        snippet = sentences[anchor]
        row = {"t": hit["title"] or hit["id"], "v": snippet}
        added_bytes = len(_encode_row(row)) + int(bool(rows))
        if encoded_size + added_bytes > max_bytes:
            skipped_for_budget += 1
            continue
        rows.append(row)
        encoded_size += added_bytes
        emitted.append({**hit, "snippet": snippet, "sentence_positions": [anchor]})
        selected.append(item)
        if signature:
            seen_contexts.add(key)

    if not rows:
        return None, [], {
            "projection_id": MULTIHOP_COVERAGE_PROJECTION_ID,
            "max_evidence_bytes": max_bytes,
            "max_items": max_items,
            "retrieved_count": len(hits),
            "deduped_count": len(unique),
            "document_duplicate_count": len(hits) - len(unique),
            "hit_count": 0,
            "coverage_pass_hits": 0,
            "expanded_hit_count": 0,
            "skipped_for_budget": skipped_for_budget,
            "redundant_context_count": redundant_spans,
            "evidence_bytes": 0,
        }

    # Context pass: use leftover bytes to expand already-covered documents.
    expanded = 0
    for row_index, item in enumerate(selected):
        hit, sentences, _signatures, preferred, _title_identity = item
        if len(preferred) <= 1:
            continue
        candidate_snippet = " ".join(sentences[position] for position in preferred)
        if candidate_snippet == rows[row_index]["v"]:
            continue
        candidate_row = {"t": hit["title"] or hit["id"], "v": candidate_snippet}
        delta = len(_encode_row(candidate_row)) - len(_encode_row(rows[row_index]))
        if encoded_size + delta > max_bytes:
            continue
        rows[row_index] = candidate_row
        encoded_size += delta
        emitted[row_index] = {
            **emitted[row_index],
            "snippet": candidate_snippet,
            "sentence_positions": list(preferred),
        }
        expanded += 1

    projection = _encode_grouped_rows(rows)
    if len(projection) != encoded_size or len(projection) > max_bytes:
        raise CorpusError("multihop coverage projection byte accounting drift")
    return projection, emitted, {
        "projection_id": MULTIHOP_COVERAGE_PROJECTION_ID,
        "max_evidence_bytes": max_bytes,
        "max_items": max_items,
        "retrieved_count": len(hits),
        "deduped_count": len(unique),
        "document_duplicate_count": len(hits) - len(unique),
        "hit_count": len(emitted),
        "coverage_pass_hits": len(emitted),
        "expanded_hit_count": expanded,
        "skipped_for_budget": skipped_for_budget,
        "redundant_context_count": redundant_spans,
        "evidence_bytes": len(projection),
    }


def precision_ranked_evidence_tiers_v1(
    hits: list[dict[str, Any]],
    retrieval_query: str,
    *,
    tiers: tuple[int, ...] = (2048, 1024, 512),
    max_items: int = 8,
    term_weights: dict[str, float] | None = None,
    term_doc_freqs: dict[str, int] | None = None,
    document_count: int | None = None,
) -> tuple[tuple[bytes | None, list[dict[str, Any]], dict[str, Any]], ...]:
    """Project bounded host-ranked hits without owning the host retrieval index."""
    if not isinstance(hits, list) or not 1 <= len(hits) <= 16:
        raise CorpusError("host-ranked hits must contain between 1 and 16 entries")
    if (
        not isinstance(tiers, tuple)
        or not tiers
        or len(tiers) > 4
        or any(type(value) is not int or value < 256 for value in tiers)
        or any(left <= right for left, right in zip(tiers, tiers[1:]))
    ):
        raise CorpusError("evidence tiers must be 1-4 strictly descending byte budgets")
    if type(max_items) is not int or not 1 <= max_items <= 16:
        raise CorpusError("max_items must be between 1 and 16")
    for hit in hits:
        if not isinstance(hit, dict):
            raise CorpusError("host-ranked hit must be an object")
        if not isinstance(hit.get("id"), str) or not hit["id"].strip():
            raise CorpusError("host-ranked hit id must be nonempty text")
        if not isinstance(hit.get("title"), str) or not isinstance(hit.get("text"), str) or not hit["text"].strip():
            raise CorpusError("host-ranked hit title/text is invalid")
        if len(hit["text"].encode("utf-8")) > 32 * 1024:
            raise CorpusError("host-ranked hit text exceeds bounded size")

    unique = _query_aware_exact_dedup(hits, retrieval_query, allow_text_identity=True)
    prepared = _prepare_projection_hits(
        None,
        unique,
        retrieval_query,
        term_weights=term_weights,
        term_doc_freqs=term_doc_freqs,
        document_count=document_count,
    )
    duplicates = len(hits) - len(unique)
    result = []
    for budget in tiers:
        projection, emitted, redundant, fallbacks = _project_prepared_at_budget(
            prepared, max_bytes=budget, max_items=max_items
        )
        result.append((projection, emitted, {
            "projection_id": PRECISION_CONTEXT_PROJECTION_ID,
            "weight_source": "host-term-weights" if term_weights is not None else "candidate-local-idf",
            "max_evidence_bytes": budget,
            "retrieved_count": len(hits),
            "deduped_count": len(unique),
            "document_duplicate_count": duplicates,
            "redundant_context_count": redundant,
            "anchor_fallback_count": fallbacks,
            "hit_count": len(emitted),
            "evidence_bytes": len(projection) if projection is not None else 0,
        }))
    return tuple(result)


def precision_ranked_evidence_fit_v1(
    hits: list[dict[str, Any]],
    retrieval_query: str,
    fits: Callable[[bytes, list[dict[str, Any]], dict[str, Any]], bool],
    *,
    tiers: tuple[int, ...] = (2048, 1024, 512),
    max_items: int = 8,
    term_weights: dict[str, float] | None = None,
) -> tuple[bytes | None, list[dict[str, Any]], dict[str, Any]]:
    """Choose the first complete projection the host reports can fit its real context."""
    if not callable(fits):
        raise CorpusError("host context-fit callback must be callable")
    attempts = 0
    for payload, emitted, meta in precision_ranked_evidence_tiers_v1(
        hits,
        retrieval_query,
        tiers=tiers,
        max_items=max_items,
        term_weights=term_weights,
    ):
        if payload is None:
            continue
        attempts += 1
        try:
            accepted = fits(payload, emitted, meta)
        except Exception as exc:
            raise CorpusError(f"host context-fit callback failed: {exc}") from exc
        if type(accepted) is not bool:
            raise CorpusError("host context-fit callback must return bool")
        if accepted:
            return payload, emitted, {**meta, "fit_attempts": attempts}
    return None, [], {"fit_attempts": attempts, "fit_failed": True}
