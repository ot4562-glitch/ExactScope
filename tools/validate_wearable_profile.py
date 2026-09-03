#!/usr/bin/env python3
"""Validate the ExactScope wearable-edge product contract without network access."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "spec" / "examples" / "wearable-edge-profile.json"
SCHEMA_PATH = ROOT / "spec" / "schemas" / "wearable-edge-profile.schema.json"
SPEC_PATH = ROOT / "spec" / "WEARABLE_EDGE_PROFILE_V0_1.md"


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


def main() -> int:
    try:
        schema = read_json(SCHEMA_PATH)
        profile = read_json(PROFILE_PATH)
        if not isinstance(schema, dict) or not isinstance(profile, dict):
            raise ValidationFailure("schema and profile roots must be JSON objects")
        validate_schema(profile, schema)
        validate_semantics(profile)
        validate_spec_presence(profile)
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
