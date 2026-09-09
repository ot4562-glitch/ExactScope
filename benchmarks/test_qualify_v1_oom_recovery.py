"""Offline regressions for the efficient v0.2 OOM qualification seal."""
import copy
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "benchmarks"), str(ROOT / "tools"), str(ROOT)]
import qualify_v1_oom_recovery as q
import test_verify_v1_oom_recovery as fixtures

v, put = fixtures.v, fixtures.put


class QualificationV02Tests(fixtures.Fixture):
    def test_terminal_failure_skips_scorer(self):
        cell = self.p["cells"][0]
        row = {
            "id": cell["id"], "model_id": cell["model_id"], "benchmark_id": cell["benchmark_id"],
            "status": "failed", "metric_status": "N/A", "source_run": str(self.parent),
            "source_child_run": cell["run"], "source_attempt": 1,
            "verification": {"verified": True, "kind": "terminal_failure"},
            "failure": {"kind": "fixed_runtime_protocol_failure", "error": "protocol", "terminal": True},
            "disposition": "retained_failed", "actual_task_denominators": {"A": 0, "G": 0},
            "score_artifacts": {}, "latency_qualifying": False,
        }
        with patch.object(v.native, "invoke", side_effect=AssertionError("scorer must not run")):
            result = q.score_one(cell, row, self.root / "qualification")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["metric_status"], "N/A")

    def test_verified_completed_cell_scores_once(self):
        cell = self.p["cells"][3]
        qualification = self.root / "qualification"
        (qualification / "logs").mkdir(parents=True)
        row = {
            "id": cell["id"], "model_id": cell["model_id"], "benchmark_id": cell["benchmark_id"],
            "status": "verified_completed", "metric_status": "N/A", "source_run": str(self.parent),
            "source_child_run": cell["run"], "source_attempt": 1,
            "verification": {"verified": True, "items_per_arm": 2, "records": 4},
            "failure": None, "disposition": "retained_completed",
            "actual_task_denominators": {"A": 0, "G": 0}, "score_artifacts": {},
            "latency_qualifying": False,
        }
        result = q.score_one(cell, row, qualification)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][2], "score")
        self.assertEqual(result["status"], "scored")
        self.assertEqual(result["metric_status"], "scored")
        self.assertEqual(result["actual_task_denominators"], {"A": 2, "G": 2})
        self.assertTrue(result["score_artifacts"])

    def test_qualify_uses_exactly_two_global_recovery_barriers(self):
        recovery_root = self.root / "sealed-recovery"
        recovery_root.mkdir()
        put(recovery_root / "preregistration.json", {"sealed": True})
        put(recovery_root / "run-complete.json", {"sealed": True})
        output = self.root / "qualification-v02"

        verified = []
        for index, cell in enumerate(self.p["cells"]):
            failed = index < 6
            row = {
                "id": cell["id"], "model_id": cell["model_id"], "benchmark_id": cell["benchmark_id"],
                "status": "failed" if failed else "verified_completed",
                "metric_status": "N/A", "source_run": str(self.parent),
                "source_child_run": cell["run"], "source_attempt": 1,
                "verification": ({"verified": True, "kind": "terminal_failure"} if failed else
                                 {"verified": True, "items_per_arm": 2, "records": 4}),
                "failure": ({"kind": "fixed_runtime_protocol_failure", "error": "protocol", "terminal": True}
                            if failed else None),
                "disposition": "retained_failed" if failed else "retained_completed",
                "actual_task_denominators": {"A": 0, "G": 0}, "score_artifacts": {},
                "latency_qualifying": False,
            }
            verified.append((cell, row))

        recovery_manifest = {"parent_run_complete_present": False}
        barrier = patch.object(q.recovery, "verify_recovery",
                               side_effect=[(self.p, recovery_manifest, copy.deepcopy(verified)),
                                            (self.p, recovery_manifest, copy.deepcopy(verified))])

        def fake_score(cell, row, _output):
            result = copy.deepcopy(row)
            if result["status"] != "verified_completed":
                return result
            task = cell["benchmark_id"]
            metrics = ["label_accuracy"] if task == "fever" else ["exact_match", "f1"]
            arms = {"A": {}, "G": {}}
            paired = {}
            for metric in metrics:
                arms["A"][metric] = 0.25
                arms["G"][metric] = 0.50
                paired[metric + "_uplift"] = 0.25
            result.update(status="scored", metric_status="scored",
                          summary={"arms": arms, "paired": paired}, score_artifacts={},
                          actual_task_denominators={"A": 2, "G": 2})
            return result

        with barrier as verify_mock, patch.object(q, "score_one", side_effect=fake_score):
            manifest = q.qualify(recovery_root, output)

        self.assertEqual(verify_mock.call_count, 2)
        self.assertEqual(manifest["cell_count"], 60)
        self.assertEqual(manifest["scored_cells"], 54)
        self.assertEqual(manifest["explicit_failures"], 6)
        self.assertTrue((output / "qualification-manifest.json").is_file())
        self.assertTrue((output / "checksums.json").is_file())
        self.assertEqual(sum(t["scored_cells"] for t in manifest["tasks"].values()), 54)


if __name__ == "__main__":
    import unittest
    unittest.main()
