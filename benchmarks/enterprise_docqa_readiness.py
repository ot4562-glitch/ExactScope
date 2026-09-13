#!/usr/bin/env python3
"""Fail-closed preflight for the first enterprise DocQA confirmatory model call.

This command performs no retrieval and no model inference. It revalidates the frozen
preregistration, Study Contract, runner-visible question set, ordinary alternative,
exact Candidate/Workload/Host binding, executable source identities and fixed economic
counters. Only a complete unchanged pre-outcome bundle receives
READY_FOR_CONFIRMATORY_EXECUTION.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "tools", ROOT / "benchmarks"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from grounding_canonical import canonical_bytes  # noqa: E402
import enterprise_docqa_observations as observations  # noqa: E402
import enterprise_docqa_preregister as prereg_tool  # noqa: E402
import enterprise_docqa_study_contract as study_contract  # noqa: E402
import qualified_execution as qe  # noqa: E402

FORMAT = "exactscope.enterprise-docqa-readiness"
FORMAT_VERSION = "0.1"


class ReadinessError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return observations.sha256(path)


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ReadinessError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _load(path: Path) -> dict[str, Any]:
    try:
        return observations.load_object(path)
    except observations.ObservationError as exc:
        raise ReadinessError(str(exc)) from exc


def _expected_evidence(records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "evidence_composition": records["workload"]["evidence_composition"],
        "evidence_policy_id": records["integrated"]["evidence_policy_id"],
        "evidence_budget_bytes": records["workload"]["evidence_budget_bytes"],
        "max_projected_items": records["integrated"]["max_projected_items"],
        "retrieval_top_k_limit": records["retrieval"]["top_k_limit"],
    }


def check_readiness(
    prereg_path: Path,
    study_path: Path,
    questions_path: Path,
    alternative_path: Path,
    workload_path: Path,
    host_path: Path,
    candidate_path: Path,
    runner_source: Path,
    scorer_source: Path,
    analysis_source: Path,
    decision_source: Path,
    run_output: Path,
    report_output: Path,
) -> dict[str, Any]:
    if report_output.exists():
        raise ReadinessError("readiness report output already exists")
    if run_output.exists():
        raise ReadinessError("confirmatory run output already exists; resume/reuse is forbidden")
    if run_output.resolve() == report_output.resolve():
        raise ReadinessError("readiness report and confirmatory run output must be distinct")

    prereg = _load(prereg_path)
    study = _load(study_path)
    if prereg.get("format") != prereg_tool.PREREG_FORMAT or prereg.get("format_version") != prereg_tool.FORMAT_VERSION:
        raise ReadinessError("unsupported preregistration identity")
    if prereg.get("confirmatory_status") != "frozen-unscored":
        raise ReadinessError("preregistration is not frozen-unscored")
    if prereg.get("post_score_rule_changes_allowed") is not False:
        raise ReadinessError("preregistration permits post-score rule changes")
    if prereg.get("fever_stage1_heldout_reuse") is not False:
        raise ReadinessError("preregistration permits retired FEVER held-out reuse")

    records = prereg.get("records")
    try:
        optimizer_enabled = prereg_tool.validate_record_objects(records)
    except prereg_tool.DocQAPreregistrationError as exc:
        raise ReadinessError(f"embedded preregistration record invalid: {exc}") from exc
    if prereg.get("optimizer_branch_enabled") is not optimizer_enabled:
        raise ReadinessError("optimizer branch state differs from embedded frozen records")
    primary = prereg.get("primary_comparison")
    if primary != {
        "base_config_id": records["base"]["config_id"],
        "integrated_config_id": records["integrated"]["config_id"],
    }:
        raise ReadinessError("preregistration primary comparison drift")
    if prereg.get("workload_id") != records["workload"]["workload_id"]:
        raise ReadinessError("preregistration workload identity drift")
    if prereg.get("evidence_contract") != _expected_evidence(records):
        raise ReadinessError("preregistration evidence contract drift")

    record_sha = prereg.get("record_sha256")
    if not isinstance(record_sha, dict) or set(record_sha) != set(prereg_tool.RECORD_FORMATS):
        raise ReadinessError("preregistration record digest set is incomplete")
    for role, digest in record_sha.items():
        _digest(digest, f"record_sha256.{role}")
    source_sha = prereg.get("source_sha256")
    if not isinstance(source_sha, dict):
        raise ReadinessError("preregistration source identities missing")
    for role in ("runner", "scorer", "preregister_tool"):
        _digest(source_sha.get(role), f"source_sha256.{role}")
    if source_sha["preregister_tool"] != sha256(Path(prereg_tool.__file__)):
        raise ReadinessError("preregistration tool source drift")

    try:
        study_contract.validate_prereg(prereg, prereg_path, runner_source, scorer_source)
    except study_contract.StudyContractError as exc:
        raise ReadinessError(str(exc)) from exc
    if study.get("format") != study_contract.FORMAT or study.get("format_version") != FORMAT_VERSION:
        raise ReadinessError("unsupported Study Contract identity")
    if study.get("state") != "frozen-unscored":
        raise ReadinessError("Study Contract is not frozen-unscored")
    if study.get("preregistration_sha256") != sha256(prereg_path):
        raise ReadinessError("Study Contract/preregistration identity drift")
    if study.get("ordinary_alternative_required") is not True:
        raise ReadinessError("Study Contract does not require the ordinary alternative")
    if study.get("confirmatory_outcomes_visible_at_freeze") is not False:
        raise ReadinessError("Study Contract was not frozen before confirmatory outcomes")
    if study.get("post_score_rule_changes_allowed") is not False:
        raise ReadinessError("Study Contract permits post-score rule changes")

    try:
        question_identity = study_contract.validate_questions_freeze(questions_path, prereg)
    except study_contract.StudyContractError as exc:
        raise ReadinessError(str(exc)) from exc
    if study.get("questions_sha256") != question_identity["questions_sha256"]:
        raise ReadinessError("confirmatory question set differs from frozen Study Contract")
    if study.get("confirmatory_question_count") != question_identity["confirmatory_question_count"]:
        raise ReadinessError("confirmatory question count differs from frozen Study Contract")

    alternative = _load(alternative_path)
    try:
        alternative = study_contract.validate_alternative(alternative, prereg)
    except study_contract.StudyContractError as exc:
        raise ReadinessError(str(exc)) from exc
    if study.get("alternative_sha256") != sha256(alternative_path) or study.get("alternative") != alternative:
        raise ReadinessError("ordinary alternative differs from frozen Study Contract")

    try:
        workload = qe.validate_workload(_load(workload_path))
        host = qe.validate_host(_load(host_path))
        candidate = qe.validate_candidate(_load(candidate_path), workload, host)
    except qe.QualifiedExecutionError as exc:
        raise ReadinessError(f"invalid north-star artifact: {exc}") from exc
    expected_binding = {
        "config_id": records["integrated"]["config_id"],
        "candidate_policy_sha256": qe.artifact_sha256(candidate),
        "workload_contract_sha256": qe.artifact_sha256(workload),
        "host_manifest_sha256": qe.artifact_sha256(host),
    }
    if study.get("integrated_binding") != expected_binding:
        raise ReadinessError("Integrated Candidate/Workload/Host binding drift")
    if workload["workload_id"] != prereg["workload_id"]:
        raise ReadinessError("generic Workload Contract workload identity drift")
    evidence = prereg["evidence_contract"]
    if workload.get("evidence_composition", "unspecified") != evidence["evidence_composition"]:
        raise ReadinessError("generic Workload Contract evidence composition drift")
    if workload.get("evidence_budget_bytes") != evidence["evidence_budget_bytes"]:
        raise ReadinessError("generic Workload Contract evidence budget drift")
    if workload["evidence_policy_id"] != evidence["evidence_policy_id"]:
        raise ReadinessError("generic Workload Contract evidence policy drift")

    source_paths = {
        "runner_source_sha256": runner_source,
        "scorer_source_sha256": scorer_source,
        "analysis_source_sha256": analysis_source,
        "decision_source_sha256": decision_source,
    }
    for field, path in source_paths.items():
        if not path.is_file() or study.get(field) != sha256(path):
            raise ReadinessError(f"{field} differs from frozen Study Contract")
    current_readiness_sha = sha256(Path(__file__))
    if study.get("readiness_source_sha256") != current_readiness_sha:
        raise ReadinessError("readiness implementation differs from frozen Study Contract")
    if study.get("runner_source_sha256") != source_sha["runner"] or study.get("scorer_source_sha256") != source_sha["scorer"]:
        raise ReadinessError("Study Contract runner/scorer identities differ from preregistration")

    expected_fixed = {
        "base": records["economics"]["fixed_counters_by_arm"]["base"],
        "integrated": records["economics"]["fixed_counters_by_arm"]["integrated"],
        "alternative": alternative["fixed_economic_counters"],
    }
    if study.get("fixed_counters_by_arm") != expected_fixed:
        raise ReadinessError("Study Contract fixed economic counters drift")
    if study.get("evidence_contract") != evidence:
        raise ReadinessError("Study Contract evidence contract differs from preregistration")
    if study.get("arms") != {
        "base": records["base"]["config_id"],
        "integrated": records["integrated"]["config_id"],
        "alternative": alternative["config_id"],
    }:
        raise ReadinessError("Study Contract arm identities drift")

    result = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "status": "READY_FOR_CONFIRMATORY_EXECUTION",
        "model_inference_performed": False,
        "retrieval_performed": False,
        "preregistration_sha256": sha256(prereg_path),
        "study_contract_sha256": sha256(study_path),
        "questions_sha256": question_identity["questions_sha256"],
        "confirmatory_question_count": question_identity["confirmatory_question_count"],
        "candidate_policy_sha256": expected_binding["candidate_policy_sha256"],
        "workload_contract_sha256": expected_binding["workload_contract_sha256"],
        "host_manifest_sha256": expected_binding["host_manifest_sha256"],
        "ordinary_alternative_sha256": sha256(alternative_path),
        "readiness_source_sha256": current_readiness_sha,
        "confirmatory_run_output": str(run_output.resolve()),
    }
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_bytes(canonical_bytes(result))
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--alternative", type=Path, required=True)
    parser.add_argument("--workload-contract", type=Path, required=True)
    parser.add_argument("--host-manifest", type=Path, required=True)
    parser.add_argument("--candidate-policy", type=Path, required=True)
    parser.add_argument("--runner-source", type=Path, required=True)
    parser.add_argument("--scorer-source", type=Path, required=True)
    parser.add_argument("--analysis-source", type=Path, required=True)
    parser.add_argument("--decision-source", type=Path, required=True)
    parser.add_argument("--run-output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = check_readiness(
            args.prereg,
            args.study,
            args.questions,
            args.alternative,
            args.workload_contract,
            args.host_manifest,
            args.candidate_policy,
            args.runner_source,
            args.scorer_source,
            args.analysis_source,
            args.decision_source,
            args.run_output,
            args.report_output,
        )
    except (ReadinessError, observations.ObservationError, prereg_tool.DocQAPreregistrationError, study_contract.StudyContractError, qe.QualifiedExecutionError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
