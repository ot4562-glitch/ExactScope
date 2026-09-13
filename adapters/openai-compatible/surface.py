#!/usr/bin/env python3
"""Small backend wire-profile map for ExactScope structured answers.

These profiles encode request-shape differences only. Capability support must still be
probed against the immutable runtime identity before a profile is trusted.
"""
from __future__ import annotations

from typing import Any

STANDARD_JSON_SCHEMA = "openai-json-schema-v1"
TRTLLM_GUIDED_JSON = "trtllm-guided-json-v1"
SURFACE_PROFILES = (STANDARD_JSON_SCHEMA, TRTLLM_GUIDED_JSON)


def constraint_fields(profile: str, schema: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(schema, dict) or not schema:
        raise ValueError("schema must be a nonempty object")
    if profile == STANDARD_JSON_SCHEMA:
        return {
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "grounding_answer", "schema": schema},
            }
        }
    if profile == TRTLLM_GUIDED_JSON:
        return {"response_format": {"type": "json", "schema": schema}}
    raise ValueError("unsupported OpenAI-compatible structured-output profile")
