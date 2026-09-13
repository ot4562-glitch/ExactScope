#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "tools", ROOT / "benchmarks", ROOT / "adapters/llama-cpp"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import harness_distillation_stage1 as stage1  # noqa: E402


class HarnessDistillationStage1Tests(unittest.TestCase):
    def record(self, item_id: str, policy_id: str, value: str, cost: int) -> dict:
        return {
            "item_id": item_id,
            "policy_id": policy_id,
            "valid": True,
            "value": value,
            "raw_content": '{"answer":"x"}',
            "prompt_tokens": 10,
            "completion_tokens": 2,
            "e2e_latency_ms": cost,
            "exactscope_cpu_ms": 1,
            "evidence_bytes": 20,
            "evidence_sha256": "0" * 64,
            "emitted_ids": [],
            "retrieval_query": "q",
            "top_k": 4,
            "projection_id": "test",
            "prompt_profile": "full",
            "model_calls": 1,
        }

    def test_calibration_selects_paired_safe_p_and_cheaper_aggregate_t(self):
        gold = {"i1": "SUPPORTS", "i2": "REFUTES", "i3": "NOT ENOUGH INFO"}
        policy_ids = ["Base", "integrated", "paired-safe", "aggregate-cheaper"]
        answers = {
            "Base": ["SUPPORTS", "SUPPORTS", "SUPPORTS"],
            "integrated": ["SUPPORTS", "REFUTES", "SUPPORTS"],
            "paired-safe": ["SUPPORTS", "REFUTES", "SUPPORTS"],
            "aggregate-cheaper": ["SUPPORTS", "SUPPORTS", "NOT ENOUGH INFO"],
        }
        costs = {"Base": 8, "integrated": 10, "paired-safe": 7, "aggregate-cheaper": 5}
        records = [
            self.record(item_id, policy_id, answers[policy_id][index], costs[policy_id])
            for index, item_id in enumerate(gold)
            for policy_id in policy_ids
        ]
        rows, selection, resources = stage1.score_calibration_records(
            records,
            gold=gold,
            policy_ids=policy_ids,
            cost_model={"integer_coefficients": {"e2e_latency_ms": 1}},
        )
        self.assertEqual(selection, {"outcome": "CompiledCandidate", "P": "paired-safe", "T": "aggregate-cheaper"})
        by_id = {row["policy_id"]: row for row in rows}
        self.assertEqual(by_id["paired-safe"]["reference_loss_count"], 0)
        self.assertEqual(by_id["aggregate-cheaper"]["reference_loss_count"], 1)
        self.assertLess(resources["aggregate-cheaper"]["serving_cost"], resources["paired-safe"]["serving_cost"])

    def test_heldout_summary_deduplicates_identical_logical_arms(self):
        gold = {"i1": "SUPPORTS", "i2": "REFUTES"}
        policy_ids = ["Base", "integrated", "paired-safe"]
        records = []
        for item_id, expected in gold.items():
            for policy_id in policy_ids:
                records.append(self.record(item_id, policy_id, expected, 10))
        summary = stage1.build_heldout_summary(
            records,
            gold=gold,
            logical_policy_ids=["Base", "integrated", "paired-safe", "paired-safe"],
            selection={"outcome": "CompiledCandidate", "P": "paired-safe", "T": "paired-safe"},
            cost_model={"integer_coefficients": {"e2e_latency_ms": 1}},
        )
        self.assertEqual(set(summary["serving_cost"]), {"Base", "integrated", "paired-safe"})
        self.assertEqual(summary["serving_cost"]["paired-safe"], 20)
        self.assertEqual(summary["paired_by_policy"]["paired-safe"], {"g": 0, "b": 0, "r": 0})

    def test_invalid_structured_output_is_a_mandatory_violation(self):
        record = self.record("i1", "Base", "SUPPORTS", 10)
        record["valid"] = False
        self.assertTrue(stage1._mandatory_violation(record))


if __name__ == "__main__":
    unittest.main(verbosity=2)
