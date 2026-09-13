#!/usr/bin/env python3
"""Focused tests for the v1.1 Harness Distillation vertical slice.

The fixture is synthetic compiler plumbing evidence, not a product benchmark claim.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from harness_distillation import (  # noqa: E402
    CandidatePolicy,
    DistillationError,
    FrozenSplit,
    HostQualification,
    Observation,
    calibration_policy_ids,
    choose_hot_route,
    compile_profile,
    load_profile,
    minimum_candidate_catalog,
    transfer_report,
)


def host(**overrides):
    value = dict(
        host_profile_digest="host-fixture-v1",
        context_fit_qualification_digest="fit-qualified",
        typed_contract_supported=True,
        native_constraint_surface_id="native-schema-v1",
        gxh_qualification_digest="gxh-qualified",
        zero_call_proof_supported=True,
        prefix_cache_mode="host-prefix",
        prefix_cache_parity_digest="cache-parity-qualified",
    )
    value.update(overrides)
    return HostQualification(**value)


def candidates(current_host=None):
    base = list(minimum_candidate_catalog(current_host or host()))
    base.append(
        CandidatePolicy(
            "fixed-max",
            "A+B+D+I",
            "full",
            "G+H",
            "J-proof-first+qualified-K",
            "integrated",
            False,
        )
    )
    return tuple(base)


CAL_SUCCESS = {
    "Base": {"c1", "c2"},
    "A": {"c1", "c2", "c3"},
    "B": {"c1", "c2", "c4"},
    "D": {"c1", "c2", "c6"},
    "A+B": {"c1", "c2", "c3", "c4", "c5"},
    "A+D": {"c1", "c2", "c3", "c6"},
    "B+D": {"c1", "c2", "c4", "c6", "c7"},
    "A+B+D": {"c1", "c2", "c3", "c4", "c5", "c6", "c7"},
    "D+I": {"c1", "c2", "c6", "c8"},
    "A+B+D+I": {"c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8"},
    "prompt_reduced": {"c1", "c2", "c6"},
    "prompt_full+I": {"c1", "c2", "c6", "c8"},
    "prompt_reduced+I": {"c1", "c2", "c5", "c6", "c8"},
    "G": {"c1", "c2", "c3"},
    "H": {"c1", "c2", "c4"},
    "G+H": {"c1", "c2", "c3", "c4", "c5"},
    "J": {"c1", "c2", "c3"},
    "K-off": {"c1", "c2"},
    "K-on": {"c1", "c2"},
    "integrated-K-off": {"c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8"},
    "integrated": {"c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8"},
    "fixed-max": {"c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8"},
}


HELD_SUCCESS = {
    policy_id: ({"h1", "h2", "h3", "h4"} if policy_id in {"integrated", "fixed-max", "A+B+D+I"} else {"h1"})
    for policy_id in CAL_SUCCESS
}


def observations(split, success_map, current_candidates=None):
    rows = []
    active = current_candidates or candidates()
    for policy in active:
        for index, item_id in enumerate(split.item_ids):
            if policy.policy_id in {"integrated", "integrated-K-off", "fixed-max", "J"}:
                model_calls = 0 if index < 2 else 1
            else:
                model_calls = 1
            if policy.policy_id == "integrated":
                prompt_tokens, latency, integration = 300, 70.0, 3
            elif policy.policy_id == "integrated-K-off":
                prompt_tokens, latency, integration = 300, 78.0, 3
            elif policy.policy_id == "fixed-max":
                prompt_tokens, latency, integration = 500, 100.0, 5
            elif policy.policy_id == "A+B+D+I":
                prompt_tokens, latency, integration = 450, 95.0, 1
            elif policy.policy_id == "prompt_reduced+I":
                prompt_tokens, latency, integration = 320, 80.0, 1
            elif policy.policy_id == "K-on":
                prompt_tokens, latency, integration = 500, 85.0, 1
            else:
                prompt_tokens, latency, integration = 500, 100.0, 0
            if model_calls == 0:
                prompt_tokens = 0
                completion_tokens = 0
                latency = 1.0
            else:
                completion_tokens = 8
            output_identity = None
            if policy.policy_id in {"K-off", "K-on"}:
                output_identity = f"stable-output-{item_id}"
            elif policy.policy_id in {"integrated-K-off", "integrated"}:
                output_identity = f"stable-integrated-{item_id}"
            rows.append(
                Observation(
                    item_id=item_id,
                    policy_id=policy.policy_id,
                    task_success=item_id in success_map[policy.policy_id],
                    false_grounding=False,
                    unsupported_answer=False,
                    strict_format_failure=False,
                    model_calls=model_calls,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    e2e_latency_ms=latency,
                    exactscope_cpu_ms=1.0,
                    peak_ram_bytes=4096,
                    distribution_bytes=1024,
                    integration_cost_units=integration,
                    output_identity=output_identity,
                )
            )
    return tuple(rows)


class HarnessDistillationTests(unittest.TestCase):
    def setUp(self):
        self.calibration = FrozenSplit("calibration-v1", tuple(f"c{i}" for i in range(1, 9)))
        self.held_out = FrozenSplit("held-out-v1", tuple(f"h{i}" for i in range(1, 5)))
        self.host = host()
        self.candidates = candidates(self.host)
        self.calibration_rows = observations(self.calibration, CAL_SUCCESS, self.candidates)
        self.held_out_rows = observations(self.held_out, HELD_SUCCESS, self.candidates)

    def compile(self, rows=None):
        return compile_profile(
            calibration=self.calibration,
            held_out=self.held_out,
            host=self.host,
            candidates=self.candidates,
            observations=rows or self.calibration_rows,
        )

    def test_frozen_split_normalizes_json_array_identity_to_tuple(self):
        split = FrozenSplit("json-roundtrip", ["a", "b"])
        self.assertEqual(split.item_ids, ("a", "b"))
        self.assertEqual(split.as_dict(), {"split_id": "json-roundtrip", "item_ids": ["a", "b"]})

    def test_catalog_preserves_required_interaction_bundles_and_qualification(self):
        by_id = {candidate.policy_id: candidate for candidate in self.candidates}
        self.assertEqual(tuple(policy_id for policy_id in REQUIRED_ORDER if policy_id in by_id), REQUIRED_ORDER)
        self.assertEqual(by_id["integrated"].evidence_bundle, "A+B+D+I")
        self.assertEqual(by_id["integrated"].model_bundle, "G+H")
        self.assertEqual(by_id["integrated"].cost_bundle, "J-proof-first+qualified-K")
        self.assertFalse(by_id["H"].selection_eligible)

    def test_capability_unavailable_candidates_are_not_required_or_executed(self):
        minimal_host = host(
            context_fit_qualification_digest=None,
            typed_contract_supported=False,
            native_constraint_surface_id=None,
            gxh_qualification_digest=None,
            zero_call_proof_supported=False,
            prefix_cache_mode="off",
            prefix_cache_parity_digest=None,
        )
        current_candidates = candidates(minimal_host)
        required = calibration_policy_ids(current_candidates)
        self.assertNotIn("D+I", required)
        self.assertNotIn("G", required)
        self.assertNotIn("H", required)
        self.assertNotIn("G+H", required)
        self.assertNotIn("J", required)
        self.assertNotIn("K-off", required)
        self.assertNotIn("K-on", required)
        self.assertIn("integrated", required)

        rows = tuple(
            row
            for row in observations(self.calibration, CAL_SUCCESS, current_candidates)
            if row.policy_id in required
        )
        result = compile_profile(
            calibration=self.calibration,
            held_out=self.held_out,
            host=minimal_host,
            candidates=current_candidates,
            observations=rows,
        )
        self.assertEqual(result.profile.selected_policy.policy_id, "integrated")
        self.assertEqual(result.profile.selected_policy.evidence_bundle, "A+B+D")
        self.assertEqual(result.profile.selected_policy.model_bundle, "plain")
        self.assertEqual(result.profile.selected_policy.cost_bundle, "generation")
        self.assertEqual(result.report["executed_policy_ids"], list(required))
        self.assertIn("G+H", result.report["skipped_policy_ids"])
        self.assertFalse(result.report["interactions"]["G+H"]["measured"])
        self.assertTrue(result.report["interactions"]["A+B"]["measured"])
        self.assertTrue(result.report["interactions"]["B+D"]["measured"])

    def test_fixed_max_reference_rejects_equal_count_success_swap(self):
        current_host = host(
            context_fit_qualification_digest=None,
            typed_contract_supported=False,
            native_constraint_surface_id=None,
            gxh_qualification_digest=None,
            zero_call_proof_supported=False,
            prefix_cache_mode="off",
            prefix_cache_parity_digest=None,
        )
        current_candidates = candidates(current_host)
        success_map = {
            policy.policy_id: {"c1", "c2"} for policy in current_candidates
        }
        success_map["integrated"] = {"c1", "c2", "c3"}
        success_map["prompt_reduced"] = {"c1", "c2", "c4"}
        rows = observations(self.calibration, success_map, current_candidates)
        result = compile_profile(
            calibration=self.calibration,
            held_out=self.held_out,
            host=current_host,
            candidates=current_candidates,
            observations=rows,
            fixed_max_policy_id="integrated",
        )
        self.assertEqual(result.profile.selected_policy.policy_id, "integrated")
        self.assertEqual(
            result.report["rejected_policy_ids"]["prompt_reduced"],
            "fixed-max-calibration-success-not-preserved",
        )
        paired = result.report["fixed_max_calibration_reference"]["prompt_reduced"]
        self.assertEqual(paired["gain_item_ids"], ["c4"])
        self.assertEqual(paired["loss_item_ids"], ["c3"])
        self.assertFalse(paired["preserves_reference_successes"])

    def test_cheaper_policy_can_win_when_it_preserves_fixed_max_successes(self):
        current_host = host(
            context_fit_qualification_digest=None,
            typed_contract_supported=False,
            native_constraint_surface_id=None,
            gxh_qualification_digest=None,
            zero_call_proof_supported=False,
            prefix_cache_mode="off",
            prefix_cache_parity_digest=None,
        )
        current_candidates = candidates(current_host)
        success_map = {
            policy.policy_id: {"c1", "c2"} for policy in current_candidates
        }
        success_map["integrated"] = {"c1", "c2", "c3"}
        success_map["prompt_reduced"] = {"c1", "c2", "c3"}
        rows = []
        for row in observations(self.calibration, success_map, current_candidates):
            if row.policy_id == "prompt_reduced":
                row = replace(
                    row,
                    model_calls=1,
                    prompt_tokens=200,
                    completion_tokens=8,
                    e2e_latency_ms=50.0,
                    integration_cost_units=1,
                )
            elif row.policy_id == "integrated":
                row = replace(
                    row,
                    model_calls=1,
                    prompt_tokens=400,
                    completion_tokens=8,
                    e2e_latency_ms=80.0,
                    integration_cost_units=2,
                )
            rows.append(row)
        result = compile_profile(
            calibration=self.calibration,
            held_out=self.held_out,
            host=current_host,
            candidates=current_candidates,
            observations=tuple(rows),
            fixed_max_policy_id="integrated",
        )
        self.assertEqual(result.profile.selected_policy.policy_id, "prompt_reduced")
        self.assertTrue(
            result.report["fixed_max_calibration_reference"]["prompt_reduced"]
            ["preserves_reference_successes"]
        )

    def test_compiler_selects_integrated_bundle_and_records_phase_transitions(self):
        result = self.compile()
        self.assertEqual(result.profile.selected_policy.policy_id, "integrated")
        self.assertIn("c5", result.report["interactions"]["A+B"]["phase_transition_item_ids"])
        self.assertIn("c7", result.report["interactions"]["B+D"]["phase_transition_item_ids"])
        self.assertIn("c5", result.report["interactions"]["prompt+I"]["phase_transition_item_ids"])
        self.assertIn("c5", result.report["interactions"]["G+H"]["phase_transition_item_ids"])
        self.assertTrue(result.report["k_output_parity_by_policy"]["integrated"])
        self.assertTrue(result.report["causal_checks"]["A+B+D"]["complete"])
        self.assertEqual(result.report["hot_path_calibration_model_calls"], 0)

    def test_profile_roundtrip_and_J_precedes_G_H_K(self):
        profile = self.compile().profile
        loaded = load_profile(profile.canonical_bytes(), host_profile_digest="host-fixture-v1")
        self.assertEqual(loaded.sha256(), profile.sha256())
        complete = choose_hot_route(loaded, True)
        self.assertEqual(complete["route"], "complete")
        self.assertEqual(complete["model_calls"], 0)
        self.assertIsNone(complete["model_bundle"])
        self.assertEqual(complete["prefix_cache_mode"], "off")
        generate = choose_hot_route(loaded, False)
        self.assertEqual(generate["route"], "generate")
        self.assertEqual(generate["model_bundle"], "G+H")
        self.assertEqual(generate["prefix_cache_mode"], "qualified")

    def test_held_out_report_does_not_reselect_profile(self):
        profile = self.compile().profile
        report = transfer_report(
            profile=profile,
            held_out=self.held_out,
            candidates=self.candidates,
            observations=self.held_out_rows,
            fixed_max_policy_id="fixed-max",
        )
        self.assertFalse(report["profile_reselected_on_held_out"])
        self.assertEqual(report["baseline"]["success_count"], 1)
        self.assertEqual(report["compiled"]["success_count"], 4)
        self.assertEqual(report["fixed_max"]["success_count"], 4)
        self.assertLess(report["compiled"]["prompt_tokens"], report["fixed_max"]["prompt_tokens"])

    def test_heldout_equal_count_success_swap_is_rejected_against_fixed_max(self):
        profile = self.compile().profile
        success_map = {policy.policy_id: {"h1"} for policy in self.candidates}
        success_map["integrated"] = {"h1", "h2"}
        success_map["fixed-max"] = {"h1", "h3"}
        report = transfer_report(
            profile=profile,
            held_out=self.held_out,
            candidates=self.candidates,
            observations=observations(self.held_out, success_map, self.candidates),
            fixed_max_policy_id="fixed-max",
        )
        self.assertEqual(report["compiled"]["success_count"], 2)
        self.assertEqual(report["fixed_max"]["success_count"], 2)
        self.assertFalse(report["qualification"]["passed"])
        self.assertIn(
            "compiled-policy-lost-fixed-max-heldout-success",
            report["qualification"]["rejection_reasons"],
        )
        paired = report["fixed_max_heldout_reference"]
        self.assertEqual(paired["gain_item_ids"], ["h2"])
        self.assertEqual(paired["loss_item_ids"], ["h3"])

    def test_K_and_GH_fail_closed_without_qualification(self):
        rows = list(self.calibration_rows)
        for index, row in enumerate(rows):
            if row.policy_id == "integrated" and row.item_id == "c8":
                rows[index] = replace(row, output_identity="parity-mismatch")
                break
        result = self.compile(tuple(rows))
        self.assertEqual(
            result.report["rejected_policy_ids"]["integrated"],
            "K-output-parity-not-observed-on-selected-policy",
        )
        self.assertEqual(result.profile.selected_policy.policy_id, "integrated-K-off")

        no_pair_proof = host(gxh_qualification_digest=None)
        by_id = {candidate.policy_id: candidate for candidate in candidates(no_pair_proof)}
        self.assertFalse(by_id["G+H"].selection_eligible)
        self.assertEqual(by_id["integrated"].model_bundle, "G")

    def test_split_overlap_and_stale_host_fail_closed(self):
        overlap = FrozenSplit("bad-held-out", ("c8", "h1"))
        with self.assertRaises(DistillationError):
            compile_profile(
                calibration=self.calibration,
                held_out=overlap,
                host=self.host,
                candidates=self.candidates,
                observations=self.calibration_rows,
            )
        profile = self.compile().profile
        with self.assertRaises(DistillationError):
            load_profile(profile.canonical_bytes(), host_profile_digest="different-host")


REQUIRED_ORDER = (
    "Base", "A", "B", "D", "A+B", "B+D", "A+B+D", "D+I", "A+B+D+I",
    "prompt_full+I", "prompt_reduced+I", "G", "H", "G+H", "J", "K-off", "K-on", "integrated",
)


if __name__ == "__main__":
    unittest.main(verbosity=2)
