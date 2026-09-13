#!/usr/bin/env python3
"""Fresh FEVER transfer driver for the ExactScope v1.1 Harness Distillation proof.

The workflow is deliberately split so held-out gold cannot participate in policy
selection:

  freeze -> run-calibration -> score-calibration -> exactscope_calibrate compile
         -> run-heldout -> score-heldout -> exactscope_calibrate qualify

The model-facing runner reads serving data only. Gold is opened only by score commands.
This first real slice exposes A/B/D plus prompt-profile selection; G/H/I/J/K remain out
of the search space and must be proven separately.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any
import unicodedata

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "tools", ROOT / "benchmarks"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from grounding_canonical import canonical_bytes, loads  # noqa: E402
from grounding_corpus import load_index, search  # noqa: E402
from grounding_projection import precision_context_evidence_projection_v5  # noqa: E402
from grounding_projection_legacy import _context_grouped_projection  # noqa: E402
from grounding_v1_surface import messages, surface_sha256  # noqa: E402
from harness_distillation import (  # noqa: E402
    CandidatePolicy,
    DistillationObjective,
    FrozenSplit,
    HostQualification,
    Observation,
    calibration_policy_ids,
    digest_json,
    load_profile,
    minimum_candidate_catalog,
)
import public_fever_benchmark as fever  # noqa: E402
import public_fever_candidate as fever_candidate  # noqa: E402
from run_grounding_benchmark import stop_server, wait_server  # noqa: E402

ADAPTER_PATH = ROOT / "adapters/llama-cpp/grounding_v1.py"
_adapter_spec = importlib.util.spec_from_file_location("exactscope_harness_llama_adapter", ADAPTER_PATH)
if _adapter_spec is None or _adapter_spec.loader is None:
    raise RuntimeError("cannot load llama.cpp grounding adapter")
adapter = importlib.util.module_from_spec(_adapter_spec)
_adapter_spec.loader.exec_module(adapter)

FORMAT_VERSION = "0.1"
FREEZE_FORMAT = "exactscope.harness-fever-freeze"
RUN_FORMAT = "exactscope.harness-fever-run"
HOST_FORMAT = "exactscope.harness-fever-host"
SELECTION_DOMAIN = "exactscope-harness-fever-transfer-v0.1\0"
RUNNER_ID = "harness-fever-abd-prompt-v0.1"
POLICY_PATH = ROOT / "grounding/reference-profile-v0.1/projection-policy.txt"
MAX_EVIDENCE_BYTES = 2048
MODEL_ITEM_CAP = 8
CONTROL_TOP_K = 4
OVERFETCH_TOP_K = 12
DEFAULT_CONTEXT = 4096


class HarnessFeverError(RuntimeError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = loads(path.read_bytes())
    if not isinstance(value, dict):
        raise HarnessFeverError(f"expected JSON object: {path}")
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("rb") as handle:
        for line in handle:
            line = line.rstrip(b"\r\n")
            if not line:
                continue
            value = loads(line)
            if not isinstance(value, dict):
                raise HarnessFeverError(f"expected JSON object row: {path}")
            rows.append(value)
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_bytes(b"".join(canonical_bytes(row) + b"\n" for row in rows))


def _fresh_key(source_id: int) -> tuple[bytes, int]:
    if type(source_id) is not int or source_id < 0:
        raise HarnessFeverError("FEVER source id must be a nonnegative integer")
    return hashlib.sha256((SELECTION_DOMAIN + str(source_id)).encode("utf-8")).digest(), source_id


def _claim_identity(claim: str) -> str:
    if not isinstance(claim, str) or not claim.strip():
        raise HarnessFeverError("FEVER claim must be nonempty text")
    normalized = " ".join(unicodedata.normalize("NFKC", claim).split()).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def select_fresh_balanced(
    rows: list[dict[str, Any]],
    *,
    excluded_source_ids: set[int],
    excluded_claim_identities: set[str] | frozenset[str] = frozenset(),
    calibration_per_label: int,
    held_out_per_label: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Select disjoint calibration/held-out rows before any new scoring occurs."""
    if type(calibration_per_label) is not int or calibration_per_label < 1:
        raise HarnessFeverError("calibration_per_label must be positive")
    if type(held_out_per_label) is not int or held_out_per_label < 1:
        raise HarnessFeverError("held_out_per_label must be positive")
    by_label: dict[str, list[dict[str, Any]]] = {label: [] for label in fever.LABELS}
    seen: set[int] = set()
    for row in rows:
        source_id = row.get("id")
        label = row.get("label")
        if type(source_id) is not int or source_id < 0 or source_id in seen:
            raise HarnessFeverError("source FEVER ids must be unique nonnegative integers")
        seen.add(source_id)
        if label not in by_label:
            raise HarnessFeverError(f"unsupported FEVER label: {label!r}")
        claim_identity = _claim_identity(row.get("claim"))
        if source_id not in excluded_source_ids and claim_identity not in excluded_claim_identities:
            by_label[label].append(row)

    calibration: list[dict[str, Any]] = []
    held_out: list[dict[str, Any]] = []
    need = calibration_per_label + held_out_per_label
    for label in fever.LABELS:
        ordered = sorted(by_label[label], key=lambda row: _fresh_key(row["id"]))
        if len(ordered) < need:
            raise HarnessFeverError(f"not enough fresh FEVER rows for {label}")
        calibration.extend(ordered[:calibration_per_label])
        held_out.extend(ordered[calibration_per_label:need])
    calibration.sort(key=lambda row: _fresh_key(row["id"]))
    held_out.sort(key=lambda row: _fresh_key(row["id"]))
    return calibration, held_out


STAGE1_GROUPING_POLICY = "exact-claim-or-overlapping-evidence-page-component-v2"
STAGE1_SAMPLING_METHOD = "seeded-sha256-rank-without-replacement-v1"
STAGE1_SAMPLING_DOMAIN = "exactscope-stage1-heldout-srs-v1\0"


def _stage1_sample_key(source_id: int, seed: int) -> tuple[bytes, int]:
    payload = f"{STAGE1_SAMPLING_DOMAIN}{seed}\0{source_id}".encode("utf-8")
    return hashlib.sha256(payload).digest(), source_id


def _stage1_group_keys(row: dict[str, Any]) -> tuple[str, ...]:
    """Return keys used to keep related FEVER claims in one Stage 1 group."""
    keys = {"claim:" + _claim_identity(row.get("claim"))}
    for group in fever_candidate.normalize_evidence_sets(row):
        for evidence in group:
            keys.add("page:" + evidence["page"])
    return tuple(sorted(keys, key=lambda value: value.encode("utf-8")))


