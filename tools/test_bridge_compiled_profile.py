#!/usr/bin/env python3
"""Tests for consuming a compiled Amplifier Profile on the existing prepared path."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
BRIDGE = ROOT / "adapters/bridge"
for path in (TOOLS, BRIDGE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import grounding_engine as engine  # noqa: E402
from compiled_profile import CompiledProfileError, prepare_from_profile  # noqa: E402
from harness_distillation import AmplifierProfile, CandidatePolicy  # noqa: E402

PROFILE_DIR = ROOT / "grounding/reference-profile-v0.1"


def generation_profile():
    return AmplifierProfile(
        host_profile_digest="host-fixture-v1",
        host_qualification_digest="host-qualification-v1",
        context_fit_qualification_digest=None,
        gxh_qualification_digest=None,
        native_constraint_surface_id=None,
        prefix_cache_mode="off",
        prefix_cache_parity_digest=None,
        calibration_split_digest="calibration-split-v1",
        calibration_evidence_digest="calibration-evidence-v1",
        selected_policy=CandidatePolicy(
            "prompt_reduced",
            "D",
            "no-policy",
            "plain",
            "generation",
            "leave-one-out",
        ),
    )


def integrated_profile(prompt_profile="no-policy"):
    return AmplifierProfile(
        host_profile_digest="host-fixture-v1",
        host_qualification_digest="host-qualification-v1",
        context_fit_qualification_digest="fit-qualification-v1",
        gxh_qualification_digest="gxh-qualification-v1",
        native_constraint_surface_id="json-schema-v1",
        prefix_cache_mode="host-prefix",
        prefix_cache_parity_digest="cache-parity-v1",
        calibration_split_digest="calibration-split-v1",
        calibration_evidence_digest="calibration-evidence-v1",
        selected_policy=CandidatePolicy(
            "integrated",
            "A+B+D+I",
            prompt_profile,
            "G+H",
            "J-proof-first+qualified-K",
            "integrated",
        ),
    )


class FakePrepared:
    def plan(self, *, question, **kwargs):
        generation = question != "proof"
        return {
            "model_called": generation,
            "amplifier": {
                "prefix_cache_eligible": generation,
                "prefix_cache_key": "prefix-key" if generation else None,
            },
        }

    def finalize_generation(self, text):
        return {"finalized": text}


class FakeSession:
    def __init__(self):
        self.kwargs = None

    def prepare(self, **kwargs):
        self.kwargs = kwargs
        return FakePrepared()


class CompiledProfileBridgeTests(unittest.TestCase):
    def test_profile_binds_existing_prepare_path_and_exposes_host_owned_actions(self):
        session = FakeSession()
        execution = prepare_from_profile(
            session=session,
            profile=integrated_profile().canonical_bytes(),
            host_profile_digest="host-fixture-v1",
            host_qualification_digest="host-qualification-v1",
            contract="answer-object-v3",
            answer_spec={"kind": "text", "nullable": False},
        )
        self.assertEqual(session.kwargs["prompt_profile"], "no-policy")
        self.assertEqual(session.kwargs["corpus_top_k"], 12)
        self.assertTrue(session.kwargs["proof_first"])
        generated = execution.plan(
            question="generate",
            qid="q1",
            retrieval_query="retrieval form",
            ranked_hits=[{"id": "x"}],
            context_fit=lambda messages: True,
        )
        self.assertEqual(generated.host_hints["native_constraint_surface_id"], "json-schema-v1")
        self.assertEqual(generated.host_hints["native_constraint_qualification_digest"], "gxh-qualification-v1")
        self.assertEqual(generated.host_hints["prefix_cache_mode"], "host-prefix")
        self.assertEqual(generated.host_hints["prefix_cache_parity_digest"], "cache-parity-v1")
        self.assertEqual(generated.host_hints["prefix_cache_key"], "prefix-key")

        completed = execution.plan(
            question="proof",
            qid="q2",
            retrieval_query="retrieval form",
            ranked_hits=[{"id": "x"}],
            context_fit=lambda messages: True,
        )
        self.assertTrue(completed.host_hints["generation_eliminated"])
        self.assertIsNone(completed.host_hints["native_constraint_surface_id"])
        self.assertEqual(completed.host_hints["prefix_cache_mode"], "off")
        self.assertEqual(execution.finalize_generation("raw"), {"finalized": "raw"})

    def test_generation_only_profile_disables_optional_proof_completion(self):
        session = FakeSession()
        execution = prepare_from_profile(
            session=session,
            profile=generation_profile(),
            host_profile_digest="host-fixture-v1",
            host_qualification_digest="host-qualification-v1",
            contract="answer-object-v3",
        )
        self.assertEqual(session.kwargs["corpus_top_k"], 4)
        self.assertEqual(session.kwargs["prompt_profile"], "no-policy")
        self.assertFalse(session.kwargs["proof_first"])
        self.assertEqual(execution.profile.selected_policy.policy_id, "prompt_reduced")

    def test_real_generation_profile_does_not_take_grounded_scalar_J_shortcut(self):
        session = engine.GroundingSession.open(PROFILE_DIR)
        execution = prepare_from_profile(
            session=session,
            profile=generation_profile(),
            host_profile_digest="host-fixture-v1",
            host_qualification_digest="host-qualification-v1",
            contract="answer-object-v3",
            answer_choices=["17 cm", "20 cm"],
        )
        frame = {
            "groups": [{
                "target_key": "device:clearance",
                "target_label": "Device clearance",
                "authority": "authoritative",
                "state": "grounded",
                "items": [{"content": {"kind": "scalar", "type": "integer", "value": "17", "unit": "cm"}}],
            }]
        }
        with patch.object(engine, "run_grounding_frame", return_value={"frame": frame, "audit": {}}):
            planned = execution.plan(question="Choose the exact clearance value.", qid="no-j")
        self.assertTrue(planned.plan["model_called"])
        self.assertEqual(planned.plan["route"], "grounded-context")
        self.assertFalse(planned.host_hints["generation_eliminated"])

    def test_selected_A_and_I_fail_closed_when_host_inputs_are_missing(self):
        execution = prepare_from_profile(
            session=FakeSession(),
            profile=integrated_profile(),
            host_profile_digest="host-fixture-v1",
            host_qualification_digest="host-qualification-v1",
            contract="answer-object-v3",
            answer_spec={"kind": "text", "nullable": False},
        )
        with self.assertRaises(CompiledProfileError):
            execution.plan(question="generate", qid="q", ranked_hits=[{"id": "x"}], context_fit=lambda m: True)
        with self.assertRaises(CompiledProfileError):
            execution.plan(
                question="generate", qid="q", retrieval_query="r", ranked_hits=[{"id": "x"}]
            )

    def test_G_compact_native_and_current_local_I_limit_fail_closed(self):
        with self.assertRaises(CompiledProfileError):
            prepare_from_profile(
                session=FakeSession(),
                profile=integrated_profile(),
                host_profile_digest="host-fixture-v1",
                host_qualification_digest="host-qualification-v1",
                contract="answer-object-v3",
            )
        with self.assertRaises(CompiledProfileError):
            prepare_from_profile(
                session=FakeSession(),
                profile=integrated_profile("compact-native"),
                host_profile_digest="host-fixture-v1",
                host_qualification_digest="host-qualification-v1",
                contract="answer-object-v3",
                answer_spec={"kind": "text", "nullable": False},
            )
        with self.assertRaises(CompiledProfileError):
            prepare_from_profile(
                session=FakeSession(),
                profile=integrated_profile(),
                host_profile_digest="host-fixture-v1",
                host_qualification_digest="host-qualification-v1",
                contract="answer-object-v3",
                corpus_index=Path("unused.json"),
                answer_spec={"kind": "text", "nullable": False},
            )

    def test_real_session_uses_reduced_prompt_and_existing_strict_finalizer(self):
        session = engine.GroundingSession.open(PROFILE_DIR)
        execution = prepare_from_profile(
            session=session,
            profile=integrated_profile().canonical_bytes(),
            host_profile_digest="host-fixture-v1",
            host_qualification_digest="host-qualification-v1",
            contract="answer-object-v3",
            answer_spec={"kind": "integer", "nullable": False, "minimum": 0, "maximum": 100},
        )
        prepared = execution.prepared
        self.assertEqual(prepared.prompt_profile, "no-policy")
        messages = engine._prepared_messages(prepared, "Question?", b"Evidence", policy=True)
        self.assertEqual(messages[0]["content"], prepared.system_plain)
        self.assertNotEqual(prepared.system_plain, prepared.system_with_policy)
        self.assertEqual(
            execution.finalize_generation('{"a":42}'),
            {"a": 42, "disposition": "answer"},
        )
        self.assertIsNone(execution.finalize_generation('{"a":101}'))

    def test_stale_host_identity_is_rejected(self):
        with self.assertRaises(CompiledProfileError):
            prepare_from_profile(
                session=FakeSession(),
                profile=integrated_profile().canonical_bytes(),
                host_profile_digest="other-host",
                host_qualification_digest="host-qualification-v1",
                contract="answer-object-v3",
                answer_spec={"kind": "text", "nullable": False},
            )
        with self.assertRaises(CompiledProfileError):
            prepare_from_profile(
                session=FakeSession(),
                profile=integrated_profile().canonical_bytes(),
                host_profile_digest="host-fixture-v1",
                host_qualification_digest="stale-qualification",
                contract="answer-object-v3",
                answer_spec={"kind": "text", "nullable": False},
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
