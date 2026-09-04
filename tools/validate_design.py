#!/usr/bin/env python3
"""Validate the ExactScope design baseline without implementing runtime logic."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "spec" / "schemas"
REGISTRY_DIR = ROOT / "spec" / "registries"
HEADER_DEFAULT = ROOT / "include" / "exactscope.h"

REQUIRED_FILES = (
    "README.md",
    "Cargo.toml",
    "rust-toolchain.toml",
    "LICENSE-APACHE",
    "LICENSE-MIT",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "docs/ARCHITECTURE.md",
    "docs/COMPATIBILITY.md",
    "docs/AI_INTEGRATION.md",
    "docs/DECISIONS.md",
    "docs/IMPLEMENTATION_PLAN.md",
    "docs/INSTALLATION.md",
    "docs/REFERENCES.md",
    ".github/workflows/design-baseline.yml",
    "packs/CATALOG_V0_1.md",
    "include/exactscope.h",
    "include/exactscope_wasm.h",
    "spec/CORE_ABI_V0_1.md",
    "spec/WASM_ABI_V0_1.md",
    "spec/NUMERIC_V0_1.md",
    "spec/SCOPEPACK_V0_1.md",
    "spec/TINYWIRE_V0_1.md",
    "spec/ERRORS_V0_1.md",
    "spec/registries/status-codes.json",
    "spec/registries/semantic-kinds.json",
    "spec/registries/rounding-modes.json",
    "spec/registries/kernel-ids.json",
    "spec/registries/vm-opcodes.json",
    "spec/registries/protocol-ids.json",
)

PROHIBITED_TOOL_SCHEMA_KEYS = {
    "$ref",
    "allOf",
    "anyOf",
    "oneOf",
    "not",
    "if",
    "then",
    "else",
    "contains",
    "dependentSchemas",
    "pattern",
    "patternProperties",
    "unevaluatedProperties",
}


class ValidationFailure(Exception):
    """Raised after one or more deterministic design checks fail."""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationFailure(f"{path.relative_to(ROOT)}: invalid JSON: {exc}") from exc


def collect_json_lines(path: Path) -> list[Any]:
    documents: list[Any] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ValidationFailure(f"{path.relative_to(ROOT)}: cannot read JSONL: {exc}") from exc
    for line_number, raw in enumerate(lines, start=1):
        if not raw.strip():
            continue
        try:
            documents.append(json.loads(raw))
        except json.JSONDecodeError as exc:
            raise ValidationFailure(
                f"{path.relative_to(ROOT)}:{line_number}: invalid JSONL object: {exc}"
            ) from exc
    return documents


def ensure_unique(values: Iterable[Any], label: str) -> None:
    seen: set[Any] = set()
    for value in values:
        if value in seen:
            raise ValidationFailure(f"duplicate {label}: {value!r}")
        seen.add(value)


def parse_c_defines(path: Path) -> dict[str, int]:
    text = path.read_text(encoding="utf-8")
    defines: dict[str, int] = {}
    for name, literal in re.findall(r"^\s*#define\s+([A-Z][A-Z0-9_]*)\s+([^\s/]+)", text, re.MULTILINE):
        cleaned = literal.strip().strip("()")
        cleaned = re.sub(r"[uUlL]+$", "", cleaned)
        try:
            defines[name] = int(cleaned, 0)
        except ValueError:
            continue
    return defines


def validate_registries() -> dict[str, dict[str, int]]:
    registries: dict[str, dict[str, int]] = {}
    for path in sorted(REGISTRY_DIR.glob("*.json")):
        document = read_json(path)
        if document.get("format") != "exactscope.registry" or document.get("format_version") != 1:
            raise ValidationFailure(f"{path.relative_to(ROOT)}: unsupported registry envelope")
        entries = document.get("entries")
        if not isinstance(entries, list) or not entries:
            raise ValidationFailure(f"{path.relative_to(ROOT)}: registry entries must be nonempty")

        keys: list[str] = []
        ids: list[int] = []
        c_names: list[str] = []
        mapping: dict[str, int] = {}
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ValidationFailure(f"{path.relative_to(ROOT)}: entry {index} is not an object")
            identifier = entry.get("id")
            key = entry.get("key")
            if not isinstance(identifier, int) or identifier < 0 or identifier > 0xFFFFFFFF:
                raise ValidationFailure(f"{path.relative_to(ROOT)}: invalid id at entry {index}")
            if not isinstance(key, str) or not key:
                raise ValidationFailure(f"{path.relative_to(ROOT)}: invalid key at entry {index}")
            ids.append(identifier)
            keys.append(key)
            mapping[key] = identifier
            c_name = entry.get("c_name")
            if c_name is not None:
                if not isinstance(c_name, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", c_name):
                    raise ValidationFailure(f"{path.relative_to(ROOT)}: invalid c_name {c_name!r}")
                c_names.append(c_name)
                header = ROOT / entry.get("header", "include/exactscope.h")
                defines = parse_c_defines(header)
                if defines.get(c_name) != identifier:
                    raise ValidationFailure(
                        f"{path.relative_to(ROOT)}: {c_name}={identifier} does not match {header.relative_to(ROOT)}"
                    )

        ensure_unique(keys, f"key in {path.name}")
        ensure_unique(c_names, f"c_name in {path.name}")
        if document.get("unique_ids") is True:
            ensure_unique(ids, f"id in {path.name}")
        registries[document["name"]] = mapping
    return registries


def validate_schema_documents() -> dict[str, Any]:
    schemas: dict[str, Any] = {}
    for path in sorted(SCHEMA_DIR.glob("*.json")):
        schema = read_json(path)
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as exc:  # jsonschema exposes several validation exception classes
            raise ValidationFailure(f"{path.relative_to(ROOT)}: invalid JSON Schema: {exc}") from exc
        schemas[path.name] = schema
    return schemas


def validate_examples(schemas: dict[str, Any]) -> int:
    validated = 0
    examples = ROOT / "spec" / "examples"
    explicit = {
        "compatibility-manifest.json": "compatibility-manifest.schema.json",
    }
    json_documents = list(examples.glob("*.json"))
    json_documents.extend((ROOT / "packs").glob("*.xsp.json"))
    for path in sorted(json_documents):
        document = read_json(path)
        schema_name = explicit.get(path.name)
        if schema_name is None:
            schema_ref = document.get("$schema") if isinstance(document, dict) else None
            if isinstance(schema_ref, str) and not schema_ref.startswith(("http://", "https://", "urn:")):
                schema_path = (path.parent / schema_ref).resolve()
                try:
                    schema_name = schema_path.relative_to(SCHEMA_DIR.resolve()).as_posix()
                except ValueError as exc:
                    raise ValidationFailure(
                        f"{path.relative_to(ROOT)}: local $schema escapes spec/schemas"
                    ) from exc
        if schema_name is None or schema_name not in schemas:
            raise ValidationFailure(f"{path.relative_to(ROOT)}: no local validation schema selected")
        validator = Draft202012Validator(schemas[schema_name], format_checker=FormatChecker())
        errors = sorted(validator.iter_errors(document), key=lambda error: list(error.absolute_path))
        if errors:
            first = errors[0]
            location = "/".join(str(part) for part in first.absolute_path) or "<root>"
            raise ValidationFailure(
                f"{path.relative_to(ROOT)}:{location}: schema validation failed: {first.message}"
            )
        validated += 1

    for path in sorted(examples.glob("*.jsonl")):
        documents = collect_json_lines(path)
        if path.name == "tiny-json.jsonl":
            tool_schemas = {
                "xs_find": schemas["xs-find-tool.schema.json"],
                "xs_eval": schemas["xs-eval-tool.schema.json"],
            }
            for index, document in enumerate(documents, start=1):
                if not isinstance(document, dict):
                    raise ValidationFailure(
                        f"{path.relative_to(ROOT)}:{index}: example must be an object"
                    )
                tool = document.get("tool")
                request = document.get("request")
                response = document.get("response")
                if tool not in tool_schemas or not isinstance(request, dict) or not isinstance(response, dict):
                    raise ValidationFailure(
                        f"{path.relative_to(ROOT)}:{index}: invalid tool/request/response envelope"
                    )
                errors = sorted(
                    Draft202012Validator(tool_schemas[tool]).iter_errors(request),
                    key=lambda error: list(error.absolute_path),
                )
                if errors:
                    first = errors[0]
                    location = "/".join(str(part) for part in first.absolute_path) or "<root>"
                    raise ValidationFailure(
                        f"{path.relative_to(ROOT)}:{index}:{location}: request schema failed: {first.message}"
                    )
                status = response.get("s")
                if not isinstance(status, int) or status < 0 or status > 23:
                    raise ValidationFailure(
                        f"{path.relative_to(ROOT)}:{index}: response status is not a stable core code"
                    )
                if status != 0 and "v" in response:
                    raise ValidationFailure(
                        f"{path.relative_to(ROOT)}:{index}: failed response must not contain a value"
                    )
        validated += len(documents)
    return validated


def nested_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from nested_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from nested_keys(nested)


def validate_tool_schema_subset(schemas: dict[str, Any]) -> None:
    for name in ("xs-find-tool.schema.json", "xs-eval-tool.schema.json"):
        used = set(nested_keys(schemas[name]))
        forbidden = sorted(used & PROHIBITED_TOOL_SCHEMA_KEYS)
        if forbidden:
            raise ValidationFailure(f"{name}: unsupported tiny-model schema keywords: {forbidden}")
        root = schemas[name]
        if root.get("type") != "object" or root.get("additionalProperties") is not False:
            raise ValidationFailure(f"{name}: root must be a closed object")
        required = set(root.get("required", []))
        properties = set(root.get("properties", {}))
        if required != properties:
            raise ValidationFailure(f"{name}: every model-facing field must be required")


def validate_schema_registry_alignment(schemas: dict[str, Any], registries: dict[str, dict[str, int]]) -> None:
    scope = schemas["scopepack-source.schema.json"]
    definitions = scope["$defs"]
    comparisons = {
        "status-codes": set(definitions["statusKey"]["enum"]),
        "semantic-kinds": set(definitions["semantic"]["enum"]),
        "rounding-modes": set(definitions["rounding"]["enum"]),
        "kernel-ids": set(definitions["operation"]["properties"]["kernel"]["enum"]),
        "vm-opcodes": set(definitions["instruction"]["prefixItems"][0]["enum"]),
    }
    for registry_name, schema_keys in comparisons.items():
        registry_keys = set(registries[registry_name])
        if schema_keys != registry_keys:
            raise ValidationFailure(
                f"schema/registry drift for {registry_name}: schema-only={sorted(schema_keys - registry_keys)}, "
                f"registry-only={sorted(registry_keys - schema_keys)}"
            )


def validate_program(
    instructions: list[Any],
    opcodes: dict[str, dict[str, Any]],
    arg_count: int,
    constant_count: int,
    result_count: int,
    classification: bool,
    label: str,
) -> None:
    if not instructions or instructions[-1] != ["end"]:
        raise ValidationFailure(f"{label}: program must end with exactly ['end']")
    stack = 0
    for index, instruction in enumerate(instructions):
        if not isinstance(instruction, list) or not instruction or not isinstance(instruction[0], str):
            raise ValidationFailure(f"{label}: malformed instruction {index}")
        key = instruction[0]
        spec = opcodes.get(key)
        if spec is None:
            raise ValidationFailure(f"{label}: unknown opcode {key!r}")
        if key == "result" and not classification:
            raise ValidationFailure(f"{label}: result opcode is classification-only")
        if key in {"and", "or", "not"} and not classification:
            raise ValidationFailure(f"{label}: boolean opcode {key!r} is classification-only")
        if key == "arg":
            if len(instruction) != 2 or not isinstance(instruction[1], int) or not 0 <= instruction[1] < arg_count:
                raise ValidationFailure(f"{label}: invalid argument operand at instruction {index}")
        elif key == "const":
            if len(instruction) != 2 or not isinstance(instruction[1], int) or not 0 <= instruction[1] < constant_count:
                raise ValidationFailure(f"{label}: invalid constant operand at instruction {index}")
        elif key == "result":
            if len(instruction) != 2 or not isinstance(instruction[1], int) or not 0 <= instruction[1] < result_count:
                raise ValidationFailure(f"{label}: invalid result operand at instruction {index}")
        elif key == "round":
            if len(instruction) != 3 or not all(isinstance(item, int) for item in instruction[1:]):
                raise ValidationFailure(f"{label}: round requires scale and rounding id")
        elif spec["operand"] == "none":
            if len(instruction) != 1:
                raise ValidationFailure(f"{label}: opcode {key!r} takes no operand")
        elif len(instruction) != 2 or not isinstance(instruction[1], int):
            raise ValidationFailure(f"{label}: opcode {key!r} requires one integer operand")

        pop_count = int(spec["pop"])
        push_count = int(spec["push"])
        if stack < pop_count:
            raise ValidationFailure(f"{label}: stack underflow at instruction {index}")
        stack = stack - pop_count + push_count
        if stack > 16:
            raise ValidationFailure(f"{label}: stack exceeds global v0.1 limit")
    if stack != 0:
        raise ValidationFailure(f"{label}: END did not consume the single final value")


def validate_scopepack_semantics(registries: dict[str, dict[str, int]]) -> None:
    path = ROOT / "spec" / "examples" / "econ-undergrad-minimal.xsp.json"
    document = read_json(path)
    source_ids = [source["id"] for source in document["sources"]]
    ensure_unique(source_ids, "source id")
    operations = document["operations"]
    ensure_unique((operation["id"] for operation in operations), "operation id")
    ensure_unique((operation["key"] for operation in operations), "operation key")

    opcode_document = read_json(REGISTRY_DIR / "vm-opcodes.json")
    opcodes = {entry["key"]: entry for entry in opcode_document["entries"]}
    for operation in operations:
        key = operation["key"]
        if not key.startswith(("math.", "stats.", "econ.", "finance.", "x.")):
            raise ValidationFailure(f"{key}: operation key does not use an allowed namespace")
        input_names = [item["name"] for item in operation["inputs"]]
        output_names = [item["name"] for item in operation["outputs"]]
        ensure_unique(input_names, f"input name in {key}")
        ensure_unique(output_names, f"output name in {key}")
        ensure_unique(operation["aliases"], f"alias in {key}")
        ensure_unique((test["name"] for test in operation["tests"]), f"test name in {key}")
        relation_details: list[int] = []
        for relation in operation.get("relations", []):
            if relation["left"] not in input_names or relation["right"] not in input_names:
                raise ValidationFailure(
                    f"{key}: relation references an undeclared input: {relation!r}"
                )
            if relation["left"] == relation["right"]:
                raise ValidationFailure(f"{key}: relation must compare distinct inputs")
            relation_details.append(relation["detail_id"])
        ensure_unique(relation_details, f"relation detail id in {key}")
        for test in operation["tests"]:
            if len(test["args"]) != len(input_names):
                raise ValidationFailure(
                    f"{key}:{test['name']}: test argument count does not match the signature"
                )
            expected_values = test["expect"].get("values", [])
            if test["expect"]["status"] == "OK" and len(expected_values) != len(output_names):
                raise ValidationFailure(
                    f"{key}:{test['name']}: successful test must specify every output value"
                )
            if test["expect"]["status"] != "OK" and expected_values:
                raise ValidationFailure(
                    f"{key}:{test['name']}: failed test must not specify output values"
                )
        unknown_sources = set(operation["sources"]) - set(source_ids)
        if unknown_sources:
            raise ValidationFailure(f"{key}: unknown source references {sorted(unknown_sources)}")

        constants = operation.get("constants", [])
        if operation["kind"] == "formula":
            programs = operation.get("programs", [])
            if len(programs) != len(output_names):
                raise ValidationFailure(f"{key}: one scalar program is required per output")
            if {program["output"] for program in programs} != set(output_names):
                raise ValidationFailure(f"{key}: program outputs do not match output declarations")
            for program in programs:
                validate_program(
                    program["instructions"],
                    opcodes,
                    len(input_names),
                    len(constants),
                    len(output_names),
                    False,
                    f"{key}:{program['output']}",
                )
        elif operation.get("kernel") not in registries["kernel-ids"]:
            raise ValidationFailure(f"{key}: unknown kernel {operation.get('kernel')!r}")

        classification_ids = [item["id"] for item in operation["classifications"]]
        classification_keys = [item["key"] for item in operation["classifications"]]
        ensure_unique(classification_ids, f"classification id in {key}")
        ensure_unique(classification_keys, f"classification key in {key}")
        for classification_item in operation["classifications"]:
            validate_program(
                classification_item["program"],
                opcodes,
                len(input_names),
                len(constants),
                len(output_names),
                True,
                f"{key}:classification:{classification_item['key']}",
            )


def validate_workflows() -> int:
    paths = sorted((ROOT / ".github" / "workflows").glob("*.y*ml"))
    if not paths:
        raise ValidationFailure("no GitHub workflow validates the design baseline")
    for path in paths:
        try:
            document = yaml.compose(path.read_text(encoding="utf-8"), Loader=yaml.SafeLoader)
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise ValidationFailure(f"{path.relative_to(ROOT)}: invalid YAML: {exc}") from exc
        if document is None:
            raise ValidationFailure(f"{path.relative_to(ROOT)}: empty workflow")
    return len(paths)


def validate_toml_workspace() -> int:
    paths = sorted(ROOT.rglob("*.toml"))
    documents: dict[Path, Any] = {}
    for path in paths:
        try:
            documents[path] = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
            raise ValidationFailure(f"{path.relative_to(ROOT)}: invalid TOML: {exc}") from exc

    workspace = documents[ROOT / "Cargo.toml"]
    members = workspace.get("workspace", {}).get("members")
    if not isinstance(members, list) or not members:
        raise ValidationFailure("Cargo.toml: workspace.members must be nonempty")
    ensure_unique(members, "Cargo workspace member")
    for member in members:
        if not isinstance(member, str) or not (ROOT / member / "Cargo.toml").is_file():
            raise ValidationFailure(f"Cargo.toml: missing workspace member manifest {member!r}")

    package = workspace.get("workspace", {}).get("package", {})
    example = read_json(ROOT / "spec" / "examples" / "compatibility-manifest.json")
    if package.get("version") != example.get("project_version"):
        raise ValidationFailure("Cargo workspace and compatibility example versions differ")
    if package.get("rust-version") != "1.84":
        raise ValidationFailure("Cargo.toml: v0.1 MSRV must remain 1.84 without a compatibility decision")

    toolchain = documents[ROOT / "rust-toolchain.toml"].get("toolchain", {})
    if toolchain.get("channel") != "1.98.0":
        raise ValidationFailure("rust-toolchain.toml: design baseline must use reviewed Rust 1.98.0")
    if "wasm32v1-none" not in toolchain.get("targets", []):
        raise ValidationFailure("rust-toolchain.toml: wasm32v1-none target is required")
    return len(paths)


def validate_repository_text() -> tuple[int, int]:
    ignored_parts = {".git", ".venv", "target"}
    files = [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and ignored_parts.isdisjoint(path.relative_to(ROOT).parts)
    ]
    markdown_files: list[Path] = []
    link_pattern = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative = path.relative_to(ROOT)
        if text and not text.endswith("\n"):
            raise ValidationFailure(f"{relative}: missing final newline")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if line.rstrip(" \t") != line:
                raise ValidationFailure(f"{relative}:{line_number}: trailing whitespace")
            if line.startswith(("<<<<<<<", "=======", ">>>>>>>")):
                raise ValidationFailure(f"{relative}:{line_number}: conflict marker")
        if path.suffix != ".md":
            continue
        markdown_files.append(path)
        for raw_target in link_pattern.findall(text):
            target = raw_target.split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError as exc:
                raise ValidationFailure(f"{relative}: local link escapes repository: {raw_target}") from exc
            if not resolved.exists():
                raise ValidationFailure(f"{relative}: missing local link target: {raw_target}")
    return len(files), len(markdown_files)


def validate_catalog() -> int:
    text = (ROOT / "packs" / "CATALOG_V0_1.md").read_text(encoding="utf-8")
    markers = (
        ("`math-basic`", "`statistics-core`", 16),
        ("`statistics-core`", "`econ-undergrad`", 18),
        ("`econ-undergrad`", "Explicitly deferred operations", 65),
    )
    keys: list[str] = []
    total = 0
    for start_marker, end_marker, expected in markers:
        try:
            section = text.split(f"## {start_marker}", 1)[1].split(f"## {end_marker}", 1)[0]
        except IndexError as exc:
            raise ValidationFailure(f"operation catalog section missing: {start_marker}") from exc
        rows = re.findall(r"^\|\s*(\d+)\s*\|\s*`([^`]+)`", section, re.MULTILINE)
        if len(rows) != expected:
            raise ValidationFailure(
                f"operation catalog {start_marker}: expected {expected}, found {len(rows)}"
            )
        keys.extend(signature.split("(", 1)[0] for _, signature in rows)
        total += len(rows)
    ensure_unique(keys, "canonical catalog operation key")
    return total


def format_fraction(value: Fraction, scale: int) -> tuple[str, bool]:
    with localcontext() as context:
        context.prec = 96
        quantum = Decimal(1).scaleb(-scale)
        decimal_value = Decimal(value.numerator) / Decimal(value.denominator)
        rounded_value = decimal_value.quantize(quantum, rounding=ROUND_HALF_EVEN)
    text = format(rounded_value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text == "-0":
        text = "0"
    return text, Fraction(rounded_value) != value


def validate_reference_operation() -> int:
    document = read_json(ROOT / "spec" / "examples" / "econ-undergrad-minimal.xsp.json")
    operations = document["operations"]
    if len(operations) != 1 or operations[0]["key"] != "econ.ped.mid":
        raise ValidationFailure("minimal economics fixture must contain only econ.ped.mid")
    operation = operations[0]
    scale = int(operation["output_policy"]["scale"])
    validated = 0
    for test in operation["tests"]:
        values = [Fraction(value) for value in test["args"]]
        p1, p2, q1, q2 = values
        expected = test["expect"]
        status = "OK"
        result: Fraction | None = None
        argument_index: int | None = None
        detail_id: int | None = None
        if p1 <= 0:
            status, argument_index, detail_id = "CONSTRAINT_VIOLATION", 0, 1
        elif p2 <= 0:
            status, argument_index, detail_id = "CONSTRAINT_VIOLATION", 1, 2
        elif q1 < 0:
            status, argument_index, detail_id = "CONSTRAINT_VIOLATION", 2, 3
        elif q2 < 0:
            status, argument_index, detail_id = "CONSTRAINT_VIOLATION", 3, 4
        else:
            try:
                quantity_change = (q2 - q1) / ((q1 + q2) / 2)
                price_change = (p2 - p1) / ((p1 + p2) / 2)
                result = quantity_change / price_change
            except ZeroDivisionError:
                status = "DIVIDE_BY_ZERO"
        if status != expected["status"]:
            raise ValidationFailure(
                f"econ.ped.mid:{test['name']}: expected {expected['status']}, got {status}"
            )
        if argument_index is not None and expected.get("argument_index") != argument_index:
            raise ValidationFailure(f"econ.ped.mid:{test['name']}: argument index drift")
        if detail_id is not None and expected.get("detail_id") != detail_id:
            raise ValidationFailure(f"econ.ped.mid:{test['name']}: constraint detail drift")
        if status == "OK":
            assert result is not None
            rendered, rounded = format_fraction(result, scale)
            classification = (
                "inelastic"
                if abs(result) < 1
                else "unit_elastic"
                if abs(result) == 1
                else "elastic"
            )
            if expected.get("values") != [rendered]:
                raise ValidationFailure(
                    f"econ.ped.mid:{test['name']}: expected value {expected.get('values')}, got {rendered}"
                )
            if expected.get("classification") != classification:
                raise ValidationFailure(f"econ.ped.mid:{test['name']}: classification drift")
            if expected.get("rounded") is not rounded:
                raise ValidationFailure(f"econ.ped.mid:{test['name']}: rounded flag drift")
        validated += 1
    return validated


def validate_required_text_contracts() -> None:
    scopepack = (ROOT / "spec" / "SCOPEPACK_V0_1.md").read_text(encoding="utf-8")
    tinywire = (ROOT / "spec" / "TINYWIRE_V0_1.md").read_text(encoding="utf-8")
    wasm = (ROOT / "spec" / "WASM_ABI_V0_1.md").read_text(encoding="utf-8")
    for path, text in (("SCOPEPACK_V0_1.md", scopepack), ("TINYWIRE_V0_1.md", tinywire)):
        if "CRC-32/ISO-HDLC" not in text or "0xcbf43926" not in text.lower():
            raise ValidationFailure(f"{path}: exact CRC-32 profile and check value are not frozen")
    if "must not promise to catch a panic" not in wasm or "panic=abort" not in wasm:
        raise ValidationFailure("WASM_ABI_V0_1.md: abort-only panic contract is missing")


def main() -> int:
    try:
        missing = [path for path in REQUIRED_FILES if not (ROOT / path).is_file()]
        if missing:
            raise ValidationFailure(f"missing required design files: {missing}")

        schemas = validate_schema_documents()
        registries = validate_registries()
        validate_tool_schema_subset(schemas)
        validate_schema_registry_alignment(schemas, registries)
        example_count = validate_examples(schemas)
        validate_scopepack_semantics(registries)
        reference_vector_count = validate_reference_operation()
        operation_count = validate_catalog()
        workflow_count = validate_workflows()
        toml_count = validate_toml_workspace()
        file_count, markdown_count = validate_repository_text()
        validate_required_text_contracts()
    except (OSError, UnicodeError, KeyError, TypeError, ValueError, ValidationFailure) as exc:
        print(f"DESIGN VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print(
        "ExactScope design valid: "
        f"{len(schemas)} schemas, {len(registries)} registries, "
        f"{example_count} example documents, {operation_count} catalog operations, "
        f"{reference_vector_count} reference vectors, {workflow_count} workflow, "
        f"{toml_count} TOML files, {markdown_count} Markdown/{file_count} repository files, "
        "ABI constants aligned"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
