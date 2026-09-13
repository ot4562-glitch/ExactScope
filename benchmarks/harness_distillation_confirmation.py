#!/usr/bin/env python3
"""Preregister and verify the ExactScope v1.1 Stage 1 Qwen/FEVER study.

This module intentionally supersedes the obsolete 120/300, label-balanced,
B/F/P-only confirmation protocol. It does not run the model. It binds the
pre-score protocol and verifies a later frozen analysis report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from math import comb
from pathlib import Path
import sys
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "tools", ROOT / "benchmarks", ROOT / "adapters/llama-cpp"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from grounding_canonical import canonical_bytes, loads  # noqa: E402
from grounding_v1_surface import surface_sha256  # noqa: E402
from harness_distillation import (  # noqa: E402
    calibration_policy_ids,
    digest_json,
    minimum_candidate_catalog,
)
import harness_distillation_fever as fever_driver  # noqa: E402

PREREG_FORMAT = "exactscope.harness-fever-stage1-preregistration"
RESULT_FORMAT = "exactscope.harness-fever-stage1-result"
REPORT_FORMAT = "exactscope.harness-fever-stage1-analysis"
FORMAT_VERSION = "0.2"
ANALYSIS_VERSION = "0.1"
CALIBRATION_PER_LABEL = 40
CALIBRATION_ITEMS = 120
HELD_OUT_TARGET = 600
BASELINE_POLICY_ID = "Base"
REFERENCE_POLICY_ID = "integrated"
STAGE1_RUNNER_ID = "harness-fever-stage1-bfpt-v0.1"
ALPHA_NUMERATOR = 1
ALPHA_DENOMINATOR = 60  # 0.05 / 3 exactly
BASE_IMPROVEMENT_NUMERATOR = 3
BASE_IMPROVEMENT_DENOMINATOR = 100
REFERENCE_REGRESSION_NUMERATOR = 2
REFERENCE_REGRESSION_DENOMINATOR = 100
MAX_COST_VS_REFERENCE_NUMERATOR = 85
MAX_COST_VS_REFERENCE_DENOMINATOR = 100
MAX_LATENCY_VS_BASE_NUMERATOR = 105
MAX_LATENCY_VS_BASE_DENOMINATOR = 100
PREFLIGHT_POLICY_ID = "stage1-exact-gate-resolution-v1"
PREFLIGHT_MIN_TOLERATED_REFERENCE_LOSS_BPS = 50  # at least 0.5% observed losses may still pass
PREFLIGHT_BASE_LOSS_SCENARIO_BPS = 100  # evaluate the Base-only loss cell at 1%
PREFLIGHT_MAX_REQUIRED_OBSERVED_NET_GAIN_BPS = 700  # <=7pp observed net gain to certify the 3pp gate

BOUND_SOURCE_FILES = (
    "benchmarks/harness_distillation_confirmation.py",
    "benchmarks/harness_distillation_fever.py",
    "benchmarks/harness_distillation_stage1.py",
    "benchmarks/public_fever_candidate.py",
    "benchmarks/public_fever_benchmark.py",
    "adapters/llama-cpp/grounding_v1.py",
    "tools/harness_distillation.py",
    "tools/exactscope_calibrate.py",
    "tools/grounding_corpus.py",
    "tools/grounding_projection.py",
    "tools/grounding_projection_legacy.py",
    "tools/grounding_v1_surface.py",
    "tools/grounding_answer_contract.py",
    "grounding/reference-profile-v0.1/projection-policy.txt",
    "docs/V1_1_STAGE1_PREREGISTRATION.md",
)


class ConfirmationError(RuntimeError):
    pass


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ConfirmationError(f"cannot load JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise ConfirmationError(f"expected JSON object: {path}")
    return value


def _source_hashes() -> dict[str, str]:
    result: dict[str, str] = {}
    for relative in BOUND_SOURCE_FILES:
        path = ROOT / relative
        if not path.is_file():
            raise ConfirmationError(f"bound source file is missing: {relative}")
        result[relative] = _file_sha256(path)
    return result


def _require_format(record: dict[str, Any], expected: str, label: str) -> None:
    if record.get("format") != expected or record.get("format_version") != ANALYSIS_VERSION:
        raise ConfirmationError(f"{label} identity drift")


def _require_stage1_freeze(freeze: Path) -> dict[str, Any]:
    manifest = _load_object(freeze / "freeze-manifest.json")
    if manifest.get("format") != fever_driver.FREEZE_FORMAT or manifest.get("format_version") != fever_driver.FORMAT_VERSION:
        raise ConfirmationError("freeze identity drift")
    if manifest.get("selection_mode") != "stage1-balanced-calibration+srs-heldout-v1":
        raise ConfirmationError("Stage 1 requires the current grouped/SRS freeze mode")
    if manifest.get("calibration_per_label") != CALIBRATION_PER_LABEL:
        raise ConfirmationError("Stage 1 requires exactly 40 calibration items per FEVER label")
    if manifest.get("grouping_policy") != fever_driver.STAGE1_GROUPING_POLICY:
        raise ConfirmationError("Stage 1 grouping policy drift")
    if manifest.get("held_out_sampling_method") != fever_driver.STAGE1_SAMPLING_METHOD:
        raise ConfirmationError("Stage 1 held-out sampling method drift")
    if type(manifest.get("held_out_seed")) is not int or manifest["held_out_seed"] < 0:
        raise ConfirmationError("Stage 1 held-out seed must be frozen explicitly")
    if not isinstance(manifest.get("held_out_seed_provenance"), str) or not manifest["held_out_seed_provenance"].strip():
        raise ConfirmationError("Stage 1 held-out seed provenance must be frozen before sample inspection")
    calibration = manifest.get("calibration_split")
    held_out = manifest.get("held_out_split")
    if not isinstance(calibration, dict) or not isinstance(held_out, dict):
        raise ConfirmationError("freeze lacks split identities")
    calibration_ids = calibration.get("item_ids")
    held_out_ids = held_out.get("item_ids")
    if not isinstance(calibration_ids, list) or len(calibration_ids) != CALIBRATION_ITEMS:
        raise ConfirmationError("Stage 1 calibration split must contain 120 items")
    if not isinstance(held_out_ids, list) or len(held_out_ids) != manifest.get("held_out_count"):
        raise ConfirmationError("Stage 1 held-out split size drift")
    if set(calibration_ids) & set(held_out_ids):
        raise ConfirmationError("Stage 1 calibration and held-out splits overlap")
    frame_count = manifest.get("held_out_frame_count")
    if type(frame_count) is not int or frame_count < len(held_out_ids):
        raise ConfirmationError("Stage 1 finite held-out frame is invalid")
    if not isinstance(manifest.get("held_out_frame_sha256"), str):
        raise ConfirmationError("Stage 1 finite held-out frame identity is missing")
    if manifest.get("claim_identity_policy") != "NFKC+whitespace-collapse+casefold+sha256-v1":
        raise ConfirmationError("Stage 1 duplicate-claim exclusion policy drift")
    if type(manifest.get("excluded_claim_identity_count")) is not int or manifest["excluded_claim_identity_count"] < 1:
        raise ConfirmationError("Stage 1 must exclude prior claim identities")
    return manifest


def _candidate_binding() -> tuple[list[dict[str, Any]], list[str], str]:
    host = fever_driver._minimal_host("stage1-preregister-placeholder")
    candidates = minimum_candidate_catalog(host)
    catalog = [candidate.as_dict() for candidate in candidates]
    executed = list(calibration_policy_ids(candidates, BASELINE_POLICY_ID))
    return catalog, executed, digest_json(catalog)


def _load_protocol_record(path: Path, expected_format: str, label: str) -> dict[str, Any]:
    record = _load_object(path)
    _require_format(record, expected_format, label)
    return record


def _validate_competence_record(record: dict[str, Any]) -> None:
    if record.get("baseline_policy_id") != BASELINE_POLICY_ID:
        raise ConfirmationError("competence record baseline identity drift")
    if record.get("reference_policy_id") != REFERENCE_POLICY_ID:
        raise ConfirmationError("competence record reference identity drift")
    floor = record.get("task_utility_floor")
    if not isinstance(floor, dict) or not floor:
        raise ConfirmationError("competence record must freeze a nonempty task_utility_floor")
    if not isinstance(record.get("preexisting_evidence"), list) or not record["preexisting_evidence"]:
        raise ConfirmationError("competence record must cite pre-existing evidence")
    if type(record.get("product_inference_allowed")) is not bool:
        raise ConfirmationError("competence record must declare product_inference_allowed")

    classification = record.get("classification")
    if classification not in {"product-inference-eligible", "algorithm-diagnostic-only"}:
        raise ConfirmationError("competence record classification is unsupported")
    floor_status = floor.get("status")
    if record["product_inference_allowed"]:
        if classification != "product-inference-eligible" or floor_status != "established":
            raise ConfirmationError("product inference requires an established pre-score competence floor")
        required_floor_fields = ("metric", "minimum", "population_scope", "evidence_basis")
        if any(field not in floor for field in required_floor_fields):
            raise ConfirmationError("established competence floor lacks required frozen fields")
        minimum = floor.get("minimum")
        if isinstance(minimum, bool) or not isinstance(minimum, (int, float)):
            raise ConfirmationError("established competence floor minimum must be numeric")
        if not isinstance(floor.get("metric"), str) or not floor["metric"].strip():
            raise ConfirmationError("established competence floor metric must be nonempty")
        if not isinstance(floor.get("population_scope"), str) or not floor["population_scope"].strip():
            raise ConfirmationError("established competence floor population_scope must be nonempty")
        if not isinstance(floor.get("evidence_basis"), str) or not floor["evidence_basis"].strip():
            raise ConfirmationError("established competence floor evidence_basis must be nonempty")
    else:
        if classification != "algorithm-diagnostic-only" or floor_status != "not-established":
            raise ConfirmationError("diagnostic-only study must explicitly record an unestablished competence floor")
        reason = record.get("diagnostic_reason")
        if not isinstance(reason, str) or not reason.strip():
            raise ConfirmationError("diagnostic-only competence record requires diagnostic_reason")


def _validate_cost_model(record: dict[str, Any]) -> None:
    if not isinstance(record.get("unit"), str) or not record["unit"].strip():
        raise ConfirmationError("serving-cost model requires a unit")
    coefficients = record.get("integer_coefficients")
    if not isinstance(coefficients, dict) or not coefficients:
        raise ConfirmationError("serving-cost model requires integer_coefficients")
    for key, value in coefficients.items():
        if not isinstance(key, str) or not key or type(value) is not int or value < 0:
            raise ConfirmationError("serving-cost coefficients must be named nonnegative integers")
    if not isinstance(record.get("accounting_scope"), list) or not record["accounting_scope"]:
        raise ConfirmationError("serving-cost model requires an accounting_scope")
    if type(record.get("double_count_reviewed")) is not bool or record["double_count_reviewed"] is not True:
        raise ConfirmationError("serving-cost model must affirm double_count_reviewed=true")


def _validate_timing_protocol(record: dict[str, Any]) -> None:
    required = ("hardware_identity", "warmup", "cache_policy", "request_order", "concurrency", "latency_boundary")
    if any(key not in record for key in required):
        raise ConfirmationError("timing protocol lacks a required frozen field")


def _validate_contract_record(record: dict[str, Any]) -> None:
    if record.get("format") != "exactscope.stage1-frozen-contract-record" or record.get("format_version") != "0.1":
        raise ConfirmationError("unsupported Stage 1 frozen contract record")
    for field in ("model_key", "model_sha256", "runtime_sha256", "selected_contract", "selected_output_surface"):
        if not isinstance(record.get(field), str) or not record[field]:
            raise ConfirmationError(f"frozen contract record lacks {field}")
    calibration = record.get("contract_calibration")
    if not isinstance(calibration, dict):
        raise ConfirmationError("frozen contract record lacks contract_calibration")
    if calibration.get("selected_contract") != record["selected_contract"]:
        raise ConfirmationError("frozen contract selected contract drift")
    if calibration.get("selected_output_surface") != record["selected_output_surface"]:
        raise ConfirmationError("frozen contract selected output surface drift")
    if record.get("selection_frozen_before_stage1_scoring") is not True:
        raise ConfirmationError("frozen contract must be selected before Stage 1 scoring")


def _validate_semantic_metadata(record: dict[str, Any], catalog: list[dict[str, Any]]) -> None:
    if record.get("format") != "exactscope.stage1-semantic-metadata" or record.get("format_version") != "0.1":
        raise ConfirmationError("unsupported Stage 1 semantic metadata record")
    if record.get("selection_role") != "descriptive-only":
        raise ConfirmationError("Stage 1 semantic metadata must be descriptive-only")
    workload = record.get("workload_descriptor")
    host = record.get("host_capability_vector")
    vectors = record.get("semantic_policy_vectors")
    if not isinstance(workload, dict) or not workload:
        raise ConfirmationError("semantic metadata lacks workload descriptor")
    if not isinstance(host, dict) or not host:
        raise ConfirmationError("semantic metadata lacks host capability vector")
    if not isinstance(vectors, list):
        raise ConfirmationError("semantic metadata lacks policy vectors")
    expected = [candidate["policy_id"] for candidate in catalog]
    actual = [value.get("policy_id") for value in vectors if isinstance(value, dict)]
    if actual != expected:
        raise ConfirmationError("semantic metadata policy vector identities differ from candidate catalog")
    if record.get("may_affect_stage1_selection") is not False:
        raise ConfirmationError("semantic metadata must not affect Stage 1 selection")


def _validate_analysis_record(record: dict[str, Any], freeze: dict[str, Any]) -> None:
    if record.get("bound_method") != "exact-one-sided-hypergeometric-inversion-v1":
        raise ConfirmationError("analysis record exact-bound method drift")
    if record.get("alpha_numerator") != ALPHA_NUMERATOR or record.get("alpha_denominator") != ALPHA_DENOMINATOR:
        raise ConfirmationError("analysis record alpha allocation drift")
    if record.get("finite_frame_size") != freeze["held_out_frame_count"]:
        raise ConfirmationError("analysis record finite frame size drift")
    if record.get("held_out_sample_size") != freeze["held_out_count"]:
        raise ConfirmationError("analysis record held-out sample size drift")
    if record.get("preflight_passed") is not True:
        raise ConfirmationError("precision/power preflight must pass before preregistration")
    if not isinstance(record.get("preflight_assumptions"), list) or not record["preflight_assumptions"]:
        raise ConfirmationError("analysis record must freeze preflight assumptions")
    identity = record.get("freeze_identity")
    if not isinstance(identity, dict):
        raise ConfirmationError("analysis record lacks frozen frame identity")
    expected_identity = {
        "held_out_frame_sha256": freeze.get("held_out_frame_sha256"),
        "held_out_split_digest": freeze.get("held_out_split_digest"),
        "grouping_policy": freeze.get("grouping_policy"),
        "sampling_method": freeze.get("held_out_sampling_method"),
    }
    if identity != expected_identity:
        raise ConfirmationError("analysis record frozen frame identity drift")


def preregister(args: argparse.Namespace) -> dict[str, Any]:
    if args.output.exists():
        raise ConfirmationError("preregistration output already exists")
    freeze_manifest = _require_stage1_freeze(args.freeze)
    if not args.primary.is_file() or not args.executor.is_file():
        raise ConfirmationError("frozen stack artifact/executor missing")
    if type(args.threads) is not int or args.threads < 1:
        raise ConfirmationError("threads must be positive")

    competence = _load_protocol_record(args.competence_record, "exactscope.stage1-competence-record", "competence record")
    cost_model = _load_protocol_record(args.cost_model, "exactscope.stage1-serving-cost-model", "serving-cost model")
    timing = _load_protocol_record(args.timing_protocol, "exactscope.stage1-timing-protocol", "timing protocol")
    analysis = _load_protocol_record(args.analysis_record, "exactscope.stage1-analysis-plan", "analysis record")
    contract = _load_protocol_record(args.contract_record, "exactscope.stage1-frozen-contract-record", "frozen contract record")
    semantic_metadata = _load_protocol_record(args.semantic_metadata, "exactscope.stage1-semantic-metadata", "semantic metadata")
    _validate_competence_record(competence)
    _validate_cost_model(cost_model)
    _validate_timing_protocol(timing)
    _validate_analysis_record(analysis, freeze_manifest)
    _validate_contract_record(contract)

    primary_sha256 = _file_sha256(args.primary)
    executor_sha256 = _file_sha256(args.executor)
    if contract["model_sha256"] != primary_sha256 or contract["runtime_sha256"] != executor_sha256:
        raise ConfirmationError("frozen contract model/runtime identity differs from preregistered stack")
    model_identity = timing.get("model_identity")
    runtime_identity = timing.get("runtime_identity")
    if not isinstance(model_identity, dict) or model_identity.get("model_sha256") != primary_sha256:
        raise ConfirmationError("timing protocol model identity differs from preregistered stack")
    if not isinstance(runtime_identity, dict) or runtime_identity.get("executable_sha256") != executor_sha256:
        raise ConfirmationError("timing protocol runtime identity differs from preregistered stack")
    if runtime_identity.get("threads") != args.threads:
        raise ConfirmationError("timing protocol thread count differs from preregistered stack")

    catalog, executed_policy_ids, catalog_digest = _candidate_binding()
    _validate_semantic_metadata(semantic_metadata, catalog)
    semantic_host = semantic_metadata["host_capability_vector"]
    if semantic_host.get("structured_output_surface") != contract["selected_output_surface"]:
        raise ConfirmationError("semantic metadata structured output surface differs from frozen contract")
    if semantic_host.get("fixed_answer_contract") != contract["selected_contract"]:
        raise ConfirmationError("semantic metadata answer contract differs from frozen contract")
    if semantic_host.get("stack") != args.stack_name:
        raise ConfirmationError("semantic metadata stack name differs from preregistration")
    record = {
        "format": PREREG_FORMAT,
        "format_version": FORMAT_VERSION,
        "purpose": "fresh Qwen/FEVER Stage 1 within-workload compiler-value falsification; not release qualification",
        "freeze_manifest_sha256": _file_sha256(args.freeze / "freeze-manifest.json"),
        "calibration_split_digest": freeze_manifest["calibration_split_digest"],
        "held_out_split_digest": freeze_manifest["held_out_split_digest"],
        "held_out_frame_count": freeze_manifest["held_out_frame_count"],
        "held_out_frame_sha256": freeze_manifest["held_out_frame_sha256"],
        "calibration_items": CALIBRATION_ITEMS,
        "held_out_items": freeze_manifest["held_out_count"],
        "held_out_target_before_preflight": HELD_OUT_TARGET,
        "calibration_per_label": CALIBRATION_PER_LABEL,
        "baseline_policy_id": BASELINE_POLICY_ID,
        "reference_policy_id": REFERENCE_POLICY_ID,
        "candidate_catalog": catalog,
        "candidate_catalog_digest": catalog_digest,
        "calibration_policy_ids": executed_policy_ids,
        "selection": {
            "P": "valid+mandatory-gates+L[p,F]==0+C[p]<C[F]; choose lowest C, highest S, canonical ID; else ReferenceOnly",
            "T": "valid+mandatory-gates+S[p]>=S[F]+C[p]<C[F]; choose lowest C, highest S, canonical ID; else T=F",
        },
        "held_out_policy_rule": "unique policy IDs among B/F/frozen-P/frozen-T; no rescue or reselection",
        "protocol_record_sha256": {
            "competence": _file_sha256(args.competence_record),
            "serving_cost_model": _file_sha256(args.cost_model),
            "timing": _file_sha256(args.timing_protocol),
            "analysis": _file_sha256(args.analysis_record),
            "contract": _file_sha256(args.contract_record),
            "semantic_metadata": _file_sha256(args.semantic_metadata),
        },
        "protocol_records": {
            "competence": competence,
            "serving_cost_model": cost_model,
            "timing": timing,
            "analysis": analysis,
            "contract": contract,
            "semantic_metadata": semantic_metadata,
        },
        "stack_identity": {
            "primary": primary_sha256,
            "executor": executor_sha256,
            "primary_bytes": args.primary.stat().st_size,
            "threads": args.threads,
        },
        "stack_name": args.stack_name,
        "surface_fingerprint": surface_sha256(),
        "runner_id": STAGE1_RUNNER_ID,
        "evidence": {
            "max_bytes": fever_driver.MAX_EVIDENCE_BYTES,
            "item_cap": fever_driver.MODEL_ITEM_CAP,
            "control_top_k": fever_driver.CONTROL_TOP_K,
            "overfetch_top_k": fever_driver.OVERFETCH_TOP_K,
            "searchable_materials": ["A", "B", "D", "prompt-profile"],
        },
        "primary_gates": {
            "alpha_numerator": ALPHA_NUMERATOR,
            "alpha_denominator": ALPHA_DENOMINATOR,
            "base_improvement_numerator": BASE_IMPROVEMENT_NUMERATOR,
            "base_improvement_denominator": BASE_IMPROVEMENT_DENOMINATOR,
            "reference_regression_numerator": REFERENCE_REGRESSION_NUMERATOR,
            "reference_regression_denominator": REFERENCE_REGRESSION_DENOMINATOR,
            "max_cost_vs_reference_numerator": MAX_COST_VS_REFERENCE_NUMERATOR,
            "max_cost_vs_reference_denominator": MAX_COST_VS_REFERENCE_DENOMINATOR,
            "max_cost_vs_base_numerator": 1,
            "max_cost_vs_base_denominator": 1,
            "max_latency_vs_base_numerator": MAX_LATENCY_VS_BASE_NUMERATOR,
            "max_latency_vs_base_denominator": MAX_LATENCY_VS_BASE_DENOMINATOR,
            "mandatory_violation_count": 0,
        },
        "protocol": {
            "gold_visible_to_model_runner": False,
            "held_out_reselection": False,
            "reference_or_tuner_rescue": False,
            "optional_sample_extension": False,
            "outcome_based_exclusions": False,
            "repeat_model_call_for_better_answer": False,
            "outcome_informed_rule_change_consumes_heldout": True,
        },
        "bound_source_files": _source_hashes(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(record))
    return record


def _policy_row(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfirmationError(f"{label} must be an object")
    required = {"policy_id", "valid", "mandatory_gates_pass", "success_count", "reference_loss_count", "serving_cost"}
    if set(value) != required:
        raise ConfirmationError(f"{label} shape drift")
    if not isinstance(value["policy_id"], str) or not value["policy_id"]:
        raise ConfirmationError(f"{label}.policy_id invalid")
    if type(value["valid"]) is not bool or type(value["mandatory_gates_pass"]) is not bool:
        raise ConfirmationError(f"{label} validity fields must be boolean")
    for field in ("success_count", "reference_loss_count", "serving_cost"):
        if type(value[field]) is not int or value[field] < 0:
            raise ConfirmationError(f"{label}.{field} must be a nonnegative integer")
    return value


def select_stage1_policies(policy_rows: list[dict[str, Any]], baseline_policy_id: str, reference_policy_id: str) -> dict[str, Any]:
    rows: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(policy_rows):
        row = _policy_row(raw, f"calibration_policy_rows[{index}]")
        if row["policy_id"] in rows:
            raise ConfirmationError("duplicate calibration policy identity")
        rows[row["policy_id"]] = row
    if baseline_policy_id not in rows or reference_policy_id not in rows:
        raise ConfirmationError("calibration policy rows lack Base or Reference")
    base = rows[baseline_policy_id]
    reference = rows[reference_policy_id]
    if not reference["valid"] or not reference["mandatory_gates_pass"]:
        return {"outcome": "NoQualifiedReference", "P": None, "T": None}
    if reference["success_count"] <= 0 or reference["success_count"] < base["success_count"]:
        return {"outcome": "NoQualifiedReference", "P": None, "T": None}

    candidates_p = [
        row for row in rows.values()
        if row["valid"]
        and row["mandatory_gates_pass"]
        and row["reference_loss_count"] == 0
        and row["serving_cost"] < reference["serving_cost"]
    ]
    candidates_p.sort(key=lambda row: (row["serving_cost"], -row["success_count"], row["policy_id"].encode("utf-8")))
    candidates_t = [
        row for row in rows.values()
        if row["valid"]
        and row["mandatory_gates_pass"]
        and row["success_count"] >= reference["success_count"]
        and row["serving_cost"] < reference["serving_cost"]
    ]
    candidates_t.sort(key=lambda row: (row["serving_cost"], -row["success_count"], row["policy_id"].encode("utf-8")))
    tuner = candidates_t[0]["policy_id"] if candidates_t else reference_policy_id
    if not candidates_p:
        return {"outcome": "ReferenceOnly", "P": None, "T": tuner}
    return {"outcome": "CompiledCandidate", "P": candidates_p[0]["policy_id"], "T": tuner}


def _hypergeom_numerator_sum(N: int, K: int, n: int, start: int, stop: int) -> int:
    low = max(start, 0, n - (N - K))
    high = min(stop, n, K)
    if low > high:
        return 0
    return sum(comb(K, x) * comb(N - K, n - x) for x in range(low, high + 1))


def _probability_greater_than_alpha(numerator: int, denominator: int) -> bool:
    return numerator * ALPHA_DENOMINATOR > denominator * ALPHA_NUMERATOR


def hypergeometric_lower_count_bound(N: int, n: int, x: int) -> int:
    """Exact conservative one-sided lower bound for population success count K."""
    if not (0 < n <= N) or not (0 <= x <= n):
        raise ConfirmationError("invalid finite-population bound arguments")
    if x == 0:
        return 0
    denominator = comb(N, n)
    lo, hi = x, N - n + x
    while lo < hi:
        mid = (lo + hi) // 2
        tail = _hypergeom_numerator_sum(N, mid, n, x, n)
        if _probability_greater_than_alpha(tail, denominator):
            hi = mid
        else:
            lo = mid + 1
    return lo


def hypergeometric_upper_count_bound(N: int, n: int, x: int) -> int:
    """Exact conservative one-sided upper bound for population success count K."""
    if not (0 < n <= N) or not (0 <= x <= n):
        raise ConfirmationError("invalid finite-population bound arguments")
    if x == n:
        return N
    denominator = comb(N, n)
    lo, hi = x, N - n + x
    while lo < hi:
        mid = (lo + hi + 1) // 2
        cdf = _hypergeom_numerator_sum(N, mid, n, 0, x)
        if _probability_greater_than_alpha(cdf, denominator):
            lo = mid
        else:
            hi = mid - 1
    return lo


def _max_reference_loss_count_passing(N: int, n: int) -> int:
    lo, hi = 0, n
    while lo < hi:
        mid = (lo + hi + 1) // 2
        upper = hypergeometric_upper_count_bound(N, n, mid)
        if upper * REFERENCE_REGRESSION_DENOMINATOR <= REFERENCE_REGRESSION_NUMERATOR * N:
            lo = mid
        else:
            hi = mid - 1
    return lo


def _minimum_gain_count_passing(N: int, n: int, base_loss_count: int) -> int | None:
    if not 0 <= base_loss_count <= n:
        raise ConfirmationError("preflight Base-loss count outside sample")
    upper_b = hypergeometric_upper_count_bound(N, n, base_loss_count)
    lo, hi = 0, n
    while lo < hi:
        mid = (lo + hi) // 2
        lower_g = hypergeometric_lower_count_bound(N, n, mid)
        if (lower_g - upper_b) * BASE_IMPROVEMENT_DENOMINATOR >= BASE_IMPROVEMENT_NUMERATOR * N:
            hi = mid
        else:
            lo = mid + 1
    lower_g = hypergeometric_lower_count_bound(N, n, lo)
    if (lower_g - upper_b) * BASE_IMPROVEMENT_DENOMINATOR < BASE_IMPROVEMENT_NUMERATOR * N:
        return None
    return lo


def build_preflight_record(freeze_manifest: dict[str, Any]) -> dict[str, Any]:
    N = freeze_manifest.get("held_out_frame_count")
    n = freeze_manifest.get("held_out_count")
    if type(N) is not int or type(n) is not int or not (0 < n <= N):
        raise ConfirmationError("preflight requires a valid frozen finite frame/sample size")

    max_r = _max_reference_loss_count_passing(N, n)
    max_r_upper = hypergeometric_upper_count_bound(N, n, max_r)
    scenario_bps = (0, 50, 100, 200, 300, 500)
    base_regions: list[dict[str, Any]] = []
    for bps in scenario_bps:
        b = (n * bps) // 10000
        upper_b = hypergeometric_upper_count_bound(N, n, b)
        min_g = _minimum_gain_count_passing(N, n, b)
        lower_g = None if min_g is None else hypergeometric_lower_count_bound(N, n, min_g)
        observed_net_bps = None if min_g is None else ((min_g - b) * 10000) // n
        base_regions.append({
            "base_only_loss_scenario_bps": bps,
            "b_count": b,
            "upper_b_count": upper_b,
            "minimum_g_count_passing": min_g,
            "lower_g_count_at_minimum": lower_g,
            "minimum_observed_net_gain_bps": observed_net_bps,
        })

    one_percent = next(row for row in base_regions if row["base_only_loss_scenario_bps"] == PREFLIGHT_BASE_LOSS_SCENARIO_BPS)
    tolerated_reference_loss_bps = (max_r * 10000) // n
    reference_resolution_ok = tolerated_reference_loss_bps >= PREFLIGHT_MIN_TOLERATED_REFERENCE_LOSS_BPS
    base_resolution_ok = (
        one_percent["minimum_observed_net_gain_bps"] is not None
        and one_percent["minimum_observed_net_gain_bps"] <= PREFLIGHT_MAX_REQUIRED_OBSERVED_NET_GAIN_BPS
    )
    preflight_passed = reference_resolution_ok and base_resolution_ok

    return {
        "format": "exactscope.stage1-analysis-plan",
        "format_version": ANALYSIS_VERSION,
        "preflight_policy_id": PREFLIGHT_POLICY_ID,
        "bound_method": "exact-one-sided-hypergeometric-inversion-v1",
        "alpha_numerator": ALPHA_NUMERATOR,
        "alpha_denominator": ALPHA_DENOMINATOR,
        "finite_frame_size": N,
        "held_out_sample_size": n,
        "preflight_passed": preflight_passed,
        "preflight_assumptions": [
            "No reliable effect-size prior is inferred from the historical 6+6 run; this is an exact gate-resolution screen, not a calibrated 80%-power claim.",
            "Reference-regression resolution is considered useful only if the 2pp upper-bound gate can tolerate at least 0.5% observed P-wrong/F-correct losses.",
            "Base-improvement resolution is considered useful only if, with a 1% observed Base-only loss cell, the 3pp lower-bound gate needs no more than a 7pp observed net P-only-minus-Base-only gain.",
            "The held-out sample remains fixed after this record; no post-score extension is permitted.",
        ],
        "resolution_policy": {
            "minimum_tolerated_reference_loss_bps": PREFLIGHT_MIN_TOLERATED_REFERENCE_LOSS_BPS,
            "base_only_loss_scenario_bps": PREFLIGHT_BASE_LOSS_SCENARIO_BPS,
            "maximum_required_observed_net_gain_bps": PREFLIGHT_MAX_REQUIRED_OBSERVED_NET_GAIN_BPS,
        },
        "reference_regression_pass_region": {
            "maximum_r_count_passing": max_r,
            "maximum_observed_r_bps_passing": tolerated_reference_loss_bps,
            "upper_population_count_at_maximum": max_r_upper,
            "upper_population_bps_at_maximum": (max_r_upper * 10000) // N,
            "resolution_ok": reference_resolution_ok,
        },
        "base_improvement_pass_regions": base_regions,
        "base_resolution_ok": base_resolution_ok,
        "freeze_identity": {
            "held_out_frame_sha256": freeze_manifest.get("held_out_frame_sha256"),
            "held_out_split_digest": freeze_manifest.get("held_out_split_digest"),
            "grouping_policy": freeze_manifest.get("grouping_policy"),
            "sampling_method": freeze_manifest.get("held_out_sampling_method"),
        },
    }


def write_preflight(freeze: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise ConfirmationError("preflight output already exists")
    freeze_manifest = _require_stage1_freeze(freeze)
    record = build_preflight_record(freeze_manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_bytes(record))
    return record


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ConfirmationError(f"{label} must be a nonnegative integer")
    return value


def _competence_allows_product_inference(prereg: dict[str, Any]) -> bool:
    """Return the preregistered competence authorization for product-level inference."""
    protocol_records = prereg.get("protocol_records")
    if protocol_records is None:
        # Unit-level evaluator fixtures may omit preregistration records. Real verifier
        # preregistrations always embed and validate them before this function runs.
        return True
    if not isinstance(protocol_records, dict):
        raise ConfirmationError("preregistration protocol_records shape drift")
    competence = protocol_records.get("competence")
    if not isinstance(competence, dict) or type(competence.get("product_inference_allowed")) is not bool:
        raise ConfirmationError("preregistration lacks validated competence authorization")
    return competence["product_inference_allowed"]


def _evaluate_heldout_policy(
    *,
    policy_id: str,
    baseline_policy_id: str,
    reference_policy_id: str,
    paired: dict[str, Any],
    costs: dict[str, Any],
    p95: dict[str, Any],
    violations: dict[str, Any],
    N: int,
    n: int,
) -> dict[str, Any]:
    counts = paired.get(policy_id)
    if not isinstance(counts, dict) or set(counts) != {"g", "b", "r"}:
        raise ConfirmationError(f"Stage 1 held-out lacks paired counts for {policy_id}")
    g = _nonnegative_int(counts["g"], f"{policy_id}.g")
    b = _nonnegative_int(counts["b"], f"{policy_id}.b")
    r = _nonnegative_int(counts["r"], f"{policy_id}.r")
    if g > n or b > n or r > n:
        raise ConfirmationError(f"Stage 1 paired count exceeds held-out sample size for {policy_id}")
    lower_g = hypergeometric_lower_count_bound(N, n, g)
    upper_b = hypergeometric_upper_count_bound(N, n, b)
    upper_r = hypergeometric_upper_count_bound(N, n, r)

    for role_id in (policy_id, baseline_policy_id, reference_policy_id):
        if role_id not in costs or role_id not in p95 or role_id not in violations:
            raise ConfirmationError(f"Stage 1 held-out lacks aggregate for logical arm {role_id}")
    policy_cost = _nonnegative_int(costs[policy_id], f"{policy_id} serving cost")
    reference_cost = _nonnegative_int(costs[reference_policy_id], "Reference serving cost")
    baseline_cost = _nonnegative_int(costs[baseline_policy_id], "Base serving cost")
    policy_latency = _nonnegative_int(p95[policy_id], f"{policy_id} p95 latency")
    baseline_latency = _nonnegative_int(p95[baseline_policy_id], "Base p95 latency")
    policy_violations = _nonnegative_int(violations[policy_id], f"{policy_id} mandatory violations")
    if reference_cost <= 0 or baseline_latency <= 0:
        raise ConfirmationError("Stage 1 Reference cost/Base latency must be positive")

    narrow_failures: list[str] = []
    if upper_r * REFERENCE_REGRESSION_DENOMINATOR > REFERENCE_REGRESSION_NUMERATOR * N:
        narrow_failures.append("reference-regression-bound-exceeded-preregistered-margin")
    if policy_cost >= reference_cost:
        narrow_failures.append("serving-cost-not-strictly-below-reference")
    if policy_violations != 0:
        narrow_failures.append("mandatory-contract-identity-observation-model-call-violation")

    product_failures: list[str] = []
    if (lower_g - upper_b) * BASE_IMPROVEMENT_DENOMINATOR < BASE_IMPROVEMENT_NUMERATOR * N:
        product_failures.append("base-improvement-bound-below-preregistered-margin")
    if upper_r * REFERENCE_REGRESSION_DENOMINATOR > REFERENCE_REGRESSION_NUMERATOR * N:
        product_failures.append("reference-regression-bound-exceeded-preregistered-margin")
    if policy_cost * MAX_COST_VS_REFERENCE_DENOMINATOR > reference_cost * MAX_COST_VS_REFERENCE_NUMERATOR:
        product_failures.append("serving-cost-vs-reference-exceeded-preregistered-margin")
    if policy_cost > baseline_cost:
        product_failures.append("serving-cost-exceeded-base")
    if policy_latency * MAX_LATENCY_VS_BASE_DENOMINATOR > baseline_latency * MAX_LATENCY_VS_BASE_NUMERATOR:
        product_failures.append("p95-latency-exceeded-base-margin")
    if policy_violations != 0:
        product_failures.append("mandatory-contract-identity-observation-model-call-violation")

    return {
        "policy_id": policy_id,
        "narrow_selector_verdict": "PASS" if not narrow_failures else "FAIL",
        "narrow_selector_failure_reasons": narrow_failures,
        "product_verdict": "PASS" if not product_failures else "FAIL",
        "product_failure_reasons": product_failures,
        "paired_counts": {"g": g, "b": b, "r": r},
        "bounds": {
            "finite_frame_size": N,
            "sample_size": n,
            "lower_g_count": lower_g,
            "upper_b_count": upper_b,
            "upper_r_count": upper_r,
            "alpha_numerator": ALPHA_NUMERATOR,
            "alpha_denominator": ALPHA_DENOMINATOR,
        },
        "serving_cost": policy_cost,
        "p95_latency_ms": policy_latency,
        "mandatory_violations": policy_violations,
    }


def evaluate_stage1_report(report: dict[str, Any], prereg: dict[str, Any]) -> dict[str, Any]:
    if report.get("format") != REPORT_FORMAT or report.get("format_version") != ANALYSIS_VERSION:
        raise ConfirmationError("Stage 1 analysis report identity drift")
    if report.get("calibration_split_digest") != prereg["calibration_split_digest"]:
        raise ConfirmationError("Stage 1 calibration report split drift")
    if report.get("held_out_split_digest") != prereg["held_out_split_digest"]:
        raise ConfirmationError("Stage 1 held-out report split drift")
    if report.get("held_out_frame_sha256") != prereg["held_out_frame_sha256"]:
        raise ConfirmationError("Stage 1 finite frame identity drift")
    policy_rows = report.get("calibration_policy_rows")
    if not isinstance(policy_rows, list) or not policy_rows:
        raise ConfirmationError("Stage 1 report lacks calibration_policy_rows")
    selection = select_stage1_policies(policy_rows, prereg["baseline_policy_id"], prereg["reference_policy_id"])
    declared = report.get("selection")
    if declared != selection:
        raise ConfirmationError("Stage 1 reported P/T selection differs from preregistered selector")
    if selection["outcome"] != "CompiledCandidate":
        if report.get("held_out") not in (None, {}):
            raise ConfirmationError("Stage 1 stop outcome must not consume held-out results")
        stop_suffix = "REFERENCE_ONLY" if selection["outcome"] == "ReferenceOnly" else "NO_QUALIFIED_REFERENCE"
        return {
            "verdict": selection["outcome"],
            "selection": selection,
            "narrow_selector_verdict": f"NOT_EVALUATED_{stop_suffix}",
            "product_verdict": f"NOT_EVALUATED_{stop_suffix}",
            "incremental_selector_verdict": f"NOT_EVALUATED_{stop_suffix}",
            "qualification_passed": False,
            "failure_reasons": [],
            "P_evaluation": None,
            "T_evaluation": None,
        }

    heldout = report.get("held_out")
    if not isinstance(heldout, dict):
        raise ConfirmationError("compiled Stage 1 report lacks held_out analysis")
    n = prereg["held_out_items"]
    N = prereg["held_out_frame_count"]
    if heldout.get("sample_size") != n or heldout.get("finite_frame_size") != N:
        raise ConfirmationError("Stage 1 held-out sample/frame size drift")
    paired = heldout.get("paired_by_policy")
    costs = heldout.get("serving_cost")
    p95 = heldout.get("p95_latency_ms")
    violations = heldout.get("mandatory_violations")
    if not all(isinstance(value, dict) for value in (paired, costs, p95, violations)):
        raise ConfirmationError("Stage 1 held-out paired/economics/latency/violation aggregates missing")

    P = selection["P"]
    T = selection["T"]
    B = prereg["baseline_policy_id"]
    F = prereg["reference_policy_id"]
    for policy_id in {B, F, P, T}:
        if policy_id not in costs or policy_id not in p95 or policy_id not in violations:
            raise ConfirmationError(f"Stage 1 held-out lacks logical arm {policy_id}")
    p_eval = _evaluate_heldout_policy(
        policy_id=P,
        baseline_policy_id=B,
        reference_policy_id=F,
        paired=paired,
        costs=costs,
        p95=p95,
        violations=violations,
        N=N,
        n=n,
    )
    t_eval = _evaluate_heldout_policy(
        policy_id=T,
        baseline_policy_id=B,
        reference_policy_id=F,
        paired=paired,
        costs=costs,
        p95=p95,
        violations=violations,
        N=N,
        n=n,
    )

    p_product_gate_pass = p_eval["product_verdict"] == "PASS"
    t_product_gate_pass = t_eval["product_verdict"] == "PASS"
    if p_product_gate_pass and not t_product_gate_pass:
        incremental = "FAVORS_P_DESCRIPTIVELY"
    elif t_product_gate_pass and not p_product_gate_pass:
        incremental = "FAVORS_CONVENTIONAL_TUNER_DESCRIPTIVELY"
    elif p_product_gate_pass and t_product_gate_pass:
        incremental = "NO_SPECIAL_SELECTOR_ADVANTAGE_DEMONSTRATED"
    else:
        incremental = "NO_COMPILER_VALUE_DEMONSTRATED"

    product_inference_allowed = _competence_allows_product_inference(prereg)
    if product_inference_allowed:
        verdict = p_eval["product_verdict"]
        product_verdict = p_eval["product_verdict"]
        qualification_passed = p_product_gate_pass
        incremental_scope = "descriptive-product-gate-comparison"
    else:
        verdict = "ALGORITHM_DIAGNOSTIC_ONLY"
        product_verdict = "NOT_AUTHORIZED_ALGORITHM_DIAGNOSTIC_ONLY"
        qualification_passed = False
        incremental_scope = "descriptive-algorithm-diagnostic-only"

    return {
        "verdict": verdict,
        "selection": selection,
        "narrow_selector_verdict": p_eval["narrow_selector_verdict"],
        "product_gate_verdict": p_eval["product_verdict"],
        "product_verdict": product_verdict,
        "product_inference_allowed": product_inference_allowed,
        "incremental_selector_verdict": incremental,
        "incremental_selector_scope": incremental_scope,
        "qualification_passed": qualification_passed,
        "failure_reasons": p_eval["product_failure_reasons"],
        "P_evaluation": p_eval,
        "T_evaluation": t_eval,
    }


def _verify_bound_sources(prereg: dict[str, Any]) -> None:
    expected = prereg.get("bound_source_files")
    if not isinstance(expected, dict) or expected != _source_hashes():
        raise ConfirmationError("bound source files drifted after preregistration")
    if prereg.get("surface_fingerprint") != surface_sha256():
        raise ConfirmationError("model surface drifted after preregistration")


def verify_confirmation(args: argparse.Namespace) -> dict[str, Any]:
    prereg = _load_object(args.preregistration)
    if prereg.get("format") != PREREG_FORMAT or prereg.get("format_version") != FORMAT_VERSION:
        raise ConfirmationError("unsupported Stage 1 preregistration identity")
    _verify_bound_sources(prereg)
    if _file_sha256(args.freeze / "freeze-manifest.json") != prereg.get("freeze_manifest_sha256"):
        raise ConfirmationError("freeze manifest drifted after preregistration")
    freeze_manifest = _require_stage1_freeze(args.freeze)
    if freeze_manifest["calibration_split_digest"] != prereg["calibration_split_digest"]:
        raise ConfirmationError("preregistered calibration split identity drift")
    if freeze_manifest["held_out_split_digest"] != prereg["held_out_split_digest"]:
        raise ConfirmationError("preregistered held-out split identity drift")
    if freeze_manifest["held_out_frame_sha256"] != prereg["held_out_frame_sha256"]:
        raise ConfirmationError("preregistered finite frame identity drift")
    report = _load_object(args.stage1_report)
    gate_result = evaluate_stage1_report(report, prereg)
    product_inference_allowed = _competence_allows_product_inference(prereg)
    if product_inference_allowed:
        authorized_claim = (
            "In the frozen Qwen/FEVER oracle-page-pooled Stage 1 study, a policy selected before held-out "
            "met the preregistered Base-improvement, Reference-regression, serving-cost, latency, and contract gates."
        )
    else:
        authorized_claim = (
            "This Stage 1 run is algorithm-diagnostic-only because a defensible absolute pre-score B/F competence "
            "floor was not established; it may report selector/reference/tuner behavior but cannot qualify a product profile."
        )
    result = {
        "format": RESULT_FORMAT,
        "format_version": FORMAT_VERSION,
        "preregistration_fingerprint": _file_sha256(args.preregistration),
        "freeze_manifest_fingerprint": prereg["freeze_manifest_sha256"],
        "calibration_split_digest": prereg["calibration_split_digest"],
        "held_out_split_digest": prereg["held_out_split_digest"],
        "held_out_frame_sha256": prereg["held_out_frame_sha256"],
        "product_inference_allowed": product_inference_allowed,
        "stage1": gate_result,
        "authorized_claim": authorized_claim,
        "claim_not_supported": [
            "release qualification for v1.1",
            "real-retrieval customer value",
            "universal same-model improvement",
            "cross-runtime transfer",
            "established category distinctness",
            "a durable moat",
        ] + ([] if product_inference_allowed else ["product qualification from this FEVER Stage 1 run"]),
    }
    payload = canonical_bytes(result)
    if args.output.exists():
        if args.output.read_bytes() != payload:
            raise ConfirmationError("Stage 1 result output exists with different payload")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(payload)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("preflight")
    p.add_argument("--freeze", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)

    p = sub.add_parser("preregister")
    p.add_argument("--freeze", type=Path, required=True)
    p.add_argument("--primary", type=Path, required=True, help="primary inference artifact used by the frozen stack")
    p.add_argument("--executor", type=Path, required=True, help="runtime executable used by the frozen stack")
    p.add_argument("--stack-name", required=True)
    p.add_argument("--threads", type=int, default=2)
    p.add_argument("--competence-record", type=Path, required=True)
    p.add_argument("--cost-model", type=Path, required=True)
    p.add_argument("--timing-protocol", type=Path, required=True)
    p.add_argument("--analysis-record", type=Path, required=True)
    p.add_argument("--contract-record", type=Path, required=True)
    p.add_argument("--semantic-metadata", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)

    p = sub.add_parser("verify")
    p.add_argument("--preregistration", type=Path, required=True)
    p.add_argument("--freeze", type=Path, required=True)
    p.add_argument("--stage1-report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "preflight":
            result = write_preflight(args.freeze, args.output)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["preflight_passed"] else 2
        if args.command == "preregister":
            result = preregister(args)
            print(json.dumps({
                "status": "PREREGISTERED",
                "calibration_items": result["calibration_items"],
                "held_out_items": result["held_out_items"],
                "held_out_frame_count": result["held_out_frame_count"],
                "calibration_split_digest": result["calibration_split_digest"],
                "held_out_split_digest": result["held_out_split_digest"],
            }, indent=2, sort_keys=True))
            return 0
        result = verify_confirmation(args)
        verdict = result["stage1"]["verdict"]
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if verdict == "PASS" else 2
    except (ConfirmationError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
