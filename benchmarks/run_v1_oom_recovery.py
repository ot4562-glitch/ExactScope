#!/usr/bin/env python3
"""One-shot r2 OOM recovery and separately gated qualification.

In the original WSL environment:
  python3 benchmarks/run_v1_oom_recovery.py run --output NEW --oom-evidence FILE [FILE ...]
  python3 benchmarks/run_v1_oom_recovery.py qualify --recovery NEW --output NEW_QUALIFICATION

An interrupted recovery cannot resume. Keep its evidence and preregister a new
attempt only under a separately reviewed protocol; this controller offers no retry.
"""
from __future__ import annotations

import argparse
import subprocess
import re
from pathlib import Path
import sys

import verify_v1_oom_recovery as v


def fresh(path, *protected):
    path = v.separated(Path(path).absolute(), *protected)
    v.require(not path.exists(), "output exists; no resume/retry/overwrite")
    return path


recovery_cell = v.relocated


def run_command(cell):
    v.require(not any(x in cell["run_command"] for x in ("--resume", "--retry")), "resume/retry forbidden")
    return list(cell["run_command"])


def code_hashes(static_hashes=None):
    root = v.safe(v.native.ROOT)
    expected = (root / "benchmarks/run_v1_oom_recovery.py", root / "benchmarks/verify_v1_oom_recovery.py")
    v.require(v.safe(__file__) == expected[0] and v.safe(v.__file__) == expected[1], "shadow recovery source")
    # Reuse only hashes authenticated in this pass, never a previous barrier.
    authenticated = {} if static_hashes is None else static_hashes
    return {str(path): authenticated[str(path)] if str(path) in authenticated else v.sha(path)
            for path in expected}


def execution_binding(p, static_hashes=None):
    return {"recovery_sources": code_hashes(static_hashes), "interpreter_path": sys.executable,
            "interpreter_resolved": str(Path(sys.executable).resolve()),
            "interpreter_sha256": (v.sha(Path(sys.executable).resolve()) if static_hashes is None
                                   else static_hashes[str(Path(sys.executable).resolve())]),
            "commands": {c["id"]: {key: c[key][:2] for key in ("run_command", "score_command")} for c in p["cells"]}}


def execution_failure(exc):
    # Native invoke raises this exact ValueError for a nonzero child exit.
    return (isinstance(exc, (OSError, subprocess.SubprocessError)) or
            type(exc) is ValueError and re.fullmatch(r"child exit code -?\d+", str(exc)) is not None)


def integrity(p, manifest):
    hashes = v.verify_static_environment(p)
    v.verify_snapshot(p, manifest["snapshot"])
    binding = execution_binding(p, hashes)
    v.require(manifest["execution"] == binding, "recovery execution drift")
    v.require(manifest["source_files"] == binding["recovery_sources"], "recovery source drift")


def run(output, evidence):
    p = v.load_parent(verify_static=False)
    hashes = v.verify_static_environment(p)
    output = fresh(output, *(Path(f) for f in evidence))
    rows = v.partition(p)
    saved = v.snapshot(p, evidence)
    # Validate retention before spending any inference; absent parent completion is explicit.
    for cell, row in zip(p["cells"], rows):
        if row["disposition"] == "retained_completed":
            v.verify_sealed_cell(cell, v.read(v.PARENT / "ledger" / (cell["id"] + ".json")), parent=p)
    v.verify_snapshot(p, saved)
    binding = execution_binding(p, hashes)
    manifest = {"format": "exactscope.v1-oom-recovery", "format_version": "0.1",
                "parent": str(v.PARENT), "parent_preregistration_sha256": v.PARENT_SHA,
                "parent_run_complete_present": bool(saved["completion"]),
                "output": str(output), "workers": 1, "resume": False, "retry_count": 0,
                "attempt": 1, "partition": rows, "snapshot": saved, "source_files": binding["recovery_sources"], "execution": binding}
    output.mkdir(parents=True, exist_ok=False)
    v.write(output / "preregistration.json", manifest)
    v.write(output / "preregistration-checksum.json", {"sha256": v.sha(output / "preregistration.json")})
    (output / "cells").mkdir()
    (output / "ledger").mkdir()
    (output / "logs").mkdir()
    for original, row in zip(p["cells"], rows):
        if row["disposition"] != "recovery":
            continue
        integrity(p, manifest)
        cell = recovery_cell(original, output)
        v.require(not Path(cell["run"]).exists(), "partial output; resume forbidden")
        entry = {"id": cell["id"], "status": "failed", "error": None, "attempt": 1}
        # Seal the attempted command before launch. A process interruption never authorizes resume.
        v.write(output / "logs" / (cell["id"] + ".attempt.json"),
                {"id": cell["id"], "attempt": 1, "command": run_command(cell)})
        error = None
        v.verify_live_model(p, cell)
        try:
            v.native.invoke(run_command(cell), output / "logs" / (cell["id"] + ".run.log"))
        except Exception as exc:
            if not execution_failure(exc):
                raise
            error = f"{type(exc).__name__}: {exc}"
        integrity(p, manifest)
        # A process that fails before creating its child still has an explicit,
        # empty evidence directory; no inference is retried.
        v.safe(cell["run"], output)
        Path(cell["run"]).mkdir(parents=True, exist_ok=True)
        if error is None:
            entry.update(status="completed", artifacts=v.tree(Path(cell["run"])))
            v.verify_sealed_cell(cell, entry, output, parent=p)
        else:
            entry.update(error=error, failure_kind="child_execution", evidence=v.inventory(Path(cell["run"])))
        v.write(output / "ledger" / (cell["id"] + ".json"), entry)
    integrity(p, manifest)
    v.write(output / "run-complete.json", {
        "preregistration_sha256": v.sha(output / "preregistration.json"),
        "ledger": v.inventory(output / "ledger"), "children": v.inventory(output / "cells"),
        "logs": v.inventory(output / "logs")})


