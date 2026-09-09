"""Focused, offline regressions for the public screen's validity and preregistration."""
import argparse
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch


spec = importlib.util.spec_from_file_location("public_suite", Path(__file__).with_name("run_v1_public_suite.py"))
suite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(suite)


def item(task="mmlu"):
    return {"benchmark_id": task, "source_index": 0, "kind": "multiple_choice",
            "question": "Pick A", "choices": [{"label": "A", "text": "yes"},
                                              {"label": "B", "text": "no"}], "answer": "A"}


def completion(content='{"choice":"A"}'):
    return {"choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3}}


class PublicSuiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        model_path = self.root / "model.gguf"
        model_path.write_bytes(b"model")
        self.model = {key: "test" for key in ("id", "family", "parameters", "bucket", "repository",
                                            "resolved_revision", "requested_file", "quantization")}
        self.model.update(path=str(model_path), bytes=5, sha256=suite.file_sha(model_path))
        self.args = argparse.Namespace(data_dir=self.root / "data", acquisition_manifest=self.root / "models.json",
                                       runtime_executable=self.root / "server", threads=2, context=4096, port=18400)
        self.args.acquisition_manifest.write_bytes(suite.canonical({"records": [self.model]}))
        self.args.runtime_executable.write_bytes(b"runtime")
        self.args.data_dir.mkdir()
        records = []
        for task in suite.TASK_IDS:
            path = self.args.data_dir / (task + ".jsonl")
            path.write_bytes(suite.canonical(item(task)))
            records.append({"id": task, "filename": path.name, "sha256": suite.file_sha(path), "item_count": 1})
        (self.args.data_dir / "manifest.json").write_bytes(suite.canonical({"tasks": records}))
        self.manifest, self.tasks = suite.verify_data(self.args.data_dir)

    def run_response(self, response):
        with patch.object(suite, "request_json", return_value=(response, 10)) as request:
            result = suite.run_item(1, "test", item())
        self.assertEqual(request.call_count, 1)
        self.assertEqual(request.call_args.args[1]["temperature"], 0)
        return result

    def test_failures_are_separate_from_wrong_answers_and_latency(self):
        good = self.run_response(completion())
        wrong = self.run_response(completion('{"choice":"B"}'))
        malformed = self.run_response(completion('{"choice":"Z"}'))
        protocol = self.run_response({"error": {"message": "failed"}})
        with patch.object(suite, "request_json", side_effect=TimeoutError("timeout")) as request:
            infrastructure = suite.run_item(1, "test", item())
        self.assertEqual(request.call_count, 1)
        for result, kind in [(malformed, "format"), (protocol, "protocol"), (infrastructure, "infrastructure")]:
            self.assertIsNone(result["correct"])
            self.assertEqual(result["error_kind"], kind)
            result["latency_us"] = 10000
        summary = suite.summarize(self.model, [good, wrong, malformed, protocol, infrastructure], {}, "runtime",
                                  data_manifest_sha="data")
        self.assertEqual(summary["status"], "FAIL")
        self.assertEqual(summary["total_errors"], 3)
        self.assertEqual(summary["total_wrong_answers"], 1)
        self.assertEqual(summary["tasks"]["mmlu"]["mean_latency_us"], 3340)
        self.assertEqual(summary["tasks"]["mmlu"]["latency_items"], 3)
        for kind in ("infrastructure", "protocol", "format"):
            self.assertEqual(summary[f"total_{kind}_errors"], 1)
        failed = suite.summarize(self.model, [malformed], {}, "runtime", data_manifest_sha="data")
        self.assertEqual(failed["status"], "PASS")
        self.assertEqual(failed["tasks"]["mmlu"]["mean_latency_us"], 10000)
        self.assertEqual(failed["tasks"]["mmlu"]["format_compliance"], 0)

    def test_malformed_structured_outputs(self):
        for content in ('no JSON', '[]', '{"choice":"A","extra":1}', '{"choice":"A","choice":"B"}',
                        '{"choice":1e999}', '{"choice":NaN}'):
            with self.subTest(content=content):
                self.assertEqual(self.run_response(completion(content))["error_kind"], "format")
        row = dict(item(), kind="numeric", answer="42")
        for answer in (42, "NaN", "Infinity", "", "x", "1" * 65):
            with self.subTest(answer=answer), patch.object(suite, "request_json", return_value=(completion(json.dumps({"answer": answer})), 10)):
                self.assertEqual(suite.run_item(1, "test", row)["error_kind"], "format")

    def test_malformed_protocol(self):
        for mutate in (lambda r: r.update(error="failed"), lambda r: r.update(usage=[]),
                       lambda r: r["choices"][0].update(index=True),
                       lambda r: r["choices"][0]["message"].update(role="user"),
                       lambda r: r["usage"].update(prompt_tokens=-1)):
            response = completion()
            mutate(response)
            self.assertEqual(self.run_response(response)["error_kind"], "protocol")
        response = completion()
        response["choices"][0]["finish_reason"] = "length"
        result = self.run_response(response)
        self.assertIsNone(result["error_kind"])
        self.assertTrue(result["correct"])

    def test_transport_does_not_redirect_or_retry(self):
        for status in (302, 307, 429, 500):
            connection = Mock()
            connection.getresponse.return_value.status = status
            with patch.object(suite.http.client, "HTTPConnection", return_value=connection):
                result = suite.run_item(1, "test", item())
            self.assertEqual(result["error_kind"], "protocol")
            connection.request.assert_called_once()
            connection.close.assert_called_once()

    def freeze(self):
        command = suite.server_command(self.args.runtime_executable, Path(self.model["path"]), "test", 18400, 2, 4096)
        return suite.freeze_protocol(self.args, self.model, self.manifest, self.tasks, command, {})

    def test_protocol_is_deterministic_and_binds_inputs(self):
        protocol = self.freeze()
        self.assertEqual(suite.canonical(protocol), suite.canonical(self.freeze()))
        for key in ("runner_source_sha256", "data_manifest_sha256", "runtime_executable_sha256"):
            self.assertEqual(len(protocol[key]), 64)
        self.assertEqual(protocol["model"], self.model)
        self.assertEqual(len(protocol["policy"]["requests"]), 6)
        self.assertEqual(protocol["policy"]["retry_count"], 0)
        self.assertEqual(protocol["policy"]["attempts_per_item"], 1)
        for request in protocol["policy"]["requests"]:
            self.assertEqual(request["payload"]["temperature"], 0)
            self.assertIn("response_format", request["payload"])
        path = self.root / "preregistration.json"
        path.write_bytes(suite.canonical(protocol))
        digest = suite.file_sha(path)
        suite.verify_frozen(protocol, path, digest)
        self.args.runtime_executable.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "frozen input drift"):
            suite.verify_frozen(protocol, path, digest)
        path.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "preregistration drift"):
            suite.verify_frozen(protocol, path, digest)

    def test_freeze_records_host_without_spawning_subprocess(self):
        with patch.object(suite.subprocess, "Popen", side_effect=AssertionError("subprocess before preregistration")) as launch:
            protocol = self.freeze()
        launch.assert_not_called()
        host = protocol["host"]
        self.assertEqual(host["platform"], suite.sys.platform)
        self.assertTrue(host["uname"]["system"])
        self.assertTrue(host["uname"]["release"])
        self.assertEqual(host["machine"], host["uname"]["machine"])
        self.assertEqual(host["python"], suite.sys.version)
        self.assertEqual(len(host["python_executable_sha256"]), 64)

    def test_rejects_loaded_manifest_and_data_drift(self):
        changed = copy.deepcopy(self.model)
        changed["resolved_revision"] = "changed"
        self.args.acquisition_manifest.write_bytes(suite.canonical({"records": [changed]}))
        with self.assertRaisesRegex(ValueError, "acquisition manifest changed"):
            self.freeze()
        self.args.acquisition_manifest.write_bytes(suite.canonical({"records": [self.model]}))
        self.tasks["mmlu"][0]["question"] = "changed in memory"
        with self.assertRaisesRegex(ValueError, "public data changed while loading"):
            self.freeze()

    def test_main_preregisters_before_inference_and_fails_on_drift_or_startup(self):
        for mode in ("success", "format", "drift", "startup"):
            with self.subTest(mode=mode):
                output = self.root / mode
                argv = ["runner", "--acquisition-manifest", str(self.args.acquisition_manifest),
                        "--data-dir", str(self.args.data_dir), "--runtime-executable", str(self.args.runtime_executable),
                        "--model-id", "test", "--output", str(output)]
                process = Mock()
                process.poll.return_value = None

                def launch(*args, **kwargs):
                    self.assertTrue((output / "preregistration.json").is_file())
                    if mode == "startup":
                        raise OSError("cannot launch")
                    return process

                def infer(port, payload):
                    protocol = suite.load_json(output / "preregistration.json")
                    self.assertIn(payload, [r["payload"] for r in protocol["policy"]["requests"]])
                    if mode == "drift":
                        self.args.runtime_executable.write_bytes(b"changed runtime")
                    return completion("invalid" if mode == "format" else '{"choice":"A"}'), 10

                with patch.object(suite.sys, "argv", argv), patch.object(suite.socket, "socket"), \
                        patch.object(suite.subprocess, "Popen", side_effect=launch), \
                        patch.object(suite, "wait_server"), patch.object(suite, "stop_server"), \
                        patch.object(suite, "request_json", side_effect=infer) as request, \
                        contextlib.redirect_stdout(io.StringIO()):
                    code = suite.main()
                summary = suite.load_json(output / "summary.json")
                expected_pass = mode in {"success", "format"}
                self.assertEqual(code, 0 if expected_pass else 1)
                self.assertEqual(summary["status"], "PASS" if expected_pass else "FAIL")
                self.assertEqual(request.call_count, 0 if mode == "startup" else 6)
                self.assertEqual(summary["frozen_inputs_verified_after_run"], mode != "drift")
                if mode != "success":
                    self.assertGreater(summary["total_errors"], 0)
                if mode == "format":
                    self.assertEqual(summary["total_format_errors"], 6)
                    self.assertEqual(summary["total_execution_errors"], 0)


if __name__ == "__main__":
    unittest.main()
