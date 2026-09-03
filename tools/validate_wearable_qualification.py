#!/usr/bin/env python3
"""Validate wearable target-device evidence and qualification claims."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
RECORD_PATH = ROOT / "spec" / "examples" / "wearable-qualification-record.json"
RECORD_SCHEMA_PATH = ROOT / "spec" / "schemas" / "wearable-qualification-record.schema.json"
PROFILE_PATH = ROOT / "spec" / "examples" / "wearable-edge-profile.json"

ZERO_SHA256 = "0" * 64
ZERO_COMMIT = "0" * 40
PLACEHOLDER_TEXT = {"", "TBD", "TODO", "UNKNOWN", "UNMEASURED"}


class ValidationFailure(Exception):
    """Raised when evidence and its claimed status do not agree."""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationFailure(f"{path.relative_to(ROOT)}: invalid JSON: {exc}") from exc


def validate_schema(record: dict[str, Any], schema: dict[str, Any]) -> None:
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(record),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path) or "<root>"
        raise ValidationFailure(f"qualification schema failure at {location}: {first.message}")


def profile_sha256() -> str:
    try:
        return hashlib.sha256(PROFILE_PATH.read_bytes()).hexdigest()
    except OSError as exc:
        raise ValidationFailure(f"cannot hash {PROFILE_PATH.relative_to(ROOT)}: {exc}") from exc


def is_placeholder(value: str) -> bool:
    return value.strip().upper() in PLACEHOLDER_TEXT


def require_real_text(value: str, label: str) -> None:
    if is_placeholder(value):
        raise ValidationFailure(f"{label} still contains a placeholder")


def validate_percentiles(metric: dict[str, Any], label: str) -> None:
    values = (metric["p50_us"], metric["p95_us"], metric["p99_us"], metric["max_us"])
    if not (values[0] <= values[1] <= values[2] <= values[3]):
        raise ValidationFailure(f"{label}: require p50 <= p95 <= p99 <= max")


def metric_is_zero(metric: dict[str, Any]) -> bool:
    return all(metric[key] == 0 for key in ("p50_us", "p95_us", "p99_us", "max_us"))


def validate_latency(record: dict[str, Any], profile: dict[str, Any]) -> bool:
    latency = record["latency"]
    execution_mode = record["execution_mode"]
    targets = profile["product_targets"]
    contract = profile["conformance"]

    for name in ("lookup", "scalar_eval", "pack_mount_256k"):
        validate_percentiles(latency[name], f"latency.{name}")

    if latency["state"] == "not-run":
        if latency["warmup_iterations"] != 0 or latency["sample_iterations"] != 0:
            raise ValidationFailure("latency not-run state must keep iteration counts at zero")
        if any(not metric_is_zero(latency[name]) for name in ("lookup", "scalar_eval", "pack_mount_256k")):
            raise ValidationFailure("latency not-run state must keep percentile fields at zero")
        return False

    require_real_text(latency["clock"], "latency.clock")
    if latency["warmup_iterations"] < contract["benchmark_warmup_iterations"]:
        raise ValidationFailure(
            f"latency warmup {latency['warmup_iterations']} < required {contract['benchmark_warmup_iterations']}"
        )
    if latency["sample_iterations"] < contract["benchmark_sample_iterations"]:
        raise ValidationFailure(
            f"latency samples {latency['sample_iterations']} < required {contract['benchmark_sample_iterations']}"
        )

    lookup_pass = latency["lookup"]["p99_us"] <= targets["lookup_p99_us"]
    eval_pass = (
        latency["scalar_eval"]["p50_us"] <= targets["scalar_eval_p50_us"]
        and latency["scalar_eval"]["p99_us"] <= targets["scalar_eval_p99_us"]
    )

    mount_pass = True
    if execution_mode == "native-dynamic-exact":
        if metric_is_zero(latency["pack_mount_256k"]):
            raise ValidationFailure("dynamic execution mode requires a measured 256 KiB pack-mount latency")
        mount_pass = (
            latency["pack_mount_256k"]["p99_us"] <= targets["pack_mount_256k_p99_us"]
        )

    actual_pass = lookup_pass and eval_pass and mount_pass
    if latency["state"] == "pass" and not actual_pass:
        raise ValidationFailure("latency is marked pass but one or more product targets are exceeded")
    if latency["state"] == "fail" and actual_pass:
        raise ValidationFailure("latency is marked fail but all enforced latency targets pass")
    return actual_pass


def validate_energy(record: dict[str, Any], profile: dict[str, Any]) -> bool:
    energy = record["energy"]
    target = profile["product_targets"]["scalar_eval_energy_uj_excluding_host_wake"]
    minimum_samples = profile["conformance"]["benchmark_sample_iterations"]

    if energy["state"] == "not-run":
        if energy["method"] != "not-run":
            raise ValidationFailure("energy not-run state must use method=not-run")
        if any(
            energy[key] != 0
            for key in (
                "sample_iterations",
                "baseline_total_uj",
                "measured_total_uj",
                "incremental_per_eval_uj",
                "sampling_interval_us",
            )
        ):
            raise ValidationFailure("energy not-run state must keep measurement fields at zero")
        return False

    if energy["method"] not in {"battery-rail", "pmic-counter"}:
        raise ValidationFailure("measured energy requires battery-rail or pmic-counter method")
    require_real_text(energy["instrument"], "energy.instrument")
    if energy["sample_iterations"] < minimum_samples:
        raise ValidationFailure(
            f"energy samples {energy['sample_iterations']} < required {minimum_samples}"
        )
    if energy["sampling_interval_us"] <= 0:
        raise ValidationFailure("measured energy requires a positive sampling interval")
    if energy["measured_total_uj"] < energy["baseline_total_uj"]:
        raise ValidationFailure("energy measured_total_uj cannot be below baseline_total_uj")

    actual_pass = energy["incremental_per_eval_uj"] <= target
    if energy["state"] == "pass" and not actual_pass:
        raise ValidationFailure(
            f"energy is marked pass but {energy['incremental_per_eval_uj']} uJ exceeds {target} uJ"
        )
    if energy["state"] == "fail" and actual_pass:
        raise ValidationFailure("energy is marked fail but the enforced energy target passes")
    return actual_pass


def validate_footprint(record: dict[str, Any], profile: dict[str, Any]) -> bool:
    footprint = record["footprint"]
    limits = profile["hard_limits"]
    targets = profile["product_targets"]

    component_keys = (
        "context_bytes",
        "eval_scratch_bytes",
        "pack_mount_arena_bytes",
        "adapter_buffer_bytes",
    )
    component_sum = sum(footprint[key] for key in component_keys)
    if footprint["mutable_total_bytes"] != component_sum:
        raise ValidationFailure(
            "footprint.mutable_total_bytes must equal context + scratch + mount arena + adapter buffers"
        )

    if footprint["state"] == "not-run":
        if footprint["mutable_total_bytes"] != 0 or footprint["stripped_runtime_plus_fused_pack_bytes"] != 0:
            raise ValidationFailure("footprint not-run state must keep measured sizes at zero")
        return False

    if footprint["context_bytes"] <= 0:
        raise ValidationFailure("measured footprint requires a nonzero context size")
    if footprint["stripped_runtime_plus_fused_pack_bytes"] <= 0:
        raise ValidationFailure("measured footprint requires a nonzero stripped artifact size")

    checks = (
        footprint["context_bytes"] <= limits["max_context_bytes"],
        footprint["eval_scratch_bytes"] <= limits["max_eval_scratch_bytes"],
        footprint["pack_mount_arena_bytes"] <= limits["max_pack_mount_arena_bytes"],
        footprint["adapter_buffer_bytes"] <= limits["max_adapter_buffer_bytes"],
        footprint["mutable_total_bytes"] <= limits["max_mutable_runtime_bytes"],
        footprint["stripped_runtime_plus_fused_pack_bytes"]
        <= targets["stripped_runtime_plus_fused_pack_bytes"],
    )
    actual_pass = all(checks)
    if footprint["state"] == "pass" and not actual_pass:
        raise ValidationFailure("footprint is marked pass but one or more wearable memory/size limits are exceeded")
    if footprint["state"] == "fail" and actual_pass:
        raise ValidationFailure("footprint is marked fail but all enforced footprint limits pass")
    return actual_pass


def validate_conformance(record: dict[str, Any]) -> bool:
    conformance = record["conformance"]
    power_loss = conformance["power_loss_update"]

    if conformance["total"] != conformance["passed"] + conformance["failed"]:
        raise ValidationFailure("conformance total must equal passed + failed")
    if power_loss["passed_cases"] > power_loss["total_cases"]:
        raise ValidationFailure("power-loss passed_cases cannot exceed total_cases")

    if conformance["state"] == "not-run":
        if conformance["total"] != 0 or power_loss["total_cases"] != 0:
            raise ValidationFailure("conformance not-run state must keep test counts at zero")
        return False

    require_real_text(conformance["design_baseline_run"], "conformance.design_baseline_run")
    require_real_text(conformance["wearable_profile_run"], "conformance.wearable_profile_run")
    if conformance["corpus_sha256"] == ZERO_SHA256:
        raise ValidationFailure("measured conformance requires a nonzero corpus digest")
    if conformance["total"] <= 0:
        raise ValidationFailure("measured conformance requires at least one corpus test")

    required_booleans = (
        "truncate_every_pack_byte_pass",
        "single_bit_corruption_pass",
        "fused_dynamic_identity_pass",
        "native_wasm_identity_pass",
        "airplane_mode_pass",
        "privacy_audit_pass",
    )
    all_booleans_pass = all(conformance[key] for key in required_booleans)
    power_loss_pass = power_loss["total_cases"] >= 8 and power_loss["passed_cases"] == power_loss["total_cases"]
    actual_pass = (
        conformance["failed"] == 0
        and conformance["passed"] == conformance["total"]
        and all_booleans_pass
        and power_loss_pass
    )

    if conformance["state"] == "pass" and not actual_pass:
        raise ValidationFailure("conformance is marked pass but mandatory destructive/product checks are incomplete")
    if conformance["state"] == "fail" and actual_pass:
        raise ValidationFailure("conformance is marked fail but every mandatory check passes")
    return actual_pass


def validate_device_and_artifacts(record: dict[str, Any], profile: dict[str, Any], measured: bool) -> None:
    device = record["device"]
    artifacts = record["artifacts"]
    limits = profile["hard_limits"]
    targets = profile["product_targets"]

    if measured:
        for key in (
            "product",
            "board_revision",
            "soc",
            "os",
            "os_build",
            "firmware_build",
            "power_mode",
            "thermal_state",
            "display_state",
            "radio_state",
        ):
            require_real_text(device[key], f"device.{key}")
        if device["battery_mv"] <= 0:
            raise ValidationFailure("measured/qualified evidence requires a real battery voltage")
        if artifacts["source_commit"] == ZERO_COMMIT:
            raise ValidationFailure("measured/qualified evidence requires a nonzero source commit")
        if artifacts["runtime_sha256"] == ZERO_SHA256:
            raise ValidationFailure("measured/qualified evidence requires a nonzero runtime digest")
        if artifacts["profile_sha256"] == ZERO_SHA256:
            raise ValidationFailure("measured/qualified evidence requires a nonzero profile digest")
        if artifacts["profile_sha256"] != profile_sha256():
            raise ValidationFailure("qualification profile_sha256 does not match the canonical wearable profile bytes")
        if artifacts["runtime_size_bytes"] <= 0:
            raise ValidationFailure("measured/qualified evidence requires a nonzero runtime artifact size")

    if artifacts["runtime_size_bytes"] > targets["stripped_runtime_plus_fused_pack_bytes"]:
        raise ValidationFailure("runtime artifact exceeds wearable stripped artifact target")
    if len(artifacts["packs"]) > limits["max_mounted_packs"]:
        raise ValidationFailure("qualification record contains too many packs")
    total_pack_bytes = sum(pack["size_bytes"] for pack in artifacts["packs"])
    if total_pack_bytes > limits["max_total_mounted_pack_bytes"]:
        raise ValidationFailure("qualification record pack bytes exceed wearable total pack budget")
    for pack in artifacts["packs"]:
        if pack["size_bytes"] > limits["max_pack_bytes"]:
            raise ValidationFailure(f"pack {pack['pack_id']!r} exceeds wearable per-pack limit")
        if measured and pack["sha256"] == ZERO_SHA256:
            raise ValidationFailure(f"pack {pack['pack_id']!r} has a zero digest")

    if measured and record["execution_mode"] == "native-dynamic-exact" and not artifacts["packs"]:
        raise ValidationFailure("native-dynamic-exact evidence requires at least one mounted pack artifact")


def validate_status(record: dict[str, Any], category_passes: dict[str, bool]) -> None:
    status = record["status"]
    states = {
        "latency": record["latency"]["state"],
        "energy": record["energy"]["state"],
        "footprint": record["footprint"]["state"],
        "conformance": record["conformance"]["state"],
    }

    if status == "draft":
        return
    if any(state == "not-run" for state in states.values()):
        raise ValidationFailure(f"{status} status requires every evidence category to have been run")
    if status == "qualified" and not all(category_passes.values()):
        failed = sorted(name for name, passed in category_passes.items() if not passed)
        raise ValidationFailure(f"qualified status requires every category to pass; failing={failed}")


def validate_record(record: dict[str, Any], profile: dict[str, Any]) -> None:
    if record["profile"] != profile["profile"]:
        raise ValidationFailure("qualification record/profile identity mismatch")

    measured = record["status"] in {"measured", "qualified"}
    validate_device_and_artifacts(record, profile, measured)

    category_passes = {
        "latency": validate_latency(record, profile),
        "energy": validate_energy(record, profile),
        "footprint": validate_footprint(record, profile),
        "conformance": validate_conformance(record),
    }
    validate_status(record, category_passes)


def synthetic_qualified_record(template: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    record = json.loads(json.dumps(template))
    record["status"] = "qualified"
    record["execution_mode"] = "native-fused-discovery"
    record["device"] = {
        "product": "qualification-fixture",
        "board_revision": "rev-a",
        "soc": "target-soc",
        "cpu_arch": "aarch64",
        "os": "target-os",
        "os_build": "build-1",
        "firmware_build": "fw-1",
        "power_mode": "nominal",
        "thermal_state": "steady",
        "battery_mv": 3800,
        "display_state": "on",
        "radio_state": "airplane-mode",
    }
    record["artifacts"] = {
        "source_commit": "1" * 40,
        "runtime_sha256": "2" * 64,
        "runtime_size_bytes": 500_000,
        "profile_sha256": profile_sha256(),
        "packs": [],
    }
    record["latency"] = {
        "state": "pass",
        "clock": "monotonic-target-clock",
        "warmup_iterations": profile["conformance"]["benchmark_warmup_iterations"],
        "sample_iterations": profile["conformance"]["benchmark_sample_iterations"],
        "lookup": {"p50_us": 80, "p95_us": 150, "p99_us": 200, "max_us": 230},
        "scalar_eval": {"p50_us": 100, "p95_us": 500, "p99_us": 800, "max_us": 900},
        "pack_mount_256k": {"p50_us": 0, "p95_us": 0, "p99_us": 0, "max_us": 0},
    }
    record["energy"] = {
        "state": "pass",
        "method": "battery-rail",
        "instrument": "qualification-fixture-meter",
        "sample_iterations": profile["conformance"]["benchmark_sample_iterations"],
        "baseline_total_uj": 1000,
        "measured_total_uj": 4000,
        "incremental_per_eval_uj": 300,
        "sampling_interval_us": 100,
    }
    record["footprint"] = {
        "state": "pass",
        "context_bytes": 1024,
        "eval_scratch_bytes": 1024,
        "pack_mount_arena_bytes": 0,
        "adapter_buffer_bytes": 4096,
        "mutable_total_bytes": 6144,
        "stripped_runtime_plus_fused_pack_bytes": 500_000,
    }
    record["conformance"] = {
        "state": "pass",
        "design_baseline_run": "fixture-design-run",
        "wearable_profile_run": "fixture-wearable-run",
        "corpus_sha256": "3" * 64,
        "total": 100,
        "passed": 100,
        "failed": 0,
        "truncate_every_pack_byte_pass": True,
        "single_bit_corruption_pass": True,
        "fused_dynamic_identity_pass": True,
        "native_wasm_identity_pass": True,
        "airplane_mode_pass": True,
        "privacy_audit_pass": True,
        "power_loss_update": {"total_cases": 8, "passed_cases": 8},
    }
    record["notes"] = "Synthetic validator self-test only; never product evidence."
    return record


def expect_invalid(record: dict[str, Any], profile: dict[str, Any], label: str) -> None:
    try:
        validate_record(record, profile)
    except ValidationFailure:
        return
    raise ValidationFailure(f"validator self-test failed to reject {label}")


def run_self_tests(template: dict[str, Any], profile: dict[str, Any]) -> None:
    passing = synthetic_qualified_record(template, profile)
    validate_record(passing, profile)

    latency = json.loads(json.dumps(passing))
    latency["latency"]["scalar_eval"]["p99_us"] = 1001
    latency["latency"]["scalar_eval"]["max_us"] = 1100
    expect_invalid(latency, profile, "scalar eval p99 above 1 ms")

    energy = json.loads(json.dumps(passing))
    energy["energy"]["incremental_per_eval_uj"] = 501
    expect_invalid(energy, profile, "scalar eval energy above 500 uJ")

    footprint = json.loads(json.dumps(passing))
    footprint["footprint"]["context_bytes"] = 4097
    footprint["footprint"]["mutable_total_bytes"] = 9217
    expect_invalid(footprint, profile, "context size above 4096 bytes")

    power_loss = json.loads(json.dumps(passing))
    power_loss["conformance"]["power_loss_update"] = {"total_cases": 7, "passed_cases": 7}
    expect_invalid(power_loss, profile, "insufficient power-loss injection cases")

    placeholder = json.loads(json.dumps(passing))
    placeholder["device"]["product"] = "TBD"
    expect_invalid(placeholder, profile, "measured device placeholder")

    dynamic_without_pack = json.loads(json.dumps(passing))
    dynamic_without_pack["execution_mode"] = "native-dynamic-exact"
    dynamic_without_pack["latency"]["pack_mount_256k"] = {
        "p50_us": 1000,
        "p95_us": 4000,
        "p99_us": 8000,
        "max_us": 9000,
    }
    expect_invalid(dynamic_without_pack, profile, "dynamic mode without pack artifact")

    wrong_profile = json.loads(json.dumps(passing))
    wrong_profile["artifacts"]["profile_sha256"] = "4" * 64
    expect_invalid(wrong_profile, profile, "profile digest mismatch")


def main() -> int:
    try:
        schema = read_json(RECORD_SCHEMA_PATH)
        record = read_json(RECORD_PATH)
        profile = read_json(PROFILE_PATH)
        if not isinstance(schema, dict) or not isinstance(record, dict) or not isinstance(profile, dict):
            raise ValidationFailure("qualification schema, record, and profile roots must be JSON objects")
        validate_schema(record, schema)
        validate_record(record, profile)
        if "--self-test" in sys.argv[1:]:
            run_self_tests(record, profile)
    except ValidationFailure as exc:
        print(f"wearable qualification invalid: {exc}", file=sys.stderr)
        return 1

    states = ", ".join(
        f"{name}={record[name]['state']}" for name in ("latency", "energy", "footprint", "conformance")
    )
    suffix = ", self-test=pass" if "--self-test" in sys.argv[1:] else ""
    print(
        "wearable qualification valid: "
        f"status={record['status']}, mode={record['execution_mode']}, {states}{suffix}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
