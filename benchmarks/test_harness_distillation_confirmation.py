#!/usr/bin/env python3
from __future__ import annotations

from math import comb
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "tools", ROOT / "benchmarks"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import harness_distillation_confirmation as confirmation  # noqa: E402


class HarnessDistillationConfirmationTests(unittest.TestCase):
    def row(self, policy_id, *, success, loss, cost, valid=True, gates=True):
        return {
            "policy_id": policy_id,
            "valid": valid,
            "mandatory_gates_pass": gates,
            "success_count": success,
            "reference_loss_count": loss,
            "serving_cost": cost,
        }

    def test_paired_selector_and_conventional_tuner_can_differ(self):
        rows = [
            self.row("Base", success=70, loss=10, cost=80),
            self.row("integrated", success=80, loss=0, cost=100),
            self.row("paired-safe", success=80, loss=0, cost=75),
            self.row("aggregate-cheaper", success=80, loss=1, cost=60),
        ]
        result = confirmation.select_stage1_policies(rows, "Base", "integrated")
        self.assertEqual(result, {"outcome": "CompiledCandidate", "P": "paired-safe", "T": "aggregate-cheaper"})

    def test_reference_only_is_a_stop_outcome(self):
        rows = [
            self.row("Base", success=70, loss=10, cost=80),
            self.row("integrated", success=80, loss=0, cost=100),
            self.row("cheap-but-lossy", success=80, loss=1, cost=60),
        ]
        result = confirmation.select_stage1_policies(rows, "Base", "integrated")
        self.assertEqual(result, {"outcome": "ReferenceOnly", "P": None, "T": "cheap-but-lossy"})

    def test_incompetent_empirical_reference_stops(self):
        rows = [
            self.row("Base", success=80, loss=0, cost=80),
            self.row("integrated", success=79, loss=0, cost=100),
        ]
        result = confirmation.select_stage1_policies(rows, "Base", "integrated")
        self.assertEqual(result, {"outcome": "NoQualifiedReference", "P": None, "T": None})

    def test_selection_tie_break_is_cost_then_success_then_canonical_id(self):
        rows = [
            self.row("Base", success=60, loss=20, cost=90),
            self.row("integrated", success=80, loss=0, cost=100),
            self.row("z", success=81, loss=0, cost=70),
            self.row("b", success=82, loss=0, cost=70),
            self.row("a", success=82, loss=0, cost=70),
        ]
        result = confirmation.select_stage1_policies(rows, "Base", "integrated")
        self.assertEqual(result["P"], "a")
        self.assertEqual(result["T"], "a")

    def test_exact_lower_bound_inverts_upper_tail(self):
        N, n, x = 40, 12, 5
        K = confirmation.hypergeometric_lower_count_bound(N, n, x)
        denominator = comb(N, n)
        tail = confirmation._hypergeom_numerator_sum(N, K, n, x, n)
        self.assertGreater(tail * confirmation.ALPHA_DENOMINATOR, denominator)
        if K > x:
            previous = confirmation._hypergeom_numerator_sum(N, K - 1, n, x, n)
            self.assertLessEqual(previous * confirmation.ALPHA_DENOMINATOR, denominator)

    def test_exact_upper_bound_inverts_lower_tail(self):
        N, n, x = 40, 12, 2
        K = confirmation.hypergeometric_upper_count_bound(N, n, x)
        denominator = comb(N, n)
        cdf = confirmation._hypergeom_numerator_sum(N, K, n, 0, x)
        self.assertGreater(cdf * confirmation.ALPHA_DENOMINATOR, denominator)
        maximum_feasible = N - n + x
        if K < maximum_feasible:
            next_cdf = confirmation._hypergeom_numerator_sum(N, K + 1, n, 0, x)
            self.assertLessEqual(next_cdf * confirmation.ALPHA_DENOMINATOR, denominator)

    def test_exact_bound_extremes(self):
        self.assertEqual(confirmation.hypergeometric_lower_count_bound(50, 20, 0), 0)
        self.assertEqual(confirmation.hypergeometric_upper_count_bound(50, 20, 20), 50)

    def test_three_stage1_verdicts_are_reported_separately(self):
        prereg = {
            "calibration_split_digest": "cal",
            "held_out_split_digest": "held",
            "held_out_frame_sha256": "frame",
            "baseline_policy_id": "Base",
            "reference_policy_id": "integrated",
            "held_out_items": 100,
            "held_out_frame_count": 100,
        }
        rows = [
            self.row("Base", success=70, loss=10, cost=90),
            self.row("integrated", success=80, loss=0, cost=100),
            self.row("paired-safe", success=80, loss=0, cost=75),
            self.row("aggregate-cheaper", success=80, loss=1, cost=60),
        ]
        report = {
            "format": confirmation.REPORT_FORMAT,
            "format_version": confirmation.ANALYSIS_VERSION,
            "calibration_split_digest": "cal",
            "held_out_split_digest": "held",
            "held_out_frame_sha256": "frame",
            "calibration_policy_rows": rows,
            "selection": {"outcome": "CompiledCandidate", "P": "paired-safe", "T": "aggregate-cheaper"},
            "held_out": {
                "sample_size": 100,
                "finite_frame_size": 100,
                "paired_by_policy": {
                    "paired-safe": {"g": 10, "b": 0, "r": 0},
                    "aggregate-cheaper": {"g": 10, "b": 0, "r": 0},
                },
                "serving_cost": {"Base": 90, "integrated": 100, "paired-safe": 80, "aggregate-cheaper": 90},
                "p95_latency_ms": {"Base": 100, "integrated": 100, "paired-safe": 100, "aggregate-cheaper": 100},
                "mandatory_violations": {"Base": 0, "integrated": 0, "paired-safe": 0, "aggregate-cheaper": 0},
            },
        }
        result = confirmation.evaluate_stage1_report(report, prereg)
        self.assertEqual(result["narrow_selector_verdict"], "PASS")
        self.assertEqual(result["product_verdict"], "PASS")
        self.assertEqual(result["incremental_selector_verdict"], "FAVORS_P_DESCRIPTIVELY")
        self.assertEqual(result["T_evaluation"]["product_verdict"], "FAIL")

    def test_diagnostic_only_competence_cannot_emit_product_qualification(self):
        prereg = {
            "calibration_split_digest": "cal",
            "held_out_split_digest": "held",
            "held_out_frame_sha256": "frame",
            "baseline_policy_id": "Base",
            "reference_policy_id": "integrated",
            "held_out_items": 100,
            "held_out_frame_count": 100,
            "protocol_records": {
                "competence": {
                    "product_inference_allowed": False,
                }
            },
        }
        rows = [
            self.row("Base", success=70, loss=10, cost=90),
            self.row("integrated", success=80, loss=0, cost=100),
            self.row("paired-safe", success=80, loss=0, cost=75),
            self.row("aggregate-cheaper", success=80, loss=1, cost=60),
        ]
        report = {
            "format": confirmation.REPORT_FORMAT,
            "format_version": confirmation.ANALYSIS_VERSION,
            "calibration_split_digest": "cal",
            "held_out_split_digest": "held",
            "held_out_frame_sha256": "frame",
            "calibration_policy_rows": rows,
            "selection": {"outcome": "CompiledCandidate", "P": "paired-safe", "T": "aggregate-cheaper"},
            "held_out": {
                "sample_size": 100,
                "finite_frame_size": 100,
                "paired_by_policy": {
                    "paired-safe": {"g": 10, "b": 0, "r": 0},
                    "aggregate-cheaper": {"g": 10, "b": 0, "r": 0},
                },
                "serving_cost": {"Base": 90, "integrated": 100, "paired-safe": 80, "aggregate-cheaper": 90},
                "p95_latency_ms": {"Base": 100, "integrated": 100, "paired-safe": 100, "aggregate-cheaper": 100},
                "mandatory_violations": {"Base": 0, "integrated": 0, "paired-safe": 0, "aggregate-cheaper": 0},
            },
        }
        result = confirmation.evaluate_stage1_report(report, prereg)
        self.assertEqual(result["narrow_selector_verdict"], "PASS")
        self.assertEqual(result["product_gate_verdict"], "PASS")
        self.assertEqual(result["product_verdict"], "NOT_AUTHORIZED_ALGORITHM_DIAGNOSTIC_ONLY")
        self.assertEqual(result["verdict"], "ALGORITHM_DIAGNOSTIC_ONLY")
        self.assertFalse(result["qualification_passed"])

    def test_preflight_exact_gate_resolution_for_frozen_3573_by_600_frame(self):
        record = confirmation.build_preflight_record({
            "held_out_frame_count": 3573,
            "held_out_count": 600,
            "held_out_frame_sha256": "frame",
            "held_out_split_digest": "held",
            "grouping_policy": "group-v2",
            "held_out_sampling_method": "srs-v1",
        })
        self.assertTrue(record["preflight_passed"])
        self.assertEqual(record["reference_regression_pass_region"]["maximum_r_count_passing"], 5)
        one_percent = next(
            row for row in record["base_improvement_pass_regions"]
            if row["base_only_loss_scenario_bps"] == 100
        )
        self.assertEqual(one_percent["b_count"], 6)
        self.assertEqual(one_percent["minimum_g_count_passing"], 43)
        self.assertLessEqual(one_percent["minimum_observed_net_gain_bps"], 700)

    def test_competence_record_requires_explicit_diagnostic_or_established_floor(self):
        diagnostic = {
            "baseline_policy_id": "Base",
            "reference_policy_id": "integrated",
            "classification": "algorithm-diagnostic-only",
            "product_inference_allowed": False,
            "task_utility_floor": {"status": "not-established"},
            "preexisting_evidence": ["historical 6+6 is insufficient for an absolute competence floor"],
            "diagnostic_reason": "No defensible absolute B/F task-utility floor exists before fresh Stage 1 scoring.",
        }
        confirmation._validate_competence_record(diagnostic)
        invalid = dict(diagnostic)
        invalid["product_inference_allowed"] = True
        with self.assertRaises(confirmation.ConfirmationError):
            confirmation._validate_competence_record(invalid)

    def test_stop_outcome_must_not_consume_heldout(self):
        prereg = {
            "calibration_split_digest": "cal",
            "held_out_split_digest": "held",
            "held_out_frame_sha256": "frame",
            "baseline_policy_id": "Base",
            "reference_policy_id": "integrated",
            "held_out_items": 20,
            "held_out_frame_count": 50,
        }
        rows = [
            self.row("Base", success=10, loss=2, cost=80),
            self.row("integrated", success=12, loss=0, cost=100),
            self.row("lossy", success=12, loss=1, cost=60),
        ]
        report = {
            "format": confirmation.REPORT_FORMAT,
            "format_version": confirmation.ANALYSIS_VERSION,
            "calibration_split_digest": "cal",
            "held_out_split_digest": "held",
            "held_out_frame_sha256": "frame",
            "calibration_policy_rows": rows,
            "selection": {"outcome": "ReferenceOnly", "P": None, "T": "lossy"},
            "held_out": None,
        }
        result = confirmation.evaluate_stage1_report(report, prereg)
        self.assertEqual(result["verdict"], "ReferenceOnly")
        report["held_out"] = {"sample_size": 20}
        with self.assertRaises(confirmation.ConfirmationError):
            confirmation.evaluate_stage1_report(report, prereg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
