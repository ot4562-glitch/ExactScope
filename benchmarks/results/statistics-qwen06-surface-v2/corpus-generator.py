#!/usr/bin/env python3
"""Seeded Statistics templates checked against an independent oracle AND real core."""
from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from compile_capability import ROOT, canonical, digest, load
from run_benchmark import CoreBridge

SEED = 20260905
DEFAULT = ROOT / "benchmarks/statistics-v0.1.jsonl"
LAYOUT = [("S1", 40), ("S2", 40), ("S3", 50), ("S4", 40), ("S5", 40), ("S6", 30)]


class Generator:
    """Explicit 32-bit LCG; independent of Python random/library versions."""
    def __init__(self, seed):
        self.state = seed

    def integer(self, low, high):
        self.state = (1664525 * self.state + 1013904223) & 0xffffffff
        return low + self.state % (high - low + 1)


def decimal_text(value):
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def rounded(value, sqrt=False):
    with localcontext() as context:
        context.prec = 100
        result = Decimal(value.numerator) / Decimal(value.denominator)
        if sqrt:
            result = result.sqrt()
        return decimal_text(result.quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN))


def oracle(call):
    """Test-only rational oracle for this declared bounded corpus; never a serving fallback."""
    op = call["op"]
    vectors = [[Fraction(v) for v in a] for a in call["a"]]
    x = vectors[0]
    paired = op in ("stats.mean.weighted", "stats.corr.pearson")
    minimum = 2 if op in ("stats.var.sample", "stats.sd.sample", "stats.corr.pearson") else 1
    if paired and len(x) != len(vectors[1]):
        return {"s": 6, "e": "ARGUMENT_TYPE"}
    if len(x) < minimum:
        return {"s": 16, "e": "INSUFFICIENT_DATA"}
    mean = sum(x) / len(x)
    if op == "stats.sum":
        result = sum(x)
    elif op == "stats.mean":
        result = mean
    elif op == "stats.mean.weighted":
        weights = vectors[1]
        if sum(weights) == 0:
            return {"s": 13, "e": "DIVIDE_BY_ZERO"}
        result = sum(v * w for v, w in zip(x, weights)) / sum(weights)
    elif op == "stats.corr.pearson":
        y = vectors[1]
        mean_y = sum(y) / len(y)
        sxx = sum((v - mean) ** 2 for v in x)
        syy = sum((v - mean_y) ** 2 for v in y)
        if not sxx or not syy:
            return {"s": 10, "e": "DOMAIN_ERROR"}
        sxy = sum((a - mean) * (b - mean_y) for a, b in zip(x, y))
        value = rounded(sxy ** 2 / (sxx * syy), sqrt=True)
        return {"s": 0, "v": "-" + value if sxy < 0 and value != "0" else value}
    else:
        divisor = len(x) - int(op.endswith("sample"))
        result = sum((v - mean) ** 2 for v in x) / divisor
    return {"s": 0, "v": rounded(result, sqrt=op.startswith("stats.sd."))}


