#!/usr/bin/env python3
"""Frozen-candidate r17 Statistics corpus with new wording, checked against oracle and core."""
from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from compile_capability import ROOT, canonical, digest, load
from run_benchmark import CoreBridge
from statistics_corpus import Generator, decimal_text, oracle, validate_rows

SEED = 20260917
DEFAULT = ROOT / "benchmarks/statistics-r17-v0.1.jsonl"
LAYOUT = [("S1", 24), ("S2", 24), ("S3", 24), ("S4", 24), ("S5", 24), ("S6", 24)]
WORDING_REVISION = "r17-independent-wording-v1"


def values_text(values):
    return ", ".join(values)


def ensure_nonconstant(values):
    if len(set(values)) > 1:
        return values
    changed = list(values)
    changed[-1] = decimal_text(Decimal(changed[-1]) + Decimal("0.7"))
    return changed


def supported_prompt(family, index, op, x, y):
    xs = values_text(x)
    ys = values_text(y)
    variant = index % 6
    if family == "S1":
        noun = "sum" if op == "stats.sum" else "arithmetic mean"
        options = [
            f"A sensor calibration batch recorded these readings: {xs}. Find the {noun} of the recorded readings.",
            f"The observations in a quality-control lot are {xs}. Determine their {noun}.",
            f"A lab worksheet contains the numeric observations {xs}. What is the {noun}?",
            f"For a data audit, the usable observations are {xs}; an earlier report number is not part of the data. Report the {noun} of the usable observations.",
            f"A device logged the sequence {xs}. Calculate the {noun} across that sequence.",
            f"Dataset A has values {xs}. The requested descriptive statistic is the {noun}.",
        ]
        return options[variant]
    if family == "S2":
        options = [
            f"A scoring model has values {xs} with corresponding weights {ys}. Find the weighted arithmetic mean using those weights.",
            f"For paired value/weight lists, values are {xs} and weights are {ys}. Determine the weighted mean.",
            f"A composite measurement uses readings {xs}; their weights, in the same order, are {ys}. What weighted arithmetic mean results?",
            f"The entries {xs} carry importance weights {ys}, position by position. Calculate the weighted mean without changing the pairing.",
            f"A portfolio-style average uses quantities {xs} and coefficients {ys}. Treat the coefficients as weights and find the weighted arithmetic mean.",
            f"Use values {xs} with aligned weights {ys}. Report the weighted arithmetic mean implied by the two lists.",
        ]
        return options[variant]
    if family == "S3":
        sample = op.endswith("sample")
        method = "sample variance using the n-1 denominator" if sample else "population variance using the n denominator"
        options = [
            f"The measurements are {xs}. Treat them as {'a sample' if sample else 'the complete population'} and find the {method}.",
            f"For values {xs}, the required method is explicitly {method}. Determine the variance.",
            f"An analysis sheet lists {xs}. Use {method}; do not substitute the other variance convention.",
            f"A study records {xs}. The protocol calls for {method}. What variance does that give?",
            f"Evaluate the dispersion of {xs} with the stated rule: {method}.",
            f"Values {xs} must be processed as {'sample data' if sample else 'population data'}. Report the resulting variance under {method}.",
        ]
        return options[variant]
    if family == "S4":
        sample = op.endswith("sample")
        method = "sample standard deviation using the n-1 variance denominator" if sample else "population standard deviation using the n variance denominator"
        options = [
            f"The recorded values are {xs}. Find the {method}.",
            f"A measurement set contains {xs}. Apply {method}, not the alternative convention.",
            f"For observations {xs}, the protocol explicitly requests {method}. What is the standard deviation?",
            f"A statistical report uses data {xs} and specifies {method}. Determine the result.",
            f"Process {xs} under the rule '{method}' and report the resulting standard deviation.",
            f"The data sequence {xs} is to be treated as {'a sample' if sample else the_complete_population()}. Calculate its {method}.",
        ]
        return options[variant]
    if family == "S5":
        options = [
            f"Matched observations are x = {xs} and y = {ys}. Find the Pearson correlation coefficient for the aligned pairs.",
            f"Two variables were measured in the same order: x values {xs}; y values {ys}. Determine their Pearson correlation.",
            f"For paired sequences x:[{xs}] and y:[{ys}], calculate Pearson's correlation coefficient.",
            f"A paired-data analysis uses x = {xs} with y = {ys}. The requested association measure is Pearson correlation.",
            f"Keep the positions aligned between {xs} and {ys}. What Pearson correlation results from those pairs?",
            f"The first variable has observations {xs}; the second has {ys}. Report the Pearson correlation coefficient.",
        ]
        return options[variant]
    raise AssertionError(f"unsupported family {family}")


