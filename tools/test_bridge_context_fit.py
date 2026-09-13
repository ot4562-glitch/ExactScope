#!/usr/bin/env python3
"""Tests for the detached Bridge token/context-fit negotiation experiment."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "adapters/bridge"
if str(BRIDGE) not in sys.path:
    sys.path.insert(0, str(BRIDGE))

from context_fit import (  # noqa: E402
    ContextFitError,
    FitCandidate,
    FitReport,
    select_fitting_delivery,
)
from delivery import Delivery, Message, TargetState  # noqa: E402

DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64


def delivery(user_text: str, *, answer_spec: str = DIGEST_B, action: str = "generate") -> Delivery:
    return Delivery(
        action=action,
        route="local-corpus",
        profile_sha256=DIGEST_A,
        states=(TargetState("doc:1", "supplemental", "grounded"),),
        reply=None if action == "generate" else {"a": "x", "disposition": "answer"},
        messages=(Message("system", "stable policy"), Message("user", user_text)) if action == "generate" else (),
        answer_spec_sha256=answer_spec,
        prefix_cache_key=DIGEST_C if action == "generate" else None,
    )


def candidate(candidate_id: str, user_text: str, *, semantic_identity: str = "same") -> FitCandidate:
    return FitCandidate(candidate_id, delivery(user_text), semantic_identity)


class ContextFitTests(unittest.TestCase):
    def test_selects_first_preferred_candidate_that_fits_and_stops(self):
        candidates = [
            candidate("2048", "large evidence"),
            candidate("1024", "medium evidence"),
            candidate("512", "small evidence"),
        ]
        calls = []
        reports = iter([
            FitReport(False, input_tokens=220, input_capacity_tokens=200, reserved_output_tokens=0),
            FitReport(True, input_tokens=180, input_capacity_tokens=200, reserved_output_tokens=0),
        ])

        def measure(value):
            calls.append(value.messages[-1].content)
            return next(reports)

        selection = select_fitting_delivery(candidates, measure)
        self.assertIsNotNone(selection.selected)
        self.assertEqual(selection.selected.candidate_id, "1024")
        self.assertEqual([attempt.candidate_id for attempt in selection.attempts], ["2048", "1024"])
        self.assertEqual(calls, ["large evidence", "medium evidence"])

    def test_returns_none_when_no_complete_candidate_fits(self):
        candidates = [candidate("1024", "medium"), candidate("512", "small")]
        selection = select_fitting_delivery(
            candidates,
            lambda _delivery: FitReport(False, input_tokens=150, input_capacity_tokens=128),
        )
        self.assertIsNone(selection.selected)
        self.assertEqual([attempt.candidate_id for attempt in selection.attempts], ["1024", "512"])

    def test_rejects_semantic_family_drift(self):
        with self.assertRaises(ContextFitError):
            select_fitting_delivery(
                [candidate("a", "one", semantic_identity="x"), candidate("b", "two", semantic_identity="y")],
                lambda _delivery: FitReport(True),
            )
        drifted = FitCandidate("b", delivery("two", answer_spec="d" * 64), "same")
        with self.assertRaises(ContextFitError):
            select_fitting_delivery(
                [candidate("a", "one"), drifted],
                lambda _delivery: FitReport(True),
            )

    def test_rejects_complete_action_and_unbounded_candidate_sets(self):
        complete = FitCandidate("complete", delivery("", action="complete"), "same")
        with self.assertRaises(ContextFitError):
            select_fitting_delivery([complete], lambda _delivery: FitReport(True))
        too_many = [candidate(str(index), str(index)) for index in range(5)]
        with self.assertRaises(ContextFitError):
            select_fitting_delivery(too_many, lambda _delivery: FitReport(True))

    def test_rejects_contradictory_host_capacity_report(self):
        with self.assertRaises(ContextFitError):
            select_fitting_delivery(
                [candidate("one", "evidence")],
                lambda _delivery: FitReport(
                    True,
                    input_tokens=129,
                    input_capacity_tokens=128,
                    reserved_output_tokens=0,
                ),
            )
        with self.assertRaises(ContextFitError):
            select_fitting_delivery(
                [candidate("one", "evidence")],
                lambda _delivery: FitReport(
                    False,
                    input_tokens=100,
                    input_capacity_tokens=128,
                    reserved_output_tokens=8,
                ),
            )

    def test_host_measurement_exception_fails_closed(self):
        def boom(_delivery):
            raise RuntimeError("tokenizer unavailable")

        with self.assertRaisesRegex(ContextFitError, "tokenizer unavailable"):
            select_fitting_delivery([candidate("one", "evidence")], boom)


if __name__ == "__main__":
    unittest.main(verbosity=2)
