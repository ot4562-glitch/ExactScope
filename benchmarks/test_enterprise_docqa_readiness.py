#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "tools", ROOT / "benchmarks"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from grounding_canonical import canonical_bytes
import enterprise_docqa_analysis as analysis_tool
import enterprise_docqa_decision as decision_tool
import enterprise_docqa_preregister as prereg_tool
import enterprise_docqa_readiness as readiness
import enterprise_docqa_study_contract as study_tool
import qualified_execution as qe
import test_enterprise_docqa_preregister as prereg_test_helpers


class EnterpriseDocQAReadinessTests(unittest.TestCase):
    def write_obj(self, path: Path, value):
        path.write_bytes(canonical_bytes(value))

    def write_rows(self, path: Path, rows):
        with path.open("wb") as handle:
            for row in rows:
                handle.write(canonical_bytes(row) + b"\n")

    def fixture(self, root: Path):
        source_test = prereg_test_helpers.EnterpriseDocQAPreregisterTests(methodName="runTest")
        records = source_test.records()
        record_dir = root / "records"
        record_dir.mkdir()
        record_paths = source_test.write_records(record_dir, records)

        runner = root / "runner.py"
        scorer = root / "scorer.py"
        runner.write_text("print('runner')\n", encoding="utf-8")
        scorer.write_text("print('scorer')\n", encoding="utf-8")
        prereg_path = root / "prereg.json"
        prereg_tool.preregister_command(argparse.Namespace(
            **record_paths,
            runner_source=runner,
            scorer_source=scorer,
            output=prereg_path,
        ))

        workload = {
            "v": 1,
            "format": "exactscope.workload-contract",
            "format_version": "0.1",
            "workload_id": records["workload"]["workload_id"],
            "workload_revision": "r1",
            "population_identity": records["workload"]["authorized_collection_identity"],
            "runtime_obligations": [{
                "obligation_id": "output-schema",
                "kind": "output-schema",
                "rule_id": "answer-object-v4",
                "failure_reason": "output-contract-failed",
            }],
            "empirical_requirements": [{
                "requirement_id": "accuracy-min",
                "metric_id": "task_accuracy",
                "direction": "min",
                "threshold": 8000,
                "unit": "basis-points",
                "mandatory": True,
            }],
            "answer_contract_id": "answer-object-v4",
            "evidence_policy_id": records["integrated"]["evidence_policy_id"],
            "evidence_composition": records["workload"]["evidence_composition"],
            "evidence_budget_bytes": records["workload"]["evidence_budget_bytes"],
            "economic_model_id": "enterprise-economics-v1",
            "invalidation_policy": {
                "unknown_change": "full-requalification",
                "targeted_requalification_allowed": False,
                "dependency_rule_id": "enterprise-dependency-v1",
                "nonbehavioral_dependency_ids": [],
                "targeted_dependency_ids": [],
            },
        }
        host = {
            "v": 1,
            "format": "exactscope.host-capability-manifest",
            "format_version": "0.1",
            "host_id": "enterprise-host-1",
            "supported_checks": [{
                "kind": "output-schema",
                "rule_id": "answer-object-v4",
                "lowering_id": "schema-lowering-v1",
                "check_id": "schema-check-v1",
            }],
            "qualification_scope": "inspectable-pinned",
            "dependencies": [{
                "dependency_id": "model",
                "kind": "model",
                "identity": records["integrated"]["model_identity"],
                "assurance": "pinned",
                "valid_until_epoch_s": None,
                "observation_policy_id": None,
            }],
            "capabilities": [{
                "capability_id": "structured-output",
                "binding_id": "json-schema-v1",
                "assurance": "pinned",
            }],
            "exact_fit_supported": True,
            "max_model_calls": records["integrated"]["max_model_calls"],
            "fallback_owner": "host",
        }
        source_policy = {
            "policy_id": records["integrated"]["answer_policy_identity"],
            "lowerings": [{
                "obligation_id": "output-schema",
                "lowering_id": "schema-lowering-v1",
                "check_id": "schema-check-v1",
                "failure_reason": "output-contract-failed",
            }],
            "required_capabilities": ["structured-output"],
            "max_model_calls": records["integrated"]["max_model_calls"],
        }
        candidate = qe.compile_candidate(workload, host, source_policy)
        workload_path = root / "workload-contract.json"
        host_path = root / "host-manifest.json"
        candidate_path = root / "candidate-policy.json"
        self.write_obj(workload_path, workload)
        self.write_obj(host_path, host)
        self.write_obj(candidate_path, candidate)

        questions_path = root / "questions.jsonl"
        self.write_rows(questions_path, [
            {
                "item_id": f"q-{index:03d}",
                "group_id": f"g-{index:03d}",
                "question_class": "answerable",
                "question": f"Frozen enterprise question {index}?",
            }
            for index in range(records["analysis"]["confirmatory_sample_size"])
        ])
        alternative = {
            "format": study_tool.ALTERNATIVE_FORMAT,
            "format_version": study_tool.FORMAT_VERSION,
            "config_id": "ordinary-1",
            "model_identity": records["base"]["model_identity"],
            "runtime_identity": records["base"]["runtime_identity"],
            "tokenizer_template_identity": records["base"]["tokenizer_template_identity"],
            "retrieval_identity": records["retrieval"]["retriever_identity"],
            "generation_settings_identity": "ordinary-gen-1",
            "answer_policy_identity": "ordinary-fixed-prompt-1",
            "development_evidence_identity": "ordinary-dev-report-1",
            "ordinary_alternative_kind": "matched-model-simple-fixed-configuration",
            "max_model_calls": 1,
            "runtime_answer_repair": False,
            "second_model_judge": False,
            "adaptive_policy_routing": False,
            "uses_exactscope": False,
            "development_eligible": True,
            "ordinary_deployable": True,
            "fixed_economic_counters": {
                "integration_units": 0,
                "qualification_units": 1,
                "refresh_units": 1,
                "maintenance_units": 1,
            },
        }
        alternative_path = root / "alternative.json"
        self.write_obj(alternative_path, alternative)

        analysis_source = Path(analysis_tool.__file__).resolve()
        decision_source = Path(decision_tool.__file__).resolve()
        study_path = root / "study.json"
        study_tool.freeze(
            prereg_path,
            alternative_path,
            workload_path,
            host_path,
            candidate_path,
            questions_path,
            runner,
            scorer,
            analysis_source,
            decision_source,
            Path(readiness.__file__).resolve(),
            study_path,
        )
        return {
            "prereg": prereg_path,
            "study": study_path,
            "questions": questions_path,
            "alternative": alternative_path,
            "workload": workload_path,
            "host": host_path,
            "candidate": candidate_path,
            "runner": runner,
            "scorer": scorer,
            "analysis_source": analysis_source,
            "decision_source": decision_source,
            "run_output": root / "confirmatory-run",
            "report": root / "readiness.json",
        }

    def call(self, f):
        return readiness.check_readiness(
            f["prereg"], f["study"], f["questions"], f["alternative"], f["workload"],
            f["host"], f["candidate"], f["runner"], f["scorer"], f["analysis_source"],
            f["decision_source"], f["run_output"], f["report"],
        )

    def test_complete_frozen_bundle_is_ready_without_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp))
            result = self.call(f)
            self.assertEqual(result["status"], "READY_FOR_CONFIRMATORY_EXECUTION")
            self.assertFalse(result["model_inference_performed"])
            self.assertFalse(result["retrieval_performed"])
            self.assertEqual(result["confirmatory_question_count"], 200)
            self.assertFalse(f["run_output"].exists())

    def test_question_set_drift_blocks_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp))
            rows = study_tool.load_jsonl(f["questions"])
            rows[0]["question"] = "Changed after freeze"
            self.write_rows(f["questions"], rows)
            with self.assertRaisesRegex(readiness.ReadinessError, "question set differs"):
                self.call(f)

    def test_runner_source_drift_blocks_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp))
            f["runner"].write_text("print('changed')\n", encoding="utf-8")
            with self.assertRaisesRegex(readiness.ReadinessError, "runner source differs"):
                self.call(f)

    def test_readiness_source_drift_blocks_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp))
            study = readiness._load(f["study"])
            study["readiness_source_sha256"] = "f" * 64
            self.write_obj(f["study"], study)
            with self.assertRaisesRegex(readiness.ReadinessError, "readiness implementation differs"):
                self.call(f)

    def test_existing_run_output_blocks_resume_or_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp))
            f["run_output"].mkdir()
            with self.assertRaisesRegex(readiness.ReadinessError, "resume/reuse is forbidden"):
                self.call(f)

    def test_candidate_substitution_blocks_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.fixture(Path(tmp))
            candidate = readiness._load(f["candidate"])
            candidate["policy_id"] = "post-freeze-substitution"
            self.write_obj(f["candidate"], candidate)
            with self.assertRaises((readiness.ReadinessError, qe.QualifiedExecutionError)):
                self.call(f)


if __name__ == "__main__":
    unittest.main(verbosity=2)
