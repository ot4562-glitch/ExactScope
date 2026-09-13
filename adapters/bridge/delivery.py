#!/usr/bin/env python3
"""Tiny, backend-neutral delivery contract for ExactScope integration experiments.

This module intentionally knows nothing about retrieval, authority resolution, evidence
projection, or any inference runtime.  Only ``from_v11_plan`` understands the current
unreleased ExactScope v1.1-dev planner shape; backend adapters consume ``Delivery``.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

DELIVERY_VERSION = 1
ACTIONS = frozenset({"complete", "generate"})
AUTHORITIES = frozenset({"authoritative", "supplemental"})
GROUNDING_STATES = frozenset({"grounded", "none", "ambiguous", "conflict", "unavailable"})
MESSAGE_ROLES = frozenset({"system", "user", "assistant", "tool"})


class BridgeContractError(ValueError):
    """The ExactScope-to-runtime delivery boundary was malformed or ambiguous."""


@dataclass(frozen=True, slots=True)
class TargetState:
    target_key: str
    authority: str
    state: str


@dataclass(frozen=True, slots=True)
class Message:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class Delivery:
    """One already-decided ExactScope delivery action.

    Backends MUST NOT reinterpret ``states`` or rebuild evidence from them.  ``reply`` is
    authoritative when action=complete; ``messages`` are the only model-visible payload
    when action=generate.
    """

    action: str
    route: str
    profile_sha256: str
    states: tuple[TargetState, ...]
    reply: dict[str, Any] | None
    messages: tuple[Message, ...]
    answer_spec_sha256: str | None = None
    prefix_cache_key: str | None = None
    version: int = DELIVERY_VERSION

    def messages_json(self) -> str:
        return json.dumps(
            [{"role": message.role, "content": message.content} for message in self.messages],
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "v": self.version,
            "action": self.action,
            "route": self.route,
            "profile_sha256": self.profile_sha256,
            "states": [
                {"target_key": item.target_key, "authority": item.authority, "state": item.state}
                for item in self.states
            ],
            "reply": self.reply,
            "messages": [
                {"role": message.role, "content": message.content} for message in self.messages
            ],
            "answer_spec_sha256": self.answer_spec_sha256,
            "prefix_cache_key": self.prefix_cache_key,
        }


def _text(value: Any, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value):
        raise BridgeContractError(f"{name} must be {'text' if allow_empty else 'nonempty text'}")
    return value


def _digest(value: Any, name: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    text = _text(value, name)
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise BridgeContractError(f"{name} must be a lowercase SHA-256 hex digest")
    return text


def _states(frame: Any) -> tuple[TargetState, ...]:
    if not isinstance(frame, dict):
        raise BridgeContractError("plan.frame must be an object")
    groups = frame.get("groups")
    if not isinstance(groups, list):
        raise BridgeContractError("plan.frame.groups must be a list")
    out: list[TargetState] = []
    for index, group in enumerate(groups):
        if not isinstance(group, dict):
            raise BridgeContractError(f"plan.frame.groups[{index}] must be an object")
        target_key = _text(group.get("target_key"), f"plan.frame.groups[{index}].target_key")
        authority = _text(group.get("authority"), f"plan.frame.groups[{index}].authority")
        state = _text(group.get("state"), f"plan.frame.groups[{index}].state")
        if authority not in AUTHORITIES:
            raise BridgeContractError(f"unsupported grounding authority: {authority}")
        if state not in GROUNDING_STATES:
            raise BridgeContractError(f"unsupported grounding state: {state}")
        out.append(TargetState(target_key, authority, state))
    return tuple(out)


def _messages(value: Any) -> tuple[Message, ...]:
    if not isinstance(value, list) or not value:
        raise BridgeContractError("generation delivery requires nonempty messages")
    out: list[Message] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict) or set(item) != {"role", "content"}:
            raise BridgeContractError(f"messages[{index}] must contain only role/content")
        role = _text(item.get("role"), f"messages[{index}].role")
        content = _text(item.get("content"), f"messages[{index}].content", allow_empty=True)
        if role not in MESSAGE_ROLES:
            raise BridgeContractError(f"unsupported message role: {role}")
        out.append(Message(role, content))
    return tuple(out)


def from_v11_plan(plan: dict[str, Any]) -> Delivery:
    """Normalize the current v1.1-dev planner result behind one removable adapter.

    This is deliberately the *only* Bridge function that reaches into the development
    planner's dictionary shape.  A future frozen public delivery API should replace this
    function without changing ORT/ExecuTorch/LiteRT adapters.
    """
    if not isinstance(plan, dict):
        raise BridgeContractError("ExactScope plan must be an object")
    model_called = plan.get("model_called")
    if type(model_called) is not bool:
        raise BridgeContractError("plan.model_called must be boolean")
    route = _text(plan.get("route"), "plan.route")
    profile_sha256 = _digest(plan.get("profile_sha256"), "plan.profile_sha256")
    states = _states(plan.get("frame"))

    amplifier = plan.get("amplifier")
    if amplifier is None:
        amplifier = {}
    if not isinstance(amplifier, dict):
        raise BridgeContractError("plan.amplifier must be an object when present")
    answer_spec_sha256 = _digest(
        amplifier.get("answer_spec_sha256"), "plan.amplifier.answer_spec_sha256", optional=True
    )
    prefix_cache_key = _digest(
        amplifier.get("prefix_cache_key"), "plan.amplifier.prefix_cache_key", optional=True
    )

    reply = plan.get("reply")
    messages_value = plan.get("messages")
    if model_called:
        if reply is not None:
            raise BridgeContractError("generation delivery cannot also carry a host reply")
        messages = _messages(messages_value)
        action = "generate"
    else:
        if not isinstance(reply, dict) or "disposition" not in reply:
            raise BridgeContractError("deterministic delivery requires a host reply with disposition")
        if messages_value is not None:
            raise BridgeContractError("deterministic delivery cannot carry model messages")
        messages = ()
        action = "complete"

    return Delivery(
        action=action,
        route=route,
        profile_sha256=profile_sha256,
        states=states,
        reply=reply,
        messages=messages,
        answer_spec_sha256=answer_spec_sha256,
        prefix_cache_key=prefix_cache_key,
    )
