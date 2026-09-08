#!/usr/bin/env python3
"""Prepare, run and score a gold-isolated HotpotQA ExactScope development screen."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import string
import subprocess
import sys
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "tools", ROOT / "benchmarks"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from grounding_canonical import canonical_bytes, loads
from grounding_corpus import build_index, index_sha256, load_index, search
from grounding_projection import compact_evidence_projection
from grounding_preregister import file_sha, load_json, resolve_model, resolve_runtime
from grounding_v1_surface import messages, parse_answer_object, surface_sha256
from run_grounding_benchmark import (
    BenchmarkRunError,
    calibrate_grounding_v1_contract,
    request_grounding_v1_model,
    server_command,
    stop_server,
    wait_server,
    write_sums,
)

FORMAT = "exactscope.public-hotpot-candidate"
FORMAT_VERSION = "0.1"
RUN_FORMAT = "exactscope.public-hotpot-run"
RUN_VERSION = "0.1"
MODE = "pooled-distractor-corpus-v1"
POLICY_PATH = ROOT / "grounding/reference-profile-v0.1/projection-policy.txt"
MAX_EVIDENCE_BYTES = 4096
SOURCE_FILES = (
    "benchmarks/public_hotpot_benchmark.py",
    "benchmarks/run_grounding_benchmark.py",
    "tools/grounding_corpus.py",
    "tools/grounding_projection.py",
    "tools/grounding_v1_surface.py",
)


class PublicBenchmarkError(RuntimeError):
    pass


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(canonical_bytes(row) + b"\n" for row in rows)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    data = _jsonl_bytes(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return _sha256_bytes(data)


def _source_hashes() -> dict[str, str]:
    return {name: file_sha(ROOT / name) for name in SOURCE_FILES}


def _dataset_sha(path: Path) -> str:
    return file_sha(path)


def _selection_key(seed: int, item_id: str) -> bytes:
    return hashlib.sha256(f"{seed}:{item_id}".encode("utf-8")).digest()


def select_rows(rows: list[dict[str, Any]], *, limit: int, seed: int) -> list[dict[str, Any]]:
    if type(limit) is not int or limit < 1 or limit > len(rows):
        raise PublicBenchmarkError("invalid Hotpot subset limit")
    ids = [row.get("id") for row in rows]
    if any(not isinstance(item_id, str) or not item_id for item_id in ids) or len(set(ids)) != len(ids):
        raise PublicBenchmarkError("Hotpot rows require unique string ids")
    return sorted(rows, key=lambda row: (_selection_key(seed, row["id"]), row["id"].encode("utf-8")))[:limit]


def _context_pairs(row: dict[str, Any]) -> list[tuple[str, list[str]]]:
    context = row.get("context")
    if isinstance(context, dict):
        titles = context.get("title")
        sentences = context.get("sentences")
        if isinstance(titles, list) and isinstance(sentences, list) and len(titles) == len(sentences):
            pairs = []
            for title, sentence_list in zip(titles, sentences):
                if not isinstance(title, str) or not isinstance(sentence_list, list) or not all(isinstance(s, str) for s in sentence_list):
                    raise PublicBenchmarkError("invalid Hotpot context row")
                pairs.append((title, sentence_list))
            return pairs
    if isinstance(context, list):
        pairs = []
        for entry in context:
            if not isinstance(entry, (list, tuple)) or len(entry) != 2:
                raise PublicBenchmarkError("invalid Hotpot context row")
            title, sentence_list = entry
            if not isinstance(title, str) or not isinstance(sentence_list, list) or not all(isinstance(s, str) for s in sentence_list):
                raise PublicBenchmarkError("invalid Hotpot context row")
            pairs.append((title, sentence_list))
        return pairs
    raise PublicBenchmarkError("Hotpot row lacks context")


def _supporting_titles(row: dict[str, Any]) -> list[str]:
    supporting = row.get("supporting_facts")
    if isinstance(supporting, dict):
        titles = supporting.get("title")
        if not isinstance(titles, list) or not all(isinstance(title, str) for title in titles):
            raise PublicBenchmarkError("invalid Hotpot supporting facts")
        return sorted(set(titles), key=lambda value: value.encode("utf-8"))
    if isinstance(supporting, list):
        titles = []
        for entry in supporting:
            if not isinstance(entry, (list, tuple)) or len(entry) != 2 or not isinstance(entry[0], str):
                raise PublicBenchmarkError("invalid Hotpot supporting facts")
            titles.append(entry[0])
        return sorted(set(titles), key=lambda value: value.encode("utf-8"))
    raise PublicBenchmarkError("Hotpot row lacks supporting facts")


def build_candidate_from_rows(
    rows: list[dict[str, Any]],
    output: Path,
    *,
    dataset_sha256: str,
    dataset_identity: str,
    limit: int,
    seed: int,
) -> dict[str, Any]:
    if output.exists():
        raise PublicBenchmarkError("candidate output exists")
    selected = select_rows(rows, limit=limit, seed=seed)
    output.mkdir(parents=True)
    (output / "serving").mkdir()
    (output / "gold").mkdir()

    serving_rows: list[dict[str, Any]] = []
    gold_rows: list[dict[str, Any]] = []
    documents_by_id: dict[str, dict[str, str]] = {}
    for row in selected:
        item_id = row["id"]
        question = row.get("question")
        answer = row.get("answer")
        if not isinstance(question, str) or not question.strip() or not isinstance(answer, str) or not answer.strip():
            raise PublicBenchmarkError("Hotpot row lacks question/answer")
        serving_rows.append({"item_id": item_id, "question": question})
        gold_rows.append({
            "item_id": item_id,
            "answer": answer,
            "supporting_titles": _supporting_titles(row),
        })
        for title, sentences in _context_pairs(row):
            text = "".join(sentences).strip()
            if not text:
                continue
            identity = hashlib.sha256((title + "\n" + text).encode("utf-8")).hexdigest()[:24]
            doc_id = "hotpot-" + identity
            candidate = {"id": doc_id, "title": title, "text": text}
            previous = documents_by_id.setdefault(doc_id, candidate)
            if previous != candidate:
                raise PublicBenchmarkError("Hotpot document identity collision")

    serving_rows.sort(key=lambda row: row["item_id"].encode("utf-8"))
    gold_rows.sort(key=lambda row: row["item_id"].encode("utf-8"))
    corpus = build_index(
        documents_by_id.values(),
        source={
            "kind": "hotpotqa-pooled-distractor-context",
            "dataset_identity": dataset_identity,
            "dataset_sha256": dataset_sha256,
            "selection_seed": seed,
            "selection_limit": limit,
        },
    )
    corpus_path = output / "serving/corpus-index.json"
    corpus_path.write_bytes(canonical_bytes(corpus))
    questions_sha = _write_jsonl(output / "serving/questions.jsonl", serving_rows)
    gold_sha = _write_jsonl(output / "gold/answers.jsonl", gold_rows)
    manifest = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "mode": MODE,
        "dataset_identity": dataset_identity,
        "dataset_sha256": dataset_sha256,
        "selection": {"method": "sha256-seed-id-smallest-v1", "seed": seed, "limit": limit},
        "item_count": len(serving_rows),
        "corpus_document_count": corpus["document_count"],
        "corpus_index_sha256": index_sha256(corpus),
        "questions_sha256": questions_sha,
        "gold_sha256": gold_sha,
        "gold_visible_to_runner": False,
        "supporting_facts_visible_to_runner": False,
    }
    (output / "manifest.json").write_bytes(canonical_bytes(manifest))
    verify_candidate(output, include_gold=True)
    return manifest


def read_hotpot_parquet(path: Path) -> list[dict[str, Any]]:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise PublicBenchmarkError("Parquet preparation requires benchmark-only pyarrow") from exc
    return pq.read_table(path).to_pylist()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    try:
        for line in path.read_bytes().splitlines():
            value = loads(line)
            if not isinstance(value, dict):
                raise PublicBenchmarkError("JSONL row is not an object")
            rows.append(value)
    except (OSError, ValueError, UnicodeError) as exc:
        raise PublicBenchmarkError(f"cannot read canonical JSONL: {path}") from exc
    return rows


def verify_candidate(candidate: Path, *, include_gold: bool) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    manifest_path = candidate / "manifest.json"
    try:
        manifest_raw = manifest_path.read_bytes()
        manifest = loads(manifest_raw)
    except (OSError, ValueError, UnicodeError) as exc:
        raise PublicBenchmarkError("cannot read Hotpot candidate manifest") from exc
    if not isinstance(manifest, dict) or manifest_raw != canonical_bytes(manifest):
        raise PublicBenchmarkError("Hotpot candidate manifest is not canonical")
    if manifest.get("format") != FORMAT or manifest.get("format_version") != FORMAT_VERSION or manifest.get("mode") != MODE:
        raise PublicBenchmarkError("Hotpot candidate identity drift")
    questions_path = candidate / "serving/questions.jsonl"
    corpus_path = candidate / "serving/corpus-index.json"
    questions = _load_jsonl(questions_path)
    if len(questions) != manifest.get("item_count") or len({row.get("item_id") for row in questions}) != len(questions):
        raise PublicBenchmarkError("Hotpot serving item set drift")
    if any(set(row) != {"item_id", "question"} for row in questions):
        raise PublicBenchmarkError("Hotpot serving questions contain forbidden fields")
    if file_sha(questions_path) != manifest.get("questions_sha256"):
        raise PublicBenchmarkError("Hotpot question hash drift")
    corpus = load_index(corpus_path)
    if index_sha256(corpus) != manifest.get("corpus_index_sha256") or corpus["document_count"] != manifest.get("corpus_document_count"):
        raise PublicBenchmarkError("Hotpot corpus identity drift")
    if include_gold:
        gold_path = candidate / "gold/answers.jsonl"
        gold = _load_jsonl(gold_path)
        if file_sha(gold_path) != manifest.get("gold_sha256") or {row["item_id"] for row in gold} != {row["item_id"] for row in questions}:
            raise PublicBenchmarkError("Hotpot gold identity drift")
    return manifest, questions, corpus


def _runtime_inputs(model_id: str, model_root: Path | None, model_path: Path | None, runtime_executable: Path, port: int, threads: int):
    inventory_sha, model = resolve_model(ROOT / "benchmarks/grounding-model-inventory.json", model_id, model_root, model_path)
    runtime_sha, runtime = resolve_runtime(ROOT / "benchmarks/grounding-runtime-llama-v040.json", runtime_executable)
    runtime = json.loads(json.dumps(runtime))
    runtime["launch"]["port"] = port
    runtime["launch"]["threads"] = threads
    generation = load_json(ROOT / "benchmarks/grounding-generation-config.json")
    return inventory_sha, model, runtime_sha, runtime, generation


def _trim_hits(
    corpus: dict[str, Any],
    hits: list[dict[str, Any]],
    question: str,
    *,
    max_bytes: int,
) -> tuple[list[dict[str, Any]], bytes | None]:
    projection, emitted = compact_evidence_projection(
        corpus,
        hits,
        question,
        max_bytes=max_bytes,
    )
    return emitted, projection


def run_screen(args: argparse.Namespace) -> None:
    if args.output.exists():
        raise PublicBenchmarkError("run output exists; resume/reuse forbidden")
    if type(args.top_k) is not int or not 1 <= args.top_k <= 16:
        raise PublicBenchmarkError("top_k must be between 1 and 16")
    if type(args.max_evidence_bytes) is not int or not 256 <= args.max_evidence_bytes <= 4096:
        raise PublicBenchmarkError("max_evidence_bytes must be between 256 and 4096")
    candidate = args.candidate.resolve()
    manifest, questions, corpus = verify_candidate(candidate, include_gold=False)
    inventory_sha, model, runtime_sha, runtime, generation = _runtime_inputs(
        args.model_id, args.model_root, args.model_path, args.runtime_executable, args.port, args.threads
    )
    policy = POLICY_PATH.read_bytes()
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
        "source_files": _source_hashes(),
        "model_inventory_sha256": inventory_sha,
        "model": model,
        "runtime_record_sha256": runtime_sha,
        "runtime": runtime,
        "generation_config_sha256": file_sha(ROOT / "benchmarks/grounding-generation-config.json"),
        "model_surface_sha256": surface_sha256(),
        "policy_sha256": _sha256_bytes(policy),
        "top_k": args.top_k,
        "max_evidence_bytes": args.max_evidence_bytes,
        "arms": ["A", "G"],
        "retry_count": 0,
        "hidden_repair": False,
        "gold_visible_to_runner": False,
    }
    args.output.mkdir(parents=True)
    (args.output / "preregistration.json").write_bytes(canonical_bytes(prereg))
    status_path = args.output / "run-status.json"
    status = {
        "format": RUN_FORMAT,
        "format_version": RUN_VERSION,
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
    env = os.environ.copy()
    runtime_dir = str(Path(runtime["executable_path"]).resolve().parent)
    env["LD_LIBRARY_PATH"] = runtime_dir + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    process: subprocess.Popen[bytes] | None = None
    records = []
    try:
        with log_path.open("wb") as server_log:
            process = subprocess.Popen(command, cwd=runtime_dir, stdout=server_log, stderr=subprocess.STDOUT, env=env)
            runtime_record = load_json(ROOT / "benchmarks/grounding-runtime-llama-v040.json")
            wait_server(process, runtime["launch"]["host"], int(runtime["launch"]["port"]), float(runtime_record["server_ready_timeout_seconds"]))
            selected, calibration = calibrate_grounding_v1_contract(prereg, generation, policy)
            (args.output / "contract-calibration.json").write_bytes(canonical_bytes(calibration))
            with raw_path.open("wb") as raw:
                for question in questions:
                    item_id = question["item_id"]
                    text = question["question"]
                    a = request_grounding_v1_model(prereg, generation, messages(selected, text), selected)
                    a_record = {
                        "item_id": item_id,
                        "arm": "A",
                        "model_contract": selected,
                        "model_contract_valid": a["model_contract_valid"],
                        "model_contract_output": a["model_contract_output"],
                        "raw_content": a["raw_content"],
                        "input_tokens": a["input_tokens"],
                        "output_tokens": a["output_tokens"],
                        "model_latency_us": a["model_latency_us"],
                        "retrieved_document_ids": [],
                        "retrieved_titles": [],
                        "evidence_bytes": 0,
                    }
                    raw.write(canonical_bytes(a_record) + b"\n")
                    records.append(a_record)
                    hits, projection = _trim_hits(
                        corpus,
                        search(corpus, text, top_k=args.top_k),
                        text,
                        max_bytes=args.max_evidence_bytes,
                    )
                    g_messages = messages(selected, text, evidence=projection, policy=policy) if projection else messages(selected, text)
                    g = request_grounding_v1_model(prereg, generation, g_messages, selected)
                    g_record = {
                        "item_id": item_id,
                        "arm": "G",
                        "model_contract": selected,
                        "model_contract_valid": g["model_contract_valid"],
                        "model_contract_output": g["model_contract_output"],
                        "raw_content": g["raw_content"],
                        "input_tokens": g["input_tokens"],
                        "output_tokens": g["output_tokens"],
                        "model_latency_us": g["model_latency_us"],
                        "retrieved_document_ids": [hit["id"] for hit in hits],
                        "retrieved_titles": [hit["title"] for hit in hits],
                        "evidence_bytes": len(projection) if projection else 0,
                    }
                    raw.write(canonical_bytes(g_record) + b"\n")
                    records.append(g_record)
        stop_server(process)
        process = None
        if _source_hashes() != prereg["source_files"]:
            raise PublicBenchmarkError("public benchmark source hash drift during run")
        verify_candidate(candidate, include_gold=False)
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


def _normalize_answer(text: str | None) -> str:
    if not isinstance(text, str):
        return ""
    lowered = text.lower()
    no_punct = "".join(ch for ch in lowered if ch not in string.punctuation)
    no_articles = re.sub(r"\b(a|an|the)\b", " ", no_punct)
    return " ".join(no_articles.split())


def _f1(prediction: str | None, gold: str) -> tuple[int, int, int, float]:
    pred_tokens = _normalize_answer(prediction).split()
    gold_tokens = _normalize_answer(gold).split()
    if not pred_tokens or not gold_tokens:
        score = float(pred_tokens == gold_tokens)
        return int(score), len(pred_tokens), len(gold_tokens), score
    common = Counter(pred_tokens) & Counter(gold_tokens)
    same = sum(common.values())
    if same == 0:
        return 0, len(pred_tokens), len(gold_tokens), 0.0
    precision = same / len(pred_tokens)
    recall = same / len(gold_tokens)
    return same, len(pred_tokens), len(gold_tokens), 2 * precision * recall / (precision + recall)


def _verify_run(
    run: Path,
    manifest: dict[str, Any],
    item_count: int,
    *,
    manifest_sha256: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    status = loads((run / "run-status.json").read_bytes())
    if not isinstance(status, dict) or status.get("state") != "complete" or status.get("record_count") != item_count * 2:
        raise PublicBenchmarkError("Hotpot run is incomplete")
    sums = {}
    for line in (run / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        if "  " not in line:
            raise PublicBenchmarkError("invalid Hotpot SHA256SUMS line")
        digest, relative = line.split("  ", 1)
        if relative in sums or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise PublicBenchmarkError("unsafe/duplicate Hotpot SHA256SUMS path")
        sums[relative] = digest
    actual = {p.relative_to(run).as_posix() for p in run.rglob("*") if p.is_file() and p.name != "SHA256SUMS"}
    if set(sums) != actual or any(file_sha(run / relative) != digest for relative, digest in sums.items()):
        raise PublicBenchmarkError("Hotpot run checksum mismatch")

    prereg_path = run / "preregistration.json"
    prereg_raw = prereg_path.read_bytes()
    prereg = loads(prereg_raw)
    if not isinstance(prereg, dict) or prereg_raw != canonical_bytes(prereg):
        raise PublicBenchmarkError("Hotpot preregistration is not canonical")
    if prereg.get("format") != "exactscope.public-hotpot-preregistration" or prereg.get("format_version") != "0.1":
        raise PublicBenchmarkError("Hotpot preregistration identity drift")
    candidate_identity = prereg.get("candidate")
    if not isinstance(candidate_identity, dict) or candidate_identity != {
        "manifest_sha256": manifest_sha256,
        "questions_sha256": manifest["questions_sha256"],
        "corpus_index_sha256": manifest["corpus_index_sha256"],
        "item_count": manifest["item_count"],
        "mode": manifest["mode"],
    }:
        raise PublicBenchmarkError("Hotpot run/candidate identity mismatch")
    if prereg.get("source_files") != _source_hashes():
        raise PublicBenchmarkError("Hotpot run/source identity drift")
    if prereg.get("model_surface_sha256") != surface_sha256() or status.get("model_surface_sha256") != prereg["model_surface_sha256"]:
        raise PublicBenchmarkError("Hotpot model-surface identity drift")
    if prereg.get("arms") != ["A", "G"] or prereg.get("retry_count") != 0 or prereg.get("hidden_repair") is not False:
        raise PublicBenchmarkError("Hotpot A/G execution-policy drift")
    if prereg.get("gold_visible_to_runner") is not False:
        raise PublicBenchmarkError("Hotpot runner illegally permits gold visibility")
    if status.get("preregistration_sha256") != file_sha(prereg_path):
        raise PublicBenchmarkError("Hotpot preregistration/status identity drift")

    calibration_path = run / "contract-calibration.json"
    calibration_raw = calibration_path.read_bytes()
    calibration = loads(calibration_raw)
    selected = status.get("selected_model_contract")
    if (
        not isinstance(calibration, dict)
        or calibration_raw != canonical_bytes(calibration)
        or calibration.get("format") != "exactscope.grounding-v1-contract-calibration"
        or calibration.get("format_version") != "0.1"
        or calibration.get("selected_contract") != selected
        or calibration.get("model_surface_sha256") != prereg["model_surface_sha256"]
        or calibration.get("model_request_count") != status.get("calibration_model_requests")
    ):
        raise PublicBenchmarkError("Hotpot calibration identity drift")

    records = _load_jsonl(run / "raw-results.jsonl")
    if len(records) != item_count * 2 or status.get("answer_model_requests") != len(records):
        raise PublicBenchmarkError("Hotpot run record count drift")
    if status.get("total_model_requests_including_calibration") != len(records) + status.get("calibration_model_requests", -1):
        raise PublicBenchmarkError("Hotpot model-request accounting drift")
    for record in records:
        if record.get("arm") not in {"A", "G"} or record.get("model_contract") != selected:
            raise PublicBenchmarkError("Hotpot model record contract drift")
        raw_content = record.get("raw_content")
        if not isinstance(raw_content, str):
            raise PublicBenchmarkError("Hotpot model record lacks raw output")
        valid, value = parse_answer_object(raw_content)
        if record.get("model_contract_valid") is not valid or record.get("model_contract_output") != value:
            raise PublicBenchmarkError("Hotpot raw/model output mismatch")
        if type(record.get("input_tokens")) is not int or record["input_tokens"] <= 0:
            raise PublicBenchmarkError("Hotpot input-token accounting drift")
        if type(record.get("output_tokens")) is not int or record["output_tokens"] <= 0:
            raise PublicBenchmarkError("Hotpot output-token accounting drift")
        if type(record.get("model_latency_us")) is not int or record["model_latency_us"] <= 0:
            raise PublicBenchmarkError("Hotpot model-latency accounting drift")
        if record["arm"] == "A" and (record.get("retrieved_document_ids") != [] or record.get("retrieved_titles") != [] or record.get("evidence_bytes") != 0):
            raise PublicBenchmarkError("Hotpot A arm received retrieval evidence")
    return status, records


def score_run(candidate: Path, run: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise PublicBenchmarkError("score output exists")
    manifest, questions, _ = verify_candidate(candidate, include_gold=False)
    status, records = _verify_run(
        run,
        manifest,
        len(questions),
        manifest_sha256=file_sha(candidate / "manifest.json"),
    )
    # Gold is opened only after serving/run identity and checksums have been verified.
    verify_candidate(candidate, include_gold=True)
    gold_rows = _load_jsonl(candidate / "gold/answers.jsonl")
    gold = {row["item_id"]: row for row in gold_rows}
    keyed = {(row["item_id"], row["arm"]): row for row in records}
    if len(keyed) != len(records) or set(keyed) != {(q["item_id"], arm) for q in questions for arm in ("A", "G")}:
        raise PublicBenchmarkError("Hotpot A/G record identity drift")

    arms: dict[str, dict[str, Any]] = {}
    scored_rows = []
    for arm in ("A", "G"):
        exact = 0
        f1_total = 0.0
        format_failures = 0
        retrieval_all = 0
        retrieval_any = 0
        retrieval_den = 0
        for question in questions:
            item_id = question["item_id"]
            row = keyed[(item_id, arm)]
            expected = gold[item_id]
            prediction = row.get("model_contract_output") if row.get("model_contract_valid") else None
            em = int(_normalize_answer(prediction) == _normalize_answer(expected["answer"]))
            _, _, _, f1 = _f1(prediction, expected["answer"])
            exact += em
            f1_total += f1
            format_failures += int(not row.get("model_contract_valid"))
            support = set(expected["supporting_titles"])
            retrieved = set(row.get("retrieved_titles", []))
            if arm == "G" and support:
                retrieval_den += 1
                retrieval_all += int(support <= retrieved)
                retrieval_any += int(bool(support & retrieved))
            scored_rows.append({"item_id": item_id, "arm": arm, "exact_match": bool(em), "f1_milli": int(round(f1 * 1000))})
        n = len(questions)
        arms[arm] = {
            "exact_match": exact / n,
            "f1": f1_total / n,
            "format_failure_rate": format_failures / n,
            "mean_input_tokens": sum(keyed[(q["item_id"], arm)]["input_tokens"] for q in questions) / n,
        }
        if arm == "G":
            arms[arm]["retrieval_all_support_titles"] = retrieval_all / retrieval_den if retrieval_den else None
            arms[arm]["retrieval_any_support_title"] = retrieval_any / retrieval_den if retrieval_den else None
    summary = {
        "format": "exactscope.public-hotpot-summary",
        "format_version": "0.1",
        "candidate_mode": manifest["mode"],
        "item_count": len(questions),
        "model_id": status["model_id"],
        "selected_model_contract": status["selected_model_contract"],
        "arms": arms,
        "paired": {
            "exact_match_uplift": arms["G"]["exact_match"] - arms["A"]["exact_match"],
            "f1_uplift": arms["G"]["f1"] - arms["A"]["f1"],
        },
        "notes": {
            "qualification_eligible": False,
            "retrieval_mode": MODE,
            "gold_opened_after_run_integrity": True,
            "latency_from_parallel_screen_is_not_a_release_claim": True,
        },
    }
    output.mkdir(parents=True)
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "scored.jsonl").write_bytes(_jsonl_bytes(scored_rows))
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--parquet", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--dataset-identity", default="hotpotqa/hotpot_qa@a8af52d:distractor/validation")
    prepare.add_argument("--limit", type=int, default=100)
    prepare.add_argument("--seed", type=int, default=20260908)
    run = sub.add_parser("run")
    run.add_argument("--candidate", type=Path, required=True)
    run.add_argument("--model-id", required=True)
    run.add_argument("--model-root", type=Path)
    run.add_argument("--model-path", type=Path)
    run.add_argument("--runtime-executable", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--port", type=int, default=18201)
    run.add_argument("--threads", type=int, default=6)
    run.add_argument("--top-k", type=int, default=12)
    run.add_argument("--max-evidence-bytes", type=int, default=MAX_EVIDENCE_BYTES)
    score = sub.add_parser("score")
    score.add_argument("--candidate", type=Path, required=True)
    score.add_argument("--run", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            rows = read_hotpot_parquet(args.parquet)
            manifest = build_candidate_from_rows(
                rows,
                args.output,
                dataset_sha256=_dataset_sha(args.parquet),
                dataset_identity=args.dataset_identity,
                limit=args.limit,
                seed=args.seed,
            )
            print(json.dumps(manifest, indent=2, sort_keys=True))
        elif args.command == "run":
            run_screen(args)
            print(json.dumps(loads((args.output / "run-status.json").read_bytes()), indent=2, sort_keys=True))
        else:
            print(json.dumps(score_run(args.candidate, args.run, args.output), indent=2, sort_keys=True))
        return 0
    except (PublicBenchmarkError, BenchmarkRunError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ExactScope public Hotpot benchmark: FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
