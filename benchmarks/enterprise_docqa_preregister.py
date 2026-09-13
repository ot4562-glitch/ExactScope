#!/usr/bin/env python3
"""Validate and freeze a non-scoring enterprise document-QA preregistration.

This tool deliberately does not run a model, retrieve documents, score answers, or
choose policy thresholds. It only refuses incomplete / outcome-flexible study
specifications and binds approved records plus runner/scorer source identities.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from grounding_canonical import canonical_bytes, loads  # noqa: E402

FORMAT_VERSION = "0.1"
PREREG_FORMAT = "exactscope.enterprise-docqa-preregistration"
PLACEHOLDER_RE = re.compile(r"\b(?:TBD|TODO|FIXME|PLACEHOLDER|FILL[ -]?ME)\b", re.IGNORECASE)

RECORD_FORMATS = {
    "workload": "exactscope.enterprise-docqa-workload",
    "retrieval": "exactscope.enterprise-docqa-retrieval",
    "partitions": "exactscope.enterprise-docqa-partitions",
    "competence": "exactscope.enterprise-docqa-competence",
    "base": "exactscope.enterprise-docqa-base-config",
    "integrated": "exactscope.enterprise-docqa-integrated-config",
    "scorer": "exactscope.enterprise-docqa-scorer",
    "timing": "exactscope.enterprise-docqa-timing",
    "economics": "exactscope.enterprise-docqa-economics",
    "analysis": "exactscope.enterprise-docqa-analysis",
    "optimizer": "exactscope.enterprise-docqa-optimizer-branch",
}

QUESTION_CLASSES = {"answerable", "unanswerable", "ambiguous-or-conflicting", "retrieval-stress"}
EVIDENCE_COMPOSITION_POLICIES = {
    "single-source-precision": "precision-context-v5",
    "multi-source-coverage": "multihop-coverage-v1",
}
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
FIXED_COUNTERS = EXECUTABLE_COUNTERS - MEASURED_COUNTERS


class DocQAPreregistrationError(RuntimeError):
    pass


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise DocQAPreregistrationError(f"cannot load JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise DocQAPreregistrationError(f"expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise DocQAPreregistrationError(f"cannot hash file: {path}") from exc
    return digest.hexdigest()


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DocQAPreregistrationError(f"{label} must be nonempty text")
    if PLACEHOLDER_RE.search(value):
        raise DocQAPreregistrationError(f"{label} contains placeholder text")
    return value.strip()


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise DocQAPreregistrationError(f"{label} must be a positive integer")
    return value


def _evidence_budget(value: Any, label: str) -> int:
    budget = _positive_int(value, label)
    if not 256 <= budget <= 1048576:
        raise DocQAPreregistrationError(f"{label} must be between 256 and 1048576 bytes")
    return budget


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise DocQAPreregistrationError(f"{label} must be a nonnegative integer")
    return value


def _validate_fixed_counters(value: Any, label: str) -> dict[str, int]:
    if not isinstance(value, dict):
        raise DocQAPreregistrationError(f"{label} must be an object")
    out: dict[str, int] = {}
    for name, count in value.items():
        if name not in FIXED_COUNTERS:
            raise DocQAPreregistrationError(f"{label} contains unsupported/non-fixed counter: {name}")
        out[name] = _nonnegative_int(count, f"{label}.{name}")
    return out


def _assert_no_placeholders(value: Any, label: str = "record") -> None:
    if isinstance(value, str):
        if PLACEHOLDER_RE.search(value):
            raise DocQAPreregistrationError(f"{label} contains placeholder text")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise DocQAPreregistrationError(f"{label} contains an invalid key")
            _assert_no_placeholders(item, f"{label}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _assert_no_placeholders(item, f"{label}[{index}]")


def _load_record(path: Path, role: str) -> dict[str, Any]:
    record = _load_object(path)
    if record.get("format") != RECORD_FORMATS[role] or record.get("format_version") != FORMAT_VERSION:
        raise DocQAPreregistrationError(f"unsupported {role} record identity")
    _assert_no_placeholders(record, role)
    return record


def _validate_workload(record: dict[str, Any]) -> None:
    _text(record.get("workload_id"), "workload.workload_id")
    _text(record.get("owner_role"), "workload.owner_role")
    if record.get("owner_approved") is not True:
        raise DocQAPreregistrationError("workload must have owner_approved=true")
    _text(record.get("authorized_collection_identity"), "workload.authorized_collection_identity")
    _text(record.get("authority_revision_policy"), "workload.authority_revision_policy")
    classes = record.get("question_classes")
    if not isinstance(classes, list) or set(classes) != QUESTION_CLASSES:
        raise DocQAPreregistrationError("workload question_classes must exactly cover the required four semantic classes")
    _text(record.get("population_definition"), "workload.population_definition")
    _text(record.get("answer_contract"), "workload.answer_contract")
    composition = record.get("evidence_composition")
    if composition not in {"single-source-precision", "multi-source-coverage"}:
        raise DocQAPreregistrationError("workload.evidence_composition must be a frozen supported composition")
    _evidence_budget(record.get("evidence_budget_bytes"), "workload.evidence_budget_bytes")


def _validate_retrieval(record: dict[str, Any]) -> None:
    for field in ("corpus_identity", "retriever_identity", "index_identity", "query_rule_identity"):
        _text(record.get(field), f"retrieval.{field}")
    if record.get("real_host_retrieval") is not True:
        raise DocQAPreregistrationError("retrieval must use real_host_retrieval=true")
    if record.get("oracle_evidence") is not False:
        raise DocQAPreregistrationError("retrieval must freeze oracle_evidence=false")
    if record.get("gold_visible_to_runner") is not False:
        raise DocQAPreregistrationError("retrieval must freeze gold_visible_to_runner=false")
    _positive_int(record.get("top_k_limit"), "retrieval.top_k_limit")


def _validate_partitions(record: dict[str, Any], optimizer_enabled: bool) -> None:
    if record.get("groups_disjoint") is not True:
        raise DocQAPreregistrationError("partitions must freeze groups_disjoint=true")
    if record.get("confirmatory_uninspected") is not True:
        raise DocQAPreregistrationError("partitions must freeze confirmatory_uninspected=true")
    _text(record.get("grouping_rule"), "partitions.grouping_rule")
    partitions = record.get("partitions")
    if not isinstance(partitions, dict):
        raise DocQAPreregistrationError("partitions.partitions must be an object")
    required = ("development", "confirmatory") + (("calibration",) if optimizer_enabled else ())
    identities: set[str] = set()
    for name in required:
        split = partitions.get(name)
        if not isinstance(split, dict):
            raise DocQAPreregistrationError(f"partitions lacks {name}")
        identity = _text(split.get("identity"), f"partitions.{name}.identity")
        _positive_int(split.get("count"), f"partitions.{name}.count")
        if identity in identities:
            raise DocQAPreregistrationError("partition identities must be distinct")
        identities.add(identity)


def _validate_gate(gate: Any, index: int) -> None:
    if not isinstance(gate, dict):
        raise DocQAPreregistrationError(f"competence.gates[{index}] must be an object")
    _text(gate.get("metric"), f"competence.gates[{index}].metric")
    if gate.get("direction") not in {"min", "max", "zero"}:
        raise DocQAPreregistrationError(f"competence.gates[{index}].direction is unsupported")
    threshold = gate.get("threshold")
    if type(threshold) is not int:
        raise DocQAPreregistrationError(f"competence.gates[{index}].threshold must be an integer in its declared unit")
    _text(gate.get("unit"), f"competence.gates[{index}].unit")
    if gate.get("owner_approved") is not True:
        raise DocQAPreregistrationError(f"competence.gates[{index}] must be owner approved")


def _validate_competence(record: dict[str, Any]) -> None:
    if record.get("owner_approved") is not True:
        raise DocQAPreregistrationError("competence must have owner_approved=true")
    if record.get("all_gates_conjunctive") is not True:
        raise DocQAPreregistrationError("competence must declare all_gates_conjunctive=true")
    gates = record.get("gates")
    if not isinstance(gates, list) or not gates:
        raise DocQAPreregistrationError("competence requires nonempty gates")
    for index, gate in enumerate(gates):
        _validate_gate(gate, index)
    _text(record.get("unacceptable_error_definition"), "competence.unacceptable_error_definition")
    _text(record.get("development_evidence_identity"), "competence.development_evidence_identity")
    if record.get("base_development_eligible") is not True:
        raise DocQAPreregistrationError("Base is not development-eligible")
    if record.get("integrated_development_eligible") is not True:
        raise DocQAPreregistrationError("Integrated is not development-eligible")


def _validate_config(record: dict[str, Any], role: str) -> None:
    for field in (
        "config_id",
        "model_identity",
        "runtime_identity",
        "tokenizer_template_identity",
        "retrieval_identity",
        "generation_settings_identity",
        "answer_policy_identity",
    ):
        _text(record.get(field), f"{role}.{field}")
    _positive_int(record.get("max_model_calls"), f"{role}.max_model_calls")
    if role == "integrated":
        composition = record.get("evidence_composition")
        if composition not in {"single-source-precision", "multi-source-coverage"}:
            raise DocQAPreregistrationError("integrated.evidence_composition must be a frozen supported composition")
        _text(record.get("evidence_policy_id"), "integrated.evidence_policy_id")
        _evidence_budget(record.get("evidence_budget_bytes"), "integrated.evidence_budget_bytes")
        _positive_int(record.get("max_projected_items"), "integrated.max_projected_items")
    if record.get("runtime_answer_repair") is not False:
        raise DocQAPreregistrationError(f"{role} must freeze runtime_answer_repair=false")
    if record.get("second_model_judge") is not False:
        raise DocQAPreregistrationError(f"{role} must freeze second_model_judge=false")
    if record.get("adaptive_policy_routing") is not False:
        raise DocQAPreregistrationError(f"{role} must freeze adaptive_policy_routing=false")


def _validate_scorer(record: dict[str, Any]) -> None:
    mode = record.get("mode")
    if mode not in {"deterministic", "human", "hybrid"}:
        raise DocQAPreregistrationError("scorer.mode is unsupported")
    _text(record.get("rubric_identity"), "scorer.rubric_identity")
    _text(record.get("invalid_observation_rule"), "scorer.invalid_observation_rule")
    if record.get("repairs_answers") is not False:
        raise DocQAPreregistrationError("scorer must freeze repairs_answers=false")
    if record.get("runtime_model_judge") is not False:
        raise DocQAPreregistrationError("scorer must freeze runtime_model_judge=false")
    if mode in {"human", "hybrid"}:
        _text(record.get("adjudicator_role"), "scorer.adjudicator_role")
        _text(record.get("disagreement_resolution"), "scorer.disagreement_resolution")
        if record.get("arm_blinded_where_practical") is not True:
            raise DocQAPreregistrationError("human/hybrid scorer must require arm blinding where practical")


def _validate_timing(record: dict[str, Any]) -> None:
    for field in ("hardware_identity", "load_identity", "latency_boundary", "cache_policy", "request_order"):
        _text(record.get(field), f"timing.{field}")
    _positive_int(record.get("concurrency"), "timing.concurrency")
    if record.get("outcome_dependent_reordering") is not False:
        raise DocQAPreregistrationError("timing must freeze outcome_dependent_reordering=false")


def _validate_economics(record: dict[str, Any]) -> None:
    if record.get("owner_approved") is not True:
        raise DocQAPreregistrationError("economics must have owner_approved=true")
    if record.get("double_count_reviewed") is not True:
        raise DocQAPreregistrationError("economics must have double_count_reviewed=true")
    _text(record.get("unit"), "economics.unit")
    _text(record.get("avoidable_cost_interpretation"), "economics.avoidable_cost_interpretation")
    components = record.get("components")
    if not isinstance(components, list) or not components:
        raise DocQAPreregistrationError("economics requires nonempty components")
    names: set[str] = set()
    counters: set[str] = set()
    for index, component in enumerate(components):
        if not isinstance(component, dict):
            raise DocQAPreregistrationError(f"economics.components[{index}] must be an object")
        name = _text(component.get("name"), f"economics.components[{index}].name")
        if name in names:
            raise DocQAPreregistrationError("economics component names must be unique")
        names.add(name)
        counter = component.get("counter")
        if counter not in EXECUTABLE_COUNTERS:
            raise DocQAPreregistrationError(f"economics.components[{index}].counter must name a supported executable counter")
        if counter in counters:
            raise DocQAPreregistrationError("economics executable counters must be unique")
        counters.add(counter)
        _nonnegative_int(component.get("coefficient"), f"economics.components[{index}].coefficient")
        _text(component.get("basis"), f"economics.components[{index}].basis")
    fixed_by_arm = record.get("fixed_counters_by_arm")
    if not isinstance(fixed_by_arm, dict) or set(fixed_by_arm) != {"base", "integrated"}:
        raise DocQAPreregistrationError("economics.fixed_counters_by_arm must freeze base and integrated")
    _validate_fixed_counters(fixed_by_arm["base"], "economics.fixed_counters_by_arm.base")
    _validate_fixed_counters(fixed_by_arm["integrated"], "economics.fixed_counters_by_arm.integrated")
    if record.get("integration_cost_included") is not True:
        raise DocQAPreregistrationError("economics must include integration cost")
    if record.get("qualification_cost_included") is not True:
        raise DocQAPreregistrationError("economics must include qualification cost")
    if record.get("refresh_cost_included") is not True:
        raise DocQAPreregistrationError("economics must include refresh cost")
    if record.get("maintenance_cost_included") is not True:
        raise DocQAPreregistrationError("economics must include maintenance cost")


def _validate_analysis(record: dict[str, Any]) -> None:
    for field in (
        "estimand",
        "sampling_design",
        "uncertainty_method",
        "sample_size_rationale",
        "stopping_rule",
        "missing_invalid_rule",
    ):
        _text(record.get(field), f"analysis.{field}")
    method_id = _text(record.get("method_id"), "analysis.method_id")
    method_parameters = record.get("method_parameters")
    if not isinstance(method_parameters, dict) or not method_parameters:
        raise DocQAPreregistrationError("analysis.method_parameters must be a nonempty object")
    _assert_no_placeholders(method_parameters, "analysis.method_parameters")
    if method_id == "paired-bootstrap-v1":
        expected = {
            "bootstrap_seed",
            "bootstrap_resamples",
            "confidence_bps",
            "quality_noninferiority_margin_bps",
            "base_min_cost_savings_bps",
            "alternative_min_cost_savings_bps",
        }
        if set(method_parameters) != expected:
            raise DocQAPreregistrationError("paired-bootstrap-v1 method_parameters keys are incomplete or unsupported")
        _nonnegative_int(method_parameters["bootstrap_seed"], "analysis.method_parameters.bootstrap_seed")
        resamples = _positive_int(method_parameters["bootstrap_resamples"], "analysis.method_parameters.bootstrap_resamples")
        if not 100 <= resamples <= 20000:
            raise DocQAPreregistrationError("analysis.method_parameters.bootstrap_resamples must be between 100 and 20000")
        confidence = _positive_int(method_parameters["confidence_bps"], "analysis.method_parameters.confidence_bps")
        if not 5000 <= confidence < 10000:
            raise DocQAPreregistrationError("analysis.method_parameters.confidence_bps must be between 5000 and 9999")
        margin = _nonnegative_int(
            method_parameters["quality_noninferiority_margin_bps"],
            "analysis.method_parameters.quality_noninferiority_margin_bps",
        )
        if margin > 10000:
            raise DocQAPreregistrationError("analysis quality noninferiority margin cannot exceed 10000 bps")
        for field in ("base_min_cost_savings_bps", "alternative_min_cost_savings_bps"):
            value = method_parameters[field]
            if type(value) is not int or not -9999 <= value <= 9999:
                raise DocQAPreregistrationError(f"analysis.method_parameters.{field} must be an integer between -9999 and 9999")
    _positive_int(record.get("confirmatory_sample_size"), "analysis.confirmatory_sample_size")
    if record.get("all_thresholds_frozen") is not True:
        raise DocQAPreregistrationError("analysis must freeze all_thresholds_frozen=true")
    if record.get("post_score_extension_allowed") is not False:
        raise DocQAPreregistrationError("analysis must freeze post_score_extension_allowed=false")
    thresholds = record.get("confirmatory_thresholds")
    if not isinstance(thresholds, list) or not thresholds:
        raise DocQAPreregistrationError("analysis requires nonempty confirmatory_thresholds")
    for index, threshold in enumerate(thresholds):
        if not isinstance(threshold, dict):
            raise DocQAPreregistrationError(f"analysis.confirmatory_thresholds[{index}] must be an object")
        _text(threshold.get("name"), f"analysis.confirmatory_thresholds[{index}].name")
        if threshold.get("owner_approved") is not True:
            raise DocQAPreregistrationError(f"analysis.confirmatory_thresholds[{index}] must be owner approved")
        value = threshold.get("value")
        if type(value) is not int:
            raise DocQAPreregistrationError(f"analysis.confirmatory_thresholds[{index}].value must be an integer in its declared unit")
        _text(threshold.get("unit"), f"analysis.confirmatory_thresholds[{index}].unit")


def _validate_optimizer(record: dict[str, Any]) -> bool:
    enabled = record.get("enabled")
    if type(enabled) is not bool:
        raise DocQAPreregistrationError("optimizer.enabled must be boolean")
    if not enabled:
        _text(record.get("disabled_reason"), "optimizer.disabled_reason")
        return False
    for field in ("reference_policy_id", "selector_id", "conventional_tuner_id", "economic_objective_identity"):
        _text(record.get(field), f"optimizer.{field}")
    catalog = record.get("candidate_policy_ids")
    if not isinstance(catalog, list) or len(catalog) < 2 or not all(isinstance(item, str) and item for item in catalog):
        raise DocQAPreregistrationError("optimizer candidate_policy_ids must contain at least two policy IDs")
    if len(set(catalog)) != len(catalog):
        raise DocQAPreregistrationError("optimizer candidate_policy_ids must be unique")
    materiality = record.get("cheaper_reference_materiality_bps")
    if type(materiality) is not int or not 0 < materiality < 10000:
        raise DocQAPreregistrationError("optimizer cheaper_reference_materiality_bps must be an integer between 1 and 9999")
    if record.get("heldout_rescue_allowed") is not False:
        raise DocQAPreregistrationError("optimizer must freeze heldout_rescue_allowed=false")
    return True


def validate_record_objects(records: dict[str, dict[str, Any]]) -> bool:
    if not isinstance(records, dict) or set(records) != set(RECORD_FORMATS):
        raise DocQAPreregistrationError("embedded preregistration records must exactly cover the required roles")
    for role, record in records.items():
        if not isinstance(record, dict):
            raise DocQAPreregistrationError(f"{role} record must be an object")
        if record.get("format") != RECORD_FORMATS[role] or record.get("format_version") != FORMAT_VERSION:
            raise DocQAPreregistrationError(f"unsupported {role} record identity")
        _assert_no_placeholders(record, role)

    optimizer_enabled = _validate_optimizer(records["optimizer"])
    _validate_workload(records["workload"])
    _validate_retrieval(records["retrieval"])
    _validate_partitions(records["partitions"], optimizer_enabled)
    _validate_competence(records["competence"])
    _validate_config(records["base"], "base")
    _validate_config(records["integrated"], "integrated")
    _validate_scorer(records["scorer"])
    _validate_timing(records["timing"])
    _validate_economics(records["economics"])
    _validate_analysis(records["analysis"])

    if records["base"]["retrieval_identity"] != records["retrieval"]["retriever_identity"]:
        raise DocQAPreregistrationError("Base retrieval identity differs from retrieval record")
    if records["integrated"]["retrieval_identity"] != records["retrieval"]["retriever_identity"]:
        raise DocQAPreregistrationError("Integrated retrieval identity differs from retrieval record")
    if records["integrated"]["evidence_composition"] != records["workload"]["evidence_composition"]:
        raise DocQAPreregistrationError("Integrated evidence composition differs from workload contract")
    expected_policy = EVIDENCE_COMPOSITION_POLICIES[records["workload"]["evidence_composition"]]
    if records["integrated"]["evidence_policy_id"] != expected_policy:
        raise DocQAPreregistrationError("Integrated evidence policy differs from the frozen composition contract")
    if records["integrated"]["evidence_budget_bytes"] != records["workload"]["evidence_budget_bytes"]:
        raise DocQAPreregistrationError("Integrated evidence budget differs from workload contract")
    if records["integrated"]["max_projected_items"] > records["retrieval"]["top_k_limit"]:
        raise DocQAPreregistrationError("Integrated max_projected_items exceeds retrieval top_k_limit")
    if records["analysis"]["confirmatory_sample_size"] != records["partitions"]["partitions"]["confirmatory"]["count"]:
        raise DocQAPreregistrationError("analysis confirmatory sample size differs from frozen partition")
    return optimizer_enabled


def validate_records(paths: dict[str, Path]) -> tuple[dict[str, dict[str, Any]], bool]:
    records = {role: _load_record(path, role) for role, path in paths.items()}
    optimizer_enabled = validate_record_objects(records)
    return records, optimizer_enabled


def _paths_from_args(args: argparse.Namespace) -> dict[str, Path]:
    return {role: getattr(args, role.replace("-", "_")) for role in RECORD_FORMATS}


def validate_command(args: argparse.Namespace) -> dict[str, Any]:
    paths = _paths_from_args(args)
    records, optimizer_enabled = validate_records(paths)
    return {
        "status": "VALID",
        "format_version": FORMAT_VERSION,
        "optimizer_enabled": optimizer_enabled,
        "record_sha256": {role: _sha256(path) for role, path in paths.items()},
        "workload_id": records["workload"]["workload_id"],
        "confirmatory_sample_size": records["analysis"]["confirmatory_sample_size"],
    }


def preregister_command(args: argparse.Namespace) -> dict[str, Any]:
    if args.output.exists():
        raise DocQAPreregistrationError("preregistration output already exists")
    paths = _paths_from_args(args)
    records, optimizer_enabled = validate_records(paths)
    for label, source in (("runner_source", args.runner_source), ("scorer_source", args.scorer_source)):
        if not source.is_file():
            raise DocQAPreregistrationError(f"{label} does not exist")
        if source.resolve() == args.output.resolve():
            raise DocQAPreregistrationError(f"{label} cannot be the preregistration output")
    record = {
        "format": PREREG_FORMAT,
        "format_version": FORMAT_VERSION,
        "purpose": "bounded enterprise document-QA competence and total-economic qualification; no FEVER held-out reuse",
        "workload_id": records["workload"]["workload_id"],
        "primary_comparison": {
            "base_config_id": records["base"]["config_id"],
            "integrated_config_id": records["integrated"]["config_id"],
        },
        "evidence_contract": {
            "evidence_composition": records["workload"]["evidence_composition"],
            "evidence_policy_id": records["integrated"]["evidence_policy_id"],
            "evidence_budget_bytes": records["workload"]["evidence_budget_bytes"],
            "max_projected_items": records["integrated"]["max_projected_items"],
            "retrieval_top_k_limit": records["retrieval"]["top_k_limit"],
        },
        "optimizer_branch_enabled": optimizer_enabled,
        "records": records,
        "record_sha256": {role: _sha256(path) for role, path in paths.items()},
        "source_sha256": {
            "runner": _sha256(args.runner_source),
            "scorer": _sha256(args.scorer_source),
            "preregister_tool": _sha256(Path(__file__)),
        },
        "confirmatory_status": "frozen-unscored",
        "fever_stage1_heldout_reuse": False,
        "post_score_rule_changes_allowed": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(record))
    return record


def _add_record_args(parser: argparse.ArgumentParser) -> None:
    for role in RECORD_FORMATS:
        parser.add_argument(f"--{role}", type=Path, required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate")
    _add_record_args(p)

    p = sub.add_parser("preregister")
    _add_record_args(p)
    p.add_argument("--runner-source", type=Path, required=True)
    p.add_argument("--scorer-source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            result = validate_command(args)
        else:
            result = preregister_command(args)
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    except (DocQAPreregistrationError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
