#!/usr/bin/env python3
"""Create/verify a frozen rc4 grounding benchmark run identity. Zero inference."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from grounding_canonical import canonical_bytes, loads  # noqa: E402
from grounding_runtime import load_bundle  # noqa: E402
from grounding_v1_surface import (  # noqa: E402
    ANSWER_CONTRACT_APPLICATION,
    AUTO_CONTRACT_CALIBRATION,
    AUTO_CONTRACT_CANDIDATES,
    AUTO_V2_TIE_PREFERENCE,
    MODEL_PROJECTION_ID,
    surface_sha256,
)
from verify_grounding_package import verify as verify_package_root  # noqa: E402

SHA_RE = re.compile(r"^[a-f0-9]{64}$")
COMMIT_RE = re.compile(r"^[a-f0-9]{40}$")
EXPECTED_CANDIDATE_ANSWER_CALL_POLICY = "bound-by-benchmark-isolation-policy-v0.4"

EXPECTED_ANSWER_CALL_POLICY = {
    "A": "exactly-one-model-answer-matched-selected-contract",
    "G": "zero-or-one-model-answer-after-deterministic-host",
    "host_completion": {
        "authoritative_unresolved": {
            "authority": "authoritative",
            "block_if_any_target_unresolved": True,
            "state_precedence": ["conflict", "ambiguous", "unavailable", "none"],
            "state_to_disposition": {
                "ambiguous": "clarify",
                "conflict": "conflict",
                "none": "abstain",
                "unavailable": "unavailable",
            },
        },
        "canonical_scalar": {
            "single_target_group_only": True,
            "state": "grounded",
            "item_count": 1,
            "content_kind": "scalar",
            "canonical_lexical_required": True,
        },
    },
}
EXPECTED_MODEL_SURFACE_POLICY = {
    "selector": "answer-object-auto-v2",
    "candidates": list(AUTO_CONTRACT_CANDIDATES),
    "tie_preference": list(AUTO_V2_TIE_PREFERENCE),
    "calibration_case_count": len(AUTO_CONTRACT_CALIBRATION),
    "calibration_model_requests": len(AUTO_CONTRACT_CANDIDATES) * len(AUTO_CONTRACT_CALIBRATION),
    "answer_contract_application": ANSWER_CONTRACT_APPLICATION,
    "supplemental_empty": "ordinary-knowledge-no-grounding-context",
    "grounded_text_projection": MODEL_PROJECTION_ID,
    "grounding_policy": "full-profile-policy",
    "retry_count": 0,
}


class PreregistrationError(RuntimeError):
    pass


def validate_answer_call_policy(value: Any) -> dict[str, Any]:
    if value != EXPECTED_ANSWER_CALL_POLICY:
        raise PreregistrationError("unsupported answer-call policy")
    return value


def validate_model_surface_policy(value: Any) -> dict[str, Any]:
    if value != EXPECTED_MODEL_SURFACE_POLICY:
        raise PreregistrationError("unsupported grounding model-surface policy")
    return value


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise PreregistrationError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PreregistrationError(f"JSON root is not object: {path}")
    return value


def load_cjson(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    value = loads(data)
    if not isinstance(value, dict) or data != canonical_bytes(value):
        raise PreregistrationError(f"noncanonical JSON: {path}")
    return value


def require_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise PreregistrationError(f"invalid sha256: {label}")
    return value


def _verify_candidate(candidate: Path, *, verify_gold_manifest: bool) -> dict[str, Any]:
    candidate = candidate.resolve()
    manifests = candidate / "manifests"
    serving = candidate / "serving"
    if not manifests.is_dir() or not serving.is_dir():
        raise PreregistrationError("candidate must contain serving/ and manifests/")
    if verify_gold_manifest and not (candidate / "gold").is_dir():
        raise PreregistrationError("candidate must contain gold/ for preregistration")
    candidate_manifest_path = manifests / "candidate-manifest.json"
    candidate_manifest = load_cjson(candidate_manifest_path)
    if candidate_manifest.get("status") != "generated-before-inference" or candidate_manifest.get("model_inference_performed") is not False:
        raise PreregistrationError("candidate is not frozen before inference")
    if candidate_manifest.get("answer_call_policy") != EXPECTED_CANDIDATE_ANSWER_CALL_POLICY:
        raise PreregistrationError("candidate answer-call policy identity drift")
    selected_isolation_sha = file_sha(ROOT / "benchmarks/grounding-isolation-policy.json")
    if candidate_manifest.get("isolation_policy_sha256") != selected_isolation_sha:
        raise PreregistrationError("candidate isolation-policy digest drift")
    if candidate_manifest.get("arms") != ["A", "G"] or candidate_manifest.get("rewrite_calls") != 0:
        raise PreregistrationError("candidate A/G execution contract drift")
    serving_manifest_path = manifests / "serving-manifest.json"
    if file_sha(serving_manifest_path) != candidate_manifest.get("serving_manifest_sha256"):
        raise PreregistrationError("serving manifest digest drift")
    if verify_gold_manifest:
        gold_manifest_path = manifests / "gold-manifest.json"
        if file_sha(gold_manifest_path) != candidate_manifest.get("gold_manifest_sha256"):
            raise PreregistrationError("gold manifest digest drift")
    bundle = load_bundle(serving / "grounding")
    if bundle.profile_sha256 != candidate_manifest.get("grounding_profile_sha256"):
        raise PreregistrationError("grounding profile digest drift")
    if hashlib.sha256(canonical_bytes(bundle.manifest)).hexdigest() != candidate_manifest.get("grounding_manifest_sha256"):
        raise PreregistrationError("grounding manifest digest drift")
    profile = bundle.profile
    sources = sorted({ref["sha256"] for ref in profile["source_snapshots"]})
    providers = sorted({entry["identity"]["sha256"] for entry in profile["providers"]})
    projection = profile["projection"]
    return {
        "candidate_id": candidate_manifest["candidate_id"],
        "candidate_manifest_sha256": file_sha(candidate_manifest_path),
        "serving_manifest_sha256": candidate_manifest["serving_manifest_sha256"],
        "gold_manifest_sha256": candidate_manifest["gold_manifest_sha256"],
        "grounding_manifest_sha256": candidate_manifest["grounding_manifest_sha256"],
        "grounding_profile_sha256": bundle.profile_sha256,
        "source_snapshot_sha256": sources,
        "provider_identity_sha256": providers,
        "projection_template_sha256": projection["template"]["sha256"],
        "projection_policy_sha256": projection["policy"]["sha256"],
        "projection_renderer_sha256": projection["renderer"]["sha256"],
        "generator_sha256": require_sha(candidate_manifest["generator_sha256"], "candidate.generator_sha256"),
        "isolation_policy_sha256": selected_isolation_sha,
        "generator_seed": str(candidate_manifest["seed"]),
        "item_count": int(candidate_manifest["item_count"]),
    }


def verify_candidate(candidate: Path) -> dict[str, Any]:
    """Full preregistration-side candidate verification, including the gold manifest."""
    return _verify_candidate(candidate, verify_gold_manifest=True)


def verify_serving_candidate(candidate: Path) -> dict[str, Any]:
    """Runner-safe candidate verification that never opens gold/ or gold-manifest.json."""
    return _verify_candidate(candidate, verify_gold_manifest=False)


def resolve_model(inventory_path: Path, model_id: str, model_root: Path | None, model_path: Path | None) -> tuple[str, dict[str, Any]]:
    inventory = load_json(inventory_path)
    if inventory.get("format") != "exactscope.grounding-model-inventory" or inventory.get("format_version") != "0.1":
        raise PreregistrationError("unsupported grounding model inventory")
    records = [record for record in inventory.get("records", []) if isinstance(record, dict) and record.get("id") == model_id]
    if len(records) != 1:
        raise PreregistrationError("unknown or duplicate model id")
    record = dict(records[0])
    if model_path is None:
        if model_root is None:
            raise PreregistrationError("provide --model-root or --model-path")
        model_path = model_root.resolve() / record["id"] / record["requested_file"]
    else:
        model_path = model_path.resolve()
    if not model_path.is_file():
        raise PreregistrationError(f"model file missing: {model_path}")
    if model_path.stat().st_size != record["bytes"]:
        raise PreregistrationError("model byte-size drift")
    digest = file_sha(model_path)
    if digest != record["sha256"]:
        raise PreregistrationError("model sha256 drift")
    record["path"] = str(model_path)
    return file_sha(inventory_path), record


def resolve_runtime(record_path: Path, executable: Path) -> tuple[str, dict[str, Any]]:
    record = load_json(record_path)
    if record.get("format") != "exactscope.grounding-runtime-record" or record.get("format_version") != "0.1":
        raise PreregistrationError("unsupported runtime record")
    executable = executable.resolve()
    if not executable.is_file():
        raise PreregistrationError(f"runtime executable missing: {executable}")
    digest = file_sha(executable)
    if digest != record.get("executable_sha256"):
        raise PreregistrationError("runtime executable sha256 drift")
    launch = record.get("launch")
    hardware = record.get("hardware")
    if not isinstance(launch, dict) or not isinstance(hardware, dict):
        raise PreregistrationError("runtime record lacks launch/hardware")
    return file_sha(record_path), {
        "runtime_id": record["runtime_id"],
        "executable_sha256": digest,
        "executable_path": str(executable),
        "version": record["version"],
        "commit": record["commit"],
        "launch": launch,
        "hardware": hardware,
    }


def verify_package_manifest(path: Path, candidate: dict[str, Any], source_commit: str) -> tuple[str, dict[str, Any]]:
    package_verification = verify_package_root(path.parent)
    manifest = load_json(path)
    if manifest.get("format") != "exactscope.grounding-evaluation-package" or manifest.get("format_version") != "0.3":
        raise PreregistrationError("unsupported evaluation package manifest")
    if manifest.get("source_commit") != source_commit:
        raise PreregistrationError("package source commit mismatch")
    if manifest.get("candidate_id") != candidate["candidate_id"]:
        raise PreregistrationError("package candidate id mismatch")
    if manifest.get("candidate_manifest_sha256") != candidate["candidate_manifest_sha256"]:
        raise PreregistrationError("package candidate manifest mismatch")
    manifest_sha = file_sha(path)
    if package_verification.get("package_manifest_sha256") != manifest_sha:
        raise PreregistrationError("package payload verification drift")
    return manifest_sha, manifest


def create_document(args: argparse.Namespace) -> dict[str, Any]:
    if not COMMIT_RE.fullmatch(args.source_commit):
        raise PreregistrationError("--source-commit must be 40 lowercase hex chars")
    if args.output.exists():
        raise PreregistrationError("preregistration output already exists")
    candidate = verify_candidate(args.candidate)
    inventory_sha, model = resolve_model(args.model_inventory, args.model_id, args.model_root, args.model_path)
    runtime_record_sha, runtime = resolve_runtime(args.runtime_record, args.runtime_executable)
    generation = load_json(args.generation_config)
    isolation = load_json(args.isolation_policy)
    if generation.get("format") != "exactscope.grounding-generation-config" or generation.get("retry_count") != 0 or generation.get("hidden_repair") is not False:
        raise PreregistrationError("generation config violates frozen no-retry/no-repair contract")
    if isolation.get("format") != "exactscope.grounding-isolation-policy" or isolation.get("format_version") != "0.4" or isolation.get("arms") != ["A", "G"]:
        raise PreregistrationError("isolation policy violates selected A/G contract")
    answer_call_policy = validate_answer_call_policy(isolation.get("answer_call_policy"))
    model_surface_policy = validate_model_surface_policy(isolation.get("model_surface_policy"))
    if isolation.get("rewrite_calls") != 0:
        raise PreregistrationError("isolation policy changes rewrite-call contract")
    package_manifest_sha, package_manifest = verify_package_manifest(args.package_manifest, candidate, args.source_commit)
    generation_sha = file_sha(args.generation_config)
    isolation_sha = file_sha(args.isolation_policy)
    scorer_sha = file_sha(args.scorer)
    selected_surface_sha = surface_sha256()
    packaged_identities = {
        "model_inventory_sha256": inventory_sha,
        "runtime_record_sha256": runtime_record_sha,
        "generation_config_sha256": generation_sha,
        "isolation_policy_sha256": isolation_sha,
        "scorer_sha256": scorer_sha,
        "model_surface_sha256": selected_surface_sha,
    }
    for key, expected in packaged_identities.items():
        if package_manifest.get(key) != expected:
            raise PreregistrationError(f"package identity mismatch: {key}")
    archive_sha = require_sha(args.archive_sha256, "archive_sha256")
    archive_path = args.archive.resolve()
    if not archive_path.is_file():
        raise PreregistrationError("evaluation archive missing")
    if file_sha(archive_path) != archive_sha:
        raise PreregistrationError("evaluation archive sha256 drift")
    document = {
        "v": 1,
        "format": "exactscope.grounding-benchmark-preregistration",
        "format_version": "0.4",
        "state": "frozen-before-inference",
        "run_id": args.run_id,
        "writer_id": args.writer_id,
        "planned_output": args.planned_output,
        "source_commit": args.source_commit,
        "candidate": candidate,
        "evaluation_package": {
            "package_manifest_sha256": package_manifest_sha,
            "archive_sha256": archive_sha,
        },
        "model_inventory_sha256": inventory_sha,
        "model": model,
        "runtime_record_sha256": runtime_record_sha,
        "runtime": runtime,
        "generation_config_sha256": generation_sha,
        "isolation_policy_sha256": isolation_sha,
        "scorer_sha256": scorer_sha,
        "model_surface_sha256": selected_surface_sha,
        "model_surface_policy": model_surface_policy,
        "answer_call_policy": answer_call_policy,
        "arms": ["A", "G"],
        "rewrite_calls": 0,
        "retry_count": 0,
        "hidden_repair": False,
        "manual_correction": False,
        "futility_rule": "deterministic-host-completion-serving-derived-v1",
        "duplicate_rule": "reject-(arm,item_id)",
        "drift_rule": "reject-any-bound-byte-or-config-drift",
        "model_inference_performed": False,
        "claim": "Frozen identity/configuration record only; creating or verifying this file performs zero model inference.",
    }
    return document


def verify_document(document: dict[str, Any], path: Path | None = None) -> None:
    required = {
        "v", "format", "format_version", "state", "run_id", "writer_id", "planned_output", "source_commit",
        "candidate", "evaluation_package", "model_inventory_sha256", "model", "runtime_record_sha256", "runtime",
        "generation_config_sha256", "isolation_policy_sha256", "scorer_sha256", "model_surface_sha256",
        "model_surface_policy", "answer_call_policy", "arms",
        "rewrite_calls", "retry_count", "hidden_repair", "manual_correction", "futility_rule", "duplicate_rule",
        "drift_rule", "model_inference_performed", "claim",
    }
    if set(document) != required:
        raise PreregistrationError("preregistration top-level shape drift")
    if document["format"] != "exactscope.grounding-benchmark-preregistration" or document["format_version"] != "0.4":
        raise PreregistrationError("unsupported preregistration format")
    if document["state"] != "frozen-before-inference" or document["model_inference_performed"] is not False:
        raise PreregistrationError("preregistration is not pre-inference")
    if document["arms"] != ["A", "G"] or document["rewrite_calls"] != 0:
        raise PreregistrationError("preregistration A/G contract drift")
    validate_answer_call_policy(document["answer_call_policy"])
    validate_model_surface_policy(document["model_surface_policy"])
    if document["model_surface_sha256"] != surface_sha256():
        raise PreregistrationError("preregistration model-surface identity drift")
    if document["futility_rule"] != "deterministic-host-completion-serving-derived-v1":
        raise PreregistrationError("preregistration futility rule drift")
    if document["retry_count"] != 0 or document["hidden_repair"] is not False or document["manual_correction"] is not False:
        raise PreregistrationError("preregistration repair/retry contract drift")
    if not COMMIT_RE.fullmatch(document["source_commit"]):
        raise PreregistrationError("invalid source commit")
    for key in ("model_inventory_sha256", "runtime_record_sha256", "generation_config_sha256", "isolation_policy_sha256", "scorer_sha256", "model_surface_sha256"):
        require_sha(document[key], key)
    if path is not None and path.read_bytes() != canonical_bytes(document):
        raise PreregistrationError("preregistration bytes are not canonical")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("--candidate", type=Path, required=True)
    create.add_argument("--package-manifest", type=Path, required=True)
    create.add_argument("--archive", type=Path, required=True)
    create.add_argument("--archive-sha256", required=True)
    create.add_argument("--source-commit", required=True)
    create.add_argument("--model-inventory", type=Path, required=True)
    create.add_argument("--model-id", required=True)
    model_source = create.add_mutually_exclusive_group(required=True)
    model_source.add_argument("--model-root", type=Path)
    model_source.add_argument("--model-path", type=Path)
    create.add_argument("--runtime-record", type=Path, required=True)
    create.add_argument("--runtime-executable", type=Path, required=True)
    create.add_argument("--generation-config", type=Path, required=True)
    create.add_argument("--isolation-policy", type=Path, required=True)
    create.add_argument("--scorer", type=Path, required=True)
    create.add_argument("--run-id", required=True)
    create.add_argument("--writer-id", default="single-writer-1")
    create.add_argument("--planned-output", required=True)
    create.add_argument("--output", type=Path, required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--preregistration", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "verify":
        document = load_cjson(args.preregistration)
        verify_document(document, args.preregistration)
        print(json.dumps({"status": "ok", "run_id": document["run_id"], "model_id": document["model"]["id"], "model_inference_performed": False}, sort_keys=True))
        return 0
    document = create_document(args)
    verify_document(document)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    data = canonical_bytes(document)
    args.output.write_bytes(data)
    print(json.dumps({"status": "frozen-before-inference", "run_id": document["run_id"], "model_id": document["model"]["id"], "sha256": hashlib.sha256(data).hexdigest(), "model_inference_performed": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PreregistrationError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ExactScope grounding preregistration: FAIL: {exc}")
        raise SystemExit(1) from exc
