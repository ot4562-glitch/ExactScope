#!/usr/bin/env python3
"""Parity tests for the steady-state Bridge finalizer."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "tools", ROOT / "adapters/bridge"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from finalizer import FinalizerError, finalize_answer  # noqa: E402
from grounding_v1_surface import normalize_answer, parse_answer_object  # noqa: E402


class BridgeFinalizerTests(unittest.TestCase):
    def test_default_contract_parity_with_existing_surface_parser(self):
        samples = [
            '{"a":"Room 12"}',
            '{"a":null}',
            '{"a":""}',
            '{"a":"   "}',
            '{"a":"Room 12","x":1}',
            '{"a":"one","a":"two"}',
            'Room 12',
            '{"a":NaN}',
        ]
        for content in samples:
            with self.subTest(content=content):
                valid, value = parse_answer_object(content)
                expected = normalize_answer(valid, value)
                self.assertEqual(finalize_answer(content), expected)

    def test_typed_contract_parity(self):
        specs = [
            {"kind": "choice", "nullable": False, "choices": ["yes", "no"]},
            {"kind": "boolean", "nullable": True},
            {"kind": "integer", "nullable": False, "minimum": 1, "maximum": 3},
            {"kind": "number", "nullable": True, "minimum": 0, "maximum": 1.5},
        ]
        samples = ['{"a":"yes"}', '{"a":"other"}', '{"a":true}', '{"a":2}', '{"a":4}', '{"a":1.25}', '{"a":null}']
        for spec in specs:
            for content in samples:
                with self.subTest(spec=spec, content=content):
                    valid, value = parse_answer_object(content, spec)
                    self.assertEqual(finalize_answer(content, spec), normalize_answer(valid, value))

    def test_non_text_invocation_is_explicit_error(self):
        with self.assertRaises(FinalizerError):
            finalize_answer(None)  # type: ignore[arg-type]

    def test_module_contains_no_calibration_transport_or_runtime_dependency(self):
        source = (ROOT / "adapters/bridge/finalizer.py").read_text(encoding="utf-8")
        for token in (
            "import urllib",
            "import requests",
            "import onnxruntime",
            "import llama_cpp",
            "import litert",
            "from grounding_v1_surface",
            "import grounding_v1_surface",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
