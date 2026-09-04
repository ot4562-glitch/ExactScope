#!/usr/bin/env python3
"""Inspect the fused ExactScope WebAssembly release artifact without extra tools."""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path

MAGIC = b"\x00asm"
VERSION = b"\x01\x00\x00\x00"
MAX_FUSED_BYTES = 256 * 1024
REQUIRED_EXPORTS = {
    "memory": 2,
    "xs_abi_version": 0,
    "xs_wasm_reserved_end": 0,
    "xs_wasm_memory_alignment": 0,
    "xs_wasm_eval_statistics": 0,
    "xs_wire_request": 0,
}
ALLOWED_EXTRA_EXPORTS = {
    "__heap_base": 3,
    "__data_end": 3,
}


class WasmError(RuntimeError):
    """Raised when the artifact violates the ExactScope Wasm profile."""


@dataclass(frozen=True)
class Section:
    section_id: int
    payload: memoryview


class Reader:
    def __init__(self, data: bytes | memoryview) -> None:
        self.data = memoryview(data)
        self.offset = 0

    def remaining(self) -> int:
        return len(self.data) - self.offset

    def byte(self) -> int:
        if self.offset >= len(self.data):
            raise WasmError("unexpected end of WebAssembly data")
        value = self.data[self.offset]
        self.offset += 1
        return int(value)

    def bytes(self, length: int) -> memoryview:
        end = self.offset + length
        if length < 0 or end > len(self.data):
            raise WasmError("WebAssembly length exceeds containing section")
        value = self.data[self.offset:end]
        self.offset = end
        return value

    def uleb(self, max_bits: int = 32) -> int:
        value = 0
        shift = 0
        max_bytes = (max_bits + 6) // 7
        for _ in range(max_bytes):
            byte = self.byte()
            value |= (byte & 0x7F) << shift
            if byte & 0x80 == 0:
                if value >= 1 << max_bits:
                    raise WasmError(f"ULEB value exceeds u{max_bits}")
                return value
            shift += 7
        raise WasmError(f"unterminated or oversized u{max_bits} LEB128")

    def name(self) -> str:
        length = self.uleb()
        raw = bytes(self.bytes(length))
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise WasmError("invalid UTF-8 export/import name") from exc


def parse_sections(module: bytes) -> list[Section]:
    if len(module) < 8 or module[:4] != MAGIC or module[4:8] != VERSION:
        raise WasmError("not a WebAssembly 1.0 module")

    reader = Reader(module[8:])
    sections: list[Section] = []
    previous_noncustom = 0
    while reader.remaining() != 0:
        section_id = reader.byte()
        size = reader.uleb()
        payload = reader.bytes(size)
        if section_id != 0:
            if section_id < previous_noncustom:
                raise WasmError("non-custom sections are not in canonical order")
            previous_noncustom = section_id
        sections.append(Section(section_id, payload))
    return sections


def parse_limits(reader: Reader) -> tuple[int, int | None, int]:
    flags = reader.uleb()
    if flags not in (0, 1):
        raise WasmError(f"forbidden memory/table limits flags: {flags:#x}")
    minimum = reader.uleb()
    maximum = reader.uleb() if flags & 1 else None
    if maximum is not None and maximum < minimum:
        raise WasmError("maximum memory/table limit is below minimum")
    return minimum, maximum, flags


def skip_import_descriptor(reader: Reader, kind: int) -> None:
    if kind == 0:  # function
        reader.uleb()
    elif kind == 1:  # table
        element_type = reader.byte()
        if element_type != 0x70:
            raise WasmError(f"non-MVP table element type: {element_type:#x}")
        parse_limits(reader)
    elif kind == 2:  # memory
        parse_limits(reader)
    elif kind == 3:  # global
        reader.byte()
        mutability = reader.byte()
        if mutability not in (0, 1):
            raise WasmError("invalid global mutability")
    else:
        raise WasmError(f"unknown import kind {kind}")


def inspect_imports(sections: list[Section]) -> int:
    total = 0
    for section in sections:
        if section.section_id != 2:
            continue
        reader = Reader(section.payload)
        count = reader.uleb()
        total += count
        for _ in range(count):
            reader.name()
            reader.name()
            kind = reader.byte()
            skip_import_descriptor(reader, kind)
        if reader.remaining() != 0:
            raise WasmError("trailing bytes in import section")
    return total


def inspect_memories(sections: list[Section]) -> tuple[int, int | None]:
    memories: list[tuple[int, int | None]] = []
    for section in sections:
        if section.section_id != 5:
            continue
        reader = Reader(section.payload)
        count = reader.uleb()
        for _ in range(count):
            minimum, maximum, _ = parse_limits(reader)
            memories.append((minimum, maximum))
        if reader.remaining() != 0:
            raise WasmError("trailing bytes in memory section")
    if len(memories) != 1:
        raise WasmError(f"expected exactly one internal memory, found {len(memories)}")
    return memories[0]


def inspect_exports(sections: list[Section]) -> dict[str, int]:
    exports: dict[str, int] = {}
    for section in sections:
        if section.section_id != 7:
            continue
        reader = Reader(section.payload)
        count = reader.uleb()
        for _ in range(count):
            name = reader.name()
            kind = reader.byte()
            reader.uleb()  # index
            if name in exports:
                raise WasmError(f"duplicate export name: {name}")
            exports[name] = kind
        if reader.remaining() != 0:
            raise WasmError("trailing bytes in export section")
    return exports


def validate_exports(exports: dict[str, int]) -> None:
    for name, expected_kind in REQUIRED_EXPORTS.items():
        actual_kind = exports.get(name)
        if actual_kind != expected_kind:
            raise WasmError(
                f"required export {name!r} has kind {actual_kind!r}, expected {expected_kind}"
            )

    unexpected = {
        name: kind
        for name, kind in exports.items()
        if name not in REQUIRED_EXPORTS and name not in ALLOWED_EXTRA_EXPORTS
    }
    if unexpected:
        raise WasmError(f"unexpected exports: {unexpected}")
    for name, expected_kind in ALLOWED_EXTRA_EXPORTS.items():
        if name in exports and exports[name] != expected_kind:
            raise WasmError(f"toolchain export {name!r} has unexpected kind {exports[name]}")

    memory_exports = [name for name, kind in exports.items() if kind == 2]
    if memory_exports != ["memory"]:
        raise WasmError(f"expected only exported memory 'memory', got {memory_exports}")


def inspect(path: Path) -> None:
    module = path.read_bytes()
    if len(module) > MAX_FUSED_BYTES:
        raise WasmError(
            f"fused artifact is {len(module)} bytes; budget is {MAX_FUSED_BYTES} bytes"
        )

    sections = parse_sections(module)
    if any(section.section_id == 8 for section in sections):
        raise WasmError("start section is forbidden")
    if any(section.section_id == 13 for section in sections):
        raise WasmError("exception/tag section is forbidden")

    import_count = inspect_imports(sections)
    if import_count != 0:
        raise WasmError(f"expected zero imports, found {import_count}")

    minimum_pages, maximum_pages = inspect_memories(sections)
    exports = inspect_exports(sections)
    validate_exports(exports)

    digest = hashlib.sha256(module).hexdigest()
    max_text = "unbounded" if maximum_pages is None else str(maximum_pages)
    print(
        "PASS wasm "
        f"size={len(module)} imports=0 memory_pages={minimum_pages}..{max_text} "
        f"exports={','.join(sorted(exports))} sha256={digest}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("wasm", type=Path)
    args = parser.parse_args()
    try:
        inspect(args.wasm)
    except (OSError, WasmError) as exc:
        print(f"FAIL wasm: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
