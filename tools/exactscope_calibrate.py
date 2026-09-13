#!/usr/bin/env python3
"""Compile and qualify an ExactScope v1.1 Amplifier Profile.

This first product-facing Harness Distillation slice keeps calibration separate from
held-out qualification and never reselects policy on held-out data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

from harness_distillation import (
    DistillationError,
    DistillationObjective,
    FrozenSplit,
    HostQualification,
    Observation,
    canonical_bytes,
    compile_profile,
    digest_json,
    load_profile,
    minimum_candidate_catalog,
    transfer_report,
)

COMPILE_REQUEST_FORMAT = "exactscope.harness-calibration-request"
HELDOUT_REQUEST_FORMAT = "exactscope.harness-heldout-request"
CONTEXT_FORMAT = "exactscope.harness-compile-context"
BUNDLE_FORMAT = "exactscope.harness-distillation-bundle"
FORMAT_VERSION = "0.1"

MANIFEST_FILE = "manifest.json"
MANIFEST_DIGEST_FILE = "manifest-sha256.txt"
CANDIDATE_PROFILE_FILE = "candidate-profile.json"
QUALIFIED_PROFILE_FILE = "amplifier-profile.json"
CALIBRATION_REPORT_FILE = "calibration-report.json"
HELDOUT_REPORT_FILE = "heldout-transfer.json"
CONTEXT_FILE = "compile-context.json"

HOST_KEYS = {
    "host_profile_digest", "context_fit_qualification_digest", "typed_contract_supported",
    "native_constraint_surface_id", "gxh_qualification_digest", "zero_call_proof_supported",
    "prefix_cache_mode", "prefix_cache_parity_digest",
}
OBJECTIVE_KEYS = set(DistillationObjective().as_dict())
OBSERVATION_KEYS = {
    "item_id", "policy_id", "task_success", "false_grounding", "unsupported_answer",
    "strict_format_failure", "model_calls", "prompt_tokens", "completion_tokens",
    "e2e_latency_ms", "exactscope_cpu_ms", "peak_ram_bytes", "distribution_bytes",
    "integration_cost_units", "output_identity",
}
COMPILE_REQUEST_KEYS = {
    "format", "format_version", "host_qualification", "calibration_split", "held_out_split",
    "objective", "reduced_prompt_profile", "baseline_policy_id", "fixed_max_policy_id",
    "observations",
}
HELDOUT_REQUEST_KEYS = {"format", "format_version", "held_out_split", "observations"}
CONTEXT_KEYS = {
    "format", "format_version", "host_qualification", "objective", "reduced_prompt_profile",
    "baseline_policy_id", "fixed_max_policy_id", "calibration_split", "held_out_split",
    "candidate_catalog_digest",
}
MANIFEST_KEYS = {
    "format", "format_version", "stage", "deployment_qualified", "profile_file",
    "profile_sha256", "selected_policy_id", "files",
}


class CalibrationError(ValueError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_json(raw: bytes | str, label: str) -> Any:
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CalibrationError(f"{label} must be UTF-8 JSON") from exc
    if not isinstance(raw, str):
        raise CalibrationError(f"{label} must be JSON text or bytes")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CalibrationError(f"{label} is not valid JSON") from exc


def _exact_object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise CalibrationError(f"{label} shape drift")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CalibrationError(f"{label} must be nonempty text")
    return value.strip()


def _parse_split(value: Any, label: str) -> FrozenSplit:
    obj = _exact_object(value, {"split_id", "item_ids"}, label)
    if not isinstance(obj["item_ids"], list):
        raise CalibrationError(f"{label}.item_ids must be an array")
    try:
        return FrozenSplit(_text(obj["split_id"], f"{label}.split_id"), tuple(obj["item_ids"]))
    except DistillationError as exc:
        raise CalibrationError(str(exc)) from exc


def _parse_host(value: Any) -> HostQualification:
    obj = _exact_object(value, HOST_KEYS, "host_qualification")
    try:
        return HostQualification(**obj)
    except (TypeError, DistillationError) as exc:
        raise CalibrationError(f"invalid host qualification: {exc}") from exc


def _parse_objective(value: Any) -> DistillationObjective:
    obj = _exact_object(value, OBJECTIVE_KEYS, "objective")
    try:
        return DistillationObjective(**obj)
    except (TypeError, DistillationError) as exc:
        raise CalibrationError(f"invalid distillation objective: {exc}") from exc


def _parse_observations(value: Any, label: str) -> tuple[Observation, ...]:
    if not isinstance(value, list) or not value:
        raise CalibrationError(f"{label} must be a nonempty array")
    rows: list[Observation] = []
    for index, item in enumerate(value):
        obj = _exact_object(item, OBSERVATION_KEYS, f"{label}[{index}]")
        try:
            rows.append(Observation(**obj))
        except (TypeError, DistillationError) as exc:
            raise CalibrationError(f"invalid {label}[{index}]: {exc}") from exc
    return tuple(rows)


# -- PARSERS --

def _parse_compile_request(raw: bytes | str) -> dict[str, Any]:
    value = _exact_object(
        _load_json(raw, "calibration request"), COMPILE_REQUEST_KEYS, "calibration request"
    )
    if value["format"] != COMPILE_REQUEST_FORMAT or value["format_version"] != FORMAT_VERSION:
        raise CalibrationError("unsupported calibration request identity")
    host = _parse_host(value["host_qualification"])
    calibration = _parse_split(value["calibration_split"], "calibration_split")
    held_out = _parse_split(value["held_out_split"], "held_out_split")
    objective = _parse_objective(value["objective"])
    return {
        "host": host,
        "calibration": calibration,
        "held_out": held_out,
        "objective": objective,
        "reduced_prompt_profile": _text(value["reduced_prompt_profile"], "reduced_prompt_profile"),
        "baseline_policy_id": _text(value["baseline_policy_id"], "baseline_policy_id"),
        "fixed_max_policy_id": _text(value["fixed_max_policy_id"], "fixed_max_policy_id"),
        "observations": _parse_observations(value["observations"], "observations"),
    }


def _parse_heldout_request(raw: bytes | str) -> dict[str, Any]:
    value = _exact_object(
        _load_json(raw, "held-out request"), HELDOUT_REQUEST_KEYS, "held-out request"
    )
    if value["format"] != HELDOUT_REQUEST_FORMAT or value["format_version"] != FORMAT_VERSION:
        raise CalibrationError("unsupported held-out request identity")
    return {
        "held_out": _parse_split(value["held_out_split"], "held_out_split"),
        "observations": _parse_observations(value["observations"], "observations"),
    }


def _context_bytes(parsed: dict[str, Any], candidates: tuple[Any, ...]) -> bytes:
    context = {
        "format": CONTEXT_FORMAT,
        "format_version": FORMAT_VERSION,
        "host_qualification": parsed["host"].as_dict(),
        "objective": parsed["objective"].as_dict(),
        "reduced_prompt_profile": parsed["reduced_prompt_profile"],
        "baseline_policy_id": parsed["baseline_policy_id"],
        "fixed_max_policy_id": parsed["fixed_max_policy_id"],
        "calibration_split": parsed["calibration"].as_dict(),
        "held_out_split": parsed["held_out"].as_dict(),
        "candidate_catalog_digest": digest_json([candidate.as_dict() for candidate in candidates]),
    }
    return canonical_bytes(context)


def _parse_context(raw: bytes | str) -> dict[str, Any]:
    value = _exact_object(_load_json(raw, "compile context"), CONTEXT_KEYS, "compile context")
    if value["format"] != CONTEXT_FORMAT or value["format_version"] != FORMAT_VERSION:
        raise CalibrationError("unsupported compile context identity")
    host = _parse_host(value["host_qualification"])
    objective = _parse_objective(value["objective"])
    calibration = _parse_split(value["calibration_split"], "calibration_split")
    held_out = _parse_split(value["held_out_split"], "held_out_split")
    reduced = _text(value["reduced_prompt_profile"], "reduced_prompt_profile")
    candidates = minimum_candidate_catalog(host, reduced)
    expected_catalog = digest_json([candidate.as_dict() for candidate in candidates])
    if value["candidate_catalog_digest"] != expected_catalog:
        raise CalibrationError("compile context candidate catalog identity drift")
    return {
        "host": host,
        "objective": objective,
        "calibration": calibration,
        "held_out": held_out,
        "reduced_prompt_profile": reduced,
        "baseline_policy_id": _text(value["baseline_policy_id"], "baseline_policy_id"),
        "fixed_max_policy_id": _text(value["fixed_max_policy_id"], "fixed_max_policy_id"),
        "candidates": candidates,
    }


# -- BUNDLE BUILDERS --

def _manifest(
    stage: str,
    qualified: bool,
    profile_file: str,
    selected_policy_id: str,
    files: dict[str, bytes],
) -> bytes:
    value = {
        "format": BUNDLE_FORMAT,
        "format_version": FORMAT_VERSION,
        "stage": stage,
        "deployment_qualified": qualified,
        "profile_file": profile_file,
        "profile_sha256": _sha256(files[profile_file]),
        "selected_policy_id": selected_policy_id,
        "files": [
            {"name": name, "sha256": _sha256(data), "bytes": len(data)}
            for name, data in sorted(files.items())
        ],
    }
    return canonical_bytes(value)


def _finish_bundle(
    stage: str,
    qualified: bool,
    profile_file: str,
    selected_policy_id: str,
    files: dict[str, bytes],
) -> dict[str, bytes]:
    payloads = dict(files)
    manifest = _manifest(stage, qualified, profile_file, selected_policy_id, files)
    payloads[MANIFEST_FILE] = manifest
    payloads[MANIFEST_DIGEST_FILE] = (_sha256(manifest) + "\n").encode("ascii")
    return payloads


def build_compile_bundle(raw: bytes | str) -> dict[str, bytes]:
    parsed = _parse_compile_request(raw)
    candidates = minimum_candidate_catalog(parsed["host"], parsed["reduced_prompt_profile"])
    try:
        result = compile_profile(
            calibration=parsed["calibration"],
            held_out=parsed["held_out"],
            host=parsed["host"],
            candidates=candidates,
            observations=parsed["observations"],
            objective=parsed["objective"],
            baseline_policy_id=parsed["baseline_policy_id"],
            fixed_max_policy_id=parsed["fixed_max_policy_id"],
        )
    except DistillationError as exc:
        raise CalibrationError(str(exc)) from exc
    files = {
        CANDIDATE_PROFILE_FILE: result.profile.canonical_bytes(),
        CALIBRATION_REPORT_FILE: canonical_bytes(result.report),
        CONTEXT_FILE: _context_bytes(parsed, candidates),
    }
    return _finish_bundle(
        "compile",
        False,
        CANDIDATE_PROFILE_FILE,
        result.profile.selected_policy.policy_id,
        files,
    )


def build_qualification_bundle(
    compile_dir: Path, heldout_raw: bytes | str
) -> tuple[dict[str, bytes], bool]:
    compile_manifest = verify_bundle(compile_dir)
    if compile_manifest["stage"] != "compile":
        raise CalibrationError("qualification requires a compile-stage bundle")
    context = _parse_context((compile_dir / CONTEXT_FILE).read_bytes())
    profile = load_profile(
        (compile_dir / CANDIDATE_PROFILE_FILE).read_bytes(),
        host_profile_digest=context["host"].host_profile_digest,
    )
    if profile.host_qualification_digest != context["host"].sha256():
        raise CalibrationError("candidate profile host qualification identity drift")
    heldout = _parse_heldout_request(heldout_raw)
    if heldout["held_out"].sha256() != context["held_out"].sha256():
        raise CalibrationError("held-out split differs from the split frozen during compilation")
    try:
        transfer = transfer_report(
            profile=profile,
            held_out=heldout["held_out"],
            candidates=context["candidates"],
            observations=heldout["observations"],
            baseline_policy_id=context["baseline_policy_id"],
            fixed_max_policy_id=context["fixed_max_policy_id"],
            objective=context["objective"],
        )
    except DistillationError as exc:
        raise CalibrationError(str(exc)) from exc
    qualified = bool(transfer["qualification"]["passed"])
    profile_file = QUALIFIED_PROFILE_FILE if qualified else CANDIDATE_PROFILE_FILE
    files = {
        profile_file: profile.canonical_bytes(),
        CALIBRATION_REPORT_FILE: (compile_dir / CALIBRATION_REPORT_FILE).read_bytes(),
        CONTEXT_FILE: (compile_dir / CONTEXT_FILE).read_bytes(),
        HELDOUT_REPORT_FILE: canonical_bytes(transfer),
    }
    return (
        _finish_bundle(
            "qualification", qualified, profile_file, profile.selected_policy.policy_id, files
        ),
        qualified,
    )


# -- BUNDLE IO --

def write_immutable_bundle(payloads: dict[str, bytes], output: Path) -> None:
    if output.exists():
        if not output.is_dir():
            raise CalibrationError("bundle output exists and is not a directory")
        current = {entry.name for entry in output.iterdir() if entry.is_file()}
        if current != set(payloads):
            raise CalibrationError("immutable bundle file inventory differs; use a new output directory")
        for name, data in payloads.items():
            if (output / name).read_bytes() != data:
                raise CalibrationError("immutable bundle payload differs; use a new output directory")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".xs-harness-") as tmp:
        stage = Path(tmp) / "bundle"
        stage.mkdir()
        for name, data in payloads.items():
            (stage / name).write_bytes(data)
        stage.rename(output)


def verify_bundle(path: Path) -> dict[str, Any]:
    if not path.is_dir():
        raise CalibrationError("bundle path must be a directory")
    manifest_raw = (path / MANIFEST_FILE).read_bytes()
    expected_digest = (path / MANIFEST_DIGEST_FILE).read_text(encoding="ascii").strip()
    if _sha256(manifest_raw) != expected_digest:
        raise CalibrationError("bundle manifest digest mismatch")
    manifest = _exact_object(
        _load_json(manifest_raw, "bundle manifest"), MANIFEST_KEYS, "bundle manifest"
    )
    if manifest["format"] != BUNDLE_FORMAT or manifest["format_version"] != FORMAT_VERSION:
        raise CalibrationError("unsupported bundle identity")
    if manifest["stage"] not in {"compile", "qualification"}:
        raise CalibrationError("unsupported bundle stage")
    if type(manifest["deployment_qualified"]) is not bool:
        raise CalibrationError("deployment_qualified must be boolean")
    profile_file = _text(manifest["profile_file"], "profile_file")
    files = manifest["files"]
    if not isinstance(files, list) or not files:
        raise CalibrationError("bundle manifest files must be a nonempty array")
    expected_files = {MANIFEST_FILE, MANIFEST_DIGEST_FILE}
    for index, item in enumerate(files):
        obj = _exact_object(item, {"name", "sha256", "bytes"}, f"files[{index}]")
        name = _text(obj["name"], f"files[{index}].name")
        expected_files.add(name)
        data = (path / name).read_bytes()
        if _sha256(data) != obj["sha256"] or len(data) != obj["bytes"]:
            raise CalibrationError(f"bundle payload mismatch: {name}")
    actual_files = {entry.name for entry in path.iterdir() if entry.is_file()}
    if actual_files != expected_files:
        raise CalibrationError("bundle file inventory drift")
    profile_raw = (path / profile_file).read_bytes()
    if _sha256(profile_raw) != manifest["profile_sha256"]:
        raise CalibrationError("bundle profile digest mismatch")
    profile = load_profile(profile_raw)
    if profile.selected_policy.policy_id != manifest["selected_policy_id"]:
        raise CalibrationError("bundle selected policy identity mismatch")
    if manifest["stage"] == "compile" and manifest["deployment_qualified"]:
        raise CalibrationError("compile-stage bundle cannot be deployment-qualified")
    if manifest["stage"] == "qualification":
        expected_qualified = profile_file == QUALIFIED_PROFILE_FILE
        if manifest["deployment_qualified"] != expected_qualified:
            raise CalibrationError("qualification bundle profile naming contradicts verdict")
    return manifest


# -- CLI --

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    compile_parser = sub.add_parser(
        "compile", help="select a candidate Amplifier Profile from calibration only"
    )
    compile_parser.add_argument("request", type=Path)
    compile_parser.add_argument("output", type=Path)

    qualify_parser = sub.add_parser(
        "qualify", help="verify the frozen candidate on held-out data without reselection"
    )
    qualify_parser.add_argument("compile_bundle", type=Path)
    qualify_parser.add_argument("heldout_request", type=Path)
    qualify_parser.add_argument("output", type=Path)

    verify_parser = sub.add_parser("verify", help="verify an immutable distillation bundle")
    verify_parser.add_argument("bundle", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "compile":
            payloads = build_compile_bundle(args.request.read_bytes())
            write_immutable_bundle(payloads, args.output)
            manifest = verify_bundle(args.output)
            print(
                f"PASS harness compile selected={manifest['selected_policy_id']} "
                f"bundle={args.output}"
            )
            return 0
        if args.command == "qualify":
            payloads, qualified = build_qualification_bundle(
                args.compile_bundle, args.heldout_request.read_bytes()
            )
            write_immutable_bundle(payloads, args.output)
            manifest = verify_bundle(args.output)
            verdict = "PASS" if qualified else "REJECTED"
            print(
                f"{verdict} harness qualification selected={manifest['selected_policy_id']} "
                f"bundle={args.output}"
            )
            return 0 if qualified else 2
        manifest = verify_bundle(args.bundle)
        verdict = "qualified" if manifest["deployment_qualified"] else "not-qualified"
        print(
            f"PASS harness bundle stage={manifest['stage']} status={verdict} "
            f"selected={manifest['selected_policy_id']}"
        )
        return 0
    except (CalibrationError, DistillationError, OSError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
