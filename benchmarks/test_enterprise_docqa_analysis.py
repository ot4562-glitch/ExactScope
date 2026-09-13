#!/usr/bin/env python3
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "tools", ROOT / "benchmarks"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from grounding_canonical import canonical_bytes
import enterprise_docqa_analysis as analysis
import enterprise_docqa_observations as obs
import enterprise_docqa_score as scorer
from test_enterprise_docqa_score import ScoreTests


class EnterpriseDocQAAnalysisTests(unittest.TestCase):
    def write_obj(self, path: Path, value):
        path.write_bytes(canonical_bytes(value))

    def fixture(self, root: Path):
        base = ScoreTests()
        prereg_path, study_path, questions_path, readiness_path, manifest_path, observations_path, adjudications_path = base.scoring_fixture(root)
        prereg = obs.load_object(prereg_path)
        prereg["records"]["analysis"].update({
            "method_id": analysis.METHOD_ID,
            "method_parameters": {
                "bootstrap_seed": 7,
                "bootstrap_resamples": 100,
                "confidence_bps": 9500,
                "quality_noninferiority_margin_bps": 0,
                "base_min_cost_savings_bps": 0,
                "alternative_min_cost_savings_bps": 0,
            },
            "estimand": "paired task correctness and total economic cost",
            "sampling_design": "fixed paired confirmatory sample",
            "uncertainty_method": "deterministic paired bootstrap lower bounds",
            "sample_size_rationale": "synthetic unit-test sample",
            "stopping_rule": "one fixed sample",
            "missing_invalid_rule": "invalid rows fail closed",
            "all_thresholds_frozen": True,
            "post_score_extension_allowed": False,
        })
        self.write_obj(prereg_path, prereg)

        study = obs.load_object(study_path)
        study["preregistration_sha256"] = obs.sha256(prereg_path)
        study["analysis_source_sha256"] = analysis.sha256(Path(analysis.__file__))
        self.write_obj(study_path, study)
        base.rebind_run(prereg_path, study_path, questions_path, readiness_path, manifest_path, observations_path)

        score_path = root / "score.json"
        scorer.score(
            prereg_path,
            study_path,
            questions_path,
            readiness_path,
            manifest_path,
            observations_path,
            adjudications_path,
            score_path,
        )
        return prereg_path, study_path, questions_path, readiness_path, manifest_path, observations_path, adjudications_path, score_path

    def test_reference_analysis_is_deterministic_and_can_pass_equal_cost_noninferiority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self.fixture(root)
            first = analysis.analyze(*paths, root / "analysis-1.json")
            second = analysis.analyze(*paths, root / "analysis-2.json")
            self.assertEqual(first, second)
            self.assertEqual(first["method_identity"], analysis.METHOD_ID)
            self.assertEqual(first["conclusion"], "pass")
            self.assertEqual(first["integrated_vs_base"], "pass")
            self.assertEqual(first["integrated_vs_alternative"], "pass")
            self.assertTrue(first["uncertainty_conclusive"])

    def test_analysis_source_must_match_frozen_study_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self.fixture(root)
            study = obs.load_object(paths[1])
            study["analysis_source_sha256"] = "0" * 64
            self.write_obj(paths[1], study)
            ScoreTests().rebind_run(paths[0], paths[1], paths[2], paths[3], paths[4], paths[5])
            with self.assertRaisesRegex(analysis.AnalysisError, "analysis source differs"):
                analysis.analyze(*paths, root / "analysis.json")

    def test_tampered_score_metrics_are_recomputed_and_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self.fixture(root)
            score_record = obs.load_object(paths[7])
            score_record["arms"]["integrated"]["metrics"]["task_accuracy"] = 0
            self.write_obj(paths[7], score_record)
            with self.assertRaisesRegex(analysis.AnalysisError, "metrics/economics drift"):
                analysis.analyze(*paths, root / "analysis.json")

    def test_frozen_positive_savings_requirement_can_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = list(self.fixture(root))
            prereg = obs.load_object(paths[0])
            prereg["records"]["analysis"]["method_parameters"]["alternative_min_cost_savings_bps"] = 1
            self.write_obj(paths[0], prereg)
            study = obs.load_object(paths[1])
            study["preregistration_sha256"] = obs.sha256(paths[0])
            self.write_obj(paths[1], study)
            ScoreTests().rebind_run(paths[0], paths[1], paths[2], paths[3], paths[4], paths[5])
            paths[7].unlink()
            scorer.score(*paths[:7], paths[7])
            result = analysis.analyze(*paths, root / "analysis.json")
            self.assertEqual(result["comparisons"]["alternative"]["economics"]["status"], "fail")
            self.assertEqual(result["total_economics"], "fail")
            self.assertEqual(result["conclusion"], "fail")


if __name__ == "__main__":
    unittest.main(verbosity=2)
