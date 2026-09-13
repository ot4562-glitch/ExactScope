#!/usr/bin/env python3
"""Dependency-free control-flow tests for the LiteRT-LM Bridge target."""
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

from delivery import Delivery, Message, TargetState  # noqa: E402

ADAPTER = ROOT / "adapters/bridge/litert-lm/bridge.py"
spec = importlib.util.spec_from_file_location("exactscope_litert_bridge", ADAPTER)
assert spec is not None and spec.loader is not None
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class FakeConversation:
    def __init__(self, owner):
        self.owner = owner

    def __enter__(self):
        self.owner.calls.append(("conversation_enter",))
        return self

    def __exit__(self, *args):
        self.owner.calls.append(("conversation_exit",))

    def send_message(self, message):
        self.owner.calls.append(("send_message", message))
        return {"role": "assistant", "content": [{"type": "text", "text": "OK"}]}


class FakeEngine:
    owner = None

    def __init__(self, **kwargs):
        assert self.owner is not None
        self.owner.calls.append(("Engine", kwargs))

    def __enter__(self):
        self.owner.calls.append(("engine_enter",))
        return self

    def __exit__(self, *args):
        self.owner.calls.append(("engine_exit",))

    def create_conversation(self, **kwargs):
        self.owner.calls.append(("create_conversation", kwargs))
        return FakeConversation(self.owner)


class FakeLiteRt:
    calls = []
    Engine = FakeEngine


FakeEngine.owner = FakeLiteRt


def delivery(action: str) -> Delivery:
    if action == "complete":
        return Delivery(
            action="complete",
            route="host-grounded-scalar",
            profile_sha256="a" * 64,
            states=(TargetState("device:x", "authoritative", "grounded"),),
            reply={"a": "17 cm", "disposition": "answer"},
            messages=(),
        )
    return Delivery(
        action="generate",
        route="grounded-context",
        profile_sha256="a" * 64,
        states=(TargetState("reference:desk", "authoritative", "grounded"),),
        reply=None,
        messages=(
            Message("system", "answer from approved evidence"),
            Message("user", "Where? Evidence: Room 12"),
        ),
    )


class LiteRtBridgeTests(unittest.TestCase):
    def setUp(self):
        FakeLiteRt.calls.clear()

    def test_complete_returns_before_engine_access(self):
        result = bridge.run_delivery(
            delivery("complete"),
            model_path=None,
            litert_module=FakeLiteRt,
        )
        self.assertFalse(result["model_called"])
        self.assertEqual(result["reply"]["a"], "17 cm")
        self.assertEqual(FakeLiteRt.calls, [])

    def test_generate_maps_history_and_last_message_without_grounding_logic(self):
        result = bridge.run_delivery(
            delivery("generate"),
            model_path=Path("fake.litertlm"),
            max_output_tokens=8,
            litert_module=FakeLiteRt,
        )
        self.assertTrue(result["model_called"])
        self.assertEqual(result["raw_generation"], "OK")
        create = next(call[1] for call in FakeLiteRt.calls if call[0] == "create_conversation")
        self.assertEqual(create["max_output_tokens"], 8)
        self.assertFalse(create["automatic_tool_calling"])
        self.assertEqual(create["messages"][0]["role"], "system")
        self.assertIn("approved evidence", create["messages"][0]["content"][0]["text"])
        sent = next(call[1] for call in FakeLiteRt.calls if call[0] == "send_message")
        self.assertEqual(sent["role"], "user")
        self.assertIn("Room 12", sent["content"][0]["text"])

    def test_generation_requires_final_user_message(self):
        broken = Delivery(
            action="generate",
            route="grounded-context",
            profile_sha256="a" * 64,
            states=(),
            reply=None,
            messages=(Message("system", "only system"),),
        )
        with self.assertRaises(bridge.LiteRtBridgeError):
            bridge.run_delivery(
                broken,
                model_path=Path("fake.litertlm"),
                litert_module=FakeLiteRt,
            )
        self.assertEqual(FakeLiteRt.calls, [])


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    unittest.main(verbosity=2)
