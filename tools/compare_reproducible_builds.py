#!/usr/bin/env python3
"""Compare two ExactScope build outputs against one pinned build-input identity.

This tool compares bytes only. Builder IDs are caller-provided labels; the tool
cannot prove that the builders were organizationally, physically, or hermetically
independent. It never executes either artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from build_input_identity import BuildInputError, canonical, load, verify_identity
from compile_capability import ROOT

FORMAT = "exactscope.reproducible-build.comparison"
FORMAT_VERSION = "0.1"
SCHEMA = ROOT / "spec/schemas/reproducible-build-comparison.schema.json"
MAX_ARTIFACT_BYTES = 256 * 1024 * 1024


class RebuildComparisonError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_record(document: dict[str, Any]) -> None:
    schema = load(SCHEMA.read_bytes())
    errors = sorted(
        Draft202012Validator(schema).iter_errors(document),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path) or "<root>"
        raise RebuildComparisonError(f"comparison schema failed at {location}: {first.message}")
    builders = document["builders"]
    if builders[0]["id"] == builders[1]["id"]:
        raise RebuildComparisonError("builder IDs must be distinct")
    identical = builders[0]["artifact_sha256"] == builders[1]["artifact_sha256"]
    identical = identical and builders[0]["size_bytes"] == builders[1]["size_bytes"]
    if document["byte_identical"] != identical:
        raise RebuildComparisonError("byte-identical flag disagrees with artifact records")
    expected_status = "MATCH" if identical else "MISMATCH"
    if document["status"] != expected_status:
        raise RebuildComparisonError("comparison status disagrees with artifact records")


def artifact_record(path: Path, builder_id: str) -> dict[str, Any]:
    if not builder_id or len(builder_id) > 128 or any(ch in builder_id for ch in "\r\n"):
        raise RebuildComparisonError("builder ID must be printable, nonempty, and <=128 characters")
    if path.is_symlink() or not path.is_file():
        raise RebuildComparisonError(f"artifact is not a regular file: {path}")
    size = path.stat().st_size
    if size <= 0 or size > MAX_ARTIFACT_BYTES:
        raise RebuildComparisonError(f"artifact size is outside comparison bounds: {path}")
    return {"id": builder_id, "artifact_sha256": sha256_file(path), "size_bytes": size}


def compare(
    *,
    build_inputs: Path,
    artifact_a: Path,
    builder_a: str,
    artifact_b: Path,
    builder_b: str,
) -> dict[str, Any]:
    try:
        build_document = verify_identity(build_inputs)
        build_bytes = build_inputs.read_bytes()
    except (BuildInputError, OSError, ValueError, json.JSONDecodeError) as exc:
        raise RebuildComparisonError(f"invalid build-input identity: {exc}") from exc
    first = artifact_record(artifact_a, builder_a)
    second = artifact_record(artifact_b, builder_b)
    if first["id"] == second["id"]:
        raise RebuildComparisonError("builder IDs must be distinct")
    identical = (
        first["artifact_sha256"] == second["artifact_sha256"]
        and first["size_bytes"] == second["size_bytes"]
    )
    release_profile = build_document["release_profile"]
    artifact_kind = "wasm-module" if release_profile == "no-import-wasm" else "static-library"
    document = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "build_input_sha256": hashlib.sha256(build_bytes).hexdigest(),
        "release_profile": release_profile,
        "target": build_document["target"],
        "artifact_kind": artifact_kind,
        "builders": [first, second],
        "byte_identical": identical,
        "status": "MATCH" if identical else "MISMATCH",
        "claim": (
            "Two caller-identified build outputs are byte-identical for the recorded inputs; "
            "builder independence and runtime qualification are not implied."
            if identical
            else "Build outputs differ; reproducible-build proof is not established."
        ),
    }
    validate_record(document)
    return document


def write_record(document: dict[str, Any], output: Path) -> None:
    payload = canonical(document)
    if output.exists() and output.read_bytes() != payload:
        raise RebuildComparisonError("existing comparison record differs; do not overwrite evidence")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)


def verify_record(path: Path, build_inputs: Path | None = None) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
        document = load(payload)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise RebuildComparisonError(f"invalid comparison record: {exc}") from exc
    if canonical(document) != payload:
        raise RebuildComparisonError("comparison record is not canonical")
    validate_record(document)
    if build_inputs is not None:
        try:
            build_document = verify_identity(build_inputs)
            build_bytes = build_inputs.read_bytes()
        except (BuildInputError, OSError, ValueError, json.JSONDecodeError) as exc:
            raise RebuildComparisonError(f"invalid build-input identity: {exc}") from exc
        if document["build_input_sha256"] != hashlib.sha256(build_bytes).hexdigest():
            raise RebuildComparisonError("comparison/build-input digest mismatch")
        if (document["release_profile"], document["target"]) != (
            build_document["release_profile"], build_document["target"]
        ):
            raise RebuildComparisonError("comparison/build-input profile or target mismatch")
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--build-inputs", type=Path)
    parser.add_argument("--artifact-a", type=Path)
    parser.add_argument("--builder-a")
    parser.add_argument("--artifact-b", type=Path)
    parser.add_argument("--builder-b")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.verify is not None:
            document = verify_record(args.verify, args.build_inputs)
            print(f"PASS rebuild comparison record status={document['status']}")
            return 0 if document["status"] == "MATCH" else 2
        required = (args.build_inputs, args.artifact_a, args.builder_a, args.artifact_b, args.builder_b, args.output)
        if any(value is None for value in required):
            parser.error("comparison requires build inputs, two artifacts/builder IDs, and output")
        document = compare(
            build_inputs=args.build_inputs,
            artifact_a=args.artifact_a,
            builder_a=args.builder_a,
            artifact_b=args.artifact_b,
            builder_b=args.builder_b,
        )
        write_record(document, args.output)
        print(f"PASS rebuild comparison status={document['status']}")
        return 0 if document["status"] == "MATCH" else 2
    except (OSError, ValueError, json.JSONDecodeError, RebuildComparisonError) as exc:
        print(f"FAIL rebuild comparison: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
