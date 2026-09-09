"""Offline synthetic recovery fixtures: no benchmark processes or gold access."""
import copy
from collections import Counter
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "benchmarks"), str(ROOT / "tools"), str(ROOT)]
import verify_v1_oom_recovery as v
import run_v1_oom_recovery as r


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.parent = self.root / "parent"
        self.parent.mkdir()
        self.output = self.root / "recovery"
        self.evidence = self.root / "oom.txt"
        self.evidence.write_text("OOM")
        self.p = {"models": [], "cells": [], "candidates": {}, "frozen_files": {},
                  "runtime": {"launch": {"port": 1, "threads": 1}}, "cwd": str(v.native.ROOT)}
        for task in v.native.PANEL:
            candidate = self.root / task
            manifest = candidate / ("manifest.json" if task == "hotpotqa" else "serving/manifest.json")
            put(manifest, {"mode": "synthetic", "qualification_eligible": False})
            self.p["candidates"][task] = {"path": str(candidate), "items": 2, "hashes": {str(manifest): v.sha(manifest)}}
        for i in range(20):
            model = {"id": v.TINY if i == 0 else f"model-{i}", "path": str(self.root / f"model-{i}.gguf"),
                     **{k: "synthetic" for k in v.native.IDENTITY}, "sha256": "synthetic",
                     "runtime": "llama.cpp"}
            Path(model["path"]).write_bytes(b"synthetic model")
            model.update(sha256=v.sha(model["path"]), bytes=Path(model["path"]).stat().st_size)
            self.p["models"].append(model)
            for task in v.native.PANEL:
                cid = model["id"] + "--" + task
                cell = {"id": cid, "model_id": model["id"], "benchmark_id": task, "port": 1,
                        "model_path": model["path"], "model_sha256": model["sha256"],
                        "run": str(self.parent / "cells" / cid), "score": str(self.parent / "scores" / cid)}
                cell["run_command"] = [sys.executable, "synthetic.py", "run", "--model-inventory", "inventory", "--runtime-record", "runtime", "--threads", "1", "--output", cell["run"]]
                cell["score_command"] = [sys.executable, "synthetic.py", "score", "--run", cell["run"], "--output", cell["score"]]
                self.p["cells"].append(cell)
        self.p["frozen_files"] = {"inventory": "synthetic", "runtime": "synthetic"}
        self.patch(v, "PARENT", self.parent)
        self.patch(v, "load_parent", return_value=self.p)
        self.patch(v, "verify_static_environment", return_value={})
        self.patch(v.native, "verify_child_run", side_effect=self.native_verify)
        self.patch(r, "execution_binding", side_effect=lambda p, static_hashes=None:
                   {"recovery_sources": r.code_hashes()})
        self.patch(v.native.subprocess, "run", side_effect=AssertionError("process creation forbidden"))
        self.patch(v.native, "validate_summary", return_value=None)
        for i, cell in enumerate(self.p["cells"][:38]):
            if i < 3:
                entry = {"id": cell["id"], "status": "failed", "error": "protocol"}
            else:
                self.child(cell)
                entry = {"id": cell["id"], "status": "completed", "error": None, "artifacts": v.tree(Path(cell["run"]))}
            put(self.parent / "ledger" / (cell["id"] + ".json"), entry)
        # A partial directory must never decide retention.
        partial = Path(self.p["cells"][-1]["run"])
        partial.mkdir(parents=True)
        (partial / "opaque").write_text("not JSON")
        self.calls = []
        self.patch(v.native, "invoke", side_effect=self.invoke)

    def patch(self, obj, name, *args, **kwargs):
        patcher = patch.object(obj, name, *args, **kwargs)
        value = patcher.start()
        self.addCleanup(patcher.stop)
        return value

    def child(self, cell):
        run = Path(cell["run"])
        model = next(m for m in self.p["models"] if m["id"] == cell["model_id"])
        execution_model = {k: model[k] for k in ("id", "path", "sha256", "runtime", *v.native.IDENTITY)}
        prereg = {"model": execution_model, "model_inventory_sha256": "synthetic", "runtime_record_sha256": "synthetic",
                  "runtime": self.p["runtime"], "format": f"exactscope.public-{v.native.FORMATS[cell['benchmark_id']]}-preregistration",
                  "format_version": "0.1", "arms": ["A", "G"], "retry_count": 0, "hidden_repair": False, "gold_visible_to_runner": False}
        put(run / "preregistration.json", prereg)
        put(run / "run-status.json", {"model_id": cell["model_id"], "state": "complete", "record_count": 4,
                                      "preregistration_sha256": v.sha(run / "preregistration.json")})
        for name in v.REQUIRED - {"preregistration.json", "run-status.json"}:
            (run / name).write_text("synthetic")

    def native_verify(self, protocol, cell):
        # Native API boundary stub: never accesses candidate gold or starts a runtime.
        v.require((Path(cell["run"]) / "raw-results.jsonl").read_text() == "synthetic", "raw record drift")

    def invoke(self, command, log):
        self.calls.append(command)
        log.write_text("synthetic invocation")
        destination = Path(v.option(command, "--output"))
        if command[2] == "run":
            original = next(c for c in self.p["cells"] if c["id"] == destination.name)
            self.child(v.relocated(original, self.output))
        else:
            put(destination / "summary.json", {})


