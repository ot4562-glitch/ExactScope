#!/usr/bin/env python3
"""Configure-test the relocatable ExactScope SDK CMake package."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import package_wearable_sdk as sdk


def main() -> int:
    cmake = shutil.which("cmake")
    if cmake is None:
        raise SystemExit("cmake executable is required for the SDK configure smoke test")

    with tempfile.TemporaryDirectory(prefix="exactscope-cmake-sdk-") as temporary:
        root = Path(temporary)
        library = root / "libexactscope_cabi.a"
        library.write_bytes(b"EXACTSCOPE-SYNTHETIC-STATIC-LIB\n")
        stage_root = root / "stage"
        stage_root.mkdir()
        bundle_root, _ = sdk.stage_bundle(
            stage_root,
            target="aarch64-unknown-linux-musl",
            library=library,
            source_commit="1" * 40,
            toolchain="rustc 1.98.0 cmake-smoke",
        )

        source_dir = root / "consumer"
        build_dir = root / "build"
        source_dir.mkdir()
        (source_dir / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.15)\n"
            "project(exactscope_sdk_consumer LANGUAGES C)\n"
            "find_package(ExactScope CONFIG REQUIRED)\n"
            "if(NOT TARGET ExactScope::exactscope)\n"
            "  message(FATAL_ERROR \"ExactScope imported target is missing\")\n"
            "endif()\n"
            "get_target_property(_exactscope_location ExactScope::exactscope IMPORTED_LOCATION)\n"
            "if(NOT EXISTS \"${_exactscope_location}\")\n"
            "  message(FATAL_ERROR \"ExactScope imported archive is missing: ${_exactscope_location}\")\n"
            "endif()\n"
            "get_target_property(_exactscope_includes ExactScope::exactscope INTERFACE_INCLUDE_DIRECTORIES)\n"
            "if(NOT EXISTS \"${_exactscope_includes}/exactscope.h\")\n"
            "  message(FATAL_ERROR \"ExactScope public header is missing\")\n"
            "endif()\n"
            "add_library(exactscope_consumer INTERFACE)\n"
            "target_link_libraries(exactscope_consumer INTERFACE ExactScope::exactscope)\n",
            encoding="utf-8",
        )

        config_dir = bundle_root / "lib" / "cmake" / "ExactScope"
        subprocess.run(
            [
                cmake,
                "-S",
                str(source_dir),
                "-B",
                str(build_dir),
                f"-DExactScope_DIR={config_dir}",
            ],
            check=True,
        )

    print("PASS cmake-sdk imported-target=ExactScope::exactscope")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
