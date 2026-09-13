#!/usr/bin/env python3
"""No-network tests for the experimental OpenAI-compatible portability slice."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


transport = load_module("exactscope_openai_transport", ROOT / "adapters/openai-compatible/transport.py")
surface = load_module("exactscope_openai_surface", ROOT / "adapters/openai-compatible/surface.py")
grounding = load_module("exactscope_openai_grounding", ROOT / "adapters/openai-compatible/grounding_v1.py")
PROFILE = ROOT / "grounding/reference-profile-v0.1"


class OpenAICompatibleAdapterTests(unittest.TestCase):
    def test_prepare_endpoint_accepts_v1_v3_and_explicit_chat_paths(self):
        v1 = transport.prepare_endpoint("http://127.0.0.1:8000/v1/")
        self.assertEqual((v1.scheme, v1.host, v1.port, v1.chat_path), ("http", "127.0.0.1", 8000, "/v1/chat/completions"))
        v3 = transport.prepare_endpoint("https://example.com/v3")
        self.assertEqual((v3.scheme, v3.host, v3.port, v3.chat_path), ("https", "example.com", 443, "/v3/chat/completions"))
        explicit = transport.prepare_endpoint("https://example.com/custom/chat/completions")
        self.assertEqual(explicit.chat_path, "/custom/chat/completions")

    def test_prepare_endpoint_rejects_embedded_credentials_query_and_unknown_scheme(self):
        for value in (
            "ftp://example.com/v1",
            "http://user:pass@example.com/v1",
            "https://example.com/v1?token=secret",
            "https://example.com/v1#fragment",
        ):
            with self.subTest(value=value), self.assertRaises(transport.TransportError):
                transport.prepare_endpoint(value)

    def test_prepared_transport_posts_direct_json_and_normalizes_one_text_choice(self):
        class Response:
            status = 200

            def read(self, limit):
                self.limit = limit
                return json.dumps({
                    "choices": [{"message": {"content": '{"a":"ZX-41"}'}}],
                    "usage": {"prompt_tokens": 11, "completion_tokens": 4},
                }).encode("utf-8")

        class Connection:
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs
                self.request_args = None
                self.closed = False
                self.response = Response()

            def request(self, method, path, body, headers):
                self.request_args = (method, path, body, headers)

            def getresponse(self):
                return self.response

            def close(self):
                self.closed = True

        connection = Connection()
        endpoint = transport.prepare_endpoint("http://127.0.0.1:8000/v1")
        with patch.object(transport.http.client, "HTTPConnection", return_value=connection) as factory:
            response = endpoint.request(
                {"model": "m", "stream": False, "messages": [{"role": "user", "content": "q"}]},
                authorization="Bearer test-token",
                timeout_seconds=7,
            )
        factory.assert_called_once_with("127.0.0.1", 8000, timeout=7)
        self.assertEqual(connection.request_args[0:2], ("POST", "/v1/chat/completions"))
        self.assertEqual(connection.request_args[3]["Authorization"], "Bearer test-token")
        self.assertTrue(connection.closed)
        content, usage = transport.single_text_completion(response)
        self.assertEqual(content, '{"a":"ZX-41"}')
        self.assertEqual(usage, {"prompt_tokens": 11, "completion_tokens": 4})

    def test_models_metadata_uses_matching_api_base_and_single_model_is_fail_closed(self):
        class Response:
            status = 200

            def read(self, _limit):
                return b'{"data":[{"id":"only-model"}]}'

        class Connection:
            def __init__(self, *_args, **_kwargs):
                self.request_args = None

            def request(self, method, path, body, headers):
                self.request_args = (method, path, body, headers)

            def getresponse(self):
                return Response()

            def close(self):
                pass

        connection = Connection()
        endpoint = transport.prepare_endpoint("http://127.0.0.1:8000/v3")
        with patch.object(transport.http.client, "HTTPConnection", return_value=connection):
            response = endpoint.models()
        self.assertEqual(connection.request_args[0:3], ("GET", "/v3/models", None))
        self.assertEqual(transport.single_model_id(response), "only-model")
        for data in ([], [{"id": "a"}, {"id": "b"}], [{"object": "model"}]):
            with self.subTest(data=data), self.assertRaises(transport.TransportError):
                transport.single_model_id({"data": data})

    def test_transport_does_not_follow_http_errors_or_hide_protocol_status(self):
        class Response:
            status = 422

            def read(self, _limit):
                return b'{"error":"unsupported response_format"}'

        class Connection:
            def request(self, *_args, **_kwargs):
                pass

            def getresponse(self):
                return Response()

            def close(self):
                pass

        endpoint = transport.prepare_endpoint("http://127.0.0.1:8000/v1")
        with patch.object(transport.http.client, "HTTPConnection", return_value=Connection()):
            with self.assertRaises(transport.HTTPStatusError) as caught:
                endpoint.request({"model": "m", "messages": []})
        self.assertEqual(caught.exception.status, 422)

    def test_surface_profiles_keep_backend_wire_differences_out_of_core_contract(self):
        schema = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]}
        standard = surface.constraint_fields(surface.STANDARD_JSON_SCHEMA, schema)
        self.assertEqual(standard["response_format"]["type"], "json_schema")
        self.assertEqual(standard["response_format"]["json_schema"]["schema"], schema)
        trt = surface.constraint_fields(surface.TRTLLM_GUIDED_JSON, schema)
        self.assertEqual(trt, {"response_format": {"type": "json", "schema": schema}})

    def test_integrated_adapter_keeps_core_plan_and_only_changes_wire_profile(self):
        captured = []

        class Endpoint:
            def request(self, payload, **kwargs):
                captured.append((payload, kwargs))
                return {
                    "choices": [{"message": {"content": '{"a":42}'}}],
                    "usage": {"prompt_tokens": 7, "completion_tokens": 3},
                }

        answer_spec = {"kind": "integer", "nullable": False, "minimum": 0, "maximum": 100}
        messages = [{"role": "system", "content": "contract"}, {"role": "user", "content": "q"}]
        standard = grounding.request_answer(
            Endpoint(),
            "model",
            "answer-object-v3",
            messages,
            wire_profile=surface.STANDARD_JSON_SCHEMA,
            answer_spec=answer_spec,
        )
        trt = grounding.request_answer(
            Endpoint(),
            "model",
            "answer-object-v3",
            messages,
            wire_profile=surface.TRTLLM_GUIDED_JSON,
            answer_spec=answer_spec,
        )
        self.assertEqual(standard["reply"], {"a": 42, "disposition": "answer"})
        self.assertEqual(trt["reply"], standard["reply"])
        self.assertEqual(captured[0][0]["response_format"]["type"], "json_schema")
        self.assertEqual(captured[1][0]["response_format"]["type"], "json")
        self.assertEqual(captured[0][0]["messages"], captured[1][0]["messages"])

    def test_integrated_plan_needs_no_model_endpoint(self):
        output = []
        with patch.object(grounding, "_print", side_effect=output.append):
            result = grounding.main([
                "plan",
                "--profile", str(PROFILE),
                "--question", "What is the capital of France?",
            ])
        self.assertEqual(result, 0)
        self.assertEqual(output[0]["route"], "ordinary-knowledge")
        self.assertTrue(output[0]["model_called"])
        self.assertEqual(output[0]["wire_profile"], surface.STANDARD_JSON_SCHEMA)

    def test_integrated_answer_auto_selects_only_single_exposed_model(self):
        captured = []

        class Endpoint:
            host = "127.0.0.1"

            def models(self, **kwargs):
                captured.append(("models", kwargs))
                return {"data": [{"id": "single-local-model"}]}

            def request(self, payload, **kwargs):
                captured.append(("answer", payload, kwargs))
                return {
                    "choices": [{"message": {"content": '{"a":"Paris"}'}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 3},
                }

        output = []
        with patch.object(grounding, "prepare_endpoint", return_value=Endpoint()), patch.object(
            grounding, "_print", side_effect=output.append
        ):
            result = grounding.main([
                "answer",
                "--profile", str(PROFILE),
                "--question", "What is the capital of France?",
            ])
        self.assertEqual(result, 0)
        self.assertEqual(captured[0][0], "models")
        self.assertEqual(captured[1][0], "answer")
        self.assertEqual(captured[1][1]["model"], "single-local-model")
        self.assertEqual(output[0]["reply"], {"a": "Paris", "disposition": "answer"})

    def test_integrated_adapter_requires_explicit_opt_in_for_remote_model(self):
        remote = transport.prepare_endpoint("https://models.example.com/v1")
        with self.assertRaisesRegex(grounding.AdapterError, "allow-remote-model"):
            grounding._allow_endpoint(remote, False)
        grounding._allow_endpoint(remote, True)


if __name__ == "__main__":
    unittest.main()
