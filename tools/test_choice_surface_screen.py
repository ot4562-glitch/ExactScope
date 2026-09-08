"""No model process or network is used by these renderer-screen tests."""
from __future__ import annotations

import argparse
from collections import Counter
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import choice_surface_screen as screen
from choice_codec import schema_json
from choice_prompt import (
    COMPACT_STRING_RENDERER_ID,
    COMPACT_VALUE_RENDERER_ID,
    RENDERER_IDS,
    VERBOSE_RENDERER_ID,
    render_choice_variant,
    renderer_hash,
)


class ScreenTests(unittest.TestCase):
    def run_fake(self, overrides=None):
        calls = []
        overrides = overrides or {}

        def request(launch, payload):
            renderer_index = len(calls) // len(screen.RUN_CASES)
            case_index = len(calls) % len(screen.RUN_CASES)
            renderer_id = RENDERER_IDS[renderer_index]
            case = screen.RUN_CASES[case_index]
            calls.append((renderer_id, case, payload))
            answer = overrides.get((renderer_id, case.name), overrides.get(case.name, json.dumps({"a": case.expected})))
            if isinstance(answer, Exception):
                raise answer
            return json.dumps({
                "choices": [{"message": {"content": answer}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 42, "completion_tokens": 5},
            })

        result = screen.run_screen({"alias": "test"}, {"model_sha256": "fake"}, request)
        self.assertEqual(len(calls), len(RENDERER_IDS) * len(screen.RUN_CASES))
        return result, calls

    def test_frozen_balanced_families_and_preference_selection(self):
        self.assertEqual(Counter(case.expected for case in screen.CASES if case.family == "copy"),
                         {"dax": 1, "pel": 1, "vek": 1})
        for family in screen.SEMANTIC_FAMILIES:
            self.assertEqual(Counter(case.expected for case in screen.CASES if case.family == family),
                             {"dax": 1, "pel": 1, "vek": 1})
        result, calls = self.run_fake()
        self.assertEqual(result["status"], "supported")
        self.assertEqual(result["non_null_status"], "supported")
        self.assertEqual(result["null_status"], "supported")
        self.assertEqual(result["selected_renderer"], COMPACT_VALUE_RENDERER_ID)
        self.assertEqual(result["malformed_outputs"], 0)
        for renderer_id in RENDERER_IDS:
            summary = result["renderers"][renderer_id]
            self.assertTrue(summary["qualified_non_null"])
            self.assertEqual(set(summary["reachable_labels"]), {"dax", "pel", "vek"})
            self.assertEqual(summary["min_family_accuracy"], 1.0)
            self.assertEqual(summary["overall_semantic_accuracy"], 1.0)
            self.assertEqual(summary["renderer_sha256"], renderer_hash(renderer_id))
        for renderer_id, case, payload in calls:
            self.assertEqual(payload["messages"], render_choice_variant(case.spec, case.input_value, renderer_id))
            self.assertEqual(payload["response_format"]["json_schema"]["schema"], json.loads(schema_json(case.spec)))
            self.assertEqual(payload["n"], 1)
            self.assertEqual(payload["temperature"], 0)
            self.assertEqual(payload["seed"], 0)

    def test_renderer_fallback_when_preferred_fails(self):
        result, _ = self.run_fake({(COMPACT_VALUE_RENDERER_ID, "numeric-middle"): '{"a":"dax"}'})
        self.assertEqual(result["status"], "supported")
        self.assertFalse(result["renderers"][COMPACT_VALUE_RENDERER_ID]["qualified_non_null"])
        self.assertEqual(result["selected_renderer"], COMPACT_STRING_RENDERER_ID)

    def test_verbose_fallback_preserves_request_and_contract_identity(self):
        overrides = {(renderer_id, "numeric-middle"): '{"a":"dax"}'
                     for renderer_id in (COMPACT_STRING_RENDERER_ID, COMPACT_VALUE_RENDERER_ID)}
        result, _ = self.run_fake(overrides)
        self.assertEqual(result["selected_renderer"], VERBOSE_RENDERER_ID)
        self.assertEqual(result["selected_renderer_sha256"], renderer_hash(VERBOSE_RENDERER_ID))
        for case in screen.RUN_CASES:
            rows = [row for row in result["cases"] if row["case"] == case.name]
            self.assertEqual(len(rows), 3)
            baseline = rows[0]
            for row in rows:
                for key in ("surface_sha256", "contract_sha256", "schema_json", "expected"):
                    self.assertEqual(row[key], baseline[key])
                settings = {key: value for key, value in row["request"].items() if key != "messages"}
                self.assertEqual(settings, {key: value for key, value in baseline["request"].items()
                                            if key != "messages"})
                self.assertEqual(row["raw_output"], json.loads(row["raw_response"])["choices"][0]["message"]["content"])
                self.assertEqual(row["input_tokens"], 42)
                self.assertEqual(row["output_tokens"], 5)
                self.assertGreaterEqual(row["latency_us"], 0)

    def test_all_renderers_wrong_semantics_or_unreachable_are_unsupported(self):
        for case_name in ("evidence-support", "copy-dax"):
            overrides = {(renderer_id, case_name): '{"a":"pel"}' for renderer_id in RENDERER_IDS}
            with self.subTest(case=case_name):
                result, _ = self.run_fake(overrides)
                self.assertEqual(result["status"], "unsupported")
                self.assertIsNone(result["selected_renderer"])

    def test_malformed_outputs_are_never_repaired(self):
        overrides = {(renderer_id, "copy-dax"): '{"a":"DAX"}' for renderer_id in RENDERER_IDS}
        result, _ = self.run_fake(overrides)
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(result["malformed_outputs"], len(RENDERER_IDS))
        failures = [row for row in result["cases"] if row["case"] == "copy-dax"]
        self.assertTrue(all(row["parse_result"] == {"type": "ChoiceFailure"} for row in failures))

    def test_null_is_reported_separately_from_non_null_selection(self):
        overrides = {(renderer_id, "null-enabled"): '{"a":"vek"}' for renderer_id in RENDERER_IDS}
        result, _ = self.run_fake(overrides)
        self.assertEqual(result["non_null_status"], "supported")
        self.assertEqual(result["selected_renderer"], COMPACT_VALUE_RENDERER_ID)
        self.assertEqual(result["null_status"], "unsupported")
        self.assertEqual(result["status"], "supported")

    def test_transport_error_no_retry(self):
        overrides = {(renderer_id, "copy-dax"): TimeoutError("synthetic timeout") for renderer_id in RENDERER_IDS}
        result, calls = self.run_fake(overrides)
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(len(calls), len(RENDERER_IDS) * len(screen.RUN_CASES))
        errors = [row for row in result["cases"] if row["case"] == "copy-dax"]
        self.assertTrue(all("synthetic timeout" in row["error"] for row in errors))

    def test_preferred_null_failure_does_not_select_another_renderer(self):
        for answer in ('{"a":"vek"}', 'not JSON', TimeoutError("null timeout")):
            with self.subTest(answer=answer):
                result, _ = self.run_fake({(COMPACT_VALUE_RENDERER_ID, "null-enabled"): answer})
                self.assertEqual(result["selected_renderer"], COMPACT_VALUE_RENDERER_ID)
                self.assertEqual(result["non_null_status"], "supported")
                self.assertEqual(result["null_status"], "unsupported")
                self.assertEqual(result["renderers"][COMPACT_STRING_RENDERER_ID]["null_status"], "supported")

    def test_wire_request_and_missing_accounting(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"choices":[{"message":{"content":"{\\"a\\":\\"dax\\"}"}}]}'
        with patch.object(screen.urllib.request, "urlopen", return_value=response) as opened:
            result = screen.run_screen({"alias": "test", "host": "127.0.0.1", "port": 8080}, {})
        self.assertEqual(opened.call_count, len(RENDERER_IDS) * len(screen.RUN_CASES))
        request = opened.call_args.args[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/v1/chat/completions")
        self.assertEqual(json.loads(request.data)["response_format"]["json_schema"]["schema"],
                         json.loads(schema_json(screen.NULL_SPEC)))
        self.assertIsNone(result["cases"][0]["input_tokens"])
        self.assertEqual(result["cases"][0]["parse_result"]["type"], "ChoiceSuccess")

    def test_pinned_identity_and_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable, model = root / "server", root / "model"
            executable.write_bytes(b"invented executable")
            model.write_bytes(b"invented model")
            runtime, inventory = root / "runtime.json", root / "inventory.json"
            runtime.write_text(json.dumps({"family": "llama.cpp", "runtime_id": "synthetic",
                                           "executable_sha256": screen.file_sha(executable)}))
            inventory.write_text(json.dumps({"records": [{"id": "invented", "runtime": "llama.cpp",
                "bytes": model.stat().st_size, "sha256": screen.file_sha(model)}]}))
            args = argparse.Namespace(runtime_record=runtime, runtime_sha256=screen.file_sha(runtime),
                inventory=inventory, inventory_sha256=screen.file_sha(inventory),
                executable=executable, model=model, model_id="invented")
            self.assertEqual(screen.verify_inputs(args)[3]["model_sha256"], screen.file_sha(model))
            model.write_bytes(b"changed model!")
            with self.assertRaisesRegex(ValueError, "model size/hash mismatch"):
                screen.verify_inputs(args)
            with self.assertRaisesRegex(ValueError, "record hash mismatch"):
                screen.pinned_record(runtime, "0" * 64)

    def test_startup_failure_stops_process_without_generation(self):
        runtime = {"launch": {"host": "127.0.0.1", "port": 8080}, "server_ready_timeout_seconds": 1}
        process = unittest.mock.MagicMock()
        process.poll.return_value = None
        argv = [item for name in ("runtime-record", "runtime-sha256", "executable", "inventory",
                                  "inventory-sha256", "model-id", "model")
                for item in ("--" + name, "synthetic")]
        with patch.object(screen, "verify_inputs", return_value=(runtime, Path("server"), Path("model"), {})), \
                patch.object(screen, "server_command", return_value=["server"]), \
                patch.object(screen.socket, "socket"), \
                patch.object(screen.subprocess, "Popen", return_value=process) as start, \
                patch.object(screen, "wait_server", side_effect=TimeoutError("startup")), \
                patch.object(screen, "run_screen") as run, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(screen.main(argv), 1)
        start.assert_called_once()
        run.assert_not_called()
        process.terminate.assert_called_once()
        process.wait.assert_called_once_with(timeout=10)
        self.assertEqual(json.loads(output.getvalue())["status"], "unsupported")


if __name__ == "__main__":
    unittest.main()
