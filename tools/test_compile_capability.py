"""Adversarial and reproducibility tests for the build-time profile boundary."""
import copy
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from compile_capability import (ROOT, canonical, compile_profile, load, validate,
                                verify_bundle, write_bundle)


class CompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = load((ROOT / "spec/examples/statistics-capability-profile.json").read_bytes())
        executable = "exactscope-packc.exe" if __import__("os").name == "nt" else "exactscope-packc"
        cls.packc = ROOT / "target/debug" / executable
        cls.bundle = compile_profile(canonical(cls.source), cls.packc)

    def test_order_and_whitespace_do_not_change_identity(self):
        source = copy.deepcopy(self.source)
        source["task_families"].reverse()
        source["runtime_surface"]["xs_eval"]["operations"].reverse()
        self.assertEqual(self.bundle, compile_profile(canonical(source), self.packc))

    def test_bad_semantics_fail_closed(self):
        changes = [
            ("support", "benchmarked"), ("domain", "unknown"),
            ("task_families", ["made-up"]),
        ]
        for key, value in changes:
            source = copy.deepcopy(self.source)
            source[key] = value
            with self.assertRaises(ValueError):
                validate(source)
        for key, value in [("semantic_operation_count", 7), ("request_bytes_max", 1024),
                           ("plan_steps_max", 7), ("normal_model_turns_max", 2)]:
            source = copy.deepcopy(self.source)
            source["model_budget"][key] = value
            with self.assertRaises(ValueError):
                validate(source)

    def test_duplicate_unknown_keys_and_binding_spoofs(self):
        with self.assertRaises(ValueError):
            load('{"x":1,"x":2}')
        source = copy.deepcopy(self.source)
        source["extra"] = 1
        with self.assertRaises(Exception):
            validate(source)
        source = copy.deepcopy(self.source)
        source["bindings"]["abi_revision"] = "99"
        with self.assertRaises(ValueError):
            validate(source)

    def test_actual_budget_and_revision_change(self):
        source = copy.deepcopy(self.source)
        source["model_budget"]["schema_bytes_max"] = 10
        with self.assertRaisesRegex(ValueError, "exceeds budget"):
            compile_profile(canonical(source), self.packc)
        source = copy.deepcopy(self.source)
        source["profile_revision"] += 1
        self.assertNotEqual(self.bundle["bundle-sha256.txt"],
                            compile_profile(canonical(source), self.packc)["bundle-sha256.txt"])

    def test_schema_is_operation_specific(self):
        schema = load(self.bundle["xs-eval.tool.json"])["function"]["parameters"]
        validator = Draft202012Validator(schema)
        self.assertTrue(validator.is_valid({"op": "stats.mean", "a": [["1", "2"]]}))
        self.assertTrue(validator.is_valid({"op": "stats.mean", "a": [[]]}))
        for call in [{"op": "stats.mean", "a": ["1"]},
                     {"op": "stats.mean", "a": [["1"], ["2"]]},
                     {"op": "stats.mean.weighted", "a": [["1"]]},
                     {"op": "stats.mean", "a": [["1"] * 65]},
                     {"op": "stats.mean", "a": [[1]]}]:
            self.assertFalse(validator.is_valid(call), call)

    def test_immutable_write_and_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "bundle"
            write_bundle(self.bundle, output)
            write_bundle(self.bundle, output)
            verify_bundle(output)
            (output / "profile.json").write_text("{}")
            with self.assertRaises(ValueError):
                verify_bundle(output)
            with self.assertRaises(ValueError):
                write_bundle(self.bundle, output)

    def test_checked_in_drift(self):
        output = ROOT / "adapters/capabilities/statistics-core-8-ai-r6"
        self.assertEqual(self.bundle, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_requirements_select_minimal_task_surface(self):
        request = load((ROOT / "spec/examples/statistics-capability-request.json").read_bytes())
        request["task_families"] = ["weighted-mean"]
        bundle = compile_profile(canonical(request), self.packc)
        profile = load(bundle["profile.json"])
        self.assertEqual(profile["runtime_surface"]["xs_eval"]["operations"], ["stats.mean.weighted"])
        self.assertEqual(profile["model_budget"]["semantic_operation_count"], 1)
        self.assertIn("xs-calc.contract.json", bundle)
        request["task_families"] = ["unknown"]
        with self.assertRaises(ValueError):
            compile_profile(canonical(request), self.packc)


if __name__ == "__main__":
    unittest.main()
