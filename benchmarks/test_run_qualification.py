from __future__ import annotations

import unittest
from pathlib import Path

from capability_surface import CapabilitySurface
from run_benchmark import Case
from run_qualification import (
    ModelReply,
    QualificationFailure,
    parse_json_strict,
    score_model_only,
    score_tool_reply,
    validate_calc_call,
    validate_eval_call,
)


def surface(*, calc: bool = False) -> CapabilitySurface:
    catalog = {
        "binding_sha256": "0" * 64,
        "operations": [
            {
                "op": "stats.mean",
                "revision": 1,
                "args": [{"name": "values", "shape": "vector", "semantic": "number"}],
            },
            {
                "op": "econ.gdp.deflator100",
                "revision": 1,
                "args": [
                    {"name": "nominal_gdp", "shape": "scalar", "semantic": "currency_amount"},
                    {"name": "real_gdp", "shape": "scalar", "semantic": "currency_amount"},
                ],
            },
        ],
    }
    profile = {
        "profile_id": "test",
        "profile_revision": 1,
        "runtime_surface": {
            "xs_eval": {"operations": ["stats.mean", "econ.gdp.deflator100"]},
            "xs_calc": {"enabled": calc},
        },
    }
    return CapabilitySurface(
        root=Path("."),
        manifest={},
        profile=profile,
        contract={"assets": []},
        catalog=catalog,
        prompt="test",
        tools={},
        grammars={},
        bundle_sha256="1" * 64,
        surface_contract_sha256="2" * 64,
        artifact_sha256="3" * 64,
    )


class FakeCore:
    def eval(self, call):
        self.last_eval = call
        return {"s": 0, "v": "2", "p": "statistics-core@0.1.0", "r": 1}, 0.01

    def call(self, mode, payload):
        self.last_call = (mode, payload)
        return {"s": 0, "v": "2", "f": 0, "p": "plan-v0.1", "r": 1}, 0.01


class QualificationValidationTests(unittest.TestCase):
    def test_duplicate_json_key_is_rejected(self):
        with self.assertRaises(QualificationFailure):
            parse_json_strict('{"op":"stats.mean","op":"other","a":[]}')

    def test_eval_validation_preserves_exact_shapes_and_decimal_strings(self):
        valid = validate_eval_call({"op": "stats.mean", "a": [["1", "2", "3"]]}, surface())
        self.assertEqual(valid, {"op": "stats.mean", "a": [["1", "2", "3"]]})
        with self.assertRaises(QualificationFailure):
            validate_eval_call({"op": "stats.mean", "a": [[1, "2"]]}, surface())
        with self.assertRaises(QualificationFailure):
            validate_eval_call({"op": "stats.mean", "a": [["01", "2"]]}, surface())
        with self.assertRaises(QualificationFailure):
            validate_eval_call({"op": "stats.mean", "a": [["1"] * 65]}, surface())

    def test_eval_validation_rejects_unknown_operation_and_wrong_arity(self):
        with self.assertRaises(QualificationFailure):
            validate_eval_call({"op": "stats.median", "a": [["1"]]}, surface())
        with self.assertRaises(QualificationFailure):
            validate_eval_call({"op": "econ.gdp.deflator100", "a": ["100"]}, surface())

    def test_calc_validation_enforces_backward_references_and_powi_bound(self):
        valid = validate_calc_call(
            {
                "p": [
                    {"o": "mul", "a": ["12", "7"]},
                    {"o": "sub", "a": ["#0", "4"]},
                    {"o": "div", "a": ["#1", "5"]},
                ]
            }
        )
        self.assertEqual(len(valid["p"]), 3)
        with self.assertRaises(QualificationFailure):
            validate_calc_call({"p": [{"o": "add", "a": ["#0", "1"]}]})
        with self.assertRaises(QualificationFailure):
            validate_calc_call({"p": [{"o": "powi", "a": ["2", "33"]}]})
        with self.assertRaises(QualificationFailure):
            validate_calc_call({"p": [{"o": "add", "a": ["1", "1"]}] * 9})

    def test_model_only_success_requires_exact_expected_decimal(self):
        case = Case(
            identifier="mean",
            domain="statistics-core",
            method="ordered",
            prompt="mean",
            expected_call={"op": "stats.mean", "a": [["1", "2", "3"]]},
            expected_core={"status": "OK", "value": "2"},
            should_fail=False,
        )
        reply = ModelReply(
            message={"content": '{"answer":"2","error":null}'},
            input_tokens=1,
            output_tokens=1,
            latency_ms=1.0,
            raw={},
        )
        self.assertTrue(score_model_only(case, reply)["final_answer_correct"])
        wrong = ModelReply(
            message={"content": '{"answer":"2.0","error":null}'},
            input_tokens=1,
            output_tokens=1,
            latency_ms=1.0,
            raw={},
        )
        self.assertFalse(score_model_only(case, wrong)["final_answer_correct"])

    def test_combined_calc_on_semantic_item_is_wrong_lane_even_if_numeric_matches(self):
        case = Case(
            identifier="mean",
            domain="statistics-core",
            method="ordered",
            prompt="mean",
            expected_call={"op": "stats.mean", "a": [["1", "2", "3"]]},
            expected_core={"status": "OK", "value": "2"},
            should_fail=False,
        )
        reply = ModelReply(
            message={
                "tool_calls": [
                    {
                        "type": "function",
                        "function": {
                            "name": "xs_calc",
                            "arguments": '{"p":[{"o":"add","a":["1","1"]}]}',
                        },
                    }
                ]
            },
            input_tokens=1,
            output_tokens=1,
            latency_ms=1.0,
            raw={},
        )
        result = score_tool_reply(
            case=case,
            reply=reply,
            surface=surface(calc=True),
            core=FakeCore(),
            arm="D",
        )
        self.assertEqual(result["selected_lane"], "xs_calc")
        self.assertFalse(result["lane_selection"])
        self.assertFalse(result["final_answer_correct"])
        self.assertTrue(result["incorrect_numeric_answer"])


if __name__ == "__main__":
    unittest.main()
