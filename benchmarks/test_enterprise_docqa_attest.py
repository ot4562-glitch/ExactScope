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
import enterprise_docqa_attest as bridge
import enterprise_docqa_decision as decision_tool
import enterprise_docqa_study_contract as study_tool
import qualified_execution as qe


class AttestationBridgeTests(unittest.TestCase):
    def write_obj(self, path, value):
        path.write_bytes(canonical_bytes(value))

    def fixture(self, root: Path):
        workload = {
            "v": 1,
            "format": "exactscope.workload-contract",
            "format_version": "0.1",
            "workload_id": "docqa-policy-v1",
            "workload_revision": "r1",
            "population_identity": "population-r1",
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
                "dependency_rule_id": "dep-rule-v1",
                "nonbehavioral_dependency_ids": [],
                "targeted_dependency_ids": [],
            },
        }
        host = {
            "v": 1,
            "format": "exactscope.host-capability-manifest",
            "format_version": "0.1",
            "host_id": "host-1",
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
        candidate = qe.compile_candidate(workload, host, source_policy)
        workload_path = root / "workload.json"
        host_path = root / "host.json"
        candidate_path = root / "candidate.json"
        self.write_obj(workload_path, workload)
        self.write_obj(host_path, host)
        self.write_obj(candidate_path, candidate)

        prereg = {
            "format": "exactscope.enterprise-docqa-preregistration",
            "format_version": "0.1",
            "workload_id": workload["workload_id"],
            "records": {
                "economics": {
                    "unit": "internal-cost-unit",
                    "components": [{"name": "model", "counter": "model_service_ms", "coefficient": 1, "basis": "ms"}],
                },
                "analysis": {
                    "estimand": "paired owner-accepted utility and total economics",
                    "sampling_design": "fixed paired confirmatory sample",
                    "uncertainty_method": "external frozen paired method",
                    "method_id": "external-paired-v1",
                    "method_parameters": {"family": "fixture"},
                    "sample_size_rationale": "fixture",
                    "stopping_rule": "one fixed sample",
                    "missing_invalid_rule": "fail closed",
                    "confirmatory_sample_size": 1,
                    "all_thresholds_frozen": True,
                    "post_score_extension_allowed": False,
                    "confirmatory_thresholds": [{"name": "task_accuracy_min", "value": 8000, "unit": "basis-points", "owner_approved": True}],
                },
            },
        }
        prereg_path = root / "prereg.json"
        self.write_obj(prereg_path, prereg)
        analysis_source = root / "analysis.py"
        analysis_source.write_text("print('analysis')\n", encoding="utf-8")
        decision_source = Path(decision_tool.__file__).resolve()
        study = {
            "format": study_tool.FORMAT,
            "format_version": "0.1",
            "state": "frozen-unscored",
            "preregistration_sha256": bridge.sha256(prereg_path),
            "questions_sha256": "1" * 64,
            "confirmatory_question_count": 1,
            "arms": {"base": "base-1", "integrated": "integrated-1", "alternative": "alt-1"},
            "integrated_binding": {
                "config_id": "integrated-1",
                "candidate_policy_sha256": qe.artifact_sha256(candidate),
                "workload_contract_sha256": qe.artifact_sha256(workload),
                "host_manifest_sha256": qe.artifact_sha256(host),
            },
            "runner_source_sha256": "2" * 64,
            "readiness_source_sha256": "8" * 64,
            "scorer_source_sha256": "3" * 64,
            "analysis_source_sha256": bridge.sha256(analysis_source),
            "decision_source_sha256": bridge.sha256(decision_source),
            "ordinary_alternative_required": True,
            "confirmatory_outcomes_visible_at_freeze": False,
            "post_score_rule_changes_allowed": False,
        }
        study_path = root / "study.json"
        self.write_obj(study_path, study)
        score = {
            "format": "exactscope.enterprise-docqa-score",
            "format_version": "0.1",
            "preregistration_sha256": bridge.sha256(prereg_path),
            "study_contract_sha256": bridge.sha256(study_path),
            "readiness_report_sha256": "7" * 64,
            "run_manifest_sha256": "4" * 64,
            "observations_sha256": "5" * 64,
            "adjudications_sha256": "6" * 64,
            "arms": {
                "integrated": {
                    "metrics": {
                        "task_accuracy": 9000,
                        "format_violations": 0,
                        "finalization_violations": 0,
                    },
                    "total_economic_cost": 100,
                }
            },
            "integrated_gate_verdict": "GATES_PASSED_CANDIDATE",
            "commercial_comparison": "INTEGRATED_LOWEST_FROZEN_COST",
            "qualified_execution_profile_emitted": False,
        }
        score_path = root / "score.json"
        self.write_obj(score_path, score)
        analysis = {
            "format": "exactscope.enterprise-docqa-analysis-report",
            "format_version": "0.1",
            "analysis_id": "analysis-fixture-1",
            "method_identity": "external-paired-v1",
            "score_sha256": bridge.sha256(score_path),
            "preregistration_sha256": bridge.sha256(prereg_path),
            "study_contract_sha256": bridge.sha256(study_path),
            "readiness_report_sha256": score["readiness_report_sha256"],
            "analysis_source_sha256": bridge.sha256(analysis_source),
            "analysis_record_sha256": decision_tool.digest_object(prereg["records"]["analysis"]),
            "conclusion": "pass",
            "integrated_vs_base": "pass",
            "integrated_vs_alternative": "pass",
            "customer_utility": "pass",
            "total_economics": "pass",
            "uncertainty_conclusive": True,
            "mandatory_violations": 0,
            "post_score_rule_changes_allowed": False,
        }
        analysis_path = root / "analysis.json"
        self.write_obj(analysis_path, analysis)
        owner = {
            "format": decision_tool.OWNER_FORMAT,
            "format_version": "0.1",
            "decision_id": "owner-fixture-1",
            "authority_id": "policy-owner-1",
            "workload_id": workload["workload_id"],
            "analysis_report_sha256": bridge.sha256(analysis_path),
            "owner_approved": True,
            "customer_utility_accepted": True,
            "total_economics_accepted": True,
            "ordinary_alternative_considered": True,
            "no_post_score_exception": True,
        }
        owner_path = root / "owner.json"
        self.write_obj(owner_path, owner)
        decision = {
            "format": decision_tool.DECISION_FORMAT,
            "format_version": "0.1",
            "status": "qualified",
            "preregistration_sha256": bridge.sha256(prereg_path),
            "study_contract_sha256": bridge.sha256(study_path),
            "score_sha256": bridge.sha256(score_path),
            "analysis_report_sha256": bridge.sha256(analysis_path),
            "owner_decision_sha256": bridge.sha256(owner_path),
            "analysis_source_sha256": bridge.sha256(analysis_source),
            "decision_source_sha256": bridge.sha256(decision_source),
            "ordinary_alternative_included": True,
            "mandatory_violations": 0,
            "generic_attestation_eligible": True,
            "qualified_execution_profile_emitted": False,
            "note": "Qualified status here is only eligibility to construct the generic Qualification Attestation after binding the exact Candidate Execution Policy, Workload Contract and Host Capability Manifest.",
        }
        decision_path = root / "decision.json"
        self.write_obj(decision_path, decision)
        return {
            "prereg": prereg_path,
            "study": study_path,
            "score": score_path,
            "analysis": analysis_path,
            "owner": owner_path,
            "decision": decision_path,
            "analysis_source": analysis_source,
            "decision_source": decision_source,
            "workload": workload_path,
            "host": host_path,
            "candidate": candidate_path,
            "decision_record": decision,
            "study_record": study,
            "score_record": score,
        }

    def call(self, f, output):
        return bridge.build_attestation(
            f["prereg"], f["study"], f["score"], f["analysis"], f["owner"], f["decision"],
            f["analysis_source"], f["decision_source"], f["workload"], f["host"], f["candidate"],
            "attestation-1", 1000, None, None, output,
        )

    def test_qualified_decision_builds_valid_generic_attestation_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = self.fixture(root)
            result = self.call(f, root / "bridge.json")
            self.assertEqual(result["attestation"]["status"], "qualified")
            self.assertFalse(result["qualified_execution_profile_emitted"])
            self.assertEqual(result["attestation"]["gate_results"][0]["observed"], 9000)

    def test_bridge_can_emit_standalone_attestation_with_bound_evaluation_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = self.fixture(root)
            bridge_path = root / "bridge.json"
            attestation_path = root / "attestation.json"
            result = bridge.build_attestation(
                f["prereg"], f["study"], f["score"], f["analysis"], f["owner"], f["decision"],
                f["analysis_source"], f["decision_source"], f["workload"], f["host"], f["candidate"],
                "attestation-standalone", 1000, None, None, bridge_path, attestation_path,
            )
            self.assertEqual(bridge.load_object(attestation_path), result["attestation"])
            self.assertEqual(
                result["evaluation_package_sha256"],
                bridge.canonical_sha256(result["evaluation_package"]),
            )
            self.assertEqual(
                result["attestation"]["evidence"]["evaluation_package_sha256"],
                result["evaluation_package_sha256"],
            )
            self.assertEqual(
                result["evaluation_package"]["questions_sha256"],
                f["study_record"]["questions_sha256"],
            )
            self.assertEqual(
                result["evaluation_package"]["readiness_report_sha256"],
                f["score_record"]["readiness_report_sha256"],
            )

    def test_ineligible_decision_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = self.fixture(root)
            record = f["decision_record"]
            record["generic_attestation_eligible"] = False
            record["status"] = "inconclusive"
            self.write_obj(f["decision"], record)
            with self.assertRaisesRegex(bridge.AttestationBridgeError, "not eligible"):
                self.call(f, root / "bridge.json")

    def test_study_candidate_binding_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = self.fixture(root)
            candidate = bridge.load_object(f["candidate"])
            candidate["policy_id"] = "tampered-integrated-policy"
            self.write_obj(f["candidate"], candidate)
            with self.assertRaisesRegex(bridge.AttestationBridgeError, "artifact binding drift"):
                self.call(f, root / "bridge.json")

    def test_workload_empirical_gate_is_recomputed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = self.fixture(root)
            score = f["score_record"]
            score["arms"]["integrated"]["metrics"]["task_accuracy"] = 7000
            self.write_obj(f["score"], score)
            analysis = bridge.load_object(f["analysis"])
            analysis["score_sha256"] = bridge.sha256(f["score"])
            self.write_obj(f["analysis"], analysis)
            owner = bridge.load_object(f["owner"])
            owner["analysis_report_sha256"] = bridge.sha256(f["analysis"])
            self.write_obj(f["owner"], owner)
            decision = f["decision_record"]
            decision["score_sha256"] = bridge.sha256(f["score"])
            decision["analysis_report_sha256"] = bridge.sha256(f["analysis"])
            decision["owner_decision_sha256"] = bridge.sha256(f["owner"])
            self.write_obj(f["decision"], decision)
            with self.assertRaisesRegex(bridge.AttestationBridgeError, "empirical gate"):
                self.call(f, root / "bridge.json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
