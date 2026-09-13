"""Focused tests for the fixed multi-hop coverage projection."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools")]

from grounding_corpus import CorpusError, build_index, search
from grounding_projection import (
    MULTIHOP_COVERAGE_PROJECTION_ID,
    multihop_coverage_evidence_projection_v1,
    precision_context_evidence_projection_v5,
)


class MultiHopCoverageProjectionTests(unittest.TestCase):
    def _corpus(self):
        documents = []
        for index in range(12):
            documents.append({
                "id": f"doc-{index}",
                "title": f"Bridge Topic {index}",
                "text": (
                    f"Bridge Topic {index} has background context about the shared expedition. "
                    f"The shared expedition clue for stage {index} is TOKEN-{index}. "
                    "A trailing sentence contains unrelated filler."
                ),
            })
        return build_index(documents)

    def test_preserves_ranked_document_coverage_before_adjacent_context(self):
        corpus = self._corpus()
        query = "shared expedition clue stage"
        hits = search(corpus, query, top_k=12)
        payload, emitted, meta = multihop_coverage_evidence_projection_v1(
            corpus, hits, query, max_bytes=2048, max_items=12
        )
        self.assertIsNotNone(payload)
        self.assertEqual(meta["projection_id"], MULTIHOP_COVERAGE_PROJECTION_ID)
        self.assertEqual(meta["coverage_pass_hits"], len(emitted))
        self.assertGreaterEqual(len(emitted), 8)
        self.assertEqual(len({row["title"] for row in emitted}), len(emitted))
        self.assertLessEqual(len(payload), 2048)

    def test_same_budget_keeps_at_least_as_many_titles_as_precision_projection(self):
        corpus = self._corpus()
        query = "shared expedition clue stage"
        hits = search(corpus, query, top_k=12)
        precision_payload, precision_emitted, _ = precision_context_evidence_projection_v5(
            corpus, hits, query, max_bytes=2048, max_items=8
        )
        coverage_payload, coverage_emitted, _ = multihop_coverage_evidence_projection_v1(
            corpus, hits, query, max_bytes=2048, max_items=12
        )
        self.assertIsNotNone(precision_payload)
        self.assertIsNotNone(coverage_payload)
        self.assertGreaterEqual(len(coverage_emitted), len(precision_emitted))
        self.assertLessEqual(len(coverage_payload), 2048)

    def test_is_deterministic_and_compiled_index_safe(self):
        documents = [
            {"id": "a", "title": "Alpha", "text": "Alpha links the rover to Mina. The rover token is RM-42."},
            {"id": "b", "title": "Beta", "text": "Beta links Mina to Seoul. Mina arrived in Seoul."},
            {"id": "c", "title": "Gamma", "text": "Gamma is unrelated background."},
        ]
        raw = build_index(documents)
        compiled = build_index(documents, compiled=True)
        query = "rover Mina Seoul link"
        first = multihop_coverage_evidence_projection_v1(raw, search(raw, query, top_k=3), query)
        second = multihop_coverage_evidence_projection_v1(raw, search(raw, query, top_k=3), query)
        compiled_result = multihop_coverage_evidence_projection_v1(
            compiled, search(compiled, query, top_k=3), query
        )
        self.assertEqual(first, second)
        self.assertEqual(first, compiled_result)

    def test_rejects_invalid_bounds(self):
        corpus = self._corpus()
        hits = search(corpus, "shared expedition", top_k=3)
        with self.assertRaises(CorpusError):
            multihop_coverage_evidence_projection_v1(corpus, hits, "shared expedition", max_bytes=255)
        with self.assertRaises(CorpusError):
            multihop_coverage_evidence_projection_v1(corpus, hits, "shared expedition", max_items=17)


if __name__ == "__main__":
    unittest.main()
