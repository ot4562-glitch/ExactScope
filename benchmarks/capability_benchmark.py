#!/usr/bin/env python3
"""Five-arm, one-turn Statistics evaluation with raw evidence and paired aggregation."""
from __future__ import annotations

import argparse
import math
import os
import re
import subprocess
import sys
import urllib.request
from urllib.parse import urlparse
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from pathlib import Path

from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from compile_capability import ROOT, canonical, digest, load, verify_bundle
from run_benchmark import CoreBridge, LlamaClient
from statistics_corpus import DEFAULT, validate_rows

SURFACES = {"A": (), "B": ("xs-calc",), "C": ("xs-eval",),
            "D": ("xs-calc", "xs-eval"), "E": ()}


class SingleWriterLock:
    """Cross-process advisory lock for one benchmark output directory."""

    def __init__(self, path):
        self.path = Path(path)
        self.handle = None

    def acquire(self):
        if self.handle is not None:
            raise RuntimeError("single-writer lock is already held by this process")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt
                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write(b"0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            handle.close()
            raise RuntimeError(f"benchmark output already has an active writer: {self.path}") from error
        handle.seek(0)
        handle.write(f"pid={os.getpid()}\n".encode("ascii"))
        handle.flush()
        self.handle = handle
        return self

    def release(self):
        handle = self.handle
        if handle is None:
            return
        try:
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()
            self.handle = None

    def __enter__(self):
        return self.acquire()

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False


def writer_lock_path(output):
    output = Path(output)
    return output.with_name(output.name + ".writer.lock")
ERRORS = ("AMBIGUOUS_METHOD", "MISSING_INFORMATION", "UNSUPPORTED_OPERATION",
          "INSUFFICIENT_DATA", "ARGUMENT_TYPE", "DOMAIN_ERROR", "DIVIDE_BY_ZERO",
          "RESOURCE_LIMIT", "OVERFLOW", "INVALID_REQUEST", "INVALID_DECIMAL",
          "ARGUMENT_COUNT", "PRECISION_UNRESOLVED")
POLICY = ('Answer the question as {"v":"decimal answer"}. Round statistics to six '
          'fractional places, half even. Omit trailing zeros.\n')
FAILURE_POLICY = ('Only for variance or standard deviation: if sample/population is unspecified return {"e":"AMBIGUOUS_METHOD"}. '
                  'If required data is missing return {"e":"MISSING_INFORMATION"}. '
                  'For an unsupported method return {"e":"UNSUPPORTED_OPERATION"}.\n')
FINAL_LINE_CONTRACT = "final-line-v1"
FINAL_LINE_RE = re.compile(r"(?im)^\s*Final (answer|error):[ \t]*(.*?)[ \t]*$")


def namespaced(grammar, prefix):
    # Rename only rule identifiers; preserve quoted literals and character classes.
    token = r'"(?:\\.|[^"\\])*"|\[(?:\\.|[^\]\\])*\]|[A-Za-z][A-Za-z0-9-]*'
    return re.sub(token, lambda m: m[0] if m[0][0] in '\"[' else prefix + m[0], grammar)


def surface(bundle, arm, baseline_mode="answer-only"):
    tools = SURFACES[arm]
    alternatives = ["failure"] if tools else ["answer", "failure"]
    grammars = []
    for index, name in enumerate(tools):
        prefix = f"{chr(97 + index)}-"
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
        prompt = 'Translate the question into one ExactScope JSON request. Do not calculate. Replace example values with question values.\n'
    if "xs-eval" in tools:
        catalog = load((bundle / "catalog.json").read_bytes())
        prompt += 'Use xs_eval for a listed method. Example mean request: {"op":"stats.mean","a":[["2","4"]]}.\n'
        prompt += "\n".join(op["sig"] + (": " + op["method"].replace("_", " ")
                            if op["op"].startswith(("stats.var.", "stats.sd.")) else "")
                            for op in catalog["operations"]) + "\n"
    if "xs-calc" in tools:
        prompt += ('Arithmetic xs_calc example (2*3)-1: {"p":[{"o":"mul","a":["2","3"]},'
                   '{"o":"sub","a":["#0","1"]}]}. 1-8 steps: add/sub/mul/div/powi take '
                   '2 arguments, sqrt takes 1. Use decimal strings and backward #0..#7 references.\n')
    prompt = FAILURE_POLICY + prompt
    if arm == "B":
        prompt = ('Translate arithmetic questions into xs_calc JSON. Do not calculate. '
                  'add(x,y)=x+y, sub(x,y)=x-y, mul(x,y)=x*y, div(x,y)=x/y, '
                  'powi(x,n)=x to integer power n, sqrt(x)=square root. Quote numbers. '
                  'Use 1-8 steps. First result is #0, second is #1. References point backward. '
                  'Example (2*3)-1: {"p":[{"o":"mul","a":["2","3"]},'
                  '{"o":"sub","a":["#0","1"]}]}. Replace example values with question values. '
                  'For missing data or an unspecified variance method, return an error object.\n')
    if not tools:
        prompt += 'Example: sum of 2 and 4 -> {"v":"6"}. Use the question data, not example data.\n'
        if baseline_mode == "reasoning":
            prompt = ('Explain the calculation step by step. Your final non-empty line MUST be exactly one '
                      'of these forms: Final answer: 12.34 OR Final error: AMBIGUOUS_METHOD. '
                      'Do not print angle brackets, placeholders, markdown around that final line, or a second final line. '
                      'Round statistics to six fractional places, half even. '
                      + FAILURE_POLICY.replace('return {"e":"', 'say Final error: ').replace('"}', ''))
            grammar = ""
        elif baseline_mode != "answer-only":
            raise ValueError("unsupported baseline mode")
    schemas = {name: load((bundle / (name + ".tool.json")).read_bytes())["function"]["parameters"]
               for name in tools}
    profile = load((bundle / "profile.json").read_bytes())
    for kind, size in (("prompt_fragment", len(prompt.encode())), ("grammar", len(grammar.encode()))):
        if size > profile["model_budget"][kind + "_bytes_max"]:
            raise ValueError(f"actual {arm} {kind} surface exceeds profile budget: {size}")
    return {"prompt": prompt, "grammar": grammar, "schemas": schemas, "arm": arm,
            "baseline_mode": baseline_mode if not tools else None,
            "top_level_tool_count": len(tools),
            "visible_semantic_operation_count": len(load((bundle / "catalog.json").read_bytes())["operations"])
            if "xs-eval" in tools else 0,
            "schema_bytes": sum(len((bundle / (name + ".tool.json")).read_bytes()) for name in tools)}


def hydrate_model_config(config, inventory_path):
    """Resolve model identity fields from one external immutable model inventory."""
    if inventory_path is None:
        return None
    inventory_bytes = inventory_path.read_bytes()
    inventory = load(inventory_bytes)
    models = {entry["id"]: entry for entry in inventory.get("models", [])}
    for kind in ("small", "larger"):
        model_config = config.get(kind)
        if not model_config or "model_inventory_id" not in model_config:
            continue
        identifier = model_config["model_inventory_id"]
        if identifier not in models:
            raise ValueError(f"unknown {kind} model_inventory_id")
        source = models[identifier]
        if source.get("status") != "READY":
            raise ValueError(f"{kind} model inventory entry is not READY")
        requested_context = model_config.get("context_size")
        if requested_context is not None and (
            type(requested_context) is not int or requested_context <= 0 or requested_context > source["context"]
        ):
            raise ValueError(f"{kind}.context_size exceeds model inventory context")
        derived = {
            "model": source["id"],
            "model_sha256": source["sha256"],
            "quantization": source["quantization"],
            "model_bytes": source["size_bytes"],
            "source_revision": source["source_revision"],
            "tokenizer_id": f"{source['original_repository']}@{source['source_revision']}",
        }
        for field, value in derived.items():
            if model_config.get(field) not in (None, value):
                raise ValueError(f"{kind}.{field} conflicts with model inventory")
            model_config[field] = value
    return {"path": str(inventory_path), "sha256": digest(inventory_bytes)}


def managed_profile(reasoning):
    if reasoning in ("off", "none"):
        return "nothink"
    if reasoning == "on":
        return "think"
    if reasoning in ("auto", "default"):
        return "default"
    raise ValueError(f"unsupported managed reasoning mode: {reasoning}")


def managed_server_command(bench_root, python_exe, model_config, seed, timeout):
    """Build one manifest-pinned ExactScopeBench server command from benchmark config."""
    parsed = urlparse(model_config["base_url"])
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.port is None:
        raise ValueError("managed llama server requires an explicit http://127.0.0.1:<port>/v1 base_url")
    if parsed.path.rstrip("/") != "/v1":
        raise ValueError("managed llama server base_url must end in /v1")
    model_id = model_config.get("model_inventory_id")
    if not model_id:
        raise ValueError("managed llama server requires model_inventory_id")
    command = [
        str(python_exe), str(bench_root / "scripts/start_llama_model.py"), model_id,
        "--port", str(parsed.port), "--profile", managed_profile(model_config.get("reasoning")),
        "--ctx-size", str(model_config["context_size"]), "--threads", str(model_config["threads"]),
        "--gpu-layers", str(model_config.get("gpu_layers", "all")),
        "--parallel", str(model_config.get("parallel", 1)), "--seed", str(seed),
        "--timeout", str(timeout),
    ]
    return command


def start_managed_server(bench_root, python_exe, model_config, seed, timeout):
    command = managed_server_command(bench_root, python_exe, model_config, seed, timeout)
    subprocess.run(command, cwd=bench_root, check=True)
    try:
        model_id = model_config["model_inventory_id"]
        metadata_path = bench_root / "results/logs" / model_id / "server-metadata.json"
        metadata_bytes = metadata_path.read_bytes()
        metadata = load(metadata_bytes)
        parsed = urlparse(model_config["base_url"])
        if metadata.get("model_id") != model_id or metadata.get("port") != parsed.port:
            raise ValueError("managed server metadata identity mismatch")
        return {
            "model_id": model_id,
            "port": parsed.port,
            "profile": metadata.get("profile"),
            "server_metadata_sha256": digest(metadata_bytes),
            "server_metadata": metadata,
        }
    except Exception:
        stop_managed_server(bench_root, python_exe)
        raise


def stop_managed_server(bench_root, python_exe):
    subprocess.run(
        [str(python_exe), str(bench_root / "scripts/stop_llama_model.py")],
        cwd=bench_root, check=True,
    )


def generation_budget(config, arm):
    """Resolve a predeclared output-token budget without accidental arm asymmetry."""
    common = config.get("generation_max_tokens")
    legacy = config.get("baseline_max_tokens")
    if common is not None and legacy is not None:
        raise ValueError("generation_max_tokens and baseline_max_tokens cannot be combined")
    if common is not None:
        if type(common) is not int or not 1 <= common <= 4096:
            raise ValueError("generation_max_tokens must be an integer in 1..4096")
        return common
    if legacy is not None:
        if config.get("legacy_asymmetric_token_budget") is not True:
            raise ValueError("baseline_max_tokens requires legacy_asymmetric_token_budget=true")
        if type(legacy) is not int or not 1 <= legacy <= 4096:
            raise ValueError("baseline_max_tokens must be an integer in 1..4096")
        return legacy if arm in ("A", "E") else 256
    return 256


def finite_decimal(value):
    if not isinstance(value, str) or not re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", value):
        return None
    try:
        result = Decimal(value)
        return result if result.is_finite() else None
    except InvalidOperation:
        return None


def parse_reasoning_final(text):
    """Parse only the declared final line; never recover a number from reasoning prose."""
    matches = FINAL_LINE_RE.findall(text)
    if not matches:
        return None, "missing_final_line"
    if len(matches) != 1:
        return None, "multiple_final_lines"
    kind, value = matches[0]
    value = value.strip()
    if kind.lower() == "answer" and finite_decimal(value) is not None:
        return {"v": value}, "ok"
    if kind.lower() == "error" and value in ERRORS:
        return {"e": value}, "ok"
    return None, "malformed_final_line"


def final_matches(expected, final):
    """Return benchmark scoring equivalence without rewriting an authoritative result."""
    if not final:
        return False, None
    numeric = finite_decimal(final.get("v"))
    if "v" in expected:
        if numeric is None:
            return False, None
        try:
            with localcontext() as context:
                context.prec = 120
                correct = numeric.quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN) == Decimal(expected["v"])
            return correct, numeric
        except InvalidOperation:
            return False, numeric
    return final.get("e") == expected["e"] and "v" not in final, numeric


