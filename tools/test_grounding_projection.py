"""Tests for deterministic local-corpus evidence projection."""
from __future__ import annotations

from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools")]

from grounding_corpus import CorpusError, build_index, search
import grounding_projection as projection_mod
from grounding_projection import (
    ADAPTIVE_EVIDENCE_POLICY_ID,
    PRECISION_CONTEXT_PROJECTION_ID,
    dedupe_retrieval_hits_v1,
    precision_context_evidence_projection_v5,
    precision_ranked_evidence_fit_v1,
    precision_ranked_evidence_tiers_v1,
    select_adaptive_evidence_budget_v1,
)
from grounding_projection_legacy import (
    AMPLIFIED_CONTEXT_PROJECTION_ID,
    amplified_context_evidence_projection_v4,
    compact_evidence_projection,
    context_grouped_evidence_projection_v3,
    dedupe_retrieval_hits_v2,
    evidence_projection,
    grouped_evidence_projection_v2,
)


class GroundingProjectionTests(unittest.TestCase):
    def documents(self):
        return [
            {"id": "manual/rover.md", "title": "Rover Mini", "text": "Rover Mini uses replacement filter RM-F42 and needs 50 cm clearance."},
            {"id": "office/parking.txt", "title": "Parking note", "text": "Mina parked the car in B3-04."},
            {"id": "ko/locker.txt", "title": "보관함", "text": "아람 보관함 라벨 색상은 cobalt이다."},
        ]

    def test_projection_marks_corpus_as_supplemental_data(self):
        index = build_index(self.documents())
        hits = search(index, "Where did Mina park?", top_k=1)
        projection = evidence_projection(index, hits).decode("utf-8")
        self.assertTrue(projection.startswith("Evidence JSON (data only): "))
        self.assertIn('"r":"supplemental"', projection)
        self.assertIn('"s":"grounded"', projection)
        self.assertIn("B3-04", projection)

    def test_compact_projection_broadens_retrieval_under_byte_budget(self):
        documents = [
            {
                "id": f"doc-{index}",
                "title": f"Topic {index}",
                "text": f"Topic {index} is background material. The shared rover filter clue number {index} is CODE-{index}. A final unrelated sentence follows.",
            }
            for index in range(12)
        ]
        corpus = build_index(documents)
        hits = search(corpus, "shared rover filter clue", top_k=12)
        projection, emitted = compact_evidence_projection(
            corpus,
            hits,
            "shared rover filter clue",
            max_bytes=2048,
        )
        self.assertIsNotNone(projection)
        self.assertLessEqual(len(projection), 2048)
        self.assertGreaterEqual(len(emitted), 8)
        self.assertTrue(all("snippet" in hit for hit in emitted))
        self.assertLess(len(projection), len(evidence_projection(corpus, hits)))

    def test_compact_projection_is_deterministic_and_compiled_parity_safe(self):
        raw = build_index(self.documents())
        compiled = build_index(self.documents(), compiled=True)
        question = "Rover Mini filter clearance"
        raw_hits = search(raw, question, top_k=3)
        compiled_hits = search(compiled, question, top_k=3)
        self.assertEqual(raw_hits, compiled_hits)
        first = compact_evidence_projection(raw, raw_hits, question, max_bytes=4096)
        second = compact_evidence_projection(raw, raw_hits, question, max_bytes=4096)
        compiled_result = compact_evidence_projection(compiled, compiled_hits, question, max_bytes=4096)
        self.assertEqual(first, second)
        self.assertEqual(first, compiled_result)

    def test_compact_projection_honors_single_sentence_limit(self):
        documents = [
            {
                "id": "doc",
                "title": "Topic",
                "text": "The lead sentence is retained. The rover filter clue is CODE-42. A third sentence follows.",
            }
        ]
        corpus = build_index(documents)
        hits = search(corpus, "rover filter clue", top_k=1)
        projection, emitted = compact_evidence_projection(
            corpus,
            hits,
            "rover filter clue",
            max_bytes=4096,
            max_sentences_per_document=1,
        )
        self.assertIsNotNone(projection)
        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0]["snippet"], "The lead sentence is retained.")
        self.assertNotIn(b"CODE-42", projection)

    def test_grouped_v2_preserves_hit_order_and_removes_repeated_metadata(self):
        documents = [
            {
                "id": f"doc-{index}",
                "title": f"Topic {index}",
                "text": f"Topic {index} is background material. The shared rover clue {index} is CODE-{index}.",
            }
            for index in range(12)
        ]
        corpus = build_index(documents)
        hits = search(corpus, "shared rover clue", top_k=12)
        legacy, legacy_emitted = compact_evidence_projection(corpus, hits, "shared rover clue", max_bytes=4096)
        grouped, grouped_emitted = grouped_evidence_projection_v2(corpus, hits, "shared rover clue", max_bytes=4096)
        self.assertIsNotNone(legacy)
        self.assertIsNotNone(grouped)
        self.assertEqual([hit["id"] for hit in legacy_emitted], [hit["id"] for hit in grouped_emitted])
        self.assertLess(len(grouped), len(legacy))
        payload = json.loads(grouped.decode("utf-8").split(": ", 1)[1])
        self.assertEqual(len(payload["g"]), 1)
        group = payload["g"][0]
        self.assertEqual((group["r"], group["s"]), ("supplemental", "grounded"))
        self.assertTrue(all(set(row) == {"t", "v"} for row in group["e"]))

    def test_grouped_v2_is_deterministic_and_compiled_parity_safe(self):
        raw = build_index(self.documents())
        compiled = build_index(self.documents(), compiled=True)
        retrieval_query = "Rover Mini filter clearance"
        raw_hits = search(raw, retrieval_query, top_k=3)
        compiled_hits = search(compiled, retrieval_query, top_k=3)
        first = grouped_evidence_projection_v2(raw, raw_hits, retrieval_query, max_bytes=4096)
        second = grouped_evidence_projection_v2(raw, raw_hits, retrieval_query, max_bytes=4096)
        compiled_result = grouped_evidence_projection_v2(compiled, compiled_hits, retrieval_query, max_bytes=4096)
        self.assertEqual(first, second)
        self.assertEqual(first, compiled_result)

    def test_grouped_v2_requires_explicit_nonempty_retrieval_query(self):
        corpus = build_index(self.documents())
        hits = search(corpus, "Rover Mini", top_k=3)
        for query in ("", "   "):
            with self.subTest(query=query), self.assertRaises(CorpusError):
                grouped_evidence_projection_v2(corpus, hits, query, max_bytes=4096)

    def test_context_grouped_v3_preserves_predecessor_and_anchor_as_contiguous_span(self):
        corpus = build_index([
            {
                "id": "manual/device",
                "title": "Mounting guide",
                "text": (
                    "Wall-mounted mode disables the general clearance rule. "
                    "The standard device requires 17 cm of clear space. "
                    "A later unrelated sentence mentions 99 cm."
                ),
            }
        ])
        hits = search(corpus, "standard device clearance 17 cm", top_k=1)
        projection, emitted = context_grouped_evidence_projection_v3(
            corpus,
            hits,
            "standard device clearance 17 cm",
            max_bytes=2048,
        )
        self.assertIsNotNone(projection)
        self.assertEqual(emitted[0]["sentence_positions"], [0, 1])
        self.assertIn("Wall-mounted mode disables", emitted[0]["snippet"])
        self.assertIn("17 cm", emitted[0]["snippet"])
        self.assertNotIn("99 cm", emitted[0]["snippet"])
        self.assertLessEqual(len(projection), 2048)

    def test_context_grouped_v3_is_deterministic_and_compiled_parity_safe(self):
        raw = build_index(self.documents())
        compiled = build_index(self.documents(), compiled=True)
        query = "Rover Mini replacement filter"
        raw_hits = search(raw, query, top_k=3)
        compiled_hits = search(compiled, query, top_k=3)
        first = context_grouped_evidence_projection_v3(raw, raw_hits, query, max_bytes=2048)
        second = context_grouped_evidence_projection_v3(raw, raw_hits, query, max_bytes=2048)
        compiled_result = context_grouped_evidence_projection_v3(compiled, compiled_hits, query, max_bytes=2048)
        self.assertEqual(first, second)
        self.assertEqual(first, compiled_result)

    def test_adaptive_budget_uses_small_tiers_only_for_clear_retrieval(self):
        high = [
            {"score": 3.0, "matched_query_terms": 3},
            {"score": 1.0, "matched_query_terms": 1},
        ]
        medium = [
            {"score": 2.0, "matched_query_terms": 2},
            {"score": 1.5, "matched_query_terms": 1},
        ]
        ambiguous = [
            {"score": 2.0, "matched_query_terms": 2},
            {"score": 1.9, "matched_query_terms": 2},
        ]
        query = "rover filter code"
        self.assertEqual(select_adaptive_evidence_budget_v1(high, query), 512)
        self.assertEqual(select_adaptive_evidence_budget_v1(medium, query), 1024)
        self.assertEqual(select_adaptive_evidence_budget_v1(ambiguous, query), 2048)
        self.assertEqual(select_adaptive_evidence_budget_v1(high, query, max_bytes=768), 512)

    def test_amplified_projection_dedupes_exact_text_without_semantic_guessing(self):
        corpus = build_index([
            {"id": "a", "title": "Rover manual", "text": "Rover filter code is RM-F42. Keep this source sentence."},
            {"id": "b", "title": "Mirrored manual", "text": "Rover filter code is RM-F42. Keep this source sentence."},
            {"id": "c", "title": "Distinct", "text": "Rover filter maintenance happens annually."},
        ])
        query = "rover filter code"
        hits = search(corpus, query, top_k=3)
        unique = dedupe_retrieval_hits_v1(hits)
        self.assertEqual(len(hits), 3)
        self.assertEqual(len(unique), 2)
        projection, emitted, meta = amplified_context_evidence_projection_v4(
            corpus, hits, query, max_bytes=2048, evidence_policy=ADAPTIVE_EVIDENCE_POLICY_ID
        )
        self.assertIsNotNone(projection)
        self.assertEqual(meta["projection_id"], AMPLIFIED_CONTEXT_PROJECTION_ID)
        self.assertEqual(meta["document_duplicate_count"], 1)
        self.assertEqual(meta["redundant_context_count"], 0)
        self.assertEqual(meta["duplicate_count"], 1)
        self.assertEqual(meta["deduped_count"], 2)
        self.assertEqual(meta["hit_count"], len(emitted))
        self.assertLessEqual(len(projection), meta["selected_evidence_bytes"])
        self.assertLessEqual(meta["selected_evidence_bytes"], 2048)

    def test_query_aware_exact_dedup_preserves_title_identity_named_by_question(self):
        corpus = build_index([
            {"id": "alpha", "title": "Alpha", "text": "Warranty period is 24 months."},
            {"id": "beta", "title": "Beta", "text": "Warranty period is 24 months."},
            {"id": "mirror", "title": "Mirror copy", "text": "Warranty period is 24 months."},
        ])
        query = "compare alpha beta warranty"
        hits = search(corpus, query, top_k=3)
        unique = dedupe_retrieval_hits_v2(hits, query)
        self.assertEqual({hit["id"] for hit in unique}, {"alpha", "beta"})

    def test_amplified_projection_skips_repeated_context_span_and_keeps_later_unique_evidence(self):
        corpus = build_index([
            {"id": "a", "title": "Primary", "text": "Rover filter code is RM-F42. Service interval is 12 months."},
            {"id": "b", "title": "Mirror", "text": "ROVER FILTER CODE IS RM F42! Service interval is 12 months."},
            {"id": "c", "title": "Clearance", "text": "Rover filter clearance is 17 cm."},
        ])
        query = "rover filter code service interval"
        hits = search(corpus, query, top_k=3)
        projection, emitted, meta = amplified_context_evidence_projection_v4(
            corpus,
            hits,
            query,
            max_bytes=2048,
            evidence_policy=ADAPTIVE_EVIDENCE_POLICY_ID,
            max_items=2,
        )
        self.assertIsNotNone(projection)
        self.assertLessEqual(len(emitted), 2)
        self.assertIn("c", {hit["id"] for hit in emitted})
        self.assertGreaterEqual(meta["redundant_context_count"], 1)

    def test_precision_v5_preserves_query_named_title_identity_across_exact_body_and_span_dedup(self):
        corpus = build_index([
            {"id": "alpha", "title": "Alpha", "text": "Warranty period is 24 months."},
            {"id": "beta", "title": "Beta", "text": "Warranty period is 24 months."},
            {"id": "mirror", "title": "Mirror copy", "text": "Warranty period is 24 months."},
        ])
        query = "compare alpha beta warranty"
        hits = search(corpus, query, top_k=3)
        projection, emitted, meta = precision_context_evidence_projection_v5(
            corpus, hits, query, max_bytes=2048, max_items=3
        )
        self.assertIsNotNone(projection)
        self.assertEqual({hit["id"] for hit in emitted}, {"alpha", "beta"})
        self.assertEqual(meta["document_duplicate_count"], 1)
        self.assertEqual(meta["redundant_context_count"], 0)

    def test_precision_v5_prepares_sentences_once_across_adaptive_tier_promotion(self):
        corpus = build_index([
            {
                "id": "large-anchor",
                "title": "Rover",
                "text": "Rover " + ("x" * 650) + ".",
            }
        ])
        query = "rover"
        hits = search(corpus, query, top_k=1)
        with patch.object(projection_mod, "split_sentences", wraps=projection_mod.split_sentences) as splitter:
            projection, emitted, meta = precision_context_evidence_projection_v5(
                corpus, hits, query, max_bytes=2048, max_items=1
            )
        self.assertIsNotNone(projection)
        self.assertEqual(len(emitted), 1)
        self.assertGreater(meta["tier_promotions"], 0)
        self.assertEqual(splitter.call_count, 1)

    def test_precision_v5_serializes_grouped_projection_once_after_incremental_byte_accounting(self):
        corpus = build_index([
            {"id": "a", "title": "Alpha", "text": "Rover filter code is RM-F42."},
            {"id": "b", "title": "Beta", "text": "Rover service interval is 12 months."},
            {"id": "c", "title": "Gamma", "text": "Rover clearance is 17 cm."},
        ])
        query = "rover filter service clearance"
        hits = search(corpus, query, top_k=3)
        with patch.object(projection_mod, "_encode_grouped_rows", wraps=projection_mod._encode_grouped_rows) as encoder:
            projection, emitted, _meta = precision_context_evidence_projection_v5(
                corpus, hits, query, max_bytes=2048, max_items=3
            )
        self.assertIsNotNone(projection)
        self.assertEqual(len(emitted), 3)
        self.assertEqual(encoder.call_count, 1)

    def test_precision_v5_first_sentence_anchor_keeps_successor_context(self):
        corpus = build_index([
            {
                "id": "rover",
                "title": "Rover",
                "text": "Rover filter overview. It uses replacement filter RM-F42.",
            }
        ])
        query = "rover filter overview"
        hits = search(corpus, query, top_k=1)
        projection, emitted, meta = precision_context_evidence_projection_v5(
            corpus, hits, query, max_bytes=2048
        )
        self.assertIsNotNone(projection)
        self.assertEqual(meta["projection_id"], PRECISION_CONTEXT_PROJECTION_ID)
        self.assertEqual(emitted[0]["sentence_positions"], [0, 1])
        self.assertIn("RM-F42", emitted[0]["snippet"])
        self.assertLessEqual(len(projection), meta["selected_evidence_bytes"])

    def test_precision_v5_falls_back_to_complete_anchor_before_spending_more_budget(self):
        long_background = "Background " + ("padding " * 90) + "."
        corpus = build_index([
            {
                "id": "rover",
                "title": "Rover",
                "text": long_background + " Rover filter code is RM-F42.",
            }
        ])
        query = "rover filter code"
        hits = search(corpus, query, top_k=1)
        projection, emitted, meta = precision_context_evidence_projection_v5(
            corpus, hits, query, max_bytes=2048
        )
        self.assertIsNotNone(projection)
        self.assertEqual(meta["initial_evidence_bytes"], 512)
        self.assertEqual(meta["selected_evidence_bytes"], 512)
        self.assertEqual(meta["tier_promotions"], 0)
        self.assertEqual(meta["anchor_fallback_count"], 1)
        self.assertEqual(emitted[0]["sentence_positions"], [1])
        self.assertIn("RM-F42", emitted[0]["snippet"])
        self.assertNotIn("padding padding", emitted[0]["snippet"])

    def test_precision_v5_promotes_tier_only_when_top_complete_evidence_cannot_fit(self):
        large_anchor = "Rover calibration payload " + ("detail " * 75) + "."
        corpus = build_index([
            {"id": "payload", "title": "Payload", "text": large_anchor}
        ])
        query = "rover calibration payload"
        hits = search(corpus, query, top_k=1)
        projection, emitted, meta = precision_context_evidence_projection_v5(
            corpus, hits, query, max_bytes=2048
        )
        self.assertIsNotNone(projection)
        self.assertEqual(meta["initial_evidence_bytes"], 512)
        self.assertEqual(meta["selected_evidence_bytes"], 1024)
        self.assertEqual(meta["tier_promotions"], 1)
        self.assertEqual(emitted[0]["sentence_positions"], [0])
        self.assertLessEqual(len(projection), 1024)

    def test_precision_v5_is_deterministic_and_compiled_parity_safe(self):
        raw = build_index(self.documents())
        compiled = build_index(self.documents(), compiled=True)
        query = "Rover Mini replacement filter"
        raw_hits = search(raw, query, top_k=3)
        compiled_hits = search(compiled, query, top_k=3)
        first = precision_context_evidence_projection_v5(raw, raw_hits, query, max_bytes=2048)
        second = precision_context_evidence_projection_v5(raw, raw_hits, query, max_bytes=2048)
        compiled_result = precision_context_evidence_projection_v5(
            compiled, compiled_hits, query, max_bytes=2048
        )
        self.assertEqual(first, second)
        self.assertEqual(first, compiled_result)
        self.assertLessEqual(len(first[0]), 2048)

    def test_ranked_tiers_reuse_host_weights_without_index_or_digest(self):
        corpus = build_index(self.documents())
        query = "Rover Mini replacement filter"
        hits = search(corpus, query, top_k=3)
        query_terms = set(projection_mod.tokenize(query))
        weights = projection_mod._projection_term_weights(corpus, [], query_terms, None)
        host_hits = [{key: value for key, value in hit.items() if key != "text_sha256"} for hit in hits]
        full, full_emitted, _meta = precision_context_evidence_projection_v5(
            corpus,
            hits,
            query,
            max_bytes=2048,
            evidence_policy=projection_mod.FIXED_EVIDENCE_POLICY_ID,
            max_items=8,
        )
        ranked, ranked_emitted, ranked_meta = precision_ranked_evidence_tiers_v1(
            host_hits,
            query,
            tiers=(2048,),
            max_items=8,
            term_weights=weights,
        )[0]
        self.assertEqual(ranked, full)
        self.assertEqual(
            [(hit["id"], hit["snippet"], hit["sentence_positions"]) for hit in ranked_emitted],
            [(hit["id"], hit["snippet"], hit["sentence_positions"]) for hit in full_emitted],
        )
        self.assertEqual(ranked_meta["evidence_bytes"], len(ranked))

    def test_ranked_tiers_candidate_local_fallback_is_deterministic(self):
        hits = [
            {"id": "a", "title": "Desk", "text": "Common office note. The help desk is in Room 12."},
            {"id": "b", "title": "Office", "text": "Common office note. General visitor information."},
        ]
        first = precision_ranked_evidence_tiers_v1(hits, "help desk office", tiers=(1024, 512))
        second = precision_ranked_evidence_tiers_v1(hits, "help desk office", tiers=(1024, 512))
        self.assertEqual(first, second)
        self.assertIn("Room 12", first[0][1][0]["snippet"])

    def test_ranked_tiers_reject_unbounded_host_input(self):
        base = {"id": "a", "title": "T", "text": "text"}
        with self.assertRaises(CorpusError):
            precision_ranked_evidence_tiers_v1([], "query")
        with self.assertRaises(CorpusError):
            precision_ranked_evidence_tiers_v1([dict(base, id=str(index)) for index in range(17)], "query")
        with self.assertRaises(CorpusError):
            precision_ranked_evidence_tiers_v1([dict(base, text="x" * (32 * 1024 + 1))], "query")
        with self.assertRaises(CorpusError):
            precision_ranked_evidence_tiers_v1([base], "query", tiers=(512, 1024))
        with self.assertRaises(CorpusError):
            precision_ranked_evidence_tiers_v1([base], "query", term_weights={"other": 1.0})

    def test_ranked_fit_stops_at_first_complete_host_fit(self):
        hits = [{
            "id": "a",
            "title": "Rover",
            "text": "Background " + ("padding " * 90) + ". Rover filter code is RM-F42.",
        }]
        attempts = []

        def fits(payload, emitted, meta):
            attempts.append((meta["max_evidence_bytes"], len(payload), emitted[0]["id"]))
            return meta["max_evidence_bytes"] <= 1024

        payload, emitted, meta = precision_ranked_evidence_fit_v1(
            hits,
            "rover filter code",
            fits,
            tiers=(2048, 1024, 512),
            max_items=1,
            term_weights={"rover": 1.0, "filter": 1.0, "code": 1.0},
        )
        self.assertIsNotNone(payload)
        self.assertEqual([row[0] for row in attempts], [2048, 1024])
        self.assertEqual(meta["max_evidence_bytes"], 1024)
        self.assertEqual(meta["fit_attempts"], 2)
        self.assertEqual(emitted[0]["id"], "a")
        self.assertIn(b"RM-F42", payload)

    def test_ranked_fit_fails_closed_on_invalid_host_result(self):
        hits = [{"id": "a", "title": "Rover", "text": "Rover filter code is RM-F42."}]
        with self.assertRaises(CorpusError):
            precision_ranked_evidence_fit_v1(hits, "rover filter", lambda *_args: 1)
        with self.assertRaises(CorpusError):
            precision_ranked_evidence_fit_v1(hits, "rover filter", lambda *_args: (_ for _ in ()).throw(RuntimeError("boom")))

    def test_compact_projection_validates_limits(self):
        corpus = build_index(self.documents())
        hits = search(corpus, "Rover Mini", top_k=3)
        for budget in (255, True, 512.0):
            with self.subTest(budget=budget), self.assertRaises(CorpusError):
                compact_evidence_projection(corpus, hits, "Rover Mini", max_bytes=budget)
        for limit in (0, 5, True, 2.0):
            with self.subTest(limit=limit), self.assertRaises(CorpusError):
                compact_evidence_projection(
                    corpus,
                    hits,
                    "Rover Mini",
                    max_bytes=4096,
                    max_sentences_per_document=limit,
                )


if __name__ == "__main__":
    unittest.main()
