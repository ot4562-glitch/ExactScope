"""Tests for deterministic local-corpus evidence projection."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools")]

from grounding_corpus import CorpusError, build_index, search
from grounding_projection import compact_evidence_projection, evidence_projection


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