def templates(seed=SEED):
    rng = Generator(seed)
    rows = []
    labels = {"stats.sum": "sum", "stats.mean": "arithmetic mean",
              "stats.mean.weighted": "weighted arithmetic mean",
              "stats.var.pop": "population variance", "stats.var.sample": "sample variance",
              "stats.sd.pop": "population standard deviation", "stats.sd.sample": "sample standard deviation",
              "stats.corr.pearson": "Pearson correlation"}
    for family, count in LAYOUT:
        for index in range(count):
            n = rng.integer(2, 8)
            x = [decimal_text(Decimal(rng.integer(-90, 90)) / 10) for _ in range(n)]
            y = [str(rng.integer(1, 9)) for _ in range(n)]
            op = {"S1": ["stats.sum", "stats.mean"][index % 2],
                  "S2": "stats.mean.weighted",
                  "S3": ["stats.var.pop", "stats.var.sample"][index % 2],
                  "S4": ["stats.sd.pop", "stats.sd.sample"][index % 2],
                  "S5": "stats.corr.pearson", "S6": "stats.mean"}[family]
            args = [x, y] if family in ("S2", "S5") else [x]
            ambiguity = None
            if family == "S6":
                kind = index % 6
                if kind < 3:
                    ambiguity = ["AMBIGUOUS_METHOD", "MISSING_INFORMATION", "UNSUPPORTED_OPERATION"][kind]
                    prompt = [f"Compute the variance of {x}. No population or sample method is specified.",
                              f"Compute the weighted mean of {x}. The weights are unavailable.",
                              f"Compute the Spearman rank correlation of {x} and {y}. Only Pearson is supported."][kind]
                elif kind == 3:
                    op, args = "stats.var.sample", [[x[0]]]
                elif kind == 4:
                    op, args = "stats.mean.weighted", [x, ["0"] * n]
                else:
                    op, args = "stats.corr.pearson", [x, y[:-1]]
            if ambiguity is None:
                values = "values=" + str(args[0])
                if len(args) == 2:
                    values += ("; weights=" if op.endswith("weighted") else "; paired y=") + str(args[1])
                question = f"Compute the {labels[op]} for {values}."
                prompt = [question,
                          f"Measurement report: {values}. Report its {labels[op]}.",
                          f"Report ID 2048, collected in 2025; these are identifiers, not observations. {question}",
                          question + " Use exactly the stated method; preserve any typed failure.",
                          f"The observations follow: {values}.\nThe requested measure is {labels[op]}."][index % 5]
            call = None if ambiguity else {"op": op, "a": args}
            expected = {"e": ambiguity} if ambiguity else oracle(call)
            rows.append({"id": f"stats-v1-{family}-{index:03}", "revision": 1,
                         "family": family, "difficulty": "ambiguity" if ambiguity else [
                             "direct", "extraction", "distractor", "method", "multi-sentence"][index % 5],
                         "seed": seed, "template": f"{family}-{index % (6 if family == 'S6' else 5)}",
                         "prompt": prompt, "state": "ambiguous" if ambiguity else (
                             "typed-failure" if expected["s"] else "supported"),
                         "call": call, "expected": expected})
    return rows


def validate_rows(rows, core):
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("duplicate corpus item")
    for row in rows:
        if row["call"] is None:
            if row["state"] != "ambiguous" or row["expected"].get("e") not in (
                    "AMBIGUOUS_METHOD", "MISSING_INFORMATION", "UNSUPPORTED_OPERATION"):
                raise ValueError(f"invalid ambiguity gold: {row['id']}")
            continue
        expected = oracle(row["call"])
        if row["expected"] != expected:
            raise ValueError(f"independent gold mismatch: {row['id']}")
        response, _ = core.call("eval", row["call"])
        if any(response.get(k) != v for k, v in expected.items()):
            raise ValueError(f"runtime disagrees with oracle: {row['id']}: {response} != {expected}")
        if expected["s"] and "v" in response:
            raise ValueError(f"runtime emitted a number on failure: {row['id']}")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=ROOT / "target/debug" / (
        "exactscope-core.exe" if os.name == "nt" else "exactscope-core"))
    parser.add_argument("--output", type=Path, default=DEFAULT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rows = validate_rows(templates(), CoreBridge(args.core))
    data = b"".join(canonical(row) for row in rows)
    if args.check:
        if args.output.read_bytes() != data:
            raise ValueError("corpus regeneration drift")
    else:
        if args.output.exists() and args.output.read_bytes() != data:
            raise ValueError("existing corpus differs; use a new revision/output")
        args.output.write_bytes(data)
    print(f"PASS Statistics corpus cases={len(rows)} runtime_checked={sum(r['call'] is not None for r in rows)} sha256={digest(data)}")


if __name__ == "__main__":
    main()
