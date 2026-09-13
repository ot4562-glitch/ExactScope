#!/usr/bin/env python3
"""Validate frozen enterprise DocQA confirmatory observations.

This module is deliberately host-neutral. It does not retrieve, call a model, judge
answers, or repair outputs. A customer/host runner performs those actions. This layer
only verifies that the frozen three-arm study was executed within the prospectively
bound identities, call limits, evidence budget, item cap and no-gold boundary.
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
import enterprise_docqa_study_contract as study_contract  # noqa: E402

FORMAT_VERSION = "0.1"
QUESTION_FORMAT = "exactscope.enterprise-docqa-confirmatory-questions"
RUN_FORMAT = "exactscope.enterprise-docqa-confirmatory-run"
READINESS_FORMAT = "exactscope.enterprise-docqa-readiness"
OBSERVATION_FORMAT = "exactscope.enterprise-docqa-observation"
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
FORBIDDEN_OBSERVATION_KEYS = {
    "gold",
    "expected_answer",
    "reference_answer",
    "judge_score",
    "model_reasoning",
    "chain_of_thought",
}


class ObservationError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise ObservationError(f"cannot hash file: {path}") from exc
    return digest.hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ObservationError(f"cannot load JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise ObservationError(f"expected JSON object: {path}")
    if raw != canonical_bytes(value):
        raise ObservationError(f"object is not canonical JSON: {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ObservationError(f"cannot read JSONL: {path}") from exc
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(raw.splitlines(), 1):
        if not line:
            raise ObservationError(f"blank JSONL row: {path}:{index}")
        try:
            value = loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ObservationError(f"invalid JSONL row: {path}:{index}") from exc
        if not isinstance(value, dict) or line != canonical_bytes(value):
            raise ObservationError(f"noncanonical JSONL row: {path}:{index}")
        rows.append(value)
    return rows


def text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ObservationError(f"{label} must be nonempty text")
    return value.strip()


def nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ObservationError(f"{label} must be a nonnegative integer")
    return value


def positive_int(value: Any, label: str) -> int:
    value = nonnegative_int(value, label)
    if value == 0:
        raise ObservationError(f"{label} must be positive")
    return value


def _forbidden_keys(row: dict[str, Any], forbidden: set[str], label: str) -> None:
    overlap = set(row) & forbidden
    if overlap:
        raise ObservationError(f"{label} exposes forbidden fields: {sorted(overlap)}")


def validate_questions(path: Path, prereg: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows = load_jsonl(path)
    analysis = prereg.get("records", {}).get("analysis", {})
    expected_count = analysis.get("confirmatory_sample_size")
    if type(expected_count) is not int or expected_count <= 0:
        raise ObservationError("preregistration confirmatory sample size missing")
    if len(rows) != expected_count:
        raise ObservationError("runner-visible confirmatory question count differs from preregistration")

    by_id: dict[str, dict[str, Any]] = {}
    groups: set[str] = set()
    for index, row in enumerate(rows):
        _forbidden_keys(row, FORBIDDEN_QUESTION_KEYS, f"questions[{index}]")
        item_id = text(row.get("item_id"), f"questions[{index}].item_id")
        if item_id in by_id:
            raise ObservationError("duplicate confirmatory item_id")
        group_id = text(row.get("group_id"), f"questions[{index}].group_id")
        if group_id in groups:
            raise ObservationError("confirmatory question groups must be disjoint within the frozen sample")
        groups.add(group_id)
        question_class = row.get("question_class")
        if question_class not in QUESTION_CLASSES:
            raise ObservationError("unsupported confirmatory question_class")
        text(row.get("question"), f"questions[{index}].question")
        by_id[item_id] = row
    return rows, by_id


def _arm_limits(prereg: dict[str, Any], study: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = prereg.get("records", {})
    result = {
        "base": {
            "config_id": study["arms"]["base"],
            "max_model_calls": records.get("base", {}).get("max_model_calls"),
        },
        "integrated": {
            "config_id": study["arms"]["integrated"],
            "max_model_calls": records.get("integrated", {}).get("max_model_calls"),
        },
        "alternative": {
            "config_id": study["arms"]["alternative"],
            "max_model_calls": study.get("alternative", {}).get("max_model_calls"),
        },
    }
    for arm, value in result.items():
        text(value.get("config_id"), f"study.arms.{arm}")
        positive_int(value.get("max_model_calls"), f"{arm}.max_model_calls")
    return result


def validate_readiness_receipt(
    prereg_path: Path,
    study_path: Path,
    questions_path: Path,
    readiness_path: Path,
    prereg: dict[str, Any],
    study: dict[str, Any],
) -> dict[str, Any]:
    receipt = load_object(readiness_path)
    if receipt.get("format") != READINESS_FORMAT or receipt.get("format_version") != FORMAT_VERSION:
        raise ObservationError("unsupported readiness receipt identity")
    if receipt.get("status") != "READY_FOR_CONFIRMATORY_EXECUTION":
        raise ObservationError("readiness receipt does not authorize confirmatory execution")
    if receipt.get("model_inference_performed") is not False or receipt.get("retrieval_performed") is not False:
        raise ObservationError("readiness receipt is not a no-inference preflight")
    expected = {
        "preregistration_sha256": sha256(prereg_path),
        "study_contract_sha256": sha256(study_path),
        "questions_sha256": sha256(questions_path),
        "confirmatory_question_count": prereg.get("records", {}).get("analysis", {}).get("confirmatory_sample_size"),
        "candidate_policy_sha256": study.get("integrated_binding", {}).get("candidate_policy_sha256"),
        "workload_contract_sha256": study.get("integrated_binding", {}).get("workload_contract_sha256"),
        "host_manifest_sha256": study.get("integrated_binding", {}).get("host_manifest_sha256"),
        "ordinary_alternative_sha256": study.get("alternative_sha256"),
        "readiness_source_sha256": study.get("readiness_source_sha256"),
    }
    for field, value in expected.items():
        if receipt.get(field) != value:
            raise ObservationError(f"readiness receipt mismatch: {field}")
    text(receipt.get("confirmatory_run_output"), "readiness.confirmatory_run_output")
    return receipt


def validate_run_artifact_path(path: Path, readiness: dict[str, Any], label: str) -> Path:
    raw_root = text(readiness.get("confirmatory_run_output"), "readiness.confirmatory_run_output")
    run_root = Path(raw_root)
    if not run_root.is_absolute():
        raise ObservationError("readiness confirmatory_run_output must be absolute")
    resolved_root = run_root.resolve()
    resolved_path = path.resolve()
    try:
        relative = resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ObservationError(f"{label} is outside frozen confirmatory run output") from exc
    if relative == Path("."):
        raise ObservationError(f"{label} must be a file below frozen confirmatory run output")
    return resolved_root


def validate_observations(
    prereg: dict[str, Any],
    study: dict[str, Any],
    questions_by_id: dict[str, dict[str, Any]],
    readiness_sha256: str,
    path: Path,
) -> list[dict[str, Any]]:
    rows = load_jsonl(path)
    limits = _arm_limits(prereg, study)
    evidence = study["evidence_contract"]
    expected = {(item_id, arm) for item_id in questions_by_id for arm in limits}
    keyed: dict[tuple[str, str], dict[str, Any]] = {}

    for index, row in enumerate(rows):
        _forbidden_keys(row, FORBIDDEN_OBSERVATION_KEYS, f"observations[{index}]")
        if row.get("format") != OBSERVATION_FORMAT or row.get("format_version") != FORMAT_VERSION:
            raise ObservationError("unsupported observation identity")
        item_id = text(row.get("item_id"), f"observations[{index}].item_id")
        arm = row.get("arm")
        if item_id not in questions_by_id or arm not in limits:
            raise ObservationError("observation item/arm is outside frozen study")
        key = (item_id, arm)
        if key in keyed:
            raise ObservationError("duplicate item/arm observation")
        keyed[key] = row
        if row.get("config_id") != limits[arm]["config_id"]:
            raise ObservationError("observation config identity drift")
        if row.get("readiness_report_sha256") != readiness_sha256:
            raise ObservationError("observation readiness identity drift")
        calls = nonnegative_int(row.get("model_calls"), f"observations[{index}].model_calls")
        if calls > limits[arm]["max_model_calls"]:
            raise ObservationError("observation exceeded frozen model-call limit")
        for field in (
            "input_tokens",
            "output_tokens",
            "retrieval_units",
            "evidence_bytes",
            "projected_item_count",
            "model_service_ms",
            "e2e_ms",
        ):
            nonnegative_int(row.get(field), f"observations[{index}].{field}")
        if row["e2e_ms"] < row["model_service_ms"]:
            raise ObservationError("observation E2E time is smaller than model-service time")
        if arm == "integrated":
            if row["evidence_bytes"] > evidence["evidence_budget_bytes"]:
                raise ObservationError("Integrated evidence exceeded frozen byte budget")
            if row["projected_item_count"] > evidence["max_projected_items"]:
                raise ObservationError("Integrated projected-item count exceeded frozen cap")
        citations = row.get("citations")
        if not isinstance(citations, list):
            raise ObservationError("observation citations must be a list")
        for citation in citations:
            if not isinstance(citation, dict):
                raise ObservationError("observation citation must be an object")
            text(citation.get("source_id"), "citation.source_id")
            text(citation.get("span_id"), "citation.span_id")
        answer = row.get("answer")
        if answer is not None and not isinstance(answer, str):
            raise ObservationError("observation answer must be text or null")
        if type(row.get("abstained")) is not bool:
            raise ObservationError("observation abstained must be boolean")
        if row["abstained"] != (answer is None):
            raise ObservationError("observation abstention/answer mismatch")
        for field in ("format_valid", "finalization_valid"):
            if type(row.get(field)) is not bool:
                raise ObservationError(f"observation {field} must be boolean")
        if row.get("retry_count") != 0:
            raise ObservationError("quality retries are forbidden")
        if row.get("second_model_judge") is not False:
            raise ObservationError("runtime second-model judge is forbidden")
        if row.get("adaptive_policy_routing") is not False:
            raise ObservationError("adaptive policy routing is forbidden")

    if set(keyed) != expected:
        missing = len(expected - set(keyed))
        extra = len(set(keyed) - expected)
        raise ObservationError(f"observation matrix incomplete: missing={missing}, extra={extra}")
    return rows


def validate_bundle(
    prereg_path: Path,
    study_path: Path,
    questions_path: Path,
    readiness_path: Path,
    run_manifest_path: Path,
    observations_path: Path,
) -> dict[str, Any]:
    prereg = load_object(prereg_path)
    study = load_object(study_path)
    if study.get("format") != study_contract.FORMAT or study.get("format_version") != FORMAT_VERSION:
        raise ObservationError("unsupported study contract identity")
    if study.get("state") != "frozen-unscored":
        raise ObservationError("study contract is not frozen-unscored")
    if study.get("preregistration_sha256") != sha256(prereg_path):
        raise ObservationError("study/preregistration identity drift")
    _questions, questions_by_id = validate_questions(questions_path, prereg)
    if study.get("questions_sha256") != sha256(questions_path):
        raise ObservationError("confirmatory question set differs from frozen Study Contract")
    if study.get("confirmatory_question_count") != len(questions_by_id):
        raise ObservationError("confirmatory question count differs from frozen Study Contract")
    readiness = validate_readiness_receipt(
        prereg_path, study_path, questions_path, readiness_path, prereg, study
    )
    readiness_sha = sha256(readiness_path)
    validate_run_artifact_path(observations_path, readiness, "observations")
    validate_run_artifact_path(run_manifest_path, readiness, "run manifest")
    rows = validate_observations(prereg, study, questions_by_id, readiness_sha, observations_path)

    manifest = load_object(run_manifest_path)
    if manifest.get("format") != RUN_FORMAT or manifest.get("format_version") != FORMAT_VERSION:
        raise ObservationError("unsupported run manifest identity")
    expected_manifest = {
        "state": "complete",
        "study_contract_sha256": sha256(study_path),
        "preregistration_sha256": sha256(prereg_path),
        "questions_sha256": sha256(questions_path),
        "readiness_report_sha256": readiness_sha,
        "observations_sha256": sha256(observations_path),
        "item_count": len(questions_by_id),
        "record_count": len(rows),
        "arms": study["arms"],
        "gold_visible_to_runner": False,
        "outcome_dependent_reordering": False,
        "confirmatory_run_output": readiness["confirmatory_run_output"],
    }
    for field, expected in expected_manifest.items():
        if manifest.get(field) != expected:
            raise ObservationError(f"run manifest mismatch: {field}")
    fixed = manifest.get("fixed_counters_by_arm")
    if fixed != study.get("fixed_counters_by_arm"):
        raise ObservationError("run manifest fixed counters differ from frozen study contract")
    if not isinstance(fixed, dict) or set(fixed) != set(study["arms"]):
        raise ObservationError("run manifest fixed_counters_by_arm must cover all arms")
    for arm, counters in fixed.items():
        if not isinstance(counters, dict):
            raise ObservationError("fixed arm counters must be an object")
        for name, value in counters.items():
            text(name, "fixed counter name")
            nonnegative_int(value, f"fixed_counters_by_arm.{arm}.{name}")

    return {
        "status": "VALID",
        "item_count": len(questions_by_id),
        "record_count": len(rows),
        "study_contract_sha256": sha256(study_path),
        "readiness_report_sha256": readiness_sha,
        "run_manifest_sha256": sha256(run_manifest_path),
        "observations_sha256": sha256(observations_path),
    }


def seal_run(
    prereg_path: Path,
    study_path: Path,
    questions_path: Path,
    readiness_path: Path,
    observations_path: Path,
    output: Path,
) -> dict[str, Any]:
    if output.exists():
        raise ObservationError("run manifest output already exists")
    prereg = load_object(prereg_path)
    study = load_object(study_path)
    if study.get("format") != study_contract.FORMAT or study.get("format_version") != FORMAT_VERSION:
        raise ObservationError("unsupported study contract identity")
    if study.get("state") != "frozen-unscored" or study.get("preregistration_sha256") != sha256(prereg_path):
        raise ObservationError("study contract is not the frozen preregistration binding")
    _questions, questions_by_id = validate_questions(questions_path, prereg)
    if study.get("questions_sha256") != sha256(questions_path):
        raise ObservationError("confirmatory question set differs from frozen Study Contract")
    if study.get("confirmatory_question_count") != len(questions_by_id):
        raise ObservationError("confirmatory question count differs from frozen Study Contract")
    readiness = validate_readiness_receipt(
        prereg_path, study_path, questions_path, readiness_path, prereg, study
    )
    readiness_sha = sha256(readiness_path)
    validate_run_artifact_path(observations_path, readiness, "observations")
    validate_run_artifact_path(output, readiness, "run manifest")
    rows = validate_observations(prereg, study, questions_by_id, readiness_sha, observations_path)
    manifest = {
        "format": RUN_FORMAT,
        "format_version": FORMAT_VERSION,
        "state": "complete",
        "study_contract_sha256": sha256(study_path),
        "preregistration_sha256": sha256(prereg_path),
        "questions_sha256": sha256(questions_path),
        "readiness_report_sha256": readiness_sha,
        "observations_sha256": sha256(observations_path),
        "item_count": len(questions_by_id),
        "record_count": len(rows),
        "arms": study["arms"],
        "gold_visible_to_runner": False,
        "outcome_dependent_reordering": False,
        "confirmatory_run_output": readiness["confirmatory_run_output"],
        "fixed_counters_by_arm": study["fixed_counters_by_arm"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_bytes(manifest))
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--run-manifest", type=Path)
    parser.add_argument("--seal-run-output", type=Path)
    parser.add_argument("--observations", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.seal_run_output is not None:
            if args.run_manifest is not None:
                raise ObservationError("choose either --run-manifest validation or --seal-run-output")
            result = seal_run(
                args.prereg,
                args.study,
                args.questions,
                args.readiness,
                args.observations,
                args.seal_run_output,
            )
        else:
            if args.run_manifest is None:
                raise ObservationError("--run-manifest is required when not sealing a run")
            result = validate_bundle(
                args.prereg,
                args.study,
                args.questions,
                args.readiness,
                args.run_manifest,
                args.observations,
            )
    except (ObservationError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
