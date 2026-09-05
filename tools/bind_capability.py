#!/usr/bin/env python3
"""Bind an experimental capability revision to an actual no-import Wasm and gold evidence."""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from compile_capability import (ROOT, canonical, digest, load, model_surface_contract,
                                source_identity, specialization_features, verify_bundle,
                                write_bundle)
from inspect_wasm import inspect_imports, inspect_memories, parse_sections

sys.path.insert(0, str(ROOT / "benchmarks"))
from economics_ped_conformance import generate as generate_economics_ped_conformance
from run_benchmark import CoreBridge
from statistics_corpus import validate_rows


def verify_build_provenance(bundle, artifact, profile, provenance_path):
    data = provenance_path.read_bytes()
    provenance = load(data)
    if canonical(provenance) != data:
        raise ValueError("noncanonical build provenance")
    if provenance.get("format") != "exactscope.capability.wasm-build-provenance":
        raise ValueError("unsupported build provenance format")
    if provenance.get("profile_id") != profile["profile_id"] or provenance.get("profile_revision") != profile["profile_revision"]:
        raise ValueError("build provenance profile identity mismatch")
    if provenance.get("profile_bundle_sha256") != digest((bundle / "manifest.json").read_bytes()):
        raise ValueError("build provenance parent bundle mismatch")
    profile_sha256 = digest((bundle / "profile.json").read_bytes())
    if provenance.get("profile_sha256") is not None and provenance.get("profile_sha256") != profile_sha256:
        raise ValueError("build provenance profile digest mismatch")
    if profile["domain"] != "statistics" and provenance.get("profile_sha256") != profile_sha256:
        raise ValueError("domain build provenance must bind the exact profile digest")
    if provenance.get("runtime_source_identity") != source_identity():
        raise ValueError("build provenance runtime source mismatch")
    if provenance.get("profile_core_revision") != profile["bindings"]["core_revision"]:
        raise ValueError("build provenance core binding mismatch")
    if provenance.get("artifact", {}).get("sha256") != digest(artifact.read_bytes()):
        raise ValueError("build provenance artifact mismatch")
    if provenance.get("artifact", {}).get("imports") != 0:
        raise ValueError("build provenance reports imported Wasm")
    build = provenance.get("build", {})
    expected_features = list(specialization_features(profile))
    provenance_domain = provenance.get("domain")
    if provenance_domain is not None and provenance_domain != profile["domain"]:
        raise ValueError("build provenance domain mismatch")
    if profile["domain"] != "statistics" and provenance_domain != profile["domain"]:
        raise ValueError("domain build provenance must carry explicit domain identity")
    if (build.get("target") != "wasm32v1-none" or
            build.get("features") != expected_features or
            build.get("selected_operations") != profile["runtime_surface"]["xs_eval"]["operations"]):
        raise ValueError("build provenance specialization mismatch")
    if build.get("configured_stack_bytes") != profile["device_budget"].get("wasm_stack_bytes_max"):
        raise ValueError("build provenance stack policy mismatch")
    if provenance.get("artifact", {}).get("initial_memory_pages") != profile["device_budget"].get("wasm_initial_pages_max"):
        raise ValueError("build provenance initial-memory mismatch")
    if provenance.get("artifact", {}).get("maximum_memory_pages") != profile["device_budget"].get("wasm_maximum_pages_max"):
        raise ValueError("build provenance maximum-memory mismatch")
    if profile["domain"] != "statistics":
        validations = provenance.get("evidence", {}).get("validations")
        if not isinstance(validations, list):
            raise ValueError("domain build provenance has no validation evidence")
        passed = {entry.get("name") for entry in validations
                  if isinstance(entry, dict) and entry.get("status") == "pass"}
        required = {"specialized_surface", "capability_gold"}
        if not required.issubset(passed):
            raise ValueError("domain build provenance is missing required passed validations")
    return data, provenance


def validate_domain_rows(profile, rows, corpus, core):
    domain = profile["domain"]
    if domain == "statistics":
        if rows:
            validate_rows(rows, CoreBridge(core))
        return
    if domain == "economics":
        selected = profile["runtime_surface"]["xs_eval"]["operations"]
        if selected != ["econ.ped.mid"]:
            raise ValueError("Economics binder currently admits reviewed econ.ped.mid evidence only")
        if corpus.read_bytes() != generate_economics_ped_conformance():
            raise ValueError("Economics conformance corpus differs from reviewed source-derived corpus")
        bridge = CoreBridge(core)
        for row in rows:
            actual, _ = bridge.eval(row["call"])
            expected = row["expected"]
            if actual.get("s") != expected.get("s"):
                raise ValueError(f"native Economics status mismatch: {row['id']}")
            for key, value in expected.items():
                if actual.get(key) != value:
                    raise ValueError(f"native Economics gold mismatch {row['id']}: {key}")
            if expected["s"] != 0 and "v" in actual:
                raise ValueError(f"native Economics failure leaked numeric value: {row['id']}")
        return
    raise ValueError(f"no native conformance validator registered for domain: {domain}")


