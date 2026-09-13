#!/usr/bin/env python3
"""Reference semantics for ExactScope qualified execution artifacts.

This is the Python reference implementation for the v1.1+ immutable qualification
core. It is deliberately small: it compiles a restricted semantic policy, verifies
candidate/attestation pairing, emits admission/finalization receipts, and fails
closed on stale or mismatched identities. It does not own model execution.
"""
from __future__ import annotations

import argparse
from functools import lru_cache
import json
from pathlib import Path
import sys
import time
from typing import Any, Mapping

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "spec" / "schemas"
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from grounding_canonical import canonical_bytes, canonical_sha256, loads  # noqa: E402


class QualifiedExecutionError(RuntimeError):
    """A fail-closed artifact/compiler/guard error with a stable reason code."""

    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(reason if not detail else f"{reason}: {detail}")


SCHEMA_FILES = {
    "workload": "workload-contract-v0.1.schema.json",
    "host": "host-capability-manifest-v0.1.schema.json",
    "candidate": "candidate-execution-policy-v0.1.schema.json",
    "attestation": "qualification-attestation-v0.1.schema.json",
    "receipt": "execution-receipt-v0.1.schema.json",
    "profile": "qualified-execution-profile-v0.1.schema.json",
}

PROFILE_KEYS = {
    "v",
    "format",
    "format_version",
    "profile_id",
    "candidate_policy",
    "qualification_attestation",
}

EVIDENCE_COMPOSITION_POLICIES = {
    "single-source-precision": "precision-context-v5",
    "multi-source-coverage": "multihop-coverage-v1",
}


# ---------- strict JSON / schema helpers ----------


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = loads(path.read_bytes())
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise QualifiedExecutionError("invalid-json", str(path)) from exc
    if not isinstance(value, dict):
        raise QualifiedExecutionError("invalid-artifact", f"{path}: expected object")
    return value


def artifact_sha256(value: Mapping[str, Any]) -> str:
    return canonical_sha256(dict(value))


def _schema(kind: str) -> dict[str, Any]:
    try:
        return json.loads((SCHEMA_DIR / SCHEMA_FILES[kind]).read_text(encoding="utf-8"))
    except (KeyError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise QualifiedExecutionError("schema-unavailable", kind) from exc


@lru_cache(maxsize=len(SCHEMA_FILES))
def _validator(kind: str) -> Draft202012Validator:
    # Resolve only the bounded local schema set, without network retrieval.
    schemas = [_schema(name) for name in SCHEMA_FILES]
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas
    )
    return Draft202012Validator(_schema(kind), registry=registry)


def _validate_schema(kind: str, value: Mapping[str, Any]) -> None:
    if not isinstance(value, Mapping):
        raise QualifiedExecutionError(f"invalid-{kind}", "expected object")
    errors = sorted(_validator(kind).iter_errors(dict(value)), key=lambda e: tuple(str(x) for x in e.absolute_path))
    if errors:
        first = errors[0]
        path = ".".join(str(x) for x in first.absolute_path)
        detail = first.message if not path else f"{path}: {first.message}"
        raise QualifiedExecutionError(f"invalid-{kind}", detail)
    try:
        canonical_bytes(dict(value))
    except ValueError as exc:
        raise QualifiedExecutionError(f"invalid-{kind}", str(exc)) from exc


def _unique(items: list[dict[str, Any]], key: str, reason: str) -> None:
    values = [item[key] for item in items]
    if len(values) != len(set(values)):
        raise QualifiedExecutionError(reason, key)


