# ExactScope architecture baseline v0.1

This document defines the runtime architecture. Product priority is defined in `PRODUCT_DIRECTION.md`; where an older architecture emphasis conflicts with the current product priority, the shared-core invariants remain binding while release sequencing follows the product direction.

## 1. System boundary

ExactScope is a deterministic quantitative execution component embedded inside another AI system.

The host owns:

- model inference and natural-language understanding;
- sensor/UI input and output;
- extraction of candidate values from the request;
- model/tool routing;
- hot-set selection and cache binding;
- optional discovery invocation;
- storage, updates, authentication/signature policy, and lifecycle.

ExactScope owns:

- exact operation identity;
- input count/type/semantic/constraint validation;
- unit compatibility checks;
- deterministic calculation;
- explicit rounding/classification;
- stable status/error codes;
- pack/operation provenance.

ExactScope does not own model inference, retrieval, forecasting, live market/economic data, arbitrary code execution, or general symbolic reasoning.

## 2. Primary product call path

The primary steady-state path is one-hop direct evaluation:

```text
small/local model
    -> xs_eval(known operation,args)
    -> ExactScope core
    -> deterministic result
```

`xs_find` is a cold-path discovery helper:

```text
unknown operation
    -> xs_find
    -> bind/cache canonical operation against registry digest
    -> xs_eval
```

Subsequent calls should use the cached/bound operation directly until the registry digest or operation revision changes.

This architecture deliberately avoids making a second model inference turn mandatory for common operations.

## 3. Hot-set architecture

A product normally exposes a small generated hot set rather than the full catalog.

```text
installed packs/registry
        |
        v
 hot-set generator
        |
        +--> compact catalog/hints
        +--> OpenAI-compatible tool asset
        +--> GBNF
        +--> registry/pack digest binding
        |
        v
 small model direct xs_eval
```

The hot set is host/product metadata. It is not a second formula catalog and may not change operation semantics.

## 4. Strict semantic core and adapter boundary

The core remains fail-closed for semantic uncertainty and invalid input.

Adapters may normalize transport syntax, but may not:

- calculate;
- round/classify independently;
- infer missing values;
- silently convert units/rates/currencies;
- choose ambiguous methods;
- turn an ExactScope error into a plausible number.

This separation is central to benchmark design: the project must measure whether constrained decoding/hot sets make strict validation practical for small models.

## 5. Workspace boundaries

```text
crates/
  exactscope-kernel/      # no_std numeric model, VM, validation, kernels
  exactscope-pack/        # pack parser/registry; allocation optional by profile
  exactscope-cabi/        # stable C ABI wrapper
  exactscope-wasm/        # wasm32v1-none exports, no imports
  exactscope-tinyjson/    # bounded JSON adapter
  exactscope-packc/       # desktop/build-time pack compiler
  exactscope-conformance/ # shared conformance/golden runner
adapters/
  wearable/               # implemented integration reference
  llama-cpp/              # planned P0 product adapter
  openai-tools/           # planned P0 generated protocol assets
packs/
include/
spec/
docs/
```

## 6. `exactscope-kernel`

Required properties:

- `#![no_std]`;
- no global allocator in the default feature set;
- no filesystem/sockets/clocks/environment/process APIs;
- no mutable global state;
- no binary floating point in the deterministic baseline;
- bounded VM instructions/stack/vector/output sizes;
- malformed external input follows checked non-panicking paths;
- no unwind/exception/trap crosses a public ABI boundary.

Responsibilities:

- Decimal64 parsing/canonicalization;
- exact checked rational/decimal work arithmetic;
- deterministic square root/rounding;
- scalar formula VM;
- bounded statistics/other numeric kernels;
- input semantic constraints;
- deterministic classification;
- canonical result formation.

Caller-owned vectors are read through bounded source abstractions in deterministic index order. The C ABI fused statistics path is zero-copy and does not copy an entire vector into scratch.

## 7. `exactscope-pack`

Scope packs are data only.

The loader:

- validates format/ABI/version/CRC;
- validates offsets, counts, strings, operation identity, and resource limits;
- rejects malformed/duplicate/unsupported entries;
- validates formula programs/kernel declarations;
- mounts immutable caller-owned bytes where dynamic/static registry profiles use packs.

No pack dynamically links native code.

Dynamic packs are a secondary profile for v0.1 product sequencing. Their semantics remain shared with fused/static paths, but full dynamic-discovery maturity does not block the first product proof.

