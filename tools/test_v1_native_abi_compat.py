#!/usr/bin/env python3
"""Compile and run a frozen v1.0 C-ABI client against a release archive.

This is a release-artifact compatibility gate, not a source-tree-only check.
The fixture deliberately names every public v1.0 function and the ABI-sensitive
sizes/offsets that were part of the v1.0.0 Linux x86-64 header contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile


class CompatError(RuntimeError):
    pass


V1_HEADER_SHA256 = "ab4554523c3634deb6ecc86f40cb4f1b3ea72311dfeda4c354612a9d067bd02f"


CLIENT = r'''#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include "exactscope.h"
#include "exactscope_platform.h"

_Static_assert(XS_ABI_MAJOR_V1 == 1u, "v1 ABI major changed");
_Static_assert(XS_ABI_MINOR_V1 == 0u, "v1 ABI minor changed");
_Static_assert(XS_ABI_VERSION_V1 == 0x00010000u, "v1 ABI version changed");
_Static_assert(sizeof(xs_decimal_v1) == 16u, "xs_decimal_v1 size changed");
_Static_assert(sizeof(xs_plan_value_v1) == 32u, "xs_plan_value_v1 size changed");
_Static_assert(sizeof(xs_plan_step_v1) == 80u, "xs_plan_step_v1 size changed");
_Static_assert(sizeof(xs_plan_result_v1) == 48u, "xs_plan_result_v1 size changed");
_Static_assert(sizeof(xs_grounding_projection_result_v1) == 20u, "grounding projection size changed");
#if UINTPTR_MAX == UINT64_MAX
_Static_assert(sizeof(xs_grounding_search_scratch_v1) == 16u, "grounding scratch size changed");
_Static_assert(sizeof(xs_grounding_search_hit_v1) == 24u, "grounding hit size changed");
_Static_assert(offsetof(xs_grounding_search_hit_v1, score) == 8u, "grounding hit score offset changed");
#endif

void XS_CALL xs_platform_panic_abort(void) XS_NOEXCEPT {
    abort();
}

static uint32_t (XS_CALL *p_xs_abi_version)(void) = xs_abi_version;
static xs_status (XS_CALL *p_xs_decimal_parse_ascii)(const uint8_t*, uint32_t, uint8_t, uint16_t, xs_decimal_v1*) = xs_decimal_parse_ascii;
static uint32_t (XS_CALL *p_xs_context_align)(void) = xs_context_align;
static uint32_t (XS_CALL *p_xs_context_size)(const xs_config_v1*) = xs_context_size;
static xs_status (XS_CALL *p_xs_context_init)(void*, uint32_t, const xs_config_v1*, xs_context**) = xs_context_init;
static xs_status (XS_CALL *p_xs_context_reset)(xs_context*) = xs_context_reset;
static uint32_t (XS_CALL *p_xs_grounding_index_align)(void) = xs_grounding_index_align;
static uint32_t (XS_CALL *p_xs_grounding_index_size)(void) = xs_grounding_index_size;
static xs_status (XS_CALL *p_xs_grounding_index_init)(void*, uint32_t, xs_bytes_v1, xs_grounding_index**, uint32_t*) = xs_grounding_index_init;
static xs_status (XS_CALL *p_xs_grounding_index_search)(const xs_grounding_index*, const xs_bytes_v1*, uint16_t, xs_grounding_search_scratch_v1*, uint32_t, xs_grounding_search_hit_v1*, uint16_t, uint16_t*) = xs_grounding_index_search;
static xs_status (XS_CALL *p_xs_grounding_index_project)(const xs_grounding_index*, const xs_grounding_search_hit_v1*, uint16_t, const xs_bytes_v1*, uint16_t, uint32_t, uint8_t, uint8_t*, uint32_t, xs_grounding_projection_result_v1*) = xs_grounding_index_project;
static xs_status (XS_CALL *p_xs_pack_mount)(xs_context*, const uint8_t*, uint32_t, void*, uint32_t, uint16_t*, uint32_t*) = xs_pack_mount;
static xs_status (XS_CALL *p_xs_pack_unmount)(xs_context*, uint16_t) = xs_pack_unmount;
static xs_status (XS_CALL *p_xs_registry_freeze)(xs_context*) = xs_registry_freeze;
static xs_status (XS_CALL *p_xs_lookup)(xs_context*, const uint8_t*, uint32_t, uint16_t*, uint32_t*, uint16_t*) = xs_lookup;
static xs_status (XS_CALL *p_xs_find)(xs_context*, const uint8_t*, uint32_t, xs_match_v1*, uint16_t, uint16_t*) = xs_find;
static xs_status (XS_CALL *p_xs_calc)(xs_context*, const xs_plan_step_v1*, uint16_t, xs_plan_result_v1*) = xs_calc;
static xs_status (XS_CALL *p_xs_eval)(xs_context*, uint16_t, uint32_t, const xs_value_ref_v1*, uint16_t, const xs_eval_options_v1*, void*, uint32_t, xs_result_v1*) = xs_eval;
static xs_status (XS_CALL *p_xs_result_json)(xs_context*, const xs_result_v1*, uint8_t*, uint32_t, uint32_t*) = xs_result_json;
static xs_status (XS_CALL *p_xs_match_json)(const xs_match_v1*, uint16_t, uint8_t*, uint32_t, uint32_t*) = xs_match_json;

int main(void) {
    (void)p_xs_abi_version;
    (void)p_xs_decimal_parse_ascii;
    (void)p_xs_context_align;
    (void)p_xs_context_size;
    (void)p_xs_context_init;
    (void)p_xs_context_reset;
    (void)p_xs_grounding_index_align;
    (void)p_xs_grounding_index_size;
    (void)p_xs_grounding_index_init;
    (void)p_xs_grounding_index_search;
    (void)p_xs_grounding_index_project;
    (void)p_xs_pack_mount;
    (void)p_xs_pack_unmount;
    (void)p_xs_registry_freeze;
    (void)p_xs_lookup;
    (void)p_xs_find;
    (void)p_xs_calc;
    (void)p_xs_eval;
    (void)p_xs_result_json;
    (void)p_xs_match_json;
    return xs_abi_version() == XS_ABI_VERSION_V1 ? 0 : 2;
}
'''


def extract_archive(archive: Path, destination: Path) -> Path:
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        for member in members:
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts or member.issym() or member.islnk():
                raise CompatError(f"unsafe archive member: {member.name}")
        bundle.extractall(destination, filter="data")
    roots = [path for path in destination.iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise CompatError(f"expected exactly one archive root, found {len(roots)}")
    return roots[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--cc", default="cc")
    args = parser.parse_args()
    archive = args.archive.resolve()
    if not archive.is_file():
        raise CompatError(f"release archive not found: {archive}")

    with tempfile.TemporaryDirectory(prefix="exactscope-v1-abi-") as temporary:
        root = extract_archive(archive, Path(temporary) / "extract")
        manifest_path = root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("support_scope", {}).get("native_status") != "stable":
            raise CompatError("release archive does not declare stable native support")
        if manifest.get("support_scope", {}).get("host_integration_status") != "experimental-reference":
            raise CompatError("release archive host-integration stability boundary drift")
        if manifest.get("support_scope", {}).get("qualification_architecture_status") != "source-reference-only":
            raise CompatError("release archive qualification-architecture stability boundary drift")

        include_dir = root / "include"
        header = include_dir / "exactscope.h"
        library = root / "lib/x86_64-unknown-linux-gnu/libexactscope_cabi.a"
        if not header.is_file() or not library.is_file():
            raise CompatError("release archive is missing the stable v1 C ABI payload")
        header_sha256 = hashlib.sha256(header.read_bytes()).hexdigest()
        if header_sha256 != V1_HEADER_SHA256:
            raise CompatError(
                f"release exactscope.h drifted from the frozen v1.0.0 header: {header_sha256}"
            )

        source = Path(temporary) / "v1_abi_client.c"
        binary = Path(temporary) / "v1_abi_client"
        source.write_text(CLIENT, encoding="utf-8", newline="\n")
        compile_result = subprocess.run(
            [
                args.cc,
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-pedantic",
                f"-I{include_dir}",
                str(source),
                str(library),
                "-o",
                str(binary),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if compile_result.returncode != 0:
            raise CompatError(
                "v1 C ABI client failed to compile/link against release archive:\n"
                + compile_result.stdout
                + compile_result.stderr
            )
        run_result = subprocess.run(
            [str(binary)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if run_result.returncode != 0:
            raise CompatError(
                f"v1 C ABI client failed at runtime with exit {run_result.returncode}:\n"
                + run_result.stdout
                + run_result.stderr
            )

    print("ExactScope v1 native C ABI compatibility: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
