"""Model evidence may attach only to an exact clean-source capability/runtime identity."""
import tempfile
import unittest
from pathlib import Path

from attach_model_evidence import attach, validate_model_results
from compile_capability import (canonical, digest, load, model_surface_contract,
                                source_identity, verify_bundle, write_bundle)


def write_evidence_fixture(root: Path) -> Path:
    """Create an artifact-bound capability fixture without historical generated evidence."""
    runtime = b"unit-artifact-bound-runtime"
    benchmark_mapping = canonical({"id": "unit", "family": "S1", "call": None})
    catalog = {
        "format": "exactscope.hotset",
        "format_version": "0.1",
        "abi": "1.0",
        "binding_sha256": "1" * 64,
        "packs": [{"id": "unit-pack", "version": "0.1"}],
        "operations": [{"op": "stats.mean", "revision": 1}],
    }
    files = {
        "catalog.json": canonical(catalog),
        "prompt-fragment.txt": b"Use only stats.mean with exact decimal strings.\n",
        "task-map.json": canonical({"unit-family": ["stats.mean"]}),
        "xs-eval.gbnf": b"root ::= \"{}\"\n",
        "xs-eval.tool.json": b'{"type":"function"}\n',
        "runtime.wasm": runtime,
        "benchmark-mapping.jsonl": benchmark_mapping,
    }
    profile = {
        "profile_id": "model-evidence-unit",
        "profile_revision": 17,
        "support": "experimental",
        "domain": "statistics",
        "task_families": ["unit-family"],
        "runtime_surface": {
            "specialization": "statistics-selected-wasm",
            "xs_calc": {"enabled": False, "plan_revision": None},
            "xs_eval": {"operations": ["stats.mean"]},
            "xs_find": {"enabled": False},
            "model_visible_tools_max": 1,
            "normal_model_turns_max": 1,
        },
        "model_budget": {
            "semantic_operation_count": 1,
            "prompt_fragment_bytes_max": 1024,
            "schema_bytes_max": 4096,
            "grammar_bytes_max": 4096,
        },
        "device_budget": {
            "target_profile": "no-import-wasm",
            "artifact_bytes_max": 131072,
            "imports_max": 0,
            "wasm_initial_pages_max": 1,
            "wasm_maximum_pages_max": 1,
        },
        "bindings": {
            "core_revision": "sha256:" + source_identity(),
            "abi_revision": "1.0",
            "registry_sha256": digest(canonical(catalog["packs"])),
            "hotset_sha256": catalog["binding_sha256"],
            "tool_schema_sha256": digest(canonical({
                "xs-eval.tool.json": digest(files["xs-eval.tool.json"]),
            })),
            "grammar_sha256": digest(canonical({
                "xs-eval.gbnf": digest(files["xs-eval.gbnf"]),
            })),
            "prompt_sha256": digest(canonical({
                "prompt-fragment.txt": digest(files["prompt-fragment.txt"]),
            })),
            "artifact_sha256": digest(runtime),
        },
        "evidence": {
            "conformance_suite": "unit-conformance.json",
            "conformance_sha256": "2" * 64,
            "benchmark_mapping": "benchmark-mapping.jsonl",
            "benchmark_mapping_sha256": digest(benchmark_mapping),
            "qualification_records": [],
            "model_result_bundles": [],
        },
    }
    contract_bytes = canonical(model_surface_contract(profile, catalog, files))
    profile["bindings"]["surface_contract_sha256"] = digest(contract_bytes)
    files["surface-contract.json"] = contract_bytes
    files["profile.json"] = canonical(profile)
    manifest = {
        "format": "exactscope.capability.bundle",
        "format_version": "0.1",
        "files": {name: digest(data) for name, data in sorted(files.items())},
        "measurements": {
            "prompt_fragment_bytes": len(files["prompt-fragment.txt"]),
            "schema_bytes": len(files["xs-eval.tool.json"]),
            "grammar_bytes": len(files["xs-eval.gbnf"]),
            "top_level_tool_count": 1,
            "visible_semantic_operation_count": 1,
        },
        "operation_revisions": {"stats.mean": 1},
        "artifact_status": "artifact and gold bound; experimental, not target-qualified",
        "artifact_measurements": {
            "bytes": len(runtime),
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


class ModelEvidenceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="xs-model-evidence-fixture-")
        self.bundle = write_evidence_fixture(Path(self._tmp.name) / "capability")
        self.manifest = verify_bundle(self.bundle)
        self.profile = load((self.bundle / "profile.json").read_bytes())

    def tearDown(self):
        self._tmp.cleanup()

    def make_results(self, root, *, bundle_sha=None, artifact_sha=None, corpus_sha=None, identifier="one"):
        result = root / "results"
        result.mkdir(parents=True)
        harness = b"# frozen test harness\n"
        (result / "harness.py").write_bytes(harness)
        bundle_sha = bundle_sha or digest((self.bundle / "manifest.json").read_bytes())
        corpus_sha = corpus_sha or self.profile["evidence"]["benchmark_mapping_sha256"]
        artifact_sha = artifact_sha or self.profile["bindings"]["artifact_sha256"]
        rows = [{"arm": arm, "id": identifier, "family": "S1", "bundle_sha256": bundle_sha,
                 "corpus_sha256": corpus_sha, "correct": arm in ("C", "D")}
                for arm in ("A", "B", "C", "D")]
        items = b"".join(canonical(row) for row in rows)
        (result / "items.jsonl").write_bytes(items)
        metadata = {
            "config": {"incremental_costs": {"artifact_bytes": self.manifest["artifact_measurements"]["bytes"]}},
            "corpus_sha256": corpus_sha,
            "bundle_sha256": bundle_sha,
            "harness_sha256": digest(harness),
            "scoring_contract": "final-line-v1",
            "runtime_evidence": {
                "profile_id": self.profile["profile_id"],
                "profile_revision": self.profile["profile_revision"],
                "specialization": self.profile["runtime_surface"]["specialization"],
                "artifact_sha256": artifact_sha,
                "artifact_bytes": self.manifest["artifact_measurements"]["bytes"],
                "initial_memory_pages": self.manifest["artifact_measurements"]["initial_memory_pages"],
                "artifact_status": self.manifest["artifact_status"],
            },
        }
        metadata_bytes = canonical(metadata)
        (result / "metadata.json").write_bytes(metadata_bytes)
        (result / "summary.json").write_bytes(canonical({
            "items_sha256": digest(items), "metadata_sha256": digest(metadata_bytes)}))
        return result

    def test_identity_matched_raw_evidence_creates_namespaced_appendable_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = self.make_results(root / "first", identifier="one")
            validate_model_results(self.bundle, results)
            files = attach(self.bundle, results, 18)
            profile = load(files["profile.json"])
            self.assertEqual(profile["profile_revision"], 18)
            self.assertEqual(profile["support"], "experimental")
            self.assertEqual(len(profile["evidence"]["model_result_bundles"]), 1)
            evidence_names = [name for name in files if name.startswith("model-evidence-") and name.endswith(".json")]
            item_names = [name for name in files if name.startswith("model-") and name.endswith("-items.jsonl")]
            self.assertEqual(len(evidence_names), 1)
            self.assertEqual(len(item_names), 1)

            output = root / "bound-r18"
            write_bundle(files, output)
            manifest18 = verify_bundle(output)
            self.assertEqual(manifest18["model_evidence_source_profile_revision"], 17)
            self.assertEqual(manifest18["model_evidence_source_bundle_sha256"], digest((self.bundle / "manifest.json").read_bytes()))

            second = self.make_results(root / "second", identifier="two")
            files19 = attach(output, second, 19)
            profile19 = load(files19["profile.json"])
            self.assertEqual(profile19["profile_revision"], 19)
            self.assertEqual(profile19["support"], "experimental")
            self.assertEqual(len(profile19["evidence"]["model_result_bundles"]), 2)
            self.assertTrue(set(evidence_names) <= set(files19))
            self.assertEqual(len([name for name in files19 if name.startswith("model-evidence-") and name.endswith(".json")]), 2)
            self.assertEqual(len([name for name in files19 if name.startswith("model-") and name.endswith("-items.jsonl")]), 2)
            output19 = root / "bound-r19"
            write_bundle(files19, output19)
            manifest19 = verify_bundle(output19)
            self.assertEqual(manifest19["model_evidence_source_profile_revision"], 17)
            self.assertEqual(manifest19["model_evidence_count"], 2)

    def test_historical_or_wrong_runtime_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            wrong_bundle = self.make_results(Path(tmp), bundle_sha="0" * 64)
            with self.assertRaisesRegex(ValueError, "bundle mismatch"):
                validate_model_results(self.bundle, wrong_bundle)
        with tempfile.TemporaryDirectory() as tmp:
            wrong_runtime = self.make_results(Path(tmp), artifact_sha="f" * 64)
            with self.assertRaisesRegex(ValueError, "runtime artifact mismatch"):
                validate_model_results(self.bundle, wrong_runtime)

    def test_external_corpus_requires_preregistered_snapshot_and_invalidated_runs_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = self.make_results(Path(tmp), corpus_sha="1" * 64)
            with self.assertRaisesRegex(ValueError, "external benchmark corpus snapshot required"):
                validate_model_results(self.bundle, results)
        with tempfile.TemporaryDirectory() as tmp:
            results = self.make_results(Path(tmp))
            (results / "INVALIDATION.json").write_bytes(canonical({"status": "INVALID_TEST"}))
            with self.assertRaisesRegex(ValueError, "invalidated benchmark output"):
                validate_model_results(self.bundle, results)

    def test_revision_reuse_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = self.make_results(Path(tmp))
            for revision in (17, 1, True, 0x100000000):
                with self.assertRaises(ValueError):
                    attach(self.bundle, results, revision)


if __name__ == "__main__":
    unittest.main()
