#!/usr/bin/env python3
"""No-inference tests for the experimental ExactScope Bridge delivery boundary."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "adapters/bridge"
for path in (BRIDGE, ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from delivery import BridgeContractError, from_v11_plan  # noqa: E402
from exactscope_v11 import finalize_generation, prepare_delivery  # noqa: E402

PROFILE = ROOT / "grounding/reference-profile-v0.1"
DIGEST = "a" * 64


def plan(*, model_called: bool, groups: list[dict], reply=None, messages=None):
    return {
        "route": "test-route",
        "model_called": model_called,
        "reply": reply,
        "messages": messages,
        "frame": {"groups": groups},
        "audit": {},
        "profile_sha256": DIGEST,
        "amplifier": {
            "answer_spec_sha256": "b" * 64,
            "prefix_cache_key": "c" * 64 if model_called else None,
        },
    }


class ExactScopeBridgeTests(unittest.TestCase):
    def test_real_v11_grounded_plan_collapses_to_generation_delivery(self):
        delivery = prepare_delivery(profile_dir=PROFILE, question="Where is the help desk?")
        self.assertEqual(delivery.action, "generate")
        self.assertEqual(delivery.route, "grounded-context")
        self.assertEqual(
            [(item.target_key, item.authority, item.state) for item in delivery.states],
            [
                ("reference:desk", "authoritative", "grounded"),
                ("reference:desk-tip", "supplemental", "grounded"),
            ],
        )
        self.assertEqual(len(delivery.messages), 2)
        self.assertIn("Room 12", delivery.messages[1].content)

    def test_contract_preserves_all_grounding_states_without_interpreting_them(self):
        states = ["grounded", "none", "ambiguous", "conflict", "unavailable"]
        groups = [
            {"target_key": f"t:{state}", "authority": "authoritative", "state": state}
            for state in states
        ]
        delivery = from_v11_plan(plan(
            model_called=True,
            groups=groups,
            messages=[{"role": "system", "content": "s"}, {"role": "user", "content": "u"}],
        ))
        self.assertEqual([item.state for item in delivery.states], states)
        self.assertEqual(delivery.action, "generate")

    def test_deterministic_answer_never_carries_generation_payload(self):
        delivery = from_v11_plan(plan(
            model_called=False,
            groups=[{"target_key": "device:value", "authority": "authoritative", "state": "grounded"}],
            reply={"a": "17 cm", "disposition": "answer"},
            messages=None,
        ))
        self.assertEqual(delivery.action, "complete")
        self.assertEqual(delivery.reply, {"a": "17 cm", "disposition": "answer"})
        self.assertEqual(delivery.messages, ())

    def test_unresolved_host_dispositions_remain_exact(self):
        cases = {
            "none": "abstain",
            "ambiguous": "clarify",
            "conflict": "conflict",
            "unavailable": "unavailable",
        }
        for state, disposition in cases.items():
            with self.subTest(state=state):
                delivery = from_v11_plan(plan(
                    model_called=False,
                    groups=[{"target_key": f"t:{state}", "authority": "authoritative", "state": state}],
                    reply={"a": None, "disposition": disposition},
                    messages=None,
                ))
                self.assertEqual(delivery.states[0].state, state)
                self.assertEqual(delivery.reply["disposition"], disposition)

    def test_generation_finalization_is_strict_and_never_repairs(self):
        self.assertEqual(
            finalize_generation('{"a":"Room 12"}'),
            {"a": "Room 12", "disposition": "answer"},
        )
        self.assertIsNone(finalize_generation("Room 12"))
        self.assertIsNone(finalize_generation('{"a":"Room 12","extra":true}'))

    def test_generation_requires_messages_and_complete_requires_reply(self):
        with self.assertRaises(BridgeContractError):
            from_v11_plan(plan(model_called=True, groups=[], messages=None))
        with self.assertRaises(BridgeContractError):
            from_v11_plan(plan(model_called=False, groups=[], reply=None, messages=None))
        with self.assertRaises(BridgeContractError):
            from_v11_plan(plan(
                model_called=False,
                groups=[],
                reply={"a": None, "disposition": "abstain"},
                messages=[{"role": "user", "content": "must not exist"}],
            ))


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    unittest.main(verbosity=2)
