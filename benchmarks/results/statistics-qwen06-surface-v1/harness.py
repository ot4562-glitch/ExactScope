#!/usr/bin/env python3
"""Five-arm, one-turn Statistics evaluation with raw evidence and paired aggregation."""
from __future__ import annotations

import argparse
import math
import os
import re
import sys
import urllib.request
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from pathlib import Path

from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from compile_capability import ROOT, canonical, digest, load, verify_bundle
from run_benchmark import CoreBridge, LlamaClient
from statistics_corpus import DEFAULT, validate_rows

SURFACES = {"A": (), "B": ("xs-calc",), "C": ("xs-eval",),
            "D": ("xs-calc", "xs-eval"), "E": ()}
ERRORS = ("AMBIGUOUS_METHOD", "MISSING_INFORMATION", "UNSUPPORTED_OPERATION",
          "INSUFFICIENT_DATA", "ARGUMENT_TYPE", "DOMAIN_ERROR", "DIVIDE_BY_ZERO",
          "RESOURCE_LIMIT", "OVERFLOW", "INVALID_REQUEST", "INVALID_DECIMAL",
          "ARGUMENT_COUNT", "PRECISION_UNRESOLVED")
POLICY = ('Return one JSON object only: {"v":"exact decimal answer"}, '
          '{"e":"typed error name"}, or one allowed ExactScope request. '
          'Use a tool for supported calculations when available. Never invent missing '
          'values or choose unspecified methods. Round final statistics answers to six '
          'fractional places, half even, omit trailing zeros. '
          'For missing sample/population use AMBIGUOUS_METHOD; missing weights use '
          'MISSING_INFORMATION; unsupported methods use UNSUPPORTED_OPERATION.\n')


def namespaced(grammar, prefix):
    # Rename only rule identifiers; preserve quoted literals and character classes.
    token = r'"(?:\\.|[^"\\])*"|\[(?:\\.|[^\]\\])*\]|[A-Za-z][A-Za-z0-9-]*'
    return re.sub(token, lambda m: m[0] if m[0][0] in '\"[' else prefix + m[0], grammar)


def surface(bundle, arm):
    tools = SURFACES[arm]
    alternatives = ["failure"] if tools else ["answer", "failure"]
    grammars = []
    for index, name in enumerate(tools):
        prefix = f"lane{index}-"
        alternatives.append(prefix + "root")
        grammars.append(namespaced((bundle / (name + ".gbnf")).read_text(), prefix))
    grammar = "root ::= " + " | ".join(alternatives) + "\n"
    grammar += 'answer ::= "{" ws "\\\"v\\\"" ws ":" ws decimal ws "}" ws\n'
    grammar += 'failure ::= "{" ws "\\\"e\\\"" ws ":" ws error ws "}" ws\n'
    grammar += 'error ::= ' + " | ".join('"\\\"' + e + '\\\""' for e in ERRORS) + "\n"
    grammar += 'decimal ::= "\\\"" "-"? ("0" | [1-9] [0-9]{0,95}) ("." [0-9]{1,95})? "\\\""\nws ::= [ \\t\\n\\r]*\n'
    grammar += "\n".join(grammars)
    prompt = POLICY
    if tools:
        prompt = prompt.replace('Return one JSON object only: {"v":"exact decimal answer"}, '
                                '{"e":"typed error name"}, or one allowed ExactScope request.',
                                'Return one allowed ExactScope request or {"e":"typed error name"}. '
                                'Do not output a numeric answer yourself.')
    if "xs-eval" in tools:
        catalog = load((bundle / "catalog.json").read_bytes())
        prompt += "xs_eval request: {\"op\":\"operation\",\"a\":[[\"decimal\",...],...]}.\n"
        prompt += "\n".join(op["sig"] for op in catalog["operations"]) + "\n"
    if "xs-calc" in tools:
        prompt += ('xs_calc request: {"p":[{"o":"add","a":["1","2"]}]}. '
                   '1-8 steps; add/sub/mul/div/powi have 2 arguments, sqrt has 1. '
                   'Exact decimal strings or backward #0..#7 results; powi exponent -32..32.\n')
    schemas = {name: load((bundle / (name + ".tool.json")).read_bytes())["function"]["parameters"]
               for name in tools}
    return {"prompt": prompt, "grammar": grammar, "schemas": schemas,
            "top_level_tool_count": len(tools),
            "visible_semantic_operation_count": len(load((bundle / "catalog.json").read_bytes())["operations"])
            if "xs-eval" in tools else 0,
            "schema_bytes": sum(len((bundle / (name + ".tool.json")).read_bytes()) for name in tools)}


def finite_decimal(value):
    if not isinstance(value, str) or not re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", value):
        return None
    try:
        result = Decimal(value)
        return result if result.is_finite() else None
    except InvalidOperation:
        return None


