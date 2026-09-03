# Implementation plan

This plan is ordered to preserve compatibility and deterministic semantics. Later phases must not be used to bypass incomplete earlier contracts.

## 0. Repository rules

Before runtime code is accepted:

- core behavior must trace to a normative specification;
- every public operation must have golden vectors;
- baseline crates must build without network/runtime service dependencies;
- default kernel features must remain `no_std` and allocator-free;
- adapters may not reimplement calculation logic;
- compatibility claims require the matrix in `docs/COMPATIBILITY.md`.

Selected implementation language: Rust for the core, pack loader/compiler, ABI wrapper, and WebAssembly build. The checked-in workspace and toolchain policy are now frozen. The portability authority remains the C ABI and data formats, not the Rust API.

## 1. Frozen crates and dependency policy

| Crate | Runtime class | Default allocation | Dependency policy |
|---|---|---:|---|
| `exactscope-kernel` | required | none | ideally zero external dependencies |
| `exactscope-pack` | required except fully fused build | none | zero or narrowly audited no_std dependencies |
| `exactscope-cabi` | native wrapper | none | kernel/pack only |
| `exactscope-wasm` | portable wrapper | none | kernel/pack only |
| `exactscope-tinyjson` | optional adapter | caller buffer | small no_std-capable parser or project-owned bounded parser |
| `exactscope-packc` | build-time desktop tool | allowed | `serde`, JSON Schema validation, hashing, CLI dependencies allowed |
| `exactscope-conformance` | test/dev | allowed | test-only dependencies allowed |

Default features must never pull `std`, logging frameworks, async runtimes, HTTP stacks, TLS, Unicode databases, or general serialization frameworks into the fused kernel.

## 2. Milestone M0 — specifications and fixtures

Deliverables:

- numeric model specification;
- status/error code specification;
- scope-pack source schema;
- binary pack format specification;
- Tiny JSON tool schemas;
- TinyWire CBOR/framing specification;
- one complete economics operation example;
- malformed pack and request fixture descriptions;
- compatibility matrix and engineering budgets.

Exit criteria:

- every JSON document validates;
- examples agree across README and specs;
- no unresolved semantic choice remains for the first example operation;
- operation identity/versioning rules are frozen for ABI major 1.

M0 is complete at the design/scaffold level. `python tools/validate_design.py` is the authoritative local check for schema, registry, example, VM-shape, CRC-contract, and public-header alignment. M0 completion does not imply that any runtime calculation is implemented.

## 3. Milestone M1 — deterministic numeric kernel

Implement in order:

1. `Decimal64` lexical parser;
2. canonicalization;
3. checked add/subtract/multiply/divide;
4. comparison and absolute value;
5. integer power;
6. explicit rounding modes;
7. deterministic fixed-point square root;
8. canonical decimal formatter;
9. semantic/unit metadata representation;
10. result/provenance structure.

Required tests:

- zero and negative zero;
- minimum/maximum coefficient;
- exponent alignment;
- every overflow path;
- division tie cases;
- all rounding modes;
- scientific notation boundaries;
- invalid lexical forms;
- cross-check against a high-precision reference implementation;
- byte-identical output on native and WebAssembly targets.

Exit criteria:

- no panics under property tests;
- no allocation in the default kernel;
- all numeric conformance vectors pass;
- footprint recorded for `wasm32v1-none` and one native target.

## 4. Milestone M2 — formula VM and kernels

Implement scalar VM:

- validated RPN program representation;
- static stack analysis;
- instruction limit enforcement;
- runtime checked stack;
- all v0.1 opcodes;
- classification table evaluation over the unrounded result.

Implement initial bounded vector kernels:

- sum;
- arithmetic mean;
- weighted mean;
- population variance;
- sample variance;
- covariance;
- correlation;
- simple linear regression.

All vector algorithms must define iteration order, intermediate precision, denominator behavior, and output rounding.

Exit criteria:

- malformed programs are rejected before registration;
- runtime cannot jump or loop based on pack bytecode;
- vector length caps are enforced before work begins;
- formula and kernel golden vectors pass on all available targets.

## 5. Milestone M3 — pack compiler and loader

### Compiler

Implement:

- JSON Schema validation;
- source semantic validation;
- stable operation-key and ID checks;
- alias normalization and deterministic index generation;
- VM stack/resource analysis;
- golden-vector execution;
- canonical `.xsp` serialization;
- CRC and manifest generation;
- fused-table generation.

### Loader

Implement:

- header/version validation;
- safe section decoding without struct casts;
- CRC verification;
- count/offset/length overflow checks;
- UTF-8 and string-table checks;
- operation/program validation;
- static and caller-arena registration;
- immutable registry freeze.

Exit criteria:

- compiler output is byte-reproducible;
- load-then-reserialize tests are unnecessary because runtime never rewrites packs;
- truncation at every input byte fails safely;
- fuzzing finds no panic, out-of-bounds access, or uncontrolled allocation;
- fused and dynamic execution produce identical canonical results.

## 6. Milestone M4 — C ABI and WebAssembly

### C ABI

Implement the logical surface already frozen in `include/exactscope.h`, keep it aligned with `spec/CORE_ABI_V0_1.md`, and add:

- generated Rust constants/layouts checked against canonical registries and the header;
- C99 compile test;
- C++11 compile test;
- struct size/offset assertions on 32- and 64-bit targets;
- buffer-sizing tests;
- invalid pointer/length/overlap contract tests where safely testable;
- non-panicking malformed-input paths and proof that no unwind crosses `extern "C"`;
- optional desktop `catch_unwind` containment only where the build uses unwind semantics.

### WebAssembly