def _stage1_group_assignments(rows: list[dict[str, Any]]) -> dict[int, str]:
    """Assign deterministic connected components under exact-claim/page overlap."""
    parent: dict[int, int] = {}
    key_owner: dict[str, int] = {}
    row_by_id: dict[int, dict[str, Any]] = {}

    def find(source_id: int) -> int:
        root = source_id
        while parent[root] != root:
            root = parent[root]
        while parent[source_id] != source_id:
            nxt = parent[source_id]
            parent[source_id] = root
            source_id = nxt
        return root

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return
        keep, merge = sorted((left_root, right_root), key=_fresh_key)
        parent[merge] = keep

    for row in sorted(rows, key=lambda value: _fresh_key(value["id"])):
        source_id = row.get("id")
        if type(source_id) is not int or source_id < 0 or source_id in row_by_id:
            raise HarnessFeverError("Stage 1 grouping requires unique nonnegative FEVER source ids")
        parent[source_id] = source_id
        row_by_id[source_id] = row
        for key in _stage1_group_keys(row):
            owner = key_owner.get(key)
            if owner is None:
                key_owner[key] = source_id
            else:
                union(source_id, owner)

    component_members: dict[int, list[int]] = {}
    for source_id in row_by_id:
        component_members.setdefault(find(source_id), []).append(source_id)

    assignments: dict[int, str] = {}
    for member_ids in component_members.values():
        all_keys = sorted(
            {key for source_id in member_ids for key in _stage1_group_keys(row_by_id[source_id])},
            key=lambda value: value.encode("utf-8"),
        )
        group_id = digest_json({"policy": STAGE1_GROUPING_POLICY, "keys": all_keys})
        for source_id in member_ids:
            assignments[source_id] = group_id
    return assignments


def _assert_stage1_group_independent(rows: list[dict[str, Any]], label: str) -> None:
    seen: dict[str, int] = {}
    for row in rows:
        source_id = row["id"]
        for key in _stage1_group_keys(row):
            previous = seen.get(key)
            if previous is not None:
                raise HarnessFeverError(
                    f"{label} contains Stage 1 grouping overlap: {previous} and {source_id} share {key!r}"
                )
            seen[key] = source_id


