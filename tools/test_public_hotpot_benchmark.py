"""No-inference integrity tests for the public HotpotQA development screen."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "benchmarks")]

from grounding_canonical import canonical_bytes
from grounding_corpus import load_index, search
from grounding_preregister import file_sha
from grounding_v1_surface import AUTO_CONTRACT_CALIBRATION, AUTO_CONTRACT_CANDIDATES, AUTO_V2_TIE_PREFERENCE, PREFLIGHT_STOPPING_RULE, surface_sha256
from run_grounding_benchmark import write_sums

MODULE_PATH = ROOT / "benchmarks/public_hotpot_benchmark.py"
spec = importlib.util.spec_from_file_location("public_hotpot_benchmark", MODULE_PATH)
assert spec is not None and spec.loader is not None
hotpot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hotpot)


class PublicHotpotBenchmarkTests(unittest.TestCase):
    def test_public_product_contract_is_multihop_coverage_3k_cap12(self):
        self.assertEqual(hotpot.MULTIHOP_COVERAGE_PROJECTION_ID, "multihop-coverage-v1")
        self.assertEqual(hotpot.MAX_EVIDENCE_BYTES, 3072)
        self.assertEqual(hotpot.PRODUCT_MODEL_ITEM_CAP, 12)

        hits = [{"id": "doc"}]
        with patch.object(
            hotpot,
            "multihop_coverage_evidence_projection_v1",
            return_value=(b"projection", hits, {"projection_id": hotpot.MULTIHOP_COVERAGE_PROJECTION_ID}),
        ) as projector:
            emitted, projection = hotpot._trim_hits(
                {}, hits, "multi hop question", max_bytes=hotpot.MAX_EVIDENCE_BYTES
            )
        self.assertEqual((emitted, projection), (hits, b"projection"))
        projector.assert_called_once_with(
            {}, hits, "multi hop question", max_bytes=3072, max_items=12
        )

        with tempfile.TemporaryDirectory() as directory:
            args = SimpleNamespace(
                output=Path(directory) / "run",
                top_k=12,
                max_evidence_bytes=2048,
            )
            with self.assertRaisesRegex(hotpot.PublicBenchmarkError, "product cap 3072"):
                hotpot.run_screen(args)

    def rows(self):
        return [
            {
                "id": "q-a",
                "question": "Which filter does Rover Mini use?",
                "answer": "RM-F42",
                "supporting_facts": {"title": ["Rover Mini"], "sent_id": [0]},
                "context": {
                    "title": ["Rover Mini", "Unrelated A"],
                    "sentences": [["Rover Mini uses replacement filter RM-F42."], ["The sky is blue."]],
                },
            },
            {
                "id": "q-b",
                "question": "Where did Mina park?",
                "answer": "B3-04",
                "supporting_facts": {"title": ["Parking note"], "sent_id": [0]},
                "context": {
                    "title": ["Parking note", "Unrelated B"],
                    "sentences": [["Mina parked the car in B3-04."], ["Coffee is served downstairs."]],
                },
            },
            {
                "id": "q-c",
                "question": "What color is the Ara locker label?",
                "answer": "cobalt",
                "supporting_facts": {"title": ["Locker note"], "sent_id": [0]},
                "context": {
                    "title": ["Locker note", "Unrelated C"],
                    "sentences": [["The Ara locker label is cobalt."], ["The hallway is quiet."]],
                },
            },
        ]

    def build_candidate(self, root: Path, *, rows=None, limit=2):
        candidate = root / "candidate"
        manifest = hotpot.build_candidate_from_rows(
            rows or self.rows(),
            candidate,
            dataset_sha256="d" * 64,
            dataset_identity="synthetic-hotpot-test",
            limit=limit,
            seed=20260908,
        )
        return candidate, manifest

    def test_selection_depends_on_id_not_answer_or_context(self):
        original = self.rows()
        mutated = copy.deepcopy(original)
        for row in mutated:
            row["answer"] = "CHANGED-" + row["id"]
            row["context"]["sentences"][0][0] = "Changed content for " + row["id"]
        selected_a = [row["id"] for row in hotpot.select_rows(original, limit=2, seed=7)]
        selected_b = [row["id"] for row in hotpot.select_rows(mutated, limit=2, seed=7)]
        self.assertEqual(selected_a, selected_b)

    def test_candidate_physically_separates_serving_and_gold(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate, manifest = self.build_candidate(Path(directory))
            serving = hotpot._load_jsonl(candidate / "serving/questions.jsonl")
            gold = hotpot._load_jsonl(candidate / "gold/answers.jsonl")
            self.assertTrue(serving)
            self.assertTrue(gold)
            self.assertTrue(all(set(row) == {"item_id", "question"} for row in serving))
            self.assertTrue(all("answer" not in row and "supporting_titles" not in row for row in serving))
            self.assertTrue(all(set(row) == {"item_id", "answer", "supporting_titles"} for row in gold))
            self.assertFalse(manifest["gold_visible_to_runner"])
            self.assertFalse(manifest["supporting_facts_visible_to_runner"])

    def test_candidate_verification_without_gold_never_opens_gold(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate, _ = self.build_candidate(Path(directory))
            original_open = Path.open

            def guarded(path, *args, **kwargs):
                self.assertNotIn("gold", path.parts)
                return original_open(path, *args, **kwargs)

            with patch.object(Path, "open", guarded):
                manifest, questions, corpus = hotpot.verify_candidate(candidate, include_gold=False)
            self.assertEqual(manifest["item_count"], len(questions))
            self.assertEqual(manifest["corpus_index_sha256"], hotpot.index_sha256(corpus))

    def test_pooled_corpus_retrieves_supporting_document(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate, _ = self.build_candidate(Path(directory), limit=3)
            corpus = load_index(candidate / "serving/corpus-index.json")
            hits = search(corpus, "Which filter does Rover Mini use?", top_k=2)
            self.assertTrue(hits)
            self.assertEqual(hits[0]["title"], "Rover Mini")
            self.assertIn("RM-F42", hits[0]["text"])

    def test_serving_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate, _ = self.build_candidate(Path(directory))
            path = candidate / "serving/questions.jsonl"
            rows = hotpot._load_jsonl(path)
            rows[0]["answer"] = "illegal leak"
            path.write_bytes(hotpot._jsonl_bytes(rows))
            with self.assertRaisesRegex(hotpot.PublicBenchmarkError, "forbidden fields|hash drift"):
                hotpot.verify_candidate(candidate, include_gold=False)

    def test_run_verification_recomputes_raw_model_output_before_gold(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate, manifest = self.build_candidate(root, limit=2)
            run = root / "run"
            run.mkdir()
            selected = "answer-object-v3"
            selected_surface = "json-schema-v1"
            prereg = {
                "format": "exactscope.public-hotpot-preregistration",
                "format_version": "0.1",
                "qualification_eligible": False,
                "candidate": {
                    "manifest_sha256": file_sha(candidate / "manifest.json"),
                    "questions_sha256": manifest["questions_sha256"],
                    "corpus_index_sha256": manifest["corpus_index_sha256"],
                    "item_count": manifest["item_count"],
                    "mode": manifest["mode"],
                },
                "source_files": hotpot._source_hashes(),
                "model_inventory_sha256": "i" * 64,
                "model": {"id": "synthetic"},
                "runtime_record_sha256": "r" * 64,
                "runtime": {"launch": {}},
                "generation_config_sha256": "g" * 64,
                "model_surface_sha256": surface_sha256(),
                "policy_sha256": "p" * 64,
                "top_k": 4,
                "max_evidence_bytes": hotpot.MAX_EVIDENCE_BYTES,
                "model_item_cap": hotpot.PRODUCT_MODEL_ITEM_CAP,
                "evidence_composition": "multi-source-coverage",
                "evidence_policy": hotpot.MULTIHOP_COVERAGE_PROJECTION_ID,
                "retrieval_query_policy": "question-only-v1.1",
                "projection_id": hotpot.MULTIHOP_COVERAGE_PROJECTION_ID,
                "arms": ["A", "G"],
                "retry_count": 0,
                "hidden_repair": False,
                "gold_visible_to_runner": False,
            }
            (run / "preregistration.json").write_bytes(canonical_bytes(prereg))
            cases = [
                {"case_id": case_id, "expected": expected, "actual": expected, "valid": True, "correct": True}
                for case_id, _question, _evidence, expected in AUTO_CONTRACT_CALIBRATION
            ]
            profiles = [{"contract": selected, "score": len(cases), "case_count": len(cases), "cases": cases}]
            calibration = {
                "format": "exactscope.grounding-v1-contract-calibration",
                "format_version": "0.2",
                "model_surface_sha256": surface_sha256(),
                "selected_contract": selected,
                "selected_output_surface": selected_surface,
                "tie_preference": list(AUTO_V2_TIE_PREFERENCE),
                "stopping_rule": PREFLIGHT_STOPPING_RULE,
                "model_request_count": len(cases),
                "profiles": profiles,
            }
            negotiation = {
                "format": "exactscope.grounding-v1.1-surface-negotiation",
                "format_version": "0.2",
                "fingerprint": hotpot.model_runtime_fingerprint(prereg),
                "model_surface_sha256": surface_sha256(),
                "candidate_surfaces": list(hotpot.OUTPUT_SURFACE_CANDIDATES),
                "selected_surface": selected_surface,
                "supported": True,
                "model_request_count": 1,
                "retry_count": 0,
                "stopping_rule": PREFLIGHT_STOPPING_RULE,
                "probes": [{
                    "surface": selected_surface,
                    "case_id": "surface-probe",
                    "protocol_valid": True,
                    "semantic_match": True,
                    "actual": "ZX-41",
                    "error": None,
                }],
            }
            (run / "surface-negotiation.json").write_bytes(canonical_bytes(negotiation))
            (run / "contract-calibration.json").write_bytes(canonical_bytes(calibration))
            questions = hotpot._load_jsonl(candidate / "serving/questions.jsonl")
            records = []
            for question in questions:
                for arm in ("A", "G"):
                    records.append({
                        "item_id": question["item_id"],
                        "arm": arm,
                        "model_contract": selected,
                        "model_output_surface": selected_surface,
                        "model_contract_valid": True,
                        "model_contract_output": "synthetic",
                        "raw_content": '{"a":"synthetic"}',
                        "input_tokens": 10,
                        "output_tokens": 2,
                        "model_latency_us": 100,
                        "retrieved_document_ids": [] if arm == "A" else ["doc"],
                        "retrieved_titles": [] if arm == "A" else ["title"],
                        "evidence_bytes": 0 if arm == "A" else 12,
                    })
            (run / "raw-results.jsonl").write_bytes(hotpot._jsonl_bytes(records))
            status = {
                "format": hotpot.RUN_FORMAT,
                "format_version": hotpot.RUN_VERSION,
                "state": "complete",
                "item_count": len(questions),
                "record_count": len(records),
                "model_id": "synthetic",
                "preregistration_sha256": file_sha(run / "preregistration.json"),
                "selected_model_contract": selected,
                "selected_output_surface": selected_surface,
                "model_runtime_fingerprint": hotpot.model_runtime_fingerprint(prereg),
                "surface_probe_requests": 1,
                "surface_probe_request_attempts": 1,
                "calibration_model_requests": len(AUTO_CONTRACT_CALIBRATION),
                "calibration_model_request_attempts": len(AUTO_CONTRACT_CALIBRATION),
                "answer_model_requests": len(records),
                "answer_model_request_attempts": len(records),
                "total_model_requests_including_calibration": len(records) + 1 + len(AUTO_CONTRACT_CALIBRATION),
                "model_surface_sha256": surface_sha256(),
            }
            (run / "run-status.json").write_bytes(canonical_bytes(status))
            write_sums(run)
            verified_status, verified = hotpot._verify_run(
                run,
                manifest,
                len(questions),
                manifest_sha256=file_sha(candidate / "manifest.json"),
            )
            self.assertEqual(verified_status["state"], "complete")
            self.assertEqual(len(verified), len(records))

            status["surface_probe_request_attempts"] = 2
            (run / "run-status.json").write_bytes(canonical_bytes(status))
            write_sums(run)
            with self.assertRaisesRegex(hotpot.PublicBenchmarkError, "request/attempt accounting"):
                hotpot._verify_run(
                    run,
                    manifest,
                    len(questions),
                    manifest_sha256=file_sha(candidate / "manifest.json"),
                )
            status["surface_probe_request_attempts"] = 1
            (run / "run-status.json").write_bytes(canonical_bytes(status))
            write_sums(run)

            records[0]["raw_content"] = '{"a":"tampered"}'
            (run / "raw-results.jsonl").write_bytes(hotpot._jsonl_bytes(records))
            write_sums(run)
            with self.assertRaisesRegex(hotpot.PublicBenchmarkError, "raw/model output"):
                hotpot._verify_run(
                    run,
                    manifest,
                    len(questions),
                    manifest_sha256=file_sha(candidate / "manifest.json"),
                )


if __name__ == "__main__":
    unittest.main()