## 8. `exactscope-packc`

Build-time/desktop tool only. It may use `std` and ordinary development dependencies.

Responsibilities include:

- source/schema validation;
- semantic/identity checks;
- VM/resource validation;
- golden-vector execution;
- canonical `.xsp` serialization;
- manifests/digests;
- optional fused tables;
- product hot-set/adapter metadata generation as P0 work evolves.

The target runtime does not contain a general expression parser.

## 9. Stable ABI boundaries

### Native C ABI

The public C ABI is the primary native portability boundary.

Properties:

- fixed-width C99 structures;
- opaque context;
- caller-owned buffers;
- no required allocator;
- stable status codes;
- no Rust layout exposure;
- no callback/thread/runtime requirement in the baseline.

### No-import WebAssembly

The portable primary profile uses `wasm32v1-none`:

- WebAssembly 1.0 baseline;
- zero host imports/WASI;
- exported memory and explicit caller regions;
- TinyWire/direct typed evaluation paths;
- no filesystem/network/clock/random dependency.

## 10. Product release profiles

The architecture supports more than the first product needs.

### Primary v0.1 candidates

1. native static C ABI;
2. no-import WebAssembly.

These are the release profiles that should receive first-class prebuilt artifacts, quickstart, benchmark integration, and qualification.

### Secondary/experimental profiles

- dynamic data packs;
- static embedded `.xsp` registries;
- shared-library/mobile wrappers;
- additional OS/architecture variants.

All exposed operations must use shared semantics, but these profiles may remain Experimental without blocking focused v0.1.

## 11. Execution pipeline

Direct hot path:

```text
model/tool request
  -> adapter envelope/syntax validation
  -> canonical operation binding lookup
  -> exact decimal/vector decoding
  -> core semantic/constraint validation
  -> formula VM or bounded kernel
  -> classification on unrounded internal value
  -> output rounding
  -> provenance/status encoding
```

Cold discovery prepends:

```text
query -> xs_find -> canonical key/signature -> digest-bound cache
```

No stage invokes a language model inside ExactScope.

## 12. Numeric model

The deterministic baseline uses canonical base-10 Decimal64 values and exact/bounded rational intermediates. Unsupported precision/range fails rather than wrapping or silently switching to host float semantics.

Materially different methods remain separate operation keys.

## 13. Formula VM

The v0.1 scalar VM is deliberately non-Turing-complete and bounded. It supports the frozen instruction families required by current packs, including arithmetic, integer power, square root, comparisons, boolean/select, and explicit round.

No jumps, recursion, arbitrary memory access, or general expression execution are permitted.

Vector work uses bounded kernel IDs rather than VM loops.

## 14. Installation boundary

ExactScope's product is a component, not a daemon/application service.

The intended release-shaped flow is:

```text
prebuilt artifact
  -> verify manifest/digest
  -> link/load
  -> self-test
  -> bind generated hot set
  -> direct xs_eval calls
```

Target installation must not require Rust, Python, Node.js, Java, a package manager runtime, cloud login, or background process.

Closed devices with no application/plugin/native/Wasm/paired-host execution boundary cannot be made directly installable by ExactScope alone.

## 15. Compatibility philosophy

Compilation is not support.

Primary release artifacts must pass:

- ABI/wire conformance;
- shared golden vectors;
- malformed-input tests;
- exact artifact identity checks;
- size/memory measurements;
- actual runtime execution.

Real-device performance/energy claims require real-device evidence.

Wider fused/static/dynamic parity is valuable but no longer the first product milestone. The invariant is **one calculation semantics**, not **every profile must mature at once**.

## 16. Security/privacy boundary

The core does not need:

- user identity;
- prompt history;
- raw camera/audio/OCR input;
- location;
- telemetry transport;
- accounts/network.

It receives only the typed operation request needed for deterministic execution and returns typed result/provenance/status data.

## 17. Engineering budgets

Budgets remain implementation gates rather than marketing claims. Fused/static paths must remain suitable for very small resident footprints, bounded scratch, and no required heap.

Any budget increase requires measurement and an explicit design decision.

## 18. Product-proof architecture rule

New architecture work should first answer one of these needs:

- make direct model integration easier;
- reduce invalid/rejected calls without semantic guessing;
- improve benchmark evidence;
- improve release/installation simplicity;
- improve deterministic correctness/security;
- improve target qualification.

Work that only broadens internal elegance or platform count is secondary until the product proof exists.
