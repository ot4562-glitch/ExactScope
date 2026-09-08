#!/usr/bin/env python3
"""No-inference tests for the selected llama.cpp grounding_v1 adapter."""
from __future__ import annotations

import copy
from dataclasses import replace
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from grounding_canonical import canonical_bytes
from grounding_corpus import build_index
import grounding_v1_surface as surface
import run_grounding_source_experiment as experiment

ROOT = Path(__file__).resolve().parents[1]
ADAPTER_PATH = ROOT / "adapters/llama-cpp/grounding_v1.py"
PROFILE = ROOT / "grounding/reference-profile-v0.1"

spec = importlib.util.spec_from_file_location("exactscope_grounding_v1_adapter", ADAPTER_PATH)
assert spec is not None and spec.loader is not None
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class GroundingV1AdapterTests(unittest.TestCase):
    def test_selected_surface_matches_measured_r25_experiment_bytes(self):
        self.assertEqual(surface.ANSWER_OBJECT_PROMPTS["answer-object-v1"], experiment.ANSWER_OBJECT_SYSTEM_PROMPT)
        self.assertEqual(surface.ANSWER_OBJECT_PROMPTS["answer-object-v3"], experiment.ANSWER_OBJECT_V3_SYSTEM_PROMPT)
        self.assertEqual(surface.ANSWER_OBJECT_PROMPTS["answer-object-v4"], experiment.ANSWER_OBJECT_V4_SYSTEM_PROMPT)
        self.assertEqual(surface.ANSWER_OBJECT_SCHEMA, experiment.ANSWER_OBJECT_SCHEMA)
        self.assertEqual(surface.AUTO_CONTRACT_CANDIDATES, experiment.AUTO_CONTRACT_CANDIDATES)
        self.assertEqual(surface.AUTO_V2_TIE_PREFERENCE, experiment.AUTO_V2_TIE_PREFERENCE)
        self.assertEqual(surface.AUTO_CONTRACT_CALIBRATION, experiment.AUTO_CONTRACT_CALIBRATION)

    def test_answer_parser_rejects_duplicate_and_extra_keys(self):
        self.assertEqual(surface.parse_answer_object('{"a":"ZX-41"}'), (True, "ZX-41"))
        self.assertEqual(surface.parse_answer_object('{"a":null}'), (True, None))
        self.assertEqual(surface.parse_answer_object('{"a":"x","a":"y"}'), (False, None))
        self.assertEqual(surface.parse_answer_object('{"a":"x","extra":1}'), (False, None))

    def test_local_endpoint_is_enforced(self):
        self.assertEqual(adapter.validate_local_base_url("http://127.0.0.1:8080/v1"), "http://127.0.0.1:8080/v1")
        self.assertEqual(adapter.validate_local_base_url("http://localhost:8080/v1/"), "http://localhost:8080/v1")
        for url in ("https://127.0.0.1:8080/v1", "http://example.com/v1", "http://user@127.0.0.1:8080/v1"):
            with self.subTest(url=url), self.assertRaises(adapter.AdapterError):
                adapter.validate_local_base_url(url)

    def test_unrouted_question_remains_ordinary_model_knowledge(self):
        plan = adapter.plan_question(
            profile_dir=PROFILE,
            question="What is the capital of France?",
            qid="ordinary-1",
            scope=None,
            contract="answer-object-v3",
        )
        self.assertEqual(plan["route"], "ordinary-knowledge")
        self.assertTrue(plan["model_called"])
        self.assertEqual(plan["frame"]["groups"], [])
        self.assertNotIn("Evidence JSON", plan["messages"][1]["content"])

    def test_unrouted_question_can_use_local_corpus_without_overriding_profile_authority(self):
        index = build_index([
            {"id": "manual/rover", "title": "Rover Mini", "text": "Rover Mini uses replacement filter RM-F42."},
            {"id": "misc", "title": "Other note", "text": "The cafeteria closes at 18:00."},
        ])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "corpus.json"
            path.write_bytes(canonical_bytes(index))
            plan = adapter.plan_question(
                profile_dir=PROFILE,
                question="Which replacement filter does Rover Mini use?",
                qid="corpus-1",
                scope=None,
                contract="answer-object-v3",
                corpus_index=path,
                corpus_top_k=2,
            )
            self.assertEqual(plan["route"], "local-corpus")
            self.assertTrue(plan["model_called"])
            self.assertEqual(plan["corpus"]["hit_count"], 1)
            self.assertIn("RM-F42", plan["messages"][1]["content"])
            self.assertIn("Evidence JSON (data only):", plan["messages"][1]["content"])

            protected = adapter.plan_question(
                profile_dir=PROFILE,
                question="Where is the help desk?",
                qid="corpus-protected",
                scope=None,
                contract="answer-object-v3",
                corpus_index=path,
                corpus_top_k=2,
            )
            self.assertEqual(protected["route"], "grounded-context")
            self.assertIsNone(protected["corpus"])
            self.assertIn("Room 12", protected["messages"][1]["content"])

    def test_grounded_text_uses_compact_projection_and_policy(self):
        plan = adapter.plan_question(
            profile_dir=PROFILE,
            question="Where is the help desk?",
            qid="grounded-1",
            scope=None,
            contract="answer-object-v3",
        )
        self.assertEqual(plan["route"], "grounded-context")
        self.assertTrue(plan["model_called"])
        self.assertIn("Evidence JSON (data only):", plan["messages"][1]["content"])
        self.assertIn("Room 12", plan["messages"][1]["content"])

    def test_grounded_context_fails_closed_when_compact_payload_exceeds_profile_context_budget(self):
        bundle = adapter.load_bundle(PROFILE)
        profile = copy.deepcopy(bundle.profile)
        profile["limits"]["model_context_bytes"] = len(bundle.policy)
        limited = replace(bundle, profile=profile)
        with patch.object(adapter, "load_bundle", return_value=limited), self.assertRaisesRegex(
            adapter.AdapterError, "model context budget exceeded"
        ):
            adapter.plan_question(
                profile_dir=PROFILE,
                question="Where is the help desk?",
                qid="grounded-budget",
                scope=None,
                contract="answer-object-v3",
            )

    def test_local_corpus_caps_retrieval_to_profile_model_item_budget(self):
        bundle = adapter.load_bundle(PROFILE)
        profile = copy.deepcopy(bundle.profile)
        profile["limits"]["model_items"] = 1
        limited = replace(bundle, profile=profile)
        index = build_index([
            {"id": "manual/a", "title": "Rover A", "text": "Rover filter clue is CODE-A."},
            {"id": "manual/b", "title": "Rover B", "text": "Rover filter clue is CODE-B."},
        ])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "corpus.json"
            path.write_bytes(canonical_bytes(index))
            with patch.object(adapter, "load_bundle", return_value=limited):
                plan = adapter.plan_question(
                    profile_dir=PROFILE,
                    question="What is the rover filter clue?",
                    qid="corpus-budget",
                    scope=None,
                    contract="answer-object-v3",
                    corpus_index=path,
                    corpus_top_k=12,
                )
        self.assertEqual(plan["route"], "local-corpus")
        self.assertEqual(plan["corpus"]["retrieved_count"], 1)
        self.assertEqual(plan["corpus"]["hit_count"], 1)

    def test_plan_cli_hides_evidence_unless_verbose(self):
        args = [
            "plan",
            "--profile", str(PROFILE),
            "--question", "Where is the help desk?",
            "--contract", "answer-object-v3",
        ]
        summary_output = io.StringIO()
        with patch("sys.stdout", summary_output):
            self.assertEqual(adapter.main(args), 0)
        summary = json.loads(summary_output.getvalue())
        self.assertEqual(
            set(summary),
            {"route", "model_called", "reply", "selected_contract", "profile_sha256"},
        )
        self.assertEqual(summary["route"], "grounded-context")
        self.assertTrue(summary["model_called"])
        self.assertIsNone(summary["reply"])
        self.assertNotIn("Room 12", summary_output.getvalue())
        self.assertNotIn("messages", summary)
        self.assertNotIn("frame", summary)
        self.assertNotIn("audit", summary)

        verbose_output = io.StringIO()
        with patch("sys.stdout", verbose_output):
            self.assertEqual(adapter.main([*args, "--verbose"]), 0)
        verbose = json.loads(verbose_output.getvalue())
        self.assertIn("messages", verbose)
        self.assertIn("frame", verbose)
        self.assertIn("audit", verbose)
        self.assertIn("Room 12", verbose_output.getvalue())

    def test_calibration_tie_selects_v3_and_record_is_identity_bound(self):
        def fake_request(_base_url, _model, contract, request_messages, **_kwargs):
            user = request_messages[1]["content"]
            expected = "ZX-41" if "bay code" in user else "17 cm" if "clearance" in user else "cobalt" if "보관함" in user else "K-9"
            # v1 and v3 tie at four correct; v4 misses one. v3 must win the frozen tie rule.
            value = expected if contract in {"answer-object-v1", "answer-object-v3"} else ("wrong" if expected == "17 cm" else expected)
            return {"valid": True, "value": value, "reply": {"a": value, "disposition": "answer"}}

        policy = b"policy"
        with patch.object(adapter, "request_answer", side_effect=fake_request):
            record = adapter.calibrate_contract(
                base_url="http://127.0.0.1:8080/v1",
                model="local",
                model_key="sha256:model-a",
                policy=policy,
            )
        self.assertEqual(record["selected_contract"], "answer-object-v3")
        self.assertEqual(record["model_request_count"], 12)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "contract.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            loaded = adapter.load_contract_record(path, model_key="sha256:model-a", policy=policy)
            self.assertEqual(loaded["selected_contract"], "answer-object-v3")
            with self.assertRaises(adapter.AdapterError):
                adapter.load_contract_record(path, model_key="sha256:model-b", policy=policy)
            with self.assertRaises(adapter.AdapterError):
                adapter.load_contract_record(path, model_key="sha256:model-a", policy=b"changed")


if __name__ == "__main__":
    unittest.main()