def wasm_conformance(bundle_profile, artifact, corpus, report):
    domain = bundle_profile["domain"]
    if domain == "statistics":
        command = ["node", str(ROOT / "tools/check_statistics_wasm.mjs"),
                   str(artifact.resolve()), str(corpus.resolve()), str(report)]
        filename = "statistics-conformance.json"
    else:
        if domain == "economics":
            calc_mode = "calc" if bundle_profile["runtime_surface"]["xs_calc"]["enabled"] else "no-calc"
            subprocess.run(["node", str(ROOT / "tools/test_selected_economics_wasm.mjs"),
                            str(artifact.resolve()), calc_mode],
                           check=True, capture_output=True)
        command = ["node", str(ROOT / "tools/check_capability_wasm.mjs"),
                   str(artifact.resolve()), str(corpus.resolve()), domain, str(report)]
        filename = "capability-conformance.json"
    subprocess.run(command, check=True, capture_output=True)
    evidence = load(report.read_bytes())
    return filename, evidence


def bind(bundle, artifact, corpus, core, revision, build_provenance=None):
    original = verify_bundle(bundle)
    profile = load((bundle / "profile.json").read_bytes())
    if profile["bindings"]["core_revision"] != "sha256:" + source_identity():
        raise ValueError("profile source identity differs from the checked-out runtime source")
    if profile["device_budget"]["target_profile"] != "no-import-wasm":
        raise ValueError("only no-import-wasm binding is implemented")
    if type(revision) is not int or revision <= profile["profile_revision"] or revision > 0xffffffff:
        raise ValueError("bound output requires a new, greater profile revision")
    data = artifact.read_bytes()
    provenance_bytes = provenance = None
    if profile["domain"] != "statistics" and build_provenance is None:
        raise ValueError("non-Statistics capability binding requires verified build provenance")
    if build_provenance is not None:
        provenance_bytes, provenance = verify_build_provenance(
            bundle, artifact, profile, build_provenance)
    sections = parse_sections(data)
    imports = inspect_imports(sections)
    initial, maximum = inspect_memories(sections)
    if imports != 0 or len(data) > profile["device_budget"]["artifact_bytes_max"]:
        raise ValueError("artifact exceeds import/byte budget")
    rows = [load(line) for line in corpus.read_bytes().splitlines()]
    selected = set(profile["runtime_surface"]["xs_eval"]["operations"])
    if not rows and selected:
        raise ValueError("empty conformance corpus")
    covered = {row["call"]["op"] for row in rows if row["call"] is not None}
    if covered != selected:
        raise ValueError("corpus operations must exactly cover selected surface")
    validate_domain_rows(profile, rows, corpus, core)
    with tempfile.TemporaryDirectory(prefix="xs-bind-") as tmp:
        report = Path(tmp) / "conformance.json"
        conformance_name, evidence = wasm_conformance(profile, artifact, corpus, report)
    files = {name: (bundle / name).read_bytes() for name in original["files"]}
    files["runtime.wasm"] = data
    files[conformance_name] = canonical(evidence)
    files["benchmark-mapping.jsonl"] = corpus.read_bytes()
    if provenance_bytes is not None:
        files["build-provenance.json"] = provenance_bytes
    profile["profile_revision"] = revision
    profile["bindings"]["artifact_sha256"] = digest(data)
    profile["evidence"].update(
        conformance_suite=conformance_name,
        conformance_sha256=digest(files[conformance_name]),
        benchmark_mapping="benchmark-mapping.jsonl",
        benchmark_mapping_sha256=digest(files["benchmark-mapping.jsonl"]))
    if "surface-contract.json" in files:
        catalog = load(files["catalog.json"])
        files["surface-contract.json"] = canonical(model_surface_contract(profile, catalog, files))
        profile["bindings"]["surface_contract_sha256"] = digest(files["surface-contract.json"])
    files["profile.json"] = canonical(profile)
    manifest = dict(original)
    artifact_status = "artifact and gold bound; experimental, not target-qualified"
    source_match = "profile matches checkout; artifact behavior checked against gold, not build attestation"
    if provenance_bytes is not None:
        artifact_status = "artifact, build provenance and gold bound; experimental, not target-qualified"
        source_match = ("profile/runtime source identity and specialized build provenance match; "
                        "this is still not a signature, independent reproducible-build proof, or target qualification")
    manifest.update(parent_bundle_sha256=digest((bundle / "manifest.json").read_bytes()),
                    artifact_status=artifact_status,
                    binder_sha256=digest(Path(__file__).read_text(encoding="utf-8").encode()),
                    artifact_measurements={"bytes": len(data), "imports": imports,
                                           "initial_memory_pages": initial, "maximum_memory_pages": maximum,
                                           "resident_bytes": None, "scratch_bytes": None},
                    build_provenance_sha256=digest(provenance_bytes) if provenance_bytes is not None else None,
                    conformance_core_sha256=digest(core.read_bytes()),
                    source_match=source_match)
    manifest["files"] = {name: digest(value) for name, value in sorted(files.items())}
    files["manifest.json"] = canonical(manifest)
    files["bundle-sha256.txt"] = (digest(files["manifest.json"]) + "\n").encode()
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("bundle", "artifact", "corpus", "core", "output"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--revision", type=int, required=True)
    parser.add_argument("--build-provenance", type=Path)
    args = parser.parse_args()
    write_bundle(bind(args.bundle, args.artifact, args.corpus, args.core, args.revision,
                      args.build_provenance), args.output)
    verify_bundle(args.output)
    print("PASS artifact-bound experimental capability unit")


if __name__ == "__main__":
    main()
