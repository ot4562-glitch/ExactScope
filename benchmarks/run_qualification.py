#!/usr/bin/env python3
"""Immutable A/C/D local-model qualification for packaged ExactScope capabilities.

The harness has two phases. `preregister` performs no inference; it freezes the
release/model/runtime/corpus/capability/generation identities. `run` re-verifies
those identities byte-for-byte and then performs exactly one request per
(arm, item) with no retry or semantic repair.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from capability_surface import CapabilityError, CapabilitySurface, digest_file, load_capability
from run_benchmark import Case, CoreBridge, core_matches, load_cases, normalize_core

ROOT = Path(__file__).resolve().parents[1]
ARMS = ("A", "C", "D")
MODEL_INTERFACES = ("constrained_json", "native_tools")
DECIMAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$")
REFERENCE_RE = re.compile(r"^#([0-7])$")
INTEGER_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)$")
PLAN_BINARY = {"add", "sub", "mul", "div", "powi"}
PLAN_UNARY = {"sqrt"}
MAX_DECIMAL_CHARS = 96
MAX_VECTOR_VALUES = 64
MAX_DECIMAL_LEAVES = 64
MAX_PLAN_STEPS = 8
MAX_REQUEST_BYTES = 512


class QualificationFailure(RuntimeError):
    """A frozen-input, runtime, response, or evidence failure."""


@dataclass(frozen=True)
class ModelReply:
    message: dict[str, Any]
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: float
    raw: dict[str, Any]
    finish_reason: str | None = None


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise QualificationFailure(f"cannot read JSON {path}: {exc}") from exc


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise QualificationFailure(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json_strict(data: bytes | str) -> Any:
    text = data.decode("utf-8") if isinstance(data, bytes) else data
    try:
        return json.loads(
            text,
            object_pairs_hook=unique_object,
            parse_constant=lambda value: (_ for _ in ()).throw(QualificationFailure(f"non-finite JSON constant: {value}")),
        )
    except json.JSONDecodeError as exc:
        raise QualificationFailure(f"invalid JSON: {exc}") from exc


def optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


class QualificationClient:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout: float,
        seed: int,
        max_tokens: int,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.seed = seed
        self.max_tokens = max_tokens

    def chat(self, body: dict[str, Any]) -> ModelReply:
        payload = dict(body)
        payload["model"] = self.model
        payload["stream"] = False
        payload["temperature"] = 0
        payload["seed"] = self.seed
        payload["max_tokens"] = self.max_tokens
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("ascii"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = time.perf_counter_ns()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body_bytes = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise QualificationFailure(f"llama.cpp HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise QualificationFailure(f"cannot reach llama.cpp: {exc}") from exc
        except TimeoutError as exc:
            raise QualificationFailure("llama.cpp request timed out") from exc
        latency_ms = (time.perf_counter_ns() - started) / 1_000_000
        raw = parse_json_strict(body_bytes)
        if not isinstance(raw, dict):
            raise QualificationFailure("llama.cpp response root must be an object")
        choices = raw.get("choices")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise QualificationFailure("llama.cpp response must contain exactly one choice")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise QualificationFailure("llama.cpp response lacks choices[0].message")
        usage = raw.get("usage") if isinstance(raw.get("usage"), dict) else {}
        finish_reason = choices[0].get("finish_reason")
        return ModelReply(
            message=message,
            input_tokens=optional_int(usage.get("prompt_tokens")),
            output_tokens=optional_int(usage.get("completion_tokens")),
            latency_ms=latency_ms,
            raw=raw,
            finish_reason=finish_reason if isinstance(finish_reason, str) else None,
        )


def decode_single_tool_call(message: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    calls = message.get("tool_calls")
    if calls is None:
        return None
    if not isinstance(calls, list) or len(calls) != 1 or not isinstance(calls[0], dict):
        raise QualificationFailure("response must contain zero or exactly one tool call")
    call = calls[0]
    if call.get("type") not in (None, "function"):
        raise QualificationFailure("tool call type must be function")
    function = call.get("function")
    if not isinstance(function, dict) or not isinstance(function.get("name"), str):
        raise QualificationFailure("tool call has no function name")
    arguments = function.get("arguments")
    if isinstance(arguments, str):
        arguments = parse_json_strict(arguments)
    if not isinstance(arguments, dict):
        raise QualificationFailure("tool arguments must decode to an object")
    return function["name"], arguments


def validate_decimal(value: Any) -> str:
    if not isinstance(value, str) or not (1 <= len(value) <= MAX_DECIMAL_CHARS) or DECIMAL_RE.fullmatch(value) is None:
        raise QualificationFailure("tool argument is not a canonical exact decimal string")
    return value


def catalog_by_key(surface: CapabilitySurface) -> dict[str, dict[str, Any]]:
    return {entry["op"]: entry for entry in surface.catalog["operations"]}


def validate_eval_call(arguments: dict[str, Any], surface: CapabilitySurface) -> dict[str, Any]:
    if set(arguments) != {"op", "a"}:
        raise QualificationFailure("xs_eval arguments must contain exactly op and a")
    operation = arguments.get("op")
    values = arguments.get("a")
    by_key = catalog_by_key(surface)
    if not isinstance(operation, str) or operation not in by_key:
        raise QualificationFailure("xs_eval operation is outside the bound capability")
    if not isinstance(values, list):
        raise QualificationFailure("xs_eval a must be an array")
    metadata = by_key[operation].get("args")
    if not isinstance(metadata, list) or len(values) != len(metadata):
        raise QualificationFailure("xs_eval argument count does not match bound signature")
    leaves = 0
    normalized: list[Any] = []
    for value, expected in zip(values, metadata, strict=True):
        shape = expected.get("shape") if isinstance(expected, dict) else None
        if shape == "scalar":
            normalized.append(validate_decimal(value))
            leaves += 1
        elif shape == "vector":
            if not isinstance(value, list) or len(value) > MAX_VECTOR_VALUES:
                raise QualificationFailure("xs_eval vector exceeds bound shape/size")
            normalized.append([validate_decimal(element) for element in value])
            leaves += len(value)
        else:
            raise QualificationFailure("xs_eval bound signature has unknown shape")
    if leaves > MAX_DECIMAL_LEAVES:
        raise QualificationFailure("xs_eval exceeds decimal-leaf limit")
    normalized_call = {"op": operation, "a": normalized}
    if len(json.dumps(normalized_call, separators=(",", ":"), ensure_ascii=True).encode("ascii")) > MAX_REQUEST_BYTES:
        raise QualificationFailure("xs_eval request exceeds 512-byte limit")
    return normalized_call


def validate_plan_operand(value: Any, step_index: int) -> tuple[str, bool]:
    if not isinstance(value, str):
        raise QualificationFailure("xs_calc operand must be a string")
    reference = REFERENCE_RE.fullmatch(value)
    if reference is not None:
        if int(reference.group(1)) >= step_index:
            raise QualificationFailure("xs_calc result reference is self/forward")
        return value, True
    return validate_decimal(value), False


def validate_calc_call(arguments: dict[str, Any]) -> dict[str, Any]:
    if set(arguments) != {"p"}:
        raise QualificationFailure("xs_calc arguments must contain exactly p")
    steps = arguments.get("p")
    if not isinstance(steps, list) or not (1 <= len(steps) <= MAX_PLAN_STEPS):
        raise QualificationFailure("xs_calc p must contain 1-8 steps")
    normalized_steps: list[dict[str, Any]] = []
    for step_index, step in enumerate(steps):
        if not isinstance(step, dict) or set(step) != {"o", "a"}:
            raise QualificationFailure("xs_calc step must contain exactly o and a")
        operation = step.get("o")
        operands = step.get("a")
        if operation not in PLAN_BINARY | PLAN_UNARY:
            raise QualificationFailure("xs_calc operation is unsupported")
        arity = 1 if operation in PLAN_UNARY else 2
        if not isinstance(operands, list) or len(operands) != arity:
            raise QualificationFailure("xs_calc operation arity mismatch")
        normalized_operands: list[str] = []
        references: list[bool] = []
        for operand in operands:
            normalized, is_reference = validate_plan_operand(operand, step_index)
            normalized_operands.append(normalized)
            references.append(is_reference)
        if operation == "powi" and not references[1]:
            exponent = normalized_operands[1]
            if INTEGER_RE.fullmatch(exponent) is None or not (-32 <= int(exponent) <= 32):
                raise QualificationFailure("literal xs_calc powi exponent must be an integer in -32..32")
        normalized_steps.append({"o": operation, "a": normalized_operands})
    normalized = {"p": normalized_steps}
    if len(json.dumps(normalized, separators=(",", ":"), ensure_ascii=True).encode("ascii")) > MAX_REQUEST_BYTES:
        raise QualificationFailure("xs_calc request exceeds 512-byte limit")
    return normalized


def stage_metrics(case: Case, call: dict[str, Any] | None) -> dict[str, bool]:
    if case.expected_call is None:
        return {
            "tool_use_recognition": call is None,
            "operation_selection": call is None,
            "argument_extraction": call is None,
        }
    return {
        "tool_use_recognition": call is not None,
        "operation_selection": bool(call and call.get("op") == case.expected_call["op"]),
        "argument_extraction": bool(call and call.get("a") == case.expected_call["a"]),
    }


def score_model_only(case: Case, reply: ModelReply) -> dict[str, Any]:
    content = reply.message.get("content")
    parsed: dict[str, Any] | None = None
    malformed = False
    if isinstance(content, str):
        try:
            value = parse_json_strict(content)
            if isinstance(value, dict) and set(value) == {"answer", "error"}:
                parsed = value
            else:
                malformed = True
        except QualificationFailure:
            malformed = True
    else:
        malformed = True
    if parsed is None:
        final_correct = False
        failure_fidelity = False if case.should_fail else None
    elif case.expected_core["status"] == "OK":
        final_correct = parsed.get("answer") == case.expected_core.get("value") and parsed.get("error") is None
        failure_fidelity = None
    else:
        final_correct = parsed.get("answer") is None and isinstance(parsed.get("error"), str) and bool(parsed["error"])
        failure_fidelity = final_correct
    return {
        "expected_lane": "model_only",
        "selected_lane": "model_only",
        "lane_selection": True,
        "tool_use_recognition": None,
        "tool_call_validity": None,
        "operation_selection": None,
        "argument_extraction": None,
        "core_status_correct": None,
        "final_answer_correct": final_correct,
        "result_fidelity": final_correct if case.expected_core["status"] == "OK" else None,
        "failure_fidelity": failure_fidelity,
        "malformed_output": malformed,
        "incorrect_numeric_answer": bool(parsed and parsed.get("answer") is not None and not final_correct),
        "model_output": parsed,
        "call": None,
        "core_response": None,
        "core_latency_ms": None,
    }


def model_only_body(case: Case) -> dict[str, Any]:
    return {
        "messages": [
            {
                "role": "system",
                "content": (
                    "Solve the quantitative task yourself without external tools. Return only JSON with keys answer and error. "
                    "If information is missing or the calculation is undefined, set answer to null and return a nonempty error."
                ),
            },
            {"role": "user", "content": case.prompt},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "answer",
                "schema": {
                    "type": "object",
                    "properties": {
                        "answer": {"type": ["string", "null"]},
                        "error": {"type": ["string", "null"]},
                    },
                    "required": ["answer", "error"],
                    "additionalProperties": False,
                },
            },
        },
    }


def tool_body(case: Case, surface: CapabilitySurface) -> dict[str, Any]:
    tools = [surface.tools["xs_eval"]]
    if surface.calc_enabled:
        tools.append(surface.tools["xs_calc"])
    return {
        "messages": [
            {"role": "system", "content": surface.prompt},
            {"role": "user", "content": case.prompt},
        ],
        "tools": tools,
        "tool_choice": "auto",
        "parallel_tool_calls": False,
    }


def constrained_body(case: Case, surface: CapabilitySurface) -> dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": surface.constrained_prompt},
            {"role": "user", "content": case.prompt},
        ],
        "grammar": surface.grammars["request"],
    }


def score_constrained_reply(
    *,
    case: Case,
    reply: ModelReply,
    surface: CapabilitySurface,
    core: CoreBridge,
    arm: str,
) -> dict[str, Any]:
    expected_lane = "none" if case.expected_call is None else "xs_eval"
    selected_lane = "none"
    call: dict[str, Any] | None = None
    parsed: dict[str, Any] | None = None
    core_response: dict[str, Any] | None = None
    normalized_core: dict[str, Any] | None = None
    core_latency: float | None = None
    request_valid = True
    malformed = False
    try:
        content = reply.message.get("content")
        if not isinstance(content, str):
            raise QualificationFailure("constrained response content must be a JSON string")
        decoded = parse_json_strict(content)
        if not isinstance(decoded, dict):
            raise QualificationFailure("constrained response root must be an object")
        parsed = decoded
        if set(decoded) == {"n"} and decoded.get("n") is True:
            selected_lane = "none"
        elif set(decoded) == {"op", "a"}:
            selected_lane = "xs_eval"
            call = validate_eval_call(decoded, surface)
            core_response, core_latency = core.eval(call)
            normalized_core = normalize_core(core_response)
        elif set(decoded) == {"p"} and surface.calc_enabled:
            selected_lane = "xs_calc"
            call = validate_calc_call(decoded)
            core_response, core_latency = core.call("request", call)
            normalized_core = normalize_core(core_response)
        else:
            raise QualificationFailure("constrained response is outside the frozen request grammar lanes")
    except QualificationFailure:
        request_valid = False
        malformed = True

    eval_call = call if selected_lane == "xs_eval" else None
    stages = stage_metrics(case, eval_call)
    stages["tool_use_recognition"] = (
        selected_lane == "none" if case.expected_call is None else selected_lane != "none"
    )
    lane_correct = selected_lane == expected_lane
    core_status_correct: bool | None = None
    if selected_lane == "xs_eval" and normalized_core is not None:
        core_status_correct = core_matches(case, normalized_core)
    if case.expected_call is None:
        final_correct = lane_correct and request_valid
        failure_fidelity = final_correct
    else:
        final_correct = bool(
            lane_correct
            and request_valid
            and stages["operation_selection"]
            and stages["argument_extraction"]
            and core_status_correct
        )
        failure_fidelity = final_correct if case.should_fail else None
    return {
        "expected_lane": expected_lane,
        "selected_lane": selected_lane,
        "lane_selection": lane_correct,
        **stages,
        "tool_call_validity": request_valid if selected_lane != "none" else None,
        "core_status_correct": core_status_correct,
        "final_answer_correct": final_correct,
        "result_fidelity": final_correct if case.expected_core["status"] == "OK" else None,
        "failure_fidelity": failure_fidelity,
        "malformed_output": malformed,
        "incorrect_numeric_answer": bool(
            normalized_core is not None and normalized_core.get("status") == "OK" and not final_correct
        ),
        "model_output": parsed,
        "call": call,
        "core_response": core_response,
        "core_latency_ms": round(core_latency, 6) if core_latency is not None else None,
    }


def score_tool_reply(
    *,
    case: Case,
    reply: ModelReply,
    surface: CapabilitySurface,
    core: CoreBridge,
    arm: str,
) -> dict[str, Any]:
    expected_lane = "none" if case.expected_call is None else "xs_eval"
    tool_valid = True
    selected_lane = "none"
    call: dict[str, Any] | None = None
    core_response: dict[str, Any] | None = None
    normalized_core: dict[str, Any] | None = None
    core_latency: float | None = None
    malformed = False
    try:
        decoded = decode_single_tool_call(reply.message)
        if decoded is not None:
            function_name, arguments = decoded
            selected_lane = function_name
            if function_name == "xs_eval":
                call = validate_eval_call(arguments, surface)
                core_response, core_latency = core.eval(call)
                normalized_core = normalize_core(core_response)
            elif function_name == "xs_calc" and surface.calc_enabled:
                plan = validate_calc_call(arguments)
                call = plan
                core_response, core_latency = core.call("request", plan)
                normalized_core = normalize_core(core_response)
            else:
                raise QualificationFailure("model selected a tool outside the frozen capability")
    except QualificationFailure:
        tool_valid = False
        malformed = True

    eval_call = call if selected_lane == "xs_eval" else None
    stages = stage_metrics(case, eval_call)
    stages["tool_use_recognition"] = (
        selected_lane == "none" if case.expected_call is None else selected_lane != "none"
    )
    lane_correct = selected_lane == expected_lane
    core_status_correct: bool | None = None
    if selected_lane == "xs_eval" and normalized_core is not None:
        core_status_correct = core_matches(case, normalized_core)
    if case.expected_call is None:
        final_correct = lane_correct and tool_valid
        failure_fidelity = final_correct
    else:
        final_correct = bool(
            lane_correct
            and tool_valid
            and stages["operation_selection"]
            and stages["argument_extraction"]
            and core_status_correct
        )
        failure_fidelity = final_correct if case.should_fail else None
    return {
        "expected_lane": expected_lane,
        "selected_lane": selected_lane,
        "lane_selection": lane_correct,
        **stages,
        "tool_call_validity": tool_valid if selected_lane != "none" else None,
        "core_status_correct": core_status_correct,
        "final_answer_correct": final_correct,
        "result_fidelity": final_correct if case.expected_core["status"] == "OK" else None,
        "failure_fidelity": failure_fidelity,
        "malformed_output": malformed,
        "incorrect_numeric_answer": bool(
            normalized_core is not None and normalized_core.get("status") == "OK" and not final_correct
        ),
        "model_output": None,
        "call": call,
        "core_response": core_response,
        "core_latency_ms": round(core_latency, 6) if core_latency is not None else None,
    }


def run_version(runtime: Path) -> str:
    completed = subprocess.run(
        [str(runtime), "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
    )
    output = completed.stdout.strip()
    if completed.returncode != 0 or not output:
        raise QualificationFailure(f"runtime --version failed: {output}")
    return output


def model_record(inventory_path: Path, model_id: str) -> dict[str, Any]:
    inventory = load_json(inventory_path)
    records = inventory.get("records") if isinstance(inventory, dict) else None
    if not isinstance(records, list):
        raise QualificationFailure("model inventory has no records")
    matches = [record for record in records if isinstance(record, dict) and record.get("id") == model_id]
    if len(matches) != 1:
        raise QualificationFailure(f"model inventory does not contain exactly one {model_id!r}")
    record = dict(matches[0])
    path = Path(record.get("path", ""))
    if record.get("status") != "ready" or not path.is_file():
        raise QualificationFailure("selected model is not ready or file is missing")
    actual_bytes = path.stat().st_size
    actual_sha = sha256_path(path)
    if record.get("bytes") != actual_bytes or record.get("sha256") != actual_sha:
        raise QualificationFailure("selected model bytes/hash differ from inventory")
    record["path"] = str(path.resolve())
    return record


def preregistration_document(args: argparse.Namespace) -> dict[str, Any]:
    corpus = args.corpus.resolve()
    core = args.core.resolve()
    runtime = args.runtime_executable.resolve()
    if not corpus.is_file() or not core.is_file() or not runtime.is_file():
        raise QualificationFailure("corpus/core/runtime executable must exist")
    cases = load_cases(corpus)
    semantic = load_capability(args.semantic_capability, corpus=corpus)
    combined = load_capability(args.combined_capability, corpus=corpus)
    if semantic.calc_enabled or not combined.calc_enabled:
        raise QualificationFailure("semantic/combined capability lane exposure is invalid")
    if semantic.operations != combined.operations:
        raise QualificationFailure("semantic and combined capability operation surfaces differ")
    if semantic.artifact_sha256 != combined.artifact_sha256:
        raise QualificationFailure("semantic and combined capabilities bind different runtimes")
    archive = args.evaluation_archive.resolve()
    if not archive.is_file():
        raise QualificationFailure("evaluation archive does not exist")
    archive_sha256 = sha256_path(archive)
    if archive_sha256 != args.evaluation_archive_sha256:
        raise QualificationFailure("evaluation archive SHA-256 differs from preregistration input")
    inventory_path = args.model_inventory.resolve()
    model = model_record(inventory_path, args.model_id)
    return {
        "format": "exactscope.qualification.preregistration",
        "format_version": "0.1",
        "status": "frozen-before-inference",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "release": {
            "tag": args.release_tag,
            "commit": args.release_commit,
            "evaluation_archive": str(archive),
            "evaluation_archive_sha256": archive_sha256,
        },
        "model_inventory": {
            "path": str(inventory_path),
            "sha256": sha256_path(inventory_path),
        },
        "model": model,
        "runtime": {
            "executable": str(runtime),
            "sha256": sha256_path(runtime),
            "version": run_version(runtime),
            "launch_command": args.runtime_launch_command,
            "base_url": args.base_url.rstrip("/"),
            "server_model_name": args.server_model_name,
            "context_size": args.context_size,
        },
        "generation": {
            "temperature": 0,
            "seed": args.seed,
            "max_tokens": args.max_tokens,
            "timeout_seconds": args.timeout,
            "retry_count": 0,
            "hidden_repair": False,
            "parallel_tool_calls": False,
        },
        "model_interface": {
            "mode": args.model_interface,
            "fallback": "none",
            "native_tool_template_required": args.model_interface == "native_tools",
            "constrained_no_call_sentinel": {"n": True} if args.model_interface == "constrained_json" else None,
        },
        "corpus": {
            "path": str(corpus),
            "sha256": sha256_path(corpus),
            "item_count": len(cases),
        },
        "core": {
            "path": str(core),
            "sha256": sha256_path(core),
        },
        "capabilities": {
            "C": capability_identity(semantic),
            "D": capability_identity(combined),
        },
        "arms": {
            "A": "model-only; no ExactScope model-facing surface",
            "C": f"semantic capability via {args.model_interface}; exact bound xs_eval only plus explicit no-call",
            "D": f"combined capability via {args.model_interface}; exact bound xs_eval + xs_calc plus explicit no-call; semantic corpus expects xs_eval",
        },
        "order": {"type": "arm-major", "arms": list(ARMS), "corpus_order": "file-order"},
        "scoring": {
            "A_success": "exact expected decimal string; failures require null answer and nonempty error",
            "C_D_success": "expected lane + valid call + exact op + exact args + expected ExactScope status/value/classification",
            "D_lane_rule": "xs_calc on a benchmark semantic item is a wrong-lane failure even if its arithmetic result is numerically correct",
            "missing_information": "explicit no-call sentinel for constrained_json; no tool call for native_tools",
        },
        "failure_policy": {
            "single_writer": True,
            "duplicate_arm_item_invalidates": True,
            "partial_output_is_not_complete": True,
            "runtime_or_http_failure_aborts_run": True,
            "retry": "none",
            "manual_correction": False,
        },
    }


def capability_identity(surface: CapabilitySurface) -> dict[str, Any]:
    assets = {}
    for name in sorted(entry.get("path") for entry in surface.contract.get("assets", []) if isinstance(entry, dict)):
        assets[name] = digest_file(surface.root / name)
    return {
        "path": str(surface.root),
        "profile_id": surface.profile["profile_id"],
        "profile_revision": surface.profile["profile_revision"],
        "bundle_sha256": surface.bundle_sha256,
        "surface_contract_sha256": surface.surface_contract_sha256,
        "artifact_sha256": surface.artifact_sha256,
        "hotset_sha256": surface.catalog["binding_sha256"],
        "operations": surface.operations,
        "calc_enabled": surface.calc_enabled,
        "model_surface_assets": assets,
    }


def verify_preregistration(document: dict[str, Any]) -> tuple[list[Case], CoreBridge, CapabilitySurface, CapabilitySurface]:
    if document.get("format") != "exactscope.qualification.preregistration" or document.get("status") != "frozen-before-inference":
        raise QualificationFailure("unsupported or unfrozen preregistration")
    interface = document.get("model_interface")
    if not isinstance(interface, dict) or interface.get("mode") not in MODEL_INTERFACES or interface.get("fallback") != "none":
        raise QualificationFailure("preregistration model interface is missing or unsupported")
    corpus_info = document.get("corpus")
    core_info = document.get("core")
    runtime_info = document.get("runtime")
    model = document.get("model")
    model_inventory = document.get("model_inventory")
    release = document.get("release")
    if not all(
        isinstance(value, dict)
        for value in (corpus_info, core_info, runtime_info, model, model_inventory, release)
    ):
        raise QualificationFailure("preregistration identity sections are incomplete")
    corpus = Path(corpus_info["path"])
    core_path = Path(core_info["path"])
    runtime = Path(runtime_info["executable"])
    model_path = Path(model["path"])
    inventory_path = Path(model_inventory["path"])
    archive = Path(release["evaluation_archive"])
    for path, expected in (
        (corpus, corpus_info["sha256"]),
        (core_path, core_info["sha256"]),
        (runtime, runtime_info["sha256"]),
        (model_path, model["sha256"]),
        (inventory_path, model_inventory["sha256"]),
        (archive, release["evaluation_archive_sha256"]),
    ):
        if not path.is_file() or sha256_path(path) != expected:
            raise QualificationFailure(f"frozen file identity changed: {path}")
    if model_path.stat().st_size != model.get("bytes"):
        raise QualificationFailure("frozen model byte size changed")
    cases = load_cases(corpus)
    if len(cases) != corpus_info.get("item_count"):
        raise QualificationFailure("frozen corpus item count changed")
    capabilities = document.get("capabilities")
    if not isinstance(capabilities, dict) or set(capabilities) != {"C", "D"}:
        raise QualificationFailure("preregistration lacks C/D capability identities")
    semantic = load_capability(Path(capabilities["C"]["path"]), corpus=corpus)
    combined = load_capability(Path(capabilities["D"]["path"]), corpus=corpus)
    for lane, surface in (("C", semantic), ("D", combined)):
        frozen = capabilities[lane]
        current = capability_identity(surface)
        if current != frozen:
            raise QualificationFailure(f"frozen {lane} capability identity changed")
    return cases, CoreBridge(core_path), semantic, combined


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {"record_count": len(records), "arms": {}}
    bool_metrics = (
        "lane_selection",
        "tool_use_recognition",
        "tool_call_validity",
        "operation_selection",
        "argument_extraction",
        "core_status_correct",
        "final_answer_correct",
        "result_fidelity",
        "failure_fidelity",
        "malformed_output",
        "incorrect_numeric_answer",
        "token_limit",
    )
    for arm in ARMS:
        subset = [record for record in records if record["arm"] == arm]
        metrics: dict[str, Any] = {"count": len(subset), "correct": sum(bool(record["final_answer_correct"]) for record in subset)}
        metrics["correct_rate"] = metrics["correct"] / len(subset) if subset else None
        for key in bool_metrics:
            values = [record[key] for record in subset if isinstance(record.get(key), bool)]
            metrics[key + "_count"] = sum(values) if values else None
            metrics[key + "_rate"] = (sum(values) / len(values)) if values else None
        for key in ("input_tokens", "output_tokens", "model_latency_ms", "core_latency_ms"):
            values = [record[key] for record in subset if isinstance(record.get(key), (int, float)) and not isinstance(record.get(key), bool)]
            metrics[key + "_mean"] = (sum(values) / len(values)) if values else None
        summary["arms"][arm] = metrics
    if all(arm in summary["arms"] for arm in ARMS):
        a = summary["arms"]["A"]["correct_rate"]
        c = summary["arms"]["C"]["correct_rate"]
        d = summary["arms"]["D"]["correct_rate"]
        summary["uplift"] = {
            "C_minus_A": c - a if isinstance(a, float) and isinstance(c, float) else None,
            "D_minus_A": d - a if isinstance(a, float) and isinstance(d, float) else None,
            "D_minus_C": d - c if isinstance(c, float) and isinstance(d, float) else None,
        }
    return summary


def evidence_manifest(root: Path) -> dict[str, Any]:
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "SHA256MANIFEST.json":
            files.append({
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_path(path),
            })
    return {"format": "exactscope.qualification.evidence-manifest", "format_version": "0.1", "files": files}


def copy_capability_surface(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination)


def execute_run(preregistration_path: Path, output_dir: Path) -> None:
    if output_dir.exists():
        raise QualificationFailure("output directory already exists; qualification runs are immutable single-writer outputs")
    prereg_bytes = preregistration_path.read_bytes()
    prereg = parse_json_strict(prereg_bytes)
    if not isinstance(prereg, dict):
        raise QualificationFailure("preregistration root must be an object")
    cases, core, semantic, combined = verify_preregistration(prereg)
    generation = prereg["generation"]
    runtime = prereg["runtime"]
    model_interface = prereg["model_interface"]["mode"]
    client = QualificationClient(
        base_url=runtime["base_url"],
        model=runtime["server_model_name"],
        timeout=float(generation["timeout_seconds"]),
        seed=int(generation["seed"]),
        max_tokens=int(generation["max_tokens"]),
    )

    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "preregistration.json").write_bytes(prereg_bytes)
    shutil.copyfile(Path(prereg["model_inventory"]["path"]), output_dir / "model-inventory.json")
    shutil.copyfile(Path(prereg["corpus"]["path"]), output_dir / "corpus.jsonl")
    copy_capability_surface(semantic.root, output_dir / "capability-C")
    copy_capability_surface(combined.root, output_dir / "capability-D")
    raw_path = output_dir / "results.jsonl"
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    status = {
        "format": "exactscope.qualification.run-status",
        "format_version": "0.1",
        "status": "running",
        "started_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "preregistration_sha256": sha256_bytes(prereg_bytes),
    }
    (output_dir / "run-status.json").write_bytes(canonical(status))
    try:
        with raw_path.open("w", encoding="utf-8", newline="\n") as handle:
            for arm in ARMS:
                surface = semantic if arm == "C" else combined if arm == "D" else None
                for case in cases:
                    key = (arm, case.identifier)
                    if key in seen:
                        raise QualificationFailure(f"duplicate arm/item key: {key}")
                    seen.add(key)
                    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    if arm == "A":
                        reply = client.chat(model_only_body(case))
                        scored = score_model_only(case, reply)
                    else:
                        assert surface is not None
                        if model_interface == "constrained_json":
                            reply = client.chat(constrained_body(case, surface))
                            scored = score_constrained_reply(
                                case=case, reply=reply, surface=surface, core=core, arm=arm
                            )
                        else:
                            reply = client.chat(tool_body(case, surface))
                            scored = score_tool_reply(
                                case=case, reply=reply, surface=surface, core=core, arm=arm
                            )
                    record = {
                        "case_id": case.identifier,
                        "arm": arm,
                        "model_interface": "model_only" if arm == "A" else model_interface,
                        "timestamp_utc": started,
                        "model_turns": 1,
                        "input_tokens": reply.input_tokens,
                        "output_tokens": reply.output_tokens,
                        "model_latency_ms": round(reply.latency_ms, 6),
                        "finish_reason": reply.finish_reason,
                        "token_limit": reply.finish_reason == "length",
                        **scored,
                        "raw_model_response": reply.raw,
                    }
                    records.append(record)
                    line = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
                    handle.write(line + "\n")
                    handle.flush()
                    print(line, flush=True)
        expected = len(cases) * len(ARMS)
        if len(records) != expected or len(seen) != expected:
            raise QualificationFailure("run record count is incomplete or duplicated")
        summary = {
            "format": "exactscope.qualification.summary",
            "format_version": "0.1",
            "preregistration_sha256": sha256_bytes(prereg_bytes),
            "results_sha256": sha256_path(raw_path),
            "model": prereg["model"],
            "release": prereg["release"],
            "summary": aggregate(records),
        }
        (output_dir / "summary.json").write_bytes(canonical(summary))
        status.update(
            status="complete",
            completed_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            record_count=len(records),
            results_sha256=sha256_path(raw_path),
        )
        (output_dir / "run-status.json").write_bytes(canonical(status))
    except Exception as exc:
        status.update(
            status="aborted",
            aborted_at_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            record_count=len(records),
            error=f"{type(exc).__name__}: {exc}",
        )
        (output_dir / "run-status.json").write_bytes(canonical(status))
        (output_dir / "SHA256MANIFEST.json").write_bytes(canonical(evidence_manifest(output_dir)))
        raise
    (output_dir / "SHA256MANIFEST.json").write_bytes(canonical(evidence_manifest(output_dir)))
    print(json.dumps(aggregate(records), indent=2, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("preregister")
    pre.add_argument("--release-tag", required=True)
    pre.add_argument("--release-commit", required=True)
    pre.add_argument("--evaluation-archive", type=Path, required=True)
    pre.add_argument("--evaluation-archive-sha256", required=True)
    pre.add_argument("--model-inventory", type=Path, required=True)
    pre.add_argument("--model-id", required=True)
    pre.add_argument("--runtime-executable", type=Path, required=True)
    pre.add_argument("--runtime-launch-command", required=True)
    pre.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    pre.add_argument("--server-model-name", default="local-model")
    pre.add_argument("--context-size", type=int, required=True)
    pre.add_argument("--seed", type=int, default=42)
    pre.add_argument("--max-tokens", type=int, default=256)
    pre.add_argument("--timeout", type=float, default=120.0)
    pre.add_argument("--model-interface", choices=MODEL_INTERFACES, default="constrained_json")
    pre.add_argument("--corpus", type=Path, default=ROOT / "benchmarks/corpus-v0.1.jsonl")
    pre.add_argument("--core", type=Path, required=True)
    pre.add_argument("--semantic-capability", type=Path, required=True)
    pre.add_argument("--combined-capability", type=Path, required=True)
    pre.add_argument("--output", type=Path, required=True)

    run = sub.add_parser("run")
    run.add_argument("--preregistration", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "preregister":
        if args.context_size <= 0 or args.max_tokens <= 0 or args.timeout <= 0:
            raise QualificationFailure("context/max-token/timeout values must be positive")
        if args.output.exists():
            raise QualificationFailure("preregistration output already exists; use a new run identity")
        document = preregistration_document(args)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        data = canonical(document)
        args.output.write_bytes(data)
        print(f"PASS preregistration sha256={sha256_bytes(data)} model={args.model_id} items={document['corpus']['item_count']}")
        return 0
    execute_run(args.preregistration.resolve(), args.output_dir.resolve())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (QualificationFailure, CapabilityError, OSError, ValueError) as exc:
        print(f"ExactScope qualification: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