def validate_workload(workload: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(workload)
    _validate_schema("workload", value)
    _unique(value["runtime_obligations"], "obligation_id", "duplicate-obligation")
    _unique(value["empirical_requirements"], "requirement_id", "duplicate-requirement")
    return value


def validate_host(host: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(host)
    _validate_schema("host", value)
    _unique(value["dependencies"], "dependency_id", "duplicate-dependency")
    _unique(value["capabilities"], "capability_id", "duplicate-capability")

    if value["qualification_scope"] == "inspectable-pinned":
        if any(dep["assurance"] == "unknown" for dep in value["dependencies"]):
            raise QualifiedExecutionError("unknown-dependency-in-pinned-host")
    else:
        for dep in value["dependencies"]:
            if dep["assurance"] == "unknown":
                if dep["valid_until_epoch_s"] is None and dep["observation_policy_id"] is None:
                    raise QualifiedExecutionError("opaque-dependency-without-validity-policy", dep["dependency_id"])
    return value


def _validate_lowerings(workload: Mapping[str, Any], host: Mapping[str, Any], lowerings: list[dict[str, Any]]) -> None:
    """Bind checks to a trusted host implementation declaration, never arbitrary names."""
    obligations = {item["obligation_id"]: item for item in workload["runtime_obligations"]}
    supported = host.get("supported_checks", [])
    for lowering in lowerings:
        obligation = obligations[lowering["obligation_id"]]
        binding = {key: obligation[key] for key in ("kind", "rule_id")}
        binding.update({key: lowering[key] for key in ("lowering_id", "check_id")})
        if binding not in supported:
            raise QualifiedExecutionError("unsupported-obligation", obligation["obligation_id"])
        if lowering["failure_reason"] != obligation["failure_reason"]:
            raise QualifiedExecutionError("lowering-failure-reason-mismatch", obligation["obligation_id"])
        if obligation["kind"] == "context-admission" and not host["exact_fit_supported"]:
            raise QualifiedExecutionError("unsupported-obligation", obligation["obligation_id"])


# ---------- restricted compiler ----------


def compile_candidate(
    workload: Mapping[str, Any],
    host: Mapping[str, Any],
    source_policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile a restricted source policy into an immutable Candidate Execution Policy.

    source_policy is intentionally not a general DSL. It must contain:
      policy_id, lowerings[], required_capabilities[], max_model_calls.
    Every runtime obligation must have exactly one deterministic lowering/check.
    """
    w = validate_workload(workload)
    h = validate_host(host)
    source = dict(source_policy)
    expected_keys = {"policy_id", "lowerings", "required_capabilities", "max_model_calls"}
    if set(source) != expected_keys:
        raise QualifiedExecutionError("invalid-source-policy-keys")
    if not isinstance(source["policy_id"], str) or not source["policy_id"]:
        raise QualifiedExecutionError("invalid-source-policy-id")
    if type(source["max_model_calls"]) is not int or source["max_model_calls"] < 0:
        raise QualifiedExecutionError("invalid-max-model-calls")
    if source["max_model_calls"] > h["max_model_calls"]:
        raise QualifiedExecutionError("host-model-call-limit")
    if not isinstance(source["required_capabilities"], list) or not all(
        isinstance(item, str) and item for item in source["required_capabilities"]
    ):
        raise QualifiedExecutionError("invalid-required-capabilities")
    if len(source["required_capabilities"]) != len(set(source["required_capabilities"])):
        raise QualifiedExecutionError("duplicate-required-capability")

    lowerings = source["lowerings"]
    if not isinstance(lowerings, list) or not lowerings or not all(isinstance(item, dict) for item in lowerings):
        raise QualifiedExecutionError("invalid-lowerings")
    required_lowering_keys = {"obligation_id", "lowering_id", "check_id", "failure_reason"}
    for item in lowerings:
        if set(item) != required_lowering_keys or not all(isinstance(item[key], str) and item[key] for key in required_lowering_keys):
            raise QualifiedExecutionError("invalid-lowering")
    _unique(lowerings, "obligation_id", "duplicate-lowering")

    workload_ids = {item["obligation_id"] for item in w["runtime_obligations"]}
    lowering_ids = {item["obligation_id"] for item in lowerings}
    missing = sorted(workload_ids - lowering_ids)
    extra = sorted(lowering_ids - workload_ids)
    if missing:
        raise QualifiedExecutionError("unsupported-obligation", ",".join(missing))
    if extra:
        raise QualifiedExecutionError("unknown-obligation", ",".join(extra))
    _validate_lowerings(w, h, lowerings)

    evidence_composition = w.get("evidence_composition", "unspecified")
    expected_evidence_policy = EVIDENCE_COMPOSITION_POLICIES.get(evidence_composition)
    if expected_evidence_policy is not None and w["evidence_policy_id"] != expected_evidence_policy:
        raise QualifiedExecutionError(
            "evidence-composition-policy-mismatch",
            f"{evidence_composition}:{w['evidence_policy_id']}",
        )
    if expected_evidence_policy is not None and w.get("evidence_budget_bytes") is None:
        raise QualifiedExecutionError("evidence-budget-required", evidence_composition)

    capabilities = {item["capability_id"]: item for item in h["capabilities"]}
    for capability_id in source["required_capabilities"]:
        capability = capabilities.get(capability_id)
        if capability is None:
            raise QualifiedExecutionError("unsupported-capability", capability_id)
        if capability["assurance"] == "unknown":
            raise QualifiedExecutionError("unqualified-capability", capability_id)

    candidate = {
        "v": 1,
        "format": "exactscope.candidate-execution-policy",
        "format_version": "0.1",
        "policy_id": source["policy_id"],
        "workload_contract_sha256": artifact_sha256(w),
        "host_manifest_sha256": artifact_sha256(h),
        "source_policy_sha256": canonical_sha256(source),
        "compiled_obligations": sorted(lowerings, key=lambda item: item["obligation_id"]),
        "required_capabilities": sorted(source["required_capabilities"]),
        "execution": {
            "admission_required": True,
            "finalization_required": True,
            "max_model_calls": source["max_model_calls"],
            "fallback_mode": "host-separate-authorized",
            "answer_contract_id": w["answer_contract_id"],
            "evidence_policy_id": w["evidence_policy_id"],
            "evidence_composition": evidence_composition,
            "evidence_budget_bytes": w.get("evidence_budget_bytes"),
        },
    }
    _validate_schema("candidate", candidate)
    return loads(canonical_bytes(candidate))


def validate_candidate(
    candidate: Mapping[str, Any],
    workload: Mapping[str, Any],
    host: Mapping[str, Any],
) -> dict[str, Any]:
    value = dict(candidate)
    _validate_schema("candidate", value)
    _unique(value["compiled_obligations"], "obligation_id", "duplicate-lowering")
    w = validate_workload(workload)
    h = validate_host(host)
    if value["workload_contract_sha256"] != artifact_sha256(w):
        raise QualifiedExecutionError("workload-identity-mismatch")
    if value["host_manifest_sha256"] != artifact_sha256(h):
        raise QualifiedExecutionError("host-identity-mismatch")
    if value["execution"]["answer_contract_id"] != w["answer_contract_id"]:
        raise QualifiedExecutionError("answer-contract-mismatch")
    if value["execution"]["evidence_policy_id"] != w["evidence_policy_id"]:
        raise QualifiedExecutionError("evidence-policy-mismatch")
    expected_composition = w.get("evidence_composition", "unspecified")
    if value["execution"].get("evidence_composition", "unspecified") != expected_composition:
        raise QualifiedExecutionError("evidence-composition-mismatch")
    if value["execution"].get("evidence_budget_bytes") != w.get("evidence_budget_bytes"):
        raise QualifiedExecutionError("evidence-budget-mismatch")
    if value["execution"]["max_model_calls"] > h["max_model_calls"]:
        raise QualifiedExecutionError("host-model-call-limit")

    required_obligations = {item["obligation_id"] for item in w["runtime_obligations"]}
    actual_obligations = {item["obligation_id"] for item in value["compiled_obligations"]}
    if actual_obligations != required_obligations:
        raise QualifiedExecutionError("compiled-obligation-set-mismatch")
    _validate_lowerings(w, h, value["compiled_obligations"])

    host_caps = {item["capability_id"]: item for item in h["capabilities"]}
    for capability_id in value["required_capabilities"]:
        capability = host_caps.get(capability_id)
        if capability is None:
            raise QualifiedExecutionError("unsupported-capability", capability_id)
        if capability["assurance"] == "unknown":
            raise QualifiedExecutionError("unqualified-capability", capability_id)
    return value


# ---------- qualification / profile ----------


def _gate_passes(requirement: Mapping[str, Any], observed: int) -> bool:
    direction = requirement["direction"]
    threshold = requirement["threshold"]
    if direction == "min":
        return observed >= threshold
    if direction == "max":
        return observed <= threshold
    if direction == "zero":
        return observed == 0
    raise QualifiedExecutionError("unsupported-gate-direction", str(direction))


def validate_attestation(
    attestation: Mapping[str, Any],
    candidate: Mapping[str, Any],
    workload: Mapping[str, Any],
    host: Mapping[str, Any],
) -> dict[str, Any]:
    value = dict(attestation)
    _validate_schema("attestation", value)
    _unique(value["gate_results"], "requirement_id", "duplicate-gate-result")
    w = validate_workload(workload)
    h = validate_host(host)
    p = validate_candidate(candidate, w, h)

    if value["candidate_policy_sha256"] != artifact_sha256(p):
        raise QualifiedExecutionError("candidate-attestation-mismatch")
    if value["workload_contract_sha256"] != artifact_sha256(w):
        raise QualifiedExecutionError("attestation-workload-mismatch")
    if value["host_manifest_sha256"] != artifact_sha256(h):
        raise QualifiedExecutionError("attestation-host-mismatch")
    if value["validity"]["scope"] != h["qualification_scope"]:
        raise QualifiedExecutionError("qualification-scope-mismatch")

    issued = value["validity"]["issued_epoch_s"]
    valid_until = value["validity"]["valid_until_epoch_s"]
    if valid_until is not None and valid_until < issued:
        raise QualifiedExecutionError("invalid-validity-window")
    if h["qualification_scope"] == "provider-observable":
        if valid_until is None and value["validity"]["observation_policy_id"] is None:
            raise QualifiedExecutionError("provider-validity-policy-required")

    requirements = {item["requirement_id"]: item for item in w["empirical_requirements"]}
    results = {item["requirement_id"]: item for item in value["gate_results"]}
    if set(results) != set(requirements):
        raise QualifiedExecutionError("qualification-gate-set-mismatch")
    for requirement_id, requirement in requirements.items():
        result = results[requirement_id]
        if result["unit"] != requirement["unit"]:
            raise QualifiedExecutionError("qualification-gate-unit-mismatch", requirement_id)
        computed = _gate_passes(requirement, result["observed"])
        if result["passed"] is not computed:
            raise QualifiedExecutionError("qualification-gate-claim-mismatch", requirement_id)

    if value["status"] == "qualified":
        if value["mandatory_violations"] != 0:
            raise QualifiedExecutionError("qualified-with-mandatory-violations")
        if not all(item["passed"] for item in value["gate_results"]):
            raise QualifiedExecutionError("qualified-with-failed-gate")
    return value


def make_profile(
    profile_id: str,
    candidate: Mapping[str, Any],
    attestation: Mapping[str, Any],
    workload: Mapping[str, Any],
    host: Mapping[str, Any],
) -> dict[str, Any]:
    if not profile_id:
        raise QualifiedExecutionError("invalid-profile-id")
    p = validate_candidate(candidate, workload, host)
    a = validate_attestation(attestation, p, workload, host)
    if a["status"] != "qualified":
        raise QualifiedExecutionError("attestation-not-qualified")
    profile = {
        "v": 1,
        "format": "exactscope.qualified-execution-profile",
        "format_version": "0.1",
        "profile_id": profile_id,
        "candidate_policy": p,
        "qualification_attestation": a,
    }
    _validate_schema("profile", profile)
    return loads(canonical_bytes(profile))


def plan_requalification(
    workload: Mapping[str, Any],
    qualified_host: Mapping[str, Any],
    current_host: Mapping[str, Any],
) -> dict[str, Any]:
    """Conservatively classify host drift against a qualified host identity.

    Targeted or identity-only refresh is allowed only when the Workload Contract
    prospectively lists the exact dependency ids. Everything else requires full
    requalification.
    """
    w = validate_workload(workload)
    old = validate_host(qualified_host)
    new = validate_host(current_host)
    rule = w["invalidation_policy"]

    if artifact_sha256(old) == artifact_sha256(new):
        return {
            "status": "current",
            "changed_dependency_ids": [],
            "reason": "host-identity-current",
            "dependency_rule_id": rule["dependency_rule_id"],
        }

    if old["host_id"] != new["host_id"] or old["qualification_scope"] != new["qualification_scope"]:
        return {
            "status": "full-requalification",
            "changed_dependency_ids": [],
            "reason": "host-or-scope-changed",
            "dependency_rule_id": rule["dependency_rule_id"],
        }

    old_caps = {item["capability_id"]: item for item in old["capabilities"]}
    new_caps = {item["capability_id"]: item for item in new["capabilities"]}
    if (
        old_caps != new_caps
        or old.get("supported_checks", []) != new.get("supported_checks", [])
        or old["exact_fit_supported"] != new["exact_fit_supported"]
        or old["max_model_calls"] != new["max_model_calls"]
        or old["fallback_owner"] != new["fallback_owner"]
    ):
        return {
            "status": "full-requalification",
            "changed_dependency_ids": [],
            "reason": "host-capability-surface-changed",
            "dependency_rule_id": rule["dependency_rule_id"],
        }

    old_deps = {item["dependency_id"]: item for item in old["dependencies"]}
    new_deps = {item["dependency_id"]: item for item in new["dependencies"]}
    if set(old_deps) != set(new_deps):
        changed = sorted(set(old_deps) ^ set(new_deps))
        return {
            "status": "full-requalification",
            "changed_dependency_ids": changed,
            "reason": "dependency-set-changed",
            "dependency_rule_id": rule["dependency_rule_id"],
        }

    changed_ids: list[str] = []
    identity_only_ids: list[str] = []
    behavioral_ids: list[str] = []
    for dep_id in sorted(old_deps):
        before = old_deps[dep_id]
        after = new_deps[dep_id]
        if before == after:
            continue
        changed_ids.append(dep_id)
        differing = {key for key in before if before[key] != after[key]}
        if differing == {"identity"}:
            identity_only_ids.append(dep_id)
        else:
            behavioral_ids.append(dep_id)

    if not changed_ids:
        return {
            "status": "full-requalification",
            "changed_dependency_ids": [],
            "reason": "unclassified-host-drift",
            "dependency_rule_id": rule["dependency_rule_id"],
        }

    nonbehavioral = set(rule["nonbehavioral_dependency_ids"])
    if not behavioral_ids and set(identity_only_ids).issubset(nonbehavioral):
        return {
            "status": "identity-refresh",
            "changed_dependency_ids": changed_ids,
            "reason": "prospectively-declared-nonbehavioral-identity-change",
            "dependency_rule_id": rule["dependency_rule_id"],
        }

    targeted = set(rule["targeted_dependency_ids"])
    if rule["targeted_requalification_allowed"] and set(changed_ids).issubset(targeted):
        for dep_id in changed_ids:
            if old_deps[dep_id]["kind"] != new_deps[dep_id]["kind"]:
                return {
                    "status": "full-requalification",
                    "changed_dependency_ids": changed_ids,
                    "reason": "dependency-kind-changed",
                    "dependency_rule_id": rule["dependency_rule_id"],
                }
        return {
            "status": "targeted-requalification",
            "changed_dependency_ids": changed_ids,
            "reason": "prospectively-declared-targeted-dependencies-changed",
            "dependency_rule_id": rule["dependency_rule_id"],
        }

    return {
        "status": "full-requalification",
        "changed_dependency_ids": changed_ids,
        "reason": "behavior-affecting-change-outside-targeted-scope",
        "dependency_rule_id": rule["dependency_rule_id"],
    }


def validate_profile(
    profile: Mapping[str, Any],
    workload: Mapping[str, Any],
    host: Mapping[str, Any],
    *,
    now_epoch_s: int | None = None,
    observation_checks: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    _validate_schema("profile", profile)
    value = dict(profile)
    if set(value) != PROFILE_KEYS:
        raise QualifiedExecutionError("invalid-profile-keys")
    if value.get("v") != 1 or value.get("format") != "exactscope.qualified-execution-profile" or value.get("format_version") != "0.1":
        raise QualifiedExecutionError("invalid-profile-identity")
    if not isinstance(value.get("profile_id"), str) or not value["profile_id"]:
        raise QualifiedExecutionError("invalid-profile-id")
    p = validate_candidate(value["candidate_policy"], workload, host)
    a = validate_attestation(value["qualification_attestation"], p, workload, host)
    if a["status"] != "qualified":
        raise QualifiedExecutionError("profile-not-qualified")
    now = int(time.time()) if now_epoch_s is None else now_epoch_s
    if type(now) is not int or now < 0:
        raise QualifiedExecutionError("invalid-current-time")
    if now < a["validity"]["issued_epoch_s"]:
        raise QualifiedExecutionError("profile-not-yet-valid")
    validity_records = [a["validity"], *host["dependencies"]]
    for record in validity_records:
        expiry = record["valid_until_epoch_s"]
        if expiry is not None and now > expiry:
            raise QualifiedExecutionError("profile-stale")
        policy_id = record["observation_policy_id"]
        if policy_id is not None and (observation_checks or {}).get(policy_id) is not True:
            raise QualifiedExecutionError("observation-policy-not-satisfied", policy_id)
    canonical_bytes(value)
    return value


# ---------- binding serving receipts ----------


def _sha_field(binding: Mapping[str, Any], key: str) -> str:
    value = binding.get(key)
    if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise QualifiedExecutionError("invalid-request-binding", key)
    return value


def admit(
    profile: Mapping[str, Any],
    workload: Mapping[str, Any],
    host: Mapping[str, Any],
    request_binding: Mapping[str, Any],
    *,
    now_epoch_s: int | None = None,
    observation_checks: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    """Return an immutable admission receipt. Malformed/stale profiles fail closed."""
    p = validate_profile(profile, workload, host, now_epoch_s=now_epoch_s, observation_checks=observation_checks)
    request_id = request_binding.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        raise QualifiedExecutionError("invalid-request-binding", "request_id")
    evidence_sha = _sha_field(request_binding, "evidence_snapshot_sha256")
    rendered_sha = _sha_field(request_binding, "rendered_request_sha256")
    settings_sha = _sha_field(request_binding, "execution_settings_sha256")
    policy_sha = artifact_sha256(p["candidate_policy"])
    profile_sha = artifact_sha256(p)
    basis = {
        "profile_sha256": profile_sha,
        "candidate_policy_sha256": policy_sha,
        "request_id": request_id,
        "evidence_snapshot_sha256": evidence_sha,
        "rendered_request_sha256": rendered_sha,
        "execution_settings_sha256": settings_sha,
    }
    receipt = {
        "v": 1,
        "format": "exactscope.execution-receipt",
        "format_version": "0.1",
        "receipt_id": "admission-" + canonical_sha256(basis)[:32],
        "phase": "admission",
        "decision": "admitted",
        "reason": "qualified-profile-admitted",
        "profile_sha256": profile_sha,
        "candidate_policy_sha256": policy_sha,
        "workload_contract_sha256": artifact_sha256(dict(workload)),
        "host_manifest_sha256": artifact_sha256(dict(host)),
        "request_id": request_id,
        "evidence_snapshot_sha256": evidence_sha,
        "rendered_request_sha256": rendered_sha,
        "execution_settings_sha256": settings_sha,
        "parent_admission_receipt_sha256": None,
        "output_sha256": None,
    }
    _validate_schema("receipt", receipt)
    return receipt


def finalize(
    profile: Mapping[str, Any],
    workload: Mapping[str, Any],
    host: Mapping[str, Any],
    admission_receipt: Mapping[str, Any],
    output_sha256: str,
    runtime_checks: Mapping[str, bool],
    *,
    request_binding: Mapping[str, Any],
    now_epoch_s: int | None = None,
    observation_checks: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    """Finalize against the trusted host's current execution binding and checks.

    The host supplies the actual request/evidence/settings, authenticates retained
    receipts and check results, and owns one-shot consumption. Digests are not
    signatures, and this stateless reference does not prove semantic correctness.
    """
    p = validate_profile(profile, workload, host, now_epoch_s=now_epoch_s, observation_checks=observation_checks)
    receipt = dict(admission_receipt)
    _validate_schema("receipt", receipt)
    if receipt["phase"] != "admission" or receipt["decision"] != "admitted":
        raise QualifiedExecutionError("invalid-admission-receipt")
    if receipt["profile_sha256"] != artifact_sha256(p):
        raise QualifiedExecutionError("receipt-profile-mismatch")
    if receipt["candidate_policy_sha256"] != artifact_sha256(p["candidate_policy"]):
        raise QualifiedExecutionError("receipt-policy-mismatch")
    if receipt["workload_contract_sha256"] != artifact_sha256(dict(workload)):
        raise QualifiedExecutionError("receipt-workload-mismatch")
    if receipt["host_manifest_sha256"] != artifact_sha256(dict(host)):
        raise QualifiedExecutionError("receipt-host-mismatch")
    expected = admit(p, workload, host, request_binding, now_epoch_s=now_epoch_s,
                     observation_checks=observation_checks)
    for key in ("request_id", "evidence_snapshot_sha256", "rendered_request_sha256", "execution_settings_sha256"):
        if receipt[key] != expected[key]:
            raise QualifiedExecutionError("receipt-request-binding-mismatch", key)
    if receipt != expected:
        raise QualifiedExecutionError("invalid-admission-receipt")
    if not isinstance(output_sha256, str) or len(output_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in output_sha256):
        raise QualifiedExecutionError("invalid-output-digest")

    obligation_ids = {item["obligation_id"] for item in p["candidate_policy"]["compiled_obligations"]}
    if set(runtime_checks) != obligation_ids or not all(type(value) is bool for value in runtime_checks.values()):
        raise QualifiedExecutionError("runtime-check-set-mismatch")
    passed = all(runtime_checks.values())
    decision = "accepted" if passed else "rejected"
    reason = "runtime-obligations-passed" if passed else "runtime-obligation-failed"
    parent_sha = artifact_sha256(receipt)
    basis = {
        "parent_admission_receipt_sha256": parent_sha,
        "output_sha256": output_sha256,
        "decision": decision,
    }
    final = {
        "v": 1,
        "format": "exactscope.execution-receipt",
        "format_version": "0.1",
        "receipt_id": "finalization-" + canonical_sha256(basis)[:32],
        "phase": "finalization",
        "decision": decision,
        "reason": reason,
        "profile_sha256": receipt["profile_sha256"],
        "candidate_policy_sha256": receipt["candidate_policy_sha256"],
        "workload_contract_sha256": receipt["workload_contract_sha256"],
        "host_manifest_sha256": receipt["host_manifest_sha256"],
        "request_id": receipt["request_id"],
        "evidence_snapshot_sha256": receipt["evidence_snapshot_sha256"],
        "rendered_request_sha256": receipt["rendered_request_sha256"],
        "execution_settings_sha256": receipt["execution_settings_sha256"],
        "parent_admission_receipt_sha256": parent_sha,
        "output_sha256": output_sha256,
    }
    _validate_schema("receipt", final)
    return final


# ---------- CLI ----------


def _write(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists():
        raise QualifiedExecutionError("output-exists", str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(dict(value)))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    compile_p = sub.add_parser("compile")
    compile_p.add_argument("workload", type=Path)
    compile_p.add_argument("host", type=Path)
    compile_p.add_argument("source_policy", type=Path)
    compile_p.add_argument("output", type=Path)

    profile_p = sub.add_parser("make-profile")
    profile_p.add_argument("profile_id")
    profile_p.add_argument("candidate", type=Path)
    profile_p.add_argument("attestation", type=Path)
    profile_p.add_argument("workload", type=Path)
    profile_p.add_argument("host", type=Path)
    profile_p.add_argument("output", type=Path)

    verify_p = sub.add_parser("verify-profile")
    verify_p.add_argument("profile", type=Path)
    verify_p.add_argument("workload", type=Path)
    verify_p.add_argument("host", type=Path)
    verify_p.add_argument("--now-epoch-s", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "compile":
            candidate = compile_candidate(load_object(args.workload), load_object(args.host), load_object(args.source_policy))
            _write(args.output, candidate)
            print(json.dumps({"status": "COMPILED", "candidate_sha256": artifact_sha256(candidate)}, sort_keys=True))
        elif args.command == "make-profile":
            workload = load_object(args.workload)
            host = load_object(args.host)
            profile = make_profile(
                args.profile_id,
                load_object(args.candidate),
                load_object(args.attestation),
                workload,
                host,
            )
            _write(args.output, profile)
            print(json.dumps({"status": "PROFILE_EMITTED", "profile_sha256": artifact_sha256(profile)}, sort_keys=True))
        else:
            profile = validate_profile(
                load_object(args.profile),
                load_object(args.workload),
                load_object(args.host),
                now_epoch_s=args.now_epoch_s,
            )
            print(json.dumps({"status": "QUALIFIED", "profile_sha256": artifact_sha256(profile)}, sort_keys=True))
        return 0
    except QualifiedExecutionError as exc:
        print(json.dumps({"status": "REJECTED", "reason": exc.reason, "detail": exc.detail}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
