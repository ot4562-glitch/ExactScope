"""Focused offline tests for the 20-model public benchmark dispatcher."""
from __future__ import annotations

import argparse
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import benchmarks.run_v1_public_matrix as matrix


class PublicMatrixTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        model = self.root / "model.gguf"
        model.write_bytes(b"model")
        digest = matrix.file_sha(model)
        self.specs = []
        self.records = []
        for i in range(20):
            spec = {
                "id": f"m{i}", "repository": f"repo/{i}", "resolved_revision": "a" * 40,
                "requested_file": "model.gguf", "quantization": "Q4", "bytes": 5,
                "upstream_sha256": digest,
            }
            record = {**spec, "sha256": digest, "upstream_sha256": digest,
                      "path": str(model), "runtime": "llama.cpp"}
            self.specs.append(spec)
            self.records.append(record)
        self.model_matrix = {"format": "exactscope.v1-model-matrix",
                             "selection_policy": {"frozen": True, "model_count": 20},
                             "models": self.specs}
        self.matrix_path = self.root / "matrix.json"
        matrix.write_new(self.matrix_path, self.model_matrix)
        self.acquisition = {"format": "exactscope.v1-model-acquisition", "model_count": 20,
                            "matrix_sha256": matrix.file_sha(self.matrix_path), "records": self.records}

    def test_model_contract_requires_exact_twenty_and_upstream_sha(self):
        rows = matrix.verify_models(self.model_matrix, self.acquisition, matrix.file_sha(self.matrix_path))
        self.assertEqual([row["id"] for row in rows], [f"m{i}" for i in range(20)])
        for mutate in (
            lambda m, a: a["records"].pop(),
            lambda m, a: a.update(matrix_sha256="0" * 64),
            lambda m, a: a["records"][0].update(sha256="0" * 64),
            lambda m, a: m["models"][0].update(upstream_sha256="0" * 64),
        ):
            with self.subTest(mutate=mutate):
                m, a = copy.deepcopy(self.model_matrix), copy.deepcopy(self.acquisition)
                mutate(m, a)
                with self.assertRaises(ValueError):
                    matrix.verify_models(m, a, matrix.file_sha(self.matrix_path))

    def test_public_data_requires_six_by_twenty_four(self):
        data = self.root / "data"
        data.mkdir()
        records = []
        for task in matrix.TASK_IDS:
            path = data / f"{task}.jsonl"
            path.write_text("{}\n" * 24, encoding="utf-8")
            records.append({"id": task, "filename": path.name, "item_count": 24,
                            "sha256": matrix.file_sha(path)})
        matrix.write_new(data / "manifest.json", {"format": "exactscope.v1-public-suite-data",
                                                    "format_version": "0.1", "tasks": records})
        verified = matrix.verify_public_data(data)
        self.assertEqual(verified["total_items"], 144)
        records[0]["item_count"] = 23
        (data / "manifest.json").unlink()
        matrix.write_new(data / "manifest.json", {"format": "exactscope.v1-public-suite-data",
                                                    "format_version": "0.1", "tasks": records})
        with self.assertRaises(ValueError):
            matrix.verify_public_data(data)

    def test_aggregate_keeps_failed_models_explicit(self):
        protocol = {"cells": [{"model_id": f"m{i}"} for i in range(20)],
                    "claim_scope": "not leaderboard"}
        task_summary = {task: {"accuracy": 0.5} for task in matrix.TASK_IDS}
        summary = {"tasks": task_summary, "macro_accuracy": 0.5, "total_errors": 0,
                   "total_format_errors": 0, "total_protocol_errors": 0,
                   "total_infrastructure_errors": 0}
        rows = [{"model_id": f"m{i}", "status": "completed" if i else "failed",
                 "error": "offline" if i == 0 else None, "summary": None if i == 0 else summary}
                for i in range(20)]
        result = matrix.aggregate(protocol, rows)
        self.assertEqual(result["completed_models"], 19)
        self.assertIsNone(result["models"][0]["mmlu"])
        self.assertEqual(result["models"][1]["mmlu"], 0.5)
        self.assertFalse(result["leaderboard_comparable"])

    def test_matrix_writes_preregistration_before_first_child(self):
        output = self.root / "out"
        protocol = {
            "format": "exactscope.v1-public-matrix-preregistration", "format_version": "0.1",
            "claim_scope": "not leaderboard", "frozen_files": {},
            "runtime": {"sha256": "r"}, "data_manifest_sha256": "d",
            "cells": [{"model_id": f"m{i}", "model_sha256": "x", "model_path": str(self.root / "missing"),
                       "output": str(output / "cells" / f"m{i}"), "command": ["child", str(i)]}
                      for i in range(20)],
        }
        args = argparse.Namespace(output=output)
        calls = []
        def invoke(command, log):
            self.assertTrue((output / "preregistration.json").is_file())
            self.assertTrue((output / "preregistration-checksum.json").is_file())
            calls.append(command)
            return 9
        with patch.object(matrix, "preregister", return_value=protocol), \
                patch.object(matrix, "file_sha", return_value="x"), \
                patch.object(matrix, "invoke", side_effect=invoke):
            self.assertFalse(matrix.run_matrix(args))
        self.assertEqual(len(calls), 20)
        result = matrix.load(output / "matrix-results.json")
        self.assertEqual(len(result["models"]), 20)
        self.assertEqual(result["completed_models"], 0)

    def test_preregister_assigns_unique_frozen_ports(self):
        matrix_path = self.root / "matrix-for-ports.json"
        acquisition_path = self.root / "acquisition-for-ports.json"
        data_dir = self.root / "data-for-ports"
        runtime = self.root / "runtime"
        matrix.write_new(matrix_path, {})
        matrix.write_new(acquisition_path, {})
        data_dir.mkdir()
        (data_dir / "manifest.json").write_text("{}\n", encoding="utf-8")
        runtime.write_bytes(b"runtime")
        args = argparse.Namespace(
            output=self.root / "ports-output", matrix=matrix_path,
            acquisition_manifest=acquisition_path, data_dir=data_dir,
            runtime_executable=runtime, port=20000, threads=2, context=4096,
        )
        public_data = {
            "hashes": {str((data_dir / "manifest.json").resolve()): "d" * 64},
            "total_items": 144,
        }
        with patch.object(matrix, "load", side_effect=[self.model_matrix, self.acquisition]), \
                patch.object(matrix, "verify_models", return_value=self.records), \
                patch.object(matrix, "verify_public_data", return_value=public_data), \
                patch.object(matrix, "file_sha", return_value="a" * 64):
            protocol = matrix.preregister(args)
        ports = [cell["port"] for cell in protocol["cells"]]
        self.assertEqual(ports, list(range(20000, 20020)))
        self.assertEqual(len(set(ports)), 20)
        for cell, port in zip(protocol["cells"], ports):
            command = cell["command"]
            self.assertEqual(command[command.index("--port") + 1], str(port))
        self.assertEqual(protocol["runtime"]["base_port"], 20000)
        self.assertIn("frozen model index", protocol["runtime"]["port_policy"])


if __name__ == "__main__":
    unittest.main()