def verify_recovery(output):
    output = v.safe(output)
    p = v.load_parent(verify_static=False)
    manifest = v.read(output / "preregistration.json")
    digest = v.sha(output / "preregistration.json")
    v.require(v.read(output / "preregistration-checksum.json") == {"sha256": digest}, "recovery checksum")
    v.require(manifest.get("format") == "exactscope.v1-oom-recovery"
              and manifest.get("format_version") == "0.1"
              and manifest.get("parent") == str(v.PARENT)
              and manifest.get("parent_preregistration_sha256") == v.PARENT_SHA
              and manifest.get("output") == str(output)
              and manifest.get("workers") == 1 and manifest.get("resume") is False
              and manifest.get("retry_count") == 0 and manifest.get("attempt") == 1, "recovery identity/policy")
    v.require(manifest["partition"] == v.partition(p), "partition duplicate/omission/drift")
    v.separated(output, *manifest["snapshot"]["oom"])
    integrity(p, manifest)
    v.require(manifest["parent_run_complete_present"] == bool(manifest["snapshot"]["completion"]), "parent completion claim")
    complete = v.read(v.safe(output / "run-complete.json"))
    v.require(complete["preregistration_sha256"] == digest, "recovery completion identity")
    for name in ("ledger", "children", "logs"):
        directory = "cells" if name == "children" else name
        v.require(complete[name] == v.inventory(output / directory), f"recovery {name} drift")
    recovery_ids = [r["id"] for r in manifest["partition"] if r["disposition"] == "recovery"]
    v.require(set(complete["ledger"]["files"]) == {str(output / "ledger" / (i + ".json")) for i in recovery_ids}, "recovery ledger coverage")
    expected_logs = {str(output / "logs" / (i + suffix)) for i in recovery_ids
                     for suffix in (".attempt.json", ".run.log")}
    v.require(set(complete["logs"]["files"]) == expected_logs, "attempt/log coverage")
    v.require(not complete["ledger"]["directories"] and not complete["logs"]["directories"], "extra control directory")
    v.require({name.split("/")[0] for name in complete["children"]["directories"]} == set(recovery_ids), "exact 22 child directories")
    v.require(all(Path(f).relative_to(output / "cells").parts[0] in recovery_ids
                  for f in complete["children"]["files"]), "unexpected recovery child")
    v.require({x.name for x in output.iterdir()} == {"preregistration.json", "preregistration-checksum.json", "run-complete.json", "cells", "logs", "ledger"}, "extra recovery control artifact")
    verified = []
    for original, row in zip(p["cells"], manifest["partition"]):
        is_recovery = row["disposition"] == "recovery"
        source = output if is_recovery else v.PARENT
        cell = recovery_cell(original, output) if is_recovery else original
        entry = v.read(v.safe(source / "ledger" / (cell["id"] + ".json")))
        v.require(entry.get("id") == cell["id"], "ledger identity")
        if is_recovery:
            attempt = v.read(output / "logs" / (cell["id"] + ".attempt.json"))
            v.require(attempt == {"id": cell["id"], "attempt": 1, "command": run_command(cell)}
                      and entry.get("attempt") == 1, "attempt/command drift")
        result = {**row, "model_id": cell["model_id"], "benchmark_id": cell["benchmark_id"],
                  "benchmark_policy": v.benchmark_policy(p, cell["benchmark_id"]),
                  "metric_status": "N/A", "latency_qualifying": False, "source_run": str(source), "source_child_run": cell["run"],
                  "source_attempt": 1, "verification": {"verified": True, "kind": "terminal_failure"},
                  "score_artifacts": {}, "actual_task_denominators": {"A": 0, "G": 0},
                  "failure": None, "status": "failed"}
        if entry.get("status") == "completed":
            result["verification"] = v.verify_sealed_cell(cell, entry, source, parent=p)
            result["status"] = "verified_completed"
        else:
            v.require(entry.get("status") == "failed" and bool(entry.get("error")), "unsealed failure")
            if is_recovery:
                v.require(entry.get("failure_kind") == "child_execution" and entry.get("evidence") == v.inventory(Path(cell["run"])), "failed evidence drift")
            else:
                v.require(row["disposition"] == "retained_failed" and cell["model_id"] == v.TINY, "retained failure identity")
            result["failure"] = {"kind": "recovery_failure" if is_recovery else "fixed_runtime_protocol_failure",
                                 "error": entry["error"], "terminal": True}
        verified.append((cell, result))
    return p, manifest, verified


