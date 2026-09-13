#!/usr/bin/env python3
"""Consume the historical v1.1 compiled-profile format without re-running calibration.

`AmplifierProfile` remains the compatibility type for the pre-reframe prototype. The
current product design separates an immutable Candidate Execution Policy from a
Qualification Attestation. This module is still a thin execution seam: the host owns
retrieval, tokenization, constrained decoding, prefix caching, and model execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TOOLS = ROOT / "tools"
for path in (TOOLS, HERE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from grounding_engine import GroundingSession, PreparedAmplifier  # noqa: E402
from harness_distillation import AmplifierProfile, DistillationError, load_profile  # noqa: E402


class CompiledProfileError(ValueError):
    """The compiled profile cannot be honored by this execution seam."""


@dataclass(frozen=True, slots=True)
class CompiledPlan:
    plan: dict[str, Any]
    host_hints: dict[str, Any]


@dataclass(frozen=True, slots=True)
class PreparedProfileExecution:
    profile: AmplifierProfile
    prepared: PreparedAmplifier
    host_candidate_top_k: int

    def plan(
        self,
        *,
        question: str,
        qid: str,
        scope: str | None = None,
        retrieval_query: str | None = None,
        ranked_hits: list[dict[str, Any]] | None = None,
        term_weights: dict[str, float] | None = None,
        context_fit: Callable[[list[dict[str, str]]], bool] | None = None,
    ) -> CompiledPlan:
        policy = self.profile.selected_policy
        evidence_path = ranked_hits is not None
        if evidence_path and "A" in policy.evidence_bundle and retrieval_query is None:
            raise CompiledProfileError("compiled A bundle requires a retrieval query on the evidence path")
        if evidence_path and "A" not in policy.evidence_bundle and retrieval_query is not None:
            raise CompiledProfileError("retrieval query separation was not selected by this profile")
        if evidence_path and "I" in policy.evidence_bundle and context_fit is None:
            raise CompiledProfileError("compiled I bundle requires host context-fit measurement")
        if evidence_path and "I" not in policy.evidence_bundle and context_fit is not None:
            raise CompiledProfileError("host context-fit negotiation was not selected by this profile")
        plan = self.prepared.plan(
            question=question,
            qid=qid,
            scope=scope,
            retrieval_query=retrieval_query,
            ranked_hits=ranked_hits,
            term_weights=term_weights,
            context_fit=context_fit,
        )
        generation = bool(plan.get("model_called"))
        amplifier = plan.get("amplifier") if isinstance(plan.get("amplifier"), dict) else {}
        cache_eligible = generation and amplifier.get("prefix_cache_eligible") is True
        hints = {
            "host_candidate_top_k": self.host_candidate_top_k,
            "typed_contract_required": generation and policy.model_bundle in {"G", "G+H"},
            "native_constraint_surface_id": (
                self.profile.native_constraint_surface_id
                if generation and policy.model_bundle == "G+H"
                else None
            ),
            "native_constraint_qualification_digest": (
                self.profile.gxh_qualification_digest
                if generation and policy.model_bundle == "G+H"
                else None
            ),
            "prefix_cache_mode": self.profile.prefix_cache_mode if cache_eligible else "off",
            "prefix_cache_parity_digest": (
                self.profile.prefix_cache_parity_digest if cache_eligible else None
            ),
            "prefix_cache_key": amplifier.get("prefix_cache_key") if cache_eligible else None,
            "generation_eliminated": not generation,
            "calibration_model_calls": 0,
        }
        return CompiledPlan(plan, hints)

    def finalize_generation(self, text: str) -> dict[str, Any] | None:
        return self.prepared.finalize_generation(text)


def prepare_from_profile(
    *,
    session: GroundingSession,
    profile: AmplifierProfile | bytes | str,
    host_profile_digest: str,
    host_qualification_digest: str,
    contract: str,
    corpus_index: Path | None = None,
    answer_spec: dict[str, Any] | None = None,
    answer_choices: tuple[str, ...] | list[str] | None = None,
) -> PreparedProfileExecution:
    """Load policy data once and bind it to existing PreparedAmplifier machinery."""
    if isinstance(profile, AmplifierProfile):
        compiled = profile
    else:
        try:
            compiled = load_profile(profile, host_profile_digest=host_profile_digest)
        except DistillationError as exc:
            raise CompiledProfileError(str(exc)) from exc
    if compiled.host_profile_digest != host_profile_digest:
        raise CompiledProfileError("compiled profile does not match current host identity")
    if compiled.host_qualification_digest != host_qualification_digest:
        raise CompiledProfileError("compiled profile does not match current host qualification identity")
    policy = compiled.selected_policy
    if "D" not in policy.evidence_bundle:
        raise CompiledProfileError("the first compiled-profile bridge executes only D-based evidence bundles")
    if policy.model_bundle == "H":
        raise CompiledProfileError("H cannot execute without an ExactScope semantic answer contract")
    if policy.prompt_profile not in {"full", "no-policy"}:
        raise CompiledProfileError("this bridge does not implement compact-native prompt rendering")
    if "G" in policy.model_bundle and answer_spec is None and answer_choices is None:
        raise CompiledProfileError("compiled G bundle requires an application-defined answer contract")
    if "I" in policy.evidence_bundle and corpus_index is not None:
        raise CompiledProfileError("compiled I currently requires the host-ranked context-fit path")
    top_k = 12 if "B" in policy.evidence_bundle else 4
    prepared = session.prepare(
        contract=contract,
        corpus_index=corpus_index,
        corpus_top_k=top_k,
        prompt_profile=policy.prompt_profile,
        proof_first="J-proof-first" in policy.cost_bundle,
        answer_spec=answer_spec,
        answer_choices=answer_choices,
    )
    return PreparedProfileExecution(compiled, prepared, top_k)
