#!/usr/bin/env python3
"""Build and verify deterministic ExactScope prerelease evaluation bundles."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import shutil
import sys
import tarfile
import tempfile
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECT_MANIFEST = ROOT / "Cargo.toml"
HOTSET_FILES = (
    "binding-sha256.txt",
    "catalog.json",
    "prompt-fragment.txt",
    "xs-eval.gbnf",
    "xs-eval.tool.json",
    "xs-find.gbnf",
    "xs-find.tool.json",
)
PUBLIC_FILES: tuple[tuple[str, str], ...] = (
    ("cmake/ExactScopeConfig.cmake", "lib/cmake/ExactScope/ExactScopeConfig.cmake"),
    ("include/exactscope.h", "include/exactscope.h"),
    ("include/exactscope_platform.h", "include/exactscope_platform.h"),
    ("include/exactscope_wasm.h", "include/exactscope_wasm.h"),
    ("examples/evaluation/native_smoke.c", "examples/native_smoke.c"),
    ("tools/test_wasm.mjs", "tools/test_wasm.mjs"),
    ("tools/inspect_wasm.py", "tools/inspect_wasm.py"),
    ("benchmarks/run_benchmark.py", "benchmarks/run_benchmark.py"),
    ("benchmarks/corpus-v0.1.jsonl", "benchmarks/corpus-v0.1.jsonl"),
    ("benchmarks/README.md", "benchmarks/README.md"),
    ("docs/QUICKSTART.md", "docs/QUICKSTART.md"),
    ("docs/EVALUATION_BUNDLE.md", "docs/EVALUATION_BUNDLE.md"),
    ("LICENSE-MIT", "licenses/LICENSE-MIT"),
    ("LICENSE-APACHE", "licenses/LICENSE-APACHE"),
)
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
TARGET_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
HOTSET_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


class PackagingError(Exception):
    """Raised when an evaluation bundle cannot be built or verified safely."""


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def read_project_version() -> str:
    with PROJECT_MANIFEST.open("rb") as handle:
        document = tomllib.load(handle)
    version = document.get("workspace", {}).get("package", {}).get("version")
    if not isinstance(version, str) or not version:
        raise PackagingError("Cargo.toml workspace.package.version is missing")
    return version


def safe_repo_file(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise PackagingError(f"source path escapes repository: {relative}") from exc
    if not path.is_file():
        raise PackagingError(f"required source file is missing: {relative}")
    return path


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def file_record(root: Path, path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "size_bytes": len(data),
        "sha256": digest_bytes(data),
    }


def validate_identity(native_target: str, source_commit: str, toolchain: str) -> None:
    if not TARGET_RE.fullmatch(native_target):
        raise PackagingError("native target must be a compact printable target identifier")
    if not COMMIT_RE.fullmatch(source_commit):
        raise PackagingError("source commit must be exactly 40 lowercase hexadecimal characters")
    if not toolchain or len(toolchain) > 160 or any(ord(ch) < 0x20 for ch in toolchain):
        raise PackagingError("toolchain must be a printable nonempty string <=160 bytes")


def native_library_name(path: Path) -> str:
    if path.suffix == ".lib":
        return "exactscope_cabi.lib"
    if path.suffix == ".a":
        return "libexactscope_cabi.a"
    raise PackagingError("native library must be a .a or .lib static library")


def stage_bundle(
    stage_root: Path,
    *,
    native_target: str,
    native_library: Path,
    core_executable: Path,
    wasm: Path,
    hotset_dir: Path,
    source_commit: str,
    toolchain: str,
) -> tuple[Path, dict[str, Any]]:
    validate_identity(native_target, source_commit, toolchain)
    for label, path in (
        ("native library", native_library),
        ("core executable", core_executable),
        ("WebAssembly artifact", wasm),
    ):
        if not path.is_file() or path.stat().st_size <= 0:
            raise PackagingError(f"{label} does not exist or is empty: {path}")
    if not hotset_dir.is_dir():
        raise PackagingError(f"hot-set directory is missing: {hotset_dir}")

    version = read_project_version()
    bundle_name = f"exactscope-eval-{version}-{native_target}"
    bundle_root = stage_root / bundle_name
    bundle_root.mkdir(parents=True, exist_ok=False)

    for source_rel, destination_rel in PUBLIC_FILES:
        copy_file(safe_repo_file(source_rel), bundle_root / destination_rel)

    native_name = native_library_name(native_library)
    native_rel = f"lib/{native_target}/{native_name}"
    copy_file(native_library, bundle_root / native_rel)
    core_name = "exactscope-core.exe" if core_executable.suffix.lower() == ".exe" else "exactscope-core"
    core_rel = f"bin/{core_name}"
    copy_file(core_executable, bundle_root / core_rel)
    wasm_rel = "wasm/exactscope.wasm"
    copy_file(wasm, bundle_root / wasm_rel)

    catalog_path = hotset_dir / "catalog.json"
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PackagingError(f"cannot parse hot-set catalog: {exc}") from exc
    if not isinstance(catalog, dict):
        raise PackagingError("hot-set catalog root must be an object")
    binding = catalog.get("binding_sha256")
    if not isinstance(binding, str) or not HEX64_RE.fullmatch(binding):
        raise PackagingError("hot-set catalog has no valid binding_sha256")
    hotset_name = catalog.get("name")
    if not isinstance(hotset_name, str) or not HOTSET_NAME_RE.fullmatch(hotset_name):
        raise PackagingError("hot-set catalog has no valid canonical name")

    hotset_destination = bundle_root / "adapters" / "generated" / hotset_name
    for name in HOTSET_FILES:
        source = hotset_dir / name
        if not source.is_file():
            raise PackagingError(f"hot set is missing required generated file: {name}")
        copy_file(source, hotset_destination / name)

    payload_files = sorted(path for path in bundle_root.rglob("*") if path.is_file())
    records = [file_record(bundle_root, path) for path in payload_files]
    by_path = {record["path"]: record for record in records}
    manifest: dict[str, Any] = {
        "format": "exactscope.evaluation-bundle",
        "format_version": "0.1",
        "project_version": version,
        "support": "prerelease-evaluation",
        "source_commit": source_commit,
        "toolchain": toolchain,
        "native_target": native_target,
        "artifacts": {
            "native_static_library": by_path[native_rel],
            "core_executable": by_path[core_rel],
            "wasm": by_path[wasm_rel],
        },
        "hotset": {
            "name": hotset_name,
            "binding_sha256": binding,
            "catalog_path": f"adapters/generated/{hotset_name}/catalog.json",
        },
        "integration": {
            "cmake_target": "ExactScope::exactscope",
            "native_smoke": "examples/native_smoke.c",
            "wasm_smoke": "tools/test_wasm.mjs",
            "benchmark_runner": "benchmarks/run_benchmark.py",
            "rust_toolchain_required_to_evaluate": False,
        },
        "files": records,
        "claim": (
            "Prerelease evaluation artifact. Passing bundled smoke/conformance checks does not "
            "constitute real-device qualification or a measured model-accuracy improvement."
        ),
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    (bundle_root / "manifest.json").write_bytes(manifest_bytes)

    checksum_files = sorted(path for path in bundle_root.rglob("*") if path.is_file())
    lines = [
        f"{digest_file(path)}  {path.relative_to(bundle_root).as_posix()}\n"
        for path in checksum_files
    ]
    (bundle_root / "SHA256SUMS").write_text("".join(lines), encoding="ascii", newline="\n")
    return bundle_root, manifest


def normalized_archive_bytes(bundle_root: Path) -> bytes:
    parent = bundle_root.parent
    members = [bundle_root] + sorted(bundle_root.rglob("*"), key=lambda path: path.as_posix())
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for path in members:
            relative = path.relative_to(parent).as_posix()
            info = tarfile.TarInfo(relative + ("/" if path.is_dir() else ""))
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mtime = 0
            info.mode = 0o755 if path.is_dir() or path.name in {"exactscope-core", "exactscope-core.exe"} else 0o644
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
    with gzip.GzipFile(filename="", mode="wb", fileobj=gzip_buffer, mtime=0, compresslevel=9) as stream:
        stream.write(tar_buffer.getvalue())
    return gzip_buffer.getvalue()


def build_archive(**kwargs: Any) -> Path:
    output_dir = Path(kwargs.pop("output_dir"))
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="exactscope-eval-stage-") as temporary:
        bundle_root, _manifest = stage_bundle(Path(temporary), **kwargs)
        archive = output_dir / f"{bundle_root.name}.tar.gz"
        archive.write_bytes(normalized_archive_bytes(bundle_root))
    verify_archive(archive)
    return archive


def safe_member_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise PackagingError(f"unsafe archive member path: {name}")
    return path


def verify_bundle_root(bundle_root: Path) -> dict[str, Any]:
    manifest_path = bundle_root / "manifest.json"
    checksum_path = bundle_root / "SHA256SUMS"
    if not manifest_path.is_file() or not checksum_path.is_file():
        raise PackagingError("bundle is missing manifest.json or SHA256SUMS")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PackagingError(f"invalid manifest JSON: {exc}") from exc
    if manifest.get("format") != "exactscope.evaluation-bundle" or manifest.get("format_version") != "0.1":
        raise PackagingError("unsupported evaluation bundle manifest")

    expected: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="ascii").splitlines():
        if "  " not in line:
            raise PackagingError("malformed SHA256SUMS line")
        digest, relative = line.split("  ", 1)
        safe_member_path(relative)
        if not HEX64_RE.fullmatch(digest) or relative in expected:
            raise PackagingError("invalid or duplicate SHA256SUMS entry")
        expected[relative] = digest
    actual_files = {
        path.relative_to(bundle_root).as_posix(): path
        for path in bundle_root.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS"
    }
    if set(expected) != set(actual_files):
        raise PackagingError("SHA256SUMS file set does not match bundle payload")
    for relative, path in actual_files.items():
        if digest_file(path) != expected[relative]:
            raise PackagingError(f"checksum mismatch: {relative}")

    for record in manifest.get("files", []):
        if not isinstance(record, dict):
            raise PackagingError("manifest files entry must be an object")
        relative = record.get("path")
        if not isinstance(relative, str) or relative not in actual_files:
            raise PackagingError("manifest references missing payload file")
        if record.get("sha256") != digest_file(actual_files[relative]):
            raise PackagingError(f"manifest digest mismatch: {relative}")
    return manifest


def verify_archive(archive: Path) -> dict[str, Any]:
    if not archive.is_file() or archive.stat().st_size <= 0:
        raise PackagingError(f"archive does not exist or is empty: {archive}")
    with tempfile.TemporaryDirectory(prefix="exactscope-eval-verify-") as temporary:
        root = Path(temporary)
        with tarfile.open(archive, mode="r:gz") as source:
            members = source.getmembers()
            if not members:
                raise PackagingError("archive is empty")
            top_levels = {safe_member_path(member.name).parts[0] for member in members}
            if len(top_levels) != 1:
                raise PackagingError("archive must contain exactly one top-level directory")
            for member in members:
                path = safe_member_path(member.name)
                destination = root.joinpath(*path.parts).resolve()
                try:
                    destination.relative_to(root.resolve())
                except ValueError as exc:
                    raise PackagingError("archive member escapes extraction root") from exc
                if member.issym() or member.islnk() or member.isdev():
                    raise PackagingError("links/devices are forbidden in evaluation bundles")
            source.extractall(root, filter="data")
        bundle_root = root / next(iter(top_levels))
        return verify_bundle_root(bundle_root)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--native-target", required=True)
    build.add_argument("--native-library", type=Path, required=True)
    build.add_argument("--core-executable", type=Path, required=True)
    build.add_argument("--wasm", type=Path, required=True)
    build.add_argument(
        "--hotset-dir",
        type=Path,
        default=ROOT / "adapters" / "generated" / "quant-core-16",
    )
    build.add_argument("--source-commit", required=True)
    build.add_argument("--toolchain", required=True)
    build.add_argument("--output-dir", type=Path, required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("archive", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "verify":
        manifest = verify_archive(args.archive)
        print(
            f"PASS evaluation-bundle target={manifest['native_target']} "
            f"hotset={manifest['hotset']['name']}"
        )
        return 0
    archive = build_archive(
        native_target=args.native_target,
        native_library=args.native_library,
        core_executable=args.core_executable,
        wasm=args.wasm,
        hotset_dir=args.hotset_dir,
        source_commit=args.source_commit,
        toolchain=args.toolchain,
        output_dir=args.output_dir,
    )
    print(archive)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PackagingError, OSError, ValueError) as exc:
        print(f"ExactScope evaluation bundle: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
