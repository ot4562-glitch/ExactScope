#!/usr/bin/env python3
"""Static upgrade-compatibility check for ExactScope operation revisions.

The checker compares immutable capability metadata only. It never loads or executes
an ExactScope runtime artifact and it never transfers evidence between revisions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from compile_capability import load, verify_bundle


class RevisionCompatibilityError(Exception):
    """Raised when a candidate is not a transparent operation-compatible upgrade."""


def operation_map(catalog: dict[str, Any], label: str) -> dict[str, dict[str, Any]]:
    operations = catalog.get("operations") if isinstance(catalog, dict) else None
    if not isinstance(operations, list):
        raise RevisionCompatibilityError(f"{label} catalog has no operation array")
    mapped: dict[str, dict[str, Any]] = {}
    for operation in operations:
        if not isinstance(operation, dict):
            raise RevisionCompatibilityError(f"{label} catalog contains an invalid operation")
        key = operation.get("op")
        revision = operation.get("revision")
        if not isinstance(key, str) or not key or not isinstance(revision, int) or revision < 1:
            raise RevisionCompatibilityError(f"{label} catalog contains an invalid operation identity")
        if key in mapped:
            raise RevisionCompatibilityError(f"{label} catalog contains duplicate operation key: {key}")
        mapped[key] = operation
    return mapped


def same_revision_contract(operation: dict[str, Any]) -> dict[str, Any]:
    """Return model-visible metadata that must not drift within one operation revision."""
    return {
        "op": operation.get("op"),
        "revision": operation.get("revision"),
        "method": operation.get("method"),
        "sig": operation.get("sig"),
        "args": operation.get("args"),
        "pack_id": operation.get("pack_id"),
    }


def compare_capability_metadata(
    baseline_profile: dict[str, Any],
    baseline_catalog: dict[str, Any],
    candidate_profile: dict[str, Any],
    candidate_catalog: dict[str, Any],
    *,
    allow_revision_upgrade: bool = False,
    identical_bundle: bool = False,
) -> dict[str, Any]:
    baseline_identity = (baseline_profile.get("profile_id"), baseline_profile.get("domain"))
    candidate_identity = (candidate_profile.get("profile_id"), candidate_profile.get("domain"))
    if baseline_identity != candidate_identity or not all(isinstance(value, str) and value for value in baseline_identity):
        raise RevisionCompatibilityError("transparent upgrade requires the same capability profile id and domain")

    baseline_profile_revision = baseline_profile.get("profile_revision")
    candidate_profile_revision = candidate_profile.get("profile_revision")
    if not isinstance(baseline_profile_revision, int) or not isinstance(candidate_profile_revision, int):
        raise RevisionCompatibilityError("capability profile revision is invalid")
    if identical_bundle:
        if candidate_profile_revision != baseline_profile_revision:
            raise RevisionCompatibilityError("identical bundle identity disagrees with profile revision")
    elif candidate_profile_revision <= baseline_profile_revision:
        raise RevisionCompatibilityError("changed capability upgrade requires a strictly newer profile revision")

    baseline = operation_map(baseline_catalog, "baseline")
    candidate = operation_map(candidate_catalog, "candidate")
    removed = sorted(set(baseline) - set(candidate))
    if removed:
        raise RevisionCompatibilityError(
            "transparent upgrade removes baseline operations: " + ", ".join(removed)
        )

    upgraded: list[dict[str, Any]] = []
    unchanged: list[str] = []
    for key in sorted(baseline):
        old = baseline[key]
        new = candidate[key]
        old_revision = old["revision"]
        new_revision = new["revision"]
        if new_revision < old_revision:
            raise RevisionCompatibilityError(
                f"operation revision rollback is forbidden: {key} {old_revision}->{new_revision}"
            )
        if new_revision == old_revision:
            if same_revision_contract(old) != same_revision_contract(new):
                raise RevisionCompatibilityError(
                    f"same operation revision changed observable metadata: {key}@{old_revision}"
                )
            unchanged.append(key)
            continue
        if not allow_revision_upgrade:
            raise RevisionCompatibilityError(
                f"operation revision changed and requires explicit review: {key} {old_revision}->{new_revision}"
            )
        upgraded.append({"op": key, "from_revision": old_revision, "to_revision": new_revision})

    added = sorted(set(candidate) - set(baseline))
    return {
        "status": "COMPATIBLE",
        "profile_id": baseline_identity[0],
        "domain": baseline_identity[1],
        "baseline_profile_revision": baseline_profile_revision,
        "candidate_profile_revision": candidate_profile_revision,
        "unchanged_operations": unchanged,
        "revision_upgrades": upgraded,
        "added_operations": added,
        "evidence_inheritance": False,
    }


def compare_bundles(
    baseline_path: Path, candidate_path: Path, *, allow_revision_upgrade: bool = False
) -> dict[str, Any]:
    try:
        verify_bundle(baseline_path)
        verify_bundle(candidate_path)
        baseline_profile = load((baseline_path / "profile.json").read_bytes())
        candidate_profile = load((candidate_path / "profile.json").read_bytes())
        baseline_catalog = load((baseline_path / "catalog.json").read_bytes())
        candidate_catalog = load((candidate_path / "catalog.json").read_bytes())
        baseline_identity = (baseline_path / "bundle-sha256.txt").read_text(encoding="ascii").strip()
        candidate_identity = (candidate_path / "bundle-sha256.txt").read_text(encoding="ascii").strip()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise RevisionCompatibilityError(f"invalid capability bundle: {exc}") from exc
    return compare_capability_metadata(
        baseline_profile,
        baseline_catalog,
        candidate_profile,
        candidate_catalog,
        allow_revision_upgrade=allow_revision_upgrade,
        identical_bundle=baseline_identity == candidate_identity,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--allow-revision-upgrade", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    try:
        result = compare_bundles(
            args.baseline,
            args.candidate,
            allow_revision_upgrade=args.allow_revision_upgrade,
        )
    except RevisionCompatibilityError as exc:
        if args.json_output:
            print(json.dumps({"status": "INCOMPATIBLE", "error": str(exc)}, sort_keys=True))
        else:
            print(f"INCOMPATIBLE: {exc}")
        return 2
    if args.json_output:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            f"COMPATIBLE profile={result['profile_id']} "
            f"r{result['baseline_profile_revision']}->r{result['candidate_profile_revision']} "
            f"unchanged={len(result['unchanged_operations'])} "
            f"upgraded={len(result['revision_upgrades'])} added={len(result['added_operations'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
