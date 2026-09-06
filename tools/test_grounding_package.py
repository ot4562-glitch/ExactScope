#!/usr/bin/env python3
"""No-inference package/preregistration/runner verification for rc4 grounding."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


candidate_mod = load_module("candidate_mod", ROOT / "tools/generate_grounding_candidate.py")
package_mod = load_module("package_mod", ROOT / "tools/package_grounding_evaluation.py")
verify_mod = load_module("verify_mod", ROOT / "tools/verify_grounding_package.py")
prereg_mod = load_module("prereg_mod", ROOT / "benchmarks/grounding_preregister.py")
runner_mod = load_module("runner_mod", ROOT / "benchmarks/run_grounding_benchmark.py")


class GroundingPackageTests(unittest.TestCase):
    SOURCE_COMMIT = "a" * 40

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="grounding-package-", dir=ROOT / "target")
        self.work = Path(self.temp.name)
        self.candidate = self.work / "candidate-source"
        builder = candidate_mod.CandidateBuilder(20260906)
        builder.build(self.candidate)

    def tearDown(self):
        self.temp.cleanup()

    def build_package(self, output_name: str, *, model_inventory=None, runtime_record=None):
        output = self.work / output_name
        args = argparse.Namespace(
            candidate=self.candidate,
            output=output,
            version="1.0.0-rc.4-test",
            source_commit=self.SOURCE_COMMIT,
            model_inventory=model_inventory,
            runtime_record=runtime_record,
        )
        result = package_mod.build(args)
        return output, result

    def extract(self, archive: Path, destination: Path) -> Path:
        destination.mkdir(parents=True)
        with tarfile.open(archive, "r:gz") as tar:
            members = tar.getmembers()
            for member in members:
                self.assertFalse(member.issym() or member.islnk())
                parts = Path(member.name).parts
                self.assertNotIn("..", parts)
            tar.extractall(destination)
        roots = [p for p in destination.iterdir() if p.is_dir()]
        self.assertEqual(len(roots), 1)
        return roots[0]

    def test_package_is_deterministic_and_self_verifying(self):
        out1, result1 = self.build_package("pkg1")
        out2, result2 = self.build_package("pkg2")
        self.assertEqual(result1["archive_sha256"], result2["archive_sha256"])
        root = self.extract(Path(result1["archive"]), self.work / "extract1")
        verified = verify_mod.verify(root)
        self.assertEqual(verified["status"], "ok")
        self.assertEqual(verified["candidate_id"], result1["candidate_id"])
        self.assertFalse(verified["model_inference_performed"])
        self.assertEqual(hashlib.sha256(Path(result1["archive"]).read_bytes()).hexdigest(), result1["archive_sha256"])
        self.assertTrue((root / "candidate/gold/answers.jsonl").is_file())
        self.assertTrue((root / "candidate/serving/questions.jsonl").is_file())
        self.assertTrue((root / "benchmarks/run_grounding_benchmark.py").is_file())
        self.assertEqual(result1["file_count"], result2["file_count"])

    def make_dummy_identity(self):
        model_root = self.work / "models"
        model_dir = model_root / "dummy-small"
        model_dir.mkdir(parents=True)
        model_file = model_dir / "dummy.gguf"
        model_file.write_bytes(b"not-a-real-model; identity-test-only\n")
        model_sha = hashlib.sha256(model_file.read_bytes()).hexdigest()
        inventory = {
            "format": "exactscope.grounding-model-inventory",
            "format_version": "0.1",
            "source_inventory_sha256": "0" * 64,
            "identity_reuse_note": "unit-test-only",
            "records": [{
                "id": "dummy-small",
                "repository": "unit/test",
                "resolved_revision": "unit-rev",
                "requested_file": "dummy.gguf",
                "runtime": "llama.cpp",
                "quantization": "TEST",
                "bytes": model_file.stat().st_size,
                "sha256": model_sha,
            }],
        }
        inventory_path = self.work / "dummy-model-inventory.json"
        inventory_path.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        runtime_file = self.work / "dummy-llama-server"
        runtime_file.write_bytes(b"#!/bin/sh\nexit 99\n")
        runtime_sha = hashlib.sha256(runtime_file.read_bytes()).hexdigest()
        runtime = {
            "format": "exactscope.grounding-runtime-record",
            "format_version": "0.1",
            "runtime_id": "dummy-runtime",
            "family": "llama.cpp",
            "version": "unit",
            "build": 0,
            "commit": "unit",
            "build_description": "unit-test-only",
            "executable_name": "dummy-llama-server",
            "executable_sha256": runtime_sha,
            "server_ready_timeout_seconds": 1,
            "launch": {
                "alias": "exactscope-model",
                "host": "127.0.0.1",
                "port": 18080,
                "context": 4096,
                "threads": 1,
                "parallel": 1,
                "jinja": True,
                "webui": False,
                "offline": True,
                "mmproj": False,
                "reasoning": "off",
                "cache_prompt": False,
            },
            "hardware": {"architecture": "test", "cpu": "test", "logical_cpus": 1, "physical_cores": 1, "memory_bytes": 1, "environment": "test"},
            "measurement_note": "unit-test-only",
        }
        runtime_path = self.work / "dummy-runtime.json"
        runtime_path.write_text(json.dumps(runtime, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return model_root, model_file, inventory_path, runtime_file, runtime_path

    def test_preregistration_and_runner_verify_only_never_execute_runtime(self):
        model_root, model_file, inventory_path, runtime_file, runtime_path = self.make_dummy_identity()
        _, result = self.build_package("pkg", model_inventory=inventory_path, runtime_record=runtime_path)
        package_root = self.extract(Path(result["archive"]), self.work / "extract")
        packaged_inventory = package_root / "benchmarks/grounding-model-inventory.json"
        packaged_runtime = package_root / "benchmarks/grounding-runtime-llama-v040.json"
        prereg_path = self.work / "prereg.json"
        planned_output = self.work / "must-not-exist"
        args = argparse.Namespace(
            candidate=package_root / "candidate",
            package_manifest=package_root / "package-manifest.json",
            archive_sha256=result["archive_sha256"],
            source_commit=self.SOURCE_COMMIT,
            model_inventory=packaged_inventory,
            model_id="dummy-small",
            model_root=model_root,
            model_path=None,
            runtime_record=packaged_runtime,
            runtime_executable=runtime_file,
            generation_config=package_root / "benchmarks/grounding-generation-config.json",
            isolation_policy=package_root / "benchmarks/grounding-isolation-policy.json",
            scorer=package_root / "benchmarks/score_grounding.py",
            run_id="unit-run-1",
            writer_id="unit-writer",
            planned_output=str(planned_output.resolve()),
            output=prereg_path,
        )
        document = prereg_mod.create_document(args)
        prereg_mod.verify_document(document)
        prereg_path.write_bytes(prereg_mod.canonical_bytes(document))
        prereg_mod.verify_document(prereg_mod.load_cjson(prereg_path), prereg_path)
        self.assertFalse(document["model_inference_performed"])
        self.assertEqual(document["model"]["sha256"], hashlib.sha256(model_file.read_bytes()).hexdigest())

        old_root = runner_mod.ROOT
        try:
            runner_mod.ROOT = package_root
            verified, candidate_path, generation, isolation = runner_mod.verify_frozen_inputs(prereg_path, planned_output)
            self.assertEqual(verified["run_id"], "unit-run-1")
            self.assertEqual(candidate_path, package_root / "candidate")
            self.assertEqual(generation["retry_count"], 0)
            self.assertEqual(isolation["arms"], ["A", "G"])
            self.assertFalse(planned_output.exists())
            command = runner_mod.server_command(verified)
            self.assertEqual(command[0], str(runtime_file.resolve()))
            self.assertNotIn("--tools", command)
        finally:
            runner_mod.ROOT = old_root

    def test_runner_strict_model_output_parser(self):
        self.assertEqual(
            runner_mod.parse_model_output_strict('{"a":"Room 12","disposition":"answer"}'),
            {"a": "Room 12", "disposition": "answer"},
        )
        self.assertEqual(
            runner_mod.parse_model_output_strict('{"a":null,"disposition":"abstain"}'),
            {"a": None, "disposition": "abstain"},
        )
        for invalid in [
            '{"a":"x","a":"y","disposition":"answer"}',
            '{"a":NaN,"disposition":"answer"}',
            '{"a":"","disposition":"answer"}',
            '{"a":"x","disposition":"abstain"}',
            '{"a":"x","disposition":"answer","extra":1}',
            '[]',
        ]:
            with self.subTest(invalid=invalid):
                self.assertIsNone(runner_mod.parse_model_output_strict(invalid))

    def test_preregistration_rejects_model_drift(self):
        model_root, model_file, inventory_path, runtime_file, runtime_path = self.make_dummy_identity()
        _, result = self.build_package("pkg", model_inventory=inventory_path, runtime_record=runtime_path)
        package_root = self.extract(Path(result["archive"]), self.work / "extract")
        packaged_inventory = package_root / "benchmarks/grounding-model-inventory.json"
        packaged_runtime = package_root / "benchmarks/grounding-runtime-llama-v040.json"
        model_file.write_bytes(model_file.read_bytes() + b"drift")
        args = argparse.Namespace(
            candidate=package_root / "candidate",
            package_manifest=package_root / "package-manifest.json",
            archive_sha256=result["archive_sha256"],
            source_commit=self.SOURCE_COMMIT,
            model_inventory=packaged_inventory,
            model_id="dummy-small",
            model_root=model_root,
            model_path=None,
            runtime_record=packaged_runtime,
            runtime_executable=runtime_file,
            generation_config=package_root / "benchmarks/grounding-generation-config.json",
            isolation_policy=package_root / "benchmarks/grounding-isolation-policy.json",
            scorer=package_root / "benchmarks/score_grounding.py",
            run_id="unit-run-drift",
            writer_id="unit-writer",
            planned_output=str((self.work / "out").resolve()),
            output=self.work / "drift-prereg.json",
        )
        with self.assertRaises(prereg_mod.PreregistrationError):
            prereg_mod.create_document(args)


if __name__ == "__main__":
    unittest.main(verbosity=2)
