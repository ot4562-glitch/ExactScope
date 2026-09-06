# ExactScope v1.0.0-rc.3 — Release-Bound AI Qualification Candidate

`v1.0.0-rc.3` is a prerelease candidate that closes the public AI-integration packaging blocker found during independent external-user qualification of `v1.0.0-rc.2`.

The rc2 deterministic core/native/Wasm paths passed the tested release-integrity, clean-source, smoke and fail-closed gates, but the published evaluation SDK did not contain a complete bound capability identity usable directly from the archive. The documented capability host required files such as `profile.json`, `manifest.json`, `bundle-sha256.txt`, `surface-contract.json` and a bound runtime, while the archive exposed only the raw generated hot-set assets. Model inference was therefore correctly stopped at zero calls rather than reconstructing private inputs and weakening the evidence boundary.

rc3 fixes that release/package defect without changing the benchmark corpus or claiming model/target qualification.

## What changed

### Complete public evaluation capabilities

Each x86-64 evaluation SDK now contains two complete artifact-bound capability bundles:

```text
capabilities/quant-core-16-semantic-ai/
capabilities/quant-core-16-combined-ai/
```

Both bind the exact packaged generic no-import `runtime.wasm`, the reviewed `quant-core-16` catalog/binding, prompt/tool/GBNF assets, operation revisions and the packaged benchmark mapping. Each directory contains its own profile, model-surface contract, manifest, detached bundle digest and exact file hashes.

The semantic capability exposes one model-visible `xs_eval` tool. The combined capability exposes the same 16-operation `xs_eval` surface plus bounded `xs_calc`. Neither exposes `xs_find` on the primary qualification path.

### Archive-local capability host

The published path is now explicit:

```text
examples/capability-host.mjs
```

It accepts the packaged capability directories directly and verifies the bundle/profile/surface/runtime identity before execution. Documentation distinguishes this archive path from the source-checkout path `examples/javascript/capability-host.mjs`.

### Immutable A/C/D qualification harness

The evaluation SDK now ships:

```text
benchmarks/capability_surface.py
benchmarks/run_qualification.py
```

`preregister` performs zero inference calls and freezes the exact release archive, selected model inventory/file, inference-runtime executable/version/launch command, context, core, corpus, capability identities, seed, token ceiling, timeout, arm definitions, scorer policy, single-writer rule and no-retry/no-repair policy.

`run` re-verifies those bytes before the first model request and writes one immutable evidence directory containing the preregistration, model inventory, corpus, copied C/D capabilities, raw model responses/item records, summary, status and SHA-256 manifest.

Primary arms are:

- **A** — model only;
- **C** — exact public semantic capability (`xs_eval` only);
- **D** — exact public combined capability (`xs_eval + xs_calc`).

The current benchmark corpus is semantic. Supported C/D items expect `xs_eval`; a D-side `xs_calc` choice is recorded as a wrong-lane failure even if an arithmetic result happens to match. Missing-information items expect no tool call. There are no hidden retries or answer repairs.

### Stronger release clean-room test

The evaluation-bundle clean-room test now extracts the final tarball and, using only packaged files:

1. verifies the core and no-import Wasm paths;
2. executes the semantic capability through `examples/capability-host.mjs`;
3. executes the combined capability through the same host;
4. imports the packaged qualification runner;
5. performs a zero-inference preregistration smoke using the extracted archive/core/corpus/capabilities;
6. on Linux, compiles and executes the packaged native C example against the packaged static library.

This is specifically intended to prevent a recurrence of the rc2 archive/documentation mismatch.

## What did not change into a claim

rc3 is **not** a stable or production-qualified release. This release does not inherit model scores from older development evidence and does not claim:

- measured A→C or A→D model uplift;
- hallucination reduction;
- equivalence to or replacement of a larger model;
- Android/ARM64 RAM, latency, energy or thermal savings;
- hardware-life extension;
- production readiness or stable support.

Those claims remain gated on a fresh qualification run performed from the immutable published rc3 assets and, for target claims, a recorded representative real ARM64 device.

## Intended next step

After GitHub publishes `v1.0.0-rc.3`, start from a fresh directory, verify release/tag/archive hashes, run the packaged no-model/clean-room baseline, inventory the planned model files, preregister each model with `benchmarks/run_qualification.py`, and only then start A/C/D inference. Historical r20 and rc2 blocked evidence remain historical and must not be copied into rc3 scores.
