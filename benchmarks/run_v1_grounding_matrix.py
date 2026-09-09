#!/usr/bin/env python3
"""Preregister, run, then separately score the frozen twenty-model A/G panel."""
from __future__ import annotations

import argparse
import ast
import csv
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "benchmarks"), str(ROOT / "tools")]
from grounding_preregister import file_sha, resolve_runtime
import public_nq_benchmark as nq
import public_hotpot_benchmark as hotpot
import public_fever_benchmark as fever

PANEL = {"natural_questions": nq, "hotpotqa": hotpot, "fever": fever}
FORMATS = {"natural_questions": "nq", "hotpotqa": "hotpot", "fever": "fever"}
IDENTITY = ("repository", "resolved_revision", "requested_file", "quantization", "bytes")
SERVING_FILES = {
    "natural_questions": ("serving/manifest.json", "serving/questions.jsonl", "serving/chunks.jsonl", "serving/corpus-index.json"),
    "hotpotqa": ("manifest.json", "serving/questions.jsonl", "serving/corpus-index.json"),
    "fever": ("serving/manifest.json", "serving/items.jsonl", "serving/corpus-candidates.jsonl", "serving/corpus-index.json"),
}


def read(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    def constant(value):
        raise ValueError(f"nonfinite JSON: {value}")
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs,
                      parse_constant=constant)


def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")


