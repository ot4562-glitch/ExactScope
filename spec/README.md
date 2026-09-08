# ExactScope specification index

The files in this directory define the v0.1 runtime/data/wire contracts plus clearly labeled product-format drafts. Runtime code must not silently diverge from normative contracts. The active rc4 flagship is provider-neutral everyday grounding, defined by `GROUNDING_CONTRACT_V0_1.md`, `../docs/GROUNDING_ARCHITECTURE.md`, `../docs/PRODUCT_DIRECTION.md`, and `../docs/BENCHMARK.md`. The existing `xs_calc`/`xs_eval`, capability-slice, native-static and no-import-Wasm specifications remain the retained quantitative subsystem rather than the flagship product definition.

## Normative specifications

| Document | Authority |
|---|---|
| [GROUNDING_CONTRACT_V0_1.md](GROUNDING_CONTRACT_V0_1.md) | Provider-neutral rc4 grounding contract: profile/query/target/provider/evidence/frame/projection semantics, authority, privacy, reproducibility, and benchmark isolation |
| [NUMERIC_V0_1.md](NUMERIC_V0_1.md) | Decimal representation, lexical grammar, arithmetic, rounding, deterministic kernels |
| [ERRORS_V0_1.md](ERRORS_V0_1.md) | Stable status codes and failure behavior |
| [CORE_ABI_V0_1.md](CORE_ABI_V0_1.md) | Logical native C ABI, ownership, structures, and function contract |
| [WASM_ABI_V0_1.md](WASM_ABI_V0_1.md) | No-import WebAssembly 1.0 memory/export contract |
| [SCOPEPACK_V0_1.md](SCOPEPACK_V0_1.md) | Source-pack schema, VM program, compiled `.xsp` format, identity/versioning |
| [TINYWIRE_V0_1.md](TINYWIRE_V0_1.md) | Tiny JSON adapter messages and deterministic CBOR transport |
| [PLAN_V0_1.md](PLAN_V0_1.md) | Experimental bounded `xs_calc` arithmetic-plan semantics for weak-model use |
| [WEARABLE_EDGE_PROFILE_V0_1.md](WEARABLE_EDGE_PROFILE_V0_1.md) | Product-level memory, latency, energy, privacy, update, and qualification contract for AI wearables |
| [WEARABLE_SDK_BUNDLE_V0_1.md](WEARABLE_SDK_BUNDLE_V0_1.md) | Deterministic Android/Linux arm64 OEM SDK archive, manifest, integrity, and claim-discipline contract |
| [WEARABLE_BENCHMARK_V0_1.md](WEARABLE_BENCHMARK_V0_1.md) | O(1)-memory target latency collection, canonical raw CSV, nearest-rank percentiles, and target pass thresholds |
| [WEARABLE_QUALIFICATION_V0_1.md](WEARABLE_QUALIFICATION_V0_1.md) | Target-device evidence collection, destructive testing, and measured/qualified release-claim procedure |

## Product-format design drafts

| Document | Purpose |
|---|---|
| [CAPABILITY_PROFILE_V0_1.md](CAPABILITY_PROFILE_V0_1.md) | Draft identity/budget/evidence contract for one deployed AI capability slice; not yet a stable runtime or release format |
| [BUILD_INPUT_IDENTITY_V0_1.md](BUILD_INPUT_IDENTITY_V0_1.md) | Experimental deterministic record of current-source/toolchain/feature/package inputs; prerequisite metadata, not independent reproducible-build proof |
| [MODEL_SURFACE_NEGOTIATION_V0_1.md](MODEL_SURFACE_NEGOTIATION_V0_1.md) | Experimental host/build contract for exact tool-schema/grammar/prompt ID, version, and digest negotiation |
| [OPERATION_REVISION_POLICY_V0_1.md](OPERATION_REVISION_POLICY_V0_1.md) | Active prerelease immutability, revision-bump, transparent-upgrade, and future supported-release-line policy |
| [RELEASE_BUNDLE_V0_1.md](RELEASE_BUNDLE_V0_1.md) | Experimental deterministic native-static/no-import-Wasm integration archive with optional SHA-256-bound native `.xsgi` grounding payload; packaging contract only, not qualification |
| [REPRODUCIBLE_BUILD_COMPARISON_V0_1.md](REPRODUCIBLE_BUILD_COMPARISON_V0_1.md) | Experimental byte-comparison evidence record for two labeled outputs of one pinned build-input identity |

