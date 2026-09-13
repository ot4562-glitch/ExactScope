#!/usr/bin/env python3
"""Tests for the detached single-file portable ExactScope amplifier package."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGER_PATH = ROOT / "tools/package_runtime_amplifier_zipapp.py"
spec = importlib.util.spec_from_file_location("exactscope_portable_packager", PACKAGER_PATH)
assert spec is not None and spec.loader is not None
packager = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = packager
spec.loader.exec_module(packager)
PROFILE = ROOT / "grounding/reference-profile-v0.1"


class PortableRuntimeAmplifierTests(unittest.TestCase):
    def test_build_is_deterministic_small_and_contains_no_model_or_corpus(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / "first.pyz"
            second = root / "second.pyz"
            result_a = packager.build(first)
            result_b = packager.build(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(result_a["sha256"], result_b["sha256"])
            self.assertLess(first.stat().st_size, 128 * 1024)
            self.assertEqual(result_a["third_party_python_dependencies"], 0)
            self.assertEqual(result_a["models_included"], 0)
            self.assertEqual(result_a["corpora_included"], 0)
            self.assertEqual(packager.verify(first)["status"], "PASS")

    def test_zipapp_executes_plan_against_external_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            app = Path(temp) / "exactscope-amplifier.pyz"
            packager.build(app)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(app),
                    "plan",
                    "--profile",
                    str(PROFILE),
                    "--question",
                    "What is the capital of France?",
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            result = json.loads(completed.stdout)
            self.assertEqual(result["route"], "ordinary-knowledge")
            self.assertTrue(result["model_called"])
            self.assertEqual(result["wire_profile"], "openai-json-schema-v1")

    def test_zipapp_help_requires_no_profile_or_network(self):
        with tempfile.TemporaryDirectory() as temp:
            app = Path(temp) / "exactscope-amplifier.pyz"
            packager.build(app)
            completed = subprocess.run(
                [sys.executable, str(app), "--help"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertIn("OpenAI-compatible", completed.stdout)
            self.assertIn("{plan,answer}", completed.stdout)

    def test_verify_rejects_tampered_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            app = Path(temp) / "exactscope-amplifier.pyz"
            packager.build(app)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(app, "a", compression=zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr("transport.py", b"tampered\n")
            with self.assertRaises(packager.PortablePackageError):
                packager.verify(app)


if __name__ == "__main__":
    unittest.main()
