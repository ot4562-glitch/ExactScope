# ExactScope roadmap

No dates are promised. This roadmap is ordered by **adoption leverage and evidence**, not by internal subsystem elegance or raw operation count.

ExactScope v0.1 should prove that a tiny deterministic quantitative coprocessor can improve real small-model quantitative workflows before the project spends heavily on catalog breadth or universal platform parity.

## Current baseline

Implemented today:

- deterministic `no_std` numeric kernel;
- checked decimal/rational arithmetic, deterministic sqrt, explicit round;
- executable economics operations;
- bounded statistics kernels;
- stable C ABI and zero-copy native vectors;
- current formula/kernel `.xsp` compile/load path;
- fused/dynamic shared statistics execution;
- no-import Wasm;
- Tiny JSON and TinyWire;
- wearable reference integration and A/B update reference;
- experimental Android/Linux ARM64 SDK packaging;
- relocatable CMake package;
- SDK doctor;
- CI covering the implemented paths.

This is enough engine to stop treating engine completeness as the primary blocker.

# P0 — prove the product

## P0.1 Direct one-hop hot path

- [x] `xs_eval` can execute known canonical operations directly.
- [x] Document `xs_find` as optional fallback rather than mandatory first hop.
- [x] Bind cached operation metadata to registry/pack digest and revision in the integration contract.
- [x] Add a bounded generated hot-set manifest format (1-32 operations; production target 8-32, with smaller smoke fixtures allowed).
- [x] Add direct hot-set fixtures that never require discovery.
- [x] Add cache invalidation tests for digest/revision changes.

Success criterion: common product calls require one model inference turn, not `find -> model -> eval`.

## P0.2 AI runtime adapters

- [x] Generate conservative OpenAI-compatible `xs_eval` tool assets.
- [x] Generate optional `xs_find` fallback assets.
- [x] Generate checked-in/reproducible GBNF for the direct hot path.
- [x] Generate compact digest-bound hot-set hints/catalogs from canonical pack metadata.
- [x] Add llama.cpp reference integration fixtures and an offline envelope self-test.
- [ ] Add one runnable local-model example from a prebuilt ExactScope artifact and record a real model result.
- [x] Keep every adapter calculation-free.

Success criterion: a local-AI developer does not write custom ExactScope glue from scratch.

## P0.3 Benchmark and claim evidence

- [x] Build the reproducible benchmark harness defined in `docs/BENCHMARK.md`, including a real Tiny JSON/core bridge and corpus/core drift self-test.
- [ ] Compare model-only vs direct `xs_eval` hot path on recorded real models.
- [ ] Measure `xs_find -> xs_eval` cold-path overhead on recorded real models.
- [ ] Measure direct hot path with constrained decoding/GBNF on recorded real models.
- [ ] Test at least sub-1B, 1B-2B, and about-3B model classes.
- [x] Report stage-level fields for recognition, operation, extraction, syntax/tool validity, core rejection/status, and result fidelity.
- [x] Report successful-answer/fidelity and incorrect-numeric-answer rates separately.
- [ ] Complete evidence capture for tokens, inference turns, end-to-end latency, ExactScope compute latency, resident bytes, scratch bytes, and energy; the harness already records model tokens/turns/latencies/core latency when supplied by the runtime.
- [x] Keep accuracy/latency/energy improvement claims blocked until recorded evidence exists.

Success criterion: ExactScope has a reproducible answer to “how much does this help?”

## P0.4 Five-minute evaluation and prebuilt artifacts

- [x] Add `docs/QUICKSTART.md`.
- [x] Provide relocatable `ExactScope::exactscope` CMake target in the experimental SDK.
- [x] Provide developer-side SDK doctor.
- [ ] Publish permanent prebuilt native evaluation archive.
- [ ] Publish permanent no-import Wasm evaluation artifact.
- [ ] Include manifest, checksums, hot-set metadata, licenses, and smoke-test instructions.
- [ ] Add a clean-room quickstart CI test using only downloaded/release-shaped artifacts.

Success criterion: a non-Rust integrator can evaluate ExactScope without building the workspace.

# P1 — make the initial domain content defensible

## P1.1 Benchmark hot sets

- [ ] Choose the smallest reviewed `math-basic` benchmark hot set.
- [ ] Choose the smallest reviewed `statistics-core` benchmark hot set.
- [x] Choose the first bounded `econ-undergrad` benchmark hot set (`econ-core-8`) directly from the fused executable registry.
- [ ] Ensure each benchmark operation has explicit method/semantics/provenance.
- [ ] Ensure valid, invalid, boundary, overflow/resource, and precision vectors.

