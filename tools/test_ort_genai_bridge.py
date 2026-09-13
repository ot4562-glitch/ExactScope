#!/usr/bin/env python3
"""Dependency-free control-flow tests for the ONNX Runtime GenAI Bridge target."""
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

ADAPTER = ROOT / "adapters/bridge/onnxruntime-genai/bridge.py"
spec = importlib.util.spec_from_file_location("exactscope_ort_genai_bridge", ADAPTER)
assert spec is not None and spec.loader is not None
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class FakeOrt:
    calls: list[tuple] = []

    class Model:
        def __init__(self, path):
            FakeOrt.calls.append(("Model", path))

    class Tokenizer:
        def __init__(self, model):
            FakeOrt.calls.append(("Tokenizer", model))

        def apply_chat_template(self, **kwargs):
            FakeOrt.calls.append(("apply_chat_template", kwargs["messages"]))
            return "templated:" + kwargs["messages"]

        def encode(self, prompt):
            FakeOrt.calls.append(("encode", prompt))
            return [11, 12, 13]

        def decode(self, tokens):
            FakeOrt.calls.append(("decode", tuple(tokens)))
            return "OK"

    class GeneratorParams:
        def __init__(self, model):
            self.options = {}
            FakeOrt.calls.append(("GeneratorParams", model))

        def set_search_options(self, **kwargs):
            self.options.update(kwargs)
            FakeOrt.calls.append(("set_search_options", kwargs))

    class Generator:
        def __init__(self, model, params):
            self.sequence = []
            self.done = False
            FakeOrt.calls.append(("Generator", model, params))

        def append_tokens(self, tokens):
            self.sequence.extend(tokens)
            FakeOrt.calls.append(("append_tokens", tuple(tokens)))

        def token_count(self):
            return len(self.sequence)

        def is_done(self):
            return self.done

        def generate_next_token(self):
            self.sequence.extend([77, 78])
            self.done = True
            FakeOrt.calls.append(("generate_next_token",))

        def get_sequence(self, index):
            assert index == 0
            return self.sequence


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
            Message("user", "Where?\n\nEvidence JSON: Room 12"),
        ),
    )


class OrtGenAIBridgeTests(unittest.TestCase):
    def setUp(self):
        FakeOrt.calls.clear()

    def test_complete_returns_before_any_ort_access(self):
        result = bridge.run_delivery(
            delivery("complete"),
            model_path=None,
            ort_module=object(),
        )
        self.assertFalse(result["model_called"])
        self.assertEqual(result["reply"]["a"], "17 cm")
        self.assertEqual(FakeOrt.calls, [])

    def test_generate_passes_only_delivery_messages_to_ort_generation(self):
        result = bridge.run_delivery(
            delivery("generate"),
            model_path=Path("fake-model"),
            max_new_tokens=8,
            prompt_mode="chat-template",
            ort_module=FakeOrt,
        )
        self.assertTrue(result["model_called"])
        self.assertEqual(result["raw_generation"], "OK")
        self.assertNotIn("reply", result)
        names = [entry[0] for entry in FakeOrt.calls]
        self.assertEqual(
            names,
            [
                "Model",
                "Tokenizer",
                "apply_chat_template",
                "encode",
                "GeneratorParams",
                "set_search_options",
                "Generator",
                "append_tokens",
                "generate_next_token",
                "decode",
            ],
        )
        rendered = next(call[1] for call in FakeOrt.calls if call[0] == "apply_chat_template")
        self.assertIn("approved evidence", rendered)
        self.assertIn("Room 12", rendered)
        options = next(call[1] for call in FakeOrt.calls if call[0] == "set_search_options")
        self.assertEqual(options, {"max_length": 11, "do_sample": False, "batch_size": 1})

    def test_plain_prompt_is_explicit_not_a_silent_chat_template_fallback(self):
        bridge.run_delivery(
            delivery("generate"),
            model_path=Path("fake-model"),
            max_new_tokens=1,
            prompt_mode="plain",
            ort_module=FakeOrt,
        )
        self.assertNotIn("apply_chat_template", [entry[0] for entry in FakeOrt.calls])
        prompt = next(call[1] for call in FakeOrt.calls if call[0] == "encode")
        self.assertIn("system: answer from approved evidence", prompt)
        self.assertTrue(prompt.endswith("assistant:"))


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    unittest.main(verbosity=2)
