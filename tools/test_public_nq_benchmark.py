"""Focused tests for the NQ mirror development harness."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "benchmarks")]

from public_nq_candidate import chunk_document, score_normalize
import public_nq_benchmark as nq
from public_nq_benchmark import _contains_alias, _f1, _reconstruct_documents


class PublicNQBenchmarkTests(unittest.TestCase):
    def test_public_product_contract_is_precision_3k_cap8(self):
        self.assertEqual(nq.PRECISION_CONTEXT_PROJECTION_ID, "precision-context-v5")
        self.assertEqual(nq.DEFAULT_TOP_K, 12)
        self.assertEqual(nq.DEFAULT_MAX_EVIDENCE_BYTES, 3072)
        self.assertEqual(nq.PRODUCT_MODEL_ITEM_CAP, 8)

        with tempfile.TemporaryDirectory() as directory:
            args = SimpleNamespace(
                output=Path(directory) / "run",
                top_k=nq.DEFAULT_TOP_K,
                max_evidence_bytes=2048,
            )
            with self.assertRaisesRegex(nq.NQBenchmarkError, "product cap 3072"):
                nq.run_screen(args)

    def test_scoring_uses_normalized_alias_max(self):
        self.assertEqual(score_normalize("The Moon!"), "moon")
        self.assertEqual(_f1("The Moon!", ["moon", "luna"]), 1.0)
        self.assertGreater(_f1("Apollo 11 mission", ["apollo 11"]), 0.0)
        self.assertEqual(_f1(None, ["moon"]), 0.0)

    def test_answer_bearing_match_respects_token_boundaries(self):
        self.assertTrue(_contains_alias("The answer is Apollo 11.", ["apollo 11"]))
        self.assertFalse(_contains_alias("A caterpillar appears.", ["cat"]))

    def test_fixed_chunker_is_question_independent_and_offsets_reconstruct(self):
        document = " ".join(f"t{i}" for i in range(400))
        chunks = chunk_document("doc", "Title", document)
        self.assertEqual([(row["body_token_start"], row["body_token_end"]) for row in chunks], [(0, 256), (192, 400)])
        reconstructed = _reconstruct_documents(chunks)
        self.assertEqual(reconstructed["doc"], document)

    def test_reconstruction_fails_on_overlap_drift(self):
        chunks = [
            {"chunk_id": "a", "doc_id": "doc", "title": "", "text": "one two", "body_token_start": 0, "body_token_end": 2},
            {"chunk_id": "b", "doc_id": "doc", "title": "", "text": "DIFFERENT three", "body_token_start": 1, "body_token_end": 3},
        ]
        with self.assertRaisesRegex(RuntimeError, "overlapping"):
            _reconstruct_documents(chunks)


if __name__ == "__main__":
    unittest.main()
