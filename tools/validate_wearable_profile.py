#!/usr/bin/env python3
"""Validate the ExactScope wearable-edge product contract without network access."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "spec" / "examples" / "wearable-edge-profile.json"
SCHEMA_PATH = ROOT / "spec" / "schemas" / "wearable-edge-profile.schema.json"
SPEC_PATH = ROOT / "spec" / "WEARABLE_EDGE_PROFILE_V0_1.md"
ADAPTER_HEADER_PATH = ROOT / "adapters" / "wearable" / "exactscope_wearable_ref.h"
ADAPTER_SOURCE_PATH = ROOT / "adapters" / "wearable" / "exactscope_wearable_ref.c"


class ValidationFailure(Exception):
    """Raised when the wearable product profile is internally inconsistent."""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationFailure(f"{path.relative_to(ROOT)}: invalid JSON: {exc}") from exc


def validate_schema(profile: dict[str, Any], schema: dict[str, Any]) -> None:
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(profile),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path) or "<root>"
        raise ValidationFailure(f"profile schema failure at {location}: {first.message}")


def validate_semantics(profile: dict[str, Any]) -> None:
    limits = profile["hard_limits"]
    targets = profile["product_targets"]
    evidence = profile["evidence"]

    mutable_sum = (
        limits["max_context_bytes"]
        + limits["max_eval_scratch_bytes"]
        + limits["max_pack_mount_arena_bytes"]
        + limits["max_adapter_buffer_bytes"]
    )
    if mutable_sum > limits["max_mutable_runtime_bytes"]:
        raise ValidationFailure(
            "context + scratch + adapter buffers exceed max_mutable_runtime_bytes"
        )

    if limits["max_total_mounted_pack_bytes"] < limits["max_pack_bytes"]:
        raise ValidationFailure("total mounted-pack budget is smaller than one legal pack")
    if limits["max_total_mounted_pack_bytes"] > (
        limits["max_pack_bytes"] * limits["max_mounted_packs"]
    ):
        raise ValidationFailure("total mounted-pack budget exceeds per-pack * pack-count envelope")

    if targets["scalar_eval_p50_us"] > targets["scalar_eval_p99_us"]:
        raise ValidationFailure("scalar eval p50 target cannot exceed p99 target")

    if limits["max_tiny_request_bytes"] > limits["max_adapter_buffer_bytes"]:
        raise ValidationFailure("request cap exceeds adapter-buffer cap")
    if limits["max_tiny_response_bytes"] > limits["max_adapter_buffer_bytes"]:
        raise ValidationFailure("response cap exceeds adapter-buffer cap")

    # These are implementation/spec ceilings already frozen elsewhere in v0.1.
    core_caps = {
        "max_vector_len": 256,
        "max_vm_steps": 64,
        "max_vm_stack": 16,
        "max_result_values": 4,
        "max_operation_key_bytes": 96,
    }
    for key, cap in core_caps.items():
        if limits[key] > cap:
            raise ValidationFailure(f"wearable {key}={limits[key]} exceeds core cap {cap}")

    states = {name: evidence[name] for name in ("latency", "energy", "footprint", "real_device")}
    claim_state = profile["claim_state"]
    if claim_state == "contract-only":
        if any(state != "unmeasured" for state in states.values()):
            raise ValidationFailure("contract-only profile must not carry measured evidence states")
    elif claim_state == "measured":
        required_measured = ("latency", "energy", "footprint", "real_device")
        if any(states[name] == "unmeasured" for name in required_measured):
            raise ValidationFailure("measured claim requires all physical evidence categories to be measured")
    elif claim_state == "qualified":
        if any(state != "measured-pass" for state in states.values()):
            raise ValidationFailure("qualified claim requires measured-pass for every evidence category")
    else:  # schema should make this unreachable
        raise ValidationFailure(f"unknown claim_state {claim_state!r}")

    privacy = profile["privacy_policy"]
    telemetry = set(privacy["allowed_default_telemetry"])
    forbidden_value_keys = {"argument_value", "result_value", "raw_text", "sensor_frame"}
    if telemetry & forbidden_value_keys:
        raise ValidationFailure("default telemetry leaks raw values or sensor content")


def validate_spec_presence(profile: dict[str, Any]) -> None:
    try:
        text = SPEC_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValidationFailure(f"cannot read {SPEC_PATH.relative_to(ROOT)}: {exc}") from exc

    required_tokens = (
        "# ExactScope Wearable Edge Profile v0.1",
        "A/B transaction",
        "airplane mode",
        "10,000",
        "500 uJ",
        "16 KiB",
        "claim_state",
    )
    missing = [token for token in required_tokens if token not in text]
    if missing:
        raise ValidationFailure(f"wearable specification missing required contract text: {missing}")

    if profile["format"] not in text and "wearable-edge-v0.1" not in text:
        raise ValidationFailure("wearable specification does not identify the machine-readable profile")


def parse_adapter_uint_macros() -> dict[str, int]:
    try:
        text = ADAPTER_HEADER_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValidationFailure(
            f"cannot read {ADAPTER_HEADER_PATH.relative_to(ROOT)}: {exc}"
        ) from exc

    macros: dict[str, int] = {}
    pattern = re.compile(
        r"^\s*#define\s+(XSW_REF_[A-Z0-9_]+)\s+((?:0[xX])?[0-9A-Fa-f]+)[uU]?\s*$",
        re.MULTILINE,
    )
    for name, literal in pattern.findall(text):
        macros[name] = int(literal, 0)
    return macros


def validate_adapter_alignment(profile: dict[str, Any]) -> None:
    macros = parse_adapter_uint_macros()
    limits = profile["hard_limits"]
    targets = profile["product_targets"]

    limit_mapping = {
        "max_context_bytes": "XSW_REF_MAX_CONTEXT_BYTES_V1",
        "max_eval_scratch_bytes": "XSW_REF_MAX_EVAL_SCRATCH_BYTES_V1",
        "max_pack_mount_arena_bytes": "XSW_REF_MAX_PACK_MOUNT_ARENA_BYTES_V1",
        "max_adapter_buffer_bytes": "XSW_REF_MAX_ADAPTER_BUFFER_BYTES_V1",
        "max_mutable_runtime_bytes": "XSW_REF_MAX_MUTABLE_RUNTIME_BYTES_V1",
        "max_tiny_request_bytes": "XSW_REF_MAX_TINY_REQUEST_BYTES_V1",
        "max_tiny_response_bytes": "XSW_REF_MAX_TINY_RESPONSE_BYTES_V1",
        "max_pack_bytes": "XSW_REF_MAX_PACK_BYTES_V1",
        "max_total_mounted_pack_bytes": "XSW_REF_MAX_TOTAL_PACK_BYTES_V1",
        "max_mounted_packs": "XSW_REF_MAX_MOUNTED_PACKS_V1",
        "max_vector_len": "XSW_REF_MAX_VECTOR_LEN_V1",
        "max_result_values": "XSW_REF_MAX_RESULT_VALUES_V1",
        "max_operation_key_bytes": "XSW_REF_MAX_OPERATION_KEY_BYTES_V1",
    }
    target_mapping = {
        "scalar_eval_p50_us": "XSW_REF_TARGET_SCALAR_EVAL_P50_US_V1",
        "scalar_eval_p99_us": "XSW_REF_TARGET_SCALAR_EVAL_P99_US_V1",
        "lookup_p99_us": "XSW_REF_TARGET_LOOKUP_P99_US_V1",
        "pack_mount_256k_p99_us": "XSW_REF_TARGET_PACK_MOUNT_256K_P99_US_V1",
        "scalar_eval_energy_uj_excluding_host_wake": "XSW_REF_TARGET_SCALAR_EVAL_ENERGY_UJ_V1",
        "stripped_runtime_plus_fused_pack_bytes": "XSW_REF_TARGET_STRIPPED_ARTIFACT_BYTES_V1",
    }

    for field, macro in limit_mapping.items():
        if macro not in macros:
            raise ValidationFailure(f"wearable reference header is missing {macro}")
        if macros[macro] != limits[field]:
            raise ValidationFailure(
                f"wearable header/profile drift: {macro}={macros[macro]} != {field}={limits[field]}"
            )

    for field, macro in target_mapping.items():
        if macro not in macros:
            raise ValidationFailure(f"wearable reference header is missing {macro}")
        if macros[macro] != targets[field]:
            raise ValidationFailure(
                f"wearable header/profile drift: {macro}={macros[macro]} != {field}={targets[field]}"
            )

    expected_frame = max(limits["max_tiny_request_bytes"], limits["max_tiny_response_bytes"])
    if macros.get("XSW_REF_MAX_TINYWIRE_FRAME_V1") != expected_frame:
        raise ValidationFailure("wearable TinyWire frame macro does not match request/response envelope")


def validate_adapter_source_boundary() -> None:
    try:
        text = ADAPTER_SOURCE_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValidationFailure(
            f"cannot read {ADAPTER_SOURCE_PATH.relative_to(ROOT)}: {exc}"
        ) from exc

    includes = set(re.findall(r'^\s*#include\s+[<\"]([^>\"]+)[>\"]', text, re.MULTILINE))
    allowed_includes = {"exactscope_wearable_ref.h", "stddef.h", "string.h"}
    unexpected_includes = sorted(includes - allowed_includes)
    if unexpected_includes:
        raise ValidationFailure(
            f"wearable reference source imports unexpected host/runtime headers: {unexpected_includes}"
        )

    prohibited_calls = (
        "malloc",
        "calloc",
        "realloc",
        "free",
        "socket",
        "connect",
        "send",
        "recv",
        "fopen",
        "fread",
        "fwrite",
        "pthread_create",
        "CreateThread",
        "Sleep",
        "usleep",
        "clock_gettime",
    )
    used = [name for name in prohibited_calls if re.search(rf"\b{re.escape(name)}\s*\(", text)]
    if used:
        raise ValidationFailure(f"wearable reference source uses prohibited host services: {used}")

    required_tokens = (
        "xs_registry_freeze(",
        "XSW_REF_STATE_FROZEN_V1",
        "XSW_REF_MAX_PACK_MOUNT_ARENA_BYTES_V1",
        "XSW_REF_MAX_TOTAL_PACK_BYTES_V1",
    )
    missing = [token for token in required_tokens if token not in text]
    if missing:
        raise ValidationFailure(f"wearable reference source is missing fail-closed boundary tokens: {missing}")


def main() -> int:
    try:
        schema = read_json(SCHEMA_PATH)
        profile = read_json(PROFILE_PATH)
        if not isinstance(schema, dict) or not isinstance(profile, dict):
            raise ValidationFailure("schema and profile roots must be JSON objects")
        validate_schema(profile, schema)
        validate_semantics(profile)
        validate_spec_presence(profile)
        validate_adapter_alignment(profile)
        validate_adapter_source_boundary()
    except ValidationFailure as exc:
        print(f"wearable profile invalid: {exc}", file=sys.stderr)
        return 1

    limits = profile["hard_limits"]
    targets = profile["product_targets"]
    print(
        "wearable profile valid: "
        f"claim={profile['claim_state']}, "
        f"mutable<={limits['max_mutable_runtime_bytes']} B, "
        f"pack<={limits['max_pack_bytes']} B, "
        f"eval-p99-target<={targets['scalar_eval_p99_us']} us, "
        f"energy-target<={targets['scalar_eval_energy_uj_excluding_host_wake']} uJ"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
