#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import verify_v11_public_evidence as evidence  # noqa: E402


class V11PublicEvidenceTests(unittest.TestCase):
    def fixture(self):
        return evidence._load(evidence.EVIDENCE), evidence._load(evidence.INVENTORY)

    def test_tracked_snapshot_recomputes_exactly(self):
        snapshot, inventory = self.fixture()
        result = evidence.verify(snapshot, inventory)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["models"], 20)
        self.assertEqual(result["scheduled_cells"], 40)
        self.assertEqual(result["scored_cells"], 32)
        self.assertEqual(result["n_a_cells"], 8)
        self.assertAlmostEqual(result["nq_mean_uplift_pp"], 9.240812941920558)
        self.assertAlmostEqual(result["hotpot_mean_uplift_pp"], 19.793960140783437)
        self.assertAlmostEqual(result["pooled_mean_uplift_pp"], 14.517386541351998)

    def test_tampered_model_delta_fails_closed(self):
        snapshot, inventory = self.fixture()
        tampered = deepcopy(snapshot)
        row = next(model for model in tampered["models"] if model["model_id"] == "qwen35-2b-q4km")
        row["hotpotqa"]["uplift_pp"] += 1.0
        with self.assertRaisesRegex(evidence.EvidenceError, "uplift"):
            evidence.verify(tampered, inventory)

    def test_qualification_overclaim_fails_closed(self):
        snapshot, inventory = self.fixture()
        tampered = deepcopy(snapshot)
        tampered["qualification_eligible"] = True
        with self.assertRaisesRegex(evidence.EvidenceError, "qualification eligible"):
            evidence.verify(tampered, inventory)

    def test_comparison_definition_drift_fails_closed(self):
        snapshot, inventory = self.fixture()
        tampered = deepcopy(snapshot)
        tampered["comparison_definition"]["hotpot_boundary"] = "ordinary RAG superiority established"
        with self.assertRaisesRegex(evidence.EvidenceError, "comparison definition"):
            evidence.verify(tampered, inventory)

    def test_model_set_drift_fails_closed(self):
        snapshot, inventory = self.fixture()
        tampered = deepcopy(snapshot)
        tampered["models"][0]["model_id"] = "not-the-frozen-model"
        with self.assertRaisesRegex(evidence.EvidenceError, "model set"):
            evidence.verify(tampered, inventory)


if __name__ == "__main__":
    unittest.main(verbosity=2)
