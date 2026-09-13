#!/usr/bin/env python3
"""Thin llama.cpp transport used by ExactScope v1.1 research paths.

Planning, retrieval, projection and proof-based zero-call resolution live outside this
transport. This module owns only the inference boundary: loopback HTTP, one-time
capability calibration/cache, and the reference CLI. Normal answers use zero or one
model call. The current product direction is a semantic policy/qualification layer,
not a competing runtime amplifier or inference engine.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import ipaddress
import json
from pathlib import Path
import sys
from typing import Any
import urllib.parse

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from grounding_answer_contract import (  # noqa: E402
    ANSWER_SPEC_KINDS,
    CompiledAnswerSpec,
    compile_answer_spec,
)
from grounding_canonical import loads as canonical_loads  # noqa: E402
from grounding_engine import (  # noqa: E402
    DEFAULT_CORPUS_EVIDENCE_BYTES,
    DEFAULT_CORPUS_EVIDENCE_POLICY,
    DEFAULT_CORPUS_PROJECTION_ID,
    SUPPORTED_CORPUS_PROJECTIONS,
    EngineError,
    GroundingSession,
    plan_question,
    prefix_cache_key,
)
from grounding_projection import EVIDENCE_POLICY_IDS  # noqa: E402
from grounding_runtime import load_bundle  # noqa: E402
from grounding_v1_surface import (  # noqa: E402
    AUTO_CONTRACT_CALIBRATION,
    AUTO_CONTRACT_CANDIDATES,
    AUTO_V2_TIE_PREFERENCE,
    OUTPUT_SURFACE_CANDIDATES,
    OUTPUT_SURFACE_JSON_SCHEMA,
    OUTPUT_SURFACE_PROBE,
    PREFLIGHT_STOPPING_RULE,
    calibration_messages,
    normalize_answer,
    output_surface_request_fields,
    parse_answer_object,
    select_supported_contract,
    surface_sha256,
    validate_preflight_contract_profiles,
    validate_preflight_surface_probes,
)

MODEL_KEY_MAX_BYTES = 2048
MAX_CONTRACT_RECORD_BYTES = 64 * 1024
MAX_HTTP_RESPONSE_BYTES = 1024 * 1024
CAPABILITY_CACHE_FORMAT = "exactscope.runtime-amplifier-capability-cache"
CAPABILITY_CACHE_VERSION = "0.3"


class AdapterError(RuntimeError):
    """Invalid or failed llama.cpp inference boundary."""


class SurfaceUnsupportedError(AdapterError):
    """The server explicitly rejected one output surface."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _validate_model_key(model_key: str) -> str:
    if not isinstance(model_key, str) or not model_key.strip():
        raise AdapterError("model-key must be a stable nonempty model/runtime/template/reasoning identity")
    value = model_key.strip()
    if len(value.encode("utf-8")) > MODEL_KEY_MAX_BYTES:
        raise AdapterError("model-key exceeds the bounded identity size")
    return value


def validate_local_base_url(base_url: str) -> str:
    """Accept literal loopback HTTP only; no DNS, proxy, redirect, credentials or query."""
    if not isinstance(base_url, str) or not base_url.strip():
        raise AdapterError("grounding_v1 accepts only a loopback http llama.cpp endpoint")
    normalized = base_url.rstrip("/")
    parsed = urllib.parse.urlparse(normalized)
    if parsed.scheme != "http" or parsed.hostname is None:
        raise AdapterError("grounding_v1 accepts only a loopback http llama.cpp endpoint")
    try:
        host = ipaddress.ip_address(parsed.hostname)
        _ = parsed.port
    except ValueError as exc:
        raise AdapterError("invalid llama.cpp base URL") from exc
    if not host.is_loopback:
        raise AdapterError("grounding_v1 accepts only a literal loopback IP endpoint")
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise AdapterError("invalid llama.cpp base URL")
    return normalized


