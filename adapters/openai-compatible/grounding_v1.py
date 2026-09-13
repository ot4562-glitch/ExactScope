#!/usr/bin/env python3
"""Experimental ExactScope adapter for OpenAI-compatible chat endpoints.

The core runtime stays unchanged. This slice only maps one prepared ExactScope plan to
one host-selected OpenAI-compatible wire profile. No backend is trusted by name: the
wire profile remains explicit until capability discovery is qualified.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import sys
from typing import Any

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TOOLS = ROOT / "tools"
for path in (TOOLS, HERE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from grounding_answer_contract import ANSWER_SPEC_KINDS, CompiledAnswerSpec, compile_answer_spec  # noqa: E402
from grounding_engine import (  # noqa: E402
    DEFAULT_CORPUS_EVIDENCE_BYTES,
    DEFAULT_CORPUS_EVIDENCE_POLICY,
    GroundingSession,
)
from grounding_projection import EVIDENCE_POLICY_IDS  # noqa: E402
from grounding_v1_surface import AUTO_CONTRACT_CANDIDATES, normalize_answer, parse_answer_object  # noqa: E402
from surface import STANDARD_JSON_SCHEMA, SURFACE_PROFILES, constraint_fields  # noqa: E402
from transport import HTTPStatusError, PreparedEndpoint, TransportError, prepare_endpoint, single_model_id, single_text_completion  # noqa: E402


class AdapterError(RuntimeError):
    pass


def _qid(question: str) -> str:
    return "q-" + hashlib.sha256(question.encode("utf-8")).hexdigest()[:16]


def _allow_endpoint(endpoint: PreparedEndpoint, allow_remote_model: bool) -> None:
    if allow_remote_model:
        return
    if endpoint.host == "localhost":
        return
    try:
        host = ipaddress.ip_address(endpoint.host)
    except ValueError as exc:
        raise AdapterError("non-loopback model endpoint requires --allow-remote-model") from exc
    if not host.is_loopback:
        raise AdapterError("non-loopback model endpoint requires --allow-remote-model")


def _authorization_from_env(name: str | None) -> str | None:
    if name is None:
        return None
    value = os.environ.get(name)
    if not value:
        raise AdapterError(f"authorization environment variable is missing: {name}")
    return value


def request_answer(
    endpoint: PreparedEndpoint,
    model: str,
    contract: str,
    request_messages: list[dict[str, str]],
    *,
    wire_profile: str = STANDARD_JSON_SCHEMA,
    answer_spec: dict[str, Any] | CompiledAnswerSpec | None = None,
    authorization: str | None = None,
    timeout_seconds: float = 60.0,
    max_tokens: int = 96,
) -> dict[str, Any]:
    """Map one ExactScope model plan to exactly one OpenAI-compatible model request."""
    if contract not in AUTO_CONTRACT_CANDIDATES:
        raise AdapterError("unsupported ExactScope answer contract")
    if wire_profile not in SURFACE_PROFILES:
        raise AdapterError("unsupported OpenAI-compatible wire profile")
    if not isinstance(model, str) or not model:
        raise AdapterError("model must be nonempty")
    compiled = compile_answer_spec(answer_spec)
    payload = {
        "model": model,
        "stream": False,
        "temperature": 0,
        "max_tokens": max_tokens,
        "messages": request_messages,
        **constraint_fields(wire_profile, compiled.json_schema),
    }
    try:
        raw = endpoint.request(payload, authorization=authorization, timeout_seconds=timeout_seconds)
        content, usage = single_text_completion(raw)
    except (HTTPStatusError, TransportError, ValueError) as exc:
        raise AdapterError(str(exc)) from exc
    valid, value = parse_answer_object(content, compiled)
    return {
        "valid": valid,
        "value": value,
        "reply": normalize_answer(valid, value),
        "raw_content": content,
        "answer_spec_sha256": compiled.sha256,
        **usage,
    }


def _answer_spec_from_args(args: argparse.Namespace) -> CompiledAnswerSpec:
    choices = args.answer_choices
    kind = args.answer_kind
    if kind is None:
        return compile_answer_spec(answer_choices=choices)
    spec: dict[str, Any] = {"kind": kind, "nullable": not args.answer_required}
    if kind == "choice":
        if not choices:
            raise AdapterError("--answer-kind choice requires repeated --answer-choice")
        spec["choices"] = choices
        if not args.answer_required:
            spec["nullable"] = False
    elif choices:
        raise AdapterError("--answer-choice requires --answer-kind choice")
    if args.answer_minimum is not None or args.answer_maximum is not None:
        if kind not in {"integer", "number"}:
            raise AdapterError("answer bounds require integer or number answer kind")
        parser = int if kind == "integer" else float
        try:
            if args.answer_minimum is not None:
                spec["minimum"] = parser(args.answer_minimum)
            if args.answer_maximum is not None:
                spec["maximum"] = parser(args.answer_maximum)
        except ValueError as exc:
            raise AdapterError("invalid numeric answer bound") from exc
    return compile_answer_spec(spec)


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "answer"))
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--qid")
    parser.add_argument("--scope")
    parser.add_argument("--retrieval-query")
    parser.add_argument("--corpus-index", type=Path)
    parser.add_argument("--corpus-top-k", type=int, default=12)
    parser.add_argument("--corpus-evidence-bytes", type=int, default=DEFAULT_CORPUS_EVIDENCE_BYTES)
    parser.add_argument("--corpus-evidence-policy", choices=EVIDENCE_POLICY_IDS, default=DEFAULT_CORPUS_EVIDENCE_POLICY)
    parser.add_argument("--contract", choices=AUTO_CONTRACT_CANDIDATES, default="answer-object-v3")
    parser.add_argument("--answer-choice", dest="answer_choices", action="append")
    parser.add_argument("--answer-kind", choices=ANSWER_SPEC_KINDS)
    parser.add_argument("--answer-required", action="store_true")
    parser.add_argument("--answer-minimum")
    parser.add_argument("--answer-maximum")
    parser.add_argument("--wire-profile", choices=SURFACE_PROFILES, default=STANDARD_JSON_SCHEMA)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--model")
    parser.add_argument("--allow-remote-model", action="store_true")
    parser.add_argument("--authorization-env")
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    args = parser.parse_args(argv)

    try:
        answer_spec = _answer_spec_from_args(args)
        session = GroundingSession.open(args.profile)
        amplifier = session.prepare(
            contract=args.contract,
            corpus_index=args.corpus_index,
            corpus_top_k=args.corpus_top_k,
            corpus_evidence_bytes=args.corpus_evidence_bytes,
            corpus_evidence_policy=args.corpus_evidence_policy,
            answer_spec=answer_spec,
        )
        plan = amplifier.plan(
            question=args.question,
            qid=args.qid or _qid(args.question),
            scope=args.scope,
            retrieval_query=args.retrieval_query,
        )
        if args.command == "plan" or not plan["model_called"]:
            _print({
                "route": plan["route"],
                "model_called": plan["model_called"],
                "reply": plan["reply"],
                "profile_sha256": plan["profile_sha256"],
                "wire_profile": args.wire_profile,
            })
            return 0
        endpoint = prepare_endpoint(args.base_url)
        _allow_endpoint(endpoint, args.allow_remote_model)
        authorization = _authorization_from_env(args.authorization_env)
        model = args.model
        if model is None:
            model = single_model_id(endpoint.models(
                authorization=authorization,
                timeout_seconds=min(args.timeout_seconds, 5.0),
            ))
        result = request_answer(
            endpoint,
            model,
            args.contract,
            plan["messages"],
            wire_profile=args.wire_profile,
            answer_spec=answer_spec,
            authorization=authorization,
            timeout_seconds=args.timeout_seconds,
        )
        if not result["valid"] or result["reply"] is None:
            raise AdapterError("model returned an invalid ExactScope answer object; no retry or repair performed")
        _print({
            "route": plan["route"],
            "model_called": True,
            "reply": result["reply"],
            "profile_sha256": plan["profile_sha256"],
            "wire_profile": args.wire_profile,
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
        })
        return 0
    except (AdapterError, TransportError, ValueError, OSError) as exc:
        print(f"ExactScope openai-compatible: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
