#!/usr/bin/env python3
"""Reduce streamed target-device latency samples into qualification percentiles."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "spec" / "examples" / "wearable-edge-profile.json"
CANONICAL_COLUMNS = ["sequence", "metric", "duration_ns", "status"]
METRICS = {"lookup", "scalar_eval", "pack_mount_256k"}
MAX_REASONABLE_DURATION_NS = 60_000_000_000


class ReductionFailure(Exception):
    """Raised when raw benchmark evidence is malformed or insufficient."""


def read_profile() -> dict[str, object]:
    try:
        value = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReductionFailure(f"cannot read wearable profile: {exc}") from exc
    if not isinstance(value, dict):
        raise ReductionFailure("wearable profile root must be an object")
    return value


def ns_to_ceil_us(duration_ns: int) -> int:
    if duration_ns < 0:
        raise ReductionFailure("duration_ns cannot be negative")
    return (duration_ns + 999) // 1000


def nearest_rank(sorted_values: list[int], percentile: int) -> int:
    if not sorted_values:
        raise ReductionFailure("cannot compute percentile of empty sample set")
    if percentile <= 0 or percentile > 100:
        raise ReductionFailure(f"unsupported percentile {percentile}")
    rank = (percentile * len(sorted_values) + 99) // 100
    return sorted_values[rank - 1]


def summarize_ns(durations_ns: Iterable[int]) -> dict[str, int]:
    durations_us = sorted(ns_to_ceil_us(value) for value in durations_ns)
    if not durations_us:
        raise ReductionFailure("no measured samples")
    return {
        "p50_us": nearest_rank(durations_us, 50),
        "p95_us": nearest_rank(durations_us, 95),
        "p99_us": nearest_rank(durations_us, 99),
        "max_us": durations_us[-1],
    }


def load_csv(path: Path, metric: str) -> list[int]:
    try:
        handle = path.open("r", encoding="utf-8", newline="")
    except OSError as exc:
        raise ReductionFailure(f"cannot open {path}: {exc}") from exc

    durations: list[int] = []
    with handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != CANONICAL_COLUMNS:
            raise ReductionFailure(
                f"CSV header must be exactly {','.join(CANONICAL_COLUMNS)}"
            )
        for expected_sequence, row in enumerate(reader):
            try:
                sequence = int(row["sequence"], 10)
                duration_ns = int(row["duration_ns"], 10)
                status = int(row["status"], 10)
            except (TypeError, ValueError) as exc:
                raise ReductionFailure(
                    f"row {expected_sequence + 2}: non-integer sequence/duration/status"
                ) from exc
            if sequence != expected_sequence:
                raise ReductionFailure(
                    f"row {expected_sequence + 2}: sequence {sequence} != expected {expected_sequence}"
                )
            if row["metric"] != metric:
                raise ReductionFailure(
                    f"row {expected_sequence + 2}: metric {row['metric']!r} != {metric!r}"
                )
            if status != 0:
                raise ReductionFailure(
                    f"row {expected_sequence + 2}: measured benchmark status must be 0, got {status}"
                )
            if duration_ns < 0 or duration_ns > MAX_REASONABLE_DURATION_NS:
                raise ReductionFailure(
                    f"row {expected_sequence + 2}: duration_ns out of evidence range: {duration_ns}"
                )
            durations.append(duration_ns)
    return durations


def metric_passes(metric: str, summary: dict[str, int], profile: dict[str, object]) -> bool:
    targets = profile["product_targets"]
    assert isinstance(targets, dict)
    if metric == "lookup":
        return summary["p99_us"] <= int(targets["lookup_p99_us"])
    if metric == "scalar_eval":
        return (
            summary["p50_us"] <= int(targets["scalar_eval_p50_us"])
            and summary["p99_us"] <= int(targets["scalar_eval_p99_us"])
        )
    if metric == "pack_mount_256k":
        return summary["p99_us"] <= int(targets["pack_mount_256k_p99_us"])
    raise ReductionFailure(f"unknown metric {metric!r}")


def reduce_samples(
    metric: str,
    durations_ns: list[int],
    warmup_iterations: int,
    profile: dict[str, object],
) -> dict[str, object]:
    if metric not in METRICS:
        raise ReductionFailure(f"unsupported metric {metric!r}")
    conformance = profile["conformance"]
    assert isinstance(conformance, dict)
    required_warmup = int(conformance["benchmark_warmup_iterations"])
    required_samples = int(conformance["benchmark_sample_iterations"])
    if warmup_iterations < required_warmup:
        raise ReductionFailure(
            f"warmup {warmup_iterations} < required {required_warmup}"
        )
    if len(durations_ns) < required_samples:
        raise ReductionFailure(
            f"samples {len(durations_ns)} < required {required_samples}"
        )

    summary = summarize_ns(durations_ns)
    passed = metric_passes(metric, summary, profile)
    return {
        "metric": metric,
        "state": "pass" if passed else "fail",
        "warmup_iterations": warmup_iterations,
        "sample_iterations": len(durations_ns),
        **summary,
    }


def expect_csv_invalid(path: Path, metric: str, label: str) -> None:
    try:
        load_csv(path, metric)
    except ReductionFailure:
        return
    raise ReductionFailure(f"CSV self-test failed to reject {label}")


def run_csv_self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="exactscope-latency-") as directory:
        root = Path(directory)
        valid = root / "valid.csv"
        valid.write_text(
            "sequence,metric,duration_ns,status\n"
            "0,scalar_eval,100000,0\n"
            "1,scalar_eval,101000,0\n",
            encoding="utf-8",
        )
        if load_csv(valid, "scalar_eval") != [100_000, 101_000]:
            raise ReductionFailure("CSV self-test failed to load canonical rows")

        bad_header = root / "bad-header.csv"
        bad_header.write_text(
            "metric,sequence,duration_ns,status\nscalar_eval,0,100000,0\n",
            encoding="utf-8",
        )
        expect_csv_invalid(bad_header, "scalar_eval", "column-order drift")

        bad_sequence = root / "bad-sequence.csv"
        bad_sequence.write_text(
            "sequence,metric,duration_ns,status\n0,scalar_eval,100000,0\n2,scalar_eval,101000,0\n",
            encoding="utf-8",
        )
        expect_csv_invalid(bad_sequence, "scalar_eval", "sequence gap")

        bad_status = root / "bad-status.csv"
        bad_status.write_text(
            "sequence,metric,duration_ns,status\n0,scalar_eval,100000,11\n",
            encoding="utf-8",
        )
        expect_csv_invalid(bad_status, "scalar_eval", "non-OK measured sample")

        bad_metric = root / "bad-metric.csv"
        bad_metric.write_text(
            "sequence,metric,duration_ns,status\n0,lookup,100000,0\n",
            encoding="utf-8",
        )
        expect_csv_invalid(bad_metric, "scalar_eval", "metric mismatch")


def run_self_test(profile: dict[str, object]) -> None:
    run_csv_self_test()
    minimum_samples = int(profile["conformance"]["benchmark_sample_iterations"])
    minimum_warmup = int(profile["conformance"]["benchmark_warmup_iterations"])

    ordered = [index * 1000 for index in range(1, minimum_samples + 1)]
    ordered_summary = summarize_ns(ordered)
    if ordered_summary != {
        "p50_us": 5000,
        "p95_us": 9500,
        "p99_us": 9900,
        "max_us": 10000,
    }:
        raise ReductionFailure(f"nearest-rank self-test drifted: {ordered_summary}")

    passing = reduce_samples(
        "scalar_eval",
        [100_000] * minimum_samples,
        minimum_warmup,
        profile,
    )
    if passing["state"] != "pass" or passing["p50_us"] != 100 or passing["p99_us"] != 100:
        raise ReductionFailure(f"passing scalar self-test drifted: {passing}")

    failing = reduce_samples(
        "scalar_eval",
        [1_001_000] * minimum_samples,
        minimum_warmup,
        profile,
    )
    if failing["state"] != "fail" or failing["p99_us"] != 1001:
        raise ReductionFailure(f"failing scalar self-test drifted: {failing}")

    if ns_to_ceil_us(1) != 1 or ns_to_ceil_us(1000) != 1 or ns_to_ceil_us(1001) != 2:
        raise ReductionFailure("nanosecond-to-microsecond ceiling self-test failed")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reduce canonical ExactScope wearable latency CSV evidence."
    )
    parser.add_argument("csv", nargs="?", type=Path, help="canonical sample CSV")
    parser.add_argument("--metric", choices=sorted(METRICS))
    parser.add_argument("--warmup-iterations", type=int, default=1000)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        profile = read_profile()
        if args.self_test:
            run_self_test(profile)
            print("wearable latency reducer self-test: PASS")
            return 0
        if args.csv is None or args.metric is None:
            raise ReductionFailure("csv path and --metric are required unless --self-test is used")
        durations = load_csv(args.csv, args.metric)
        reduced = reduce_samples(args.metric, durations, args.warmup_iterations, profile)
    except ReductionFailure as exc:
        print(f"wearable latency evidence invalid: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(reduced, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
