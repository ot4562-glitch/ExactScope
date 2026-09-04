# ExactScope roadmap

No dates are promised. Compatibility, deterministic semantics, and measured footprint take priority over feature count.

The product direction is a **tiny resident academic-computation micro-runtime for local AI**, not a standalone application. See [`docs/PRODUCT_DIRECTION.md`](docs/PRODUCT_DIRECTION.md).

## Design baseline — current

- [x] Define AI-only/offline system boundary.
- [x] Choose library-first fused/static/dynamic execution profiles.
- [x] Define the user-installable resident-component packaging goal for hosts that expose an extension/runtime boundary.
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
- [x] Add the first complete economics source-pack fixture.
- [x] Create the Rust workspace and pin the primary/MSRV toolchains.
- [x] Freeze C99/C++11 ABI headers and the no-import WebAssembly memory contract.
- [x] Move stable IDs into machine-readable registries with cross-file validation.
- [x] Add design/schema/VM/header validation and GitHub contract CI.
- [x] Freeze the exact first implementation slice and acceptance sequence.

The repository is no longer a design-only scaffold. The first scalar execution path works; remaining unchecked items below are implementation, coverage, packaging, measurement, or qualification work.

### Release-closing priority order

For the current v0.1 completion sprint, work is ordered by adoption leverage rather than raw operation count:

1. **semantic parity:** fused/static/dynamic/Wasm must share one evaluator and return identical canonical results;
2. **vector completion:** finish `.xsp` kernel/vector compilation/loading, dynamic C ABI evaluation, and portable conformance;
3. **numeric closure:** deterministic square root, standard deviation/correlation, explicit round, and required malformed/boundary coverage;
4. **OEM integration:** CMake imported target, Android Prefab/AAR convenience packaging, doctor/self-test/qualification helpers, no target-side toolchain dependency;
5. **release evidence:** immutable manifests, checksums, SBOM, reproducible archives, support-tier records, and permanent release assets;
6. **catalog depth:** finish the reviewed official hot set and only then expand breadth toward the full 99-operation catalog;
7. **real hardware:** publish measured footprint, latency, energy, offline behavior, and update/rollback evidence before Tier 1 claims.

A smaller fully qualified hot set is preferred to a large catalog with weak installation or compatibility evidence.

## v0.1 implementation

### Vertical slice

- [x] Establish runtime modules inside the frozen Rust workspace without adding unreviewed runtime dependencies.
- [x] Implement `Decimal64` parsing, canonicalization, checked arithmetic support, and formatting.
- [x] Implement the VM subset required by `econ.ped.mid`.
- [x] Implement the minimal fused registry and typed evaluation path.
- [x] Implement `econ.ped.mid` source compilation and golden tests.
- [x] Implement the C ABI context/evaluation path.
- [x] Implement the no-import WebAssembly evaluation path.
- [x] Implement the Tiny JSON scalar `xs_eval` path.
- [x] Exercise the canonical first-slice flow across native/dynamic/Wasm conformance paths in CI.
- [ ] Record release-grade size, scratch, latency, and energy measurements on real target hardware.

### Numeric and VM completion

- [x] Implement exact ordered statistics sum and arithmetic mean kernels.
- [x] Implement exact weighted mean.
- [x] Implement deterministic two-pass population/sample variance.
- [x] Implement population/sample covariance.
- [x] Implement exact simple linear-regression slope/intercept kernel.
- [x] Wire the first fused statistics vector operations through the public C ABI with zero-copy caller-owned inputs.
- [x] Wire bounded statistics vector/kernel operations through canonical `.xsp` compilation/loading and dynamic evaluation using the shared kernel.
- [x] Implement exact VM integer power, negation, min/max, full comparisons, boolean composition, and numeric select.
- [x] Implement deterministic square root with the normative rounding/inexact contract.
- [x] Implement population/sample standard deviation and Pearson correlation through the shared deterministic square root.
- [x] Implement explicit VM `round` while preserving the active scale/rounding contract.
- [x] Complete portable vector transport for the fused no-import Wasm path: typed statistics evaluation plus deterministic-CBOR TinyWire `find`/scalar/vector `eval`, canonical-encoding rejection, ambiguity preservation, and buffer-sizing conformance.

### Pack and discovery foundation

- [ ] Complete the full `.xsp` compiler and safe loader for every v0.1 operation shape.
- [x] Establish deterministic fused discovery/lookup and `xs_find` foundations.
- [x] Implement caller-owned dynamic-pack registration/mounting foundations.
- [ ] Complete dynamic discovery only when its alias index has the same deterministic contract as fused discovery.
- [ ] Implement the shared malformed-pack corpus and fuzz targets.
- [x] Establish reproducible compiler output checks for the implemented slice.
- [ ] Complete release manifests for every supported artifact/profile.

### Official academic packs

