#!/usr/bin/env python3
"""Attach identity-matched model benchmark evidence to a new capability revision.

Two benchmark-corpus modes are supported:

1. Legacy/profile mapping: result corpus SHA equals the bound profile's
   ``benchmark_mapping_sha256``.
2. External preregistered benchmark: a different natural-language corpus may attach
   only when the exact corpus bytes, preregistration, corpus manifest, generator,
   parent bundle/runtime identity, model identities and raw arm/item pairs all bind.

Attachments preserve raw evidence, never upgrade support status, and use digest-
namespaced snapshot files so later model runs can append without overwriting earlier
model evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from compile_capability import (canonical, digest, load, model_surface_contract,
                                verify_bundle, write_bundle)

REQUIRED_RESULTS = ("metadata.json", "summary.json", "items.jsonl", "harness.py")
EXTERNAL_SNAPSHOTS = ("preregistration.json", "corpus-manifest.json", "corpus-generator.py")
ARM_ORDER = ("A", "B", "C", "D", "E")


def capability_contract_sha256(profile):
    """Digest serving semantics while excluding revision-coupled negotiation metadata."""
    bindings = dict(profile["bindings"])
    # An evidence-only profile revision must reissue surface-contract.json because
    # that document carries the profile revision. Its digest therefore changes
    # even when ABI, hot-set, schemas, grammar, prompt, artifact and budgets do not.
    # Exclude only that derived digest from the lineage contract; all actual
    # serving bindings remain identity-bound below.
    bindings.pop("surface_contract_sha256", None)
    contract = {
        "profile_id": profile["profile_id"],
        "support": profile["support"],
        "domain": profile["domain"],
        "bindings": bindings,
        "device_budget": profile["device_budget"],
        "model_budget": profile["model_budget"],
        "runtime_surface": profile["runtime_surface"],
        "task_families": profile["task_families"],
    }
    return digest(canonical(contract))


def benchmark_source_identity(bundle, manifest, profile):
    """Resolve the immutable capability revision that all evidence-only descendants benchmark."""
    current_bundle_sha = digest((bundle / "manifest.json").read_bytes())
    current_contract_sha = capability_contract_sha256(profile)
    source_bundle_sha = manifest.get("model_evidence_source_bundle_sha256", current_bundle_sha)
    source_revision = manifest.get("model_evidence_source_profile_revision", profile["profile_revision"])
    source_contract_sha = manifest.get("model_evidence_source_contract_sha256", current_contract_sha)
    if not isinstance(source_bundle_sha, str) or len(source_bundle_sha) != 64:
        raise ValueError("invalid model-evidence source bundle identity")
    if type(source_revision) is not int or source_revision <= 0 or source_revision > profile["profile_revision"]:
        raise ValueError("invalid model-evidence source profile revision")
    if source_contract_sha != current_contract_sha:
        raise ValueError("current capability serving contract differs from model-evidence source contract")
    return {
        "bundle_sha256": source_bundle_sha,
        "profile_revision": source_revision,
        "contract_sha256": source_contract_sha,
    }


def validate_semantic_baseline(metadata, semantic_baseline_bundle):
    runtime = metadata.get("runtime_evidence") or {}
    identity = runtime.get("semantic_baseline")
    marginal = runtime.get("semantic_artifact_bytes")
    if identity is None and marginal is None:
        if semantic_baseline_bundle is not None:
            raise ValueError("semantic baseline bundle supplied but result has no semantic baseline identity")
        return None
    if not isinstance(identity, dict) or type(marginal) is not int or marginal <= 0:
        raise ValueError("incomplete semantic baseline evidence")
    if semantic_baseline_bundle is None:
        raise ValueError("semantic baseline bundle required for marginal-byte model evidence")

    baseline_manifest = verify_bundle(semantic_baseline_bundle)
    baseline_profile = load((semantic_baseline_bundle / "profile.json").read_bytes())
    baseline_artifact = semantic_baseline_bundle / "runtime.wasm"
    if not baseline_artifact.is_file():
        raise ValueError("semantic baseline runtime.wasm is missing")
    measurements = baseline_manifest.get("artifact_measurements") or {}
    baseline_bytes = baseline_artifact.read_bytes()
    if baseline_profile["runtime_surface"]["xs_eval"]["operations"]:
        raise ValueError("semantic baseline must expose zero semantic operations")
    expected = {
        "profile_id": baseline_profile["profile_id"],
        "profile_revision": baseline_profile["profile_revision"],
        "artifact_sha256": digest(baseline_bytes),
        "artifact_bytes": len(baseline_bytes),
        "bundle_sha256": digest((semantic_baseline_bundle / "manifest.json").read_bytes()),
    }
    for field, value in expected.items():
        if identity.get(field) != value:
            raise ValueError(f"semantic baseline identity mismatch: {field}")
    if measurements.get("bytes") != len(baseline_bytes):
        raise ValueError("semantic baseline manifest byte measurement mismatch")
    runtime_bytes = runtime.get("artifact_bytes")
    if type(runtime_bytes) is not int or runtime_bytes - len(baseline_bytes) != marginal:
        raise ValueError("semantic marginal artifact bytes do not match verified baseline delta")
    return expected


def validate_external_benchmark(results, benchmark_corpus, manifest, profile, metadata, paired, source_identity):
    if benchmark_corpus is None:
        raise ValueError("model evidence corpus mismatch; external benchmark corpus snapshot required")
    for name in EXTERNAL_SNAPSHOTS:
        if not (results / name).is_file():
            raise ValueError(f"missing preregistered benchmark snapshot: {name}")

    corpus_bytes = benchmark_corpus.read_bytes()
    corpus_sha = digest(corpus_bytes)
    if corpus_sha != metadata.get("corpus_sha256"):
        raise ValueError("external benchmark corpus digest mismatch")

    prereg_bytes = (results / "preregistration.json").read_bytes()
    corpus_manifest_bytes = (results / "corpus-manifest.json").read_bytes()
    generator_bytes = (results / "corpus-generator.py").read_bytes()
    prereg = load(prereg_bytes)
    corpus_manifest = load(corpus_manifest_bytes)
    prereg_evidence = metadata.get("preregistration_evidence") or {}

    snapshot_checks = (
        ("preregistration_sha256", digest(prereg_bytes)),
        ("corpus_manifest_sha256", digest(corpus_manifest_bytes)),
        ("corpus_generator_sha256", digest(generator_bytes)),
    )
    for field, value in snapshot_checks:
        if prereg_evidence.get(field) != value:
            raise ValueError(f"model result preregistration evidence mismatch: {field}")
    if metadata.get("corpus_manifest_sha256") != digest(corpus_manifest_bytes):
        raise ValueError("model result corpus manifest snapshot mismatch")
    if metadata.get("corpus_generator_sha256") != digest(generator_bytes):
        raise ValueError("model result corpus generator snapshot mismatch")

    if prereg.get("status") != "FROZEN_READY_FOR_MODEL_RUN_CONFIGURATION":
        raise ValueError("external benchmark preregistration is not frozen")
    prereg_corpus = prereg.get("corpus") or {}
    if prereg_corpus.get("status") != "FROZEN_BEFORE_MODEL_RUN":
        raise ValueError("external benchmark corpus was not frozen before model execution")
    if prereg_corpus.get("sha256") != corpus_sha:
        raise ValueError("preregistered corpus digest mismatch")
    if prereg_corpus.get("manifest_sha256") != digest(corpus_manifest_bytes):
        raise ValueError("preregistered corpus manifest digest mismatch")
    if prereg_corpus.get("generator_sha256") != digest(generator_bytes):
        raise ValueError("preregistered corpus generator digest mismatch")

    capability = prereg.get("capability") or {}
    measurements = manifest.get("artifact_measurements") or {}
    if capability.get("profile_revision") != source_identity["profile_revision"]:
        raise ValueError("preregistered capability revision mismatch")
    if capability.get("artifact_sha256") != profile["bindings"].get("artifact_sha256"):
        raise ValueError("preregistered capability artifact mismatch")
    if capability.get("artifact_bytes") != measurements.get("bytes"):
        raise ValueError("preregistered capability byte measurement mismatch")

    runtime_binding = corpus_manifest.get("runtime_binding") or {}
    provenance = corpus_manifest.get("provenance") or {}
    corpus_contract = corpus_manifest.get("corpus") or {}
    if corpus_manifest.get("status") != "FROZEN_BEFORE_MODEL_RUN":
        raise ValueError("corpus manifest is not frozen-before-model-run evidence")
    if corpus_contract.get("sha256") != corpus_sha:
        raise ValueError("corpus manifest digest mismatch")
    if runtime_binding.get("capability_profile_revision") != source_identity["profile_revision"]:
        raise ValueError("corpus manifest capability revision mismatch")
    if runtime_binding.get("artifact_sha256") != profile["bindings"].get("artifact_sha256"):
        raise ValueError("corpus manifest runtime artifact mismatch")
    if runtime_binding.get("core_revision") != profile["bindings"].get("core_revision"):
        raise ValueError("corpus manifest core revision mismatch")
    if provenance.get("model_outputs_used_to_construct_or_edit_corpus") is not False:
        raise ValueError("corpus provenance does not prove model-output independence")
    if provenance.get("model_results_observed_before_freeze") is not False:
        raise ValueError("corpus provenance does not prove pre-result freeze")

    corpus_rows = [load(line) for line in corpus_bytes.splitlines() if line]
    corpus_ids = [row.get("id") for row in corpus_rows]
    if not corpus_rows or any(not isinstance(identifier, str) for identifier in corpus_ids):
        raise ValueError("invalid external benchmark corpus rows")
    if len(set(corpus_ids)) != len(corpus_ids):
        raise ValueError("duplicate external benchmark corpus id")
    if corpus_contract.get("items") != len(corpus_rows) or prereg_corpus.get("items") != len(corpus_rows):
        raise ValueError("external benchmark corpus item count mismatch")
    runtime_calls = sum(row.get("call") is not None for row in corpus_rows)
    if corpus_contract.get("runtime_calls") != runtime_calls or prereg_corpus.get("runtime_calls") != runtime_calls:
        raise ValueError("external benchmark runtime-call count mismatch")
    family_counts = dict(Counter(row.get("family") for row in corpus_rows))
    if corpus_contract.get("family_layout") != family_counts or prereg_corpus.get("family_layout") != family_counts:
        raise ValueError("external benchmark family layout mismatch")

    a_ids = {identifier for arm, identifier in paired if arm == "A"}
    if a_ids != set(corpus_ids):
        raise ValueError("raw model rows do not exactly cover external benchmark corpus ids")

    generation = prereg.get("generation_contract") or {}
    config = metadata.get("config") or {}
    if config.get("seed") != generation.get("seed"):
        raise ValueError("model result generation seed differs from preregistration")
    if config.get("generation_max_tokens") != generation.get("generation_max_tokens"):
        raise ValueError("model result generation token budget differs from preregistration")
    if config.get("baseline_mode") != generation.get("baseline_mode"):
        raise ValueError("model result baseline mode differs from preregistration")
    if generation.get("temperature") != 0 or generation.get("model_turns") != 1:
        raise ValueError("unsupported external benchmark generation contract")
    if generation.get("hidden_retry_or_repair") is not False or generation.get("legacy_asymmetric_token_budget") is not False:
        raise ValueError("external benchmark contract permits hidden repair or legacy asymmetric budget")
    if metadata.get("scoring_contract") != (prereg.get("scoring_contract") or {}).get("id"):
        raise ValueError("model result scoring contract differs from preregistration")
    for row in paired.values():
        if row.get("generation_budget") != generation.get("generation_max_tokens"):
            raise ValueError("raw row generation budget differs from preregistration")

    inventory_sha = (metadata.get("model_inventory_evidence") or {}).get("sha256")
    if inventory_sha != (prereg.get("model_inventory") or {}).get("source_sha256"):
        raise ValueError("model inventory digest differs from preregistration")
    if prereg_evidence.get("model_inventory_sha256") != inventory_sha:
        raise ValueError("preregistration evidence model inventory mismatch")

    run_id = prereg_evidence.get("preregistered_run_id")
    runs = [candidate for candidate in prereg.get("predeclared_runs", []) if candidate.get("id") == run_id]
    if len(runs) != 1:
        raise ValueError("model result does not identify one preregistered run")
    run = runs[0]
    actual_arms = [arm for arm in ARM_ORDER if any(candidate == arm for candidate, _ in paired)]
    if actual_arms != run.get("arms"):
        raise ValueError("raw model arm set differs from preregistered run")

    small = config.get("small") or {}
    for field, expected in (
        ("model", run.get("small_model_id")),
        ("model_sha256", run.get("small_model_sha256")),
        ("quantization", run.get("small_quantization")),
        ("reasoning", run.get("reasoning_mode")),
    ):
        if small.get(field) != expected:
            raise ValueError(f"small model differs from preregistration: {field}")
    if small.get("context_size") != generation.get("context_size"):
        raise ValueError("small-model context differs from preregistration")

    larger = config.get("larger")
    if run.get("larger_model_id") is None:
        if larger is not None:
            raise ValueError("preregistered run does not permit a larger model")
    else:
        if not isinstance(larger, dict):
            raise ValueError("preregistered run requires a larger model")
        for field, expected in (
            ("model", run.get("larger_model_id")),
            ("model_sha256", run.get("larger_model_sha256")),
            ("quantization", run.get("larger_quantization")),
            ("reasoning", run.get("reasoning_mode")),
        ):
            if larger.get(field) != expected:
                raise ValueError(f"larger model differs from preregistration: {field}")
        if larger.get("context_size") != generation.get("context_size"):
            raise ValueError("larger-model context differs from preregistration")

    runtime = metadata.get("runtime_evidence") or {}
    if runtime.get("semantic_artifact_bytes") != capability.get("semantic_artifact_bytes"):
        raise ValueError("semantic marginal bytes differ from preregistration")
    baseline = runtime.get("semantic_baseline") or {}
    if baseline.get("artifact_sha256") != capability.get("semantic_baseline_sha256"):
        raise ValueError("semantic baseline artifact differs from preregistration")
    if baseline.get("artifact_bytes") != capability.get("semantic_baseline_bytes"):
        raise ValueError("semantic baseline bytes differ from preregistration")

    return {
        "source": "external-preregistered",
        "corpus_sha256": corpus_sha,
        "corpus_items": len(corpus_rows),
        "runtime_calls": runtime_calls,
        "preregistration_sha256": digest(prereg_bytes),
        "corpus_manifest_sha256": digest(corpus_manifest_bytes),
        "corpus_generator_sha256": digest(generator_bytes),
        "model_inventory_sha256": inventory_sha,
        "preregistered_run_id": run_id,
    }


def validate_model_results(bundle, results, benchmark_corpus=None, semantic_baseline_bundle=None):
    manifest = verify_bundle(bundle)
    profile = load((bundle / "profile.json").read_bytes())
    source_identity = benchmark_source_identity(bundle, manifest, profile)
    if profile["support"] != "experimental":
        raise ValueError("model evidence attachment does not change support status")
    if (results / "INVALIDATION.json").exists():
        raise ValueError("invalidated benchmark output cannot be attached")
    for name in REQUIRED_RESULTS:
        if not (results / name).is_file():
            raise ValueError(f"missing model evidence file: {name}")

    metadata_bytes = (results / "metadata.json").read_bytes()
    summary_bytes = (results / "summary.json").read_bytes()
    items_bytes = (results / "items.jsonl").read_bytes()
    metadata = load(metadata_bytes)
    summary = load(summary_bytes)
    if canonical(metadata) != metadata_bytes or canonical(summary) != summary_bytes:
        raise ValueError("metadata/summary must be canonical benchmark output")
    if metadata.get("run_status") not in (None, "complete"):
        raise ValueError("partial model benchmark output cannot be attached")

    expected_bundle = source_identity["bundle_sha256"]
    if metadata.get("bundle_sha256") != expected_bundle:
        raise ValueError("model evidence capability bundle mismatch")
    if metadata.get("harness_sha256") != digest((results / "harness.py").read_bytes()):
        raise ValueError("model evidence harness snapshot mismatch")
    if summary.get("items_sha256") != digest(items_bytes):
        raise ValueError("model summary does not bind raw rows")
    if summary.get("metadata_sha256") != digest(metadata_bytes):
        raise ValueError("model summary does not bind metadata")

    runtime = metadata.get("runtime_evidence") or {}
    artifact_sha = profile["bindings"].get("artifact_sha256")
    measurements = manifest.get("artifact_measurements") or {}
    if not artifact_sha or runtime.get("artifact_sha256") != artifact_sha:
        raise ValueError("model evidence runtime artifact mismatch")
    if runtime.get("artifact_bytes") != measurements.get("bytes"):
        raise ValueError("model evidence runtime byte cost mismatch")
    if runtime.get("profile_id") != profile["profile_id"] or runtime.get("profile_revision") != source_identity["profile_revision"]:
        raise ValueError("model evidence profile revision mismatch")
    configured_cost = (metadata.get("config", {}).get("incremental_costs") or {}).get("artifact_bytes")
    if configured_cost != measurements.get("bytes"):
        raise ValueError("model evidence did not use the bound artifact byte cost")

    rows = [load(line) for line in items_bytes.splitlines() if line]
    if not rows:
        raise ValueError("empty model evidence")
    paired = {}
    for row in rows:
        if row.get("bundle_sha256") != expected_bundle or row.get("corpus_sha256") != metadata.get("corpus_sha256"):
            raise ValueError("raw model row identity mismatch")
        arm, identifier = row.get("arm"), row.get("id")
        if arm not in ARM_ORDER or not isinstance(identifier, str):
            raise ValueError("invalid model evidence arm/id")
        key = (arm, identifier)
        if key in paired:
            raise ValueError("duplicate raw model row")
        paired[key] = row
    ids = {identifier for arm, identifier in paired if arm == "A"}
    if not ids:
        raise ValueError("missing baseline arm")
    for arm in ("A", "B", "C", "D"):
        if {identifier for candidate, identifier in paired if candidate == arm} != ids:
            raise ValueError("unpaired A/B/C/D raw model rows")
    e_ids = {identifier for arm, identifier in paired if arm == "E"}
    if e_ids and e_ids != ids:
        raise ValueError("unpaired larger-model raw rows")

    profile_corpus = profile["evidence"].get("benchmark_mapping_sha256")
    result_corpus = metadata.get("corpus_sha256")
    if result_corpus == profile_corpus:
        benchmark_evidence = {
            "source": "profile-benchmark-mapping",
            "corpus_sha256": result_corpus,
            "profile_benchmark_mapping_sha256": profile_corpus,
        }
        if benchmark_corpus is not None and digest(benchmark_corpus.read_bytes()) != result_corpus:
            raise ValueError("supplied benchmark corpus does not match profile-mapping result")
    else:
        benchmark_evidence = validate_external_benchmark(
            results, benchmark_corpus, manifest, profile, metadata, paired, source_identity
        )

    semantic_baseline_evidence = validate_semantic_baseline(metadata, semantic_baseline_bundle)
    return manifest, profile, metadata, summary, benchmark_evidence, semantic_baseline_evidence, source_identity


def attach(bundle, results, revision, benchmark_corpus=None, semantic_baseline_bundle=None):
    (manifest, profile, metadata, summary, benchmark_evidence,
     semantic_baseline_evidence, source_identity) = validate_model_results(
        bundle, results, benchmark_corpus, semantic_baseline_bundle
    )
    if type(revision) is not int or revision <= profile["profile_revision"] or revision > 0xffffffff:
        raise ValueError("model evidence output requires a new, greater profile revision")

    result_files = {p.name: p.read_bytes() for p in results.iterdir() if p.is_file()}
    required_snapshots = {"metadata.json", "summary.json", "items.jsonl", "harness.py"}
    if not required_snapshots <= result_files.keys():
        raise AssertionError("validated evidence inventory changed")

    evidence_index = {
        "format": "exactscope.capability.model-evidence",
        "format_version": "0.2",
        "status": "experimental benchmark evidence; not target qualification or model-equivalence proof",
        "source_profile_revision": source_identity["profile_revision"],
        "benchmark_source_bundle_sha256": source_identity["bundle_sha256"],
        "benchmark_source_contract_sha256": source_identity["contract_sha256"],
        "attachment_parent_bundle_sha256": digest((bundle / "manifest.json").read_bytes()),
        "corpus_sha256": metadata["corpus_sha256"],
        "artifact_sha256": metadata["runtime_evidence"]["artifact_sha256"],
        "model_config": metadata["config"],
        "scoring_contract": metadata.get("scoring_contract"),
        "raw_items_sha256": summary["items_sha256"],
        "summary_sha256": digest((results / "summary.json").read_bytes()),
        "benchmark_evidence": benchmark_evidence,
        "semantic_baseline_evidence": semantic_baseline_evidence,
        "result_files": {name: digest(data) for name, data in sorted(result_files.items())},
    }
    if benchmark_corpus is not None:
        evidence_index["benchmark_corpus_sha256"] = digest(benchmark_corpus.read_bytes())
    evidence_bytes = canonical(evidence_index)
    evidence_sha = digest(evidence_bytes)
    prefix = evidence_sha[:16]

    files = {name: (bundle / name).read_bytes() for name in manifest["files"]}
    index_name = f"model-evidence-{prefix}.json"
    if index_name in files:
        raise ValueError("model evidence digest is already present in bundle")
    files[index_name] = evidence_bytes
    for name, data in sorted(result_files.items()):
        snapshot_name = f"model-{prefix}-{name}"
        if snapshot_name in files:
            raise ValueError("model evidence snapshot name collision")
        files[snapshot_name] = data
    if benchmark_corpus is not None:
        corpus_name = f"model-{prefix}-benchmark-corpus.jsonl"
        files[corpus_name] = benchmark_corpus.read_bytes()

    profile["profile_revision"] = revision
    model_bundles = list(profile["evidence"].get("model_result_bundles") or [])
    model_identity = "sha256:" + evidence_sha
    if model_identity in model_bundles:
        raise ValueError("model evidence is already bound")
    model_bundles.append(model_identity)
    profile["evidence"]["model_result_bundles"] = model_bundles
    if "surface-contract.json" in files:
        catalog = load(files["catalog.json"])
        files["surface-contract.json"] = canonical(model_surface_contract(profile, catalog, files))
        profile["bindings"]["surface_contract_sha256"] = digest(files["surface-contract.json"])
    files["profile.json"] = canonical(profile)

    next_manifest = dict(manifest)
    next_manifest.update(
        parent_bundle_sha256=digest((bundle / "manifest.json").read_bytes()),
        model_evidence_source_bundle_sha256=source_identity["bundle_sha256"],
        model_evidence_source_profile_revision=source_identity["profile_revision"],
        model_evidence_source_contract_sha256=source_identity["contract_sha256"],
        artifact_status="artifact, build provenance, gold and identity-matched model evidence bound; experimental, not target-qualified",
        model_evidence_sha256=evidence_sha,
        model_evidence_count=len(model_bundles),
        model_evidence_attacher_sha256=digest(Path(__file__).read_text(encoding="utf-8").encode()),
    )
    next_manifest["files"] = {name: digest(data) for name, data in sorted(files.items())}
    files["manifest.json"] = canonical(next_manifest)
    files["bundle-sha256.txt"] = (digest(files["manifest.json"]) + "\n").encode()
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--revision", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--benchmark-corpus", type=Path)
    parser.add_argument("--semantic-baseline-bundle", type=Path)
    args = parser.parse_args()
    write_bundle(
        attach(
            args.bundle, args.results, args.revision,
            args.benchmark_corpus, args.semantic_baseline_bundle,
        ),
        args.output,
    )
    verify_bundle(args.output)
    print("PASS identity-matched model evidence attached; support remains experimental")


if __name__ == "__main__":
    main()
