#!/usr/bin/env python3
"""Small local-only llama.cpp adapter for the selected ExactScope v1 grounding path."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from grounding_corpus import (  # noqa: E402
    index_sha256 as corpus_index_sha256,
    load_index as load_corpus_index,
    search as search_corpus,
)
from grounding_projection import compact_evidence_projection as corpus_compact_projection  # noqa: E402
from grounding_runtime import (  # noqa: E402
    LocalExactLexicalProvider,
    compact_model_projection,
    host_grounded_scalar_reply,
    host_short_circuit_reply,
    load_bundle,
    run_grounding_frame,
    supplemental_empty_frame,
)
from grounding_v1_surface import (  # noqa: E402
    ANSWER_OBJECT_SCHEMA,
    AUTO_CONTRACT_CALIBRATION,
    AUTO_CONTRACT_CANDIDATES,
    AUTO_V2_TIE_PREFERENCE,
    calibration_messages,
    messages,
    normalize_answer,
    parse_answer_object,
    select_contract,
    surface_sha256,
)


class AdapterError(RuntimeError):
    """Fail-closed local adapter error."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _model_limit(bundle: Any, key: str) -> int:
    limits = bundle.profile.get("limits") if isinstance(bundle.profile, dict) else None
    value = limits.get(key) if isinstance(limits, dict) else None
    if type(value) is not int or value < 0:
        raise AdapterError(f"invalid grounding profile limit: {key}")
    return value


def _frame_item_count(frame: dict[str, Any]) -> int:
    groups = frame.get("groups")
    if not isinstance(groups, list):
        raise AdapterError("frame groups are missing")
    count = 0
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("items"), list):
            raise AdapterError("malformed frame items")
        count += len(group["items"])
    return count


def _enforce_model_payload_limits(bundle: Any, *, evidence: bytes, item_count: int) -> None:
    if type(item_count) is not int or item_count < 0:
        raise AdapterError("invalid model item count")
    if item_count > _model_limit(bundle, "model_items"):
        raise AdapterError("model item budget exceeded")
    if len(evidence) > _model_limit(bundle, "model_evidence_bytes"):
        raise AdapterError("model evidence budget exceeded")
    if len(bundle.policy) + len(evidence) > _model_limit(bundle, "model_context_bytes"):
        raise AdapterError("model context budget exceeded")


def validate_local_base_url(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url.rstrip("/"))
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise AdapterError("grounding_v1 accepts only a loopback http llama.cpp endpoint")
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise AdapterError("invalid llama.cpp base URL")
    return base_url.rstrip("/")


