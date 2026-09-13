#!/usr/bin/env python3
"""Bridge a fully qualified enterprise DocQA decision into generic attestation.

This tool does not emit a Qualified Execution Profile. It only constructs the generic
Qualification Attestation for the exact Candidate Execution Policy / Workload Contract /
Host Capability Manifest that were already frozen in the Study Contract, then asks the
generic qualified-execution validator to recompute every empirical gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
BENCH = ROOT / "benchmarks"
for directory in (TOOLS, BENCH):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from grounding_canonical import canonical_bytes, canonical_sha256, loads  # noqa: E402
import enterprise_docqa_decision as decision_tool  # noqa: E402
import enterprise_docqa_observations as observations  # noqa: E402
import enterprise_docqa_score as score_tool  # noqa: E402
import enterprise_docqa_study_contract as study_tool  # noqa: E402
import qualified_execution as qe  # noqa: E402

FORMAT_VERSION = "0.1"
BRIDGE_FORMAT = "exactscope.enterprise-docqa-attestation-bridge"
EVALUATION_PACKAGE_FORMAT = "exactscope.enterprise-docqa-evaluation-package"
RATE_METRICS = {
    "task_accuracy",
    "evidence_support_rate",
    "unsupported_answer_rate",
    "abstention_correct_rate",
    "unacceptable_error_rate",
}
COUNT_METRICS = {
    "unacceptable_error_count",
    "format_violations",
    "finalization_violations",
}


class AttestationBridgeError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return observations.sha256(path)


def load_object(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise AttestationBridgeError(f"cannot load JSON object: {path}") from exc
    if not isinstance(value, dict) or raw != canonical_bytes(value):
        raise AttestationBridgeError(f"noncanonical JSON object: {path}")
    return value


def positive_or_zero_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise AttestationBridgeError(f"{label} must be a nonnegative integer")
    return value


def gate_passes(requirement: dict[str, Any], observed: int) -> bool:
    direction = requirement["direction"]
    threshold = requirement["threshold"]
    if direction == "min":
        return observed >= threshold
    if direction == "max":
        return observed <= threshold
    if direction == "zero":
        if threshold != 0:
            raise AttestationBridgeError("zero-direction workload requirement must have threshold=0")
        return observed == 0
    raise AttestationBridgeError(f"unsupported requirement direction: {direction}")


def observed_metrics(score: dict[str, Any], prereg: dict[str, Any]) -> dict[str, tuple[int, str]]:
    arms = score.get("arms")
    if not isinstance(arms, dict) or not isinstance(arms.get("integrated"), dict):
        raise AttestationBridgeError("score lacks Integrated arm")
    integrated = arms["integrated"]
    metrics = integrated.get("metrics")
    if not isinstance(metrics, dict):
        raise AttestationBridgeError("score lacks Integrated metrics")
    result: dict[str, tuple[int, str]] = {}
    for name, value in metrics.items():
        if type(value) is not int:
            raise AttestationBridgeError(f"Integrated metric must be integer: {name}")
        if name in RATE_METRICS:
            result[name] = (value, "basis-points")
        elif name in COUNT_METRICS:
            result[name] = (value, "count")
    total_cost = integrated.get("total_economic_cost")
    if type(total_cost) is not int or total_cost < 0:
        raise AttestationBridgeError("score lacks integer Integrated total_economic_cost")
    unit = prereg.get("records", {}).get("economics", {}).get("unit")
    if not isinstance(unit, str) or not unit:
        raise AttestationBridgeError("preregistration economics unit missing")
    result["total_economic_cost"] = (total_cost, unit)
    return result


def build_attestation(
    prereg_path: Path,
    study_path: Path,
    score_path: Path,
    analysis_path: Path,
    owner_path: Path,
    decision_path: Path,
    analysis_source_path: Path,
    decision_source_path: Path,
    workload_contract_path: Path,
    host_manifest_path: Path,
    candidate_policy_path: Path,
    attestation_id: str,
    issued_epoch_s: int,
    valid_until_epoch_s: int | None,
    observation_policy_id: str | None,
    output: Path,
    attestation_output: Path | None = None,
) -> dict[str, Any]:
    if output.exists():
        raise AttestationBridgeError("attestation bridge output already exists")
    if attestation_output is not None:
        if attestation_output.resolve() == output.resolve():
            raise AttestationBridgeError("standalone attestation output must differ from bridge output")
        if attestation_output.exists():
            raise AttestationBridgeError("standalone attestation output already exists")
    if not isinstance(attestation_id, str) or not attestation_id.strip():
        raise AttestationBridgeError("attestation_id must be nonempty text")
    positive_or_zero_int(issued_epoch_s, "issued_epoch_s")
    if valid_until_epoch_s is not None:
        positive_or_zero_int(valid_until_epoch_s, "valid_until_epoch_s")
        if valid_until_epoch_s < issued_epoch_s:
            raise AttestationBridgeError("valid_until_epoch_s precedes issuance")

    prereg = load_object(prereg_path)
    study = load_object(study_path)
    score = load_object(score_path)
    analysis = load_object(analysis_path)
    owner = load_object(owner_path)
    decision = load_object(decision_path)
    workload = load_object(workload_contract_path)
    host = load_object(host_manifest_path)
    candidate = load_object(candidate_policy_path)

    if study.get("format") != study_tool.FORMAT or study.get("format_version") != FORMAT_VERSION:
        raise AttestationBridgeError("unsupported Study Contract identity")
    if decision.get("format") != decision_tool.DECISION_FORMAT or decision.get("format_version") != FORMAT_VERSION:
        raise AttestationBridgeError("unsupported enterprise decision identity")
    if decision.get("status") != "qualified" or decision.get("generic_attestation_eligible") is not True:
        raise AttestationBridgeError("enterprise decision is not eligible for generic attestation")
    if decision.get("qualified_execution_profile_emitted") is not False:
        raise AttestationBridgeError("enterprise decision illegally claims profile emission")

    bindings = {
        "preregistration_sha256": sha256(prereg_path),
        "study_contract_sha256": sha256(study_path),
        "score_sha256": sha256(score_path),
        "analysis_report_sha256": sha256(analysis_path),
        "owner_decision_sha256": sha256(owner_path),
    }
    for field, expected in bindings.items():
        if decision.get(field) != expected:
            raise AttestationBridgeError(f"enterprise decision binding drift: {field}")
    if not analysis_source_path.is_file() or sha256(analysis_source_path) != study.get("analysis_source_sha256"):
        raise AttestationBridgeError("analysis source differs from frozen Study Contract")
    if not decision_source_path.is_file() or sha256(decision_source_path) != study.get("decision_source_sha256"):
        raise AttestationBridgeError("decision source differs from frozen Study Contract")
    if decision.get("analysis_source_sha256") != study.get("analysis_source_sha256"):
        raise AttestationBridgeError("decision analysis-source identity drift")
    if decision.get("decision_source_sha256") != study.get("decision_source_sha256"):
        raise AttestationBridgeError("decision implementation identity drift")
    try:
        decision_tool.validate_decision_record(
            decision,
            prereg_path,
            study_path,
            score_path,
            analysis_path,
            analysis_source_path,
            owner_path,
        )
    except decision_tool.DecisionError as exc:
        raise AttestationBridgeError(f"enterprise qualification decision failed revalidation: {exc}") from exc

    readiness_sha = score.get("readiness_report_sha256")
    if not isinstance(readiness_sha, str) or len(readiness_sha) != 64:
        raise AttestationBridgeError("score readiness receipt identity missing")
    if analysis.get("readiness_report_sha256") != readiness_sha:
        raise AttestationBridgeError("analysis readiness receipt identity drift")

    try:
        workload = qe.validate_workload(workload)
        host = qe.validate_host(host)
        candidate = qe.validate_candidate(candidate, workload, host)
    except qe.QualifiedExecutionError as exc:
        raise AttestationBridgeError(f"invalid generic qualification artifacts: {exc}") from exc

    integrated_binding = study.get("integrated_binding")
    expected_binding = {
        "config_id": study.get("arms", {}).get("integrated"),
        "candidate_policy_sha256": qe.artifact_sha256(candidate),
        "workload_contract_sha256": qe.artifact_sha256(workload),
        "host_manifest_sha256": qe.artifact_sha256(host),
    }
    if integrated_binding != expected_binding:
        raise AttestationBridgeError("Study Contract integrated artifact binding drift")
    if prereg.get("workload_id") != workload["workload_id"]:
        raise AttestationBridgeError("preregistration/workload identity drift")

    metric_map = observed_metrics(score, prereg)
    gate_results = []
    for requirement in workload["empirical_requirements"]:
        metric_id = requirement["metric_id"]
        if metric_id not in metric_map:
            raise AttestationBridgeError(f"score does not expose Workload Contract metric: {metric_id}")
        observed, unit = metric_map[metric_id]
        if unit != requirement["unit"]:
            raise AttestationBridgeError(f"metric unit differs from Workload Contract: {metric_id}")
        gate_results.append({
            "requirement_id": requirement["requirement_id"],
            "passed": gate_passes(requirement, observed),
            "observed": observed,
            "unit": unit,
        })

    if not all(row["passed"] for row in gate_results):
        raise AttestationBridgeError("enterprise decision conflicts with Workload Contract empirical gate")
    if decision.get("mandatory_violations") != 0:
        raise AttestationBridgeError("qualified decision contains mandatory violations")

    economics = prereg.get("records", {}).get("economics")
    if not isinstance(economics, dict):
        raise AttestationBridgeError("economics record missing")
    authority_id = owner.get("authority_id")
    if not isinstance(authority_id, str) or not authority_id:
        raise AttestationBridgeError("owner authority identity missing")

    evaluation_package = {
        "format": EVALUATION_PACKAGE_FORMAT,
        "format_version": FORMAT_VERSION,
        "preregistration_sha256": sha256(prereg_path),
        "study_contract_sha256": sha256(study_path),
        "questions_sha256": study.get("questions_sha256"),
        "readiness_report_sha256": readiness_sha,
        "run_manifest_sha256": score.get("run_manifest_sha256"),
        "observations_sha256": score.get("observations_sha256"),
        "adjudications_sha256": score.get("adjudications_sha256"),
        "score_sha256": sha256(score_path),
        "analysis_report_sha256": sha256(analysis_path),
        "owner_decision_sha256": sha256(owner_path),
        "qualification_decision_sha256": sha256(decision_path),
        "candidate_policy_sha256": qe.artifact_sha256(candidate),
        "workload_contract_sha256": qe.artifact_sha256(workload),
        "host_manifest_sha256": qe.artifact_sha256(host),
        "runner_source_sha256": study.get("runner_source_sha256"),
        "readiness_source_sha256": study.get("readiness_source_sha256"),
        "scorer_source_sha256": study.get("scorer_source_sha256"),
        "analysis_source_sha256": study.get("analysis_source_sha256"),
        "decision_source_sha256": study.get("decision_source_sha256"),
        "economic_model_sha256": canonical_sha256(economics),
    }
    for field, value in evaluation_package.items():
        if field in {"format", "format_version"}:
            continue
        if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise AttestationBridgeError(f"evaluation package digest missing or invalid: {field}")
    evaluation_package_sha256 = canonical_sha256(evaluation_package)

    attestation = {
        "v": 1,
        "format": "exactscope.qualification-attestation",
        "format_version": "0.1",
        "attestation_id": attestation_id.strip(),
        "status": "qualified",
        "candidate_policy_sha256": qe.artifact_sha256(candidate),
        "workload_contract_sha256": qe.artifact_sha256(workload),
        "host_manifest_sha256": qe.artifact_sha256(host),
        "authority": {
            "kind": "workload-owner",
            "authority_id": authority_id,
            "process_sha256": study["decision_source_sha256"],
        },
        "evidence": {
            "evaluation_package_sha256": evaluation_package_sha256,
            "analysis_sha256": sha256(analysis_path),
            "scorer_sha256": study["scorer_source_sha256"],
            "economic_model_sha256": evaluation_package["economic_model_sha256"],
        },
        "validity": {
            "scope": host["qualification_scope"],
            "issued_epoch_s": issued_epoch_s,
            "valid_until_epoch_s": valid_until_epoch_s,
            "observation_policy_id": observation_policy_id,
        },
        "gate_results": gate_results,
        "mandatory_violations": 0,
    }
    try:
        validated = qe.validate_attestation(attestation, candidate, workload, host)
    except qe.QualifiedExecutionError as exc:
        raise AttestationBridgeError(f"generic attestation validation failed: {exc}") from exc

    bridge = {
        "format": BRIDGE_FORMAT,
        "format_version": FORMAT_VERSION,
        "enterprise_decision_sha256": sha256(decision_path),
        "study_contract_sha256": sha256(study_path),
        "candidate_policy_sha256": qe.artifact_sha256(candidate),
        "workload_contract_sha256": qe.artifact_sha256(workload),
        "host_manifest_sha256": qe.artifact_sha256(host),
        "evaluation_package": evaluation_package,
        "evaluation_package_sha256": evaluation_package_sha256,
        "attestation": validated,
        "qualified_execution_profile_emitted": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_bytes(bridge))
    if attestation_output is not None:
        attestation_output.parent.mkdir(parents=True, exist_ok=True)
        attestation_output.write_bytes(canonical_bytes(validated))
    return bridge


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--score", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--owner-decision", type=Path, required=True)
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--analysis-source", type=Path, required=True)
    parser.add_argument("--decision-source", type=Path, required=True)
    parser.add_argument("--workload-contract", type=Path, required=True)
    parser.add_argument("--host-manifest", type=Path, required=True)
    parser.add_argument("--candidate-policy", type=Path, required=True)
    parser.add_argument("--attestation-id", required=True)
    parser.add_argument("--issued-epoch-s", type=int, required=True)
    parser.add_argument("--valid-until-epoch-s", type=int)
    parser.add_argument("--observation-policy-id")
    parser.add_argument("--output", type=Path, required=True, help="enterprise attestation bridge output")
    parser.add_argument("--attestation-output", type=Path, help="optional standalone generic Qualification Attestation")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = build_attestation(
            args.prereg,
            args.study,
            args.score,
            args.analysis,
            args.owner_decision,
            args.decision,
            args.analysis_source,
            args.decision_source,
            args.workload_contract,
            args.host_manifest,
            args.candidate_policy,
            args.attestation_id,
            args.issued_epoch_s,
            args.valid_until_epoch_s,
            args.observation_policy_id,
            args.output,
            args.attestation_output,
        )
    except (AttestationBridgeError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
