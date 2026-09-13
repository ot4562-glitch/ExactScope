#!/usr/bin/env python3
"""Deterministically score a frozen enterprise DocQA study.

Quality labels come only from frozen offline adjudication rows. This scorer never
calls a model, repairs answers, changes retrieval, or chooses a policy after outcomes.
It first revalidates the complete observation bundle, then aggregates integer metrics,
applies owner-approved frozen gates, and computes economics only from explicitly
named counters.
"""
from __future__ import annotations

import argparse
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

from grounding_canonical import canonical_bytes  # noqa: E402
import enterprise_docqa_observations as observations  # noqa: E402

FORMAT_VERSION = "0.1"
ADJUDICATION_FORMAT = "exactscope.enterprise-docqa-adjudication"
SCORE_FORMAT = "exactscope.enterprise-docqa-score"
SUPPORTED_COUNTERS = {
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


class ScoringError(RuntimeError):
    pass


def rate_bps(count: int, total: int) -> int:
    if total <= 0:
        raise ScoringError("rate denominator must be positive")
    return (count * 10000) // total


def load_adjudications(path: Path) -> list[dict[str, Any]]:
    try:
        rows = observations.load_jsonl(path)
    except observations.ObservationError as exc:
        raise ScoringError(str(exc)) from exc
    for index, row in enumerate(rows):
        if row.get("format") != ADJUDICATION_FORMAT or row.get("format_version") != FORMAT_VERSION:
            raise ScoringError("unsupported adjudication identity")
        for field in (
            "task_correct",
            "evidence_supported",
            "unsupported_answer",
            "abstention_correct",
            "unacceptable_error",
            "adjudication_valid",
        ):
            if type(row.get(field)) is not bool:
                raise ScoringError(f"adjudications[{index}].{field} must be boolean")
        observations.nonnegative_int(row.get("human_review_events"), f"adjudications[{index}].human_review_events")
        observations.text(row.get("item_id"), f"adjudications[{index}].item_id")
        if row.get("arm") not in {"base", "integrated", "alternative"}:
            raise ScoringError("unsupported adjudication arm")
    return rows


def metric_values(
    arm: str,
    arm_observations: list[dict[str, Any]],
    arm_adjudications: list[dict[str, Any]],
    fixed_counters: dict[str, int],
) -> tuple[dict[str, int], dict[str, int]]:
    n = len(arm_observations)
    if n == 0 or len(arm_adjudications) != n:
        raise ScoringError("arm observation/adjudication count mismatch")
    correct = sum(int(row["task_correct"] and row["adjudication_valid"]) for row in arm_adjudications)
    supported = sum(int(row["evidence_supported"] and row["adjudication_valid"]) for row in arm_adjudications)
    unsupported = sum(int(row["unsupported_answer"] or not row["adjudication_valid"]) for row in arm_adjudications)
    abstention_correct = sum(int(row["abstention_correct"] and row["adjudication_valid"]) for row in arm_adjudications)
    unacceptable = sum(int(row["unacceptable_error"] or not row["adjudication_valid"]) for row in arm_adjudications)
    format_violations = sum(int(not row["format_valid"]) for row in arm_observations)
    finalization_violations = sum(int(not row["finalization_valid"]) for row in arm_observations)
    metrics = {
        "task_accuracy": rate_bps(correct, n),
        "evidence_support_rate": rate_bps(supported, n),
        "unsupported_answer_rate": rate_bps(unsupported, n),
        "abstention_correct_rate": rate_bps(abstention_correct, n),
        "unacceptable_error_rate": rate_bps(unacceptable, n),
        "unacceptable_error_count": unacceptable,
        "format_violations": format_violations,
        "finalization_violations": finalization_violations,
    }
    counters = {
        "model_service_ms": sum(row["model_service_ms"] for row in arm_observations),
        "model_calls": sum(row["model_calls"] for row in arm_observations),
        "input_tokens": sum(row["input_tokens"] for row in arm_observations),
        "output_tokens": sum(row["output_tokens"] for row in arm_observations),
        "retrieval_units": sum(row["retrieval_units"] for row in arm_observations),
        "evidence_bytes": sum(row["evidence_bytes"] for row in arm_observations),
        "human_review_events": sum(row["human_review_events"] for row in arm_adjudications),
        "unacceptable_error_count": unacceptable,
    }
    for name, value in fixed_counters.items():
        if name in counters:
            raise ScoringError(f"fixed counter collides with measured counter: {name}")
        if name not in SUPPORTED_COUNTERS:
            raise ScoringError(f"unsupported fixed economic counter: {name}")
        counters[name] = value
    return metrics, counters


def economic_cost(economics: dict[str, Any], counters: dict[str, int]) -> tuple[int, list[dict[str, Any]]]:
    total = 0
    components_out = []
    components = economics.get("components")
    if not isinstance(components, list) or not components:
        raise ScoringError("economics components missing")
    for index, component in enumerate(components):
        if not isinstance(component, dict):
            raise ScoringError("economics component must be an object")
        name = observations.text(component.get("name"), f"economics.components[{index}].name")
        counter = component.get("counter")
        if counter not in SUPPORTED_COUNTERS:
            raise ScoringError(f"economics component {name} lacks a supported executable counter")
        coefficient = component.get("coefficient")
        if type(coefficient) is not int or coefficient < 0:
            raise ScoringError(f"economics component {name} coefficient must be a nonnegative integer")
        if counter not in counters:
            raise ScoringError(f"economic counter not present in frozen run: {counter}")
        value = counters[counter]
        cost = coefficient * value
        total += cost
        components_out.append({"name": name, "counter": counter, "counter_value": value, "coefficient": coefficient, "cost": cost})
    return total, components_out


def check_gate(metric_value: int, gate: dict[str, Any], economics_unit: str) -> dict[str, Any]:
    metric = gate.get("metric")
    if not isinstance(metric, str) or not metric:
        raise ScoringError("gate metric missing")
    direction = gate.get("direction")
    if direction not in {"min", "max", "zero"}:
        raise ScoringError("gate direction unsupported")
    threshold = gate.get("threshold")
    if type(threshold) is not int:
        raise ScoringError("gate threshold must be integer")
    unit = gate.get("unit")
    expected_unit = "count" if metric.endswith("_count") or metric.endswith("violations") else "basis-points"
    if metric == "total_economic_cost":
        expected_unit = economics_unit
    if unit != expected_unit:
        raise ScoringError(f"gate unit mismatch for {metric}: expected {expected_unit}")
    if direction == "min":
        passed = metric_value >= threshold
    elif direction == "max":
        passed = metric_value <= threshold
    else:
        if threshold != 0:
            raise ScoringError("zero-direction gate threshold must be zero")
        passed = metric_value == 0
    return {"metric": metric, "direction": direction, "threshold": threshold, "unit": unit, "actual": metric_value, "passed": passed}


def normalize_analysis_threshold(row: dict[str, Any]) -> dict[str, Any]:
    metric = row.get("metric")
    direction = row.get("direction")
    if isinstance(metric, str) and metric and direction in {"min", "max", "zero"}:
        return {"metric": metric, "direction": direction, "threshold": row.get("value"), "unit": row.get("unit")}
    name = row.get("name")
    if not isinstance(name, str):
        raise ScoringError("analysis threshold lacks metric/direction and parseable name")
    for suffix, inferred_direction in (("_min", "min"), ("_max", "max"), ("_zero", "zero")):
        if name.endswith(suffix):
            return {"metric": name[: -len(suffix)], "direction": inferred_direction, "threshold": row.get("value"), "unit": row.get("unit")}
    raise ScoringError(f"analysis threshold is not executable: {name}")


def score(
    prereg_path: Path,
    study_path: Path,
    questions_path: Path,
    readiness_path: Path,
    run_manifest_path: Path,
    observations_path: Path,
    adjudications_path: Path,
    output: Path,
) -> dict[str, Any]:
    if output.exists():
        raise ScoringError("score output already exists")
    try:
        validation = observations.validate_bundle(prereg_path, study_path, questions_path, readiness_path, run_manifest_path, observations_path)
    except observations.ObservationError as exc:
        raise ScoringError(str(exc)) from exc
    prereg = observations.load_object(prereg_path)
    study = observations.load_object(study_path)
    run_manifest = observations.load_object(run_manifest_path)
    observation_rows = observations.load_jsonl(observations_path)
    adjudication_rows = load_adjudications(adjudications_path)
    expected = {(row["item_id"], row["arm"]) for row in observation_rows}
    keyed_adjudications: dict[tuple[str, str], dict[str, Any]] = {}
    for row in adjudication_rows:
        key = (row["item_id"], row["arm"])
        if key in keyed_adjudications:
            raise ScoringError("duplicate adjudication item/arm")
        keyed_adjudications[key] = row
    if set(keyed_adjudications) != expected:
        raise ScoringError("adjudication matrix differs from frozen observation matrix")

    economics = prereg.get("records", {}).get("economics", {})
    economics_unit = economics.get("unit")
    if not isinstance(economics_unit, str) or not economics_unit:
        raise ScoringError("economics unit missing")
    competence = prereg.get("records", {}).get("competence", {})
    competence_gates = competence.get("gates")
    if not isinstance(competence_gates, list) or not competence_gates:
        raise ScoringError("competence gates missing")
    analysis_thresholds = prereg.get("records", {}).get("analysis", {}).get("confirmatory_thresholds")
    if not isinstance(analysis_thresholds, list) or not analysis_thresholds:
        raise ScoringError("analysis thresholds missing")

    arms: dict[str, Any] = {}
    for arm in ("base", "integrated", "alternative"):
        arm_obs = [row for row in observation_rows if row["arm"] == arm]
        arm_adj = [keyed_adjudications[(row["item_id"], arm)] for row in arm_obs]
        fixed = run_manifest["fixed_counters_by_arm"][arm]
        metrics, counters = metric_values(arm, arm_obs, arm_adj, fixed)
        total_cost, cost_components = economic_cost(economics, counters)
        all_metrics = dict(metrics)
        all_metrics["total_economic_cost"] = total_cost
        gates = []
        for gate in competence_gates:
            metric = gate.get("metric")
            if metric not in all_metrics:
                raise ScoringError(f"unsupported competence metric: {metric}")
            gates.append(check_gate(all_metrics[metric], gate, economics_unit))
        thresholds = []
        for threshold in analysis_thresholds:
            executable = normalize_analysis_threshold(threshold)
            metric = executable["metric"]
            if metric not in all_metrics:
                raise ScoringError(f"unsupported analysis metric: {metric}")
            thresholds.append(check_gate(all_metrics[metric], executable, economics_unit))
        arms[arm] = {
            "metrics": metrics,
            "resource_counters": counters,
            "total_economic_cost": total_cost,
            "economic_components": cost_components,
            "competence_gates": gates,
            "confirmatory_thresholds": thresholds,
            "all_required_gates_pass": all(item["passed"] for item in gates + thresholds),
        }

    integrated = arms["integrated"]
    verdict = "GATES_PASSED_CANDIDATE" if integrated["all_required_gates_pass"] else "FAILED_OR_INCONCLUSIVE"
    if integrated["total_economic_cost"] >= min(arms["base"]["total_economic_cost"], arms["alternative"]["total_economic_cost"]):
        commercial = "ORDINARY_ALTERNATIVE_NOT_BEATEN"
    else:
        commercial = "INTEGRATED_LOWEST_FROZEN_COST"
    result = {
        "format": SCORE_FORMAT,
        "format_version": FORMAT_VERSION,
        "study_contract_sha256": observations.sha256(study_path),
        "preregistration_sha256": observations.sha256(prereg_path),
        "readiness_report_sha256": observations.sha256(readiness_path),
        "run_manifest_sha256": observations.sha256(run_manifest_path),
        "observations_sha256": observations.sha256(observations_path),
        "adjudications_sha256": observations.sha256(adjudications_path),
        "validation": validation,
        "arms": arms,
        "integrated_gate_verdict": verdict,
        "commercial_comparison": commercial,
        "qualified_execution_profile_emitted": False,
        "note": "This scorer does not issue a Qualified Execution Profile; a separate attestation step must bind statistical/owner approval and all required identities.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_bytes(result))
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--adjudications", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = score(args.prereg, args.study, args.questions, args.readiness, args.run_manifest, args.observations, args.adjudications, args.output)
    except (ScoringError, observations.ObservationError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
