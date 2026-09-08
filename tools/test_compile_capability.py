"""Adversarial and reproducibility tests for the build-time profile boundary."""
import copy
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from compile_capability import (ROOT, canonical, compile_profile, load, specialization_features,
                                statistics_specialization_features, validate, verify_bundle,
                                write_bundle)


class CompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = load((ROOT / "spec/examples/statistics-capability-profile-r27.json").read_bytes())
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

    def test_model_surface_contract_is_explicit_and_digest_bound(self):
        contract = load(self.bundle["surface-contract.json"])
        profile = load(self.bundle["profile.json"])
        self.assertEqual(contract["format"], "exactscope.model-surface.contract")
        self.assertEqual(contract["format_version"], "0.1")
        self.assertEqual(contract["negotiation"], "exact-version-and-digest")
        self.assertEqual(contract["profile"], {
            "id": profile["profile_id"],
            "revision": profile["profile_revision"],
            "domain": profile["domain"],
        })
        self.assertEqual(contract["abi_revision"], profile["bindings"]["abi_revision"])
        self.assertEqual(contract["hotset"]["binding_sha256"], profile["bindings"]["hotset_sha256"])
        self.assertEqual(
            [asset["path"] for asset in contract["assets"]],
            [
                "constrained-prompt.txt",
                "prompt-fragment.txt",
                "xs-calc.gbnf",
                "xs-calc.tool.json",
                "xs-eval.gbnf",
                "xs-eval.tool.json",
                "xs-request.gbnf",
            ],
        )

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

    def test_clean_source_generation_is_reproducible(self):
        # Release source intentionally excludes mutable generated capability bundles.
        # Reproducibility therefore has to be proven from reviewed inputs and the
        # compiler, not by comparing against a checked-in generated directory.
        rebuilt = compile_profile(canonical(copy.deepcopy(self.source)), self.packc)
        self.assertEqual(self.bundle, rebuilt)
        self.assertIn("surface-contract.json", self.bundle)
        profile = load(self.bundle["profile.json"])
        self.assertRegex(profile["bindings"]["surface_contract_sha256"], r"^[a-f0-9]{64}$")
        self.assertRegex(profile["bindings"]["core_revision"], r"^sha256:[a-f0-9]{64}$")
        manifest = load(self.bundle["manifest.json"])
        self.assertRegex(manifest["generator_sha256"], r"^[a-f0-9]{64}$")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "bundle"
            write_bundle(self.bundle, output)
            verify_bundle(output)

    def test_requirements_select_minimal_task_surface(self):
        request = load((ROOT / "spec/examples/statistics-capability-request-r27.json").read_bytes())
        request["task_families"] = ["weighted-mean"]
        request["specialization"] = "host-limited"
        bundle = compile_profile(canonical(request), self.packc)
        profile = load(bundle["profile.json"])
        self.assertEqual(profile["runtime_surface"]["xs_eval"]["operations"], ["stats.mean.weighted"])
        self.assertEqual(profile["model_budget"]["semantic_operation_count"], 1)
        self.assertIn("xs-calc.contract.json", bundle)
        request["task_families"] = ["unknown"]
        with self.assertRaises(ValueError):
            compile_profile(canonical(request), self.packc)

    def test_position_aware_calc_grammar_preserves_history_and_budget(self):
        grammar = self.bundle["xs-calc.gbnf"].decode()
        self.assertIn('v0 ::= dec', grammar)
        self.assertIn('v1 ::= v0 | "\\\"#0\\\""', grammar)
        self.assertIn('v7 ::= v6 | "\\\"#6\\\""', grammar)
        self.assertNotIn('#7', grammar)
        self.assertIn("xs-calc.grammar-source.json", self.bundle)
        total = len(self.bundle["xs-calc.gbnf"]) + len(self.bundle["xs-eval.gbnf"])
        self.assertLessEqual(total, self.source["model_budget"]["grammar_bytes_max"])

        historical = load((ROOT / "spec/examples/statistics-capability-profile.json").read_bytes())
        old_bundle = compile_profile(canonical(historical), self.packc)
        self.assertEqual(old_bundle["xs-calc.gbnf"],
                         (ROOT / "adapters/xs-calc-v0.1/xs-calc.gbnf").read_bytes())
        # Historical source inputs remain reviewable, but generated capability
        # directories are deliberately absent from the clean release source.
        self.assertEqual(old_bundle, compile_profile(canonical(copy.deepcopy(historical)), self.packc))

    def test_binary_specialization_derives_operation_features_and_memory_budget(self):
        profile = load(self.bundle["profile.json"])
        self.assertEqual(profile["runtime_surface"]["specialization"], "statistics-selected-wasm")
        self.assertEqual(profile["device_budget"]["wasm_stack_bytes_max"], 16384)
        self.assertEqual(profile["device_budget"]["wasm_initial_pages_max"], 1)
        self.assertEqual(profile["device_budget"]["wasm_maximum_pages_max"], 1)
        features = statistics_specialization_features(profile)
        self.assertEqual(features[:4], ("fused", "tinyjson", "stats-specialized", "selected-calc"))
        self.assertIn("stats-mean-weighted", features)
        self.assertNotIn("stats-cov-pop", features)
        for field, value in (("wasm_stack_bytes_max", 4096), ("wasm_initial_pages_max", 2),
                             ("wasm_maximum_pages_max", 2)):
            source = copy.deepcopy(self.source)
            source["device_budget"][field] = value
            with self.assertRaises(ValueError):
                validate(source)

        request = load((ROOT / "spec/examples/statistics-weighted-mean-capability-request-r5.json").read_bytes())
        weighted = load(compile_profile(canonical(request), self.packc)["profile.json"])
        self.assertEqual(weighted["runtime_surface"]["xs_eval"]["operations"], ["stats.mean.weighted"])
        self.assertEqual(
            statistics_specialization_features(weighted),
            ("fused", "tinyjson", "stats-specialized", "selected-calc", "stats-mean-weighted"),
        )

        legacy = copy.deepcopy(weighted)
        legacy["runtime_surface"]["specialization"] = "statistics-core-8-wasm"
        with self.assertRaisesRegex(ValueError, "exact reviewed eight-operation"):
            validate(legacy)

    def test_calc_only_specialized_baseline_has_no_semantic_assets(self):
        request = load((ROOT / "spec/examples/statistics-calc-only-capability-request-r2.json").read_bytes())
        bundle = compile_profile(canonical(request), self.packc)
        profile = load(bundle["profile.json"])
        self.assertEqual(profile["runtime_surface"]["xs_eval"]["operations"], [])
        self.assertEqual(profile["model_budget"]["semantic_operation_count"], 0)
        self.assertEqual(
            statistics_specialization_features(profile),
            ("fused", "tinyjson", "stats-specialized", "selected-calc"),
        )
        self.assertIn("xs-calc.tool.json", bundle)
        self.assertNotIn("xs-eval.tool.json", bundle)
        self.assertNotIn("xs-eval.gbnf", bundle)
        self.assertEqual(load(bundle["manifest.json"])["measurements"]["top_level_tool_count"], 1)

        for key, value in (
            ("specialization", "host-limited"),
            ("xs_calc", False),
            ("task_families", ["arithmetic-baseline", "weighted-mean"]),
        ):
            bad = copy.deepcopy(request)
            bad[key] = value
            with self.assertRaises(ValueError):
                compile_profile(canonical(bad), self.packc)

    def test_economics_second_domain_compiles_minimal_and_explicit_combined_surfaces(self):
        request = load((ROOT / "spec/examples/economics-ped-capability-request-r5.json").read_bytes())
        bundle = compile_profile(canonical(request), self.packc)
        profile = load(bundle["profile.json"])
        self.assertEqual(profile["domain"], "economics")
        self.assertEqual(profile["runtime_surface"]["xs_eval"]["operations"], ["econ.ped.mid"])
        self.assertFalse(profile["runtime_surface"]["xs_calc"]["enabled"])
        self.assertEqual(specialization_features(profile),
                         ("fused", "tinyjson", "econ-specialized", "econ-ped-mid"))
        measurements = load(bundle["manifest.json"])["measurements"]
        self.assertEqual(measurements["top_level_tool_count"], 1)
        self.assertEqual(measurements["visible_semantic_operation_count"], 1)
        self.assertEqual(measurements["native_prompt_bytes"], 129)
        self.assertGreater(measurements["constrained_prompt_bytes"], measurements["native_prompt_bytes"])
        self.assertEqual(
            measurements["prompt_fragment_bytes"],
            max(measurements["native_prompt_bytes"], measurements["constrained_prompt_bytes"]),
        )
        self.assertEqual(measurements["schema_bytes"], 811)
        self.assertEqual(measurements["native_grammar_bytes"], 411)
        self.assertGreater(
            measurements["constrained_request_grammar_bytes"],
            measurements["native_grammar_bytes"],
        )
        self.assertEqual(
            measurements["grammar_bytes"],
            max(measurements["native_grammar_bytes"], measurements["constrained_request_grammar_bytes"]),
        )
        self.assertIn(b"ws ::= [ \\t\\n\\r]{0,2}", bundle["xs-eval.gbnf"])
        self.assertNotIn(b"ws ::= [ \\t\\n\\r]*", bundle["xs-eval.gbnf"])
        self.assertNotIn("xs-calc.tool.json", bundle)

        combined = copy.deepcopy(request)
        combined["profile_revision"] += 1
        combined["xs_calc"] = True
        combined["model_visible_tools_max"] = 2
        combined["model_budget"]["plan_steps_max"] = 8
        combined_bundle = compile_profile(canonical(combined), self.packc)
        combined_profile = load(combined_bundle["profile.json"])
        self.assertEqual(
            specialization_features(combined_profile),
            ("fused", "tinyjson", "econ-specialized", "selected-calc", "econ-ped-mid"),
        )
        self.assertIn("xs-calc.tool.json", combined_bundle)

        wrong_domain_specialization = copy.deepcopy(request)
        wrong_domain_specialization["specialization"] = "statistics-selected-wasm"
        with self.assertRaises(ValueError):
            compile_profile(canonical(wrong_domain_specialization), self.packc)

    def test_release_size_gate_matches_declared_device_budget(self):
        from inspect_wasm import MAX_FUSED_BYTES
        self.assertEqual(MAX_FUSED_BYTES, self.source["device_budget"]["artifact_bytes_max"])


if __name__ == "__main__":
    unittest.main()
