#!/usr/bin/env python3
"""Zero-inference tests for the rc4 grounding candidate, scorer, and isolation."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
BENCH = ROOT / "benchmarks"
for path in (str(TOOLS), str(BENCH)):
    if path not in sys.path:
        sys.path.insert(0, path)

from generate_grounding_candidate import CandidateBuilder  # noqa: E402
from grounding_canonical import canonical_bytes, loads  # noqa: E402
from grounding_dry_run import gold_verify, serving_run  # noqa: E402
from score_grounding import ScoreError, score  # noqa: E402


def load_jsonl(path: Path):
    return [loads(line) for line in path.read_bytes().splitlines() if line]


def answer_for_gold(row):
    disposition = row["required_disposition"]
    if disposition == "answer":
        return {"a": row["allowed_answers"][0], "disposition": "answer"}
    return {"a": None, "disposition": disposition}


def make_records(candidate: Path, serving_records: Path, *, a_mode: str = "perfect"):
    answers = {row["item_id"]: row for row in load_jsonl(candidate / "gold/answers.jsonl")}
    dry = {row["item_id"]: row for row in load_jsonl(serving_records)}
    records = []
    for item_id in sorted(answers):
        gold = answers[item_id]
        good = answer_for_gold(gold)
        if a_mode == "perfect":
            a_reply = good
        elif a_mode == "wrong-answerable":
            if gold["answer_expected"]:
                a_reply = {"a": "definitely-wrong-value", "disposition": "answer"}
            else:
                a_reply = good
        else:
            raise AssertionError(a_mode)
        records.append(
            {
                "v": 1,
                "item_id": item_id,
                "arm": "A",
                "model_output": a_reply,
                "input_tokens": 50,
                "output_tokens": 8,
                "model_latency_ms": 10.0,
                "retrieval_latency_ms": 0.0,
                "projection_bytes": 0,
                "frame": None,
            }
        )
        records.append(
            {
                "v": 1,
                "item_id": item_id,
                "arm": "G",
                "model_output": good,
                "input_tokens": 70,
                "output_tokens": 8,
                "model_latency_ms": 12.0,
                "retrieval_latency_ms": 0.5,
                "projection_bytes": dry[item_id]["projection_bytes"],
                "frame": dry[item_id]["frame"],
            }
        )
    return records


def write_records(path: Path, rows):
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


class GroundingBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.candidate = self.root / "candidate"
        CandidateBuilder(20260906).build(self.candidate)
        self.serving_out = self.root / "serving-out"
        serving_report = serving_run(self.candidate, self.serving_out)
        self.assertEqual(serving_report["model_requests"], 0)
        self.assertEqual(serving_report["gold_reads"], 0)
        self.assertEqual(serving_report["item_count"], 30)
        verification = gold_verify(
            self.candidate,
            self.serving_out / "serving-records.jsonl",
            self.root / "gold-verify",
        )
        self.assertTrue(verification["pass"])

    def tearDown(self):
        self.tmp.cleanup()

    def test_candidate_generation_is_byte_reproducible(self):
        second = self.root / "candidate-2"
        CandidateBuilder(20260906).build(second)
        first_files = {
            p.relative_to(self.candidate).as_posix(): p.read_bytes()
            for p in self.candidate.rglob("*") if p.is_file()
        }
        second_files = {
            p.relative_to(second).as_posix(): p.read_bytes()
            for p in second.rglob("*") if p.is_file()
        }
        self.assertEqual(first_files, second_files)

    def test_all_required_strata_are_present_and_serving_is_oracle_free(self):
        classes = load_jsonl(self.candidate / "gold/class-labels.jsonl")
        strata = {row["stratum"] for row in classes}
        self.assertEqual(
            strata,
            {
                "stable_public", "synthetic_private", "product_manual", "stale_revision",
                "distractor", "authoritative_no_answer", "provider_unavailable",
                "ambiguity", "conflict", "multilingual", "adversarial_evidence",
                "supplemental_no_hit",
            },
        )
        serving_bytes = b"".join(
            path.read_bytes()
            for path in sorted((self.candidate / "serving").rglob("*")) if path.is_file()
        )
        for forbidden in (
            b"allowed_answers", b"expected_states", b"valid_evidence",
            b"forbidden_evidence", b"required_disposition", b"obsolete_answer",
            b"injection_bait", b"auth_unresolved", b'"stratum"',
        ):
            self.assertNotIn(forbidden, serving_bytes)

    def test_perfect_records_score_exact_raw_denominators(self):
        records = make_records(self.candidate, self.serving_out / "serving-records.jsonl")
        records_path = self.root / "perfect.jsonl"
        write_records(records_path, records)
        summary, scored = score(self.candidate, records_path)
        self.assertEqual(len(scored), 60)
        for arm in ("A", "G"):
            accuracy = summary["arms"][arm]["factual_accuracy"]
            self.assertEqual((accuracy["numerator"], accuracy["denominator"]), (30, 30))
            self.assertEqual(accuracy["ratio"], 1.0)
            self.assertEqual(summary["arms"][arm]["wrong_confident_answer_rate"]["numerator"], 0)
        self.assertEqual(summary["arms"]["G"]["false_grounding_rate"]["numerator"], 0)
        self.assertEqual(summary["arms"]["G"]["precision_at_k_micro"]["ratio"], 1.0)
        self.assertEqual(summary["arms"]["G"]["provider_unavailable_frame_accuracy"]["ratio"], 1.0)
        self.assertEqual(summary["arms"]["G"]["injection_bait_obedience"]["numerator"], 0)
        self.assertEqual(summary["cost"]["added_mean_input_tokens"], 20.0)

    def test_recovery_and_penalty_use_paired_raw_denominators(self):
        records = make_records(
            self.candidate,
            self.serving_out / "serving-records.jsonl",
            a_mode="wrong-answerable",
        )
        records_path = self.root / "recovery.jsonl"
        write_records(records_path, records)
        summary, _ = score(self.candidate, records_path)
        recovery = summary["paired"]["grounding_recovery_rate"]
        self.assertGreater(recovery["denominator"], 0)
        self.assertEqual(recovery["numerator"], recovery["denominator"])
        self.assertEqual(recovery["ratio"], 1.0)
        penalty = summary["paired"]["grounding_penalty_rate"]
        self.assertEqual(penalty["numerator"], 0)

    def test_duplicate_and_incomplete_runs_are_rejected(self):
        records = make_records(self.candidate, self.serving_out / "serving-records.jsonl")
        duplicate = self.root / "duplicate.jsonl"
        write_records(duplicate, records + [records[0]])
        with self.assertRaises(ScoreError):
            score(self.candidate, duplicate)
        incomplete = self.root / "incomplete.jsonl"
        write_records(incomplete, records[:-1])
        with self.assertRaises(ScoreError):
            score(self.candidate, incomplete)

    def test_scorer_is_gold_side_and_runtime_is_gold_blind(self):
        scorer = (ROOT / "benchmarks/score_grounding.py").read_text(encoding="utf-8")
        runtime = (ROOT / "tools/grounding_runtime.py").read_text(encoding="utf-8")
        self.assertIn('candidate / "gold"', scorer)
        self.assertNotIn('candidate / "gold"', runtime)
        self.assertNotIn("allowed_answers", runtime)
        self.assertNotIn("expected_states", runtime)


if __name__ == "__main__":
    unittest.main(verbosity=2)
