#!/usr/bin/env python3
"""Fetch deterministic public benchmark screens for ExactScope v1 qualification.

Uses the Hugging Face datasets-server row API only as a transport. The tracked
suite file names the public datasets/configs/splits. Exact selected row indices
and fetched payload digests are recorded in the local manifest.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = ROOT / "benchmarks/v1-public-benchmark-suite.json"
USER_AGENT = "ExactScope-v1-public-suite/1"


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_page(task: dict, offset: int, length: int) -> dict:
    query = urllib.parse.urlencode({
        "dataset": task["dataset"],
        "config": task["config"],
        "split": task["split"],
        "offset": offset,
        "length": length,
    })
    request = urllib.request.Request(
        "https://datasets-server.huggingface.co/rows?" + query,
        headers={"User-Agent": USER_AGENT},
    )
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.load(response)
            if not isinstance(payload, dict) or not isinstance(payload.get("rows"), list):
                raise RuntimeError(f"malformed datasets-server response for {task['id']}")
            return payload
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 3:
                raise
            retry_after = exc.headers.get("Retry-After") if exc.headers is not None else None
            delay = float(retry_after) if retry_after and retry_after.isdigit() else float(2 ** attempt)
            time.sleep(max(1.0, min(delay, 8.0)))
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt == 3:
                raise
            time.sleep(float(2 ** attempt))
    raise RuntimeError(f"datasets-server transport failed for {task['id']}: {last_error}")


def selected_indices(total: int, count: int) -> list[int]:
    if total <= 0 or count <= 0 or count > total:
        raise ValueError("invalid deterministic screen bounds")
    indices = [min(total - 1, ((2 * i + 1) * total) // (2 * count)) for i in range(count)]
    if len(set(indices)) != count:
        raise RuntimeError("deterministic screen produced duplicate indices")
    return indices


def normalize_mc(task_id: str, row: dict) -> dict:
    if task_id == "mmlu":
        choices = list(row["choices"])
        labels = [chr(ord("A") + i) for i in range(len(choices))]
        answer = labels[int(row["answer"])]
        question = str(row["question"])
        metadata = {"subject": row.get("subject")}
    elif task_id == "arc_challenge":
        question = str(row["question"])
        labels = [str(value) for value in row["choices"]["label"]]
        choices = [str(value) for value in row["choices"]["text"]]
        answer = str(row["answerKey"])
        metadata = {"source_id": row.get("id")}
    elif task_id == "hellaswag":
        question = str(row.get("ctx") or (str(row.get("ctx_a", "")) + " " + str(row.get("ctx_b", "")))).strip()
        choices = [str(value) for value in row["endings"]]
        labels = [chr(ord("A") + i) for i in range(len(choices))]
        answer = labels[int(row["label"])]
        metadata = {"activity_label": row.get("activity_label"), "source_id": row.get("source_id")}
    elif task_id == "truthfulqa_mc1":
        question = str(row["question"])
        target = row["mc1_targets"]
        choices = [str(value) for value in target["choices"]]
        labels = [chr(ord("A") + i) for i in range(len(choices))]
        correct = [i for i, value in enumerate(target["labels"]) if int(value) == 1]
        if len(correct) != 1:
            raise RuntimeError("TruthfulQA MC1 row does not have exactly one correct answer")
        answer = labels[correct[0]]
        metadata = {}
    elif task_id == "winogrande":
        question = str(row["sentence"])
        choices = [str(row["option1"]), str(row["option2"])]
        labels = ["A", "B"]
        answer = labels[int(row["answer"]) - 1]
        metadata = {}
    else:
        raise ValueError(f"unsupported multiple-choice task: {task_id}")
    if len(labels) != len(choices) or answer not in labels:
        raise RuntimeError(f"invalid normalized choices for {task_id}")
    return {
        "question": question,
        "choices": [{"label": label, "text": text} for label, text in zip(labels, choices, strict=True)],
        "answer": answer,
        "metadata": metadata,
    }


def normalize_gsm8k(row: dict) -> dict:
    answer_text = str(row["answer"])
    match = re.search(r"####\s*([^\n]+)\s*$", answer_text)
    if match is None:
        raise RuntimeError("GSM8K row lacks final #### answer")
    answer = match.group(1).strip().replace(",", "")
    return {"question": str(row["question"]), "answer": answer, "metadata": {}}


def normalize(task: dict, index: int, row: dict) -> dict:
    if task["kind"] == "multiple_choice":
        normalized = normalize_mc(task["id"], row)
    elif task["kind"] == "numeric_generation" and task["id"] == "gsm8k":
        normalized = normalize_gsm8k(row)
    else:
        raise ValueError(f"unsupported benchmark kind: {task['kind']}")
    return {
        "benchmark_id": task["id"],
        "dataset": task["dataset"],
        "config": task["config"],
        "split": task["split"],
        "source_index": index,
        "kind": task["kind"],
        **normalized,
    }


def fetch_one(task: dict, index: int) -> dict:
    page = fetch_page(task, index, 1)
    rows = page["rows"]
    if len(rows) != 1 or not isinstance(rows[0], dict) or not isinstance(rows[0].get("row"), dict):
        raise RuntimeError(f"could not fetch exact row {index} for {task['id']}")
    return normalize(task, index, rows[0]["row"])


def write_jsonl(path: Path, rows: list[dict]) -> str:
    data = b"".join(canonical(row) for row in rows)
    path.write_bytes(data)
    return sha256_bytes(data)


def fetch_task_via_datasets(task: dict, count: int) -> tuple[int, list[int], list[dict]]:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError(
            "datasets transport requires the optional 'datasets' package; use an isolated benchmark venv"
        ) from exc
    dataset = load_dataset(task["dataset"], task["config"], split=task["split"])
    total = len(dataset)
    if total < count:
        raise RuntimeError(f"invalid total row count for {task['id']}")
    indices = selected_indices(total, count)
    rows = [normalize(task, index, dict(dataset[index])) for index in indices]
    return total, indices, rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "target/v1-public-suite-data")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--transport",
        choices=("datasets-server", "huggingface-datasets"),
        default="datasets-server",
    )
    args = parser.parse_args()

    suite_bytes = args.suite.read_bytes()
    suite = json.loads(suite_bytes)
    tasks = suite.get("standard_panel") if isinstance(suite, dict) else None
    count = suite.get("methodology", {}).get("standard_screen_items_per_task") if isinstance(suite, dict) else None
    if not isinstance(tasks, list) or len(tasks) != 6 or type(count) is not int or count <= 0:
        raise RuntimeError("invalid v1 public suite definition")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    manifest_tasks = []
    for task in tasks:
        if args.transport == "huggingface-datasets":
            total, indices, rows = fetch_task_via_datasets(task, count)
        else:
            probe = fetch_page(task, 0, 1)
            total = probe.get("num_rows_total")
            if type(total) is not int or total < count:
                raise RuntimeError(f"invalid total row count for {task['id']}")
            indices = selected_indices(total, count)
            rows = []
            with ThreadPoolExecutor(max_workers=max(1, min(args.workers, count))) as pool:
                futures = {pool.submit(fetch_one, task, index): index for index in indices}
                for future in as_completed(futures):
                    rows.append(future.result())
            rows.sort(key=lambda row: row["source_index"])
        filename = f"{task['id']}-{count}.jsonl"
        digest = write_jsonl(args.output_dir / filename, rows)
        manifest_tasks.append({
            "id": task["id"],
            "dataset": task["dataset"],
            "config": task["config"],
            "split": task["split"],
            "kind": task["kind"],
            "source_rows_total": total,
            "selected_indices": indices,
            "item_count": len(rows),
            "filename": filename,
            "sha256": digest,
        })
        print(f"READY {task['id']} {len(rows)}/{total} {digest}", flush=True)

    manifest = {
        "format": "exactscope.v1-public-suite-data",
        "format_version": "0.1",
        "suite_sha256": sha256_bytes(suite_bytes),
        "transport": args.transport,
        "selection": suite["methodology"]["selection"],
        "tasks": manifest_tasks,
    }
    manifest_bytes = canonical(manifest)
    (args.output_dir / "manifest.json").write_bytes(manifest_bytes)
    print(json.dumps({"status": "PASS", "tasks": len(manifest_tasks), "items": sum(row["item_count"] for row in manifest_tasks), "manifest_sha256": sha256_bytes(manifest_bytes)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
