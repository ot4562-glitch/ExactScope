#!/usr/bin/env python3
"""Execute the preregistered ExactScope v1.1 Qwen/FEVER Stage 1 diagnostic.

This is deliberately separate from the historical Harness Distillation Pareto /
AmplifierProfile runner. It implements the current B/F/P/T protocol only.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "tools", ROOT / "benchmarks", ROOT / "adapters/llama-cpp"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from grounding_canonical import canonical_bytes, loads  # noqa: E402
from harness_distillation import HostQualification, calibration_policy_ids, minimum_candidate_catalog  # noqa: E402
import harness_distillation_confirmation as confirmation  # noqa: E402
import harness_distillation_fever as driver  # noqa: E402
import public_fever_benchmark as fever  # noqa: E402

CALIBRATION_ANALYSIS_FORMAT = "exactscope.harness-fever-stage1-calibration-analysis"
FORMAT_VERSION = "0.1"


class Stage1Error(RuntimeError):
    pass


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise Stage1Error(f"cannot load JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise Stage1Error(f"expected JSON object: {path}")
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise Stage1Error(f"non-object JSONL row at {path}:{line_number}")
                rows.append(value)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Stage1Error(f"cannot load JSONL: {path}") from exc
    return rows


def _write_immutable(path: Path, value: dict[str, Any]) -> None:
    payload = canonical_bytes(value)
    if path.exists():
        if path.read_bytes() != payload:
            raise Stage1Error(f"output exists with different payload: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _load_cost_model(path: Path) -> dict[str, Any]:
    record = _load_object(path)
    if record.get("format") != "exactscope.stage1-serving-cost-model" or record.get("format_version") != FORMAT_VERSION:
        raise Stage1Error("unsupported Stage 1 serving-cost model")
    coefficients = record.get("integer_coefficients")
    if coefficients != {"e2e_latency_ms": 1}:
        raise Stage1Error("first Stage 1 runner supports only the frozen e2e_latency_ms=1 cost model")
    if record.get("double_count_reviewed") is not True:
        raise Stage1Error("serving-cost model lacks double-count review")
    return record


def _record_cost(record: dict[str, Any], cost_model: dict[str, Any]) -> int:
    _ = cost_model
    value = record.get("e2e_latency_ms")
    if type(value) is not int or value < 0:
        raise Stage1Error("run record lacks nonnegative integer e2e_latency_ms")
    return value


def _gold_by_id(candidate: Path) -> dict[str, str]:
    rows = _load_jsonl(candidate / "gold" / "items.jsonl")
    result: dict[str, str] = {}
    for row in rows:
        item_id = row.get("id")
        label = row.get("label")
        if not isinstance(item_id, str) or label not in fever.LABELS or item_id in result:
            raise Stage1Error("invalid/duplicate Stage 1 gold row")
        result[item_id] = label
    return result


def _read_run(run: Path, *, stage: str, split_digest: str) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    manifest = _load_object(run / "run-manifest.json")
    if manifest.get("format") != driver.RUN_FORMAT or manifest.get("format_version") != driver.FORMAT_VERSION:
        raise Stage1Error("Stage 1 run manifest identity drift")
    if manifest.get("stage") != stage or manifest.get("split_digest") != split_digest:
        raise Stage1Error("Stage 1 run stage/split drift")
    raw_path = run / "raw-results.jsonl"
    if driver._file_sha256(raw_path) != manifest.get("raw_results_sha256"):
        raise Stage1Error("Stage 1 raw-results digest drift")
    host_record = _load_object(run / "host-record.json")
    if driver._file_sha256(run / "host-record.json") != manifest.get("host_record_sha256"):
        raise Stage1Error("Stage 1 host-record digest drift")
    return manifest, host_record, _load_jsonl(raw_path)


def _validate_matrix(records: list[dict[str, Any]], item_ids: set[str], policy_ids: list[str]) -> dict[tuple[str, str], dict[str, Any]]:
    expected = {(item_id, policy_id) for item_id in item_ids for policy_id in policy_ids}
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = (record.get("item_id"), record.get("policy_id"))
        if not isinstance(key[0], str) or not isinstance(key[1], str) or key in indexed:
            raise Stage1Error("Stage 1 run contains invalid/duplicate observation identity")
        indexed[key] = record
    if set(indexed) != expected:
        missing = sorted(expected - set(indexed))[:3]
        extra = sorted(set(indexed) - expected)[:3]
        raise Stage1Error(f"Stage 1 observation matrix drift missing={missing} extra={extra}")
    return indexed


def _record_success(record: dict[str, Any], gold_label: str) -> bool:
    if record.get("valid") is not True:
        return False
    normalized = fever.normalize_label(record.get("value"))
    return normalized == gold_label


def _mandatory_violation(record: dict[str, Any]) -> bool:
    return record.get("valid") is not True or record.get("model_calls") != 1


def score_calibration_records(
    records: list[dict[str, Any]],
    *,
    gold: dict[str, str],
    policy_ids: list[str],
    cost_model: dict[str, Any],
    reference_policy_id: str = confirmation.REFERENCE_POLICY_ID,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    indexed = _validate_matrix(records, set(gold), policy_ids)
    if reference_policy_id not in policy_ids:
        raise Stage1Error("calibration matrix lacks predeclared Reference")

    success: dict[tuple[str, str], bool] = {}
    for item_id, gold_label in gold.items():
        for policy_id in policy_ids:
            success[(item_id, policy_id)] = _record_success(indexed[(item_id, policy_id)], gold_label)

    policy_rows: list[dict[str, Any]] = []
    resources: dict[str, Any] = {}
    for policy_id in policy_ids:
        policy_records = [indexed[(item_id, policy_id)] for item_id in sorted(gold, key=lambda value: value.encode("utf-8"))]
        reference_loss_count = sum(
            1
            for item_id in gold
            if success[(item_id, reference_policy_id)] and not success[(item_id, policy_id)]
        )
        success_count = sum(success[(item_id, policy_id)] for item_id in gold)
        serving_cost = sum(_record_cost(record, cost_model) for record in policy_records)
        violation_count = sum(_mandatory_violation(record) for record in policy_records)
        policy_rows.append({
            "policy_id": policy_id,
            "valid": True,
            "mandatory_gates_pass": violation_count == 0,
            "success_count": success_count,
            "reference_loss_count": reference_loss_count,
            "serving_cost": serving_cost,
        })
        resources[policy_id] = {
            "item_count": len(policy_records),
            "success_count": success_count,
            "mandatory_violation_count": violation_count,
            "serving_cost": serving_cost,
            "model_calls": sum(int(record.get("model_calls", 0)) for record in policy_records),
            "prompt_tokens": sum(int(record.get("prompt_tokens", 0)) for record in policy_records),
            "completion_tokens": sum(int(record.get("completion_tokens", 0)) for record in policy_records),
            "exactscope_cpu_ms": sum(int(record.get("exactscope_cpu_ms", 0)) for record in policy_records),
            "evidence_bytes": sum(int(record.get("evidence_bytes", 0)) for record in policy_records),
        }
    policy_rows.sort(key=lambda row: row["policy_id"].encode("utf-8"))
    selection = confirmation.select_stage1_policies(
        policy_rows,
        confirmation.BASELINE_POLICY_ID,
        reference_policy_id,
    )
    return policy_rows, selection, resources


def _nearest_rank_p95(values: list[int]) -> int:
    if not values or any(type(value) is not int or value < 0 for value in values):
        raise Stage1Error("p95 requires nonempty nonnegative integer timings")
    ordered = sorted(values)
    rank = max(1, math.ceil(0.95 * len(ordered)))
    return ordered[rank - 1]


def build_heldout_summary(
    records: list[dict[str, Any]],
    *,
    gold: dict[str, str],
    logical_policy_ids: list[str],
    selection: dict[str, Any],
    cost_model: dict[str, Any],
) -> dict[str, Any]:
    unique_ids = list(dict.fromkeys(logical_policy_ids))
    indexed = _validate_matrix(records, set(gold), unique_ids)
    success: dict[tuple[str, str], bool] = {}
    for item_id, gold_label in gold.items():
        for policy_id in unique_ids:
            success[(item_id, policy_id)] = _record_success(indexed[(item_id, policy_id)], gold_label)

    B = confirmation.BASELINE_POLICY_ID
    F = confirmation.REFERENCE_POLICY_ID
    P = selection.get("P")
    T = selection.get("T")
    if not isinstance(P, str) or not isinstance(T, str):
        raise Stage1Error("held-out summary requires frozen P and T")

    paired: dict[str, Any] = {}
    for policy_id in (P, T):
        paired[policy_id] = {
            "g": sum(success[(item_id, policy_id)] and not success[(item_id, B)] for item_id in gold),
            "b": sum(not success[(item_id, policy_id)] and success[(item_id, B)] for item_id in gold),
            "r": sum(not success[(item_id, policy_id)] and success[(item_id, F)] for item_id in gold),
        }

    serving_cost: dict[str, int] = {}
    p95: dict[str, int] = {}
    violations: dict[str, int] = {}
    descriptive: dict[str, Any] = {}
    for policy_id in unique_ids:
        policy_records = [indexed[(item_id, policy_id)] for item_id in sorted(gold, key=lambda value: value.encode("utf-8"))]
        serving_cost[policy_id] = sum(_record_cost(record, cost_model) for record in policy_records)
        p95[policy_id] = _nearest_rank_p95([int(record["e2e_latency_ms"]) for record in policy_records])
        violations[policy_id] = sum(_mandatory_violation(record) for record in policy_records)
        descriptive[policy_id] = {
            "success_count": sum(success[(item_id, policy_id)] for item_id in gold),
            "item_count": len(gold),
            "model_calls": sum(int(record.get("model_calls", 0)) for record in policy_records),
            "prompt_tokens": sum(int(record.get("prompt_tokens", 0)) for record in policy_records),
            "completion_tokens": sum(int(record.get("completion_tokens", 0)) for record in policy_records),
            "exactscope_cpu_ms": sum(int(record.get("exactscope_cpu_ms", 0)) for record in policy_records),
            "evidence_bytes": sum(int(record.get("evidence_bytes", 0)) for record in policy_records),
        }
    return {
        "sample_size": len(gold),
        "paired_by_policy": paired,
        "serving_cost": serving_cost,
        "p95_latency_ms": p95,
        "mandatory_violations": violations,
        "descriptive": descriptive,
    }


def _load_preregistration_identity(path: Path, *, freeze: Path) -> dict[str, Any]:
    prereg = _load_object(path)
    if prereg.get("format") != confirmation.PREREG_FORMAT or prereg.get("format_version") != confirmation.FORMAT_VERSION:
        raise Stage1Error("unsupported Stage 1 preregistration")
    if prereg.get("runner_id") != confirmation.STAGE1_RUNNER_ID:
        raise Stage1Error("Stage 1 preregistration runner identity drift")
    confirmation._verify_bound_sources(prereg)
    freeze_manifest = confirmation._require_stage1_freeze(freeze)
    if driver._file_sha256(freeze / "freeze-manifest.json") != prereg.get("freeze_manifest_sha256"):
        raise Stage1Error("Stage 1 freeze differs from preregistration")
    if freeze_manifest["calibration_split_digest"] != prereg.get("calibration_split_digest"):
        raise Stage1Error("Stage 1 calibration split differs from preregistration")
    if freeze_manifest["held_out_split_digest"] != prereg.get("held_out_split_digest"):
        raise Stage1Error("Stage 1 held-out split differs from preregistration")
    return prereg


def _load_bound_preregistration(
    path: Path,
    *,
    freeze: Path,
    model_path: Path,
    runtime_executable: Path,
    model_key: str,
    threads: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    prereg = _load_preregistration_identity(path, freeze=freeze)

    stack = prereg.get("stack_identity")
    if not isinstance(stack, dict):
        raise Stage1Error("Stage 1 preregistration lacks stack identity")
    if driver._file_sha256(model_path) != stack.get("primary") or model_path.stat().st_size != stack.get("primary_bytes"):
        raise Stage1Error("Stage 1 model artifact differs from preregistration")
    if driver._file_sha256(runtime_executable) != stack.get("executor"):
        raise Stage1Error("Stage 1 runtime executable differs from preregistration")
    if threads != stack.get("threads"):
        raise Stage1Error("Stage 1 thread count differs from preregistration")
    if prereg.get("surface_fingerprint") != driver.surface_sha256():
        raise Stage1Error("Stage 1 adapter/model surface differs from preregistration")

    protocol_records = prereg.get("protocol_records")
    if not isinstance(protocol_records, dict):
        raise Stage1Error("Stage 1 preregistration lacks protocol records")
    contract = protocol_records.get("contract")
    if not isinstance(contract, dict):
        raise Stage1Error("Stage 1 preregistration lacks frozen contract")
    confirmation._validate_contract_record(contract)
    if contract.get("model_key") != model_key:
        raise Stage1Error("Stage 1 model key differs from frozen contract")
    if contract.get("model_sha256") != stack.get("primary") or contract.get("runtime_sha256") != stack.get("executor"):
        raise Stage1Error("Stage 1 frozen contract stack identity drift")
    return prereg, contract


def freeze_contract(args: argparse.Namespace) -> dict[str, Any]:
    if args.output.exists():
        raise Stage1Error("frozen contract output already exists")
    if not args.model_path.is_file() or not args.runtime_executable.is_file():
        raise Stage1Error("model/runtime executable missing")
    server_log_path = args.output.with_suffix(".llama-server.log")
    server_log_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    runtime_dir = str(args.runtime_executable.resolve().parent)
    if os.name != "nt":
        env["LD_LIBRARY_PATH"] = runtime_dir + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    process: subprocess.Popen[bytes] | None = None
    with server_log_path.open("wb") as server_log:
        process = subprocess.Popen(
            driver._server_command(args.runtime_executable, args.model_path, args.port, args.threads),
            cwd=runtime_dir,
            stdout=server_log,
            stderr=subprocess.STDOUT,
            env=env,
        )
        try:
            driver.wait_server(process, "127.0.0.1", args.port, 180)
            calibration = driver.adapter.calibrate_contract(
                base_url=f"http://127.0.0.1:{args.port}/v1",
                model="exactscope-harness-model",
                model_key=args.model_key,
                policy=driver.POLICY_PATH.read_bytes(),
                timeout_seconds=90,
            )
        finally:
            if process is not None:
                driver.stop_server(process)
    record = {
        "format": "exactscope.stage1-frozen-contract-record",
        "format_version": FORMAT_VERSION,
        "model_key": args.model_key,
        "model_sha256": driver._file_sha256(args.model_path),
        "runtime_sha256": driver._file_sha256(args.runtime_executable),
        "selected_contract": calibration["selected_contract"],
        "selected_output_surface": calibration["selected_output_surface"],
        "selection_frozen_before_stage1_scoring": True,
        "calibration_scope": "synthetic interface/answer-contract calibration only; no Stage 1 FEVER item consumed",
        "surface_fingerprint": driver.surface_sha256(),
        "contract_calibration": calibration,
        "server_log": str(server_log_path),
    }
    confirmation._validate_contract_record(record)
    _write_immutable(args.output, record)
    return record


def _run_stage(
    *,
    freeze: Path,
    candidate_name: str,
    split_key: str,
    stage_name: str,
    policy_ids: list[str] | None,
    model_path: Path,
    runtime_executable: Path,
    model_key: str,
    port: int,
    threads: int,
    output: Path,
    preregistration: Path,
    logical_roles: dict[str, str] | None = None,
    expected_host_record: dict[str, Any] | None = None,
) -> None:
    prereg, frozen_contract = _load_bound_preregistration(
        preregistration,
        freeze=freeze,
        model_path=model_path,
        runtime_executable=runtime_executable,
        model_key=model_key,
        threads=threads,
    )
    freeze_manifest = confirmation._require_stage1_freeze(freeze)
    candidate = freeze / candidate_name
    _candidate_manifest, items, _candidate_rows, _corpus = fever.verify_serving_candidate(candidate)
    expected_item_ids = tuple(freeze_manifest[split_key]["item_ids"])
    actual_item_ids = tuple(sorted((item["id"] for item in items), key=lambda value: value.encode("utf-8")))
    if actual_item_ids != expected_item_ids:
        raise Stage1Error(f"{stage_name} serving items differ from frozen split")
    if not model_path.is_file() or not runtime_executable.is_file():
        raise Stage1Error("model/runtime executable missing")

    server_log_path = output.with_suffix(".llama-server.log")
    server_log_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    runtime_dir = str(runtime_executable.resolve().parent)
    if os.name != "nt":
        env["LD_LIBRARY_PATH"] = runtime_dir + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    process: subprocess.Popen[bytes] | None = None
    with server_log_path.open("wb") as server_log:
        process = subprocess.Popen(
            driver._server_command(runtime_executable, model_path, port, threads),
            cwd=runtime_dir,
            stdout=server_log,
            stderr=subprocess.STDOUT,
            env=env,
        )
        try:
            driver.wait_server(process, "127.0.0.1", port, 180)
            base_url = f"http://127.0.0.1:{port}/v1"
            contract_record = frozen_contract["contract_calibration"]
            host_record = driver._host_record(
                model_path=model_path,
                runtime_path=runtime_executable,
                model_key=model_key,
                contract_record=contract_record,
                threads=threads,
            )
            host = HostQualification(**host_record["host_qualification"])
            candidates = minimum_candidate_catalog(host)
            executable = list(calibration_policy_ids(candidates))
            if prereg.get("calibration_policy_ids") != executable:
                raise Stage1Error("executable Stage 1 candidate matrix differs from preregistration")
            if prereg.get("candidate_catalog") != [candidate.as_dict() for candidate in candidates]:
                raise Stage1Error("Stage 1 candidate catalog differs from preregistration")
            selected_policy_ids = executable if policy_ids is None else list(dict.fromkeys(policy_ids))
            unknown = [policy_id for policy_id in selected_policy_ids if policy_id not in executable]
            if unknown:
                raise Stage1Error(f"Stage 1 requested non-executable policy IDs: {unknown}")
            if expected_host_record is not None and host_record != expected_host_record:
                raise Stage1Error("held-out host/contract qualification differs from calibration")
            records = driver._run_records(
                candidate=candidate,
                host_record=host_record,
                policy_ids=selected_policy_ids,
                candidates=candidates,
                base_url=base_url,
            )
        finally:
            if process is not None:
                driver.stop_server(process)

    split_digest = freeze_manifest["calibration_split_digest" if split_key == "calibration_split" else "held_out_split_digest"]
    driver._write_run(
        output,
        {
            "format": driver.RUN_FORMAT,
            "format_version": driver.FORMAT_VERSION,
            "stage": stage_name,
            "runner_id": confirmation.STAGE1_RUNNER_ID,
            "split_digest": split_digest,
            "policy_ids": selected_policy_ids,
            "logical_policy_roles": logical_roles or {
                "B": confirmation.BASELINE_POLICY_ID,
                "F": confirmation.REFERENCE_POLICY_ID,
            },
            "preregistration_sha256": driver._file_sha256(preregistration),
            "frozen_contract_record_sha256": prereg["protocol_record_sha256"]["contract"],
            "gold_visible_to_model_runner": False,
            "profile_reselected_on_held_out": False if stage_name == "stage1-heldout" else None,
            "server_log": str(server_log_path),
        },
        host_record,
        records,
    )


def run_calibration(args: argparse.Namespace) -> None:
    with driver._exclusive_run_lock(args.output):
        _run_stage(
            freeze=args.freeze,
            candidate_name="calibration-candidate",
            split_key="calibration_split",
            stage_name="stage1-calibration",
            policy_ids=None,
            model_path=args.model_path,
            runtime_executable=args.runtime_executable,
            model_key=args.model_key,
            port=args.port,
            threads=args.threads,
            output=args.output,
            preregistration=args.preregistration,
        )


def score_calibration(args: argparse.Namespace) -> dict[str, Any]:
    prereg = _load_preregistration_identity(args.preregistration, freeze=args.freeze)
    freeze_manifest = confirmation._require_stage1_freeze(args.freeze)
    manifest, host_record, records = _read_run(
        args.run,
        stage="stage1-calibration",
        split_digest=freeze_manifest["calibration_split_digest"],
    )
    if manifest.get("runner_id") != confirmation.STAGE1_RUNNER_ID:
        raise Stage1Error("calibration run runner identity drift")
    if manifest.get("preregistration_sha256") != driver._file_sha256(args.preregistration):
        raise Stage1Error("calibration run is not bound to this preregistration")
    policy_ids = manifest.get("policy_ids")
    if policy_ids != prereg.get("calibration_policy_ids"):
        raise Stage1Error("calibration run policy matrix differs from preregistration")
    if driver._file_sha256(args.cost_model) != prereg["protocol_record_sha256"]["serving_cost_model"]:
        raise Stage1Error("calibration scoring cost model differs from preregistration")
    cost_model = _load_cost_model(args.cost_model)
    gold = _gold_by_id(args.freeze / "calibration-candidate")
    policy_rows, selection, resources = score_calibration_records(
        records,
        gold=gold,
        policy_ids=policy_ids,
        cost_model=cost_model,
    )
    result = {
        "format": CALIBRATION_ANALYSIS_FORMAT,
        "format_version": FORMAT_VERSION,
        "calibration_split_digest": freeze_manifest["calibration_split_digest"],
        "held_out_split_digest": freeze_manifest["held_out_split_digest"],
        "held_out_frame_sha256": freeze_manifest["held_out_frame_sha256"],
        "preregistration_sha256": driver._file_sha256(args.preregistration),
        "host_record_sha256": driver._file_sha256(args.run / "host-record.json"),
        "cost_model_sha256": driver._file_sha256(args.cost_model),
        "calibration_policy_rows": policy_rows,
        "selection": selection,
        "resources": resources,
        "held_out_consumed": False,
    }
    _write_immutable(args.output, result)
    return result


def run_heldout(args: argparse.Namespace) -> None:
    prereg = _load_preregistration_identity(args.preregistration, freeze=args.freeze)
    prereg_sha256 = driver._file_sha256(args.preregistration)
    calibration = _load_object(args.calibration_analysis)
    if calibration.get("format") != CALIBRATION_ANALYSIS_FORMAT or calibration.get("format_version") != FORMAT_VERSION:
        raise Stage1Error("unsupported calibration analysis")
    if calibration.get("preregistration_sha256") != prereg_sha256:
        raise Stage1Error("calibration analysis is not bound to this preregistration")
    if calibration.get("cost_model_sha256") != prereg["protocol_record_sha256"]["serving_cost_model"]:
        raise Stage1Error("calibration analysis cost model identity drift")
    selection = calibration.get("selection")
    if not isinstance(selection, dict) or selection.get("outcome") != "CompiledCandidate":
        raise Stage1Error("held-out is forbidden unless calibration produced CompiledCandidate(P)")
    P = selection.get("P")
    T = selection.get("T")
    if not isinstance(P, str) or not isinstance(T, str):
        raise Stage1Error("calibration analysis lacks frozen P/T")
    calibration_manifest = _load_object(args.calibration_run / "run-manifest.json")
    if calibration_manifest.get("preregistration_sha256") != prereg_sha256:
        raise Stage1Error("calibration run is not bound to this preregistration")
    expected_host_record = _load_object(args.calibration_run / "host-record.json")
    logical = [confirmation.BASELINE_POLICY_ID, confirmation.REFERENCE_POLICY_ID, P, T]
    with driver._exclusive_run_lock(args.output):
        _run_stage(
            freeze=args.freeze,
            candidate_name="heldout-candidate",
            split_key="held_out_split",
            stage_name="stage1-heldout",
            policy_ids=logical,
            model_path=args.model_path,
            runtime_executable=args.runtime_executable,
            model_key=args.model_key,
            port=args.port,
            threads=args.threads,
            output=args.output,
            preregistration=args.preregistration,
            logical_roles={
                "B": confirmation.BASELINE_POLICY_ID,
                "F": confirmation.REFERENCE_POLICY_ID,
                "P": P,
                "T": T,
            },
            expected_host_record=expected_host_record,
        )


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    prereg = _load_preregistration_identity(args.preregistration, freeze=args.freeze)
    prereg_sha256 = driver._file_sha256(args.preregistration)
    if driver._file_sha256(args.cost_model) != prereg["protocol_record_sha256"]["serving_cost_model"]:
        raise Stage1Error("report cost model differs from preregistration")
    freeze_manifest = confirmation._require_stage1_freeze(args.freeze)
    calibration = _load_object(args.calibration_analysis)
    if calibration.get("format") != CALIBRATION_ANALYSIS_FORMAT or calibration.get("format_version") != FORMAT_VERSION:
        raise Stage1Error("unsupported calibration analysis")
    if calibration.get("preregistration_sha256") != prereg_sha256:
        raise Stage1Error("calibration analysis is not bound to this preregistration")
    selection = calibration.get("selection")
    if not isinstance(selection, dict):
        raise Stage1Error("calibration analysis lacks selection")
    if selection.get("outcome") != "CompiledCandidate":
        result = {
            "format": confirmation.REPORT_FORMAT,
            "format_version": confirmation.ANALYSIS_VERSION,
            "calibration_split_digest": freeze_manifest["calibration_split_digest"],
            "held_out_split_digest": freeze_manifest["held_out_split_digest"],
            "held_out_frame_sha256": freeze_manifest["held_out_frame_sha256"],
            "preregistration_sha256": prereg_sha256,
            "calibration_policy_rows": calibration["calibration_policy_rows"],
            "selection": selection,
            "held_out": None,
        }
        _write_immutable(args.output, result)
        return result

    manifest, _host_record, records = _read_run(
        args.heldout_run,
        stage="stage1-heldout",
        split_digest=freeze_manifest["held_out_split_digest"],
    )
    if manifest.get("runner_id") != confirmation.STAGE1_RUNNER_ID:
        raise Stage1Error("held-out run runner identity drift")
    if manifest.get("preregistration_sha256") != prereg_sha256:
        raise Stage1Error("held-out run is not bound to this preregistration")
    P = selection["P"]
    T = selection["T"]
    logical = [confirmation.BASELINE_POLICY_ID, confirmation.REFERENCE_POLICY_ID, P, T]
    expected_unique = list(dict.fromkeys(logical))
    expected_roles = {"B": confirmation.BASELINE_POLICY_ID, "F": confirmation.REFERENCE_POLICY_ID, "P": P, "T": T}
    if manifest.get("policy_ids") != expected_unique:
        raise Stage1Error("held-out run policy set differs from frozen B/F/P/T roles")
    if manifest.get("logical_policy_roles") != expected_roles:
        raise Stage1Error("held-out run logical B/F/P/T role mapping drift")
    cost_model = _load_cost_model(args.cost_model)
    gold = _gold_by_id(args.freeze / "heldout-candidate")
    heldout = build_heldout_summary(
        records,
        gold=gold,
        logical_policy_ids=logical,
        selection=selection,
        cost_model=cost_model,
    )
    heldout["finite_frame_size"] = freeze_manifest["held_out_frame_count"]
    result = {
        "format": confirmation.REPORT_FORMAT,
        "format_version": confirmation.ANALYSIS_VERSION,
        "calibration_split_digest": freeze_manifest["calibration_split_digest"],
        "held_out_split_digest": freeze_manifest["held_out_split_digest"],
        "held_out_frame_sha256": freeze_manifest["held_out_frame_sha256"],
        "preregistration_sha256": prereg_sha256,
        "calibration_policy_rows": calibration["calibration_policy_rows"],
        "selection": selection,
        "held_out": heldout,
    }
    _write_immutable(args.output, result)
    return result


def _stack_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--runtime-executable", type=Path, required=True)
    parser.add_argument("--model-key", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--output", type=Path, required=True)


def _runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    _stack_args(parser)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("freeze-contract")
    _stack_args(p)

    p = sub.add_parser("run-calibration")
    _runtime_args(p)

    p = sub.add_parser("score-calibration")
    p.add_argument("--freeze", type=Path, required=True)
    p.add_argument("--preregistration", type=Path, required=True)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--cost-model", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)

    p = sub.add_parser("run-heldout")
    _runtime_args(p)
    p.add_argument("--calibration-run", type=Path, required=True)
    p.add_argument("--calibration-analysis", type=Path, required=True)

    p = sub.add_parser("build-report")
    p.add_argument("--freeze", type=Path, required=True)
    p.add_argument("--preregistration", type=Path, required=True)
    p.add_argument("--calibration-analysis", type=Path, required=True)
    p.add_argument("--heldout-run", type=Path)
    p.add_argument("--cost-model", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "freeze-contract":
            result = freeze_contract(args)
            print(json.dumps({
                "selected_contract": result["selected_contract"],
                "selected_output_surface": result["selected_output_surface"],
            }, indent=2, sort_keys=True))
            return 0
        if args.command == "run-calibration":
            run_calibration(args)
            print("PASS Stage 1 calibration run")
            return 0
        if args.command == "score-calibration":
            result = score_calibration(args)
            print(json.dumps(result["selection"], indent=2, sort_keys=True))
            return 0
        if args.command == "run-heldout":
            run_heldout(args)
            print("PASS Stage 1 held-out run")
            return 0
        result = build_report(args)
        print(json.dumps({"selection": result["selection"], "held_out": result["held_out"] is not None}, indent=2, sort_keys=True))
        return 0
    except (Stage1Error, confirmation.ConfirmationError, driver.HarnessFeverError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
