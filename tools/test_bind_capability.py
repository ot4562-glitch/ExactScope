"""Binding requires real artifact execution and preserves immutable parent identity."""
import os
import tempfile
import unittest
from pathlib import Path

from bind_capability import bind
from compile_capability import ROOT, digest, load, verify_bundle, write_bundle


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.bundle = ROOT / "adapters/capabilities/statistics-core-8-ai-r6"
        self.artifact = ROOT / "target/wasm32v1-none/release/exactscope_wasm.wasm"
        self.corpus = ROOT / "benchmarks/statistics-v0.1.jsonl"
        self.core = ROOT / "target/debug" / ("exactscope-core.exe" if os.name == "nt" else "exactscope-core")

    def test_real_artifact_binds_gold_without_claim_promotion(self):
        files = bind(self.bundle, self.artifact, self.corpus, self.core, 7)
        profile = load(files["profile.json"])
        self.assertEqual(profile["support"], "experimental")
        self.assertEqual(profile["bindings"]["artifact_sha256"], digest(self.artifact.read_bytes()))
        self.assertEqual(load(files["statistics-conformance.json"])["checked_calls"], 225)
        self.assertEqual(profile["evidence"]["conformance_sha256"], digest(files["statistics-conformance.json"]))
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "unit"
            write_bundle(files, output)
            verify_bundle(output)
            (output / "runtime.wasm").write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                verify_bundle(output)

    def test_revision_reuse_is_rejected_before_execution(self):
        for revision in (1, 6, True, 0x100000000):
            with self.assertRaises(ValueError):
                bind(self.bundle, self.artifact, self.corpus, self.core, revision)

    def test_invalid_artifact_fails_before_gold_admission(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "runtime.wasm"
            bad.write_bytes(b"not wasm")
            with self.assertRaises(RuntimeError):
                bind(self.bundle, bad, self.corpus, self.core, 7)


if __name__ == "__main__":
    unittest.main()
