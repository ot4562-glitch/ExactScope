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

from grounding_answer_contract import compile_answer_spec
from grounding_canonical import canonical_bytes
from grounding_corpus import build_index
import grounding_engine as engine
import grounding_v1_surface as surface
import run_grounding_benchmark as benchmark
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

    def test_task_specific_answer_choices_are_equivalent_on_json_schema_and_gbnf(self):
        choices = ("SUPPORTS", "REFUTES", "NOT ENOUGH INFO")
        schema_fields = surface.output_surface_request_fields("json-schema-v1", answer_choices=choices)
        schema = schema_fields["response_format"]["json_schema"]["schema"]
        self.assertEqual(schema["properties"]["a"]["enum"], list(choices))
        self.assertNotIn("null", schema["properties"]["a"].get("type", ""))
        grammar = surface.output_surface_request_fields("compact-gbnf-v1", answer_choices=choices)["grammar"]
        for choice in choices:
            self.assertIn(choice, grammar)
        for invalid in (("ONLY-ONE",), ("A", "A"), ("A", " bad")):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                surface.validate_answer_choices(invalid)

    def test_local_endpoint_is_enforced(self):
        self.assertEqual(adapter.validate_local_base_url("http://127.0.0.1:8080/v1"), "http://127.0.0.1:8080/v1")
        self.assertEqual(adapter.validate_local_base_url("http://127.0.0.2:8080/v1/"), "http://127.0.0.2:8080/v1")
        self.assertEqual(adapter.validate_local_base_url("http://[::1]:8080/v1/"), "http://[::1]:8080/v1")
        for url in (
            "http://localhost:8080/v1",
            "https://127.0.0.1:8080/v1",
            "http://example.com/v1",
            "http://user@127.0.0.1:8080/v1",
        ):
            with self.subTest(url=url), self.assertRaises(adapter.AdapterError):
                adapter.validate_local_base_url(url)

    def test_request_uses_direct_bounded_http_connection_without_redirect_following(self):
        class Response:
            def __init__(self, status, payload):
                self.status = status
                self.payload = payload
                self.read_limit = None

            def read(self, limit):
                self.read_limit = limit
                return self.payload

        class Connection:
            def __init__(self, response):
                self.response = response
                self.request_args = None
                self.closed = False

            def request(self, method, path, body, headers):
                self.request_args = (method, path, body, headers)

            def getresponse(self):
                return self.response

            def close(self):
                self.closed = True

        payload = json.dumps({
            "choices": [{"message": {"content": '{"a":"ZX-41"}'}}],
            "usage": {"prompt_tokens": 4, "completion_tokens": 3},
        }).encode("utf-8")
        response = Response(200, payload)
        connection = Connection(response)
        with patch.object(adapter.http.client, "HTTPConnection", return_value=connection) as factory:
            result = adapter.request_answer(
                "http://127.0.0.1:8080/v1",
                "local",
                "answer-object-v3",
                [{"role": "user", "content": "probe"}],
            )
        factory.assert_called_once_with("127.0.0.1", 8080, timeout=60.0)
        self.assertEqual(connection.request_args[0:2], ("POST", "/v1/chat/completions"))
        self.assertEqual(response.read_limit, adapter.MAX_HTTP_RESPONSE_BYTES + 1)
        self.assertTrue(connection.closed)
        self.assertEqual(result["value"], "ZX-41")

        redirected = Connection(Response(302, b"redirect"))
        with patch.object(adapter.http.client, "HTTPConnection", return_value=redirected):
            with self.assertRaisesRegex(adapter.AdapterError, "HTTP 302"):
                adapter.request_answer(
                    "http://127.0.0.1:8080/v1",
                    "local",
                    "answer-object-v3",
                    [{"role": "user", "content": "probe"}],
                )
        self.assertTrue(redirected.closed)

        oversized = Connection(Response(200, b"x" * (adapter.MAX_HTTP_RESPONSE_BYTES + 1)))
        with patch.object(adapter.http.client, "HTTPConnection", return_value=oversized):
            with self.assertRaisesRegex(adapter.AdapterError, "bounded size"):
                adapter.request_answer(
                    "http://127.0.0.1:8080/v1",
                    "local",
                    "answer-object-v3",
                    [{"role": "user", "content": "probe"}],
                )
        self.assertTrue(oversized.closed)

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
            self.assertEqual(plan["corpus"]["projection_id"], engine.PRECISION_CONTEXT_PROJECTION_ID)
            self.assertEqual(plan["corpus"]["evidence_policy"], engine.ADAPTIVE_EVIDENCE_POLICY_ID)
            self.assertEqual(plan["corpus"]["max_evidence_bytes"], 2048)
            self.assertIn(plan["corpus"]["evidence_budget_bytes"], {512, 1024, 2048})
            self.assertLessEqual(plan["corpus"]["evidence_bytes"], plan["corpus"]["evidence_budget_bytes"])
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
        limited = replace(
            bundle,
            profile=profile,
            limits=replace(bundle.limits, model_context_bytes=len(bundle.policy)),
        )
        with patch.object(engine, "load_bundle", return_value=limited), self.assertRaisesRegex(
            engine.EngineError, "model context budget exceeded"
        ):
            adapter.plan_question(
                profile_dir=PROFILE,
                question="Where is the help desk?",
                qid="grounded-budget",
                scope=None,
                contract="answer-object-v3",
            )

    def test_local_corpus_can_overfetch_candidates_but_caps_projected_model_items(self):
        bundle = adapter.load_bundle(PROFILE)
        profile = copy.deepcopy(bundle.profile)
        profile["limits"]["model_items"] = 1
        limited = replace(
            bundle,
            profile=profile,
            limits=replace(bundle.limits, model_items=1),
        )
        index = build_index([
            {"id": "manual/a", "title": "Rover A", "text": "Rover filter clue is CODE-A."},
            {"id": "manual/b", "title": "Rover B", "text": "Rover filter clue is CODE-B."},
        ])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "corpus.json"
            path.write_bytes(canonical_bytes(index))
            with patch.object(engine, "load_bundle", return_value=limited):
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
        self.assertEqual(plan["corpus"]["retrieved_count"], 2)
        self.assertEqual(plan["corpus"]["hit_count"], 1)

    def test_explicit_session_reuses_one_validated_immutable_corpus_snapshot(self):
        index = build_index([
            {"id": "manual/a", "title": "Rover", "text": "Rover uses filter RM-F42."},
            {"id": "manual/b", "title": "Desk", "text": "Desk clearance is 17 cm."},
        ])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "corpus.json"
            path.write_bytes(canonical_bytes(index))
            session = engine.GroundingSession.open(PROFILE)
            with patch.object(engine, "load_corpus_index", wraps=engine.load_corpus_index) as loader:
                first = engine.plan_question(
                    profile_dir=PROFILE,
                    question="Which filter does Rover use?",
                    qid="session-1",
                    scope=None,
                    contract="answer-object-v3",
                    corpus_index=path,
                    session=session,
                )
                second = engine.plan_question(
                    profile_dir=PROFILE,
                    question="What is the desk clearance?",
                    qid="session-2",
                    scope=None,
                    contract="answer-object-v3",
                    corpus_index=path,
                    session=session,
                )
                self.assertEqual(loader.call_count, 1)
                original_sha = first["corpus"]["index_sha256"]
                path.write_bytes(canonical_bytes(build_index([{"id": "changed", "title": "Changed", "text": "Changed content."}])))
                after_disk_change = engine.plan_question(
                    profile_dir=PROFILE,
                    question="Which filter does Rover use?",
                    qid="session-3",
                    scope=None,
                    contract="answer-object-v3",
                    corpus_index=path,
                    session=session,
                )
                self.assertEqual(loader.call_count, 1)
            self.assertEqual(first["corpus"]["index_sha256"], second["corpus"]["index_sha256"])
            self.assertEqual(after_disk_change["corpus"]["index_sha256"], original_sha)
            fresh = engine.GroundingSession.open(PROFILE)
            changed_snapshot = fresh.corpus(path)
            self.assertNotEqual(changed_snapshot.sha256, original_sha)

    def test_plan_cli_answer_choices_preserve_task_routing(self):
        frame = {
            "groups": [{
                "target_key": "device:clearance",
                "target_label": "Device clearance",
                "authority": "authoritative",
                "state": "grounded",
                "items": [{"content": {"kind": "scalar", "type": "integer", "value": "17", "unit": "cm"}}],
            }]
        }
        output = io.StringIO()
        with patch.object(engine, "run_grounding_frame", return_value={"frame": frame, "audit": {}}), patch("sys.stdout", output):
            self.assertEqual(adapter.main([
                "plan", "--profile", str(PROFILE), "--question", "Is clearance safe?",
                "--contract", "answer-object-v3", "--answer-choice", "YES", "--answer-choice", "NO",
            ]), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["route"], "grounded-context")
        self.assertTrue(result["model_called"])
        self.assertIsNone(result["reply"])

    def test_plan_cli_exact_choice_can_use_grounded_scalar_without_model(self):
        frame = {
            "groups": [{
                "target_key": "device:clearance",
                "target_label": "Device clearance",
                "authority": "authoritative",
                "state": "grounded",
                "items": [{"content": {"kind": "scalar", "type": "integer", "value": "17", "unit": "cm"}}],
            }]
        }
        output = io.StringIO()
        with patch.object(engine, "run_grounding_frame", return_value={"frame": frame, "audit": {}}), patch("sys.stdout", output):
            self.assertEqual(adapter.main([
                "plan", "--profile", str(PROFILE), "--question", "Choose the exact clearance value.",
                "--contract", "answer-object-v3", "--answer-choice", "17 cm", "--answer-choice", "20 cm",
            ]), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["route"], "host-grounded-scalar")
        self.assertFalse(result["model_called"])
        self.assertEqual(result["reply"], {"a": "17 cm", "disposition": "answer"})

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
            {"route", "model_called", "reply", "selected_contract", "selected_output_surface", "profile_sha256"},
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

    def test_explicit_retrieval_query_never_reuses_model_instruction_for_corpus_search(self):
        index = build_index([
            {"id": "claim", "title": "Claim", "text": "The rover token is RM-F42."},
        ])
        model_instruction = "Classify using SUPPORTS REFUTES JSON. Claim: rover token RM-F42"
        retrieval_query = "rover token RM-F42"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "corpus.json"
            path.write_bytes(canonical_bytes(index))
            with patch.object(engine, "search_corpus", wraps=engine.search_corpus) as search_mock, patch.object(
                engine, "precision_context_evidence_projection_v5", wraps=engine.precision_context_evidence_projection_v5
            ) as projection_mock:
                plan = adapter.plan_question(
                    profile_dir=PROFILE,
                    question=model_instruction,
                    retrieval_query=retrieval_query,
                    qid="retrieval-split",
                    scope=None,
                    contract="answer-object-v3",
                    corpus_index=path,
                    corpus_top_k=2,
                )
        self.assertEqual(plan["route"], "local-corpus")
        self.assertEqual(search_mock.call_args.args[1], retrieval_query)
        self.assertEqual(projection_mock.call_args.args[2], retrieval_query)
        self.assertTrue(plan["messages"][1]["content"].startswith(model_instruction))
        self.assertNotEqual(search_mock.call_args.args[1], model_instruction)

    def test_generic_request_model_preserves_legacy_answer_schema(self):
        captured = {}

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b'{"choices":[{"message":{"content":"\\\"B3-04\\\""},"finish_reason":"stop"}],"usage":{"prompt_tokens":3,"completion_tokens":2}}'

        prereg = {"runtime": {"launch": {"alias": "m", "host": "127.0.0.1", "port": 8080}}}
        generation = {
            "temperature": 0,
            "seed": 1,
            "max_output_tokens": 8,
            "timeout_seconds": 1,
            "answer_schema": {"type": ["string", "null"], "maxLength": 64},
        }

        def fake_urlopen(request, timeout):
            captured["payload"] = json.loads(request.data)
            captured["timeout"] = timeout
            return Response()

        with patch.object(benchmark.urllib.request, "urlopen", side_effect=fake_urlopen):
            benchmark.request_model(prereg, generation, [{"role": "user", "content": "q"}])
        self.assertEqual(captured["payload"]["response_format"]["json_schema"]["schema"], generation["answer_schema"])
        self.assertEqual(captured["timeout"], 1)

    def test_explicit_retrieval_query_disables_host_scalar_answering(self):
        frame = {
            "groups": [{
                "target_key": "device:clearance",
                "target_label": "Device clearance",
                "authority": "authoritative",
                "state": "grounded",
                "items": [{"content": {"kind": "scalar", "type": "integer", "value": "17", "unit": "cm"}}],
            }]
        }
        with patch.object(engine, "run_grounding_frame", return_value={"frame": frame, "audit": {}}):
            plan = adapter.plan_question(
                profile_dir=PROFILE,
                question="Is the clearance greater than 20 cm? Answer yes or no.",
                retrieval_query="clearance",
                qid="scalar-instruction-split",
                scope=None,
                contract="answer-object-v3",
            )
        self.assertEqual(plan["route"], "grounded-context")
        self.assertTrue(plan["model_called"])
        self.assertIsNone(plan["reply"])
        self.assertIn("Is the clearance greater than 20 cm?", plan["messages"][1]["content"])
        self.assertIn("17 cm", plan["messages"][1]["content"])
        self.assertIn("Device clearance", plan["messages"][1]["content"])

    def test_explicit_retrieval_query_cannot_bypass_model_instruction_byte_budget(self):
        bundle = adapter.load_bundle(PROFILE)
        oversized = "x" * (bundle.profile["limits"]["query_bytes"] + 1)
        with self.assertRaisesRegex(engine.EngineError, "model instruction exceeds"):
            adapter.plan_question(
                profile_dir=PROFILE,
                question=oversized,
                retrieval_query="help desk",
                qid="oversized-instruction",
                scope=None,
                contract="answer-object-v3",
            )

    def test_model_runtime_fingerprint_binds_effective_launch_and_rejects_template_overrides(self):
        prereg = {
            "model": {"sha256": "a" * 64},
            "generation_config_sha256": "c" * 64,
            "runtime": {
                "runtime_id": "llama.cpp-test",
                "version": "1",
                "commit": "abc",
                "executable_sha256": "b" * 64,
                "executable_path": "/tmp/llama-server",
                "launch": {"alias": "m", "host": "127.0.0.1", "port": 8080, "context": 4096, "threads": 4, "parallel": 1, "jinja": True, "reasoning": "off", "mmproj": False},
            },
        }
        baseline = surface.model_runtime_fingerprint(prereg)
        changed_context = copy.deepcopy(prereg)
        changed_context["runtime"]["launch"]["context"] = 8192
        self.assertNotEqual(baseline, surface.model_runtime_fingerprint(changed_context))
        changed_reasoning = copy.deepcopy(prereg)
        changed_reasoning["runtime"]["launch"]["reasoning"] = "on"
        self.assertNotEqual(baseline, surface.model_runtime_fingerprint(changed_reasoning))
        changed_parallel = copy.deepcopy(prereg)
        changed_parallel["runtime"]["launch"]["parallel"] = 4
        self.assertNotEqual(baseline, surface.model_runtime_fingerprint(changed_parallel))
        changed_generation = copy.deepcopy(prereg)
        changed_generation["generation_config_sha256"] = "d" * 64
        self.assertNotEqual(baseline, surface.model_runtime_fingerprint(changed_generation))
        overridden = copy.deepcopy(prereg)
        overridden["runtime"]["launch"]["chat_template"] = "custom"
        with self.assertRaisesRegex(ValueError, "chat-template overrides"):
            surface.model_runtime_fingerprint(overridden)
        with self.assertRaisesRegex(benchmark.BenchmarkRunError, "chat-template overrides"):
            benchmark.server_command(overridden)

    def test_interrupted_calibration_persists_attempt_count_before_failure(self):
        prereg = {"runtime": {"launch": {"alias": "m", "host": "127.0.0.1", "port": 8080}}}
        generation = {"temperature": 0, "seed": 1, "max_output_tokens": 8, "timeout_seconds": 1}
        attempts = {"count": 0}
        calls = 0

        def fail_third(*_args, **_kwargs):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise benchmark.BenchmarkRunError("synthetic calibration failure")
            return {"model_contract_valid": True, "model_contract_output": "wrong"}

        with patch.object(benchmark, "request_grounding_v1_model", side_effect=fail_third):
            with self.assertRaisesRegex(benchmark.BenchmarkRunError, "synthetic calibration failure"):
                benchmark.calibrate_grounding_v1_contract(
                    prereg, generation, b"policy", "json-schema-v1", attempts
                )
        self.assertEqual(attempts["count"], 3)

    def test_surface_negotiation_falls_back_once_then_calibrates_only_selected_surface(self):
        calls = []

        def fake_request(_base_url, _model, contract, request_messages, **kwargs):
            surface_id = kwargs.get("output_surface")
            calls.append(surface_id)
            if surface_id == "json-schema-v1":
                raise adapter.SurfaceUnsupportedError("synthetic JSON schema failure")
            user = request_messages[1]["content"]
            expected = "ZX-41" if "bay code" in user or "surface probe" in user else "17 cm" if "clearance" in user else "cobalt" if "보관함" in user else "K-9"
            return {"valid": True, "value": expected, "reply": {"a": expected, "disposition": "answer"}}

        with patch.object(adapter, "request_answer", side_effect=fake_request):
            record = adapter.calibrate_contract(
                base_url="http://127.0.0.1:8080/v1",
                model="local",
                model_key="sha256:model-runtime-template",
                policy=b"policy",
            )
        self.assertEqual(record["selected_output_surface"], "compact-gbnf-v1")
        self.assertEqual(calls[:2], ["json-schema-v1", "compact-gbnf-v1"])
        self.assertEqual(len(calls), 6)
        self.assertEqual(calls[2:], ["compact-gbnf-v1"] * 4)
        self.assertEqual(record["retry_count"], 0)

    def test_staged_preflight_proves_common_v3_path_in_five_requests(self):
        calls = []

        def fake_request(_base_url, _model, _contract, request_messages, **kwargs):
            calls.append(kwargs.get("output_surface"))
            user = request_messages[1]["content"]
            expected = "ZX-41" if "bay code" in user or "surface probe" in user else "17 cm" if "clearance" in user else "cobalt" if "보관함" in user else "K-9"
            return {"valid": True, "value": expected, "reply": {"a": expected, "disposition": "answer"}}

        policy = b"policy"
        model_key = "sha256:staged-fast"
        with patch.object(adapter, "request_answer", side_effect=fake_request):
            record = adapter.calibrate_contract(
                base_url="http://127.0.0.1:8080/v1",
                model="local",
                model_key=model_key,
                policy=policy,
            )
        self.assertEqual(len(record["profiles"]), 1)
        self.assertEqual(record["stopping_rule"], adapter.PREFLIGHT_STOPPING_RULE)
        self.assertEqual(record["selected_output_surface"], "json-schema-v1")
        self.assertEqual(record["selected_contract"], "answer-object-v3")
        self.assertEqual(record["surface_probe_model_requests"], 1)
        self.assertEqual(record["contract_calibration_model_requests"], 4)
        self.assertEqual(record["model_request_count"], 5)
        self.assertEqual(len(calls), 5)
        self.assertEqual(len(record["profiles"]), 1)
        self.assertEqual(
            adapter.validate_contract_record(record, model_key=model_key, policy=policy),
            ("json-schema-v1", "answer-object-v3"),
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "staged.json"
            path.write_bytes(adapter._json_bytes(record) + b"\n")
            loaded = adapter.load_contract_record(path, model_key=model_key, policy=policy)
        self.assertEqual(loaded, record)

    def test_staged_preflight_fallback_surface_finishes_in_six_requests(self):
        calls = []

        def fake_request(_base_url, _model, _contract, request_messages, **kwargs):
            surface_id = kwargs.get("output_surface")
            calls.append(surface_id)
            if surface_id == "json-schema-v1":
                raise adapter.SurfaceUnsupportedError("synthetic JSON schema failure")
            user = request_messages[1]["content"]
            expected = "ZX-41" if "bay code" in user or "surface probe" in user else "17 cm" if "clearance" in user else "cobalt" if "보관함" in user else "K-9"
            return {"valid": True, "value": expected, "reply": {"a": expected, "disposition": "answer"}}

        with patch.object(adapter, "request_answer", side_effect=fake_request):
            record = adapter.calibrate_contract(
                base_url="http://127.0.0.1:8080/v1",
                model="local",
                model_key="sha256:staged-gbnf",
                policy=b"policy",
            )
        self.assertEqual(len(record["profiles"]), 1)
        self.assertEqual(record["selected_output_surface"], "compact-gbnf-v1")
        self.assertEqual(record["model_request_count"], 6)
        self.assertEqual(calls[:2], ["json-schema-v1", "compact-gbnf-v1"])
        self.assertEqual(calls[2:], ["compact-gbnf-v1"] * 4)

    def test_proof_preflight_falls_through_to_full_selector_when_preferred_is_not_perfect(self):
        calls = []

        def fake_request(_base_url, _model, contract, request_messages, **_kwargs):
            calls.append(contract)
            user = request_messages[1]["content"]
            expected = "ZX-41" if "bay code" in user or "surface probe" in user else "17 cm" if "clearance" in user else "cobalt" if "보관함" in user else "K-9"
            if "surface probe" in user:
                value = expected
            elif contract == "answer-object-v4":
                value = expected
            elif contract == "answer-object-v3":
                value = "wrong" if expected == "17 cm" else expected
            else:
                value = expected if expected == "ZX-41" else "wrong"
            return {"valid": True, "value": value, "reply": {"a": value, "disposition": "answer"}}

        policy = b"policy"
        with patch.object(adapter, "request_answer", side_effect=fake_request):
            record = adapter.calibrate_contract(
                base_url="http://127.0.0.1:8080/v1",
                model="local",
                model_key="sha256:selector-equivalence",
                policy=policy,
            )
        self.assertEqual(len(record["profiles"]), 3)
        self.assertEqual(record["selected_output_surface"], "json-schema-v1")
        self.assertEqual(record["selected_contract"], "answer-object-v4")
        self.assertEqual(record["surface_probe_model_requests"], 1)
        self.assertEqual(record["contract_calibration_model_requests"], 12)
        self.assertEqual(record["model_request_count"], 13)
        self.assertEqual(len(calls), 13)

    def test_staged_preflight_validator_rejects_unproven_early_stop(self):
        def fake_request(_base_url, _model, _contract, request_messages, **_kwargs):
            user = request_messages[1]["content"]
            expected = "ZX-41" if "bay code" in user or "surface probe" in user else "17 cm" if "clearance" in user else "cobalt" if "보관함" in user else "K-9"
            return {"valid": True, "value": expected, "reply": {"a": expected, "disposition": "answer"}}

        policy = b"policy"
        model_key = "sha256:staged-proof"
        with patch.object(adapter, "request_answer", side_effect=fake_request):
            record = adapter.calibrate_contract(
                base_url="http://127.0.0.1:8080/v1",
                model="local",
                model_key=model_key,
                policy=policy,
            )
        tampered = copy.deepcopy(record)
        tampered["profiles"][0]["cases"][0]["actual"] = "wrong"
        tampered["profiles"][0]["cases"][0]["correct"] = False
        tampered["profiles"][0]["score"] = 3
        with self.assertRaisesRegex(adapter.AdapterError, "stopped before contract selection was proven"):
            adapter.validate_contract_record(tampered, model_key=model_key, policy=policy)

    def test_surface_negotiation_does_not_misclassify_transport_failure_as_unsupported(self):
        calls = []

        def fail_transport(*_args, **kwargs):
            calls.append(kwargs.get("output_surface"))
            raise adapter.AdapterError("llama.cpp request failed: timed out")

        with patch.object(adapter, "request_answer", side_effect=fail_transport), self.assertRaisesRegex(
            adapter.AdapterError, "timed out"
        ):
            adapter.calibrate_contract(
                base_url="http://127.0.0.1:8080/v1",
                model="local",
                model_key="sha256:model-runtime-template",
                policy=b"policy",
            )
        self.assertEqual(calls, ["json-schema-v1"])

    def test_zero_semantic_calibration_is_unsupported(self):
        def fake_request(_base_url, _model, _contract, request_messages, **_kwargs):
            user = request_messages[1]["content"]
            if "surface probe" in user:
                return {"valid": True, "value": "ZX-41", "reply": {"a": "ZX-41", "disposition": "answer"}}
            return {"valid": True, "value": "wrong", "reply": {"a": "wrong", "disposition": "answer"}}

        with patch.object(adapter, "request_answer", side_effect=fake_request), self.assertRaisesRegex(
            adapter.AdapterError, "semantic calibration scored zero"
        ):
            adapter.calibrate_contract(
                base_url="http://127.0.0.1:8080/v1",
                model="local",
                model_key="sha256:model-zero",
                policy=b"policy",
            )

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
        self.assertEqual(record["selected_output_surface"], "json-schema-v1")
        self.assertEqual(record["surface_probe_model_requests"], 1)
        self.assertEqual(record["contract_calibration_model_requests"], 4)
        self.assertEqual(record["model_request_count"], 5)
        self.assertEqual(record["retry_count"], 0)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "contract.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            loaded = adapter.load_contract_record(path, model_key="sha256:model-a", policy=policy)
            self.assertEqual(loaded["selected_contract"], "answer-object-v3")
            with self.assertRaises(adapter.AdapterError):
                adapter.load_contract_record(path, model_key="sha256:model-b", policy=policy)
            with self.assertRaises(adapter.AdapterError):
                adapter.load_contract_record(path, model_key="sha256:model-a", policy=b"changed")
            tampered = copy.deepcopy(record)
            tampered["selected_output_surface"] = "compact-gbnf-v1"
            path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaisesRegex(adapter.AdapterError, "surface selection mismatch"):
                adapter.load_contract_record(path, model_key="sha256:model-a", policy=policy)
            tampered = copy.deepcopy(record)
            tampered["selected_contract"] = "answer-object-v1"
            path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaisesRegex(adapter.AdapterError, "contract selection mismatch"):
                adapter.load_contract_record(path, model_key="sha256:model-a", policy=policy)

            # Duplicate keys must fail closed even when both values are identical.
            encoded = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            path.write_text(encoded[:-1] + ',"model_key":"sha256:model-a"}', encoding="utf-8")
            with self.assertRaisesRegex(adapter.AdapterError, "cannot read grounding contract record"):
                adapter.load_contract_record(path, model_key="sha256:model-a", policy=policy)

    def test_model_key_is_bounded_before_any_calibration_request(self):
        with patch.object(adapter, "request_answer") as request, self.assertRaisesRegex(
            adapter.AdapterError, "bounded identity size"
        ):
            adapter.calibrate_contract(
                base_url="http://127.0.0.1:8080/v1",
                model="local",
                model_key="x" * (adapter.MODEL_KEY_MAX_BYTES + 1),
                policy=b"policy",
            )
        request.assert_not_called()

    def test_contract_record_size_is_bounded_before_json_parse(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "oversized.json"
            path.write_bytes(b" " * (adapter.MAX_CONTRACT_RECORD_BYTES + 1))
            with self.assertRaisesRegex(adapter.AdapterError, "contract record exceeds bounded size"):
                adapter.load_contract_record(path, model_key="bounded-record", policy=b"policy")

    def test_existing_calibration_output_fails_before_model_requests(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "contract.json"
            output.write_text("keep-me", encoding="utf-8")
            with patch.object(adapter, "calibrate_contract", side_effect=AssertionError("calibration should not run")) as calibrate, patch("builtins.print"):
                result = adapter.main([
                    "calibrate",
                    "--profile", str(PROFILE),
                    "--model", "local",
                    "--model-key", "existing-output",
                    "--output", str(output),
                ])
            self.assertEqual(result, 1)
            calibrate.assert_not_called()
            self.assertEqual(output.read_text(encoding="utf-8"), "keep-me")

    def test_doctor_validates_record_without_network_and_redacts_model_key(self):
        def fake_request(_base_url, _model, _contract, request_messages, **_kwargs):
            user = request_messages[1]["content"]
            expected = (
                "ZX-41" if "surface probe" in user or "bay code" in user
                else "17 cm" if "clearance" in user
                else "cobalt" if "보관함" in user
                else "K-9"
            )
            return {"valid": True, "value": expected, "reply": {"a": expected, "disposition": "answer"}}

        policy = adapter._profile_policy(PROFILE)
        model_key = "model-sha256:test;runtime-sha256:test;surface-config-sha256:test"
        with patch.object(adapter, "request_answer", side_effect=fake_request):
            record = adapter.calibrate_contract(
                base_url="http://127.0.0.1:8080/v1",
                model="local",
                model_key=model_key,
                policy=policy,
            )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "contract.json"
            path.write_bytes(adapter._json_bytes(record) + b"\n")
            with patch.object(adapter, "request_answer", side_effect=AssertionError("doctor attempted network")) as request, patch("builtins.print") as output:
                result = adapter.main([
                    "doctor",
                    "--profile", str(PROFILE),
                    "--contract-record", str(path),
                    "--model-key", model_key,
                ])
            self.assertEqual(result, 0)
            request.assert_not_called()
            rendered = output.call_args.args[0]
            payload = json.loads(rendered)
            self.assertEqual(payload["status"], "PASS")
            self.assertEqual(payload["network_requests"], 0)
            self.assertEqual(payload["selected_contract"], record["selected_contract"])
            self.assertEqual(payload["selected_output_surface"], record["selected_output_surface"])
            self.assertNotIn(model_key, rendered)

    def test_typed_answer_contracts_compile_and_validate_without_repair(self):
        boolean = {"kind": "boolean", "nullable": False}
        integer = {"kind": "integer", "nullable": False, "minimum": 0, "maximum": 100}
        number = {"kind": "number", "nullable": True, "minimum": -1.5, "maximum": 2.5}

        boolean_schema = surface.output_surface_request_fields("json-schema-v1", answer_spec=boolean)
        self.assertEqual(
            boolean_schema["response_format"]["json_schema"]["schema"]["properties"]["a"]["type"],
            "boolean",
        )
        integer_schema = surface.output_surface_request_fields("json-schema-v1", answer_spec=integer)
        integer_value = integer_schema["response_format"]["json_schema"]["schema"]["properties"]["a"]
        self.assertEqual((integer_value["type"], integer_value["minimum"], integer_value["maximum"]), ("integer", 0, 100))
        self.assertIn('"true"', surface.output_surface_request_fields("compact-gbnf-v1", answer_spec=boolean)["grammar"])
        self.assertIn("integer ::=", surface.output_surface_request_fields("compact-gbnf-v1", answer_spec=integer)["grammar"])
        self.assertIn("number ::=", surface.output_surface_request_fields("compact-gbnf-v1", answer_spec=number)["grammar"])

        self.assertEqual(surface.parse_answer_object('{"a":true}', boolean), (True, True))
        self.assertEqual(surface.parse_answer_object('{"a":"true"}', boolean), (False, None))
        self.assertEqual(surface.parse_answer_object('{"a":42}', integer), (True, 42))
        self.assertEqual(surface.parse_answer_object('{"a":101}', integer), (False, None))
        self.assertEqual(surface.parse_answer_object('{"a":1.25}', number), (True, 1.25))
        self.assertEqual(surface.parse_answer_object('{"a":null}', number), (True, None))

    def test_typed_authoritative_scalar_can_finish_in_zero_model_calls(self):
        frame = {
            "groups": [{
                "target_key": "device:count",
                "target_label": "Device count",
                "authority": "authoritative",
                "state": "grounded",
                "items": [{"content": {"kind": "scalar", "type": "integer", "value": "17", "unit": None}}],
            }]
        }
        with patch.object(engine, "run_grounding_frame", return_value={"frame": frame, "audit": {}}):
            plan = adapter.plan_question(
                profile_dir=PROFILE,
                question="How many devices are available?",
                qid="typed-zero-call",
                scope=None,
                contract="answer-object-v3",
                answer_spec={"kind": "integer", "nullable": False, "minimum": 0},
            )
        self.assertEqual(plan["route"], "host-grounded-scalar")
        self.assertFalse(plan["model_called"])
        self.assertEqual(plan["reply"], {"a": 17, "disposition": "answer"})
        self.assertEqual(plan["amplifier"]["second_model_calls"], 0)
        self.assertEqual(plan["amplifier"]["retry_count"], 0)

    def test_prefix_cache_key_is_stable_and_bound_to_policy_and_answer_contract(self):
        spec = {"kind": "integer", "nullable": False, "minimum": 0, "maximum": 100}
        first = adapter.prefix_cache_key("answer-object-v3", b"policy-a", spec)
        second = adapter.prefix_cache_key("answer-object-v3", b"policy-a", spec)
        self.assertEqual(first, second)
        self.assertNotEqual(first, adapter.prefix_cache_key("answer-object-v3", b"policy-b", spec))
        self.assertNotEqual(first, adapter.prefix_cache_key("answer-object-v3", b"policy-a", {"kind": "boolean", "nullable": False}))

    def test_identity_bound_capability_cache_calibrates_once_then_reuses(self):
        def fake_request(_base_url, _model, _contract, request_messages, **_kwargs):
            user = request_messages[1]["content"]
            expected = (
                "ZX-41" if "surface probe" in user or "bay code" in user
                else "17 cm" if "clearance" in user
                else "cobalt" if "보관함" in user
                else "K-9"
            )
            return {"valid": True, "value": expected, "reply": {"a": expected, "disposition": "answer"}}

        policy = b"cache-policy"
        model_key = "model+runtime+template:test-cache"
        with tempfile.TemporaryDirectory() as temp, patch.object(adapter, "request_answer", side_effect=fake_request):
            record, hit, path = adapter.load_or_calibrate_capability(
                cache_dir=Path(temp),
                base_url="http://127.0.0.1:8080/v1",
                model="local",
                model_key=model_key,
                policy=policy,
            )
            self.assertFalse(hit)
            self.assertTrue(path.exists())
            with patch.object(adapter, "calibrate_contract", side_effect=AssertionError("cache hit recalibrated")):
                reused, reused_hit, reused_path = adapter.load_or_calibrate_capability(
                    cache_dir=Path(temp),
                    base_url="http://127.0.0.1:8080/v1",
                    model="local",
                    model_key=model_key,
                    policy=policy,
                )
        self.assertTrue(reused_hit)
        self.assertEqual(reused_path, path)
        self.assertEqual(reused, record)

    def test_compiled_answer_spec_is_reused_without_recompilation(self):
        compiled = compile_answer_spec({"kind": "integer", "nullable": False, "minimum": 0, "maximum": 100})
        self.assertIs(compile_answer_spec(compiled), compiled)
        self.assertTrue(compiled.validate(42))
        self.assertFalse(compiled.validate(101))

    def test_prepared_amplifier_finalizes_with_compiled_contract_without_repair(self):
        session = engine.GroundingSession.open(PROFILE)
        amplifier = session.prepare(
            contract="answer-object-v3",
            answer_spec={"kind": "integer", "nullable": False, "minimum": 0, "maximum": 100},
        )
        with patch.object(engine, "compile_answer_spec", side_effect=AssertionError("finalizer recompiled contract")):
            self.assertEqual(amplifier.finalize_generation('{"a":42}'), {"a": 42, "disposition": "answer"})
            self.assertIsNone(amplifier.finalize_generation('{"a":101}'))
            self.assertIsNone(amplifier.finalize_generation('42'))

    def test_session_caches_equivalent_raw_answer_contracts_across_prepares(self):
        session = engine.GroundingSession.open(PROFILE)
        answer_spec = {"kind": "integer", "nullable": False, "minimum": 0, "maximum": 100}
        with patch.object(engine, "compile_answer_spec", wraps=engine.compile_answer_spec) as compiler:
            first = session.prepare(contract="answer-object-v3", answer_spec=answer_spec)
            second = session.prepare(contract="answer-object-v3", answer_spec=dict(answer_spec))
        self.assertEqual(compiler.call_count, 1)
        self.assertIs(first.answer_spec, second.answer_spec)

    def test_bound_snapshot_hot_path_does_not_reload_profile_or_corpus(self):
        index = build_index([{"id": "manual/a", "title": "Rover", "text": "Rover filter code is RM-F42."}])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "corpus.json"
            path.write_bytes(canonical_bytes(index))
            session = engine.GroundingSession.open(PROFILE)
            snapshot = session.bind_corpus(path)
            compiled = compile_answer_spec()
            amplifier = session.prepare(
                contract="answer-object-v3",
                corpus_index=snapshot,
                answer_spec=compiled,
            )
            with patch.object(engine, "load_bundle", side_effect=AssertionError("hot path reloaded profile")), patch.object(
                engine, "load_corpus_index", side_effect=AssertionError("hot path reloaded corpus")
            ), patch.object(engine, "compile_answer_spec", side_effect=AssertionError("hot path recompiled contract")), patch.object(
                engine, "system_prompt", side_effect=AssertionError("hot path rebuilt model prefix")
            ), patch.object(engine, "surface_sha256", side_effect=AssertionError("hot path rebuilt surface identity")):
                plan = amplifier.plan(
                    question="What is the Rover filter code?",
                    qid="bound-hot-path",
                    scope=None,
                )
        self.assertEqual(plan["route"], "local-corpus")
        self.assertEqual(plan["corpus"]["index_sha256"], snapshot.sha256)
        self.assertEqual(plan["amplifier"]["session_state"], "prepared-immutable-amplifier-v1")


if __name__ == "__main__":
    unittest.main()
