# ExactScope roadmap

No dates are promised. Compatibility and measured footprint take priority over feature count.

## Design baseline — current

- [x] Define AI-only/offline system boundary.
- [x] Choose library-first fused/static/dynamic deployment profiles.
- [x] Define `no_std` allocator-free kernel requirements.
- [x] Define stable logical C ABI.
- [x] Choose no-import `wasm32v1-none` portability baseline.
- [x] Define `decimal64-v1` and deterministic error model.
- [x] Define bounded formula VM and kernel boundary.
- [x] Define data-only source and binary scope-pack formats.
- [x] Define Tiny JSON `xs_find`/`xs_eval` interface.
- [x] Define deterministic CBOR TinyWire and stream frame.
- [x] Define compatibility tiers and release manifest.
- [x] Freeze the first math/statistics/economics catalog.
- [x] Add one complete economics source-pack fixture.
- [x] Create the compile-oriented Rust workspace and pin the primary/MSRV toolchains.
- [x] Freeze C99/C++11 ABI headers and the no-import WebAssembly memory contract.
- [x] Move stable IDs into machine-readable registries with cross-file validation.
- [x] Add design/schema/VM/header validation and GitHub contract CI.
- [x] Freeze the exact first implementation slice and acceptance sequence.

The checked boxes describe specifications and scaffolding, not working calculation features or released runtime artifacts.

## v0.1 implementation

### Vertical slice

- [ ] Implement runtime modules inside the frozen Rust workspace without adding unreviewed runtime dependencies.
- [ ] Implement `Decimal64` parsing, canonicalization, arithmetic, and formatting.
- [ ] Implement the VM subset required by `econ.ped.mid`.
- [ ] Implement minimal fused registry.
- [ ] Implement `econ.ped.mid` source compilation and golden tests.
- [ ] Implement C ABI context/evaluation path.
- [ ] Implement no-import WebAssembly evaluation path.
- [ ] Implement Tiny JSON `xs_eval` path.
- [ ] Prove byte-identical fused/native/dynamic/Wasm results.
- [ ] Record first size, scratch, and latency measurements.

### Pack and discovery foundation

- [ ] Implement complete `.xsp` compiler and safe loader.
- [ ] Implement deterministic alias index and `xs_find`.
- [ ] Implement caller-arena dynamic registration.
- [ ] Implement all scalar VM instructions.
- [ ] Implement shared malformed-pack corpus and fuzz targets.
- [ ] Implement reproducible compiler output and manifests.

### Official packs

- [ ] Complete `math-basic` 16-operation source pack.
- [ ] Implement deterministic statistics kernels.
- [ ] Complete `statistics-core` 18-operation source pack.
- [ ] Complete `econ-undergrad` 65-operation source pack.
- [ ] Reach at least 20 golden vectors per stable operation.
- [ ] Complete formula/source review.

### Compatibility and packaging

- [ ] Tier 1 no-import WebAssembly artifact.
- [ ] Tier 1 Linux x86-64 and AArch64 archives.
- [ ] Tier 1 Windows x86-64 archive.
- [ ] Tier 1 Android `arm64-v8a` AAR.
- [ ] Tier 2 Android `armeabi-v7a` and `x86_64` AAR entries.
- [ ] Tier 1 Apple Silicon macOS artifact.
- [ ] Tier 2 iOS XCFramework.
- [ ] Execute conformance in an embedded WebAssembly runtime.
- [ ] Execute conformance on one real constrained embedded target before claiming embedded support.
- [ ] Publish compatibility manifest, checksums, and SBOM.

### AI adapters and benchmark

- [ ] Generate conservative OpenAI-style tool schemas.
- [ ] Generate and test checked-in GBNF grammars.
- [ ] Add llama.cpp integration fixtures.
- [ ] Add Android/Kotlin convenience wrapper.
- [ ] Add optional MCP adapter.
- [ ] Build model-only versus ExactScope benchmark harness.
- [ ] Test sub-1B, 1B–2B, and 3B local models.
- [ ] Publish stage-level accuracy/token/latency results only after measurement.

## After v0.1

Candidates, not commitments:

- exact-rational public profile;
- wider decimal profile;
- deterministic integer-power finance kernels;
- `finance-basic` pack;
- compact locale lexicon packs;
- additional embedded targets;
- signed pack metadata profile;
- operation hot-set learning performed by the host, not the core;
- domain packs where deterministic formulas and bounded procedures are genuinely appropriate.

## Explicit non-roadmap items

- human calculator UI;
- general chatbot;
- cloud account/service requirement;
- live market/economic data inside the core;
- arbitrary code plugins;
- arbitrary expression language;
- general symbolic algebra;
- universal policy forecasting;
- feature growth that removes scalar fallback or no-allocation fused mode.

## v0.1 release gate

v0.1 is not released until:

1. the three initial packs are installable;
2. every official operation is source-reviewed and tested;
3. C ABI and no-import Wasm conformance pass;
4. Android and Linux release artifacts pass installation tests;
5. fused/static/dynamic results are identical;
6. memory and size budgets are measured and published;
7. all support labels are backed by compatibility manifests;
8. no manual model reasoning is required inside the calculation path.
