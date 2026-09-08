#!/usr/bin/env python3
"""Clean-room C11 smoke test for an extracted ExactScope grounding runtime package."""
from __future__ import annotations

import argparse
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path

from package_grounding_runtime import verify_archive


def run(archive: Path) -> dict[str, object]:
    verification = verify_archive(archive)
    manifest = verification["manifest"]
    target = manifest["target"]
    if target != "x86_64-unknown-linux-gnu":
        raise RuntimeError(f"clean-room test does not qualify target {target}")

    with tempfile.TemporaryDirectory(prefix="exactscope-grounding-cleanroom-") as temporary:
        root = Path(temporary)
        with tarfile.open(archive, mode="r:gz") as tar:
            members = tar.getmembers()
            tar.extractall(root, filter="data")
        roots = {member.name.split("/", 1)[0] for member in members}
        if len(roots) != 1:
            raise RuntimeError("archive does not contain one clean-room root")
        package = root / next(iter(roots))
        executable = root / "grounding-demo"
        compile_command = [
            "cc",
            "-std=c11",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            "-Iinclude",
            "examples/c/grounding.c",
            f"lib/{target}/libexactscope_cabi.a",
            "-o",
            str(executable),
        ]
        subprocess.run(compile_command, cwd=package, check=True)

        queries = {
            "warranty": ["warranty", "period"],
            "battery": ["battery", "level"],
        }
        expected = {
            "warranty": "24 months",
            "battery": "73 percent",
        }
        outputs: dict[str, str] = {}
        for name, tokens in queries.items():
            result = subprocess.run(
                [str(executable), "grounding/sample-index-v1.xsgi", *tokens],
                cwd=package,
                check=True,
                text=True,
                capture_output=True,
            )
            output = result.stdout.strip()
            if expected[name] not in output:
                raise RuntimeError(f"clean-room {name} query did not return expected evidence")
            outputs[name] = output

        return {
            "status": "PASS",
            "target": target,
            "archive_bytes": verification["archive_bytes"],
            "unpacked_file_bytes": verification["unpacked_file_bytes"],
            "sample_index_bytes": manifest["sample_provider"]["size_bytes"],
            "queries": outputs,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.archive), indent=2, sort_keys=True))
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError, tarfile.TarError) as exc:
        print(f"ExactScope grounding clean-room: FAIL: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