def classify_failure(record, *, correct=None, final=None, parser_status=None, finish_reason=None):
    """Assign one primary failure class without semantic repair or hidden retries."""
    correct = record.get("correct") if correct is None else correct
    final = record.get("final") if final is None else final
    if correct:
        return "correct"
    if finish_reason in ("length", "max_tokens"):
        return "token_limit"
    if record.get("arm") in ("A", "E"):
        if parser_status and parser_status != "ok":
            return parser_status
        if record.get("wrong_numeric") or (final and "v" in final):
            return "wrong_numeric"
        if final and "e" in final:
            return "wrong_error"
        return "baseline_unscored"
    if not record.get("call_attempted"):
        if final and "e" in final:
            return "wrong_error"
        return "no_call"
    if record.get("valid_call") is False:
        return "invalid_call"
    if record.get("operation_selection") is False:
        return "wrong_operation"
    if record.get("argument_extraction") is False:
        return "argument_extraction"
    if record.get("accepted_call") is False:
        return "runtime_rejected"
    if record.get("wrong_numeric") or (final and "v" in final):
        return "wrong_plan_result" if record.get("arm") == "B" else "wrong_numeric"
    if final and "e" in final:
        return "wrong_error"
    return "other_incorrect"


def score(row, text, assets, core, finish_reason=None):
    record = {"id": row["id"], "family": row["family"], "state": row["state"], "arm": assets.get("arm"),
              "generated_text": text, "call_attempted": bool(assets["schemas"]),
              "valid_call": False if assets["schemas"] else None,
              "accepted_call": False if assets["schemas"] else None,
              "operation_selection": None, "argument_extraction": None,
              "plan_steps": None, "core_response": None, "core_bridge_ms": None,
              "result_fidelity": None, "failure_fidelity": None, "model_turns": 1,
              "finish_reason": finish_reason, "final_parser_status": None}
    final = None
    reply = None
    if assets.get("baseline_mode") == "reasoning":
        reply, record["final_parser_status"] = parse_reasoning_final(text)
    else:
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
            record.update(call_attempted=False, valid_call=None, accepted_call=None)
    expected = row["expected"]
    correct, numeric = final_matches(expected, final)
    record.update(final=final, correct=correct, wrong_numeric=numeric is not None and not correct,
                  numeric_correct=correct if row["state"] == "supported" else None,
                  failure_correct=correct if row["state"] != "supported" else None,
                  ambiguity_preserved=correct if row["state"] == "ambiguous" else None,
                  fidelity_source="host-renderer", plan_selection=None,
                  plan_selection_reason="no unique gold plan; final answer scored independently")
    record["failure_class"] = classify_failure(
        record, parser_status=record["final_parser_status"], finish_reason=finish_reason)
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
    for key in ("corpus_sha256", "bundle_sha256"):
        if len({r.get(key) for r in records}) != 1:
            raise ValueError(f"mixed {key} identities")
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
            "correct", "numeric_correct", "failure_correct", "wrong_numeric", "valid_call", "accepted_call", "operation_selection",
            "argument_extraction", "result_fidelity", "failure_fidelity", "ambiguity_preserved",
            "generated_request_tokens", "prompt_tokens", "completion_tokens", "model_turns",
            "plan_steps", "model_ms", "core_bridge_ms", "model_plus_bridge_ms")}
        summary["tool_penalty"] = ratio(sum(by_arm["A"][i]["correct"] and not r["correct"] for i, r in items.items()), len(rows))
        failure_classes = {}
        for row in rows:
            key = row.get("failure_class", "unclassified")
            failure_classes[key] = failure_classes.get(key, 0) + 1
        summary["failure_classes"] = dict(sorted(failure_classes.items()))
        result["arms"][arm] = summary
    a = result["arms"]["A"]["correct"]["mean"]
    d = result["arms"]["D"]["correct"]["mean"]
    e = result["arms"].get("E", {}).get("correct", {}).get("mean")
    result["crr"] = ratio(d - a, e - a if e is not None else None, "larger reference does not outperform baseline")
    result["crr"]["scores"] = {"A": a, "D": d, "E": e}
    # Costs are explicit incremental D-minus-A measurements, never inferred from ceilings.
    costs = dict(costs or {})
    # Infer only complete, paired measurements. Never substitute a design ceiling.
    for cost, metric in (("prompt_tokens", "prompt_tokens"), ("added_ms", "model_plus_bridge_ms")):
        aa, dd = result["arms"]["A"][metric], result["arms"]["D"][metric]
        if costs.get(cost) is None and aa["count"] == dd["count"] == len(expected_ids):
            costs[cost] = dd["mean"] - aa["mean"]
    for key, value in costs.items():
        if key not in ("artifact_bytes", "semantic_artifact_bytes", "resident_bytes", "prompt_tokens", "added_ms", "joules"):
            raise ValueError(f"unknown cost: {key}")
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
            raise ValueError("costs must be finite measured numbers or null")
    result["incremental_costs"] = costs
    scales = {"artifact_bytes": 102400, "semantic_artifact_bytes": 102400,
              "resident_bytes": 1024, "prompt_tokens": 1, "added_ms": 1, "joules": 1}
    result["density"] = {}
    for key, scale in scales.items():
        raw = costs.get(key)
        entry = ratio(d - a, raw / scale if raw is not None else None)
        entry.update(raw_denominator=raw, denominator_unit=key, denominator_scale=scale)
        result["density"][key] = entry
    reduction = result["arms"]["A"]["wrong_numeric"]["mean"] - result["arms"]["D"]["wrong_numeric"]["mean"]
    result["wrong_number_density"] = ratio(
        reduction, costs.get("artifact_bytes") / 102400 if costs.get("artifact_bytes") is not None else None
    )
    result["wrong_number_density_semantic"] = ratio(
        reduction,
        costs.get("semantic_artifact_bytes") / 102400
        if costs.get("semantic_artifact_bytes") is not None else None,
    )
    result["families"] = {}
    families = sorted({r["family"] for r in records})
    if len(families) > 1:
        for family in families:
            # Shared artifact cost cannot be independently allocated to one family.
            result["families"][family] = aggregate([r for r in records if r["family"] == family])
    return result


