# Rust workspace boundaries

The workspace contains a real executable runtime, not just the original vertical slice: deterministic scalar/vector evaluation, canonical `.xsp` compilation/loading for the implemented shapes, Tiny JSON/TinyWire, typed C ABI, no-import WebAssembly, executable economics operations, and exact statistics kernels with zero-copy C ABI vector inputs. Continue filling the existing crates in place without moving calculation responsibilities across compatibility boundaries. The current v0.1 priority is product proof—direct hot-set integration, AI adapters, benchmark evidence, and prebuilt evaluation—rather than expanding every runtime profile in parallel. See [`../ROADMAP.md`](../ROADMAP.md) and [`../docs/IMPLEMENTATION_PLAN.md`](../docs/IMPLEMENTATION_PLAN.md).

## Crates

### `exactscope-kernel`

Required, `#![no_std]`, no default allocator, preferably no external dependencies.

Owns:

- `Decimal64` and exact bounded work arithmetic;
- rounding and canonical formatting;
- scalar VM and deterministic kernels;
- semantic kinds, constraints, relations, classifications;
- core status/result types.

Must not own:

- files, sockets, clocks, random state, environment variables;
- JSON/CBOR DOMs;
- language-model APIs;
- pack source parsing;
- platform-specific code.

### `exactscope-pack`

Required for static/dynamic `.xsp` loading; optional in a fully generated fused artifact.

Owns:

- safe binary pack decoding;
- structural and semantic pack validation;
- immutable registry and alias lookup;
- caller-arena sizing;
- fused/dynamic representation equivalence.

Default feature remains `no_std` and allocation-free.

### `exactscope-cabi`

Thin native ABI wrapper.

Owns:

- generated `exactscope.h` compatibility;
- pointer/length validation;
- in-place context construction;
- panic containment;
- exported-symbol control.

Contains no calculation semantics.

### `exactscope-wasm`

Thin `wasm32v1-none` wrapper.

Owns:

- no-import exports;
- linear-memory pointer/length validation;
- optional one-call TinyWire/Tiny JSON helper;
- fused profile artifact generation.

Contains no duplicate evaluator.

### `exactscope-tinyjson`

Optional model-facing adapter.

Owns:

- bounded parsing of the two request schemas;
- decimal string conversion;
- compact canonical response serialization;
- generated GBNF fixtures.

It is excluded from minimum typed C ABI deployments.

### `exactscope-packc`

Desktop build-time compiler using `std`.

Owns:

- JSON Schema and semantic validation;
- RPN compilation and stack analysis;
- canonical `.xsp` emission;
- source/golden-vector execution;
- manifests and fused-table generation.

This is the only official component that parses reviewed source-pack JSON.

### `exactscope-conformance`

Development/test harness.

Owns:

- shared vectors;
- native/Wasm byte-result comparison;
- ABI layout and symbol tests;
- malformed-pack/request corpus;
- release compatibility manifest generation.

## Feature policy

Proposed feature flags:

```text
exactscope-kernel: no default features
exactscope-pack:   default = []
                  alloc = optional dynamic convenience structures
exactscope-cabi:   fused, dynamic-packs, discovery
exactscope-wasm:   fused, dynamic-packs, tinyjson, tinywire
```

Rules:

- `std` is never a transitive dependency of the kernel;
- `alloc` is never required for fused/static evaluation;
- discovery may be disabled for a direct-operation appliance build;
- disabled capabilities return stable unsupported status rather than changing unrelated semantics;
- feature combinations used in releases receive distinct conformance records.

## Unsafe-code policy

The kernel and pack semantic layers should use `#![forbid(unsafe_code)]` where possible. Unsafe code is isolated in ABI/memory modules and requires:

- a documented safety invariant beside each block;
- negative tests;
- fuzz coverage when parsing or pointer arithmetic is involved;
- review as a compatibility/security change.

## Dependency admission

A runtime dependency requires a written review of:

- `no_std` and allocator behavior;
- supported architectures;
- panic/unsafe behavior;
- binary-size impact for no-pack and fused Wasm;
- license;
- maintenance risk;
- whether a small internal implementation would have a narrower surface.

Build-time and test dependencies are less restricted but must not leak into release artifacts.

## Historical first code slice

The project originally started with one vertical path only:

```text
Decimal64
  -> VM subset needed by econ.ped.mid
  -> minimal fused registry
  -> C ABI eval
  -> wasm32v1-none eval
  -> Tiny JSON eval
  -> shared golden vectors
```

That first slice established the one-shared-semantics rule and is now historical. It must not be read as requiring every execution profile to reach the same release tier before a focused product release. Current primary v0.1 product profiles are native static C ABI and no-import Wasm; dynamic breadth is secondary. See the current product/implementation documents for sequencing.
