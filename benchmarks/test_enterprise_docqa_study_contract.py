#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "tools", ROOT / "benchmarks"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from grounding_canonical import canonical_bytes  # noqa: E402
import enterprise_docqa_study_contract as study  # noqa: E402


class EnterpriseDocQAStudyContractTests(unittest.TestCase):
    def sha_bytes(self, value: bytes) -> str:
        return hashlib.sha256(value).hexdigest()

    def fixture(self, root: Path):
        runner = root / "runner.py"
        scorer = root / "scorer.py"
        analysis = root / "analysis.py"
        decision_source = root / "decision.py"
        runner.write_text("print('runner')\n", encoding="utf-8")
        scorer.write_text("print('scorer')\n", encoding="utf-8")
        analysis.write_text("print('analysis')\n", encoding="utf-8")
        decision_source.write_text("print('decision')\n", encoding="utf-8")
        workload = {
            "v": 1,
            "format": "exactscope.workload-contract",
            "format_version": "0.1",
            "workload_id": "docqa-policy-v1",
            "workload_revision": "r1",
            "population_identity": "enterprise-population-r1",
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
            "evidence_policy_id": "precision-context-v5",
            "evidence_composition": "single-source-precision",
            "evidence_budget_bytes": 3072,
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
                "identity": "model-a",
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
            "max_model_calls": 1,
            "fallback_owner": "host",
        }
        source_policy = {
            "policy_id": "integrated-policy-1",
            "lowerings": [{
                "obligation_id": "output-schema",
                "lowering_id": "schema-lowering-v1",
                "check_id": "schema-check-v1",
                "failure_reason": "output-contract-failed",
            }],
            "required_capabilities": ["structured-output"],
            "max_model_calls": 1,
        }
        candidate = study.qe.compile_candidate(workload, host, source_policy)
        workload_path = root / "workload.json"
        host_path = root / "host.json"
        candidate_path = root / "candidate.json"
        workload_path.write_bytes(canonical_bytes(workload))
        host_path.write_bytes(canonical_bytes(host))
        candidate_path.write_bytes(canonical_bytes(candidate))
        questions_path = root / "questions.jsonl"
        questions_path.write_bytes(canonical_bytes({
            "item_id": "q1",
            "group_id": "g1",
            "question_class": "answerable",
            "question": "What is the policy answer?",
        }) + b"\n")
        prereg = {
            "format": "exactscope.enterprise-docqa-preregistration",
            "format_version": "0.1",
            "confirmatory_status": "frozen-unscored",
            "post_score_rule_changes_allowed": False,
            "fever_stage1_heldout_reuse": False,
            "workload_id": "docqa-policy-v1",
            "primary_comparison": {
                "base_config_id": "base-1",
                "integrated_config_id": "integrated-1",
            },
            "records": {
                "analysis": {"confirmatory_sample_size": 1},
                "retrieval": {"retriever_identity": "retriever-1"},
                "economics": {
                    "components": [
                        {"name": "model-time", "counter": "model_service_ms", "coefficient": 1},
                        {"name": "integration", "counter": "integration_units", "coefficient": 10},
                    ],
                    "fixed_counters_by_arm": {
                        "base": {"integration_units": 0},
                        "integrated": {"integration_units": 2},
                    },
                },
            },
            "evidence_contract": {
                "evidence_composition": "single-source-precision",
                "evidence_policy_id": "precision-context-v5",
                "evidence_budget_bytes": 3072,
                "max_projected_items": 8,
                "retrieval_top_k_limit": 8,
            },
            "source_sha256": {
                "runner": study.sha256(runner),
                "scorer": study.sha256(scorer),
                "preregister_tool": "0" * 64,
            },
        }
        prereg_path = root / "prereg.json"
        prereg_path.write_bytes(canonical_bytes(prereg))
        alternative = {
            "format": study.ALTERNATIVE_FORMAT,
            "format_version": study.FORMAT_VERSION,
            "config_id": "ordinary-1",
            "model_identity": "model-a",
            "runtime_identity": "runtime-a",
            "tokenizer_template_identity": "template-a",
            "retrieval_identity": "retriever-1",
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
            "fixed_economic_counters": {"integration_units": 1},
        }
        alternative_path = root / "alternative.json"
        alternative_path.write_bytes(canonical_bytes(alternative))
        return prereg_path, alternative_path, workload_path, host_path, candidate_path, questions_path, runner, scorer, analysis, decision_source, alternative

    def test_valid_study_contract_freezes_three_arms(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, alternative, workload, host, candidate, questions, runner, scorer, analysis, decision_source, _record = self.fixture(root)
            output = root / "study.json"
            result = study.freeze(prereg, alternative, workload, host, candidate, questions, runner, scorer, analysis, decision_source, Path(study.__file__), output)
            self.assertTrue(output.is_file())
            self.assertEqual(
                result["arms"],
                {"base": "base-1", "integrated": "integrated-1", "alternative": "ordinary-1"},
            )
            self.assertTrue(result["ordinary_alternative_required"])
            self.assertFalse(result["confirmatory_outcomes_visible_at_freeze"])
            self.assertEqual(result["questions_sha256"], study.sha256(questions))
            self.assertEqual(result["confirmatory_question_count"], 1)

    def test_confirmatory_questions_cannot_expose_gold(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, alternative, workload, host, candidate, questions, runner, scorer, analysis, decision_source, _record = self.fixture(root)
            questions.write_bytes(canonical_bytes({
                "item_id": "q1",
                "group_id": "g1",
                "question_class": "answerable",
                "question": "What is the policy answer?",
                "gold": "forbidden",
            }) + b"\n")
            with self.assertRaisesRegex(study.StudyContractError, "forbidden fields"):
                study.freeze(prereg, alternative, workload, host, candidate, questions, runner, scorer, analysis, decision_source, Path(study.__file__), root / "study.json")

    def test_confirmatory_question_count_is_frozen_before_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, alternative, workload, host, candidate, questions, runner, scorer, analysis, decision_source, _record = self.fixture(root)
            with questions.open("ab") as handle:
                handle.write(canonical_bytes({
                    "item_id": "q2",
                    "group_id": "g2",
                    "question_class": "answerable",
                    "question": "A second question",
                }) + b"\n")
            with self.assertRaisesRegex(study.StudyContractError, "count differs"):
                study.freeze(prereg, alternative, workload, host, candidate, questions, runner, scorer, analysis, decision_source, Path(study.__file__), root / "study.json")

    def test_alternative_cannot_use_exactscope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, alternative_path, workload, host, candidate, questions, runner, scorer, analysis, decision_source, alternative = self.fixture(root)
            alternative["uses_exactscope"] = True
            alternative_path.write_bytes(canonical_bytes(alternative))
            with self.assertRaisesRegex(study.StudyContractError, "uses_exactscope"):
                study.freeze(prereg, alternative_path, workload, host, candidate, questions, runner, scorer, analysis, decision_source, Path(study.__file__), root / "study.json")

    def test_alternative_must_be_development_eligible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, alternative_path, workload, host, candidate, questions, runner, scorer, analysis, decision_source, alternative = self.fixture(root)
            alternative["development_eligible"] = False
            alternative_path.write_bytes(canonical_bytes(alternative))
            with self.assertRaisesRegex(study.StudyContractError, "development-eligible"):
                study.freeze(prereg, alternative_path, workload, host, candidate, questions, runner, scorer, analysis, decision_source, Path(study.__file__), root / "study.json")

    def test_alternative_must_use_frozen_retrieval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, alternative_path, workload, host, candidate, questions, runner, scorer, analysis, decision_source, alternative = self.fixture(root)
            alternative["retrieval_identity"] = "other-retriever"
            alternative_path.write_bytes(canonical_bytes(alternative))
            with self.assertRaisesRegex(study.StudyContractError, "retrieval identity differs"):
                study.freeze(prereg, alternative_path, workload, host, candidate, questions, runner, scorer, analysis, decision_source, Path(study.__file__), root / "study.json")

    def test_alternative_config_id_cannot_collide(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, alternative_path, workload, host, candidate, questions, runner, scorer, analysis, decision_source, alternative = self.fixture(root)
            alternative["config_id"] = "integrated-1"
            alternative_path.write_bytes(canonical_bytes(alternative))
            with self.assertRaisesRegex(study.StudyContractError, "collides"):
                study.freeze(prereg, alternative_path, workload, host, candidate, questions, runner, scorer, analysis, decision_source, Path(study.__file__), root / "study.json")

    def test_runner_source_identity_must_match_prereg(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, alternative_path, workload, host, candidate, questions, runner, scorer, analysis, decision_source, _alternative = self.fixture(root)
            runner.write_text("print('changed')\n", encoding="utf-8")
            with self.assertRaisesRegex(study.StudyContractError, "runner source differs"):
                study.freeze(prereg, alternative_path, workload, host, candidate, questions, runner, scorer, analysis, decision_source, Path(study.__file__), root / "study.json")

    def test_evidence_budget_bound_is_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg_path, alternative_path, workload, host, candidate, questions, runner, scorer, analysis, decision_source, _alternative = self.fixture(root)
            prereg = study.load_object(prereg_path)
            prereg["evidence_contract"]["evidence_budget_bytes"] = 128
            prereg_path.write_bytes(canonical_bytes(prereg))
            with self.assertRaisesRegex(study.StudyContractError, "outside the supported bound"):
                study.freeze(prereg_path, alternative_path, workload, host, candidate, questions, runner, scorer, analysis, decision_source, Path(study.__file__), root / "study.json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
