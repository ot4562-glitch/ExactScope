#!/usr/bin/env python3
"""Verify an extracted ExactScope grounding evaluation package. Zero inference."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


class PackageVerificationError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe_path(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise PackageVerificationError(f"unsafe package path: {relative}")
    path = (root / rel).resolve()
    if not path.is_relative_to(root.resolve()):
        raise PackageVerificationError(f"package path escapes root: {relative}")
    if path.is_symlink():
        raise PackageVerificationError(f"symlink not permitted in evaluation package: {relative}")
    return path


def verify(root: Path) -> dict[str, object]:
    root = root.resolve()
    manifest_path = root / "package-manifest.json"
    sums_path = root / "SHA256SUMS"
    if not manifest_path.is_file() or not sums_path.is_file():
        raise PackageVerificationError("missing package-manifest.json or SHA256SUMS")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "exactscope.grounding-evaluation-package" or manifest.get("format_version") != "0.1":
        raise PackageVerificationError("unsupported package manifest")
    if manifest.get("model_inference_performed") is not False:
        raise PackageVerificationError("package manifest is not pre-inference")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise PackageVerificationError("package manifest has no files")
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "bytes"}:
            raise PackageVerificationError("invalid package file entry")
        relative = entry["path"]
        if not isinstance(relative, str) or relative in seen:
            raise PackageVerificationError("duplicate/invalid package file path")
        seen.add(relative)
        path = safe_path(root, relative)
        if not path.is_file():
            raise PackageVerificationError(f"missing package file: {relative}")
        if path.stat().st_size != entry["bytes"]:
            raise PackageVerificationError(f"byte-size mismatch: {relative}")
        if sha256(path) != entry["sha256"]:
            raise PackageVerificationError(f"sha256 mismatch: {relative}")
    actual_payload = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"package-manifest.json", "SHA256SUMS"}
    }
    if actual_payload != seen:
        missing = sorted(actual_payload - seen)
        extra = sorted(seen - actual_payload)
        raise PackageVerificationError(f"package manifest file-set mismatch missing={missing} extra={extra}")
    sums: dict[str, str] = {}
    for number, line in enumerate(sums_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        if "  " not in line:
            raise PackageVerificationError(f"invalid SHA256SUMS line {number}")
        digest, relative = line.split("  ", 1)
        if relative in sums:
            raise PackageVerificationError("duplicate SHA256SUMS path")
        sums[relative] = digest
    expected_sum_paths = seen | {"package-manifest.json"}
    if set(sums) != expected_sum_paths:
        raise PackageVerificationError("SHA256SUMS file-set mismatch")
    for relative, digest in sums.items():
        path = safe_path(root, relative)
        if not path.is_file() or sha256(path) != digest:
            raise PackageVerificationError(f"SHA256SUMS mismatch: {relative}")
    return {
        "status": "ok",
        "candidate_id": manifest.get("candidate_id"),
        "source_commit": manifest.get("source_commit"),
        "file_count": len(entries),
        "package_manifest_sha256": sha256(manifest_path),
        "model_inference_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = verify(args.root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PackageVerificationError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ExactScope grounding package verification: FAIL: {exc}")
        raise SystemExit(1) from exc
