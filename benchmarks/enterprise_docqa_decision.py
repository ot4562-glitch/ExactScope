#!/usr/bin/env python3
"""Gate an enterprise DocQA score before generic qualification attestation.

This stage binds the frozen score, the frozen analysis implementation, the analysis
report and workload-owner decision. It never emits a Qualified Execution Profile.
Only a fully passing decision becomes eligible for conversion into the generic
Qualification Attestation tied to real Workload Contract / Host Manifest artifacts.
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

from grounding_canonical import canonical_bytes, loads  # noqa: E402
import enterprise_docqa_analysis as analyzer  # noqa: E402
import enterprise_docqa_observations as observations  # noqa: E402
import enterprise_docqa_score as scorer  # noqa: E402
import enterprise_docqa_study_contract as study_contract  # noqa: E402

FORMAT_VERSION = "0.1"
ANALYSIS_FORMAT = "exactscope.enterprise-docqa-analysis-report"
OWNER_FORMAT = "exactscope.enterprise-docqa-owner-decision"
DECISION_FORMAT = "exactscope.enterprise-docqa-qualification-decision"
OUTCOMES = {"pass", "fail", "inconclusive"}


class DecisionError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return observations.sha256(path)


def digest_object(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise DecisionError(f"cannot load JSON object: {path}") from exc
    if not isinstance(value, dict) or raw != canonical_bytes(value):
        raise DecisionError(f"noncanonical JSON object: {path}")
    return value


def text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DecisionError(f"{label} must be nonempty text")
    return value.strip()


def validate_analysis(
    analysis: dict[str, Any],
    analysis_path: Path,
    analysis_source_path: Path,
    score_path: Path,
    prereg_path: Path,
    study_path: Path,
    prereg: dict[str, Any],
    study: dict[str, Any],
    score: dict[str, Any],
) -> None:
    if analysis.get("format") != ANALYSIS_FORMAT or analysis.get("format_version") != FORMAT_VERSION:
        raise DecisionError("unsupported analysis report identity")
    if analysis.get("score_sha256") != sha256(score_path):
        raise DecisionError("analysis report score identity drift")
    if analysis.get("preregistration_sha256") != sha256(prereg_path):
        raise DecisionError("analysis report preregistration identity drift")
    if analysis.get("study_contract_sha256") != sha256(study_path):
        raise DecisionError("analysis report study identity drift")
    if not analysis_source_path.is_file() or sha256(analysis_source_path) != study.get("analysis_source_sha256"):
        raise DecisionError("analysis source file differs from frozen Study Contract")
    if analysis.get("analysis_source_sha256") != study.get("analysis_source_sha256"):
        raise DecisionError("analysis implementation identity drift")
    frozen_analysis = prereg.get("records", {}).get("analysis")
    if not isinstance(frozen_analysis, dict):
        raise DecisionError("frozen analysis record missing")
    if analysis.get("analysis_record_sha256") != digest_object(frozen_analysis):
        raise DecisionError("analysis report does not bind frozen analysis record")
    method_id = text(frozen_analysis.get("method_id"), "frozen analysis method_id")
    if analysis.get("method_identity") != method_id:
        raise DecisionError("analysis method identity differs from frozen analysis record")
    if method_id == analyzer.METHOD_ID and analysis.get("method_parameters") != frozen_analysis.get("method_parameters"):
        raise DecisionError("analysis method parameters differ from frozen analysis record")
    for field in (
        "conclusion",
        "integrated_vs_base",
        "integrated_vs_alternative",
        "customer_utility",
        "total_economics",
    ):
        if analysis.get(field) not in OUTCOMES:
            raise DecisionError(f"analysis.{field} is unsupported")
    if type(analysis.get("uncertainty_conclusive")) is not bool:
        raise DecisionError("analysis.uncertainty_conclusive must be boolean")
    violations = analysis.get("mandatory_violations")
    if type(violations) is not int or violations < 0:
        raise DecisionError("analysis.mandatory_violations must be nonnegative integer")
    if analysis.get("post_score_rule_changes_allowed") is not False:
        raise DecisionError("analysis permits post-score rule changes")
    text(analysis.get("analysis_id"), "analysis.analysis_id")
    if sha256(analysis_path) == study.get("analysis_source_sha256"):
        raise DecisionError("analysis report cannot masquerade as analysis source")

    if method_id == analyzer.METHOD_ID:
        comparisons = analysis.get("comparisons")
        if not isinstance(comparisons, dict) or set(comparisons) != {"base", "alternative"}:
            raise DecisionError("paired-bootstrap analysis comparisons missing")
        expected_statuses = {
            "integrated_vs_base": comparisons["base"].get("status"),
            "integrated_vs_alternative": comparisons["alternative"].get("status"),
        }
        for field, expected in expected_statuses.items():
            if expected not in OUTCOMES or analysis.get(field) != expected:
                raise DecisionError(f"analysis {field} conflicts with paired comparison")
        if analysis.get("score_integrated_gate_verdict") != score.get("integrated_gate_verdict"):
            raise DecisionError("analysis integrated gate verdict differs from frozen score")
        if analysis.get("score_commercial_comparison") != score.get("commercial_comparison"):
            raise DecisionError("analysis commercial comparison differs from frozen score")


def validate_owner(
    owner: dict[str, Any],
    analysis_path: Path,
    prereg: dict[str, Any],
) -> None:
    if owner.get("format") != OWNER_FORMAT or owner.get("format_version") != FORMAT_VERSION:
        raise DecisionError("unsupported owner decision identity")
    if owner.get("analysis_report_sha256") != sha256(analysis_path):
        raise DecisionError("owner decision analysis identity drift")
    workload_id = prereg.get("workload_id")
    if owner.get("workload_id") != workload_id:
        raise DecisionError("owner decision workload identity drift")
    text(owner.get("decision_id"), "owner.decision_id")
    text(owner.get("authority_id"), "owner.authority_id")
    for field in (
        "owner_approved",
        "customer_utility_accepted",
        "total_economics_accepted",
        "ordinary_alternative_considered",
        "no_post_score_exception",
    ):
        if type(owner.get(field)) is not bool:
            raise DecisionError(f"owner.{field} must be boolean")


def _derive_status(score: dict[str, Any], analysis: dict[str, Any], owner: dict[str, Any]) -> str:
    score_pass = score.get("integrated_gate_verdict") == "GATES_PASSED_CANDIDATE"
    analysis_fields = (
        analysis["conclusion"],
        analysis["integrated_vs_base"],
        analysis["integrated_vs_alternative"],
        analysis["customer_utility"],
        analysis["total_economics"],
    )
    owner_pass = all(
        owner[field]
        for field in (
            "owner_approved",
            "customer_utility_accepted",
            "total_economics_accepted",
            "ordinary_alternative_considered",
            "no_post_score_exception",
        )
    )
    if not score_pass or "fail" in analysis_fields or analysis["mandatory_violations"] != 0 or not owner_pass:
        return "failed"
    if "inconclusive" in analysis_fields or not analysis["uncertainty_conclusive"]:
        return "inconclusive"
    return "qualified"


def validate_decision_record(
    record: dict[str, Any],
    prereg_path: Path,
    study_path: Path,
    score_path: Path,
    analysis_path: Path,
    analysis_source_path: Path,
    owner_path: Path,
) -> dict[str, Any]:
    prereg = load_object(prereg_path)
    study = load_object(study_path)
    score = load_object(score_path)
    analysis = load_object(analysis_path)
    owner = load_object(owner_path)
    if study.get("format") != study_contract.FORMAT or study.get("state") != "frozen-unscored":
        raise DecisionError("invalid frozen study contract")
    if study.get("preregistration_sha256") != sha256(prereg_path):
        raise DecisionError("study/preregistration identity drift")
    questions_sha = study.get("questions_sha256")
    if not isinstance(questions_sha, str) or len(questions_sha) != 64 or any(ch not in "0123456789abcdef" for ch in questions_sha):
        raise DecisionError("study frozen question identity missing")
    frozen_count = prereg.get("records", {}).get("analysis", {}).get("confirmatory_sample_size")
    if type(frozen_count) is not int or frozen_count < 1 or study.get("confirmatory_question_count") != frozen_count:
        raise DecisionError("study frozen question count differs from preregistration")
    if study.get("ordinary_alternative_required") is not True:
        raise DecisionError("study does not require the ordinary alternative")
    if study.get("post_score_rule_changes_allowed") is not False:
        raise DecisionError("study permits post-score rule changes")
    if study.get("confirmatory_outcomes_visible_at_freeze") is not False:
        raise DecisionError("study was not frozen before confirmatory outcomes")
    if study.get("decision_source_sha256") != sha256(Path(__file__)):
        raise DecisionError("decision implementation identity drift")
    if score.get("format") != scorer.SCORE_FORMAT or score.get("format_version") != FORMAT_VERSION:
        raise DecisionError("unsupported score identity")
    if score.get("study_contract_sha256") != sha256(study_path):
        raise DecisionError("score/study identity drift")
    if score.get("preregistration_sha256") != sha256(prereg_path):
        raise DecisionError("score/preregistration identity drift")
    if score.get("qualified_execution_profile_emitted") is not False:
        raise DecisionError("score illegally claims profile emission")
    validate_analysis(
        analysis,
        analysis_path,
        analysis_source_path,
        score_path,
        prereg_path,
        study_path,
        prereg,
        study,
        score,
    )
    validate_owner(owner, analysis_path, prereg)
    expected_status = _derive_status(score, analysis, owner)
    expected = {
        "format": DECISION_FORMAT,
        "format_version": FORMAT_VERSION,
        "status": expected_status,
        "preregistration_sha256": sha256(prereg_path),
        "study_contract_sha256": sha256(study_path),
        "score_sha256": sha256(score_path),
        "analysis_report_sha256": sha256(analysis_path),
        "owner_decision_sha256": sha256(owner_path),
        "analysis_source_sha256": study["analysis_source_sha256"],
        "decision_source_sha256": study["decision_source_sha256"],
        "ordinary_alternative_included": True,
        "mandatory_violations": analysis["mandatory_violations"],
        "generic_attestation_eligible": expected_status == "qualified",
        "qualified_execution_profile_emitted": False,
    }
    for field, value in expected.items():
        if record.get(field) != value:
            raise DecisionError(f"qualification decision field drift: {field}")
    note = record.get("note")
    if not isinstance(note, str) or not note:
        raise DecisionError("qualification decision note missing")
    if set(record) != set(expected) | {"note"}:
        raise DecisionError("qualification decision contains unsupported fields")
    return record


def decide(
    prereg_path: Path,
    study_path: Path,
    score_path: Path,
    analysis_path: Path,
    analysis_source_path: Path,
    owner_path: Path,
    output: Path,
) -> dict[str, Any]:
    if output.exists():
        raise DecisionError("decision output already exists")
    prereg = load_object(prereg_path)
    study = load_object(study_path)
    score = load_object(score_path)
    analysis = load_object(analysis_path)
    owner = load_object(owner_path)

    if study.get("format") != study_contract.FORMAT or study.get("state") != "frozen-unscored":
        raise DecisionError("invalid frozen study contract")
    if study.get("preregistration_sha256") != sha256(prereg_path):
        raise DecisionError("study/preregistration identity drift")
    questions_sha = study.get("questions_sha256")
    if not isinstance(questions_sha, str) or len(questions_sha) != 64 or any(ch not in "0123456789abcdef" for ch in questions_sha):
        raise DecisionError("study frozen question identity missing")
    frozen_count = prereg.get("records", {}).get("analysis", {}).get("confirmatory_sample_size")
    if type(frozen_count) is not int or frozen_count < 1 or study.get("confirmatory_question_count") != frozen_count:
        raise DecisionError("study frozen question count differs from preregistration")
    if study.get("ordinary_alternative_required") is not True:
        raise DecisionError("study does not require the ordinary alternative")
    if study.get("post_score_rule_changes_allowed") is not False:
        raise DecisionError("study permits post-score rule changes")
    if study.get("confirmatory_outcomes_visible_at_freeze") is not False:
        raise DecisionError("study was not frozen before confirmatory outcomes")
    if study.get("decision_source_sha256") != sha256(Path(__file__)):
        raise DecisionError("decision implementation identity drift")
    if score.get("format") != scorer.SCORE_FORMAT or score.get("format_version") != FORMAT_VERSION:
        raise DecisionError("unsupported score identity")
    if score.get("study_contract_sha256") != sha256(study_path):
        raise DecisionError("score/study identity drift")
    if score.get("preregistration_sha256") != sha256(prereg_path):
        raise DecisionError("score/preregistration identity drift")
    if score.get("qualified_execution_profile_emitted") is not False:
        raise DecisionError("score illegally claims profile emission")

    validate_analysis(
        analysis,
        analysis_path,
        analysis_source_path,
        score_path,
        prereg_path,
        study_path,
        prereg,
        study,
        score,
    )
    validate_owner(owner, analysis_path, prereg)

    status = _derive_status(score, analysis, owner)

    result = {
        "format": DECISION_FORMAT,
        "format_version": FORMAT_VERSION,
        "status": status,
        "preregistration_sha256": sha256(prereg_path),
        "study_contract_sha256": sha256(study_path),
        "score_sha256": sha256(score_path),
        "analysis_report_sha256": sha256(analysis_path),
        "owner_decision_sha256": sha256(owner_path),
        "analysis_source_sha256": study["analysis_source_sha256"],
        "decision_source_sha256": study["decision_source_sha256"],
        "ordinary_alternative_included": True,
        "mandatory_violations": analysis["mandatory_violations"],
        "generic_attestation_eligible": status == "qualified",
        "qualified_execution_profile_emitted": False,
        "note": "Qualified status here is only eligibility to construct the generic Qualification Attestation after binding the exact Candidate Execution Policy, Workload Contract and Host Capability Manifest.",
    }
    validate_decision_record(
        result,
        prereg_path,
        study_path,
        score_path,
        analysis_path,
        analysis_source_path,
        owner_path,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_bytes(result))
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--score", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--analysis-source", type=Path, required=True)
    parser.add_argument("--owner-decision", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = decide(
            args.prereg,
            args.study,
            args.score,
            args.analysis,
            args.analysis_source,
            args.owner_decision,
            args.output,
        )
    except (DecisionError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
