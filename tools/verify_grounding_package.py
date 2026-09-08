#!/usr/bin/env python3
"""Verify an extracted ExactScope grounding evaluation package. Zero inference."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys


sys.dont_write_bytecode = True
SHA_RE = re.compile(r"^[a-f0-9]{64}$")


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


def is_gold_payload(relative: str) -> bool:
    return relative == "candidate/manifests/gold-manifest.json" or relative.startswith("candidate/gold/")


def load_surface_sha(path: Path) -> str:
    spec = importlib.util.spec_from_file_location("exactscope_packaged_grounding_v1_surface", path)
    if spec is None or spec.loader is None:
        raise PackageVerificationError("cannot load packaged grounding v1 surface")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    digest = module.surface_sha256()
    if not isinstance(digest, str) or not SHA_RE.fullmatch(digest):
        raise PackageVerificationError("packaged grounding v1 surface produced invalid digest")
    return digest


def verify(root: Path, *, serving_only: bool = False) -> dict[str, object]:
    root = root.resolve()
    manifest_path = root / "package-manifest.json"
    sums_path = root / "SHA256SUMS"
    if not manifest_path.is_file() or not sums_path.is_file():
        raise PackageVerificationError("missing package-manifest.json or SHA256SUMS")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "exactscope.grounding-evaluation-package" or manifest.get("format_version") != "0.3":
        raise PackageVerificationError("unsupported package manifest")
    if manifest.get("model_inference_performed") is not False:
        raise PackageVerificationError("package manifest is not pre-inference")
    for key in (
        "candidate_manifest_sha256",
        "model_inventory_sha256",
        "runtime_record_sha256",
        "generation_config_sha256",
        "isolation_policy_sha256",
        "scorer_sha256",
        "model_surface_sha256",
        "model_surface_module_sha256",
        "grounding_corpus_module_sha256",
        "grounding_projection_module_sha256",
        "llama_cpp_adapter_sha256",
    ):
        if not isinstance(manifest.get(key), str) or not SHA_RE.fullmatch(manifest[key]):
            raise PackageVerificationError(f"invalid package identity digest: {key}")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise PackageVerificationError("package manifest has no files")
    seen: set[str] = set()
    verified_payload: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "bytes"}:
            raise PackageVerificationError("invalid package file entry")
        relative = entry["path"]
        if not isinstance(relative, str) or relative in seen:
            raise PackageVerificationError("duplicate/invalid package file path")
        rel = Path(relative)
        if rel.is_absolute() or ".." in rel.parts:
            raise PackageVerificationError(f"unsafe package path: {relative}")
        seen.add(relative)
        if serving_only and is_gold_payload(relative):
            # The runner may see the frozen hash references in package metadata,
            # but it must never open/hash scorer-only gold bytes.
            continue
        path = safe_path(root, relative)
        if not path.is_file():
            raise PackageVerificationError(f"missing package file: {relative}")
        if path.stat().st_size != entry["bytes"]:
            raise PackageVerificationError(f"byte-size mismatch: {relative}")
        if sha256(path) != entry["sha256"]:
            raise PackageVerificationError(f"sha256 mismatch: {relative}")
        verified_payload.add(relative)
    actual_payload = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path.name not in {"package-manifest.json", "SHA256SUMS"}
        and (not serving_only or not is_gold_payload(path.relative_to(root).as_posix()))
    }
    expected_payload = verified_payload if serving_only else seen
    if actual_payload != expected_payload:
        missing = sorted(actual_payload - expected_payload)
        extra = sorted(expected_payload - actual_payload)
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
        if serving_only and is_gold_payload(relative):
            continue
        path = safe_path(root, relative)
        if not path.is_file() or sha256(path) != digest:
            raise PackageVerificationError(f"SHA256SUMS mismatch: {relative}")

    named_identities = {
        "candidate_manifest_sha256": "candidate/manifests/candidate-manifest.json",
        "model_inventory_sha256": "benchmarks/grounding-model-inventory.json",
        "runtime_record_sha256": "benchmarks/grounding-runtime-llama-v040.json",
        "generation_config_sha256": "benchmarks/grounding-generation-config.json",
        "isolation_policy_sha256": "benchmarks/grounding-isolation-policy.json",
        "scorer_sha256": "benchmarks/score_grounding.py",
        "model_surface_module_sha256": "tools/grounding_v1_surface.py",
        "grounding_corpus_module_sha256": "tools/grounding_corpus.py",
        "grounding_projection_module_sha256": "tools/grounding_projection.py",
        "llama_cpp_adapter_sha256": "adapters/llama-cpp/grounding_v1.py",
    }
    for key, relative in named_identities.items():
        path = safe_path(root, relative)
        if not path.is_file() or sha256(path) != manifest[key]:
            raise PackageVerificationError(f"named package identity mismatch: {key}")
    if load_surface_sha(root / "tools/grounding_v1_surface.py") != manifest["model_surface_sha256"]:
        raise PackageVerificationError("semantic grounding model-surface digest mismatch")
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
