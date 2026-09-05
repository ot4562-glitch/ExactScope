#!/usr/bin/env python3
"""Reference one-tool ExactScope xs_calc integration for llama.cpp.

The adapter never evaluates arithmetic. It verifies one explicit calc-only
capability/model-surface identity, sends only the generated xs_calc tool to the
model, and validates the returned bounded plan before a real host forwards it to
ExactScope.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from check_model_surface_compat import CompatibilityError, check_acceptance  # noqa: E402
from compile_capability import (  # noqa: E402
    canonical,
    digest,
    load,
    model_surface_contract,
    position_aware_calc_grammar,
    verify_bundle,
)

DEFAULT_ACCEPTANCE = ROOT / "spec/examples/model-surface-acceptance-v0.1.json"
CALC_ADAPTER = ROOT / "adapters/xs-calc-v0.1"
DEFAULT_PROMPT = "Produce the smallest exact xs_calc plan needed for this arithmetic question."
DECIMAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$")
INTEGER_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)$")
REFERENCE_RE = re.compile(r"^#([0-7])$")
MAX_DECIMAL_CHARS = 96
MAX_REQUEST_BYTES = 512
MAX_PLAN_STEPS = 8
BINARY_OPS = {"add", "sub", "mul", "div", "powi"}
UNARY_OPS = {"sqrt"}
PLAN_OPERATIONS = BINARY_OPS | UNARY_OPS


class CalcSmokeFailure(RuntimeError):
    """Raised when capability identity or an xs_calc plan violates the contract."""


@dataclass(frozen=True)
class CalcCapabilitySurface:
    root: Path
    manifest: dict[str, Any]
    profile: dict[str, Any]
    contract: dict[str, Any]
    catalog: dict[str, Any]
    tool: dict[str, Any]
    prompt: str
    bundle_sha256: str
    surface_contract_sha256: str


def load_json(path: Path) -> Any:
    return load(path.read_bytes())


def _reject_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CalcSmokeFailure(f"duplicate JSON key in xs_calc arguments: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise CalcSmokeFailure(f"non-finite JSON constant is forbidden: {value}")


def decode_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        raise CalcSmokeFailure("tool arguments must be a JSON object or JSON string")
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_object,
            parse_constant=_reject_json_constant,
        )
    except json.JSONDecodeError as exc:
        raise CalcSmokeFailure(f"tool arguments are not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise CalcSmokeFailure("decoded xs_calc arguments must be an object")
    return value


def validate_decimal_literal(value: str, *, label: str) -> None:
    if len(value) == 0 or len(value) > MAX_DECIMAL_CHARS or DECIMAL_RE.fullmatch(value) is None:
        raise CalcSmokeFailure(f"{label} is not a canonical ExactScope decimal lexical form")


def validate_operand(value: Any, *, step_index: int, operand_index: int) -> tuple[str, bool]:
    label = f"step {step_index} operand {operand_index}"
    if not isinstance(value, str):
        raise CalcSmokeFailure(f"{label} must be a decimal string or backward # reference")
    reference = REFERENCE_RE.fullmatch(value)
    if reference is not None:
        referenced = int(reference.group(1))
        if referenced >= step_index:
            raise CalcSmokeFailure(
                f"{label} reference {value} is self/forward; only earlier results are allowed"
            )
        return value, True
    if value.startswith("#"):
        raise CalcSmokeFailure(f"{label} is not a valid #0..#7 result reference")
    validate_decimal_literal(value, label=label)
    return value, False


def validate_plan(arguments: dict[str, Any]) -> dict[str, Any]:
    if set(arguments) != {"p"}:
        raise CalcSmokeFailure("xs_calc arguments must contain exactly p")
    steps = arguments["p"]
    if not isinstance(steps, list) or not (1 <= len(steps) <= MAX_PLAN_STEPS):
        raise CalcSmokeFailure("xs_calc p must contain 1-8 steps")

    normalized_steps: list[dict[str, Any]] = []
    for step_index, step in enumerate(steps):
        if not isinstance(step, dict) or set(step) != {"o", "a"}:
            raise CalcSmokeFailure(f"step {step_index} must contain exactly o and a")
        operation = step["o"]
        operands = step["a"]
        if not isinstance(operation, str) or operation not in PLAN_OPERATIONS:
            raise CalcSmokeFailure(f"step {step_index} uses unsupported operation {operation!r}")
        expected_arity = 1 if operation in UNARY_OPS else 2
        if not isinstance(operands, list) or len(operands) != expected_arity:
            raise CalcSmokeFailure(
                f"step {step_index} operation {operation} requires {expected_arity} operand(s)"
            )

        normalized_operands: list[str] = []
        reference_flags: list[bool] = []
        for operand_index, operand in enumerate(operands):
            normalized, is_reference = validate_operand(
                operand,
                step_index=step_index,
                operand_index=operand_index,
            )
            normalized_operands.append(normalized)
            reference_flags.append(is_reference)

        # If the powi exponent is a literal, its static contract can be checked
        # without doing arithmetic. A referenced exponent is left to ExactScope,
        # because only the runtime knows the referenced exact intermediate value.
        if operation == "powi" and not reference_flags[1]:
            exponent = normalized_operands[1]
            if INTEGER_RE.fullmatch(exponent) is None:
                raise CalcSmokeFailure("literal powi exponent must be an exact integer")
            if not (-32 <= int(exponent) <= 32):
                raise CalcSmokeFailure("literal powi exponent must be in -32..32")

        normalized_steps.append({"o": operation, "a": normalized_operands})

    normalized = {"p": normalized_steps}
    encoded = json.dumps(normalized, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    if len(encoded) > MAX_REQUEST_BYTES:
        raise CalcSmokeFailure(
            f"canonical xs_calc request is {len(encoded)} bytes; maximum is {MAX_REQUEST_BYTES}"
        )
    return normalized


def load_calc_surface(
    capability: Path,
    acceptance_policy: Path = DEFAULT_ACCEPTANCE,
) -> CalcCapabilitySurface:
    try:
        manifest = verify_bundle(capability)
        profile = load_json(capability / "profile.json")
        catalog = load_json(capability / "catalog.json")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise CalcSmokeFailure(f"invalid capability bundle: {exc}") from exc

    binding = profile.get("bindings", {}).get("surface_contract_sha256")
    contract_path = capability / "surface-contract.json"
    if not isinstance(binding, str) or not contract_path.is_file():
        raise CalcSmokeFailure(
            "xs_calc reference integration requires explicit v0.1 model-surface negotiation"
        )
    try:
        surface_contract = load_json(contract_path)
        policy = load_json(acceptance_policy)
        check_acceptance(surface_contract, policy)
    except (OSError, ValueError, json.JSONDecodeError, CompatibilityError) as exc:
        raise CalcSmokeFailure(f"model-surface compatibility rejected: {exc}") from exc

    runtime_surface = profile.get("runtime_surface")
    if not isinstance(runtime_surface, dict):
        raise CalcSmokeFailure("capability runtime surface is missing")
    calc = runtime_surface.get("xs_calc")
    selected = runtime_surface.get("xs_eval", {}).get("operations")
    find = runtime_surface.get("xs_find")
    if not isinstance(calc, dict) or calc.get("enabled") is not True \
            or calc.get("plan_revision") != "plan-v0.1":
        raise CalcSmokeFailure("calc reference integration requires xs_calc plan-v0.1")
    if selected != []:
        raise CalcSmokeFailure("calc reference integration requires a calc-only capability")
    if not isinstance(find, dict) or find.get("enabled") is not False:
        raise CalcSmokeFailure("calc reference integration does not expose xs_find")
    if manifest.get("measurements", {}).get("top_level_tool_count") != 1:
        raise CalcSmokeFailure("calc reference integration requires exactly one model-visible tool")
    if catalog.get("operations") != []:
        raise CalcSmokeFailure("calc-only capability catalog must expose zero semantic operations")

    required_assets = {"prompt-fragment.txt", "xs-calc.tool.json", "xs-calc.gbnf"}
    contract_assets = {
        record.get("path")
        for record in surface_contract.get("assets", [])
        if isinstance(record, dict)
    }
    if not required_assets.issubset(contract_assets):
        raise CalcSmokeFailure("model-surface contract does not bind the complete xs_calc surface")

    plan_contract_path = capability / "xs-calc.contract.json"
    if not plan_contract_path.is_file():
        raise CalcSmokeFailure("calc-only capability is missing xs-calc.contract.json")
    plan_contract = load_json(plan_contract_path)
    if (
        plan_contract.get("format") != "exactscope.xs-calc-contract"
        or plan_contract.get("format_version") != 1
        or plan_contract.get("plan_id") != "plan-v0.1"
        or plan_contract.get("plan_revision") != 1
        or plan_contract.get("max_steps") != MAX_PLAN_STEPS
        or set(plan_contract.get("operations", [])) != PLAN_OPERATIONS
    ):
        raise CalcSmokeFailure("unsupported or malformed xs_calc plan contract")

    tool = load_json(capability / "xs-calc.tool.json")
    function = tool.get("function") if isinstance(tool, dict) else None
    if not isinstance(function, dict) or function.get("name") != "xs_calc":
        raise CalcSmokeFailure("capability tool asset is not the xs_calc function contract")
    prompt = (capability / "prompt-fragment.txt").read_text(encoding="utf-8").strip()
    if not prompt:
        raise CalcSmokeFailure("capability prompt fragment is empty")

    return CalcCapabilitySurface(
        root=capability,
        manifest=manifest,
        profile=profile,
        contract=surface_contract,
        catalog=catalog,
        tool=tool,
        prompt=prompt,
        bundle_sha256=(capability / "bundle-sha256.txt").read_text(encoding="ascii").strip(),
        surface_contract_sha256=binding,
    )


def build_request(
    surface: CalcCapabilitySurface,
    model: str,
    prompt: str,
    tool_choice: str,
) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": surface.prompt},
            {"role": "user", "content": prompt},
        ],
        "tools": [surface.tool],
        "tool_choice": tool_choice,
        "parallel_tool_calls": False,
        "stream": False,
        "temperature": 0,
    }


def validate_tool_call(
    response: dict[str, Any],
    surface: CalcCapabilitySurface,
) -> dict[str, Any]:
    choices = response.get("choices") if isinstance(response, dict) else None
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise CalcSmokeFailure("response must contain exactly one choices entry")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise CalcSmokeFailure("response does not contain choices[0].message")
    calls = message.get("tool_calls")
    if not isinstance(calls, list) or len(calls) != 1 or not isinstance(calls[0], dict):
        raise CalcSmokeFailure("expected exactly one xs_calc tool call")
    if calls[0].get("type") not in (None, "function"):
        raise CalcSmokeFailure("tool call type must be function")
    function = calls[0].get("function")
    if not isinstance(function, dict) or function.get("name") != "xs_calc":
        raise CalcSmokeFailure("expected one xs_calc function call")
    plan = validate_plan(decode_arguments(function.get("arguments")))
    return {
        "capability_bundle_sha256": surface.bundle_sha256,
        "surface_contract_sha256": surface.surface_contract_sha256,
        "binding_sha256": surface.catalog["binding_sha256"],
        "profile_id": surface.profile["profile_id"],
        "profile_revision": surface.profile["profile_revision"],
        "plan_id": "plan-v0.1",
        "plan_revision": 1,
        "plan": plan,
    }


def post_json(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise CalcSmokeFailure(f"llama.cpp HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise CalcSmokeFailure(f"cannot reach llama.cpp server: {exc}") from exc
    try:
        decoded = json.loads(
            body,
            object_pairs_hook=_reject_duplicate_object,
            parse_constant=_reject_json_constant,
        )
    except json.JSONDecodeError as exc:
        raise CalcSmokeFailure("llama.cpp response is not JSON") from exc
    if not isinstance(decoded, dict):
        raise CalcSmokeFailure("llama.cpp response must be an object")
    return decoded


def synthetic_response(plan: dict[str, Any]) -> dict[str, Any]:
    return synthetic_response_raw(json.dumps(plan, separators=(",", ":")))


def synthetic_response_raw(arguments: str) -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "exactscope-calc-smoke",
                            "type": "function",
                            "function": {"name": "xs_calc", "arguments": arguments},
                        }
                    ],
                }
            }
        ]
    }


def prepare_self_test_capability(destination: Path) -> Path:
    destination.mkdir(parents=True)
    contract = load_json(CALC_ADAPTER / "contract.json")
    contract_bytes = canonical(contract)
    tool_bytes = canonical(load_json(CALC_ADAPTER / "xs-calc.tool.json"))
    grammar_bytes = position_aware_calc_grammar()
    grammar_source_bytes = canonical(
        {
            "kind": "position-aware-derived-v1",
            "base_contract_sha256": digest(contract_bytes),
            "rule": "step i permits decimal literals and only #0..#(i-1) result references",
        }
    )
    prompt_bytes = (
        "xs_calc: 1-8 add/sub/mul/div/powi/sqrt steps; backward # references only.\n"
    ).encode("ascii")

    catalog = {
        "format": "exactscope.hotset",
        "format_version": "0.1",
        "name": "llama-calc-self-test",
        "abi": "1.0",
        "binding_sha256": digest(b"llama-calc-self-test-hotset-v0.1"),
        "operations": [],
        "packs": [],
    }
    catalog_bytes = canonical(catalog)
    task_map_bytes = canonical({"arithmetic-baseline": []})

    profile: dict[str, Any] = {
        "format": "exactscope.capability.profile",
        "format_version": "0.1-draft",
        "profile_id": "llama-calc-self-test",
        "profile_revision": 7,
        "support": "experimental",
        "domain": "statistics",
        "task_families": ["arithmetic-baseline"],
        "runtime_surface": {
            "xs_calc": {"enabled": True, "plan_revision": "plan-v0.1"},
            "xs_eval": {"operations": []},
            "xs_find": {"enabled": False},
            "model_visible_tools_max": 1,
            "normal_model_turns_max": 1,
            "specialization": "statistics-selected-wasm",
        },
        "model_budget": {
            "generated_request_tokens_max": 256,
            "grammar_bytes_max": 4096,
            "normal_model_turns_max": 1,
            "plan_steps_max": 8,
            "prompt_fragment_bytes_max": 1024,
            "request_bytes_max": 512,
            "schema_bytes_max": 4096,
            "semantic_operation_count": 0,
        },
        "device_budget": {
            "target_profile": "no-import-wasm",
            "artifact_bytes_max": 131072,
            "resident_bytes_max": None,
            "scratch_bytes_max": None,
            "imports_max": 0,
            "wasm_stack_bytes_max": 16384,
            "wasm_initial_pages_max": 1,
            "wasm_maximum_pages_max": 1,
        },
        "bindings": {
            "core_revision": "sha256:" + "0" * 64,
            "abi_revision": catalog["abi"],
            "registry_sha256": digest(canonical([])),
            "hotset_sha256": catalog["binding_sha256"],
            "tool_schema_sha256": digest(
                canonical({"xs-calc.tool.json": digest(tool_bytes)})
            ),
            "grammar_sha256": digest(
                canonical({"xs-calc.gbnf": digest(grammar_bytes)})
            ),
            "prompt_sha256": digest(
                canonical({"prompt-fragment.txt": digest(prompt_bytes)})
            ),
            "artifact_sha256": None,
            "surface_contract_sha256": None,
            "profile_generator": "llama.cpp-calc-self-test-fixture",
        },
        "evidence": {
            "conformance_suite": None,
            "conformance_sha256": None,
            "benchmark_mapping": None,
            "benchmark_mapping_sha256": None,
            "qualification_records": [],
            "model_result_bundles": [],
        },
    }

    files = {
        "catalog.json": catalog_bytes,
        "prompt-fragment.txt": prompt_bytes,
        "task-map.json": task_map_bytes,
        "xs-calc.contract.json": contract_bytes,
        "xs-calc.gbnf": grammar_bytes,
        "xs-calc.grammar-source.json": grammar_source_bytes,
        "xs-calc.tool.json": tool_bytes,
    }
    surface_contract_bytes = canonical(model_surface_contract(profile, catalog, files))
    files["surface-contract.json"] = surface_contract_bytes
    profile["bindings"]["surface_contract_sha256"] = digest(surface_contract_bytes)
    profile_bytes = canonical(profile)
    files["profile.json"] = profile_bytes

    manifest = {
        "format": "exactscope.capability.bundle",
        "format_version": "0.1",
        "files": {name: digest(data) for name, data in sorted(files.items())},
        "measurements": {
            "prompt_fragment_bytes": len(prompt_bytes),
            "schema_bytes": len(tool_bytes),
            "grammar_bytes": len(grammar_bytes),
            "top_level_tool_count": 1,
            "visible_semantic_operation_count": 0,
        },
        "operation_revisions": {},
        "artifact_status": "self-test fixture; unbound and never executed",
    }
    for name, data in files.items():
        (destination / name).write_bytes(data)
    manifest_bytes = canonical(manifest)
    (destination / "manifest.json").write_bytes(manifest_bytes)
    (destination / "bundle-sha256.txt").write_text(
        digest(manifest_bytes) + "\n", encoding="ascii"
    )
    return destination


def run_self_test(acceptance_policy: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="xs-llama-calc-adapter-") as temporary:
        capability = prepare_self_test_capability(Path(temporary) / "calc-only")
        surface = load_calc_surface(capability, acceptance_policy)
        request = build_request(surface, "local-model", DEFAULT_PROMPT, "auto")
        if request["messages"][0]["content"] != surface.prompt or len(request["tools"]) != 1:
            raise CalcSmokeFailure("request builder widened or duplicated the compiled calc surface")

        valid_plan = {
            "p": [
                {"o": "mul", "a": ["2", "3"]},
                {"o": "sub", "a": ["#0", "1"]},
            ]
        }
        valid = validate_tool_call(synthetic_response(valid_plan), surface)

        invalid_plans: list[dict[str, Any]] = [
            {"p": []},
            {"p": [{"o": "add", "a": ["1", "2"]}] * 9},
            {"p": [{"o": "unknown", "a": ["1", "2"]}]},
            {"p": [{"o": "sqrt", "a": ["4", "5"]}]},
            {"p": [{"o": "add", "a": [1, "2"]}]},
            {"p": [{"o": "add", "a": ["01", "2"]}]},
            {"p": [{"o": "add", "a": ["+1", "2"]}]},
            {"p": [{"o": "add", "a": ["NaN", "2"]}]},
            {"p": [{"o": "add", "a": ["#8", "2"]}]},
            {"p": [{"o": "add", "a": ["#0", "2"]}]},
            {
                "p": [
                    {"o": "add", "a": ["1", "2"]},
                    {"o": "mul", "a": ["#1", "3"]},
                ]
            },
            {"p": [{"o": "powi", "a": ["2", "1.5"]}]},
            {"p": [{"o": "powi", "a": ["2", "33"]}]},
            {"p": [{"o": "add", "a": ["1" * 97, "2"]}]},
        ]
        for invalid in invalid_plans:
            try:
                validate_tool_call(synthetic_response(invalid), surface)
            except CalcSmokeFailure:
                continue
            raise CalcSmokeFailure("offline self-test accepted an invalid xs_calc plan")

        duplicate = synthetic_response_raw(
            '{"p":[{"o":"add","o":"sub","a":["1","2"]}]}'
        )
        try:
            validate_tool_call(duplicate, surface)
        except CalcSmokeFailure:
            pass
        else:
            raise CalcSmokeFailure("offline self-test accepted duplicate JSON keys")

        oversized_plan = {
            "p": [
                {"o": "add", "a": ["1." + "0" * 90, "2"]}
                for _ in range(8)
            ]
        }
        try:
            validate_tool_call(synthetic_response(oversized_plan), surface)
        except CalcSmokeFailure as exc:
            if "maximum is 512" not in str(exc):
                raise
        else:
            raise CalcSmokeFailure("offline self-test accepted a >512-byte canonical plan")

        return valid


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--model", default="local-model")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--capability", type=Path)
    parser.add_argument("--acceptance-policy", type=Path, default=DEFAULT_ACCEPTANCE)
    parser.add_argument("--tool-choice", choices=("auto", "required"), default="auto")
    parser.add_argument("--timeout", type=float, default=120.0)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        print(json.dumps(run_self_test(args.acceptance_policy), sort_keys=True))
        return 0
    if args.capability is None:
        raise CalcSmokeFailure("--capability is required outside --self-test")
    surface = load_calc_surface(args.capability, args.acceptance_policy)
    request = build_request(surface, args.model, args.prompt, args.tool_choice)
    if args.dry_run:
        print(json.dumps(request, indent=2, sort_keys=True))
        return 0

    response = post_json(
        f"{args.base_url.rstrip('/')}/chat/completions",
        request,
        args.timeout,
    )
    validated = validate_tool_call(response, surface)
    print(json.dumps(validated, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, KeyError, TypeError, CalcSmokeFailure, json.JSONDecodeError) as exc:
        print(f"exactscope llama.cpp calc adapter: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
