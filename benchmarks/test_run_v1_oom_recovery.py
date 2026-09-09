"""Offline runner/qualification regressions; processes and gold reads are trapped."""
import builtins
import copy
from functools import lru_cache
import io
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "benchmarks"), str(ROOT / "tools"), str(ROOT)]
import test_verify_v1_oom_recovery as fixtures

r, v, put = fixtures.r, fixtures.v, fixtures.put


class RunnerTests(fixtures.Fixture):
    def setUp(self):
        super().setUp()
        # These fixtures never change path types or links; the verifier suite
        # covers those controls. Check each path once to avoid repeating costly
        # Windows ancestor metadata walks across every qualification pass.
        # Inventories, file contents, hashes and all recovery checks remain live.
        self.patch(v, "safe", new=lru_cache(maxsize=None)(v.safe))
        for module, names in ((subprocess, ("Popen", "run", "call", "check_call", "check_output")),
                              (os, ("system", "popen", "posix_spawn", "posix_spawnp",
                                    "spawnl", "spawnle", "spawnlp", "spawnlpe",
                                    "spawnv", "spawnve", "spawnvp", "spawnvpe"))):
            for name in names:
                if hasattr(module, name):
                    self.patch(module, name, side_effect=AssertionError("real process forbidden"))
        self.gold_reads = []
        for module in (builtins, io):
            original = module.open

            def guarded_open(file, *args, _open=original, **kwargs):
                if isinstance(file, (str, bytes, os.PathLike)):
                    parts = Path(os.fsdecode(file)).parts
                    if any("gold" in part.lower() for part in parts):
                        self.gold_reads.append(str(file))
                        raise AssertionError("gold read forbidden")
                return _open(file, *args, **kwargs)

            self.patch(module, "open", new=guarded_open)
        self.qualification = self.root / "qualification"
        self.fresh_cells = self.p["cells"][38:]

    def recover(self):
        r.run(self.output, [self.evidence])
        self.calls.clear()

    def test_exact_22_serial_launches_in_original_order(self):
        owner = threading.get_ident()
        active = False

        def launch(command, log):
            nonlocal active
            self.assertEqual(threading.get_ident(), owner)
            self.assertFalse(active)
            active = True
            try:
                index = len(self.calls)
                self.assertEqual(command, v.relocated(self.fresh_cells[index], self.output)["run_command"])
                self.assertNotIn("--resume", command)
                self.assertNotIn("--retry", command)
                if index:
                    previous = self.fresh_cells[index - 1]["id"]
                    self.assertEqual(v.read(self.output / "ledger" / (previous + ".json"))["status"], "completed")
                self.invoke(command, log)
            finally:
                active = False

        self.patch(v.native, "invoke", side_effect=launch)
        r.run(self.output, [self.evidence])
        ids = [Path(v.option(c, "--output")).name for c in self.calls]
        self.assertEqual(ids, [c["id"] for c in self.fresh_cells])
        self.assertEqual(len(ids), 22)
        self.assertFalse(set(ids) & {c["id"] for c in self.p["cells"][:38]})
        self.assertFalse(any(v.TINY in cid for cid in ids))
        self.assertEqual(len(list((self.output / "ledger").iterdir())), 22)
        self.assertTrue((self.output / "run-complete.json").is_file())
        self.assertEqual(self.gold_reads, [])

    def test_resume_retry_and_existing_output_refused(self):
        for flag in ("--resume", "--retry"):
            cell = copy.deepcopy(self.fresh_cells[0])
            cell["run_command"].append(flag)
            with self.subTest(flag=flag), self.assertRaises(v.IntegrityError):
                r.run_command(cell)
        self.output.mkdir()
        sentinel = self.output / "partial"
        sentinel.write_bytes(b"preserve")
        with self.assertRaisesRegex(v.IntegrityError, "output exists"):
            r.run(self.output, [self.evidence])
        self.assertEqual(sentinel.read_bytes(), b"preserve")
        self.assertEqual(self.calls, [])
        with self.assertRaisesRegex(v.IntegrityError, "output exists"):
            r.qualify(self.root / "nonexistent-recovery", self.output)

    def test_child_failure_is_terminal_preserves_evidence_and_continues(self):
        first = self.fresh_cells[0]

        def launch(command, log):
            if not self.calls:
                self.calls.append(command)
                log.write_text("child exited after partial output")
                run = Path(v.option(command, "--output"))
                run.mkdir(parents=True)
                (run / "partial.bin").write_bytes(b"partial evidence")
                raise ValueError("child exit code 137")
            self.invoke(command, log)

        self.patch(v.native, "invoke", side_effect=launch)
        r.run(self.output, [self.evidence])
        self.assertEqual([Path(v.option(c, "--output")).name for c in self.calls], [c["id"] for c in self.fresh_cells])
        entry = v.read(self.output / "ledger" / (first["id"] + ".json"))
        self.assertEqual(entry["status"], "failed")
        self.assertEqual(entry["failure_kind"], "child_execution")
        self.assertEqual(entry["attempt"], 1)
        self.assertIn("137", entry["error"])
        child = self.output / "cells" / first["id"]
        self.assertEqual((child / "partial.bin").read_bytes(), b"partial evidence")
        self.assertEqual(entry["evidence"], v.inventory(child))
        _, _, verified = r.verify_recovery(self.output)
        failed = next(row for _, row in verified if row["id"] == first["id"])
        self.assertTrue(failed["failure"]["terminal"])
        self.assertEqual(sum(row["status"] == "verified_completed" for _, row in verified), 56)

    def test_integrity_failure_aborts_without_completion_or_completed_ledger(self):
        def launch(command, log):
            self.invoke(command, log)
            (Path(v.option(command, "--output")) / "raw-results.jsonl").write_text("corrupt")

        self.patch(v.native, "invoke", side_effect=launch)
        with self.assertRaises(v.IntegrityError):
            r.run(self.output, [self.evidence])
        self.assertEqual(len(self.calls), 1)
        self.assertFalse((self.output / "run-complete.json").exists())
        self.assertEqual(list((self.output / "ledger").iterdir()), [])
        self.assertTrue((self.output / "cells" / self.fresh_cells[0]["id"] / "raw-results.jsonl").exists())

    def test_best_case_verifies_all_60_before_scoring_and_manifest_denominators(self):
        self.recover()
        verify = r.verify_recovery
        passes = []

        def verified_all(output):
            result = verify(output)
            rows = result[2]
            self.assertEqual([row["id"] for _, row in rows], [c["id"] for c in self.p["cells"]])
            self.assertTrue(all(row["verification"]["verified"] for _, row in rows))
            passes.append(len(rows))
            return result

        def score(command, log):
            self.assertTrue(passes)
            self.assertTrue(all(count == 60 for count in passes))
            self.assertEqual(command[2], "score")
            self.assertEqual(self.gold_reads, [])
            self.invoke(command, log)

        self.patch(r, "verify_recovery", side_effect=verified_all)
        self.patch(v.native, "invoke", side_effect=score)
        r.qualify(self.output, self.qualification)
        manifest = v.read(self.qualification / "qualification-manifest.json")
        self.assertEqual(len(self.calls), 57)
        self.assert_manifest(manifest)

    def assert_manifest(self, manifest, score_failure=None):
        self.assertEqual(manifest["cell_count"], 60)
        self.assertEqual(len(manifest["cells"]), 60)
        self.assertEqual([row["id"] for row in manifest["cells"]], [c["id"] for c in self.p["cells"]])
        extra = int(score_failure is not None)
        self.assertEqual(manifest["scored_cells"], 57 - extra)
        self.assertEqual(manifest["explicit_failures"], 3 + extra)
        self.assertIs(manifest["latency_qualifying"], False)
        for row in manifest["cells"]:
            self.assertIs(row["latency_qualifying"], False)
            failed = row["model_id"] == v.TINY or row["id"] == score_failure
            self.assertEqual(row["status"], "failed" if failed else "scored")
            self.assertEqual(row["metric_status"], "N/A" if failed else "scored")
            self.assertEqual(row["actual_task_denominators"], {"A": 0 if failed else 2, "G": 0 if failed else 2})
            if failed:
                self.assertTrue(row["failure"]["terminal"])
                self.assertEqual(row["failure"]["kind"], "score_failure" if row["id"] == score_failure else "fixed_runtime_protocol_failure")
            else:
                self.assertIsNone(row["failure"])
        for task in v.native.PANEL:
            lost = int(score_failure is not None and score_failure.endswith("--" + task))
            counts = manifest["tasks"][task]
            self.assertEqual(counts["expected_cells"], 20)
            self.assertEqual(counts["scored_cells"], 19 - lost)
            self.assertEqual(counts["failed_cells"], 1 + lost)
            self.assertEqual(counts["scored_model_items"], {"A": 38 - 2 * lost, "G": 38 - 2 * lost})

    def test_last_cell_tamper_prevents_all_scorers_and_gold(self):
        self.recover()
        (self.output / "cells" / self.fresh_cells[-1]["id"] / "raw-results.jsonl").write_text("tamper")
        with self.assertRaises(v.IntegrityError):
            r.qualify(self.output, self.qualification)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.gold_reads, [])
        self.assertFalse(self.qualification.exists())

    def test_mid_score_integrity_drift_stops_later_scorers_and_manifest(self):
        self.recover()

        def score(command, log):
            self.invoke(command, log)
            (self.output / "cells" / self.fresh_cells[-1]["id"] / "raw-results.jsonl").write_text("drift")
            # A genuine scorer failure must not conceal the integrity failure.
            raise ValueError("child exit code 1")

        self.patch(v.native, "invoke", side_effect=score)
        with self.assertRaises(v.IntegrityError):
            r.qualify(self.output, self.qualification)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.gold_reads, [])
        self.assertFalse((self.qualification / "qualification-manifest.json").exists())

    def test_genuine_score_failure_is_explicit_and_lowers_denominators(self):
        self.recover()
        failed_id = self.p["cells"][3]["id"]

        def score(command, log):
            self.invoke(command, log)
            if Path(v.option(command, "--output")).name == failed_id:
                raise subprocess.CalledProcessError(1, command)

        self.patch(v.native, "invoke", side_effect=score)
        r.qualify(self.output, self.qualification)
        self.assertEqual(len(self.calls), 57)
        manifest = v.read(self.qualification / "qualification-manifest.json")
        self.assert_manifest(manifest, failed_id)
        row = next(row for row in manifest["cells"] if row["id"] == failed_id)
        self.assertTrue(row["failure"]["error"])
        self.assertTrue(row["score_artifacts"])
        self.assertEqual(self.gold_reads, [])


if __name__ == "__main__":
    unittest.main()