def indexed(rows, count):
    if not isinstance(rows, list) or len(rows) != count:
        raise ValueError(f"expected exactly {count} records")
    result = {}
    for row in rows:
        key = row["id"]
        if not isinstance(key, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", key) or key in result:
            raise ValueError("invalid or duplicate id")
        result[key] = row
    return result


def match_models(matrix, acquisition, inventory, matrix_sha):
    if matrix.get("format") != "exactscope.v1-model-matrix" or matrix.get("selection_policy", {}).get("frozen") is not True:
        raise ValueError("model matrix must be frozen")
    if matrix["selection_policy"].get("model_count") != 20:
        raise ValueError("matrix must specify twenty models")
    if acquisition.get("format") != "exactscope.v1-model-acquisition" or acquisition.get("model_count") != 20:
        raise ValueError("invalid acquisition manifest")
    if inventory.get("format") != "exactscope.grounding-model-inventory":
        raise ValueError("invalid inventory")
    if acquisition.get("matrix_sha256") != matrix_sha or inventory.get("source_inventory_sha256") != matrix_sha:
        raise ValueError("matrix hash mismatch")
    specs = indexed(matrix["models"], 20)
    acquired = indexed(acquisition["records"], 20)
    registered = indexed(inventory["records"], 20)
    if specs.keys() != acquired.keys() or specs.keys() != registered.keys():
        raise ValueError("twenty-model sets differ")
    for key, spec in specs.items():
        a, i = acquired[key], registered[key]
        for field in IDENTITY:
            if spec[field] != a[field] or spec[field] != i[field]:
                raise ValueError(f"model identity mismatch: {key}/{field}")
        if not re.fullmatch(r"[0-9a-f]{40}", spec["resolved_revision"]):
            raise ValueError("unfrozen model revision")
        digest = spec["upstream_sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or a["sha256"] != digest or i["sha256"] != digest or a.get("upstream_sha256") != digest:
            raise ValueError(f"model digest mismatch: {key}")
        if a.get("runtime") != "llama.cpp" or i.get("runtime") != "llama.cpp":
            raise ValueError("unsupported model runtime")
        path = Path(a["path"])
        if not path.is_absolute() or not path.is_file() or path.stat().st_size != spec["bytes"] or file_sha(path) != digest:
            raise ValueError(f"model file identity mismatch: {key}")
    return list(acquired[key] for key in specs)


def select_runtime(executable, record=None):
    if record is None:
        digest = file_sha(executable)
        choices = [ROOT / "benchmarks/grounding-runtime-llama-v040.json",
                   ROOT / "benchmarks/grounding-runtime-llama-b10797-windows.json"]
        matches = [path for path in choices if read(path).get("executable_sha256") == digest]
        if len(matches) != 1:
            raise ValueError("runtime is not uniquely known; supply --runtime-record")
        record = matches[0]
    _, runtime = resolve_runtime(record, executable)
    return Path(record).resolve(), runtime


def source_paths():
    pending = [Path(__file__).resolve()] + [Path(module.__file__).resolve() for module in PANEL.values()]
    found = set()
    while pending:
        path = pending.pop()
        if path in found:
            continue
        found.add(path)
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = ([node.module] if isinstance(node, ast.ImportFrom) else
                     [a.name for a in node.names] if isinstance(node, ast.Import) else [])
            for name in names:
                if name:
                    for directory in (ROOT / "tools", ROOT / "benchmarks"):
                        dependency = directory / (name.replace(".", "/") + ".py")
                        if dependency.is_file():
                            pending.append(dependency.resolve())
    return found


def hashes(paths):
    return {str(path.resolve()): file_sha(path) for path in sorted(set(paths))}


def verify_hashes(frozen):
    for name, digest in frozen.items():
        if file_sha(Path(name)) != digest:
            raise ValueError(f"frozen file drift: {name}")


def preflight(args):
    output = args.output.resolve()
    if output.exists():
        raise ValueError("output exists; overwrite/resume forbidden")
    matrix, acquisition, inventory, suite = [read(p) for p in
        (args.matrix, args.acquisition_manifest, args.model_inventory, args.suite)]
    models = match_models(matrix, acquisition, inventory, file_sha(args.matrix))
    if suite.get("format") != "exactscope.v1-public-benchmark-suite":
        raise ValueError("invalid suite")
    panel = indexed(suite["exactscope_grounding_panel"], 3)
    if panel.keys() != PANEL.keys():
        raise ValueError("suite must contain exactly the three grounding benchmarks")
    record, runtime = select_runtime(args.runtime_executable, args.runtime_record)
    workers = getattr(args, "workers", 1)
    if not 1 <= args.port <= 65476 or args.threads < 1 or not 1 <= workers <= 4:
        raise ValueError("invalid port, threads, or workers")
    paths = source_paths() | {args.matrix, args.acquisition_manifest, args.model_inventory, args.suite,
        record, args.runtime_executable, Path(sys.executable),
        ROOT / "benchmarks/grounding-generation-config.json",
        ROOT / "benchmarks/grounding-isolation-policy.json", nq.POLICY_PATH}
    generation = read(ROOT / "benchmarks/grounding-generation-config.json")
    if generation.get("retry_count") != 0 or generation.get("hidden_repair") is not False:
        raise ValueError("generation violates no-retry policy")
    paths.update(p for p in args.runtime_executable.resolve().parent.iterdir()
                 if p.is_file() and (p.suffix.lower() in {".dll", ".so", ".dylib"} or ".so." in p.name))
    candidates = {}
    for task, spec in panel.items():
        if spec.get("arms") != ["A", "G"] or type(spec.get("items")) is not int or spec["items"] < 1:
            raise ValueError("suite A/G or item-count mismatch")
        candidate = (ROOT / spec["candidate_path"]).resolve()
        candidate_paths = [candidate / name for name in SERVING_FILES[task]]
        # Reject redirects before native verification can open a serving file.
        if any(path.resolve() != path for path in candidate_paths):
            raise ValueError("serving inputs must not redirect to other files")
        verified = (hotpot.verify_candidate(candidate, include_gold=False) if task == "hotpotqa"
                    else PANEL[task].verify_serving_candidate(candidate))
        if len(verified[1]) != spec["items"]:
            raise ValueError(f"suite candidate count mismatch: {task}")
        # Freeze serving inputs only. Gold is owned exclusively by native scorers,
        # which open it only after validating the complete child run.
        candidate_hashes = hashes(candidate_paths)
        paths.update(Path(p) for p in candidate_hashes)
        candidates[task] = {"path": str(candidate), "items": spec["items"], "hashes": candidate_hashes}
    cells = []
    cell_index = 0
    for model in models:
        for task, module in PANEL.items():
            key = model["id"] + "--" + task
            run = output / "cells" / key
            score = output / "scores" / key
            cell_port = args.port + cell_index
            cell_index += 1
            base = [sys.executable, str(Path(module.__file__).resolve())]
            command = base + ["run", "--candidate", candidates[task]["path"], "--model-id", model["id"],
                "--model-path", model["path"], "--model-inventory", str(args.model_inventory.resolve()),
                "--runtime-record", str(record), "--runtime-executable", str(args.runtime_executable.resolve()),
                "--port", str(cell_port), "--threads", str(args.threads), "--top-k", "12",
                "--max-evidence-bytes", "4096", "--output", str(run)]
            cells.append({"id": key, "model_id": model["id"], "benchmark_id": task,
                "model_path": model["path"], "model_sha256": model["sha256"], "port": cell_port,
                "run": str(run), "score": str(score),
                "run_command": command, "score_command": base + ["score", "--candidate", candidates[task]["path"],
                    "--run", str(run), "--output", str(score)]})
    return {"format": "exactscope.v1-grounding-matrix-preregistration", "format_version": "0.1",
        "output": str(output), "cwd": str(ROOT), "model_inference_performed": False,
        "retry_count": 0, "resume": False, "arms": ["A", "G"], "models": models,
        "parallel_workers": workers,
        "parallelism_scope": "models may run concurrently; each model's three benchmark cells remain sequential; latency is non-qualifying",
        "runtime": {**runtime, "base_port": args.port,
                    "port_policy": "cell port = base_port + frozen cell index"},
        "candidates": candidates, "frozen_files": hashes(paths), "cells": cells,
        "gold_policy": "no gold access in preflight/run; native scorers access gold only after child run integrity",
        "calibration_policy": "each native benchmark selects its contract independently"}


def invoke(command, log):
    with log.open("xb") as handle:
        result = subprocess.run(command, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        raise ValueError(f"child exit code {result.returncode}")


def verify_child_run(protocol, cell):
    candidate = Path(protocol["candidates"][cell["benchmark_id"]]["path"])
    run = Path(cell["run"])
    if cell["benchmark_id"] == "natural_questions":
        manifest, questions, chunks, _ = nq.verify_serving_candidate(candidate)
        nq._verify_run(candidate, manifest, questions, chunks, run)
    elif cell["benchmark_id"] == "hotpotqa":
        manifest, questions, _ = hotpot.verify_candidate(candidate, include_gold=False)
        _, records = hotpot._verify_run(run, manifest, len(questions),
                                       manifest_sha256=file_sha(candidate / "manifest.json"))
        hotpot.verify_record_keys(questions, records)
    else:
        _, items, _, _ = fever.verify_serving_candidate(candidate)
        fever.verify_run(candidate, run, len(items))


def run_matrix(args):
    protocol = preflight(args)
    output = Path(protocol["output"])
    output.mkdir(parents=True, exist_ok=False)
    write(output / "preregistration.json", protocol)
    write(output / "preregistration-checksum.json", {"sha256": file_sha(output / "preregistration.json")})
    (output / "ledger").mkdir()
    (output / "logs").mkdir()

    def run_cell(cell):
        entry = {"id": cell["id"], "status": "failed", "error": None}
        try:
            verify_hashes(protocol["frozen_files"])
            verify_hashes({cell["model_path"]: cell["model_sha256"]})
            invoke(cell["run_command"], output / "logs" / (cell["id"] + ".run.log"))
            run = Path(cell["run"])
            if not (run / "preregistration.json").is_file() or not (run / "run-status.json").is_file():
                raise ValueError("child omitted run identity/status")
            verify_child_run(protocol, cell)
            verify_hashes(protocol["frozen_files"])
            entry.update(status="completed", artifacts=hashes(p for p in run.rglob("*") if p.is_file()))
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
            entry["error"] = str(exc)
        write(output / "ledger" / (cell["id"] + ".json"), entry)
        return entry

    groups = []
    for model in protocol["models"]:
        group = [cell for cell in protocol["cells"] if cell["model_id"] == model["id"]]
        if len(group) != 3:
            raise ValueError("each model must have exactly three benchmark cells")
        groups.append(group)

    def run_group(group):
        return [run_cell(cell) for cell in group]

    with ThreadPoolExecutor(max_workers=protocol["parallel_workers"]) as executor:
        futures = [executor.submit(run_group, group) for group in groups]
        for future in futures:
            future.result()

    ledger = hashes((output / "ledger").glob("*.json"))
    write(output / "run-complete.json", {"preregistration_sha256": file_sha(output / "preregistration.json"), "ledger": ledger})
    return all(read(Path(p))["status"] == "completed" for p in ledger)


def validate_summary(summary, cell, count):
    if summary.get("format") != f"exactscope.public-{FORMATS[cell['benchmark_id']]}-summary" or summary.get("format_version") != "0.1":
        raise ValueError("summary format mismatch")
    if summary.get("model_id") != cell["model_id"] or summary.get("item_count") != count:
        raise ValueError("summary model/count mismatch")
    if set(summary.get("arms", {})) != {"A", "G"}:
        raise ValueError("summary arms mismatch")
    metrics = ["label_accuracy"] if cell["benchmark_id"] == "fever" else ["exact_match", "f1"]
    for metric in metrics:
        for arm in ("A", "G"):
            value = summary["arms"][arm][metric]
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("invalid summary metric")
        uplift = summary["paired"][metric + "_uplift"]
        if type(uplift) not in (int, float) or not math.isfinite(uplift) or not math.isclose(
                uplift, summary["arms"]["G"][metric] - summary["arms"]["A"][metric], abs_tol=1e-12):
            raise ValueError("summary uplift mismatch")


def score_matrix(output):
    output = output.resolve()
    protocol = read(output / "preregistration.json")
    digest = read(output / "preregistration-checksum.json")["sha256"]
    verify_hashes({str(output / "preregistration.json"): digest})
    if protocol["output"] != str(output) or len(protocol["cells"]) != 60:
        raise ValueError("matrix location or cell count mismatch")
    expected = {m["id"] + "--" + task for m in protocol["models"] for task in PANEL}
    if len(expected) != 60 or {c["id"] for c in protocol["cells"]} != expected:
        raise ValueError("matrix cell identity mismatch")
    # Exclusive directory is also the score-phase lock: interrupted scoring cannot resume.
    (output / "scores").mkdir(exist_ok=False)
    rows = []
    for cell in protocol["cells"]:
        row = {"id": cell["id"], "model_id": cell["model_id"], "benchmark_id": cell["benchmark_id"],
               "status": "invalid", "error": None, "summary": None}
        try:
            verify_hashes(protocol["frozen_files"])
            complete = read(output / "run-complete.json")
            if complete["preregistration_sha256"] != digest:
                raise ValueError("run completion identity mismatch")
            ledger_path = output / "ledger" / (cell["id"] + ".json")
            verify_hashes({str(ledger_path): complete["ledger"][str(ledger_path)]})
            ledger = read(ledger_path)
            if ledger["id"] != cell["id"] or ledger["status"] != "completed":
                raise ValueError(f"run failed: {ledger.get('error')}")
            verify_hashes(ledger["artifacts"])
            child = read(Path(cell["run"]) / "preregistration.json")
            if child["model"]["id"] != cell["model_id"] or child["model"]["sha256"] != cell["model_sha256"]:
                raise ValueError("child model identity mismatch")
            if child["model_inventory_sha256"] != protocol["frozen_files"][cell["run_command"][cell["run_command"].index("--model-inventory") + 1]]:
                raise ValueError("child inventory identity mismatch")
            if child["runtime"]["executable_sha256"] != protocol["runtime"]["executable_sha256"]:
                raise ValueError("child runtime identity mismatch")
            verify_child_run(protocol, cell)
            invoke(cell["score_command"], output / "logs" / (cell["id"] + ".score.log"))
            verify_hashes(ledger["artifacts"])
            verify_hashes(protocol["frozen_files"])
            summary = read(Path(cell["score"]) / "summary.json")
            validate_summary(summary, cell, protocol["candidates"][cell["benchmark_id"]]["items"])
            row.update(status="scored", summary=summary,
                       score_artifacts=hashes(p for p in Path(cell["score"]).rglob("*") if p.is_file()))
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
            row["error"] = str(exc)
        rows.append(row)
    write(output / "matrix-results.json", {"format": "exactscope.v1-grounding-matrix-results", "format_version": "0.1",
        "preregistration_sha256": digest, "cell_count": 60, "scored_cells": sum(r["status"] == "scored" for r in rows), "cells": rows})
    with (output / "matrix-results.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "model_id", "benchmark_id", "status", "error", "summary"])
        writer.writeheader()
        for row in rows:
            writer.writerow({**{k: row[k] for k in ("id", "model_id", "benchmark_id", "status", "error")},
                             "summary": json.dumps(row["summary"], sort_keys=True, allow_nan=False) if row["summary"] else ""})
    write(output / "checksums.json", hashes(p for p in output.rglob("*") if p.is_file()))
    return all(row["status"] == "scored" for row in rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="phase", required=True)
    run = sub.add_parser("run")
    run.add_argument("--matrix", type=Path, default=ROOT / "benchmarks/v1-model-matrix-20.json")
    run.add_argument("--suite", type=Path, default=ROOT / "benchmarks/v1-public-benchmark-suite.json")
    run.add_argument("--acquisition-manifest", type=Path, default=ROOT / "target/v1-20-model-acquisition.json")
    run.add_argument("--model-inventory", type=Path, required=True)
    run.add_argument("--runtime-executable", type=Path, required=True)
    run.add_argument("--runtime-record", type=Path)
    run.add_argument("--port", type=int, default=18801)
    run.add_argument("--threads", type=int, default=6)
    run.add_argument("--workers", type=int, default=1,
                     help="model groups in parallel; each model's three benchmark cells remain sequential")
    run.add_argument("--output", type=Path, required=True)
    score = sub.add_parser("score")
    score.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        return 0 if (run_matrix(args) if args.phase == "run" else score_matrix(args.output)) else 1
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        print(f"grounding matrix: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
