#!/usr/bin/env python3
"""Reproducibly build and verify one experimental binary-specialized Wasm capability.

This records build provenance and conformance evidence. It is not a signature,
remote attestation, reproducible-build proof across independent builders, or
target qualification.
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

from compile_capability import (ROOT, canonical, digest, domain_descriptor, load, source_identity,
                                specialization_features, verify_bundle)
from inspect_wasm import inspect_imports, inspect_memories, parse_sections

LEGACY_SPECIALIZATIONS = {"statistics-core-8-wasm"}
TARGET = "wasm32v1-none"
STACK_BYTES = 16384
MAXIMUM_PAGES = 1


def resolve_tool(name, explicit=None):
    if explicit is not None:
        path = Path(explicit).absolute()
        if not path.is_file():
            raise ValueError(f"missing tool: {path}")
        return path
    found = shutil.which(name)
    if found:
        return Path(found).absolute()
    suffix = ".exe" if os.name == "nt" else ""
    candidates = []
    if os.environ.get("USERPROFILE"):
        candidates.append(Path(os.environ["USERPROFILE"]) / ".cargo/bin" / (name + suffix))
    candidates.append(Path.home() / ".cargo/bin" / (name + suffix))
    for path in candidates:
        if path.is_file():
            return path.absolute()
    raise ValueError(f"cannot locate {name}")


def command_output(command):
    return subprocess.run([str(part) for part in command], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()


def git_state():
    commit = command_output(["git", "rev-parse", "HEAD"])
    status = command_output(["git", "status", "--porcelain=v1"])
    return {"commit": commit, "dirty": bool(status)}


def validate_specialized_profile(bundle):
    manifest = verify_bundle(bundle)
    profile = load((bundle / "profile.json").read_bytes())
    if profile["support"] != "experimental":
        raise ValueError("specialized builder only accepts experimental profiles")
    if profile["bindings"]["core_revision"] != "sha256:" + source_identity():
        raise ValueError("profile runtime source identity differs from checkout")
    surface = profile["runtime_surface"]
    device = profile["device_budget"]
    descriptor = domain_descriptor(profile["domain"])
    specialization = surface.get("specialization")
    if specialization not in ({descriptor["specialization"]} | LEGACY_SPECIALIZATIONS):
        raise ValueError("profile does not request a supported Wasm specialization")
    if specialization in LEGACY_SPECIALIZATIONS and profile["domain"] != "statistics":
        raise ValueError("legacy Statistics specialization cannot serve another domain")
    specialization_features(profile)
    if surface["xs_find"]["enabled"]:
        raise ValueError("specialized serving profile cannot expose discovery")
    if device["target_profile"] != "no-import-wasm" or device.get("imports_max") != 0:
        raise ValueError("specialized builder requires the no-import Wasm target")
    if device.get("wasm_stack_bytes_max") != STACK_BYTES:
        raise ValueError("profile stack budget differs from the specialized build policy")
    if device.get("wasm_initial_pages_max") != 1:
        raise ValueError("profile must require a one-page initial Wasm memory ceiling")
    if device.get("wasm_maximum_pages_max") != MAXIMUM_PAGES:
        raise ValueError("profile must require a one-page maximum Wasm memory ceiling")
    return manifest, profile


def selected_conformance_corpus(corpus, profile):
    selected = set(profile["runtime_surface"]["xs_eval"]["operations"])
    rows = [load(line) for line in corpus.read_bytes().splitlines() if line.strip()]
    kept = [row for row in rows if row.get("call") is not None and row["call"].get("op") in selected]
    covered = {row["call"]["op"] for row in kept}
    if covered != selected:
        raise ValueError("source corpus does not cover every selected semantic operation")
    return b"".join(canonical(row) for row in kept)


def validate_artifact(artifact, profile):
    data = artifact.read_bytes()
    sections = parse_sections(data)
    imports = inspect_imports(sections)
    initial, maximum = inspect_memories(sections)
    budget = profile["device_budget"]
    if imports != 0:
        raise ValueError("specialized artifact has imports")
    if len(data) > budget["artifact_bytes_max"]:
        raise ValueError("specialized artifact exceeds byte budget")
    if initial > budget["wasm_initial_pages_max"]:
        raise ValueError("specialized artifact exceeds initial-memory-page budget")
    if maximum is None or maximum > budget["wasm_maximum_pages_max"]:
        raise ValueError("specialized artifact exceeds maximum-memory-page budget")
    return data, {"bytes": len(data), "sha256": digest(data), "imports": imports,
                  "initial_memory_pages": initial, "maximum_memory_pages": maximum,
                  "configured_stack_bytes": STACK_BYTES}


def immutable_write(files, output):
    if output.exists():
        actual = {p.name: p.read_bytes() for p in output.iterdir() if p.is_file()}
        if actual != files or any(p.is_dir() for p in output.iterdir()):
            raise ValueError("immutable build output differs; use a new directory/revision")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".xs-wasm-build-") as tmp:
        stage = Path(tmp) / "output"
        stage.mkdir()
        for name, data in files.items():
            (stage / name).write_bytes(data)
        stage.rename(output)


def verify_output(output, bundle):
    provenance_bytes = (output / "build-provenance.json").read_bytes()
    provenance = load(provenance_bytes)
    if canonical(provenance) != provenance_bytes:
        raise ValueError("noncanonical build provenance")
    if (output / "build-sha256.txt").read_text().strip() != digest(provenance_bytes):
        raise ValueError("build provenance digest mismatch")
    artifact = (output / "runtime.wasm").read_bytes()
    generic_pair = (output / "capability-conformance.json", output / "capability-conformance-corpus.jsonl")
    legacy_pair = (output / "statistics-conformance.json", output / "statistics-conformance-corpus.jsonl")
    generic_present = tuple(path.is_file() for path in generic_pair)
    legacy_present = tuple(path.is_file() for path in legacy_pair)
    if generic_present not in ((False, False), (True, True)) or legacy_present not in ((False, False), (True, True)):
        raise ValueError("incomplete conformance evidence pair")
    if all(generic_present) and all(legacy_present):
        raise ValueError("conflicting generic and legacy conformance layouts")
    profile = load((bundle / "profile.json").read_bytes())
    if all(generic_present):
        conformance_path, corpus_path = generic_pair
        evidence_key = "conformance_sha256"
        expected_inventory = {"runtime.wasm", "capability-conformance.json",
                              "capability-conformance-corpus.jsonl", "build-provenance.json",
                              "build-sha256.txt"}
    elif all(legacy_present) and profile.get("domain") == "statistics":
        conformance_path, corpus_path = legacy_pair
        evidence_key = "statistics_conformance_sha256"
        expected_inventory = {"runtime.wasm", "statistics-conformance.json",
                              "statistics-conformance-corpus.jsonl", "build-provenance.json",
                              "build-sha256.txt"}
    else:
        raise ValueError("missing recognized conformance evidence layout")
    conformance = conformance_path.read_bytes()
    conformance_corpus = corpus_path.read_bytes()
    if provenance["artifact"]["sha256"] != digest(artifact):
        raise ValueError("artifact digest mismatch")
    if provenance["evidence"].get(evidence_key) != digest(conformance):
        raise ValueError("conformance evidence digest mismatch")
    if provenance["evidence"].get("conformance_corpus_sha256") != digest(conformance_corpus):
        raise ValueError("conformance corpus digest mismatch")
    if provenance["profile_bundle_sha256"] != digest((bundle / "manifest.json").read_bytes()):
        raise ValueError("profile bundle identity mismatch")
    if set(p.name for p in output.iterdir()) != expected_inventory:
        raise ValueError("build output file inventory mismatch")
    return provenance


def selected_surface_check(profile, node, artifact, selected_csv):
    calc_mode = "calc" if profile["runtime_surface"]["xs_calc"]["enabled"] else "no-calc"
    domain = profile["domain"]
    if domain == "statistics":
        return [node, ROOT / "tools/test_selected_statistics_wasm.mjs", artifact, selected_csv,
                calc_mode]
    if domain == "economics":
        if selected_csv != "econ.ped.mid":
            raise ValueError("Economics selected-surface checker currently covers econ.ped.mid only")
        return [node, ROOT / "tools/test_selected_economics_wasm.mjs", artifact, calc_mode]
    raise ValueError(f"no selected-surface checker registered for domain: {domain}")


def build(bundle, corpus, output, cargo=None, node=None):
    bundle_manifest, profile = validate_specialized_profile(bundle)
    features = specialization_features(profile)
    selected_operations = profile["runtime_surface"]["xs_eval"]["operations"]
    domain = profile["domain"]
    source_corpus_bytes = corpus.read_bytes()
    conformance_corpus_bytes = selected_conformance_corpus(corpus, profile)
    cargo = resolve_tool("cargo", cargo)
    rustc = resolve_tool("rustc")
    node = resolve_tool("node", node)

    with tempfile.TemporaryDirectory(prefix="xs-capability-wasm-") as tmp:
        target_dir = Path(tmp) / "target"
        command = [cargo, "build", "--locked", "--release", "-p", "exactscope-wasm",
                   "--target", TARGET, "--no-default-features", "--features", ",".join(features),
                   "--target-dir", target_dir]
        subprocess.run([str(part) for part in command], cwd=ROOT, check=True)
        artifact = target_dir / TARGET / "release" / "exactscope_wasm.wasm"
        data, measurements = validate_artifact(artifact, profile)

        conformance_corpus = Path(tmp) / "capability-conformance-corpus.jsonl"
        conformance_corpus.write_bytes(conformance_corpus_bytes)
        conformance = Path(tmp) / "capability-conformance.json"
        selected_csv = ",".join(selected_operations) or "-"
        validations = []
        checks = (
            ("specialized_surface", selected_surface_check(profile, node, artifact, selected_csv)),
            ("capability_gold", [node, ROOT / "tools/check_capability_wasm.mjs", artifact,
                                 conformance_corpus, domain, conformance,
                                 "allow-empty" if not selected_operations else "require-calls"]),
        )
        for name, check in checks:
            completed = subprocess.run([str(part) for part in check], cwd=ROOT, check=True,
                                       capture_output=True, text=True)
            validations.append({"name": name, "status": "pass", "stdout": completed.stdout.strip()})

        conformance_bytes = conformance.read_bytes()
        conformance_doc = load(conformance_bytes)
        if (conformance_doc.get("format") != "exactscope.capability.wasm-conformance"
                or conformance_doc.get("format_version") != "0.1"
                or conformance_doc.get("domain") != domain):
            raise ValueError("conformance report domain/format mismatch")
        if conformance_doc["artifact_sha256"] != measurements["sha256"]:
            raise ValueError("conformance report artifact identity mismatch")
        if conformance_doc["corpus_sha256"] != digest(conformance_corpus_bytes):
            raise ValueError("conformance report corpus identity mismatch")
        if conformance_doc.get("operations") != sorted(selected_operations):
            raise ValueError("conformance report operation surface mismatch")
        checked_calls = conformance_doc.get("checked_calls")
        if not isinstance(checked_calls, int) or checked_calls < 0:
            raise ValueError("conformance report has invalid checked-call count")
        if selected_operations and checked_calls <= 0:
            raise ValueError("conformance report contains no checked calls")
        if not selected_operations and checked_calls != 0:
            raise ValueError("zero-operation profile produced semantic conformance calls")

        provenance = {
            "format": "exactscope.capability.wasm-build-provenance",
            "format_version": "0.1",
            "status": "experimental build provenance; not attestation or target qualification",
            "profile_id": profile["profile_id"],
            "profile_revision": profile["profile_revision"],
            "domain": domain,
            "profile_bundle_sha256": digest((bundle / "manifest.json").read_bytes()),
            "profile_sha256": digest((bundle / "profile.json").read_bytes()),
            "runtime_source_identity": source_identity(),
            "profile_core_revision": profile["bindings"]["core_revision"],
            "build": {
                "target": TARGET,
                "package": "exactscope-wasm",
                "profile": "release",
                "default_features": False,
                "features": list(features),
                "selected_operations": list(selected_operations),
                "configured_stack_bytes": STACK_BYTES,
                "cargo": command_output([cargo, "--version"]),
                "rustc": command_output([rustc, "--version", "--verbose"]),
                "normalized_command": ["cargo", "build", "--locked", "--release", "-p", "exactscope-wasm",
                                       "--target", TARGET, "--no-default-features", "--features", ",".join(features),
                                       "--target-dir", "<temporary>"],
            },
            "artifact": measurements,
            "evidence": {
                "source_corpus_sha256": digest(source_corpus_bytes),
                "conformance_corpus_sha256": digest(conformance_corpus_bytes),
                "conformance_sha256": digest(conformance_bytes),
                "checked_calls": conformance_doc["checked_calls"],
                "validations": validations,
            },
            "checkout": git_state(),
            "host": {"platform": platform.platform(), "python": platform.python_version()},
            "profile_manifest_generator_sha256": bundle_manifest["generator_sha256"],
        }
        provenance_bytes = canonical(provenance)
        files = {
            "runtime.wasm": data,
            "capability-conformance.json": conformance_bytes,
            "capability-conformance-corpus.jsonl": conformance_corpus_bytes,
            "build-provenance.json": provenance_bytes,
            "build-sha256.txt": (digest(provenance_bytes) + "\n").encode(),
        }
    immutable_write(files, output)
    verify_output(output, bundle)
    return load(files["build-provenance.json"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, default=ROOT / "benchmarks/statistics-v0.1.jsonl")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cargo", type=Path)
    parser.add_argument("--node", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        if args.output is None:
            parser.error("--output is required with --verify")
        verify_output(args.output, args.bundle)
        print("PASS specialized Wasm build provenance")
        return
    if args.output is None:
        parser.error("--output is required")
    result = build(args.bundle, args.corpus, args.output, args.cargo, args.node)
    print("PASS specialized Wasm build "
          f"bytes={result['artifact']['bytes']} imports={result['artifact']['imports']} "
          f"initial_pages={result['artifact']['initial_memory_pages']} sha256={result['artifact']['sha256']}")


if __name__ == "__main__":
    main()
