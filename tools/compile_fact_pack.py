#!/usr/bin/env python3
"""Compile and verify immutable ExactScope factual-recall packs."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "adapters" / "xs-recall-v0.1"
MAX_FACTS = 65535
MAX_QUERY_BYTES = 192
MAX_ALIASES = 32


class FactPackError(ValueError):
    pass


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FactPackError(f"cannot read JSON {path}: {exc}") from exc


def normalize_alias(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise FactPackError("fact alias must be a nonempty string")
    if len(value.encode("utf-8")) > MAX_QUERY_BYTES:
        raise FactPackError("fact alias exceeds 192 UTF-8 bytes")
    output: list[str] = []
    pending_space = False
    for char in value:
        code = ord(char)
        if "A" <= char <= "Z":
            char = char.lower()
        if char.isascii() and (char.isspace() or (not char.isalnum())):
            pending_space = bool(output)
            continue
        if pending_space:
            output.append(" ")
            pending_space = False
        output.append(char)
    normalized = "".join(output).strip()
    if not normalized:
        raise FactPackError("fact alias normalizes to empty")
    if len(normalized.encode("utf-8")) > MAX_QUERY_BYTES:
        raise FactPackError("normalized alias exceeds 192 UTF-8 bytes")
    return normalized


def require_string(value: Any, label: str, *, minimum: int = 1, maximum: int) -> str:
    if not isinstance(value, str) or not minimum <= len(value) <= maximum:
        raise FactPackError(f"{label} must be a string of length {minimum}..{maximum}")
    return value


def require_revision(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 0xFFFFFFFF:
        raise FactPackError(f"{label} must be an integer in 1..4294967295")
    return value


def validate_source(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise FactPackError("fact-pack source root must be an object")
    if document.get("format") != "exactscope.fact-pack.source" or document.get("format_version") != "0.1":
        raise FactPackError("unsupported fact-pack source format")
    pack_id = require_string(document.get("pack_id"), "pack_id", maximum=128)
    pack_revision = require_revision(document.get("pack_revision"), "pack_revision")
    authority = document.get("authority")
    if authority not in ("authoritative", "supplemental"):
        raise FactPackError("authority must be authoritative or supplemental")
    languages = document.get("languages", [])
    if not isinstance(languages, list) or len(languages) > 16 or any(not isinstance(item, str) or not 2 <= len(item) <= 32 for item in languages):
        raise FactPackError("languages must contain at most 16 short strings")
    if len(set(languages)) != len(languages):
        raise FactPackError("languages must be unique")
    source_set_sha256 = document.get("source_set_sha256")
    if source_set_sha256 is not None and (
        not isinstance(source_set_sha256, str)
        or len(source_set_sha256) != 64
        or any(char not in "0123456789abcdef" for char in source_set_sha256)
    ):
        raise FactPackError("source_set_sha256 must be null or lowercase SHA-256")
    facts = document.get("facts")
    if not isinstance(facts, list) or not 1 <= len(facts) <= MAX_FACTS:
        raise FactPackError("facts must contain 1..65535 records")

    compiled_facts: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    alias_owner: dict[str, str] = {}
    for index, raw in enumerate(facts):
        if not isinstance(raw, dict):
            raise FactPackError(f"facts[{index}] must be an object")
        fact_id = require_string(raw.get("id"), f"facts[{index}].id", maximum=160)
        if fact_id in seen_ids:
            raise FactPackError(f"duplicate fact id: {fact_id}")
        seen_ids.add(fact_id)
        evidence = require_string(raw.get("evidence"), f"facts[{index}].evidence", maximum=1024)
        source = require_string(raw.get("source"), f"facts[{index}].source", maximum=256)
        revision = require_revision(raw.get("revision"), f"facts[{index}].revision")
        aliases = raw.get("aliases")
        if not isinstance(aliases, list) or not 1 <= len(aliases) <= MAX_ALIASES:
            raise FactPackError(f"facts[{index}].aliases must contain 1..32 aliases")
        normalized_aliases = sorted({normalize_alias(alias) for alias in aliases})
        if len(normalized_aliases) != len(aliases):
            raise FactPackError(f"fact {fact_id} has duplicate aliases after normalization")
        for alias in normalized_aliases:
            owner = alias_owner.get(alias)
            if owner is not None and owner != fact_id:
                raise FactPackError(f"ambiguous exact alias {alias!r} belongs to both {owner} and {fact_id}")
            alias_owner[alias] = fact_id
        source_sha256 = raw.get("source_sha256")
        if source_sha256 is not None and (
            not isinstance(source_sha256, str)
            or len(source_sha256) != 64
            or any(char not in "0123456789abcdef" for char in source_sha256)
        ):
            raise FactPackError(f"fact {fact_id} has invalid source_sha256")
        for field in ("valid_from", "valid_until"):
            value = raw.get(field)
            if value is not None and not isinstance(value, str):
                raise FactPackError(f"fact {fact_id} {field} must be null or a string")
        compiled_facts.append(
            {
                "id": fact_id,
                "evidence": evidence,
                "source": source,
                "revision": revision,
                "aliases": normalized_aliases,
                "source_sha256": source_sha256,
                "valid_from": raw.get("valid_from"),
                "valid_until": raw.get("valid_until"),
            }
        )

    compiled_facts.sort(key=lambda fact: fact["id"])
    return {
        "format": "exactscope.fact-pack",
        "format_version": "0.1",
        "pack_id": pack_id,
        "pack_revision": pack_revision,
        "authority": authority,
        "languages": sorted(languages),
        "source_set_sha256": source_set_sha256,
        "facts": compiled_facts,
    }


def build(source_path: Path) -> dict[str, bytes]:
    source_bytes = source_path.read_bytes()
    try:
        source_document = json.loads(source_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise FactPackError(f"invalid source JSON: {exc}") from exc
    compiled = validate_source(source_document)
    compiled["source_document_sha256"] = digest(source_bytes)
    fact_pack = canonical(compiled)
    tool = canonical(load_json(ADAPTER / "xs-recall.tool.json"))
    grammar = (ADAPTER / "xs-recall.gbnf").read_bytes()
    prompt = (
        "Emit one xs_recall request only. Use a short fact-id or keyword query; do not answer from memory. "
        "If returned evidence is absent, do not invent a factual value.\n"
    ).encode("utf-8")
    files = {
        "fact-pack.json": fact_pack,
        "xs-recall.tool.json": tool,
        "xs-recall.gbnf": grammar,
        "constrained-prompt.txt": prompt,
    }
    facts = compiled["facts"]
    manifest = {
        "format": "exactscope.fact-pack.bundle",
        "format_version": "0.1",
        "pack_id": compiled["pack_id"],
        "pack_revision": compiled["pack_revision"],
        "authority": compiled["authority"],
        "source_document_sha256": compiled["source_document_sha256"],
        "files": {name: digest(data) for name, data in sorted(files.items())},
        "measurements": {
            "fact_count": len(facts),
            "evidence_bytes": sum(len(fact["evidence"].encode("utf-8")) for fact in facts),
            "alias_count": sum(len(fact["aliases"]) for fact in facts),
            "alias_bytes": sum(len(alias.encode("utf-8")) for fact in facts for alias in fact["aliases"]),
            "fact_pack_bytes": len(fact_pack),
            "model_prompt_bytes": len(prompt),
            "grammar_bytes": len(grammar),
            "tool_schema_bytes": len(tool),
        },
    }
    files["manifest.json"] = canonical(manifest)
    files["bundle-sha256.txt"] = (digest(files["manifest.json"]) + "\n").encode("ascii")
    return files


def write_bundle(files: dict[str, bytes], output: Path) -> None:
    if output.exists():
        actual = {path.name: path.read_bytes() for path in output.iterdir() if path.is_file()}
        if actual != files or any(path.is_dir() for path in output.iterdir()):
            raise FactPackError("immutable output differs; use a new output directory")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".xs-recall-", dir=output.parent) as tmp:
        stage = Path(tmp) / "bundle"
        stage.mkdir()
        for name, data in files.items():
            (stage / name).write_bytes(data)
        stage.rename(output)


def verify_bundle(path: Path) -> dict[str, Any]:
    if not path.is_dir():
        raise FactPackError("fact-pack bundle path is not a directory")
    manifest_path = path / "manifest.json"
    detached_path = path / "bundle-sha256.txt"
    if not manifest_path.is_file() or not detached_path.is_file():
        raise FactPackError("fact-pack bundle lacks manifest/detached digest")
    manifest_bytes = manifest_path.read_bytes()
    if detached_path.read_text(encoding="ascii").strip() != digest(manifest_bytes):
        raise FactPackError("fact-pack manifest detached digest mismatch")
    manifest = json.loads(manifest_bytes)
    if manifest.get("format") != "exactscope.fact-pack.bundle" or manifest.get("format_version") != "0.1":
        raise FactPackError("unsupported compiled fact-pack bundle")
    expected = set(manifest.get("files", {})) | {"manifest.json", "bundle-sha256.txt"}
    actual = {entry.name for entry in path.iterdir() if entry.is_file()}
    if expected != actual or any(entry.is_dir() or entry.is_symlink() for entry in path.iterdir()):
        raise FactPackError("fact-pack bundle inventory mismatch")
    for name, expected_sha in manifest["files"].items():
        if digest((path / name).read_bytes()) != expected_sha:
            raise FactPackError(f"fact-pack file digest mismatch: {name}")
    pack = load_json(path / "fact-pack.json")
    if pack.get("pack_id") != manifest.get("pack_id") or pack.get("pack_revision") != manifest.get("pack_revision"):
        raise FactPackError("fact-pack identity mismatch")
    validate_source(
        {
            "format": "exactscope.fact-pack.source",
            "format_version": "0.1",
            "pack_id": pack["pack_id"],
            "pack_revision": pack["pack_revision"],
            "authority": pack["authority"],
            "languages": pack.get("languages", []),
            "source_set_sha256": pack.get("source_set_sha256"),
            "facts": pack["facts"],
        }
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    compile_parser = sub.add_parser("compile")
    compile_parser.add_argument("--source", type=Path, required=True)
    compile_parser.add_argument("--output", type=Path, required=True)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("bundle", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "compile":
        files = build(args.source.resolve())
        write_bundle(files, args.output.resolve())
        manifest = verify_bundle(args.output.resolve())
        print(json.dumps({"bundle": str(args.output), "manifest_sha256": digest(canonical(manifest))}, sort_keys=True))
        return 0
    manifest = verify_bundle(args.bundle.resolve())
    print(json.dumps(manifest["measurements"], sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FactPackError, OSError, KeyError, ValueError) as exc:
        print(f"ExactScope fact-pack: FAIL: {exc}")
        raise SystemExit(1) from exc
