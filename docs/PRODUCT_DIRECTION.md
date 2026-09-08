# ExactScope product direction

Release context: **ExactScope v1.0.0 promotes the selected r25 grounding behavior into a stable Linux x86-64 native grounding software/package scope.** The native C ABI, deterministic XSGI search/projection path, footprint-gated package, and final-archive C11 clean-room integration are complete. The seven-model and public-benchmark accuracy results remain bound to their exact candidate/provider/corpus identities, and physical ARM64 RAM/latency/energy/thermal qualification remains unclaimed. See [`GROUNDING_ARCHITECTURE.md`](GROUNDING_ARCHITECTURE.md), [`../spec/GROUNDING_CONTRACT_V0_1.md`](../spec/GROUNDING_CONTRACT_V0_1.md), [`BENCHMARK.md`](BENCHMARK.md), and [`../spec/GROUNDING_RUNTIME_BUNDLE_V1.md`](../spec/GROUNDING_RUNTIME_BUNDLE_V1.md).

This document defines what ExactScope is optimizing for. It supersedes any earlier product framing that treated broad platform parity or full catalog completion as more important than proving adoption value.

## 1. Product sentence

ExactScope is a **tiny provider-neutral grounding and deterministic capability layer for small and on-device AI**.

Its flagship customer value is:

> **Make an existing small model more correct and less confidently wrong on everyday factual questions by supplying compact, scoped, auditable evidence before answer generation.**

ExactScope is designed as a **capability retrofit layer** for products whose model size and inference cost are bounded by RAM, bandwidth, storage, accelerator capability, thermals, battery, latency, privacy, or qualification constraints.

The product does not claim to make model weights generally more intelligent. It moves selected factual state outside model memory and into explicit Source -> Provider -> Evidence Policy -> Grounding Frame paths. The existing quantitative `xs_calc`/`xs_eval` subsystem remains supported for tasks where deterministic calculation is the actual failure mode.

Smart glasses and wearables are strong use cases, but the thesis applies more broadly to phones, robots, industrial systems, automotive systems, embedded assistants, and private/local AI.

The normative grounding design is [`GROUNDING_ARCHITECTURE.md`](GROUNDING_ARCHITECTURE.md) plus [`../spec/GROUNDING_CONTRACT_V0_1.md`](../spec/GROUNDING_CONTRACT_V0_1.md). [`CAPABILITY_PRODUCT_ARCHITECTURE.md`](CAPABILITY_PRODUCT_ARCHITECTURE.md) remains a quantitative-subsystem reference rather than the flagship product definition.

## 2. Product hypothesis

The product hypothesis is not assumed true merely because retrieval is useful in principle.

It must be measured:

> For an existing constrained model, can a compact high-precision grounding layer materially increase everyday factual accuracy and reduce wrong-confident answers at sufficiently low storage, RAM, context-token, latency, energy, privacy/integration and qualification cost that keeping the existing model/hardware is the better engineering choice than a larger model, much larger context, heavyweight RAG stack, remote dependency, or newer device?

The flagship proof compares:

- **A:** model only, one answer-generation call;
- **G:** original-question prefetch -> deterministic Grounding Frame -> host completion when serving-visible state is sufficient, otherwise compact Projection -> the same model, zero or one answer-generation call;
- optional **L:** a justified larger-model/hardware alternative;
- optional rewrite/tool profiles only as separately costed diagnostics.

The first public proof is **everyday factual accuracy + wrong-confident-answer reduction + low false grounding**, not academic catalog breadth.

## 3. Primary interaction model

The flagship v1 path is host-side grounding prefetch **before** model answer generation.

```text
original user question
        |
        v
host security/application scope
        |
        v
Grounding Router -> bounded TargetPlan(s)
        |
        v
Retrieval Providers
(exact/lexical/vector/app/captured-network)
        |
        v
ProviderOutcome(s)
        |
        v
Evidence Policy
(coverage/authority/freshness/merge/conflict/budget)
        |
        v
grouped GroundingFrame
        |
        +-- authoritative unresolved -> host disposition (0 model calls)
        |
        +-- one canonical scalar -> host value (0 model calls)
        |
        `-- remaining text/ordinary knowledge -> compact Model Projection
                                           |
                                           v
                               small/local model -- one answer call