def select_stage1_fresh(
    rows: list[dict[str, Any]],
    *,
    excluded_source_ids: set[int],
    excluded_claim_identities: set[str] | frozenset[str] = frozenset(),
    calibration_per_label: int,
    held_out_count: int,
    held_out_seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Freeze Stage 1 balanced calibration plus SRSWOR held-out from grouped representatives."""
    if type(calibration_per_label) is not int or calibration_per_label < 1:
        raise HarnessFeverError("calibration_per_label must be positive")
    if type(held_out_count) is not int or held_out_count < 1:
        raise HarnessFeverError("held_out_count must be positive")
    if type(held_out_seed) is not int or held_out_seed < 0:
        raise HarnessFeverError("held_out_seed must be a nonnegative integer")

    seen_source_ids: set[int] = set()
    eligible_rows: list[dict[str, Any]] = []
    for row in rows:
        source_id = row.get("id")
        label = row.get("label")
        if type(source_id) is not int or source_id < 0 or source_id in seen_source_ids:
            raise HarnessFeverError("source FEVER ids must be unique nonnegative integers")
        seen_source_ids.add(source_id)
        if label not in fever.LABELS:
            raise HarnessFeverError(f"unsupported FEVER label: {label!r}")
        claim_identity = _claim_identity(row.get("claim"))
        if source_id in excluded_source_ids or claim_identity in excluded_claim_identities:
            continue
        eligible_rows.append(row)

    group_assignments = _stage1_group_assignments(eligible_rows)
    representatives: dict[str, dict[str, Any]] = {}
    for row in eligible_rows:
        source_id = row["id"]
        group_identity = group_assignments[source_id]
        current = representatives.get(group_identity)
        if current is None or _fresh_key(source_id) < _fresh_key(current["id"]):
            representatives[group_identity] = row

    by_label: dict[str, list[dict[str, Any]]] = {label: [] for label in fever.LABELS}
    for row in representatives.values():
        by_label[row["label"]].append(row)
    calibration: list[dict[str, Any]] = []
    calibration_groups: set[str] = set()
    for label in fever.LABELS:
        ordered = sorted(by_label[label], key=lambda row: _fresh_key(row["id"]))
        if len(ordered) < calibration_per_label:
            raise HarnessFeverError(f"not enough grouped fresh FEVER rows for calibration label {label}")
        selected = ordered[:calibration_per_label]
        calibration.extend(selected)
        calibration_groups.update(group_assignments[row["id"]] for row in selected)
    calibration.sort(key=lambda row: _fresh_key(row["id"]))
    _assert_stage1_group_independent(calibration, "Stage 1 calibration")

    frame = [
        row
        for group_identity, row in representatives.items()
        if group_identity not in calibration_groups
    ]
    frame.sort(key=lambda row: row["id"])
    if len(frame) < held_out_count:
        raise HarnessFeverError("not enough grouped fresh FEVER rows for Stage 1 held-out frame")
    _assert_stage1_group_independent(frame, "Stage 1 held-out frame")
    held_out = sorted(
        frame,
        key=lambda row: _stage1_sample_key(row["id"], held_out_seed),
    )[:held_out_count]
    held_out.sort(key=lambda row: row["id"])
    if calibration_groups & {group_assignments[row["id"]] for row in held_out}:
        raise HarnessFeverError("Stage 1 calibration/held-out grouping overlap")
    return calibration, held_out, frame


def _split_from_source(split_id: str, rows: list[dict[str, Any]]) -> FrozenSplit:
    item_ids = tuple(sorted((f"fever-dev:{row['id']}" for row in rows), key=lambda value: value.encode("utf-8")))
    return FrozenSplit(split_id, item_ids)


def _required_pages_for_source_rows(rows: list[dict[str, Any]]) -> set[str]:
    pages: set[str] = set()
    for row in rows:
        for group in fever_candidate.normalize_evidence_sets(row):
            for evidence in group:
                pages.add(evidence["page"])
    return pages


def _excluded_source_ids(
    candidate: Path | None, prior_freezes: list[Path] | tuple[Path, ...] = ()
) -> set[int]:
    result: set[int] = set()
    if candidate is not None:
        source_records = candidate / "gold/source-records.jsonl"
        if not source_records.is_file():
            raise HarnessFeverError("exclude candidate lacks gold/source-records.jsonl")
        for row in _load_jsonl(source_records):
            source_id = row.get("id")
            if type(source_id) is not int or source_id < 0:
                raise HarnessFeverError("exclude candidate has invalid FEVER source id")
            result.add(source_id)
    for freeze_root in prior_freezes:
        manifest = _load_json(freeze_root / "freeze-manifest.json")
        if manifest.get("format") != FREEZE_FORMAT or manifest.get("format_version") != FORMAT_VERSION:
            raise HarnessFeverError("exclude freeze identity drift")
        for field in ("calibration_source_ids", "held_out_source_ids"):
            ids = manifest.get(field)
            if not isinstance(ids, list) or any(type(source_id) is not int or source_id < 0 for source_id in ids):
                raise HarnessFeverError(f"exclude freeze has invalid {field}")
            result.update(ids)
    return result


def _excluded_claim_identities(
    candidate: Path | None, prior_freezes: list[Path] | tuple[Path, ...] = ()
) -> set[str]:
    identities: set[str] = set()
    if candidate is not None:
        source_records = candidate / "gold/source-records.jsonl"
        if not source_records.is_file():
            raise HarnessFeverError("exclude candidate lacks gold/source-records.jsonl")
        for row in _load_jsonl(source_records):
            identities.add(_claim_identity(row.get("claim")))
    for freeze_root in prior_freezes:
        manifest = _load_json(freeze_root / "freeze-manifest.json")
        if manifest.get("format") != FREEZE_FORMAT or manifest.get("format_version") != FORMAT_VERSION:
            raise HarnessFeverError("exclude freeze identity drift")
        for name in ("calibration.jsonl", "heldout.jsonl"):
            path = freeze_root / "frozen-source" / name
            if not path.is_file():
                raise HarnessFeverError(f"exclude freeze lacks frozen source: {name}")
            for row in _load_jsonl(path):
                identities.add(_claim_identity(row.get("claim")))
    return identities


def _wiki_source_identity(wiki_zip: Path, candidate: Path | None) -> tuple[str, str]:
    """Reuse a previously frozen source digest when the same FEVER source is available.

    Hashing the multi-gigabyte wiki ZIP repeatedly is pure bookkeeping cost. The existing
    FEVER serving candidate already binds the source ZIP SHA-256, so fresh transfer runs
    may reuse that recorded identity while still reading the current ZIP for the selected
    evidence pages. Without such a record, fall back to a direct full-file hash.
    """
    if candidate is None:
        return _file_sha256(wiki_zip), "direct-sha256"
    manifest = _load_json(candidate / "serving/manifest.json")
    if manifest.get("format") != "exactscope.public-fever-serving-candidate":
        raise HarnessFeverError("exclude candidate serving manifest identity drift")
    source = manifest.get("source")
    if not isinstance(source, dict) or source.get("parser_id") != fever_candidate.PARSER_ID:
        raise HarnessFeverError("exclude candidate FEVER source identity drift")
    digest = source.get("wiki_zip_sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(ch not in "0123456789abcdef" for ch in digest)
    ):
        raise HarnessFeverError("exclude candidate lacks a valid wiki ZIP SHA-256")
    if not wiki_zip.is_file():
        raise HarnessFeverError("FEVER wiki ZIP is missing")
    return digest, "exclude-candidate-serving-manifest"


def _verify_freeze_output(
    output: Path,
    *,
    paper_dev_sha256: str,
    wiki_zip_sha256: str,
    excluded_source_ids_sha256: str,
    excluded_claim_identities_sha256: str,
    calibration_per_label: int,
    held_out_per_label: int,
) -> dict[str, Any]:
    manifest_path = output / "freeze-manifest.json"
    if not manifest_path.is_file():
        raise HarnessFeverError("freeze output exists but is incomplete")
    manifest = _load_json(manifest_path)
    if manifest.get("format") != FREEZE_FORMAT or manifest.get("format_version") != FORMAT_VERSION:
        raise HarnessFeverError("freeze output identity drift")
    if manifest.get("selection_domain") != SELECTION_DOMAIN.rstrip("\0"):
        raise HarnessFeverError("freeze selection domain drift")
    manifest_calibration_per_label = manifest.get("calibration_per_label", manifest.get("per_label_per_split"))
    manifest_held_out_per_label = manifest.get("held_out_per_label", manifest.get("per_label_per_split"))
    if manifest_calibration_per_label != calibration_per_label or manifest_held_out_per_label != held_out_per_label:
        raise HarnessFeverError("freeze split size differs from requested size")
    source = manifest.get("source")
    if not isinstance(source, dict) or source.get("paper_dev_sha256") != paper_dev_sha256 or source.get("wiki_zip_sha256") != wiki_zip_sha256:
        raise HarnessFeverError("freeze source identity drift")
    if manifest.get("excluded_source_ids_sha256") != excluded_source_ids_sha256:
        raise HarnessFeverError("freeze exclusion identity drift")
    recorded_claim_digest = manifest.get("excluded_claim_identities_sha256")
    if recorded_claim_digest is not None and recorded_claim_digest != excluded_claim_identities_sha256:
        raise HarnessFeverError("freeze excluded-claim identity drift")
    calibration = FrozenSplit(**manifest["calibration_split"])
    held_out = FrozenSplit(**manifest["held_out_split"])
    if calibration.sha256() != manifest.get("calibration_split_digest") or held_out.sha256() != manifest.get("held_out_split_digest"):
        raise HarnessFeverError("freeze split digest drift")
    if set(calibration.item_ids) & set(held_out.item_ids):
        raise HarnessFeverError("freeze calibration/held-out overlap")
    for name, split in (("calibration-candidate", calibration), ("heldout-candidate", held_out)):
        _candidate_manifest, items, _candidate_rows, _corpus = fever.verify_serving_candidate(output / name)
        item_ids = tuple(sorted((item["id"] for item in items), key=lambda value: value.encode("utf-8")))
        if item_ids != split.item_ids:
            raise HarnessFeverError(f"{name} serving items differ from frozen split")
    return manifest


def _verify_stage1_freeze_output(
    output: Path,
    *,
    paper_dev_sha256: str,
    wiki_zip_sha256: str,
    excluded_source_ids_sha256: str,
    excluded_claim_identities_sha256: str,
    calibration_per_label: int,
    held_out_count: int,
    held_out_seed: int,
    held_out_seed_provenance: str,
) -> dict[str, Any]:
    manifest_path = output / "freeze-manifest.json"
    if not manifest_path.is_file():
        raise HarnessFeverError("Stage 1 freeze output exists but is incomplete")
    manifest = _load_json(manifest_path)
    if manifest.get("format") != FREEZE_FORMAT or manifest.get("format_version") != FORMAT_VERSION:
        raise HarnessFeverError("Stage 1 freeze output identity drift")
    if manifest.get("selection_mode") != "stage1-balanced-calibration+srs-heldout-v1":
        raise HarnessFeverError("Stage 1 freeze selection mode drift")
    if manifest.get("selection_domain") != SELECTION_DOMAIN.rstrip("\0"):
        raise HarnessFeverError("Stage 1 freeze selection domain drift")
    if manifest.get("calibration_per_label") != calibration_per_label:
        raise HarnessFeverError("Stage 1 calibration size differs from requested size")
    if manifest.get("held_out_count") != held_out_count or manifest.get("held_out_seed") != held_out_seed:
        raise HarnessFeverError("Stage 1 held-out sampling parameters drift")
    if manifest.get("held_out_seed_provenance") != held_out_seed_provenance:
        raise HarnessFeverError("Stage 1 held-out seed provenance drift")
    if manifest.get("grouping_policy") != STAGE1_GROUPING_POLICY:
        raise HarnessFeverError("Stage 1 grouping policy drift")
    if manifest.get("held_out_sampling_method") != STAGE1_SAMPLING_METHOD:
        raise HarnessFeverError("Stage 1 held-out sampling method drift")
    source = manifest.get("source")
    if (
        not isinstance(source, dict)
        or source.get("paper_dev_sha256") != paper_dev_sha256
        or source.get("wiki_zip_sha256") != wiki_zip_sha256
    ):
        raise HarnessFeverError("Stage 1 freeze source identity drift")
    if manifest.get("excluded_source_ids_sha256") != excluded_source_ids_sha256:
        raise HarnessFeverError("Stage 1 freeze exclusion identity drift")
    if manifest.get("excluded_claim_identities_sha256") != excluded_claim_identities_sha256:
        raise HarnessFeverError("Stage 1 freeze excluded-claim identity drift")

    calibration = FrozenSplit(**manifest["calibration_split"])
    held_out = FrozenSplit(**manifest["held_out_split"])
    if calibration.sha256() != manifest.get("calibration_split_digest"):
        raise HarnessFeverError("Stage 1 calibration split digest drift")
    if held_out.sha256() != manifest.get("held_out_split_digest"):
        raise HarnessFeverError("Stage 1 held-out split digest drift")
    if len(calibration.item_ids) != calibration_per_label * len(fever.LABELS):
        raise HarnessFeverError("Stage 1 calibration item count drift")
    if len(held_out.item_ids) != held_out_count:
        raise HarnessFeverError("Stage 1 held-out item count drift")
    if set(calibration.item_ids) & set(held_out.item_ids):
        raise HarnessFeverError("Stage 1 calibration/held-out overlap")

    source_dir = output / "frozen-source"
    calibration_rows = _load_jsonl(source_dir / "calibration.jsonl")
    held_out_rows = _load_jsonl(source_dir / "heldout.jsonl")
    frame_path = source_dir / "heldout-frame.jsonl"
    if not frame_path.is_file():
        raise HarnessFeverError("Stage 1 freeze lacks heldout-frame.jsonl")
    frame_rows = _load_jsonl(frame_path)
    if len(frame_rows) != manifest.get("held_out_frame_count"):
        raise HarnessFeverError("Stage 1 held-out frame count drift")
    if _sha256(frame_path.read_bytes()) != manifest.get("held_out_frame_sha256"):
        raise HarnessFeverError("Stage 1 held-out frame digest drift")
    frame_ids = {row["id"] for row in frame_rows}
    if not {row["id"] for row in held_out_rows}.issubset(frame_ids):
        raise HarnessFeverError("Stage 1 held-out sample is not contained in frozen frame")
    _assert_stage1_group_independent(
        calibration_rows + frame_rows,
        "Stage 1 frozen calibration/frame representatives",
    )
    _assert_stage1_group_independent(held_out_rows, "Stage 1 held-out sample")

    for name, split in (("calibration-candidate", calibration), ("heldout-candidate", held_out)):
        _candidate_manifest, items, _candidate_rows, _corpus = fever.verify_serving_candidate(output / name)
        item_ids = tuple(sorted((item["id"] for item in items), key=lambda value: value.encode("utf-8")))
        if item_ids != split.item_ids:
            raise HarnessFeverError(f"{name} serving items differ from Stage 1 frozen split")
    return manifest


def _freeze_counts(args: argparse.Namespace) -> tuple[int, int]:
    legacy = args.per_label_per_split
    explicit_calibration = args.calibration_per_label
    explicit_held_out = args.held_out_per_label
    if legacy is not None and (explicit_calibration is not None or explicit_held_out is not None):
        raise HarnessFeverError("legacy per-label split size cannot be mixed with explicit calibration/held-out sizes")
    if legacy is not None:
        return legacy, legacy
    return explicit_calibration or 2, explicit_held_out or 2


def _freeze_stage1(args: argparse.Namespace) -> None:
    if args.per_label_per_split is not None or args.held_out_per_label is not None:
        raise HarnessFeverError("Stage 1 freeze cannot use legacy/balanced held-out size arguments")
    calibration_per_label = args.calibration_per_label or 40
    held_out_count = args.held_out_count or 600
    if args.held_out_seed is None:
        raise HarnessFeverError("Stage 1 freeze requires an explicitly frozen --held-out-seed")
    held_out_seed = args.held_out_seed
    if not isinstance(args.held_out_seed_provenance, str) or not args.held_out_seed_provenance.strip():
        raise HarnessFeverError("Stage 1 freeze requires --held-out-seed-provenance recorded before sample inspection")
    held_out_seed_provenance = args.held_out_seed_provenance.strip()

    paper_sha = _file_sha256(args.paper_dev)
    wiki_sha, wiki_identity_source = _wiki_source_identity(args.wiki_zip, args.exclude_candidate)
    source_rows = fever_candidate.read_jsonl(args.paper_dev)
    excluded = _excluded_source_ids(args.exclude_candidate, args.exclude_freeze)
    excluded_claims = _excluded_claim_identities(args.exclude_candidate, args.exclude_freeze)
    excluded_digest = digest_json(sorted(excluded))
    excluded_claim_digest = digest_json(sorted(excluded_claims))
    if args.output.exists():
        manifest = _verify_stage1_freeze_output(
            args.output,
            paper_dev_sha256=paper_sha,
            wiki_zip_sha256=wiki_sha,
            excluded_source_ids_sha256=excluded_digest,
            excluded_claim_identities_sha256=excluded_claim_digest,
            calibration_per_label=calibration_per_label,
            held_out_count=held_out_count,
            held_out_seed=held_out_seed,
            held_out_seed_provenance=held_out_seed_provenance,
        )
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return

    calibration_rows, held_out_rows, frame_rows = select_stage1_fresh(
        source_rows,
        excluded_source_ids=excluded,
        excluded_claim_identities=excluded_claims,
        calibration_per_label=calibration_per_label,
        held_out_count=held_out_count,
        held_out_seed=held_out_seed,
    )
    calibration_split = _split_from_source("fever-stage1-calibration-v1", calibration_rows)
    held_out_split = _split_from_source("fever-stage1-heldout-v1", held_out_rows)
    calibration_pages = _required_pages_for_source_rows(calibration_rows)
    held_out_pages = _required_pages_for_source_rows(held_out_rows)
    required_pages = calibration_pages | held_out_pages
    if not required_pages:
        raise HarnessFeverError("Stage 1 FEVER split has no verifiable evidence pages")

    frame_bytes = b"".join(canonical_bytes(row) + b"\n" for row in frame_rows)
    manifest = {
        "format": FREEZE_FORMAT,
        "format_version": FORMAT_VERSION,
        "selection_mode": "stage1-balanced-calibration+srs-heldout-v1",
        "selection_domain": SELECTION_DOMAIN.rstrip("\0"),
        "calibration_per_label": calibration_per_label,
        "held_out_count": held_out_count,
        "held_out_seed": held_out_seed,
        "held_out_seed_provenance": held_out_seed_provenance,
        "held_out_sampling_method": STAGE1_SAMPLING_METHOD,
        "held_out_sampling_domain": STAGE1_SAMPLING_DOMAIN.rstrip("\0"),
        "grouping_policy": STAGE1_GROUPING_POLICY,
        "source": {
            "paper_dev_sha256": paper_sha,
            "wiki_zip_sha256": wiki_sha,
            "wiki_zip_sha256_source": wiki_identity_source,
            "wiki_zip_bytes": args.wiki_zip.stat().st_size,
        },
        "excluded_source_id_count": len(excluded),
        "excluded_source_ids_sha256": excluded_digest,
        "excluded_claim_identity_count": len(excluded_claims),
        "excluded_claim_identities_sha256": excluded_claim_digest,
        "claim_identity_policy": "NFKC+whitespace-collapse+casefold+sha256-v1",
        "excluded_prior_freeze_count": len(args.exclude_freeze),
        "calibration_split": calibration_split.as_dict(),
        "calibration_split_digest": calibration_split.sha256(),
        "held_out_split": held_out_split.as_dict(),
        "held_out_split_digest": held_out_split.sha256(),
        "calibration_source_ids": [row["id"] for row in calibration_rows],
        "held_out_source_ids": [row["id"] for row in held_out_rows],
        "held_out_frame_count": len(frame_rows),
        "held_out_frame_sha256": _sha256(frame_bytes),
        "held_out_realized_label_counts": dict(sorted(Counter(row["label"] for row in held_out_rows).items())),
        "calibration_required_page_count": len(calibration_pages),
        "held_out_required_page_count": len(held_out_pages),
        "union_required_page_count": len(required_pages),
        "wiki_scan_count": 1,
        "gold_visible_to_model_runner": False,
        "development_disclosure": "oracle-page-pooled FEVER Stage 1 research; not release qualification",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent, prefix=".xs-harness-fever-stage1-freeze-") as tmp:
        stage = Path(tmp) / "freeze"
        stage.mkdir()
        source_dir = stage / "frozen-source"
        source_dir.mkdir()
        calibration_source = source_dir / "calibration.jsonl"
        held_out_source = source_dir / "heldout.jsonl"
        frame_source = source_dir / "heldout-frame.jsonl"
        _write_jsonl(calibration_source, calibration_rows)
        _write_jsonl(held_out_source, held_out_rows)
        frame_source.write_bytes(frame_bytes)
        shared_page_rows = fever_candidate.scan_required_pages(args.wiki_zip, required_pages)
        fever_candidate.build_candidate(
            calibration_source,
            args.wiki_zip,
            stage / "calibration-candidate",
            preserve_input_selection=True,
            wiki_zip_sha256=wiki_sha,
            preloaded_page_rows=shared_page_rows,
        )
        fever_candidate.build_candidate(
            held_out_source,
            args.wiki_zip,
            stage / "heldout-candidate",
            preserve_input_selection=True,
            wiki_zip_sha256=wiki_sha,
            preloaded_page_rows=shared_page_rows,
        )
        (stage / "freeze-manifest.json").write_bytes(canonical_bytes(manifest))
        _verify_stage1_freeze_output(
            stage,
            paper_dev_sha256=paper_sha,
            wiki_zip_sha256=wiki_sha,
            excluded_source_ids_sha256=excluded_digest,
            excluded_claim_identities_sha256=excluded_claim_digest,
            calibration_per_label=calibration_per_label,
            held_out_count=held_out_count,
            held_out_seed=held_out_seed,
            held_out_seed_provenance=held_out_seed_provenance,
        )
        stage.rename(args.output)
    print(json.dumps(manifest, indent=2, sort_keys=True))


def freeze(args: argparse.Namespace) -> None:
    if getattr(args, "stage1", False):
        _freeze_stage1(args)
        return
    if args.held_out_count is not None or args.held_out_seed is not None:
        raise HarnessFeverError("held-out count/seed require --stage1")
    calibration_per_label, held_out_per_label = _freeze_counts(args)
    paper_sha = _file_sha256(args.paper_dev)
    wiki_sha, wiki_identity_source = _wiki_source_identity(args.wiki_zip, args.exclude_candidate)
    source_rows = fever_candidate.read_jsonl(args.paper_dev)
    excluded = _excluded_source_ids(args.exclude_candidate, args.exclude_freeze)
    excluded_claims = _excluded_claim_identities(args.exclude_candidate, args.exclude_freeze)
    excluded_digest = digest_json(sorted(excluded))
    excluded_claim_digest = digest_json(sorted(excluded_claims))
    if args.output.exists():
        manifest = _verify_freeze_output(
            args.output,
            paper_dev_sha256=paper_sha,
            wiki_zip_sha256=wiki_sha,
            excluded_source_ids_sha256=excluded_digest,
            excluded_claim_identities_sha256=excluded_claim_digest,
            calibration_per_label=calibration_per_label,
            held_out_per_label=held_out_per_label,
        )
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return

    calibration_rows, held_out_rows = select_fresh_balanced(
        source_rows,
        excluded_source_ids=excluded,
        excluded_claim_identities=excluded_claims,
        calibration_per_label=calibration_per_label,
        held_out_per_label=held_out_per_label,
    )
    calibration_split = _split_from_source("fever-fresh-calibration-v0.1", calibration_rows)
    held_out_split = _split_from_source("fever-fresh-heldout-v0.1", held_out_rows)
    if set(calibration_split.item_ids) & set(held_out_split.item_ids):
        raise HarnessFeverError("fresh calibration/held-out selection overlapped")
    calibration_pages = _required_pages_for_source_rows(calibration_rows)
    held_out_pages = _required_pages_for_source_rows(held_out_rows)
    required_pages = calibration_pages | held_out_pages
    if not required_pages:
        raise HarnessFeverError("fresh FEVER split has no verifiable evidence pages")

    manifest = {
        "format": FREEZE_FORMAT,
        "format_version": FORMAT_VERSION,
        "selection_domain": SELECTION_DOMAIN.rstrip("\0"),
        "calibration_per_label": calibration_per_label,
        "held_out_per_label": held_out_per_label,
        "source": {
            "paper_dev_sha256": paper_sha,
            "wiki_zip_sha256": wiki_sha,
            "wiki_zip_sha256_source": wiki_identity_source,
            "wiki_zip_bytes": args.wiki_zip.stat().st_size,
        },
        "excluded_source_id_count": len(excluded),
        "excluded_source_ids_sha256": excluded_digest,
        "excluded_claim_identity_count": len(excluded_claims),
        "excluded_claim_identities_sha256": excluded_claim_digest,
        "claim_identity_policy": "NFKC+whitespace-collapse+casefold+sha256-v1",
        "excluded_prior_freeze_count": len(args.exclude_freeze),
        "calibration_split": calibration_split.as_dict(),
        "calibration_split_digest": calibration_split.sha256(),
        "held_out_split": held_out_split.as_dict(),
        "held_out_split_digest": held_out_split.sha256(),
        "calibration_source_ids": [row["id"] for row in calibration_rows],
        "held_out_source_ids": [row["id"] for row in held_out_rows],
        "calibration_required_page_count": len(calibration_pages),
        "held_out_required_page_count": len(held_out_pages),
        "union_required_page_count": len(required_pages),
        "wiki_scan_count": 1,
        "gold_visible_to_model_runner": False,
        "development_disclosure": "oracle-page-pooled FEVER corpus; fresh transfer research, not release qualification",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent, prefix=".xs-harness-fever-freeze-") as tmp:
        stage = Path(tmp) / "freeze"
        stage.mkdir()
        source_dir = stage / "frozen-source"
        source_dir.mkdir()
        calibration_source = source_dir / "calibration.jsonl"
        held_out_source = source_dir / "heldout.jsonl"
        _write_jsonl(calibration_source, calibration_rows)
        _write_jsonl(held_out_source, held_out_rows)
        shared_page_rows = fever_candidate.scan_required_pages(args.wiki_zip, required_pages)
        fever_candidate.build_candidate(
            calibration_source,
            args.wiki_zip,
            stage / "calibration-candidate",
            per_label=calibration_per_label,
            wiki_zip_sha256=wiki_sha,
            preloaded_page_rows=shared_page_rows,
        )
        fever_candidate.build_candidate(
            held_out_source,
            args.wiki_zip,
            stage / "heldout-candidate",
            per_label=held_out_per_label,
            wiki_zip_sha256=wiki_sha,
            preloaded_page_rows=shared_page_rows,
        )
        (stage / "freeze-manifest.json").write_bytes(canonical_bytes(manifest))
        _verify_freeze_output(
            stage,
            paper_dev_sha256=paper_sha,
            wiki_zip_sha256=wiki_sha,
            excluded_source_ids_sha256=excluded_digest,
            excluded_claim_identities_sha256=excluded_claim_digest,
            calibration_per_label=calibration_per_label,
            held_out_per_label=held_out_per_label,
        )
        stage.rename(args.output)
    print(json.dumps(manifest, indent=2, sort_keys=True))


# -- host / candidate execution -------------------------------------------------


def _minimal_host(host_profile_digest: str) -> HostQualification:
    return HostQualification(
        host_profile_digest=host_profile_digest,
        context_fit_qualification_digest=None,
        typed_contract_supported=False,
        native_constraint_surface_id=None,
        gxh_qualification_digest=None,
        zero_call_proof_supported=False,
        prefix_cache_mode="off",
        prefix_cache_parity_digest=None,
    )


def _server_command(runtime: Path, model: Path, port: int, threads: int) -> list[str]:
    return [
        str(runtime), "-m", str(model), "--alias", "exactscope-harness-model",
        "--host", "127.0.0.1", "--port", str(port), "-c", str(DEFAULT_CONTEXT),
        "-t", str(threads), "--parallel", "1", "--jinja", "--no-webui", "--offline",
        "--no-mmproj", "--reasoning", "off", "--no-cache-prompt",
    ]


def _host_record(
    *,
    model_path: Path,
    runtime_path: Path,
    model_key: str,
    contract_record: dict[str, Any],
    threads: int,
) -> dict[str, Any]:
    identity = {
        "runner_id": RUNNER_ID,
        "model_key": model_key,
        "model_sha256": _file_sha256(model_path),
        "model_bytes": model_path.stat().st_size,
        "runtime_sha256": _file_sha256(runtime_path),
        "model_surface_sha256": surface_sha256(),
        "projection_policy_sha256": _file_sha256(POLICY_PATH),
        "contract_record_sha256": digest_json(contract_record),
        "context_tokens": DEFAULT_CONTEXT,
        "threads": threads,
        "cache_prompt": False,
        "max_evidence_bytes": MAX_EVIDENCE_BYTES,
        "model_item_cap": MODEL_ITEM_CAP,
        "control_top_k": CONTROL_TOP_K,
        "overfetch_top_k": OVERFETCH_TOP_K,
        "fixed_application_answer_choices": list(fever.LABELS),
        "searchable_materials": ["A", "B", "D", "prompt-profile"],
    }
    host = _minimal_host(digest_json(identity))
    return {
        "format": HOST_FORMAT,
        "format_version": FORMAT_VERSION,
        "identity": identity,
        "host_qualification": host.as_dict(),
        "host_qualification_digest": host.sha256(),
        "contract_record": contract_record,
    }


def _validate_reused_host_record(
    record: dict[str, Any], *, model_path: Path, runtime_path: Path, model_key: str, threads: int
) -> HostQualification:
    if record.get("format") != HOST_FORMAT or record.get("format_version") != FORMAT_VERSION:
        raise HarnessFeverError("unsupported host record identity")
    identity = record.get("identity")
    if not isinstance(identity, dict):
        raise HarnessFeverError("host record lacks identity")
    expected = {
        "model_key": model_key,
        "model_sha256": _file_sha256(model_path),
        "model_bytes": model_path.stat().st_size,
        "runtime_sha256": _file_sha256(runtime_path),
        "threads": threads,
    }
    for key, value in expected.items():
        if identity.get(key) != value:
            raise HarnessFeverError(f"held-out host identity drift: {key}")
    try:
        host = HostQualification(**record["host_qualification"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HarnessFeverError("invalid host qualification record") from exc
    if host.sha256() != record.get("host_qualification_digest"):
        raise HarnessFeverError("host qualification digest drift")
    return host


def _policy_flags(policy: CandidatePolicy) -> tuple[bool, bool, bool]:
    if policy.model_bundle != "plain" or policy.cost_bundle != "generation":
        raise HarnessFeverError(f"first FEVER runner cannot execute policy {policy.policy_id}")
    tokens = set(policy.evidence_bundle.split("+"))
    if not tokens <= {"Base", "A", "B", "D"}:
        raise HarnessFeverError(f"unsupported FEVER evidence bundle: {policy.evidence_bundle}")
    return "A" in tokens, "B" in tokens, "D" in tokens


def _project(
    index: dict[str, Any], hits: list[dict[str, Any]], retrieval_query: str, use_d: bool
) -> tuple[bytes | None, list[dict[str, Any]], str]:
    if use_d:
        evidence, emitted, meta = precision_context_evidence_projection_v5(
            index,
            hits,
            retrieval_query,
            max_bytes=MAX_EVIDENCE_BYTES,
            max_items=MODEL_ITEM_CAP,
        )
        return evidence, emitted, str(meta["projection_id"])
    evidence, emitted, _redundant = _context_grouped_projection(
        index,
        hits,
        retrieval_query,
        max_bytes=MAX_EVIDENCE_BYTES,
        max_items=MODEL_ITEM_CAP,
        suppress_redundant_spans=False,
    )
    return evidence, emitted, "context-v3-cap8-control"


def _policy_order(item_id: str, policy_ids: list[str]) -> list[str]:
    return sorted(
        policy_ids,
        key=lambda policy_id: hashlib.sha256(f"{item_id}\0{policy_id}".encode("utf-8")).digest(),
    )


def _load_compile_bundle(compile_bundle: Path) -> tuple[HostQualification, tuple[CandidatePolicy, ...], dict[str, Any], Any]:
    context = _load_json(compile_bundle / "compile-context.json")
    try:
        host = HostQualification(**context["host_qualification"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HarnessFeverError("compile bundle has invalid host qualification") from exc
    reduced = context.get("reduced_prompt_profile")
    if reduced != "no-policy":
        raise HarnessFeverError("first FEVER runner supports only no-policy reduction")
    candidates = minimum_candidate_catalog(host, reduced)
    expected_catalog = digest_json([candidate.as_dict() for candidate in candidates])
    if context.get("candidate_catalog_digest") != expected_catalog:
        raise HarnessFeverError("compile bundle candidate catalog drift")
    profile = load_profile(
        (compile_bundle / "candidate-profile.json").read_bytes(),
        host_profile_digest=host.host_profile_digest,
    )
    if profile.host_qualification_digest != host.sha256():
        raise HarnessFeverError("compiled profile host qualification drift")
    return host, candidates, context, profile


def _run_records(
    *,
    candidate: Path,
    host_record: dict[str, Any],
    policy_ids: list[str],
    candidates: tuple[CandidatePolicy, ...],
    base_url: str,
) -> list[dict[str, Any]]:
    _manifest, items, _candidate_rows, corpus = fever.verify_serving_candidate(candidate)
    by_id = {policy.policy_id: policy for policy in candidates}
    policy_bytes = POLICY_PATH.read_bytes()
    contract_record = host_record["contract_record"]
    contract = contract_record["selected_contract"]
    surface = contract_record["selected_output_surface"]
    records: list[dict[str, Any]] = []
    for item in items:
        item_id = item["id"]
        model_instruction = fever.question_text(item["claim"])
        for policy_id in _policy_order(item_id, policy_ids):
            policy = by_id.get(policy_id)
            if policy is None:
                raise HarnessFeverError(f"run requested unknown policy: {policy_id}")
            use_a, use_b, use_d = _policy_flags(policy)
            retrieval_query = fever.retrieval_query_text(item["claim"]) if use_a else model_instruction
            top_k = OVERFETCH_TOP_K if use_b else CONTROL_TOP_K
            prep_started = time.perf_counter()
            hits = search(corpus, retrieval_query, top_k=top_k)
            evidence, emitted, projection_id = _project(corpus, hits, retrieval_query, use_d)
            request_messages = messages(
                contract,
                model_instruction,
                evidence=evidence,
                policy=policy_bytes if policy.prompt_profile == "full" else None,
                answer_choices=fever.LABELS,
            )
            exactscope_cpu_ms = int(round((time.perf_counter() - prep_started) * 1000.0))
            request_started = time.perf_counter()
            result = adapter.request_answer(
                base_url,
                "exactscope-harness-model",
                contract,
                request_messages,
                output_surface=surface,
                answer_choices=fever.LABELS,
                timeout_seconds=90,
                max_tokens=32,
            )
            e2e_latency_ms = exactscope_cpu_ms + int(round((time.perf_counter() - request_started) * 1000.0))
            prompt_tokens = result.get("prompt_tokens")
            completion_tokens = result.get("completion_tokens")
            if type(prompt_tokens) is not int or prompt_tokens < 0 or type(completion_tokens) is not int or completion_tokens < 0:
                raise HarnessFeverError("llama.cpp usage accounting missing")
            records.append({
                "item_id": item_id,
                "policy_id": policy_id,
                "valid": bool(result["valid"]),
                "value": result["value"] if result["valid"] else None,
                "raw_content": result["raw_content"],
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "e2e_latency_ms": e2e_latency_ms,
                "exactscope_cpu_ms": exactscope_cpu_ms,
                "evidence_bytes": len(evidence or b""),
                "evidence_sha256": _sha256(evidence or b""),
                "emitted_ids": [hit["id"] for hit in emitted],
                "retrieval_query": retrieval_query,
                "top_k": top_k,
                "projection_id": projection_id,
                "prompt_profile": policy.prompt_profile,
                "model_calls": 1,
            })
    return records


@contextmanager
def _exclusive_run_lock(output: Path):
    """Prevent duplicate calibration/held-out execution for the same output identity.

    The lock is intentionally fail-closed. A crashed process may leave a stale lock;
    the operator must then choose a new run identity or inspect/remove the stale lock
    explicitly. Silent stale-lock recovery would risk concurrent model execution.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    lock_path = output.with_name(output.name + ".lock")
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise HarnessFeverError(f"run output is already locked: {lock_path}") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"pid": os.getpid(), "output": str(output)}, sort_keys=True) + "\n")
        yield lock_path
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _write_run(output: Path, manifest: dict[str, Any], host_record: dict[str, Any], records: list[dict[str, Any]]) -> None:
    if output.exists():
        raise HarnessFeverError("run output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = b"".join(canonical_bytes(record) + b"\n" for record in records)
    manifest = dict(manifest)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".xs-harness-fever-run-") as tmp:
        stage = Path(tmp) / "run"
        stage.mkdir()
        host_path = stage / "host-record.json"
        host_path.write_bytes(canonical_bytes(host_record))
        (stage / "raw-results.jsonl").write_bytes(raw)
        manifest["host_record_sha256"] = _file_sha256(host_path)
        manifest["raw_results_sha256"] = _sha256(raw)
        manifest["record_count"] = len(records)
        (stage / "run-manifest.json").write_bytes(canonical_bytes(manifest))
        stage.rename(output)


