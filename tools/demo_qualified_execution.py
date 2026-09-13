#!/usr/bin/env python3
"""Run an in-memory ExactScope qualified-execution conformance demo.

This is deliberately SYNTHETIC CONFORMANCE ONLY. The qualification attestation in
this demo is fabricated test data so reviewers can exercise artifact binding and
fail-closed semantics without a customer workload. It is not enterprise evidence.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import qualified_execution as qe  # noqa: E402

H0 = "0" * 64
H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64
H4 = "4" * 64


def workload() -> dict:
    return {
        "v": 1,
        "format": "exactscope.workload-contract",
        "format_version": "0.1",
        "workload_id": "synthetic-review-docqa-v1",
        "workload_revision": "r1",
        "population_identity": "synthetic-conformance-population",
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
        "evidence_policy_id": "precision-context-v5",
        "evidence_composition": "single-source-precision",
        "evidence_budget_bytes": 3072,
        "economic_model_id": "synthetic-economics-v1",
        "invalidation_policy": {
            "unknown_change": "full-requalification",
            "targeted_requalification_allowed": True,
            "dependency_rule_id": "synthetic-dependency-rule-v1",
            "nonbehavioral_dependency_ids": [],
            "targeted_dependency_ids": ["runtime"],
        },
    }


def host() -> dict:
    return {
        "v": 1,
        "format": "exactscope.host-capability-manifest",
        "format_version": "0.1",
        "host_id": "synthetic-local-host",
        "supported_checks": [
            {
                "kind": "citation-membership",
                "rule_id": "citation-rule-v1",
                "lowering_id": "citation-set-lowering-v1",
                "check_id": "citation-set-check-v1",
            },
            {
                "kind": "output-schema",
                "rule_id": "answer-object-v4",
                "lowering_id": "json-schema-lowering-v1",
                "check_id": "answer-object-check-v1",
            },
        ],
        "qualification_scope": "inspectable-pinned",
        "dependencies": [
            {
                "dependency_id": "model",
                "kind": "model",
                "identity": "synthetic-model-sha-v1",
                "assurance": "pinned",
                "valid_until_epoch_s": None,
                "observation_policy_id": None,
            },
            {
                "dependency_id": "runtime",
                "kind": "runtime",
                "identity": "synthetic-runtime-sha-v1",
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
            }
        ],
        "exact_fit_supported": False,
        "max_model_calls": 1,
        "fallback_owner": "host",
    }


def source_policy() -> dict:
    return {
        "policy_id": "synthetic-integrated-docqa-v1",
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


def synthetic_attestation(candidate: dict, w: dict, h: dict) -> dict:
    return {
        "v": 1,
        "format": "exactscope.qualification-attestation",
        "format_version": "0.1",
        "attestation_id": "synthetic-conformance-attestation-r1",
        "status": "qualified",
        "candidate_policy_sha256": qe.artifact_sha256(candidate),
        "workload_contract_sha256": qe.artifact_sha256(w),
        "host_manifest_sha256": qe.artifact_sha256(h),
        "authority": {
            "kind": "workload-owner",
            "authority_id": "synthetic-conformance-owner-NOT-REAL",
            "process_sha256": H0,
        },
        "evidence": {
            "evaluation_package_sha256": H1,
            "analysis_sha256": H2,
            "scorer_sha256": H3,
            "economic_model_sha256": H4,
        },
        "validity": {
            "scope": "inspectable-pinned",
            "issued_epoch_s": 1000,
            "valid_until_epoch_s": None,
            "observation_policy_id": None,
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


def rejection_reason(fn) -> str:
    try:
        fn()
    except qe.QualifiedExecutionError as exc:
        return exc.reason
    raise RuntimeError("expected fail-closed rejection did not occur")


def main() -> int:
    w = workload()
    h = host()
    candidate = qe.compile_candidate(w, h, source_policy())
    attestation = synthetic_attestation(candidate, w, h)
    profile = qe.make_profile("synthetic-review-profile-r1", candidate, attestation, w, h)

    binding = {
        "request_id": "synthetic-request-1",
        "evidence_snapshot_sha256": H1,
        "rendered_request_sha256": H2,
        "execution_settings_sha256": H3,
    }
    admission = qe.admit(profile, w, h, binding, now_epoch_s=1500)
    finalization = qe.finalize(
        profile,
        w,
        h,
        admission,
        H4,
        {"citation-membership": True, "output-schema": True},
        request_binding=binding,
        now_epoch_s=1500,
    )

    changed_binding = dict(binding)
    changed_binding["rendered_request_sha256"] = H4
    receipt_rejection = rejection_reason(
        lambda: qe.finalize(
            profile,
            w,
            h,
            admission,
            H4,
            {"citation-membership": True, "output-schema": True},
            request_binding=changed_binding,
            now_epoch_s=1500,
        )
    )

    drifted_host = deepcopy(h)
    drifted_host["dependencies"][1]["identity"] = "synthetic-runtime-sha-v2"
    requalification = qe.plan_requalification(w, h, drifted_host)
    stale_profile_rejection = rejection_reason(
        lambda: qe.admit(profile, w, drifted_host, binding, now_epoch_s=1500)
    )

    output = {
        "status": "CONFORMANCE_DEMO_ONLY",
        "warning": "Synthetic attestation/gate values are test data, not enterprise qualification evidence.",
        "artifacts": {
            "workload_contract_sha256": qe.artifact_sha256(w),
            "host_manifest_sha256": qe.artifact_sha256(h),
            "candidate_policy_sha256": qe.artifact_sha256(candidate),
            "qualification_attestation_sha256": qe.artifact_sha256(attestation),
            "qualified_execution_profile_sha256": qe.artifact_sha256(profile),
        },
        "candidate_execution": candidate["execution"],
        "admission": {
            "decision": admission["decision"],
            "receipt_id": admission["receipt_id"],
        },
        "finalization": {
            "decision": finalization["decision"],
            "receipt_id": finalization["receipt_id"],
        },
        "tampered_rendered_request": {
            "decision": "rejected",
            "reason": receipt_rejection,
        },
        "runtime_identity_drift": {
            "requalification_plan": requalification,
            "old_profile_decision": "rejected",
            "old_profile_reason": stale_profile_rejection,
        },
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
