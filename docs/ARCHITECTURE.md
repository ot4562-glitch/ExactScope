# ExactScope architecture baseline v0.1

This document defines the runtime architecture. Product priority is defined in `PRODUCT_DIRECTION.md`; [`GROUNDING_ARCHITECTURE.md`](GROUNDING_ARCHITECTURE.md) and [`../spec/GROUNDING_CONTRACT_V0_1.md`](../spec/GROUNDING_CONTRACT_V0_1.md) define the active rc4 grounding architecture; `CAPABILITY_PRODUCT_ARCHITECTURE.md` and `MODEL_INTERFACE_RC4.md` remain valid for the quantitative capability lanes. Where older wording conflicts, the grounding contract governs the flagship rc4 product path while shared deterministic-core invariants remain binding.

## 1. System boundary

ExactScope is a compact grounding and deterministic-capability component embedded inside another AI system.

The host owns:

- model inference and natural-language understanding;
- sensor/UI input and output;
- user/application/tenant scope and access control;
- source registration, storage, updates, signatures and lifecycle;
- optional network/search/vector providers;
- final model invocation and answer rendering.

The ExactScope grounding layer owns the provider-neutral logical contract between a scoped user query and a deterministic model projection:

- immutable GroundingProfile and router identity;
- factual TargetPlan identity and per-target/source authority (`authoritative` vs `supplemental`);
- explicit provider/source bindings and required coverage/sufficiency;
- typed ProviderOutcome including complete no-hit versus timeout/error/denied/budget/incomplete coverage;
- revision/freshness/validity policy;
- deterministic dedup/merge/order/tie-break and conflict/ambiguity policy;
- evidence/model-context budgets;
- stable source/item/revision/content identity;
- target-grouped `grounded/none/ambiguous/conflict/unavailable` states;
- deterministic Model Projection identity and data-versus-instruction boundary.

The existing deterministic quantitative layer owns:

- exact operation identity;
- input count/type/semantic/constraint validation;
- unit compatibility checks;
- deterministic calculation;
- explicit rounding/classification;
- stable status/error codes;
- pack/operation provenance.

ExactScope does not own model inference, arbitrary code execution, unrestricted network browsing, user authentication, or a universal truth-ranking algorithm. Retrieval implementations may be local, vector-based, application-native, or host/network provided as long as they map into the Grounding Contract and expose a frozen identity for qualification.

## 2. Product call paths

The flagship rc4 path is **grounding before generation**, not model-selected tool invocation.

```text
original user question + host security/application scope
    |
    v
Grounding Router -> TargetPlan(s)
    |
    +--> exact/lexical provider
    +--> optional semantic/vector provider
    +--> optional application/network provider
    |
    v
ProviderOutcome(s)
    |
    v
Evidence Policy
    |
    +--> required coverage / sufficiency
    +--> target-scoped authority
    +--> freshness / revision / validity
    +--> deterministic merge / order / tie-break
    +--> ambiguity / conflict
    +--> evidence/context budget
    |
    v
grouped GroundingFrame
    |
    v
deterministic Model Projection
    |
    v
small/local model called once
    |
    v
final answer
```

The normal prefetch profile does not require the model to choose a retrieval tool, operation, or provider. Providers and target/source bindings are host/profile configuration, and the original user question is the default query.

### 2.1 Grounding prefetch path — default rc4 product path

The host establishes effective security/application scope, creates a QueryEnvelope, and routes the original question into bounded factual TargetPlans before answer generation. Providers return typed outcomes per target. Evidence Policy converts those outcomes into one **grouped** GroundingFrame and a deterministic compact Model Projection. A model-generated query rewrite is optional and belongs to a separate profile because it adds model tokens/latency and a new failure mode.