def the_complete_population():
    return "the complete population"


def supported_difficulty(family, index):
    if family == "S1":
        return "distractor-resistant" if index % 6 == 3 else "single-vector-extraction"
    if family == "S2":
        return "paired-weight-extraction"
    if family in ("S3", "S4"):
        return "explicit-method-selection"
    if family == "S5":
        return "paired-variable-extraction"
    raise AssertionError(family)


def failure_case(rng, index):
    kind = index % 6
    variant = (index // 6) % 4
    n = rng.integer(3, 7)
    x = [decimal_text(Decimal(rng.integer(-120, 120)) / 10) for _ in range(n)]
    y = ensure_nonconstant([decimal_text(Decimal(rng.integer(-100, 100)) / 10) for _ in range(n)])
    x = ensure_nonconstant(x)
    xs = values_text(x)
    ys = values_text(y)
    if kind == 0:
        prompts = [
            f"A dataset contains {xs}. Find its variance, but the request does not say whether these values are a sample or a population.",
            f"A report asks for the variance of {xs}. It never identifies the sample-versus-population convention.",
            f"Values {xs} are provided for a variance calculation, but no denominator convention is stated.",
            f"Determine the variance for {xs}. There is no information saying whether the data are a sample or the full population.",
        ]
        return {"prompt": prompts[variant], "call": None, "expected": {"e": "AMBIGUOUS_METHOD"},
                "state": "ambiguous", "difficulty": "method-ambiguity"}
    if kind == 1:
        prompts = [
            f"The values are {xs}. Find their weighted arithmetic mean; no weights were supplied anywhere in the request.",
            f"A weighted mean is requested for {xs}, but the weighting coefficients are missing.",
            f"Find the weighted arithmetic mean of {xs}. The source gives values only and omits every weight.",
            f"An analyst wants a weighted average of {xs}; no corresponding weights are available.",
        ]
        return {"prompt": prompts[variant], "call": None, "expected": {"e": "MISSING_INFORMATION"},
                "state": "ambiguous", "difficulty": "missing-information"}
    if kind == 2:
        prompts = [
            f"Using paired data x = {xs} and y = {ys}, report the Spearman rank correlation coefficient.",
            f"For x values {xs} and aligned y values {ys}, determine Spearman rank correlation.",
            f"The requested association measure for x=[{xs}] and y=[{ys}] is Spearman correlation.",
            f"Compute a Spearman rank correlation from paired sequences {xs} and {ys}.",
        ]
        return {"prompt": prompts[variant], "call": None, "expected": {"e": "UNSUPPORTED_OPERATION"},
                "state": "ambiguous", "difficulty": "unsupported-method"}
    if kind == 3:
        value = x[0]
        call = {"op": "stats.var.sample", "a": [[value]]}
        prompts = [
            f"A sample contains exactly one observation, {value}. Using the sample-variance n-1 convention, determine its variance.",
            f"Treat the single value {value} as a sample and calculate sample variance with the n-1 denominator.",
            f"The sample dataset is [{value}]. Apply the ordinary sample-variance rule using n-1.",
            f"Only one sample observation, {value}, is available. Determine sample variance under the n-1 convention.",
        ]
        return {"prompt": prompts[variant], "call": call, "expected": oracle(call),
                "state": "typed-failure", "difficulty": "insufficient-data"}
    if kind == 4:
        values = x[:2]
        weights = ["2", "-2"]
        call = {"op": "stats.mean.weighted", "a": [values, weights]}
        vs = values_text(values)
        ws = values_text(weights)
        prompts = [
            f"Values {vs} have aligned weights {ws}. Determine the weighted arithmetic mean using exactly those signed weights.",
            f"Find the weighted mean for values {vs} with corresponding signed weights {ws}.",
            f"Use value list [{vs}] and weight list [{ws}] without altering the signs; report the weighted arithmetic mean.",
            f"A weighted-average calculation pairs {vs} with weights {ws}. Determine the result from those exact weights.",
        ]
        return {"prompt": prompts[variant], "call": call, "expected": oracle(call),
                "state": "typed-failure", "difficulty": "zero-weight-sum"}
    y_short = y[:-1]
    call = {"op": "stats.corr.pearson", "a": [x, y_short]}
    yss = values_text(y_short)
    prompts = [
        f"Compute Pearson correlation for x = {xs} and y = {yss}. The two sequences are provided exactly as recorded.",
        f"Find Pearson correlation from x values {xs} and y values {yss}; do not invent a missing paired observation.",
        f"The supplied paired-data lists are x=[{xs}] and y=[{yss}]. Determine Pearson correlation from the data as given.",
        f"A Pearson-correlation request provides x sequence {xs} but y sequence {yss}. Use only the supplied entries.",
    ]
    return {"prompt": prompts[variant], "call": call, "expected": oracle(call),
            "state": "typed-failure", "difficulty": "mismatched-pairs"}


def rows(seed=SEED):
    rng = Generator(seed)
    result = []
    for family, count in LAYOUT:
        for index in range(count):
            if family == "S6":
                case = failure_case(rng, index)
                result.append({
                    "id": f"stats-r17-{family}-{index:03}",
                    "revision": 1,
                    "family": family,
                    "seed": seed,
                    "wording_revision": WORDING_REVISION,
                    **case,
                })
                continue
            n = rng.integer(3, 8)
            x = [decimal_text(Decimal(rng.integer(-120, 120)) / 10) for _ in range(n)]
            x = ensure_nonconstant(x)
            if family == "S1":
                op = "stats.sum" if index % 2 == 0 else "stats.mean"
                args = [x]
            elif family == "S2":
                op = "stats.mean.weighted"
                y = [str(rng.integer(1, 9)) for _ in range(n)]
                args = [x, y]
            elif family == "S3":
                op = "stats.var.pop" if index % 2 == 0 else "stats.var.sample"
                args = [x]
            elif family == "S4":
                op = "stats.sd.pop" if index % 2 == 0 else "stats.sd.sample"
                args = [x]
            elif family == "S5":
                op = "stats.corr.pearson"
                y = ensure_nonconstant([
                    decimal_text(Decimal(rng.integer(-100, 100)) / 10) for _ in range(n)
                ])
                args = [x, y]
            else:
                raise AssertionError(family)
            call = {"op": op, "a": args}
            expected = oracle(call)
            if expected.get("s") != 0:
                raise ValueError(f"supported family generated a failure: {family} {index} {expected}")
            prompt = supported_prompt(family, index, op, x, args[1] if len(args) == 2 else [])
            result.append({
                "id": f"stats-r17-{family}-{index:03}",
                "revision": 1,
                "family": family,
                "difficulty": supported_difficulty(family, index),
                "seed": seed,
                "wording_revision": WORDING_REVISION,
                "prompt": prompt,
                "state": "supported",
                "call": call,
                "expected": expected,
            })
    return result


def encoded(rows_):
    return b"".join(canonical(row) for row in rows_)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--output", type=Path, default=DEFAULT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generated = rows(args.seed)
    core_path = ROOT / "target/debug" / ("exactscope-core.exe" if os.name == "nt" else "exactscope-core")
    validate_rows(generated, CoreBridge(core_path))
    data = encoded(generated)
    if args.check:
        if not args.output.exists() or args.output.read_bytes() != data:
            raise ValueError("frozen r17 corpus differs from deterministic generator output")
    else:
        args.output.write_bytes(data)
    calls = sum(row["call"] is not None for row in generated)
    print(f"PASS r17 corpus items={len(generated)} runtime_calls={calls} sha256={digest(data)}")


if __name__ == "__main__":
    main()