def score(row, text, assets, core):
    record = {"id": row["id"], "family": row["family"], "state": row["state"],
              "generated_text": text, "call_attempted": False, "valid_call": None,
              "accepted_call": None, "operation_selection": None, "argument_extraction": None,
              "plan_steps": None, "core_response": None, "core_bridge_ms": None,
              "result_fidelity": None, "failure_fidelity": None, "model_turns": 1}
    final = None
    try:
        reply = load(text)
    except (ValueError, TypeError):
        reply = None
    if isinstance(reply, dict):
        lane = "xs-calc" if "p" in reply else ("xs-eval" if "op" in reply else None)
        if lane:
            record["call_attempted"] = True
            record["valid_call"] = lane in assets["schemas"] and Draft202012Validator(
                assets["schemas"][lane]).is_valid(reply)
            if lane == "xs-eval" and row["call"] is not None:
                record["operation_selection"] = reply.get("op") == row["call"]["op"]
                record["argument_extraction"] = reply.get("a") == row["call"]["a"]
            if lane == "xs-calc" and isinstance(reply.get("p"), list):
                record["plan_steps"] = len(reply["p"])
            if record["valid_call"]:
                response, elapsed = core.call("request", reply)
                record["core_response"], record["core_bridge_ms"] = response, elapsed
                record["accepted_call"] = response.get("s") == 0
                final = {"v": response["v"]} if response.get("s") == 0 and "v" in response else {"e": response.get("e")}
                # One-turn host renderer copies the authoritative response, no second model turn.
                if response.get("s") == 0:
                    record["result_fidelity"] = True
                else:
                    record["failure_fidelity"] = "v" not in response
        elif not assets["schemas"] and set(reply) == {"v"} and finite_decimal(reply["v"]) is not None:
            final = reply
        elif set(reply) == {"e"} and reply["e"] in ERRORS:
            final = reply
    expected = row["expected"]
    numeric = finite_decimal(final.get("v")) if final else None
    correct = False
    if final:
        if "v" in expected:
            if numeric is not None:
                # Scoring equivalence only: never rewrite the host's authoritative result.
                # xs_calc retains up to 18 places; semantic Statistics publishes six.
                try:
                    with localcontext() as context:
                        context.prec = 120
                        correct = numeric.quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN) == Decimal(expected["v"])
                except InvalidOperation:
                    correct = False
        else:
            correct = final.get("e") == expected["e"] and "v" not in final
    record.update(final=final, correct=correct, wrong_numeric=numeric is not None and not correct,
                  ambiguity_preserved=correct if row["state"] == "ambiguous" else None,
                  fidelity_source="host-renderer", plan_selection=None,
                  plan_selection_reason="no unique gold plan; final answer scored independently")
    return record


def ratio(numerator, denominator, reason="non-positive denominator"):
    applicable = denominator is not None and denominator > 0
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if applicable else None,
            "reason": None if applicable else ("unmeasured denominator" if denominator is None else reason)}


def mean_metric(rows, key):
    values = [r[key] for r in rows if r.get(key) is not None]
    return {"sum": sum(values), "count": len(values),
            "mean": sum(values) / len(values) if values else None}


def aggregate(records, costs=None):
    if not records:
        raise ValueError("empty benchmark")
    by_arm = {}
    for record in records:
        arm = record["arm"]
        if arm not in SURFACES or (arm in by_arm and record["id"] in by_arm[arm]):
            raise ValueError("unknown arm or duplicate per-item evidence")
        by_arm.setdefault(arm, {})[record["id"]] = record
    if not {"A", "B", "C", "D"} <= by_arm.keys():
        raise ValueError("paired A/B/C/D records required")
    expected_ids = set(by_arm["A"])
    for arm, rows in by_arm.items():
        if set(rows) != expected_ids:
            raise ValueError(f"unpaired item set for arm {arm}")
        for identifier, row in rows.items():
            if row["family"] != by_arm["A"][identifier]["family"]:
                raise ValueError("inconsistent task-family labels")
    result = {"arms": {}}
    for arm, items in by_arm.items():
        rows = list(items.values())
        summary = {key: mean_metric(rows, key) for key in (
            "correct", "wrong_numeric", "valid_call", "accepted_call", "operation_selection",
            "argument_extraction", "result_fidelity", "failure_fidelity", "ambiguity_preserved",
            "generated_request_tokens", "prompt_tokens", "completion_tokens", "model_turns",
            "plan_steps", "model_ms", "core_bridge_ms")}
        summary["tool_penalty"] = ratio(sum(by_arm["A"][i]["correct"] and not r["correct"] for i, r in items.items()), len(rows))
        result["arms"][arm] = summary
    a = result["arms"]["A"]["correct"]["mean"]
    d = result["arms"]["D"]["correct"]["mean"]
    e = result["arms"].get("E", {}).get("correct", {}).get("mean")
    result["crr"] = ratio(d - a, e - a if e is not None else None, "larger reference does not outperform baseline")
    result["crr"]["scores"] = {"A": a, "D": d, "E": e}
    # Costs are explicit incremental D-minus-A measurements, never inferred from ceilings.
    costs = costs or {}
    for key, value in costs.items():
        if key not in ("artifact_bytes", "resident_bytes", "prompt_tokens", "added_ms", "joules"):
            raise ValueError(f"unknown cost: {key}")
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
            raise ValueError("costs must be finite measured numbers or null")
    result["incremental_costs"] = costs
    scales = {"artifact_bytes": 102400, "resident_bytes": 1024,
              "prompt_tokens": 1, "added_ms": 1, "joules": 1}
    result["density"] = {}
    for key, scale in scales.items():
        raw = costs.get(key)
        entry = ratio(d - a, raw / scale if raw is not None else None)
        entry.update(raw_denominator=raw, denominator_unit=key, denominator_scale=scale)
        result["density"][key] = entry
    reduction = result["arms"]["A"]["wrong_numeric"]["mean"] - result["arms"]["D"]["wrong_numeric"]["mean"]
    result["wrong_number_density"] = ratio(reduction, costs.get("artifact_bytes") / 102400 if costs.get("artifact_bytes") is not None else None)
    result["families"] = {}
    families = sorted({r["family"] for r in records})
    if len(families) > 1:
        for family in families:
            # Shared artifact cost cannot be independently allocated to one family.
            result["families"][family] = aggregate([r for r in records if r["family"] == family])
    return result


