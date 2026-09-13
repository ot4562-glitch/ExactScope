#!/usr/bin/env python3
"""Experimental ExactScope Bridge target for Google LiteRT-LM.

LiteRT-LM owns the engine, conversation template and generation. ExactScope owns
retrieval/authority/evidence policy, deterministic completion and strict output
validation. This adapter passes only an already-decided Delivery into LiteRT-LM.
"""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import sys
from typing import Any

HERE = Path(__file__).resolve().parent
BRIDGE = HERE.parent
ROOT = BRIDGE.parents[1]
for path in (BRIDGE, ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from delivery import Delivery  # noqa: E402
from exactscope_v11 import finalize_generation, prepare_delivery  # noqa: E402


class LiteRtBridgeError(RuntimeError):
    pass


def _load_litert_lm() -> Any:
    try:
        return importlib.import_module("litert_lm")
    except ImportError as exc:
        raise LiteRtBridgeError(
            "LiteRT-LM is required only on the generation path"
        ) from exc


def _message_mapping(role: str, content: str) -> dict[str, Any]:
    return {"role": role, "content": [{"type": "text", "text": content}]}


def _extract_text(response: Any) -> str:
    if not isinstance(response, dict):
        raise LiteRtBridgeError("LiteRT-LM response must be an object")
    content = response.get("content")
    if not isinstance(content, list):
        raise LiteRtBridgeError("LiteRT-LM response content must be a list")
    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "text" and isinstance(item.get("text"), str):
            parts.append(item["text"])
    return "".join(parts)


def run_delivery(
    delivery: Delivery,
    *,
    model_path: Path | None,
    max_output_tokens: int = 32,
    litert_module: Any | None = None,
) -> dict[str, Any]:
    """Execute one Delivery without reinterpreting ExactScope semantics."""
    if delivery.action == "complete":
        return {
            "source": "exactscope",
            "model_called": False,
            "route": delivery.route,
            "reply": delivery.reply,
        }
    if delivery.action != "generate":
        raise LiteRtBridgeError(f"unsupported delivery action: {delivery.action}")
    if model_path is None:
        raise LiteRtBridgeError("model path is required for generation")
    if type(max_output_tokens) is not int or max_output_tokens < 1:
        raise LiteRtBridgeError("output limit must be a positive integer")
    if not delivery.messages or delivery.messages[-1].role != "user":
        raise LiteRtBridgeError("final approved message must have user role")

    litert_lm = litert_module if litert_module is not None else _load_litert_lm()
    history = [
        _message_mapping(message.role, message.content)
        for message in delivery.messages[:-1]
    ]
    last_message = _message_mapping(
        delivery.messages[-1].role, delivery.messages[-1].content
    )

    with litert_lm.Engine(model_path=str(model_path)) as engine:
        with engine.create_conversation(
            messages=history or None,
            automatic_tool_calling=False,
            max_output_tokens=max_output_tokens,
        ) as conversation:
            response = conversation.send_message(last_message)

    return {
        "source": "litert-lm",
        "model_called": True,
        "route": delivery.route,
        "raw_generation": _extract_text(response),
    }
