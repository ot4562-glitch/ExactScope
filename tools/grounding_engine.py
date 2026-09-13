#!/usr/bin/env python3
"""ExactScope v1.1 runtime amplifier.

Architecture: cold path validates immutable artifacts, compiles contracts and binds stable policy.
Hot path: accept a question, retrieve/project bounded evidence, then return a zero/
one-model-call plan.

The request path deliberately trusts objects created by :class:`GroundingSession`.
Artifact-shaped checks therefore happen when state enters the session, not again for
every question.  Request-dependent bounds remain enforced because their values are
not known until execution.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from grounding_answer_contract import CompiledAnswerSpec, answer_spec_cache_key, compile_answer_spec
from grounding_projection import (
    ADAPTIVE_EVIDENCE_POLICY_ID,
    EVIDENCE_POLICY_IDS,
    PRECISION_CONTEXT_PROJECTION_ID,
    precision_context_evidence_projection_v5,
    precision_ranked_evidence_fit_v1,
    precision_ranked_evidence_tiers_v1,
)
from grounding_runtime import (
    LocalExactLexicalProvider,
    grouped_model_projection_v2,
    host_grounded_scalar_reply,
    host_short_circuit_reply,
    load_bundle,
    run_grounding_frame,
    supplemental_empty_frame,
)
from grounding_v1_surface import (
    AUTO_CONTRACT_CANDIDATES,
    normalize_answer,
    parse_answer_object,
    surface_sha256,
    system_prompt,
)

DEFAULT_CORPUS_EVIDENCE_BYTES = 2048
DEFAULT_CORPUS_PROJECTION_ID = PRECISION_CONTEXT_PROJECTION_ID
DEFAULT_CORPUS_EVIDENCE_POLICY = ADAPTIVE_EVIDENCE_POLICY_ID
MAX_SESSION_ANSWER_SPECS = 64
SUPPORTED_CORPUS_PROJECTIONS = (PRECISION_CONTEXT_PROJECTION_ID,)


class EngineError(RuntimeError):
    """Invalid input at the runtime-amplifier boundary."""


def finalize_generation(
    text: str,
    answer_spec: dict[str, Any] | CompiledAnswerSpec | None = None,
) -> dict[str, Any] | None:
    """Strictly validate one generated answer object; never repair invalid output."""
    if not isinstance(text, str):
        return None
    valid, value = parse_answer_object(text, answer_spec)
    return normalize_answer(valid, value)


def load_corpus_index(path: Path, *, compiled: bool = False) -> Any:
    """Compatibility-preserving lazy boundary for optional local corpus support."""
    from grounding_corpus import load_index

    return load_index(path, compiled=compiled)


def corpus_index_sha256(index: Any) -> str:
    from grounding_corpus import index_sha256

    return index_sha256(index)


def search_corpus(index: Any, query: str, *, top_k: int) -> list[dict[str, Any]]:
    from grounding_corpus import search

    return search(index, query, top_k=top_k)


def _is_validated_corpus_index(index: Any) -> bool:
    from grounding_corpus import ValidatedIndex

    return isinstance(index, ValidatedIndex)


@dataclass(frozen=True, slots=True)
class CorpusSnapshot:
    """Canonical corpus validated once and frozen for request execution."""

    path: Path
    index: Any
    sha256: str


@dataclass(frozen=True, slots=True)
class PreparedAmplifier:
    """All stable request configuration compiled before the hot path."""

    session: "GroundingSession"
    contract: str
    answer_spec: CompiledAnswerSpec
    corpus: CorpusSnapshot | None
    corpus_top_k: int
    corpus_evidence_bytes: int
    corpus_projection: str
    corpus_evidence_policy: str
    prompt_profile: str
    proof_first: bool
    system_plain: str
    system_with_policy: str
    prefix_key_plain: str
    prefix_key_with_policy: str

    def finalize_generation(self, text: str) -> dict[str, Any] | None:
        """Validate generation against this prepared answer contract without repair."""
        return finalize_generation(text, self.answer_spec)

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
    ) -> dict[str, Any]:
        """Execute the prepared guard-light path for one question."""
        return _plan_prepared(
            self,
            question=question,
            qid=qid,
            scope=scope,
            retrieval_query=retrieval_query,
            ranked_hits=ranked_hits,
            term_weights=term_weights,
            context_fit=context_fit,
        )


class GroundingSession:
    """Trust boundary for immutable ExactScope runtime state.

    ``open`` validates the profile once. ``bind_corpus`` validates each corpus once.
    ``prepare`` compiles the stable model contract, prompt prefix and evidence policy.
    A prepared amplifier therefore never stats or re-opens those artifacts while it
    answers questions.  Opening a new session is the explicit way to adopt changes.
    """

    __slots__ = (
        "profile_dir",
        "_bundle",
        "_provider",
        "limits",
        "scope",
        "profile_sha256",
        "policy",
        "policy_sha256",
        "_corpus_cache",
        "_answer_spec_cache",
    )

    def __init__(self, profile_dir: Path, bundle: Any) -> None:
        self.profile_dir = profile_dir
        self._bundle = bundle
        self._provider = LocalExactLexicalProvider(bundle)
        self.limits = bundle.limits
        self.scope = bundle.scope
        self.profile_sha256 = bundle.profile_sha256
        self.policy = bundle.policy
        self.policy_sha256 = hashlib.sha256(bundle.policy).hexdigest()
        self._corpus_cache: dict[Path, CorpusSnapshot] = {}
        self._answer_spec_cache: dict[bytes, CompiledAnswerSpec] = {}

    @classmethod
    def open(cls, profile_dir: Path) -> "GroundingSession":
        root = profile_dir.resolve()
        return cls(root, load_bundle(root))

    def bind_corpus(self, path: Path) -> CorpusSnapshot:
        """Validate a corpus once and bind its immutable in-memory representation."""
        resolved = path.resolve()
        cached = self._corpus_cache.get(resolved)
        if cached is not None:
            return cached
        loaded = load_corpus_index(resolved, compiled=True)
        if not _is_validated_corpus_index(loaded):
            raise EngineError("compiled corpus loader did not return immutable state")
        snapshot = CorpusSnapshot(resolved, loaded, corpus_index_sha256(loaded))
        self._corpus_cache[resolved] = snapshot
        return snapshot

    corpus = bind_corpus

    def compile_answer_spec(
        self,
        answer_spec: dict[str, Any] | CompiledAnswerSpec | None = None,
        *,
        answer_choices: tuple[str, ...] | list[str] | None = None,
    ) -> CompiledAnswerSpec:
        """Compile one canonical answer contract once per long-lived session."""
        if isinstance(answer_spec, CompiledAnswerSpec):
            if answer_choices is not None:
                raise EngineError("compiled answer_spec and answer_choices are mutually exclusive")
            return answer_spec
        key = answer_spec_cache_key(answer_spec, answer_choices=answer_choices)
        cached = self._answer_spec_cache.get(key)
        if cached is not None:
            return cached
        compiled = compile_answer_spec(answer_spec, answer_choices=answer_choices)
        if len(self._answer_spec_cache) >= MAX_SESSION_ANSWER_SPECS:
            self._answer_spec_cache.pop(next(iter(self._answer_spec_cache)))
        self._answer_spec_cache[key] = compiled
        return compiled

    def prepare(
        self,
        *,
        contract: str,
        corpus_index: Path | CorpusSnapshot | None = None,
        corpus_top_k: int = 12,
        corpus_evidence_bytes: int = DEFAULT_CORPUS_EVIDENCE_BYTES,
        corpus_projection: str = DEFAULT_CORPUS_PROJECTION_ID,
        corpus_evidence_policy: str = DEFAULT_CORPUS_EVIDENCE_POLICY,
        prompt_profile: str = "full",
        proof_first: bool = True,
        answer_spec: dict[str, Any] | CompiledAnswerSpec | None = None,
        answer_choices: tuple[str, ...] | list[str] | None = None,
    ) -> PreparedAmplifier:
        """Compile all stable execution choices once before request traffic begins."""
        if contract not in AUTO_CONTRACT_CANDIDATES:
            raise EngineError("unsupported grounding model contract")
        compiled = self.compile_answer_spec(answer_spec, answer_choices=answer_choices)
        if (
            type(corpus_evidence_bytes) is not int
            or not 256 <= corpus_evidence_bytes <= self.limits.model_evidence_bytes
        ):
            raise EngineError("evidence byte tier exceeds grounding profile limits")
        if corpus_projection not in SUPPORTED_CORPUS_PROJECTIONS:
            raise EngineError("unsupported corpus projection")
        if corpus_evidence_policy not in EVIDENCE_POLICY_IDS:
            raise EngineError("unsupported corpus evidence policy")
        if prompt_profile not in {"full", "no-policy"}:
            raise EngineError("unsupported prepared prompt profile")
        if type(proof_first) is not bool:
            raise EngineError("proof_first must be boolean")
        snapshot: CorpusSnapshot | None = None
        if corpus_index is not None:
            if type(corpus_top_k) is not int or not 1 <= corpus_top_k <= 16:
                raise EngineError("corpus top_k must be between 1 and 16")
            snapshot = corpus_index if isinstance(corpus_index, CorpusSnapshot) else self.bind_corpus(corpus_index)

        base_system = system_prompt(contract, answer_spec=compiled)
        policy_text = self.policy.decode("utf-8")
        return PreparedAmplifier(
            session=self,
            contract=contract,
            answer_spec=compiled,
            corpus=snapshot,
            corpus_top_k=corpus_top_k,
            corpus_evidence_bytes=corpus_evidence_bytes,
            corpus_projection=corpus_projection,
            corpus_evidence_policy=corpus_evidence_policy,
            prompt_profile=prompt_profile,
            proof_first=proof_first,
            system_plain=base_system,
            system_with_policy=base_system + "\n\n" + policy_text,
            prefix_key_plain=_prefix_cache_key_from_digest(
                contract,
                None,
                compiled.sha256,
                policy_in_prompt=False,
            ),
            prefix_key_with_policy=_prefix_cache_key_from_digest(
                contract,
                self.policy_sha256,
                compiled.sha256,
                policy_in_prompt=True,
            ),
        )

    def plan(
        self,
        *,
        question: str,
        qid: str,
        contract: str,
        scope: str | None = None,
        retrieval_query: str | None = None,
        ranked_hits: list[dict[str, Any]] | None = None,
        term_weights: dict[str, float] | None = None,
        context_fit: Callable[[list[dict[str, str]]], bool] | None = None,
        corpus_index: Path | CorpusSnapshot | None = None,
        corpus_top_k: int = 12,
        corpus_evidence_bytes: int = DEFAULT_CORPUS_EVIDENCE_BYTES,
        corpus_projection: str = DEFAULT_CORPUS_PROJECTION_ID,
        corpus_evidence_policy: str = DEFAULT_CORPUS_EVIDENCE_POLICY,
        answer_spec: dict[str, Any] | CompiledAnswerSpec | None = None,
        answer_choices: tuple[str, ...] | list[str] | None = None,
    ) -> dict[str, Any]:
        """Compatibility wrapper; repeated callers should prepare once and reuse it."""
        prepared = self.prepare(
            contract=contract,
            corpus_index=corpus_index,
            corpus_top_k=corpus_top_k,
            corpus_evidence_bytes=corpus_evidence_bytes,
            corpus_projection=corpus_projection,
            corpus_evidence_policy=corpus_evidence_policy,
            answer_spec=answer_spec,
            answer_choices=answer_choices,
        )
        return prepared.plan(
            question=question,
            qid=qid,
            scope=scope,
            retrieval_query=retrieval_query,
            ranked_hits=ranked_hits,
            term_weights=term_weights,
            context_fit=context_fit,
        )


def _prepared_messages(
    prepared: PreparedAmplifier,
    question: str,
    evidence: bytes | None,
    *,
    policy: bool,
) -> list[dict[str, str]]:
    system = prepared.system_with_policy if policy and prepared.prompt_profile == "full" else prepared.system_plain
    user = question if evidence is None else question + "\n\n" + evidence.decode("utf-8")
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _plan_prepared(
    prepared: PreparedAmplifier,
    *,
    question: str,
    qid: str,
    scope: str | None,
    retrieval_query: str | None,
    ranked_hits: list[dict[str, Any]] | None,
    term_weights: dict[str, float] | None,
    context_fit: Callable[[list[dict[str, str]]], bool] | None,
) -> dict[str, Any]:
    """Guard-light hot path over already validated immutable state."""
    session = prepared.session
    model_instruction = _bounded_text(question, "question/model instruction", session.limits.query_bytes)
    effective_retrieval_query = _bounded_text(
        retrieval_query if retrieval_query is not None else question,
        "retrieval-query",
        session.limits.query_bytes,
    )
    instruction_equivalent = retrieval_query is None or effective_retrieval_query == model_instruction
    effective_scope = scope if scope is not None else session.scope
    if not isinstance(effective_scope, str) or not effective_scope:
        raise EngineError("effective grounding scope is missing")
    if ranked_hits is not None and not isinstance(ranked_hits, list):
        raise EngineError("ranked_hits must be a list when provided")
    if ranked_hits is not None and prepared.corpus is not None:
        raise EngineError("host-ranked hits and local corpus are mutually exclusive")
    if ranked_hits is None and (term_weights is not None or context_fit is not None):
        raise EngineError("term_weights/context_fit require host-ranked hits")
    if context_fit is not None and not callable(context_fit):
        raise EngineError("context_fit must be callable")

    grounding = run_grounding_frame(
        session._bundle,
        {
            "v": 1,
            "qid": qid,
            "q": effective_retrieval_query,
            "profile_sha256": session._bundle.profile_sha256,
            "security_scope_id": effective_scope,
        },
        session._provider,
    )
    frame = grounding["frame"]
    amplifier = {
        "id": "runtime-amplifier-v1.1",
        "answer_kind": prepared.answer_spec.kind,
        "answer_spec_sha256": prepared.answer_spec.sha256,
        "prompt_profile": prepared.prompt_profile,
        "prefix_cache_eligible": False,
        "prefix_cache_key": None,
        "retry_count": 0,
        "second_model_calls": 0,
        "session_state": "prepared-immutable-amplifier-v1",
    }

    reply = host_short_circuit_reply(frame)
    if reply is not None:
        return _plan_result(
            route="host-unresolved-state",
            model_called=False,
            reply=reply,
            messages_value=None,
            frame=frame,
            grounding=grounding,
            bundle=session._bundle,
            amplifier=amplifier,
        )

    reply = (
        _host_typed_scalar_reply(frame, prepared.answer_spec)
        if prepared.proof_first and instruction_equivalent
        else None
    )
    if reply is not None:
        return _plan_result(
            route="host-grounded-scalar",
            model_called=False,
            reply=reply,
            messages_value=None,
            frame=frame,
            grounding=grounding,
            bundle=session._bundle,
            amplifier=amplifier,
        )

    groups = frame.get("groups")
    ordinary = not groups or supplemental_empty_frame(frame)
    corpus_meta = None
    policy_in_prompt = prepared.prompt_profile == "full"

    if ordinary and ranked_hits is not None:
        max_evidence = prepared.corpus_evidence_bytes
        ranked_tiers = (max_evidence, *(tier for tier in (1024, 512) if tier < max_evidence))
        try:
            if context_fit is not None:
                def fits_payload(payload: bytes, _hits: list[dict[str, Any]], _meta: dict[str, Any]) -> bool:
                    accepted = context_fit(_prepared_messages(prepared, model_instruction, payload, policy=True))
                    if type(accepted) is not bool:
                        raise EngineError("context_fit must return bool")
                    return accepted

                evidence, hits, projection_meta = precision_ranked_evidence_fit_v1(
                    ranked_hits,
                    effective_retrieval_query,
                    fits_payload,
                    tiers=ranked_tiers,
                    max_items=session.limits.model_items,
                    term_weights=term_weights,
                )
            else:
                evidence, hits, projection_meta = precision_ranked_evidence_tiers_v1(
                    ranked_hits,
                    effective_retrieval_query,
                    tiers=(max_evidence,),
                    max_items=session.limits.model_items,
                    term_weights=term_weights,
                )[0]
        except EngineError:
            raise
        except Exception as exc:
            raise EngineError(f"host-ranked evidence projection failed: {exc}") from exc
        if not hits or evidence is None:
            reason = "cannot fit the model context" if context_fit is not None else "produced no complete projection"
            raise EngineError(f"host-ranked evidence {reason}")
        _enforce_model_payload_limits(session, evidence, len(hits))
        request_messages = _prepared_messages(prepared, model_instruction, evidence, policy=True)
        route = "host-ranked-context"
        corpus_meta = {
            "source": "host-ranked",
            **projection_meta,
            "evidence_budget_bytes": projection_meta["max_evidence_bytes"],
            "hits": [
                {
                    "id": hit["id"],
                    "title": hit["title"],
                    "text_sha256": hit.get("text_sha256"),
                    "sentence_positions": hit.get("sentence_positions"),
                }
                for hit in hits
            ],
        }
    elif ordinary and prepared.corpus is not None:
        snapshot = prepared.corpus
        retrieved = search_corpus(snapshot.index, effective_retrieval_query, top_k=prepared.corpus_top_k)
        evidence, hits, projection_meta = precision_context_evidence_projection_v5(
            snapshot.index,
            retrieved,
            effective_retrieval_query,
            max_bytes=prepared.corpus_evidence_bytes,
            evidence_policy=prepared.corpus_evidence_policy,
            max_items=session.limits.model_items,
        )
        if hits and evidence is not None:
            _enforce_model_payload_limits(session, evidence, len(hits))
            request_messages = _prepared_messages(prepared, model_instruction, evidence, policy=True)
            route = "local-corpus"
            corpus_meta = {
                "index_sha256": snapshot.sha256,
                **projection_meta,
                "evidence_budget_bytes": projection_meta["selected_evidence_bytes"],
                "hits": [
                    {
                        "id": hit["id"],
                        "title": hit["title"],
                        "text_sha256": hit["text_sha256"],
                        "sentence_positions": hit.get("sentence_positions"),
                    }
                    for hit in hits
                ],
            }
        else:
            request_messages = _prepared_messages(prepared, model_instruction, None, policy=False)
            route = "ordinary-knowledge"
            policy_in_prompt = False
    elif ordinary:
        request_messages = _prepared_messages(prepared, model_instruction, None, policy=False)
        route = "ordinary-knowledge"
        policy_in_prompt = False
    else:
        evidence = grouped_model_projection_v2(frame, include_single_target=not instruction_equivalent)
        _enforce_model_payload_limits(session, evidence, _frame_item_count(frame))
        request_messages = _prepared_messages(prepared, model_instruction, evidence, policy=True)
        route = "grounded-context"

    amplifier["prefix_cache_eligible"] = True
    amplifier["prefix_cache_key"] = (
        prepared.prefix_key_with_policy if policy_in_prompt else prepared.prefix_key_plain
    )
    return _plan_result(
        route=route,
        model_called=True,
        reply=None,
        messages_value=request_messages,
        frame=frame,
        grounding=grounding,
        bundle=session._bundle,
        amplifier=amplifier,
        corpus=corpus_meta,
    )


def _bounded_text(value: Any, label: str, max_bytes: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EngineError(f"{label} must be nonempty text")
    stripped = value.strip()
    if len(stripped.encode("utf-8")) > max_bytes:
        raise EngineError(f"{label} exceeds grounding profile query byte budget")
    return stripped


def _host_typed_scalar_reply(frame: dict[str, Any], answer_spec: CompiledAnswerSpec) -> dict[str, Any] | None:
    base = host_grounded_scalar_reply(frame)
    if base is None or base.get("disposition") != "answer":
        return None
    if answer_spec.kind in {"text", "choice"}:
        value: Any = base.get("a")
    else:
        groups = frame.get("groups")
        items = groups[0].get("items") if isinstance(groups, list) and len(groups) == 1 and isinstance(groups[0], dict) else None
        content = items[0].get("content") if isinstance(items, list) and len(items) == 1 and isinstance(items[0], dict) else None
        if not isinstance(content, dict) or content.get("kind") != "scalar" or content.get("unit") is not None:
            return None
        raw = content.get("value")
        scalar_type = content.get("type")
        try:
            if answer_spec.kind == "boolean" and scalar_type == "boolean" and raw in {"true", "false"}:
                value = raw == "true"
            elif answer_spec.kind == "integer" and scalar_type == "integer" and isinstance(raw, str):
                value = int(raw)
            elif answer_spec.kind == "number" and scalar_type in {"integer", "decimal"} and isinstance(raw, str):
                value = int(raw) if scalar_type == "integer" else float(raw)
            else:
                return None
        except ValueError:
            return None
    if not answer_spec.validate(value):
        return None
    return {"a": value, "disposition": "answer"}


def _frame_item_count(frame: dict[str, Any]) -> int:
    groups = frame.get("groups")
    if not isinstance(groups, list):
        raise EngineError("frame groups are missing")
    return sum(
        len(group["items"])
        for group in groups
        if isinstance(group, dict) and isinstance(group.get("items"), list)
    )


def _enforce_model_payload_limits(session: GroundingSession, evidence: bytes, item_count: int) -> None:
    # These are request-dependent bounds. Artifact-shaped validation was already done
    # at open/bind/prepare and is intentionally absent from the hot loop.
    if item_count > session.limits.model_items:
        raise EngineError("model item budget exceeded")
    if len(evidence) > session.limits.model_evidence_bytes:
        raise EngineError("model evidence budget exceeded")
    if len(session._bundle.policy) + len(evidence) > session.limits.model_context_bytes:
        raise EngineError("model context budget exceeded")


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _prefix_cache_key_from_digest(
    contract: str,
    policy_sha256: str | None,
    answer_spec_sha256: str,
    *,
    policy_in_prompt: bool,
) -> str:
    payload = {
        "format": "exactscope.runtime-amplifier-prefix",
        "format_version": "0.2",
        "contract": contract,
        "model_surface_sha256": surface_sha256(),
        "policy_sha256": policy_sha256,
        "policy_in_prompt": policy_in_prompt,
        "answer_spec_sha256": answer_spec_sha256,
    }
    return hashlib.sha256(_json_bytes(payload)).hexdigest()


def prefix_cache_key(
    contract: str,
    policy: bytes,
    answer_spec: dict[str, Any] | CompiledAnswerSpec | None = None,
    *,
    policy_in_prompt: bool = True,
) -> str:
    """Stable reusable-prefix identity; the backend cache itself stays host-owned."""
    compiled = compile_answer_spec(answer_spec)
    return _prefix_cache_key_from_digest(
        contract,
        hashlib.sha256(policy).hexdigest() if policy_in_prompt else None,
        compiled.sha256,
        policy_in_prompt=policy_in_prompt,
    )


def _plan_result(
    *,
    route: str,
    model_called: bool,
    reply: dict[str, Any] | None,
    messages_value: list[dict[str, str]] | None,
    frame: dict[str, Any],
    grounding: dict[str, Any],
    bundle: Any,
    amplifier: dict[str, Any],
    corpus: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = {
        "route": route,
        "model_called": model_called,
        "reply": reply,
        "messages": messages_value,
        "frame": frame,
        "audit": grounding["audit"],
        "profile_sha256": bundle.profile_sha256,
        "amplifier": amplifier,
    }
    if model_called:
        result["corpus"] = corpus
    return result


def plan_question(
    *,
    profile_dir: Path,
    question: str,
    qid: str,
    scope: str | None,
    contract: str,
    retrieval_query: str | None = None,
    corpus_index: Path | CorpusSnapshot | None = None,
    corpus_top_k: int = 12,
    corpus_evidence_bytes: int = DEFAULT_CORPUS_EVIDENCE_BYTES,
    corpus_projection: str = DEFAULT_CORPUS_PROJECTION_ID,
    corpus_evidence_policy: str = DEFAULT_CORPUS_EVIDENCE_POLICY,
    answer_choices: tuple[str, ...] | list[str] | None = None,
    answer_spec: dict[str, Any] | CompiledAnswerSpec | None = None,
    session: GroundingSession | None = None,
) -> dict[str, Any]:
    """Compatibility entrypoint; long-lived hosts should prepare once instead."""
    resolved = profile_dir.resolve()
    active = session if session is not None else GroundingSession.open(resolved)
    if active.profile_dir != resolved:
        raise EngineError("grounding session profile does not match profile_dir")
    return active.plan(
        question=question,
        qid=qid,
        scope=scope,
        contract=contract,
        retrieval_query=retrieval_query,
        corpus_index=corpus_index,
        corpus_top_k=corpus_top_k,
        corpus_evidence_bytes=corpus_evidence_bytes,
        corpus_projection=corpus_projection,
        corpus_evidence_policy=corpus_evidence_policy,
        answer_spec=answer_spec,
        answer_choices=answer_choices,
    )
