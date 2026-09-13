#!/usr/bin/env python3
"""Freeze the executable enterprise DocQA study contract above prereg v0.1.

The lower preregistration freezes Base/Integrated, workload, retrieval, competence,
scoring, timing, economics and analysis records. This layer adds the mandatory
ordinary deployable alternative and refuses to proceed unless the actual runner and
scorer source files still match the preregistration identities.
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
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from grounding_canonical import canonical_bytes, loads  # noqa: E402
import qualified_execution as qe  # noqa: E402

FORMAT = "exactscope.enterprise-docqa-study-contract"
FORMAT_VERSION = "0.1"
ALTERNATIVE_FORMAT = "exactscope.enterprise-docqa-alternative-config"
PREREG_FORMAT = "exactscope.enterprise-docqa-preregistration"
EXECUTABLE_COUNTERS = {
    "model_service_ms",
    "model_calls",
    "input_tokens",
    "output_tokens",
    "retrieval_units",
    "evidence_bytes",
    "human_review_events",
    "unacceptable_error_count",
    "integration_units",
    "qualification_units",
    "refresh_units",
    "maintenance_units",
}
MEASURED_COUNTERS = {
    "model_service_ms",
    "model_calls",
    "input_tokens",
    "output_tokens",
    "retrieval_units",
    "evidence_bytes",
    "human_review_events",
    "unacceptable_error_count",
}
QUESTION_CLASSES = {"answerable", "unanswerable", "ambiguous-or-conflicting", "retrieval-stress"}
FORBIDDEN_QUESTION_KEYS = {
    "answer",
    "answers",
    "accepted_answers",
    "expected_answer",
    "gold",
    "gold_answer",
    "label",
    "reference_answer",
    "supporting_facts",
    "target",
}


class StudyContractError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise StudyContractError(f"cannot hash file: {path}") from exc
    return digest.hexdigest()


def load_object(path: Path, *, canonical: bool = True) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise StudyContractError(f"cannot load JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise StudyContractError(f"expected JSON object: {path}")
    if canonical and raw != canonical_bytes(value):
        raise StudyContractError(f"object is not canonical JSON: {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise StudyContractError(f"cannot read JSONL: {path}") from exc
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(raw.splitlines(), 1):
        if not line:
            raise StudyContractError(f"blank JSONL row: {path}:{index}")
        try:
            value = loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise StudyContractError(f"invalid JSONL row: {path}:{index}") from exc
        if not isinstance(value, dict) or line != canonical_bytes(value):
            raise StudyContractError(f"noncanonical JSONL row: {path}:{index}")
        rows.append(value)
    return rows


def validate_questions_freeze(path: Path, prereg: dict[str, Any]) -> dict[str, Any]:
    rows = load_jsonl(path)
    expected_count = prereg.get("records", {}).get("analysis", {}).get("confirmatory_sample_size")
    if type(expected_count) is not int or expected_count <= 0:
        raise StudyContractError("preregistration confirmatory sample size missing")
    if len(rows) != expected_count:
        raise StudyContractError("confirmatory question count differs from preregistration")
    item_ids: set[str] = set()
    group_ids: set[str] = set()
    for index, row in enumerate(rows):
        forbidden = set(row) & FORBIDDEN_QUESTION_KEYS
        if forbidden:
            raise StudyContractError(f"questions[{index}] exposes forbidden fields: {sorted(forbidden)}")
        item_id = text(row.get("item_id"), f"questions[{index}].item_id")
        group_id = text(row.get("group_id"), f"questions[{index}].group_id")
        if item_id in item_ids:
            raise StudyContractError("duplicate confirmatory item_id")
        if group_id in group_ids:
            raise StudyContractError("confirmatory question groups must be disjoint within the frozen sample")
        item_ids.add(item_id)
        group_ids.add(group_id)
        if row.get("question_class") not in QUESTION_CLASSES:
            raise StudyContractError("unsupported confirmatory question_class")
        text(row.get("question"), f"questions[{index}].question")
    return {"questions_sha256": sha256(path), "confirmatory_question_count": len(rows)}


def text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StudyContractError(f"{label} must be nonempty text")
    return value.strip()


def positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise StudyContractError(f"{label} must be a positive integer")
    return value


def validate_fixed_counters(value: Any, label: str) -> dict[str, int]:
    if not isinstance(value, dict):
        raise StudyContractError(f"{label} must be an object")
    out: dict[str, int] = {}
    for name, count in value.items():
        if name not in EXECUTABLE_COUNTERS - MEASURED_COUNTERS:
            raise StudyContractError(f"{label} contains unsupported/non-fixed counter: {name}")
        if type(count) is not int or count < 0:
            raise StudyContractError(f"{label}.{name} must be a nonnegative integer")
        out[name] = count
    return out


def validate_alternative(record: dict[str, Any], prereg: dict[str, Any]) -> dict[str, Any]:
    if record.get("format") != ALTERNATIVE_FORMAT or record.get("format_version") != FORMAT_VERSION:
        raise StudyContractError("unsupported alternative record identity")
    for field in (
        "config_id",
        "model_identity",
        "runtime_identity",
        "tokenizer_template_identity",
        "retrieval_identity",
        "generation_settings_identity",
        "answer_policy_identity",
        "development_evidence_identity",
        "ordinary_alternative_kind",
    ):
        text(record.get(field), f"alternative.{field}")
    positive_int(record.get("max_model_calls"), "alternative.max_model_calls")
    for field in ("runtime_answer_repair", "second_model_judge", "adaptive_policy_routing", "uses_exactscope"):
        if record.get(field) is not False:
            raise StudyContractError(f"alternative.{field} must be false")
    if record.get("development_eligible") is not True:
        raise StudyContractError("alternative must be development-eligible before confirmatory freeze")
    if record.get("ordinary_deployable") is not True:
        raise StudyContractError("alternative must be ordinary_deployable=true")

    records = prereg.get("records")
    if not isinstance(records, dict):
        raise StudyContractError("preregistration records missing")
    retrieval = records.get("retrieval")
    if not isinstance(retrieval, dict):
        raise StudyContractError("preregistration retrieval record missing")
    if record["retrieval_identity"] != retrieval.get("retriever_identity"):
        raise StudyContractError("alternative retrieval identity differs from frozen study retrieval")

    primary = prereg.get("primary_comparison")
    if not isinstance(primary, dict):
        raise StudyContractError("preregistration primary comparison missing")
    reserved = {primary.get("base_config_id"), primary.get("integrated_config_id")}
    if record["config_id"] in reserved:
        raise StudyContractError("alternative config identity collides with Base/Integrated")
    validate_fixed_counters(record.get("fixed_economic_counters"), "alternative.fixed_economic_counters")
    return record


def validate_prereg(prereg: dict[str, Any], prereg_path: Path, runner_source: Path, scorer_source: Path) -> None:
    if prereg.get("format") != PREREG_FORMAT or prereg.get("format_version") != FORMAT_VERSION:
        raise StudyContractError("unsupported preregistration identity")
    if prereg.get("confirmatory_status") != "frozen-unscored":
        raise StudyContractError("preregistration is not frozen-unscored")
    if prereg.get("post_score_rule_changes_allowed") is not False:
        raise StudyContractError("preregistration permits post-score rule changes")
    if prereg.get("fever_stage1_heldout_reuse") is not False:
        raise StudyContractError("preregistration permits retired FEVER held-out reuse")

    evidence = prereg.get("evidence_contract")
    if not isinstance(evidence, dict):
        raise StudyContractError("preregistration lacks frozen evidence_contract")
    if evidence.get("evidence_composition") not in {"single-source-precision", "multi-source-coverage"}:
        raise StudyContractError("unsupported evidence composition")
    budget = evidence.get("evidence_budget_bytes")
    if type(budget) is not int or not 256 <= budget <= 1048576:
        raise StudyContractError("evidence budget is outside the supported bound")
    positive_int(evidence.get("max_projected_items"), "evidence_contract.max_projected_items")
    top_k = positive_int(evidence.get("retrieval_top_k_limit"), "evidence_contract.retrieval_top_k_limit")
    if evidence["max_projected_items"] > top_k:
        raise StudyContractError("evidence projected-item cap exceeds retrieval top-k")
    text(evidence.get("evidence_policy_id"), "evidence_contract.evidence_policy_id")

    records = prereg.get("records")
    if not isinstance(records, dict):
        raise StudyContractError("preregistration records missing")
    economics = records.get("economics")
    if not isinstance(economics, dict):
        raise StudyContractError("preregistration economics record missing")
    components = economics.get("components")
    if not isinstance(components, list) or not components:
        raise StudyContractError("economics components missing")
    for index, component in enumerate(components):
        if not isinstance(component, dict):
            raise StudyContractError(f"economics.components[{index}] must be an object")
        counter = component.get("counter")
        if counter not in EXECUTABLE_COUNTERS:
            raise StudyContractError(f"economics.components[{index}] lacks an executable counter")
        coefficient = component.get("coefficient")
        if type(coefficient) is not int or coefficient < 0:
            raise StudyContractError(f"economics.components[{index}].coefficient must be a nonnegative integer")
    fixed_by_arm = economics.get("fixed_counters_by_arm")
    if not isinstance(fixed_by_arm, dict) or set(fixed_by_arm) != {"base", "integrated"}:
        raise StudyContractError("economics.fixed_counters_by_arm must freeze base and integrated")
    validate_fixed_counters(fixed_by_arm["base"], "economics.fixed_counters_by_arm.base")
    validate_fixed_counters(fixed_by_arm["integrated"], "economics.fixed_counters_by_arm.integrated")

    source_sha = prereg.get("source_sha256")
    if not isinstance(source_sha, dict):
        raise StudyContractError("preregistration source identities missing")
    if not runner_source.is_file() or sha256(runner_source) != source_sha.get("runner"):
        raise StudyContractError("runner source differs from preregistered identity")
    if not scorer_source.is_file() or sha256(scorer_source) != source_sha.get("scorer"):
        raise StudyContractError("scorer source differs from preregistered identity")
    if sha256(prereg_path) == source_sha.get("runner") or sha256(prereg_path) == source_sha.get("scorer"):
        raise StudyContractError("preregistration file cannot masquerade as runner/scorer source")


def freeze(
    prereg_path: Path,
    alternative_path: Path,
    workload_contract_path: Path,
    host_manifest_path: Path,
    candidate_policy_path: Path,
    questions_path: Path,
    runner_source: Path,
    scorer_source: Path,
    analysis_source: Path,
    decision_source: Path,
    readiness_source: Path,
    output: Path,
) -> dict[str, Any]:
    if output.exists():
        raise StudyContractError("study contract output already exists")
    prereg = load_object(prereg_path)
    validate_prereg(prereg, prereg_path, runner_source, scorer_source)
    question_identity = validate_questions_freeze(questions_path, prereg)
    if not analysis_source.is_file():
        raise StudyContractError("analysis source does not exist")
    if not decision_source.is_file():
        raise StudyContractError("decision source does not exist")
    if not readiness_source.is_file():
        raise StudyContractError("readiness source does not exist")
    try:
        workload = qe.validate_workload(load_object(workload_contract_path))
        host = qe.validate_host(load_object(host_manifest_path))
        candidate = qe.validate_candidate(load_object(candidate_policy_path), workload, host)
    except qe.QualifiedExecutionError as exc:
        raise StudyContractError(f"invalid north-star artifact binding: {exc}") from exc
    if prereg.get("workload_id") != workload["workload_id"]:
        raise StudyContractError("preregistration workload differs from Workload Contract")
    evidence = prereg["evidence_contract"]
    if workload.get("evidence_composition", "unspecified") != evidence["evidence_composition"]:
        raise StudyContractError("Workload Contract evidence composition differs from preregistration")
    if workload.get("evidence_budget_bytes") != evidence["evidence_budget_bytes"]:
        raise StudyContractError("Workload Contract evidence budget differs from preregistration")
    if workload["evidence_policy_id"] != evidence["evidence_policy_id"]:
        raise StudyContractError("Workload Contract evidence policy differs from preregistration")
    execution = candidate["execution"]
    if execution.get("evidence_composition", "unspecified") != evidence["evidence_composition"]:
        raise StudyContractError("Candidate evidence composition differs from preregistration")
    if execution.get("evidence_budget_bytes") != evidence["evidence_budget_bytes"]:
        raise StudyContractError("Candidate evidence budget differs from preregistration")
    if execution["evidence_policy_id"] != evidence["evidence_policy_id"]:
        raise StudyContractError("Candidate evidence policy differs from preregistration")
    alternative = validate_alternative(load_object(alternative_path), prereg)
    primary = prereg["primary_comparison"]
    record = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "state": "frozen-unscored",
        "preregistration_sha256": sha256(prereg_path),
        "alternative_sha256": sha256(alternative_path),
        "questions_sha256": question_identity["questions_sha256"],
        "confirmatory_question_count": question_identity["confirmatory_question_count"],
        "arms": {
            "base": primary["base_config_id"],
            "integrated": primary["integrated_config_id"],
            "alternative": alternative["config_id"],
        },
        "integrated_binding": {
            "config_id": primary["integrated_config_id"],
            "candidate_policy_sha256": qe.artifact_sha256(candidate),
            "workload_contract_sha256": qe.artifact_sha256(workload),
            "host_manifest_sha256": qe.artifact_sha256(host),
        },
        "evidence_contract": prereg["evidence_contract"],
        "alternative": alternative,
        "fixed_counters_by_arm": {
            "base": prereg["records"]["economics"]["fixed_counters_by_arm"]["base"],
            "integrated": prereg["records"]["economics"]["fixed_counters_by_arm"]["integrated"],
            "alternative": alternative["fixed_economic_counters"],
        },
        "runner_source_sha256": sha256(runner_source),
        "scorer_source_sha256": sha256(scorer_source),
        "analysis_source_sha256": sha256(analysis_source),
        "decision_source_sha256": sha256(decision_source),
        "readiness_source_sha256": sha256(readiness_source),
        "ordinary_alternative_required": True,
        "confirmatory_outcomes_visible_at_freeze": False,
        "post_score_rule_changes_allowed": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_bytes(record))
    return record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--alternative", type=Path, required=True)
    parser.add_argument("--workload-contract", type=Path, required=True)
    parser.add_argument("--host-manifest", type=Path, required=True)
    parser.add_argument("--candidate-policy", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--runner-source", type=Path, required=True)
    parser.add_argument("--scorer-source", type=Path, required=True)
    parser.add_argument("--analysis-source", type=Path, required=True)
    parser.add_argument("--decision-source", type=Path, required=True)
    parser.add_argument("--readiness-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        record = freeze(
            args.prereg,
            args.alternative,
            args.workload_contract,
            args.host_manifest,
            args.candidate_policy,
            args.questions,
            args.runner_source,
            args.scorer_source,
            args.analysis_source,
            args.decision_source,
            args.readiness_source,
            args.output,
        )
    except (StudyContractError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
