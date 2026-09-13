"""Tests for detached v1.1 amplifier projection materials."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools")]

from grounding_corpus import CorpusError, build_index, search
from grounding_projection import precision_context_evidence_projection_v5
from grounding_projection_experiments import (
    GLOBAL_SNIPPET_PROJECTION_ID,
    HEAD_PRESERVING_GLOBAL_SNIPPET_PROJECTION_ID,
    global_snippet_evidence_projection_v1,
    head_preserving_global_snippet_projection_v2,
)


class GroundingProjectionExperimentTests(unittest.TestCase):
    def phase_transition_documents(self):
        return [
            {
                "id": "decoy",
                "title": "Rover filter",
                "text": "Rover rover rover rover filter filter filter calibration calibration background.",
            },
            {
                "id": "target",
                "title": "Service note",
                "text": ("filler " * 180) + ". Rover filter calibration code is RM-F42.",
            },
        ]

    def test_global_snippet_projection_is_deterministic_and_compiled_parity_safe(self):
        raw = build_index(self.phase_transition_documents())
        compiled = build_index(self.phase_transition_documents(), compiled=True)
        query = "rover filter calibration code"
        raw_hits = search(raw, query, top_k=2)
        compiled_hits = search(compiled, query, top_k=2)
        first = global_snippet_evidence_projection_v1(raw, raw_hits, query, max_bytes=2048, max_items=1)
        second = global_snippet_evidence_projection_v1(raw, raw_hits, query, max_bytes=2048, max_items=1)
        compiled_result = global_snippet_evidence_projection_v1(
            compiled, compiled_hits, query, max_bytes=2048, max_items=1
        )
        self.assertEqual(first, second)
        self.assertEqual(first, compiled_result)
        self.assertEqual(first[2]["projection_id"], GLOBAL_SNIPPET_PROJECTION_ID)
        self.assertEqual(first[2]["material_id"], "C")
        self.assertGreater(first[2]["global_reordered_count"], 0)

    def test_material_b_plus_c_exposes_candidate_that_neither_control_path_selects(self):
        corpus = build_index(self.phase_transition_documents())
        query = "rover filter calibration code"

        # Without B (overfetch), C has no second candidate to rescue.
        one_hit = search(corpus, query, top_k=1)
        one_projection, one_emitted, _ = global_snippet_evidence_projection_v1(
            corpus, one_hit, query, max_bytes=2048, max_items=1
        )
        self.assertIsNotNone(one_projection)
        self.assertEqual([hit["id"] for hit in one_emitted], ["decoy"])
        self.assertNotIn(b"RM-F42", one_projection)

        # B alone still feeds v5 in retrieval order, so the final one-item budget
        # remains occupied by the high-BM25 decoy.
        two_hits = search(corpus, query, top_k=2)
        current_projection, current_emitted, _ = precision_context_evidence_projection_v5(
            corpus, two_hits, query, max_bytes=2048, max_items=1
        )
        self.assertIsNotNone(current_projection)
        self.assertEqual([hit["id"] for hit in current_emitted], ["decoy"])
        self.assertNotIn(b"RM-F42", current_projection)

        # B+C lets the overfetched candidate compete at the complete-snippet level.
        candidate_projection, candidate_emitted, meta = global_snippet_evidence_projection_v1(
            corpus, two_hits, query, max_bytes=2048, max_items=1
        )
        self.assertIsNotNone(candidate_projection)
        self.assertEqual([hit["id"] for hit in candidate_emitted], ["target"])
        self.assertIn(b"RM-F42", candidate_projection)
        self.assertEqual(meta["retrieved_count"], 2)
        self.assertEqual(meta["hit_count"], 1)
        self.assertGreater(meta["global_reordered_count"], 0)

    def test_head_preserving_c2_keeps_control_head_and_promotes_useful_overfetch_tail(self):
        documents = [
            {
                "id": f"decoy-{index}",
                "title": f"Rover note {index}",
                "text": (
                    f"Rover rover rover filter filter calibration background unique{index}. "
                    f"Generic code note unique{index}."
                ),
            }
            for index in range(8)
        ] + [
            {
                "id": "target",
                "title": "Service note",
                "text": ("filler " * 180) + ". Rover filter calibration code is RM-F42.",
            }
        ]
        corpus = build_index(documents)
        query = "rover filter calibration code"
        hits = search(corpus, query, top_k=9)
        self.assertEqual([hit["id"] for hit in hits[:4]], [f"decoy-{index}" for index in range(4)])
        self.assertEqual(hits[-1]["id"], "target")

        current_projection, current_emitted, _ = precision_context_evidence_projection_v5(
            corpus, hits, query, max_bytes=2048, max_items=8
        )
        candidate_projection, candidate_emitted, meta = head_preserving_global_snippet_projection_v2(
            corpus, hits, query, max_bytes=2048, max_items=8, protected_head=4
        )
        self.assertIsNotNone(current_projection)
        self.assertIsNotNone(candidate_projection)
        self.assertNotIn(b"RM-F42", current_projection)
        self.assertIn(b"RM-F42", candidate_projection)
        self.assertEqual(
            [hit["id"] for hit in candidate_emitted[:4]],
            [f"decoy-{index}" for index in range(4)],
        )
        self.assertIn("target", {hit["id"] for hit in candidate_emitted})
        self.assertEqual(meta["projection_id"], HEAD_PRESERVING_GLOBAL_SNIPPET_PROJECTION_ID)
        self.assertEqual(meta["candidate_revision"], 2)
        self.assertEqual(meta["protected_head_count"], 4)
        self.assertGreater(meta["tail_reordered_count"], 0)

    def test_global_snippet_projection_validates_experiment_boundaries(self):
        corpus = build_index(self.phase_transition_documents())
        hits = search(corpus, "rover filter", top_k=2)
        for query in ("", "   "):
            with self.subTest(query=query), self.assertRaises(CorpusError):
                global_snippet_evidence_projection_v1(corpus, hits, query)
        for max_items in (0, True, 1.5):
            with self.subTest(max_items=max_items), self.assertRaises(CorpusError):
                global_snippet_evidence_projection_v1(
                    corpus, hits, "rover filter", max_items=max_items
                )


if __name__ == "__main__":
    unittest.main()
