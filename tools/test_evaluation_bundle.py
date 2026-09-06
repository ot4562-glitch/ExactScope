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


def test_capabilities(root: Path, manifest: dict, archive: Path) -> None:
    integration = manifest.get("integration") if isinstance(manifest, dict) else None
    if not isinstance(integration, dict):
        raise SmokeError("manifest lacks integration metadata")
    host_relative = integration.get("capability_host")
    semantic_relative = integration.get("semantic_capability")
    combined_relative = integration.get("combined_capability")
    if not all(isinstance(value, str) for value in (host_relative, semantic_relative, combined_relative)):
        raise SmokeError("manifest lacks capability host/capability paths")
    host = root / host_relative
    semantic = root / semantic_relative
    combined = root / combined_relative
    if not host.is_file() or not semantic.is_dir() or not combined.is_dir():
        raise SmokeError("packaged capability integration assets are missing")
    node = shutil.which("node")
    if node is None:
        raise SmokeError("node is required for capability-host clean-room execution")

    semantic_output = run(
        [
            node,
            str(host),
            str(semantic),
            '{"op":"stats.mean","a":[["1","2","3"]]}',
        ],
        cwd=root,
    )
    semantic_result = json.loads(semantic_output)
    if semantic_result.get("surface") != "xs_eval" or semantic_result.get("status") != 0:
        raise SmokeError(f"semantic capability-host result is invalid: {semantic_result}")

    combined_output = run(
        [
            node,
            str(host),
            str(combined),
            '{"p":[{"o":"mul","a":["12","7"]},{"o":"sub","a":["#0","4"]},{"o":"div","a":["#1","5"]}]}',
        ],
        cwd=root,
    )
    combined_result = json.loads(combined_output)
    if combined_result.get("surface") != "xs_calc" or combined_result.get("status") != 0:
        raise SmokeError(f"combined capability-host result is invalid: {combined_result}")

    qualification_relative = integration.get("qualification_runner")
    if not isinstance(qualification_relative, str):
        raise SmokeError("manifest lacks qualification runner path")
    qualification = root / qualification_relative
    if not qualification.is_file():
        raise SmokeError("packaged qualification runner is missing")
    help_output = run([sys.executable, str(qualification), "--help"], cwd=root)
    if "preregister" not in help_output or "run" not in help_output:
        raise SmokeError("packaged qualification runner does not expose preregister/run")

    model_bytes = b"exactscope-qualification-preregistration-smoke\n"
    model_path = root / "qualification-smoke-model.gguf"
    model_path.write_bytes(model_bytes)
    inventory_path = root / "qualification-smoke-model-inventory.json"
    inventory_path.write_text(
        json.dumps(
            {
                "format": "exactscope.model-download-inventory",
                "format_version": "0.1",
                "records": [
                    {
                        "id": "qualification-smoke-model",
                        "repository": "local/qualification-smoke",
                        "requested_file": model_path.name,
                        "runtime": "qualification-smoke",
                        "quantization": None,
                        "status": "ready",
                        "resolved_revision": "qualification-smoke",
                        "path": str(model_path.resolve()),
                        "bytes": len(model_bytes),
                        "sha256": bundle.digest_bytes(model_bytes),
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    preregistration = root / "qualification-smoke-preregistration.json"
    preregister_output = run(
        [
            sys.executable,
            str(qualification),
            "preregister",
            "--release-tag",
            "qualification-smoke",
            "--release-commit",
            manifest["source_commit"],
            "--evaluation-archive",
            str(archive.resolve()),
            "--evaluation-archive-sha256",
            bundle.digest_file(archive.resolve()),
            "--model-inventory",
            str(inventory_path),
            "--model-id",
            "qualification-smoke-model",
            "--runtime-executable",
            sys.executable,
            "--runtime-launch-command",
            f"{sys.executable} --version",
            "--base-url",
            "http://127.0.0.1:65535/v1",
            "--server-model-name",
            "qualification-smoke-model",
            "--context-size",
            "1024",
            "--seed",
            "42",
            "--max-tokens",
            "64",
            "--timeout",
            "1",
            "--corpus",
            str(root / "benchmarks/corpus-v0.1.jsonl"),
            "--core",
            str(find_core(root, manifest)),
            "--semantic-capability",
            str(semantic),
            "--combined-capability",
            str(combined),
            "--output",
            str(preregistration),
        ],
        cwd=root,
    )
    if "PASS preregistration" not in preregister_output or not preregistration.is_file():
        raise SmokeError("packaged qualification preregistration smoke did not report PASS")


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
        test_capabilities(root, manifest, args.archive)
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
