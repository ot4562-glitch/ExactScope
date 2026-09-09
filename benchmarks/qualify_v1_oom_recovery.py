#!/usr/bin/env python3
"""Efficient, fail-closed qualification for the sealed v1 OOM recovery evidence.

The recovery controller authenticates the complete 60-cell evidence set before any
gold access. This qualifier preserves that contract while avoiding repeated full-
repository hashing around every scorer: one complete pre-score barrier, score each
verified-completed cell once, then one complete post-score barrier before sealing.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
import sys

import run_v1_oom_recovery as recovery
import verify_v1_oom_recovery as v

FORMAT = "exactscope.v1-oom-qualification"
VERSION = "0.2"


def canonical_verified(verified):
    rows = []
    for cell, row in verified:
        rows.append({
            "id": cell["id"],
            "model_id": cell["model_id"],
            "benchmark_id": cell["benchmark_id"],
            "status": row["status"],
            "metric_status": row["metric_status"],
            "source_run": row["source_run"],
            "source_child_run": row["source_child_run"],
            "source_attempt": row["source_attempt"],
            "verification": copy.deepcopy(row["verification"]),
            "failure": copy.deepcopy(row["failure"]),
            "disposition": row["disposition"],
        })
    return rows


def score_one(cell, row, output):
    result = copy.deepcopy(row)
    if row["status"] != "verified_completed":
        return result
    scoring = v.relocated(cell, Path(row["source_run"]), output)
    score = Path(scoring["score"])
    command = scoring["score_command"]
    error = None
    try:
        v.native.invoke(command, output / "logs" / (cell["id"] + ".score.log"))
    except Exception as exc:
        if not recovery.execution_failure(exc):
            raise
        error = str(exc)
    artifacts = v.tree(score)
    if error is None:
        summary = v.read(score / "summary.json")
        count = row["verification"]["items_per_arm"]
        try:
            v.native.validate_summary(summary, cell, count)
        except ValueError as exc:
            error = str(exc)
    if error is None:
        result.update(
            status="scored",
            metric_status="scored",
            summary=summary,
            score_artifacts=artifacts,
            actual_task_denominators={"A": count, "G": count},
        )
    else:
        result.update(
            status="failed",
            metric_status="N/A",
            failure={"kind": "score_failure", "error": error, "terminal": True},
            score_artifacts=artifacts,
        )
    return result


def aggregate(parent, rows):
    tasks = {}
    for task in v.native.PANEL:
        group = [r for r in rows if r["benchmark_id"] == task]
        scored = [r for r in group if r["status"] == "scored"]
        metrics = ["label_accuracy"] if task == "fever" else ["exact_match", "f1"]
        metric_summary = {}
        for metric in metrics:
            arms = {}
            for arm in ("A", "G"):
                values = [r["summary"]["arms"][arm][metric] for r in scored]
                arms[arm] = sum(values) / len(values) if values else None
            metric_summary[metric] = {
                "A": arms["A"],
                "G": arms["G"],
                "uplift": (arms["G"] - arms["A"] if arms["A"] is not None else None),
            }
        tasks[task] = {
            "expected_cells": len(group),
            "scored_cells": len(scored),
            "failed_cells": sum(r["failure"] is not None for r in group),
            "scored_model_items": {
                arm: sum(r["actual_task_denominators"][arm] for r in group)
                for arm in ("A", "G")
            },
            "benchmark_policy": v.benchmark_policy(parent, task),
            "macro_metrics_across_scored_models": metric_summary,
        }
    return tasks


def qualify(recovery_root, output):
    recovery_root = v.safe(recovery_root)
    output = recovery.fresh(output, recovery_root)

    # Barrier 1: authenticate all sixty dispositions and sealed evidence before any
    # scorer/gold access. This is outside score-failure handling by design.
    parent, recovery_manifest, verified_pre = recovery.verify_recovery(recovery_root)
    pre = canonical_verified(verified_pre)
    v.require(len(pre) == 60, "pre-score qualification coverage")

    output.mkdir(parents=True, exist_ok=False)
    (output / "logs").mkdir()
    source_sha = v.sha(Path(__file__).resolve())
    prereg = {
        "format": "exactscope.v1-oom-qualification-preregistration",
        "format_version": VERSION,
        "recovery": str(recovery_root),
        "output": str(output),
        "source_sha256": source_sha,
        "gold_policy": "no scorer/gold access before complete pre-score recovery verification",
        "integrity_policy": "complete global pre-score barrier, score verified-completed cells once, complete global post-score barrier before seal",
        "resume": False,
        "retry_count": 0,
        "cell_count": 60,
        "pre_score_dispositions": pre,
    }
    v.write(output / "preregistration.json", prereg)
    v.write(output / "preregistration-checksum.json", {"sha256": v.sha(output / "preregistration.json")})

    rows = [score_one(cell, row, output) for cell, row in verified_pre]

    # Barrier 2: evidence must still authenticate after all scoring. A failure leaves
    # an unsealed, non-resumable partial qualification directory.
    _, _, verified_post = recovery.verify_recovery(recovery_root)
    post = canonical_verified(verified_post)
    v.require(pre == post, "pre/post recovery verification drift")
    v.require(v.sha(Path(__file__).resolve()) == source_sha, "qualification source drift")

    scored = sum(r["status"] == "scored" for r in rows)
    failed = sum(r["failure"] is not None for r in rows)
    v.require(len(rows) == scored + failed == 60, "qualification coverage")

    tasks = aggregate(parent, rows)
    manifest = {
        "format": FORMAT,
        "format_version": VERSION,
        "parent_preregistration_sha256": v.PARENT_SHA,
        "parent_run_complete_present": recovery_manifest["parent_run_complete_present"],
        "parent_status": "complete_marker_present" if recovery_manifest["parent_run_complete_present"] else "interrupted",
        "recovery_preregistration_sha256": v.sha(recovery_root / "preregistration.json"),
        "recovery_completion_sha256": v.sha(recovery_root / "run-complete.json"),
        "qualification_preregistration_sha256": v.sha(output / "preregistration.json"),
        "qualification_source_sha256": source_sha,
        "cell_count": 60,
        "latency_qualifying": False,
        "scored_cells": scored,
        "explicit_failures": failed,
        "tasks": tasks,
        "cells": rows,
    }
    for task in tasks.values():
        for metrics in task["macro_metrics_across_scored_models"].values():
            for value in metrics.values():
                v.require(value is None or (isinstance(value, (int, float)) and math.isfinite(value)), "nonfinite aggregate")
    v.write(output / "qualification-manifest.json", manifest)
    v.write(output / "checksums.json", v.tree(output))
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recovery", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        manifest = qualify(args.recovery, args.output)
        print(json.dumps({
            "status": "PASS",
            "scored_cells": manifest["scored_cells"],
            "explicit_failures": manifest["explicit_failures"],
        }, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"OOM qualification v0.2: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
