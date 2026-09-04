# ExactScope architecture baseline v0.1

This document defines the runtime architecture. Product priority is defined in `PRODUCT_DIRECTION.md`, while `CAPABILITY_PRODUCT_ARCHITECTURE.md` defines the next-stage product unit and capability-slice architecture. Where older wording conflicts, shared-core invariants remain binding while product sequencing follows those documents.

## 1. System boundary

ExactScope is a deterministic quantitative execution component embedded inside another AI system.

The host owns:

- model inference and natural-language understanding;
- sensor/UI input and output;
- extraction of candidate values from the request;
- model/tool routing;
- capability-slice/hot-set selection and cache binding;
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

## 2. Product call paths

The architecture has two current model-facing execution paths: bounded generic `xs_calc` arithmetic and reviewed semantic `xs_eval`. Both converge on the same deterministic core.

```text
                         small/local model
                                |
                 +--------------+--------------+
                 |                             |
                 v                             v
        generic short arithmetic       known semantic method
                 |                             |
                 v                             v
        xs_calc(bounded plan)            xs_eval(op,args)
      IMPLEMENTED / EXPERIMENTAL       IMPLEMENTED / REVIEWED
                 |                             |
                 +--------------+--------------+
                                |
                                v
                     ExactScope shared core
```

### 2.1 Current experimental `xs_calc` plan path

`xs_calc` is implemented as a single model turn followed by one bounded deterministic execution. Plan v0.1 contains at most eight arithmetic steps and only a fixed vocabulary (`add`, `sub`, `mul`, `div`, `powi`, `sqrt`). Previous-result references are backward-only. Loops, arbitrary branches, variables, arbitrary functions, arbitrary expression text, and arbitrary code are forbidden.

The plan path must lower into the existing bounded VM/numeric kernel. It must not create a second arithmetic semantics.

### 2.2 Existing `xs_eval` semantic path

`xs_eval` remains a first-class hot path for reviewed operations whose identity carries method or domain semantics. Examples include sample versus population statistics and economics operations. A fixed product may bind these operations ahead of time.

### 2.3 `xs_find` cold/development path

`xs_find` remains a discovery helper for unknown semantic operations and developer/setup workflows. It is no longer treated as a primary tiny-model serving path. Successful discovery may still be cached against registry/pack digest and operation revision.

## 3. Model-surface architecture

A constrained product should expose the smallest useful surface rather than the full catalog.

```text
ordinary short arithmetic
        -> one bounded xs_calc schema/grammar

reviewed domain methods
        -> compact xs_eval capability slice

unknown semantic operation
        -> optional xs_find cold/development path
```

A semantic hot set may still generate compact catalog/hints, OpenAI-compatible tool assets, GBNF, digest bindings, and typed operation IDs. The full catalog remains host/tooling metadata and should not be injected into a tiny-model prompt by default.

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
  llama-cpp/              # implemented direct semantic reference
  xs-calc-v0.1/           # bounded arithmetic tool/schema/GBNF/prompt assets
  generated/              # generated semantic hot-set/capability inputs
examples/
  llama.cpp/              # one-turn xs_calc reference runner and smoke benchmark
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
- product hot-set/capability-slice model assets and profile metadata generation.

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

### Primary RC/evaluation profiles

1. native static C ABI;
2. no-import WebAssembly.

These profiles now receive first-class prebuilt RC artifacts, quickstart coverage, benchmark integration, and conformance gates. Stable support still requires the qualification evidence defined elsewhere.

### Secondary/experimental profiles

- dynamic data packs;
- static embedded `.xsp` registries;
- shared-library/mobile wrappers;
- additional OS/architecture variants.

All exposed operations must use shared semantics, but these profiles may remain Experimental without blocking focused v0.1.

## 11. Execution pipelines

### 11.1 Bounded-plan execution path

```text
model/host xs_calc request
  -> adapter envelope/syntax validation
  -> bounded plan decode
  -> step/reference/arity/resource validation
  -> exact decimal decoding
  -> canonical lowering to shared VM/kernel semantics
  -> deterministic execution
  -> output rounding/status encoding
```

The plan decoder/compiler is not allowed to evaluate arbitrary expression text or introduce another arithmetic implementation.

### 11.2 Existing semantic-operation path

```text
model/host xs_eval request
  -> adapter envelope/syntax validation
  -> canonical operation binding lookup
  -> exact decimal/vector decoding
  -> core semantic/constraint validation
  -> formula VM or bounded kernel
  -> classification on unrounded internal value
  -> output rounding
  -> provenance/status encoding
```

Optional cold discovery prepends:

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

ExactScope's product is a component, not a daemon/application service. The primary deployment story is a **small software retrofit** into an existing AI stack.

The current release-shaped integration flow is:

```text
prebuilt artifact / product software update
  -> verify manifest/digest
  -> link/load
  -> self-test
  -> bind xs_calc schema/grammar and selected semantic ops
  -> route supported deterministic work through ExactScope
```

Target installation must not require replacing/retraining the model, Rust, Python, Node.js, Java, a package-manager runtime, cloud login, or background process.

Update/rollback compatibility and artifact identity are first-class concerns because an important target is already-designed or already-deployed hardware.

Closed devices with no product-controlled application/plugin/native/Wasm/paired-host execution boundary cannot be retrofitted by ExactScope independently. End users are not expected to install or configure ExactScope themselves.

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
