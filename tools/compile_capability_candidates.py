#!/usr/bin/env python3
"""Compile two deterministic, mutually exclusive serving-surface candidates.

This is a thin build/qualification helper over the ordinary capability compiler.
It does not define a new runtime capability format and never exposes both candidates
to a model at once. The ordinary capability profile remains the serving authority.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import os
import tempfile
from pathlib import Path

from compile_capability import ROOT, canonical, compile_profile, load, verify_bundle, write_bundle

FORMAT = "exactscope.capability.candidate-set"
FORMAT_VERSION = "0.1"
VARIANTS = (
    ("semantic-only", False, 1, 0, ".semantic"),
    ("combined", True, 2, 8, ".combined"),
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def candidate_requests(source: bytes):
    request = load(source)
    if not isinstance(request, dict) or request.get("format") != "exactscope.capability.request":
        raise ValueError("candidate compilation requires an ordinary capability request")
    families = request.get("task_families")
    if not isinstance(families, list) or not families or "arithmetic-baseline" in families:
        raise ValueError("candidate compilation requires a non-baseline semantic task request")
    base_id = request.get("profile_id")
    if not isinstance(base_id, str):
        raise ValueError("capability request has no profile_id")

    candidates = []
    for label, xs_calc, visible_tools, plan_steps, suffix in VARIANTS:
        candidate = copy.deepcopy(request)
        candidate["profile_id"] = base_id + suffix
        if len(candidate["profile_id"]) > 96:
            raise ValueError("candidate profile_id exceeds capability request limit")
        candidate["xs_calc"] = xs_calc
        candidate["model_visible_tools_max"] = visible_tools
        candidate["model_budget"]["plan_steps_max"] = plan_steps
        candidates.append((label, candidate))
    return candidates


def compile_candidates(source: bytes, packc: Path):
    compiled = []
    seen_bundle_ids = set()
    for label, request in candidate_requests(source):
        request_bytes = canonical(request)
        files = compile_profile(request_bytes, packc)
        bundle_sha = files["bundle-sha256.txt"].decode("ascii").strip()
        if bundle_sha in seen_bundle_ids:
            raise ValueError("candidate surfaces compiled to duplicate bundle identities")
        seen_bundle_ids.add(bundle_sha)
        profile = load(files["profile.json"])
        compiled.append((label, request_bytes, files, profile))
    return compiled


def build_candidate_set(source: bytes, packc: Path):
    compiled = compile_candidates(source, packc)
    manifest = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "source_request_sha256": digest(canonical(load(source))),
        "compiler": "tools/compile_capability_candidates.py@0.1",
        "selection_policy": "qualification-required; deterministic ties prefer fewer model-visible tools",
        "candidates": [],
    }
    payloads = {}
    for label, request_bytes, files, profile in compiled:
        request_name = f"{label}.request.json"
        payloads[request_name] = request_bytes
        manifest["candidates"].append({
            "label": label,
            "profile_id": profile["profile_id"],
            "profile_revision": profile["profile_revision"],
            "request_file": request_name,
            "request_sha256": digest(request_bytes),
            "bundle_directory": label,
            "bundle_sha256": files["bundle-sha256.txt"].decode("ascii").strip(),
        })
    manifest_bytes = canonical(manifest)
    payloads["candidate-set.json"] = manifest_bytes
    payloads["candidate-set-sha256.txt"] = (digest(manifest_bytes) + "\n").encode("ascii")
    return payloads, compiled


def verify_candidate_set(path: Path):
    manifest_bytes = (path / "candidate-set.json").read_bytes()
    expected = digest(manifest_bytes)
    if (path / "candidate-set-sha256.txt").read_text(encoding="ascii").strip() != expected:
        raise ValueError("candidate-set manifest digest mismatch")
    manifest = load(manifest_bytes)
    if manifest.get("format") != FORMAT or manifest.get("format_version") != FORMAT_VERSION:
        raise ValueError("unsupported candidate-set format")
    candidates = manifest.get("candidates")
    if not isinstance(candidates, list) or [item.get("label") for item in candidates] != [v[0] for v in VARIANTS]:
        raise ValueError("candidate-set variants are missing or reordered")
    bundle_ids = set()
    for item in candidates:
        request_path = path / item["request_file"]
        if digest(request_path.read_bytes()) != item["request_sha256"]:
            raise ValueError(f"candidate request digest mismatch: {item['label']}")
        bundle_path = path / item["bundle_directory"]
        bundle_manifest = verify_bundle(bundle_path)
        bundle_sha = (bundle_path / "bundle-sha256.txt").read_text(encoding="ascii").strip()
        if bundle_sha != item["bundle_sha256"]:
            raise ValueError(f"candidate bundle digest mismatch: {item['label']}")
        profile = load((bundle_path / "profile.json").read_bytes())
        if (profile["profile_id"], profile["profile_revision"]) != (item["profile_id"], item["profile_revision"]):
            raise ValueError(f"candidate profile identity mismatch: {item['label']}")
        if bundle_sha in bundle_ids:
            raise ValueError("duplicate candidate bundle identity")
        bundle_ids.add(bundle_sha)
        if bundle_manifest.get("format") != "exactscope.capability.bundle":
            raise ValueError("candidate is not an ordinary capability bundle")
    return manifest


def write_candidate_set(source: bytes, packc: Path, output: Path):
    payloads, compiled = build_candidate_set(source, packc)
    if output.exists():
        verify_candidate_set(output)
        expected_files = set(payloads)
        expected_dirs = {label for label, *_ in compiled}
        if {p.name for p in output.iterdir() if p.is_file()} != expected_files:
            raise ValueError("immutable candidate-set file inventory differs")
        if {p.name for p in output.iterdir() if p.is_dir()} != expected_dirs:
            raise ValueError("immutable candidate-set directory inventory differs")
        for name, data in payloads.items():
            if (output / name).read_bytes() != data:
                raise ValueError("immutable candidate-set payload differs; use a new output")
        for label, _request, files, _profile in compiled:
            if {p.name: p.read_bytes() for p in (output / label).iterdir()} != files:
                raise ValueError("immutable candidate bundle differs; use a new output")
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".xs-candidates-") as tmp:
        stage = Path(tmp) / "candidate-set"
        stage.mkdir()
        for name, data in payloads.items():
            (stage / name).write_bytes(data)
        for label, _request, files, _profile in compiled:
            write_bundle(files, stage / label)
        stage.rename(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--packc", type=Path, default=ROOT / "target/debug" / (
        "exactscope-packc.exe" if os.name == "nt" else "exactscope-packc"))
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        verify_candidate_set(args.source)
    else:
        if args.output is None:
            parser.error("output directory required")
        write_candidate_set(args.source.read_bytes(), args.packc, args.output)
    print("PASS capability candidate set")


if __name__ == "__main__":
    main()
