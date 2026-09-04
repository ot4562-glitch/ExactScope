#!/usr/bin/env python3
"""Reproduce FinQA/TAT-QA bounded xs_calc oracle-subset measurements."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

STEP_RE = re.compile(r"\s*([A-Za-z_][A-Za-z0-9_]*)\((.*)\)\s*")
REF_RE = re.compile(r"#[0-7]")
NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
TOKEN_RE = re.compile(r"\d+(?:\.\d+)?|[()+\-*/%]")
FINQA_OPS = {"add": "add", "subtract": "sub", "multiply": "mul", "divide": "div", "exp": "powi"}


def split_top_level(text: str) -> list[str]:
    """Split commas only at parenthesis depth zero."""
    parts: list[str] = []
    start = depth = 0
    for index, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("unbalanced closing parenthesis")
        elif char == "," and depth == 0:
            part = text[start:index].strip()
            if not part:
                raise ValueError("empty item")
            parts.append(part)
            start = index + 1
    if depth:
        raise ValueError("unbalanced opening parenthesis")
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    elif parts:
        raise ValueError("trailing delimiter")
    return parts


def literal(token: str) -> str:
    value = token.strip().replace(",", "").replace("$", "").replace("%", "")
    if value.startswith("const_"):
        value = "-1" if value == "const_m1" else value[6:]
    if not NUMBER_RE.fullmatch(value) or not Decimal(value).is_finite():
        raise ValueError("unsupported decimal")
    return value.lstrip("+")


def finqa_plan(program: str) -> dict[str, Any]:
    raw_steps = split_top_level(program)
    if not 1 <= len(raw_steps) <= 8:
        raise ValueError("step bound")
    steps: list[dict[str, Any]] = []
    for index, raw_step in enumerate(raw_steps):
        match = STEP_RE.fullmatch(raw_step)
        if not match or match.group(1) not in FINQA_OPS:
            raise ValueError("unsupported operation")
        arguments = split_top_level(match.group(2))
        if len(arguments) != 2:
            raise ValueError("arity")
        normalized = []
        for argument in arguments:
            if REF_RE.fullmatch(argument):
                if int(argument[1:]) >= index:
                    raise ValueError("forward reference")
                normalized.append(argument)
            else:
                normalized.append(literal(argument))
        steps.append({"o": FINQA_OPS[match.group(1)], "a": normalized})
    return bounded({"p": steps})


class ExpressionPlan:
    def __init__(self, derivation: str) -> None:
        compact = "".join(derivation.replace(",", "").replace("$", "").replace("[", "(").replace("]", ")").split())
        self.tokens = TOKEN_RE.findall(compact)
        if "".join(self.tokens) != compact:
            raise ValueError("unsupported derivation token")
        self.at = 0
        self.steps: list[dict[str, Any]] = []

    def peek(self) -> str | None:
        return self.tokens[self.at] if self.at < len(self.tokens) else None

    def take(self, expected: str | None = None) -> str:
        token = self.peek()
        if token is None or expected is not None and token != expected:
            raise ValueError("unexpected token")
        self.at += 1
        return token

    def emit(self, operation: str, left: str, right: str) -> str:
        if len(self.steps) >= 8:
            raise ValueError("step bound")
        self.steps.append({"o": operation, "a": [left, right]})
        return f"#{len(self.steps) - 1}"

    def expression(self) -> str:
        value = self.term()
        while self.peek() in {"+", "-"}:
            value = self.emit("add" if self.take() == "+" else "sub", value, self.term())
        return value

    def term(self) -> str:
        value = self.factor()
        while self.peek() in {"*", "/"}:
            value = self.emit("mul" if self.take() == "*" else "div", value, self.factor())
        return value

    def factor(self) -> str:
        if self.peek() in {"+", "-"}:
            sign = self.take()
            value = self.factor()
            if sign == "-":
                value = "-" + value if not value.startswith("#") else self.emit("mul", value, "-1")
            return value
        if self.peek() == "(":
            self.take("(")
            value = self.expression()
            self.take(")")
        else:
            value = self.take()
            if not re.fullmatch(r"\d+(?:\.\d+)?", value):
                raise ValueError("expected decimal")
        if self.peek() == "%":
            self.take("%")
            value = self.emit("div", value, "100")
        return value

    def plan(self) -> dict[str, Any]:
        result = self.expression()
        if self.peek() is not None or not self.steps or result != f"#{len(self.steps) - 1}":
            raise ValueError("not a bounded plan")
        return bounded({"p": self.steps})


def bounded(request: dict[str, Any]) -> dict[str, Any]:
    if len(json.dumps(request, separators=(",", ":")).encode("ascii")) > 512:
        raise ValueError("request byte bound")
    return request


def run_core(core: Path, request: dict[str, Any]) -> dict[str, Any]:
    completed = subprocess.run(
        [str(core), "request"], input=json.dumps(request, separators=(",", ":")).encode("ascii"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
    )
    return json.loads(completed.stdout)


def candidates(dataset: str, source: Path) -> tuple[int, int, Iterable[tuple[str, str, str]]]:
    document = json.loads(source.read_text(encoding="utf-8"))
    if dataset == "finqa":
        def rows() -> Iterable[tuple[str, str, str]]:
            for index, row in enumerate(document):
                qa = row.get("qa", {})
                yield str(index), qa.get("program", ""), str(qa.get("answer", ""))
        return len(document), len(document), rows()
    questions = [question for item in document for question in item.get("questions", [])]
    arithmetic = [question for question in questions if question.get("answer_type") == "arithmetic"]
    def rows() -> Iterable[tuple[str, str, str]]:
        for question in arithmetic:
            derivation = question.get("derivation", "")
            yield question.get("uid", ""), derivation, str(question.get("answer", ""))
    return len(questions), len(arithmetic), rows()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", choices=("finqa", "tatqa"))
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--core", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    total, arithmetic, source_rows = candidates(args.dataset, args.source)
    supported = accepted = matches = mismatches = 0
    examples: list[dict[str, Any]] = []
    iterator = iter(source_rows)
    while True:
        try:
            identity, expression, expected_text = next(iterator)
            expected = Decimal(expected_text.replace(",", "").replace("$", "").replace("%", ""))
            request = finqa_plan(expression) if args.dataset == "finqa" else ExpressionPlan(expression).plan()
            supported += 1
        except StopIteration:
            break
        except (InvalidOperation, KeyError, TypeError, ValueError):
            continue
        try:
            response = run_core(args.core, request)
        except (OSError, subprocess.CalledProcessError, json.JSONDecodeError):
            continue
        if response.get("s") != 0 or "v" not in response:
            continue
        accepted += 1
        actual = Decimal(response["v"])
        if actual == expected:
            matches += 1
        else:
            mismatches += 1
        if len(examples) < 10:
            examples.append({"id": identity, "expression": expression, "expected": str(expected), "actual": str(actual), "match": actual == expected})
    report = {
        "classification": "oracle/structural validation subset; not a model accuracy score",
        "dataset": args.dataset,
        "dataset_items": total,
        "arithmetic_items": arithmetic,
        "bounded_supported": supported,
        "runtime_accepted": accepted,
        "explicit_result_matches": matches,
        "explicit_result_mismatches": mismatches,
        "oracle_subset_match_rate_pct": round(100 * matches / accepted, 3) if accepted else 0,
        "limits": {"steps": 8, "arguments": 2, "request_bytes": 512},
        "examples": examples,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