def _reject_legacy_runner_for_stage1(freeze_manifest: dict[str, Any], command: str) -> None:
    if freeze_manifest.get("selection_mode") == "stage1-balanced-calibration+srs-heldout-v1":
        raise HarnessFeverError(
            f"{command} is the historical runner and is disabled for the current Stage 1 freeze; "
            "use a Stage 1 runner that binds preregistered B/F/P/T roles, serving cost, timing, and analysis identities"
        )


def _run_calibration_locked(args: argparse.Namespace) -> None:
    freeze_manifest = _load_json(args.freeze / "freeze-manifest.json")
    _reject_legacy_runner_for_stage1(freeze_manifest, "run-calibration")
    candidate = args.freeze / "calibration-candidate"
    _manifest, items, _candidate_rows, _corpus = fever.verify_serving_candidate(candidate)
    split = FrozenSplit(**freeze_manifest["calibration_split"])
    if tuple(sorted((item["id"] for item in items), key=lambda value: value.encode("utf-8"))) != split.item_ids:
        raise HarnessFeverError("calibration serving items differ from frozen split")
    if not args.model_path.is_file() or not args.runtime_executable.is_file():
        raise HarnessFeverError("model/runtime executable missing")

    server_log_path = args.output.with_suffix(".llama-server.log")
    server_log_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    runtime_dir = str(args.runtime_executable.resolve().parent)
    env["LD_LIBRARY_PATH"] = runtime_dir + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    process: subprocess.Popen[bytes] | None = None
    with server_log_path.open("wb") as server_log:
        process = subprocess.Popen(
            _server_command(args.runtime_executable, args.model_path, args.port, args.threads),
            cwd=runtime_dir,
            stdout=server_log,
            stderr=subprocess.STDOUT,
            env=env,
        )
        try:
            wait_server(process, "127.0.0.1", args.port, 180)
            base_url = f"http://127.0.0.1:{args.port}/v1"
            contract_record = adapter.calibrate_contract(
                base_url=base_url,
                model="exactscope-harness-model",
                model_key=args.model_key,
                policy=POLICY_PATH.read_bytes(),
                timeout_seconds=90,
            )
            host_record = _host_record(
                model_path=args.model_path,
                runtime_path=args.runtime_executable,
                model_key=args.model_key,
                contract_record=contract_record,
                threads=args.threads,
            )
            host = HostQualification(**host_record["host_qualification"])
            candidates = minimum_candidate_catalog(host)
            policy_ids = list(calibration_policy_ids(candidates))
            records = _run_records(
                candidate=candidate,
                host_record=host_record,
                policy_ids=policy_ids,
                candidates=candidates,
                base_url=base_url,
            )
        finally:
            if process is not None:
                stop_server(process)
    _write_run(
        args.output,
        {
            "format": RUN_FORMAT,
            "format_version": FORMAT_VERSION,
            "stage": "calibration",
            "runner_id": RUNNER_ID,
            "split_digest": split.sha256(),
            "policy_ids": policy_ids,
            "gold_visible_to_model_runner": False,
            "server_log": str(server_log_path),
        },
        host_record,
        records,
    )
    print(f"PASS FEVER harness calibration run policies={len(policy_ids)} records={len(records)}")