## Machine-readable schemas

| File | Purpose |
|---|---|
| [schemas/grounding-profile-v0.1.schema.json](schemas/grounding-profile-v0.1.schema.json) | Frozen rc4 GroundingProfile behavior/identity shape |
| [schemas/grounding-query-envelope-v0.1.schema.json](schemas/grounding-query-envelope-v0.1.schema.json) | Host-bound original query, profile and security-scope envelope |
| [schemas/grounding-routing-plan-v0.1.schema.json](schemas/grounding-routing-plan-v0.1.schema.json) | Router output bound to profile/router identity |
| [schemas/grounding-target-plan-v0.1.schema.json](schemas/grounding-target-plan-v0.1.schema.json) | Per-target namespace, authority, binding and sufficiency contract |
| [schemas/grounding-provider-outcome-v0.1.schema.json](schemas/grounding-provider-outcome-v0.1.schema.json) | Typed provider completion/failure outcome and candidates |
| [schemas/grounding-evidence-item-v0.1.schema.json](schemas/grounding-evidence-item-v0.1.schema.json) | Provider-neutral evidence content and provenance identity |
| [schemas/grounding-frame-v0.1.schema.json](schemas/grounding-frame-v0.1.schema.json) | Grouped per-target grounding states and approved evidence |
| [schemas/grounding-source-snapshot-v0.1.schema.json](schemas/grounding-source-snapshot-v0.1.schema.json) | Immutable source/adapter snapshot identity |
| [schemas/grounding-provider-identity-v0.1.schema.json](schemas/grounding-provider-identity-v0.1.schema.json) | Provider implementation/index/preprocessing/ranking identity |
| [schemas/grounding-preregistration-v0.1.schema.json](schemas/grounding-preregistration-v0.1.schema.json) | Provider-neutral grounding identity record for profile/source/provider/projection/corpus/model/runtime binding; not the full benchmark-run wrapper |
| [schemas/grounding-benchmark-preregistration-v0.1.schema.json](schemas/grounding-benchmark-preregistration-v0.1.schema.json) | Benchmark-specific zero-inference wrapper that additionally freezes source commit, evaluation package, planned output, exact model path/hash, llama.cpp runtime/launch/hardware, scorer/config identities, A/G fairness, no-retry/no-repair and pre-inference state |
| [schemas/xs-find-tool.schema.json](schemas/xs-find-tool.schema.json) | Arguments generated by a model for `xs_find` |
| [schemas/xs-eval-tool.schema.json](schemas/xs-eval-tool.schema.json) | Arguments generated by a model for `xs_eval` |
| [schemas/hotset-source.schema.json](schemas/hotset-source.schema.json) | Build-time direct-eval hot-set selection manifest |
| [schemas/capability-profile.schema.json](schemas/capability-profile.schema.json) | **Design-draft** machine-readable capability-profile identity/budget/evidence shape; not yet a stable release contract |
| [schemas/build-input-identity.schema.json](schemas/build-input-identity.schema.json) | Deterministic current-source/toolchain/feature/input identity for reproducibility requests |
| [schemas/model-surface-contract.schema.json](schemas/model-surface-contract.schema.json) | Exact model-facing asset contract IDs/versions/digests emitted by new capability bundles |
| [schemas/model-surface-acceptance.schema.json](schemas/model-surface-acceptance.schema.json) | Host acceptance policy for supported ABI/hot-set/model-asset contract versions |
| [schemas/release-bundle.schema.json](schemas/release-bundle.schema.json) | Experimental outer integration archive manifest for native-static/no-import-Wasm packaging |
| [schemas/reproducible-build-comparison.schema.json](schemas/reproducible-build-comparison.schema.json) | Canonical MATCH/MISMATCH record for two build outputs under one build-input identity |
| [schemas/scopepack-source.schema.json](schemas/scopepack-source.schema.json) | Build-time source pack validation |
| [schemas/compatibility-manifest.schema.json](schemas/compatibility-manifest.schema.json) | Release target/conformance record; current experimental records may bind exact release/runtime/capability/model-surface identity |
| [schemas/wearable-edge-profile.schema.json](schemas/wearable-edge-profile.schema.json) | Machine-readable wearable product ceilings, targets, and evidence states |
| [schemas/wearable-qualification-record.schema.json](schemas/wearable-qualification-record.schema.json) | Target-device qualification record: device identity, artifact digests, latency, energy, footprint, and destructive-test evidence |