Implement `wasm32v1-none` exports exactly as frozen in `include/exactscope_wasm.h` and `spec/WASM_ABI_V0_1.md`, including:

- no imports or WASI;
- one exported 32-bit memory;
- exported module-reserved boundary and required alignment;
- caller-owned nonoverlapping request/output/meta regions;
- allocator-free one-call Tiny JSON helper;
- abort-only panic policy with malformed-input no-trap tests;
- the same status codes and canonical result bytes as native;
- import/feature/export inspection in CI.

Exit criteria:

- C and Wasm conformance suites pass;
- stripped no-pack Wasm core meets the size budget or a measured design review is opened;
- WAMR or another WebAssembly 1.0 embedded runtime executes the conformance sample;
- no host-specific calculation path exists.

## 7. Milestone M5 — Tiny JSON and TinyWire

Implement Tiny JSON first because it is the direct model-facing boundary.

Requirements:

- bounded flat-object parser;
- exact decimal strings;
- two operations only: find and eval;
- stable compact responses;
- no generic JSON DOM requirement in the minimum adapter;
- pre-generated GBNF fixtures.

Then implement TinyWire:

- deterministic CBOR subset;
- decimal tag 4;
- integer map keys;
- stream framing and CRC;
- in-process payload mode without framing;
- golden byte fixtures.

Exit criteria:

- all fixture bytes match the specification;
- malformed input never reaches evaluation;
- adapter overhead is measured separately from core size;
- model-generated requests round-trip without numeric precision loss.

## 8. Milestone M6 — first official packs

### `math-basic`

Initial target operations:

- add/subtract/multiply/divide;
- percent of;
- percent change;
- successive percentage changes;
- ratio and proportion;
- weighted mean;
- linear equation with one unknown;
- integer powers and roots within baseline support;
- common rounding operations.

### `statistics-core`

Initial target operations:

- sum/count/mean;
- weighted mean;
- population/sample variance;
- standard deviation;
- z-score;
- covariance;
- correlation;
- simple linear regression;
- standard error and basic confidence intervals only where assumptions are explicit.

### `econ-undergrad`

Initial target: the 65 operations frozen in `packs/CATALOG_V0_1.md` across microeconomics, macroeconomics, labor, international economics, and growth. Each alternative method must be a separate operation key; compound finance operations remain deferred until deterministic integer-power kernels are specified.

Pack acceptance:

- at least 20 golden vectors per operation before stable release;
- at least one invalid-input vector per constraint;
- source citation metadata;
- no unsupported forecasting or empirical coefficient claims;
- pack size recorded in source and compiled form.

## 9. Milestone M7 — AI adapters

Implement in this order:

1. generic OpenAI-style tool definitions;
2. llama.cpp JSON and checked-in GBNF fixtures;
3. Android/Kotlin convenience wrapper;
4. optional MCP adapter;
5. additional runtime integrations based on real adoption.

Adapters are thin translations. They must share generated schemas and fixture tests.

Exit criteria:

- no calculation code in adapters;
- no catalog drift between installed packs and generated tool hints;
- at least three small local models produce valid direct/discovery calls under constrained decoding;
- failures are reported, not repaired with hidden model reasoning.

## 10. Milestone M8 — packaging

Produce:

- no-import fused economics Wasm;
- generic core Wasm plus `.xsp` packs;
- native Linux AArch64/x86-64 archives;
- Windows x86-64 archive;
- Android AAR with selected ABIs;
- macOS static library, then XCFramework when iOS is ready;
- SHA-256 checksums;
- compatibility manifest;
- SBOM for release tooling and adapters.

Installation tests must start from release artifacts, not the development tree.

## 11. Milestone M9 — benchmark

Benchmark model-only versus model-plus-ExactScope using fixed prompts and exact expected outputs.

Models should include at least:

- one sub-1B local model capable of constrained JSON;
- one 1B–2B model;
- one 3B model;
- one routing-specialized tiny model if available.

Metrics:

- decision to call the tool;
- operation selection;
- argument extraction/order;
- tool-call syntax validity;
- final numeric accuracy;
- classification accuracy;
- ambiguity/error fidelity;
- prompt and completion tokens;
- wall-clock latency;
- memory and energy where measurable.

Do not report a single blended accuracy score without exposing the stage-level failure breakdown.

## 12. Initial operation-key allocation

Official key prefixes:

```text
math.*
stats.*
econ.*
finance.*
```

Numeric IDs are pack-local unsigned 32-bit values. Suggested official source ranges:

```text
math-basic:       1–999
statistics-core:  1–999
econ-undergrad:   1–1999
```

Numeric IDs are never used without a pack slot/digest context. Canonical string keys are the durable cross-pack identity visible to adapters.

## 13. Pull-request gates after implementation begins

Every runtime PR must run:

- formatting and lint;
- unit tests;
- pack/compiler schema tests;
- conformance vectors;
- native C ABI tests;
- `wasm32v1-none` build and import inspection;
- no-default-features/no-allocator build;
- size regression check;
- dependency-policy check;
- fuzz smoke tests for parsers where available.

Every official pack PR must run:

- source schema validation;
- duplicate identity/alias checks;
- complete golden vectors;
- compiler reproducibility;
- fused/dynamic equivalence;
- operation catalog diff requiring explicit review for semantic changes.

## 14. Definition of v0.1 complete

v0.1 is complete only when:

- all M1–M8 exit criteria pass;
- `math-basic`, `statistics-core`, and `econ-undergrad` are installable;
- one fused no-import economics Wasm artifact exists;
- one Android AAR and one Linux native archive pass installation tests;
- the public C ABI is documented and tested;
- every official operation has provenance and golden vectors;
- the compatibility manifest contains no fabricated support claim;
- benchmark tooling exists, even if broad model results are released later.
