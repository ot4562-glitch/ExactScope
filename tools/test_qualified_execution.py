#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import qualified_execution as qe  # noqa: E402
from grounding_canonical import canonical_bytes, canonical_sha256  # noqa: E402


H = "0" * 64
H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64
H4 = "4" * 64


class QualifiedExecutionTests(unittest.TestCase):
    def binding(self):
        return {
            "request_id": "req-1",
            "evidence_snapshot_sha256": H1,
            "rendered_request_sha256": H2,
            "execution_settings_sha256": H3,
        }

    def workload(self):
        return {
            "v": 1,
            "format": "exactscope.workload-contract",
            "format_version": "0.1",
            "workload_id": "docqa-policy-v1",
            "workload_revision": "r1",
            "population_identity": "population-r1",
            "runtime_obligations": [
                {
                    "obligation_id": "citation-membership",
                    "kind": "citation-membership",
                    "rule_id": "citation-rule-v1",
                    "failure_reason": "citation-outside-authorized-set",
                },
                {
                    "obligation_id": "output-schema",
                    "kind": "output-schema",
                    "rule_id": "answer-object-v4",
                    "failure_reason": "output-contract-failed",
                },
            ],
            "empirical_requirements": [
                {
                    "requirement_id": "accuracy-min",
                    "metric_id": "task-accuracy",
                    "direction": "min",
                    "threshold": 8000,
                    "unit": "basis-points",
                    "mandatory": True,
                },
                {
                    "requirement_id": "unsupported-max",
                    "metric_id": "unsupported-answer-rate",
                    "direction": "max",
                    "threshold": 200,
                    "unit": "basis-points",
                    "mandatory": True,
                },
            ],
            "answer_contract_id": "answer-object-v4",
            "evidence_policy_id": "bounded-authorized-evidence-v1",
            "economic_model_id": "enterprise-economics-v1",
            "invalidation_policy": {
                "unknown_change": "full-requalification",
                "targeted_requalification_allowed": True,
                "dependency_rule_id": "docqa-dependency-rule-v1",
                "nonbehavioral_dependency_ids": [],
                "targeted_dependency_ids": ["runtime"],
            },
        }

    def host(self, *, provider=False):
        if provider:
            return {
                "v": 1,
                "format": "exactscope.host-capability-manifest",
                "format_version": "0.1",
                "host_id": "frontier-provider-host",
                "supported_checks": self.supported_checks(),
                "qualification_scope": "provider-observable",
                "dependencies": [
                    {
                        "dependency_id": "model",
                        "kind": "model",
                        "identity": "provider-model-tier-a",
                        "assurance": "unknown",
                        "valid_until_epoch_s": 2000,
                        "observation_policy_id": "provider-observation-v1",
                    }
                ],
                "capabilities": [
                    {
                        "capability_id": "structured-output",
                        "binding_id": "json-schema",
                        "assurance": "provider-guaranteed",
                    }
                ],
                "exact_fit_supported": False,
                "max_model_calls": 1,
                "fallback_owner": "host",
            }
        return {
            "v": 1,
            "format": "exactscope.host-capability-manifest",
            "format_version": "0.1",
            "host_id": "local-qwen-host",
            "supported_checks": self.supported_checks(),
            "qualification_scope": "inspectable-pinned",
            "dependencies": [
                {
                    "dependency_id": "model",
                    "kind": "model",
                    "identity": "qwen-model-sha",
                    "assurance": "pinned",
                    "valid_until_epoch_s": None,
                    "observation_policy_id": None,
                },
                {
                    "dependency_id": "runtime",
                    "kind": "runtime",
                    "identity": "llama-runtime-sha",
                    "assurance": "pinned",
                    "valid_until_epoch_s": None,
                    "observation_policy_id": None,
                },
            ],
            "capabilities": [
                {
                    "capability_id": "structured-output",
                    "binding_id": "json-schema-v1",
                    "assurance": "pinned",
                },
                {
                    "capability_id": "exact-fit",
                    "binding_id": "render-fit-v1",
                    "assurance": "host-asserted",
                },
            ],
            "exact_fit_supported": True,
            "max_model_calls": 1,
            "fallback_owner": "host",
        }

    def supported_checks(self):
        return [
            {"kind": "citation-membership", "rule_id": "citation-rule-v1",
             "lowering_id": "citation-set-lowering-v1", "check_id": "citation-set-check-v1"},
            {"kind": "output-schema", "rule_id": "answer-object-v4",
             "lowering_id": "json-schema-lowering-v1", "check_id": "answer-object-check-v1"},
        ]

    def source_policy(self):
        return {
            "policy_id": "integrated-docqa-v1",
            "lowerings": [
                {
                    "obligation_id": "citation-membership",
                    "lowering_id": "citation-set-lowering-v1",
                    "check_id": "citation-set-check-v1",
                    "failure_reason": "citation-outside-authorized-set",
                },
                {
                    "obligation_id": "output-schema",
                    "lowering_id": "json-schema-lowering-v1",
                    "check_id": "answer-object-check-v1",
                    "failure_reason": "output-contract-failed",
                },
            ],
            "required_capabilities": ["structured-output"],
            "max_model_calls": 1,
        }

    def attestation(self, candidate, workload, host, *, status="qualified", valid_until=None):
        return {
            "v": 1,
            "format": "exactscope.qualification-attestation",
            "format_version": "0.1",
            "attestation_id": "attestation-r1",
            "status": status,
            "candidate_policy_sha256": qe.artifact_sha256(candidate),
            "workload_contract_sha256": qe.artifact_sha256(workload),
            "host_manifest_sha256": qe.artifact_sha256(host),
            "authority": {
                "kind": "workload-owner",
                "authority_id": "policy-owner-v1",
                "process_sha256": H,
            },
            "evidence": {
                "evaluation_package_sha256": H1,
                "analysis_sha256": H2,
                "scorer_sha256": H3,
                "economic_model_sha256": H4,
            },
            "validity": {
                "scope": host["qualification_scope"],
                "issued_epoch_s": 1000,
                "valid_until_epoch_s": valid_until,
                "observation_policy_id": "provider-observation-v1" if host["qualification_scope"] == "provider-observable" else None,
            },
            "gate_results": [
                {
                    "requirement_id": "accuracy-min",
                    "passed": True,
                    "observed": 8500,
                    "unit": "basis-points",
                },
                {
                    "requirement_id": "unsupported-max",
                    "passed": True,
                    "observed": 100,
                    "unit": "basis-points",
                },
            ],
            "mandatory_violations": 0,
        }

    def qualified_fixture(self, *, provider=False, valid_until=None):
        workload = self.workload()
        host = self.host(provider=provider)
        candidate = qe.compile_candidate(workload, host, self.source_policy())
        attestation = self.attestation(candidate, workload, host, valid_until=valid_until)
        profile = qe.make_profile("profile-r1", candidate, attestation, workload, host)
        return workload, host, candidate, attestation, profile

    def test_make_profile_cli_emits_generic_profile_from_standalone_attestation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workload, host, candidate, attestation, _profile = self.qualified_fixture()
            paths = {
                "workload": root / "workload.json",
                "host": root / "host.json",
                "candidate": root / "candidate.json",
                "attestation": root / "attestation.json",
                "profile": root / "profile.json",
            }
            for key, value in (
                ("workload", workload),
                ("host", host),
                ("candidate", candidate),
                ("attestation", attestation),
            ):
                paths[key].write_bytes(canonical_bytes(value))
            self.assertEqual(
                qe.main([
                    "make-profile",
                    "profile-cli-r1",
                    str(paths["candidate"]),
                    str(paths["attestation"]),
                    str(paths["workload"]),
                    str(paths["host"]),
                    str(paths["profile"]),
                ]),
                0,
            )
            profile = qe.load_object(paths["profile"])
            self.assertEqual(profile["profile_id"], "profile-cli-r1")
            self.assertEqual(qe.validate_profile(profile, workload, host), profile)

    def test_compile_profile_admit_finalize(self):
        workload, host, candidate, _attestation, profile = self.qualified_fixture()
        self.assertEqual(candidate["execution"]["fallback_mode"], "host-separate-authorized")
        binding = {
            "request_id": "req-1",
            "evidence_snapshot_sha256": H1,
            "rendered_request_sha256": H2,
            "execution_settings_sha256": H3,
        }
        admission = qe.admit(profile, workload, host, binding, now_epoch_s=1500)
        self.assertEqual(admission["decision"], "admitted")
        final = qe.finalize(
            profile,
            workload,
            host,
            admission,
            H4,
            {"citation-membership": True, "output-schema": True},
            request_binding=binding,
            now_epoch_s=1500,
        )
        self.assertEqual(final["decision"], "accepted")
        self.assertEqual(final["parent_admission_receipt_sha256"], canonical_sha256(admission))

    def test_missing_obligation_is_rejected_by_compiler(self):
        workload = self.workload()
        host = self.host()
        source = self.source_policy()
        source["lowerings"] = source["lowerings"][:1]
        with self.assertRaisesRegex(qe.QualifiedExecutionError, "unsupported-obligation"):
            qe.compile_candidate(workload, host, source)

    def test_unspecified_evidence_composition_remains_backward_compatible(self):
        candidate = qe.compile_candidate(self.workload(), self.host(), self.source_policy())
        self.assertEqual(candidate["execution"]["evidence_composition"], "unspecified")

    def test_single_source_precision_composition_compiles_to_precision_policy(self):
        workload = self.workload()
        workload["evidence_composition"] = "single-source-precision"
        workload["evidence_policy_id"] = "precision-context-v5"
        workload["evidence_budget_bytes"] = 3072
        candidate = qe.compile_candidate(workload, self.host(), self.source_policy())
        self.assertEqual(candidate["execution"]["evidence_composition"], "single-source-precision")
        self.assertEqual(candidate["execution"]["evidence_policy_id"], "precision-context-v5")
        self.assertEqual(candidate["execution"]["evidence_budget_bytes"], 3072)

    def test_multi_source_coverage_composition_compiles_to_coverage_policy(self):
        workload = self.workload()
        workload["evidence_composition"] = "multi-source-coverage"
        workload["evidence_policy_id"] = "multihop-coverage-v1"
        workload["evidence_budget_bytes"] = 3072
        candidate = qe.compile_candidate(workload, self.host(), self.source_policy())
        self.assertEqual(candidate["execution"]["evidence_composition"], "multi-source-coverage")
        self.assertEqual(candidate["execution"]["evidence_policy_id"], "multihop-coverage-v1")
        self.assertEqual(candidate["execution"]["evidence_budget_bytes"], 3072)

    def test_evidence_composition_policy_mismatch_fails_closed(self):
        workload = self.workload()
        workload["evidence_composition"] = "multi-source-coverage"
        workload["evidence_policy_id"] = "precision-context-v5"
        workload["evidence_budget_bytes"] = 3072
        with self.assertRaisesRegex(qe.QualifiedExecutionError, "evidence-composition-policy-mismatch"):
            qe.compile_candidate(workload, self.host(), self.source_policy())

    def test_known_evidence_composition_requires_explicit_budget(self):
        workload = self.workload()
        workload["evidence_composition"] = "single-source-precision"
        workload["evidence_policy_id"] = "precision-context-v5"
        with self.assertRaisesRegex(qe.QualifiedExecutionError, "evidence-budget-required"):
            qe.compile_candidate(workload, self.host(), self.source_policy())

    def test_unknown_required_capability_is_rejected(self):
        workload = self.workload()
        host = self.host(provider=True)
        host["capabilities"][0]["assurance"] = "unknown"
        with self.assertRaisesRegex(qe.QualifiedExecutionError, "unqualified-capability"):
            qe.compile_candidate(workload, host, self.source_policy())

    def test_qualified_attestation_cannot_lie_about_gate(self):
        workload = self.workload()
        host = self.host()
        candidate = qe.compile_candidate(workload, host, self.source_policy())
        attestation = self.attestation(candidate, workload, host)
        attestation["gate_results"][0]["observed"] = 7000
        with self.assertRaisesRegex(qe.QualifiedExecutionError, "qualification-gate-claim-mismatch"):
            qe.validate_attestation(attestation, candidate, workload, host)

    def test_failed_attestation_cannot_be_profile(self):
        workload = self.workload()
        host = self.host()
        candidate = qe.compile_candidate(workload, host, self.source_policy())
        attestation = self.attestation(candidate, workload, host, status="failed")
        with self.assertRaisesRegex(qe.QualifiedExecutionError, "attestation-not-qualified"):
            qe.make_profile("profile-r1", candidate, attestation, workload, host)

    def test_stale_profile_is_rejected_before_admission(self):
        workload, host, _candidate, _attestation, profile = self.qualified_fixture(provider=True, valid_until=2000)
        with self.assertRaisesRegex(qe.QualifiedExecutionError, "profile-stale"):
            qe.admit(
                profile,
                workload,
                host,
                {
                    "request_id": "req-1",
                    "evidence_snapshot_sha256": H1,
                    "rendered_request_sha256": H2,
                    "execution_settings_sha256": H3,
                },
                now_epoch_s=2001,
            )

    def test_opaque_provider_dependency_requires_validity_policy(self):
        host = self.host(provider=True)
        host["dependencies"][0]["valid_until_epoch_s"] = None
        host["dependencies"][0]["observation_policy_id"] = None
        with self.assertRaisesRegex(qe.QualifiedExecutionError, "opaque-dependency-without-validity-policy"):
            qe.validate_host(host)

    def test_runtime_obligation_failure_rejects_output(self):
        workload, host, _candidate, _attestation, profile = self.qualified_fixture()
        admission = qe.admit(
            profile,
            workload,
            host,
            {
                "request_id": "req-1",
                "evidence_snapshot_sha256": H1,
                "rendered_request_sha256": H2,
                "execution_settings_sha256": H3,
            },
        )
        final = qe.finalize(
            profile,
            workload,
            host,
            admission,
            H4,
            {"citation-membership": False, "output-schema": True},
            request_binding=self.binding(),
        )
        self.assertEqual(final["decision"], "rejected")
        self.assertEqual(final["reason"], "runtime-obligation-failed")

    def test_receipt_cannot_be_reused_for_different_profile_identity(self):
        workload, host, _candidate, _attestation, profile = self.qualified_fixture()
        admission = qe.admit(
            profile,
            workload,
            host,
            {
                "request_id": "req-1",
                "evidence_snapshot_sha256": H1,
                "rendered_request_sha256": H2,
                "execution_settings_sha256": H3,
            },
        )
        other_profile = deepcopy(profile)
        other_profile["profile_id"] = "profile-r2"
        with self.assertRaisesRegex(qe.QualifiedExecutionError, "receipt-profile-mismatch"):
            qe.finalize(
                other_profile,
                workload,
                host,
                admission,
                H4,
                {"citation-membership": True, "output-schema": True},
                request_binding=self.binding(),
            )

    def test_changed_host_fails_profile_validation(self):
        workload, host, _candidate, _attestation, profile = self.qualified_fixture()
        changed = deepcopy(host)
        changed["dependencies"][0]["identity"] = "different-model"
        with self.assertRaisesRegex(qe.QualifiedExecutionError, "host-identity-mismatch"):
            qe.validate_profile(profile, workload, changed)

    def test_requalification_exact_host_is_current(self):
        workload = self.workload()
        host = self.host()
        plan = qe.plan_requalification(workload, host, deepcopy(host))
        self.assertEqual(plan["status"], "current")
        self.assertEqual(plan["changed_dependency_ids"], [])

    def test_requalification_targeted_runtime_identity_change(self):
        workload = self.workload()
        host = self.host()
        changed = deepcopy(host)
        changed["dependencies"][1]["identity"] = "llama-runtime-sha-r2"
        plan = qe.plan_requalification(workload, host, changed)
        self.assertEqual(plan["status"], "targeted-requalification")
        self.assertEqual(plan["changed_dependency_ids"], ["runtime"])

    def test_requalification_model_change_is_full(self):
        workload = self.workload()
        host = self.host()
        changed = deepcopy(host)
        changed["dependencies"][0]["identity"] = "qwen-model-sha-r2"
        plan = qe.plan_requalification(workload, host, changed)
        self.assertEqual(plan["status"], "full-requalification")
        self.assertEqual(plan["changed_dependency_ids"], ["model"])

    def test_requalification_capability_change_is_full(self):
        workload = self.workload()
        host = self.host()
        changed = deepcopy(host)
        changed["capabilities"][0]["binding_id"] = "gbnf-v2"
        plan = qe.plan_requalification(workload, host, changed)
        self.assertEqual(plan["status"], "full-requalification")
        self.assertEqual(plan["reason"], "host-capability-surface-changed")

    def test_requalification_identity_refresh_requires_predeclared_id(self):
        workload = self.workload()
        workload["invalidation_policy"]["nonbehavioral_dependency_ids"] = ["runtime"]
        workload["invalidation_policy"]["targeted_dependency_ids"] = []
        host = self.host()
        changed = deepcopy(host)
        changed["dependencies"][1]["identity"] = "llama-runtime-build-label-r2"
        plan = qe.plan_requalification(workload, host, changed)
        self.assertEqual(plan["status"], "identity-refresh")
        self.assertEqual(plan["changed_dependency_ids"], ["runtime"])

    def test_finalization_rejects_changed_execution_binding(self):
        w, h, _, _, p = self.qualified_fixture()
        binding = self.binding()
        admission = qe.admit(p, w, h, binding)
        for field in binding:
            with self.subTest(field=field):
                changed = dict(binding)
                changed[field] = "another-request" if field == "request_id" else H4
                with self.assertRaisesRegex(qe.QualifiedExecutionError, "receipt-request-binding-mismatch"):
                    qe.finalize(p, w, h, admission, H4,
                                {"citation-membership": True, "output-schema": True},
                                request_binding=changed)

    def test_finalization_rejects_mutated_admission(self):
        w, h, _, _, p = self.qualified_fixture()
        admission = qe.admit(p, w, h, self.binding())
        for field, value in [("receipt_id", "forged"), ("output_sha256", H4),
                             ("parent_admission_receipt_sha256", H4)]:
            with self.subTest(field=field):
                changed = dict(admission, **{field: value})
                with self.assertRaisesRegex(qe.QualifiedExecutionError, "invalid-admission-receipt"):
                    qe.finalize(p, w, h, changed, H4,
                                {"citation-membership": True, "output-schema": True},
                                request_binding=self.binding())

    def test_provider_dependency_expiry_and_observation_are_enforced(self):
        w, h, _, _, p = self.qualified_fixture(provider=True, valid_until=3000)
        checks = {"provider-observation-v1": True}
        qe.admit(p, w, h, self.binding(), now_epoch_s=2000, observation_checks=checks)
        with self.assertRaisesRegex(qe.QualifiedExecutionError, "profile-stale"):
            qe.admit(p, w, h, self.binding(), now_epoch_s=2001, observation_checks=checks)
        for invalid in (None, {}, {"wrong-policy": True}, {"provider-observation-v1": False},
                        {"provider-observation-v1": 1}):
            with self.subTest(checks=invalid):
                with self.assertRaisesRegex(qe.QualifiedExecutionError, "observation-policy-not-satisfied"):
                    qe.admit(p, w, h, self.binding(), now_epoch_s=1500, observation_checks=invalid)

    def test_omitted_clock_cannot_bypass_expiry(self):
        w, h, _, _, p = self.qualified_fixture(valid_until=2000)
        with patch.object(qe.time, "time", return_value=2001):
            with self.assertRaisesRegex(qe.QualifiedExecutionError, "profile-stale"):
                qe.admit(p, w, h, self.binding())
        with self.assertRaisesRegex(qe.QualifiedExecutionError, "profile-not-yet-valid"):
            qe.admit(p, w, h, self.binding(), now_epoch_s=999)

    def test_finalization_rechecks_provider_observations(self):
        w, h, _, _, p = self.qualified_fixture(provider=True, valid_until=3000)
        admission = qe.admit(p, w, h, self.binding(), now_epoch_s=1500,
                             observation_checks={"provider-observation-v1": True})
        with self.assertRaisesRegex(qe.QualifiedExecutionError, "observation-policy-not-satisfied"):
            qe.finalize(p, w, h, admission, H4,
                        {"citation-membership": True, "output-schema": True},
                        request_binding=self.binding(), now_epoch_s=1501,
                        observation_checks={"provider-observation-v1": False})

    def test_unknown_dependency_cannot_claim_pinned_scope(self):
        host = self.host()
        host["dependencies"][0]["assurance"] = "unknown"
        with self.assertRaisesRegex(qe.QualifiedExecutionError, "unknown-dependency-in-pinned-host"):
            qe.validate_host(host)

    def test_all_nonqualified_statuses_are_nondeployable(self):
        for status in ("diagnostic", "failed", "inconclusive"):
            with self.subTest(status=status):
                w, h, c, a, p = self.qualified_fixture()
                a["status"] = status
                with self.assertRaisesRegex(qe.QualifiedExecutionError, "attestation-not-qualified"):
                    qe.make_profile("no", c, a, w, h)
                p["qualification_attestation"] = a
                with self.assertRaisesRegex(qe.QualifiedExecutionError, "profile-not-qualified"):
                    qe.admit(p, w, h, self.binding())

    def test_profile_schema_is_validated_with_local_references(self):
        w, h, c, a, p = self.qualified_fixture()
        with self.assertRaisesRegex(qe.QualifiedExecutionError, "invalid-profile"):
            qe.make_profile("x" * 257, c, a, w, h)
        for field, value in [("profile_id", 12), ("candidate_policy", []),
                             ("qualification_attestation", None)]:
            with self.subTest(field=field):
                bad = dict(p, **{field: value})
                with self.assertRaisesRegex(qe.QualifiedExecutionError, "invalid-profile"):
                    qe.validate_profile(bad, w, h)

    def test_profile_does_not_alias_mutable_inputs(self):
        w, h, c, a, p = self.qualified_fixture()
        original = qe.artifact_sha256(p)
        c["execution"]["max_model_calls"] = 0
        a["gate_results"][0]["observed"] = 0
        self.assertEqual(qe.artifact_sha256(p), original)

    def test_duplicate_gates_and_lowerings_fail_closed(self):
        w, h, c, a, _ = self.qualified_fixture()
        a["gate_results"].append(deepcopy(a["gate_results"][0]))
        with self.assertRaisesRegex(qe.QualifiedExecutionError, "duplicate-gate-result"):
            qe.validate_attestation(a, c, w, h)
        c["compiled_obligations"].append(deepcopy(c["compiled_obligations"][0]))
        with self.assertRaisesRegex(qe.QualifiedExecutionError, "duplicate-lowering"):
            qe.validate_candidate(c, w, h)

    def test_targeted_scope_must_be_predeclared_and_enabled(self):
        for enabled, ids in [(False, ["runtime"]), (True, [])]:
            w, h = self.workload(), self.host()
            w["invalidation_policy"]["targeted_requalification_allowed"] = enabled
            w["invalidation_policy"]["targeted_dependency_ids"] = ids
            changed = deepcopy(h)
            changed["dependencies"][1]["identity"] = "new-runtime"
            self.assertEqual(qe.plan_requalification(w, h, changed)["status"], "full-requalification")

    def test_capability_surface_changes_force_full_requalification(self):
        for field, value in [("exact_fit_supported", False), ("max_model_calls", 0),
                             ("supported_checks", [])]:
            w, h = self.workload(), self.host()
            changed = dict(h, **{field: value})
            self.assertEqual(qe.plan_requalification(w, h, changed)["status"], "full-requalification")

    def test_unimplemented_check_cannot_compile_or_validate(self):
        w, h = self.workload(), self.host()
        source = self.source_policy()
        source["lowerings"][0]["check_id"] = "invented-check"
        with self.assertRaisesRegex(qe.QualifiedExecutionError, "unsupported-obligation"):
            qe.compile_candidate(w, h, source)
        c = qe.compile_candidate(w, h, self.source_policy())
        c["compiled_obligations"][0]["check_id"] = "invented-check"
        with self.assertRaisesRegex(qe.QualifiedExecutionError, "unsupported-obligation"):
            qe.validate_candidate(c, w, h)
        h.pop("supported_checks")
        with self.assertRaisesRegex(qe.QualifiedExecutionError, "unsupported-obligation"):
            qe.compile_candidate(w, h, self.source_policy())

    def test_lowering_cannot_change_failure_semantics(self):
        source = self.source_policy()
        source["lowerings"][0]["failure_reason"] = "accept-anyway"
        with self.assertRaisesRegex(qe.QualifiedExecutionError, "lowering-failure-reason-mismatch"):
            qe.compile_candidate(self.workload(), self.host(), source)

    def test_candidate_does_not_alias_source_lowerings(self):
        source = self.source_policy()
        c = qe.compile_candidate(self.workload(), self.host(), source)
        original = qe.artifact_sha256(c)
        source["lowerings"][0]["check_id"] = "changed"
        self.assertEqual(qe.artifact_sha256(c), original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
