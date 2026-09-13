#!/usr/bin/env python3
"""Run the frozen reference analysis for enterprise DocQA qualification.

The reference method is intentionally narrow. It revalidates the frozen observation
bundle, recomputes the score-relevant arm metrics/economics from raw observations and
offline adjudications, then applies a deterministic paired bootstrap whose complete
configuration was frozen in the preregistration before confirmatory outcomes existed.
It does not call a model, retrieve documents, repair answers, choose thresholds, or
emit a Qualification Attestation / Qualified Execution Profile.
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

from grounding_canonical import canonical_bytes, canonical_sha256  # noqa: E402
import enterprise_docqa_observations as observations  # noqa: E402
import enterprise_docqa_score as scorer  # noqa: E402
import enterprise_docqa_study_contract as study_contract  # noqa: E402

FORMAT_VERSION = "0.1"
ANALYSIS_FORMAT = "exactscope.enterprise-docqa-analysis-report"
METHOD_ID = "paired-bootstrap-v1"
ARMS = ("base", "integrated", "alternative")
COMPARATORS = ("base", "alternative")
VARIABLE_COUNTERS = {
    "model_service_ms",
    "model_calls",
    "input_tokens",
    "output_tokens",
    "retrieval_units",
    "evidence_bytes",
    "human_review_events",
    "unacceptable_error_count",
}


class AnalysisError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return observations.sha256(path)


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise AnalysisError(f"{label} must be a nonnegative integer")
    return value


def _load_analysis_record(prereg: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    record = prereg.get("records", {}).get("analysis")
    if not isinstance(record, dict):
        raise AnalysisError("frozen analysis record missing")
    if record.get("method_id") != METHOD_ID:
        raise AnalysisError(f"reference analyzer only supports method_id={METHOD_ID}")
    params = record.get("method_parameters")
    if not isinstance(params, dict):
        raise AnalysisError("analysis method_parameters missing")
    expected = {
        "bootstrap_seed",
        "bootstrap_resamples",
        "confidence_bps",
        "quality_noninferiority_margin_bps",
        "base_min_cost_savings_bps",
        "alternative_min_cost_savings_bps",
    }
    if set(params) != expected:
        raise AnalysisError("paired-bootstrap-v1 parameters drift")
    seed = _nonnegative_int(params["bootstrap_seed"], "bootstrap_seed")
    resamples = _nonnegative_int(params["bootstrap_resamples"], "bootstrap_resamples")
    confidence = _nonnegative_int(params["confidence_bps"], "confidence_bps")
    margin = _nonnegative_int(params["quality_noninferiority_margin_bps"], "quality_noninferiority_margin_bps")
    if not 100 <= resamples <= 20000:
        raise AnalysisError("bootstrap_resamples must be between 100 and 20000")
    if not 5000 <= confidence < 10000:
        raise AnalysisError("confidence_bps must be between 5000 and 9999")
    if margin > 10000:
        raise AnalysisError("quality_noninferiority_margin_bps cannot exceed 10000")
    out = {
        "bootstrap_seed": seed,
        "bootstrap_resamples": resamples,
        "confidence_bps": confidence,
        "quality_noninferiority_margin_bps": margin,
    }
    for field in ("base_min_cost_savings_bps", "alternative_min_cost_savings_bps"):
        value = params[field]
        if type(value) is not int or not -9999 <= value <= 9999:
            raise AnalysisError(f"{field} must be an integer between -9999 and 9999")
        out[field] = value
    return record, out


def _key_rows(rows: list[dict[str, Any]], *, label: str) -> dict[tuple[str, str], dict[str, Any]]:
    keyed: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        item_id = row.get("item_id")
        arm = row.get("arm")
        if not isinstance(item_id, str) or arm not in ARMS:
            raise AnalysisError(f"{label} contains invalid item/arm identity")
        key = (item_id, arm)
        if key in keyed:
            raise AnalysisError(f"{label} contains duplicate item/arm")
        keyed[key] = row
    return keyed


def _effective_correct(adjudication: dict[str, Any]) -> int:
    return int(adjudication["task_correct"] and adjudication["adjudication_valid"])


def _variable_counters(observation: dict[str, Any], adjudication: dict[str, Any]) -> dict[str, int]:
    return {
        "model_service_ms": observation["model_service_ms"],
        "model_calls": observation["model_calls"],
        "input_tokens": observation["input_tokens"],
        "output_tokens": observation["output_tokens"],
        "retrieval_units": observation["retrieval_units"],
        "evidence_bytes": observation["evidence_bytes"],
        "human_review_events": adjudication["human_review_events"],
        "unacceptable_error_count": int(adjudication["unacceptable_error"] or not adjudication["adjudication_valid"]),
    }


def _cost_coefficients(economics: dict[str, Any]) -> dict[str, int]:
    components = economics.get("components")
    if not isinstance(components, list) or not components:
        raise AnalysisError("economics components missing")
    coefficients: dict[str, int] = {}
    for index, component in enumerate(components):
        if not isinstance(component, dict):
            raise AnalysisError(f"economics.components[{index}] must be an object")
        counter = component.get("counter")
        coefficient = component.get("coefficient")
        if counter not in scorer.SUPPORTED_COUNTERS or type(coefficient) is not int or coefficient < 0:
            raise AnalysisError("economics component is not executable")
        if counter in coefficients:
            raise AnalysisError("duplicate economics counter")
        coefficients[counter] = coefficient
    return coefficients


def _row_variable_cost(
    observation: dict[str, Any],
    adjudication: dict[str, Any],
    coefficients: dict[str, int],
) -> int:
    counters = _variable_counters(observation, adjudication)
    return sum(coefficients.get(name, 0) * value for name, value in counters.items())


def _fixed_cost(arm: str, study: dict[str, Any], coefficients: dict[str, int]) -> int:
    fixed = study.get("fixed_counters_by_arm", {}).get(arm)
    if not isinstance(fixed, dict):
        raise AnalysisError(f"fixed counters missing for {arm}")
    total = 0
    for name, value in fixed.items():
        if name in VARIABLE_COUNTERS:
            raise AnalysisError(f"fixed counter collides with measured counter: {name}")
        if name not in scorer.SUPPORTED_COUNTERS:
            raise AnalysisError(f"unsupported fixed counter: {name}")
        _nonnegative_int(value, f"fixed_counters_by_arm.{arm}.{name}")
        total += coefficients.get(name, 0) * value
    return total


def _recompute_score_core(
    prereg: dict[str, Any],
    study: dict[str, Any],
    run_manifest: dict[str, Any],
    observation_rows: list[dict[str, Any]],
    adjudication_rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], str, str]:
    keyed_adjudications = _key_rows(adjudication_rows, label="adjudications")
    expected = {(row["item_id"], row["arm"]) for row in observation_rows}
    if set(keyed_adjudications) != expected:
        raise AnalysisError("adjudication matrix differs from frozen observation matrix")

    economics = prereg.get("records", {}).get("economics", {})
    economics_unit = economics.get("unit")
    if not isinstance(economics_unit, str) or not economics_unit:
        raise AnalysisError("economics unit missing")
    competence_gates = prereg.get("records", {}).get("competence", {}).get("gates")
    analysis_thresholds = prereg.get("records", {}).get("analysis", {}).get("confirmatory_thresholds")
    if not isinstance(competence_gates, list) or not competence_gates:
        raise AnalysisError("competence gates missing")
    if not isinstance(analysis_thresholds, list) or not analysis_thresholds:
        raise AnalysisError("analysis thresholds missing")

    arms: dict[str, Any] = {}
    for arm in ARMS:
        arm_obs = [row for row in observation_rows if row["arm"] == arm]
        arm_adj = [keyed_adjudications[(row["item_id"], arm)] for row in arm_obs]
        fixed = run_manifest["fixed_counters_by_arm"][arm]
        metrics, counters = scorer.metric_values(arm, arm_obs, arm_adj, fixed)
        total_cost, cost_components = scorer.economic_cost(economics, counters)
        all_metrics = dict(metrics)
        all_metrics["total_economic_cost"] = total_cost
        gates = []
        for gate in competence_gates:
            metric = gate.get("metric")
            if metric not in all_metrics:
                raise AnalysisError(f"unsupported competence metric: {metric}")
            gates.append(scorer.check_gate(all_metrics[metric], gate, economics_unit))
        thresholds = []
        for threshold in analysis_thresholds:
            executable = scorer.normalize_analysis_threshold(threshold)
            metric = executable["metric"]
            if metric not in all_metrics:
                raise AnalysisError(f"unsupported analysis metric: {metric}")
            thresholds.append(scorer.check_gate(all_metrics[metric], executable, economics_unit))
        arms[arm] = {
            "metrics": metrics,
            "resource_counters": counters,
            "total_economic_cost": total_cost,
            "economic_components": cost_components,
            "competence_gates": gates,
            "confirmatory_thresholds": thresholds,
            "all_required_gates_pass": all(item["passed"] for item in gates + thresholds),
        }
    verdict = "GATES_PASSED_CANDIDATE" if arms["integrated"]["all_required_gates_pass"] else "FAILED_OR_INCONCLUSIVE"
    commercial = (
        "ORDINARY_ALTERNATIVE_NOT_BEATEN"
        if arms["integrated"]["total_economic_cost"]
        >= min(arms["base"]["total_economic_cost"], arms["alternative"]["total_economic_cost"])
        else "INTEGRATED_LOWEST_FROZEN_COST"
    )
    return arms, verdict, commercial


def _bootstrap_index(seed: int, replicate: int, position: int, n: int) -> int:
    material = f"{seed}:{replicate}:{position}".encode("ascii")
    value = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    return value % n


def _lower_quantile(values: list[int], confidence_bps: int) -> int:
    if not values:
        raise AnalysisError("bootstrap produced no values")
    ordered = sorted(values)
    tail_bps = 10000 - confidence_bps
    index = (tail_bps * (len(ordered) - 1)) // 10000
    return ordered[index]


def _cost_savings_bps(integrated_cost: int, comparator_cost: int) -> int:
    if comparator_cost <= 0:
        raise AnalysisError("comparator total economic cost must be positive for paired cost analysis")
    return ((comparator_cost - integrated_cost) * 10000) // comparator_cost


def _component_status(observed: int, lower: int, threshold: int) -> str:
    if observed < threshold:
        return "fail"
    if lower < threshold:
        return "inconclusive"
    return "pass"


def _combine(*statuses: str) -> str:
    if "fail" in statuses:
        return "fail"
    if "inconclusive" in statuses:
        return "inconclusive"
    return "pass"


def _comparison(
    comparator: str,
    item_ids: list[str],
    obs_by_key: dict[tuple[str, str], dict[str, Any]],
    adj_by_key: dict[tuple[str, str], dict[str, Any]],
    study: dict[str, Any],
    coefficients: dict[str, int],
    params: dict[str, int],
) -> dict[str, Any]:
    n = len(item_ids)
    if n <= 0:
        raise AnalysisError("paired comparison requires at least one item")
    quality_diffs: list[int] = []
    integrated_costs: list[int] = []
    comparator_costs: list[int] = []
    for item_id in item_ids:
        i_obs = obs_by_key[(item_id, "integrated")]
        c_obs = obs_by_key[(item_id, comparator)]
        i_adj = adj_by_key[(item_id, "integrated")]
        c_adj = adj_by_key[(item_id, comparator)]
        quality_diffs.append(_effective_correct(i_adj) - _effective_correct(c_adj))
        integrated_costs.append(_row_variable_cost(i_obs, i_adj, coefficients))
        comparator_costs.append(_row_variable_cost(c_obs, c_adj, coefficients))

    integrated_fixed = _fixed_cost("integrated", study, coefficients)
    comparator_fixed = _fixed_cost(comparator, study, coefficients)
    observed_quality = (sum(quality_diffs) * 10000) // n
    observed_i_cost = sum(integrated_costs) + integrated_fixed
    observed_c_cost = sum(comparator_costs) + comparator_fixed
    observed_cost_savings = _cost_savings_bps(observed_i_cost, observed_c_cost)

    bootstrap_quality: list[int] = []
    bootstrap_cost_savings: list[int] = []
    for replicate in range(params["bootstrap_resamples"]):
        quality_sum = 0
        i_cost = integrated_fixed
        c_cost = comparator_fixed
        for position in range(n):
            index = _bootstrap_index(params["bootstrap_seed"], replicate, position, n)
            quality_sum += quality_diffs[index]
            i_cost += integrated_costs[index]
            c_cost += comparator_costs[index]
        bootstrap_quality.append((quality_sum * 10000) // n)
        bootstrap_cost_savings.append(_cost_savings_bps(i_cost, c_cost))

    quality_lower = _lower_quantile(bootstrap_quality, params["confidence_bps"])
    cost_lower = _lower_quantile(bootstrap_cost_savings, params["confidence_bps"])
    quality_threshold = -params["quality_noninferiority_margin_bps"]
    cost_threshold = params[f"{comparator}_min_cost_savings_bps"]
    quality_status = _component_status(observed_quality, quality_lower, quality_threshold)
    cost_status = _component_status(observed_cost_savings, cost_lower, cost_threshold)
    return {
        "comparator": comparator,
        "item_count": n,
        "quality": {
            "metric": "task_accuracy_delta_bps",
            "observed": observed_quality,
            "lower_bound": quality_lower,
            "threshold": quality_threshold,
            "status": quality_status,
        },
        "economics": {
            "metric": "total_cost_savings_bps",
            "observed": observed_cost_savings,
            "lower_bound": cost_lower,
            "threshold": cost_threshold,
            "integrated_total_cost": observed_i_cost,
            "comparator_total_cost": observed_c_cost,
            "status": cost_status,
        },
        "status": _combine(quality_status, cost_status),
    }


def analyze(
    prereg_path: Path,
    study_path: Path,
    questions_path: Path,
    readiness_path: Path,
    run_manifest_path: Path,
    observations_path: Path,
    adjudications_path: Path,
    score_path: Path,
    output: Path,
) -> dict[str, Any]:
    if output.exists():
        raise AnalysisError("analysis output already exists")
    try:
        validation = observations.validate_bundle(
            prereg_path, study_path, questions_path, readiness_path, run_manifest_path, observations_path
        )
    except observations.ObservationError as exc:
        raise AnalysisError(str(exc)) from exc

    prereg = observations.load_object(prereg_path)
    study = observations.load_object(study_path)
    run_manifest = observations.load_object(run_manifest_path)
    score = observations.load_object(score_path)
    question_rows, questions_by_id = observations.validate_questions(questions_path, prereg)
    observation_rows = observations.load_jsonl(observations_path)
    try:
        adjudication_rows = scorer.load_adjudications(adjudications_path)
    except scorer.ScoringError as exc:
        raise AnalysisError(str(exc)) from exc

    if study.get("format") != study_contract.FORMAT or study.get("format_version") != FORMAT_VERSION:
        raise AnalysisError("unsupported study contract identity")
    current_source_sha = sha256(Path(__file__))
    if study.get("analysis_source_sha256") != current_source_sha:
        raise AnalysisError("current analysis source differs from frozen Study Contract")
    if score.get("format") != scorer.SCORE_FORMAT or score.get("format_version") != FORMAT_VERSION:
        raise AnalysisError("unsupported score identity")
    expected_score_bindings = {
        "preregistration_sha256": sha256(prereg_path),
        "study_contract_sha256": sha256(study_path),
        "readiness_report_sha256": sha256(readiness_path),
        "run_manifest_sha256": sha256(run_manifest_path),
        "observations_sha256": sha256(observations_path),
        "adjudications_sha256": sha256(adjudications_path),
    }
    for field, expected in expected_score_bindings.items():
        if score.get(field) != expected:
            raise AnalysisError(f"score binding drift: {field}")
    if score.get("validation") != validation:
        raise AnalysisError("score validation record drift")
    if score.get("qualified_execution_profile_emitted") is not False:
        raise AnalysisError("score illegally claims profile emission")

    recomputed_arms, recomputed_verdict, recomputed_commercial = _recompute_score_core(
        prereg, study, run_manifest, observation_rows, adjudication_rows
    )
    if score.get("arms") != recomputed_arms:
        raise AnalysisError("score arm metrics/economics drift from raw frozen inputs")
    if score.get("integrated_gate_verdict") != recomputed_verdict:
        raise AnalysisError("score integrated gate verdict drift")
    if score.get("commercial_comparison") != recomputed_commercial:
        raise AnalysisError("score commercial comparison drift")

    analysis_record, params = _load_analysis_record(prereg)
    if analysis_record.get("confirmatory_sample_size") != len(question_rows):
        raise AnalysisError("analysis sample size differs from frozen confirmatory questions")
    obs_by_key = _key_rows(observation_rows, label="observations")
    adj_by_key = _key_rows(adjudication_rows, label="adjudications")
    expected_keys = {(item_id, arm) for item_id in questions_by_id for arm in ARMS}
    if set(obs_by_key) != expected_keys or set(adj_by_key) != expected_keys:
        raise AnalysisError("paired analysis matrix is incomplete")
    item_ids = [row["item_id"] for row in question_rows]
    coefficients = _cost_coefficients(prereg.get("records", {}).get("economics", {}))
    comparisons = {
        comparator: _comparison(comparator, item_ids, obs_by_key, adj_by_key, study, coefficients, params)
        for comparator in COMPARATORS
    }

    base_quality = comparisons["base"]["quality"]["status"]
    alt_quality = comparisons["alternative"]["quality"]["status"]
    base_econ = comparisons["base"]["economics"]["status"]
    alt_econ = comparisons["alternative"]["economics"]["status"]
    customer_utility = (
        "fail"
        if recomputed_verdict != "GATES_PASSED_CANDIDATE"
        else _combine(base_quality, alt_quality)
    )
    total_economics = _combine(base_econ, alt_econ)
    integrated_vs_base = comparisons["base"]["status"]
    integrated_vs_alternative = comparisons["alternative"]["status"]
    mandatory_violations = (
        recomputed_arms["integrated"]["metrics"]["format_violations"]
        + recomputed_arms["integrated"]["metrics"]["finalization_violations"]
    )
    statuses = (integrated_vs_base, integrated_vs_alternative, customer_utility, total_economics)
    conclusion = "fail" if mandatory_violations or "fail" in statuses else ("inconclusive" if "inconclusive" in statuses else "pass")
    uncertainty_conclusive = "inconclusive" not in statuses

    basis = {
        "score_sha256": sha256(score_path),
        "analysis_record_sha256": canonical_sha256(analysis_record),
        "analysis_source_sha256": current_source_sha,
    }
    result = {
        "format": ANALYSIS_FORMAT,
        "format_version": FORMAT_VERSION,
        "analysis_id": "enterprise-docqa-" + canonical_sha256(basis)[:32],
        "method_identity": METHOD_ID,
        "method_parameters": params,
        "score_sha256": sha256(score_path),
        "preregistration_sha256": sha256(prereg_path),
        "study_contract_sha256": sha256(study_path),
        "readiness_report_sha256": sha256(readiness_path),
        "run_manifest_sha256": sha256(run_manifest_path),
        "observations_sha256": sha256(observations_path),
        "adjudications_sha256": sha256(adjudications_path),
        "analysis_source_sha256": current_source_sha,
        "analysis_record_sha256": canonical_sha256(analysis_record),
        "comparisons": comparisons,
        "score_integrated_gate_verdict": recomputed_verdict,
        "score_commercial_comparison": recomputed_commercial,
        "conclusion": conclusion,
        "integrated_vs_base": integrated_vs_base,
        "integrated_vs_alternative": integrated_vs_alternative,
        "customer_utility": customer_utility,
        "total_economics": total_economics,
        "uncertainty_conclusive": uncertainty_conclusive,
        "mandatory_violations": mandatory_violations,
        "post_score_rule_changes_allowed": False,
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
    parser.add_argument("--score", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = analyze(
            args.prereg,
            args.study,
            args.questions,
            args.readiness,
            args.run_manifest,
            args.observations,
            args.adjudications,
            args.score,
            args.output,
        )
    except (AnalysisError, observations.ObservationError, scorer.ScoringError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
