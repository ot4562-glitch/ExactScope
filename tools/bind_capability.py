#!/usr/bin/env python3
"""Bind an experimental capability revision to an actual no-import Wasm and gold evidence."""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from compile_capability import ROOT, canonical, digest, load, source_identity, verify_bundle, write_bundle
from inspect_wasm import inspect_imports, inspect_memories, parse_sections

sys.path.insert(0, str(ROOT / "benchmarks"))
from run_benchmark import CoreBridge
from statistics_corpus import validate_rows


def bind(bundle, artifact, corpus, core, revision):
    original = verify_bundle(bundle)
    profile = load((bundle / "profile.json").read_bytes())
    if profile["bindings"]["core_revision"] != "sha256:" + source_identity():
        raise ValueError("profile source identity differs from the checked-out runtime source")
    if profile["device_budget"]["target_profile"] != "no-import-wasm":
        raise ValueError("only no-import-wasm binding is implemented")
    if type(revision) is not int or revision <= profile["profile_revision"] or revision > 0xffffffff:
        raise ValueError("bound output requires a new, greater profile revision")
    data = artifact.read_bytes()
    sections = parse_sections(data)
    imports = inspect_imports(sections)
    initial, maximum = inspect_memories(sections)
    if imports != 0 or len(data) > profile["device_budget"]["artifact_bytes_max"]:
        raise ValueError("artifact exceeds import/byte budget")
    rows = [load(line) for line in corpus.read_bytes().splitlines()]
    if not rows:
        raise ValueError("empty conformance corpus")
    selected = set(profile["runtime_surface"]["xs_eval"]["operations"])
    covered = {row["call"]["op"] for row in rows if row["call"] is not None}
    if covered != selected:
        raise ValueError("corpus operations must exactly cover selected surface")
    validate_rows(rows, CoreBridge(core))
    with tempfile.TemporaryDirectory(prefix="xs-bind-") as tmp:
        report = Path(tmp) / "conformance.json"
        subprocess.run(["node", str(ROOT / "tools/check_statistics_wasm.mjs"),
                        str(artifact.resolve()), str(corpus.resolve()), str(report)],
                       check=True, capture_output=True)
        evidence = load(report.read_bytes())
    files = {name: (bundle / name).read_bytes() for name in original["files"]}
    files["runtime.wasm"] = data
    files["statistics-conformance.json"] = canonical(evidence)
    files["benchmark-mapping.jsonl"] = corpus.read_bytes()
    profile["profile_revision"] = revision
    profile["bindings"]["artifact_sha256"] = digest(data)
    profile["evidence"].update(
        conformance_suite="statistics-conformance.json",
        conformance_sha256=digest(files["statistics-conformance.json"]),
        benchmark_mapping="benchmark-mapping.jsonl",
        benchmark_mapping_sha256=digest(files["benchmark-mapping.jsonl"]))
    files["profile.json"] = canonical(profile)
    manifest = dict(original)
    manifest.update(parent_bundle_sha256=digest((bundle / "manifest.json").read_bytes()),
                    artifact_status="artifact and gold bound; experimental, not target-qualified",
                    binder_sha256=digest(Path(__file__).read_text(encoding="utf-8").encode()),
                    artifact_measurements={"bytes": len(data), "imports": imports,
                                           "initial_memory_pages": initial, "maximum_memory_pages": maximum,
                                           "resident_bytes": None, "scratch_bytes": None},
                    conformance_core_sha256=digest(core.read_bytes()),
                    source_match="profile matches checkout; artifact behavior checked against gold, not build attestation")
    manifest["files"] = {name: digest(value) for name, value in sorted(files.items())}
    files["manifest.json"] = canonical(manifest)
    files["bundle-sha256.txt"] = (digest(files["manifest.json"]) + "\n").encode()
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("bundle", "artifact", "corpus", "core", "output"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--revision", type=int, required=True)
    args = parser.parse_args()
    write_bundle(bind(args.bundle, args.artifact, args.corpus, args.core, args.revision), args.output)
    verify_bundle(args.output)
    print("PASS artifact-bound experimental capability unit")


if __name__ == "__main__":
    main()