```

The model does **not** need to call `xs_recall` or choose a retrieval provider in the normal path. Earlier `xs_recall`/fact-pack code is an implementation prototype, not the normative API.

A model-generated retrieval rewrite is optional and belongs to a separate profile because it adds a model call, token cost, latency and another failure mode.

The quantitative paths remain separate:

- `xs_calc` — bounded short arithmetic plan;
- `xs_eval` — reviewed semantic/method operation;
- `xs_find` — optional quantitative discovery.

Native tool vs constrained JSON/GBNF selection remains relevant only when the **model must form a quantitative request** or an explicitly selected optional retrieval-tool profile. It is not required for everyday grounding.

## 4. Small model context first

The flagship optimization target is **small evidence, not broad catalog or broad context**.

The model should normally receive only:

- target label/meaning;
- authority (`authoritative` or `supplemental`);
- target state (`grounded`, `none`, `ambiguous`, `conflict`, `unavailable`);
- the few policy-approved Evidence Items needed to answer.

Keep host-side:

- provider catalogs;
- raw similarity/vector scores;
- embedding vectors;
- tenant/security scope IDs;
- access-control metadata;
- source indexes;
- verbose audit logs;
- rejected/conflicting candidate sets.

The deterministic Model Projection is versioned and digest-bound because evidence wording, ordering and labels can materially affect a small model.

For quantitative tasks, keep the same old principle: expose the smallest realistic `xs_calc`/`xs_eval` surface rather than a large operation catalog.

## 5. Fail closed where authority is real

Grounding and calculation have different failure semantics but share one principle: **do not turn uncertainty or invalid state into a plausible successful value.**

For authoritative grounding:

- a valid hit may be used;
- `none` means required authoritative coverage completed and found no usable evidence;
- timeout/error/denied/incomplete coverage becomes `unavailable`, not `none`;
- ambiguous candidates stay `ambiguous`;
- unresolved contradictions stay `conflict`;
- an unresolved authoritative target must not be filled by model memory or a merely supplemental source.

For supplemental grounding, no-hit/unavailable does not imply the fact is false or unknowable; normal model knowledge may still be used under host policy.

For quantitative calls, adapters may normalize syntax/transport but may not invent operands, methods, units, conversions, or results.

This distinction is why benchmark reporting must include both useful-answer rate and wrong-confident-answer/false-grounding rates instead of celebrating refusal alone.

## 6. Competitive axis

ExactScope does not compete on model FLOPS, universal search coverage, or full enterprise RAG orchestration. It competes on a narrower systems combination:

- **retrofit/OTA suitability for constrained or already-deployed AI**;
- provider-neutral source/search integration;
- original-question prefetch with no mandatory extra model turn;
- compact model-visible evidence;
- explicit authoritative vs supplemental semantics;
- revision/freshness/conflict/ambiguity handling;
- privacy/security-scope isolation;
- deterministic merge and candidate-bound evidence identity;
- offline-capable local profiles;
- optional semantic/application/network providers without making them core dependencies;
- deterministic quantitative capability when needed;
- reproducible model/device qualification.

A product that already has a cheap, trusted, sufficiently small grounding stack and does not need ExactScope's evidence/policy/qualification contract may not need ExactScope. That is an acceptable non-target.

## 7. Market definition

The primary market is **physically constrained or already-deployed on-device AI** where increasing model size has meaningful hardware/product cost.

Representative targets:

- smart glasses and wearables;
- phones/tablets;
- embedded assistants;
- robots and industrial systems;
- automotive systems;
- other constrained edge products;
- later regulated/certifiable systems where arbitrary code execution is undesirable.

Private/local desktop AI remains useful for development and validation, but it is not the center of the retrofit thesis.

Offline is a capability, not the whole market. A network-connected device can still benefit from keeping private/device/manual grounding local and tiny, while optionally adapting captured network/search evidence into the same Grounding Contract. Quantitative work may likewise remain local and independently qualifiable.

The strongest early adoption wedge may be **existing devices** whose hardware cannot be changed but whose AI software stack can still receive an update.

## 8. v1 product scope

The product scope remains intentionally narrow even though the grounding contract permits several retrieval implementations.

The rc3 native/Wasm quantitative runtime and packaging remain useful secondary infrastructure, but **they do not define the v1 flagship product boundary**. The v1 product boundary is the provider-neutral Grounding Contract plus the selected r25 host policy and the native `.xsgi` retrieval/projection core exposed through the C ABI. The stable Linux x86-64 package now ships that runtime with a tiny demonstration provider and explicit package/support boundaries; benchmark-sized NQ provider data stays outside the default install. Historical source `e6c3558642c77e379358b9f59aedd92abf7473f4` remains frozen as the r5 comparison baseline.

The primary v1 integration shape is:

1. **Host-side Grounding Router** — chooses only preregistered, scope-authorized sources/providers for the current application/user context.
2. **Retrieval Provider interface** — exact/lexical, frozen semantic/vector, application-native, or captured host/network providers may implement the same logical contract.
3. **Evidence Policy** — applies authority, revision/validity, duplicate/conflict/ambiguity and context-budget rules.
4. **Grounding Frame** — the compact authority/evidence representation used first by deterministic host completion and, only when needed, by the model projection before one answer-generation call.

The first benchmark candidate freezes a small offline exact/lexical provider **as a reference profile only**. That provider is not the universal product definition and does not grant authority by retrieval score. Vector/application/host providers remain future contract-compatible implementations if their identities, scope and behavior are frozen explicitly.

The v1 release now includes a native C grounding ABI for the deterministic `.xsgi` retrieval/projection core. Routing, provider access, application security scope, authority, and evidence policy remain host concerns and are intentionally not moved into the no-import quantitative Wasm core. A grounding Wasm transport remains deferred until it has its own parity/qualification evidence.

The existing quantitative subsystem remains available through native/Wasm `xs_calc`/`xs_eval` paths. Additional academic domains, dynamic calculation packs, convenience wrappers and broad platform parity are secondary to proving everyday grounding value.

## 9. Grounding-first release status

### Completed before model inference

- rc3 qualification evidence was closed and left immutable;
- the flagship product objective moved from academic/tool-call breadth to everyday factual grounding and hallucination-risk reduction;
- original-question prefetch became the default path, with one answer-generation call in both A and G benchmark arms;
- Source, Retrieval Provider, Evidence Policy, Grounding Frame and Model Projection were separated;
- `authoritative`/`supplemental` and `grounded`/`none`/`ambiguous`/`conflict`/`unavailable` semantics were frozen;
- the provider-neutral machine-readable profile/schemas and deterministic projection were implemented and conformance-tested;
- the first offline reference provider and merge path were implemented behind the provider boundary;
- a physically separated 30-item serving/gold candidate generator, gold-only scorer and zero-inference dry-run were implemented;
- evaluation-package, model/runtime identity, preregistration and benchmark-runner tooling were implemented with no retry, hidden repair or resume path;
- the retained quantitative Rust/C/Wasm code continues to pass its regression suite.

### Historical five-model baseline — completed

The first integrity-corrected five-model benchmark is **r5**, source `e6c3558642c77e379358b9f59aedd92abf7473f4`. It is frozen as historical behavioral comparison evidence. Raw run evidence remains checksum-bound and is never rewritten into newer candidate results.

### Selected r25 behavior — source-run complete

The optimization chain selected **r25** on the product priorities that matter: cross-model accuracy, wrong-confidence/unsupported-assertion safety, model-call count, token cost and tiny-model robustness. The frozen seven-model matched screen spans SmolLM2 135M through Phi-4-mini 3.8B. Its all-model mean moved from 8.1% model-only to 93.3% with ExactScope; the original five-model subset moved from 9.3% to 95.3%. The same semantic scores were reproduced after the native C ABI/release integration work.

The selected host path completes 10 authoritative unresolved cases and 13 canonical scalar facts deterministically in the 30-item G arm, leaving 7 model answer calls. It does not derive values from benchmark gold or regex text post-processing: scalar completion is permitted only when the source already supplied a valid Grounding Contract scalar.

### v1 software release qualification — complete for Linux x86-64

The selected native grounding core is now exposed through the C ABI, packaged into a deterministic Linux x86-64 SDK, checked against the Python reference with exact search-score bits and byte-exact projection, and exercised from a final-archive C11 clean room. The default package also enforces the release footprint hard caps and excludes benchmark-sized NQ provider data from the generic install.

Representative ARM64 storage/RSS/heap/stack/latency/energy/thermal qualification remains required before production-class embedded hardware claims. The absence of that hardware evidence narrows the v1 support matrix; it does not block the stable Linux x86-64 software package.

See [`../ROADMAP.md`](../ROADMAP.md) for the detailed gates.

## 10. Installation target

The target grounding retrofit experience is:

```text
download/receive software + source/index/profile update
  -> verify source/provider/profile manifest and digests
  -> bind allowed user/application/source scope
  -> configure authority + freshness/conflict/evidence budgets
  -> load or connect the selected retrieval provider
  -> run retrieval/policy self-test
  -> prefetch a compact Grounding Frame before the existing model answer call
  -> optionally route actual quantitative work through xs_calc/xs_eval
