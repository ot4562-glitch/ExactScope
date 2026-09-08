#!/usr/bin/env python3
"""Build a deterministic pre-inference ExactScope grounding evaluation archive."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile
from typing import Any

from grounding_v1_surface import surface_sha256

ROOT = Path(__file__).resolve().parents[1]
COMMIT_RE = re.compile(r"^[a-f0-9]{40}$")


class PackageBuildError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PackageBuildError(f"JSON root must be object: {path}")
    return value


def answer_call_policy_binding(policy: dict[str, Any]) -> str:
    if policy.get("format") != "exactscope.grounding-isolation-policy":
        raise PackageBuildError("invalid grounding isolation policy identity")
    version = policy.get("format_version")
    if not isinstance(version, str) or not version:
        raise PackageBuildError("grounding isolation policy version missing")
    return f"bound-by-benchmark-isolation-policy-v{version}"


def copy_file(source: Path, destination: Path) -> None:
    if not source.is_file() or source.is_symlink():
        raise PackageBuildError(f"missing/unsafe source file: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def copy_tree(source: Path, destination: Path) -> None:
    if not source.is_dir() or source.is_symlink():
        raise PackageBuildError(f"missing/unsafe source directory: {source}")
    for path in sorted(source.rglob("*"), key=lambda p: p.relative_to(source).as_posix()):
        if path.is_symlink():
            raise PackageBuildError(f"symlink not allowed in candidate: {path}")
        if path.is_file():
            copy_file(path, destination / path.relative_to(source))


def file_entry(root: Path, path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def deterministic_tar(package_root: Path, archive: Path, archive_root_name: str) -> None:
    archive.parent.mkdir(parents=True, exist_ok=True)
    with archive.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.GNU_FORMAT) as tar:
                for path in sorted((p for p in package_root.rglob("*") if p.is_file()), key=lambda p: p.relative_to(package_root).as_posix()):
                    relative = path.relative_to(package_root).as_posix()
                    info = tar.gettarinfo(str(path), arcname=f"{archive_root_name}/{relative}")
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = 0
                    info.mode = 0o755 if path.suffix == ".py" else 0o644
                    with path.open("rb") as handle:
                        tar.addfile(info, handle)


def build(args: argparse.Namespace) -> dict[str, Any]:
    if not COMMIT_RE.fullmatch(args.source_commit):
        raise PackageBuildError("--source-commit must be 40 lowercase hex chars")
    isolation_policy_source = ROOT / "benchmarks/grounding-isolation-policy.json"
    isolation_policy = load_json(isolation_policy_source)
    expected_call_policy = answer_call_policy_binding(isolation_policy)
    candidate = args.candidate.resolve()
    candidate_manifest_path = candidate / "manifests/candidate-manifest.json"
    candidate_manifest = load_json(candidate_manifest_path)
    if candidate_manifest.get("status") != "generated-before-inference" or candidate_manifest.get("model_inference_performed") is not False:
        raise PackageBuildError("candidate is not pre-inference")
    if candidate_manifest.get("answer_call_policy") != expected_call_policy:
        raise PackageBuildError("candidate answer-call policy is not bound to the selected isolation policy")
    if candidate_manifest.get("arms") != isolation_policy.get("arms") or candidate_manifest.get("rewrite_calls") != 0:
        raise PackageBuildError("candidate A/G execution contract drift")
    candidate_sha_path = candidate / "CANDIDATE_SHA256.txt"
    if not candidate_sha_path.is_file() or candidate_sha_path.read_text(encoding="ascii").strip() != sha256(candidate_manifest_path):
        raise PackageBuildError("candidate manifest digest file drift")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    package_name = f"exactscope-grounding-eval-{args.version}"
    package_root = output / package_name
    archive = output / f"{package_name}.tar.gz"
    digest_file = output / f"{package_name}.tar.gz.sha256"
    for path in (package_root, archive, digest_file):
        if path.exists():
            raise PackageBuildError(f"output already exists: {path}")
    package_root.mkdir(parents=True)
    copy_tree(candidate, package_root / "candidate")

    model_inventory_source = getattr(args, "model_inventory", None) or (ROOT / "benchmarks/grounding-model-inventory.json")
    runtime_record_source = getattr(args, "runtime_record", None) or (ROOT / "benchmarks/grounding-runtime-llama-v040.json")
    mapped_files = {
        "benchmarks/grounding_dry_run.py": ROOT / "benchmarks/grounding_dry_run.py",
        "benchmarks/grounding_preregister.py": ROOT / "benchmarks/grounding_preregister.py",
        "benchmarks/run_grounding_benchmark.py": ROOT / "benchmarks/run_grounding_benchmark.py",
        "benchmarks/score_grounding.py": ROOT / "benchmarks/score_grounding.py",
        "benchmarks/grounding-generation-config.json": ROOT / "benchmarks/grounding-generation-config.json",
        "benchmarks/grounding-isolation-policy.json": isolation_policy_source,
        "benchmarks/grounding-model-inventory.json": model_inventory_source,
        "benchmarks/grounding-runtime-llama-v040.json": runtime_record_source,
        "tools/grounding_canonical.py": ROOT / "tools/grounding_canonical.py",
        "tools/grounding_corpus.py": ROOT / "tools/grounding_corpus.py",
        "tools/grounding_match.py": ROOT / "tools/grounding_match.py",
        "tools/grounding_projection.py": ROOT / "tools/grounding_projection.py",
        "tools/grounding_runtime.py": ROOT / "tools/grounding_runtime.py",
        "tools/grounding_v1_surface.py": ROOT / "tools/grounding_v1_surface.py",
        "tools/verify_grounding_package.py": ROOT / "tools/verify_grounding_package.py",
        "adapters/llama-cpp/grounding_v1.py": ROOT / "adapters/llama-cpp/grounding_v1.py",
        "adapters/llama-cpp/README.md": ROOT / "adapters/llama-cpp/README.md",
        "spec/GROUNDING_CONTRACT_V0_1.md": ROOT / "spec/GROUNDING_CONTRACT_V0_1.md",
        "docs/GROUNDING_ARCHITECTURE.md": ROOT / "docs/GROUNDING_ARCHITECTURE.md",
        "docs/GROUNDING_RUNTIME_RC4.md": ROOT / "docs/GROUNDING_RUNTIME_RC4.md",
        "docs/AI_INTEGRATION.md": ROOT / "docs/AI_INTEGRATION.md",
        "docs/BENCHMARK.md": ROOT / "docs/BENCHMARK.md",
        "README.md": ROOT / "docs/GROUNDING_EVALUATION_PACKAGE.md",
    }
    for relative, source in mapped_files.items():
        copy_file(source, package_root / relative)
    for schema in sorted((ROOT / "spec/schemas").glob("grounding-*.schema.json"), key=lambda p: p.name):
        copy_file(schema, package_root / "spec/schemas" / schema.name)

    payload_files = sorted(
        (path for path in package_root.rglob("*") if path.is_file()),
        key=lambda p: p.relative_to(package_root).as_posix(),
    )
    candidate_manifest_sha = sha256(package_root / "candidate/manifests/candidate-manifest.json")
    model_inventory_sha = sha256(package_root / "benchmarks/grounding-model-inventory.json")
    runtime_record_sha = sha256(package_root / "benchmarks/grounding-runtime-llama-v040.json")
    generation_sha = sha256(package_root / "benchmarks/grounding-generation-config.json")
    isolation_sha = sha256(package_root / "benchmarks/grounding-isolation-policy.json")
    scorer_sha = sha256(package_root / "benchmarks/score_grounding.py")
    model_surface_sha = surface_sha256()
    model_surface_module_sha = sha256(package_root / "tools/grounding_v1_surface.py")
    corpus_module_sha = sha256(package_root / "tools/grounding_corpus.py")
    projection_module_sha = sha256(package_root / "tools/grounding_projection.py")
    adapter_sha = sha256(package_root / "adapters/llama-cpp/grounding_v1.py")
    manifest = {
        "v": 1,
        "format": "exactscope.grounding-evaluation-package",
        "format_version": "0.3",
        "product_version": args.version,
        "source_commit": args.source_commit,
        "candidate_id": candidate_manifest["candidate_id"],
        "candidate_manifest_sha256": candidate_manifest_sha,
        "model_inventory_sha256": model_inventory_sha,
        "runtime_record_sha256": runtime_record_sha,
        "generation_config_sha256": generation_sha,
        "isolation_policy_sha256": isolation_sha,
        "scorer_sha256": scorer_sha,
        "model_surface_sha256": model_surface_sha,
        "model_surface_module_sha256": model_surface_module_sha,
        "grounding_corpus_module_sha256": corpus_module_sha,
        "grounding_projection_module_sha256": projection_module_sha,
        "llama_cpp_adapter_sha256": adapter_sha,
        "model_inference_performed": False,
        "benchmark_state": "pre-inference",
        "files": [file_entry(package_root, path) for path in payload_files],
    }
    manifest_path = package_root / "package-manifest.json"
    write_json(manifest_path, manifest)
    sum_paths = payload_files + [manifest_path]
    sums = "".join(f"{sha256(path)}  {path.relative_to(package_root).as_posix()}\n" for path in sorted(sum_paths, key=lambda p: p.relative_to(package_root).as_posix()))
    (package_root / "SHA256SUMS").write_text(sums, encoding="utf-8", newline="\n")

    deterministic_tar(package_root, archive, package_name)
    archive_sha = sha256(archive)
    digest_file.write_text(f"{archive_sha}  {archive.name}\n", encoding="utf-8", newline="\n")
    return {
        "status": "built-pre-inference",
        "package_root": str(package_root),
        "archive": str(archive),
        "archive_sha256": archive_sha,
        "package_manifest_sha256": sha256(manifest_path),
        "candidate_id": candidate_manifest["candidate_id"],
        "source_commit": args.source_commit,
        "file_count": len(manifest["files"]),
        "model_inference_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", default="1.0.0-rc.4")
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--model-inventory", type=Path, help="override packaged model identity inventory; default is the tracked seven-model rc4/v1 qualification inventory")
    parser.add_argument("--runtime-record", type=Path, help="override packaged inference-runtime identity record; default is the tracked llama.cpp rc4 record")
    args = parser.parse_args()
    result = build(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PackageBuildError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ExactScope grounding package build: FAIL: {exc}")
        raise SystemExit(1) from exc
