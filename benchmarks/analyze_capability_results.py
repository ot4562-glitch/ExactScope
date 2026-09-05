#!/usr/bin/env python3
"""Derive failure classes from immutable capability-benchmark raw evidence.

The analyzer never repairs model output and never rewrites the source result directory.
For reasoning baselines it reapplies the explicit final-line-v1 contract only.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from capability_benchmark import (FINAL_LINE_CONTRACT, classify_failure, final_matches,
                                  parse_reasoning_final)
from compile_capability import canonical, digest, load
from xs_calc_plan_fixtures import reference_plan


def finish_reason(record):
    raw = record.get("raw_response")
    if not isinstance(raw, dict):
        return None
    choices = raw.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return None
    return choices[0].get("finish_reason")


def analyze_record(record, gold, reasoning_baseline):
    final = record.get("final")
    correct = bool(record.get("correct"))
    parser_status = None
    numeric = None
    if reasoning_baseline and record["arm"] in ("A", "E"):
        final, parser_status = parse_reasoning_final(record.get("generated_text", ""))
        correct, numeric = final_matches(gold["expected"], final)
    elif final:
        _, numeric = final_matches(gold["expected"], final)
    reason = finish_reason(record)
    failure = classify_failure(record, correct=correct, final=final,
                               parser_status=parser_status, finish_reason=reason)
    plan = reference_plan(gold) if record["arm"] == "B" else None
    plan_summary = None
    if plan is not None:
        plan_summary = {key: plan[key] for key in ("status", "steps", "required_steps", "reason") if key in plan}
    return {
        "id": record["id"], "arm": record["arm"], "family": record["family"],
        "state": record["state"], "original_correct": bool(record.get("correct")),
        "contract_correct": correct, "failure_class": failure,
        "finish_reason": reason, "final_parser_status": parser_status,
        "contract_final": final, "contract_wrong_numeric": numeric is not None and not correct,
        "calc_reference": plan_summary,
    }


def summarize(rows):
    result = {"arms": {}}
    for arm in sorted({row["arm"] for row in rows}):
        selected = [row for row in rows if row["arm"] == arm]
        failures = {}
        parsers = {}
        for row in selected:
            failures[row["failure_class"]] = failures.get(row["failure_class"], 0) + 1
            if row["final_parser_status"] is not None:
                parsers[row["final_parser_status"]] = parsers.get(row["final_parser_status"], 0) + 1
        arm_summary = {
            "items": len(selected),
            "original_correct": sum(row["original_correct"] for row in selected),
            "contract_correct": sum(row["contract_correct"] for row in selected),
            "failure_classes": dict(sorted(failures.items())),
        }
        if parsers:
            arm_summary["final_parser_status"] = dict(sorted(parsers.items()))
        if arm == "B":
            refs = {}
            for row in selected:
                status = (row["calc_reference"] or {}).get("status", "missing")
                bucket = refs.setdefault(status, {"items": 0, "correct": 0})
                bucket["items"] += 1
                bucket["correct"] += int(row["contract_correct"])
            arm_summary["calc_reference_status"] = dict(sorted(refs.items()))
        result["arms"][arm] = arm_summary
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    metadata_bytes = (args.results / "metadata.json").read_bytes()
    items_bytes = (args.results / "items.jsonl").read_bytes()
    metadata = load(metadata_bytes)
    if digest(args.corpus.read_bytes()) != metadata.get("corpus_sha256"):
        raise ValueError("corpus identity does not match result metadata")
    gold_rows = [load(line) for line in args.corpus.read_bytes().splitlines()]
    gold = {row["id"]: row for row in gold_rows}
    records = [load(line) for line in items_bytes.splitlines()]
    if len(gold) != len(gold_rows):
        raise ValueError("duplicate gold IDs")
    if any(record.get("id") not in gold for record in records):
        raise ValueError("result contains an unknown corpus ID")

    reasoning = metadata.get("config", {}).get("baseline_mode") == "reasoning"
    derived = [analyze_record(record, gold[record["id"]], reasoning) for record in records]
    summary = summarize(derived)
    summary.update({
        "format": "exactscope.capability.failure-analysis",
        "format_version": "0.1",
        "source_results": args.results.as_posix(),
        "source_items_sha256": digest(items_bytes),
        "source_metadata_sha256": digest(metadata_bytes),
        "corpus_sha256": metadata["corpus_sha256"],
        "scoring_contract": FINAL_LINE_CONTRACT,
        "analyzer_sha256": digest(Path(__file__).read_bytes()),
        "note": "Derived analysis only; raw source rows are unchanged. A missing xs_calc reference fixture is not proof of mathematical unrepresentability.",
    })

    args.output.mkdir(parents=True, exist_ok=False)
    analysis_bytes = b"".join(canonical(row) for row in derived)
    (args.output / "items.analysis.jsonl").write_bytes(analysis_bytes)
    summary["analysis_items_sha256"] = digest(analysis_bytes)
    (args.output / "summary.json").write_bytes(canonical(summary))
    print(f"PASS failure analysis rows={len(derived)} sha256={summary['analysis_items_sha256']}")


if __name__ == "__main__":
    main()
