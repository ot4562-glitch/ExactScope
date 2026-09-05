#!/usr/bin/env python3
"""Reference one-tool ExactScope xs_eval integration for llama.cpp.

The adapter does not calculate. It verifies one explicit capability/model-surface
identity, sends only that generated xs_eval tool to the model, and validates the
returned positional decimal arguments before a real host forwards them to ExactScope.
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
    strict_tool,
    verify_bundle,
)

DEFAULT_ACCEPTANCE = ROOT / "spec/examples/model-surface-acceptance-v0.1.json"
SELF_TEST_SOURCE = ROOT / "adapters/generated/p0-smoke"
DEFAULT_PROMPT = (
    "Using the provided ExactScope tool, calculate signed midpoint price elasticity "
    "when price changes from 10000 to 12000 and quantity changes from 100 to 80."
)
DECIMAL_RE = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$")
MAX_DECIMAL_CHARS = 96
MAX_VECTOR_VALUES = 64
MAX_DECIMAL_LEAVES = 64


class SmokeFailure(RuntimeError):
    """Raised when capability identity or llama.cpp output violates the adapter contract."""


@dataclass(frozen=True)
class CapabilitySurface:
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
            raise SmokeFailure(f"duplicate JSON key in tool arguments: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise SmokeFailure(f"non-finite JSON constant is forbidden: {value}")


def decode_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        raise SmokeFailure("tool arguments must be a JSON object or JSON string")
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_object,
            parse_constant=_reject_json_constant,
        )
    except json.JSONDecodeError as exc:
        raise SmokeFailure(f"tool arguments are not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SmokeFailure("decoded tool arguments must be an object")
    return value


def validate_decimal(value: Any, *, label: str) -> str:
    if not isinstance(value, str):
        raise SmokeFailure(f"{label} must be an exact decimal string")
    if len(value) == 0 or len(value) > MAX_DECIMAL_CHARS or DECIMAL_RE.fullmatch(value) is None:
        raise SmokeFailure(f"{label} is not a canonical ExactScope decimal lexical form")
    return value


def load_capability_surface(
    capability: Path,
    acceptance_policy: Path = DEFAULT_ACCEPTANCE,
) -> CapabilitySurface:
    try:
        manifest = verify_bundle(capability)
        profile = load_json(capability / "profile.json")
        catalog = load_json(capability / "catalog.json")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SmokeFailure(f"invalid capability bundle: {exc}") from exc

    binding = profile.get("bindings", {}).get("surface_contract_sha256")
    contract_path = capability / "surface-contract.json"
    if not isinstance(binding, str) or not contract_path.is_file():
        raise SmokeFailure(
            "llama.cpp reference integration requires explicit v0.1 model-surface negotiation; "
            "legacy unversioned hot sets are not accepted"
        )
    try:
        contract = load_json(contract_path)
        policy = load_json(acceptance_policy)
        check_acceptance(contract, policy)
    except (OSError, ValueError, json.JSONDecodeError, CompatibilityError) as exc:
        raise SmokeFailure(f"model-surface compatibility rejected: {exc}") from exc

    surface = profile.get("runtime_surface")
    if not isinstance(surface, dict):
        raise SmokeFailure("capability runtime surface is missing")
    calc = surface.get("xs_calc")
    find = surface.get("xs_find")
    selected = surface.get("xs_eval", {}).get("operations")
    if not isinstance(calc, dict) or calc.get("enabled") is not False:
        raise SmokeFailure("direct_eval_smoke requires a semantic-only capability with xs_calc disabled")
    if not isinstance(find, dict) or find.get("enabled") is not False:
        raise SmokeFailure("direct_eval_smoke does not expose xs_find")
    if not isinstance(selected, list) or not selected:
        raise SmokeFailure("direct_eval_smoke requires at least one selected xs_eval operation")
    if manifest.get("measurements", {}).get("top_level_tool_count") != 1:
        raise SmokeFailure("direct_eval_smoke requires exactly one model-visible tool")

    required_assets = {"prompt-fragment.txt", "xs-eval.tool.json", "xs-eval.gbnf"}
    contract_assets = {
        record.get("path") for record in contract.get("assets", []) if isinstance(record, dict)
    }
    if not required_assets.issubset(contract_assets):
        raise SmokeFailure("capability model-surface contract does not bind the complete xs_eval adapter surface")

    tool = load_json(capability / "xs-eval.tool.json")
    function = tool.get("function") if isinstance(tool, dict) else None
    if not isinstance(function, dict) or function.get("name") != "xs_eval":
        raise SmokeFailure("capability tool asset is not the xs_eval function contract")
    prompt = (capability / "prompt-fragment.txt").read_text(encoding="utf-8").strip()
    if not prompt:
        raise SmokeFailure("capability prompt fragment is empty")

    return CapabilitySurface(
        root=capability,
        manifest=manifest,
        profile=profile,
        contract=contract,
        catalog=catalog,
        tool=tool,
        prompt=prompt,
        bundle_sha256=(capability / "bundle-sha256.txt").read_text(encoding="ascii").strip(),
        surface_contract_sha256=binding,
    )


def build_request(
    surface: CapabilitySurface,
    model: str,
    prompt: str,
    tool_choice: str,
) -> dict[str, Any]:
    # The compiler already generated the minimal reviewed prompt fragment. Do not
    # rebuild or duplicate the catalog here: token budget is part of the product.
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


def validate_tool_call(response: dict[str, Any], surface: CapabilitySurface) -> dict[str, Any]:
    by_key = {operation["op"]: operation for operation in surface.catalog["operations"]}

    choices = response.get("choices") if isinstance(response, dict) else None
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise SmokeFailure("response must contain exactly one choices entry")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise SmokeFailure("response does not contain choices[0].message")
    calls = message.get("tool_calls")
    if not isinstance(calls, list) or not calls:
        raise SmokeFailure(
            "llama.cpp returned no tool_calls; verify that the model/chat template supports tools "
            "and run llama-server with Jinja tool-call support"
        )
    if len(calls) != 1 or not isinstance(calls[0], dict):
        raise SmokeFailure(f"expected exactly one tool call, got {len(calls)}")
    if calls[0].get("type") not in (None, "function"):
        raise SmokeFailure("tool call type must be function")

    function = calls[0].get("function")
    if not isinstance(function, dict) or function.get("name") != "xs_eval":
        raise SmokeFailure("expected one xs_eval function call")
    arguments = decode_arguments(function.get("arguments"))
    if set(arguments) != {"op", "a"}:
        raise SmokeFailure("xs_eval arguments must contain exactly op and a")

    operation_key = arguments["op"]
    if not isinstance(operation_key, str) or operation_key not in by_key:
        raise SmokeFailure(f"operation {operation_key!r} is not in the bound capability surface")
    values = arguments["a"]
    if not isinstance(values, list):
        raise SmokeFailure("xs_eval a must be an array")

    expected_args = by_key[operation_key]["args"]
    if len(values) != len(expected_args):
        raise SmokeFailure(
            f"operation {operation_key} requires {len(expected_args)} arguments, got {len(values)}"
        )
    decimal_leaves = 0
    for index, (value, metadata) in enumerate(zip(values, expected_args, strict=True)):
        shape = metadata.get("shape")
        label = f"argument {index} for {operation_key}"
        if shape == "scalar":
            validate_decimal(value, label=label)
            decimal_leaves += 1
        elif shape == "vector":
            if not isinstance(value, list) or len(value) > MAX_VECTOR_VALUES:
                raise SmokeFailure(f"{label} must be an array of at most {MAX_VECTOR_VALUES} exact decimals")
            for element_index, element in enumerate(value):
                validate_decimal(element, label=f"{label}[{element_index}]")
            decimal_leaves += len(value)
        else:
            raise SmokeFailure(f"unsupported generated argument shape {shape!r}")
    if decimal_leaves > MAX_DECIMAL_LEAVES:
        raise SmokeFailure(f"xs_eval arguments exceed the {MAX_DECIMAL_LEAVES}-decimal-leaf limit")

    return {
        "capability_bundle_sha256": surface.bundle_sha256,
        "surface_contract_sha256": surface.surface_contract_sha256,
        "binding_sha256": surface.catalog["binding_sha256"],
        "profile_id": surface.profile["profile_id"],
        "profile_revision": surface.profile["profile_revision"],
        "op": operation_key,
        "revision": by_key[operation_key]["revision"],
        "a": values,
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
        raise SmokeFailure(f"llama.cpp HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SmokeFailure(f"cannot reach llama.cpp server: {exc}") from exc
    try:
        decoded = json.loads(
            body,
            object_pairs_hook=_reject_duplicate_object,
            parse_constant=_reject_json_constant,
        )
    except json.JSONDecodeError as exc:
        raise SmokeFailure("llama.cpp response is not JSON") from exc
    if not isinstance(decoded, dict):
        raise SmokeFailure("llama.cpp response must be an object")
    return decoded


def synthetic_response(operation: str, arguments: list[Any]) -> dict[str, Any]:
    return synthetic_response_raw(
        json.dumps({"op": operation, "a": arguments}, separators=(",", ":"))
    )


def synthetic_response_raw(arguments: str) -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "exactscope-smoke",
                            "type": "function",
                            "function": {"name": "xs_eval", "arguments": arguments},
                        }
                    ],
                }
            }
        ]
    }


def prepare_self_test_capability(destination: Path) -> Path:
    """Build a canonical one-op capability fixture from tracked p0-smoke assets."""
    destination.mkdir(parents=True)
    catalog = load_json(SELF_TEST_SOURCE / "catalog.json")
    catalog_bytes = canonical(catalog)
    tool = strict_tool(catalog, load_json(SELF_TEST_SOURCE / "xs-eval.tool.json"))
    tool_bytes = canonical(tool)
    grammar_bytes = (SELF_TEST_SOURCE / "xs-eval.gbnf").read_bytes()
    prompt = (
        "Pass exact decimal strings in signature order. Never guess missing values or methods. "
        "Preserve errors.\n"
        + "\n".join(operation["sig"] for operation in catalog["operations"])
        + "\n"
    )
    prompt_bytes = prompt.encode("ascii")
    task_map = {"price-elasticity-midpoint": ["econ.ped.mid"]}
    task_map_bytes = canonical(task_map)

    profile: dict[str, Any] = {
        "format": "exactscope.capability.profile",
        "format_version": "0.1-draft",
        "profile_id": "llama-direct-eval-self-test",
        "profile_revision": 1,
        "support": "experimental",
        "domain": "economics",
        "task_families": ["price-elasticity-midpoint"],
        "runtime_surface": {
            "xs_calc": {"enabled": False, "plan_revision": None},
            "xs_eval": {"operations": ["econ.ped.mid"]},
            "xs_find": {"enabled": False},
            "model_visible_tools_max": 1,
            "normal_model_turns_max": 1,
            "specialization": "host-limited",
        },
        "model_budget": {
            "generated_request_tokens_max": 128,
            "grammar_bytes_max": 2048,
            "normal_model_turns_max": 1,
            "plan_steps_max": 0,
            "prompt_fragment_bytes_max": 512,
            "request_bytes_max": 512,
            "schema_bytes_max": 2048,
            "semantic_operation_count": 1,
        },
        "device_budget": {"target_profile": "native-static"},
        "bindings": {
            "core_revision": "sha256:" + "0" * 64,
            "abi_revision": catalog["abi"],
            "registry_sha256": digest(canonical(catalog["packs"])),
            "hotset_sha256": catalog["binding_sha256"],
            "tool_schema_sha256": digest(
                canonical({"xs-eval.tool.json": digest(tool_bytes)})
            ),
            "grammar_sha256": digest(
                canonical({"xs-eval.gbnf": digest(grammar_bytes)})
            ),
            "prompt_sha256": digest(
                canonical({"prompt-fragment.txt": digest(prompt_bytes)})
            ),
            "artifact_sha256": None,
            "surface_contract_sha256": None,
            "profile_generator": "llama.cpp-self-test-fixture",
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
        "xs-eval.gbnf": grammar_bytes,
        "xs-eval.tool.json": tool_bytes,
    }
    contract_bytes = canonical(model_surface_contract(profile, catalog, files))
    files["surface-contract.json"] = contract_bytes
    profile["bindings"]["surface_contract_sha256"] = digest(contract_bytes)
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
            "visible_semantic_operation_count": 1,
        },
        "operation_revisions": {"econ.ped.mid": 1},
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
    # A raw generated hot set has no capability/profile/surface identity and must
    # not silently enter the maintained integration path.
    try:
        load_capability_surface(SELF_TEST_SOURCE, acceptance_policy)
    except SmokeFailure:
        pass
    else:
        raise SmokeFailure("raw unversioned hot set unexpectedly passed capability verification")

    with tempfile.TemporaryDirectory(prefix="xs-llama-adapter-") as temporary:
        capability = prepare_self_test_capability(Path(temporary) / "economics-ped")
        surface = load_capability_surface(capability, acceptance_policy)
        request = build_request(surface, "local-model", DEFAULT_PROMPT, "auto")
        if request["messages"][0]["content"] != surface.prompt or len(request["tools"]) != 1:
            raise SmokeFailure("request builder widened or duplicated the compiled model surface")

        valid = validate_tool_call(
            synthetic_response("econ.ped.mid", ["10000", "12000", "100", "80"]),
            surface,
        )
        rejected = [
            synthetic_response("unknown.operation", []),
            synthetic_response("econ.ped.mid", [["10000"], "12000", "100", "80"]),
            synthetic_response("econ.ped.mid", [10000, "12000", "100", "80"]),
            synthetic_response("econ.ped.mid", ["01", "12000", "100", "80"]),
            synthetic_response("econ.ped.mid", ["+10000", "12000", "100", "80"]),
            synthetic_response("econ.ped.mid", ["NaN", "12000", "100", "80"]),
            synthetic_response("econ.ped.mid", ["1" * 97, "12000", "100", "80"]),
            synthetic_response_raw(
                '{"op":"econ.ped.mid","op":"econ.ped.mid","a":["10000","12000","100","80"]}'
            ),
        ]
        for invalid in rejected:
            try:
                validate_tool_call(invalid, surface)
            except SmokeFailure:
                continue
            raise SmokeFailure("offline self-test accepted a malformed or out-of-contract tool call")
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
        raise SmokeFailure("--capability is required outside --self-test")
    surface = load_capability_surface(args.capability, args.acceptance_policy)
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
    except (OSError, KeyError, TypeError, SmokeFailure, json.JSONDecodeError) as exc:
        print(f"exactscope llama.cpp adapter: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