def run_calibration(args: argparse.Namespace) -> None:
    with _exclusive_run_lock(args.output):
        _run_calibration_locked(args)


def _run_heldout_locked(args: argparse.Namespace) -> None:
    freeze_manifest = _load_json(args.freeze / "freeze-manifest.json")
    _reject_legacy_runner_for_stage1(freeze_manifest, "run-heldout")
    candidate = args.freeze / "heldout-candidate"
    _manifest, items, _candidate_rows, _corpus = fever.verify_serving_candidate(candidate)
    split = FrozenSplit(**freeze_manifest["held_out_split"])
    if tuple(sorted((item["id"] for item in items), key=lambda value: value.encode("utf-8"))) != split.item_ids:
        raise HarnessFeverError("held-out serving items differ from frozen split")
    calibration_host_record = _load_json(args.calibration_run / "host-record.json")
    reused_host = _validate_reused_host_record(
        calibration_host_record,
        model_path=args.model_path,
        runtime_path=args.runtime_executable,
        model_key=args.model_key,
        threads=args.threads,
    )
    compiled_host, candidates, context, profile = _load_compile_bundle(args.compile_bundle)
    if reused_host.as_dict() != compiled_host.as_dict():
        raise HarnessFeverError("compiled and calibration host qualification differ")
    policy_ids = list(dict.fromkeys((
        context["baseline_policy_id"],
        context["fixed_max_policy_id"],
        profile.selected_policy.policy_id,
    )))

    server_log_path = args.output.with_suffix(".llama-server.log")
    server_log_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    runtime_dir = str(args.runtime_executable.resolve().parent)
    env["LD_LIBRARY_PATH"] = runtime_dir + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    process: subprocess.Popen[bytes] | None = None
    with server_log_path.open("wb") as server_log:
        process = subprocess.Popen(
            _server_command(args.runtime_executable, args.model_path, args.port, args.threads),
            cwd=runtime_dir,
            stdout=server_log,
            stderr=subprocess.STDOUT,
            env=env,
        )
        try:
            wait_server(process, "127.0.0.1", args.port, 180)
            base_url = f"http://127.0.0.1:{args.port}/v1"
            records = _run_records(
                candidate=candidate,
                host_record=calibration_host_record,
                policy_ids=policy_ids,
                candidates=candidates,
                base_url=base_url,
            )
        finally:
            if process is not None:
                stop_server(process)
    _write_run(
        args.output,
        {
            "format": RUN_FORMAT,
            "format_version": FORMAT_VERSION,
            "stage": "heldout",
            "runner_id": RUNNER_ID,
            "split_digest": split.sha256(),
            "policy_ids": policy_ids,
            "profile_digest": profile.sha256(),
            "profile_reselected_on_held_out": False,
            "gold_visible_to_model_runner": False,
            "server_log": str(server_log_path),
        },
        calibration_host_record,
        records,
    )
    print(f"PASS FEVER harness held-out run policies={len(policy_ids)} records={len(records)}")


