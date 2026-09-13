#!/usr/bin/env python3
"""No-model tests for the attachable llama.cpp fast runtime identity experiment."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "adapters/llama-cpp/runtime_identity.py"
spec = importlib.util.spec_from_file_location("exactscope_llama_runtime_identity", MODULE_PATH)
assert spec is not None and spec.loader is not None
identity = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = identity
spec.loader.exec_module(identity)


class LlamaRuntimeIdentityTests(unittest.TestCase):
    def test_fetch_props_is_one_bounded_read_only_loopback_get(self):
        calls = []

        class Response:
            status = 200

            def read(self, limit):
                self.limit = limit
                return json.dumps({"build_info": "b1", "model_path": "C:/m.gguf", "chat_template": "tmpl"}).encode()

        class Connection:
            def __init__(self, host, port, timeout):
                calls.append(("connect", host, port, timeout))

            def request(self, method, path, headers):
                calls.append(("request", method, path, headers))

            def getresponse(self):
                return Response()

            def close(self):
                calls.append(("close",))

        with patch.object(identity.http.client, "HTTPConnection", Connection):
            props = identity.fetch_props("http://127.0.0.1:8080/v1", model="model/A", timeout_seconds=2)
        self.assertEqual(props["build_info"], "b1")
        self.assertEqual(calls[0], ("connect", "127.0.0.1", 8080, 2))
        self.assertEqual(calls[1][0:3], ("request", "GET", "/props?model=model%2FA"))
        self.assertEqual(calls[-1], ("close",))

    def test_probe_rejects_remote_dns_and_credentials(self):
        for url in (
            "http://example.com:8080/v1",
            "https://127.0.0.1:8080/v1",
            "http://user:secret@127.0.0.1:8080/v1",
        ):
            with self.subTest(url=url), self.assertRaises(identity.RuntimeIdentityError):
                identity._loopback_endpoint(url)

    def test_volatile_slot_state_does_not_churn_props_identity(self):
        left = {
            "build_info": "b1",
            "model_path": "C:/m.gguf",
            "chat_template": "tmpl",
            "is_sleeping": False,
            "default_generation_settings": {"id": 1, "id_task": 5, "is_processing": True, "n_ctx": 4096},
        }
        right = {
            "build_info": "b1",
            "model_path": "C:/m.gguf",
            "chat_template": "tmpl",
            "is_sleeping": True,
            "default_generation_settings": {"id": 9, "id_task": 999, "is_processing": False, "n_ctx": 4096},
        }
        self.assertEqual(identity._stable_props(left), identity._stable_props(right))
        self.assertEqual(identity._sha(identity._canonical(identity._stable_props(left))), identity._sha(identity._canonical(identity._stable_props(right))))

    def test_fast_file_fingerprint_is_bounded_and_detects_tail_change(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "model.gguf"
            path.write_bytes(b"A" * (identity.FILE_SAMPLE_BYTES * 3))
            first = identity.fast_file_fingerprint(str(path))
            self.assertIsNotNone(first)
            self.assertEqual(first["sampled_bytes_max"], 131072)
            with path.open("r+b") as handle:
                handle.seek(-1, 2)
                handle.write(b"B")
            second = identity.fast_file_fingerprint(str(path))
        self.assertIsNotNone(second)
        self.assertNotEqual(first["sample_sha256"], second["sample_sha256"])

    def test_discovery_marks_local_sample_only_as_cache_lookup_candidate_without_claiming_persistent_trust(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "model.gguf"
            path.write_bytes(b"model" * 40000)
            props = {
                "build_info": "b8123-abcdef",
                "model_path": str(path.resolve()),
                "chat_template": "{{ messages }}",
                "chat_template_caps": {"tools": True},
                "default_generation_settings": {"n_ctx": 8192, "speculative": False},
            }
            with patch.object(identity, "fetch_props", return_value=props):
                result = identity.discover_runtime_identity("http://127.0.0.1:8080/v1", model="local")
        self.assertTrue(result["cache_lookup_candidate"])
        self.assertFalse(result["persistent_cache_ok"])
        self.assertEqual(result["confidence"], "metadata+local-file-sample-candidate")
        self.assertEqual(result["required_before_persistent_reuse"], "full-model-identity-or-semantic-revalidation")
        self.assertFalse(result["full_model_sha256"])
        self.assertEqual(result["network_model_requests"], 0)
        self.assertEqual(result["metadata_requests"], 1)
        self.assertLessEqual(result["sampled_model_bytes_max"], 131072)
        self.assertTrue(result["model_key"].startswith("auto-llamacpp-v1:"))
        self.assertNotIn(str(path), json.dumps(result))

    def test_metadata_only_identity_is_session_scope_not_persistent(self):
        props = {"build_info": "b1", "model_path": "relative/model.gguf", "chat_template": "tmpl"}
        with patch.object(identity, "fetch_props", return_value=props):
            result = identity.discover_runtime_identity("http://127.0.0.1:8080/v1")
        self.assertFalse(result["cache_lookup_candidate"])
        self.assertFalse(result["persistent_cache_ok"])
        self.assertEqual(result["confidence"], "metadata-only-session-scope")
        self.assertIsNone(result["model_file_sample_sha256"])


if __name__ == "__main__":
    unittest.main()
