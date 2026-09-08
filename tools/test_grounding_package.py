#!/usr/bin/env python3
"""No-inference package/preregistration/runner verification for rc4 grounding."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
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

    def test_candidate_and_package_bind_current_isolation_policy(self):
        manifest_path = self.candidate / "manifests/candidate-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["answer_call_policy"], candidate_mod.answer_call_policy_binding())
        self.assertEqual(manifest["answer_call_policy"], prereg_mod.EXPECTED_CANDIDATE_ANSWER_CALL_POLICY)

        stale = dict(manifest)
        stale["answer_call_policy"] = "bound-by-benchmark-isolation-policy-v0.2"
        manifest_path.write_bytes(candidate_mod.canonical_bytes(stale))
        (self.candidate / "CANDIDATE_SHA256.txt").write_text(
            hashlib.sha256(manifest_path.read_bytes()).hexdigest() + "\n",
            encoding="ascii",
        )
        with self.assertRaisesRegex(package_mod.PackageBuildError, "answer-call policy"):
            self.build_package("stale-policy")
        with self.assertRaisesRegex(prereg_mod.PreregistrationError, "answer-call policy"):
            prereg_mod.verify_candidate(self.candidate)

    def test_package_rejects_stale_candidate_digest_file(self):
        (self.candidate / "CANDIDATE_SHA256.txt").write_text("0" * 64 + "\n", encoding="ascii")
        with self.assertRaisesRegex(package_mod.PackageBuildError, "manifest digest file drift"):
            self.build_package("stale-candidate-digest")

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
        self.assertTrue((root / "tools/grounding_corpus.py").is_file())
        self.assertTrue((root / "tools/grounding_projection.py").is_file())
        manifest = json.loads((root / "package-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["format_version"], "0.3")
        self.assertEqual(manifest["grounding_corpus_module_sha256"], hashlib.sha256((root / "tools/grounding_corpus.py").read_bytes()).hexdigest())
        self.assertEqual(manifest["grounding_projection_module_sha256"], hashlib.sha256((root / "tools/grounding_projection.py").read_bytes()).hexdigest())
        self.assertEqual(result1["file_count"], result2["file_count"])

    def test_packaged_python_commands_do_not_mutate_package_with_bytecode(self):
        _, result = self.build_package("pkg-bytecode")
        package_root = self.extract(Path(result["archive"]), self.work / "extract-bytecode")
        dryrun_output = self.work / "dryrun-bytecode"
        commands = [
            [sys.executable, "benchmarks/grounding_dry_run.py", "serve", "--candidate", "candidate", "--output", str(dryrun_output)],
            [sys.executable, "tools/grounding_runtime.py", "verify", "--profile-dir", "candidate/serving/grounding"],
            [sys.executable, "benchmarks/grounding_preregister.py", "--help"],
            [sys.executable, "benchmarks/run_grounding_benchmark.py", "--help"],
            [sys.executable, "benchmarks/score_grounding.py", "--help"],
            [sys.executable, "adapters/llama-cpp/grounding_v1.py", "--help"],
        ]
        for command in commands:
            with self.subTest(command=command[1]):
                subprocess.run(command, cwd=package_root, check=True, capture_output=True, text=True)
        cache_dirs = [path for path in package_root.rglob("__pycache__") if path.is_dir()]
        pyc_files = [path for path in package_root.rglob("*.pyc") if path.is_file()]
        self.assertEqual(cache_dirs, [])
        self.assertEqual(pyc_files, [])
        self.assertEqual(verify_mod.verify(package_root)["status"], "ok")

    def test_run_checksums_are_written_after_server_shutdown_log(self):
        output = self.work / "run-sums"
        log_dir = output / "logs"
        log_dir.mkdir(parents=True)
        log_path = log_dir / "llama-server.log"
        code = (
            "import signal,sys,time\n"
            "def stop(*_):\n"
            " print('shutdown', flush=True)\n"
            " raise SystemExit(0)\n"
            "signal.signal(signal.SIGTERM, stop)\n"
            "print('running', flush=True)\n"
            "time.sleep(60)\n"
        )
        with log_path.open("wb") as log_handle:
            process = subprocess.Popen([sys.executable, "-c", code], stdout=log_handle, stderr=subprocess.STDOUT)
            time.sleep(0.1)
            runner_mod.stop_server(process)
        self.assertIn(b"shutdown", log_path.read_bytes())
        (output / "run-status.json").write_text('{"state":"complete"}\n', encoding="utf-8")
        runner_mod.write_sums(output)
        expected = {}
        for line in (output / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
            digest, relative = line.split("  ", 1)
            expected[relative] = digest
        self.assertEqual(expected["logs/llama-server.log"], hashlib.sha256(log_path.read_bytes()).hexdigest())

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
            archive=Path(result["archive"]),
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

        # The runtime verifier must not depend on or hash scorer-only gold bytes.
        for gold_file in (package_root / "candidate/gold").rglob("*"):
            if gold_file.is_file():
                gold_file.unlink()
        (package_root / "candidate/manifests/gold-manifest.json").unlink()

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

    def test_host_short_circuit_blocks_any_authoritative_unresolved_target(self):
        mapping = {
            "none": "abstain",
            "unavailable": "unavailable",
            "ambiguous": "clarify",
            "conflict": "conflict",
        }
        for state, disposition in mapping.items():
            frame = {"groups": [{"authority": "authoritative", "state": state}]}
            self.assertEqual(runner_mod.host_short_circuit_reply(frame), {"a": None, "disposition": disposition})
        self.assertIsNone(runner_mod.host_short_circuit_reply({"groups": [{"authority": "authoritative", "state": "grounded"}]}))
        self.assertIsNone(runner_mod.host_short_circuit_reply({"groups": [{"authority": "supplemental", "state": "none"}]}))
        self.assertEqual(runner_mod.host_short_circuit_reply({"groups": [
            {"authority": "authoritative", "state": "none"},
            {"authority": "authoritative", "state": "unavailable"},
        ]}), {"a": None, "disposition": "unavailable"})

    def test_preregistration_rejects_archive_drift(self):
        model_root, _, inventory_path, runtime_file, runtime_path = self.make_dummy_identity()
        _, result = self.build_package("archive-drift", model_inventory=inventory_path, runtime_record=runtime_path)
        archive = Path(result["archive"])
        package_root = self.extract(archive, self.work / "archive-drift-extract")
        archive.write_bytes(archive.read_bytes() + b"drift")
        args = argparse.Namespace(
            candidate=package_root / "candidate",
            package_manifest=package_root / "package-manifest.json",
            archive=archive,
            archive_sha256=result["archive_sha256"],
            source_commit=self.SOURCE_COMMIT,
            model_inventory=package_root / "benchmarks/grounding-model-inventory.json",
            model_id="dummy-small",
            model_root=model_root,
            model_path=None,
            runtime_record=package_root / "benchmarks/grounding-runtime-llama-v040.json",
            runtime_executable=runtime_file,
            generation_config=package_root / "benchmarks/grounding-generation-config.json",
            isolation_policy=package_root / "benchmarks/grounding-isolation-policy.json",
            scorer=package_root / "benchmarks/score_grounding.py",
            run_id="unit-run-archive-drift",
            writer_id="unit-writer",
            planned_output=str((self.work / "archive-drift-out").resolve()),
            output=self.work / "archive-drift-prereg.json",
        )
        with self.assertRaisesRegex(prereg_mod.PreregistrationError, "archive sha256 drift"):
            prereg_mod.create_document(args)

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
            archive=Path(result["archive"]),
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