def run_heldout(args: argparse.Namespace) -> None:
    with _exclusive_run_lock(args.output):
        _run_heldout_locked(args)


# -- gold-only scoring ----------------------------------------------------------


def _observations_from_run(candidate: Path, run: Path) -> tuple[HostQualification, list[Observation]]:
    manifest = _load_json(run / "run-manifest.json")
    raw_path = run / "raw-results.jsonl"
    if _file_sha256(raw_path) != manifest.get("raw_results_sha256"):
        raise HarnessFeverError("run raw-results digest drift")
    host_record = _load_json(run / "host-record.json")
    host = HostQualification(**host_record["host_qualification"])
    gold_rows = _load_jsonl(candidate / "gold/items.jsonl")
    gold = {row["id"]: row for row in gold_rows}
    records = _load_jsonl(raw_path)
    observations: list[Observation] = []
    for record in records:
        item_id = record["item_id"]
        if item_id not in gold:
            raise HarnessFeverError("run item absent from gold split")
        normalized = fever.normalize_label(record.get("value")) if record.get("valid") else None
        success = normalized == gold[item_id]["label"]
        false_grounding = normalized is not None and not success
        observations.append(Observation(
            item_id=item_id,
            policy_id=record["policy_id"],
            task_success=success,
            false_grounding=false_grounding,
            unsupported_answer=False,
            strict_format_failure=not bool(record.get("valid")),
            model_calls=1,
            prompt_tokens=int(record["prompt_tokens"]),
            completion_tokens=int(record["completion_tokens"]),
            e2e_latency_ms=int(record["e2e_latency_ms"]),
            exactscope_cpu_ms=int(record["exactscope_cpu_ms"]),
            peak_ram_bytes=0,
            distribution_bytes=0,
            integration_cost_units=0,
            output_identity=_sha256(str(record.get("raw_content", "")).encode("utf-8")),
        ))
    return host, observations


