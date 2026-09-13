#!/usr/bin/env python3
"""Compiled deterministic answer contracts for the ExactScope runtime amplifier."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any

ANSWER_MAX_CHARS = 64
MAX_ANSWER_CHOICES = 32
ANSWER_SPEC_KINDS = ("text", "choice", "boolean", "integer", "number")
DEFAULT_ANSWER_SPEC = {"kind": "text", "nullable": True, "max_chars": ANSWER_MAX_CHARS}


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def answer_spec_cache_key(
    answer_spec: dict[str, Any] | "CompiledAnswerSpec" | None = None,
    *,
    answer_choices: tuple[str, ...] | list[str] | None = None,
) -> bytes:
    """Canonical in-memory cache identity for one answer contract.

    The key is the canonical contract itself rather than a truncated digest, so a
    long-lived runtime can reuse compiled constraints without introducing a second
    collision/validation path. Disk persistence is reserved for expensive model/runtime
    capability probes; compiling this tiny object remains a cold-path operation.
    """
    if isinstance(answer_spec, CompiledAnswerSpec):
        if answer_choices is not None:
            raise ValueError("compiled answer_spec and answer_choices are mutually exclusive")
        return _json_bytes(answer_spec.canonical)
    return _json_bytes(_canonical_spec(answer_spec, answer_choices=answer_choices))


def _validated_choices(answer_choices: tuple[str, ...] | list[str] | None) -> tuple[str, ...] | None:
    if answer_choices is None:
        return None
    if not isinstance(answer_choices, (tuple, list)) or not 2 <= len(answer_choices) <= MAX_ANSWER_CHOICES:
        raise ValueError(f"answer choices must contain between 2 and {MAX_ANSWER_CHOICES} labels")
    normalized: list[str] = []
    for choice in answer_choices:
        if not isinstance(choice, str) or not choice or choice.strip() != choice or len(choice) > ANSWER_MAX_CHARS:
            raise ValueError("answer choice must be a trimmed nonempty string within the answer limit")
        if any(ord(ch) < 0x20 for ch in choice):
            raise ValueError("answer choice contains a control character")
        if choice in normalized:
            raise ValueError("answer choices must be unique")
        normalized.append(choice)
    return tuple(normalized)


def _canonical_spec(
    answer_spec: dict[str, Any] | None = None,
    *,
    answer_choices: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any]:
    if answer_spec is not None and answer_choices is not None:
        raise ValueError("answer_spec and answer_choices are mutually exclusive")
    if answer_choices is not None:
        choices = _validated_choices(answer_choices)
        if choices is None:
            raise ValueError("answer choices are missing")
        return {"kind": "choice", "nullable": False, "choices": list(choices)}
    if answer_spec is None:
        return dict(DEFAULT_ANSWER_SPEC)
    if not isinstance(answer_spec, dict):
        raise ValueError("answer_spec must be an object")
    kind = answer_spec.get("kind")
    if kind not in ANSWER_SPEC_KINDS:
        raise ValueError("unsupported answer_spec kind")
    nullable = answer_spec.get("nullable", True)
    if type(nullable) is not bool:
        raise ValueError("answer_spec nullable must be boolean")

    if kind == "text":
        if set(answer_spec) - {"kind", "nullable", "max_chars"}:
            raise ValueError("text answer_spec has unexpected fields")
        max_chars = answer_spec.get("max_chars", ANSWER_MAX_CHARS)
        if type(max_chars) is not int or not 1 <= max_chars <= ANSWER_MAX_CHARS:
            raise ValueError(f"text answer_spec max_chars must be between 1 and {ANSWER_MAX_CHARS}")
        return {"kind": kind, "nullable": nullable, "max_chars": max_chars}

    if kind == "choice":
        if set(answer_spec) - {"kind", "nullable", "choices"}:
            raise ValueError("choice answer_spec has unexpected fields")
        choices = _validated_choices(answer_spec.get("choices"))
        if choices is None:
            raise ValueError("choice answer_spec requires choices")
        return {"kind": kind, "nullable": nullable, "choices": list(choices)}

    if kind == "boolean":
        if set(answer_spec) - {"kind", "nullable"}:
            raise ValueError("boolean answer_spec has unexpected fields")
        return {"kind": kind, "nullable": nullable}

    if set(answer_spec) - {"kind", "nullable", "minimum", "maximum"}:
        raise ValueError(f"{kind} answer_spec has unexpected fields")
    minimum = answer_spec.get("minimum")
    maximum = answer_spec.get("maximum")
    for label, value in (("minimum", minimum), ("maximum", maximum)):
        if value is None:
            continue
        if kind == "integer":
            if type(value) is not int:
                raise ValueError(f"integer answer_spec {label} must be an integer")
        elif type(value) not in {int, float} or not math.isfinite(float(value)):
            raise ValueError(f"number answer_spec {label} must be finite")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("answer_spec minimum cannot exceed maximum")
    normalized: dict[str, Any] = {"kind": kind, "nullable": nullable}
    if minimum is not None:
        normalized["minimum"] = minimum
    if maximum is not None:
        normalized["maximum"] = maximum
    return normalized


def _schema(spec: dict[str, Any]) -> dict[str, Any]:
    kind = spec["kind"]
    if kind == "text":
        value_schema: dict[str, Any] = {"type": "string", "maxLength": spec["max_chars"]}
    elif kind == "choice":
        value_schema = {"type": "string", "enum": list(spec["choices"])}
    elif kind == "boolean":
        value_schema = {"type": "boolean"}
    elif kind == "integer":
        value_schema = {"type": "integer"}
    else:
        value_schema = {"type": "number"}
    if "minimum" in spec:
        value_schema["minimum"] = spec["minimum"]
    if "maximum" in spec:
        value_schema["maximum"] = spec["maximum"]
    if spec["nullable"]:
        value_schema["type"] = [value_schema["type"], "null"]
        if kind == "choice":
            value_schema["enum"] = [*value_schema["enum"], None]
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {"a": value_schema},
        "required": ["a"],
    }


def _quoted_gbnf_terminal(value: str) -> str:
    return json.dumps(json.dumps(value, ensure_ascii=False), ensure_ascii=False)


def _gbnf(spec: dict[str, Any]) -> str:
    kind = spec["kind"]
    if kind == "text":
        value_rule = f'string | "null"' if spec["nullable"] else "string"
        tail = (
            f'\nstring ::= "\\\"" char{{1,{spec["max_chars"]}}} "\\\""'
            '\nchar ::= [^"\\\\\\x00-\\x1f] | escape'
            '\nescape ::= "\\\\" (["\\\\/bfnrt] | "u" hex hex hex hex)'
            '\nhex ::= [0-9a-fA-F]'
        )
    elif kind == "choice":
        terminals = " | ".join(_quoted_gbnf_terminal(choice) for choice in spec["choices"])
        if spec["nullable"]:
            terminals += ' | "null"'
        value_rule = "label"
        tail = "\nlabel ::= " + terminals
    elif kind == "boolean":
        value_rule = '"true" | "false"' + (' | "null"' if spec["nullable"] else "")
        tail = ""
    elif kind == "integer":
        value_rule = "integer" + (' | "null"' if spec["nullable"] else "")
        tail = '\ninteger ::= "-"? ("0" | [1-9] [0-9]*)'
    else:
        value_rule = "number" + (' | "null"' if spec["nullable"] else "")
        tail = (
            '\nnumber ::= "-"? ("0" | [1-9] [0-9]*) fraction? exponent?'
            '\nfraction ::= "." [0-9]+'
            '\nexponent ::= [eE] [+-]? [0-9]+'
        )
    return (
        'root ::= "{" ws "\\\"a\\\"" ws ":" ws value ws "}"'
        '\nws ::= [ \\t\\n\\r]*'
        '\nvalue ::= ' + value_rule + tail + "\n"
    )


def _instruction(spec: dict[str, Any]) -> str:
    if spec == DEFAULT_ANSWER_SPEC:
        return ""
    nullable = " Null is allowed only when the answer is unavailable." if spec["nullable"] else " Null is not allowed."
    kind = spec["kind"]
    if kind == "choice":
        body = "Field a must be exactly one of: " + ", ".join(json.dumps(v, ensure_ascii=False) for v in spec["choices"]) + "."
    elif kind == "boolean":
        body = "Field a must be a JSON boolean true or false."
    elif kind == "integer":
        body = "Field a must be a JSON integer."
    elif kind == "number":
        body = "Field a must be a finite JSON number."
    else:
        body = f"Field a must be a nonempty string of at most {spec['max_chars']} characters."
    bounds = ""
    if "minimum" in spec:
        bounds += f" Minimum is {spec['minimum']}."
    if "maximum" in spec:
        bounds += f" Maximum is {spec['maximum']}."
    return body + bounds + nullable


@dataclass(frozen=True, slots=True)
class CompiledAnswerSpec:
    """One validated answer contract compiled once for the request hot path."""

    canonical: dict[str, Any]
    sha256: str
    json_schema: dict[str, Any]
    gbnf: str
    instruction: str

    @property
    def kind(self) -> str:
        return self.canonical["kind"]

    @property
    def nullable(self) -> bool:
        return self.canonical["nullable"]

    def validate(self, value: Any) -> bool:
        if value is None:
            return self.nullable
        kind = self.kind
        if kind == "text":
            return isinstance(value, str) and bool(value.strip()) and len(value) <= self.canonical["max_chars"]
        if kind == "choice":
            return isinstance(value, str) and value in self.canonical["choices"]
        if kind == "boolean":
            return type(value) is bool
        if kind == "integer":
            if type(value) is not int:
                return False
        elif kind == "number":
            if type(value) not in {int, float} or not math.isfinite(float(value)):
                return False
        else:
            return False
        if "minimum" in self.canonical and value < self.canonical["minimum"]:
            return False
        if "maximum" in self.canonical and value > self.canonical["maximum"]:
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return dict(self.canonical)


def compile_answer_spec(
    answer_spec: dict[str, Any] | CompiledAnswerSpec | None = None,
    *,
    answer_choices: tuple[str, ...] | list[str] | None = None,
) -> CompiledAnswerSpec:
    if isinstance(answer_spec, CompiledAnswerSpec):
        if answer_choices is not None:
            raise ValueError("compiled answer_spec and answer_choices are mutually exclusive")
        return answer_spec
    canonical = _canonical_spec(answer_spec, answer_choices=answer_choices)
    encoded = _json_bytes(canonical)
    return CompiledAnswerSpec(
        canonical=canonical,
        sha256=hashlib.sha256(encoded).hexdigest(),
        json_schema=_schema(canonical),
        gbnf=_gbnf(canonical),
        instruction=_instruction(canonical),
    )


def validate_answer_choices(answer_choices: tuple[str, ...] | list[str] | None) -> tuple[str, ...] | None:
    return _validated_choices(answer_choices)


def normalize_answer_spec(
    answer_spec: dict[str, Any] | CompiledAnswerSpec | None = None,
    *,
    answer_choices: tuple[str, ...] | list[str] | None = None,
) -> dict[str, Any]:
    return compile_answer_spec(answer_spec, answer_choices=answer_choices).to_dict()


def answer_spec_sha256(answer_spec: dict[str, Any] | CompiledAnswerSpec | None = None, *, answer_choices=None) -> str:
    return compile_answer_spec(answer_spec, answer_choices=answer_choices).sha256


def validate_answer_value(value: Any, answer_spec: dict[str, Any] | CompiledAnswerSpec | None = None, *, answer_choices=None) -> bool:
    return compile_answer_spec(answer_spec, answer_choices=answer_choices).validate(value)


def answer_object_schema(answer_spec: dict[str, Any] | CompiledAnswerSpec | None = None, *, answer_choices=None) -> dict[str, Any]:
    return compile_answer_spec(answer_spec, answer_choices=answer_choices).json_schema


def answer_object_gbnf(answer_spec: dict[str, Any] | CompiledAnswerSpec | None = None, *, answer_choices=None) -> str:
    return compile_answer_spec(answer_spec, answer_choices=answer_choices).gbnf


def answer_spec_instruction(answer_spec: dict[str, Any] | CompiledAnswerSpec | None = None, *, answer_choices=None) -> str:
    return compile_answer_spec(answer_spec, answer_choices=answer_choices).instruction
