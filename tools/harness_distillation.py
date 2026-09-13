#!/usr/bin/env python3
"""Bounded Harness Distillation compiler prototype for ExactScope v1.1."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any


class DistillationError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


PROFILE_FORMAT = "exactscope.amplifier-profile"
PROFILE_VERSION = "0.1"
REPORT_FORMAT = "exactscope.harness-distillation-report"
REPORT_VERSION = "0.1"
PROMPT_PROFILES = frozenset({"full", "no-policy", "compact-native"})
EVIDENCE_BUNDLES = frozenset(
    {"Base", "A", "B", "D", "A+B", "A+D", "B+D", "A+B+D", "D+I", "A+B+D+I"}
)
MODEL_BUNDLES = frozenset({"plain", "G", "H", "G+H"})
COST_BUNDLES = frozenset(
    {"generation", "J-proof-first", "qualified-K", "J-proof-first+qualified-K"}
)
SEARCH_STAGES = frozenset({"wide", "interaction", "leave-one-out", "integrated"})
REQUIRED_POLICY_IDS = (
    "Base", "A", "B", "D", "A+B", "B+D", "A+B+D", "D+I", "A+B+D+I",
    "prompt_full+I", "prompt_reduced+I", "G", "H", "G+H", "J", "K-off", "K-on", "integrated",
)
INTERACTION_CELLS = {
    "A+B": ("Base", "A", "B", "A+B"),
    "B+D": ("Base", "B", "D", "B+D"),
    "prompt+I": ("D", "prompt_reduced", "prompt_full+I", "prompt_reduced+I"),
    "G+H": ("Base", "G", "H", "G+H"),
}
K_PARITY_PEERS = {
    "K-on": "K-off",
    "integrated": "integrated-K-off",
}


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DistillationError(f"{label} must be nonempty text")
    return value.strip()


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise DistillationError(f"{label} must be a nonnegative integer")
    return value


def _nonnegative_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise DistillationError(f"{label} must be a nonnegative number")
    return float(value)


@dataclass(frozen=True, slots=True)
class FrozenSplit:
    split_id: str
    item_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.split_id, "split_id")
        if not isinstance(self.item_ids, (tuple, list)):
            raise DistillationError("frozen split item ids must be an ordered sequence")
        object.__setattr__(self, "item_ids", tuple(self.item_ids))
        if not self.item_ids:
            raise DistillationError("frozen split must contain at least one item")
        if len(set(self.item_ids)) != len(self.item_ids):
            raise DistillationError("frozen split item ids must be unique")
        for item_id in self.item_ids:
            _text(item_id, "item_id")

    def as_dict(self) -> dict[str, Any]:
        return {"split_id": self.split_id, "item_ids": list(self.item_ids)}

    def sha256(self) -> str:
        return digest_json({"format": "exactscope.frozen-eval-split", "version": "0.1", **self.as_dict()})


@dataclass(frozen=True, slots=True)
class HostQualification:
    host_profile_digest: str
    context_fit_qualification_digest: str | None
    typed_contract_supported: bool
    native_constraint_surface_id: str | None
    gxh_qualification_digest: str | None
    zero_call_proof_supported: bool
    prefix_cache_mode: str
    prefix_cache_parity_digest: str | None

    def __post_init__(self) -> None:
        _text(self.host_profile_digest, "host_profile_digest")
        if type(self.typed_contract_supported) is not bool:
            raise DistillationError("typed_contract_supported must be boolean")
        if self.native_constraint_surface_id is not None:
            _text(self.native_constraint_surface_id, "native_constraint_surface_id")
        if self.gxh_qualification_digest is not None and (
            not self.typed_contract_supported or self.native_constraint_surface_id is None
        ):
            raise DistillationError("GxH qualification requires G semantics and an H surface")
        if type(self.zero_call_proof_supported) is not bool:
            raise DistillationError("zero_call_proof_supported must be boolean")
        _text(self.prefix_cache_mode, "prefix_cache_mode")
        if self.prefix_cache_mode == "off" and self.prefix_cache_parity_digest is not None:
            raise DistillationError("K parity evidence must be absent when K is off")
        if self.prefix_cache_mode != "off" and self.prefix_cache_parity_digest is None:
            raise DistillationError("K requires parity qualification evidence")

    def as_dict(self) -> dict[str, Any]:
        return {
            "host_profile_digest": self.host_profile_digest,
            "context_fit_qualification_digest": self.context_fit_qualification_digest,
            "typed_contract_supported": self.typed_contract_supported,
            "native_constraint_surface_id": self.native_constraint_surface_id,
            "gxh_qualification_digest": self.gxh_qualification_digest,
            "zero_call_proof_supported": self.zero_call_proof_supported,
            "prefix_cache_mode": self.prefix_cache_mode,
            "prefix_cache_parity_digest": self.prefix_cache_parity_digest,
        }

    def sha256(self) -> str:
        return digest_json({"format": "exactscope.harness-host-qualification", "version": "0.1", **self.as_dict()})


@dataclass(frozen=True, slots=True)
class CandidatePolicy:
    policy_id: str
    evidence_bundle: str
    prompt_profile: str
    model_bundle: str
    cost_bundle: str
    search_stage: str
    selection_eligible: bool = True

    def __post_init__(self) -> None:
        _text(self.policy_id, "policy_id")
        if self.evidence_bundle not in EVIDENCE_BUNDLES:
            raise DistillationError(f"unsupported evidence bundle: {self.evidence_bundle}")
        if self.prompt_profile not in PROMPT_PROFILES:
            raise DistillationError(f"unsupported prompt profile: {self.prompt_profile}")
        if self.model_bundle not in MODEL_BUNDLES:
            raise DistillationError(f"unsupported model bundle: {self.model_bundle}")
        if self.cost_bundle not in COST_BUNDLES:
            raise DistillationError(f"unsupported cost bundle: {self.cost_bundle}")
        if self.search_stage not in SEARCH_STAGES:
            raise DistillationError(f"unsupported search stage: {self.search_stage}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "evidence_bundle": self.evidence_bundle,
            "prompt_profile": self.prompt_profile,
            "model_bundle": self.model_bundle,
            "cost_bundle": self.cost_bundle,
            "search_stage": self.search_stage,
            "selection_eligible": self.selection_eligible,
        }


@dataclass(frozen=True, slots=True)
class Observation:
    item_id: str
    policy_id: str
    task_success: bool
    false_grounding: bool
    unsupported_answer: bool
    strict_format_failure: bool
    model_calls: int
    prompt_tokens: int
    completion_tokens: int
    e2e_latency_ms: float
    exactscope_cpu_ms: float
    peak_ram_bytes: int
    distribution_bytes: int
    integration_cost_units: int
    output_identity: str | None = None

    def __post_init__(self) -> None:
        _text(self.item_id, "observation item_id")
        _text(self.policy_id, "observation policy_id")
        for label in ("task_success", "false_grounding", "unsupported_answer", "strict_format_failure"):
            if type(getattr(self, label)) is not bool:
                raise DistillationError(f"{label} must be boolean")
        for label in (
            "model_calls", "prompt_tokens", "completion_tokens", "peak_ram_bytes",
            "distribution_bytes", "integration_cost_units",
        ):
            _nonnegative_int(getattr(self, label), label)
        if self.model_calls > 1:
            raise DistillationError("candidate observations must preserve the zero-or-one generation-call boundary")
        _nonnegative_number(self.e2e_latency_ms, "e2e_latency_ms")
        _nonnegative_number(self.exactscope_cpu_ms, "exactscope_cpu_ms")


@dataclass(frozen=True, slots=True)
class DistillationObjective:
    max_regressions: int = 0
    max_new_false_grounding: int = 0
    max_new_unsupported: int = 0
    max_new_format_failures: int = 0
    max_extra_model_calls: int = 0
    quality_slack_items: int = 0

    def __post_init__(self) -> None:
        for label in self.as_dict():
            _nonnegative_int(getattr(self, label), label)

    def as_dict(self) -> dict[str, int]:
        return {
            "max_regressions": self.max_regressions,
            "max_new_false_grounding": self.max_new_false_grounding,
            "max_new_unsupported": self.max_new_unsupported,
            "max_new_format_failures": self.max_new_format_failures,
            "max_extra_model_calls": self.max_extra_model_calls,
            "quality_slack_items": self.quality_slack_items,
        }


@dataclass(frozen=True, slots=True)
class PolicyAggregate:
    policy_id: str
    item_count: int
    success_count: int
    gain_count: int
    regression_count: int
    new_false_grounding: int
    new_unsupported: int
    new_format_failures: int
    model_calls: int
    prompt_tokens: int
    completion_tokens: int
    e2e_latency_ms: float
    exactscope_cpu_ms: float
    peak_ram_bytes: int
    distribution_bytes: int
    integration_cost_units: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["success_rate"] = self.success_count / self.item_count
        value["total_tokens"] = self.total_tokens
        return value


@dataclass(frozen=True, slots=True)
class AmplifierProfile:
    host_profile_digest: str
    host_qualification_digest: str
    context_fit_qualification_digest: str | None
    gxh_qualification_digest: str | None
    native_constraint_surface_id: str | None
    prefix_cache_mode: str
    prefix_cache_parity_digest: str | None
    calibration_split_digest: str
    calibration_evidence_digest: str
    selected_policy: CandidatePolicy

    def __post_init__(self) -> None:
        for label, value in (
            ("host_profile_digest", self.host_profile_digest),
            ("host_qualification_digest", self.host_qualification_digest),
            ("calibration_split_digest", self.calibration_split_digest),
            ("calibration_evidence_digest", self.calibration_evidence_digest),
        ):
            _text(value, label)
        needs_i = "I" in self.selected_policy.evidence_bundle
        if needs_i != (self.context_fit_qualification_digest is not None):
            raise DistillationError("profile I selection and context-fit qualification disagree")
        needs_gh = self.selected_policy.model_bundle == "G+H"
        if needs_gh:
            if self.gxh_qualification_digest is None or self.native_constraint_surface_id is None:
                raise DistillationError("profile GxH selection requires qualification and native surface identity")
        elif self.gxh_qualification_digest is not None or self.native_constraint_surface_id is not None:
            raise DistillationError("profile carries GxH state when GxH is not selected")
        needs_k = "qualified-K" in self.selected_policy.cost_bundle
        if needs_k:
            if self.prefix_cache_mode == "off" or self.prefix_cache_parity_digest is None:
                raise DistillationError("profile K selection requires qualified mode and parity evidence")
        elif self.prefix_cache_mode != "off" or self.prefix_cache_parity_digest is not None:
            raise DistillationError("profile carries K state when K is not selected")

    def as_dict(self) -> dict[str, Any]:
        policy = self.selected_policy
        return {
            "format": PROFILE_FORMAT,
            "format_version": PROFILE_VERSION,
            "host_profile_digest": self.host_profile_digest,
            "host_qualification_digest": self.host_qualification_digest,
            "context_fit_qualification_digest": self.context_fit_qualification_digest,
            "gxh_qualification_digest": self.gxh_qualification_digest,
            "native_constraint_surface_id": self.native_constraint_surface_id,
            "prefix_cache_mode": self.prefix_cache_mode,
            "prefix_cache_parity_digest": self.prefix_cache_parity_digest,
            "calibration_split_digest": self.calibration_split_digest,
            "calibration_evidence_digest": self.calibration_evidence_digest,
            "selected_policy": policy.as_dict(),
            "adaptive_route": {
                "proof_first": "J-proof-first" in policy.cost_bundle,
                "prefix_cache_after_proof_miss": "qualified-K" in policy.cost_bundle,
                "hot_path_calibration_model_calls": 0,
            },
        }

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.as_dict())

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class DistillationResult:
    profile: AmplifierProfile
    report: dict[str, Any]


def minimum_candidate_catalog(
    host: HostQualification, reduced_prompt_profile: str = "no-policy"
) -> tuple[CandidatePolicy, ...]:
    """Build the mandatory bounded matrix; never expand to every feature subset."""
    if reduced_prompt_profile != "no-policy":
        raise DistillationError("the first executable compiler slice supports only the no-policy reduction")
    has_i = host.context_fit_qualification_digest is not None
    has_g = host.typed_contract_supported
    has_h = host.native_constraint_surface_id is not None
    has_gh = has_g and has_h and host.gxh_qualification_digest is not None
    has_j = host.zero_call_proof_supported
    has_k = host.prefix_cache_mode != "off" and host.prefix_cache_parity_digest is not None
    return (
        CandidatePolicy("Base", "Base", "full", "plain", "generation", "wide"),
        CandidatePolicy("A", "A", "full", "plain", "generation", "wide"),
        CandidatePolicy("B", "B", "full", "plain", "generation", "wide"),
        CandidatePolicy("D", "D", "full", "plain", "generation", "wide"),
        CandidatePolicy("A+B", "A+B", "full", "plain", "generation", "interaction"),
        CandidatePolicy("A+D", "A+D", "full", "plain", "generation", "leave-one-out"),
        CandidatePolicy("B+D", "B+D", "full", "plain", "generation", "interaction"),
        CandidatePolicy("A+B+D", "A+B+D", "full", "plain", "generation", "interaction"),
        CandidatePolicy("D+I", "D+I", "full", "plain", "generation", "interaction", has_i),
        CandidatePolicy("A+B+D+I", "A+B+D+I", "full", "plain", "generation", "interaction", has_i),
        CandidatePolicy("prompt_reduced", "D", reduced_prompt_profile, "plain", "generation", "leave-one-out"),
        CandidatePolicy("prompt_full+I", "D+I", "full", "plain", "generation", "interaction", has_i),
        CandidatePolicy(
            "prompt_reduced+I", "D+I", reduced_prompt_profile, "plain", "generation", "interaction", has_i
        ),
        CandidatePolicy("G", "Base", "full", "G", "generation", "wide", has_g),
        # H by itself remains a diagnostic. Runtime support is not qualification.
        CandidatePolicy("H", "Base", "full", "H", "generation", "wide", False),
        CandidatePolicy("G+H", "Base", "full", "G+H", "generation", "interaction", has_gh),
        CandidatePolicy("J", "Base", "full", "plain", "J-proof-first", "wide", has_j),
        # K-off is a parity/control cell, not a distinct product policy. Base already
        # represents the same execution semantics when cache reuse is absent.
        CandidatePolicy("K-off", "Base", "full", "plain", "generation", "wide", False),
        CandidatePolicy("K-on", "Base", "full", "plain", "qualified-K", "wide", has_k),
        CandidatePolicy(
            "integrated-K-off",
            "A+B+D+I" if has_i else "A+B+D",
            reduced_prompt_profile,
            "G+H" if has_gh else ("G" if has_g else "plain"),
            "J-proof-first" if has_j else "generation",
            "leave-one-out",
            has_k,
        ),
        CandidatePolicy(
            "integrated",
            "A+B+D+I" if has_i else "A+B+D",
            reduced_prompt_profile,
            "G+H" if has_gh else ("G" if has_g else "plain"),
            "J-proof-first+qualified-K" if has_j and has_k else (
                "J-proof-first" if has_j else "qualified-K" if has_k else "generation"
            ),
            "integrated",
        ),
    )


def _candidate_map(candidates: Sequence[CandidatePolicy]) -> dict[str, CandidatePolicy]:
    by_id: dict[str, CandidatePolicy] = {}
    for candidate in candidates:
        if candidate.policy_id in by_id:
            raise DistillationError(f"duplicate policy id: {candidate.policy_id}")
        by_id[candidate.policy_id] = candidate
    missing = [policy_id for policy_id in REQUIRED_POLICY_IDS if policy_id not in by_id]
    if missing:
        raise DistillationError(f"bounded candidate matrix incomplete: {', '.join(missing)}")
    return by_id


def calibration_policy_ids(
    candidates: Sequence[CandidatePolicy], baseline_policy_id: str = "Base"
) -> tuple[str, ...]:
    """Return the minimal policy cells that must be executed during calibration.

    Capability-unavailable candidates are not measured. Diagnostic controls are added
    only when a selectable interaction/cache candidate actually depends on them. This
    keeps cold-path cost proportional to the host's usable semantic surface instead of
    forcing every installation through the full research rack.
    """
    by_id = _candidate_map(candidates)
    if baseline_policy_id not in by_id:
        raise DistillationError("baseline policy is missing")
    required = {baseline_policy_id}
    required.update(
        policy_id for policy_id, candidate in by_id.items() if candidate.selection_eligible
    )
    for cell in INTERACTION_CELLS.values():
        combo_id = cell[-1]
        combo = by_id.get(combo_id)
        if combo is not None and combo.selection_eligible:
            required.update(cell)
    for policy_id, candidate in by_id.items():
        if not candidate.selection_eligible or "qualified-K" not in candidate.cost_bundle:
            continue
        peer_id = K_PARITY_PEERS.get(policy_id)
        if peer_id is not None:
            required.add(peer_id)
    return tuple(policy_id for policy_id in by_id if policy_id in required)


def _validate_splits(calibration: FrozenSplit, held_out: FrozenSplit | None) -> None:
    if held_out is not None and set(calibration.item_ids) & set(held_out.item_ids):
        raise DistillationError("calibration and held-out splits must be disjoint")


def _index_observations(
    split: FrozenSplit,
    candidates: Mapping[str, CandidatePolicy],
    observations: Sequence[Observation],
) -> dict[str, dict[str, Observation]]:
    expected_items = set(split.item_ids)
    indexed = {policy_id: {} for policy_id in candidates}
    for observation in observations:
        if observation.policy_id not in candidates:
            raise DistillationError(f"observation references unknown policy: {observation.policy_id}")
        if observation.item_id not in expected_items:
            raise DistillationError(f"observation item outside frozen split: {observation.item_id}")
        bucket = indexed[observation.policy_id]
        if observation.item_id in bucket:
            raise DistillationError("duplicate policy/item observation")
        bucket[observation.item_id] = observation
    for policy_id, bucket in indexed.items():
        missing = expected_items - set(bucket)
        if missing:
            raise DistillationError(f"policy {policy_id} is missing {len(missing)} observations")
    return indexed


def _aggregate(
    split: FrozenSplit,
    indexed: Mapping[str, Mapping[str, Observation]],
    policy_id: str,
    baseline_id: str,
) -> PolicyAggregate:
    rows = [indexed[policy_id][item_id] for item_id in split.item_ids]
    base = [indexed[baseline_id][item_id] for item_id in split.item_ids]
    return PolicyAggregate(
        policy_id=policy_id,
        item_count=len(rows),
        success_count=sum(row.task_success for row in rows),
        gain_count=sum((not b.task_success) and row.task_success for row, b in zip(rows, base)),
        regression_count=sum(b.task_success and (not row.task_success) for row, b in zip(rows, base)),
        new_false_grounding=sum((not b.false_grounding) and row.false_grounding for row, b in zip(rows, base)),
        new_unsupported=sum((not b.unsupported_answer) and row.unsupported_answer for row, b in zip(rows, base)),
        new_format_failures=sum(
            (not b.strict_format_failure) and row.strict_format_failure for row, b in zip(rows, base)
        ),
        model_calls=sum(row.model_calls for row in rows),
        prompt_tokens=sum(row.prompt_tokens for row in rows),
        completion_tokens=sum(row.completion_tokens for row in rows),
        e2e_latency_ms=sum(row.e2e_latency_ms for row in rows),
        exactscope_cpu_ms=sum(row.exactscope_cpu_ms for row in rows),
        peak_ram_bytes=max(row.peak_ram_bytes for row in rows),
        distribution_bytes=max(row.distribution_bytes for row in rows),
        integration_cost_units=max(row.integration_cost_units for row in rows),
    )


def _phase_transition_ids(
    split: FrozenSplit,
    indexed: Mapping[str, Mapping[str, Observation]],
    cell: tuple[str, str, str, str],
) -> list[str]:
    base_id, left_id, right_id, combo_id = cell
    return [
        item_id
        for item_id in split.item_ids
        if not indexed[base_id][item_id].task_success
        and not indexed[left_id][item_id].task_success
        and not indexed[right_id][item_id].task_success
        and indexed[combo_id][item_id].task_success
    ]


def _interaction_score(
    aggregates: Mapping[str, PolicyAggregate], cell: tuple[str, str, str, str]
) -> float:
    base_id, left_id, right_id, combo_id = cell
    count = aggregates[base_id].item_count
    return (
        aggregates[combo_id].success_count
        - aggregates[left_id].success_count
        - aggregates[right_id].success_count
        + aggregates[base_id].success_count
    ) / count


def _dominates(left: PolicyAggregate, right: PolicyAggregate) -> bool:
    left_vector = (
        -left.success_count, left.regression_count, left.new_false_grounding,
        left.new_unsupported, left.new_format_failures, left.model_calls,
        left.total_tokens, left.e2e_latency_ms, left.exactscope_cpu_ms,
        left.peak_ram_bytes, left.distribution_bytes, left.integration_cost_units,
    )
    right_vector = (
        -right.success_count, right.regression_count, right.new_false_grounding,
        right.new_unsupported, right.new_format_failures, right.model_calls,
        right.total_tokens, right.e2e_latency_ms, right.exactscope_cpu_ms,
        right.peak_ram_bytes, right.distribution_bytes, right.integration_cost_units,
    )
    return all(a <= b for a, b in zip(left_vector, right_vector)) and any(
        a < b for a, b in zip(left_vector, right_vector)
    )


def _hard_gate(
    candidate: PolicyAggregate, baseline: PolicyAggregate, objective: DistillationObjective
) -> bool:
    return (
        candidate.regression_count <= objective.max_regressions
        and candidate.new_false_grounding <= objective.max_new_false_grounding
        and candidate.new_unsupported <= objective.max_new_unsupported
        and candidate.new_format_failures <= objective.max_new_format_failures
        and candidate.model_calls - baseline.model_calls <= objective.max_extra_model_calls
    )


def _selection_key(aggregate: PolicyAggregate) -> tuple[Any, ...]:
    return (
        aggregate.model_calls, aggregate.total_tokens, aggregate.e2e_latency_ms,
        aggregate.exactscope_cpu_ms, aggregate.peak_ram_bytes, aggregate.distribution_bytes,
        aggregate.integration_cost_units, -aggregate.gain_count, aggregate.policy_id,
    )


def _paired_reference_quality(
    split: FrozenSplit,
    indexed: Mapping[str, Mapping[str, Observation]],
    policy_id: str,
    reference_policy_id: str,
) -> dict[str, Any]:
    """Compare item-level success against a predeclared calibration reference.

    Aggregate ties are not evidence of behavioral equivalence: two policies can each
    score 3/6 while succeeding on different items. The first compiler therefore treats
    every observed success of the predeclared fixed-max policy as a preservation
    obligation before cost can break a quality tie.
    """
    gain_ids: list[str] = []
    loss_ids: list[str] = []
    for item_id in split.item_ids:
        candidate_success = indexed[policy_id][item_id].task_success
        reference_success = indexed[reference_policy_id][item_id].task_success
        if candidate_success and not reference_success:
            gain_ids.append(item_id)
        elif reference_success and not candidate_success:
            loss_ids.append(item_id)
    return {
        "gain_count": len(gain_ids),
        "loss_count": len(loss_ids),
        "gain_item_ids": gain_ids,
        "loss_item_ids": loss_ids,
        "preserves_reference_successes": not loss_ids,
    }


def _k_output_parity(
    split: FrozenSplit,
    indexed: Mapping[str, Mapping[str, Observation]],
    policy_id: str,
) -> bool:
    peer_id = K_PARITY_PEERS.get(policy_id)
    if peer_id is None or peer_id not in indexed or policy_id not in indexed:
        return False
    for item_id in split.item_ids:
        off = indexed[peer_id][item_id].output_identity
        on = indexed[policy_id][item_id].output_identity
        if off is None or on is None or off != on:
            return False
    return True


def compile_profile(
    *,
    calibration: FrozenSplit,
    host: HostQualification,
    candidates: Sequence[CandidatePolicy],
    observations: Sequence[Observation],
    objective: DistillationObjective | None = None,
    held_out: FrozenSplit | None = None,
    baseline_policy_id: str = "Base",
    fixed_max_policy_id: str = "integrated",
) -> DistillationResult:
    """Select from calibration only and emit a deterministic immutable profile."""
    objective = objective or DistillationObjective()
    _validate_splits(calibration, held_out)
    by_id = _candidate_map(candidates)
    if baseline_policy_id not in by_id:
        raise DistillationError("baseline policy is missing")
    if fixed_max_policy_id not in by_id:
        raise DistillationError("fixed-max policy is missing")
    if not by_id[fixed_max_policy_id].selection_eligible:
        raise DistillationError("fixed-max policy must be selection-eligible")
    expected_items = set(calibration.item_ids)
    for observation in observations:
        if observation.policy_id not in by_id:
            raise DistillationError(f"observation references unknown policy: {observation.policy_id}")
        if observation.item_id not in expected_items:
            raise DistillationError(f"observation item outside frozen split: {observation.item_id}")
    required_policy_ids = calibration_policy_ids(candidates, baseline_policy_id)
    executed_candidates = {policy_id: by_id[policy_id] for policy_id in required_policy_ids}
    executed_observations = tuple(
        observation for observation in observations if observation.policy_id in executed_candidates
    )
    indexed = _index_observations(calibration, executed_candidates, executed_observations)
    aggregates = {
        policy_id: _aggregate(calibration, indexed, policy_id, baseline_policy_id)
        for policy_id in required_policy_ids
    }
    baseline = aggregates[baseline_policy_id]
    if fixed_max_policy_id not in aggregates:
        raise DistillationError("fixed-max policy was not executed during calibration")
    fixed_max_reference = {
        policy_id: _paired_reference_quality(
            calibration, indexed, policy_id, fixed_max_policy_id
        )
        for policy_id in required_policy_ids
    }
    k_parity = {
        policy_id: _k_output_parity(calibration, indexed, policy_id)
        for policy_id in required_policy_ids
        if "qualified-K" in by_id[policy_id].cost_bundle
    }

    eligible: list[str] = []
    rejected: dict[str, str] = {}
    for policy_id, candidate in by_id.items():
        if not candidate.selection_eligible:
            rejected[policy_id] = "diagnostic-or-unqualified"
            continue
        if "qualified-K" in candidate.cost_bundle and not k_parity.get(policy_id, False):
            rejected[policy_id] = "K-output-parity-not-observed-on-selected-policy"
            continue
        if not _hard_gate(aggregates[policy_id], baseline, objective):
            rejected[policy_id] = "hard-safety-or-cost-gate"
            continue
        if not fixed_max_reference[policy_id]["preserves_reference_successes"]:
            rejected[policy_id] = "fixed-max-calibration-success-not-preserved"
            continue
        eligible.append(policy_id)
    if not eligible:
        raise DistillationError("no candidate survived qualification")

    frontier = [
        policy_id
        for policy_id in eligible
        if not any(
            other != policy_id and _dominates(aggregates[other], aggregates[policy_id])
            for other in eligible
        )
    ]
    best_success = max(aggregates[policy_id].success_count for policy_id in frontier)
    quality_floor = best_success - objective.quality_slack_items
    finalists = [
        policy_id for policy_id in frontier if aggregates[policy_id].success_count >= quality_floor
    ]
    selected_id = min(finalists, key=lambda policy_id: _selection_key(aggregates[policy_id]))
    selected = by_id[selected_id]

    interactions: dict[str, dict[str, Any]] = {}
    for name, cell in INTERACTION_CELLS.items():
        missing = [policy_id for policy_id in cell if policy_id not in aggregates]
        if missing:
            interactions[name] = {
                "measured": False,
                "reason": "capability-unavailable-or-not-required",
                "missing_policy_ids": missing,
            }
            continue
        interactions[name] = {
            "measured": True,
            "interaction_success_rate": _interaction_score(aggregates, cell),
            "phase_transition_item_ids": _phase_transition_ids(calibration, indexed, cell),
        }
    aggregate_dict = {
        policy_id: aggregate.as_dict() for policy_id, aggregate in sorted(aggregates.items())
    }
    executed_stages = [
        stage
        for stage in ("wide", "interaction", "leave-one-out", "integrated")
        if any(by_id[policy_id].search_stage == stage for policy_id in required_policy_ids)
    ]
    causal_checks = {
        "A+B+D": {
            "removal_neighbors": ["A+B", "A+D", "B+D"],
            "complete": all(policy_id in aggregates for policy_id in ("A+B", "A+D", "B+D")),
        },
        "integrated-K": {
            "parity_peer": "integrated-K-off",
            "complete": all(policy_id in aggregates for policy_id in ("integrated", "integrated-K-off")),
        },
    }
    evidence = {
        "calibration_split_digest": calibration.sha256(),
        "host_qualification_digest": host.sha256(),
        "objective": objective.as_dict(),
        "fixed_max_policy_id": fixed_max_policy_id,
        "fixed_max_calibration_reference": fixed_max_reference,
        "candidates": [by_id[policy_id].as_dict() for policy_id in sorted(by_id)],
        "executed_policy_ids": list(required_policy_ids),
        "skipped_policy_ids": [policy_id for policy_id in by_id if policy_id not in aggregates],
        "aggregates": aggregate_dict,
        "interactions": interactions,
        "causal_checks": causal_checks,
        "k_output_parity_by_policy": k_parity,
        "eligible_policy_ids": sorted(eligible),
        "pareto_frontier_policy_ids": sorted(frontier),
        "selected_policy_id": selected_id,
    }
    profile = AmplifierProfile(
        host_profile_digest=host.host_profile_digest,
        host_qualification_digest=host.sha256(),
        context_fit_qualification_digest=(
            host.context_fit_qualification_digest if "I" in selected.evidence_bundle else None
        ),
        gxh_qualification_digest=(host.gxh_qualification_digest if selected.model_bundle == "G+H" else None),
        native_constraint_surface_id=(
            host.native_constraint_surface_id if selected.model_bundle == "G+H" else None
        ),
        prefix_cache_mode=(host.prefix_cache_mode if "qualified-K" in selected.cost_bundle else "off"),
        prefix_cache_parity_digest=(
            host.prefix_cache_parity_digest if "qualified-K" in selected.cost_bundle else None
        ),
        calibration_split_digest=calibration.sha256(),
        calibration_evidence_digest=digest_json(evidence),
        selected_policy=selected,
    )
    report = {
        "format": REPORT_FORMAT,
        "format_version": REPORT_VERSION,
        "calibration_split_id": calibration.split_id,
        "calibration_split_digest": calibration.sha256(),
        "held_out_split_digest": held_out.sha256() if held_out is not None else None,
        "host_qualification_digest": host.sha256(),
        "objective": objective.as_dict(),
        "fixed_max_policy_id": fixed_max_policy_id,
        "fixed_max_calibration_reference": fixed_max_reference,
        "search_order": [*executed_stages, "pareto-distillation"],
        "executed_policy_ids": list(required_policy_ids),
        "skipped_policy_ids": [policy_id for policy_id in by_id if policy_id not in aggregates],
        "aggregates": aggregate_dict,
        "interactions": interactions,
        "causal_checks": causal_checks,
        "k_output_parity_by_policy": k_parity,
        "rejected_policy_ids": rejected,
        "eligible_policy_ids": sorted(eligible),
        "pareto_frontier_policy_ids": sorted(frontier),
        "selected_policy_id": selected_id,
        "profile_digest": profile.sha256(),
        "profile_bytes": len(profile.canonical_bytes()),
        "hot_path_calibration_model_calls": 0,
    }
    return DistillationResult(profile, report)


def load_profile(raw: bytes | str, host_profile_digest: str | None = None) -> AmplifierProfile:
    """Load compiled policy data without probes or calibration calls."""
    if isinstance(raw, bytes):
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DistillationError("Amplifier Profile must be UTF-8 JSON") from exc
    elif isinstance(raw, str):
        text = raw
    else:
        raise DistillationError("Amplifier Profile input must be text or bytes")
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DistillationError("Amplifier Profile is not valid JSON") from exc
    expected = {
        "format", "format_version", "host_profile_digest", "host_qualification_digest",
        "context_fit_qualification_digest", "gxh_qualification_digest", "native_constraint_surface_id",
        "prefix_cache_mode", "prefix_cache_parity_digest",
        "calibration_split_digest", "calibration_evidence_digest", "selected_policy", "adaptive_route",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise DistillationError("Amplifier Profile shape drift")
    if value.get("format") != PROFILE_FORMAT or value.get("format_version") != PROFILE_VERSION:
        raise DistillationError("unsupported Amplifier Profile identity")
    policy_value = value.get("selected_policy")
    if not isinstance(policy_value, dict):
        raise DistillationError("selected policy must be an object")
    try:
        policy = CandidatePolicy(**policy_value)
    except TypeError as exc:
        raise DistillationError("selected policy shape drift") from exc
    profile = AmplifierProfile(
        host_profile_digest=_text(value.get("host_profile_digest"), "host_profile_digest"),
        host_qualification_digest=_text(value.get("host_qualification_digest"), "host_qualification_digest"),
        context_fit_qualification_digest=value.get("context_fit_qualification_digest"),
        gxh_qualification_digest=value.get("gxh_qualification_digest"),
        native_constraint_surface_id=value.get("native_constraint_surface_id"),
        prefix_cache_mode=_text(value.get("prefix_cache_mode"), "prefix_cache_mode"),
        prefix_cache_parity_digest=value.get("prefix_cache_parity_digest"),
        calibration_split_digest=_text(value.get("calibration_split_digest"), "calibration_split_digest"),
        calibration_evidence_digest=_text(value.get("calibration_evidence_digest"), "calibration_evidence_digest"),
        selected_policy=policy,
    )
    route = value.get("adaptive_route")
    if route != profile.as_dict()["adaptive_route"]:
        raise DistillationError("adaptive route contradicts selected causal bundle")
    if host_profile_digest is not None and profile.host_profile_digest != host_profile_digest:
        raise DistillationError("Amplifier Profile does not match current host identity")
    return profile


def choose_hot_route(profile: AmplifierProfile, proof_available: bool) -> dict[str, Any]:
    """J is evaluated first; K is reachable only when generation remains necessary."""
    if type(proof_available) is not bool:
        raise DistillationError("proof_available must be boolean")
    policy = profile.selected_policy
    if proof_available and "J-proof-first" in policy.cost_bundle:
        return {
            "route": "complete",
            "model_calls": 0,
            "evidence_bundle": policy.evidence_bundle,
            "prompt_profile": None,
            "model_bundle": None,
            "prefix_cache_mode": "off",
        }
    return {
        "route": "generate",
        "model_calls": 1,
        "evidence_bundle": policy.evidence_bundle,
        "prompt_profile": policy.prompt_profile,
        "model_bundle": policy.model_bundle,
        "prefix_cache_mode": "qualified" if "qualified-K" in policy.cost_bundle else "off",
    }


def transfer_report(
    *,
    profile: AmplifierProfile,
    held_out: FrozenSplit,
    candidates: Sequence[CandidatePolicy],
    observations: Sequence[Observation],
    baseline_policy_id: str = "Base",
    fixed_max_policy_id: str = "integrated",
    objective: DistillationObjective | None = None,
) -> dict[str, Any]:
    """Evaluate a frozen profile on held-out data without reopening policy selection.

    Only the unchanged baseline, the predeclared fixed maximum, and the already compiled
    policy are required on held-out data. Running the whole candidate matrix again would
    waste inference and blur the no-reselection boundary this report is meant to prove.
    """
    objective = objective or DistillationObjective()
    by_id = _candidate_map(candidates)
    required_ids = tuple(dict.fromkeys((
        baseline_policy_id,
        fixed_max_policy_id,
        profile.selected_policy.policy_id,
    )))
    for required in required_ids:
        if required not in by_id:
            raise DistillationError(f"held-out comparison policy missing: {required}")
    if by_id[profile.selected_policy.policy_id].as_dict() != profile.selected_policy.as_dict():
        raise DistillationError("held-out candidate definition drifted from the compiled policy")

    wanted_candidates = {policy_id: by_id[policy_id] for policy_id in required_ids}
    for observation in observations:
        if observation.policy_id not in by_id:
            raise DistillationError(f"observation references unknown policy: {observation.policy_id}")
    wanted_observations = tuple(
        observation for observation in observations if observation.policy_id in wanted_candidates
    )
    indexed = _index_observations(held_out, wanted_candidates, wanted_observations)
    aggregates = {
        policy_id: _aggregate(held_out, indexed, policy_id, baseline_policy_id)
        for policy_id in required_ids
    }
    baseline = aggregates[baseline_policy_id]
    fixed_max = aggregates[fixed_max_policy_id]
    compiled = aggregates[profile.selected_policy.policy_id]
    fixed_max_reference = _paired_reference_quality(
        held_out, indexed, profile.selected_policy.policy_id, fixed_max_policy_id
    )

    rejection_reasons: list[str] = []
    if not _hard_gate(compiled, baseline, objective):
        rejection_reasons.append("compiled-policy-failed-heldout-safety-or-model-call-gate")
    quality_floor = max(0, fixed_max.success_count - objective.quality_slack_items)
    if compiled.success_count < quality_floor:
        rejection_reasons.append("compiled-policy-fell-below-fixed-max-quality-floor")
    if not fixed_max_reference["preserves_reference_successes"]:
        rejection_reasons.append("compiled-policy-lost-fixed-max-heldout-success")
    if _dominates(fixed_max, compiled):
        rejection_reasons.append("fixed-max-strictly-dominates-compiled-policy")

    return {
        "format": "exactscope.harness-heldout-transfer",
        "format_version": "0.1",
        "held_out_split_id": held_out.split_id,
        "held_out_split_digest": held_out.sha256(),
        "profile_digest": profile.sha256(),
        "compiled_policy_id": profile.selected_policy.policy_id,
        "baseline_policy_id": baseline_policy_id,
        "fixed_max_policy_id": fixed_max_policy_id,
        "baseline": baseline.as_dict(),
        "fixed_max": fixed_max.as_dict(),
        "compiled": compiled.as_dict(),
        "fixed_max_heldout_reference": fixed_max_reference,
        "qualification": {
            "passed": not rejection_reasons,
            "rejection_reasons": rejection_reasons,
            "fixed_max_quality_floor_success_count": quality_floor,
            "objective": objective.as_dict(),
        },
        "profile_reselected_on_held_out": False,
        "held_out_policy_count": len(required_ids),
        "hot_path_calibration_model_calls": 0,
    }