class VerifyTests(Fixture):
    def test_sealed_context_skips_parent_and_live_model_hashing(self):
        cell = self.p["cells"][3]
        ledger = v.read(self.parent / "ledger" / (cell["id"] + ".json"))
        Path(cell["model_path"]).unlink()
        with patch.object(v, "verify_live_model", side_effect=AssertionError("live model read")):
            v.load_parent.reset_mock()
            v.verify_static_environment.reset_mock()
            self.assertTrue(v.verify_sealed_cell(cell, ledger, parent=self.p)["verified"])
            v.load_parent.assert_not_called()
            v.verify_static_environment.assert_not_called()
            self.assertTrue(v.verify_sealed_cell(cell, ledger)["verified"])
            v.load_parent.assert_called_once_with()

    def test_ledger_only_partition_and_missing_completion(self):
        rows = v.partition(self.p)
        self.assertEqual([sum(x["disposition"] == d for x in rows) for d in ("retained_completed", "retained_failed", "recovery")], [35, 3, 22])
        snap = v.snapshot(self.p, [self.evidence])
        self.assertEqual(snap["completion"], {})
        v.verify_snapshot(self.p, snap)
        (self.parent / "empty").mkdir()
        with self.assertRaises(v.IntegrityError):
            v.verify_snapshot(self.p, snap)

    def test_snapshot_file_and_exists_drift(self):
        for kind in ("file", "completion", "directory"):
            with self.subTest(kind=kind):
                snap = v.snapshot(self.p, [self.evidence])
                target = self.parent / ("run-complete.json" if kind == "completion" else kind)
                target.mkdir() if kind == "directory" else target.write_text("changed")
                with self.assertRaises(v.IntegrityError):
                    v.verify_snapshot(self.p, snap)
                target.rmdir() if kind == "directory" else target.unlink()

    def test_retained_tamper_and_exact_relocation(self):
        cell = self.p["cells"][3]
        ledger = v.read(self.parent / "ledger" / (cell["id"] + ".json"))
        v.verify_sealed_cell(cell, ledger)
        moved = v.relocated(cell, self.output)
        self.assertEqual({k for k in cell if cell[k] != moved[k]}, {"run", "score", "run_command", "score_command"})
        self.child(moved)
        entry = {**ledger, "artifacts": v.tree(Path(moved["run"]))}
        v.verify_sealed_cell(moved, entry, self.output)
        for key in ("port", "score", "run_command", "score_command"):
            bad = copy.deepcopy(moved)
            bad[key] = 5 if key == "port" else "bad" if key == "score" else bad[key] + ["--extra"]
            with self.subTest(key=key), self.assertRaises(v.IntegrityError):
                v.verify_sealed_cell(bad, entry, self.output)
        for name in v.REQUIRED:
            target = Path(cell["run"]) / name
            before = target.read_bytes()
            target.write_text("tampered")
            with self.subTest(name=name), self.assertRaises(v.IntegrityError):
                v.verify_sealed_cell(cell, ledger)
            target.write_bytes(before)

    def test_parent_metadata_and_child_execution_identity(self):
        cell = self.p["cells"][3]
        model = next(m for m in self.p["models"] if m["id"] == cell["model_id"])
        metadata = {"acquisition_state": "verified", "bucket": "small", "family": "synthetic",
                    "parameters": 1_000_000, "upstream_sha256": model["sha256"]}
        model.update(metadata)
        self.child(cell)
        run = Path(cell["run"])
        prereg = v.read(run / "preregistration.json")
        self.assertTrue(metadata.keys().isdisjoint(prereg["model"]))

        def sealed_entry():
            return {"id": cell["id"], "status": "completed", "error": None,
                    "artifacts": v.tree(run)}

        self.assertTrue(v.verify_sealed_cell(cell, sealed_entry())["verified"])
        for key in ("id", "path", "sha256", "runtime", *v.native.IDENTITY):
            with self.subTest(key=key):
                changed = copy.deepcopy(prereg)
                changed["model"][key] = "wrong"
                put(run / "preregistration.json", changed)
                status = v.read(run / "run-status.json")
                status["preregistration_sha256"] = v.sha(run / "preregistration.json")
                put(run / "run-status.json", status)
                with self.assertRaisesRegex(v.IntegrityError, f"child model identity: {key}"):
                    v.verify_sealed_cell(cell, sealed_entry())
        self.child(cell)
        model["upstream_sha256"] = "wrong"
        with self.assertRaisesRegex(v.IntegrityError, "parent upstream_sha256 mismatch"):
            v.verify_sealed_cell(cell, sealed_entry())

    def test_resealed_model_runtime_status_and_raw_drift(self):
        cell = self.p["cells"][3]
        for name, key in (("preregistration.json", "model"), ("preregistration.json", "runtime"), ("run-status.json", "model_id"), ("run-status.json", "record_count")):
            target = Path(cell["run"]) / name
            before = target.read_bytes()
            data = v.read(target); data[key] = "wrong"; put(target, data)
            entry = {"id": cell["id"], "status": "completed", "error": None, "artifacts": v.tree(Path(cell["run"]))}
            with self.subTest(key=key), self.assertRaises((v.IntegrityError, TypeError)):
                v.verify_sealed_cell(cell, entry)
            target.write_bytes(before)

    def test_path_controls(self):
        with self.assertRaises(v.IntegrityError): v.safe(self.root / ".." / "escape")
        with self.assertRaises(v.IntegrityError): v.safe(self.evidence, self.parent)
        with self.assertRaises(v.IntegrityError): v.separated(self.parent / "new")
        link = self.root / "hard"
        os.link(self.evidence, link)
        with self.assertRaises(v.IntegrityError): v.read(link)
        link.unlink()
        # Portable metadata simulations cover platforms lacking symlink/FIFO privileges.
        for mode, attrs, links in ((stat.S_IFLNK, 0, 1), (stat.S_IFDIR, 1024, 1), (stat.S_IFIFO, 0, 1)):
            from types import SimpleNamespace
            info = SimpleNamespace(st_mode=mode, st_file_attributes=attrs, st_nlink=links)
            with self.subTest(mode=mode, attrs=attrs), patch.object(Path, "lstat", return_value=info), self.assertRaises(v.IntegrityError):
                v.safe(self.evidence)

    def test_extra_artifact_and_failed_evidence(self):
        r.run(self.output, [self.evidence])
        r.verify_recovery(self.output)
        extra = self.output / "extra"; extra.mkdir()
        with self.assertRaises(v.IntegrityError): r.verify_recovery(self.output)
        extra.rmdir()
        (self.output / "cells" / "extra-empty").mkdir()
        with self.assertRaises(v.IntegrityError): r.verify_recovery(self.output)


