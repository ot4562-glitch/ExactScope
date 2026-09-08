#!/usr/bin/env python3
"""Build and verify the standalone ExactScope v1 native grounding SDK.

This is deliberately separate from the historical capability/evaluation bundle:
the flagship v1 product is the provider-neutral grounding runtime. Deployment
provider data is application-specific; the package carries only a tiny,
demonstration-only XSGI index.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import shutil
import tarfile
import tempfile
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FORMAT = "exactscope.grounding.runtime.bundle"
FORMAT_VERSION = "1.0"
AR_MAGIC = b"!<arch>\n"
XSGI_MAGIC = b"XSGI"
SOURCE_COMMIT_RE = re.compile(r"^[a-f0-9]{40}$")
STABLE_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
SAFE_COMPONENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

MAX_ARCHIVE_MEMBERS = 128
MAX_ARCHIVE_MEMBER_BYTES = 16 * 1024 * 1024
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 20_000_000
MAX_ARCHIVE_COMPRESSED_BYTES = 10_000_000
# Includes tar headers and extended metadata, not only extracted regular-file bytes.
MAX_ARCHIVE_TAR_BYTES = MAX_ARCHIVE_UNCOMPRESSED_BYTES + 1_000_000
MAX_ARCHIVE_PATH_BYTES = 512
SAMPLE_INDEX_PATH = "grounding/sample-index-v1.xsgi"


class GroundingRuntimePackageError(RuntimeError):
    """Raised when a grounding runtime package is invalid or ambiguous."""


def canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def release_version() -> str:
    with (ROOT / "Cargo.toml").open("rb") as handle:
        document = tomllib.load(handle)
    version = document.get("workspace", {}).get("package", {}).get("version")
    if not isinstance(version, str) or not SAFE_COMPONENT_RE.fullmatch(version):
        raise GroundingRuntimePackageError("workspace release version is not archive-safe")
    return version


def release_tier(version: str) -> str:
    return "stable" if STABLE_VERSION_RE.fullmatch(version) else "candidate"


def safe_component(value: str, label: str) -> str:
    if not isinstance(value, str) or not SAFE_COMPONENT_RE.fullmatch(value):
        raise GroundingRuntimePackageError(f"invalid {label}: {value!r}")
    return value


def package_root_name(version: str, target: str) -> str:
    return f"exactscope-grounding-{safe_component(version, 'version')}-{safe_component(target, 'target')}"


def normalized_member_name(name: str) -> PurePosixPath:
    if not isinstance(name, str) or len(name.encode("utf-8")) > MAX_ARCHIVE_PATH_BYTES:
        raise GroundingRuntimePackageError("archive path is missing or too long")
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
        raise GroundingRuntimePackageError(f"unsafe archive path: {name!r}")
    return path


def validate_static_library(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise GroundingRuntimePackageError("native runtime must be a regular static library")
    if path.name not in {"libexactscope_cabi.a", "exactscope_cabi.lib"}:
        raise GroundingRuntimePackageError("native runtime filename is not canonical")
    with path.open("rb") as handle:
        if handle.read(len(AR_MAGIC)) != AR_MAGIC:
            raise GroundingRuntimePackageError("native runtime is not an ar/COFF static archive")


def validate_sample_index(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise GroundingRuntimePackageError("sample grounding index must be a regular file")
    size = path.stat().st_size
    if size <= len(XSGI_MAGIC) or size > 1024 * 1024:
        raise GroundingRuntimePackageError("demonstration index must be nonempty and <= 1 MiB")
    with path.open("rb") as handle:
        if handle.read(len(XSGI_MAGIC)) != XSGI_MAGIC:
            raise GroundingRuntimePackageError("sample grounding index is missing XSGI magic")


def copy_file(source: Path, destination: Path) -> None:
    if source.is_symlink() or not source.is_file():
        raise GroundingRuntimePackageError(f"release payload must be a regular file: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def payload_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in {"manifest.json", "SHA256SUMS"}:
            continue
        hashes[relative] = sha256_file(path)
    return hashes


def checksum_text(root: Path, names: list[str]) -> str:
    return "".join(f"{sha256_file(root / name)}  {name}\n" for name in names)


def validate_manifest(manifest: dict[str, Any]) -> None:
    required = {
        "format",
        "format_version",
        "release_version",
        "release_tier",
        "target",
        "source_commit",
        "toolchain",
        "runtime",
        "sample_provider",
        "deployment_boundary",
        "support_scope",
        "files",
    }
    if not isinstance(manifest, dict) or set(manifest) != required:
        raise GroundingRuntimePackageError("grounding runtime manifest shape is invalid")
    if (manifest.get("format"), manifest.get("format_version")) != (FORMAT, FORMAT_VERSION):
        raise GroundingRuntimePackageError("unsupported grounding runtime manifest identity")
    version = manifest.get("release_version")
    if not isinstance(version, str) or not SAFE_COMPONENT_RE.fullmatch(version):
        raise GroundingRuntimePackageError("manifest release version is invalid")
    if manifest.get("release_tier") != release_tier(version):
        raise GroundingRuntimePackageError("manifest release tier disagrees with semantic version")
    target = manifest.get("target")
    safe_component(target, "manifest target")
    source_commit = manifest.get("source_commit")
    if not isinstance(source_commit, str) or not SOURCE_COMMIT_RE.fullmatch(source_commit):
        raise GroundingRuntimePackageError("manifest source commit is invalid")
    toolchain = manifest.get("toolchain")
    if not isinstance(toolchain, str) or not toolchain or len(toolchain) > 200 or any(ch in toolchain for ch in "\r\n"):
        raise GroundingRuntimePackageError("manifest toolchain is invalid")

    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict) or set(runtime) != {"path", "size_bytes", "sha256"}:
        raise GroundingRuntimePackageError("manifest runtime identity is invalid")
    expected_runtime = f"lib/{target}/libexactscope_cabi.a"
    if runtime.get("path") != expected_runtime:
        raise GroundingRuntimePackageError("manifest runtime path is not canonical")
    if not isinstance(runtime.get("size_bytes"), int) or runtime["size_bytes"] <= 0:
        raise GroundingRuntimePackageError("manifest runtime size is invalid")
    if not isinstance(runtime.get("sha256"), str) or not re.fullmatch(r"[a-f0-9]{64}", runtime["sha256"]):
        raise GroundingRuntimePackageError("manifest runtime digest is invalid")

    sample = manifest.get("sample_provider")
    if not isinstance(sample, dict) or set(sample) != {"path", "purpose", "size_bytes", "sha256"}:
        raise GroundingRuntimePackageError("manifest sample provider identity is invalid")
    if sample.get("path") != SAMPLE_INDEX_PATH or sample.get("purpose") != "demonstration-only":
        raise GroundingRuntimePackageError("sample provider must remain demonstration-only")
    if not isinstance(sample.get("size_bytes"), int) or sample["size_bytes"] <= 0:
        raise GroundingRuntimePackageError("manifest sample provider size is invalid")
    if not isinstance(sample.get("sha256"), str) or not re.fullmatch(r"[a-f0-9]{64}", sample["sha256"]):
        raise GroundingRuntimePackageError("manifest sample provider digest is invalid")

    boundary = manifest.get("deployment_boundary")
    if boundary != {
        "provider_data": "deployment-specific-not-included",
        "model_runtime": "host-owned-not-included",
        "network_service": "not-required",
        "python_runtime": "not-required-on-target",
    }:
        raise GroundingRuntimePackageError("deployment boundary drift")

    support = manifest.get("support_scope")
    expected_support = {
        "native_target": target,
        "native_status": "stable" if release_tier(version) == "stable" else "candidate",
        "physical_arm64": "not-claimed",
        "wasm_grounding": "not-included",
    }
    if support != expected_support:
        raise GroundingRuntimePackageError("support scope drift")

    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise GroundingRuntimePackageError("manifest file inventory is empty")
    for relative, digest in files.items():
        if normalized_member_name(relative).as_posix() != relative:
            raise GroundingRuntimePackageError("manifest file path is noncanonical")
        if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise GroundingRuntimePackageError("manifest file digest is invalid")


def stage_bundle(
    stage_parent: Path,
    *,
    library: Path,
    sample_index: Path,
    target: str,
    source_commit: str,
    toolchain: str,
) -> tuple[Path, dict[str, Any]]:
    version = release_version()
    safe_component(target, "target")
    if target != "x86_64-unknown-linux-gnu":
        raise GroundingRuntimePackageError(
            "v1 stable grounding package currently supports only x86_64-unknown-linux-gnu"
        )
    if not SOURCE_COMMIT_RE.fullmatch(source_commit):
        raise GroundingRuntimePackageError("source commit must be 40 lowercase hexadecimal characters")
    if not toolchain or len(toolchain) > 200 or any(ch in toolchain for ch in "\r\n"):
        raise GroundingRuntimePackageError("invalid toolchain identity")
    validate_static_library(library)
    validate_sample_index(sample_index)

    root = stage_parent / package_root_name(version, target)
    root.mkdir(parents=True, exist_ok=False)
    runtime_path = f"lib/{target}/libexactscope_cabi.a"

    fixed_payloads = {
        "include/exactscope.h": ROOT / "include/exactscope.h",
        "include/exactscope_platform.h": ROOT / "include/exactscope_platform.h",
        "lib/cmake/ExactScope/ExactScopeConfig.cmake": ROOT / "cmake/ExactScopeConfig.cmake",
        "examples/c/grounding.c": ROOT / "examples/c/grounding.c",
        "examples/grounding/sample-docs/device-state.md": ROOT / "examples/grounding/sample-docs/device-state.md",
        "examples/grounding/sample-docs/service-policy.md": ROOT / "examples/grounding/sample-docs/service-policy.md",
        "README.md": ROOT / "docs/GROUNDING_NATIVE_QUICKSTART.md",
        "LICENSE-MIT": ROOT / "LICENSE-MIT",
        "LICENSE-APACHE": ROOT / "LICENSE-APACHE",
        "THIRD_PARTY_NOTICES.md": ROOT / "THIRD_PARTY_NOTICES.md",
    }
    for relative, source in fixed_payloads.items():
        copy_file(source, root / relative)
    copy_file(library, root / runtime_path)
    copy_file(sample_index, root / SAMPLE_INDEX_PATH)

    files = payload_hashes(root)
    manifest = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "release_version": version,
        "release_tier": release_tier(version),
        "target": target,
        "source_commit": source_commit,
        "toolchain": toolchain,
        "runtime": {
            "path": runtime_path,
            "size_bytes": (root / runtime_path).stat().st_size,
            "sha256": files[runtime_path],
        },
        "sample_provider": {
            "path": SAMPLE_INDEX_PATH,
            "purpose": "demonstration-only",
            "size_bytes": (root / SAMPLE_INDEX_PATH).stat().st_size,
            "sha256": files[SAMPLE_INDEX_PATH],
        },
        "deployment_boundary": {
            "provider_data": "deployment-specific-not-included",
            "model_runtime": "host-owned-not-included",
            "network_service": "not-required",
            "python_runtime": "not-required-on-target",
        },
        "support_scope": {
            "native_target": target,
            "native_status": "stable" if release_tier(version) == "stable" else "candidate",
            "physical_arm64": "not-claimed",
            "wasm_grounding": "not-included",
        },
        "files": files,
    }
    validate_manifest(manifest)
    (root / "manifest.json").write_bytes(canonical(manifest))
    checksum_names = sorted([*files, "manifest.json"])
    (root / "SHA256SUMS").write_text(
        checksum_text(root, checksum_names), encoding="ascii", newline="\n"
    )
    return root, manifest


def deterministic_archive_bytes(root: Path) -> bytes:
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        paths = [root, *sorted(root.rglob("*"), key=lambda path: path.relative_to(root.parent).as_posix())]
        for path in paths:
            relative = path.relative_to(root.parent).as_posix()
            if path.is_symlink():
                raise GroundingRuntimePackageError(f"symlink forbidden in release bundle: {relative}")
            info = tarfile.TarInfo(relative + ("/" if path.is_dir() else ""))
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            if path.is_dir():
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                info.size = 0
                archive.addfile(info)
            elif path.is_file():
                data = path.read_bytes()
                info.mode = 0o644
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
            else:
                raise GroundingRuntimePackageError(f"unsupported release payload type: {relative}")
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0, compresslevel=9) as compressed:
        compressed.write(tar_buffer.getvalue())
    return output.getvalue()


def parse_checksums(text: str) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for line in text.splitlines():
        if not line:
            continue
        match = re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9][A-Za-z0-9._/-]*)", line)
        if match is None or match.group(2) in checksums:
            raise GroundingRuntimePackageError("invalid or duplicate SHA256SUMS entry")
        relative = normalized_member_name(match.group(2)).as_posix()
        checksums[relative] = match.group(1)
    if not checksums:
        raise GroundingRuntimePackageError("SHA256SUMS is empty")
    return checksums


def verify_extracted(root: Path) -> dict[str, Any]:
    manifest_path = root / "manifest.json"
    checksum_path = root / "SHA256SUMS"
    if not manifest_path.is_file() or not checksum_path.is_file():
        raise GroundingRuntimePackageError("package is missing manifest.json or SHA256SUMS")
    manifest_bytes = manifest_path.read_bytes()
    try:
        manifest = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GroundingRuntimePackageError(f"invalid package manifest: {exc}") from exc
    if canonical(manifest) != manifest_bytes:
        raise GroundingRuntimePackageError("package manifest is not canonical")
    validate_manifest(manifest)
    if root.name != package_root_name(manifest["release_version"], manifest["target"]):
        raise GroundingRuntimePackageError("package root does not match manifest identity")

    files = manifest["files"]
    expected = set(files) | {"manifest.json", "SHA256SUMS"}
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    if actual != expected:
        raise GroundingRuntimePackageError("package file inventory mismatch")
    for relative, expected_digest in files.items():
        if sha256_file(root / relative) != expected_digest:
            raise GroundingRuntimePackageError(f"package payload digest mismatch: {relative}")

    checksums = parse_checksums(checksum_path.read_text(encoding="ascii"))
    if set(checksums) != set(files) | {"manifest.json"}:
        raise GroundingRuntimePackageError("SHA256SUMS inventory mismatch")
    for relative, expected_digest in checksums.items():
        if sha256_file(root / relative) != expected_digest:
            raise GroundingRuntimePackageError(f"SHA256SUMS digest mismatch: {relative}")

    runtime_path = manifest["runtime"]["path"]
    runtime = root / runtime_path
    validate_static_library(runtime)
    if manifest["runtime"]["size_bytes"] != runtime.stat().st_size or manifest["runtime"]["sha256"] != sha256_file(runtime):
        raise GroundingRuntimePackageError("runtime measurement mismatch")
    sample = root / manifest["sample_provider"]["path"]
    validate_sample_index(sample)
    if manifest["sample_provider"]["size_bytes"] != sample.stat().st_size or manifest["sample_provider"]["sha256"] != sha256_file(sample):
        raise GroundingRuntimePackageError("sample provider measurement mismatch")
    return manifest


def bounded_tar_payload(path: Path) -> bytes:
    """Decompress a gzip archive under a hard whole-tar byte ceiling."""
    output = io.BytesIO()
    total = 0
    with path.open("rb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="rb") as compressed:
            while True:
                remaining = MAX_ARCHIVE_TAR_BYTES - total
                block = compressed.read(min(64 * 1024, remaining + 1))
                if not block:
                    break
                total += len(block)
                if total > MAX_ARCHIVE_TAR_BYTES:
                    raise GroundingRuntimePackageError(
                        f"decompressed tar stream exceeds {MAX_ARCHIVE_TAR_BYTES} byte hard cap"
                    )
                output.write(block)
    return output.getvalue()


def verify_archive(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise GroundingRuntimePackageError(f"package does not exist: {path}")
    compressed_bytes = path.stat().st_size
    if compressed_bytes > MAX_ARCHIVE_COMPRESSED_BYTES:
        raise GroundingRuntimePackageError(
            f"default package exceeds {MAX_ARCHIVE_COMPRESSED_BYTES} byte compressed hard cap"
        )
    tar_payload = bounded_tar_payload(path)
    with tempfile.TemporaryDirectory(prefix="exactscope-grounding-verify-") as temporary:
        destination = Path(temporary)
        with tarfile.open(fileobj=io.BytesIO(tar_payload), mode="r:") as archive:
            members: list[tarfile.TarInfo] = []
            roots: set[str] = set()
            names: set[str] = set()
            total_size = 0
            for member in archive:
                if len(members) >= MAX_ARCHIVE_MEMBERS:
                    raise GroundingRuntimePackageError("package archive member count is invalid")
                normalized = normalized_member_name(member.name.rstrip("/"))
                name = normalized.as_posix()
                if name in names:
                    raise GroundingRuntimePackageError(f"duplicate archive member path: {member.name}")
                names.add(name)
                roots.add(normalized.parts[0])
                if not (member.isfile() or member.isdir()) or member.issym() or member.islnk():
                    raise GroundingRuntimePackageError(f"forbidden archive member type: {member.name}")
                if member.isfile():
                    if member.size < 0 or member.size > MAX_ARCHIVE_MEMBER_BYTES:
                        raise GroundingRuntimePackageError(f"archive member exceeds size limit: {member.name}")
                    total_size += member.size
                    if total_size > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                        raise GroundingRuntimePackageError(
                            f"default package exceeds {MAX_ARCHIVE_UNCOMPRESSED_BYTES} byte unpacked hard cap"
                        )
                members.append(member)
            if not members:
                raise GroundingRuntimePackageError("package archive member count is invalid")
            if len(roots) != 1:
                raise GroundingRuntimePackageError("package must contain exactly one root directory")
            archive.extractall(destination, members=members, filter="data")
        root = destination / next(iter(roots))
        manifest = verify_extracted(root)
        return {
            "manifest": manifest,
            "archive_bytes": compressed_bytes,
            "unpacked_file_bytes": total_size,
            "file_count": sum(1 for path in root.rglob("*") if path.is_file()),
        }


def build_archive(
    *,
    library: Path,
    sample_index: Path,
    target: str,
    source_commit: str,
    toolchain: str,
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="exactscope-grounding-stage-") as temporary:
        root, _ = stage_bundle(
            Path(temporary),
            library=library,
            sample_index=sample_index,
            target=target,
            source_commit=source_commit,
            toolchain=toolchain,
        )
        payload = deterministic_archive_bytes(root)
        if len(payload) > MAX_ARCHIVE_COMPRESSED_BYTES:
            raise GroundingRuntimePackageError(
                f"default package exceeds {MAX_ARCHIVE_COMPRESSED_BYTES} byte compressed hard cap"
            )
        output = output_dir / f"{root.name}.tar.gz"
        if output.exists() and output.read_bytes() != payload:
            raise GroundingRuntimePackageError("immutable package already exists with different bytes")
        output.write_bytes(payload)
    verify_archive(output)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--library", type=Path, required=True)
    build.add_argument("--sample-index", type=Path, required=True)
    build.add_argument("--target", default="x86_64-unknown-linux-gnu")
    build.add_argument("--source-commit", required=True)
    build.add_argument("--toolchain", required=True)
    build.add_argument("--output-dir", type=Path, required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("archive", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "verify":
            result = verify_archive(args.archive)
            manifest = result["manifest"]
            print(json.dumps({
                "status": "PASS",
                "release_version": manifest["release_version"],
                "release_tier": manifest["release_tier"],
                "target": manifest["target"],
                "archive_bytes": result["archive_bytes"],
                "unpacked_file_bytes": result["unpacked_file_bytes"],
                "file_count": result["file_count"],
            }, sort_keys=True))
            return 0
        archive = build_archive(
            library=args.library,
            sample_index=args.sample_index,
            target=args.target,
            source_commit=args.source_commit,
            toolchain=args.toolchain,
            output_dir=args.output_dir,
        )
        result = verify_archive(archive)
        print(json.dumps({
            "status": "PASS",
            "archive": str(archive),
            "archive_sha256": sha256_file(archive),
            "archive_bytes": result["archive_bytes"],
            "unpacked_file_bytes": result["unpacked_file_bytes"],
            "runtime_bytes": result["manifest"]["runtime"]["size_bytes"],
            "sample_index_bytes": result["manifest"]["sample_provider"]["size_bytes"],
        }, sort_keys=True))
        return 0
    except (GroundingRuntimePackageError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ExactScope grounding runtime package: FAIL: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
