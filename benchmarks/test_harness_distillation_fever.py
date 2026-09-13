#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unicodedata
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "tools", ROOT / "benchmarks"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import harness_distillation_fever as driver  # noqa: E402
from harness_distillation import calibration_policy_ids, minimum_candidate_catalog  # noqa: E402


class HarnessDistillationFeverTests(unittest.TestCase):
    def synthetic_rows(self):
        rows = []
        source_id = 1
        for label in driver.fever.LABELS:
            for index in range(6):
                rows.append({
                    "id": source_id,
                    "label": label,
                    "claim": f"{label} claim {index}",
                    "evidence": [] if label == "NOT ENOUGH INFO" else [[[0, 0, f"Page_{source_id}", 0]]],
                })
                source_id += 1
        return rows

    def test_fresh_selection_is_balanced_disjoint_and_respects_id_and_claim_exclusions(self):
        rows = self.synthetic_rows()
        excluded = {1, 7, 13}
        claim_excluded = rows[1]
        excluded_claims = {driver._claim_identity(claim_excluded["claim"])}
        calibration, held_out = driver.select_fresh_balanced(
            rows,
            excluded_source_ids=excluded,
            excluded_claim_identities=excluded_claims,
            calibration_per_label=1,
            held_out_per_label=2,
        )
        self.assertEqual(len(calibration), 3)
        self.assertEqual(len(held_out), 6)
        calibration_ids = {row["id"] for row in calibration}
        held_out_ids = {row["id"] for row in held_out}
        selected_ids = calibration_ids | held_out_ids
        self.assertFalse(calibration_ids & held_out_ids)
        self.assertFalse(selected_ids & excluded)
        self.assertNotIn(claim_excluded["id"], selected_ids)
        for label in driver.fever.LABELS:
            self.assertEqual(sum(row["label"] == label for row in calibration), 1)
            self.assertEqual(sum(row["label"] == label for row in held_out), 2)

    def test_stage1_selection_balances_calibration_and_samples_heldout_from_frozen_frame(self):
        rows = []
        source_id = 1
        for label in driver.fever.LABELS:
            for index in range(12):
                rows.append({
                    "id": source_id,
                    "label": label,
                    "claim": f"{label} stage1 claim {index}",
                    "evidence": [] if label == "NOT ENOUGH INFO" else [[[0, 0, f"Page_{source_id}", 0]]],
                })
                source_id += 1
        calibration, held_out, frame = driver.select_stage1_fresh(
            rows,
            excluded_source_ids=set(),
            calibration_per_label=2,
            held_out_count=9,
            held_out_seed=1234,
        )
        self.assertEqual(len(calibration), 6)
        self.assertEqual(len(held_out), 9)
        self.assertEqual(len(frame), 30)
        for label in driver.fever.LABELS:
            self.assertEqual(sum(row["label"] == label for row in calibration), 2)
        self.assertTrue({row["id"] for row in held_out}.issubset({row["id"] for row in frame}))
        self.assertFalse({row["id"] for row in calibration} & {row["id"] for row in held_out})
        second = driver.select_stage1_fresh(
            rows,
            excluded_source_ids=set(),
            calibration_per_label=2,
            held_out_count=9,
            held_out_seed=1234,
        )
        self.assertEqual([row["id"] for row in held_out], [row["id"] for row in second[1]])

    def test_stage1_grouping_prevents_shared_evidence_page_leakage(self):
        rows = self.synthetic_rows()
        rows[1]["evidence"] = rows[0]["evidence"]
        calibration, held_out, frame = driver.select_stage1_fresh(
            rows,
            excluded_source_ids=set(),
            calibration_per_label=1,
            held_out_count=3,
            held_out_seed=77,
        )
        driver._assert_stage1_group_independent(calibration + frame, "test representatives")
        driver._assert_stage1_group_independent(held_out, "test heldout")

    def test_stage1_grouping_is_transitive_across_overlapping_evidence_pages(self):
        rows = self.synthetic_rows()[:3]
        rows[0]["evidence"] = [[[0, 0, "Page_A", 0]]]
        rows[1]["evidence"] = [[[0, 0, "Page_A", 0], [0, 0, "Page_B", 0]]]
        rows[2]["evidence"] = [[[0, 0, "Page_B", 0]]]
        assignments = driver._stage1_group_assignments(rows)
        self.assertEqual(len(set(assignments.values())), 1)

    def test_wiki_page_resolution_normalizes_unicode_but_preserves_requested_spelling(self):
        requested = unicodedata.normalize("NFD", "José_Ferrer")
        stored = unicodedata.normalize("NFC", "José_Ferrer")
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "wiki.zip"
            payload = json.dumps({"id": stored, "lines": "0\tExample sentence"}, ensure_ascii=False) + "\n"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("wiki-pages/wiki-001.jsonl", payload.encode("utf-8"))
            found = driver.fever_candidate.scan_required_pages(archive_path, {requested})
        self.assertIn(requested, found)
        self.assertEqual(found[requested][0]["page"], requested)
        self.assertEqual(found[requested][0]["sentence_id"], 0)

    def test_stage1_freeze_rejects_historical_run_and_score_paths(self):
        manifest = {"selection_mode": "stage1-balanced-calibration+srs-heldout-v1"}
        for command in ("run-calibration", "score-calibration", "run-heldout", "score-heldout"):
            with self.assertRaises(driver.HarnessFeverError):
                driver._reject_legacy_runner_for_stage1(manifest, command)
        driver._reject_legacy_runner_for_stage1({}, "run-calibration")

    def test_claim_identity_normalizes_case_unicode_and_whitespace(self):
        left = driver._claim_identity("  Café   IS good  ")
        right = driver._claim_identity("Cafe\u0301 is GOOD")
        self.assertEqual(left, right)

    def test_first_real_host_executes_only_abd_and_prompt_candidates(self):
        host = driver._minimal_host("host-fixture")
        candidates = minimum_candidate_catalog(host)
        required = calibration_policy_ids(candidates)
        self.assertEqual(
            required,
            (
                "Base",
                "A",
                "B",
                "D",
                "A+B",
                "A+D",
                "B+D",
                "A+B+D",
                "prompt_reduced",
                "integrated",
            ),
        )
        by_id = {candidate.policy_id: candidate for candidate in candidates}
        self.assertEqual(driver._policy_flags(by_id["Base"]), (False, False, False))
        self.assertEqual(driver._policy_flags(by_id["A+B+D"]), (True, True, True))
        self.assertEqual(driver._policy_flags(by_id["integrated"]), (True, True, True))
        self.assertEqual(by_id["integrated"].prompt_profile, "no-policy")

    def test_policy_order_is_deterministic_and_item_specific(self):
        policies = ["Base", "A", "B", "D", "integrated"]
        first = driver._policy_order("item-1", policies)
        self.assertEqual(first, driver._policy_order("item-1", list(reversed(policies))))
        self.assertEqual(set(first), set(policies))
        self.assertNotEqual(first, driver._policy_order("item-2", policies))

    def test_run_lock_rejects_duplicate_output_identity_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "calibration-run"
            lock = output.with_name(output.name + ".lock")
            with driver._exclusive_run_lock(output):
                self.assertTrue(lock.is_file())
                with self.assertRaises(driver.HarnessFeverError):
                    with driver._exclusive_run_lock(output):
                        pass
            self.assertFalse(lock.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