The grounding path is provider-neutral. Exact/alias lookup is a minimum deterministic baseline, not the universal retrieval algorithm. Product integrations may use compact lexical search, a frozen embedding index, application-native memory, or captured host/network results as long as provider identity, source/security scope, target authority/coverage, evidence identity, merge policy and projection identity are frozen for qualification. Authoritative `none` is legal only after required/sufficient authoritative coverage completes successfully; provider timeout/error/denial/budget exhaustion/incomplete coverage remains `unavailable`.

### 2.2 Quantitative `xs_calc` path

`xs_calc` remains a bounded deterministic arithmetic lane. Plan v0.1 contains at most eight arithmetic steps and only a fixed vocabulary (`add`, `sub`, `mul`, `div`, `powi`, `sqrt`). Previous-result references are backward-only. Loops, arbitrary branches, variables, arbitrary functions, arbitrary expression text, and arbitrary code are forbidden.

The plan path lowers into the existing bounded VM/numeric kernel and must not create a second arithmetic semantics.

### 2.3 Quantitative `xs_eval` path

`xs_eval` remains a first-class path for reviewed operations whose identity carries method or domain semantics. It is useful when a factual question becomes a deterministic calculation after grounding or when a product genuinely needs a reviewed quantitative capability.

### 2.4 `xs_find` cold/development path

`xs_find` remains operation discovery for the quantitative subsystem. It is not the factual-memory contract and is not a mandatory serving hop.

## 3. Model-surface architecture

The grounding design reduces the normal model-visible surface rather than adding another broad tool catalog.

```text
ordinary factual question
        -> host-side prefetch
        -> grouped GroundingFrame
        -> deterministic compact Model Projection
        -> one model answer call

question requiring retrieval rewrite
        -> optional constrained rewrite profile
        -> Providers / Policy / grouped Frame / Projection
        -> model answer

short arithmetic
        -> constrained xs_calc request grammar
        -> optional native xs_calc tool envelope

reviewed quantitative method
        -> constrained xs_eval request grammar over a compact capability slice
        -> optional native xs_eval tool envelope
```

The common factual path exposes **target-scoped evidence and state, not retrieval internals**. Similarity scores, embedding vectors, security-scope IDs, full source catalogs, provider schemas, rejected candidates, and large audit metadata remain host-side. The Model Projection renderer/template is deterministic and identity-bound because wording/order can change weak-model behavior.

For quantitative capability calls, constrained JSON/GBNF remains the universal model-facing compatibility baseline and native tools remain optional when proven by pre-inference runtime metadata.

A fail-closed signal in either subsystem must preserve its exact scope and meaning. An authoritative target in `none/ambiguous/conflict/unavailable` state is not permission to invent that protected value, but an unrelated supplemental target may still use normal model knowledge according to host policy. A typed deterministic calculation rejection likewise must not be converted into a plausible result.

## 4. Strict semantic core and adapter boundary

The core remains fail-closed for semantic uncertainty and invalid input.

Adapters may normalize transport syntax, but may not:

- calculate;
- round/classify independently;
- infer missing values;
- silently convert units/rates/currencies;
- choose ambiguous methods;
- turn an ExactScope error into a plausible number.

This separation is central to benchmark design: the grounding path must measure routing/retrieval/policy/model failures independently while preserving A/G one-call fairness, and the retained quantitative subsystem must continue to measure request-selection/validation failures separately from deterministic core correctness.

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

The Statistics evaluator validates each caller's arity before erasing the vector
transport type into two borrowed trait-object references. Its large operation
dispatch and arithmetic calls are emitted once, avoiding separate generic copies
for typed Wasm, CBOR and Tiny JSON readers. No allocator or copied vector is added;
numeric order, failure precedence and the public Rust/C contracts remain intact.
Older development builds measured size changes from this refactor, but those byte
counts are historical measurements tied to their exact source/toolchain identities.
They are not rc2 release measurements and are therefore not restated as a current
artifact claim here.

