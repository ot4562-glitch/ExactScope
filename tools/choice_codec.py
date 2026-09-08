"""Strict one-field JSON choice codec; parsing checks syntax, not task truth.

schema_json returns UTF-8 bytes with compact JSON, lexically sorted object
keys, canonical label order and null last. parse_choice accepts text or strict
UTF-8 bytes, including surrounding JSON whitespace, and returns a typed success
or failure. Invalid output and a valid null abstention are distinct by type.
No trimming, case folding, normalization, substring matching or repair occurs.
"""
from __future__ import annotations

from dataclasses import dataclass
import json

from choice_contract import ChoiceSpec


@dataclass(frozen=True, slots=True)
class ChoiceSuccess:
    value: str | None


@dataclass(frozen=True, slots=True)
class ChoiceFailure:
    pass


CHOICE_FAILURE = ChoiceFailure()
ChoiceResult = ChoiceSuccess | ChoiceFailure


def schema_json(spec: ChoiceSpec) -> bytes:
    values = [label for label, _ in spec.labels]
    answer = {"type": "string", "enum": values}
    if spec.abstain_description is not None:
        values.append(None)
        answer["type"] = ["string", "null"]
    schema = {"type": "object", "additionalProperties": False,
              "properties": {"a": answer}, "required": ["a"]}
    return json.dumps(schema, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("non-JSON constant: " + value)


def parse_choice(content: str | bytes, spec: ChoiceSpec) -> ChoiceResult:
    try:
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="strict")
        if not isinstance(content, str):
            return CHOICE_FAILURE
        parsed = json.loads(content, object_pairs_hook=_unique_object,
                            parse_constant=_reject_constant)
    except (ValueError, RecursionError):
        return CHOICE_FAILURE
    if not isinstance(parsed, dict) or set(parsed) != {"a"}:
        return CHOICE_FAILURE
    value = parsed["a"]
    if value is None:
        return ChoiceSuccess(None) if spec.abstain_description is not None else CHOICE_FAILURE
    if isinstance(value, str) and any(value == label for label, _ in spec.labels):
        return ChoiceSuccess(value)
    return CHOICE_FAILURE
