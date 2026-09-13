#!/usr/bin/env python3
"""Offline scorer for the frozen Kubernetes Operations development32 run."""
from __future__ import annotations

from pathlib import Path
import json
import random
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks"
sys.path.insert(0, str(BENCH))

import kubernetes_ops_proxy_dev_run as runmod  # noqa: E402
from public_hotpot_benchmark import _f1, _normalize_answer  # noqa: E402

PROTOCOL = BENCH / "kubernetes_ops_proxy_dev_protocol.json"
OUT = ROOT / "target/kubernetes-pod-ops-docqa-v0.1/dev32/three-arm-r4"
ARMS = ("B", "R", "G")


class ProxyScoreError(RuntimeError):
    pass


def norm_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def write_score_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    pos = p * (len(ordered) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def item_utility(prediction: Any, gold: dict[str, Any]) -> float:
    if gold["truth_state"] == "answerable":
        return float(_f1(prediction, gold["answer"])[3])
    return float(
        isinstance(prediction, str)
        and _normalize_answer(prediction) == _normalize_answer(gold["answer"])
    )


def unsupported_assertion(prediction: Any, gold: dict[str, Any]) -> bool:
    if gold["truth_state"] == "answerable" or prediction is None:
        return False
    if isinstance(prediction, str) and _normalize_answer(prediction) in {"unanswerable", "ambiguous"}:
        return False
    return True


def payload_for(arm: str, hits: list[dict[str, Any]], question: str) -> bytes | None:
    if arm == "R":
        return runmod.ordinary_context(hits)
    if arm == "G":
        return runmod.exactscope_context(hits, question)[0]
    return None


def evidence_support(payload: bytes | None, gold: dict[str, Any]) -> bool:
    if gold["truth_state"] != "answerable" or payload is None:
        return False
    text = norm_ws(payload.decode("utf-8"))
    return any(norm_ws(support) in text for support in gold["support_substrings"])


def pair_stats(per_item: dict[str, dict[str, float]], left: str, right: str) -> dict[str, Any]:
    deltas = [per_item[item][right] - per_item[item][left] for item in sorted(per_item)]
    return {
        "utility_pp": 100.0 * sum(deltas) / len(deltas),
        "improved_tied_regressed": [
            sum(delta > 1e-12 for delta in deltas),
            sum(abs(delta) <= 1e-12 for delta in deltas),
            sum(delta < -1e-12 for delta in deltas),
        ],
    }


def main() -> int:
    score_dir = OUT / "score"
    if score_dir.exists():
        raise ProxyScoreError("score output already exists")
    protocol, _retrieval_manifest, questions, retrieval_by_id = runmod.validate_freeze()
    if protocol.get("runner_source_sha256") != runmod.digest(BENCH / "kubernetes_ops_proxy_dev_run.py"):
        raise ProxyScoreError("runner source digest drift")
    if protocol.get("scorer_source_sha256") != runmod.digest(Path(__file__)):
        raise ProxyScoreError("scorer source digest drift")

    run_dir = OUT / "run"
    status = runmod.load_json(run_dir / "status.json")
    expected_status = {
        "state": "complete",
        "protocol_sha256": runmod.digest(PROTOCOL),
        "candidate_manifest_sha256": runmod.digest(runmod.CANDIDATE / "manifest.json"),
        "retrieval_sha256": runmod.digest(runmod.RETRIEVAL),
        "raw_results_sha256": runmod.digest(run_dir / "raw-results.jsonl"),
        "retry_count": 0,
        "hidden_repair": False,
        "gold_visible_to_runner": False,
    }
    for key, expected in expected_status.items():
        if status.get(key) != expected:
            raise ProxyScoreError(f"run identity drift: {key}")

    rows = runmod.load_jsonl(run_dir / "raw-results.jsonl")
    keyed = {(row["item_id"], row["arm"]): row for row in rows}
    expected_keys = {(q["item_id"], arm) for q in questions for arm in ARMS}
    if set(keyed) != expected_keys:
        raise ProxyScoreError("three-arm observation matrix incomplete")

    # Scorer-side gold is opened only after all serving identities above verify.
    gold_rows = runmod.load_jsonl(runmod.CANDIDATE / "gold/answers.jsonl")
    gold = {row["item_id"]: row for row in gold_rows}
    if set(gold) != {q["item_id"] for q in questions}:
        raise ProxyScoreError("gold/question identity mismatch")

    answerable_count = sum(row["truth_state"] == "answerable" for row in gold.values())
    disposition_count = len(gold) - answerable_count
    per_item: dict[str, dict[str, float]] = {q["item_id"]: {} for q in questions}
    scored_rows: list[dict[str, Any]] = []
    arms: dict[str, dict[str, Any]] = {}

    for arm in ARMS:
        utility_total = 0.0
        answerable_f1_total = 0.0
        disposition_correct = 0
        unsupported = 0
        format_fail = 0
        support_correct = 0
        support_total = 0
        input_tokens = output_tokens = evidence_bytes = latency_us = 0
        for q in questions:
            item_id = q["item_id"]
            observation = keyed[(item_id, arm)]
            g = gold[item_id]
            valid = observation.get("model_contract_valid") is True
            prediction = observation.get("model_contract_output") if valid else None
            utility = item_utility(prediction, g) if valid else 0.0
            per_item[item_id][arm] = utility
            utility_total += utility
            if g["truth_state"] == "answerable":
                answerable_f1_total += utility
            else:
                disposition_correct += int(utility == 1.0)
            is_unsupported = bool(valid and unsupported_assertion(prediction, g))
            unsupported += int(is_unsupported)
            format_fail += int(not valid)
            input_tokens += int(observation.get("input_tokens", 0))
            output_tokens += int(observation.get("output_tokens", 0))
            evidence_bytes += int(observation.get("evidence_bytes", 0))
            latency_us += int(observation.get("model_latency_us", 0))

            support = None
            if arm in {"R", "G"} and g["truth_state"] == "answerable":
                payload = payload_for(arm, retrieval_by_id[item_id]["hits"], q["question"])
                support = evidence_support(payload, g)
                support_total += 1
                support_correct += int(support)
            scored_rows.append(
                {
                    "item_id": item_id,
                    "arm": arm,
                    "truth_state": g["truth_state"],
                    "prediction": prediction,
                    "contract_valid": valid,
                    "utility": utility,
                    "unsupported_assertion": is_unsupported,
                    "evidence_support": support,
                }
            )
        n = len(questions)
        arms[arm] = {
            "primary_utility": utility_total / n,
            "answerable_f1": answerable_f1_total / answerable_count,
            "disposition_accuracy": disposition_correct / disposition_count,
            "unsupported_assertion_count": unsupported,
            "unsupported_assertion_rate": unsupported / n,
            "unacceptable_error_count": unsupported,
            "format_failure_count": format_fail,
            "format_failure_rate": format_fail / n,
            "evidence_support_rate_answerable": support_correct / support_total if support_total else None,
            "mean_input_tokens": input_tokens / n,
            "mean_output_tokens": output_tokens / n,
            "mean_evidence_bytes": evidence_bytes / n,
            "mean_model_latency_ms": latency_us / n / 1000.0,
        }

    uncertainty = protocol["uncertainty"]
    deltas = [per_item[item]["G"] - per_item[item]["R"] for item in sorted(per_item)]
    rng = random.Random(uncertainty["seed"])
    bootstrap: list[float] = []
    for _ in range(uncertainty["resamples"]):
        indexes = [rng.randrange(len(deltas)) for _ in deltas]
        bootstrap.append(100.0 * sum(deltas[index] for index in indexes) / len(deltas))
    alpha = (1.0 - uncertainty["confidence"]) / 2.0

    r = arms["R"]
    g = arms["G"]
    quality_delta_pp = 100.0 * (g["primary_utility"] - r["primary_utility"])
    input_reduction = 1.0 - g["mean_input_tokens"] / r["mean_input_tokens"]
    evidence_reduction = 1.0 - g["mean_evidence_bytes"] / r["mean_evidence_bytes"]
    signals = {
        "G_zero_format_failures": g["format_failure_count"] == 0,
        "G_unacceptable_errors_not_above_R": g["unacceptable_error_count"] <= r["unacceptable_error_count"],
        "G_primary_utility_not_below_R_by_more_than_2pp": quality_delta_pp >= -2.0,
        "quality_path_plus_3pp": quality_delta_pp >= 3.0,
        "efficiency_path_15pct_within_quality_margin": quality_delta_pp >= -2.0 and max(input_reduction, evidence_reduction) >= 0.15,
        "safety_path_fewer_unacceptable_errors_within_quality_margin": quality_delta_pp >= -2.0 and g["unacceptable_error_count"] < r["unacceptable_error_count"],
    }
    signals["would_meet_validation_publication_shape"] = (
        signals["G_zero_format_failures"]
        and signals["G_unacceptable_errors_not_above_R"]
        and signals["G_primary_utility_not_below_R_by_more_than_2pp"]
        and (
            signals["quality_path_plus_3pp"]
            or signals["efficiency_path_15pct_within_quality_margin"]
            or signals["safety_path_fewer_unacceptable_errors_within_quality_margin"]
        )
    )

    result = {
        "format": "exactscope.public-proxy-development-score",
        "format_version": "0.1",
        "proxy_id": protocol["proxy_id"],
        "split": protocol["split"],
        "development_only": True,
        "qualification_eligible": False,
        "item_count": len(questions),
        "protocol_sha256": runmod.digest(PROTOCOL),
        "runner_source_sha256": runmod.digest(BENCH / "kubernetes_ops_proxy_dev_run.py"),
        "scorer_source_sha256": runmod.digest(Path(__file__)),
        "run_status_sha256": runmod.digest(run_dir / "status.json"),
        "primary_utility_id": protocol["primary_utility"]["id"],
        "arms": arms,
        "comparisons": {
            "R-minus-B": pair_stats(per_item, "B", "R"),
            "G-minus-B": pair_stats(per_item, "B", "G"),
            "G-minus-R": pair_stats(per_item, "R", "G"),
        },
        "paired_uncertainty_G_minus_R": {
            "method": uncertainty["method"],
            "seed": uncertainty["seed"],
            "resamples": uncertainty["resamples"],
            "confidence": uncertainty["confidence"],
            "observed_utility_pp": quality_delta_pp,
            "interval_pp": [percentile(bootstrap, alpha), percentile(bootstrap, 1.0 - alpha)],
            "probability_positive": sum(value > 0.0 for value in bootstrap) / len(bootstrap),
        },
        "resource_deltas_G_vs_R": {
            "mean_input_tokens_reduction_fraction": input_reduction,
            "mean_evidence_bytes_reduction_fraction": evidence_reduction,
            "mean_model_latency_change_fraction": g["mean_model_latency_ms"] / r["mean_model_latency_ms"] - 1.0,
        },
        "development_signals": signals,
        "note": "Development32 only. Untouched-validation32 is required before the GitHub product-evidence publication gate can pass.",
    }
    score_dir.mkdir(parents=True)
    write_score_jsonl(score_dir / "per-item.jsonl", scored_rows)
    runmod.write_json(score_dir / "summary.json", result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