def request_answer(
    base_url: str,
    model: str,
    contract: str,
    request_messages: list[dict[str, str]],
    *,
    output_surface: str = OUTPUT_SURFACE_JSON_SCHEMA,
    answer_choices: tuple[str, ...] | list[str] | None = None,
    answer_spec: dict[str, Any] | CompiledAnswerSpec | None = None,
    timeout_seconds: float = 60.0,
    max_tokens: int = 96,
    seed: int = 20260906,
) -> dict[str, Any]:
    """Make exactly one direct local request. No retry and no semantic repair."""
    base_url = validate_local_base_url(base_url)
    if contract not in AUTO_CONTRACT_CANDIDATES:
        raise AdapterError("unsupported selected grounding contract")
    if not model:
        raise AdapterError("model alias must be nonempty")
    if output_surface not in OUTPUT_SURFACE_CANDIDATES:
        raise AdapterError("unsupported grounding output surface")
    compiled = compile_answer_spec(answer_spec, answer_choices=answer_choices)
    payload = {
        "model": model,
        "stream": False,
        "temperature": 0,
        "seed": seed,
        "max_tokens": max_tokens,
        "messages": request_messages,
        **output_surface_request_fields(output_surface, answer_spec=compiled),
    }
    parsed = urllib.parse.urlparse(base_url)
    host = parsed.hostname
    if host is None:
        raise AdapterError("invalid llama.cpp base URL")
    try:
        port = parsed.port or 80
    except ValueError as exc:
        raise AdapterError("invalid llama.cpp base URL") from exc
    path = parsed.path.rstrip("/") + "/chat/completions"
    connection = http.client.HTTPConnection(host, port, timeout=timeout_seconds)
    try:
        connection.request(
            "POST",
            path,
            body=_json_bytes(payload),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        response = connection.getresponse()
        status = response.status
        raw_bytes = response.read(MAX_HTTP_RESPONSE_BYTES + 1)
    except (http.client.HTTPException, TimeoutError, OSError) as exc:
        raise AdapterError(f"llama.cpp request failed: {exc}") from exc
    finally:
        connection.close()
    if len(raw_bytes) > MAX_HTTP_RESPONSE_BYTES:
        raise AdapterError("llama.cpp response exceeds bounded size")
    if not 200 <= status < 300:
        detail = raw_bytes.decode("utf-8", errors="replace")
        error = f"llama.cpp HTTP {status}: {detail}"
        if status in {400, 422}:
            raise SurfaceUnsupportedError(error)
        raise AdapterError(error)
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
    valid, value = parse_answer_object(content, compiled)
    usage = raw.get("usage") if isinstance(raw.get("usage"), dict) else {}
    return {
        "valid": valid,
        "value": value,
        "reply": normalize_answer(valid, value),
        "raw_content": content,
        "answer_spec_sha256": compiled.sha256,
        "prompt_tokens": usage.get("prompt_tokens") if type(usage.get("prompt_tokens")) is int else None,
        "completion_tokens": usage.get("completion_tokens") if type(usage.get("completion_tokens")) is int else None,
    }


def _calibrate_candidate_profile(
    *,
    base_url: str,
    model: str,
    candidate: str,
    policy: bytes,
    output_surface: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    cases = []
    for case_id, question, evidence, expected in AUTO_CONTRACT_CALIBRATION:
        result = request_answer(
            base_url,
            model,
            candidate,
            calibration_messages(candidate, question, evidence, policy),
            output_surface=output_surface,
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
    return {
        "contract": candidate,
        "score": sum(case["correct"] for case in cases),
        "case_count": len(cases),
        "cases": cases,
    }


def calibrate_contract(
    *,
    base_url: str,
    model: str,
    model_key: str,
    policy: bytes,
    timeout_seconds: float = 60.0,
) -> dict[str, Any]:
    """Compile one model/runtime capability using proof-based early stops.

    Surface selection stops at the first supported surface because that is the
    frozen preference rule. Contract calibration tests the preferred contract
    first; a perfect profile proves it cannot be beaten and wins every tie, so
    the other candidates are unnecessary. Non-perfect preferred profiles fall
    through to the complete frozen selector.
    """
    model_key = _validate_model_key(model_key)
    probe_id, probe_question, probe_evidence, probe_expected = OUTPUT_SURFACE_PROBE
    preferred = AUTO_V2_TIE_PREFERENCE[0]
    surface_probes: list[dict[str, Any]] = []
    selected_surface: str | None = None
    for surface in OUTPUT_SURFACE_CANDIDATES:
        try:
            probe = request_answer(
                base_url,
                model,
                preferred,
                calibration_messages(preferred, probe_question, probe_evidence, policy),
                output_surface=surface,
                timeout_seconds=timeout_seconds,
            )
            valid = bool(probe["valid"])
            surface_probes.append({
                "surface": surface,
                "case_id": probe_id,
                "protocol_valid": valid,
                "semantic_match": valid and probe["value"] == probe_expected,
                "actual": probe["value"] if valid else None,
                "error": None,
            })
            if valid:
                selected_surface = surface
                break
        except SurfaceUnsupportedError as exc:
            surface_probes.append({
                "surface": surface,
                "case_id": probe_id,
                "protocol_valid": False,
                "semantic_match": False,
                "actual": None,
                "error": str(exc),
            })
    if selected_surface is None:
        raise AdapterError("unsupported model/runtime output surface")

    preferred_profile = _calibrate_candidate_profile(
        base_url=base_url,
        model=model,
        candidate=preferred,
        policy=policy,
        output_surface=selected_surface,
        timeout_seconds=timeout_seconds,
    )
    if preferred_profile["score"] == len(AUTO_CONTRACT_CALIBRATION):
        profiles = [preferred_profile]
        selected = preferred
    else:
        by_contract = {preferred: preferred_profile}
        for candidate in AUTO_CONTRACT_CANDIDATES:
            if candidate == preferred:
                continue
            by_contract[candidate] = _calibrate_candidate_profile(
                base_url=base_url,
                model=model,
                candidate=candidate,
                policy=policy,
                output_surface=selected_surface,
                timeout_seconds=timeout_seconds,
            )
        profiles = [by_contract[candidate] for candidate in AUTO_CONTRACT_CANDIDATES]
        selected = select_supported_contract({profile["contract"]: profile["score"] for profile in profiles})
        if selected is None:
            raise AdapterError("unsupported model/runtime answer contract: semantic calibration scored zero")

    surface_count = len(surface_probes)
    calibration_count = sum(profile["case_count"] for profile in profiles)
    record = {
        "format": "exactscope.grounding-v1.1-contract-record",
        "format_version": "0.4",
        "model_key": model_key,
        "model_surface_sha256": surface_sha256(),
        "policy_sha256": _sha256(policy),
        "selected_output_surface": selected_surface,
        "selected_contract": selected,
        "surface_probe_model_requests": surface_count,
        "contract_calibration_model_requests": calibration_count,
        "model_request_count": surface_count + calibration_count,
        "retry_count": 0,
        "surface_probes": surface_probes,
        "tie_preference": list(AUTO_V2_TIE_PREFERENCE),
        "profiles": profiles,
        "stopping_rule": PREFLIGHT_STOPPING_RULE,
    }
    validate_contract_record(record, model_key=model_key, policy=policy)
    return record


def validate_contract_record(record: Any, *, model_key: str, policy: bytes) -> tuple[str, str]:
    """Recompute the proof-based preflight decision from persisted cold-path evidence."""
    expected_keys = {
        "format", "format_version", "model_key", "model_surface_sha256", "policy_sha256",
        "selected_output_surface", "selected_contract", "surface_probe_model_requests",
        "contract_calibration_model_requests", "model_request_count", "retry_count",
        "surface_probes", "tie_preference", "profiles", "stopping_rule",
    }
    if not isinstance(record, dict) or set(record) != expected_keys:
        raise AdapterError("grounding contract record shape drift")
    required = {
        "format": "exactscope.grounding-v1.1-contract-record",
        "format_version": "0.4",
        "model_key": _validate_model_key(model_key),
        "model_surface_sha256": surface_sha256(),
        "policy_sha256": _sha256(policy),
        "retry_count": 0,
        "tie_preference": list(AUTO_V2_TIE_PREFERENCE),
        "stopping_rule": PREFLIGHT_STOPPING_RULE,
    }
    for key, expected in required.items():
        if record.get(key) != expected:
            raise AdapterError(f"grounding contract record mismatch: {key}")
    try:
        selected_surface = validate_preflight_surface_probes(record["surface_probes"])
        if selected_surface is None:
            raise ValueError("contract record cannot bind an unsupported output surface")
        profiles = record["profiles"]
        selected_contract = validate_preflight_contract_profiles(profiles)
        calibration_requests = sum(profile["case_count"] for profile in profiles)
    except ValueError as exc:
        raise AdapterError(f"grounding contract record evidence drift: {exc}") from exc
    surface_requests = len(record["surface_probes"])
    if record.get("surface_probe_model_requests") != surface_requests:
        raise AdapterError("grounding contract record surface request accounting drift")
    if record.get("contract_calibration_model_requests") != calibration_requests:
        raise AdapterError("grounding contract record calibration request accounting drift")
    if record.get("model_request_count") != surface_requests + calibration_requests:
        raise AdapterError("grounding contract record total request accounting drift")
    if record.get("selected_output_surface") != selected_surface:
        raise AdapterError("grounding contract record surface selection mismatch")
    if record.get("selected_contract") != selected_contract:
        raise AdapterError("grounding contract record contract selection mismatch")
    return selected_surface, selected_contract


def load_contract_record(path: Path, *, model_key: str, policy: bytes) -> dict[str, Any]:
    """Validate a persisted preflight record on the cold path before reuse."""
    model_key = _validate_model_key(model_key)
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_CONTRACT_RECORD_BYTES + 1)
        if len(raw) > MAX_CONTRACT_RECORD_BYTES:
            raise AdapterError("grounding contract record exceeds bounded size")
        record = canonical_loads(raw)
    except AdapterError:
        raise
    except (OSError, ValueError, UnicodeError) as exc:
        raise AdapterError("cannot read grounding contract record") from exc
    validate_contract_record(record, model_key=model_key, policy=policy)
    return record


def capability_cache_key(*, model_key: str, policy: bytes) -> str:
    return _sha256(_json_bytes({
        "format": CAPABILITY_CACHE_FORMAT,
        "format_version": CAPABILITY_CACHE_VERSION,
        "model_key": _validate_model_key(model_key),
        "model_surface_sha256": surface_sha256(),
        "policy_sha256": _sha256(policy),
    }))


def capability_cache_path(cache_dir: Path, *, model_key: str, policy: bytes) -> Path:
    return cache_dir.resolve() / (capability_cache_key(model_key=model_key, policy=policy) + ".json")


def load_or_calibrate_capability(
    *,
    cache_dir: Path,
    base_url: str,
    model: str,
    model_key: str,
    policy: bytes,
    timeout_seconds: float = 60.0,
) -> tuple[dict[str, Any], bool, Path]:
    path = capability_cache_path(cache_dir, model_key=model_key, policy=policy)
    if path.exists():
        return load_contract_record(path, model_key=model_key, policy=policy), True, path
    cache_root = cache_dir.resolve()
    cache_root.mkdir(parents=True, exist_ok=True)
    if not cache_root.is_dir():
        raise AdapterError("capability cache path is not a directory")
    record = calibrate_contract(
        base_url=base_url,
        model=model,
        model_key=model_key,
        policy=policy,
        timeout_seconds=timeout_seconds,
    )
    encoded = _json_bytes(record) + b"\n"
    try:
        with path.open("xb") as handle:
            handle.write(encoded)
    except FileExistsError:
        return load_contract_record(path, model_key=model_key, policy=policy), True, path
    return record, False, path


def _qid(question: str) -> str:
    return "q-" + hashlib.sha256(question.encode("utf-8")).hexdigest()[:16]


def _answer_spec_from_args(args: argparse.Namespace) -> CompiledAnswerSpec:
    choices = getattr(args, "answer_choices", None)
    kind = getattr(args, "answer_kind", None)
    minimum_raw = getattr(args, "answer_minimum", None)
    maximum_raw = getattr(args, "answer_maximum", None)
    required = bool(getattr(args, "answer_required", False))
    if kind is None:
        if minimum_raw is not None or maximum_raw is not None or required:
            raise AdapterError("typed answer options require --answer-kind")
        return compile_answer_spec(answer_choices=choices)
    if choices is not None and kind != "choice":
        raise AdapterError("--answer-choice requires --answer-kind choice or no explicit answer kind")
    spec: dict[str, Any] = {"kind": kind, "nullable": not required}
    if kind == "choice":
        if choices is None:
            raise AdapterError("--answer-kind choice requires repeated --answer-choice values")
        spec["choices"] = list(choices)
        if not required:
            spec["nullable"] = False
    if minimum_raw is not None or maximum_raw is not None:
        if kind not in {"integer", "number"}:
            raise AdapterError("answer bounds require integer or number answer kind")
        parser = int if kind == "integer" else float
        try:
            if minimum_raw is not None:
                spec["minimum"] = parser(minimum_raw)
            if maximum_raw is not None:
                spec["maximum"] = parser(maximum_raw)
        except ValueError as exc:
            raise AdapterError("invalid numeric answer bound") from exc
    return compile_answer_spec(spec)


def _profile_policy(profile_dir: Path) -> bytes:
    return load_bundle(profile_dir).policy


def _resolve_cached_capability(args: argparse.Namespace, policy: bytes) -> dict[str, Any] | None:
    cache_dir = getattr(args, "capability_cache_dir", None)
    if cache_dir is None or args.contract is not None or args.contract_record is not None:
        return None
    if args.model_key is None:
        raise AdapterError("--capability-cache-dir requires --model-key")
    path = capability_cache_path(Path(cache_dir), model_key=args.model_key, policy=policy)
    if path.exists():
        return {"record": load_contract_record(path, model_key=args.model_key, policy=policy), "path": path, "hit": True}
    if args.command != "answer":
        raise AdapterError("capability cache miss; run answer/calibrate once before offline plan")
    record, hit, resolved = load_or_calibrate_capability(
        cache_dir=Path(cache_dir),
        base_url=args.base_url,
        model=args.model,
        model_key=args.model_key,
        policy=policy,
        timeout_seconds=args.timeout_seconds,
    )
    return {"record": record, "path": resolved, "hit": hit}


def _resolve_contract_and_surface(args: argparse.Namespace, policy: bytes) -> tuple[str, str]:
    if args.contract is not None:
        if args.contract not in AUTO_CONTRACT_CANDIDATES:
            raise AdapterError("unsupported --contract")
        surface = args.surface or OUTPUT_SURFACE_JSON_SCHEMA
        if surface not in OUTPUT_SURFACE_CANDIDATES:
            raise AdapterError("unsupported --surface")
        return args.contract, surface
    if args.contract_record is None or args.model_key is None:
        raise AdapterError("use --contract/--surface or provide both --contract-record and --model-key")
    record = load_contract_record(Path(args.contract_record), model_key=args.model_key, policy=policy)
    return record["selected_contract"], record["selected_output_surface"]


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    calibrate = sub.add_parser("calibrate", help="calibrate the full frozen selector for one immutable local model/runtime")
    calibrate.add_argument("--profile", type=Path, required=True)
    calibrate.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    calibrate.add_argument("--model", required=True)
    calibrate.add_argument("--model-key", required=True)
    calibrate.add_argument("--output", type=Path, required=True)
    calibrate.add_argument("--timeout-seconds", type=float, default=60.0)

    doctor = sub.add_parser("doctor", help="validate profile and capability record with zero network")
    doctor.add_argument("--profile", type=Path, required=True)
    doctor.add_argument("--contract-record", type=Path, required=True)
    doctor.add_argument("--model-key", required=True)

    for name in ("plan", "answer"):
        command = sub.add_parser(name, help=f"{name} one amplified factual question")
        command.add_argument("--profile", type=Path, required=True)
        command.add_argument("--question", required=True)
        command.add_argument("--qid")
        command.add_argument("--scope")
        command.add_argument("--contract", choices=AUTO_CONTRACT_CANDIDATES)
        command.add_argument("--surface", choices=OUTPUT_SURFACE_CANDIDATES)
        command.add_argument("--contract-record", type=Path)
        command.add_argument("--model-key")
        command.add_argument("--retrieval-query")
        command.add_argument("--corpus-index", type=Path)
        command.add_argument("--corpus-top-k", type=int, default=12)
        command.add_argument("--corpus-evidence-bytes", type=int, default=DEFAULT_CORPUS_EVIDENCE_BYTES)
        command.add_argument("--corpus-evidence-policy", choices=EVIDENCE_POLICY_IDS, default=DEFAULT_CORPUS_EVIDENCE_POLICY)
        command.add_argument("--corpus-projection", choices=SUPPORTED_CORPUS_PROJECTIONS, default=DEFAULT_CORPUS_PROJECTION_ID)
        command.add_argument("--answer-choice", dest="answer_choices", action="append")
        command.add_argument("--answer-kind", choices=ANSWER_SPEC_KINDS)
        command.add_argument("--answer-required", action="store_true")
        command.add_argument("--answer-minimum")
        command.add_argument("--answer-maximum")
        command.add_argument("--capability-cache-dir", type=Path)
        if name == "plan":
            command.add_argument("--verbose", action="store_true")
        else:
            command.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
            command.add_argument("--model", required=True)
            command.add_argument("--timeout-seconds", type=float, default=60.0)

    args = parser.parse_args(argv)
    try:
        if args.command == "calibrate":
            if args.output.exists():
                raise AdapterError("calibration output already exists")
            policy = _profile_policy(args.profile)
            record = calibrate_contract(
                base_url=args.base_url,
                model=args.model,
                model_key=args.model_key,
                policy=policy,
                timeout_seconds=args.timeout_seconds,
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("xb") as handle:
                handle.write(_json_bytes(record) + b"\n")
            _print(record)
            return 0

        if args.command == "doctor":
            bundle = load_bundle(args.profile)
            record = load_contract_record(args.contract_record, model_key=args.model_key, policy=bundle.policy)
            _print({
                "status": "PASS",
                "network_requests": 0,
                "profile_id": bundle.profile.get("profile_id"),
                "profile_sha256": bundle.profile_sha256,
                "policy_sha256": _sha256(bundle.policy),
                "contract_record_sha256": _sha256(_json_bytes(record)),
                "model_key_sha256": _sha256(_validate_model_key(args.model_key).encode("utf-8")),
                "model_surface_sha256": record["model_surface_sha256"],
                "selected_contract": record["selected_contract"],
                "selected_output_surface": record["selected_output_surface"],
            })
            return 0

        session = GroundingSession.open(args.profile)
        policy = session.policy
        compiled_spec = _answer_spec_from_args(args)
        cached = _resolve_cached_capability(args, policy)
        if cached is not None:
            args.contract_record = cached["path"]
        contract, output_surface = _resolve_contract_and_surface(args, policy)
        plan = session.plan(
            question=args.question,
            qid=args.qid or _qid(args.question),
            scope=args.scope,
            contract=contract,
            retrieval_query=args.retrieval_query,
            corpus_index=args.corpus_index,
            corpus_top_k=args.corpus_top_k,
            corpus_evidence_bytes=args.corpus_evidence_bytes,
            corpus_projection=args.corpus_projection,
            corpus_evidence_policy=args.corpus_evidence_policy,
            answer_spec=compiled_spec,
        )
        if args.command == "plan":
            if args.verbose:
                _print({**plan, "selected_contract": contract, "selected_output_surface": output_surface})
            else:
                _print({
                    "route": plan["route"],
                    "model_called": plan["model_called"],
                    "reply": plan["reply"],
                    "selected_contract": contract,
                    "selected_output_surface": output_surface,
                    "profile_sha256": plan["profile_sha256"],
                })
            return 0
        if not plan["model_called"]:
            _print({
                "route": plan["route"],
                "model_called": False,
                "reply": plan["reply"],
                "selected_contract": contract,
                "selected_output_surface": output_surface,
                "profile_sha256": plan["profile_sha256"],
            })
            return 0
        result = request_answer(
            args.base_url,
            args.model,
            contract,
            plan["messages"],
            output_surface=output_surface,
            answer_spec=compiled_spec,
            timeout_seconds=args.timeout_seconds,
        )
        if not result["valid"] or result["reply"] is None:
            raise AdapterError("model returned an invalid grounding answer object; no retry or repair performed")
        _print({
            "route": plan["route"],
            "model_called": True,
            "reply": result["reply"],
            "selected_contract": contract,
            "selected_output_surface": output_surface,
            "profile_sha256": plan["profile_sha256"],
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
        })
        return 0
    except (AdapterError, EngineError, ValueError, OSError) as exc:
        print(f"ExactScope grounding_v1: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
