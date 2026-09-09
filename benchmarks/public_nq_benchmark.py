#!/usr/bin/env python3
"""Run and score the gold-isolated NQ mirror search split for ExactScope."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "tools", ROOT / "benchmarks"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from grounding_canonical import canonical_bytes, loads
from grounding_corpus import ValidatedIndex, index_sha256, load_index, search
from grounding_projection import compact_evidence_projection
from grounding_preregister import file_sha, load_json, resolve_model, resolve_runtime
from grounding_v1_surface import messages, parse_answer_object, surface_sha256
from public_nq_candidate import score_normalize
from run_grounding_benchmark import (
    BenchmarkRunError,
    calibrate_grounding_v1_contract,
    request_grounding_v1_model,
    server_command,
    stop_server,
    wait_server,
    write_sums,
)

POLICY_PATH = ROOT / "grounding/reference-profile-v0.1/projection-policy.txt"
DEFAULT_TOP_K = 12
DEFAULT_MAX_EVIDENCE_BYTES = 4096
SOURCE_FILES = (
    "benchmarks/public_nq_benchmark.py",
    "benchmarks/public_nq_candidate.py",
    "benchmarks/run_grounding_benchmark.py",
    "tools/grounding_corpus.py",
    "tools/grounding_projection.py",
    "tools/grounding_v1_surface.py",
)


class NQBenchmarkError(RuntimeError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_hashes() -> dict[str, str]:
    return {name: file_sha(ROOT / name) for name in SOURCE_FILES}


def _load_cjson(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = loads(raw)
    if not isinstance(value, dict) or raw != canonical_bytes(value):
        raise NQBenchmarkError(f"expected canonical JSON object: {path}")
    return value


def _load_cjsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_bytes().splitlines():
        value = loads(line)
        if not isinstance(value, dict) or line != canonical_bytes(value):
            raise NQBenchmarkError(f"expected canonical JSONL object row: {path}")
        rows.append(value)
    return rows


def verify_serving_candidate(
    candidate: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], ValidatedIndex]:
    serving = candidate / "serving"
    manifest_path = serving / "manifest.json"
    manifest = _load_cjson(manifest_path)
    if manifest.get("format") != "exactscope.public-nq-serving-candidate" or manifest.get("format_version") != "0.1":
        raise NQBenchmarkError("NQ serving candidate identity drift")
    if (
        manifest.get("split") != "search"
        or manifest.get("qualification_eligible") is not False
        or manifest.get("oracle_assisted_corpus") is not True
        or manifest.get("mode") != "oracle-page-pooled-corpus-development-v1"
    ):
        raise NQBenchmarkError("NQ development-mode disclosure drift")
    questions_path = serving / "questions.jsonl"
    chunks_path = serving / "chunks.jsonl"
    index_path = serving / "corpus-index.json"
    questions = _load_cjsonl(questions_path)
    chunks = _load_cjsonl(chunks_path)
    if len(questions) != manifest.get("search_item_count") or len({row.get("eval_id") for row in questions}) != len(questions):
        raise NQBenchmarkError("NQ serving question identity drift")
    if any(set(row) != {"eval_id", "question"} for row in questions):
        raise NQBenchmarkError("NQ serving questions contain forbidden fields")
    if len(chunks) != manifest.get("chunk_count") or len({row.get("chunk_id") for row in chunks}) != len(chunks):
        raise NQBenchmarkError("NQ chunk identity drift")
    allowed_chunk_fields = {"chunk_id", "doc_id", "title", "text", "body_token_start", "body_token_end"}
    if any(set(row) != allowed_chunk_fields for row in chunks):
        raise NQBenchmarkError("NQ serving chunk contains forbidden fields")
    if len({row["doc_id"] for row in chunks}) != manifest.get("document_count"):
        raise NQBenchmarkError("NQ pooled document count drift")
    if file_sha(questions_path) != manifest.get("questions_sha256") or file_sha(chunks_path) != manifest.get("chunks_sha256"):
        raise NQBenchmarkError("NQ serving file hash drift")
    corpus = load_index(index_path, compiled=True)
    if not isinstance(corpus, ValidatedIndex):
        raise NQBenchmarkError("NQ corpus did not compile")
    if index_sha256(corpus) != manifest.get("corpus_index_sha256"):
        raise NQBenchmarkError("NQ corpus index hash drift")
    if corpus.document_count != len(chunks):
        raise NQBenchmarkError("NQ corpus/chunk count drift")
    if {doc["id"] for doc in corpus["documents"]} != {row["chunk_id"] for row in chunks}:
        raise NQBenchmarkError("NQ corpus/chunk identity drift")
    return manifest, questions, chunks, corpus


def _runtime_inputs(args: argparse.Namespace):
    inventory_sha, model = resolve_model(
        getattr(args, "model_inventory", ROOT / "benchmarks/grounding-model-inventory.json"),
        args.model_id,
        args.model_root,
        args.model_path,
    )
    runtime_sha, runtime = resolve_runtime(args.runtime_record, args.runtime_executable)
    runtime = json.loads(json.dumps(runtime))
    runtime["launch"]["port"] = args.port
    runtime["launch"]["threads"] = args.threads
    generation = load_json(ROOT / "benchmarks/grounding-generation-config.json")
    return inventory_sha, model, runtime_sha, runtime, generation


def run_screen(args: argparse.Namespace) -> None:
    if args.output.exists():
        raise NQBenchmarkError("run output exists; resume/reuse forbidden")
    if type(args.top_k) is not int or not 1 <= args.top_k <= 16:
        raise NQBenchmarkError("top_k must be between 1 and 16")
    if type(args.max_evidence_bytes) is not int or not 256 <= args.max_evidence_bytes <= 4096:
        raise NQBenchmarkError("max_evidence_bytes must be between 256 and 4096")
    candidate = args.candidate.resolve()
    manifest, questions, chunks, corpus = verify_serving_candidate(candidate)
    chunk_ids = {row["chunk_id"] for row in chunks}
    inventory_sha, model, runtime_sha, runtime, generation = _runtime_inputs(args)
    policy = POLICY_PATH.read_bytes()
    prereg = {
        "format": "exactscope.public-nq-preregistration",
        "format_version": "0.1",
        "qualification_eligible": False,
        "candidate": {
            "serving_manifest_sha256": file_sha(candidate / "serving/manifest.json"),
            "questions_sha256": manifest["questions_sha256"],
            "chunks_sha256": manifest["chunks_sha256"],
            "corpus_index_sha256": manifest["corpus_index_sha256"],
            "item_count": manifest["search_item_count"],
            "mode": manifest["mode"],
            "source_sha256": manifest["source"]["sha256"],
        },
        "source_files": _source_hashes(),
        "model_inventory_sha256": inventory_sha,
        "model": model,
        "runtime_record_sha256": runtime_sha,
        "runtime": runtime,
        "generation_config_sha256": file_sha(ROOT / "benchmarks/grounding-generation-config.json"),
        "model_surface_sha256": surface_sha256(),
        "policy_sha256": _sha(policy),
        "top_k": args.top_k,
        "max_evidence_bytes": args.max_evidence_bytes,
        "arms": ["A", "G"],
        "retry_count": 0,
        "hidden_repair": False,
        "gold_visible_to_runner": False,
        "confirmation_visible_to_runner": False,
        "compiled_corpus_hot_path": True,
    }
    args.output.mkdir(parents=True)
    (args.output / "preregistration.json").write_bytes(canonical_bytes(prereg))
    status_path = args.output / "run-status.json"
    status = {
        "format": "exactscope.public-nq-run",
        "format_version": "0.1",
        "state": "running",
        "item_count": len(questions),
        "record_count": 0,
        "model_id": model["id"],
        "preregistration_sha256": file_sha(args.output / "preregistration.json"),
    }
    status_path.write_bytes(canonical_bytes(status))
    raw_path = args.output / "raw-results.jsonl"
    log_path = args.output / "llama-server.log"
    command = server_command(prereg)
    runtime_dir = str(Path(runtime["executable_path"]).resolve().parent)
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = runtime_dir + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    process: subprocess.Popen[bytes] | None = None
    records: list[dict[str, Any]] = []
    try:
        with log_path.open("wb") as server_log:
            process = subprocess.Popen(command, cwd=runtime_dir, stdout=server_log, stderr=subprocess.STDOUT, env=env)
            runtime_record = load_json(args.runtime_record)
            wait_server(
                process,
                runtime["launch"]["host"],
                int(runtime["launch"]["port"]),
                float(runtime_record["server_ready_timeout_seconds"]),
            )
            selected, calibration = calibrate_grounding_v1_contract(prereg, generation, policy)
            (args.output / "contract-calibration.json").write_bytes(canonical_bytes(calibration))
            with raw_path.open("wb") as raw:
                for item in questions:
                    eval_id = item["eval_id"]
                    question = item["question"]
                    a = request_grounding_v1_model(prereg, generation, messages(selected, question), selected)
                    a_record = {
                        "eval_id": eval_id,
                        "arm": "A",
                        "model_contract": selected,
                        "model_contract_valid": a["model_contract_valid"],
                        "model_contract_output": a["model_contract_output"],
                        "raw_content": a["raw_content"],
                        "input_tokens": a["input_tokens"],
                        "output_tokens": a["output_tokens"],
                        "model_latency_us": a["model_latency_us"],
                        "retrieved_chunk_ids": [],
                        "projected_chunks": [],
                        "evidence_bytes": 0,
                    }
                    raw.write(canonical_bytes(a_record) + b"\n")
                    records.append(a_record)

                    retrieved = search(corpus, question, top_k=args.top_k)
                    projection, emitted = compact_evidence_projection(
                        corpus,
                        retrieved,
                        question,
                        max_bytes=args.max_evidence_bytes,
                    )
                    projected_chunks = [
                        {"id": hit["id"], "snippet": hit["snippet"]}
                        for hit in emitted
                    ]
                    if any(row["id"] not in chunk_ids for row in projected_chunks):
                        raise NQBenchmarkError("NQ projection emitted unknown chunk")
                    g_messages = messages(selected, question, evidence=projection, policy=policy) if projection else messages(selected, question)
                    g = request_grounding_v1_model(prereg, generation, g_messages, selected)
                    g_record = {
                        "eval_id": eval_id,
                        "arm": "G",
                        "model_contract": selected,
                        "model_contract_valid": g["model_contract_valid"],
                        "model_contract_output": g["model_contract_output"],
                        "raw_content": g["raw_content"],
                        "input_tokens": g["input_tokens"],
                        "output_tokens": g["output_tokens"],
                        "model_latency_us": g["model_latency_us"],
                        "retrieved_chunk_ids": [hit["id"] for hit in retrieved],
                        "projected_chunks": projected_chunks,
                        "evidence_bytes": len(projection) if projection else 0,
                    }
                    raw.write(canonical_bytes(g_record) + b"\n")
                    records.append(g_record)
        stop_server(process)
        process = None
        if _source_hashes() != prereg["source_files"]:
            raise NQBenchmarkError("NQ benchmark source hash drift during run")
        verify_serving_candidate(candidate)
        status.update({
            "state": "complete",
            "record_count": len(records),
            "selected_model_contract": selected,
            "calibration_model_requests": calibration["model_request_count"],
            "answer_model_requests": len(records),
            "total_model_requests_including_calibration": len(records) + calibration["model_request_count"],
            "model_surface_sha256": prereg["model_surface_sha256"],
        })
        status_path.write_bytes(canonical_bytes(status))
        write_sums(args.output)
    except Exception:
        stop_server(process)
        if args.output.exists():
            status["state"] = "invalid"
            status["record_count"] = len(records)
            status_path.write_bytes(canonical_bytes(status))
            write_sums(args.output)
        raise


def _verify_run(
    candidate: Path,
    manifest: dict[str, Any],
    questions: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    run: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    status = _load_cjson(run / "run-status.json")
    if status.get("state") != "complete" or status.get("record_count") != len(questions) * 2:
        raise NQBenchmarkError("NQ run is incomplete")
    sums: dict[str, str] = {}
    for line in (run / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        if "  " not in line:
            raise NQBenchmarkError("invalid NQ SHA256SUMS line")
        digest, relative = line.split("  ", 1)
        path = Path(relative)
        if relative in sums or path.is_absolute() or ".." in path.parts:
            raise NQBenchmarkError("unsafe/duplicate NQ SHA256SUMS path")
        sums[relative] = digest
    actual = {p.relative_to(run).as_posix() for p in run.rglob("*") if p.is_file() and p.name != "SHA256SUMS"}
    if set(sums) != actual or any(file_sha(run / relative) != digest for relative, digest in sums.items()):
        raise NQBenchmarkError("NQ run checksum mismatch")

    prereg_path = run / "preregistration.json"
    prereg = _load_cjson(prereg_path)
    expected_candidate = {
        "serving_manifest_sha256": file_sha(candidate / "serving/manifest.json"),
        "questions_sha256": manifest["questions_sha256"],
        "chunks_sha256": manifest["chunks_sha256"],
        "corpus_index_sha256": manifest["corpus_index_sha256"],
        "item_count": manifest["search_item_count"],
        "mode": manifest["mode"],
        "source_sha256": manifest["source"]["sha256"],
    }
    if prereg.get("format") != "exactscope.public-nq-preregistration" or prereg.get("format_version") != "0.1":
        raise NQBenchmarkError("NQ preregistration identity drift")
    if prereg.get("candidate") != expected_candidate or prereg.get("source_files") != _source_hashes():
        raise NQBenchmarkError("NQ run source/candidate identity drift")
    if prereg.get("model_surface_sha256") != surface_sha256() or status.get("model_surface_sha256") != prereg["model_surface_sha256"]:
        raise NQBenchmarkError("NQ model-surface identity drift")
    if (
        prereg.get("arms") != ["A", "G"]
        or prereg.get("retry_count") != 0
        or prereg.get("hidden_repair") is not False
        or prereg.get("gold_visible_to_runner") is not False
        or prereg.get("confirmation_visible_to_runner") is not False
        or prereg.get("compiled_corpus_hot_path") is not True
    ):
        raise NQBenchmarkError("NQ execution-policy drift")
    if status.get("preregistration_sha256") != file_sha(prereg_path):
        raise NQBenchmarkError("NQ preregistration/status identity drift")

    calibration = _load_cjson(run / "contract-calibration.json")
    selected = status.get("selected_model_contract")
    if (
        calibration.get("format") != "exactscope.grounding-v1-contract-calibration"
        or calibration.get("format_version") != "0.1"
        or calibration.get("selected_contract") != selected
        or calibration.get("model_surface_sha256") != prereg["model_surface_sha256"]
        or calibration.get("model_request_count") != status.get("calibration_model_requests")
    ):
        raise NQBenchmarkError("NQ calibration identity drift")
    records = _load_cjsonl(run / "raw-results.jsonl")
    expected_keys = {(item["eval_id"], arm) for item in questions for arm in ("A", "G")}
    actual_keys = {(row.get("eval_id"), row.get("arm")) for row in records}
    if len(records) != len(questions) * 2 or len(actual_keys) != len(records) or actual_keys != expected_keys:
        raise NQBenchmarkError("NQ A/G record identity drift")
    if status.get("answer_model_requests") != len(records) or status.get("total_model_requests_including_calibration") != len(records) + status.get("calibration_model_requests", -1):
        raise NQBenchmarkError("NQ model-request accounting drift")
    known_chunks = {row["chunk_id"] for row in chunks}
    for row in records:
        if row.get("model_contract") != selected or row.get("arm") not in {"A", "G"}:
            raise NQBenchmarkError("NQ model record contract drift")
        raw_content = row.get("raw_content")
        if not isinstance(raw_content, str):
            raise NQBenchmarkError("NQ model record lacks raw output")
        valid, value = parse_answer_object(raw_content)
        if row.get("model_contract_valid") is not valid or row.get("model_contract_output") != value:
            raise NQBenchmarkError("NQ raw/model output mismatch")
        if type(row.get("input_tokens")) is not int or row["input_tokens"] <= 0:
            raise NQBenchmarkError("NQ input-token accounting drift")
        if type(row.get("output_tokens")) is not int or row["output_tokens"] <= 0:
            raise NQBenchmarkError("NQ output-token accounting drift")
        if type(row.get("model_latency_us")) is not int or row["model_latency_us"] <= 0:
            raise NQBenchmarkError("NQ latency accounting drift")
        retrieved = row.get("retrieved_chunk_ids")
        projected = row.get("projected_chunks")
        if not isinstance(retrieved, list) or not all(isinstance(value, str) and value in known_chunks for value in retrieved):
            raise NQBenchmarkError("NQ retrieved chunk identity drift")
        if not isinstance(projected, list) or any(
            not isinstance(item, dict)
            or set(item) != {"id", "snippet"}
            or item.get("id") not in known_chunks
            or not isinstance(item.get("snippet"), str)
            for item in projected
        ):
            raise NQBenchmarkError("NQ projected chunk identity drift")
        if not {item["id"] for item in projected} <= set(retrieved):
            raise NQBenchmarkError("NQ projection is not a subset of retrieval")
        if row["arm"] == "A" and (retrieved or projected or row.get("evidence_bytes") != 0):
            raise NQBenchmarkError("NQ A arm received retrieval evidence")
    return status, records


def _f1(prediction: str | None, aliases: list[str]) -> float:
    pred_tokens = score_normalize(prediction or "").split()
    best = 0.0
    for alias in aliases:
        gold_tokens = alias.split()
        if not pred_tokens or not gold_tokens:
            best = max(best, float(pred_tokens == gold_tokens))
            continue
        common = Counter(pred_tokens) & Counter(gold_tokens)
        overlap = sum(common.values())
        if not overlap:
            continue
        precision = overlap / len(pred_tokens)
        recall = overlap / len(gold_tokens)
        best = max(best, 2 * precision * recall / (precision + recall))
    return best


def _contains_alias(text: str, aliases: list[str]) -> bool:
    normalized = score_normalize(text)
    padded = f" {normalized} "
    return any(alias and f" {alias} " in padded for alias in aliases)


def _reconstruct_documents(chunks: list[dict[str, Any]]) -> dict[str, str]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for chunk in chunks:
        grouped.setdefault(chunk["doc_id"], []).append(chunk)
    documents: dict[str, str] = {}
    for doc_id, rows in grouped.items():
        size = max(row["body_token_end"] for row in rows)
        tokens: list[str | None] = [None] * size
        for row in sorted(rows, key=lambda item: (item["body_token_start"], item["body_token_end"], item["chunk_id"])):
            body = row["text"].split()
            start = row["body_token_start"]
            end = row["body_token_end"]
            if type(start) is not int or type(end) is not int or start < 0 or end <= start or len(body) != end - start:
                raise NQBenchmarkError("NQ chunk token offsets drift")
            for offset, token in enumerate(body, start):
                if tokens[offset] is not None and tokens[offset] != token:
                    raise NQBenchmarkError("NQ overlapping chunk text drift")
                tokens[offset] = token
        if any(token is None for token in tokens):
            raise NQBenchmarkError("NQ chunk windows do not cover source document")
        documents[doc_id] = " ".join(token for token in tokens if token is not None)
    return documents


def score_run(candidate: Path, run: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise NQBenchmarkError("score output exists")
    manifest, questions, chunks, _ = verify_serving_candidate(candidate)
    status, records = _verify_run(candidate, manifest, questions, chunks, run)

    # Gold and confirmation reservation open only after serving/run identity and checksums verify.
    gold_manifest = _load_cjson(candidate / "gold/manifest.json")
    if gold_manifest.get("serving_manifest_sha256") != file_sha(candidate / "serving/manifest.json"):
        raise NQBenchmarkError("NQ gold/serving identity drift")
    gold_path = candidate / "gold/items.jsonl"
    reservation_path = candidate / "gold/confirmation-reservation.jsonl"
    gold_rows = _load_cjsonl(gold_path)
    reservation_rows = _load_cjsonl(reservation_path)
    if file_sha(gold_path) != gold_manifest.get("items_sha256") or file_sha(reservation_path) != gold_manifest.get("confirmation_reservation_sha256"):
        raise NQBenchmarkError("NQ gold/reservation hash drift")
    if gold_manifest.get("confirmation_corpus_built") is not False:
        raise NQBenchmarkError("NQ confirmation corpus was prematurely built")
    gold = {row["eval_id"]: row for row in gold_rows}
    if set(gold) != {item["eval_id"] for item in questions} or len(gold) != len(gold_rows):
        raise NQBenchmarkError("NQ gold item set drift")
    search_source_ids = {row["source_row_id"] for row in gold_rows}
    reservation_ids = {row.get("source_row_id") for row in reservation_rows}
    if search_source_ids & reservation_ids or len(reservation_ids) != gold_manifest.get("confirmation_reserved_count"):
        raise NQBenchmarkError("NQ search/confirmation reservation overlap")

    chunk_by_id = {row["chunk_id"]: row for row in chunks}
    source_documents = _reconstruct_documents(chunks)
    keyed = {(row["eval_id"], row["arm"]): row for row in records}
    arms: dict[str, Any] = {}
    scored_rows: list[dict[str, Any]] = []
    for arm in ("A", "G"):
        exact = 0
        f1_total = 0.0
        format_failures = 0
        abstentions = 0
        for item in questions:
            eval_id = item["eval_id"]
            row = keyed[(eval_id, arm)]
            aliases = gold[eval_id]["normalized_aliases"]
            prediction = row["model_contract_output"] if row["model_contract_valid"] else None
            normalized_prediction = score_normalize(prediction or "")
            em = int(normalized_prediction in aliases if normalized_prediction else False)
            f1 = _f1(prediction, aliases)
            exact += em
            f1_total += f1
            format_failures += int(not row["model_contract_valid"])
            abstentions += int(row["model_contract_valid"] and prediction is None)
            scored_rows.append({"eval_id": eval_id, "arm": arm, "exact_match": bool(em), "f1_milli": int(round(f1 * 1000))})
        n = len(questions)
        arms[arm] = {
            "exact_match": exact / n,
            "f1": f1_total / n,
            "format_failure_rate": format_failures / n,
            "abstention_rate": abstentions / n,
            "mean_input_tokens": sum(keyed[(item["eval_id"], arm)]["input_tokens"] for item in questions) / n,
        }

    source_coverage = hit1 = hit4 = hit12 = projected = source_doc_recall12 = 0
    covered_n = covered_hit12 = covered_projected = 0
    evidence_bytes = 0
    for item in questions:
        eval_id = item["eval_id"]
        g = keyed[(eval_id, "G")]
        gold_row = gold[eval_id]
        aliases = gold_row["normalized_aliases"]
        source_doc = source_documents.get(gold_row["source_doc_id"])
        if source_doc is None:
            raise NQBenchmarkError("NQ gold source document missing from pooled corpus")
        covered = _contains_alias(source_doc, aliases)
        source_coverage += int(covered)
        retrieved_ids = g["retrieved_chunk_ids"]
        flags = [_contains_alias(chunk_by_id[chunk_id]["text"], aliases) for chunk_id in retrieved_ids]
        hit1 += int(any(flags[:1]))
        hit4 += int(any(flags[:4]))
        hit12 += int(any(flags[:12]))
        source_doc_recall12 += int(any(chunk_by_id[chunk_id]["doc_id"] == gold_row["source_doc_id"] for chunk_id in retrieved_ids))
        projected_flag = any(_contains_alias(row["snippet"], aliases) for row in g["projected_chunks"])
        projected += int(projected_flag)
        evidence_bytes += g["evidence_bytes"]
        if covered:
            covered_n += 1
            covered_hit12 += int(any(flags[:12]))
            covered_projected += int(projected_flag)
    n = len(questions)
    summary = {
        "format": "exactscope.public-nq-summary",
        "format_version": "0.1",
        "candidate_mode": manifest["mode"],
        "source_label": manifest["source_label"],
        "item_count": n,
        "model_id": status["model_id"],
        "selected_model_contract": status["selected_model_contract"],
        "arms": arms,
        "paired": {
            "exact_match_uplift": arms["G"]["exact_match"] - arms["A"]["exact_match"],
            "f1_uplift": arms["G"]["f1"] - arms["A"]["f1"],
        },
        "evidence": {
            "source_document_answer_coverage": source_coverage / n,
            "answer_bearing_hit_at_1": hit1 / n,
            "answer_bearing_hit_at_4": hit4 / n,
            "answer_bearing_hit_at_12": hit12 / n,
            "answer_bearing_projection_rate": projected / n,
            "source_document_recall_at_12": source_doc_recall12 / n,
            "conditional_hit_at_12_given_source_coverage": covered_hit12 / covered_n if covered_n else None,
            "conditional_projection_given_source_coverage": covered_projected / covered_n if covered_n else None,
            "mean_g_evidence_bytes": evidence_bytes / n,
        },
        "notes": {
            "qualification_eligible": False,
            "official_nq_score": False,
            "development_mirror": True,
            "oracle_assisted_pooled_page_corpus": True,
            "flattened_short_answers_treated_as_aliases": True,
            "confirmation_reservation_locked": True,
            "gold_opened_after_run_integrity": True,
            "parallel_latency_is_not_release_latency": True,
        },
    }
    output.mkdir(parents=True)
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "scored.jsonl").write_bytes(b"".join(canonical_bytes(row) + b"\n" for row in scored_rows))
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--candidate", type=Path, required=True)
    run.add_argument("--model-id", required=True)
    run.add_argument("--model-root", type=Path)
    run.add_argument("--model-path", type=Path)
    run.add_argument("--model-inventory", type=Path, default=ROOT / "benchmarks/grounding-model-inventory.json")
    run.add_argument("--runtime-record", type=Path, required=True)
    run.add_argument("--runtime-executable", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--port", type=int, default=18801)
    run.add_argument("--threads", type=int, default=6)
    run.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    run.add_argument("--max-evidence-bytes", type=int, default=DEFAULT_MAX_EVIDENCE_BYTES)
    score = sub.add_parser("score")
    score.add_argument("--candidate", type=Path, required=True)
    score.add_argument("--run", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            run_screen(args)
            print(json.dumps(_load_cjson(args.output / "run-status.json"), indent=2, sort_keys=True))
        else:
            print(json.dumps(score_run(args.candidate, args.run, args.output), indent=2, sort_keys=True))
        return 0
    except (NQBenchmarkError, BenchmarkRunError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ExactScope public NQ benchmark: FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
