# Implementation plan

> **Historical productization plan.** This file records the hot-set/direct-`xs_eval` implementation sequence that established the current adapter, benchmark, and packaging foundation. Several phases below are already implemented and the bounded `xs_calc` lane now exists. Do not use the old 8-32-operation or `xs_eval`-only sequencing as the current product plan. Current work is defined by [`../ROADMAP.md`](../ROADMAP.md) and [`CAPABILITY_PRODUCT_ARCHITECTURE.md`](CAPABILITY_PRODUCT_ARCHITECTURE.md): capability profiles, weak-model difficulty budgets, a flagship Statistics slice, capability-density/CRR evidence, and capability-compiler/qualification work.

This plan was ordered by product proof and adoption leverage. Core correctness invariants stay strict, but v0.1 implementation was no longer organized around making every internal profile equally mature before anyone could evaluate the product.

## 0. Non-negotiable repository rules

- `exactscope-kernel` remains `no_std` and allocator-free by default.
- adapters and wrappers never reimplement formulas, rounding, unit conversion, or classification.
- scope packs remain data-only.
- malformed/ambiguous semantic input fails closed in the core.
- the same operation semantics are shared by every profile that exposes that operation.
- support and performance claims require evidence from exact release artifacts.
- target devices do not require Rust/Python/Node/Java runtimes, a daemon, account, or network.

Rust remains the implementation language. C ABI and wire/data formats remain the portability authority.

## 1. Current checkpoint

The repository already implements enough runtime foundation for product proof:

- deterministic decimal/rational numeric kernel;
- deterministic square root and explicit rounding;
- bounded scalar VM;
- executable economics operations;
- bounded statistics kernels;
- native C ABI with zero-copy vectors;
- current canonical formula/kernel `.xsp` path;
- fused/dynamic shared statistics semantics;
- no-import WebAssembly;
- Tiny JSON and TinyWire;
- experimental wearable/ARM64 integration;
- relocatable CMake SDK target;
- developer-side SDK doctor;
- CI across the implemented paths.

Therefore new work is sequenced as follows:

```text
one-hop AI integration
    -> benchmark evidence
    -> five-minute/prebuilt evaluation
    -> reviewed hot-set content
    -> stable primary packages
    -> broader packs/platforms/profiles
```

## 2. Phase A — hot-set/direct AI integration (P0)

### A1. Hot-set metadata generator

Implement a build/dev tool that selects 8-32 installed operations and emits deterministic metadata bound to:

- core ABI version;
- registry/pack digest;
- operation key/revision;
- compact signature and method cue;
- argument names/order/semantic kinds.

Required outputs should include a machine-readable hot catalog and enough metadata for adapter/grammar generation.

Exit criteria:

- byte-reproducible generation;
- digest/revision binding;
- invalidation test when registry digest changes;
- no full-catalog prompt required.

### A2. OpenAI-compatible tool assets

Generate conservative tool-call definitions for:

- primary `xs_eval` direct path;
- optional `xs_find` fallback.

The direct path should be the first example and benchmark path.

Exit criteria:

- fixture validation;
- exact decimal preservation;
- status/provenance preservation;
- no adapter calculation.

### A3. GBNF

Generate/check in reproducible grammar for:

- direct eval requests;
- optional discovery requests;
- selected hot-set operation key constraints where practical.

Exit criteria:

- llama.cpp-compatible fixture parsing;
- grammar digest captured by benchmark records;
- invalid tool-call rate measurable.

### A4. llama.cpp reference integration

Add one minimal reference that demonstrates:

```text
local model -> generated hot-set/direct eval -> ExactScope -> result
```

No custom calculation code is allowed in the adapter.

Exit criteria:

- runnable against at least one selected GGUF model/runtime configuration;
- direct hot path works without `xs_find`;
- cold discovery remains optional fallback.

## 3. Phase B — benchmark (P0)

Implement the harness in `docs/BENCHMARK.md` before expanding the catalog for its own sake.

Required comparison arms:

1. model only;
2. model + direct `xs_eval` hot path;
3. model + `xs_find -> xs_eval` cold path;
4. direct path with constrained decoding/GBNF.

Required model classes:

- sub-1B;
- 1B-2B;
- about 3B;
- optional routing-specialized model.

Required metrics:

- recognition;
- operation selection;
- argument extraction/order;
- syntax validity;
- core acceptance/rejection;
- final answer accuracy;
- result/failure fidelity;
- successful-answer rate;
- wrong-number rate;
- model inference turns;
- prompt/completion tokens;
- end-to-end latency;
- ExactScope compute latency;
- resident/scratch bytes;
- energy where measurable.

Exit criteria:

- machine-readable per-item output;
- reproducible aggregate report;
- explicit fail-closed tradeoff analysis;
- no unsupported marketing claim.

## 4. Phase C — five-minute evaluation and prebuilt artifacts (P0)

The evaluator should not need to build the Rust workspace.

### C1. Native evaluation bundle

Produce a release-shaped native archive with:

- public headers;
- static library;
- `ExactScopeConfig.cmake`;
- manifest/checksums/licenses;
- small benchmark hot-set metadata;
- workstation doctor;
- smoke instructions.

### C2. No-import Wasm evaluation bundle

Produce:

- `.wasm`;
- manifest/checksum;
- hot-set metadata;
- TinyWire/Tiny JSON examples;
- smoke test.

