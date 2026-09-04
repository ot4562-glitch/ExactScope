# Compatibility contract

Compatibility is evidence attached to a released artifact, not a statement that the source code compiled somewhere.

The current product strategy deliberately separates **primary v0.1 release profiles** from broader experimental architecture so universal platform/profile parity does not delay the first product proof.

## 1. Support vocabulary

- **Tier 1:** exact release artifact is release-blocking, conformance-tested, and executed on the declared real/official-emulator target with recorded resource evidence.
- **Tier 2:** exact release artifact is automated and conformance-tested, but hardware/runtime evidence is narrower.
- **Experimental:** build/integration evidence exists but compatibility is not promised.
- **Planned:** design/roadmap target only.

No README badge or release note may call an artifact supported without the corresponding evidence.

## 2. Primary v0.1 compatibility scope

### Primary candidates

1. **Native static C ABI**
2. **No-import `wasm32v1-none`**

These profiles receive the first stable quickstart, prebuilt artifacts, benchmark integration, and qualification effort.

### Secondary/experimental

- dynamic-pack profile;
- dynamic discovery;
- Android/iOS convenience wrappers;
- wider native OS/architecture matrix;
- embedded/bare-metal targets;
- additional shared-library profiles.

The invariant is that any profile exposing the same operation uses the same shared calculation semantics. It is **not** a v0.1 requirement that every profile and platform reach Tier 1 simultaneously.

## 3. Current evidence snapshot

| Path | Current evidence | Current claim |
|---|---|---|
| Native scalar/statistics C ABI | unit/conformance tests; zero-copy vector path; CI | implemented runtime path |
| Dynamic statistics `.xsp` path | shared kernel and fused/dynamic parity tests for implemented slice | implemented secondary path |
| No-import Wasm | zero-import inspection; Tiny JSON/TinyWire runtime tests; scalar/vector evaluation | implemented primary candidate, not stable Tier 1 yet |
| Android AArch64 experimental SDK | CI cross-build, packaging, CMake target, doctor | Experimental |
| Linux AArch64 musl experimental SDK | CI cross-build, packaging, doctor/ELF checks | Experimental |
| Wearable reference | C host, A/B, benchmark/qualification framework | integration reference, not generic device support |
| Real constrained-target performance | incomplete | no performance Tier claim |
| Stable release artifacts | not yet published | prerelease project |

## 4. What a supported artifact must prove

For the same immutable release artifact:

1. documented clean integration/build path;
2. ABI/wire conformance;
3. canonical golden vectors;
4. malformed request/pack behavior where relevant;
5. artifact identity/digest;
6. size/memory records;
7. actual runtime execution on the declared target/runtime;
8. required self-test success;
9. exact operation/hot-set scope documented.

Performance claims additionally require the actual target used for the claim.

## 5. Native static C ABI requirements

The C ABI remains the native cross-language authority.

Required properties:

- C99-compatible fixed-width declarations;
- no Rust layout in public ABI;
- caller-owned buffers/context/scratch;
- stable status codes;
- no required allocator in the fused/static path;
- no panic/exception/unwind crossing the boundary;
- no required runtime service/thread;
- operation semantics independent of host language.

Tier evidence should include:

- C99/C++11 header compile tests;
- ABI layout/version checks;
- buffer sizing/error tests;
- direct hot-set `xs_eval` smoke test;
- exact release archive digest;
- platform runtime execution.

## 6. WebAssembly baseline

The primary portable artifact uses `wasm32v1-none` and must not require:

- WASI;
- host imports;
- threads/shared memory;
- SIMD for correctness;
- reference types/GC/exceptions/memory64;
- filesystem/clock/random/socket imports.

Required release evidence:

- zero-import inspection;
- documented memory/export contract;
- direct eval/TinyWire smoke execution;
- canonical result conformance;
- artifact size/digest;
- execution in at least one declared runtime.

## 7. Direct-hot-path compatibility

A product integration is considered compatible only when its hot-set binding cannot silently drift from the runtime.

A hot-set artifact should bind:

- core/ABI version;
- registry/pack digest;
- operation key and revision;
- compact signature/argument order.

On mismatch:

