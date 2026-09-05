#!/usr/bin/env python3
"""Create/verify an experimental compatibility record for one release archive.

This tool consumes only statically verified release metadata. It cannot promote an
artifact to Tier 1/Tier 2 and it never executes ExactScope.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from compile_capability import ROOT, canonical, load
from package_release_bundle import ReleasePackagingError, sha256_file, verify_archive

FORMAT = "exactscope.compatibility-manifest"
FORMAT_VERSION = "0.1"
SCHEMA = ROOT / "spec/schemas/compatibility-manifest.schema.json"
PACK_FORMAT_SOURCE = ROOT / "crates/exactscope-pack/src/format.rs"


class CompatibilityRecordError(RuntimeError):
    pass


def pack_format_version() -> str:
    text = PACK_FORMAT_SOURCE.read_text(encoding="utf-8")
    major = re.search(r"pub const FORMAT_MAJOR: u16 = ([0-9]+);", text)
    minor = re.search(r"pub const FORMAT_MINOR: u16 = ([0-9]+);", text)
    if major is None or minor is None:
        raise CompatibilityRecordError("cannot derive canonical ScopePack format version")
    return f"{int(major.group(1))}.{int(minor.group(1))}"


def validate_record(document: dict[str, Any]) -> None:
    artifacts = document.get("artifacts") if isinstance(document, dict) else None
    if not isinstance(artifacts, list) or len(artifacts) != 1:
        raise CompatibilityRecordError("release compatibility record must contain exactly one artifact")
    artifact = artifacts[0]
    if not isinstance(artifact, dict) or artifact.get("support") != "experimental":
        raise CompatibilityRecordError("this tool records experimental compatibility only")
    if not isinstance(artifact.get("release_identity"), dict):
        raise CompatibilityRecordError("release compatibility record requires exact release identity")

    schema = load(SCHEMA.read_bytes())
    errors = sorted(
        Draft202012Validator(schema).iter_errors(document),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path) or "<root>"
        raise CompatibilityRecordError(
            f"compatibility record schema failed at {location}: {first.message}"
        )

    identity = artifact["release_identity"]
    if artifact.get("sha256") != identity.get("release_archive_sha256"):
        raise CompatibilityRecordError("artifact/release archive digest mismatch")
    if document.get("core_abi") != identity.get("abi_revision"):
        raise CompatibilityRecordError("compatibility ABI identity mismatch")


def record_for_archive(archive: Path) -> dict[str, Any]:
    try:
        manifest = verify_archive(archive)
    except (OSError, ValueError, json.JSONDecodeError, ReleasePackagingError) as exc:
        raise CompatibilityRecordError(f"invalid release archive: {exc}") from exc
    if manifest.get("support") != "experimental" or manifest.get("qualification") != "unqualified":
        raise CompatibilityRecordError("only experimental/unqualified release archives may be recorded here")

    capability = manifest["capability"]
    archive_sha = sha256_file(archive)
    release_manifest_sha = hashlib.sha256(canonical(manifest)).hexdigest()
    release_identity: dict[str, Any] = {
        "release_format": manifest["format"],
        "release_format_version": manifest["format_version"],
        "release_archive_sha256": archive_sha,
        "release_manifest_sha256": release_manifest_sha,
        "release_profile": manifest["profile"],
        "abi_revision": capability["abi_revision"],
        "runtime_sha256": manifest["runtime"]["sha256"],
        "capability_bundle_sha256": capability["bundle_sha256"],
        "capability_profile_id": capability["profile_id"],
        "capability_profile_revision": capability["profile_revision"],
        "model_surface_sha256": capability["surface_contract_sha256"],
    }
    build_inputs = manifest.get("build_inputs")
    if isinstance(build_inputs, dict):
        release_identity["build_input_sha256"] = build_inputs["sha256"]

    document = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "project_version": manifest["release_version"],
        "source_commit": manifest["source_commit"],
        "core_abi": capability["abi_revision"],
        "pack_format": pack_format_version(),
        "artifacts": [
            {
                "target": manifest["target"],
                "artifact": archive.name,
                "artifact_kind": "archive",
                "support": "experimental",
                "toolchain": manifest["toolchain"],
                "features": [manifest["profile"]],
                "sha256": archive_sha,
                "size_bytes": archive.stat().st_size,
                "release_identity": release_identity,
                "notes": (
                    "Static release identity record only; runtime/target conformance and "
                    "support promotion require separate evidence."
                ),
            }
        ],
    }
    validate_record(document)
    return document


def write_record(document: dict[str, Any], output: Path) -> None:
    payload = canonical(document)
    if output.exists() and output.read_bytes() != payload:
        raise CompatibilityRecordError("existing compatibility record differs; do not overwrite evidence")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)


def verify_record(record_path: Path, archive: Path) -> dict[str, Any]:
    try:
        payload = record_path.read_bytes()
        document = load(payload)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise CompatibilityRecordError(f"invalid compatibility record: {exc}") from exc
    if canonical(document) != payload:
        raise CompatibilityRecordError("compatibility record is not canonical")
    validate_record(document)
    expected = record_for_archive(archive)
    if document != expected:
        raise CompatibilityRecordError("compatibility record does not match the exact release archive")
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    try:
        if args.verify is not None:
            verify_record(args.verify, args.release)
            print("PASS experimental release compatibility record")
            return 0
        if args.output is None:
            parser.error("record generation requires --output")
        document = record_for_archive(args.release)
        write_record(document, args.output)
        print("PASS experimental release compatibility record")
        return 0
    except (OSError, ValueError, json.JSONDecodeError, CompatibilityRecordError) as exc:
        print(f"FAIL compatibility record: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