### C3. Clean-room quickstart test

CI should test the documentation path from staged release-shaped artifacts rather than importing files from the development tree accidentally.

Exit criteria:

- non-Rust evaluator can run a known operation quickly;
- direct hot path is the default example;
- no target daemon/runtime dependency.

## 5. Phase D — benchmark hot sets (P1)

Select a small reviewed cross-domain set before requiring the entire frozen catalog.

Suggested initial shape:

- a handful of high-frequency math operations;
- implemented statistics mean/variance/stddev/correlation/regression operations;
- high-value deterministic economics operations such as CPI inflation, GDP deflator, real-rate, elasticity/growth helpers.

Every shipped benchmark operation requires:

- canonical method/key;
- input semantics/order;
- deterministic formula/kernel;
- constraints/unit policy;
- rounding policy;
- provenance;
- valid/invalid/boundary/overflow/precision vectors.

Exit criteria:

- enough quality to support public benchmark claims;
- small enough to keep prompt/hot-set size measured.

## 6. Phase E — stable primary release profiles (P2)

### E1. Native static C ABI

Primary native profile requirements:

- no required allocator in fused/static evaluation;
- C99/C++11 header conformance;
- exact release artifact manifest/digest;
- native conformance/golden/malformed-input suite;
- relocatable CMake package;
- target smoke/self-test.

### E2. No-import WebAssembly

Primary portable profile requirements:

- zero imports/WASI;
- WebAssembly 1.0 baseline contract;
- TinyWire/direct eval path;
- artifact inspection;
- runtime conformance against the exact release bytes;
- size budget measurement.

The v0.1 product can ship focused support when these profiles and the benchmark are strong. Dynamic-pack and universal platform maturity are not prerequisites.

## 7. Phase F — reviewed official pack expansion (P1/P3)

After the benchmark hot set proves value:

1. complete `math-basic` 16 operations;
2. complete `statistics-core` 18 operations;
3. complete `econ-undergrad` 65 operations;
4. expand golden/provenance coverage;
5. add additional domains only from demonstrated demand.

Full catalog count is not a success metric by itself.

## 8. Phase G — platform convenience packages (P2)

Implement only after primary evaluation paths are usable:

- Android AAR/Prefab for evidenced ABI(s);
- Linux archives;
- Windows archive;
- Apple Silicon/macOS package;
- iOS/XCFramework only when a real host-app path justifies it.

Wrappers remain calculation-free.

## 9. Phase H — real target qualification (P2)

For at least one constrained target record:

- exact artifact digest;
- stripped/runtime bytes;
- context/scratch/vector transport memory;
- latency distribution;
- energy where measurable;
- offline/radio-free execution;
- malformed-input behavior;
- update/rollback evidence where applicable.

A compile-only target remains Experimental.

## 10. Phase I — dynamic profile maturity (P3)

Dynamic packs are maintained as useful architecture, but no longer lead the release plan.

Future work:

- every intended `.xsp` operation shape;
- stronger malformed corpus/fuzzing;
- dynamic alias-index discovery parity;
- release manifest integration;
- adoption-driven update workflows.

Shared evaluator semantics remain mandatory wherever an operation is exposed.

## 11. Numeric/core maintenance

Core correctness remains release-critical even though product priorities changed.

Every runtime PR should preserve:

- deterministic numeric conformance;
- no-panic malformed input paths;
- bounded resource use;
- ABI/wire compatibility;
- no hidden allocation regressions;
- no adapter calculation fork.

## 12. Fail-closed usability work

Do not weaken semantic validation to improve call success.

Instead implement/measure:

- grammar-constrained output;
- compact signatures/argument names;
- allowed lexical/transport normalization;
- operation hot sets;
- exact error/status feedback;
- successful-answer rate versus wrong-number rate.

This is how the project decides whether fail-closed is a practical UX advantage rather than only a correctness principle.

## 13. Pull-request gates

Runtime/core changes:

- format/lint/check/test;
- no_std/default-feature checks;
- C ABI tests;
- Wasm build/import inspection when affected;
- conformance/golden vectors;
- size/dependency regression where relevant;
- malformed/fuzz smoke where available.

Adapter/hot-set changes:

- generated-artifact reproducibility;
- schema/GBNF fixtures;
- exact decimal preservation;
- digest binding;
- no-calculation review;
- benchmark fixture compatibility.

Official pack changes:

- source schema/semantic validation;
- identity/alias checks;
- provenance;
- golden/negative vectors;
- compiler reproducibility;
- shared-semantic conformance for every shipped profile that exposes the operation.

## 14. Definition of focused v0.1 complete

A focused v0.1 can be complete without universal catalog/platform parity when:

1. direct hot-set `xs_eval` integration is runnable;
2. generated OpenAI-compatible/GBNF assets exist;
3. at least one local-runtime reference integration exists;
4. reproducible benchmark evidence exists and exposes failure/cost breakdowns;
5. a reviewed benchmark hot set exists;
6. a stable prebuilt native static and/or no-import Wasm artifact can be evaluated without Rust;
7. exact release artifacts pass conformance and malformed-input tests;
8. at least one constrained target has real resource/latency measurements;
9. documentation states the exact shipped operation/profile scope;
10. no unsupported performance/accuracy/support claim is made.

Full 99-operation completion, dynamic discovery, Android/iOS packaging, or every architecture reaching Tier 1 may follow after this proof.
