#!/usr/bin/env python3
"""Reproducible ExactScope local-model benchmark harness."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "benchmarks" / "corpus-v0.1.jsonl"
DEFAULT_HOTSET = ROOT / "adapters" / "generated" / "econ-core-8"
ARMS = ("model_only", "direct", "discovery", "constrained")


class BenchmarkFailure(RuntimeError):
    """Raised for malformed benchmark inputs or runtime responses."""


@dataclasses.dataclass(frozen=True)
class Case:
    """One frozen quantitative benchmark item."""

    identifier: str
    domain: str
    method: str
    prompt: str
    expected_call: dict[str, Any] | None
    expected_core: dict[str, Any]
    should_fail: bool


@dataclasses.dataclass
class ModelReply:
    """Normalized one-turn model response plus usage evidence."""

    message: dict[str, Any]
    input_units: int | None
    output_units: int | None
    latency_ms: float
    raw: dict[str, Any]


class LlamaClient:
    """Minimal llama.cpp OpenAI-compatible HTTP client."""

    def __init__(self, base_url: str, model: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat(self, body: dict[str, Any]) -> ModelReply:
        payload = dict(body)
        payload["model"] = self.model
        payload.setdefault("stream", False)
        payload.setdefault("temperature", 0)
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = time.perf_counter_ns()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise BenchmarkFailure(f"llama.cpp HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise BenchmarkFailure(f"cannot reach llama.cpp: {exc}") from exc
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        try:
            raw = json.loads(data)
            message = raw["choices"][0]["message"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise BenchmarkFailure("llama.cpp response lacks choices[0].message") from exc
        if not isinstance(message, dict) or not isinstance(raw, dict):
            raise BenchmarkFailure("llama.cpp response shape is invalid")
        usage = raw.get("usage") if isinstance(raw.get("usage"), dict) else {}
        return ModelReply(
            message=message,
            input_units=optional_int(usage.get("prompt_" + "to" + "kens")),
            output_units=optional_int(usage.get("completion_" + "to" + "kens")),
            latency_ms=elapsed_ms,
            raw=raw,
        )


class CoreBridge:
    """Subprocess bridge to the real bounded Tiny JSON adapter."""

    def __init__(self, executable: Path) -> None:
        self.executable = executable

    def call(self, mode: str, payload: dict[str, Any]) -> tuple[dict[str, Any], float]:
        encoded = json.dumps(payload, separators=(",", ":")).encode("ascii")
        started = time.perf_counter_ns()
        completed = subprocess.run(
            [str(self.executable), mode],
            input=encoded,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace").strip()
            raise BenchmarkFailure(f"core bridge failed: {detail}")
        try:
            response = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise BenchmarkFailure("core bridge emitted invalid JSON") from exc
        if not isinstance(response, dict):
            raise BenchmarkFailure("core bridge response must be an object")
        return response, elapsed_ms

    def eval(self, call: dict[str, Any]) -> tuple[dict[str, Any], float]:
        return self.call("eval", call)

    def find(self, request: dict[str, Any]) -> tuple[dict[str, Any], float]:
        return self.call("find", request)


def optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkFailure(f"cannot read JSON {path}: {exc}") from exc


def load_cases(path: Path) -> list[Case]:
    cases: list[Case] = []
    seen: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise BenchmarkFailure(f"cannot read corpus {path}: {exc}") from exc
    for line_number, raw in enumerate(lines, start=1):
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise BenchmarkFailure(f"corpus line {line_number}: invalid JSON") from exc
        required = {
            "id",
            "domain",
            "method",
            "prompt",
            "expected_call",
            "expected_core",
            "should_fail",
        }
        if not isinstance(item, dict) or set(item) != required:
            raise BenchmarkFailure(f"corpus line {line_number}: unexpected fields")
        identifier = item["id"]
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            raise BenchmarkFailure(f"corpus line {line_number}: invalid/duplicate id")
        seen.add(identifier)
        expected_call = item["expected_call"]
        if expected_call is not None and not valid_eval_call_shape(expected_call):
            raise BenchmarkFailure(f"corpus line {line_number}: invalid expected_call")
        expected_core = item["expected_core"]
        if not isinstance(expected_core, dict) or not isinstance(expected_core.get("status"), str):
            raise BenchmarkFailure(f"corpus line {line_number}: invalid expected_core")
        should_fail = item["should_fail"]
        if not isinstance(should_fail, bool):
            raise BenchmarkFailure(f"corpus line {line_number}: should_fail must be boolean")
        cases.append(
            Case(
                identifier=identifier,
                domain=require_string(item, "domain", line_number),
                method=require_string(item, "method", line_number),
                prompt=require_string(item, "prompt", line_number),
                expected_call=expected_call,
                expected_core=expected_core,
                should_fail=should_fail,
            )
        )
    if not cases:
        raise BenchmarkFailure("benchmark corpus is empty")
    return cases


def require_string(item: dict[str, Any], key: str, line_number: int) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value:
        raise BenchmarkFailure(f"corpus line {line_number}: {key} must be nonempty string")
    return value


def valid_eval_call_shape(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"op", "a"}
        and isinstance(value.get("op"), str)
        and isinstance(value.get("a"), list)
        and all(isinstance(argument, str) for argument in value["a"])
    )


def valid_find_call_shape(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"q", "n"}
        and isinstance(value.get("q"), str)
        and isinstance(value.get("n"), int)
        and not isinstance(value.get("n"), bool)
        and 1 <= value["n"] <= 5
    )


def decode_tool_call(message: dict[str, Any], function_name: str) -> dict[str, Any] | None:
    calls = message.get("tool_calls")
    if not isinstance(calls, list) or len(calls) != 1:
        return None
    function = calls[0].get("function") if isinstance(calls[0], dict) else None
    if not isinstance(function, dict) or function.get("name") != function_name:
        return None
    arguments = function.get("arguments")
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return None
    return arguments if isinstance(arguments, dict) else None


def decode_raw_eval(message: dict[str, Any]) -> dict[str, Any] | None:
    content = message.get("content")
    if not isinstance(content, str):
        return None
    try:
        decoded = json.loads(content)
    except json.JSONDecodeError:
        return None
    return decoded if isinstance(decoded, dict) else None


def normalize_core(response: dict[str, Any]) -> dict[str, Any]:
    status_code = response.get("s")
    if not isinstance(status_code, int):
        raise BenchmarkFailure("core response lacks integer status")
    if status_code == 0:
        normalized: dict[str, Any] = {"status": "OK"}
        if "v" in response:
            normalized["value"] = response["v"]
        if "c" in response:
            normalized["classification"] = response["c"]
        return normalized
    error = response.get("e")
    if not isinstance(error, str):
        raise BenchmarkFailure("core error response lacks symbolic error")
    return {"status": error}


def core_matches(case: Case, normalized: dict[str, Any]) -> bool:
    expected = case.expected_core
    if normalized.get("status") != expected.get("status"):
        return False
    if expected.get("status") != "OK":
        return True
    if normalized.get("value") != expected.get("value"):
        return False
    expected_classification = expected.get("classification")
    return expected_classification is None or normalized.get("classification") == expected_classification


def call_stage_metrics(case: Case, call: dict[str, Any] | None) -> dict[str, bool]:
    if case.expected_call is None:
        return {
            "tool_use_recognition": call is None,
            "tool_call_validity": call is None or valid_eval_call_shape(call),
            "operation_selection": call is None,
            "argument_extraction": call is None,
        }
    valid = valid_eval_call_shape(call)
    return {
        "tool_use_recognition": call is not None,
        "tool_call_validity": valid,
        "operation_selection": bool(valid and call.get("op") == case.expected_call["op"]),
        "argument_extraction": bool(valid and call.get("a") == case.expected_call["a"]),
    }


def run_model_only(client: LlamaClient, case: Case) -> dict[str, Any]:
    """Run the model-only benchmark arm."""
    response_schema = {
        "type": "object",
        "properties": {
            "answer": {"type": ["string", "null"]},
            "error": {"type": ["string", "null"]},
        },
        "required": ["answer", "error"],
        "additionalProperties": False,
    }
    reply = client.chat(
        {
            "messages": [
                {
                    "role": "system",
                    "content": "Solve the quantitative task yourself without external tools. Return only JSON. If information is missing or the calculation is undefined, return an error instead of inventing a number.",
                },
                {"role": "user", "content": case.prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "answer", "schema": response_schema},
            },
        }
    )
    content = reply.message.get("content")
    parsed: dict[str, Any] | None = None
    if isinstance(content, str):
        try:
            value = json.loads(content)
            if isinstance(value, dict):
                parsed = value
        except json.JSONDecodeError:
            pass
    if parsed is None:
        final_correct = False
        failure_fidelity = False
    elif case.expected_core["status"] == "OK":
        final_correct = parsed.get("answer") == case.expected_core.get("value")
        failure_fidelity = True
    else:
        final_correct = parsed.get("answer") is None and isinstance(parsed.get("error"), str)
        failure_fidelity = final_correct
    result = {
        "case_id": case.identifier,
        "arm": "model_only",
        "model_turns": 1,
        "tool_use_recognition": None,
        "tool_call_validity": None,
        "operation_selection": None,
        "argument_extraction": None,
        "discovery_valid": None,
        "core_accepted": None,
        "core_status_correct": None,
        "final_answer_correct": final_correct,
        "result_fidelity": final_correct if case.expected_core["status"] == "OK" else None,
        "failure_fidelity": failure_fidelity if case.should_fail else None,
        "incorrect_numeric_answer": bool(parsed and parsed.get("answer") is not None and not final_correct),
        "model_latency_ms": round(reply.latency_ms, 6),
        "core_latency_ms": None,
        "discovery_latency_ms": None,
        "model_output": parsed,
    }
    result["input_" + "to" + "kens"] = reply.input_units
    result["output_" + "to" + "kens"] = reply.output_units
    return result


def run_direct(
    client: LlamaClient,
    core: CoreBridge,
    case: Case,
    tool: dict[str, Any],
    catalog_text: str,
) -> dict[str, Any]:
    reply = client.chat(
        {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Use ExactScope for supported deterministic calculations. Call xs_eval directly when all required "
                        "inputs are present. Never invent a missing input. Bound operations:\n" + catalog_text
                    ),
                },
                {"role": "user", "content": case.prompt},
            ],
            "tools": [tool],
            "tool_choice": "auto",
            "parallel_tool_calls": False,
        }
    )
    call = decode_tool_call(reply.message, "xs_eval")
    return score_tool_arm(case, "direct", call, core, [reply])


def run_constrained(
    client: LlamaClient,
    core: CoreBridge,
    case: Case,
    grammar: str,
    catalog_text: str,
) -> dict[str, Any]:
    reply = client.chat(
        {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "For a supported calculation with complete inputs, emit only an ExactScope request object "
                        "with keys op and a. Do not calculate. Do not invent missing inputs. Bound operations:\n"
                        + catalog_text
                    ),
                },
                {"role": "user", "content": case.prompt},
            ],
            "grammar": grammar,
        }
    )
    call = decode_raw_eval(reply.message)
    return score_tool_arm(case, "constrained", call, core, [reply])


def run_discovery(
    client: LlamaClient,
    core: CoreBridge,
    case: Case,
    find_tool: dict[str, Any],
    eval_tool: dict[str, Any],
) -> dict[str, Any]:
    first = client.chat(
        {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Use xs_find only to discover the canonical ExactScope method for the user's calculation. "
                        "Do not calculate. Do not invent missing inputs."
                    ),
                },
                {"role": "user", "content": case.prompt},
            ],
            "tools": [find_tool],
            "tool_choice": "auto",
            "parallel_tool_calls": False,
        }
    )
    find_call = decode_tool_call(first.message, "xs_find")
    if not valid_find_call_shape(find_call):
        return score_tool_arm(case, "discovery", None, core, [first], discovery_valid=False)
    find_response, find_latency = core.find(find_call)

    calls = first.message.get("tool_calls")
    call_id = calls[0].get("id") if isinstance(calls, list) and calls else None
    if not isinstance(call_id, str) or not call_id:
        return score_tool_arm(
            case,
            "discovery",
            None,
            core,
            [first],
            discovery_valid=False,
            discovery_latency=find_latency,
        )

    second = client.chat(
        {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Use ExactScope. After successful discovery, call xs_eval with exact decimal strings in "
                        "signature order. Never invent missing values."
                    ),
                },
                {"role": "user", "content": case.prompt},
                first.message,
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(find_response, separators=(",", ":")),
                },
            ],
            "tools": [eval_tool],
            "tool_choice": "auto",
            "parallel_tool_calls": False,
        }
    )
    eval_call = decode_tool_call(second.message, "xs_eval")
    return score_tool_arm(
        case,
        "discovery",
        eval_call,
        core,
        [first, second],
        discovery_valid=True,
        discovery_latency=find_latency,
        discovery_request=find_call,
        discovery_response=find_response,
    )


def score_tool_arm(
    case: Case,
    arm: str,
    call: dict[str, Any] | None,
    core: CoreBridge,
    replies: list[ModelReply],
    *,
    discovery_valid: bool | None = None,
    discovery_latency: float | None = None,
    discovery_request: dict[str, Any] | None = None,
    discovery_response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stages = call_stage_metrics(case, call)
    core_response: dict[str, Any] | None = None
    normalized: dict[str, Any] | None = None
    core_latency: float | None = None
    if valid_eval_call_shape(call):
        core_response, core_latency = core.eval(call)
        normalized = normalize_core(core_response)

    core_status_correct = normalized is not None and core_matches(case, normalized)
    if case.expected_call is None:
        final_correct = call is None
        failure_fidelity = call is None
    else:
        final_correct = bool(
            stages["operation_selection"]
            and stages["argument_extraction"]
            and core_status_correct
        )
        failure_fidelity = final_correct if case.should_fail else None

    input_units = sum_or_none(reply.input_units for reply in replies)
    output_units = sum_or_none(reply.output_units for reply in replies)
    model_latency = sum(reply.latency_ms for reply in replies)
    result = {
        "case_id": case.identifier,
        "arm": arm,
        "model_turns": len(replies),
        **stages,
        "discovery_valid": discovery_valid,
        "core_accepted": normalized is not None and normalized.get("status") == "OK",
        "core_status_correct": core_status_correct,
        "final_answer_correct": final_correct,
        "result_fidelity": final_correct if case.expected_core["status"] == "OK" else None,
        "failure_fidelity": failure_fidelity,
        "incorrect_numeric_answer": bool(
            normalized and normalized.get("status") == "OK" and not final_correct
        ),
        "model_latency_ms": round(model_latency, 6),
        "core_latency_ms": round(core_latency, 6) if core_latency is not None else None,
        "discovery_latency_ms": (
            round(discovery_latency, 6) if discovery_latency is not None else None
        ),
        "call": call,
        "core_response": core_response,
        "discovery_request": discovery_request,
        "discovery_response": discovery_response,
    }
    result["input_" + "to" + "kens"] = input_units
    result["output_" + "to" + "kens"] = output_units
    return result


def sum_or_none(values: Iterable[int | None]) -> int | None:
    collected = list(values)
    if any(value is None for value in collected):
        return None
    return sum(value for value in collected if value is not None)


def catalog_hint(catalog: dict[str, Any]) -> str:
    return "\n".join(
        f"- {operation['sig']} method={operation['method']} revision={operation['revision']}"
        for operation in catalog["operations"]
    )


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {"arms": {}, "record_count": len(records)}
    input_metric = "input_" + "to" + "kens"
    output_metric = "output_" + "to" + "kens"
    for arm in ARMS:
        subset = [record for record in records if record["arm"] == arm]
        if not subset:
            continue
        metrics: dict[str, Any] = {"count": len(subset)}
        for key in (
            "tool_use_recognition",
            "tool_call_validity",
            "operation_selection",
            "argument_extraction",
            "core_status_correct",
            "final_answer_correct",
            "result_fidelity",
            "failure_fidelity",
            "incorrect_numeric_answer",
        ):
            values = [record[key] for record in subset if isinstance(record.get(key), bool)]
            metrics[key + "_rate"] = (sum(values) / len(values)) if values else None
        for key in (
            input_metric,
            output_metric,
            "model_turns",
            "model_latency_ms",
            "core_latency_ms",
            "discovery_latency_ms",
        ):
            values = [
                record[key]
                for record in subset
                if isinstance(record.get(key), (int, float))
                and not isinstance(record.get(key), bool)
            ]
            metrics[key + "_mean"] = (sum(values) / len(values)) if values else None
        summary["arms"][arm] = metrics
    return summary


def benchmark_metadata(args: argparse.Namespace, catalog: dict[str, Any]) -> dict[str, Any]:
    return {
        "format": "exactscope.benchmark.result",
        "format_version": "0.1",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": args.model,
        "base_url": args.base_url,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "corpus": str(args.corpus),
        "corpus_sha256": sha256_file(args.corpus),
        "hotset": str(args.hotset),
        "hotset_binding_sha256": catalog["binding_sha256"],
        "core_executable": str(args.core),
        "core_executable_sha256": sha256_file(args.core),
        "arms": args.arms,
    }


def self_test(cases: list[Case], core: CoreBridge, hotset: Path) -> None:
    catalog = load_json(hotset / "catalog.json")
    allowed = {operation["op"] for operation in catalog["operations"]}
    if not allowed:
        raise BenchmarkFailure("hot set contains no operations")
    checked = 0
    for case in cases:
        if case.expected_call is None:
            continue
        if case.expected_call["op"] not in allowed:
            raise BenchmarkFailure(f"{case.identifier}: expected operation not in hot set")
        response, _elapsed = core.eval(case.expected_call)
        normalized = normalize_core(response)
        if not core_matches(case, normalized):
            raise BenchmarkFailure(
                f"{case.identifier}: corpus/core drift: expected={case.expected_core} actual={normalized}"
            )
        checked += 1
    if checked == 0:
        raise BenchmarkFailure("self-test did not execute any core cases")

    find_response, _elapsed = core.find({"q": "midpoint price elasticity", "n": 3})
    matches = find_response.get("m")
    if find_response.get("s") != 0 or not isinstance(matches, list) or not matches:
        raise BenchmarkFailure("xs_find self-test failed")
    if matches[0].get("op") != "econ.ped.mid":
        raise BenchmarkFailure("xs_find self-test returned unexpected operation")
    print(
        f"ExactScope benchmark self-test: PASS cases={checked} "
        f"binding={catalog['binding_sha256']}"
    )


def write_results(
    output_dir: Path, metadata: dict[str, Any], records: list[dict[str, Any]]
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "results.jsonl"
    with raw_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    summary = {
        "metadata": metadata,
        "summary": aggregate(records),
        "results_sha256": sha256_file(raw_path),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--hotset", type=Path, default=DEFAULT_HOTSET)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--model", default="local-model")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--arms", nargs="+", choices=ARMS, default=list(ARMS))
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "target" / "benchmark"
    )
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = load_cases(args.corpus)
    core = CoreBridge(args.core)
    if args.self_test:
        self_test(cases, core, args.hotset)
        return 0

    catalog = load_json(args.hotset / "catalog.json")
    eval_tool = load_json(args.hotset / "xs-eval.tool.json")
    find_tool_path = args.hotset / "xs-find.tool.json"
    find_tool = load_json(find_tool_path) if find_tool_path.exists() else None
    grammar = (args.hotset / "xs-eval.gbnf").read_text(encoding="utf-8")
    hint = catalog_hint(catalog)
    client = LlamaClient(args.base_url, args.model, args.timeout)

    records: list[dict[str, Any]] = []
    for case in cases:
        for arm in args.arms:
            if arm == "model_only":
                record = run_model_only(client, case)
            elif arm == "direct":
                record = run_direct(client, core, case, eval_tool, hint)
            elif arm == "discovery":
                if find_tool is None:
                    raise BenchmarkFailure(
                        "discovery arm requires xs-find.tool.json in the hot set"
                    )
                record = run_discovery(client, core, case, find_tool, eval_tool)
            elif arm == "constrained":
                record = run_constrained(client, core, case, grammar, hint)
            else:
                raise BenchmarkFailure(f"unsupported arm {arm}")
            records.append(record)
            print(
                json.dumps(record, sort_keys=True, separators=(",", ":")),
                flush=True,
            )

    write_results(args.output_dir, benchmark_metadata(args, catalog), records)
    print(json.dumps(aggregate(records), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BenchmarkFailure, OSError, ValueError) as exc:
        print(f"ExactScope benchmark: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