class StaticEnvironmentTests(unittest.TestCase):
    """Exercise the real static verifier with repeated command/candidate references."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name).resolve()
        source = root / "benchmarks/run_v1_grounding_matrix.py"
        source.parent.mkdir()
        source.write_text("frozen source")
        runtime = root / "runtime.bin"
        runtime.write_bytes(b"runtime")
        provider = root / "provider.dll"
        provider.write_bytes(b"provider")
        candidate = root / "candidate"
        candidate.mkdir()
        serving = candidate / "manifest.json"
        serving.write_text("serving")
        executable = Path(sys.executable).resolve()
        paths = (source, runtime, provider, serving, executable)
        self.p = {"cwd": str(root), "frozen_files": {str(f): v.sha(f) for f in paths},
                  "candidates": {"task": {"path": str(candidate), "hashes": {str(serving): v.sha(serving)}}},
                  "cells": [{"id": str(i), "benchmark_id": "task",
                             "run_command": [sys.executable, str(source)],
                             "score_command": [sys.executable, str(source)]} for i in range(60)]}
        self.paths = paths
        for obj, name, value in ((v.native, "ROOT", root), (v.native, "__file__", str(source)),
                                 (v.native, "PANEL", {"task": SimpleNamespace(__file__=str(source))}),
                                 (v.native, "SERVING_FILES", {"task": ["manifest.json"]})):
            patcher = patch.object(obj, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(v.native, "source_paths", return_value=[source])
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_distinct_static_files_hashed_once_per_pass(self):
        with patch.object(v, "sha", wraps=v.sha) as hashed:
            for _ in range(2):
                hashed.reset_mock()
                self.assertEqual(v.verify_static_environment(self.p), self.p["frozen_files"])
                self.assertEqual(Counter(str(c.args[0]) for c in hashed.call_args_list),
                                 Counter({str(f): 1 for f in self.paths}))

    def test_static_source_runtime_provider_and_candidate_drift(self):
        for path in self.paths[:-1]:
            with self.subTest(path=path.name):
                original = path.read_bytes()
                v.verify_static_environment(self.p)
                timestamp = path.stat().st_mtime_ns
                path.write_bytes(b"x" * len(original))
                os.utime(path, ns=(timestamp, timestamp))
                with self.assertRaisesRegex(v.IntegrityError, "evidence drift"):
                    v.verify_static_environment(self.p)
                path.write_bytes(original)

    def test_static_execution_identity_and_candidate_coverage(self):
        for kind in ("root", "import", "command", "interpreter", "candidate"):
            p = copy.deepcopy(self.p)
            with self.subTest(kind=kind):
                if kind == "root":
                    p["cwd"] = str(self.paths[0].parent)
                elif kind == "command":
                    p["cells"][-1]["score_command"][1] = str(self.paths[1])
                elif kind == "interpreter":
                    p["cells"][-1]["run_command"][0] = str(self.paths[1])
                elif kind == "candidate":
                    p["candidates"]["task"]["hashes"] = {}
                if kind == "import":
                    with patch.dict(sys.modules, {self.paths[0].stem: SimpleNamespace(__file__=str(self.paths[1]))}), self.assertRaises(v.IntegrityError):
                        v.verify_static_environment(p)
                else:
                    with self.assertRaises(v.IntegrityError):
                        v.verify_static_environment(p)


if __name__ == "__main__":
    unittest.main()