def bound_artifact_identity(bundle, manifest):
    """Read and verify one immutable bound Wasm artifact identity."""
    profile = load((bundle / "profile.json").read_bytes())
    runtime = bundle / "runtime.wasm"
    bound_sha = profile["bindings"].get("artifact_sha256")
    if not runtime.exists():
        if bound_sha is not None:
            raise ValueError("profile binds an artifact but runtime.wasm is absent")
        return profile, None
    runtime_bytes = runtime.read_bytes()
    runtime_sha = digest(runtime_bytes)
    if bound_sha != runtime_sha:
        raise ValueError("bundle runtime artifact differs from profile binding")
    measurements = manifest.get("artifact_measurements") or {}
    if measurements.get("bytes") != len(runtime_bytes):
        raise ValueError("bundle artifact byte measurement mismatch")
    return profile, {
        "sha256": runtime_sha,
        "bytes": len(runtime_bytes),
        "initial_memory_pages": measurements.get("initial_memory_pages"),
        "maximum_memory_pages": measurements.get("maximum_memory_pages"),
    }


def bind_runtime_evidence(bundle, manifest, config, semantic_baseline_bundle=None):
    """Bind total artifact cost and optional same-boundary semantic marginal cost."""
    profile, artifact = bound_artifact_identity(bundle, manifest)
    identity = {
        "profile_id": profile["profile_id"],
        "profile_revision": profile["profile_revision"],
        "specialization": profile["runtime_surface"].get("specialization", "host-limited"),
        "artifact_sha256": None,
        "artifact_bytes": None,
        "initial_memory_pages": None,
        "artifact_status": manifest.get("artifact_status"),
        "semantic_baseline": None,
        "semantic_artifact_bytes": None,
    }
    costs = dict(config.get("incremental_costs") or {})
    if artifact is not None:
        configured = costs.get("artifact_bytes")
        if configured is not None and configured != artifact["bytes"]:
            raise ValueError("configured artifact cost differs from bound runtime artifact")
        costs["artifact_bytes"] = artifact["bytes"]
        identity.update(artifact_sha256=artifact["sha256"], artifact_bytes=artifact["bytes"],
                        initial_memory_pages=artifact["initial_memory_pages"])

    if semantic_baseline_bundle is None:
        if costs.get("semantic_artifact_bytes") is not None:
            raise ValueError("semantic_artifact_bytes requires a verified semantic baseline bundle")
    else:
        if artifact is None:
            raise ValueError("semantic baseline requires a bound primary runtime artifact")
        baseline_manifest = verify_bundle(semantic_baseline_bundle)
        baseline_profile, baseline_artifact = bound_artifact_identity(semantic_baseline_bundle, baseline_manifest)
        if baseline_artifact is None:
            raise ValueError("semantic baseline bundle must contain runtime.wasm")
        if baseline_profile["runtime_surface"]["xs_eval"]["operations"]:
            raise ValueError("semantic baseline must expose zero semantic operations")
        if baseline_profile["runtime_surface"]["xs_calc"] != profile["runtime_surface"]["xs_calc"]:
            raise ValueError("semantic baseline xs_calc contract differs from benchmark runtime")
        for binding in ("core_revision", "abi_revision"):
            if baseline_profile["bindings"].get(binding) != profile["bindings"].get(binding):
                raise ValueError(f"semantic baseline {binding} differs from benchmark runtime")
        if baseline_profile["runtime_surface"].get("specialization") != profile["runtime_surface"].get("specialization"):
            raise ValueError("semantic baseline specialization differs from benchmark runtime")
        for field in ("target_profile", "wasm_stack_bytes_max", "wasm_initial_pages_max", "wasm_maximum_pages_max"):
            if baseline_profile["device_budget"].get(field) != profile["device_budget"].get(field):
                raise ValueError(f"semantic baseline device policy differs: {field}")
        if baseline_artifact["bytes"] >= artifact["bytes"]:
            raise ValueError("semantic baseline artifact must be smaller than benchmark runtime")
        marginal = artifact["bytes"] - baseline_artifact["bytes"]
        configured = costs.get("semantic_artifact_bytes")
        if configured is not None and configured != marginal:
            raise ValueError("configured semantic artifact cost differs from verified baseline delta")
        costs["semantic_artifact_bytes"] = marginal
        identity["semantic_artifact_bytes"] = marginal
        identity["semantic_baseline"] = {
            "profile_id": baseline_profile["profile_id"],
            "profile_revision": baseline_profile["profile_revision"],
            "artifact_sha256": baseline_artifact["sha256"],
            "artifact_bytes": baseline_artifact["bytes"],
            "bundle_sha256": digest((semantic_baseline_bundle / "manifest.json").read_bytes()),
        }
    config["incremental_costs"] = costs
    return identity


