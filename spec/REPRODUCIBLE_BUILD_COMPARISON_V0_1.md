# ExactScope reproducible-build comparison v0.1

Status: experimental evidence-record format. This format compares artifact bytes without executing ExactScope.

## Purpose

`BUILD_INPUT_IDENTITY_V0_1.md` identifies one exact build request. This contract records whether two supplied build outputs are byte-identical for that request.

The question answered is deliberately narrow:

```text
given this exact build-input identity,
do these two labeled output files have the same bytes?
```

A byte match does not by itself establish target qualification or the independence of the two build environments.

## Record

`exactscope.reproducible-build.comparison` v0.1 records:

- SHA-256 of canonical `build-inputs.json`;
- release profile and target;
- artifact kind;
- exactly two distinct builder labels;
- output size and SHA-256 for each file;
- `byte_identical`;
- `MATCH` or `MISMATCH`;
- a fixed claim string describing exactly what was checked.

The schema is `spec/schemas/reproducible-build-comparison.schema.json`.

## Compare

```text
python3 tools/compare_reproducible_builds.py \
  --build-inputs build-inputs.json \
  --artifact-a <output-a> --builder-a <label-a> \
  --artifact-b <output-b> --builder-b <label-b> \
  --output comparison.json
```

The tool verifies the build-input identity against the current source tree, accepts regular files only, bounds each compared file to 256 MiB, records hashes and sizes, emits canonical JSON, and refuses to overwrite a different existing comparison record.

A match records:

```text
Two caller-identified build outputs are byte-identical for the recorded inputs; builder independence and runtime qualification are not implied.
```

A mismatch records:

```text
Build outputs differ; reproducible-build proof is not established.
```

## Verify

```text
python3 tools/compare_reproducible_builds.py \
  --verify comparison.json \
  --build-inputs build-inputs.json
```

Verification checks canonical form, schema, distinct builder labels, internal status consistency, build-input digest, release profile, and target. A valid `MISMATCH` record still returns a nonzero command status so it cannot satisfy a byte-reproducibility gate.

## Evidence boundary

A release-level reproducibility claim needs additional release-process evidence identifying the two build environments and binding the comparison to the exact immutable release artifact being promoted. v0.1 performs no normalization and prefers exact byte identity.

Any future rule that ignores nondeterministic sections requires a new reviewed contract instead of silently weakening this comparison.

## Tiny-runtime rule

All comparison logic stays in workstation/build tooling. It adds no code or metadata parser to the constrained ExactScope runtime.
