#!/usr/bin/env python3
"""Strict steady-state answer finalizer for the experimental attach profile.

This intentionally contains no surface negotiation, calibration, model/runtime API,
retry, repair, or prompt logic. The host may enforce a qualified native output surface;
ExactScope still validates the returned semantic value independently.
"""
from __future__ import annotations

import json
from typing import Any

from grounding_answer_contract import CompiledAnswerSpec, compile_answer_spec


class FinalizerError(ValueError):
    """Invalid finalizer invocation; malformed model output returns None instead."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def finalize_answer(
    content: str,
    answer_spec: dict[str, Any] | CompiledAnswerSpec | None = None,
) -> dict[str, Any] | None:
    """Validate one exact {"a": value} result; never repair or infer missing syntax."""
    if not isinstance(content, str):
        raise FinalizerError("content must be text")
    try:
        parsed = json.loads(
            content,
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
        compiled = compile_answer_spec(answer_spec)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    if not isinstance(parsed, dict) or set(parsed) != {"a"}:
        return None
    answer = parsed["a"]
    if not compiled.validate(answer):
        return None
    if answer is None:
        return {"a": None, "disposition": "abstain"}
    return {"a": answer, "disposition": "answer"}