- [ ] Complete `math-basic` 16-operation source pack.
- [ ] Complete `statistics-core` 18-operation source pack.
- [ ] Complete `econ-undergrad` 65-operation source pack.
- [ ] Reach at least 20 golden vectors per stable operation.
- [ ] Complete independent formula/source review and provenance metadata.
- [ ] Add another academic pack only after the first three prove the resident-runtime size/accuracy advantage.

Operation count is not the primary success metric. A smaller reviewed hot set is preferable to a broad catalog that increases resident size or hides ambiguous academic methods.

### Consumer-installable resident component

- [ ] Define one canonical component manifest that binds ABI, core version, pack digests, operations, size budgets, and conformance evidence.
- [ ] Package a fused no-import Wasm component as the most portable single-file install target.
- [ ] Package a native resident component (`shared library + manifest + selected packs`) for hosts with a native extension ABI.
- [ ] Add a tiny install/register/self-test tool that exits after installation and never becomes a daemon.
- [ ] Add atomic component update/rollback using the existing A/B principles where the host permits it.
- [x] Add a developer-side SDK doctor for manifest/checksum integrity, public-header ABI, runtime digest/archive format and ARM64 ELF architecture, required host panic boundary, and relocatable CMake target checks.
- [ ] Extend the target self-test with canonical on-device smoke-vector execution and qualification evidence capture.
- [ ] Publish permanent release assets rather than relying only on expiring CI artifacts.

A closed device with no extension, plugin, application, WebAssembly, or paired-host execution boundary cannot be made directly user-installable by ExactScope alone. Compatibility claims must describe the actual host boundary.

### Compatibility and packaging

- [ ] Tier 1 no-import WebAssembly artifact.
- [ ] Tier 1 Linux x86-64 and AArch64 resident/native archives.
- [ ] Tier 1 Windows x86-64 resident/native archive.
- [ ] Tier 1 Android `arm64-v8a` component/wrapper where the host exposes a supported loading path.
- [ ] Tier 2 Android emulator/secondary ABI entries only after evidence.
- [ ] Tier 1 Apple Silicon macOS artifact.
- [ ] Tier 2 iOS/XCFramework wrapper where a host application is required by platform policy.
- [x] Cross-build experimental Android AArch64 and Linux AArch64 wearable SDK artifacts in CI.
- [ ] Execute conformance in an embedded WebAssembly runtime.
- [ ] Execute conformance on one real constrained target before claiming embedded support.
- [ ] Publish compatibility manifest, checksums, SBOM, and immutable release artifact digests.

### AI adapters and benchmark

- [ ] Generate conservative OpenAI-style tool schemas from installed operation metadata.
- [ ] Generate and test checked-in GBNF grammars.
- [ ] Add llama.cpp integration fixtures.
- [ ] Keep Android/Kotlin, Swift, MCP, and other wrappers optional and calculation-free.
- [ ] Build the model-only versus model-plus-ExactScope benchmark harness.
- [ ] Test sub-1B, 1B–2B, and 3B local models.
- [ ] Measure final numeric accuracy, tool-selection accuracy, model tokens, latency, resident bytes, scratch bytes, and energy.
- [ ] Publish comparative claims only after reproducible measurement.

## After v0.1

Candidates, not commitments:

- exact-rational public profile;
- wider decimal profile;
- deterministic finance kernels after integer-power and time-value semantics are conformed;
- `finance-basic` pack;
- compact locale lexicon packs;
- additional embedded targets;
- signed pack/component metadata profile;
- operation hot-set learning performed by the host, not the core;
- additional academic packs where deterministic formulas and bounded procedures are genuinely appropriate.

## Explicit non-roadmap items

- human calculator UI;
- general chatbot;
- mandatory companion application;
- cloud account/service requirement;
- ExactScope-owned background daemon;
- live market/economic data inside the core;
- arbitrary native code plugins inside scope packs;
- arbitrary expression language;
- general symbolic algebra;
- universal policy forecasting;
- bypassing a device platform's security model to obtain installation access;
- feature growth that removes scalar fallback or no-allocation fused mode.

## v0.1 release gate

v0.1 is not released until:

1. the initial math/statistics/economics pack set required for v0.1 is installable and source-reviewed;
2. every shipped official operation has the required golden, invalid, boundary, overflow, and precision vectors;
3. C ABI and no-import Wasm conformance pass for the exact release artifacts;
4. at least one consumer-installable resident-component package passes clean-install, offline-start, self-test, update, and rollback tests;
5. fused/static/dynamic results are identical wherever the same operation/profile is exposed;
6. memory, artifact size, latency, and energy budgets are measured and published for at least one constrained real target;
7. all support labels are backed by compatibility manifests and immutable artifact digests;
8. no manual model arithmetic or hidden adapter calculation is required inside the deterministic calculation path.
