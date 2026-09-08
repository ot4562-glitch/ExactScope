"""Product-general finite-choice contract, version 1; no label normalization.

Labels are a nonempty sequence of (label, description) pairs, frozen in UTF-8
byte order. Labels must be nonempty Unicode scalar strings (whitespace is
literal); descriptions and task_rule may be empty. None disables abstention;
a nonempty abstain_description explicitly enables it.

Hashes are lowercase SHA-256 hex. LP(x) is u64 big-endian byte length || x.
Surface bytes: LP(b'exactscope.choice.surface.v1'), u64 label count, each
LP(label UTF-8), LP(b'0' or b'1' for null disabled/enabled).
Contract bytes: LP(b'exactscope.choice.contract.v1'), LP(raw surface digest),
each LP(description UTF-8) in label order, LP(task_rule UTF-8), and, only when
enabled, LP(abstain_description UTF-8). Surface identity covers answer values;
contract identity additionally covers their meanings, not renderer wording.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib


def _utf8(value: str) -> bytes:
    if not isinstance(value, str):
        raise ValueError("expected a Unicode string")
    return value.encode("utf-8", errors="strict")


def _lp(value: bytes) -> bytes:
    return len(value).to_bytes(8, "big") + value


@dataclass(frozen=True)
class ChoiceSpec:
    labels: tuple[tuple[str, str], ...]
    task_rule: str
    abstain_description: str | None = None

    def __post_init__(self) -> None:
        pairs = []
        for pair in self.labels:
            if not isinstance(pair, (tuple, list)) or len(pair) != 2:
                raise ValueError("expected (label, description) pairs")
            label, description = pair
            if not _utf8(label):
                raise ValueError("empty label")
            _utf8(description)
            pairs.append((label, description))
        if not pairs or len({label for label, _ in pairs}) != len(pairs):
            raise ValueError("labels must be nonempty and unique")
        _utf8(self.task_rule)
        if self.abstain_description is not None:
            if not _utf8(self.abstain_description):
                raise ValueError("abstain_description must be nonempty when enabled")
        object.__setattr__(self, "labels", tuple(sorted(pairs, key=lambda p: _utf8(p[0]))))


def surface_hash(spec: ChoiceSpec) -> str:
    payload = _lp(b"exactscope.choice.surface.v1")
    payload += len(spec.labels).to_bytes(8, "big")
    payload += b"".join(_lp(_utf8(label)) for label, _ in spec.labels)
    payload += _lp(b"0" if spec.abstain_description is None else b"1")
    return hashlib.sha256(payload).hexdigest()


def contract_hash(spec: ChoiceSpec) -> str:
    payload = _lp(b"exactscope.choice.contract.v1")
    payload += _lp(bytes.fromhex(surface_hash(spec)))
    payload += b"".join(_lp(_utf8(description)) for _, description in spec.labels)
    payload += _lp(_utf8(spec.task_rule))
    if spec.abstain_description is not None:
        payload += _lp(_utf8(spec.abstain_description))
    return hashlib.sha256(payload).hexdigest()
