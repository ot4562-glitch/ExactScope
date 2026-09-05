#!/usr/bin/env python3
"""Static security-boundary audit for ExactScope source and public exports.

This audit intentionally performs no runtime execution. It verifies that unsafe
Rust remains isolated to the native/Wasm memory boundaries, that public unsafe C
entry points carry explicit Safety contracts, and that source/header/Wasm export
allowlists cannot silently drift apart.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from compile_capability import ROOT, load
from inspect_wasm import ALLOWED_EXTRA_EXPORTS, REQUIRED_EXPORTS

REGISTRY = ROOT / "spec/registries/public-exports.json"
PURE_CRATES = (
    ROOT / "crates/exactscope-kernel/src/lib.rs",
    ROOT / "crates/exactscope-pack/src/lib.rs",
    ROOT / "crates/exactscope-tinyjson/src/lib.rs",
    ROOT / "crates/exactscope-packc/src/lib.rs",
    ROOT / "crates/exactscope-conformance/src/lib.rs",
)
UNSAFE_BOUNDARIES = (
    ROOT / "crates/exactscope-cabi/src/lib.rs",
    ROOT / "crates/exactscope-wasm/src/lib.rs",
)


class SecurityAuditError(RuntimeError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise SecurityAuditError(message)


def public_c_header_symbols(text: str) -> list[str]:
    return re.findall(r"\bXS_API\b[^;]*?\bXS_CALL\s+(xs_[a-z0-9_]+)\s*\(", text, flags=re.DOTALL)


def no_mangle_rust_symbols(text: str) -> list[str]:
    pattern = re.compile(
        r"#\[unsafe\(no_mangle\)\]\s*"
        r"(?:#\[[^\n]+\]\s*)*"
        r"pub\s+(?:unsafe\s+)?extern\s+\"C\"\s+fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        flags=re.MULTILINE,
    )
    return pattern.findall(text)


def unsafe_public_functions_missing_safety(text: str) -> list[str]:
    lines = text.splitlines()
    missing: list[str] = []
    function_re = re.compile(r"pub\s+unsafe\s+extern\s+\"C\"\s+fn\s+([A-Za-z_][A-Za-z0-9_]*)")
    for index, line in enumerate(lines):
        match = function_re.search(line)
        if match is None:
            continue
        # Attributes may sit between the rustdoc block and the function, so scan a
        # bounded preceding window rather than requiring immediate adjacency.
        window = "\n".join(lines[max(0, index - 24):index])
        if "/// # Safety" not in window:
            missing.append(match.group(1))
    return missing


def audit() -> dict[str, object]:
    registry = load(REGISTRY.read_bytes())
    expect(registry.get("format") == "exactscope.public-export-registry", "bad public export registry format")
    expect(registry.get("format_version") == "0.1", "bad public export registry version")

    for path in PURE_CRATES:
        text = path.read_text(encoding="utf-8")
        expect("#![forbid(unsafe_code)]" in text, f"pure crate does not forbid unsafe code: {path.relative_to(ROOT)}")

    for path in UNSAFE_BOUNDARIES:
        text = path.read_text(encoding="utf-8")
        expect(
            "#![deny(unsafe_op_in_unsafe_fn)]" in text,
            f"unsafe boundary does not deny implicit unsafe operations: {path.relative_to(ROOT)}",
        )

    header_text = (ROOT / "include/exactscope.h").read_text(encoding="utf-8")
    header_symbols = public_c_header_symbols(header_text)
    expect(len(header_symbols) == len(set(header_symbols)), "duplicate public C declarations")
    expected_c = registry.get("native_c_api")
    expect(isinstance(expected_c, list) and all(isinstance(item, str) for item in expected_c), "bad native C allowlist")
    expect(header_symbols == expected_c, "public C header/export registry drift")

    cabi_text = (ROOT / "crates/exactscope-cabi/src/lib.rs").read_text(encoding="utf-8")
    rust_symbols = no_mangle_rust_symbols(cabi_text)
    expected_internal = registry.get("native_internal_symbols")
    expect(
        isinstance(expected_internal, list) and all(isinstance(item, str) for item in expected_internal),
        "bad native internal symbol allowlist",
    )
    expect(set(rust_symbols) == set(expected_c) | set(expected_internal), "C ABI no_mangle source/export registry drift")
    missing_safety = unsafe_public_functions_missing_safety(cabi_text)
    expect(not missing_safety, "public unsafe C functions missing # Safety docs: " + ", ".join(missing_safety))

    expected_wasm = registry.get("wasm_required_exports")
    expected_wasm_extra = registry.get("wasm_allowed_toolchain_exports")
    expect(expected_wasm == REQUIRED_EXPORTS, "Wasm required export registry/inspector drift")
    expect(expected_wasm_extra == ALLOWED_EXTRA_EXPORTS, "Wasm toolchain export registry/inspector drift")

    return {
        "pure_crates_forbid_unsafe": len(PURE_CRATES),
        "unsafe_boundary_crates": len(UNSAFE_BOUNDARIES),
        "native_public_symbols": len(expected_c),
        "native_internal_symbols": len(expected_internal),
        "wasm_required_exports": len(expected_wasm),
        "wasm_allowed_toolchain_exports": len(expected_wasm_extra),
        "public_unsafe_functions_with_safety_contracts": len(
            re.findall(r"pub\s+unsafe\s+extern\s+\"C\"\s+fn\s+", cabi_text)
        ),
    }


def main() -> int:
    try:
        result = audit()
    except (OSError, ValueError, json.JSONDecodeError, SecurityAuditError) as exc:
        print(f"SECURITY AUDIT FAILED: {exc}")
        return 2
    print(
        "PASS security surface: "
        f"pure={result['pure_crates_forbid_unsafe']} "
        f"unsafe-boundaries={result['unsafe_boundary_crates']} "
        f"native-api={result['native_public_symbols']} "
        f"unsafe-c-contracts={result['public_unsafe_functions_with_safety_contracts']} "
        f"wasm-required={result['wasm_required_exports']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
