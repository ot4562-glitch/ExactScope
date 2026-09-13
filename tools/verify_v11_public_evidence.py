#!/usr/bin/env python3
"""Verify the tracked ExactScope v1.1 public-development evidence snapshot.

This verifier intentionally needs no model files and no local target/ artifacts. It
checks the public snapshot's model identity set, A/G arithmetic, aggregate means,
negative/N/A accounting, protocol invariants, and claim boundary. The snapshot
binds the original local panel by SHA-256 but is not a substitute for enterprise
qualification or an independent reproduction of the model runs.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "benchmarks/v1.1-final-public-evidence.json"
INVENTORY = ROOT / "benchmarks/v1-grounding-model-inventory-20.json"
TASKS = ("natural_questions", "hotpotqa")
SHA_RE = re.compile(r"^[a-f0-9]{64}$")
EPS = 1e-12


class EvidenceError(RuntimeError):
    pass


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"cannot read JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"JSON root must be object: {path}")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def _close(actual: float, expected: float, label: str, *, tolerance: float = EPS) -> None:
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance):
        raise EvidenceError(f"{label}: {actual} != {expected}")


def _task_rows(models: list[dict[str, Any]], task: str) -> list[dict[str, Any]]:
    return [model[task] for model in models]


def _recompute_task(models: list[dict[str, Any]], task: str) -> dict[str, Any]:
    pairs: list[tuple[float, float, float]] = []
    for model in models:
        row = model[task]
        status = row.get("status")
        _require(status in {"scored", "n_a"}, f"{model['model_id']}/{task}: invalid status")
        if status == "n_a":
            _require(isinstance(row.get("reason_code"), str) and row["reason_code"], f"{model['model_id']}/{task}: N/A lacks reason")
            _require(not ({"a_f1", "g_f1", "uplift_pp"} & set(row)), f"{model['model_id']}/{task}: N/A carries score fields")
            continue
        _require(set(("a_f1", "g_f1", "uplift_pp")) <= set(row), f"{model['model_id']}/{task}: scored row lacks metrics")
        a = row["a_f1"]
        g = row["g_f1"]
        uplift = row["uplift_pp"]
        _require(type(a) in {int, float} and type(g) in {int, float} and type(uplift) in {int, float}, f"{model['model_id']}/{task}: nonnumeric metric")
        _require(0.0 <= float(a) <= 1.0 and 0.0 <= float(g) <= 1.0, f"{model['model_id']}/{task}: F1 outside [0,1]")
        _close(float(uplift), (float(g) - float(a)) * 100.0, f"{model['model_id']}/{task}: uplift")
        pairs.append((float(a), float(g), float(uplift)))

    uplifts = [item[2] for item in pairs]
    improved = sum(value > EPS for value in uplifts)
    tied = sum(abs(value) <= EPS for value in uplifts)
    regressed = sum(value < -EPS for value in uplifts)
    return {
        "valid_pair_count": len(pairs),
        "mean_a_f1": sum(item[0] for item in pairs) / len(pairs),
        "mean_g_f1": sum(item[1] for item in pairs) / len(pairs),
        "mean_uplift_pp": sum(uplifts) / len(uplifts),
        "improved_tied_regressed": [improved, tied, regressed],
        "uplifts": uplifts,
    }


def verify(evidence: dict[str, Any], inventory: dict[str, Any]) -> dict[str, Any]:
    _require(evidence.get("format") == "exactscope.v11-final-public-evidence", "unexpected evidence format")
    _require(evidence.get("format_version") == "0.1", "unexpected evidence version")
    _require(evidence.get("status") == "public-development-robustness-only", "evidence status drift")
    _require(evidence.get("qualification_eligible") is False, "public evidence cannot be qualification eligible")
    _require(evidence.get("production_readiness_claimed") is False, "public evidence cannot claim production readiness")
    _require(evidence.get("economic_advantage_claimed") is False, "public evidence cannot claim economic advantage")
    for key in ("source_panel_results_sha256", "source_panel_preregistration_sha256"):
        _require(isinstance(evidence.get(key), str) and SHA_RE.fullmatch(evidence[key]) is not None, f"invalid {key}")

    protocol = evidence.get("protocol")
    _require(isinstance(protocol, dict), "protocol missing")
    expected_protocol = {
        "scheduled_models": 20,
        "scheduled_cells": 40,
        "scored_cells": 32,
        "n_a_cells": 8,
        "questions_per_workload": 64,
        "all_serving_attempted_before_scoring": True,
        "retry_count": 0,
        "hidden_repair": False,
        "policy_reselection_from_panel": False,
        "retired_fever_used": False,
    }
    _require(protocol == expected_protocol, "frozen public protocol drift")
    expected_comparison = {
        "A": "same model answering without attached evidence under the frozen runtime/answer surface",
        "G": "same model under the frozen ExactScope evidence and answer-contract path",
        "task_mean_denominator": "16 valid paired model identities; four protocol-incompatible identities are retained as N/A",
        "hotpot_boundary": "A-to-G is model-only-to-H1, not ordinary-RAG-to-H1; it does not establish H1 incremental benefit over ordinary RAG across models",
        "pooled_average": "equal-weight descriptive mean over the 32 valid model-task pairs",
    }
    _require(evidence.get("comparison_definition") == expected_comparison, "A/G comparison definition drift")

    workloads = evidence.get("workloads")
    _require(isinstance(workloads, dict) and set(workloads) == set(TASKS), "workload set drift")
    nq = workloads["natural_questions"]
    hp = workloads["hotpotqa"]
    _require((nq.get("item_count"), nq.get("policy_id"), nq.get("max_evidence_bytes"), nq.get("max_items"), nq.get("top_k")) == (64, "precision-context-v5", 3072, 8, 12), "NQ policy drift")
    _require((hp.get("item_count"), hp.get("host_framework"), hp.get("host_retriever"), hp.get("host_owns_retrieval"), hp.get("attach_policy_id"), hp.get("max_evidence_bytes"), hp.get("max_items"), hp.get("top_k")) == (64, "LlamaIndex", "BM25Retriever", True, "host-ranked-hybrid-h1-v0", 3072, 12, 12), "Hotpot/H1 policy drift")

    models = evidence.get("models")
    _require(isinstance(models, list) and len(models) == 20, "evidence must contain 20 models")
    model_ids = [model.get("model_id") for model in models]
    _require(all(isinstance(model_id, str) and model_id for model_id in model_ids), "invalid model id")
    _require(len(set(model_ids)) == 20, "duplicate model id")

    inventory_records = inventory.get("records")
    _require(isinstance(inventory_records, list) and len(inventory_records) == 20, "20-model inventory drift")
    inventory_ids = {record.get("id") for record in inventory_records if isinstance(record, dict)}
    _require(set(model_ids) == inventory_ids, "public evidence model set differs from frozen inventory")

    recomputed = {task: _recompute_task(models, task) for task in TASKS}
    aggregate = evidence.get("aggregate")
    _require(isinstance(aggregate, dict), "aggregate missing")
    pooled: list[float] = []
    both_means: list[float] = []
    for task in TASKS:
        recorded = aggregate[task]
        actual = recomputed[task]
        _require(recorded.get("scheduled_model_count") == 20, f"{task}: scheduled model count drift")
        _require(recorded.get("valid_pair_count") == actual["valid_pair_count"] == 16, f"{task}: valid-pair count drift")
        _close(float(recorded["mean_a_f1"]), actual["mean_a_f1"], f"{task}: mean A")
        _close(float(recorded["mean_g_f1"]), actual["mean_g_f1"], f"{task}: mean G")
        _close(float(recorded["mean_uplift_pp"]), actual["mean_uplift_pp"], f"{task}: mean uplift")
        _require(recorded.get("improved_tied_regressed") == actual["improved_tied_regressed"], f"{task}: direction counts drift")
        pooled.extend(actual["uplifts"])

    scored_cells = 0
    n_a_cells = 0
    for model in models:
        per_model: list[float] = []
        for task in TASKS:
            row = model[task]
            if row["status"] == "scored":
                scored_cells += 1
                per_model.append(float(row["uplift_pp"]))
            else:
                n_a_cells += 1
        recorded_mean = model.get("two_task_mean_uplift_pp")
        if len(per_model) == 2:
            expected_mean = sum(per_model) / 2.0
            _require(recorded_mean is not None, f"{model['model_id']}: missing two-task mean")
            _close(float(recorded_mean), expected_mean, f"{model['model_id']}: two-task mean")
            both_means.append(expected_mean)
        else:
            _require(recorded_mean is None, f"{model['model_id']}: partial/N/A model has two-task mean")

    _require(scored_cells == protocol["scored_cells"] == 32, "scored-cell count drift")
    _require(n_a_cells == protocol["n_a_cells"] == 8, "N/A-cell count drift")
    _require(len(pooled) == aggregate.get("pooled_valid_cell_count") == 32, "pooled denominator drift")
    _close(float(aggregate["pooled_valid_cell_mean_uplift_pp"]), sum(pooled) / len(pooled), "pooled mean uplift")
    _require(len(both_means) == aggregate.get("models_with_both_tasks") == 16, "both-task model count drift")
    _close(float(aggregate["mean_two_task_uplift_pp_across_models_with_both"]), sum(both_means) / len(both_means), "mean two-task uplift")

    checkpoint = evidence.get("known_h1_three_arm_checkpoint")
    _require(isinstance(checkpoint, dict) and checkpoint.get("model_id") == "qwen35-08b-q4", "H1 checkpoint identity drift")
    qwen = next(model for model in models if model["model_id"] == "qwen35-08b-q4")
    _close(float(checkpoint["model_only_f1"]), float(qwen["hotpotqa"]["a_f1"]), "H1 checkpoint model-only F1")
    _close(float(checkpoint["h1_f1"]), float(qwen["hotpotqa"]["g_f1"]), "H1 checkpoint H1 F1")
    observed_vs_rag_pp = (float(checkpoint["h1_f1"]) - float(checkpoint["ordinary_llamaindex_rag_f1"])) * 100.0
    _close(float(checkpoint["h1_minus_ordinary_rag_f1_pp"]), observed_vs_rag_pp, "H1 vs ordinary RAG F1", tolerance=0.01)
    interval = checkpoint.get("paired_bootstrap_f1_95pct_pp")
    _require(isinstance(interval, list) and len(interval) == 2 and interval[0] < 0 < interval[1], "H1 interval must preserve non-superiority uncertainty")
    _require(checkpoint.get("superiority_claimed") is False, "H1 superiority must not be claimed")

    boundary = evidence.get("claim_boundary")
    _require(isinstance(boundary, list) and len(boundary) >= 4, "claim boundary missing")
    _require(any("not enterprise qualification" in item for item in boundary), "enterprise qualification boundary missing")

    return {
        "status": "PASS",
        "models": len(models),
        "scheduled_cells": protocol["scheduled_cells"],
        "scored_cells": scored_cells,
        "n_a_cells": n_a_cells,
        "nq_mean_uplift_pp": aggregate["natural_questions"]["mean_uplift_pp"],
        "hotpot_mean_uplift_pp": aggregate["hotpotqa"]["mean_uplift_pp"],
        "pooled_mean_uplift_pp": aggregate["pooled_valid_cell_mean_uplift_pp"],
        "source_panel_results_sha256": evidence["source_panel_results_sha256"],
        "source_panel_preregistration_sha256": evidence["source_panel_preregistration_sha256"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=EVIDENCE)
    parser.add_argument("--inventory", type=Path, default=INVENTORY)
    args = parser.parse_args(argv)
    try:
        result = verify(_load(args.evidence), _load(args.inventory))
    except EvidenceError as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
