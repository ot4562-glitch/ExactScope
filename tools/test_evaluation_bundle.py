#!/usr/bin/env python3
"""Clean-room smoke test for an ExactScope prerelease evaluation archive."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

import package_evaluation_bundle as bundle


class SmokeError(RuntimeError):
    """Raised when a release-shaped evaluation bundle cannot run standalone."""


def run(command: list[str], *, cwd: Path, input_bytes: bytes | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        stdout = completed.stdout.decode("utf-8", errors="replace")
        stderr = completed.stderr.decode("utf-8", errors="replace")
        raise SmokeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\nstdout:\n{stdout}\nstderr:\n{stderr}"
        )
    return completed.stdout.decode("utf-8", errors="replace").strip()


def extract_archive(archive: Path, destination: Path) -> Path:
    with tarfile.open(archive, mode="r:gz") as source:
        members = source.getmembers()
        top_levels = {bundle.safe_member_path(member.name).parts[0] for member in members}
        if len(top_levels) != 1:
            raise SmokeError("archive must contain exactly one top-level directory")
        source.extractall(destination, filter="data")
    return destination / next(iter(top_levels))


def find_native_library(root: Path, manifest: dict) -> Path:
    record = manifest.get("artifacts", {}).get("native_static_library", {})
    relative = record.get("path") if isinstance(record, dict) else None
    if not isinstance(relative, str):
        raise SmokeError("manifest lacks native static library path")
    path = root / relative
    if not path.is_file():
        raise SmokeError("native static library is missing after extraction")
    return path


def find_core(root: Path, manifest: dict) -> Path:
    record = manifest.get("artifacts", {}).get("core_executable", {})
    relative = record.get("path") if isinstance(record, dict) else None
    if not isinstance(relative, str):
        raise SmokeError("manifest lacks core executable path")
    path = root / relative
    if not path.is_file():
        raise SmokeError("core executable is missing after extraction")
    return path


def test_core(root: Path, core: Path) -> None:
    request = b'{"op":"econ.ped.mid","a":["10000","12000","100","80"]}'
    output = run([str(core), "eval"], cwd=root, input_bytes=request)
    parsed = json.loads(output)
    if parsed.get("s") != 0 or parsed.get("v") != "-1.222222" or parsed.get("c") != "elastic":
        raise SmokeError(f"unexpected packaged core result: {parsed}")

    benchmark = run(
        [
            sys.executable,
            "benchmarks/run_benchmark.py",
            "--self-test",
            "--core",
            str(core),
        ],
        cwd=root,
    )
    if "PASS" not in benchmark:
        raise SmokeError("packaged benchmark self-test did not report PASS")


def test_wasm(root: Path) -> None:
    wasm = root / "wasm" / "exactscope.wasm"
    run([sys.executable, "tools/inspect_wasm.py", str(wasm)], cwd=root)
    node = shutil.which("node")
    if node is None:
        raise SmokeError("node is required for clean-room Wasm execution")
    run([node, "tools/test_wasm.mjs", str(wasm)], cwd=root)


def test_native(root: Path, native_library: Path) -> bool:
    if native_library.suffix != ".a":
        return False
    cc = shutil.which("cc")
    if cc is None:
        raise SmokeError("cc is required to execute the native clean-room smoke test")
    executable = root / "native-smoke"
    run(
        [
            cc,
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            "-Iinclude",
            "examples/native_smoke.c",
            str(native_library),
            "-o",
            str(executable),
        ],
        cwd=root,
    )
    output = run([str(executable)], cwd=root)
    if "PASS native-smoke" not in output:
        raise SmokeError("packaged native smoke did not report PASS")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()

    manifest = bundle.verify_archive(args.archive)
    with tempfile.TemporaryDirectory(prefix="exactscope-eval-cleanroom-") as temporary:
        root = extract_archive(args.archive, Path(temporary))
        bundle.verify_bundle_root(root)
        core = find_core(root, manifest)
        native_library = find_native_library(root, manifest)
        test_core(root, core)
        test_wasm(root)
        native_executed = test_native(root, native_library)

    print(
        "PASS evaluation-cleanroom "
        f"target={manifest['native_target']} "
        f"native={'executed' if native_executed else 'not-host-linkable'} "
        f"hotset={manifest['hotset']['name']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SmokeError, bundle.PackagingError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ExactScope evaluation clean-room: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