def score_calibration(args: argparse.Namespace) -> None:
    freeze_manifest = _load_json(args.freeze / "freeze-manifest.json")
    _reject_legacy_runner_for_stage1(freeze_manifest, "score-calibration")
    split = FrozenSplit(**freeze_manifest["calibration_split"])
    held_out = FrozenSplit(**freeze_manifest["held_out_split"])
    host, observations = _observations_from_run(args.freeze / "calibration-candidate", args.run)
    run_manifest = _load_json(args.run / "run-manifest.json")
    if run_manifest.get("stage") != "calibration" or run_manifest.get("split_digest") != split.sha256():
        raise HarnessFeverError("calibration run/split identity drift")
    request = {
        "format": "exactscope.harness-calibration-request",
        "format_version": FORMAT_VERSION,
        "host_qualification": host.as_dict(),
        "calibration_split": split.as_dict(),
        "held_out_split": held_out.as_dict(),
        "objective": DistillationObjective().as_dict(),
        "reduced_prompt_profile": "no-policy",
        "baseline_policy_id": "Base",
        "fixed_max_policy_id": "integrated",
        "observations": [asdict(row) for row in observations],
    }
    args.output.write_bytes(canonical_bytes(request))
    print(f"PASS FEVER harness calibration score observations={len(observations)}")


