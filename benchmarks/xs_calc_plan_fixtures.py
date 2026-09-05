#!/usr/bin/env python3
"""Small hand-reviewable xs_calc reference plans for benchmark attribution.

These fixtures prove representability for selected Statistics cases. Absence of a
fixture is deliberately *not* a proof that no <=8-step algebraic plan exists.
"""
from __future__ import annotations

MAX_STEPS = 8


class PlanBuilder:
    def __init__(self):
        self.steps = []

    def op(self, operation, *args):
        self.steps.append({"o": operation, "a": list(args)})
        return f"#{len(self.steps) - 1}"

    def result(self):
        if len(self.steps) > MAX_STEPS:
            return None
        return {"p": self.steps}


def _sum(builder, values):
    if len(values) < 2:
        return None
    current = builder.op("add", values[0], values[1])
    for value in values[2:]:
        current = builder.op("add", current, value)
    return current


def _weighted_mean(values, weights):
    if len(values) != len(weights) or len(values) < 2:
        return None, None
    builder = PlanBuilder()
    products = [builder.op("mul", value, weight) for value, weight in zip(values, weights)]
    numerator = _sum(builder, products)
    denominator = _sum(builder, weights)
    if numerator is None or denominator is None:
        return None, len(builder.steps)
    builder.op("div", numerator, denominator)
    return builder.result(), len(builder.steps)


def reference_plan(row):
    """Return a proven reference plan or an explicit non-proof status.

    `reference_lowering_exceeds_budget` means this hand-written lowering is too
    long. It does not claim a globally minimal plan or mathematical impossibility.
    """
    call = row.get("call")
    if call is None:
        return {"status": "not_applicable", "reason": "no semantic call in gold"}
    op, args = call.get("op"), call.get("a")
    if not isinstance(args, list) or not args or not isinstance(args[0], list):
        return {"status": "no_verified_reference", "reason": "unsupported gold shape"}
    x = args[0]
    if op == "stats.sum":
        builder = PlanBuilder()
        result = _sum(builder, x)
        if result is None:
            return {"status": "no_verified_reference", "reason": "sum fixture requires at least two values"}
        plan = builder.result()
        return {"status": "verified_reference", "plan": plan, "steps": len(builder.steps)} if plan else {
            "status": "reference_lowering_exceeds_budget", "required_steps": len(builder.steps)}
    if op == "stats.mean":
        builder = PlanBuilder()
        total = _sum(builder, x)
        if total is None:
            return {"status": "no_verified_reference", "reason": "mean fixture requires at least two values"}
        builder.op("div", total, str(len(x)))
        plan = builder.result()
        return {"status": "verified_reference", "plan": plan, "steps": len(builder.steps)} if plan else {
            "status": "reference_lowering_exceeds_budget", "required_steps": len(builder.steps)}
    if op == "stats.mean.weighted" and len(args) == 2 and isinstance(args[1], list):
        plan, steps = _weighted_mean(x, args[1])
        if plan:
            return {"status": "verified_reference", "plan": plan, "steps": steps}
        if steps is not None and steps > MAX_STEPS:
            return {"status": "reference_lowering_exceeds_budget", "required_steps": steps}
        return {"status": "no_verified_reference", "reason": "weighted fixture requires aligned vectors"}
    if op in ("stats.var.pop", "stats.var.sample", "stats.sd.pop", "stats.sd.sample") and len(x) == 2:
        builder = PlanBuilder()
        delta = builder.op("sub", x[0], x[1])
        square = builder.op("powi", delta, "2")
        divisor = "4" if op.endswith("pop") else "2"
        value = builder.op("div", square, divisor)
        if op.startswith("stats.sd."):
            builder.op("sqrt", value)
        return {"status": "verified_reference", "plan": builder.result(), "steps": len(builder.steps)}
    if (op == "stats.corr.pearson" and len(args) == 2 and len(x) == len(args[1]) == 2
            and row.get("expected", {}).get("s") == 0):
        y = args[1]
        builder = PlanBuilder()
        dx = builder.op("sub", x[0], x[1])
        dy = builder.op("sub", y[0], y[1])
        product = builder.op("mul", dx, dy)
        square = builder.op("powi", product, "2")
        magnitude = builder.op("sqrt", square)
        builder.op("div", product, magnitude)
        return {"status": "verified_reference", "plan": builder.result(), "steps": len(builder.steps)}
    return {"status": "no_verified_reference", "reason": "no hand-reviewed <=8-step fixture for this shape"}
