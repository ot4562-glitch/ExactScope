#!/usr/bin/env python3
"""Zero-inference tests for the rc4 grounding candidate, scorer, and isolation."""
from __future__ import annotations

import hashlib
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
from grounding_preregister import (  # noqa: E402
    EXPECTED_ANSWER_CALL_POLICY,
    EXPECTED_MODEL_SURFACE_POLICY,
    verify_serving_candidate,
)
from grounding_runtime import host_grounded_scalar_reply, host_short_circuit_reply  # noqa: E402
from grounding_v1_surface import AUTO_CONTRACT_CALIBRATION, AUTO_CONTRACT_CANDIDATES, AUTO_V2_TIE_PREFERENCE, surface_sha256  # noqa: E402


def load_jsonl(path: Path):
    return [loads(line) for line in path.read_bytes().splitlines() if line]


def answer_for_gold(row):
    disposition = row["required_disposition"]
    if disposition == "answer":
        return {"a": row["allowed_answers"][0], "disposition": "answer"}
    return {"a": None, "disposition": disposition}


def selected_model_fields(reply):
    value = reply["a"] if reply["disposition"] == "answer" else None
    normalized = {"a": value, "disposition": "answer" if value is not None else "abstain"}
    return {
        "model_contract": "answer-object-v3",
        "model_contract_valid": True,
        "model_contract_output": value,
        "model_output": normalized,
        "raw_content": json.dumps({"a": value}, separators=(",", ":")),
    }


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
                "output_source": "model",
                **selected_model_fields(a_reply),
                "input_tokens": 50,
                "output_tokens": 8,
                "model_latency_us": 10_000,
                "projection_bytes": 0,
                "frame": None,
            }
        )
        frame = dry[item_id]["frame"]
        unresolved_reply = host_short_circuit_reply(frame)
        scalar_reply = None if unresolved_reply is not None else host_grounded_scalar_reply(frame)
        host_reply = unresolved_reply if unresolved_reply is not None else scalar_reply
        host_decision = (
            "unresolved-state" if unresolved_reply is not None
            else "grounded-scalar" if scalar_reply is not None
            else None
        )
        g_record = {
            "v": 1,
            "item_id": item_id,
            "arm": "G",
            "output_source": "host" if host_reply is not None else "model",
            "input_tokens": 0 if host_reply is not None else 70,
            "output_tokens": 0 if host_reply is not None else 8,
            "model_latency_us": 0 if host_reply is not None else 12_000,
            "retrieval_latency_us": 500,
            "projection_bytes": 0 if host_reply is not None else dry[item_id]["projection_bytes"],
            "frame": frame,
        }
        if host_reply is not None:
            g_record.update(
                model_output=host_reply,
                raw_content=None,
                finish_reason="host-unresolved-state" if host_decision == "unresolved-state" else "host-grounded-scalar",
                host_decision=host_decision,
            )
        else:
            g_record.update(**selected_model_fields(good), finish_reason="stop")
        records.append(g_record)
    return records


def write_records(path: Path, rows):
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def write_run_sums(run_root: Path):
    paths = sorted(
        (path for path in run_root.rglob("*") if path.is_file() and path.name != "SHA256SUMS"),
        key=lambda path: path.relative_to(run_root).as_posix(),
    )
    text = "".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(run_root).as_posix()}\n"
        for path in paths
    )
    (run_root / "SHA256SUMS").write_text(text, encoding="utf-8")


def synthetic_preregistration(candidate: Path, planned_output: Path) -> dict:
    sha = "a" * 64
    return {
        "v": 1,
        "format": "exactscope.grounding-benchmark-preregistration",
        "format_version": "0.4",
        "state": "frozen-before-inference",
        "run_id": "unit-run",
        "writer_id": "unit-writer",
        "planned_output": str(planned_output),
        "source_commit": "a" * 40,
        "candidate": verify_serving_candidate(candidate),
        "evaluation_package": {"package_manifest_sha256": sha, "archive_sha256": sha},
        "model_inventory_sha256": sha,
        "model": {
            "id": "unit-model",
            "repository": "local/unit",
            "resolved_revision": "unit",
            "requested_file": "unit.gguf",
            "runtime": "llama.cpp",
            "quantization": "Q4",
            "bytes": 1,
            "sha256": sha,
            "path": "/unit/model.gguf",
        },
        "runtime_record_sha256": sha,
        "runtime": {
            "runtime_id": "unit-runtime",
            "executable_sha256": sha,
            "executable_path": "/unit/llama-server",
            "version": "unit",
            "commit": "unit",
            "launch": {},
            "hardware": {},
        },
        "generation_config_sha256": sha,
        "isolation_policy_sha256": sha,
        "scorer_sha256": sha,
        "model_surface_sha256": surface_sha256(),
        "model_surface_policy": EXPECTED_MODEL_SURFACE_POLICY,
        "answer_call_policy": EXPECTED_ANSWER_CALL_POLICY,
        "arms": ["A", "G"],
        "rewrite_calls": 0,
        "retry_count": 0,
        "hidden_repair": False,
        "manual_correction": False,
        "futility_rule": "deterministic-host-completion-serving-derived-v1",
        "duplicate_rule": "reject-(arm,item_id)",
        "drift_rule": "reject-any-bound-byte-or-config-drift",
        "model_inference_performed": False,
        "claim": "Frozen identity/configuration record only; creating or verifying this file performs zero model inference.",
    }


