"""Tests for deterministic mutually exclusive serving-surface candidates."""
import copy
import tempfile
import unittest
from pathlib import Path

from compile_capability import ROOT, canonical, load
from compile_capability_candidates import (build_candidate_set, candidate_requests,
                                           verify_candidate_set, write_candidate_set)


class CandidateCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_path = ROOT / "spec/examples/statistics-capability-request-r23.json"
        cls.source = cls.source_path.read_bytes()
        cls.request = load(cls.source)
        executable = "exactscope-packc.exe" if __import__("os").name == "nt" else "exactscope-packc"
        cls.packc = ROOT / "target/debug" / executable

    def test_candidates_are_minimal_and_mutually_exclusive(self):
        candidates = dict(candidate_requests(self.source))
        self.assertEqual(set(candidates), {"semantic-only", "combined"})
        semantic = candidates["semantic-only"]
        combined = candidates["combined"]
        self.assertFalse(semantic["xs_calc"])
        self.assertEqual(semantic["model_visible_tools_max"], 1)
        self.assertEqual(semantic["model_budget"]["plan_steps_max"], 0)
        self.assertTrue(combined["xs_calc"])
        self.assertEqual(combined["model_visible_tools_max"], 2)
        self.assertEqual(combined["model_budget"]["plan_steps_max"], 8)
        self.assertEqual(semantic["task_families"], combined["task_families"])
        self.assertNotEqual(semantic["profile_id"], combined["profile_id"])

    def test_candidate_set_reuses_ordinary_capability_bundles(self):
        payloads, compiled = build_candidate_set(self.source, self.packc)
        manifest = load(payloads["candidate-set.json"])
        self.assertEqual([entry["label"] for entry in manifest["candidates"]],
                         ["semantic-only", "combined"])
        by_label = {label: (files, profile) for label, _request, files, profile in compiled}
        semantic_files, semantic = by_label["semantic-only"]
        combined_files, combined = by_label["combined"]
        self.assertNotIn("xs-calc.tool.json", semantic_files)
        self.assertIn("xs-eval.tool.json", semantic_files)
        self.assertIn("xs-calc.tool.json", combined_files)
        self.assertIn("xs-eval.tool.json", combined_files)
        self.assertEqual(semantic["runtime_surface"]["xs_eval"]["operations"],
                         combined["runtime_surface"]["xs_eval"]["operations"])
        self.assertNotEqual(semantic_files["bundle-sha256.txt"], combined_files["bundle-sha256.txt"])

    def test_candidate_compilation_is_deterministic_and_immutable(self):
        first = build_candidate_set(self.source, self.packc)
        second = build_candidate_set(canonical(load(self.source)), self.packc)
        self.assertEqual(first, second)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "candidates"
            write_candidate_set(self.source, self.packc, output)
            write_candidate_set(self.source, self.packc, output)
            verify_candidate_set(output)
            (output / "candidate-set-sha256.txt").write_text("0" * 64 + "\n", encoding="ascii")
            with self.assertRaises(ValueError):
                verify_candidate_set(output)

    def test_baseline_and_overlong_identity_are_rejected(self):
        request = copy.deepcopy(self.request)
        request["task_families"] = ["arithmetic-baseline"]
        with self.assertRaises(ValueError):
            candidate_requests(canonical(request))
        request = copy.deepcopy(self.request)
        request["profile_id"] = "x" * 90
        with self.assertRaises(ValueError):
            candidate_requests(canonical(request))


if __name__ == "__main__":
    unittest.main()