```

A minimal fully local profile should not require:

- replacing or retraining the model;
- native model tool-call support;
- Rust, Python, Node or Java on the target;
- a package-manager runtime;
- a daemon;
- an ExactScope account;
- a network connection;
- a writable home directory beyond whatever storage the host already uses for its approved evidence/index.

A network-connected profile may use a host provider, but private evidence/query transmission is an explicit product policy rather than a hidden dependency. Developer-side indexing/build tooling may use convenient workstation languages, but that choice must not become a target runtime dependency.

## 11. Evidence before claims

Before ExactScope markets a broad accuracy, latency or energy claim, publish reproducible candidate-bound evidence under [BENCHMARK.md](BENCHMARK.md). rc3 qualification findings may be reported as historical observations, not generalized product claims.

Before a platform is called supported, publish compatibility evidence under [COMPATIBILITY.md](COMPATIBILITY.md).

Before enterprise optimization claims, publish at least one real constrained-target qualification record.

## 12. Commercial direction

The OSS core remains the adoption wedge. The strongest near-term commercial layers described in [COMMERCIALIZATION.md](COMMERCIALIZATION.md) are **grounding source/provider assurance, target-specific Evidence Policy/profile engineering, privacy/freshness/conflict review, benchmark/qualification, LTS/update support and OEM integration assistance**. Reviewed quantitative domain products remain an optional secondary layer.

The business model must not require a proprietary cloud calculation/search service, custody of customer private memory, or an incompatible evaluator fork. A customer should be able to keep its sources and indexes private while using the public Grounding Contract and evidence tooling.

## 13. Current implementation position

The **mature retained subsystem** from rc3 is quantitative:

- deterministic `no_std` numeric kernel and bounded scalar VM;
- bounded `xs_calc` plan-v0.1 over `add/sub/mul/div/powi/sqrt`;
- Tiny JSON/TinyWire plus generated JSON Schema/GBNF/tool/prompt assets;
- reviewed Economics execution and bounded Statistics vector kernels;
- selected semantic `xs_eval` and optional cold/development `xs_find`;
- native typed C ABI and no-import Wasm;
- pack/packc plus optional dynamic-pack architecture;
- deterministic capability/profile compiler and specialization machinery;
- model-surface identity, packaging, security/export audit and qualification infrastructure.

The **stable v1 grounding implementation** now consists of:

- [`GROUNDING_ARCHITECTURE.md`](GROUNDING_ARCHITECTURE.md) plus the normative [`../spec/GROUNDING_CONTRACT_V0_1.md`](../spec/GROUNDING_CONTRACT_V0_1.md);
- the selected host completion order and llama.cpp reference adapter;
- the `no_std`, allocation-free `exactscope-grounding` native core;
- immutable `.xsgi` provider compilation, zero-copy validation, BM25-v1 search, and compact evidence projection;
- the public C ABI in `include/exactscope.h`;
- exact Python/Rust/C-ABI parity tests on NQ development-mirror and HotpotQA screens;
- the deterministic Linux x86-64 stable package in [`../spec/GROUNDING_RUNTIME_BUNDLE_V1.md`](../spec/GROUNDING_RUNTIME_BUNDLE_V1.md);
- a package-local C11 demonstration and final-archive clean-room test;
- explicit 10 MB compressed / 20 MB unpacked default-install hard caps;
- benchmark and publication audits that keep gold, raw evidence, local paths, and internal handoff material outside the public product package.

Earlier `xs_recall`/fact-pack experiments remain non-normative implementation history. The older quantitative `xs_calc`/`xs_eval` subsystem remains available as a secondary capability, but it does not define the v1 grounding product.

Post-v1 product gates are broader provider implementations, long-term compatibility/LTS evidence, and representative physical-device qualification where target-specific RAM/latency/energy/thermal claims are desired. Physical ARM64 qualification is the most important outstanding hardware gate; it is not silently inherited from x86-64 evidence.

## 14. Decision test

Before adding a flagship feature, ask:

> Does this make an existing constrained model **more correct or less confidently wrong on ordinary factual questions** with less storage, context, token, latency and integration cost than a larger model or heavyweight RAG path, **without increasing false grounding or privacy/scope risk**?

Then ask:

1. Can the behavior be expressed through the provider-neutral Grounding Contract rather than coupling the product to one retrieval implementation?
2. Can its source/provider/policy identity and cost be frozen and measured reproducibly?
3. Does it preserve one-call prefetch as the default unless an extra rewrite/tool turn proves enough value to justify itself?
4. If the problem is actually deterministic calculation, does it reuse the existing `xs_calc`/`xs_eval` core rather than creating a second semantics?

If not, it is probably lower priority than the everyday grounding product proof.
