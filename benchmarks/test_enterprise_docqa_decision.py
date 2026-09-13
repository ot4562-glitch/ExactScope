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
import enterprise_docqa_decision as decision
import enterprise_docqa_score as scorer
import enterprise_docqa_study_contract as study_contract


class DecisionTests(unittest.TestCase):
    def write_obj(self, path, value):
        path.write_bytes(canonical_bytes(value))

    def fixture(self, root: Path):
        analysis_source = root / "analysis.py"
        analysis_source.write_text("print('analysis')\n", encoding="utf-8")
        frozen_analysis = {
            "estimand": "paired owner-accepted utility and total economics",
            "sampling_design": "group-disjoint fixed confirmatory sample",
            "uncertainty_method": "frozen paired exact method",
            "method_id": "paired-exact-v1",
            "method_parameters": {"family": "external-reference"},
            "sample_size_rationale": "prospective precision calculation",
            "stopping_rule": "one fixed sample",
            "missing_invalid_rule": "invalid rows fail qualification",
            "confirmatory_sample_size": 10,
            "all_thresholds_frozen": True,
            "post_score_extension_allowed": False,
            "confirmatory_thresholds": [
                {"name": "task_accuracy_min", "value": 8000, "unit": "basis-points", "owner_approved": True}
            ],
        }
        prereg = {
            "format": "exactscope.enterprise-docqa-preregistration",
            "format_version": "0.1",
            "workload_id": "enterprise-policy-qa-v1",
            "records": {"analysis": frozen_analysis},
        }
        prereg_path = root / "prereg.json"
        self.write_obj(prereg_path, prereg)
        study = {
            "format": study_contract.FORMAT,
            "format_version": "0.1",
            "state": "frozen-unscored",
            "preregistration_sha256": decision.sha256(prereg_path),
            "questions_sha256": "1" * 64,
            "confirmatory_question_count": 10,
            "analysis_source_sha256": decision.sha256(analysis_source),
            "decision_source_sha256": decision.sha256(Path(decision.__file__)),
            "ordinary_alternative_required": True,
            "confirmatory_outcomes_visible_at_freeze": False,
            "post_score_rule_changes_allowed": False,
        }
        study_path = root / "study.json"
        self.write_obj(study_path, study)
        score = {
            "format": scorer.SCORE_FORMAT,
            "format_version": "0.1",
            "study_contract_sha256": decision.sha256(study_path),
            "preregistration_sha256": decision.sha256(prereg_path),
            "integrated_gate_verdict": "GATES_PASSED_CANDIDATE",
            "commercial_comparison": "INTEGRATED_LOWEST_FROZEN_COST",
            "qualified_execution_profile_emitted": False,
        }
        score_path = root / "score.json"
        self.write_obj(score_path, score)
        analysis = {
            "format": decision.ANALYSIS_FORMAT,
            "format_version": "0.1",
            "analysis_id": "analysis-1",
            "method_identity": "paired-exact-v1",
            "score_sha256": decision.sha256(score_path),
            "preregistration_sha256": decision.sha256(prereg_path),
            "study_contract_sha256": decision.sha256(study_path),
            "analysis_source_sha256": decision.sha256(analysis_source),
            "analysis_record_sha256": decision.digest_object(frozen_analysis),
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
            "format": decision.OWNER_FORMAT,
            "format_version": "0.1",
            "decision_id": "owner-decision-1",
            "authority_id": "policy-owner-1",
            "workload_id": "enterprise-policy-qa-v1",
            "analysis_report_sha256": decision.sha256(analysis_path),
            "owner_approved": True,
            "customer_utility_accepted": True,
            "total_economics_accepted": True,
            "ordinary_alternative_considered": True,
            "no_post_score_exception": True,
        }
        owner_path = root / "owner.json"
        self.write_obj(owner_path, owner)
        return prereg_path, study_path, score_path, analysis_path, owner_path, analysis_source, analysis, owner, score

    def test_full_pass_becomes_generic_attestation_eligible_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, study, score, analysis, owner, analysis_source, *_rest = self.fixture(root)
            result = decision.decide(prereg, study, score, analysis, analysis_source, owner, root / "decision.json")
            self.assertEqual(result["status"], "qualified")
            self.assertTrue(result["generic_attestation_eligible"])
            self.assertFalse(result["qualified_execution_profile_emitted"])

    def test_alternative_failure_makes_decision_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, study, score, analysis_path, owner, _source, analysis, _owner, _score = self.fixture(root)
            analysis["integrated_vs_alternative"] = "fail"
            self.write_obj(analysis_path, analysis)
            owner_record = decision.load_object(owner)
            owner_record["analysis_report_sha256"] = decision.sha256(analysis_path)
            self.write_obj(owner, owner_record)
            result = decision.decide(prereg, study, score, analysis_path, _source, owner, root / "decision.json")
            self.assertEqual(result["status"], "failed")
            self.assertFalse(result["generic_attestation_eligible"])

    def test_uncertainty_inconclusive_stays_inconclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, study, score, analysis_path, owner, _source, analysis, _owner, _score = self.fixture(root)
            analysis["uncertainty_conclusive"] = False
            analysis["conclusion"] = "inconclusive"
            self.write_obj(analysis_path, analysis)
            owner_record = decision.load_object(owner)
            owner_record["analysis_report_sha256"] = decision.sha256(analysis_path)
            self.write_obj(owner, owner_record)
            result = decision.decide(prereg, study, score, analysis_path, _source, owner, root / "decision.json")
            self.assertEqual(result["status"], "inconclusive")

    def test_owner_rejection_fails_even_when_analysis_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, study, score, analysis, owner_path, _source, _analysis, owner, _score = self.fixture(root)
            owner["total_economics_accepted"] = False
            self.write_obj(owner_path, owner)
            result = decision.decide(prereg, study, score, analysis, _source, owner_path, root / "decision.json")
            self.assertEqual(result["status"], "failed")

    def test_analysis_source_identity_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, study, score, analysis_path, owner, _source, analysis, _owner, _score = self.fixture(root)
            analysis["analysis_source_sha256"] = "0" * 64
            self.write_obj(analysis_path, analysis)
            owner_record = decision.load_object(owner)
            owner_record["analysis_report_sha256"] = decision.sha256(analysis_path)
            self.write_obj(owner, owner_record)
            with self.assertRaisesRegex(decision.DecisionError, "analysis implementation identity drift"):
                decision.decide(prereg, study, score, analysis_path, _source, owner, root / "decision.json")

    def test_score_cannot_claim_profile_emission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prereg, study, score_path, analysis, owner, _source, _analysis, _owner, score = self.fixture(root)
            score["qualified_execution_profile_emitted"] = True
            self.write_obj(score_path, score)
            with self.assertRaisesRegex(decision.DecisionError, "illegally claims profile emission"):
                decision.decide(prereg, study, score_path, analysis, _source, owner, root / "decision.json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
