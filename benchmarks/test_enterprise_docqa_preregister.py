#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "tools", ROOT / "benchmarks"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import enterprise_docqa_preregister as docqa  # noqa: E402


class EnterpriseDocQAPreregisterTests(unittest.TestCase):
    def records(self, *, optimizer_enabled: bool = False) -> dict[str, dict]:
        records = {
            "workload": {
                "format": docqa.RECORD_FORMATS["workload"],
                "format_version": docqa.FORMAT_VERSION,
                "workload_id": "enterprise-policy-qa-v1",
                "owner_role": "document-policy owner",
                "owner_approved": True,
                "authorized_collection_identity": "policy-corpus-rev-7",
                "authority_revision_policy": "only approved revision 7 documents are authoritative",
                "question_classes": ["answerable", "unanswerable", "ambiguous-or-conflicting", "retrieval-stress"],
                "population_definition": "bounded employee policy questions derived independently of answer generation",
                "answer_contract": "short answer with cited source span or explicit abstention",
                "evidence_composition": "single-source-precision",
                "evidence_budget_bytes": 3072,
            },
            "retrieval": {
                "format": docqa.RECORD_FORMATS["retrieval"],
                "format_version": docqa.FORMAT_VERSION,
                "corpus_identity": "corpus-7",
                "retriever_identity": "host-retriever-3",
                "index_identity": "index-11",
                "query_rule_identity": "query-rule-2",
                "real_host_retrieval": True,
                "oracle_evidence": False,
                "gold_visible_to_runner": False,
                "top_k_limit": 8,
            },
            "partitions": {
                "format": docqa.RECORD_FORMATS["partitions"],
                "format_version": docqa.FORMAT_VERSION,
                "groups_disjoint": True,
                "confirmatory_uninspected": True,
                "grouping_rule": "same document revision or same target field stays in one group",
                "partitions": {
                    "development": {"identity": "dev-1", "count": 80},
                    "confirmatory": {"identity": "confirm-1", "count": 200},
                },
            },
            "competence": {
                "format": docqa.RECORD_FORMATS["competence"],
                "format_version": docqa.FORMAT_VERSION,
                "owner_approved": True,
                "all_gates_conjunctive": True,
                "gates": [
                    {"metric": "task_accuracy", "direction": "min", "threshold": 8000, "unit": "basis-points", "owner_approved": True},
                    {"metric": "unsupported_answer_rate", "direction": "max", "threshold": 200, "unit": "basis-points", "owner_approved": True},
                    {"metric": "format_violations", "direction": "zero", "threshold": 0, "unit": "count", "owner_approved": True},
                ],
                "unacceptable_error_definition": "confident answer contradicted by the authoritative document",
                "development_evidence_identity": "dev-competence-report-1",
                "base_development_eligible": True,
                "integrated_development_eligible": True,
            },
            "base": {
                "format": docqa.RECORD_FORMATS["base"],
                "format_version": docqa.FORMAT_VERSION,
                "config_id": "base-1",
                "model_identity": "model-a",
                "runtime_identity": "runtime-a",
                "tokenizer_template_identity": "template-a",
                "retrieval_identity": "host-retriever-3",
                "generation_settings_identity": "gen-a",
                "answer_policy_identity": "base-answer-policy",
                "max_model_calls": 1,
                "runtime_answer_repair": False,
                "second_model_judge": False,
                "adaptive_policy_routing": False,
            },
            "integrated": {
                "format": docqa.RECORD_FORMATS["integrated"],
                "format_version": docqa.FORMAT_VERSION,
                "config_id": "integrated-1",
                "model_identity": "model-a",
                "runtime_identity": "runtime-a",
                "tokenizer_template_identity": "template-a",
                "retrieval_identity": "host-retriever-3",
                "generation_settings_identity": "gen-a",
                "answer_policy_identity": "exactscope-integrated-policy-1",
                "evidence_composition": "single-source-precision",
                "evidence_policy_id": "precision-context-v5",
                "evidence_budget_bytes": 3072,
                "max_projected_items": 8,
                "max_model_calls": 1,
                "runtime_answer_repair": False,
                "second_model_judge": False,
                "adaptive_policy_routing": False,
            },
            "scorer": {
                "format": docqa.RECORD_FORMATS["scorer"],
                "format_version": docqa.FORMAT_VERSION,
                "mode": "hybrid",
                "rubric_identity": "rubric-4",
                "invalid_observation_rule": "missing output or identity drift invalidates the run; ordinary wrong answers remain failures",
                "repairs_answers": False,
                "runtime_model_judge": False,
                "adjudicator_role": "trained policy QA reviewer",
                "disagreement_resolution": "independent second reviewer then workload-owner tie break",
                "arm_blinded_where_practical": True,
            },
            "timing": {
                "format": docqa.RECORD_FORMATS["timing"],
                "format_version": docqa.FORMAT_VERSION,
                "hardware_identity": "host-a",
                "load_identity": "single-concurrency-qa-v1",
                "latency_boundary": "query receipt through finalized answer",
                "cache_policy": "same frozen host cache policy for both arms",
                "request_order": "precommitted deterministic counterbalanced arm order",
                "concurrency": 1,
                "outcome_dependent_reordering": False,
            },
            "economics": {
                "format": docqa.RECORD_FORMATS["economics"],
                "format_version": docqa.FORMAT_VERSION,
                "owner_approved": True,
                "double_count_reviewed": True,
                "unit": "internal cost unit",
                "avoidable_cost_interpretation": "one unit maps to approved avoidable serving/review capacity in this pilot",
                "components": [
                    {"name": "inference_ms", "counter": "model_service_ms", "coefficient": 1, "basis": "measured model service milliseconds"},
                    {"name": "human_review", "counter": "human_review_events", "coefficient": 100, "basis": "one workload-owner approved review event"},
                    {"name": "integration", "counter": "integration_units", "coefficient": 10, "basis": "pre-outcome fixed integration units"},
                    {"name": "qualification", "counter": "qualification_units", "coefficient": 10, "basis": "pre-outcome fixed qualification units"},
                    {"name": "refresh", "counter": "refresh_units", "coefficient": 10, "basis": "pre-outcome fixed refresh units"},
                    {"name": "maintenance", "counter": "maintenance_units", "coefficient": 10, "basis": "pre-outcome fixed maintenance units"},
                ],
                "fixed_counters_by_arm": {
                    "base": {"integration_units": 0, "qualification_units": 1, "refresh_units": 1, "maintenance_units": 1},
                    "integrated": {"integration_units": 2, "qualification_units": 2, "refresh_units": 1, "maintenance_units": 1},
                },
                "integration_cost_included": True,
                "qualification_cost_included": True,
                "refresh_cost_included": True,
                "maintenance_cost_included": True,
            },
            "analysis": {
                "format": docqa.RECORD_FORMATS["analysis"],
                "format_version": docqa.FORMAT_VERSION,
                "estimand": "paired difference in workload-owner accepted outcomes and total economic cost",
                "sampling_design": "group-disjoint simple random confirmatory sample",
                "uncertainty_method": "deterministic paired bootstrap lower bounds",
                "method_id": "paired-bootstrap-v1",
                "method_parameters": {
                    "bootstrap_seed": 20260913,
                    "bootstrap_resamples": 2000,
                    "confidence_bps": 9500,
                    "quality_noninferiority_margin_bps": 0,
                    "base_min_cost_savings_bps": 0,
                    "alternative_min_cost_savings_bps": 0,
                },
                "sample_size_rationale": "200 items chosen from a pre-score precision calculation for the owner gates",
                "stopping_rule": "one fixed confirmatory sample; no extension after outcomes",
                "missing_invalid_rule": "invalid protocol rows fail qualification and are not replaced outcome-dependently",
                "confirmatory_sample_size": 200,
                "all_thresholds_frozen": True,
                "post_score_extension_allowed": False,
                "confirmatory_thresholds": [
                    {"name": "task_accuracy_min", "value": 8000, "unit": "basis-points", "owner_approved": True},
                    {"name": "unsupported_answer_rate_max", "value": 200, "unit": "basis-points", "owner_approved": True},
                ],
            },
            "optimizer": {
                "format": docqa.RECORD_FORMATS["optimizer"],
                "format_version": docqa.FORMAT_VERSION,
                "enabled": optimizer_enabled,
                "disabled_reason": "primary study evaluates fixed Integrated versus Base" if not optimizer_enabled else "not used",
            },
        }
        if optimizer_enabled:
            records["optimizer"] = {
                "format": docqa.RECORD_FORMATS["optimizer"],
                "format_version": docqa.FORMAT_VERSION,
                "enabled": True,
                "reference_policy_id": "integrated-1",
                "selector_id": "reference-preserving-cost-v1",
                "conventional_tuner_id": "aggregate-quality-cost-v1",
                "economic_objective_identity": "econ-1",
                "candidate_policy_ids": ["base-1", "candidate-a", "integrated-1"],
                "cheaper_reference_materiality_bps": 1500,
                "heldout_rescue_allowed": False,
            }
            records["partitions"]["partitions"]["calibration"] = {"identity": "cal-1", "count": 80}
        return records

    def write_records(self, root: Path, records: dict[str, dict]) -> dict[str, Path]:
        paths = {}
        for role, value in records.items():
            path = root / f"{role}.json"
            path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True), encoding="utf-8")
            paths[role] = path
        return paths

    def test_valid_primary_study_without_optimizer_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_records(Path(tmp), self.records())
            records, optimizer_enabled = docqa.validate_records(paths)
        self.assertFalse(optimizer_enabled)
        self.assertEqual(records["workload"]["workload_id"], "enterprise-policy-qa-v1")

    def test_placeholder_threshold_is_rejected(self):
        records = self.records()
        records["competence"]["unacceptable_error_definition"] = "TBD by owner"
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_records(Path(tmp), records)
            with self.assertRaises(docqa.DocQAPreregistrationError):
                docqa.validate_records(paths)

    def test_oracle_retrieval_is_rejected(self):
        records = self.records()
        records["retrieval"]["oracle_evidence"] = True
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_records(Path(tmp), records)
            with self.assertRaises(docqa.DocQAPreregistrationError):
                docqa.validate_records(paths)

    def test_missing_workload_evidence_composition_is_rejected(self):
        records = self.records()
        del records["workload"]["evidence_composition"]
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_records(Path(tmp), records)
            with self.assertRaisesRegex(docqa.DocQAPreregistrationError, "evidence_composition"):
                docqa.validate_records(paths)

    def test_integrated_evidence_composition_must_match_workload(self):
        records = self.records()
        records["integrated"]["evidence_composition"] = "multi-source-coverage"
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_records(Path(tmp), records)
            with self.assertRaisesRegex(docqa.DocQAPreregistrationError, "composition differs"):
                docqa.validate_records(paths)

    def test_integrated_evidence_budget_must_match_workload(self):
        records = self.records()
        records["integrated"]["evidence_budget_bytes"] = 4096
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_records(Path(tmp), records)
            with self.assertRaisesRegex(docqa.DocQAPreregistrationError, "budget differs"):
                docqa.validate_records(paths)

    def test_integrated_projection_cap_cannot_exceed_retrieval_top_k(self):
        records = self.records()
        records["integrated"]["max_projected_items"] = 9
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_records(Path(tmp), records)
            with self.assertRaisesRegex(docqa.DocQAPreregistrationError, "exceeds retrieval top_k_limit"):
                docqa.validate_records(paths)

    def test_evidence_budget_below_contract_minimum_is_rejected(self):
        records = self.records()
        records["workload"]["evidence_budget_bytes"] = 128
        records["integrated"]["evidence_budget_bytes"] = 128
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_records(Path(tmp), records)
            with self.assertRaisesRegex(docqa.DocQAPreregistrationError, "between 256 and 1048576"):
                docqa.validate_records(paths)

    def test_missing_integrated_evidence_budget_is_rejected(self):
        records = self.records()
        del records["integrated"]["evidence_budget_bytes"]
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_records(Path(tmp), records)
            with self.assertRaisesRegex(docqa.DocQAPreregistrationError, "evidence_budget_bytes"):
                docqa.validate_records(paths)

    def test_economics_component_requires_executable_counter(self):
        records = self.records()
        del records["economics"]["components"][0]["counter"]
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_records(Path(tmp), records)
            with self.assertRaisesRegex(docqa.DocQAPreregistrationError, "executable counter"):
                docqa.validate_records(paths)

    def test_fixed_economics_cannot_redeclare_measured_counter(self):
        records = self.records()
        records["economics"]["fixed_counters_by_arm"]["integrated"]["model_service_ms"] = 1
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_records(Path(tmp), records)
            with self.assertRaisesRegex(docqa.DocQAPreregistrationError, "unsupported/non-fixed counter"):
                docqa.validate_records(paths)

    def test_known_composition_requires_matching_evidence_policy(self):
        records = self.records()
        records["integrated"]["evidence_policy_id"] = "multihop-coverage-v1"
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_records(Path(tmp), records)
            with self.assertRaisesRegex(docqa.DocQAPreregistrationError, "policy differs"):
                docqa.validate_records(paths)

    def test_paired_bootstrap_parameters_are_complete_and_bounded(self):
        records = self.records()
        del records["analysis"]["method_parameters"]["bootstrap_seed"]
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_records(Path(tmp), records)
            with self.assertRaisesRegex(docqa.DocQAPreregistrationError, "keys are incomplete"):
                docqa.validate_records(paths)
        records = self.records()
        records["analysis"]["method_parameters"]["bootstrap_resamples"] = 20001
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_records(Path(tmp), records)
            with self.assertRaisesRegex(docqa.DocQAPreregistrationError, "between 100 and 20000"):
                docqa.validate_records(paths)

    def test_unapproved_competence_gate_is_rejected(self):
        records = self.records()
        records["competence"]["gates"][0]["owner_approved"] = False
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_records(Path(tmp), records)
            with self.assertRaises(docqa.DocQAPreregistrationError):
                docqa.validate_records(paths)

    def test_optimizer_requires_calibration_partition(self):
        records = self.records(optimizer_enabled=True)
        del records["partitions"]["partitions"]["calibration"]
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_records(Path(tmp), records)
            with self.assertRaises(docqa.DocQAPreregistrationError):
                docqa.validate_records(paths)

    def test_preregister_binds_sources_and_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = self.write_records(root, self.records())
            runner = root / "runner.py"
            scorer = root / "scorer.py"
            runner.write_text("print('runner')\n", encoding="utf-8")
            scorer.write_text("print('scorer')\n", encoding="utf-8")
            output = root / "prereg.json"
            args = argparse.Namespace(
                **paths,
                runner_source=runner,
                scorer_source=scorer,
                output=output,
            )
            result = docqa.preregister_command(args)
            self.assertTrue(output.is_file())
            self.assertEqual(result["confirmatory_status"], "frozen-unscored")
            self.assertFalse(result["fever_stage1_heldout_reuse"])
            self.assertFalse(result["optimizer_branch_enabled"])
            self.assertEqual(result["primary_comparison"], {"base_config_id": "base-1", "integrated_config_id": "integrated-1"})
            self.assertEqual(
                result["evidence_contract"],
                {
                    "evidence_composition": "single-source-precision",
                    "evidence_policy_id": "precision-context-v5",
                    "evidence_budget_bytes": 3072,
                    "max_projected_items": 8,
                    "retrieval_top_k_limit": 8,
                },
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
