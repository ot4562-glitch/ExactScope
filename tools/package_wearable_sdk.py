#!/usr/bin/env python3
"""Build and verify deterministic ExactScope wearable OEM SDK archives."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import sys
import tarfile
import tempfile
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECT_MANIFEST = ROOT / "Cargo.toml"

SUPPORTED_TARGETS = {
    "aarch64-linux-android",
    "aarch64-unknown-linux-musl",
}

PUBLIC_FILES: tuple[tuple[str, str], ...] = (
    ("include/exactscope.h", "include/exactscope.h"),
    ("include/exactscope_platform.h", "include/exactscope_platform.h"),
    ("include/exactscope_wasm.h", "include/exactscope_wasm.h"),
    ("adapters/wearable/exactscope_wearable_ref.h", "include/exactscope_wearable_ref.h"),
    ("adapters/wearable/exactscope_wearable_ab.h", "include/exactscope_wearable_ab.h"),
    ("adapters/wearable/exactscope_wearable_bench.h", "include/exactscope_wearable_bench.h"),
    ("adapters/wearable/exactscope_wearable_ref.c", "src/exactscope_wearable_ref.c"),
    ("adapters/wearable/exactscope_wearable_ab.c", "src/exactscope_wearable_ab.c"),
    ("adapters/wearable/exactscope_wearable_bench.c", "src/exactscope_wearable_bench.c"),
    ("adapters/wearable/README.md", "docs/WEARABLE_REFERENCE_HOST.md"),
    ("adapters/wearable/AB_UPDATE.md", "docs/AB_UPDATE.md"),
    ("spec/WEARABLE_EDGE_PROFILE_V0_1.md", "docs/WEARABLE_EDGE_PROFILE_V0_1.md"),
    ("spec/WEARABLE_QUALIFICATION_V0_1.md", "docs/WEARABLE_QUALIFICATION_V0_1.md"),
    ("spec/WEARABLE_BENCHMARK_V0_1.md", "docs/WEARABLE_BENCHMARK_V0_1.md"),
    ("spec/examples/wearable-edge-profile.json", "spec/wearable-edge-profile.json"),
    (
        "spec/examples/wearable-qualification-record.json",
        "spec/wearable-qualification-record.json",
    ),
    (
        "spec/schemas/wearable-edge-profile.schema.json",
        "spec/wearable-edge-profile.schema.json",
    ),
    (
        "spec/schemas/wearable-qualification-record.schema.json",
        "spec/wearable-qualification-record.schema.json",
    ),
    ("LICENSE-MIT", "licenses/LICENSE-MIT"),
    ("LICENSE-APACHE", "licenses/LICENSE-APACHE"),
)

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class PackagingError(Exception):
    """Raised when an SDK archive cannot be produced or verified safely."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_project_version() -> str:
    with PROJECT_MANIFEST.open("rb") as handle:
        document = tomllib.load(handle)
    version = document.get("workspace", {}).get("package", {}).get("version")
    if not isinstance(version, str) or not version:
        raise PackagingError("Cargo.toml workspace.package.version is missing")
    return version


