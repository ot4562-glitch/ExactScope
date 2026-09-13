#!/usr/bin/env python3
"""Freeze, execute, score, aggregate, and render the final v1.1 public A/G panel.

This is publication/robustness evidence only. It runs the frozen v1 20-model
identity over exactly two fixed 64-item public-development workloads:

* NQ: precision-context-v5, 3072 bytes, cap8.
* Hotpot: host-owned LlamaIndex BM25 top12 + host-ranked-hybrid-h1-v0.

The execution is deliberately two-phase: all 40 serving cells are attempted
before any scorer opens gold. Every scheduled model remains visible. A failed
runtime/protocol cell is N/A rather than zero and is never retried. Panel
outcomes may not change the frozen policies.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks"
TOOLS = ROOT / "tools"
BRIDGE = ROOT / "adapters/bridge"
for directory in (BENCH, TOOLS, BRIDGE):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from grounding_preregister import file_sha, resolve_runtime  # noqa: E402
from public_nq_benchmark import verify_serving_candidate  # noqa: E402
from public_hotpot_benchmark import verify_candidate as verify_hotpot_candidate  # noqa: E402
from public_hotpot_h1_benchmark import _load_retrieval as verify_h1_retrieval  # noqa: E402

FORMAT_VERSION = "0.1"
MATRIX = BENCH / "v1-model-matrix-20.json"
ACQUISITION = ROOT / "target/v1-20-model-acquisition.json"
MODEL_INVENTORY = BENCH / "v1-grounding-model-inventory-20.json"
V1_PUBLIC_RESULTS = ROOT / "target/v1-public-matrix-20x6-20260909-r4/matrix-results.json"
NQ_ROOT = ROOT / "target/v11-final-panel-nq64-20260913-r1"
NQ_CANDIDATE = NQ_ROOT / "candidate"
HOTPOT_ROOT = ROOT / "target/llamaindex-h1-stability64-20260913-r1"
HOTPOT_CANDIDATE = HOTPOT_ROOT / "candidate"
HOTPOT_RETRIEVAL_MANIFEST = HOTPOT_ROOT / "host-retrieval/retrieval-manifest.json"
HOTPOT_RETRIEVAL = HOTPOT_ROOT / "host-retrieval/retrieval.jsonl"
H1_WINNER = ROOT / "target/llamaindex-hotpot-three-arm-20260913-r1/hybrid-winner.json"
ASTRA_REVIEW = ROOT / ".ai-bridge/astra-review/h1-full-panel-review-result.md"
NQ_RUNNER = BENCH / "public_nq_benchmark.py"
HOTPOT_RUNNER = BENCH / "public_hotpot_h1_benchmark.py"
GENERATION = BENCH / "grounding-generation-config.json"
POLICY = ROOT / "grounding/reference-profile-v0.1/projection-policy.txt"
README = ROOT / "README.md"
README_START = "<!-- V11_FINAL_PUBLIC_PANEL_START -->"
README_END = "<!-- V11_FINAL_PUBLIC_PANEL_END -->"
TASKS = ("natural_questions", "hotpotqa")
MODEL_COUNT = 20
ITEMS_PER_TASK = 64


class PanelError(RuntimeError):
    pass


def sha(path: Path) -> str:
    return file_sha(path)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PanelError(f"cannot read JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PanelError(f"JSON root must be object: {path}")
    return value


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def platform_path(text: str) -> Path:
    if os.name == "nt" and text.startswith("/mnt/") and len(text) > 6:
        drive = text[5].upper()
        rest = text[7:].replace("/", "\\")
        return Path(f"{drive}:\\{rest}")
    if os.name != "nt" and len(text) >= 3 and text[1] == ":":
        drive = text[0].lower()
        return Path(f"/mnt/{drive}/{text[3:].replace(chr(92), '/')}")
    return Path(text)


def verify_matrix_models() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    matrix = load_json(MATRIX)
    acquisition = load_json(ACQUISITION)
    inventory = load_json(MODEL_INVENTORY)
    policy = matrix.get("selection_policy")
    models = matrix.get("models")
    if matrix.get("format") != "exactscope.v1-model-matrix" or not isinstance(policy, dict) or policy.get("frozen") is not True:
        raise PanelError("20-model matrix is not frozen")
    if not isinstance(models, list) or len(models) != MODEL_COUNT or policy.get("model_count") != MODEL_COUNT:
        raise PanelError("model matrix must contain exactly 20 models")
    if acquisition.get("format") != "exactscope.v1-model-acquisition" or acquisition.get("matrix_sha256") != sha(MATRIX):
        raise PanelError("model acquisition is not bound to matrix")
    acquired = {r.get("id"): r for r in acquisition.get("records", []) if isinstance(r, dict)}
    inv = {r.get("id"): r for r in inventory.get("records", []) if isinstance(r, dict)}
    if len(acquired) != MODEL_COUNT or len(inv) != MODEL_COUNT:
        raise PanelError("acquisition/inventory model count drift")
    ordered: list[dict[str, Any]] = []
    paths: dict[str, dict[str, Any]] = {}
    for spec in models:
        model_id = spec.get("id")
        if not isinstance(model_id, str) or model_id not in acquired or model_id not in inv:
            raise PanelError(f"model identity missing: {model_id}")
        a = acquired[model_id]
        i = inv[model_id]
        expected_sha = spec.get("upstream_sha256")
        for field in ("repository", "resolved_revision", "requested_file", "quantization", "bytes"):
            if a.get(field) != spec.get(field):
                raise PanelError(f"acquisition identity drift: {model_id}/{field}")
        if a.get("sha256") != expected_sha or i.get("sha256") != expected_sha or i.get("bytes") != spec.get("bytes"):
            raise PanelError(f"model inventory digest/size drift: {model_id}")
        local = platform_path(str(a.get("path", ""))).resolve()
        if not local.is_file() or local.stat().st_size != spec.get("bytes"):
            raise PanelError(f"model file missing/size drift: {model_id}: {local}")
        actual_sha = sha(local)
        if actual_sha != expected_sha:
            raise PanelError(f"model file sha256 drift: {model_id}")
        row = dict(spec)
        row["path"] = str(local)
        ordered.append(row)
        paths[model_id] = {"path": str(local), "sha256": actual_sha, "bytes": local.stat().st_size}
    return ordered, paths


def verify_cohorts() -> dict[str, Any]:
    nq_manifest, nq_questions, _chunks, _corpus = verify_serving_candidate(NQ_CANDIDATE)
    if nq_manifest.get("search_item_count") != ITEMS_PER_TASK or len(nq_questions) != ITEMS_PER_TASK:
        raise PanelError("final NQ cohort is not 64 items")
    nq_selection = load_json(NQ_ROOT / "selection-freeze.json")
    if nq_selection.get("policy_frozen_before_membership") is not True or nq_selection.get("panel_role") != "final-publication-robustness":
        raise PanelError("final NQ membership was not frozen under final policy")
    if nq_selection.get("policy") != {"id": "precision-context-v5", "max_bytes": 3072, "max_items": 8, "top_k": 12}:
        raise PanelError("final NQ policy drift")

    hotpot_manifest, hotpot_questions, _corpus = verify_hotpot_candidate(HOTPOT_CANDIDATE, include_gold=False)
    if hotpot_manifest.get("item_count") != ITEMS_PER_TASK or len(hotpot_questions) != ITEMS_PER_TASK:
        raise PanelError("final Hotpot cohort is not 64 items")
    retrieval_manifest, retrieval_rows = verify_h1_retrieval(HOTPOT_CANDIDATE, HOTPOT_RETRIEVAL_MANIFEST, HOTPOT_RETRIEVAL)
    if len(retrieval_rows) != ITEMS_PER_TASK or retrieval_manifest.get("top_k") != 12:
        raise PanelError("Hotpot frozen host retrieval drift")
    h1 = load_json(H1_WINNER)
    if h1.get("winner_id") != "host-ranked-hybrid-h1-v0" or h1.get("no_validation_reselection") is not True:
        raise PanelError("H1 frozen winner identity drift")
    return {
        "natural_questions": {
            "candidate": str(NQ_CANDIDATE.resolve()),
            "selection_sha256": sha(NQ_ROOT / "selection-freeze.json"),
            "serving_manifest_sha256": sha(NQ_CANDIDATE / "serving/manifest.json"),
            "question_count": len(nq_questions),
            "policy": {"id": "precision-context-v5", "max_bytes": 3072, "max_items": 8, "top_k": 12},
        },
        "hotpotqa": {
            "candidate": str(HOTPOT_CANDIDATE.resolve()),
            "selection_sha256": sha(HOTPOT_ROOT / "selection-freeze.json"),
            "candidate_manifest_sha256": sha(HOTPOT_CANDIDATE / "manifest.json"),
            "retrieval_manifest": str(HOTPOT_RETRIEVAL_MANIFEST.resolve()),
            "retrieval_manifest_sha256": sha(HOTPOT_RETRIEVAL_MANIFEST),
            "retrieval": str(HOTPOT_RETRIEVAL.resolve()),
            "retrieval_sha256": sha(HOTPOT_RETRIEVAL),
            "question_count": len(hotpot_questions),
            "policy": {"id": "host-ranked-hybrid-h1-v0", "max_bytes": 3072, "max_items": 12, "top_k": 12, "full_ranked_documents": 1, "prompt_profile": "no-policy"},
            "winner_sha256": sha(H1_WINNER),
        },
    }


def small_frozen_files(runtime_record: Path, runtime_executable: Path) -> dict[str, str]:
    files = [
        Path(__file__).resolve(),
        NQ_RUNNER.resolve(),
        HOTPOT_RUNNER.resolve(),
        (BENCH / "run_grounding_benchmark.py").resolve(),
        (TOOLS / "grounding_projection.py").resolve(),
        (TOOLS / "grounding_text.py").resolve(),
        (TOOLS / "grounding_v1_surface.py").resolve(),
        (TOOLS / "grounding_answer_contract.py").resolve(),
        (BRIDGE / "ranked_hits.py").resolve(),
        MATRIX.resolve(), ACQUISITION.resolve(), MODEL_INVENTORY.resolve(),
        V1_PUBLIC_RESULTS.resolve(), GENERATION.resolve(), POLICY.resolve(),
        (NQ_ROOT / "selection-freeze.json").resolve(),
        (NQ_ROOT / "protocol.json").resolve(),
        (NQ_CANDIDATE / "serving/manifest.json").resolve(),
        (NQ_CANDIDATE / "serving/questions.jsonl").resolve(),
        (NQ_CANDIDATE / "serving/chunks.jsonl").resolve(),
        (NQ_CANDIDATE / "serving/corpus-index.json").resolve(),
        (NQ_CANDIDATE / "gold/manifest.json").resolve(),
        (NQ_CANDIDATE / "gold/items.jsonl").resolve(),
        (HOTPOT_ROOT / "selection-freeze.json").resolve(),
        (HOTPOT_ROOT / "protocol.json").resolve(),
        (HOTPOT_CANDIDATE / "manifest.json").resolve(),
        (HOTPOT_CANDIDATE / "serving/questions.jsonl").resolve(),
        (HOTPOT_CANDIDATE / "serving/corpus-index.json").resolve(),
        (HOTPOT_CANDIDATE / "gold/answers.jsonl").resolve(),
        HOTPOT_RETRIEVAL_MANIFEST.resolve(), HOTPOT_RETRIEVAL.resolve(), H1_WINNER.resolve(),
        ASTRA_REVIEW.resolve(), runtime_record.resolve(), runtime_executable.resolve(),
    ]
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise PanelError("frozen panel input missing: " + ", ".join(missing))
    return {str(path): sha(path) for path in files}


def make_cells(output: Path, models: list[dict[str, Any]], runtime_record: Path, runtime_executable: Path, port_base: int, threads: int) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    python = str(Path(sys.executable).resolve())
    for model_index, model in enumerate(models):
        model_id = model["id"]
        model_path = model["path"]
        for task_index, task in enumerate(TASKS):
            cell_index = model_index * len(TASKS) + task_index
            port = port_base + cell_index
            cell_id = f"{model_id}--{task}"
            run_dir = output / "cells" / cell_id
            score_dir = output / "scores" / cell_id
            if task == "natural_questions":
                run_command = [
                    python, str(NQ_RUNNER.resolve()), "run",
                    "--candidate", str(NQ_CANDIDATE.resolve()),
                    "--model-id", model_id,
                    "--model-path", model_path,
                    "--model-inventory", str(MODEL_INVENTORY.resolve()),
                    "--runtime-record", str(runtime_record.resolve()),
                    "--runtime-executable", str(runtime_executable.resolve()),
                    "--output", str(run_dir.resolve()),
                    "--port", str(port), "--threads", str(threads),
                    "--top-k", "12", "--max-evidence-bytes", "3072",
                ]
                score_command = [
                    python, str(NQ_RUNNER.resolve()), "score",
                    "--candidate", str(NQ_CANDIDATE.resolve()),
                    "--run", str(run_dir.resolve()),
                    "--output", str(score_dir.resolve()),
                ]
            else:
                run_command = [
                    python, str(HOTPOT_RUNNER.resolve()), "run",
                    "--candidate", str(HOTPOT_CANDIDATE.resolve()),
                    "--retrieval-manifest", str(HOTPOT_RETRIEVAL_MANIFEST.resolve()),
                    "--retrieval", str(HOTPOT_RETRIEVAL.resolve()),
                    "--model-id", model_id,
                    "--model-path", model_path,
                    "--model-inventory", str(MODEL_INVENTORY.resolve()),
                    "--runtime-record", str(runtime_record.resolve()),
                    "--runtime-executable", str(runtime_executable.resolve()),
                    "--output", str(run_dir.resolve()),
                    "--port", str(port), "--threads", str(threads),
                ]
                score_command = [
                    python, str(HOTPOT_RUNNER.resolve()), "score",
                    "--candidate", str(HOTPOT_CANDIDATE.resolve()),
                    "--retrieval-manifest", str(HOTPOT_RETRIEVAL_MANIFEST.resolve()),
                    "--retrieval", str(HOTPOT_RETRIEVAL.resolve()),
                    "--run", str(run_dir.resolve()),
                    "--output", str(score_dir.resolve()),
                ]
            cells.append({
                "id": cell_id, "model_id": model_id, "task": task,
                "model_sha256": model["upstream_sha256"], "model_path": model_path,
                "port": port, "run": str(run_dir.resolve()), "score": str(score_dir.resolve()),
                "run_command": run_command, "score_command": score_command,
            })
    return cells


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    if output.exists():
        raise PanelError("panel output exists; overwrite/resume forbidden")
    if not 1024 <= args.port_base <= 65496 or args.threads < 1:
        raise PanelError("invalid runtime port/thread settings")
    models, model_files = verify_matrix_models()
    cohorts = verify_cohorts()
    runtime_sha, runtime = resolve_runtime(args.runtime_record, args.runtime_executable)
    v1 = load_json(V1_PUBLIC_RESULTS)
    if v1.get("format") != "exactscope.v1-public-matrix-results" or v1.get("scheduled_models") != MODEL_COUNT:
        raise PanelError("historical v1 Public-6 result identity drift")
    frozen = small_frozen_files(args.runtime_record, args.runtime_executable)
    cells = make_cells(output, models, args.runtime_record, args.runtime_executable, args.port_base, args.threads)
    protocol = {
        "format": "exactscope.v11-final-public-matrix-preregistration",
        "format_version": FORMAT_VERSION,
        "state": "frozen-before-panel-inference",
        "publication_robustness_only": True,
        "qualification_eligible": False,
        "policy_reselection_from_panel_forbidden": True,
        "retired_fever_used": False,
        "model_count": MODEL_COUNT,
        "task_count": len(TASKS),
        "scheduled_cells": len(cells),
        "items_per_task": ITEMS_PER_TASK,
        "model_matrix_sha256": sha(MATRIX),
        "acquisition_sha256": sha(ACQUISITION),
        "model_inventory_sha256": sha(MODEL_INVENTORY),
        "model_files": model_files,
        "cohorts": cohorts,
        "runtime_record_sha256": runtime_sha,
        "runtime": runtime,
        "generation_config_sha256": sha(GENERATION),
        "model_surface_source_sha256": sha(TOOLS / "grounding_v1_surface.py"),
        "answer_contract_source_sha256": sha(TOOLS / "grounding_answer_contract.py"),
        "nq_runner_sha256": sha(NQ_RUNNER),
        "hotpot_h1_runner_sha256": sha(HOTPOT_RUNNER),
        "h1_projector_source_sha256": sha(BRIDGE / "ranked_hits.py"),
        "orchestrator_sha256": sha(Path(__file__)),
        "astra_review_sha256": sha(ASTRA_REVIEW),
        "v1_public_results_sha256": sha(V1_PUBLIC_RESULTS),
        "v1_public_results_reused_not_rerun": True,
        "qwen_hotpot_disclosure": {
            "prior_stability64_result_known": True,
            "panel_policy": "execute exactly one new panel serving run; do not reuse or select between prior/new Qwen outputs",
        },
        "serving_then_scoring": "all 40 serving cells attempted before any score command",
        "retry_count": 0,
        "hidden_repair": False,
        "failure_policy": {
            "runtime_or_protocol_failure": "reason-coded N/A; never converted to zero; no retry",
            "scoreable_model_answer_failure": "counted by frozen task scorer, including format failures",
            "all_scheduled_models_reported": True,
        },
        "averaging_rule": {
            "task_aggregate": "arithmetic mean of observed A, G, and G-A over valid paired scored cells for that task; denominator reported",
            "per_model_two_task_mean_uplift": "reported only when both NQ and Hotpot have valid paired scored results; otherwise N/A",
            "pooled_cell_uplift": "descriptive arithmetic mean over every valid paired task cell; denominator reported",
            "not_population_estimate": True,
        },
        "readme_claim_boundary": [
            "observed public-development A->G percentage-point effects only",
            "average uplift is descriptive, not a population estimate or guarantee",
            "Hotpot A/G does not establish H1 incremental benefit over ordinary RAG across models",
            "not enterprise qualification, production readiness, or economic/latency advantage",
        ],
        "small_frozen_files": frozen,
        "models": [{k: m[k] for k in ("id", "family", "parameters", "repository", "requested_file", "quantization", "bytes", "upstream_sha256", "path")} for m in models],
        "cells": cells,
    }
    output.mkdir(parents=True)
    atomic_json(output / "panel-preregistration.json", protocol)
    atomic_json(output / "panel-status.json", {
        "format": "exactscope.v11-final-public-matrix-status", "format_version": FORMAT_VERSION,
        "state": "prepared", "phase": "prepared", "scheduled_cells": len(cells),
        "preregistration_sha256": sha(output / "panel-preregistration.json"),
    })
    return protocol


def verify_protocol(output: Path, *, verify_models: bool = False) -> dict[str, Any]:
    protocol_path = output / "panel-preregistration.json"
    protocol = load_json(protocol_path)
    if protocol.get("format") != "exactscope.v11-final-public-matrix-preregistration" or protocol.get("state") != "frozen-before-panel-inference":
        raise PanelError("invalid panel preregistration")
    if protocol.get("orchestrator_sha256") != sha(Path(__file__)):
        raise PanelError("orchestrator source drift after freeze")
    for name, expected in protocol.get("small_frozen_files", {}).items():
        path = Path(name)
        if not path.is_file() or sha(path) != expected:
            raise PanelError(f"small frozen input drift: {name}")
    if verify_models:
        for model_id, identity in protocol["model_files"].items():
            path = Path(identity["path"])
            if not path.is_file() or path.stat().st_size != identity["bytes"] or sha(path) != identity["sha256"]:
                raise PanelError(f"frozen model file drift: {model_id}")
    if len(protocol.get("cells", [])) != MODEL_COUNT * len(TASKS):
        raise PanelError("panel cell count drift")
    return protocol


def invoke(command: list[str], log: Path) -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("xb") as handle:
        completed = subprocess.run(command, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT, check=False)
    return int(completed.returncode)


def run_serving(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    protocol = verify_protocol(output, verify_models=True)
    ledger_path = output / "serving-ledger.json"
    if ledger_path.exists() or (output / "scores").exists():
        raise PanelError("serving already attempted or score directory exists; resume/reuse forbidden")
    (output / "logs").mkdir(exist_ok=False)
    (output / "cells").mkdir(exist_ok=False)
    rows: list[dict[str, Any]] = []
    atomic_json(output / "panel-status.json", {
        "format": "exactscope.v11-final-public-matrix-status", "format_version": FORMAT_VERSION,
        "state": "running", "phase": "serving", "scheduled_cells": len(protocol["cells"]),
        "completed_cells": 0, "failed_cells": 0, "preregistration_sha256": sha(output / "panel-preregistration.json"),
    })
    model_verified: set[str] = set()
    for index, cell in enumerate(protocol["cells"]):
        entry = {"id": cell["id"], "model_id": cell["model_id"], "task": cell["task"], "status": "serving_failed", "reason": None}
        try:
            verify_protocol(output, verify_models=False)
            if cell["model_id"] not in model_verified:
                identity = protocol["model_files"][cell["model_id"]]
                path = Path(identity["path"])
                if not path.is_file() or path.stat().st_size != identity["bytes"] or sha(path) != identity["sha256"]:
                    raise PanelError("model file drift immediately before serving")
                model_verified.add(cell["model_id"])
            returncode = invoke(cell["run_command"], output / "logs" / f"{cell['id']}.serve.log")
            if returncode != 0:
                raise PanelError(f"serving child exit code {returncode}")
            run_dir = Path(cell["run"])
            status_path = run_dir / "run-status.json"
            if not status_path.is_file():
                raise PanelError("serving child omitted run-status.json")
            child = load_json(status_path)
            if child.get("state") != "complete" or child.get("record_count") != ITEMS_PER_TASK * 2:
                raise PanelError("serving child incomplete")
            entry.update(status="served", reason=None, run_status_sha256=sha(status_path), raw_results_sha256=sha(run_dir / "raw-results.jsonl"))
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
            entry["reason"] = str(exc)
        rows.append(entry)
        atomic_json(ledger_path, {
            "format": "exactscope.v11-final-public-serving-ledger", "format_version": FORMAT_VERSION,
            "complete": False, "attempted": len(rows), "scheduled": len(protocol["cells"]), "rows": rows,
        })
        atomic_json(output / "panel-status.json", {
            "format": "exactscope.v11-final-public-matrix-status", "format_version": FORMAT_VERSION,
            "state": "running", "phase": "serving", "scheduled_cells": len(protocol["cells"]),
            "attempted_cells": len(rows), "completed_cells": sum(r["status"] == "served" for r in rows),
            "failed_cells": sum(r["status"] != "served" for r in rows),
            "last_cell": cell["id"], "preregistration_sha256": sha(output / "panel-preregistration.json"),
        })
    ledger = {
        "format": "exactscope.v11-final-public-serving-ledger", "format_version": FORMAT_VERSION,
        "complete": True, "attempted": len(rows), "scheduled": len(protocol["cells"]), "rows": rows,
    }
    atomic_json(ledger_path, ledger)
    atomic_json(output / "panel-status.json", {
        "format": "exactscope.v11-final-public-matrix-status", "format_version": FORMAT_VERSION,
        "state": "serving_complete", "phase": "serving_complete", "scheduled_cells": len(rows),
        "completed_cells": sum(r["status"] == "served" for r in rows), "failed_cells": sum(r["status"] != "served" for r in rows),
        "serving_ledger_sha256": sha(ledger_path), "preregistration_sha256": sha(output / "panel-preregistration.json"),
        "scoring_started": False,
    })
    return ledger


def _score_summary(task: str, score_dir: Path) -> dict[str, Any]:
    summary = load_json(score_dir / "summary.json")
    expected = "exactscope.public-nq-summary" if task == "natural_questions" else "exactscope.public-hotpot-h1-summary"
    if summary.get("format") != expected or summary.get("item_count") != ITEMS_PER_TASK:
        raise PanelError(f"score summary identity drift: {task}")
    arms = summary.get("arms")
    if not isinstance(arms, dict) or set(arms) != {"A", "G"}:
        raise PanelError(f"score arm drift: {task}")
    return summary


def aggregate(protocol: dict[str, Any], serving_rows: list[dict[str, Any]], score_rows: list[dict[str, Any]]) -> dict[str, Any]:
    matrix = load_json(MATRIX)
    v1 = load_json(V1_PUBLIC_RESULTS)
    v1_by_id = {row["model_id"]: row for row in v1["models"]}
    serve_by_id = {row["id"]: row for row in serving_rows}
    score_by_id = {row["id"]: row for row in score_rows}
    model_results: list[dict[str, Any]] = []
    task_values: dict[str, list[tuple[float, float]]] = {task: [] for task in TASKS}
    pooled_uplifts: list[float] = []

    for model in matrix["models"]:
        model_id = model["id"]
        row: dict[str, Any] = {
            "model_id": model_id, "family": model["family"], "parameters": model["parameters"],
            "v1_public6_macro": v1_by_id[model_id].get("macro_accuracy") if v1_by_id[model_id].get("status") == "completed" else None,
            "v1_public6_status": v1_by_id[model_id].get("status"),
            "tasks": {}, "two_task_mean_uplift_pp": None,
        }
        uplifts: list[float] = []
        for task in TASKS:
            cell_id = f"{model_id}--{task}"
            served = serve_by_id[cell_id]
            scored = score_by_id[cell_id]
            task_row: dict[str, Any] = {"status": scored["status"], "reason": scored.get("reason") or served.get("reason")}
            if scored["status"] == "scored":
                score_dir = Path(protocol["cells"][[c["id"] for c in protocol["cells"]].index(cell_id)]["score"])
                summary = _score_summary(task, score_dir)
                a = summary["arms"]["A"]
                g = summary["arms"]["G"]
                uplift = (g["f1"] - a["f1"]) * 100.0
                task_row.update({
                    "a_f1": a["f1"], "g_f1": g["f1"], "f1_uplift_pp": uplift,
                    "a_exact_match": a["exact_match"], "g_exact_match": g["exact_match"],
                    "exact_match_uplift_pp": (g["exact_match"] - a["exact_match"]) * 100.0,
                    "a_format_failure_rate": a["format_failure_rate"], "g_format_failure_rate": g["format_failure_rate"],
                    "g_mean_input_tokens": g.get("mean_input_tokens"), "g_mean_evidence_bytes": g.get("mean_evidence_bytes"),
                })
                task_values[task].append((a["f1"], g["f1"]))
                pooled_uplifts.append(uplift)
                uplifts.append(uplift)
            row["tasks"][task] = task_row
        if len(uplifts) == len(TASKS):
            row["two_task_mean_uplift_pp"] = sum(uplifts) / len(uplifts)
        model_results.append(row)

    task_aggregate: dict[str, Any] = {}
    for task, pairs in task_values.items():
        uplifts = [(g - a) * 100.0 for a, g in pairs]
        task_aggregate[task] = {
            "valid_pair_count": len(pairs), "scheduled_model_count": MODEL_COUNT,
            "mean_a_f1": sum(a for a, _g in pairs) / len(pairs) if pairs else None,
            "mean_g_f1": sum(g for _a, g in pairs) / len(pairs) if pairs else None,
            "mean_uplift_pp": sum(uplifts) / len(uplifts) if uplifts else None,
            "improved_tied_regressed": [
                sum(x > 1e-12 for x in uplifts), sum(abs(x) <= 1e-12 for x in uplifts), sum(x < -1e-12 for x in uplifts)
            ],
        }
    both = [row["two_task_mean_uplift_pp"] for row in model_results if row["two_task_mean_uplift_pp"] is not None]
    return {
        "format": "exactscope.v11-final-public-matrix-results", "format_version": FORMAT_VERSION,
        "publication_robustness_only": True, "qualification_eligible": False,
        "scheduled_models": MODEL_COUNT, "scheduled_cells": MODEL_COUNT * len(TASKS),
        "scored_cells": len(pooled_uplifts), "n_a_cells": MODEL_COUNT * len(TASKS) - len(pooled_uplifts),
        "models_with_both_tasks": len(both),
        "task_aggregate": task_aggregate,
        "pooled_valid_cell_mean_uplift_pp": sum(pooled_uplifts) / len(pooled_uplifts) if pooled_uplifts else None,
        "pooled_valid_cell_count": len(pooled_uplifts),
        "mean_two_task_uplift_pp_across_models_with_both": sum(both) / len(both) if both else None,
        "models": model_results,
        "claim_boundary": protocol["readme_claim_boundary"],
        "qwen_hotpot_prior_result_known": True,
        "retired_fever_used": False,
    }


def fmt_pct(value: float | None, digits: int = 2) -> str:
    return "N/A" if value is None else f"{value * 100:.{digits}f}%"


def fmt_pp(value: float | None, digits: int = 2) -> str:
    return "N/A" if value is None else f"{value:+.{digits}f}pp"


def task_cell(task: dict[str, Any]) -> str:
    if task.get("status") != "scored":
        return "N/A"
    return f"{fmt_pct(task['a_f1'])}→{fmt_pct(task['g_f1'])} (**{fmt_pp(task['f1_uplift_pp'])}**)"


def render_markdown(results: dict[str, Any]) -> str:
    nq = results["task_aggregate"]["natural_questions"]
    hp = results["task_aggregate"]["hotpotqa"]
    lines = [
        "### v1.1 candidate: frozen 20-model A/G robustness panel",
        "",
        "The v1.1 candidate was frozen **before** this cross-model panel. These are observed public-development effects, not a population estimate, guarantee, enterprise qualification, or production-readiness claim. FEVER is excluded because its prior held-out is retired. The historical v1 Public-6 capability macro is shown for context and was **not rerun**.",
        "",
        f"- **Natural Questions (fresh post-freeze 64):** valid pairs **{nq['valid_pair_count']}/{MODEL_COUNT}**, mean F1 {fmt_pct(nq['mean_a_f1'])} → **{fmt_pct(nq['mean_g_f1'])}** (**{fmt_pp(nq['mean_uplift_pp'])}**); improved/tied/regressed = **{' / '.join(map(str, nq['improved_tied_regressed']))}**.",
        f"- **HotpotQA + host-owned LlamaIndex BM25/H1 (fixed stability64):** valid pairs **{hp['valid_pair_count']}/{MODEL_COUNT}**, mean F1 {fmt_pct(hp['mean_a_f1'])} → **{fmt_pct(hp['mean_g_f1'])}** (**{fmt_pp(hp['mean_uplift_pp'])}**); improved/tied/regressed = **{' / '.join(map(str, hp['improved_tied_regressed']))}**.",
        f"- Across all valid NQ/Hotpot model-task pairs, descriptive mean uplift = **{fmt_pp(results['pooled_valid_cell_mean_uplift_pp'])}** (n={results['pooled_valid_cell_count']}). A per-model two-task mean is shown only when both task pairs are valid.",
        "",
        "| Model | Params | v1 Public-6 macro | v1.1 NQ F1 A→G | v1.1 Hotpot F1 A→G | Mean uplift (2 tasks) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in results["models"]:
        macro = fmt_pct(row["v1_public6_macro"], 1) if row["v1_public6_macro"] is not None else "N/A"
        mean = fmt_pp(row["two_task_mean_uplift_pp"]) if row["two_task_mean_uplift_pp"] is not None else "N/A"
        lines.append(
            f"| {row['family']} | {row['parameters']} | {macro} | {task_cell(row['tasks']['natural_questions'])} | {task_cell(row['tasks']['hotpotqa'])} | **{mean}** |"
        )
    failures = []
    for row in results["models"]:
        for task in TASKS:
            t = row["tasks"][task]
            if t.get("status") != "scored":
                failures.append(f"- `{row['model_id']}` / `{task}`: **N/A** — {t.get('reason') or 'unclassified panel failure'}")
    lines.extend([
        "",
        "**Interpretation.** On these fixed 64-item public development cohorts, each cell reports the same model as `A → G (+x.xxpp)`. Averages are descriptive over the explicitly reported valid pairs; they are not population estimates and do not guarantee improvement on another workload or model.",
        "",
        "For Qwen3.5 0.8B specifically, the predeclared Hotpot stability64 development screen had already shown H1 over ordinary LlamaIndex RAG by **+5.66pp F1 / +7.81pp EM**, with a paired bootstrap 95% F1 interval of **−4.69pp to +16.25pp**. That earlier result was known before this panel, so the panel is not an independent replication of Qwen. Cross-model A/G does **not** establish H1's incremental benefit over ordinary RAG across all models.",
        "",
        "This panel provides **public-workload robustness evidence only** — not enterprise qualification, production readiness, superiority/noninferiority, or demonstrated economic/latency advantage.",
    ])
    if failures:
        lines.extend(["", "N/A cells are retained explicitly:", ""] + failures)
    return "\n".join(lines) + "\n"


def update_readme(section: str) -> None:
    text = README.read_text(encoding="utf-8")
    replacement = README_START + "\n" + section.rstrip() + "\n" + README_END
    if README_START in text or README_END in text:
        if text.count(README_START) != 1 or text.count(README_END) != 1 or text.index(README_START) > text.index(README_END):
            raise PanelError("README v1.1 panel marker corruption")
        start = text.index(README_START)
        end = text.index(README_END) + len(README_END)
        updated = text[:start] + replacement + text[end:]
    else:
        anchor = "\nImportant boundaries:\n"
        if anchor not in text:
            raise PanelError("README insertion anchor missing")
        updated = text.replace(anchor, "\n" + replacement + "\n\nImportant boundaries:\n", 1)
    tmp = README.with_name("README.md.tmp")
    tmp.write_text(updated, encoding="utf-8")
    os.replace(tmp, README)


def score_and_finalize(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    protocol = verify_protocol(output, verify_models=False)
    serving_ledger = load_json(output / "serving-ledger.json")
    status = load_json(output / "panel-status.json")
    if serving_ledger.get("complete") is not True or serving_ledger.get("attempted") != len(protocol["cells"]):
        raise PanelError("all serving cells must be attempted before scoring")
    if status.get("state") != "serving_complete" or status.get("scoring_started") is not False:
        raise PanelError("panel is not at the scoring boundary")
    if (output / "score-ledger.json").exists() or (output / "panel-results.json").exists():
        raise PanelError("scoring/finalization already attempted; resume/reuse forbidden")
    (output / "scores").mkdir(exist_ok=False)
    serve_by_id = {row["id"]: row for row in serving_ledger["rows"]}
    rows: list[dict[str, Any]] = []
    atomic_json(output / "panel-status.json", {
        "format": "exactscope.v11-final-public-matrix-status", "format_version": FORMAT_VERSION,
        "state": "running", "phase": "scoring", "scheduled_cells": len(protocol["cells"]),
        "scoring_started": True, "scored_cells": 0, "n_a_cells": 0,
        "serving_ledger_sha256": sha(output / "serving-ledger.json"),
        "preregistration_sha256": sha(output / "panel-preregistration.json"),
    })
    for cell in protocol["cells"]:
        served = serve_by_id[cell["id"]]
        entry = {"id": cell["id"], "model_id": cell["model_id"], "task": cell["task"], "status": "n_a", "reason": None}
        if served["status"] != "served":
            entry["reason"] = "serving_failed: " + str(served.get("reason"))
        else:
            try:
                verify_protocol(output, verify_models=False)
                returncode = invoke(cell["score_command"], output / "logs" / f"{cell['id']}.score.log")
                if returncode != 0:
                    raise PanelError(f"scoring child exit code {returncode}")
                score_dir = Path(cell["score"])
                summary = _score_summary(cell["task"], score_dir)
                if summary.get("model_id") != cell["model_id"]:
                    raise PanelError("score model identity drift")
                entry.update(status="scored", reason=None, summary_sha256=sha(score_dir / "summary.json"))
            except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
                entry["reason"] = "score_failed: " + str(exc)
        rows.append(entry)
        atomic_json(output / "score-ledger.json", {
            "format": "exactscope.v11-final-public-score-ledger", "format_version": FORMAT_VERSION,
            "complete": False, "attempted": len(rows), "scheduled": len(protocol["cells"]), "rows": rows,
        })
        atomic_json(output / "panel-status.json", {
            "format": "exactscope.v11-final-public-matrix-status", "format_version": FORMAT_VERSION,
            "state": "running", "phase": "scoring", "scheduled_cells": len(protocol["cells"]),
            "scoring_started": True, "attempted_score_cells": len(rows),
            "scored_cells": sum(r["status"] == "scored" for r in rows), "n_a_cells": sum(r["status"] != "scored" for r in rows),
            "last_cell": cell["id"], "serving_ledger_sha256": sha(output / "serving-ledger.json"),
            "preregistration_sha256": sha(output / "panel-preregistration.json"),
        })
    score_ledger = {
        "format": "exactscope.v11-final-public-score-ledger", "format_version": FORMAT_VERSION,
        "complete": True, "attempted": len(rows), "scheduled": len(protocol["cells"]), "rows": rows,
    }
    atomic_json(output / "score-ledger.json", score_ledger)
    results = aggregate(protocol, serving_ledger["rows"], rows)
    atomic_json(output / "panel-results.json", results)
    with (output / "panel-results.csv").open("x", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["model_id", "family", "parameters", "v1_public6_macro", "nq_status", "nq_a_f1", "nq_g_f1", "nq_uplift_pp", "hotpot_status", "hotpot_a_f1", "hotpot_g_f1", "hotpot_uplift_pp", "two_task_mean_uplift_pp"])
        for row in results["models"]:
            nq = row["tasks"]["natural_questions"]
            hp = row["tasks"]["hotpotqa"]
            writer.writerow([
                row["model_id"], row["family"], row["parameters"], row["v1_public6_macro"],
                nq["status"], nq.get("a_f1"), nq.get("g_f1"), nq.get("f1_uplift_pp"),
                hp["status"], hp.get("a_f1"), hp.get("g_f1"), hp.get("f1_uplift_pp"),
                row["two_task_mean_uplift_pp"],
            ])
    section = render_markdown(results)
    (output / "README_SNIPPET.md").write_text(section, encoding="utf-8")
    update_readme(section)
    atomic_json(output / "panel-status.json", {
        "format": "exactscope.v11-final-public-matrix-status", "format_version": FORMAT_VERSION,
        "state": "complete", "phase": "complete", "scheduled_cells": len(protocol["cells"]),
        "scoring_started": True, "scored_cells": results["scored_cells"], "n_a_cells": results["n_a_cells"],
        "panel_results_sha256": sha(output / "panel-results.json"), "readme_snippet_sha256": sha(output / "README_SNIPPET.md"),
        "score_ledger_sha256": sha(output / "score-ledger.json"), "serving_ledger_sha256": sha(output / "serving-ledger.json"),
        "preregistration_sha256": sha(output / "panel-preregistration.json"),
    })
    checks = {
        p.relative_to(output).as_posix(): sha(p)
        for p in output.rglob("*")
        if p.is_file()
        and p.name != "checksums.json"
        and "detached" not in p.relative_to(output).parts
    }
    atomic_json(output / "checksums.json", checks)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--output", type=Path, required=True)
    prep.add_argument("--runtime-record", type=Path, required=True)
    prep.add_argument("--runtime-executable", type=Path, required=True)
    prep.add_argument("--port-base", type=int, default=19000)
    prep.add_argument("--threads", type=int, default=6)
    run = sub.add_parser("run")
    run.add_argument("--output", type=Path, required=True)
    score = sub.add_parser("score")
    score.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args)
            print(json.dumps({"state": result["state"], "scheduled_cells": result["scheduled_cells"], "output": str(args.output.resolve())}, indent=2))
        elif args.command == "run":
            result = run_serving(args)
            print(json.dumps({"serving_complete": result["complete"], "attempted": result["attempted"], "served": sum(r["status"] == "served" for r in result["rows"])}, indent=2))
        else:
            result = score_and_finalize(args)
            print(json.dumps({"state": "complete", "scored_cells": result["scored_cells"], "n_a_cells": result["n_a_cells"], "pooled_mean_uplift_pp": result["pooled_valid_cell_mean_uplift_pp"]}, indent=2))
        return 0
    except (PanelError, OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        print(f"ExactScope v1.1 final public matrix: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