def request_answer(
    base_url: str,
    model: str,
    contract: str,
    request_messages: list[dict[str, str]],
    *,
    timeout_seconds: float = 60.0,
    max_tokens: int = 96,
    seed: int = 20260906,
) -> dict[str, Any]:
    """Make exactly one local llama.cpp request. No retry or semantic repair."""
    base_url = validate_local_base_url(base_url)
    if contract not in AUTO_CONTRACT_CANDIDATES:
        raise AdapterError("unsupported selected grounding contract")
    if not model:
        raise AdapterError("model alias must be nonempty")
    payload = {
        "model": model,
        "stream": False,
        "temperature": 0,
        "seed": seed,
        "max_tokens": max_tokens,
        "messages": request_messages,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "exactscope_grounding_answer", "schema": ANSWER_OBJECT_SCHEMA},
        },
    }
    request = urllib.request.Request(
        base_url + "/chat/completions",
        data=_json_bytes(payload),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw_bytes = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AdapterError(f"llama.cpp HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise AdapterError(f"llama.cpp request failed: {exc}") from exc

    try:
        raw = json.loads(raw_bytes)
    except json.JSONDecodeError as exc:
        raise AdapterError("llama.cpp returned invalid JSON") from exc
    choices = raw.get("choices") if isinstance(raw, dict) else None
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise AdapterError("llama.cpp response lacks exactly one choice")
    message = choices[0].get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise AdapterError("llama.cpp response lacks textual content")
    content = message["content"]
    valid, value = parse_answer_object(content)
    usage = raw.get("usage") if isinstance(raw.get("usage"), dict) else {}
    return {
        "valid": valid,
        "value": value,
        "reply": normalize_answer(valid, value),
        "raw_content": content,
        "prompt_tokens": usage.get("prompt_tokens") if type(usage.get("prompt_tokens")) is int else None,
        "completion_tokens": usage.get("completion_tokens") if type(usage.get("completion_tokens")) is int else None,
    }


def calibrate_contract(
    *,
    base_url: str,
    model: str,
    model_key: str,
    policy: bytes,
    timeout_seconds: float = 60.0,
) -> dict[str, Any]:
    """Select the compact answer contract once for one immutable model identity."""
    if not model_key.strip():
        raise AdapterError("model-key must be a stable nonempty model identity")
    profiles = []
    scores: dict[str, int] = {}
    for contract in AUTO_CONTRACT_CANDIDATES:
        cases = []
        for case_id, question, evidence, expected in AUTO_CONTRACT_CALIBRATION:
            result = request_answer(
                base_url,
                model,
                contract,
                calibration_messages(contract, question, evidence, policy),
                timeout_seconds=timeout_seconds,
            )
            correct = result["valid"] and result["value"] == expected
            cases.append({
                "case_id": case_id,
                "expected": expected,
                "actual": result["value"] if result["valid"] else None,
                "valid": result["valid"],
                "correct": correct,
            })
        score = sum(case["correct"] for case in cases)
        scores[contract] = score
        profiles.append({"contract": contract, "score": score, "case_count": len(cases), "cases": cases})
    selected = select_contract(scores)
    return {
        "format": "exactscope.grounding-v1-contract-record",
        "format_version": "0.1",
        "model_key": model_key,
        "model_surface_sha256": surface_sha256(),
        "policy_sha256": _sha256(policy),
        "selected_contract": selected,
        "tie_preference": list(AUTO_V2_TIE_PREFERENCE),
        "model_request_count": len(AUTO_CONTRACT_CANDIDATES) * len(AUTO_CONTRACT_CALIBRATION),
        "profiles": profiles,
    }


def load_contract_record(path: Path, *, model_key: str, policy: bytes) -> dict[str, Any]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdapterError("cannot read grounding contract record") from exc
    if not isinstance(record, dict):
        raise AdapterError("grounding contract record must be an object")
    required = {
        "format": "exactscope.grounding-v1-contract-record",
        "format_version": "0.1",
        "model_key": model_key,
        "model_surface_sha256": surface_sha256(),
        "policy_sha256": _sha256(policy),
    }
    for key, expected in required.items():
        if record.get(key) != expected:
            raise AdapterError(f"grounding contract record mismatch: {key}")
    if record.get("selected_contract") not in AUTO_CONTRACT_CANDIDATES:
        raise AdapterError("grounding contract record has unsupported selected contract")
    if record.get("tie_preference") != list(AUTO_V2_TIE_PREFERENCE):
        raise AdapterError("grounding contract record tie preference drift")
    if record.get("model_request_count") != len(AUTO_CONTRACT_CANDIDATES) * len(AUTO_CONTRACT_CALIBRATION):
        raise AdapterError("grounding contract record calibration count drift")
    return record


def plan_question(
    *,
    profile_dir: Path,
    question: str,
    qid: str,
    scope: str | None,
    contract: str,
    corpus_index: Path | None = None,
    corpus_top_k: int = 12,
) -> dict[str, Any]:
    """Create the selected v1 host/model decision without performing inference."""
    bundle = load_bundle(profile_dir)
    provider = LocalExactLexicalProvider(bundle)
    effective_scope = scope if scope is not None else bundle.adapter_config.get("scope")
    if not isinstance(effective_scope, str) or not effective_scope:
        raise AdapterError("effective grounding scope is missing")
    envelope = {
        "v": 1,
        "qid": qid,
        "q": question,
        "profile_sha256": bundle.profile_sha256,
        "security_scope_id": effective_scope,
    }
    grounding = run_grounding_frame(bundle, envelope, provider)
    frame = grounding["frame"]

    reply = host_short_circuit_reply(frame)
    if reply is not None:
        return {
            "route": "host-unresolved-state",
            "model_called": False,
            "reply": reply,
            "messages": None,
            "frame": frame,
            "audit": grounding["audit"],
            "profile_sha256": bundle.profile_sha256,
        }
    reply = host_grounded_scalar_reply(frame)
    if reply is not None:
        return {
            "route": "host-grounded-scalar",
            "model_called": False,
            "reply": reply,
            "messages": None,
            "frame": frame,
            "audit": grounding["audit"],
            "profile_sha256": bundle.profile_sha256,
        }

    groups = frame.get("groups")
    ordinary = not groups or supplemental_empty_frame(frame)
    corpus_meta = None
    if ordinary and corpus_index is not None:
        index = load_corpus_index(corpus_index)
        model_items = _model_limit(bundle, "model_items")
        retrieved = search_corpus(index, question, top_k=min(corpus_top_k, model_items))
        max_evidence_bytes = _model_limit(bundle, "model_evidence_bytes")
        evidence, hits = corpus_compact_projection(
            index,
            retrieved,
            question,
            max_bytes=max_evidence_bytes,
        )
        if hits and evidence is not None:
            _enforce_model_payload_limits(bundle, evidence=evidence, item_count=len(hits))
            request_messages = messages(contract, question, evidence=evidence, policy=bundle.policy)
            route = "local-corpus"
            corpus_meta = {
                "index_sha256": corpus_index_sha256(index),
                "retrieved_count": len(retrieved),
                "hit_count": len(hits),
                "evidence_bytes": len(evidence),
                "hits": [
                    {"id": hit["id"], "title": hit["title"], "text_sha256": hit["text_sha256"]}
                    for hit in hits
                ],
            }
        else:
            request_messages = messages(contract, question)
            route = "ordinary-knowledge"
    elif ordinary:
        request_messages = messages(contract, question)
        route = "ordinary-knowledge"
    else:
        evidence = compact_model_projection(frame)
        _enforce_model_payload_limits(bundle, evidence=evidence, item_count=_frame_item_count(frame))
        request_messages = messages(contract, question, evidence=evidence, policy=bundle.policy)
        route = "grounded-context"
    return {
        "route": route,
        "model_called": True,
        "reply": None,
        "messages": request_messages,
        "frame": frame,
        "audit": grounding["audit"],
        "profile_sha256": bundle.profile_sha256,
        "corpus": corpus_meta,
    }


def _qid(question: str) -> str:
    return "q-" + hashlib.sha256(question.encode("utf-8")).hexdigest()[:16]


def _resolve_contract(args: argparse.Namespace, policy: bytes) -> str:
    if args.contract is not None:
        if args.contract not in AUTO_CONTRACT_CANDIDATES:
            raise AdapterError("unsupported --contract")
        return args.contract
    if args.contract_record is None or args.model_key is None:
        raise AdapterError("use --contract or provide both --contract-record and --model-key")
    return load_contract_record(Path(args.contract_record), model_key=args.model_key, policy=policy)["selected_contract"]


def _profile_policy(profile_dir: Path) -> bytes:
    return load_bundle(profile_dir).policy


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    calibrate = sub.add_parser("calibrate", help="calibrate once for one immutable local model")
    calibrate.add_argument("--profile", type=Path, required=True)
    calibrate.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    calibrate.add_argument("--model", required=True)
    calibrate.add_argument("--model-key", required=True)
    calibrate.add_argument("--output", type=Path, required=True)
    calibrate.add_argument("--timeout-seconds", type=float, default=60.0)

    for name in ("plan", "answer"):
        command = sub.add_parser(name, help=f"{name} one grounded factual question")
        command.add_argument("--profile", type=Path, required=True)
        command.add_argument("--question", required=True)
        command.add_argument("--qid")
        command.add_argument("--scope")
        command.add_argument("--contract", choices=AUTO_CONTRACT_CANDIDATES)
        command.add_argument("--contract-record", type=Path)
        command.add_argument("--model-key")
        command.add_argument("--corpus-index", type=Path, help="optional deterministic local text-corpus index")
        command.add_argument("--corpus-top-k", type=int, default=12)
        if name == "plan":
            command.add_argument("--verbose", action="store_true", help="include frame, audit and model messages; may contain private evidence")
        if name == "answer":
            command.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
            command.add_argument("--model", required=True)
            command.add_argument("--timeout-seconds", type=float, default=60.0)

    args = parser.parse_args(argv)
    try:
        if args.command == "calibrate":
            policy = _profile_policy(args.profile)
            record = calibrate_contract(
                base_url=args.base_url,
                model=args.model,
                model_key=args.model_key,
                policy=policy,
                timeout_seconds=args.timeout_seconds,
            )
            if args.output.exists():
                raise AdapterError("calibration output already exists")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(_json_bytes(record) + b"\n")
            _print(record)
            return 0

        policy = _profile_policy(args.profile)
        contract = _resolve_contract(args, policy)
        qid = args.qid or _qid(args.question)
        plan = plan_question(
            profile_dir=args.profile,
            question=args.question,
            qid=qid,
            scope=args.scope,
            contract=contract,
            corpus_index=args.corpus_index,
            corpus_top_k=args.corpus_top_k,
        )
        if args.command == "plan":
            if args.verbose:
                _print({**plan, "selected_contract": contract})
            else:
                _print({
                    "route": plan["route"],
                    "model_called": plan["model_called"],
                    "reply": plan["reply"],
                    "selected_contract": contract,
                    "profile_sha256": plan["profile_sha256"],
                })
            return 0
        if not plan["model_called"]:
            _print({
                "route": plan["route"],
                "model_called": False,
                "reply": plan["reply"],
                "selected_contract": contract,
                "profile_sha256": plan["profile_sha256"],
            })
            return 0
        result = request_answer(
            args.base_url,
            args.model,
            contract,
            plan["messages"],
            timeout_seconds=args.timeout_seconds,
        )
        if not result["valid"] or result["reply"] is None:
            raise AdapterError("model returned an invalid grounding answer object; no retry or repair performed")
        _print({
            "route": plan["route"],
            "model_called": True,
            "reply": result["reply"],
            "selected_contract": contract,
            "profile_sha256": plan["profile_sha256"],
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
        })
        return 0
    except (AdapterError, ValueError, OSError) as exc:
        print(f"ExactScope grounding_v1: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
