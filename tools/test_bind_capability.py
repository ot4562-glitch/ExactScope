"""Binding tests that generate their own clean-source fixtures before admission checks."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from bind_capability import bind
from build_capability_wasm import build as build_capability_wasm, resolve_tool
from compile_capability import (ROOT, canonical, compile_profile, digest, load,
                                verify_bundle, write_bundle)


class BindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="xs-bind-tests-")
        cls.tmp = Path(cls._tmp.name)
        cls.cargo = resolve_tool("cargo")
        cls.node = resolve_tool("node")

        subprocess.run([str(cls.cargo), "build", "--locked", "-p", "exactscope-packc"],
                       cwd=ROOT, check=True, capture_output=True)
        subprocess.run([str(cls.cargo), "build", "--locked", "-p", "exactscope-conformance",
                        "--bin", "exactscope-core"], cwd=ROOT, check=True, capture_output=True)
        suffix = ".exe" if os.name == "nt" else ""
        cls.packc = ROOT / "target/debug" / ("exactscope-packc" + suffix)
        cls.core = ROOT / "target/debug" / ("exactscope-core" + suffix)
        cls.corpus = ROOT / "benchmarks/statistics-v0.1.jsonl"
        cls.economics_corpus = ROOT / "benchmarks/economics-ped-conformance-v0.1.jsonl"

        cls.bundle = cls._compile_bundle("statistics-capability-request-r27.json", "statistics-r27")
        cls.build = cls._build_bundle(cls.bundle, cls.corpus, "statistics-r27")
        cls.artifact = cls.build / "runtime.wasm"
        cls.provenance = cls.build / "build-provenance.json"

        cls.weighted_bundle = cls._compile_bundle(
            "statistics-weighted-mean-capability-request-r13.json", "weighted-r13")
        cls.weighted_build = cls._build_bundle(cls.weighted_bundle, cls.corpus, "weighted-r13")

        cls.calc_bundle = cls._compile_bundle(
            "statistics-calc-only-capability-request-r10.json", "calc-r10")
        cls.calc_build = cls._build_bundle(cls.calc_bundle, cls.corpus, "calc-r10")

        cls.economics_bundle = cls._compile_bundle(
            "economics-ped-capability-request-r5.json", "economics-r5")
        cls.economics_build = cls._build_bundle(
            cls.economics_bundle, cls.economics_corpus, "economics-r5")

        # Preserve the binder's stale-source rejection test without checking a
        # generated historical bundle into the release source. The bundle stays
        # internally hash-consistent but intentionally carries an old core id.
        historical_source = load(
            (ROOT / "spec/examples/statistics-capability-profile.json").read_bytes())
        historical_files = compile_profile(canonical(historical_source), cls.packc)
        historical_profile = load(historical_files["profile.json"])
        historical_profile["bindings"]["core_revision"] = "sha256:" + ("0" * 64)
        historical_files["profile.json"] = canonical(historical_profile)
        historical_manifest = load(historical_files["manifest.json"])
        historical_manifest["files"]["profile.json"] = digest(historical_files["profile.json"])
        historical_files["manifest.json"] = canonical(historical_manifest)
        historical_files["bundle-sha256.txt"] = (
            digest(historical_files["manifest.json"]) + "\n").encode()
        cls.historical_bundle = cls.tmp / "historical-statistics"
        write_bundle(historical_files, cls.historical_bundle)
        verify_bundle(cls.historical_bundle)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    @classmethod
    def _compile_bundle(cls, source_name, label):
        source = load((ROOT / "spec/examples" / source_name).read_bytes())
        files = compile_profile(canonical(source), cls.packc)
        output = cls.tmp / ("bundle-" + label)
        write_bundle(files, output)
        verify_bundle(output)
        return output

    @classmethod
    def _build_bundle(cls, bundle, corpus, label):
        output = cls.tmp / ("build-" + label)
        build_capability_wasm(bundle, corpus, output, cargo=cls.cargo, node=cls.node)
        return output

    def test_real_artifact_binds_gold_and_build_provenance_without_claim_promotion(self):
        files = bind(self.bundle, self.artifact, self.corpus, self.core, 28, self.provenance)
        profile = load(files["profile.json"])
        self.assertEqual(profile["support"], "experimental")
        self.assertEqual(profile["profile_revision"], 28)
        self.assertEqual(profile["bindings"]["artifact_sha256"], digest(self.artifact.read_bytes()))
        self.assertEqual(load(files["statistics-conformance.json"])["checked_calls"], 225)
        self.assertEqual(profile["evidence"]["conformance_sha256"], digest(files["statistics-conformance.json"]))
        self.assertEqual(files["build-provenance.json"], self.provenance.read_bytes())
        manifest = load(files["manifest.json"])
        self.assertEqual(manifest["build_provenance_sha256"], digest(self.provenance.read_bytes()))
        self.assertIn("not target-qualified", manifest["artifact_status"])
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "unit"
            write_bundle(files, output)
            verify_bundle(output)
            (output / "runtime.wasm").write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                verify_bundle(output)

    def test_revision_reuse_is_rejected_before_execution(self):
        for revision in (1, 27, True, 0x100000000):
            with self.assertRaises(ValueError):
                bind(self.bundle, self.artifact, self.corpus, self.core, revision)

    def test_invalid_artifact_fails_before_gold_admission(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "runtime.wasm"
            bad.write_bytes(b"not wasm")
            with self.assertRaises(RuntimeError):
                bind(self.bundle, bad, self.corpus, self.core, 28)

    def test_tampered_build_provenance_is_rejected(self):
        provenance = load(self.provenance.read_bytes())
        provenance["artifact"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "build-provenance.json"
            bad.write_bytes(canonical(provenance))
            with self.assertRaisesRegex(ValueError, "artifact mismatch"):
                bind(self.bundle, self.artifact, self.corpus, self.core, 28, bad)

    def test_historical_profile_cannot_be_rebound_to_current_runtime(self):
        with self.assertRaisesRegex(ValueError, "source identity"):
            bind(self.historical_bundle, self.artifact, self.corpus, self.core, 28)

    def test_one_operation_specialization_binds_its_filtered_gold(self):
        files = bind(
            self.weighted_bundle,
            self.weighted_build / "runtime.wasm",
            self.weighted_build / "capability-conformance-corpus.jsonl",
            self.core,
            14,
            self.weighted_build / "build-provenance.json",
        )
        profile = load(files["profile.json"])
        self.assertEqual(profile["runtime_surface"]["xs_eval"]["operations"], ["stats.mean.weighted"])
        self.assertEqual(load(files["statistics-conformance.json"])["checked_calls"], 45)
        measurements = load(files["manifest.json"])["artifact_measurements"]
        self.assertEqual(measurements["bytes"], len(files["runtime.wasm"]))
        self.assertLessEqual(measurements["bytes"], profile["device_budget"]["artifact_bytes_max"])

    def test_calc_only_specialization_binds_empty_semantic_conformance(self):
        files = bind(
            self.calc_bundle,
            self.calc_build / "runtime.wasm",
            self.calc_build / "capability-conformance-corpus.jsonl",
            self.core,
            11,
            self.calc_build / "build-provenance.json",
        )
        profile = load(files["profile.json"])
        self.assertEqual(profile["runtime_surface"]["xs_eval"]["operations"], [])
        self.assertEqual(load(files["statistics-conformance.json"])["checked_calls"], 0)
        measurements = load(files["manifest.json"])["artifact_measurements"]
        self.assertEqual(measurements["bytes"], len(files["runtime.wasm"]))
        self.assertLessEqual(measurements["bytes"], profile["device_budget"]["artifact_bytes_max"])
        self.assertEqual(files["benchmark-mapping.jsonl"], b"")

    def test_economics_second_domain_binds_reviewed_native_and_wasm_conformance(self):
        files = bind(
            self.economics_bundle,
            self.economics_build / "runtime.wasm",
            self.economics_corpus,
            self.core,
            6,
            self.economics_build / "build-provenance.json",
        )
        profile = load(files["profile.json"])
        self.assertEqual(profile["domain"], "economics")
        self.assertEqual(profile["profile_revision"], 6)
        self.assertEqual(profile["runtime_surface"]["xs_eval"]["operations"], ["econ.ped.mid"])
        self.assertFalse(profile["runtime_surface"]["xs_calc"]["enabled"])
        self.assertEqual(profile["evidence"]["conformance_suite"], "capability-conformance.json")
        self.assertEqual(load(files["capability-conformance.json"])["checked_calls"], 5)
        measurements = load(files["manifest.json"])["artifact_measurements"]
        self.assertEqual(measurements["bytes"], len(files["runtime.wasm"]))
        self.assertLessEqual(measurements["bytes"], profile["device_budget"]["artifact_bytes_max"])
        self.assertNotIn("statistics-conformance.json", files)
        self.assertIn("build-provenance.json", files)

        with self.assertRaisesRegex(ValueError, "requires verified build provenance"):
            bind(self.economics_bundle, self.economics_build / "runtime.wasm",
                 self.economics_corpus, self.core, 6)

        with tempfile.TemporaryDirectory() as tmp:
            tampered = Path(tmp) / "economics.jsonl"
            rows = self.economics_corpus.read_text(encoding="utf-8").splitlines()
            tampered.write_text("\n".join(reversed(rows)) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "reviewed source-derived corpus"):
                bind(self.economics_bundle, self.economics_build / "runtime.wasm", tampered,
                     self.core, 6, self.economics_build / "build-provenance.json")

            provenance = load((self.economics_build / "build-provenance.json").read_bytes())
            provenance["evidence"]["validations"] = [
                entry for entry in provenance["evidence"]["validations"]
                if entry.get("name") != "specialized_surface"
            ]
            bad_provenance = Path(tmp) / "bad-provenance.json"
            bad_provenance.write_bytes(canonical(provenance))
            with self.assertRaisesRegex(ValueError, "required passed validations"):
                bind(self.economics_bundle, self.economics_build / "runtime.wasm",
                     self.economics_corpus, self.core, 6, bad_provenance)


if __name__ == "__main__":
    unittest.main()