def safe_source_file(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise PackagingError(f"source path escapes repository: {relative}") from exc
    if not path.is_file():
        raise PackagingError(f"required SDK source file is missing: {relative}")
    return path


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def file_record(root: Path, path: Path) -> dict[str, Any]:
    relative = path.relative_to(root).as_posix()
    data = path.read_bytes()
    return {
        "path": relative,
        "size_bytes": len(data),
        "sha256": sha256_bytes(data),
    }


def validate_identity(target: str, source_commit: str, toolchain: str) -> None:
    if target not in SUPPORTED_TARGETS:
        raise PackagingError(f"unsupported wearable SDK target: {target}")
    if not COMMIT_RE.fullmatch(source_commit):
        raise PackagingError("source commit must be exactly 40 lowercase hexadecimal characters")
    if not toolchain or len(toolchain) > 128 or any(ord(ch) < 0x20 for ch in toolchain):
        raise PackagingError("toolchain must be a printable nonempty string <=128 bytes")


def stage_bundle(
    stage_root: Path,
    *,
    target: str,
    library: Path,
    source_commit: str,
    toolchain: str,
) -> tuple[Path, dict[str, Any]]:
    validate_identity(target, source_commit, toolchain)
    if not library.is_file():
        raise PackagingError(f"static library does not exist: {library}")
    if library.stat().st_size <= 0:
        raise PackagingError("static library must be nonempty")

    version = read_project_version()
    bundle_name = f"exactscope-wearable-sdk-{version}-{target}"
    bundle_root = stage_root / bundle_name
    bundle_root.mkdir(parents=True, exist_ok=False)

    for source_rel, destination_rel in PUBLIC_FILES:
        source = safe_source_file(source_rel)
        write_bytes(bundle_root / destination_rel, source.read_bytes())

    library_rel = f"lib/{target}/libexactscope_cabi.a"
    write_bytes(bundle_root / library_rel, library.read_bytes())

    payload_files = sorted(path for path in bundle_root.rglob("*") if path.is_file())
    records = [file_record(bundle_root, path) for path in payload_files]
    runtime = next(record for record in records if record["path"] == library_rel)
    profile = next(
        record for record in records if record["path"] == "spec/wearable-edge-profile.json"
    )

    manifest: dict[str, Any] = {
        "format": "exactscope.wearable-sdk-manifest",
        "format_version": "0.1",
        "project_version": version,
        "target": target,
        "source_commit": source_commit,
        "toolchain": toolchain,
        "support": "experimental",
        "qualification": "contract-only",
        "runtime": {
            "artifact_kind": "static-library",
            "path": library_rel,
            "size_bytes": runtime["size_bytes"],
            "sha256": runtime["sha256"],
            "required_host_symbol": "xs_platform_panic_abort",
        },
        "contracts": {
            "core_abi": "1.0",
            "wearable_profile": "wearable-edge-v0.1",
            "wearable_profile_sha256": profile["sha256"],
            "pack_mount_arena_bytes": 0,
            "execution_modes": [
                "native-fused-discovery",
                "native-dynamic-exact",
            ],
        },
        "files": records,
        "claim": (
            "Cross-built SDK artifact only. Real-device latency, energy, thermal, "
            "offline, and power-loss qualification remain required."
        ),
    }
    manifest_bytes = (
        json.dumps(manifest, indent=2, sort_keys=True, separators=(",", ": ")) + "\n"
    ).encode("utf-8")
    write_bytes(bundle_root / "manifest.json", manifest_bytes)

    all_files = sorted(path for path in bundle_root.rglob("*") if path.is_file())
    checksum_lines = []
    for path in all_files:
        relative = path.relative_to(bundle_root).as_posix()
        checksum_lines.append(f"{sha256_bytes(path.read_bytes())}  {relative}\n")
    write_bytes(bundle_root / "SHA256SUMS", "".join(checksum_lines).encode("ascii"))
    return bundle_root, manifest


def normalized_tar_bytes(bundle_root: Path) -> bytes:
    root_parent = bundle_root.parent
    members = [bundle_root] + sorted(bundle_root.rglob("*"), key=lambda path: path.as_posix())
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for path in members:
            relative = path.relative_to(root_parent).as_posix()
            info = tarfile.TarInfo(relative + ("/" if path.is_dir() else ""))
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mtime = 0
            info.mode = 0o755 if path.is_dir() else 0o644
            if path.is_dir():
                info.type = tarfile.DIRTYPE
                info.size = 0
                archive.addfile(info)
            else:
                data = path.read_bytes()
                info.type = tarfile.REGTYPE
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))

    gzip_buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=gzip_buffer, mtime=0, compresslevel=9) as gz:
        gz.write(tar_buffer.getvalue())
    return gzip_buffer.getvalue()


def build_archive(
    *,
    target: str,
    library: Path,
    output_dir: Path,
    source_commit: str,
    toolchain: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="exactscope-sdk-stage-") as temporary:
        stage_root = Path(temporary)
        bundle_root, _ = stage_bundle(
            stage_root,
            target=target,
            library=library,
            source_commit=source_commit,
            toolchain=toolchain,
        )
        archive_data = normalized_tar_bytes(bundle_root)
        archive_path = output_dir / f"{bundle_root.name}.tar.gz"
        archive_path.write_bytes(archive_data)
    verify_archive(archive_path, expected_target=target)
    return archive_path


