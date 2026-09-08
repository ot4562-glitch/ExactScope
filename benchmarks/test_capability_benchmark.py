"""No model/credential required: corpus oracle, surface isolation and paired metrics."""
import copy
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from capability_benchmark import (ROOT, SingleWriterLock, aggregate, bind_runtime_evidence,
                                  final_matches, generation_budget, hydrate_model_config,
                                  managed_server_command, parse_reasoning_final, ratio, score,
                                  surface, verify_preregistered_run)
from build_capability_wasm import resolve_tool
from compile_capability import (canonical, compile_profile, constrained_request_grammar,
                                constrained_request_prompt, digest, load as load_json,
                                model_surface_contract, model_surface_measurements,
                                source_identity, verify_bundle,
                                write_bundle)
from run_benchmark import CoreBridge
from statistics_corpus import load, oracle, templates, validate_rows
from xs_calc_plan_fixtures import reference_plan


def write_bound_runtime_fixture(root, *, profile_id, revision, runtime_bytes, semantic=True):
    """Create a valid artifact-bound benchmark fixture from reviewed contract shapes only."""
    catalog = {
        "format": "exactscope.hotset",
        "format_version": "0.1",
        "abi": "1.0",
        "binding_sha256": "1" * 64,
        "packs": [{"id": "unit-pack", "version": "0.1"}],
        "operations": ([{"op": "stats.mean", "revision": 1, "sig": "stats.mean(xs[1..64])"}] if semantic else []),
    }
    files = {
        "catalog.json": canonical(catalog),
        "prompt-fragment.txt": b"Use the exact bound benchmark surface.\n",
        "task-map.json": canonical({"unit-family": (["stats.mean"] if semantic else [])}),
        "xs-calc.gbnf": b"root ::= \"{}\"\n",
        "xs-calc.tool.json": b'{"function":{"parameters":{"type":"object"}}}\n',
        "xs-calc.contract.json": canonical({"plan_id": "plan-v0.1", "plan_revision": 1}),
        "runtime.wasm": runtime_bytes,
    }
    if semantic:
        files["xs-eval.gbnf"] = b"root ::= \"{}\"\n"
        files["xs-eval.tool.json"] = b'{"function":{"parameters":{"type":"object"}}}\n'
    files["constrained-prompt.txt"] = constrained_request_prompt(catalog, include_calc=True)
    files["xs-request.gbnf"] = constrained_request_grammar(
        files.get("xs-eval.gbnf"), files.get("xs-calc.gbnf")
    )
    profile = {
        "profile_id": profile_id,
        "profile_revision": revision,
        "support": "experimental",
        "domain": "statistics",
        "task_families": ["unit-family"],
        "runtime_surface": {
            "specialization": "statistics-selected-wasm",
            "xs_calc": {"enabled": True, "plan_revision": "plan-v0.1"},
            "xs_eval": {"operations": (["stats.mean"] if semantic else [])},
            "xs_find": {"enabled": False},
            "model_visible_tools_max": 2 if semantic else 1,
            "normal_model_turns_max": 1,
        },
        "model_budget": {
            "semantic_operation_count": 1 if semantic else 0,
            "prompt_fragment_bytes_max": 4096,
            "schema_bytes_max": 4096,
            "grammar_bytes_max": 4096,
        },
        "device_budget": {
            "target_profile": "no-import-wasm",
            "artifact_bytes_max": 131072,
            "imports_max": 0,
            "wasm_stack_bytes_max": 16384,
            "wasm_initial_pages_max": 1,
            "wasm_maximum_pages_max": 1,
        },
        "bindings": {
            "core_revision": "sha256:" + source_identity(),
            "abi_revision": "1.0",
            "registry_sha256": digest(canonical(catalog["packs"])),
            "hotset_sha256": catalog["binding_sha256"],
            "artifact_sha256": digest(runtime_bytes),
        },
        "evidence": {
            "qualification_records": [],
            "model_result_bundles": [],
        },
    }
    schema_names = sorted(name for name in files if name.endswith(".tool.json"))
    grammar_names = sorted(name for name in files if name.endswith(".gbnf"))
    profile["bindings"]["tool_schema_sha256"] = digest(canonical({
        name: digest(files[name]) for name in schema_names
    }))
    profile["bindings"]["grammar_sha256"] = digest(canonical({
        name: digest(files[name]) for name in grammar_names
    }))
    profile["bindings"]["prompt_sha256"] = digest(canonical({
        "constrained-prompt.txt": digest(files["constrained-prompt.txt"]),
        "prompt-fragment.txt": digest(files["prompt-fragment.txt"]),
    }))
    contract_bytes = canonical(model_surface_contract(profile, catalog, files))
    profile["bindings"]["surface_contract_sha256"] = digest(contract_bytes)
    files["surface-contract.json"] = contract_bytes
    files["profile.json"] = canonical(profile)
    manifest = {
        "format": "exactscope.capability.bundle",
        "format_version": "0.1",
        "files": {name: digest(data) for name, data in sorted(files.items())},
        "measurements": model_surface_measurements(files, catalog),
        "operation_revisions": ({"stats.mean": 1} if semantic else {}),
        "artifact_status": "artifact and gold bound; experimental, not target-qualified",
        "artifact_measurements": {
            "bytes": len(runtime_bytes),
            "imports": 0,
            "initial_memory_pages": 1,
            "maximum_memory_pages": 1,
            "resident_bytes": None,
            "scratch_bytes": None,
        },
    }
    files["manifest.json"] = canonical(manifest)
    files["bundle-sha256.txt"] = (digest(files["manifest.json"]) + "\n").encode()
    write_bundle(files, root)
    verify_bundle(root)
    return root


class CapabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="xs-benchmark-tests-")
        cls.tmp = Path(cls._tmp.name)
        cargo = resolve_tool("cargo")
        subprocess.run([str(cargo), "build", "--locked", "-p", "exactscope-packc"],
                       cwd=ROOT, check=True, capture_output=True)
        subprocess.run([str(cargo), "build", "--locked", "-p", "exactscope-conformance",
                        "--bin", "exactscope-core"], cwd=ROOT, check=True, capture_output=True)
        suffix = ".exe" if os.name == "nt" else ""
        packc = ROOT / "target/debug" / ("exactscope-packc" + suffix)
        core_path = ROOT / "target/debug" / ("exactscope-core" + suffix)
        source = (ROOT / "spec/examples/statistics-capability-request-r27.json").read_bytes()
        cls.bundle = cls.tmp / "surface-bundle"
        write_bundle(compile_profile(source, packc), cls.bundle)
        verify_bundle(cls.bundle)
        cls.core = CoreBridge(core_path)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_corpus_matches_seed_and_real_runtime(self):
        rows = templates()
        self.assertEqual(len(rows), 240)
        self.assertEqual(rows, templates())
        self.assertNotEqual(rows, templates(17))
        validate_rows(rows, self.core)
        stored = [load(line) for line in (ROOT / "benchmarks/statistics-v0.1.jsonl").read_bytes().splitlines()]
        self.assertEqual(rows, stored)
        self.assertEqual(sum(r["state"] == "ambiguous" for r in rows), 15)
        # Two S5 templates also exercise constant-vector DOMAIN_ERROR.
        self.assertEqual(sum(r["state"] == "typed-failure" for r in rows), 17)

    def test_gold_tamper_is_not_silently_repaired(self):
        row = templates()[0]
        row["expected"]["v"] = "9999"
        with self.assertRaisesRegex(ValueError, "gold mismatch"):
            validate_rows([row], self.core)

    def test_independent_boundary_vectors(self):
        calls = [{"op": "stats.mean", "a": [[]]},
                 {"op": "stats.sum", "a": [["1"] * 64]},
                 {"op": "stats.mean.weighted", "a": [["1"], ["-1"]]},
                 {"op": "stats.corr.pearson", "a": [["2", "2"], ["1", "2"]]},
                 {"op": "stats.sd.sample", "a": [["1", "2", "3"]]}]
        for call in calls:
            expected = oracle(call)
            actual, _ = self.core.call("eval", call)
            self.assertTrue(all(actual.get(k) == v for k, v in expected.items()), (actual, expected))

    def test_arm_isolation_and_exact_error_fidelity(self):
        row = {"id": "test", "family": "S1", "state": "supported",
               "call": {"op": "stats.mean", "a": [["1", "3"]]}, "expected": {"s": 0, "v": "2"}}
        text = '{"op":"stats.mean","a":[["1","3"]]}'
        for arm in ("A", "B", "E"):
            record = score(row, text, surface(self.bundle, arm), self.core)
            self.assertFalse(record["valid_call"])
            self.assertIsNone(record["core_response"])
        for arm in ("C", "D"):
            self.assertTrue(score(row, text, surface(self.bundle, arm), self.core)["correct"])
        forbidden = '{"op":"econ.inflation.cpi_pct","a":["100","103"]}'
        self.assertFalse(score(row, forbidden, surface(self.bundle, "D"), self.core)["valid_call"])
        row.update(state="typed-failure", expected={"s": 13, "e": "DIVIDE_BY_ZERO"})
        failed = score(row, '{"p":[{"o":"div","a":["1","0"]}]}', surface(self.bundle, "D"), self.core)
        self.assertTrue(failed["correct"])
        self.assertTrue(failed["failure_fidelity"])
        self.assertFalse(failed["wrong_numeric"])

    def test_invalid_output_and_missing_method_preservation(self):
        row = next(r for r in templates() if r["state"] == "ambiguous")
        assets = surface(self.bundle, "D")
        for text in ('{"v":"NaN"}', '{"v":true}', '{"v":"1","v":"2"}', 'prose {"v":"1"}'):
            self.assertFalse(score(row, text, assets, self.core)["correct"])
        self.assertTrue(score(row, '{"e":"AMBIGUOUS_METHOD"}', assets, self.core)["correct"])
        self.assertTrue(score(row, '{"v":"1"}', surface(self.bundle, "A"), self.core)["wrong_numeric"])

    def records(self, with_e=True):
        rows = []
        for arm, values in {"A": [0, 0], "B": [0, 1], "C": [1, 0], "D": [1, 0], "E": [1, 1]}.items():
            if arm == "E" and not with_e:
                continue
            for i, value in enumerate(values):
                rows.append({"arm": arm, "id": str(i), "family": "S1", "correct": bool(value),
                             "wrong_numeric": not bool(value)})
        return rows

    def test_crr_density_and_raw_denominators(self):
        result = aggregate(self.records(), {"artifact_bytes": 102400, "semantic_artifact_bytes": 51200})
        self.assertEqual(result["crr"]["value"], .5)
        self.assertEqual(result["density"]["artifact_bytes"]["value"], .5)
        self.assertEqual(result["density"]["artifact_bytes"]["raw_denominator"], 102400)
        self.assertEqual(result["density"]["semantic_artifact_bytes"]["value"], 1.0)
        self.assertEqual(result["density"]["semantic_artifact_bytes"]["raw_denominator"], 51200)
        self.assertIsNone(result["density"]["joules"]["value"])
        self.assertIsNone(aggregate(self.records(False))["crr"]["value"])
        for denominator in (0, -1, None):
            self.assertIsNone(ratio(1, denominator)["value"])
        records = self.records()
        for row in records:
            if row["arm"] == "E":
                row["correct"] = False
        self.assertIn("does not outperform", aggregate(records)["crr"]["reason"])

    def test_unpaired_and_nonfinite_costs_fail_closed(self):
        records = self.records()
        with self.assertRaises(ValueError):
            aggregate(records[:-1])
        with self.assertRaises(ValueError):
            aggregate(records + [copy.deepcopy(records[0])])
        for value in (float("nan"), float("inf"), True):
            with self.assertRaises(ValueError):
                aggregate(records, {"joules": value})

    def test_bound_runtime_identity_overrides_stale_manual_artifact_cost(self):
        root = self.tmp / "runtime-evidence"
        root.mkdir(exist_ok=True)
        bundle = write_bound_runtime_fixture(
            root / "primary", profile_id="runtime-primary", revision=17,
            runtime_bytes=b"P" * 120, semantic=True)
        baseline = write_bound_runtime_fixture(
            root / "baseline", profile_id="runtime-baseline", revision=3,
            runtime_bytes=b"B" * 80, semantic=False)
        manifest = verify_bundle(bundle)
        config = {"incremental_costs": {"artifact_bytes": 120}}
        identity = bind_runtime_evidence(bundle, manifest, config, baseline)
        self.assertEqual(identity["artifact_bytes"], 120)
        self.assertEqual(identity["initial_memory_pages"], 1)
        self.assertEqual(identity["profile_revision"], 17)
        self.assertEqual(identity["semantic_artifact_bytes"], 40)
        self.assertEqual(identity["semantic_baseline"]["artifact_bytes"], 80)
        self.assertEqual(config["incremental_costs"]["artifact_bytes"], 120)
        self.assertEqual(config["incremental_costs"]["semantic_artifact_bytes"], 40)
        with self.assertRaisesRegex(ValueError, "configured artifact cost"):
            bind_runtime_evidence(bundle, manifest, {"incremental_costs": {"artifact_bytes": 121}})
        with self.assertRaisesRegex(ValueError, "requires a verified semantic baseline"):
            bind_runtime_evidence(bundle, manifest, {"incremental_costs": {"semantic_artifact_bytes": 40}})
        with self.assertRaisesRegex(ValueError, "configured semantic artifact cost"):
            bind_runtime_evidence(bundle, manifest, {"incremental_costs": {"semantic_artifact_bytes": 1}}, baseline)

    def test_grammar_namespaces_do_not_change_literals(self):
        assets = surface(self.bundle, "D")
        grammar = assets["grammar"]
        self.assertIn("a-root", grammar)
        self.assertIn("b-root", grammar)
        self.assertIn("stats.mean", grammar)
        self.assertNotIn("b-stats", grammar)
        self.assertEqual(assets["top_level_tool_count"], 2)

    def test_preregistered_run_rejects_model_budget_or_identity_drift(self):
        with tempfile.TemporaryDirectory(prefix="prereg-unit-", dir=ROOT / "target") as temporary:
            root = Path(temporary)
            bundle = write_bound_runtime_fixture(
                root / "primary", profile_id="prereg-primary", revision=17,
                runtime_bytes=b"P" * 120, semantic=True)
            baseline = write_bound_runtime_fixture(
                root / "baseline", profile_id="prereg-baseline", revision=3,
                runtime_bytes=b"B" * 80, semantic=False)
            corpus = root / "corpus.jsonl"
            corpus.write_bytes(b'{"id":"one"}\n')
            generator = root / "generator.py"
            generator.write_bytes(b"# frozen corpus generator\n")
            corpus_manifest = root / "corpus-manifest.json"
            corpus_manifest.write_bytes(canonical({"status": "FROZEN_BEFORE_MODEL_RUN"}))
            model_inventory = root / "models.json"
            inventory = {
                "models": [
                    {"id": "small-unit", "status": "READY", "sha256": "a" * 64,
                     "quantization": "Q4", "size_bytes": 1000, "source_revision": "rev-small",
                     "original_repository": "unit/small", "context": 4096},
                    {"id": "larger-unit", "status": "READY", "sha256": "b" * 64,
                     "quantization": "Q4", "size_bytes": 2000, "source_revision": "rev-large",
                     "original_repository": "unit/large", "context": 4096},
                ]
            }
            model_inventory.write_bytes(canonical(inventory))
            primary_profile = load_json((bundle / "profile.json").read_bytes())
            baseline_profile = load_json((baseline / "profile.json").read_bytes())
            run_id = "unit-primary"
            prereg = {
                "status": "FROZEN_READY_FOR_MODEL_RUN_CONFIGURATION",
                "model_inventory": {
                    "source": str(model_inventory.resolve()),
                    "source_sha256": digest(model_inventory.read_bytes()),
                },
                "capability": {
                    "bundle": bundle.relative_to(ROOT).as_posix(),
                    "semantic_baseline_bundle": baseline.relative_to(ROOT).as_posix(),
                    "profile_revision": 17,
                    "artifact_sha256": primary_profile["bindings"]["artifact_sha256"],
                    "semantic_artifact_bytes": 40,
                    "semantic_baseline_sha256": baseline_profile["bindings"]["artifact_sha256"],
                },
                "corpus": {
                    "path": corpus.relative_to(ROOT).as_posix(),
                    "sha256": digest(corpus.read_bytes()),
                    "generator": generator.relative_to(ROOT).as_posix(),
                    "generator_sha256": digest(generator.read_bytes()),
                    "manifest": corpus_manifest.relative_to(ROOT).as_posix(),
                    "manifest_sha256": digest(corpus_manifest.read_bytes()),
                },
                "generation_contract": {
                    "seed": 20260917, "baseline_mode": "reasoning", "temperature": 0,
                    "model_turns": 1, "hidden_retry_or_repair": False,
                    "generation_max_tokens": 512, "context_size": 4096,
                },
                "predeclared_runs": [{
                    "id": run_id, "small_model_id": "small-unit", "small_model_sha256": "a" * 64,
                    "small_quantization": "Q4", "larger_model_id": "larger-unit",
                    "larger_model_sha256": "b" * 64, "larger_quantization": "Q4",
                    "reasoning_mode": "off", "arms": ["A", "B", "C", "D", "E"],
                }],
            }
            preregistration = root / "preregistration.json"
            preregistration.write_bytes(canonical(prereg))
            config = {
                "seed": 20260917,
                "generation_max_tokens": 512,
                "baseline_mode": "reasoning",
                "small": {"model_inventory_id": "small-unit", "reasoning": "off", "context_size": 4096},
                "larger": {"model_inventory_id": "larger-unit", "reasoning": "off", "context_size": 4096},
            }
            inventory_evidence = hydrate_model_config(config, model_inventory)
            self.assertEqual(inventory_evidence["sha256"], digest(model_inventory.read_bytes()))
            self.assertEqual(config["small"]["model"], "small-unit")
            self.assertEqual(config["small"]["model_bytes"], 1000)
            runtime = bind_runtime_evidence(bundle, verify_bundle(bundle), config, baseline)
            args = SimpleNamespace(bundle=bundle, semantic_baseline_bundle=baseline, corpus=corpus,
                                   model_inventory=model_inventory)
            evidence = verify_preregistered_run(
                preregistration, run_id, args, config, runtime, generator, corpus_manifest)
            self.assertEqual(evidence["preregistered_run_id"], run_id)
            self.assertEqual(runtime["semantic_artifact_bytes"], 40)
            drifted = copy.deepcopy(config)
            drifted["generation_max_tokens"] = 256
            with self.assertRaisesRegex(ValueError, "token budget mismatch"):
                verify_preregistered_run(
                    preregistration, run_id, args, drifted, runtime, generator, corpus_manifest)
            drifted = copy.deepcopy(config)
            drifted["small"]["model_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "small model mismatch"):
                verify_preregistered_run(
                    preregistration, run_id, args, drifted, runtime, generator, corpus_manifest)

    def test_single_writer_lock_rejects_a_second_process_and_recovers(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "target") as temp_dir:
            lock_path = Path(temp_dir) / "benchmark.writer.lock"
            code = (
                "from pathlib import Path; "
                "from capability_benchmark import SingleWriterLock; "
                f"lock=SingleWriterLock(Path({str(lock_path)!r})); lock.acquire(); print('ACQUIRED')"
            )
            lock = SingleWriterLock(lock_path).acquire()
            try:
                blocked = subprocess.run(
                    [sys.executable, "-c", code], cwd=ROOT / "benchmarks",
                    capture_output=True, text=True, timeout=30,
                )
                self.assertNotEqual(blocked.returncode, 0)
                self.assertIn("active writer", blocked.stderr)
            finally:
                lock.release()
            allowed = subprocess.run(
                [sys.executable, "-c", code], cwd=ROOT / "benchmarks",
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            self.assertIn("ACQUIRED", allowed.stdout)

    def test_managed_server_command_matches_preregistered_runtime_settings(self):
        bench_root = Path("X:/ExactScopeBench")
        python_exe = bench_root / "venvs/lm-eval/Scripts/python.exe"
        config = {
            "model_inventory_id": "qwen3-0.6b",
            "base_url": "http://127.0.0.1:18089/v1",
            "context_size": 4096,
            "threads": 4,
            "gpu_layers": 99,
            "parallel": 1,
            "reasoning": "off",
        }
        command = managed_server_command(bench_root, python_exe, config, 20260917, 180)
        self.assertEqual(command[0], str(python_exe))
        self.assertIn("qwen3-0.6b", command)
        for flag, expected in (("--port", "18089"), ("--profile", "nothink"),
                               ("--ctx-size", "4096"), ("--threads", "4"),
                               ("--gpu-layers", "99"), ("--parallel", "1"),
                               ("--seed", "20260917"), ("--timeout", "180")):
            index = command.index(flag)
            self.assertEqual(command[index + 1], expected)
        bad = dict(config, base_url="http://localhost:18089/v1")
        with self.assertRaises(ValueError):
            managed_server_command(bench_root, python_exe, bad, 20260917, 180)

    def test_generation_budget_is_symmetric_unless_legacy_is_explicit(self):
        fair = {"generation_max_tokens": 512}
        self.assertEqual([generation_budget(fair, arm) for arm in "ABCDE"], [512] * 5)
        with self.assertRaises(ValueError):
            generation_budget({"baseline_max_tokens": 512}, "A")
        legacy = {"baseline_max_tokens": 512, "legacy_asymmetric_token_budget": True}
        self.assertEqual([generation_budget(legacy, arm) for arm in "ABCDE"], [512, 256, 256, 256, 512])
        with self.assertRaises(ValueError):
            generation_budget({"generation_max_tokens": 512, "baseline_max_tokens": 512}, "A")
        for value in (0, 4097, True, "512"):
            with self.assertRaises(ValueError):
                generation_budget({"generation_max_tokens": value}, "A")

    def test_reasoning_baseline_uses_strict_final_line_contract(self):
        row = {"id": "mean", "family": "S1", "state": "supported", "call": None,
               "expected": {"s": 0, "v": "2"}}
        assets = surface(self.bundle, "A", "reasoning")
        self.assertEqual(assets["grammar"], "")
        accepted = score(row, "1+3=4, then divide by 2.\nFinal answer: 2.000000", assets, self.core)
        self.assertTrue(accepted["correct"])
        self.assertEqual(accepted["failure_class"], "correct")
        for text, status in (("There are 2 observations, perhaps 4?", "missing_final_line"),
                             ("Final answer: 1\nFinal answer: 2", "multiple_final_lines"),
                             ("Final answer: <2.000000>", "malformed_final_line")):
            parsed, actual = parse_reasoning_final(text)
            self.assertIsNone(parsed)
            self.assertEqual(actual, status)
            record = score(row, text, assets, self.core)
            self.assertFalse(record["correct"])
            self.assertEqual(record["failure_class"], status)
        limited = score(row, "partial reasoning only", assets, self.core, "length")
        self.assertEqual(limited["failure_class"], "token_limit")

    def test_reference_xs_calc_fixtures_execute_through_real_runtime(self):
        verified = 0
        for row in templates():
            fixture = reference_plan(row)
            if fixture["status"] != "verified_reference":
                continue
            verified += 1
            self.assertLessEqual(fixture["steps"], 8)
            response, _ = self.core.call("request", fixture["plan"])
            final = {"v": response["v"]} if response.get("s") == 0 and "v" in response else {"e": response.get("e")}
            correct, _ = final_matches(row["expected"], final)
            self.assertTrue(correct, (row["id"], fixture, response, row["expected"]))
        self.assertGreaterEqual(verified, 60)

    def test_mixed_corpus_identity_cannot_produce_crr(self):
        rows = self.records()
        rows[0]["corpus_sha256"] = "different"
        with self.assertRaisesRegex(ValueError, "mixed corpus"):
            aggregate(rows)


if __name__ == "__main__":
    unittest.main()
