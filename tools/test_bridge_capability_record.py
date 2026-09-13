#!/usr/bin/env python3
"""Tests for the Attach Profile cold-path capability record."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "adapters/bridge"
if str(BRIDGE) not in sys.path:
    sys.path.insert(0, str(BRIDGE))

from capability_record import (  # noqa: E402
    AttachCapabilityRecord,
    CapabilityRecordError,
    load_for_host,
    parse_capability_record,
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def record_dict(**overrides):
    value = AttachCapabilityRecord(
        host_profile_sha256=digest("qwen-host-profile"),
        identity_scope="persistent",
        answer_contract_id="answer-object-v4",
        output_surface_id="json-schema-v1",
        prompt_profile="no-policy",
        prompt_qualification_sha256=digest("hotpot-nq-prompt-qualification"),
        prefix_cache_mode="host-prefix",
        prefix_cache_parity_sha256=digest("qwen-prefix-cache-parity"),
        speculation_mode="off",
        speculation_parity_sha256=None,
    ).as_dict()
    value.update(overrides)
    return value


class AttachCapabilityRecordTests(unittest.TestCase):
    def test_qwen_like_record_is_canonical_deterministic_and_hot_load_requires_no_probe(self):
        record = parse_capability_record(record_dict())
        self.assertEqual(record.prompt_profile, "no-policy")
        self.assertEqual(record.prefix_cache_mode, "host-prefix")
        self.assertEqual(record.speculation_mode, "off")
        self.assertEqual(record.sha256(), parse_capability_record(record.as_dict()).sha256())
        loaded = load_for_host(
            record.canonical_bytes(),
            host_profile_sha256=digest("qwen-host-profile"),
            allow_session_scope=False,
        )
        self.assertEqual(loaded, record)

    def test_llama_like_record_can_keep_full_prompt_and_disable_unqualified_cache(self):
        value = record_dict(
            prompt_profile="full",
            prefix_cache_mode="off",
            prefix_cache_parity_sha256=None,
        )
        record = parse_capability_record(value)
        self.assertEqual(record.prompt_profile, "full")
        self.assertEqual(record.prefix_cache_mode, "off")

    def test_accelerator_mode_requires_exact_parity_evidence(self):
        with self.assertRaises(CapabilityRecordError):
            parse_capability_record(record_dict(prefix_cache_parity_sha256=None))
        with self.assertRaises(CapabilityRecordError):
            parse_capability_record(
                record_dict(
                    speculation_mode="ngram-simple",
                    speculation_parity_sha256=None,
                )
            )
        with self.assertRaises(CapabilityRecordError):
            parse_capability_record(
                record_dict(
                    speculation_mode="off",
                    speculation_parity_sha256=digest("should-not-exist"),
                )
            )

    def test_stale_host_identity_fails_closed(self):
        record = parse_capability_record(record_dict())
        with self.assertRaises(CapabilityRecordError):
            load_for_host(record.canonical_bytes(), host_profile_sha256=digest("different-host"))

    def test_session_scope_cannot_be_reused_when_persistence_is_required(self):
        record = parse_capability_record(record_dict(identity_scope="session"))
        with self.assertRaises(CapabilityRecordError):
            load_for_host(
                record.canonical_bytes(),
                host_profile_sha256=digest("qwen-host-profile"),
                allow_session_scope=False,
            )
        self.assertEqual(
            load_for_host(
                record.canonical_bytes(),
                host_profile_sha256=digest("qwen-host-profile"),
                allow_session_scope=True,
            ),
            record,
        )

    def test_record_shape_and_prompt_profile_are_closed(self):
        with self.assertRaises(CapabilityRecordError):
            parse_capability_record(record_dict(extra=True))
        with self.assertRaises(CapabilityRecordError):
            parse_capability_record(record_dict(prompt_profile="auto"))

    def test_module_is_cold_record_only_with_no_runtime_or_network_dependency(self):
        source = (BRIDGE / "capability_record.py").read_text(encoding="utf-8")
        for token in ("urllib", "requests", "onnxruntime", "llama_cpp", "litert", "subprocess"):
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
