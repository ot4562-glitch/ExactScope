"""Offline matrix/CLI regressions. All process creation is mocked or forbidden."""
import argparse
from contextlib import ExitStack, contextmanager, redirect_stdout
import copy
import csv
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1] / "tools")]
import run_v1_grounding_matrix as matrix
from grounding_canonical import canonical_bytes
from grounding_corpus import build_index, index_sha256

SELECT_RUNTIME = matrix.select_runtime


class MatrixTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(matrix.subprocess, "Popen", side_effect=AssertionError("real process forbidden")))
        model = self.root / "model.gguf"
        model.write_bytes(b"offline")
        digest = matrix.file_sha(model)
        rows = [dict(id=f"model-{n}", repository=f"repo/{n}", resolved_revision="a" * 40,
                     requested_file="model.gguf", quantization="Q4", bytes=7,
                     upstream_sha256=digest, sha256=digest, runtime="llama.cpp", path=str(model)) for n in range(20)]
        self.spec = dict(format="exactscope.v1-model-matrix", selection_policy=dict(frozen=True, model_count=20), models=copy.deepcopy(rows))
        self.acquisition = dict(format="exactscope.v1-model-acquisition", model_count=20, records=copy.deepcopy(rows))
        self.inventory = dict(format="exactscope.grounding-model-inventory", format_version="0.1", records=copy.deepcopy(rows))
        self.args = argparse.Namespace(matrix=self.root / "matrix.json", acquisition_manifest=self.root / "acquisition.json",
            model_inventory=self.root / "inventory.json", suite=self.root / "suite.json", runtime_record=self.root / "runtime.json",
            runtime_executable=self.root / "server", output=self.root / "output", port=18801, threads=2)
        matrix.write(self.args.matrix, self.spec)
        self.matrix_sha = matrix.file_sha(self.args.matrix)
        self.acquisition["matrix_sha256"] = self.inventory["source_inventory_sha256"] = self.matrix_sha
        matrix.write(self.args.acquisition_manifest, self.acquisition)
        matrix.write(self.args.model_inventory, self.inventory)
        self.args.runtime_executable.write_bytes(b"fake runtime")
        self.runtime = {"executable_sha256": matrix.file_sha(self.args.runtime_executable), "launch": {}}
        matrix.write(self.args.runtime_record, self.runtime)
        self.candidates = {task: self.make_candidate(task) for task in matrix.PANEL}
        matrix.write(self.args.suite, dict(format="exactscope.v1-public-benchmark-suite", exactscope_grounding_panel=[
            dict(id=task, candidate_path=str(path), arms=["A", "G"], items=1) for task, path in self.candidates.items()]))
        self.stack.enter_context(patch.object(matrix, "select_runtime", return_value=(self.args.runtime_record, self.runtime)))
        # Source discovery is independently exercised once, not sixty times per test.
        self.stack.enter_context(patch.object(matrix, "source_paths", return_value={Path(matrix.__file__)}))

    def make_candidate(self, task):
        candidate = self.root / task
        serving = candidate / "serving"
        serving.mkdir(parents=True)
        (candidate / "gold").mkdir()
        for name in ("manifest.json", "items.jsonl", "answers.jsonl", "confirmation-reservation.jsonl"):
            (candidate / "gold" / name).write_text("GOLD MUST NOT OPEN", encoding="utf-8")
        # Unconsumed files must not be swept into preflight hashes.
        (serving / "gold-backup.json").write_text("GOLD MUST NOT OPEN", encoding="utf-8")
        corpus = build_index([dict(id="doc", title="Title", text="A fact.")], source={"kind": "offline"})
        (serving / "corpus-index.json").write_bytes(canonical_bytes(corpus))
        manifest = dict(format_version="0.1", qualification_eligible=False, oracle_assisted_corpus=True,
                        corpus_index_sha256=index_sha256(corpus), item_count=1)
        if task == "natural_questions":
            files = {"questions.jsonl": {"eval_id": "q", "question": "What?"}, "chunks.jsonl": dict(chunk_id="doc", doc_id="doc", title="Title", text="A fact.", body_token_start=0, body_token_end=2)}
            manifest.update(format="exactscope.public-nq-serving-candidate", mode="oracle-page-pooled-corpus-development-v1",
                            split="search", search_item_count=1, chunk_count=1, document_count=1, source=dict(sha256="0" * 64))
        elif task == "fever":
            files = {"items.jsonl": {"id": "q", "claim": "A fact."}, "corpus-candidates.jsonl": dict(candidate_id="doc", page="Title", sentence_id=0, text="A fact.")}
            manifest.update(format="exactscope.public-fever-serving-candidate", mode="oracle-page-pooled-corpus-development-v1", corpus_candidate_count=1)
        else:
            files = {"questions.jsonl": {"item_id": "q", "question": "What?"}}
            manifest.update(format=matrix.hotpot.FORMAT, mode=matrix.hotpot.MODE, corpus_document_count=1)
        for name, row in files.items():
            path = serving / name
            path.write_bytes(canonical_bytes(row) + b"\n")
            manifest[name.replace(".jsonl", "").replace("-", "_") + "_sha256"] = matrix.file_sha(path)
        (candidate / "manifest.json" if task == "hotpotqa" else serving / "manifest.json").write_bytes(canonical_bytes(manifest))
        return candidate

    @contextmanager
    def no_gold(self):
        original = Path.open
        def guarded(path, *args, **kwargs):
            self.assertFalse(any("gold" in part.lower() for part in path.parts), f"gold access: {path}")
            return original(path, *args, **kwargs)
        with patch.object(Path, "open", guarded):
            yield

    def test_exact_twenty_models_and_upstream_digest_agreement(self):
        self.assertEqual(len(matrix.match_models(self.spec, self.acquisition, self.inventory, self.matrix_sha)), 20)
        mutations = [
            lambda s, a, i: s["models"].pop(),
            lambda s, a, i: a["records"].append(a["records"][0]),
            lambda s, a, i: i["records"][0].update(id="other"),
            lambda s, a, i: i["records"][0].update(id=i["records"][1]["id"]),
            lambda s, a, i: a.update(matrix_sha256="0" * 64),
            lambda s, a, i: i.update(source_inventory_sha256="0" * 64),
            lambda s, a, i: s["models"][0].update(upstream_sha256="0" * 64),
            lambda s, a, i: a["records"][0].update(upstream_sha256="0" * 64),
            lambda s, a, i: a["records"][0].update(sha256="0" * 64),
            lambda s, a, i: i["records"][0].update(sha256="0" * 64),
        ]
        for field in matrix.IDENTITY:
            mutations.append(lambda s, a, i, field=field: i["records"][0].update({field: "wrong"}))
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                s, a, i = copy.deepcopy((self.spec, self.acquisition, self.inventory))
                mutate(s, a, i)
                with self.assertRaises(ValueError):
                    matrix.match_models(s, a, i, self.matrix_sha)
        Path(self.acquisition["records"][0]["path"]).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "file identity"):
            matrix.match_models(self.spec, self.acquisition, self.inventory, self.matrix_sha)

    def test_preflight_no_gold_and_custom_command_routing(self):
        with self.no_gold():
            protocol = matrix.preflight(self.args)
        self.assertEqual(len(protocol["cells"]), 60)
        self.assertFalse(self.args.output.exists())
        self.assertFalse(any("gold" in p for p in protocol["frozen_files"]))
        ports = []
        for cell in protocol["cells"]:
            command = cell["run_command"]
            for flag, value in (("--model-inventory", self.args.model_inventory), ("--runtime-record", self.args.runtime_record)):
                self.assertEqual(command[command.index(flag) + 1], str(value))
            port = int(command[command.index("--port") + 1])
            self.assertEqual(cell["port"], port)
            ports.append(port)
        self.assertEqual(ports, list(range(self.args.port, self.args.port + 60)))
        self.assertEqual(len(set(ports)), 60)
        self.assertEqual(protocol["runtime"]["base_port"], self.args.port)
        self.assertIn("frozen cell index", protocol["runtime"]["port_policy"])

    def test_runtime_selection_requires_unique_digest_or_explicit_record(self):
        choices = [matrix.ROOT / "benchmarks/grounding-runtime-llama-v040.json",
                   matrix.ROOT / "benchmarks/grounding-runtime-llama-b10797-windows.json"]
        digest = matrix.file_sha(self.args.runtime_executable)
        for matches in (0, 1, 2):
            with self.subTest(matches=matches), patch.object(matrix, "read", side_effect=[
                    {"executable_sha256": digest if n < matches else "unknown"} for n in range(2)]), \
                    patch.object(matrix, "resolve_runtime", return_value=("sha", self.runtime)) as resolve:
                if matches == 1:
                    self.assertEqual(SELECT_RUNTIME(self.args.runtime_executable), (choices[0].resolve(), self.runtime))
                    resolve.assert_called_once_with(choices[0], self.args.runtime_executable)
                else:
                    with self.assertRaisesRegex(ValueError, "uniquely known"):
                        SELECT_RUNTIME(self.args.runtime_executable)
                    resolve.assert_not_called()
        with patch.object(matrix, "read", side_effect=AssertionError("unexpected auto-selection")), \
                patch.object(matrix, "resolve_runtime", return_value=("sha", self.runtime)) as resolve:
            self.assertEqual(SELECT_RUNTIME(self.args.runtime_executable, self.args.runtime_record),
                             (self.args.runtime_record, self.runtime))
            resolve.assert_called_once_with(self.args.runtime_record, self.args.runtime_executable)

    def test_matrix_cli_routes_phases_and_exit_status(self):
        argv = ["run", "--model-inventory", str(self.args.model_inventory),
                "--runtime-executable", str(self.args.runtime_executable), "--output", str(self.args.output)]
        with patch.object(matrix, "run_matrix", return_value=True) as run:
            self.assertEqual(matrix.main(argv), 0)
            args = run.call_args.args[0]
            self.assertEqual((args.port, args.threads, args.runtime_record), (18801, 6, None))
            self.assertEqual(args.matrix, matrix.ROOT / "benchmarks/v1-model-matrix-20.json")
            self.assertEqual(args.suite, matrix.ROOT / "benchmarks/v1-public-benchmark-suite.json")
            self.assertEqual(args.model_inventory, self.args.model_inventory)
        for success in (False, True):
            with patch.object(matrix, "score_matrix", return_value=success) as score:
                self.assertEqual(matrix.main(["score", "--output", str(self.args.output)]), 0 if success else 1)
                score.assert_called_once_with(self.args.output)

    def test_native_complete_runs_never_read_gold_and_use_custom_runtime(self):
        runtime = dict(self.runtime, executable_path=str(self.args.runtime_executable),
                       launch={"host": "127.0.0.1", "port": 18801})
        self.args.runtime_record.write_bytes(canonical_bytes(dict(self.runtime, server_ready_timeout_seconds=37)))
        response = dict(model_contract_valid=True, model_contract_output={}, raw_content="{}",
                        input_tokens=1, output_tokens=1, model_latency_us=1)
        for task, module in matrix.PANEL.items():
            args = argparse.Namespace(candidate=self.candidates[task], output=self.root / (task + "-complete"),
                model_id="model-0", model_root=None, model_path=None, model_inventory=self.args.model_inventory,
                runtime_record=self.args.runtime_record, runtime_executable=self.args.runtime_executable,
                top_k=12, max_evidence_bytes=4096, port=18801, threads=2)
            def launch(*unused, **kwargs):
                prereg = matrix.read(args.output / "preregistration.json")
                self.assertEqual(prereg["arms"], ["A", "G"])
                self.assertEqual(prereg["retry_count"], 0)
                self.assertFalse(prereg["gold_visible_to_runner"])
                return object()
            with self.subTest(task=task), self.no_gold(), ExitStack() as stack:
                model = stack.enter_context(patch.object(module, "resolve_model", return_value=("inventory", {"id": "model-0"})))
                resolved = stack.enter_context(patch.object(module, "resolve_runtime", return_value=("runtime", runtime)))
                process = stack.enter_context(patch.object(module.subprocess, "Popen", side_effect=launch))
                wait = stack.enter_context(patch.object(module, "wait_server"))
                stack.enter_context(patch.object(module, "stop_server"))
                stack.enter_context(patch.object(module, "server_command", return_value=["offline"]))
                stack.enter_context(patch.object(module, "calibrate_grounding_v1_contract", return_value=("offline", {"model_request_count": 0})))
                stack.enter_context(patch.object(module, "messages", return_value=[]))
                request = stack.enter_context(patch.object(module, "request_grounding_v1_model", return_value=response))
                module.run_screen(args)
                process.assert_called_once()
                self.assertEqual(request.call_count, 2)
                self.assertEqual(wait.call_args.args[3], 37.0)
                model.assert_called_once_with(self.args.model_inventory, "model-0", None, None)
                resolved.assert_called_once_with(self.args.runtime_record, self.args.runtime_executable)
                status = matrix.read(args.output / "run-status.json")
                self.assertEqual((status["state"], status["record_count"]), ("complete", 2))

    def test_preregistration_before_children_failure_ledger_no_retry_no_resume(self):
        calls = []
        def failed(command, log):
            protocol = matrix.read(self.args.output / "preregistration.json")
            digest = matrix.read(self.args.output / "preregistration-checksum.json")["sha256"]
            self.assertEqual(digest, matrix.file_sha(self.args.output / "preregistration.json"))
            self.assertEqual(len(protocol["cells"]), 60)
            calls.append(tuple(command))
            raise ValueError("offline child failure")
        with self.no_gold(), patch.object(matrix, "invoke", side_effect=failed):
            self.assertFalse(matrix.run_matrix(self.args))
            with self.assertRaisesRegex(ValueError, "resume forbidden"):
                matrix.run_matrix(self.args)
        self.assertEqual(len(calls), 60)
        self.assertEqual(len(set(calls)), 60)
        ledger = list((self.args.output / "ledger").glob("*.json"))
        self.assertEqual(len(ledger), 60)
        self.assertTrue(all(matrix.read(p)["status"] == "failed" and "offline child failure" in matrix.read(p)["error"] for p in ledger))
        with patch.object(matrix, "invoke") as invoke:
            self.assertFalse(matrix.score_matrix(self.args.output))
            invoke.assert_not_called()
        self.assertEqual(len(matrix.read(self.args.output / "matrix-results.json")["cells"]), 60)

    def test_score_keeps_success_failure_and_invalid_cells_explicit(self):
        def run(command, log):
            out = Path(command[command.index("--output") + 1])
            out.mkdir(parents=True)
            model_id = command[command.index("--model-id") + 1]
            matrix.write(out / "preregistration.json", dict(model=dict(id=model_id, sha256=self.spec["models"][0]["sha256"]),
                model_inventory_sha256=matrix.file_sha(self.args.model_inventory), runtime=self.runtime))
            matrix.write(out / "run-status.json", {"state": "complete"})
        with self.no_gold(), patch.object(matrix, "invoke", side_effect=run), patch.object(matrix, "verify_child_run"):
            self.assertTrue(matrix.run_matrix(self.args))
        protocol = matrix.read(self.args.output / "preregistration.json")
        cells = {c["score"]: c for c in protocol["cells"]}
        damaged = protocol["cells"][0]
        (Path(damaged["run"]) / "run-status.json").write_text("tampered")
        verified = set()
        def integrity(p, c):
            verified.add(c["id"])
        def score(command, log):
            cell = cells[command[command.index("--output") + 1]]
            self.assertIn(cell["id"], verified)
            if cell == protocol["cells"][1]:
                raise ValueError("offline score failure")
            metrics = ["label_accuracy"] if cell["benchmark_id"] == "fever" else ["exact_match", "f1"]
            summary = dict(format=f"exactscope.public-{matrix.FORMATS[cell['benchmark_id']]}-summary", format_version="0.1",
                model_id=cell["model_id"], item_count=1, arms={a: {m: 0.5 for m in metrics} for a in ("A", "G")},
                paired={m + "_uplift": 0 for m in metrics})
            Path(cell["score"]).mkdir()
            matrix.write(Path(cell["score"]) / "summary.json", summary)
        with patch.object(matrix, "verify_child_run", side_effect=integrity), patch.object(matrix, "invoke", side_effect=score) as invoke:
            self.assertFalse(matrix.score_matrix(self.args.output))
        self.assertEqual(invoke.call_count, 59)
        result = matrix.read(self.args.output / "matrix-results.json")
        self.assertEqual((result["cell_count"], result["scored_cells"], len(result["cells"])), (60, 58, 60))
        self.assertEqual({c["id"] for c in result["cells"]}, {c["id"] for c in protocol["cells"]})
        with (self.args.output / "matrix-results.csv").open(newline="") as handle:
            self.assertEqual(len(list(csv.DictReader(handle))), 60)
        with self.assertRaises(FileExistsError):
            matrix.score_matrix(self.args.output)

    def test_native_run_and_score_reject_incomplete_before_gold(self):
        for task, module in matrix.PANEL.items():
            with self.subTest(task=task), self.no_gold():
                args = argparse.Namespace(candidate=self.candidates[task], output=self.root / (task + "-run"),
                    model_id="model-0", model_root=None, model_path=None, runtime_executable=self.args.runtime_executable,
                    top_k=12, max_evidence_bytes=4096, port=18801, threads=2)
                resolver = "resolve_inputs" if task == "fever" else "_runtime_inputs"
                with patch.object(module, resolver, side_effect=ValueError("offline stop")):
                    with self.assertRaisesRegex(ValueError, "offline stop"):
                        module.run_screen(args)
                with self.assertRaises((OSError, RuntimeError, ValueError)):
                    module.score_run(args.candidate, args.output, self.root / (task + "-score"))

    def test_hotpot_pair_integrity_before_gold(self):
        module = matrix.hotpot
        questions = [{"item_id": "q"}]
        valid = [{"item_id": "q", "arm": a} for a in ("A", "G")]
        module.verify_record_keys(questions, valid)
        for records in (valid[:1], [valid[0], valid[0]], [valid[0], {"item_id": "other", "arm": "G"}]):
            with self.subTest(records=records), self.no_gold(), patch.object(module, "_verify_run", return_value=({}, records)):
                with self.assertRaisesRegex(RuntimeError, "A/G record identity"):
                    module.score_run(self.candidates["hotpotqa"], self.root / "run", self.root / "score")
                protocol = {"candidates": {"hotpotqa": {"path": str(self.candidates["hotpotqa"])}}}
                with self.assertRaisesRegex(RuntimeError, "A/G record identity"):
                    matrix.verify_child_run(protocol, {"benchmark_id": "hotpotqa", "run": str(self.root / "run")})

    def test_cli_defaults_and_custom_inventory_runtime_routing(self):
        for task, module in matrix.PANEL.items():
            for custom in (False, True):
                with self.subTest(task=task, custom=custom):
                    argv = ["run", "--candidate", str(self.candidates[task]), "--model-id", "model-0",
                            "--runtime-executable", str(self.args.runtime_executable), "--output", str(self.root / "cli")]
                    if custom:
                        argv += ["--model-inventory", str(self.args.model_inventory)]
                    if custom or task != "hotpotqa":
                        argv += ["--runtime-record", str(self.args.runtime_record)]
                    captured = []
                    def stop(args):
                        captured.append(args)
                        raise ValueError("offline stop")
                    with patch.object(module, "run_screen", side_effect=stop), redirect_stdout(io.StringIO()):
                        self.assertEqual(module.main(argv), 1)
                    args = captured[0]
                    expected_inventory = self.args.model_inventory if custom else matrix.ROOT / "benchmarks/grounding-model-inventory.json"
                    expected_runtime = self.args.runtime_record if custom or task != "hotpotqa" else matrix.ROOT / "benchmarks/grounding-runtime-llama-v040.json"
                    self.assertEqual(args.model_inventory, expected_inventory)
                    self.assertEqual(args.runtime_record, expected_runtime)
                    self.assertEqual((args.threads, args.top_k, args.max_evidence_bytes), (6, 12, 4096))
                    self.assertEqual(args.port, {"natural_questions": 18801, "hotpotqa": 18201, "fever": 18601}[task])
                    with patch.object(module, "resolve_model", return_value=("inventory", {})) as model, patch.object(module, "resolve_runtime", return_value=("runtime", {"launch": {}})) as runtime:
                        if task == "hotpotqa":
                            module._runtime_inputs(args.model_id, args.model_root, args.model_path, args.runtime_executable,
                                args.port, args.threads, args.model_inventory, args.runtime_record)
                        else:
                            (module.resolve_inputs if task == "fever" else module._runtime_inputs)(args)
                        self.assertEqual(model.call_args.args[0], expected_inventory)
                        self.assertEqual(runtime.call_args.args, (expected_runtime, args.runtime_executable))


if __name__ == "__main__":
    unittest.main()
