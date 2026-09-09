#!/usr/bin/env python3
"""Run the frozen ExactScope v1 20-model public benchmark screen sequentially.

This orchestrates ``run_v1_public_suite.py`` only.  It is a deterministic,
post-release smoke/capability screen over famous public datasets; it is NOT an
Open LLM Leaderboard reproduction and is not an ExactScope A/G efficacy test.

The matrix preregistration is written before the first child starts.  Each model
is attempted once, in frozen matrix order, with no automatic retry, overwrite,
or resume.  Failed cells remain explicit in the aggregate result.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "benchmarks/run_v1_public_suite.py"
MATRIX = ROOT / "benchmarks/v1-model-matrix-20.json"
DATA_DIR = ROOT / "target/v1-public-suite-data"
ACQUISITION = ROOT / "target/v1-20-model-acquisition.json"
TASK_IDS = ("mmlu", "arc_challenge", "hellaswag", "truthfulqa_mc1", "winogrande", "gsm8k")
IDENTITY_FIELDS = ("id", "repository", "resolved_revision", "requested_file", "quantization", "bytes")


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load(path: Path) -> dict[str, Any]:
    def pairs(items):
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise ValueError(f"duplicate JSON key: {key}")
            out[key] = value
        return out

    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs,
                       parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return value


def write_new(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")


def verify_models(matrix: dict[str, Any], acquisition: dict[str, Any], matrix_sha: str) -> list[dict[str, Any]]:
    if matrix.get("format") != "exactscope.v1-model-matrix":
        raise ValueError("invalid model matrix format")
    policy = matrix.get("selection_policy")
    specs = matrix.get("models")
    if not isinstance(policy, dict) or policy.get("frozen") is not True or policy.get("model_count") != 20:
        raise ValueError("model matrix is not the frozen 20-model contract")
    if not isinstance(specs, list) or len(specs) != 20:
        raise ValueError("model matrix must contain exactly 20 models")
    if acquisition.get("format") != "exactscope.v1-model-acquisition" or acquisition.get("model_count") != 20:
        raise ValueError("invalid 20-model acquisition manifest")
    if acquisition.get("matrix_sha256") != matrix_sha:
        raise ValueError("acquisition is not bound to the selected matrix")
    acquired_rows = acquisition.get("records")
    if not isinstance(acquired_rows, list) or len(acquired_rows) != 20:
        raise ValueError("acquisition must contain exactly 20 model records")
    acquired = {row.get("id"): row for row in acquired_rows if isinstance(row, dict)}
    if len(acquired) != 20:
        raise ValueError("acquisition model ids are duplicate or invalid")
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    for spec in specs:
        if not isinstance(spec, dict):
            raise ValueError("model spec is not an object")
        model_id = spec.get("id")
        if not isinstance(model_id, str) or model_id in seen or model_id not in acquired:
            raise ValueError("matrix/acquisition model set drift")
        seen.add(model_id)
        row = acquired[model_id]
        for field in IDENTITY_FIELDS:
            if row.get(field) != spec.get(field):
                raise ValueError(f"model identity mismatch: {model_id}/{field}")
        upstream = spec.get("upstream_sha256")
        if not isinstance(upstream, str) or len(upstream) != 64:
            raise ValueError(f"unfrozen upstream digest: {model_id}")
        if row.get("sha256") != upstream or row.get("upstream_sha256") != upstream:
            raise ValueError(f"local/upstream model digest mismatch: {model_id}")
        path = Path(str(row.get("path", "")))
        if not path.is_absolute() or not path.is_file() or path.stat().st_size != spec.get("bytes"):
            raise ValueError(f"model file missing or size drift: {model_id}")
        if file_sha(path) != upstream:
            raise ValueError(f"model file SHA drift: {model_id}")
        ordered.append(row)
    return ordered


def verify_public_data(data_dir: Path) -> dict[str, Any]:
    manifest_path = data_dir / "manifest.json"
    manifest = load(manifest_path)
    if manifest.get("format") != "exactscope.v1-public-suite-data" or manifest.get("format_version") != "0.1":
        raise ValueError("invalid public suite data manifest")
    records = manifest.get("tasks")
    if not isinstance(records, list) or len(records) != 6:
        raise ValueError("public suite must contain six tasks")
    by_id = {row.get("id"): row for row in records if isinstance(row, dict)}
    if set(by_id) != set(TASK_IDS):
        raise ValueError("public suite task identity drift")
    total = 0
    frozen: dict[str, str] = {str(manifest_path.resolve()): file_sha(manifest_path)}
    for task in TASK_IDS:
        row = by_id[task]
        if row.get("item_count") != 24:
            raise ValueError(f"public screen must contain 24 {task} items")
        path = data_dir / str(row.get("filename", ""))
        if not path.is_file() or file_sha(path) != row.get("sha256"):
            raise ValueError(f"public data file drift: {task}")
        frozen[str(path.resolve())] = row["sha256"]
        total += row["item_count"]
    if total != 144:
        raise ValueError("public suite must contain exactly 144 items")
    return {"manifest": manifest, "hashes": frozen, "total_items": total}


def verify_hashes(mapping: dict[str, str]) -> None:
    for name, expected in mapping.items():
        path = Path(name)
        if not path.is_file() or file_sha(path) != expected:
            raise ValueError(f"frozen input drift: {name}")


def preregister(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    if output.exists():
        raise ValueError("output exists; overwrite/resume forbidden")
    matrix = load(args.matrix)
    acquisition = load(args.acquisition_manifest)
    matrix_sha = file_sha(args.matrix)
    models = verify_models(matrix, acquisition, matrix_sha)
    data = verify_public_data(args.data_dir)
    runtime = args.runtime_executable.resolve()
    if not runtime.is_file():
        raise ValueError("runtime executable missing")
    if not 1 <= args.port <= 65516 or args.threads < 1 or args.context < 512:
        raise ValueError("invalid runtime settings")
    frozen = dict(data["hashes"])
    for path in (args.matrix.resolve(), args.acquisition_manifest.resolve(), RUNNER.resolve(), Path(__file__).resolve(), runtime):
        frozen[str(path)] = file_sha(path)
    for path in runtime.parent.iterdir():
        if path.is_file() and (path.suffix.lower() in {".dll", ".so", ".dylib"} or ".so." in path.name):
            frozen[str(path.resolve())] = file_sha(path)
    cells = []
    for index, row in enumerate(models):
        cell_output = output / "cells" / row["id"]
        cell_port = args.port + index
        command = [
            sys.executable, str(RUNNER),
            "--acquisition-manifest", str(args.acquisition_manifest.resolve()),
            "--data-dir", str(args.data_dir.resolve()),
            "--runtime-executable", str(runtime),
            "--model-id", row["id"],
            "--output", str(cell_output),
            "--port", str(cell_port),
            "--threads", str(args.threads),
            "--context", str(args.context),
        ]
        cells.append({
            "model_id": row["id"], "model_sha256": row["sha256"],
            "model_path": row["path"], "output": str(cell_output), "port": cell_port,
            "command": command,
        })
    return {
        "format": "exactscope.v1-public-matrix-preregistration",
        "format_version": "0.1",
        "model_inference_performed": False,
        "leaderboard_comparable": False,
        "claim_scope": "deterministic 24-item-per-task public capability screen; not an official benchmark leaderboard reproduction",
        "retry_count": 0,
        "resume": False,
        "model_count": 20,
        "task_ids": list(TASK_IDS),
        "items_per_task": 24,
        "items_per_model": 144,
        "runtime": {"executable": str(runtime), "sha256": file_sha(runtime), "base_port": args.port,
                    "port_policy": "cell port = base_port + frozen model index",
                    "threads": args.threads, "context": args.context},
        "matrix_sha256": matrix_sha,
        "acquisition_manifest_sha256": file_sha(args.acquisition_manifest),
        "data_manifest_sha256": data["hashes"][str((args.data_dir / "manifest.json").resolve())],
        "frozen_files": frozen,
        "cells": cells,
    }


def invoke(command: list[str], log: Path) -> int:
    with log.open("xb") as handle:
        result = subprocess.run(command, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT, check=False)
    return result.returncode


def validate_child(summary: dict[str, Any], cell: dict[str, Any], protocol: dict[str, Any]) -> None:
    if summary.get("format") != "exactscope.v1-public-screen-result" or summary.get("format_version") != "0.1":
        raise ValueError("child summary format drift")
    if summary.get("leaderboard_comparable") is not False:
        raise ValueError("child incorrectly claims leaderboard comparability")
    model = summary.get("model")
    if not isinstance(model, dict) or model.get("id") != cell["model_id"] or model.get("sha256") != cell["model_sha256"]:
        raise ValueError("child model identity drift")
    if summary.get("runtime_sha256") != protocol["runtime"]["sha256"]:
        raise ValueError("child runtime identity drift")
    if summary.get("data_manifest_sha256") != protocol["data_manifest_sha256"]:
        raise ValueError("child data identity drift")
    if summary.get("expected_items") != 144 or summary.get("total_items") != 144 or summary.get("unattempted_items") != 0:
        raise ValueError("child item count drift")
    tasks = summary.get("tasks")
    if not isinstance(tasks, dict) or set(tasks) != set(TASK_IDS):
        raise ValueError("child task set drift")
    for task in TASK_IDS:
        metrics = tasks[task]
        if metrics.get("items") != 24:
            raise ValueError(f"child {task} denominator drift")
        accuracy = metrics.get("accuracy")
        if type(accuracy) not in (int, float) or not 0 <= accuracy <= 1:
            raise ValueError(f"child {task} accuracy invalid")


def run_matrix(args: argparse.Namespace) -> bool:
    protocol = preregister(args)
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_new(output / "preregistration.json", protocol)
    write_new(output / "preregistration-checksum.json", {"sha256": file_sha(output / "preregistration.json")})
    (output / "logs").mkdir()
    (output / "ledger").mkdir()
    rows: list[dict[str, Any]] = []
    for cell in protocol["cells"]:
        entry: dict[str, Any] = {"model_id": cell["model_id"], "status": "failed", "error": None,
                                 "summary": None}
        try:
            verify_hashes(protocol["frozen_files"])
            if file_sha(Path(cell["model_path"])) != cell["model_sha256"]:
                raise ValueError("model file drift")
            returncode = invoke(cell["command"], output / "logs" / f"{cell['model_id']}.log")
            if returncode != 0:
                raise ValueError(f"child exit code {returncode}")
            child = Path(cell["output"])
            if not (child / "preregistration.json").is_file() or not (child / "summary.json").is_file():
                raise ValueError("child omitted preregistration or summary")
            summary = load(child / "summary.json")
            validate_child(summary, cell, protocol)
            if (summary.get("status") != "PASS" or summary.get("total_infrastructure_errors") != 0
                    or summary.get("total_protocol_errors") != 0):
                raise ValueError(
                    f"child execution invalid: {summary.get('status')} "
                    f"infrastructure={summary.get('total_infrastructure_errors')} "
                    f"protocol={summary.get('total_protocol_errors')}"
                )
            verify_hashes(protocol["frozen_files"])
            entry.update(status="completed", summary=summary,
                         artifacts={str(p.resolve()): file_sha(p) for p in child.rglob("*") if p.is_file()})
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
            entry["error"] = str(exc)
        rows.append(entry)
        write_new(output / "ledger" / f"{cell['model_id']}.json", entry)
    result = aggregate(protocol, rows)
    write_new(output / "matrix-results.json", result)
    with (output / "matrix-results.csv").open("x", newline="", encoding="utf-8") as handle:
        fields = ["model_id", "status", "mmlu", "arc_challenge", "hellaswag", "truthfulqa_mc1",
                  "winogrande", "gsm8k", "macro_accuracy", "total_errors", "format_errors",
                  "protocol_errors", "infrastructure_errors", "error"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in result["models"]:
            writer.writerow(row)
    checks = {str(p.relative_to(output).as_posix()): file_sha(p) for p in output.rglob("*")
              if p.is_file() and p.name != "checksums.json"}
    write_new(output / "checksums.json", checks)
    return result["completed_models"] == 20


def aggregate(protocol: dict[str, Any], ledger_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if len(ledger_rows) != 20 or len({r.get("model_id") for r in ledger_rows}) != 20:
        raise ValueError("aggregate requires 20 explicit unique model rows")
    expected = [cell["model_id"] for cell in protocol["cells"]]
    if [row.get("model_id") for row in ledger_rows] != expected:
        raise ValueError("aggregate model order/identity drift")
    models = []
    completed = 0
    task_sums = {task: 0.0 for task in TASK_IDS}
    task_den = {task: 0 for task in TASK_IDS}
    for entry in ledger_rows:
        row = {"model_id": entry["model_id"], "status": entry.get("status"), "error": entry.get("error")}
        summary = entry.get("summary") if entry.get("status") == "completed" else None
        if isinstance(summary, dict):
            completed += 1
            for task in TASK_IDS:
                value = summary["tasks"][task]["accuracy"]
                row[task] = value
                task_sums[task] += value
                task_den[task] += 1
            row["macro_accuracy"] = summary["macro_accuracy"]
            row["total_errors"] = summary["total_errors"]
            row["format_errors"] = summary["total_format_errors"]
            row["protocol_errors"] = summary["total_protocol_errors"]
            row["infrastructure_errors"] = summary["total_infrastructure_errors"]
        else:
            for task in TASK_IDS:
                row[task] = None
            row.update(macro_accuracy=None, total_errors=None, format_errors=None,
                       protocol_errors=None, infrastructure_errors=None)
        models.append(row)
    means = {task: (task_sums[task] / task_den[task] if task_den[task] else None) for task in TASK_IDS}
    macro_values = [row["macro_accuracy"] for row in models if row["macro_accuracy"] is not None]
    return {
        "format": "exactscope.v1-public-matrix-results", "format_version": "0.1",
        "leaderboard_comparable": False,
        "claim_scope": protocol["claim_scope"],
        "scheduled_models": 20, "completed_models": completed,
        "items_per_task_per_model": 24, "items_per_model": 144,
        "task_mean_accuracy": means,
        "mean_macro_accuracy": sum(macro_values) / len(macro_values) if macro_values else None,
        "models": models,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=MATRIX)
    parser.add_argument("--acquisition-manifest", type=Path, default=ACQUISITION)
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--runtime-executable", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18400)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--context", type=int, default=4096)
    args = parser.parse_args(argv)
    try:
        return 0 if run_matrix(args) else 1
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        print(f"public matrix: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
