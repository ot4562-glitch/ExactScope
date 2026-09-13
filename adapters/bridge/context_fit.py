#!/usr/bin/env python3
"""Detached host-owned token/context-fit negotiation experiment for ExactScope Bridge.

The host owns chat-template rendering and tokenization. ExactScope supplies only a
small, ordered set of already-valid semantic deliveries (for example complete 2048,
1024, and 512-byte projection tiers). The host reports whether each candidate fits;
this module chooses the first preferred candidate that fits. It never truncates text,
rebuilds evidence, or imports a tokenizer/runtime library.

This is an unreleased v1.1 research seam, not a frozen public ABI.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from delivery import Delivery

MAX_FIT_CANDIDATES = 4


class ContextFitError(ValueError):
    """Malformed or semantically unsafe context-fit experiment input."""


@dataclass(frozen=True, slots=True)
class FitReport:
    """One host measurement for one already-renderable semantic delivery."""

    fits: bool
    input_tokens: int | None = None
    input_capacity_tokens: int | None = None
    reserved_output_tokens: int | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class FitCandidate:
    """One complete semantic candidate ordered by caller preference."""

    candidate_id: str
    delivery: Delivery
    semantic_identity: str


@dataclass(frozen=True, slots=True)
class FitAttempt:
    candidate_id: str
    report: FitReport


@dataclass(frozen=True, slots=True)
class FitSelection:
    selected: FitCandidate | None
    attempts: tuple[FitAttempt, ...]


def _nonempty_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContextFitError(f"{label} must be nonempty text")
    return value


def _validate_report(report: FitReport) -> None:
    if not isinstance(report, FitReport):
        raise ContextFitError("host fit callback must return FitReport")
    for label, value in (
        ("input_tokens", report.input_tokens),
        ("input_capacity_tokens", report.input_capacity_tokens),
        ("reserved_output_tokens", report.reserved_output_tokens),
    ):
        if value is not None and (type(value) is not int or value < 0):
            raise ContextFitError(f"{label} must be a nonnegative integer when reported")
    if report.input_capacity_tokens is not None and report.reserved_output_tokens is not None:
        if report.reserved_output_tokens > report.input_capacity_tokens:
            raise ContextFitError("reserved output tokens exceed host capacity")
    if report.input_tokens is not None and report.input_capacity_tokens is not None:
        usable = report.input_capacity_tokens - (report.reserved_output_tokens or 0)
        observed_fit = report.input_tokens <= usable
        if report.fits != observed_fit:
            raise ContextFitError("host fit report contradicts reported token capacity")
    if report.detail is not None and not isinstance(report.detail, str):
        raise ContextFitError("fit report detail must be text when present")


def _validate_candidates(candidates: Sequence[FitCandidate]) -> None:
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        raise ContextFitError("fit candidates must be a sequence")
    if not 1 <= len(candidates) <= MAX_FIT_CANDIDATES:
        raise ContextFitError(f"fit candidates must contain between 1 and {MAX_FIT_CANDIDATES} entries")

    ids: set[str] = set()
    reference: FitCandidate | None = None
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, FitCandidate):
            raise ContextFitError(f"fit candidate {index} has invalid type")
        candidate_id = _nonempty_text(candidate.candidate_id, f"fit candidate {index} id")
        if candidate_id in ids:
            raise ContextFitError("fit candidate ids must be unique")
        ids.add(candidate_id)
        _nonempty_text(candidate.semantic_identity, f"fit candidate {index} semantic identity")
        delivery = candidate.delivery
        if not isinstance(delivery, Delivery) or delivery.action != "generate":
            raise ContextFitError("context-fit candidates must be generation deliveries")
        if not delivery.messages:
            raise ContextFitError("context-fit candidate generation delivery has no messages")

        if reference is None:
            reference = candidate
            continue
        left = reference.delivery
        right = delivery
        if candidate.semantic_identity != reference.semantic_identity:
            raise ContextFitError("context-fit candidates must share one semantic identity")
        if (
            right.route != left.route
            or right.profile_sha256 != left.profile_sha256
            or right.states != left.states
            or right.answer_spec_sha256 != left.answer_spec_sha256
            or right.prefix_cache_key != left.prefix_cache_key
            or tuple(message.role for message in right.messages) != tuple(message.role for message in left.messages)
        ):
            raise ContextFitError("context-fit candidates drift outside one semantic delivery family")


def select_fitting_delivery(
    candidates: Sequence[FitCandidate],
    measure: Callable[[Delivery], FitReport],
) -> FitSelection:
    """Choose the first semantically preferred candidate that the host says fits.

    The callback may render/tokenize, but must not perform generation. Candidate order
    is semantic preference order. Measurement stops at the first fit so the seam stays
    bounded and cold/preparation-path friendly.
    """
    _validate_candidates(candidates)
    if not callable(measure):
        raise ContextFitError("host fit measure must be callable")

    attempts: list[FitAttempt] = []
    for candidate in candidates:
        try:
            report = measure(candidate.delivery)
        except ContextFitError:
            raise
        except Exception as exc:  # host/runtime adapter error remains explicit and fail-closed
            raise ContextFitError(f"host context-fit measurement failed: {exc}") from exc
        _validate_report(report)
        attempts.append(FitAttempt(candidate.candidate_id, report))
        if report.fits:
            return FitSelection(candidate, tuple(attempts))
    return FitSelection(None, tuple(attempts))