def tokenize(base_url, text):
    url = base_url.removesuffix("/v1").rstrip("/") + "/tokenize"
    request = urllib.request.Request(url, data=canonical({"content": text, "add_special": False}),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        body = load(response.read())
    if not isinstance(body.get("tokens"), list):
        raise ValueError("llama.cpp /tokenize did not return tokens")
    return len(body["tokens"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, default=ROOT / "adapters/capabilities/statistics-core-8-ai-r1")
    parser.add_argument("--corpus", type=Path, default=DEFAULT)
    parser.add_argument("--core", type=Path, default=ROOT / "target/debug" / ("exactscope-core.exe" if os.name == "nt" else "exactscope-core"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = verify_bundle(args.bundle)
    config = load(args.config.read_bytes())
    for kind in ("small", "larger"):
        if kind not in config:
            continue
        for field in ("base_url", "model", "model_sha256", "tokenizer_id", "quantization", "runtime_revision", "hardware", "context_size", "threads"):
            if not config[kind].get(field):
                raise ValueError(f"missing {kind}.{field}")
    if "small" not in config:
        raise ValueError("small model configuration required")
    rows = [load(line) for line in args.corpus.read_bytes().splitlines()]
    core = CoreBridge(args.core)
    validate_rows(rows, core)
    args.output.mkdir(parents=True, exist_ok=False)
    metadata = {"config": config, "corpus_sha256": digest(args.corpus.read_bytes()),
                "core_sha256": digest(args.core.read_bytes()),
                "bundle_sha256": digest((args.bundle / "manifest.json").read_bytes()),
                "harness_sha256": digest(Path(__file__).read_text(encoding="utf-8").encode()),
                "profile_measurements": manifest["measurements"],
                "evidence": "model-run", "fidelity_source": "one-turn host renderer",
                "latency_scope": "core_bridge_ms includes process startup, JSON transport and execution"}
    (args.output / "metadata.json").write_bytes(canonical(metadata))
    records = []
    with (args.output / "items.jsonl").open("xb") as output:
        for arm in ("A", "B", "C", "D", "E"):
            if arm == "E" and "larger" not in config:
                continue
            model = config["larger" if arm == "E" else "small"]
            assets = surface(args.bundle, arm)
            (args.output / f"{arm}.gbnf").write_text(assets["grammar"], encoding="utf-8", newline="\n")
            static = {k: v for k, v in assets.items() if k not in ("schemas", "grammar")}
            static.update(grammar_sha256=digest(assets["grammar"].encode()),
                          grammar_bytes=len(assets["grammar"].encode()),
                          prompt_bytes=len(assets["prompt"].encode()),
                          prompt_fragment_tokens=tokenize(model["base_url"], assets["prompt"]),
                          tokenizer_id=model["tokenizer_id"])
            (args.output / f"{arm}.surface.json").write_bytes(canonical(static))
            client = LlamaClient(model["base_url"], model["model"], config.get("timeout_seconds", 120))
            for row in rows:
                body = {"messages": [{"role": "system", "content": assets["prompt"]},
                                     {"role": "user", "content": row["prompt"]}],
                        "grammar": assets["grammar"], "temperature": 0,
                        "seed": config.get("seed", 20260905), "max_tokens": 256}
                reply = client.chat(body)
                text = reply.message.get("content") or ""
                record = score(row, text, assets, core)
                record.update(arm=arm, raw_response=reply.raw, prompt_tokens=reply.input_units,
                              completion_tokens=reply.output_units, model_ms=reply.latency_ms,
                              generated_request_tokens=tokenize(model["base_url"], text),
                              request_sha256=digest(canonical(body)))
                output.write(canonical(record))
                output.flush()
                records.append(record)
    summary = aggregate(records, config.get("incremental_costs"))
    summary["items_sha256"] = digest((args.output / "items.jsonl").read_bytes())
    summary["metadata_sha256"] = digest((args.output / "metadata.json").read_bytes())
    (args.output / "summary.json").write_bytes(canonical(summary))
    print("PASS five-arm benchmark (E optional)")


if __name__ == "__main__":
    main()
