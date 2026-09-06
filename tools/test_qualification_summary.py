import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = ROOT / "benchmarks"
if str(BENCHMARKS) not in sys.path:
    sys.path.insert(0, str(BENCHMARKS))

from run_qualification import aggregate  # noqa: E402


BOOL_FIELDS = (
    "lane_selection",
    "tool_use_recognition",
    "tool_call_validity",
    "operation_selection",
    "argument_extraction",
    "core_status_correct",
    "result_fidelity",
    "failure_fidelity",
    "malformed_output",
    "incorrect_numeric_answer",
    "token_limit",
)


def record(arm, correct, input_tokens, model_ms):
    value = {
        "arm": arm,
        "final_answer_correct": correct,
        "input_tokens": input_tokens,
        "output_tokens": 10,
        "model_latency_ms": model_ms,
        "core_latency_ms": 1.0 if arm != "A" else None,
    }
    for key in BOOL_FIELDS:
        value[key] = False if key in ("malformed_output", "incorrect_numeric_answer", "token_limit") else True
    return value


class QualificationSummaryTests(unittest.TestCase):
    def test_efficiency_metrics_use_model_only_deltas_and_frozen_surface_bytes(self):
        records = [
            record("A", False, 100, 1000.0),
            record("A", True, 100, 1000.0),
            record("C", True, 200, 1200.0),
            record("C", True, 200, 1200.0),
            record("D", True, 300, 1500.0),
            record("D", False, 300, 1500.0),
        ]
        prereg = {
            "model_interface": {
                "requested": "auto",
                "resolved": "constrained_json",
                "mode": "constrained_json",
                "selection_phase": "pre-inference",
                "selection_reason": "native tool capabilities absent or unknown",
            },
            "capabilities": {
                "C": {"model_surface_bytes_total": 1000},
                "D": {"model_surface_bytes_total": 2000},
            },
        }
        summary = aggregate(records, prereg)
        self.assertEqual(summary["model_interface"]["requested"], "auto")
        self.assertEqual(summary["model_interface"]["resolved"], "constrained_json")
        self.assertEqual(summary["uplift"]["C_minus_A"], 0.5)
        self.assertEqual(summary["uplift"]["D_minus_A"], 0.0)
        self.assertEqual(summary["efficiency"]["C"]["added_input_tokens_mean"], 100.0)
        self.assertEqual(summary["efficiency"]["C"]["added_model_latency_ms_mean"], 200.0)
        self.assertEqual(summary["efficiency"]["C"]["uplift_per_added_input_token"], 0.005)
        self.assertEqual(summary["efficiency"]["C"]["uplift_per_model_surface_byte"], 0.0005)
        self.assertEqual(summary["efficiency"]["C"]["uplift_per_added_model_latency_ms"], 0.0025)
        self.assertEqual(summary["efficiency"]["D"]["uplift_per_added_input_token"], 0.0)


if __name__ == "__main__":
    unittest.main()
