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
import enterprise_docqa_observations as obs
import enterprise_docqa_score as score
from test_enterprise_docqa_observations import ObservationTests


class ScoreTests(unittest.TestCase):
    def write_obj(self, path, value):
        path.write_bytes(canonical_bytes(value))

    def write_rows(self, path, rows):
        with path.open("wb") as handle:
            for row in rows:
                handle.write(canonical_bytes(row) + b"\n")

    def rebind_run(self, prereg_path, study_path, questions_path, readiness_path, manifest_path, observations_path):
        study = obs.load_object(study_path)
        study["preregistration_sha256"] = obs.sha256(prereg_path)
        self.write_obj(study_path, study)
        readiness = obs.load_object(readiness_path)
        readiness["preregistration_sha256"] = obs.sha256(prereg_path)
        readiness["study_contract_sha256"] = obs.sha256(study_path)
        self.write_obj(readiness_path, readiness)
        readiness_sha = obs.sha256(readiness_path)
        observation_rows = obs.load_jsonl(observations_path)
        for row in observation_rows:
            row["readiness_report_sha256"] = readiness_sha
        self.write_rows(observations_path, observation_rows)
        manifest = obs.load_object(manifest_path)
        manifest["preregistration_sha256"] = obs.sha256(prereg_path)
        manifest["study_contract_sha256"] = obs.sha256(study_path)
        manifest["questions_sha256"] = obs.sha256(questions_path)
        manifest["readiness_report_sha256"] = readiness_sha
        manifest["observations_sha256"] = obs.sha256(observations_path)
        self.write_obj(manifest_path, manifest)

    def scoring_fixture(self, root):
        base = ObservationTests()
        prereg_path, study_path, questions_path, readiness_path, manifest_path, observations_path, rows, manifest = base.fixture(root)
        prereg = obs.load_object(prereg_path)
        prereg["records"]["competence"] = {
            "gates": [
                {"metric": "task_accuracy", "direction": "min", "threshold": 10000, "unit": "basis-points", "owner_approved": True},
                {"metric": "unsupported_answer_rate", "direction": "max", "threshold": 0, "unit": "basis-points", "owner_approved": True},
                {"metric": "format_violations", "direction": "zero", "threshold": 0, "unit": "count", "owner_approved": True},
            ]
        }
        prereg["records"]["economics"] = {
            "unit": "internal-cost-unit",
            "components": [
                {"name": "model-time", "counter": "model_service_ms", "coefficient": 1, "basis": "measured model service milliseconds"},
                {"name": "input", "counter": "input_tokens", "coefficient": 1, "basis": "measured input tokens"},
            ],
        }
        prereg["records"]["analysis"]["confirmatory_thresholds"] = [
            {"name": "task_accuracy_min", "value": 10000, "unit": "basis-points", "owner_approved": True},
            {"name": "unsupported_answer_rate_max", "value": 0, "unit": "basis-points", "owner_approved": True},
        ]
        self.write_obj(prereg_path, prereg)
        study = obs.load_object(study_path)
        study["preregistration_sha256"] = obs.sha256(prereg_path)
        self.write_obj(study_path, study)
        manifest["preregistration_sha256"] = obs.sha256(prereg_path)
        manifest["study_contract_sha256"] = obs.sha256(study_path)
        self.write_obj(manifest_path, manifest)
        self.rebind_run(prereg_path, study_path, questions_path, readiness_path, manifest_path, observations_path)
        adjudications = []
        for row in rows:
            adjudications.append({
                "format": score.ADJUDICATION_FORMAT,
                "format_version": "0.1",
                "item_id": row["item_id"],
                "arm": row["arm"],
                "task_correct": True,
                "evidence_supported": True,
                "unsupported_answer": False,
                "abstention_correct": True,
                "unacceptable_error": False,
                "adjudication_valid": True,
                "human_review_events": 1,
            })
        adjudications_path = root / "adjudications.jsonl"
        self.write_rows(adjudications_path, adjudications)
        return (prereg_path, study_path, questions_path, readiness_path, manifest_path, observations_path, adjudications_path)

    def test_all_gates_can_pass_without_claiming_commercial_win(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self.scoring_fixture(root)
            result = score.score(*paths, root / "score.json")
            self.assertEqual(result["integrated_gate_verdict"], "GATES_PASSED_CANDIDATE")
            self.assertEqual(result["commercial_comparison"], "ORDINARY_ALTERNATIVE_NOT_BEATEN")
            self.assertFalse(result["qualified_execution_profile_emitted"])
            self.assertTrue(result["arms"]["integrated"]["all_required_gates_pass"])

    def test_unknown_economic_counter_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self.scoring_fixture(root)
            prereg = obs.load_object(paths[0])
            prereg["records"]["economics"]["components"][0]["counter"] = "unknown-counter"
            self.write_obj(paths[0], prereg)
            self.rebind_run(paths[0], paths[1], paths[2], paths[3], paths[4], paths[5])
            with self.assertRaises(score.ScoringError):
                score.score(*paths, root / "score.json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