Subsequent rational multiplication/division avoid a third GCD after complete
cross-cancellation of normalized inputs. The normalized-input invariant proves
the resulting numerator/denominator are already coprime. Numeric grid and i128
boundary tests preserve existing overflow behavior. Historical desktop wire
microbenchmarks were useful during development, but mutable raw benchmark payloads
are intentionally not carried forward in the rc2 clean source. Any rc2 latency
measurement must be rerun and bound to the exact public release artifact; desktop
microbenchmarks remain distinct from physical-device and model end-to-end evidence.

### Experimental profile-derived Statistics specialization

The Statistics capability compiler lowers the profile's selected reviewed operations
to operation-level build features. `stats-specialized` is the common serving boundary;
individual features select `sum`, `mean`, weighted mean, population/sample variance and
standard deviation, covariance, Pearson correlation, or linear regression. Feature names
are derived from the reviewed Statistics scope-pack keys. Selected key/ID lookup is
centralized in the kernel and reused by Tiny JSON and the direct typed Wasm Statistics
export; kernel contract/compute dispatch remains the final shared execution authority.
Packc parity tests reject reviewed scope-pack/fused Rust metadata drift. TinyWire, scalar
economics and runtime discovery are disabled in these specialized artifacts.

The specialization machinery has already demonstrated that reviewed Statistics subsets
change real binary reachability rather than merely hiding tools from the model. Historical
post-r20 development revisions measured a full eight-operation slice, a weighted-mean-only
slice, and a same-boundary `xs_calc`-only baseline under one source/toolchain line. Those
measurements remain development history; the clean rc2 source does not carry their generated
capability directories forward or relabel their byte counts as current release evidence.

For rc2, the important architectural fact is that the compiler derives selected Statistics
operation features from reviewed metadata, selected key/ID lookup is centralized in the
kernel, and specialized Tiny JSON/direct Wasm dispatch rejects excluded operations. The
exact rc2 artifact size, digest, imports, memory declaration, conformance result, and marginal
semantic cost must be measured again from the immutable public release candidate in the
qualification session.

The frozen r20 model-evidence chain remains bound to the earlier 45,804-byte r17 runtime.
Neither that model evidence nor later pre-rc2 footprint proofs are inherited by rc2. This
preserves the distinction between an implemented specialization mechanism and evidence for
one exact released artifact.

The specialized link policy replaces the generic roughly 1 MiB default Wasm stack
reservation with a 16 KiB stack and sets maximum linear memory to 64 KiB. Local stress
found 2 KiB insufficient and 4 KiB sufficient for the current stress suite; 16 KiB
retains a 4x margin. Specialized modules declare memory `1..1` pages. This is a hard
component linear-memory ceiling, not a measurement of process resident RAM, host VM
memory, model memory, energy, or target qualification.

The generalization boundary is explicit: new subsets of the currently reviewed
Statistics vocabulary can be compiled from profiles without Rust edits. A genuinely
new operation, domain, or semantic kernel still needs implementation, operation-level
feature plumbing, review and conformance before it can participate in this mechanism.

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

## Experimental compiler implementation

The build-time [capability compiler](CAPABILITY_COMPILER.md) validates Statistics and
Economics task selections through shared domain descriptors, binds operation revisions
and canonical model assets, and enforces static budgets. Selected Wasm artifacts use
operation Cargo features to remove excluded serving paths, including optional `xs_calc`.
Discovery and TinyWire remain outside selected serving slices. The draft profile stays
experimental; implementation completion does not establish model/target qualification.

Statistics operation declarations, stable kernel IDs, arity/output contracts, selected
lookups and compute-call wiring come from reviewed source plus explicit implementation
bindings. Handwritten numeric functions remain the sole algorithms. Packc reuses the
generated kernel-name lookup. Scalar Economics selection is generated, and its handwritten
identity/output policy is drift-checked against the source. Both domains use the same
descriptor-driven Cargo forwarding checks. CI rejects stale generated metadata.

The JavaScript capability host verifies the detached manifest hash, exact file inventory,
regular-file payloads and every payload digest before loading Wasm. These checks establish
bundle integrity, not publisher authentication. OEM update trust remains host-owned.
