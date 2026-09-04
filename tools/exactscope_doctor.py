#!/usr/bin/env python3
"""Validate an ExactScope OEM SDK before target integration.

This is a developer-workstation tool. It is not part of the target runtime and
never changes the SDK it inspects.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

# The doctor may be executed from inside an extracted immutable SDK. Importing
# its sibling verifier must not create __pycache__ and mutate the bundle being
# verified.
sys.dont_write_bytecode = True

import package_wearable_sdk as sdk  # noqa: E402

ABI_MAJOR_RE = re.compile(r"^#define\s+XS_ABI_MAJOR_V1\s+(\d+)u\s*$", re.MULTILINE)
ABI_MINOR_RE = re.compile(r"^#define\s+XS_ABI_MINOR_V1\s+(\d+)u\s*$", re.MULTILINE)
AR_MAGIC = b"!<arch>\n"
ELF_MAGIC = b"\x7fELF"
EXPECTED_ELF_MACHINE = {
    "aarch64-linux-android": 183,  # EM_AARCH64
    "aarch64-unknown-linux-musl": 183,
}


class DoctorError(Exception):
    """Raised when an SDK is not safe to proceed to target testing."""


def _archive_files(path: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    root_name: str | None = None
    with tarfile.open(path, mode="r:gz") as archive:
        for member in archive.getmembers():
            normalized = sdk.normalized_member_name(member.name.rstrip("/"))
            if root_name is None:
                root_name = normalized.parts[0]
            if member.isdir():
                continue
            if normalized.parts[0] != root_name or not member.isfile():
                raise DoctorError("SDK archive structure changed after verification")
            extracted = archive.extractfile(member)
            if extracted is None:
                raise DoctorError(f"cannot read SDK member: {member.name}")
            relative = PurePosixPath(*normalized.parts[1:]).as_posix()
            files[relative] = extracted.read()
    return files


def _directory_manifest(path: Path, expected_target: str | None) -> tuple[dict[str, Any], dict[str, bytes]]:
    if not path.is_dir():
        raise DoctorError(f"SDK directory does not exist: {path}")
    with tempfile.TemporaryDirectory(prefix="exactscope-doctor-dir-") as temporary:
        archive = Path(temporary) / "bundle.tar.gz"
        archive.write_bytes(sdk.normalized_tar_bytes(path))
        manifest = sdk.verify_archive(archive, expected_target=expected_target)
    files = {
        child.relative_to(path).as_posix(): child.read_bytes()
        for child in path.rglob("*")
        if child.is_file()
    }
    return manifest, files


def _load_verified_sdk(path: Path, expected_target: str | None) -> tuple[dict[str, Any], dict[str, bytes]]:
    if path.is_dir():
        return _directory_manifest(path, expected_target)
    try:
        manifest = sdk.verify_archive(path, expected_target=expected_target)
    except sdk.PackagingError as exc:
        raise DoctorError(str(exc)) from exc
    return manifest, _archive_files(path)


def _abi_from_header(header: bytes) -> str:
    try:
        text = header.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DoctorError("include/exactscope.h is not UTF-8") from exc
    major = ABI_MAJOR_RE.search(text)
    minor = ABI_MINOR_RE.search(text)
    if major is None or minor is None:
        raise DoctorError("public header is missing ABI major/minor constants")
    return f"{major.group(1)}.{minor.group(1)}"


def _archive_elf_machine(archive: bytes) -> int:
    if not archive.startswith(AR_MAGIC):
        raise DoctorError("static library does not have an ar-compatible archive header")
    offset = len(AR_MAGIC)
    while offset + 60 <= len(archive):
        header = archive[offset : offset + 60]
        if header[58:60] != b"`\n":
            raise DoctorError("static library contains a malformed ar member header")
        try:
            size = int(header[48:58].decode("ascii").strip())
        except (UnicodeDecodeError, ValueError) as exc:
            raise DoctorError("static library contains an invalid ar member size") from exc
        data_start = offset + 60
        data_end = data_start + size
        if data_end > len(archive):
            raise DoctorError("static library ar member exceeds archive bounds")
        data = archive[data_start:data_end]
        if data.startswith(ELF_MAGIC):
            if len(data) < 20:
                raise DoctorError("ELF object in static library is truncated")
            endian = data[5]
            if endian == 1:
                return int.from_bytes(data[18:20], "little")
            if endian == 2:
                return int.from_bytes(data[18:20], "big")
            raise DoctorError("ELF object has an unsupported byte order")
        offset = data_end + (size & 1)
    raise DoctorError("static library does not contain a readable ELF object")


def _synthetic_ar(machine: int) -> bytes:
    elf = bytearray(20)
    elf[:4] = ELF_MAGIC
    elf[4] = 2  # ELFCLASS64
    elf[5] = 1  # little-endian
    elf[18:20] = machine.to_bytes(2, "little")
    name = b"doctor.o/".ljust(16, b" ")
    header = (
        name
        + b"0".ljust(12, b" ")
        + b"0".ljust(6, b" ")
        + b"0".ljust(6, b" ")
        + b"100644".ljust(8, b" ")
        + str(len(elf)).encode("ascii").ljust(10, b" ")
        + b"`\n"
    )
    return AR_MAGIC + header + bytes(elf)


def inspect_sdk(path: Path, expected_target: str | None = None) -> dict[str, Any]:
    manifest, files = _load_verified_sdk(path, expected_target)
    target = manifest.get("target")
    contracts = manifest.get("contracts")
    runtime = manifest.get("runtime")
    if not isinstance(contracts, dict) or not isinstance(runtime, dict):
        raise DoctorError("manifest contracts/runtime sections are invalid")

    header = files.get("include/exactscope.h")
    cmake_config = files.get("lib/cmake/ExactScope/ExactScopeConfig.cmake")
    runtime_path = runtime.get("path")
    if header is None or cmake_config is None or not isinstance(runtime_path, str):
        raise DoctorError("SDK is missing required integration files")
    runtime_bytes = files.get(runtime_path)
    if runtime_bytes is None:
        raise DoctorError("manifest runtime path is not present in SDK")

    header_abi = _abi_from_header(header)
    manifest_abi = contracts.get("core_abi")
    if header_abi != manifest_abi:
        raise DoctorError(f"header ABI {header_abi} != manifest ABI {manifest_abi!r}")
    if runtime.get("required_host_symbol") != "xs_platform_panic_abort":
        raise DoctorError("static profile lost required xs_platform_panic_abort boundary")
    expected_machine = EXPECTED_ELF_MACHINE.get(str(target))
    if runtime_path.endswith((".a", ".lib")):
        actual_machine = _archive_elf_machine(runtime_bytes)
        if expected_machine is not None and actual_machine != expected_machine:
            raise DoctorError(
                f"runtime architecture mismatch: ELF e_machine={actual_machine}, "
                f"expected {expected_machine} for {target}"
            )
    else:
        actual_machine = None

    try:
        cmake_text = cmake_config.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DoctorError("ExactScopeConfig.cmake is not UTF-8") from exc
    if "ExactScope::exactscope" not in cmake_text:
        raise DoctorError("CMake package does not expose ExactScope::exactscope")

    support = manifest.get("support")
    qualification = manifest.get("qualification")
    if support == "experimental":
        readiness = "READY_FOR_TARGET_TEST"
    elif qualification in {"qualified", "measured"}:
        readiness = "READY"
    else:
        readiness = "READY_FOR_CONFORMANCE"

    return {
        "status": readiness,
        "target": target,
        "support": support,
        "qualification": qualification,
        "abi": header_abi,
        "source_commit": manifest.get("source_commit"),
        "runtime": {
            "path": runtime_path,
            "size_bytes": runtime.get("size_bytes"),
            "sha256": runtime.get("sha256"),
            "required_host_symbol": runtime.get("required_host_symbol"),
            "elf_machine": actual_machine,
        },
        "checks": [
            "manifest-and-checksums",
            "public-header-abi",
            "runtime-archive-format-and-architecture",
            "required-host-panic-boundary",
            "relocatable-cmake-target",
        ],
        "next": (
            "Run the target self-test/conformance and collect real-device footprint, "
            "latency, energy, offline, and update/rollback evidence before promoting support."
        ),
    }


def run_self_test() -> None:
    target = "aarch64-unknown-linux-musl"
    with tempfile.TemporaryDirectory(prefix="exactscope-doctor-selftest-") as temporary:
        root = Path(temporary)
        library = root / "libexactscope_cabi.a"
        library.write_bytes(_synthetic_ar(EXPECTED_ELF_MACHINE[target]))

        stage_root = root / "stage"
        stage_root.mkdir()
        bundle_root, _ = sdk.stage_bundle(
            stage_root,
            target=target,
            library=library,
            source_commit="2" * 40,
            toolchain="rustc 1.98.0 doctor-self-test",
        )
        directory_result = inspect_sdk(bundle_root, target)
        if directory_result["status"] != "READY_FOR_TARGET_TEST":
            raise DoctorError(f"unexpected extracted-SDK result: {directory_result}")

        bundled_doctor = bundle_root / "tools" / "exactscope_doctor.py"
        completed = subprocess.run(
            [
                sys.executable,
                str(bundled_doctor),
                str(bundle_root),
                "--expect-target",
                target,
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise DoctorError(
                "bundled doctor failed: "
                f"stdout={completed.stdout!r} stderr={completed.stderr!r}"
            )
        try:
            bundled_result = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise DoctorError("bundled doctor did not emit valid JSON") from exc
        if bundled_result.get("status") != "READY_FOR_TARGET_TEST":
            raise DoctorError(f"unexpected bundled-doctor result: {bundled_result}")
        if any(path.name == "__pycache__" for path in bundle_root.rglob("*")):
            raise DoctorError("bundled doctor mutated the SDK by creating __pycache__")

        output = root / "dist"
        archive = sdk.build_archive(
            target=target,
            library=library,
            output_dir=output,
            source_commit="2" * 40,
            toolchain="rustc 1.98.0 doctor-self-test",
        )
        archive_result = inspect_sdk(archive, target)
        if archive_result["status"] != "READY_FOR_TARGET_TEST" or archive_result["abi"] != "1.0":
            raise DoctorError(f"unexpected archive doctor result: {archive_result}")
    print("exactscope doctor self-test: PASS")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sdk", nargs="?", type=Path, help="SDK .tar.gz archive or extracted root")
    parser.add_argument("--expect-target", choices=sorted(sdk.SUPPORTED_TARGETS))
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.self_test:
            run_self_test()
            return 0
        if args.sdk is None:
            raise DoctorError("SDK archive/directory is required unless --self-test is used")
        result = inspect_sdk(args.sdk, args.expect_target)
    except (DoctorError, sdk.PackagingError) as exc:
        if args.json_output:
            print(json.dumps({"status": "BLOCKED", "error": str(exc)}, sort_keys=True))
        else:
            print(f"BLOCKED: {exc}")
        return 2

    if args.json_output:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            f"{result['status']}: target={result['target']} abi={result['abi']} "
            f"support={result['support']} qualification={result['qualification']}"
        )
        print(f"runtime={result['runtime']['path']} sha256={result['runtime']['sha256']}")
        print(result["next"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
