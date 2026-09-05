#!/usr/bin/env python3
"""Create/verify deterministic ExactScope build-input identity documents.

This tool does not build or execute ExactScope. It records the exact capability,
source-tree identity, pinned Cargo/toolchain inputs, selected compile-time feature
set, and release-packaging inputs required to make an independent rebuild request
auditable. Matching documents are prerequisite metadata, not reproducible-build proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from compile_capability import (
    ROOT,
    canonical,
    load,
    source_identity,
    specialization_features,
    verify_bundle,
)

FORMAT = "exactscope.build-input-identity"
FORMAT_VERSION = "0.1"
SCHEMA = ROOT / "spec/schemas/build-input-identity.schema.json"
PACKAGING_INPUTS = (
    "Cargo.toml",
    "Cargo.lock",
    "rust-toolchain.toml",
    ".cargo/config.toml",
    "include/exactscope.h",
    "include/exactscope_platform.h",
    "include/exactscope_wasm.h",
    "cmake/ExactScopeConfig.cmake",
    "spec/registries/public-exports.json",
    "spec/BUILD_INPUT_IDENTITY_V0_1.md",
    "spec/MODEL_SURFACE_NEGOTIATION_V0_1.md",
    "spec/OPERATION_REVISION_POLICY_V0_1.md",
    "spec/RELEASE_BUNDLE_V0_1.md",
    "spec/schemas/build-input-identity.schema.json",
    "spec/schemas/release-bundle.schema.json",
    "tools/build_input_identity.py",
    "tools/compile_capability.py",
    "tools/inspect_wasm.py",
    "tools/package_release_bundle.py",
)


class BuildInputError(RuntimeError):
    pass


def validate_document(document: dict[str, Any]) -> None:
    schema = load(SCHEMA.read_bytes())
    errors = sorted(
        Draft202012Validator(schema).iter_errors(document),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path) or "<root>"
        raise BuildInputError(f"build-input schema failed at {location}: {first.message}")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hashes(paths: tuple[str, ...] = PACKAGING_INPUTS) -> dict[str, str]:
    result: dict[str, str] = {}
    for relative in paths:
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise BuildInputError(f"required build input missing or escapes repository: {relative}")
        result[relative] = digest(path.read_bytes())
    return result


def workspace_version() -> str:
    with (ROOT / "Cargo.toml").open("rb") as handle:
        manifest = tomllib.load(handle)
    version = manifest.get("workspace", {}).get("package", {}).get("version")
    if not isinstance(version, str) or not version:
        raise BuildInputError("workspace version is missing")
    return version


def pinned_rust_channel() -> str:
    with (ROOT / "rust-toolchain.toml").open("rb") as handle:
        document = tomllib.load(handle)
    channel = document.get("toolchain", {}).get("channel")
    if not isinstance(channel, str) or not channel:
        raise BuildInputError("pinned Rust channel is missing")
    return channel


def feature_set(profile: dict[str, Any], release_profile: str) -> list[str]:
    if release_profile == "no-import-wasm":
        if profile.get("device_budget", {}).get("target_profile") != "no-import-wasm":
            raise BuildInputError("Wasm recipe requires a no-import-wasm capability")
        return list(specialization_features(profile))
    if release_profile == "native-static":
        surface = profile.get("runtime_surface", {})
        device = profile.get("device_budget", {})
        if surface.get("specialization") != "host-limited" or device.get("target_profile") != "native-static":
            raise BuildInputError("native recipe requires host-limited/native-static capability")
        return ["standalone-staticlib"]
    raise BuildInputError(f"unsupported release profile: {release_profile}")


def recipe_document(
    *,
    profile: dict[str, Any],
    capability_bundle_sha256: str,
    release_profile: str,
    target: str,
    current_source_identity: str,
    inputs: dict[str, str],
) -> dict[str, Any]:
    if not isinstance(target, str) or not target or any(ch.isspace() for ch in target):
        raise BuildInputError("target must be a nonempty whitespace-free identifier")
    core_revision = profile.get("bindings", {}).get("core_revision")
    expected_core = "sha256:" + current_source_identity
    if core_revision != expected_core:
        raise BuildInputError(
            f"capability core revision is not current source: {core_revision!r} != {expected_core!r}"
        )
    if not isinstance(capability_bundle_sha256, str) or len(capability_bundle_sha256) != 64:
        raise BuildInputError("invalid capability bundle digest")
    if any(ch not in "0123456789abcdef" for ch in capability_bundle_sha256):
        raise BuildInputError("invalid capability bundle digest")
    document = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "project_version": workspace_version(),
        "release_profile": release_profile,
        "target": target,
        "capability": {
            "bundle_sha256": capability_bundle_sha256,
            "profile_id": profile.get("profile_id"),
            "profile_revision": profile.get("profile_revision"),
            "domain": profile.get("domain"),
            "core_revision": core_revision,
            "surface_contract_sha256": profile.get("bindings", {}).get("surface_contract_sha256"),
        },
        "rust": {
            "channel": pinned_rust_channel(),
            "features": feature_set(profile, release_profile),
            "locked": True,
            "release_profile": "release",
        },
        "source_identity_sha256": current_source_identity,
        "input_files": dict(sorted(inputs.items())),
        "claim": "Build inputs pinned; independent byte-for-byte rebuild comparison not yet performed.",
    }
    validate_document(document)
    return document


def document_for_bundle(capability: Path, release_profile: str, target: str) -> dict[str, Any]:
    try:
        verify_bundle(capability)
        profile = load((capability / "profile.json").read_bytes())
        bundle_digest = (capability / "bundle-sha256.txt").read_text(encoding="ascii").strip()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise BuildInputError(f"invalid capability bundle: {exc}") from exc
    return recipe_document(
        profile=profile,
        capability_bundle_sha256=bundle_digest,
        release_profile=release_profile,
        target=target,
        current_source_identity=source_identity(),
        inputs=file_hashes(),
    )


def write_identity(document: dict[str, Any], output: Path) -> None:
    payload = canonical(document)
    if output.exists() and output.read_bytes() != payload:
        raise BuildInputError("existing build-input identity differs; do not overwrite provenance")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)


def verify_identity(path: Path) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
        document = load(payload)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise BuildInputError(f"invalid build-input identity: {exc}") from exc
    if canonical(document) != payload:
        raise BuildInputError("build-input identity is not canonical")
    validate_document(document)
    if (document.get("format"), document.get("format_version")) != (FORMAT, FORMAT_VERSION):
        raise BuildInputError("unsupported build-input identity format")
    if document.get("project_version") != workspace_version():
        raise BuildInputError("build-input project version does not match this source tree")
    if document.get("source_identity_sha256") != source_identity():
        raise BuildInputError("build-input source identity does not match this source tree")
    if document.get("input_files") != file_hashes():
        raise BuildInputError("build-input file digests do not match this source tree")
    if document.get("rust", {}).get("channel") != pinned_rust_channel():
        raise BuildInputError("build-input Rust channel does not match this source tree")
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--capability", type=Path)
    parser.add_argument("--profile", choices=("native-static", "no-import-wasm"))
    parser.add_argument("--target")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.verify is not None:
            verify_identity(args.verify)
            print("PASS build-input identity")
            return 0
        if None in (args.capability, args.profile, args.target, args.output):
            parser.error("generation requires --capability --profile --target --output")
        document = document_for_bundle(args.capability, args.profile, args.target)
        write_identity(document, args.output)
        print(f"PASS build-input identity sha256={digest(canonical(document))}")
        return 0
    except BuildInputError as exc:
        print(f"FAIL build-input identity: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