A useful 8-16 operation proof is preferred to a weakly reviewed 99-operation release.

## P1.2 Broader official pack completion

- [ ] Complete `math-basic` 16-operation source pack.
- [ ] Complete `statistics-core` 18-operation source pack.
- [ ] Complete `econ-undergrad` 65-operation source pack.
- [ ] Reach the stable-release golden-vector threshold per shipped operation.
- [ ] Complete independent source/method review.

These tasks are important but do not precede the P0 product proof.

# P2 — broaden distribution

## P2.1 Primary v0.1 release profiles

- [ ] Stable native static C ABI release package.
- [ ] Stable no-import Wasm release package.
- [ ] Immutable release manifests and checksums.
- [ ] Exact release-artifact conformance.
- [ ] Target self-test/smoke execution.

Native static and no-import Wasm are the primary v0.1 release candidates.

## P2.2 Platform convenience packages

- [ ] Android AAR/Prefab for evidenced ABI(s).
- [ ] Linux x86-64/AArch64 release archives as demand/evidence requires.
- [ ] Windows x86-64 archive.
- [ ] Apple Silicon macOS package.
- [ ] iOS/XCFramework only when a host-app path is justified.

A platform wrapper must not duplicate calculation logic.

## P2.3 Real target qualification

- [ ] Record real target artifact size/resident memory/scratch.
- [ ] Record latency distributions.
- [ ] Record energy where measurable.
- [ ] Record offline/radio-free behavior.
- [ ] Run target malformed-input smoke tests.
- [ ] Run update/rollback evidence where the platform owns durable slots.

# P3 — breadth after proof

## P3.1 Dynamic-pack maturity

- [ ] Complete every v0.1 `.xsp` operation shape.
- [ ] Complete dynamic discovery alias-index parity.
- [ ] Expand malformed-pack corpus/fuzzing.
- [ ] Promote dynamic profile only after real adoption needs it.

Dynamic mode remains valuable architecture, but it is not allowed to delay the first product proof.

## P3.2 Wider execution/profile parity

- [ ] Promote additional profiles/architectures only with immutable artifact evidence.
- [ ] Keep one shared evaluator/semantics.
- [ ] Do not require every internal profile to be Tier 1 before v0.1 proves value.

## P3.3 Additional domains

- [ ] Add finance or scientific packs only after the initial three domains demonstrate the resident-runtime advantage.
- [ ] Reject domains that require hidden judgment, live data, or unbounded computation.

# Product/market work

- [x] Document broader market beyond offline wearables.
- [x] Document benchmark-before-claim policy.
- [x] Document OSS + verified packs/LTS/qualification/custom-pack commercialization direction.
- [ ] Publish an adoption-oriented comparison against model-only reasoning and general Python/sandbox approaches using measured evidence.
- [ ] Publish at least one case study or reproducible target integration before making enterprise optimization claims.

# Explicit non-goals

- human calculator UI as a core product;
- general chatbot;
- mandatory companion app;
- mandatory cloud service/account;
- ExactScope-owned daemon;
- arbitrary code execution inside packs;
- general symbolic algebra;
- hidden semantic repair in adapters;
- universal policy forecasting;
- bypassing device security models;
- expanding platform/catalog breadth merely to appear complete.

# v0.1 product gate

ExactScope v0.1 should not be called a stable product release until all of the following are true:

1. a direct one-hop `xs_eval` hot-set integration is documented and reproducibly runnable;
2. OpenAI-compatible/GBNF assets and at least one local-runtime reference integration exist;
3. a reproducible benchmark compares model-only, direct hot path, discovery path, and constrained direct path;
4. benchmark results expose successful-answer rate, wrong-number rate, invalid/rejected-call rate, turns/tokens/latency, and resource cost;
5. at least one small reviewed cross-domain hot set has strong provenance and golden/negative coverage;
6. stable prebuilt native static and/or no-import Wasm artifact(s) can be evaluated without a Rust toolchain;
7. shipped release artifacts pass exact ABI/wire/golden/malformed-input conformance;
8. at least one constrained real target has measured size/memory/latency evidence, and energy is reported where measurable;
9. support labels are backed by immutable artifact evidence;
10. no adapter or wrapper performs hidden calculation or semantic guessing.

Full 99-operation catalog completion, dynamic discovery maturity, and universal platform Tier 1 parity are **not** prerequisites for proving and shipping a focused v0.1 product if the shipped scope is clearly documented.
