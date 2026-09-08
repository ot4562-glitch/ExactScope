"""Focused, zero-inference source experiment and pre-gold integrity tests."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "benchmarks")]

from generate_grounding_candidate import CandidateBuilder
from grounding_canonical import canonical_bytes
import run_grounding_source_experiment as runner
import score_grounding as scorer


class SourceExperimentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.candidate = self.root / "candidate"
        CandidateBuilder(20260906).build(self.candidate)
        for name in runner.SOURCE_FILES:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.model = self.root / "model.gguf"
        self.model.write_bytes(b"fake model")
        self.runtime = self.root / "llama-server"
        self.runtime.write_bytes(b"fake runtime")
        self.write_config("grounding-model-inventory.json", {
            "format": "exactscope.grounding-model-inventory", "format_version": "0.1",
            "records": [{"id": "test", "requested_file": "model.gguf",
                         "bytes": self.model.stat().st_size, "sha256": runner.file_sha(self.model)}],
        })
        runtime = runner.load_json(self.root / "benchmarks/grounding-runtime-llama-v040.json")
        runtime["executable_sha256"] = runner.file_sha(self.runtime)
        self.write_config("grounding-runtime-llama-v040.json", runtime)
        self.args = argparse.Namespace(candidate=self.candidate, model_id="test",
            model_path=self.model, model_root=None, runtime_executable=self.runtime,
            output=self.root / "run", g_contract="legacy", g_context="full", g_policy="full",
            g_projection="full", verify_only=False)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(runner, "ROOT", self.root))

    def write_config(self, name, value):
        (self.root / "benchmarks" / name).write_bytes(canonical_bytes(value))

    def execute(self, prereg, *, fail=False, drift=False, stop_fail=False):
        stopped = []
        requests = []
        original_seal = runner.write_sums

        def request(_prereg, _generation, messages):
            requests.append(copy.deepcopy(messages))
            if fail:
                raise runner.BenchmarkRunError("request failed")
            if _generation.get("answer_schema") == runner.ANSWER_ONLY_SCHEMA:
                return {"raw_content": '"B3-04"', "model_output": None,
                        "input_tokens": 7, "output_tokens": 4, "model_latency_us": 80,
                        "finish_reason": "stop"}
            if _generation.get("answer_schema") == runner.ANSWER_OBJECT_SCHEMA:
                return {"raw_content": '{"a":"B3-04"}', "model_output": None,
                        "input_tokens": 8, "output_tokens": 5, "model_latency_us": 85,
                        "finish_reason": "stop"}
            return {"raw_content": '{"a":null,"disposition":"abstain"}',
                    "model_output": {"a": None, "disposition": "abstain"},
                    "input_tokens": 10, "output_tokens": 5, "model_latency_us": 100,
                    "finish_reason": "stop"}

        def stop(process):
            if stop_fail:
                raise runner.BenchmarkRunError("stop failed")
            stopped.append(process)
            if drift:
                (self.root / runner.SOURCE_FILES[0]).write_bytes(b"changed")

        def seal(output):
            self.assertEqual(len(stopped), 1, "server must stop before SHA sealing")
            original_seal(output)

        with patch.object(runner.subprocess, "Popen", return_value=object()), \
                patch.object(runner, "wait_server"), \
                patch.object(runner, "request_model", side_effect=request), \
                patch.object(runner, "stop_server", side_effect=stop), \
                patch.object(runner, "write_sums", side_effect=seal):
            runner.execute(prereg, self.args.output)
        return requests

    def test_gold_blind_complete_run_provenance_and_scorer_compatibility(self):
        original_open = Path.open

        def no_gold(path, *args, **kwargs):
            self.assertNotIn("gold", path.parts)
            self.assertNotEqual(path.name, "gold-manifest.json")
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", no_gold):
            prereg = runner.bind_inputs(self.args)
            requests = self.execute(prereg)
        self.assertFalse(prereg["qualification_eligible"])
        self.assertEqual(set(prereg["source_files"]), set(runner.SOURCE_FILES))
        self.assertTrue(any("renderer" in name for name in prereg["serving_files"]))
        raw = self.args.output / "raw-results.jsonl"
        records = scorer.load_jsonl(raw)
        status = scorer.verify_run_integrity(raw, records, {r["item_id"] for r in records})
        self.assertEqual(status["a_model_answer_requests"], 30)
        self.assertEqual(status["host_short_circuit_count"], 23)
        self.assertEqual(status["host_unresolved_state_count"], 10)
        self.assertEqual(status["host_grounded_scalar_count"], 13)
        self.assertEqual(len(requests), 37)
        for record in records:
            if record["arm"] == "A":
                self.assertEqual(record["projection_bytes"], 0)
                self.assertEqual(record["retrieval_latency_us"], 0)
            elif record["grounding_context_sent"]:
                self.assertGreater(record["projection_bytes"], 0)
                self.assertGreater(record["policy_bytes"], 0)
                self.assertGreaterEqual(record["retrieval_latency_us"], 0)
            else:
                self.assertEqual(record["projection_bytes"], 0)
                self.assertEqual(record["policy_bytes"], 0)
            for field in ("projection", "policy"):
                self.assertEqual(len(record[field + "_sha256"]), 64)
                self.assertEqual(record["sent_" + field + "_bytes"],
                                 record[field + "_bytes"] if record["output_source"] == "model" else 0)
        self.assertEqual(len(scorer.score(self.candidate, raw)[1]), 60)
        with self.assertRaisesRegex(runner.BenchmarkRunError, "already exists"):
            runner.execute(prereg, self.args.output)

    def test_inventory_and_policy_rejections(self):
        for attr, value, message in (("model_id", "unknown", "model id"),
                                     ("model_path", self.runtime, "byte-size drift"),
                                     ("runtime_executable", self.model, "runtime executable sha256")):
            with self.subTest(attr=attr), patch.object(self.args, attr, value):
                with self.assertRaisesRegex(runner.PreregistrationError, message):
                    runner.bind_inputs(self.args)
        for name, key, value in (
            ("grounding-generation-config.json", "retry_count", 1),
            ("grounding-generation-config.json", "hidden_repair", True),
            ("grounding-generation-config.json", "parallel_tool_calls", True),
            ("grounding-isolation-policy.json", "hidden_retry", True),
            ("grounding-isolation-policy.json", "expected_answers_visible_to_runner", True),
            ("grounding-isolation-policy.json", "answer_call_policy", {}),
        ):
            original = runner.load_json(self.root / "benchmarks" / name)
            with self.subTest(key=key):
                self.write_config(name, {**original, key: value})
                with self.assertRaises((runner.BenchmarkRunError, runner.PreregistrationError)):
                    runner.bind_inputs(self.args)
                self.write_config(name, original)
        self.args.output.mkdir()
        with self.assertRaisesRegex(runner.BenchmarkRunError, "already exists"):
            runner.bind_inputs(self.args)

    def test_model_root_resolves_inventory_layout(self):
        model = self.root / "models/test/model.gguf"
        model.parent.mkdir(parents=True)
        model.write_bytes(self.model.read_bytes())
        self.args.model_path = None
        self.args.model_root = model.parent.parent
        prereg = runner.bind_inputs(self.args)
        self.assertEqual(prereg["model"]["path"], str(model.resolve()))

    def test_duplicate_serving_ids_rejected_before_output(self):
        real_load = runner.load_serving

        def duplicate(candidate):
            manifest, bundle, questions, faults = real_load(candidate)
            questions[1] = questions[0]
            return manifest, bundle, questions, faults

        with patch.object(runner, "load_serving", side_effect=duplicate):
            with self.assertRaisesRegex(runner.BenchmarkRunError, "serving corpus drift"):
                runner.bind_inputs(self.args)
        self.assertFalse(self.args.output.exists())

    def test_bound_file_drift_rejected(self):
        prereg = runner.bind_inputs(self.args)
        for path in (self.root / runner.SOURCE_FILES[0], self.model, self.runtime,
                     self.candidate / "serving/questions.jsonl"):
            original = path.read_bytes()
            with self.subTest(path=path):
                path.write_bytes(original + b" ")
                with self.assertRaises((runner.BenchmarkRunError, runner.PreregistrationError)):
                    runner.verify_bound_inputs(prereg)
                path.write_bytes(original)

    def test_failed_request_has_one_attempt_and_no_retry(self):
        prereg = runner.bind_inputs(self.args)
        with self.assertRaisesRegex(runner.BenchmarkRunError, "request failed"):
            self.execute(prereg, fail=True)
        status = runner.load_json(self.args.output / "run-status.json")
        self.assertEqual(status["state"], "invalid")
        self.assertEqual(status["model_answer_request_attempts"], 1)
        self.assertEqual(status["record_count"], 0)
        self.assertTrue((self.args.output / "SHA256SUMS").is_file())

    def test_final_drift_prevents_complete(self):
        with self.assertRaisesRegex(runner.BenchmarkRunError, "hash drift"):
            self.execute(runner.bind_inputs(self.args), drift=True)
        self.assertEqual(runner.load_json(self.args.output / "run-status.json")["state"], "invalid")

    def test_failed_stop_prevents_sealing(self):
        with self.assertRaisesRegex(runner.BenchmarkRunError, "stop failed"):
            self.execute(runner.bind_inputs(self.args), stop_fail=True)
        self.assertFalse((self.args.output / "SHA256SUMS").exists())

    def test_verify_only_has_no_output_or_inference(self):
        argv = ["--candidate", str(self.candidate), "--model-id", "test", "--model-path",
                str(self.model), "--runtime-executable", str(self.runtime),
                "--output", str(self.args.output), "--verify-only"]
        with patch.object(runner, "execute") as execute, patch("builtins.print"):
            self.assertEqual(runner.main(argv), 0)
            execute.assert_not_called()
        self.assertFalse(self.args.output.exists())

    def test_answer_only_contract_is_bound_and_normalized(self):
        self.args.g_contract = "answer-only-v1"
        prereg = runner.bind_inputs(self.args)
        requests = self.execute(prereg)
        self.assertEqual(prereg["g_contract"], "answer-only-v1")
        self.assertEqual(len(requests), 37)
        records = scorer.load_jsonl(self.args.output / "raw-results.jsonl")
        model_g = next(r for r in records if r["arm"] == "G" and r["output_source"] == "model")
        self.assertEqual(model_g["raw_content"], '"B3-04"')
        self.assertEqual(model_g["model_contract"], "answer-only-v1")
        self.assertTrue(model_g["model_contract_valid"])
        self.assertEqual(model_g["model_contract_output"], "B3-04")
        self.assertEqual(model_g["model_output"], {"a": "B3-04", "disposition": "answer"})
        scorer.verify_raw_model_record(model_g)
        self.assertTrue(any(request[0]["content"].startswith(runner.ANSWER_ONLY_SYSTEM_PROMPT) for request in requests))

    def test_answer_object_contract_is_bound_and_normalized(self):
        self.args.g_contract = "answer-object-v1"
        prereg = runner.bind_inputs(self.args)
        self.execute(prereg)
        records = scorer.load_jsonl(self.args.output / "raw-results.jsonl")
        model_g = next(r for r in records if r["arm"] == "G" and r["output_source"] == "model")
        self.assertEqual(model_g["raw_content"], '{"a":"B3-04"}')
        self.assertEqual(model_g["model_contract"], "answer-object-v1")
        self.assertEqual(model_g["model_contract_output"], "B3-04")
        self.assertEqual(model_g["model_output"], {"a": "B3-04", "disposition": "answer"})
        scorer.verify_raw_model_record(model_g)

    def test_answer_object_v2_contract_is_bound_and_normalized(self):
        self.args.g_contract = "answer-object-v2"
        prereg = runner.bind_inputs(self.args)
        requests = self.execute(prereg)
        records = scorer.load_jsonl(self.args.output / "raw-results.jsonl")
        model_g = next(r for r in records if r["arm"] == "G" and r["output_source"] == "model")
        self.assertEqual(model_g["model_contract"], "answer-object-v2")
        self.assertEqual(model_g["model_output"], {"a": "B3-04", "disposition": "answer"})
        scorer.verify_raw_model_record(model_g)
        self.assertTrue(any(request[0]["content"].startswith(runner.ANSWER_OBJECT_V2_SYSTEM_PROMPT)
                            for request in requests))

    def test_answer_object_v3_has_no_literal_value_placeholder(self):
        self.assertNotIn('{"a":"value"}', runner.ANSWER_OBJECT_V3_SYSTEM_PROMPT)
        self.args.g_contract = "answer-object-v3"
        prereg = runner.bind_inputs(self.args)
        requests = self.execute(prereg)
        records = scorer.load_jsonl(self.args.output / "raw-results.jsonl")
        model_g = next(r for r in records if r["arm"] == "G" and r["output_source"] == "model")
        self.assertEqual(model_g["model_contract"], "answer-object-v3")
        scorer.verify_raw_model_record(model_g)
        self.assertTrue(any(request[0]["content"].startswith(runner.ANSWER_OBJECT_V3_SYSTEM_PROMPT)
                            for request in requests))

    def test_answer_object_v4_targets_value_only_without_placeholder(self):
        self.assertNotIn('{"a":"value"}', runner.ANSWER_OBJECT_V4_SYSTEM_PROMPT)
        self.assertIn("shortest factual answer value", runner.ANSWER_OBJECT_V4_SYSTEM_PROMPT)
        self.args.g_contract = "answer-object-v4"
        prereg = runner.bind_inputs(self.args)
        requests = self.execute(prereg)
        records = scorer.load_jsonl(self.args.output / "raw-results.jsonl")
        model_g = next(r for r in records if r["arm"] == "G" and r["output_source"] == "model")
        self.assertEqual(model_g["model_contract"], "answer-object-v4")
        scorer.verify_raw_model_record(model_g)
        self.assertTrue(any(request[0]["content"].startswith(runner.ANSWER_OBJECT_V4_SYSTEM_PROMPT)
                            for request in requests))

    def test_answer_object_v5_is_short_and_bound(self):
        self.assertNotIn('{"a":"value"}', runner.ANSWER_OBJECT_V5_SYSTEM_PROMPT)
        self.assertLess(len(runner.ANSWER_OBJECT_V5_SYSTEM_PROMPT), len(runner.ANSWER_OBJECT_V4_SYSTEM_PROMPT))
        self.args.g_contract = "answer-object-v5"
        prereg = runner.bind_inputs(self.args)
        requests = self.execute(prereg)
        records = scorer.load_jsonl(self.args.output / "raw-results.jsonl")
        model_g = next(r for r in records if r["arm"] == "G" and r["output_source"] == "model")
        self.assertEqual(model_g["model_contract"], "answer-object-v5")
        scorer.verify_raw_model_record(model_g)
        self.assertTrue(any(request[0]["content"].startswith(runner.ANSWER_OBJECT_V5_SYSTEM_PROMPT)
                            for request in requests))

    def test_answer_object_v6_is_v1_without_literal_placeholder(self):
        self.assertNotIn('{"a":"value"}', runner.ANSWER_OBJECT_V6_SYSTEM_PROMPT)
        self.assertIn("Extract the shortest factual value", runner.ANSWER_OBJECT_V6_SYSTEM_PROMPT)
        self.args.g_contract = "answer-object-v6"
        prereg = runner.bind_inputs(self.args)
        requests = self.execute(prereg)
        records = scorer.load_jsonl(self.args.output / "raw-results.jsonl")
        model_g = next(r for r in records if r["arm"] == "G" and r["output_source"] == "model")
        self.assertEqual(model_g["model_contract"], "answer-object-v6")
        scorer.verify_raw_model_record(model_g)
        self.assertTrue(any(request[0]["content"].startswith(runner.ANSWER_OBJECT_V6_SYSTEM_PROMPT)
                            for request in requests))

    def test_auto_contract_calibration_is_separate_and_deterministic(self):
        self.args.g_contract = "answer-object-auto-v1"
        prereg = runner.bind_inputs(self.args)
        requests = self.execute(prereg)
        calibration = json.loads((self.args.output / "contract-calibration.json").read_text(encoding="utf-8"))
        status = json.loads((self.args.output / "run-status.json").read_text(encoding="utf-8"))
        records = scorer.load_jsonl(self.args.output / "raw-results.jsonl")
        model_g = next(r for r in records if r["arm"] == "G" and r["output_source"] == "model")
        self.assertEqual(calibration["selected_contract"], "answer-object-v1")
        self.assertEqual(calibration["model_request_count"], 12)
        self.assertEqual(status["selected_g_contract"], "answer-object-v1")
        self.assertEqual(status["calibration_model_requests"], 12)
        self.assertEqual(status["total_model_requests_including_calibration"], 49)
        self.assertEqual(status["host_grounded_scalar_count"], 13)
        self.assertEqual(model_g["model_contract"], "answer-object-v1")
        self.assertEqual(len(requests), 49)
        scorer.verify_run_integrity(self.args.output / "raw-results.jsonl", records,
                                    {record["item_id"] for record in records})

    def test_auto_v2_prefers_v3_on_calibration_tie(self):
        self.args.g_contract = "answer-object-auto-v2"
        prereg = runner.bind_inputs(self.args)
        self.execute(prereg)
        calibration = json.loads((self.args.output / "contract-calibration.json").read_text(encoding="utf-8"))
        status = json.loads((self.args.output / "run-status.json").read_text(encoding="utf-8"))
        self.assertEqual(calibration["tie_preference"], ["answer-object-v3", "answer-object-v4", "answer-object-v1"])
        self.assertEqual(calibration["selected_contract"], "answer-object-v3")
        self.assertEqual(status["selected_g_contract"], "answer-object-v3")

    def test_matched_a_g_uses_one_selected_release_surface_contract(self):
        self.args.g_contract = "answer-object-auto-v2"
        self.args.g_context = "skip-supplemental-empty"
        self.args.g_policy = "full"
        self.args.g_projection = "compact-stateful-v1"
        self.args.matched_a_g = True
        prereg = runner.bind_inputs(self.args)
        self.assertEqual(prereg["model_surface_sha256"], runner.v1_surface.surface_sha256())
        self.execute(prereg)
        raw = self.args.output / "raw-results.jsonl"
        records = scorer.load_jsonl(raw)
        status = runner.load_json(self.args.output / "run-status.json")
        self.assertEqual(status["selected_model_contract"], "answer-object-v3")
        self.assertEqual(status["model_surface_sha256"], prereg["model_surface_sha256"])
        model_records = [record for record in records if record["output_source"] == "model"]
        self.assertEqual(len(model_records), 37)
        self.assertTrue(model_records)
        self.assertEqual({record.get("model_contract") for record in model_records}, {"answer-object-v3"})
        scorer.verify_run_integrity(raw, records, {record["item_id"] for record in records})

    def test_skip_supplemental_empty_sends_zero_grounding_context(self):
        self.args.g_contract = "answer-object-v1"
        self.args.g_context = "skip-supplemental-empty"
        prereg = runner.bind_inputs(self.args)
        self.execute(prereg)
        records = scorer.load_jsonl(self.args.output / "raw-results.jsonl")
        skipped = [r for r in records if r["arm"] == "G" and r["output_source"] == "model"
                   and runner.supplemental_empty_frame(r["frame"])]
        grounded = [r for r in records if r["arm"] == "G" and r["output_source"] == "model"
                    and not runner.supplemental_empty_frame(r["frame"])]
        self.assertTrue(skipped)
        self.assertTrue(grounded)
        for record in skipped:
            self.assertEqual(record["context_route"], "ordinary-knowledge")
            self.assertFalse(record["grounding_context_sent"])
            self.assertEqual(record["projection_bytes"], 0)
            self.assertEqual(record["policy_bytes"], 0)
            self.assertEqual(record["sent_projection_bytes"], 0)
            self.assertEqual(record["sent_policy_bytes"], 0)
        for record in grounded:
            self.assertEqual(record["context_route"], "grounded-context")
            self.assertTrue(record["grounding_context_sent"])
            self.assertEqual(record["sent_projection_bytes"], record["projection_bytes"])
            self.assertEqual(record["sent_policy_bytes"], record["policy_bytes"])

    def test_compact_policy_records_actual_sent_policy(self):
        self.args.g_contract = "answer-object-v1"
        self.args.g_policy = "compact-v1"
        prereg = runner.bind_inputs(self.args)
        self.execute(prereg)
        records = scorer.load_jsonl(self.args.output / "raw-results.jsonl")
        model_g = [r for r in records if r["arm"] == "G" and r["output_source"] == "model"]
        self.assertTrue(model_g)
        for record in model_g:
            self.assertEqual(record["policy_bytes"], len(runner.COMPACT_GROUNDING_POLICY))
            self.assertEqual(record["sent_policy_bytes"], len(runner.COMPACT_GROUNDING_POLICY))
            self.assertEqual(record["sent_policy_sha256"], runner.sha256_bytes(runner.COMPACT_GROUNDING_POLICY))
            self.assertEqual(record["sent_projection_bytes"], record["projection_bytes"])

    def test_compact_projection_v2_keeps_single_target_label(self):
        frame = {"groups": [{"authority": "authoritative", "state": "grounded", "target_label": "Locker color",
                             "items": [{"content": {"kind": "text", "text": "The locker color is cobalt."}}]}]}
        v1 = runner.compact_model_projection(frame)
        v2 = runner.compact_model_projection(frame, include_single_target=True)
        self.assertNotIn(b'"t"', v1)
        self.assertIn(b'"t":"Locker color"', v2)
        self.assertIn(b'"v":"The locker color is cobalt."', v2)

    def test_compact_projection_records_actual_sent_projection(self):
        self.args.g_contract = "answer-object-v1"
        self.args.g_projection = "compact-v1"
        prereg = runner.bind_inputs(self.args)
        self.execute(prereg)
        records = scorer.load_jsonl(self.args.output / "raw-results.jsonl")
        model_g = [r for r in records if r["arm"] == "G" and r["output_source"] == "model"]
        self.assertTrue(model_g)
        for record in model_g:
            self.assertEqual(record["sent_projection_bytes"], record["projection_bytes"])
            self.assertEqual(record["sent_projection_sha256"], record["projection_sha256"])
            self.assertEqual(record["sent_policy_bytes"], record["policy_bytes"])

    def test_scorer_rejects_identity_and_raw_tampering_before_gold(self):
        self.execute(runner.bind_inputs(self.args))
        raw = self.args.output / "raw-results.jsonl"
        records = scorer.load_jsonl(raw)
        with patch.object(scorer, "verify_candidate", side_effect=AssertionError("gold opened")):
            with patch.object(scorer, "verify_serving_candidate", return_value={}):
                with self.assertRaisesRegex(scorer.ScoreError, "candidate identity"):
                    scorer.score(self.candidate, raw)
            for content in ('{"a":"changed","disposition":"answer"}', 'not JSON',
                            '{"a":null,"disposition":[]}',
                            '{"a":null,"a":null,"disposition":"abstain"}'):
                records[0]["raw_content"] = content
                raw.write_bytes(b"".join(canonical_bytes(r) + b"\n" for r in records))
                runner.write_sums(self.args.output)
                with self.subTest(raw=content), self.assertRaisesRegex(scorer.ScoreError, "raw_content/model_output"):
                    scorer.score(self.candidate, raw)
            records[0]["model_output"] = None
            raw.write_bytes(b"".join(canonical_bytes(r) + b"\n" for r in records))
            runner.write_sums(self.args.output)
            with self.assertRaisesRegex(AssertionError, "gold opened"):
                scorer.score(self.candidate, raw)
        self.assertEqual(len(scorer.score(self.candidate, raw)[1]), 60)


if __name__ == "__main__":
    unittest.main(verbosity=2)
