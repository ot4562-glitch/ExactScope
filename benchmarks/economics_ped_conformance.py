#!/usr/bin/env python3
"""Generate the reviewed econ.ped.mid Tiny JSON conformance corpus."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "spec/examples/econ-undergrad-minimal.xsp.json"
STATUS_SOURCE = ROOT / "crates/exactscope-kernel/src/status.rs"
DEFAULT_OUTPUT = ROOT / "benchmarks/economics-ped-conformance-v0.1.jsonl"
OPERATION_KEY = "econ.ped.mid"


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load_status_codes():
    text = STATUS_SOURCE.read_text(encoding="utf-8")
    pairs = re.findall(r"pub const ([A-Z0-9_]+): Self = Self\((\d+)\);", text)
    codes = {name: int(value) for name, value in pairs}
    if not codes or codes.get("OK") != 0:
        raise ValueError("could not derive stable status codes")
    return codes


def round_half_even(value: Fraction, scale: int = 6) -> str:
    sign = "-" if value < 0 else ""
    numerator = abs(value.numerator) * (10 ** scale)
    denominator = value.denominator
    quotient, remainder = divmod(numerator, denominator)
    doubled = remainder * 2
    if doubled > denominator or (doubled == denominator and quotient % 2 == 1):
        quotient += 1
    whole, fractional = divmod(quotient, 10 ** scale)
    if fractional == 0:
        return f"{sign}{whole}"
    digits = f"{fractional:0{scale}d}".rstrip("0")
    return f"{sign}{whole}.{digits}"


def independent_ped_oracle(args):
    p1, p2, q1, q2 = (Fraction(value) for value in args)
    constraints = ((p1 > 0, 0, 1), (p2 > 0, 1, 2), (q1 >= 0, 2, 3), (q2 >= 0, 3, 4))
    for valid, index, detail in constraints:
        if not valid:
            return {"status": "CONSTRAINT_VIOLATION", "argument_index": index, "detail_id": detail}
    if p2 == p1 or q1 + q2 == 0:
        return {"status": "DIVIDE_BY_ZERO"}
    value = (q2 - q1) * (p1 + p2) / ((q1 + q2) * (p2 - p1))
    magnitude = abs(value)
    classification = "inelastic" if magnitude < 1 else ("unit_elastic" if magnitude == 1 else "elastic")
    return {"status": "OK", "values": [round_half_even(value)], "classification": classification}


def verify_reviewed_expectation(args, expect, name):
    oracle = independent_ped_oracle(args)
    for key in ("status", "values", "classification", "argument_index", "detail_id"):
        if key in oracle and expect.get(key) != oracle[key]:
            raise ValueError(f"reviewed PED expectation disagrees with independent midpoint oracle: {name}/{key}")
        if key in expect and key not in oracle and key not in ("values", "classification"):
            raise ValueError(f"reviewed PED expectation has unexpected field for oracle state: {name}/{key}")


def generate():
    source_bytes = SOURCE.read_bytes()
    source = json.loads(source_bytes)
    pack = source["pack"]
    operations = [op for op in source["operations"] if op.get("key") == OPERATION_KEY]
    if len(operations) != 1:
        raise ValueError("reviewed source must contain exactly one econ.ped.mid operation")
    operation = operations[0]
    tests = operation.get("tests")
    if not isinstance(tests, list) or not tests:
        raise ValueError("econ.ped.mid reviewed source has no tests")
    status_codes = load_status_codes()
    provenance = f"{pack['name']}@{pack['version']}"
    first_success = next((test for test in tests if test.get("expect", {}).get("status") == "OK"), None)
    if first_success is None:
        raise ValueError("reviewed PED source has no successful method-distinction case")
    p1, p2, q1, q2 = (Fraction(value) for value in first_success["args"])
    initial_value = ((q2 - q1) / q1) / ((p2 - p1) / p1)
    if independent_ped_oracle(first_success["args"])["values"][0] == round_half_even(initial_value):
        raise ValueError("reviewed PED fixture does not distinguish midpoint from initial-value elasticity")
    rows = []
    seen = set()
    for test in tests:
        name = test.get("name")
        args = test.get("args")
        expect = test.get("expect")
        if not isinstance(name, str) or not name or name in seen:
            raise ValueError("invalid/duplicate reviewed test name")
        seen.add(name)
        if not isinstance(args, list) or not isinstance(expect, dict):
            raise ValueError(f"invalid reviewed test: {name}")
        verify_reviewed_expectation(args, expect, name)
        status_name = expect.get("status")
        if status_name not in status_codes:
            raise ValueError(f"unknown reviewed status {status_name}: {name}")
        status = status_codes[status_name]
        expected = {"s": status}
        if status == 0:
            values = expect.get("values")
            if not isinstance(values, list) or len(values) != 1 or not isinstance(values[0], str):
                raise ValueError(f"PED success test must have exactly one decimal value: {name}")
            expected.update(v=values[0], p=provenance, r=operation["revision"])
            classification = expect.get("classification")
            if classification is not None:
                if not isinstance(classification, str):
                    raise ValueError(f"invalid classification: {name}")
                expected["c"] = classification
        else:
            expected["e"] = status_name
            if "argument_index" in expect:
                expected["i"] = expect["argument_index"]
            if "detail_id" in expect:
                expected["d"] = expect["detail_id"]
        rows.append({
            "id": f"econ-ped-v1-{len(rows):03d}",
            "call": {"op": OPERATION_KEY, "a": args},
            "expected": expected,
        })
    return b"".join(canonical(row) for row in rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = generate()
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != data:
            raise SystemExit("FAIL economics PED conformance corpus drift")
        print(f"PASS economics PED conformance rows={len(data.splitlines())} sha256={sha256(data)}")
        return
    if args.output.exists() and args.output.read_bytes() != data:
        raise SystemExit("refusing to overwrite different conformance corpus; use a new revision/path")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    print(f"PASS economics PED conformance rows={len(data.splitlines())} sha256={sha256(data)}")


if __name__ == "__main__":
    main()
