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
import enterprise_docqa_study_contract as contract


class ObservationTests(unittest.TestCase):
    def write_obj(self, path, value):
        path.write_bytes(canonical_bytes(value))

    def write_rows(self, path, rows):
        with path.open("wb") as handle:
            for row in rows:
                handle.write(canonical_bytes(row) + b"\n")

    def fixture(self, root):
        prereg = {
            "format": "exactscope.enterprise-docqa-preregistration",
            "format_version": "0.1",
            "records": {
                "analysis": {"confirmatory_sample_size": 1},
                "base": {"max_model_calls": 1},
                "integrated": {"max_model_calls": 1},
            },
        }
        prereg_path = root / "prereg.json"
        self.write_obj(prereg_path, prereg)
        questions_path = root / "questions.jsonl"
        self.write_rows(
            questions_path,
            [{"item_id": "q1", "group_id": "g1", "question_class": "answerable", "question": "Question one"}],
        )
        fixed = {"base": {}, "integrated": {}, "alternative": {}}
        study = {
            "format": contract.FORMAT,
            "format_version": "0.1",
            "state": "frozen-unscored",
            "preregistration_sha256": obs.sha256(prereg_path),
            "questions_sha256": obs.sha256(questions_path),
            "confirmatory_question_count": 1,
            "alternative_sha256": "d" * 64,
            "readiness_source_sha256": "e" * 64,
            "integrated_binding": {
                "config_id": "integrated-1",
                "candidate_policy_sha256": "a" * 64,
                "workload_contract_sha256": "b" * 64,
                "host_manifest_sha256": "c" * 64,
            },
            "arms": {"base": "base-1", "integrated": "integrated-1", "alternative": "alt-1"},
            "evidence_contract": {
                "evidence_composition": "single-source-precision",
                "evidence_policy_id": "precision-context-v5",
                "evidence_budget_bytes": 3072,
                "max_projected_items": 8,
                "retrieval_top_k_limit": 8,
            },
            "alternative": {"max_model_calls": 1},
            "fixed_counters_by_arm": fixed,
        }
        study_path = root / "study.json"
        self.write_obj(study_path, study)
        readiness_path = root / "readiness.json"
        readiness = {
            "format": obs.READINESS_FORMAT,
            "format_version": "0.1",
            "status": "READY_FOR_CONFIRMATORY_EXECUTION",
            "model_inference_performed": False,
            "retrieval_performed": False,
            "preregistration_sha256": obs.sha256(prereg_path),
            "study_contract_sha256": obs.sha256(study_path),
            "questions_sha256": obs.sha256(questions_path),
            "confirmatory_question_count": 1,
            "candidate_policy_sha256": study["integrated_binding"]["candidate_policy_sha256"],
            "workload_contract_sha256": study["integrated_binding"]["workload_contract_sha256"],
            "host_manifest_sha256": study["integrated_binding"]["host_manifest_sha256"],
            "ordinary_alternative_sha256": study["alternative_sha256"],
            "readiness_source_sha256": study["readiness_source_sha256"],
            "confirmatory_run_output": str((root / "confirmatory-run").resolve()),
        }
        self.write_obj(readiness_path, readiness)
        readiness_sha = obs.sha256(readiness_path)
        run_root = Path(readiness["confirmatory_run_output"])
        run_root.mkdir()
        rows = []
        for arm, config in (("base", "base-1"), ("integrated", "integrated-1"), ("alternative", "alt-1")):
            rows.append({
                "format": obs.OBSERVATION_FORMAT,
                "format_version": "0.1",
                "item_id": "q1",
                "arm": arm,
                "config_id": config,
                "readiness_report_sha256": readiness_sha,
                "answer": "A",
                "abstained": False,
                "citations": [{"source_id": "doc-1", "span_id": "s1"}],
                "model_calls": 1,
                "input_tokens": 100,
                "output_tokens": 5,
                "retrieval_units": 8,
                "evidence_bytes": 2000 if arm == "integrated" else 4000,
                "projected_item_count": 6 if arm == "integrated" else 8,
                "model_service_ms": 10,
                "e2e_ms": 20,
                "format_valid": True,
                "finalization_valid": True,
                "retry_count": 0,
                "second_model_judge": False,
                "adaptive_policy_routing": False,
            })
        rows_path = run_root / "observations.jsonl"
        self.write_rows(rows_path, rows)
        manifest = {
            "format": obs.RUN_FORMAT,
            "format_version": "0.1",
            "state": "complete",
            "study_contract_sha256": obs.sha256(study_path),
            "preregistration_sha256": obs.sha256(prereg_path),
            "questions_sha256": obs.sha256(questions_path),
            "readiness_report_sha256": readiness_sha,
            "observations_sha256": obs.sha256(rows_path),
            "item_count": 1,
            "record_count": 3,
            "arms": study["arms"],
            "gold_visible_to_runner": False,
            "outcome_dependent_reordering": False,
            "confirmatory_run_output": readiness["confirmatory_run_output"],
            "fixed_counters_by_arm": fixed,
        }
        manifest_path = run_root / "run.json"
        self.write_obj(manifest_path, manifest)
        return prereg_path, study_path, questions_path, readiness_path, manifest_path, rows_path, rows, manifest

    def test_valid_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = self.fixture(Path(tmp))
            result = obs.validate_bundle(*fixture[:6])
            self.assertEqual(result["record_count"], 3)
            self.assertEqual(result["readiness_report_sha256"], obs.sha256(fixture[3]))

    def test_seal_run_reconstructs_canonical_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, study, questions, readiness, _manifest_path, rows_path, _rows, manifest = self.fixture(root)
            sealed_path = rows_path.parent / "sealed-run.json"
            sealed = obs.seal_run(prereg, study, questions, readiness, rows_path, sealed_path)
            self.assertEqual(sealed, manifest)
            self.assertEqual(obs.load_object(sealed_path), manifest)

    def test_seal_run_rejects_manifest_outside_frozen_run_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, study, questions, readiness, _manifest_path, rows_path, _rows, _manifest = self.fixture(root)
            with self.assertRaisesRegex(obs.ObservationError, "run manifest is outside frozen confirmatory run output"):
                obs.seal_run(prereg, study, questions, readiness, rows_path, root / "outside-run.json")

    def test_bundle_rejects_observations_outside_frozen_run_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, study, questions, readiness, manifest_path, rows_path, rows, manifest = self.fixture(root)
            outside_rows = root / "outside-observations.jsonl"
            self.write_rows(outside_rows, rows)
            manifest["observations_sha256"] = obs.sha256(outside_rows)
            self.write_obj(manifest_path, manifest)
            with self.assertRaisesRegex(obs.ObservationError, "observations is outside frozen confirmatory run output"):
                obs.validate_bundle(prereg, study, questions, readiness, manifest_path, outside_rows)

    def test_question_set_cannot_change_after_study_freeze(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, study, questions, readiness, manifest, rows_path, _rows, _run = self.fixture(root)
            self.write_rows(questions, [{
                "item_id": "q1",
                "group_id": "g1",
                "question_class": "answerable",
                "question": "A different but still structurally valid question",
            }])
            with self.assertRaisesRegex(obs.ObservationError, "differs from frozen Study Contract"):
                obs.validate_bundle(prereg, study, questions, readiness, manifest, rows_path)

    def test_observation_readiness_drift_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, study, questions, readiness, manifest, rows_path, rows, _run = self.fixture(root)
            rows[0]["readiness_report_sha256"] = "0" * 64
            self.write_rows(rows_path, rows)
            with self.assertRaisesRegex(obs.ObservationError, "readiness identity drift"):
                obs.validate_bundle(prereg, study, questions, readiness, manifest, rows_path)

    def test_integrated_budget_overflow_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, study, questions, readiness, manifest, rows_path, rows, _run = self.fixture(root)
            rows[1]["evidence_bytes"] = 3073
            self.write_rows(rows_path, rows)
            with self.assertRaises(obs.ObservationError):
                obs.validate_bundle(prereg, study, questions, readiness, manifest, rows_path)

    def test_missing_arm_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, study, questions, readiness, manifest, rows_path, rows, _run = self.fixture(root)
            self.write_rows(rows_path, rows[:-1])
            with self.assertRaises(obs.ObservationError):
                obs.validate_bundle(prereg, study, questions, readiness, manifest, rows_path)

    def test_manifest_digest_drift_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, study, questions, readiness, manifest_path, rows_path, _rows, manifest = self.fixture(root)
            manifest["observations_sha256"] = "0" * 64
            self.write_obj(manifest_path, manifest)
            with self.assertRaises(obs.ObservationError):
                obs.validate_bundle(prereg, study, questions, readiness, manifest_path, rows_path)

    def test_manifest_fixed_counters_cannot_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, study, questions, readiness, manifest_path, rows_path, _rows, manifest = self.fixture(root)
            manifest["fixed_counters_by_arm"]["integrated"] = {"integration_units": 1}
            self.write_obj(manifest_path, manifest)
            with self.assertRaises(obs.ObservationError):
                obs.validate_bundle(prereg, study, questions, readiness, manifest_path, rows_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
