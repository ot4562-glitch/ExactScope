#!/usr/bin/env python3
"""Cold-path capability record for the experimental ExactScope Attach Profile.

The record captures decisions that must not be rediscovered on every request: the
qualified semantic answer contract, minimum-sufficient prompt profile, native output
surface, and parity-qualified host accelerators. It contains no model/runtime client,
probe runner, retry logic, or vendor implementation.

This is an unreleased v1.1 adapter research format, not a frozen core ABI.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

FORMAT = "exactscope.attach-capability-record"
FORMAT_VERSION = "0.1"
PROMPT_PROFILES = frozenset({"full", "no-policy", "compact-native"})
IDENTITY_SCOPES = frozenset({"session", "persistent"})
OFF = "off"
MAX_ID_BYTES = 96


class CapabilityRecordError(ValueError):
    """Malformed, stale, or unsupported attach capability record."""


def _text(value: Any, label: str, *, max_bytes: int = MAX_ID_BYTES) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CapabilityRecordError(f"{label} must be nonempty text")
    if len(value.encode("utf-8")) > max_bytes:
        raise CapabilityRecordError(f"{label} exceeds bounded size")
    return value


def _digest(value: Any, label: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    text = _text(value, label, max_bytes=64)
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise CapabilityRecordError(f"{label} must be a lowercase SHA-256 digest")
    return text


@dataclass(frozen=True, slots=True)
class AttachCapabilityRecord:
    """One prequalified model/runtime Attach Profile decision."""

    host_profile_sha256: str
    identity_scope: str
    answer_contract_id: str
    output_surface_id: str
    prompt_profile: str
    prompt_qualification_sha256: str
    prefix_cache_mode: str = OFF
    prefix_cache_parity_sha256: str | None = None
    speculation_mode: str = OFF
    speculation_parity_sha256: str | None = None
    version: str = FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.version != FORMAT_VERSION:
            raise CapabilityRecordError("unsupported attach capability record version")
        _digest(self.host_profile_sha256, "host_profile_sha256")
        if _text(self.identity_scope, "identity_scope") not in IDENTITY_SCOPES:
            raise CapabilityRecordError("unsupported attach capability identity scope")
        _text(self.answer_contract_id, "answer_contract_id")
        _text(self.output_surface_id, "output_surface_id")
        if _text(self.prompt_profile, "prompt_profile") not in PROMPT_PROFILES:
            raise CapabilityRecordError("unsupported attach prompt profile")
        _digest(self.prompt_qualification_sha256, "prompt_qualification_sha256")
        _qualified_mode(self.prefix_cache_mode, self.prefix_cache_parity_sha256, "prefix_cache")
        _qualified_mode(self.speculation_mode, self.speculation_parity_sha256, "speculation")

    def as_dict(self) -> dict[str, Any]:
        return {
            "format": FORMAT,
            "format_version": self.version,
            "host_profile_sha256": self.host_profile_sha256,
            "identity_scope": self.identity_scope,
            "answer_contract_id": self.answer_contract_id,
            "output_surface_id": self.output_surface_id,
            "prompt_profile": self.prompt_profile,
            "prompt_qualification_sha256": self.prompt_qualification_sha256,
            "prefix_cache_mode": self.prefix_cache_mode,
            "prefix_cache_parity_sha256": self.prefix_cache_parity_sha256,
            "speculation_mode": self.speculation_mode,
            "speculation_parity_sha256": self.speculation_parity_sha256,
        }

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            self.as_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8") + b"\n"

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def _qualified_mode(mode: Any, parity: Any, label: str) -> tuple[str, str | None]:
    value = _text(mode, f"{label}_mode")
    proof = _digest(parity, f"{label}_parity_sha256", optional=True)
    if value == OFF:
        if proof is not None:
            raise CapabilityRecordError(f"{label} parity proof must be absent when mode=off")
        return value, None
    if proof is None:
        raise CapabilityRecordError(f"{label} mode requires an exact-parity qualification digest")
    return value, proof


def parse_capability_record(value: Any) -> AttachCapabilityRecord:
    """Parse and fully validate one cold-path record without probing the host."""
    expected = {
        "format",
        "format_version",
        "host_profile_sha256",
        "identity_scope",
        "answer_contract_id",
        "output_surface_id",
        "prompt_profile",
        "prompt_qualification_sha256",
        "prefix_cache_mode",
        "prefix_cache_parity_sha256",
        "speculation_mode",
        "speculation_parity_sha256",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise CapabilityRecordError("attach capability record shape drift")
    if value.get("format") != FORMAT or value.get("format_version") != FORMAT_VERSION:
        raise CapabilityRecordError("unsupported attach capability record identity")

    host_profile = _digest(value.get("host_profile_sha256"), "host_profile_sha256")
    scope = _text(value.get("identity_scope"), "identity_scope")
    if scope not in IDENTITY_SCOPES:
        raise CapabilityRecordError("unsupported attach capability identity scope")
    prompt_profile = _text(value.get("prompt_profile"), "prompt_profile")
    if prompt_profile not in PROMPT_PROFILES:
        raise CapabilityRecordError("unsupported attach prompt profile")
    prefix_mode, prefix_proof = _qualified_mode(
        value.get("prefix_cache_mode"), value.get("prefix_cache_parity_sha256"), "prefix_cache"
    )
    speculation_mode, speculation_proof = _qualified_mode(
        value.get("speculation_mode"), value.get("speculation_parity_sha256"), "speculation"
    )

    return AttachCapabilityRecord(
        host_profile_sha256=host_profile,
        identity_scope=scope,
        answer_contract_id=_text(value.get("answer_contract_id"), "answer_contract_id"),
        output_surface_id=_text(value.get("output_surface_id"), "output_surface_id"),
        prompt_profile=prompt_profile,
        prompt_qualification_sha256=_digest(
            value.get("prompt_qualification_sha256"), "prompt_qualification_sha256"
        ),
        prefix_cache_mode=prefix_mode,
        prefix_cache_parity_sha256=prefix_proof,
        speculation_mode=speculation_mode,
        speculation_parity_sha256=speculation_proof,
    )


def load_for_host(
    raw: bytes | str,
    *,
    host_profile_sha256: str,
    allow_session_scope: bool = True,
) -> AttachCapabilityRecord:
    """Load a record only when its prequalified host identity is still current."""
    if isinstance(raw, bytes):
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CapabilityRecordError("capability record must be UTF-8 JSON") from exc
    elif isinstance(raw, str):
        text = raw
    else:
        raise CapabilityRecordError("capability record input must be text or bytes")
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CapabilityRecordError("capability record is not valid JSON") from exc
    record = parse_capability_record(value)
    expected_host = _digest(host_profile_sha256, "current host_profile_sha256")
    if record.host_profile_sha256 != expected_host:
        raise CapabilityRecordError("capability record does not match current host profile")
    if record.identity_scope == "session" and not allow_session_scope:
        raise CapabilityRecordError("session-scoped capability record cannot be reused persistently")
    return record