def normalized_member_name(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise PackagingError(f"unsafe archive member path: {name!r}")
    return path


def parse_checksums(data: bytes) -> dict[str, str]:
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise PackagingError("SHA256SUMS is not ASCII") from exc
    checksums: dict[str, str] = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line:
            continue
        if len(line) < 67 or line[64:66] != "  ":
            raise PackagingError(f"malformed SHA256SUMS line {line_number}")
        digest = line[:64]
        relative = line[66:]
        if not SHA256_RE.fullmatch(digest):
            raise PackagingError(f"invalid digest at SHA256SUMS line {line_number}")
        normalized_member_name(relative)
        if relative in checksums:
            raise PackagingError(f"duplicate checksum path: {relative}")
        checksums[relative] = digest
    return checksums


def verify_archive(path: Path, *, expected_target: str | None = None) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size <= 0:
        raise PackagingError(f"SDK archive is missing or empty: {path}")

    files: dict[str, bytes] = {}
    root_name: str | None = None
    with tarfile.open(path, mode="r:gz") as archive:
        for member in archive.getmembers():
            normalized = normalized_member_name(member.name.rstrip("/"))
            if root_name is None:
                root_name = normalized.parts[0]
            if normalized.parts[0] != root_name:
                raise PackagingError("SDK archive contains more than one top-level root")
            if member.uid != 0 or member.gid != 0 or member.mtime != 0:
                raise PackagingError(f"archive metadata is not deterministic: {member.name}")
            if member.isdir():
                continue
            if not member.isfile():
                raise PackagingError(f"unsupported archive member type: {member.name}")
            extracted = archive.extractfile(member)
            if extracted is None:
                raise PackagingError(f"cannot read archive member: {member.name}")
            relative = PurePosixPath(*normalized.parts[1:]).as_posix()
            if not relative or relative in files:
                raise PackagingError(f"duplicate or empty archive member: {member.name}")
            files[relative] = extracted.read()

    if root_name is None:
        raise PackagingError("SDK archive is empty")
    for required in ("manifest.json", "SHA256SUMS"):
        if required not in files:
            raise PackagingError(f"SDK archive missing {required}")

    try:
        manifest = json.loads(files["manifest.json"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackagingError(f"invalid SDK manifest: {exc}") from exc
    if not isinstance(manifest, dict):
        raise PackagingError("SDK manifest root must be an object")
    if manifest.get("format") != "exactscope.wearable-sdk-manifest":
        raise PackagingError("unexpected SDK manifest format")
    target = manifest.get("target")
    if target not in SUPPORTED_TARGETS:
        raise PackagingError(f"manifest target is unsupported: {target!r}")
    if expected_target is not None and target != expected_target:
        raise PackagingError(f"manifest target {target!r} != expected {expected_target!r}")
    if manifest.get("support") != "experimental" or manifest.get("qualification") != "contract-only":
        raise PackagingError("SDK bundle must not make a real-device support/qualification claim")

    checksum_map = parse_checksums(files["SHA256SUMS"])
    expected_checksum_paths = set(files) - {"SHA256SUMS"}
    if set(checksum_map) != expected_checksum_paths:
        missing = sorted(expected_checksum_paths - set(checksum_map))
        extra = sorted(set(checksum_map) - expected_checksum_paths)
        raise PackagingError(f"SHA256SUMS path mismatch: missing={missing}, extra={extra}")
    for relative, digest in checksum_map.items():
        actual = sha256_bytes(files[relative])
        if actual != digest:
            raise PackagingError(f"checksum mismatch for {relative}: {actual} != {digest}")

    records = manifest.get("files")
    if not isinstance(records, list) or not records:
        raise PackagingError("SDK manifest files list must be nonempty")
    for record in records:
        if not isinstance(record, dict):
            raise PackagingError("SDK manifest file record must be an object")
        relative = record.get("path")
        if not isinstance(relative, str) or relative not in files:
            raise PackagingError(f"SDK manifest references missing file: {relative!r}")
        if record.get("size_bytes") != len(files[relative]):
            raise PackagingError(f"SDK manifest size mismatch for {relative}")
        if record.get("sha256") != sha256_bytes(files[relative]):
            raise PackagingError(f"SDK manifest digest mismatch for {relative}")

    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict):
        raise PackagingError("SDK manifest runtime must be an object")
    runtime_path = runtime.get("path")
    if not isinstance(runtime_path, str) or runtime_path not in files:
        raise PackagingError("SDK runtime artifact is missing")
    if runtime.get("required_host_symbol") != "xs_platform_panic_abort":
        raise PackagingError("SDK manifest lost the mandatory host panic boundary")
    if runtime.get("sha256") != sha256_bytes(files[runtime_path]):
        raise PackagingError("SDK runtime digest mismatch")
    return manifest


def run_self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="exactscope-sdk-selftest-") as temporary:
        root = Path(temporary)
        library = root / "libexactscope_cabi.a"
        library.write_bytes(b"EXACTSCOPE-SYNTHETIC-STATIC-LIB\n")
        commit = "1" * 40
        first = build_archive(
            target="aarch64-linux-android",
            library=library,
            output_dir=root / "first",
            source_commit=commit,
            toolchain="rustc 1.98.0 self-test",
        )
        second = build_archive(
            target="aarch64-linux-android",
            library=library,
            output_dir=root / "second",
            source_commit=commit,
            toolchain="rustc 1.98.0 self-test",
        )
        first_digest = sha256_bytes(first.read_bytes())
        second_digest = sha256_bytes(second.read_bytes())
        if first_digest != second_digest:
            raise PackagingError(
                f"deterministic archive self-test failed: {first_digest} != {second_digest}"
            )
        verify_archive(first, expected_target="aarch64-linux-android")
        print(f"wearable SDK packager self-test: PASS sha256={first_digest}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--target", choices=sorted(SUPPORTED_TARGETS))
    parser.add_argument("--library", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    parser.add_argument("--source-commit")
    parser.add_argument("--toolchain")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.self_test:
            run_self_test()
            return 0
        if args.verify is not None:
            manifest = verify_archive(args.verify, expected_target=args.target)
            print(
                "wearable SDK archive valid: "
                f"target={manifest['target']} support={manifest['support']} "
                f"sha256={sha256_bytes(args.verify.read_bytes())}"
            )
            return 0
        if None in (args.target, args.library, args.source_commit, args.toolchain):
            raise PackagingError(
                "packaging requires --target, --library, --source-commit, and --toolchain"
            )
        archive = build_archive(
            target=args.target,
            library=args.library,
            output_dir=args.output_dir,
            source_commit=args.source_commit,
            toolchain=args.toolchain,
        )
        print(
            "wearable SDK archive built: "
            f"path={archive} bytes={archive.stat().st_size} sha256={sha256_bytes(archive.read_bytes())}"
        )
        return 0
    except PackagingError as exc:
        print(f"wearable SDK packaging failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