- invalidate the binding;
- regenerate/rebind;
- never substitute a different method or operation.

`xs_find` remains available as fallback where enabled, but repeated known operations should not require discovery.

## 8. Adapter compatibility

Generated OpenAI-compatible/GBNF/llama.cpp assets are compatibility artifacts in their own right.

They require:

- deterministic/reproducible generation;
- exact decimal preservation;
- hot-set digest binding;
- no hidden calculation/semantic repair;
- fixture tests for valid/error cases;
- benchmark records identifying the exact adapter/grammar digest.

A model adapter cannot be called compatible merely because it produced parseable JSON once.

## 9. Fail-closed compatibility

The core remains strict. Compatibility testing must include both acceptance and rejection behavior.

Required negative classes include:

- wrong argument count/order;
- invalid lexical decimals;
- unsupported operation;
- ambiguous method where discovery is used;
- domain errors;
- zero denominator;
- resource/vector limits;
- pack corruption/truncation where applicable.

Adapters may apply allowed syntactic normalization but cannot repair semantic errors.

## 10. Data/pack portability

`.xsp` is canonical little-endian and contains offsets rather than native pointers. Loaders decode fields explicitly and validate every offset/count/length.

Dynamic packs remain Experimental until their intended release profile has complete loader/discovery/update evidence. Their existence does not block the primary native/Wasm product release.

## 11. CPU policy

The correctness path remains scalar.

- SIMD/CPU-specific acceleration is optional;
- acceleration requires identical canonical results and scalar fallback;
- baseline correctness must not require a specific FPU mode;
- product claims must identify the artifact/CPU profile used.

## 12. Platform packaging policy

Android, Apple, Windows, Linux, or other wrappers are convenience distribution layers around the same shared core.

A wrapper:

- may translate lifecycle/protocol/buffer types;
- may package headers/libraries/manifests;
- may package the selected capability profile and its tool/schema/GBNF/prompt assets;
- may not implement formulas/rounding/classification/unit conversion.

Only ABI slices with exact release evidence belong in a supported package.

## 13. Wearable/device claims

“Wearable support” is too broad to be a compatibility claim.

Documentation must identify the actual execution boundary:

- native application/plugin;
- WebAssembly runtime;
- Android/native host;
- paired phone/compute host;
- vendor extension environment.

A closed device without a legitimate product-controlled executable boundary cannot be retrofitted by ExactScope independently. ExactScope is integrated by the product team; it is not an end-user installation target.

## 14. Conformance corpus priorities

Primary release conformance covers:

- decimal lexical/canonical behavior;
- arithmetic/rounding/sqrt boundaries;
- scalar VM/kernel vectors;
- statistics vectors;
- classification-before-rounding;
- C ABI/TinyWire buffer/status behavior;
- direct hot-set operation identity;
- malformed request behavior;
- no-import Wasm inspection;
- adapter fixtures where shipped.

Dynamic pack corruption/offset/string/duplicate tests remain mandatory for any release that ships dynamic packs.

## 15. Performance/resource evidence

For any target used in marketing/product claims, record:

- artifact bytes;
- context bytes;
- eval scratch bytes;
- vector transport/copy bytes;
- p50/p99 ExactScope compute latency where relevant;
- end-to-end latency separately;
- energy where measurable;
- runtime/hardware/toolchain configuration.

Do not extrapolate one hardware measurement to another platform.

## 16. Benchmark compatibility

A published model benchmark must record the exact:

- ExactScope artifact digest;
- hot-set/pack digest;
- operation revisions;
- adapter schema/GBNF digest;
- model/runtime/quantization/hardware settings;
- benchmark dataset revision.

See [BENCHMARK.md](BENCHMARK.md).

## 17. Release promotion rule

An Experimental path becomes Tier 2/Tier 1 only after evidence is produced for the immutable artifact being promoted.

A green source-tree CI run from another commit cannot retroactively qualify a release artifact.

## 18. Product-scope rule

A focused v0.1 may ship with a narrow operation/profile/target matrix if that scope is clearly documented and benchmark-backed.

The project should prefer:

```text
small supported scope + strong evidence
```

over:

```text
wide matrix + compile-only claims
```
