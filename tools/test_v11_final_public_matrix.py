#!/usr/bin/env python3
"""Unit tests for final v1.1 public-panel aggregation and README rendering."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "benchmarks/run_v11_final_public_matrix.py"
spec = importlib.util.spec_from_file_location("v11_final_panel", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot import final panel module")
panel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(panel)


class FinalPublicMatrixTests(unittest.TestCase):
    def test_aggregate_keeps_na_and_reports_valid_pair_denominators(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            matrix_path = root / "matrix.json"
            v1_path = root / "v1.json"
            models = [
                {"id": f"m{i}", "family": f"Model {i}", "parameters": f"{i + 1}M"}
                for i in range(panel.MODEL_COUNT)
            ]
            matrix_path.write_text(json.dumps({"models": models}), encoding="utf-8")
            v1_path.write_text(json.dumps({
                "models": [
                    {"model_id": f"m{i}", "status": "completed", "macro_accuracy": 0.25 + i / 1000}
                    for i in range(panel.MODEL_COUNT)
                ]
            }), encoding="utf-8")

            protocol_cells = []
            serving_rows = []
            score_rows = []
            for i in range(panel.MODEL_COUNT):
                for task in panel.TASKS:
                    cell_id = f"m{i}--{task}"
                    score_dir = root / "scores" / cell_id
                    score_dir.mkdir(parents=True)
                    summary_format = "exactscope.public-nq-summary" if task == "natural_questions" else "exactscope.public-hotpot-h1-summary"
                    (score_dir / "summary.json").write_text(json.dumps({
                        "format": summary_format,
                        "item_count": panel.ITEMS_PER_TASK,
                        "model_id": f"m{i}",
                        "arms": {
                            "A": {"f1": 0.10, "exact_match": 0.05, "format_failure_rate": 0.0, "mean_input_tokens": 100, "mean_evidence_bytes": 0},
                            "G": {"f1": 0.20, "exact_match": 0.10, "format_failure_rate": 0.0, "mean_input_tokens": 200, "mean_evidence_bytes": 1000},
                        },
                    }), encoding="utf-8")
                    protocol_cells.append({"id": cell_id, "score": str(score_dir)})
                    serving_rows.append({"id": cell_id, "status": "served", "reason": None})
                    if i == 0 and task == "natural_questions":
                        score_rows.append({"id": cell_id, "status": "n_a", "reason": "serving_failed: synthetic"})
                    else:
                        score_rows.append({"id": cell_id, "status": "scored", "reason": None})

            old_matrix, old_v1 = panel.MATRIX, panel.V1_PUBLIC_RESULTS
            panel.MATRIX, panel.V1_PUBLIC_RESULTS = matrix_path, v1_path
            try:
                result = panel.aggregate(
                    {"cells": protocol_cells, "readme_claim_boundary": ["test"]},
                    serving_rows,
                    score_rows,
                )
            finally:
                panel.MATRIX, panel.V1_PUBLIC_RESULTS = old_matrix, old_v1

            self.assertEqual(result["task_aggregate"]["natural_questions"]["valid_pair_count"], 19)
            self.assertEqual(result["task_aggregate"]["hotpotqa"]["valid_pair_count"], 20)
            self.assertEqual(result["pooled_valid_cell_count"], 39)
            self.assertEqual(result["n_a_cells"], 1)
            self.assertEqual(result["models_with_both_tasks"], 19)
            self.assertIsNone(result["models"][0]["two_task_mean_uplift_pp"])
            self.assertAlmostEqual(result["models"][1]["two_task_mean_uplift_pp"], 10.0)
            rendered = panel.render_markdown(result)
            self.assertIn("valid pairs **19/20**", rendered)
            self.assertIn("N/A cells are retained explicitly", rendered)
            self.assertIn("Model 0", rendered)
            self.assertIn("10.00%→20.00% (**+10.00pp**)", rendered)

    def test_readme_marker_update_is_bounded_and_repeatable(self):
        with tempfile.TemporaryDirectory() as td:
            readme = Path(td) / "README.md"
            readme.write_text("before\n\nImportant boundaries:\n\nafter\n", encoding="utf-8")
            old = panel.README
            panel.README = readme
            try:
                panel.update_readme("### Panel\n\nfirst\n")
                first = readme.read_text(encoding="utf-8")
                self.assertEqual(first.count(panel.README_START), 1)
                self.assertEqual(first.count(panel.README_END), 1)
                self.assertIn("first", first)
                panel.update_readme("### Panel\n\nsecond\n")
                second = readme.read_text(encoding="utf-8")
                self.assertNotIn("first", second)
                self.assertIn("second", second)
                self.assertIn("Important boundaries:", second)
            finally:
                panel.README = old


if __name__ == "__main__":
    unittest.main(verbosity=2)