## Grounding reference implementation and benchmark assets

The normative grounding contract is provider-neutral. The repository additionally carries one **benchmark reference implementation** so the first candidate can be reproduced without turning that implementation into the universal product contract:

- `../grounding/reference-profile-v0.1/` — frozen small offline exact/lexical profile, provider/index/source identities, merge policy and byte-exact Model Projection fixtures;
- `../tools/grounding_runtime.py` / `grounding_match.py` — host-side reference router/provider/policy/frame/projection path; it has no benchmark-gold dependency;
- `../tools/generate_grounding_candidate.py` — deterministic serving/gold candidate generator;
- `../benchmarks/grounding_dry_run.py` — zero-inference serving replay and scorer-side gold verification;
- `../benchmarks/grounding_preregister.py` — benchmark-run identity freeze; it verifies actual model/runtime bytes without starting inference;
- `../benchmarks/run_grounding_benchmark.py` — A/G model runner, gated by a frozen preregistration and supporting `--verify-only` for the pre-inference readiness gate;
- `../benchmarks/score_grounding.py` — gold-only scorer;
- `../tools/package_grounding_evaluation.py` / `verify_grounding_package.py` — deterministic clean-room evaluation package and integrity checks.

The reference exact/lexical provider is frozen only for the first benchmark candidate. A vector, application-native, or captured host provider must bind its own implementation/index/scope identity but can reuse the same ProviderOutcome, Evidence Policy and GroundingFrame semantics.

## Canonical ID registries

The machine-readable registries under [`registries/`](registries/README.md) are the source of truth for status codes, semantic kinds, rounding modes, VM opcodes, deterministic kernel IDs, protocol IDs, and the public native/Wasm export allowlists. Generated Rust constants, C constants, inspectors, compiler tables, headers, and prose copies must remain aligned with them.

## Examples

| File | Purpose |
|---|---|
| [examples/econ-undergrad-minimal.xsp.json](examples/econ-undergrad-minimal.xsp.json) | Complete source definition for midpoint price elasticity |
| [examples/tiny-json.jsonl](examples/tiny-json.jsonl) | Model-facing request/response examples |
| [examples/compatibility-manifest.json](examples/compatibility-manifest.json) | Planned release compatibility record |
| [examples/model-surface-acceptance-v0.1.json](examples/model-surface-acceptance-v0.1.json) | Example fail-closed host policy accepting the current v0.1 model-surface contracts |
| [examples/wearable-edge-profile.json](examples/wearable-edge-profile.json) | Canonical wearable product contract and evidence-state fixture |
| [examples/wearable-qualification-record.json](examples/wearable-qualification-record.json) | Draft physical-device qualification record template; contains no product measurements or qualification claim |
| [examples/statistics-capability-profile.json](examples/statistics-capability-profile.json) | Design-only Statistics capability-profile example with explicit null evidence/binding placeholders |

## Normative language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** are to be interpreted as requirement levels.

## Version status

`v0.1` is a prerelease contract baseline, not a stable ecosystem promise. Implementation is already active; therefore:

- incompatible changes to a specification require a visible specification revision;
- fixtures and schemas must be updated in the same commit;
- an existing operation revision may not change semantics;
- releases must state which specification revisions they implement.

## Source versus compiled artifacts

- `.xsp.json` is build-time source intended for review, validation, and compilation.
- `.xsp` is the compact runtime data pack.
- AI-facing Tiny JSON is an adapter protocol.
- TinyWire CBOR is a transport protocol.
- None of these formats contains native executable plugin code.

## Experimental compiler implementation

The build-time [capability compiler](../docs/CAPABILITY_COMPILER.md) validates Statistics/Economics task selections, binds actual operation revisions and canonical model assets, enforces static budgets, emits exact model-surface negotiation metadata, and checks reproducibility. Selected Statistics/Economics profiles can also drive compile-time Wasm specialization. The draft capability/model-surface/release formats remain experimental and do not establish model accuracy, target qualification, or stable platform support.
