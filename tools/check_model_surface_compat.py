#!/usr/bin/env python3
"""Fail-closed host compatibility check for an ExactScope model-surface contract.

This tool inspects files and digests only. It never instantiates or executes the
ExactScope runtime artifact.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from compile_capability import ROOT, load, verify_bundle

CONTRACT_SCHEMA = ROOT / "spec/schemas/model-surface-contract.schema.json"
POLICY_SCHEMA = ROOT / "spec/schemas/model-surface-acceptance.schema.json"
DEFAULT_POLICY = ROOT / "spec/examples/model-surface-acceptance-v0.1.json"


class CompatibilityError(Exception):
    """Raised when a bundle surface cannot be accepted deterministically."""


def validate_document(document, schema_path: Path, label: str) -> None:
    schema = load(schema_path.read_bytes())
    errors = sorted(
        Draft202012Validator(schema).iter_errors(document),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path) or "<root>"
        raise CompatibilityError(f"{label}:{location}: {first.message}")


def check_acceptance(contract: dict, policy: dict) -> dict:
    validate_document(contract, CONTRACT_SCHEMA, "surface-contract")
    validate_document(policy, POLICY_SCHEMA, "acceptance-policy")
    if contract["negotiation"] != "exact-version-and-digest":
        raise CompatibilityError("host accepts only exact-version-and-digest negotiation")
    if contract["abi_revision"] not in policy["accepted_abi_revisions"]:
        raise CompatibilityError(f"ABI revision is not accepted: {contract['abi_revision']}")
    hotset_version = contract["hotset"]["format_version"]
    if hotset_version not in policy["accepted_hotset_format_versions"]:
        raise CompatibilityError(f"hot-set format version is not accepted: {hotset_version}")

    accepted = policy["accepted_asset_contracts"]
    seen: set[str] = set()
    for asset in contract["assets"]:
        contract_id = asset["contract_id"]
        version = asset["contract_version"]
        if contract_id in seen:
            raise CompatibilityError(f"duplicate model-surface contract id: {contract_id}")
        seen.add(contract_id)
        versions = accepted.get(contract_id)
        if not isinstance(versions, list) or version not in versions:
            raise CompatibilityError(f"model-surface contract is not accepted: {contract_id}@{version}")
    return {
        "status": "COMPATIBLE",
        "profile": contract["profile"],
        "abi_revision": contract["abi_revision"],
        "hotset_format_version": hotset_version,
        "asset_contracts": [f"{asset['contract_id']}@{asset['contract_version']}" for asset in contract["assets"]],
        "negotiation": contract["negotiation"],
    }


def inspect_bundle(bundle: Path, policy_path: Path) -> dict:
    try:
        verify_bundle(bundle)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise CompatibilityError(f"bundle integrity check failed: {exc}") from exc
    contract_path = bundle / "surface-contract.json"
    if not contract_path.is_file():
        raise CompatibilityError(
            "bundle predates explicit model-surface negotiation; regenerate as a new immutable revision"
        )
    try:
        contract = load(contract_path.read_bytes())
        policy = load(policy_path.read_bytes())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise CompatibilityError(f"cannot load model-surface contract/policy: {exc}") from exc
    return check_acceptance(contract, policy)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="extracted immutable capability bundle")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    try:
        result = inspect_bundle(args.bundle, args.policy)
    except CompatibilityError as exc:
        if args.json_output:
            print(json.dumps({"status": "INCOMPATIBLE", "error": str(exc)}, sort_keys=True))
        else:
            print(f"INCOMPATIBLE: {exc}")
        return 2
    if args.json_output:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            f"COMPATIBLE profile={result['profile']['id']}@{result['profile']['revision']} "
            f"abi={result['abi_revision']} assets={len(result['asset_contracts'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
