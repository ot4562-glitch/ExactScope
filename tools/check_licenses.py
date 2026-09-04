#!/usr/bin/env python3
"""Fail when Cargo dependencies or public header SPDX markers lack review."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTERNAL = {
    "exactscope-cabi", "exactscope-conformance", "exactscope-kernel",
    "exactscope-pack", "exactscope-packc", "exactscope-tinyjson", "exactscope-wasm",
}
REVIEWED_EXTERNAL = {
    "itoa", "memchr", "proc-macro2", "quote", "serde", "serde_core",
    "serde_derive", "serde_json", "syn", "unicode-ident", "zmij",
}


def main() -> int:
    with (ROOT / "Cargo.lock").open("rb") as handle:
        packages = tomllib.load(handle)["package"]
    external = {package["name"] for package in packages} - INTERNAL
    if external != REVIEWED_EXTERNAL:
        missing = sorted(external - REVIEWED_EXTERNAL)
        stale = sorted(REVIEWED_EXTERNAL - external)
        raise SystemExit(f"dependency license review required: new={missing} stale={stale}")
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    absent = sorted(name for name in external if not re.search(rf"`{re.escape(name)}`", notices))
    if absent:
        raise SystemExit(f"THIRD_PARTY_NOTICES.md is missing dependencies: {absent}")
    marker = "SPDX-License-Identifier: MIT OR Apache-2.0"
    for relative in ("include/exactscope.h", "include/exactscope_platform.h", "include/exactscope_wasm.h"):
        if marker not in (ROOT / relative).read_text(encoding="utf-8"):
            raise SystemExit(f"missing or inconsistent SPDX marker: {relative}")
    print(f"PASS license-inventory external_crates={len(external)} public_headers=3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