def synthetic_calibration() -> dict:
    profiles = []
    for contract in AUTO_CONTRACT_CANDIDATES:
        cases = [
            {"case_id": case_id, "expected": expected, "actual": expected, "valid": True, "correct": True}
            for case_id, _question, _evidence, expected in AUTO_CONTRACT_CALIBRATION
        ]
        profiles.append({"contract": contract, "score": len(cases), "case_count": len(cases), "cases": cases})
    return {
        "format": "exactscope.grounding-v1-contract-calibration",
        "format_version": "0.1",
        "model_surface_sha256": surface_sha256(),
        "selected_contract": "answer-object-v3",
        "tie_preference": list(AUTO_V2_TIE_PREFERENCE),
        "model_request_count": len(AUTO_CONTRACT_CANDIDATES) * len(AUTO_CONTRACT_CALIBRATION),
        "profiles": profiles,
    }


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
        summary, scored = score(self.candidate, records_path, require_run_integrity=False)
        self.assertEqual(len(scored), 60)
        a_accuracy = summary["arms"]["A"]["factual_accuracy"]
        self.assertEqual((a_accuracy["numerator"], a_accuracy["denominator"]), (23, 30))
        self.assertAlmostEqual(a_accuracy["ratio"], 23 / 30)
        g_accuracy = summary["arms"]["G"]["factual_accuracy"]
        self.assertEqual((g_accuracy["numerator"], g_accuracy["denominator"]), (30, 30))
        self.assertEqual(g_accuracy["ratio"], 1.0)
        for arm in ("A", "G"):
            self.assertEqual(summary["arms"][arm]["wrong_confident_answer_rate"]["numerator"], 0)
        self.assertEqual(summary["arms"]["G"]["false_grounding_rate"]["numerator"], 0)
        self.assertEqual(summary["arms"]["G"]["precision_at_k_micro"]["ratio"], 1.0)
        self.assertEqual(summary["arms"]["G"]["provider_unavailable_frame_accuracy"]["ratio"], 1.0)
        self.assertEqual(summary["arms"]["G"]["injection_bait_obedience"]["numerator"], 0)
        self.assertAlmostEqual(summary["cost"]["added_mean_input_tokens"], (7 * 70) / 30 - 50)

    def test_host_short_circuit_records_reduce_calls_without_changing_record_count(self):
        records = make_records(self.candidate, self.serving_out / "serving-records.jsonl")
        mapping = {"none": "abstain", "unavailable": "unavailable", "ambiguous": "clarify", "conflict": "conflict"}
        for record in records:
            if record["arm"] != "G":
                continue
            groups = record["frame"]["groups"]
            if len(groups) != 1 or groups[0]["authority"] != "authoritative" or groups[0]["state"] not in mapping:
                continue
            record.update({
                "output_source": "host",
                "model_output": {"a": None, "disposition": mapping[groups[0]["state"]]},
                "input_tokens": 0,
                "output_tokens": 0,
                "model_latency_us": 0,
                "raw_content": None,
                "finish_reason": "host-short-circuit",
            })
        records_path = self.root / "host-short-circuit.jsonl"
        write_records(records_path, records)
        summary, scored = score(self.candidate, records_path, require_run_integrity=False)
        self.assertEqual(len(scored), 60)
        self.assertEqual(summary["arms"]["G"]["host_output_count"], 23)
        self.assertEqual(summary["arms"]["G"]["model_answer_calls"], 7)
        self.assertEqual(summary["arms"]["G"]["host_short_circuit_accuracy"]["numerator"], 23)
        self.assertEqual(summary["arms"]["G"]["host_short_circuit_accuracy"]["denominator"], 23)
        self.assertEqual(summary["arms"]["G"]["host_unresolved_state_accuracy"]["numerator"], 10)
        self.assertEqual(summary["arms"]["G"]["host_grounded_scalar_accuracy"]["numerator"], 13)
        self.assertEqual(summary["arms"]["G"]["factual_accuracy"]["numerator"], 30)
        self.assertAlmostEqual(summary["arms"]["G"]["mean_input_tokens"], 490 / 30)

    def test_recovery_and_penalty_use_paired_raw_denominators(self):
        records = make_records(
            self.candidate,
            self.serving_out / "serving-records.jsonl",
            a_mode="wrong-answerable",
        )
        records_path = self.root / "recovery.jsonl"
        write_records(records_path, records)
        summary, _ = score(self.candidate, records_path, require_run_integrity=False)
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
            score(self.candidate, duplicate, require_run_integrity=False)
        incomplete = self.root / "incomplete.jsonl"
        write_records(incomplete, records[:-1])
        with self.assertRaises(ScoreError):
            score(self.candidate, incomplete, require_run_integrity=False)

    def test_incomplete_run_is_rejected_before_gold_manifest_is_opened(self):
        records = make_records(self.candidate, self.serving_out / "serving-records.jsonl")
        incomplete = self.root / "incomplete-before-gold.jsonl"
        write_records(incomplete, records[:-1])
        gold_manifest = self.candidate / "manifests/gold-manifest.json"
        saved = gold_manifest.read_bytes()
        gold_manifest.unlink()
        try:
            with self.assertRaisesRegex(ScoreError, "run is incomplete"):
                score(self.candidate, incomplete, require_run_integrity=False)
        finally:
            gold_manifest.write_bytes(saved)

    def test_production_scorer_reconciles_status_attempts_and_run_checksums(self):
        records = make_records(self.candidate, self.serving_out / "serving-records.jsonl")
        run_root = self.root / "complete-run"
        run_root.mkdir()
        raw = run_root / "raw-results.jsonl"
        write_records(raw, records)
        preregistration = run_root / "preregistration.json"
        preregistration.write_bytes(canonical_bytes(synthetic_preregistration(self.candidate, run_root)))
        (run_root / "contract-calibration.json").write_bytes(canonical_bytes(synthetic_calibration()))
        a_model = sum(row["arm"] == "A" and row["output_source"] == "model" for row in records)
        g_model = sum(row["arm"] == "G" and row["output_source"] == "model" for row in records)
        host = sum(row["arm"] == "G" and row["output_source"] == "host" for row in records)
        host_unresolved = sum(
            row["arm"] == "G" and row.get("host_decision") == "unresolved-state" for row in records
        )
        host_scalar = sum(
            row["arm"] == "G" and row.get("host_decision") == "grounded-scalar" for row in records
        )
        status = {
            "state": "complete",
            "item_count": 30,
            "record_count": 60,
            "model_answer_requests": a_model + g_model,
            "expected_model_answer_requests": 60 - host,
            "max_model_answer_requests": 60,
            "a_model_answer_requests": a_model,
            "g_model_answer_requests": g_model,
            "model_answer_request_attempts": a_model + g_model,
            "a_model_request_attempts": a_model,
            "g_model_request_attempts": g_model,
            "host_short_circuit_count": host,
            "host_unresolved_state_count": host_unresolved,
            "host_grounded_scalar_count": host_scalar,
            "selected_model_contract": "answer-object-v3",
            "model_surface_sha256": surface_sha256(),
            "calibration_model_requests": EXPECTED_MODEL_SURFACE_POLICY["calibration_model_requests"],
            "retry_count": 0,
            "preregistration_sha256": hashlib.sha256(preregistration.read_bytes()).hexdigest(),
        }
        status_path = run_root / "run-status.json"
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        write_run_sums(run_root)
        summary, scored = score(self.candidate, raw, require_run_integrity=True)
        self.assertEqual(len(scored), 60)
        self.assertEqual(summary["arms"]["G"]["host_output_count"], 23)

        status["g_model_request_attempts"] -= 1
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        write_run_sums(run_root)
        with self.assertRaisesRegex(ScoreError, "run-status accounting mismatch"):
            score(self.candidate, raw, require_run_integrity=True)

    def test_scorer_is_gold_side_and_runtime_is_gold_blind(self):
        scorer = (ROOT / "benchmarks/score_grounding.py").read_text(encoding="utf-8")
        runtime = (ROOT / "tools/grounding_runtime.py").read_text(encoding="utf-8")
        self.assertIn('candidate / "gold"', scorer)
        self.assertNotIn('candidate / "gold"', runtime)
        self.assertNotIn("allowed_answers", runtime)
        self.assertNotIn("expected_states", runtime)


if __name__ == "__main__":
    unittest.main(verbosity=2)