def qualify(recovery, output):
    output = fresh(output, recovery)
    # ALL sixty dispositions and all evidence must pass before ANY scorer/gold access.
    p, manifest, verified = verify_recovery(recovery)
    v.separated(output, *manifest["snapshot"]["oom"])
    output.mkdir(parents=True, exist_ok=False)
    (output / "logs").mkdir()
    rows = []
    for cell, row in verified:
        if row["status"] == "verified_completed":
            scoring = v.relocated(cell, Path(row["source_run"]), output)
            score = Path(scoring["score"])
            command = scoring["score_command"]
            verify_recovery(recovery)  # Unconditional, outside score failure handling.
            error = None
            try:
                v.native.invoke(command, output / "logs" / (cell["id"] + ".score.log"))
            except Exception as exc:
                if not execution_failure(exc):
                    raise
                error = str(exc)
            verify_recovery(recovery)  # Even a failing scorer cannot conceal drift.
            artifacts = v.tree(score)
            if error is None:
                summary = v.read(score / "summary.json")
                count = row["verification"]["items_per_arm"]
                try:
                    v.native.validate_summary(summary, cell, count)
                except ValueError as exc:
                    error = str(exc)
            if error is None:
                row.update(status="scored", metric_status="scored", score_artifacts=artifacts,
                           actual_task_denominators={"A": count, "G": count})
            else:
                row.update(status="failed", metric_status="N/A",
                           failure={"kind": "score_failure", "error": error, "terminal": True}, score_artifacts=artifacts)
        rows.append(row)
    # Reject evidence mutation during scoring, too; no qualification seal on failure.
    verify_recovery(recovery)
    scored = sum(r["status"] == "scored" for r in rows)
    failed = sum(r["failure"] is not None for r in rows)
    v.require(len(rows) == scored + failed == 60, "qualification coverage")
    tasks = {}
    for task in v.native.PANEL:
        group = [r for r in rows if r["benchmark_id"] == task]
        tasks[task] = {"expected_cells": len(group), "scored_cells": sum(r["status"] == "scored" for r in group),
                       "failed_cells": sum(r["failure"] is not None for r in group),
                       "scored_model_items": {arm: sum(r["actual_task_denominators"][arm] for r in group) for arm in ("A", "G")},
                       "benchmark_policy": v.benchmark_policy(p, task)}
    v.write(output / "qualification-manifest.json", {
        "format": "exactscope.v1-oom-qualification", "format_version": "0.1",
        "parent_preregistration_sha256": v.PARENT_SHA,
        "parent_run_complete_present": manifest["parent_run_complete_present"],
        "parent_status": "complete_marker_present" if manifest["parent_run_complete_present"] else "interrupted",
        "recovery_preregistration_sha256": v.sha(Path(recovery) / "preregistration.json"),
        "recovery_completion_sha256": v.sha(Path(recovery) / "run-complete.json"),
        "source_files": code_hashes(), "cell_count": 60, "latency_qualifying": False, "tasks": tasks,
        "scored_cells": sum(r["status"] == "scored" for r in rows),
        "explicit_failures": sum(r["failure"] is not None for r in rows),
        "expected_best_case": {"scored": 57, "explicit_failures": 3}, "cells": rows})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="phase", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--output", type=Path, required=True)
    run_parser.add_argument("--oom-evidence", type=Path, nargs="+", required=True)
    score_parser = sub.add_parser("qualify")
    score_parser.add_argument("--recovery", type=Path, required=True)
    score_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.phase == "run":
            run(args.output, args.oom_evidence)
        else:
            qualify(args.recovery, args.output)
        return 0
    except Exception as exc:
        print(f"OOM recovery: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