def verify_preregistered_run(preregistration_path, run_id, args, config, runtime_evidence,
                             corpus_generator, corpus_manifest):
    """Fail before model I/O if a frozen run contract does not match the actual inputs."""
    prereg_bytes = preregistration_path.read_bytes()
    prereg = load(prereg_bytes)
    if prereg.get("status") != "FROZEN_READY_FOR_MODEL_RUN_CONFIGURATION":
        raise ValueError("preregistration is not frozen for model execution")
    inventory_contract = prereg["model_inventory"]
    if args.model_inventory is None:
        raise ValueError("preregistered run requires a model inventory")
    expected_inventory = Path(inventory_contract["source"]).resolve()
    inventory_bytes = args.model_inventory.read_bytes()
    if args.model_inventory.resolve() != expected_inventory or digest(inventory_bytes) != inventory_contract["source_sha256"]:
        raise ValueError("preregistered model inventory path or digest mismatch")

    capability = prereg["capability"]
    if args.bundle.resolve() != (ROOT / capability["bundle"]).resolve():
        raise ValueError("preregistered capability bundle path mismatch")
    if args.semantic_baseline_bundle is None or args.semantic_baseline_bundle.resolve() != (ROOT / capability["semantic_baseline_bundle"]).resolve():
        raise ValueError("preregistered semantic baseline bundle path mismatch")
    if runtime_evidence.get("profile_revision") != capability["profile_revision"]:
        raise ValueError("preregistered capability revision mismatch")
    if runtime_evidence.get("artifact_sha256") != capability["artifact_sha256"]:
        raise ValueError("preregistered runtime artifact mismatch")
    if runtime_evidence.get("semantic_artifact_bytes") != capability["semantic_artifact_bytes"]:
        raise ValueError("preregistered semantic artifact delta mismatch")
    semantic_baseline = runtime_evidence.get("semantic_baseline") or {}
    if semantic_baseline.get("artifact_sha256") != capability["semantic_baseline_sha256"]:
        raise ValueError("preregistered semantic baseline artifact mismatch")

    corpus = prereg["corpus"]
    expected_corpus = (ROOT / corpus["path"]).resolve()
    if args.corpus.resolve() != expected_corpus or digest(args.corpus.read_bytes()) != corpus["sha256"]:
        raise ValueError("preregistered corpus path or digest mismatch")
    expected_generator = (ROOT / corpus["generator"]).resolve()
    if corpus_generator.resolve() != expected_generator or digest(corpus_generator.read_bytes()) != corpus["generator_sha256"]:
        raise ValueError("preregistered corpus generator path or digest mismatch")
    expected_manifest = (ROOT / corpus["manifest"]).resolve()
    if corpus_manifest.resolve() != expected_manifest or digest(corpus_manifest.read_bytes()) != corpus["manifest_sha256"]:
        raise ValueError("preregistered corpus manifest path or digest mismatch")

    generation = prereg["generation_contract"]
    if config.get("seed", 20260905) != generation["seed"]:
        raise ValueError("preregistered generation seed mismatch")
    if config.get("baseline_mode", "answer-only") != generation["baseline_mode"]:
        raise ValueError("preregistered baseline mode mismatch")
    if generation.get("temperature") != 0 or generation.get("model_turns") != 1 or generation.get("hidden_retry_or_repair") is not False:
        raise ValueError("unsupported preregistered generation contract")
    for arm in "ABCDE":
        if generation_budget(config, arm) != generation["generation_max_tokens"]:
            raise ValueError("preregistered generation token budget mismatch")

    matches = [entry for entry in prereg["predeclared_runs"] if entry["id"] == run_id]
    if len(matches) != 1:
        raise ValueError("unknown or duplicate preregistered run id")
    run = matches[0]
    small = config.get("small")
    if not small:
        raise ValueError("preregistered run requires a small model")
    for field, expected in (("model", run["small_model_id"]),
                            ("model_sha256", run["small_model_sha256"]),
                            ("quantization", run["small_quantization"]),
                            ("reasoning", run["reasoning_mode"])):
        if small.get(field) != expected:
            raise ValueError(f"preregistered small model mismatch: {field}")
    if small.get("context_size") != generation["context_size"]:
        raise ValueError("preregistered small context size mismatch")

    expected_larger = run.get("larger_model_id")
    larger = config.get("larger")
    if expected_larger is None:
        if larger is not None:
            raise ValueError("stress preregistration does not permit a larger model")
    else:
        if not larger:
            raise ValueError("preregistered paired run requires a larger model")
        for field, expected in (("model", expected_larger),
                                ("model_sha256", run["larger_model_sha256"]),
                                ("quantization", run["larger_quantization"]),
                                ("reasoning", run["reasoning_mode"])):
            if larger.get(field) != expected:
                raise ValueError(f"preregistered larger model mismatch: {field}")
        if larger.get("context_size") != generation["context_size"]:
            raise ValueError("preregistered larger context size mismatch")

    actual_arms = ["A", "B", "C", "D"] + (["E"] if larger else [])
    if actual_arms != run["arms"]:
        raise ValueError("preregistered arm set mismatch")
    return {
        "preregistration_sha256": digest(prereg_bytes),
        "preregistered_run_id": run_id,
        "model_inventory_sha256": digest(inventory_bytes),
        "corpus_generator_sha256": digest(corpus_generator.read_bytes()),
        "corpus_manifest_sha256": digest(corpus_manifest.read_bytes()),
    }


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
    parser.add_argument("--bundle", type=Path, required=True,
                        help="immutable artifact-bound capability bundle under evaluation")
    parser.add_argument("--semantic-baseline-bundle", type=Path)
    parser.add_argument("--corpus", type=Path, default=DEFAULT)
    parser.add_argument("--corpus-generator", type=Path)
    parser.add_argument("--corpus-manifest", type=Path)
    parser.add_argument("--preregistration", type=Path)
    parser.add_argument("--preregistered-run-id")
    parser.add_argument("--model-inventory", type=Path)
    parser.add_argument("--managed-bench-root", type=Path)
    parser.add_argument("--managed-python", type=Path)
    parser.add_argument("--core", type=Path, default=ROOT / "target/debug" / ("exactscope-core.exe" if os.name == "nt" else "exactscope-core"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-new-records", type=int)
    args = parser.parse_args()
    if not args.preflight and args.output is None:
        parser.error("--output is required unless --preflight is used")
    if args.preflight and args.resume:
        parser.error("--resume cannot be combined with --preflight")
    if args.max_new_records is not None and args.max_new_records <= 0:
        parser.error("--max-new-records must be positive")
    default_generator = Path(__file__).with_name("statistics_corpus.py")
    custom_corpus = args.corpus.resolve() != DEFAULT.resolve()
    prereg_fields = (
        args.corpus_generator, args.corpus_manifest, args.preregistration,
        args.preregistered_run_id, args.model_inventory,
    )
    if custom_corpus and not all(prereg_fields):
        parser.error(
            "non-default corpus requires --corpus-generator, --corpus-manifest, "
            "--preregistration, --preregistered-run-id and --model-inventory"
        )
    if any(prereg_fields) and not all(prereg_fields):
        parser.error("preregistered corpus/model arguments must be supplied together")
    corpus_generator = args.corpus_generator or default_generator
    managed_bench_root = args.managed_bench_root.resolve() if args.managed_bench_root else None
    managed_python = args.managed_python
    if managed_bench_root is not None:
        expected_inventory = (managed_bench_root / "manifests/models.json").resolve()
        if args.model_inventory is None or args.model_inventory.resolve() != expected_inventory:
            parser.error("managed bench root requires its own manifests/models.json as --model-inventory")
        if managed_python is None:
            managed_python = managed_bench_root / "venvs/lm-eval/Scripts/python.exe"
        managed_python = managed_python.resolve()
        if not managed_python.is_file():
            parser.error("managed Python interpreter does not exist")
        if not (managed_bench_root / "scripts/start_llama_model.py").is_file() or not (managed_bench_root / "scripts/stop_llama_model.py").is_file():
            parser.error("managed bench root is missing llama server lifecycle scripts")
    elif managed_python is not None:
        parser.error("--managed-python requires --managed-bench-root")

    manifest = verify_bundle(args.bundle)
    config = load(args.config.read_bytes())
    model_inventory_evidence = hydrate_model_config(config, args.model_inventory)
    runtime_evidence = bind_runtime_evidence(
        args.bundle, manifest, config, args.semantic_baseline_bundle
    )
    for kind in ("small", "larger"):
        if kind not in config:
            continue
        for field in ("base_url", "model", "model_sha256", "tokenizer_id", "quantization", "runtime_revision", "hardware", "context_size", "threads"):
            if not config[kind].get(field):
                raise ValueError(f"missing {kind}.{field}")
    if "small" not in config:
        raise ValueError("small model configuration required")

    prereg_evidence = None
    if args.preregistration is not None:
        prereg_evidence = verify_preregistered_run(
            args.preregistration, args.preregistered_run_id, args, config, runtime_evidence,
            corpus_generator, args.corpus_manifest
        )

    rows = [load(line) for line in args.corpus.read_bytes().splitlines()]
    core = CoreBridge(args.core)
    validate_rows(rows, core)
    if args.preflight:
        calls = sum(row["call"] is not None for row in rows)
        print(
            f"PASS benchmark preflight items={len(rows)} runtime_calls={calls} "
            f"artifact_bytes={runtime_evidence.get('artifact_bytes')} "
            f"semantic_artifact_bytes={runtime_evidence.get('semantic_artifact_bytes')}"
        )
        return
    writer_lock = SingleWriterLock(writer_lock_path(args.output)).acquire()
    expected_metadata = {"config": config, "corpus_sha256": digest(args.corpus.read_bytes()),
                         "core_sha256": digest(args.core.read_bytes()),
                         "bundle_sha256": digest((args.bundle / "manifest.json").read_bytes()),
                         "runtime_evidence": runtime_evidence,
                         "model_inventory_evidence": model_inventory_evidence,
                         "preregistration_evidence": prereg_evidence,
                         "managed_execution": {
                             "bench_root": str(managed_bench_root),
                             "python": str(managed_python),
                             "start_script_sha256": digest((managed_bench_root / "scripts/start_llama_model.py").read_bytes()),
                             "stop_script_sha256": digest((managed_bench_root / "scripts/stop_llama_model.py").read_bytes()),
                             "servers": [],
                         } if managed_bench_root is not None else None,
                         "single_writer_lock": {
                             "path": str(writer_lock.path),
                             "mechanism": "msvcrt.locking" if os.name == "nt" else "fcntl.flock",
                         },
                         "corpus_generator_sha256": digest(corpus_generator.read_bytes()),
                         "corpus_manifest_sha256": digest(args.corpus_manifest.read_bytes()) if args.corpus_manifest else None,
                         "harness_sha256": digest(Path(__file__).read_text(encoding="utf-8").encode()),
                         "profile_measurements": manifest["measurements"],
                         "evidence": "model-run", "fidelity_source": "one-turn host renderer",
                         "scoring_contract": FINAL_LINE_CONTRACT,
                         "latency_scope": "core_bridge_ms includes process startup, JSON transport and execution"}
    stable_metadata_keys = tuple(key for key in expected_metadata if key != "managed_execution")
    provenance_files = {
        "harness.py": Path(__file__).read_bytes(),
        "corpus-generator.py": corpus_generator.read_bytes(),
    }
    if args.corpus_manifest is not None:
        provenance_files["corpus-manifest.json"] = args.corpus_manifest.read_bytes()
    if args.preregistration is not None:
        provenance_files["preregistration.json"] = args.preregistration.read_bytes()

    if args.resume:
        if not args.output.is_dir() or not (args.output / "metadata.json").is_file() or not (args.output / "items.jsonl").is_file():
            raise ValueError("resume requires an existing partial benchmark output directory")
        if (args.output / "summary.json").exists():
            raise ValueError("completed benchmark output cannot be resumed")
        metadata = load((args.output / "metadata.json").read_bytes())
        for key in stable_metadata_keys:
            if metadata.get(key) != expected_metadata[key]:
                raise ValueError(f"resume metadata identity mismatch: {key}")
        expected_managed = expected_metadata["managed_execution"]
        actual_managed = metadata.get("managed_execution")
        if (expected_managed is None) != (actual_managed is None):
            raise ValueError("resume managed execution mode mismatch")
        if expected_managed is not None and any(
            actual_managed.get(field) != expected_managed[field]
            for field in ("bench_root", "python", "start_script_sha256", "stop_script_sha256")
        ):
            raise ValueError("resume managed execution identity mismatch")
        for name, data in provenance_files.items():
            path = args.output / name
            if not path.is_file() or path.read_bytes() != data:
                raise ValueError(f"resume provenance mismatch: {name}")
        records = [load(line) for line in (args.output / "items.jsonl").read_bytes().splitlines()]
        output_mode = "ab"
    else:
        args.output.mkdir(parents=True, exist_ok=False)
        metadata = expected_metadata
        (args.output / "metadata.json").write_bytes(canonical(metadata))
        for name, data in provenance_files.items():
            (args.output / name).write_bytes(data)
        records = []
        output_mode = "xb"

    row_ids = {row["id"] for row in rows}
    expected_arms = ("A", "B", "C", "D", "E") if "larger" in config else ("A", "B", "C", "D")
    completed_pairs = set()
    for record in records:
        pair = (record.get("arm"), record.get("id"))
        if pair[0] not in expected_arms or pair[1] not in row_ids:
            raise ValueError("existing benchmark record is outside the frozen arm/corpus identity")
        if pair in completed_pairs:
            raise ValueError("duplicate existing benchmark arm/item record")
        if record.get("corpus_sha256") != expected_metadata["corpus_sha256"] or record.get("bundle_sha256") != expected_metadata["bundle_sha256"]:
            raise ValueError("existing benchmark record identity mismatch")
        completed_pairs.add(pair)
    active_model_kind = None
    run_complete = False
    stop_failure = None
    new_record_count = 0
    limit_reached = False
    try:
        with (args.output / "items.jsonl").open(output_mode) as output:
            for arm in expected_arms:
                pending_rows = [row for row in rows if (arm, row["id"]) not in completed_pairs]
                if not pending_rows:
                    continue
                if args.max_new_records is not None and new_record_count >= args.max_new_records:
                    limit_reached = True
                    break
                model_kind = "larger" if arm == "E" else "small"
                model = config[model_kind]
                if managed_bench_root is not None and active_model_kind != model_kind:
                    if active_model_kind is not None:
                        stop_managed_server(managed_bench_root, managed_python)
                    server_evidence = start_managed_server(
                        managed_bench_root, managed_python, model,
                        config.get("seed", 20260905), config.get("server_start_timeout_seconds", 180),
                    )
                    metadata["managed_execution"]["servers"].append({"kind": model_kind, **server_evidence})
                    active_model_kind = model_kind
                assets = surface(args.bundle, arm, config.get("baseline_mode", "answer-only"))
                (args.output / f"{arm}.gbnf").write_text(assets["grammar"], encoding="utf-8", newline="\n")
                static = {k: v for k, v in assets.items() if k not in ("schemas", "grammar")}
                static.update(grammar_sha256=digest(assets["grammar"].encode()),
                              grammar_bytes=len(assets["grammar"].encode()),
                              prompt_bytes=len(assets["prompt"].encode()),
                              prompt_fragment_tokens=tokenize(model["base_url"], assets["prompt"]),
                              tokenizer_id=model["tokenizer_id"])
                (args.output / f"{arm}.surface.json").write_bytes(canonical(static))
                client = LlamaClient(model["base_url"], model["model"], config.get("timeout_seconds", 120))
                for row in pending_rows:
                    if args.max_new_records is not None and new_record_count >= args.max_new_records:
                        limit_reached = True
                        break
                    body = {"messages": [{"role": "system", "content": assets["prompt"]},
                                         {"role": "user", "content": row["prompt"]}],
                            "temperature": 0, "seed": config.get("seed", 20260905),
                            "max_tokens": generation_budget(config, arm)}
                    if assets["grammar"]:
                        body["grammar"] = assets["grammar"]
                    reply = client.chat(body)
                    text = reply.message.get("content") or ""
                    choice = reply.raw.get("choices", [{}])[0] if isinstance(reply.raw, dict) else {}
                    record = score(row, text, assets, core, choice.get("finish_reason"))
                    record.update(arm=arm, raw_response=reply.raw, prompt_tokens=reply.input_units,
                                  completion_tokens=reply.output_units, model_ms=reply.latency_ms,
                                  model_plus_bridge_ms=reply.latency_ms + (record["core_bridge_ms"] or 0),
                                  generated_request_tokens=tokenize(model["base_url"], text),
                                  corpus_sha256=metadata["corpus_sha256"], bundle_sha256=metadata["bundle_sha256"],
                                  generation_budget=body["max_tokens"],
                                  request_sha256=digest(canonical(body)))
                    output.write(canonical(record))
                    output.flush()
                    records.append(record)
                    completed_pairs.add((arm, row["id"]))
                    new_record_count += 1
                if limit_reached:
                    break
        run_complete = len(completed_pairs) == len(expected_arms) * len(rows)
    finally:
        if managed_bench_root is not None and active_model_kind is not None:
            try:
                stop_managed_server(managed_bench_root, managed_python)
            except Exception as error:
                stop_failure = error
                metadata["managed_execution"]["stop_error"] = repr(error)
        metadata["run_status"] = "complete" if run_complete else "partial"
        metadata["completed_records"] = len(records)
        metadata["new_records_this_invocation"] = new_record_count
        metadata["remaining_records"] = len(expected_arms) * len(rows) - len(completed_pairs)
        (args.output / "metadata.json").write_bytes(canonical(metadata))
    if stop_failure is not None:
        writer_lock.release()
        raise RuntimeError("managed llama-server could not be stopped cleanly") from stop_failure
    if not run_complete:
        print(
            f"PARTIAL benchmark checkpoint completed_records={len(records)} "
            f"new_records={new_record_count} remaining_records={metadata['remaining_records']}"
        )
        writer_lock.release()
        return
    summary = aggregate(records, config.get("incremental_costs"))
    summary["items_sha256"] = digest((args.output / "items.jsonl").read_bytes())
    summary["metadata_sha256"] = digest((args.output / "metadata.json").read_bytes())
    (args.output / "summary.json").write_bytes(canonical(summary))
    writer_lock.release()
    print("PASS five-arm benchmark (E optional)")


if __name__ == "__main__":
    main()
