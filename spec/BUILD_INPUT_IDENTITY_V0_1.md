# ExactScope build-input identity v0.1

Status: experimental reproducibility metadata contract. A matching identity is **not** independent reproducible-build evidence.

## Purpose

ExactScope release claims are attached to exact artifacts. Before two builders can meaningfully compare artifact bytes, they must first prove that they were asked to build the same thing. `exactscope.build-input-identity` v0.1 records that request without executing ExactScope.

The document binds:

- exact capability bundle identity;
- capability profile id/revision/domain;
- capability core/source revision and model-surface contract digest;
- release profile and target;
- pinned Rust channel;
- exact Cargo feature set;
- `--locked` dependency policy and Cargo release profile;
- current runtime source identity;
- SHA-256 of the lockfile, toolchain/configuration, public integration files, export registry, release contracts, and packaging/inspection tooling.

It deliberately states:

```text
Build inputs pinned; independent byte-for-byte rebuild comparison not yet performed.
```

That sentence must not be replaced with a stronger claim until independent artifact comparison has actually occurred.

## Generation

```text
python3 tools/build_input_identity.py \
  --capability <current-source-capability> \
  --profile native-static \
  --target <target> \
  --output build-inputs.json

python3 tools/build_input_identity.py \
  --capability <current-source-capability> \
  --profile no-import-wasm \
  --target wasm32v1-none \
  --output build-inputs.json
```

Generation fails if `profile.bindings.core_revision` does not equal the current deterministic runtime source identity. A frozen capability from older source cannot therefore be relabeled as a recipe for the current tree.

For the primary profiles:

- `native-static` records the `standalone-staticlib` feature and requires `host-limited` + `native-static` capability metadata;
- `no-import-wasm` derives the exact specialization feature list from the capability-selected operations and requires the `no-import-wasm` device profile.

## Verification

```text
python3 tools/build_input_identity.py --verify build-inputs.json
```

Verification is source-tree-relative. It checks canonical JSON, schema, project version, current source identity, pinned Rust channel, and every recorded build-input file digest.

An identity generated from one checkout is expected to fail verification after a relevant source/configuration/packaging input changes. Create a new identity rather than overwriting provenance.

## Relationship to reproducible-build evidence

This contract establishes **input equivalence**, not output equivalence.

`REPRODUCIBLE_BUILD_COMPARISON_V0_1.md` and `tools/compare_reproducible_builds.py` provide the next mechanical layer: they bind this build-input digest to two labeled output hashes/sizes and record exact byte `MATCH` or `MISMATCH` without executing either artifact.

A release-level independent-reproducibility claim still needs additional process evidence for the two builder/environment identities and their separation. Until that evidence is attached to the exact immutable release artifact, documentation must distinguish **pinned build inputs** and **byte-comparison records** from an independently reproducible release claim.

## Scope and tiny-runtime rule

All of this metadata is workstation/build tooling. The deployed kernel/Wasm/native runtime does not parse it. ExactScope spends host-side metadata and validation complexity rather than increasing the constrained runtime merely to carry provenance machinery.