def score_heldout(args: argparse.Namespace) -> None:
    freeze_manifest = _load_json(args.freeze / "freeze-manifest.json")
    _reject_legacy_runner_for_stage1(freeze_manifest, "score-heldout")
    split = FrozenSplit(**freeze_manifest["held_out_split"])
    _host, observations = _observations_from_run(args.freeze / "heldout-candidate", args.run)
    run_manifest = _load_json(args.run / "run-manifest.json")
    if run_manifest.get("stage") != "heldout" or run_manifest.get("split_digest") != split.sha256():
        raise HarnessFeverError("held-out run/split identity drift")
    request = {
        "format": "exactscope.harness-heldout-request",
        "format_version": FORMAT_VERSION,
        "held_out_split": split.as_dict(),
        "observations": [asdict(row) for row in observations],
    }
    args.output.write_bytes(canonical_bytes(request))
    print(f"PASS FEVER harness held-out score observations={len(observations)}")


def _run_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--runtime-executable", type=Path, required=True)
    parser.add_argument("--model-key", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--output", type=Path, required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("freeze")
    p.add_argument("--paper-dev", type=Path, required=True)
    p.add_argument("--wiki-zip", type=Path, required=True)
    p.add_argument("--exclude-candidate", type=Path)
    p.add_argument("--exclude-freeze", type=Path, action="append", default=[])
    p.add_argument(
        "--stage1",
        action="store_true",
        help="Freeze the current Stage 1 design: balanced calibration plus finite-frame SRS held-out.",
    )
    p.add_argument("--per-label-per-split", type=int)
    p.add_argument("--calibration-per-label", type=int)
    p.add_argument("--held-out-per-label", type=int)
    p.add_argument("--held-out-count", type=int)
    p.add_argument("--held-out-seed", type=int)
    p.add_argument(
        "--held-out-seed-provenance",
        help="Required with --stage1; record how the seed was generated before inspecting the sampled held-out set.",
    )
    p.add_argument("--output", type=Path, required=True)

    p = sub.add_parser("run-calibration")
    _run_args(p)

    p = sub.add_parser("score-calibration")
    p.add_argument("--freeze", type=Path, required=True)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)

    p = sub.add_parser("run-heldout")
    _run_args(p)
    p.add_argument("--compile-bundle", type=Path, required=True)
    p.add_argument("--calibration-run", type=Path, required=True)

    p = sub.add_parser("score-heldout")
    p.add_argument("--freeze", type=Path, required=True)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "freeze":
            freeze(args)
        elif args.command == "run-calibration":
            run_calibration(args)
        elif args.command == "score-calibration":
            score_calibration(args)
        elif args.command == "run-heldout":
            run_heldout(args)
        else:
            score_heldout(args)
        return 0
    except (HarnessFeverError, OSError, ValueError, adapter.AdapterError, fever.FeverBenchmarkError, fever_candidate.FeverCandidateError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
