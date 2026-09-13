#!/usr/bin/env python3
"""Tests for the first product-facing Harness Distillation calibration CLI."""
from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from exactscope_calibrate import (  # noqa: E402
    CALIBRATION_REPORT_FILE,
    CANDIDATE_PROFILE_FILE,
    CONTEXT_FILE,
    HELDOUT_REPORT_FILE,
    QUALIFIED_PROFILE_FILE,
    build_compile_bundle,
    build_qualification_bundle,
    verify_bundle,
    write_immutable_bundle,
)
from harness_distillation import (  # noqa: E402
    DistillationObjective,
    FrozenSplit,
    HostQualification,
    Observation,
    canonical_bytes,
    minimum_candidate_catalog,
)


def host() -> HostQualification:
    return HostQualification(
        host_profile_digest="host-fixture-v1",
        context_fit_qualification_digest="fit-qualified",
        typed_contract_supported=True,
        native_constraint_surface_id="native-schema-v1",
        gxh_qualification_digest="gxh-qualified",
        zero_call_proof_supported=True,
        prefix_cache_mode="host-prefix",
        prefix_cache_parity_digest="cache-parity-qualified",
    )


def observation_rows(split: FrozenSplit, *, heldout: bool = False, fail_compiled: bool = False):
    current = minimum_candidate_catalog(host())
    rows = []
    selected_ids = {"Base", "integrated"} if heldout else {candidate.policy_id for candidate in current}
    for candidate in current:
        if candidate.policy_id not in selected_ids:
            continue
        for item_id in split.item_ids:
            if candidate.policy_id == "Base":
                success = item_id in {split.item_ids[0]}
            elif candidate.policy_id == "integrated":
                success = False if fail_compiled else True
            else:
                success = item_id in {split.item_ids[0]}
            output_identity = None
            if candidate.policy_id in {"K-off", "K-on"}:
                output_identity = f"k-{item_id}"
            elif candidate.policy_id in {"integrated-K-off", "integrated"}:
                output_identity = f"integrated-{item_id}"
            rows.append(
                Observation(
                    item_id=item_id,
                    policy_id=candidate.policy_id,
                    task_success=success,
                    false_grounding=False,
                    unsupported_answer=False,
                    strict_format_failure=False,
                    model_calls=1,
                    prompt_tokens=300 if candidate.policy_id == "integrated" else 500,
                    completion_tokens=8,
                    e2e_latency_ms=70.0 if candidate.policy_id == "integrated" else 100.0,
                    exactscope_cpu_ms=1.0,
                    peak_ram_bytes=4096,
                    distribution_bytes=1024,
                    integration_cost_units=2 if candidate.policy_id == "integrated" else 3,
                    output_identity=output_identity,
                )
            )
    return tuple(rows)


def compile_request(calibration: FrozenSplit, held_out: FrozenSplit) -> bytes:
    value = {
        "format": "exactscope.harness-calibration-request",
        "format_version": "0.1",
        "host_qualification": host().as_dict(),
        "calibration_split": calibration.as_dict(),
        "held_out_split": held_out.as_dict(),
        "objective": DistillationObjective().as_dict(),
        "reduced_prompt_profile": "no-policy",
        "baseline_policy_id": "Base",
        "fixed_max_policy_id": "integrated",
        "observations": [asdict(row) for row in observation_rows(calibration)],
    }
    return canonical_bytes(value)


def heldout_request(held_out: FrozenSplit, *, fail_compiled: bool = False) -> bytes:
    value = {
        "format": "exactscope.harness-heldout-request",
        "format_version": "0.1",
        "held_out_split": held_out.as_dict(),
        "observations": [
            asdict(row)
            for row in observation_rows(held_out, heldout=True, fail_compiled=fail_compiled)
        ],
    }
    return canonical_bytes(value)


class ExactScopeCalibrateTests(unittest.TestCase):
    def setUp(self):
        self.calibration = FrozenSplit("calibration-v1", ("c1", "c2", "c3"))
        self.held_out = FrozenSplit("held-out-v1", ("h1", "h2"))

    def test_compile_then_qualify_emits_deployable_profile_without_heldout_reselection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            compile_dir = root / "compile"
            qualified_dir = root / "qualified"
            write_immutable_bundle(build_compile_bundle(compile_request(self.calibration, self.held_out)), compile_dir)
            compile_manifest = verify_bundle(compile_dir)
            self.assertEqual(compile_manifest["stage"], "compile")
            self.assertFalse(compile_manifest["deployment_qualified"])
            self.assertTrue((compile_dir / CANDIDATE_PROFILE_FILE).is_file())
            self.assertTrue((compile_dir / CALIBRATION_REPORT_FILE).is_file())
            self.assertTrue((compile_dir / CONTEXT_FILE).is_file())

            payloads, qualified = build_qualification_bundle(
                compile_dir, heldout_request(self.held_out)
            )
            self.assertTrue(qualified)
            write_immutable_bundle(payloads, qualified_dir)
            manifest = verify_bundle(qualified_dir)
            self.assertTrue(manifest["deployment_qualified"])
            self.assertEqual(manifest["profile_file"], QUALIFIED_PROFILE_FILE)
            self.assertTrue((qualified_dir / QUALIFIED_PROFILE_FILE).is_file())
            self.assertFalse((qualified_dir / CANDIDATE_PROFILE_FILE).exists())

            transfer = json.loads((qualified_dir / HELDOUT_REPORT_FILE).read_text(encoding="utf-8"))
            self.assertTrue(transfer["qualification"]["passed"])
            self.assertFalse(transfer["profile_reselected_on_held_out"])
            self.assertEqual(transfer["held_out_policy_count"], 2)
            self.assertEqual(transfer["compiled_policy_id"], "integrated")

    def test_failed_transfer_never_emits_deployable_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            compile_dir = root / "compile"
            rejected_dir = root / "rejected"
            write_immutable_bundle(build_compile_bundle(compile_request(self.calibration, self.held_out)), compile_dir)
            payloads, qualified = build_qualification_bundle(
                compile_dir, heldout_request(self.held_out, fail_compiled=True)
            )
            self.assertFalse(qualified)
            write_immutable_bundle(payloads, rejected_dir)
            manifest = verify_bundle(rejected_dir)
            self.assertFalse(manifest["deployment_qualified"])
            self.assertEqual(manifest["profile_file"], CANDIDATE_PROFILE_FILE)
            self.assertFalse((rejected_dir / QUALIFIED_PROFILE_FILE).exists())
            transfer = json.loads((rejected_dir / HELDOUT_REPORT_FILE).read_text(encoding="utf-8"))
            self.assertFalse(transfer["qualification"]["passed"])
            self.assertIn(
                "compiled-policy-failed-heldout-safety-or-model-call-gate",
                transfer["qualification"]["rejection_reasons"],
            )

    def test_frozen_heldout_split_cannot_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            compile_dir = Path(tmp) / "compile"
            write_immutable_bundle(build_compile_bundle(compile_request(self.calibration, self.held_out)), compile_dir)
            different = FrozenSplit("different", ("h3", "h4"))
            with self.assertRaisesRegex(ValueError, "held-out split differs"):
                build_qualification_bundle(compile_dir, heldout_request(different))


if __name__ == "__main__":
    unittest.main(verbosity=2)
