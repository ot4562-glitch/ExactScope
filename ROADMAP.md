# ExactScope roadmap

No dates are promised. This roadmap is ordered by **everyday factual reliability, false-grounding avoidance, small-model cost, evidence quality, and retrofit economics**.

Release context: **rc4 grounding architecture/contract completion followed by implementation up to benchmark-ready freeze; v1.0.0-rc.3 remains immutable historical quantitative evidence**.

The flagship product question is:

> Can a compact provider-neutral grounding layer make an already-deployed small/on-device model more correct and less confidently wrong on ordinary factual questions, at low enough storage/RAM/token/latency/integration cost to beat a larger model, much larger context, heavyweight RAG stack, remote dependency, or hardware upgrade?

## Current checkpoint

The rc3 public release and its external-user qualification are closed and immutable. Its constrained/native quantitative model-interface work remains useful infrastructure, but the flagship rc4 path is now:

```text
original question
 -> host security/application scope
 -> Grounding Router / TargetPlan(s)
 -> Retrieval Provider(s)
 -> ProviderOutcome(s)
 -> deterministic Evidence Policy
 -> grouped GroundingFrame
 -> deterministic Model Projection
 -> one small-model answer call
```

The current task proceeds in this order:

1. complete/freeze documentation and logical contracts;
2. obtain a read-only Codex architecture review with no P0 blocker;
3. freeze concrete machine-readable GroundingProfile/frame/provider schemas;
4. implement the frozen contract without preserving prototype mistakes;
5. complete no-inference conformance, security, packaging and preregistration dry-runs;
6. stop at **READY_FOR_GROUNDING_BENCHMARK** before any new model inference.

Academic-domain expansion is deferred.

## Historical/retained implementation baseline

### Mature quantitative subsystem

Retained and protected from regressions:

- [x] deterministic `no_std` decimal/rational numeric kernel;
- [x] explicit deterministic rounding/domain/status behavior;
- [x] bounded scalar VM and Plan v0.1;
- [x] `xs_calc`: 1-8 steps over `add/sub/mul/div/powi/sqrt` with backward-only references;
- [x] strict bounded Tiny JSON and optional TinyWire boundaries;
- [x] native typed C ABI;
- [x] no-import Wasm boundary;
- [x] reviewed Statistics and Economics semantic execution;
- [x] selected `xs_eval` and optional quantitative `xs_find`;
- [x] pack/packc and capability/profile specialization infrastructure;
- [x] model-surface identity/fail-closed negotiation;
- [x] constrained JSON/GBNF quantitative compatibility baseline;
- [x] optional native-tool selection from pre-inference runtime capability metadata;
- [x] release/package identity, checksums, security/export audit and qualification tooling.

### Historical rc3 public package/evidence

- [x] Windows/Linux x86-64 evaluation SDKs;
- [x] Android/Linux ARM64 static OEM SDK assets and doctor checks;
- [x] release manifest and SHA256SUMS;
- [x] Linux/Windows clean-room package checks;
- [x] frozen five-model A/C/D matrix;
- [x] chat-template/tool-protocol diagnostics;
- [x] physical ARM64 performance/RAM/energy/thermal preserved as **NOT MEASURED** because no suitable target was available.

### Prototype grounding experiments — explicitly non-normative

The branch contains early recall/fact-pack/benchmark experiments, including a zero-allocation `RecallIndex`, an `xs_recall` tool shape, fact-pack tooling and synthetic benchmark scripts.

These are implementation probes only. They do **not** freeze:

- `xs_recall` as the product API;
- one fact-pack schema as the universal Source format;
- exact/alias lexical retrieval as the only provider;
- the current benchmark runner/corpus as the release benchmark;
- current C/Wasm/API shapes for grounding.

Implementation after the contract freeze may reuse useful code, refactor it behind the provider contract, or replace it.

## Historical evidence boundary

`statistics-core-8-ai-r20` is historical evidence tied to its exact older r17 runtime. `v1.0.0-rc.3` evidence belongs only to the exact rc3 release/model/runtime/corpus/surface identities. Neither transfers to rc4 grounding.

Accepted rc3 lessons:

1. native tool-call success is not monotonic with model size;
2. chat-template/tool-protocol compatibility materially affects small-model integration;
3. large model-visible schemas can multiply prompt cost;
4. valid requests reaching ExactScope were much stronger than end-to-end model selection;
5. therefore ordinary grounding should not require a model-visible retrieval tool turn.

## P0 — freeze grounding design and contracts

### P0.1 Product and logical architecture

- [x] make everyday factual grounding/hallucination reduction the flagship objective;
- [x] make original-question prefetch the default path;
- [x] keep model-generated query rewrite/tool retrieval as optional separately costed profiles;
- [x] separate Source, Retrieval Provider, ProviderOutcome, Evidence Policy, GroundingFrame and Model Projection;
- [x] keep retrieval provider implementation replaceable;
- [x] make the minimum embedded core independent from network/clock/tokenizer/JSON requirements;
- [x] keep quantitative `xs_calc`/`xs_eval` as a secondary retained subsystem.

### P0.2 Authority, coverage and failure semantics

- [x] assign authority per target/source binding, never from provider/evidence text;
- [x] use target-grouped frames so authoritative and supplemental facts can coexist;
- [x] define `grounded | none | ambiguous | conflict | unavailable`;
- [x] require completed/sufficient authoritative coverage before `none` is legal;
- [x] keep timeout/error/denied/budget/incomplete coverage distinct from `none`;
- [x] freeze required-provider/sufficiency behavior;
- [x] prevent supplemental evidence from silently filling unresolved authoritative targets;
- [x] define compound-question claim coverage per `target_key`.

### P0.3 Identity, determinism and privacy

- [x] define `GroundingProfile` as immutable behavior identity;
- [x] bind router, source snapshot, provider/index, policy, timeout/budget and projection identities;
- [x] bind embedding/tokenizer/vector/index identity when semantic retrieval is used;
- [x] require captured/replayable evidence for remote-provider benchmark runs;
- [x] freeze deterministic merge/order/tie-break/dedup/truncation rules;
- [x] define stable Evidence Item source/item/revision/content identity;
- [x] define typed text/scalar/canonical-JSON evidence;
- [x] establish opaque host security scope before retrieval;
- [x] prohibit implicit cross-user/tenant cache/evidence reuse;
- [x] keep security/access metadata out of model projection;
- [x] define evidence as untrusted data rather than instructions;
- [x] explicitly avoid claiming that delimiters alone solve prompt injection.

### P0.4 Benchmark contract

- [x] define A=model-only and G=one-call original-question-prefetch with equal answer-generation call count;
- [x] physically/logically isolate serving data from scorer gold;
- [x] prohibit serving access to expected answer/target/source/evidence/provider labels;
- [x] define workload strata for public facts, private/device memory, manuals, stale revisions, distractors, authoritative no-answer, partial provider failure, ambiguity/conflict, multilingual/paraphrase, adversarial evidence and supplemental no-hit;
- [x] define stage-level routing/provider/policy/model failure taxonomy;
- [x] define raw numerators/denominators and exact metric formulas;
- [x] define false-grounding, grounding-penalty and unsupported-authoritative-assertion metrics;
- [x] define cost metrics for evidence/index/token/latency/RAM/storage/energy;
- [x] prohibit post-result alias/index/reranker/profile tuning under the same candidate identity.

### P0.5 Documentation convergence / architecture review

- [x] align every current integration/security/install/compatibility/README/handoff document with the target-group contract;
- [x] mark prototype recall/fact-pack documents/code clearly non-normative wherever still ambiguous;
- [x] remove remaining current-state wording that makes academic operations/tool calls the flagship product;
- [x] run read-only Codex architecture review across normative/current docs;
- [x] resolve every P0 contradiction;
- [x] mark logical Grounding Contract v0.1 **FROZEN_FOR_IMPLEMENTATION** only after the review reports no P0 blocker.

Success criterion: one coherent product and logical contract exists before implementation resumes.

## P1 — freeze concrete machine-readable grounding profile

After P0:

### P1.1 Schemas and canonical encodings

- [x] add/version machine-readable GroundingProfile schema;
- [x] add QueryEnvelope schema;
- [x] add RoutingPlan/TargetPlan schema;
- [x] add ProviderOutcome schema;
- [x] add EvidenceItem schema;
- [x] add GroundingFrame schema;
- [x] add source-snapshot/provider-identity manifest schemas;
- [x] add grounding preregistration schema;
- [x] select and document canonical JSON/digest rules for build/audit artifacts;
- [x] freeze deterministic Model Projection template/escaping/order rules.

### P1.2 Reference profile

Choose a **minimum local reference provider** for the first benchmark candidate without making it the universal contract. The default likely reuses/refactors exact/lexical prototype code because it is small/offline/deterministic, but the provider boundary must permit later vector/application providers without changing frame semantics.

Freeze:

- [x] target namespaces/labels;
- [x] authoritative/supplemental source bindings;
- [x] required coverage/sufficiency;
- [x] provider implementation and index identity;
- [x] preprocessing/ranking/tie-break/dedup rules;
- [x] timeout/retry/cancellation policy;
- [x] evidence/frame/model-context budgets;
- [x] privacy/network policy;
- [x] Model Projection identity.

Success criterion: two independent implementations could build the same logical profile/frame semantics from the schemas/docs.

## P2 — implement frozen contract

Use Codex CLI for independent review/implementation where available. The logical P0 review completed with `NO_P0_BLOCKERS`; later CLI work became credit-limited, so CodexPro Local direct edits/tests continue under the same frozen contract rather than changing the design around tool availability.

### P2.1 Host/provider core

- [x] define provider-neutral host types/interfaces;
- [x] implement QueryEnvelope validation and profile binding;
- [x] implement deterministic Router/TargetPlan for the reference profile;
- [x] refactor/reuse prototype RecallIndex only behind the provider interface where appropriate;
- [x] implement typed ProviderOutcome including timeout/error/denied/budget/incomplete semantics;
- [x] implement source snapshot/provider identity records;
- [x] ensure no serving component can read benchmark gold.

### P2.2 Evidence policy / frame

- [x] validate inherited authority and allowed source/provider bindings;
- [x] implement required coverage/sufficiency;
- [x] implement freshness/validity selection;
- [x] implement deterministic dedup/merge/order/tie-break;
- [x] implement ambiguity/conflict detection for the reference profile;
- [x] implement whole-item budget/truncation behavior;
- [x] implement grouped GroundingFrame with exact state precedence;
- [x] implement audit sidecar records.

### P2.3 Model Projection

- [x] implement deterministic compact projection;
- [x] keep scope/provider scores/internal metadata host-side;
- [x] preserve per-target authority/state;
- [x] escape/delimit evidence as untrusted data;
- [x] add authoritative/supplemental model policy text;
- [x] byte-for-byte projection tests;
- [x] adversarial evidence fixtures.

### P2.4 Transport/package integration

- [x] decide which grounding functions genuinely belong in Rust/C/Wasm versus host-side tooling;
- [x] do not force vector/network providers into the no-import core;
- [x] add stable native/Wasm grounding transport only where the frozen profile needs it;
- [x] preserve rc3 quantitative ABI/semantics;
- [x] package the grounding profile/source/provider/model-projection assets with manifests/checksums;
- [x] keep public rc3 quantitative release descriptions historical and unchanged.

Success criterion: the implemented serving path matches the frozen contract without relying on model tool calling or benchmark gold.

## P3 — build benchmark candidate without inference

### P3.1 Corpus/source generator

- [x] generate physically separated `serving/` and `gold/` trees;
- [x] include all flagship workload strata;
- [x] bind generator seed/revision and every output hash;
- [x] generate candidate-bound synthetic/private facts unlikely to exist in model weights;
- [x] include distractors/stale revisions/no-answer/provider-failure/ambiguity/conflict/injection fixtures;
- [x] include project-authored/frozen public-reference and product-manual-style workloads without importing hidden scorer labels into serving data;
- [x] validate no answer/source/evidence oracle leaks into serving inputs.

### P3.2 Scorer

- [x] implement exact benchmark metric definitions from `docs/BENCHMARK.md`;
- [x] keep gold scorer-only until after model response;
- [x] score routing, retrieval, policy/frame and model answer stages separately;
- [x] report raw counts and denominators before ratios;
- [x] report grounding recovery and grounding penalty;
- [x] report false grounding and authoritative unsupported assertions;
- [x] report token/evidence/index/latency/storage costs.

### P3.3 Preregistration / dry-run runner

- [x] add zero-inference preregistration command;
- [x] bind source/profile/provider/projection/corpus/scorer/model/runtime identities;
- [x] reject any byte/config drift after preregistration;
- [x] enforce one writer and duplicate item/arm rejection;
- [x] preserve complete/invalid/aborted run states with resume forbidden;
- [x] ensure dry-run and runner `--verify-only` never start model inference.

## P4 — no-inference qualification and packaging

Before model benchmark:

- [x] schema/canonicalization/digest tests;
- [x] source snapshot integrity tests;
- [x] serving/gold separation tests;
- [x] deterministic router/provider replay;
- [x] provider completion-order invariance tests;
- [x] authoritative `none` coverage tests;
- [x] partial provider/timeout/error/denied/budget => unavailable tests;
- [x] mixed authority tests;
- [x] freshness/stale revision tests;
- [x] ambiguity/conflict tests;
- [x] evidence canonicalization/content-digest tests;
- [x] security-scope/cache-isolation tests;
- [x] model projection byte-determinism tests;
- [x] adversarial evidence/data-boundary tests;
- [x] existing quantitative Rust/C/Wasm regression suites;
- [x] source design/security/drift checks;
- [ ] fresh final grounding evaluation package build from the final source commit;
- [x] package manifest/SHA256 verifier and deterministic-package tests;
- [ ] final clean-room first-use with zero model inference;
- [ ] actual five-model preregistration dry-run from the extracted final package only;
- [ ] native Windows/Linux command examples verified where that package supports them.

Success criterion: package is independently usable up to preregistration without a developer checkout and without launching a model.

## P5 — stop at benchmark-ready candidate

The current user request ends here.

A candidate may be labeled **READY_FOR_GROUNDING_BENCHMARK** only when:

- [ ] current docs/contracts are internally consistent;
- [ ] Codex read-only review has no unresolved P0 blocker;
- [ ] Grounding Contract/profile/schema/projection bytes are frozen;
- [ ] source/provider/index identities are frozen;
- [ ] serving/gold data are separated and hashed;
- [ ] no-inference conformance/security/determinism tests pass;
- [ ] packaging/clean-room tests pass;
- [ ] preregistration dry-run passes from the frozen package;
- [ ] benchmark model inventory is downloaded/hashed or otherwise ready to use;
- [ ] **no new rc4 grounding model inference has been run**.

At that point create/update a dedicated handoff prompt for a separate benchmark/validation session. That later session will run A/G on the frozen diverse small-model matrix and then, separately, target-device qualification.

## P6 — actual benchmark and target qualification — NOT PART OF CURRENT TASK

Later validation session only:

- run A/G on the diverse small-model matrix;
- optionally run Q/L only when preregistered and justified;
- publish factual accuracy, wrong-confident-answer, false-grounding, abstention/useful-answer and cost breakdowns;
- qualify a representative physical ARM64 target for actual storage/RAM/latency/energy/thermal behavior;
- compare against a larger-model/heavier-grounding alternative only where it reflects a real product decision.

## P7 — support promotion only after evidence

After successful benchmark/target evidence:

- choose exact supported provider/profile/platform identities;
- define update/security/privacy/LTS policy;
- obtain independent external-style integration feedback;
- publish compatibility/qualification records;
- consider stable `v1.0.0` only after unresolved release/security/evidence gates are closed.

## Deferred — academic/technical expansion

[`docs/DOMAIN_EXPANSION.md`](docs/DOMAIN_EXPANSION.md) remains design history/guidance for the quantitative subsystem. Statistics/Economics breadth and Finance/Physics/Chemistry additions are not a near-term flagship objective.

Resume domain expansion only after grounding demonstrates measured value or a concrete customer workload requires a narrow deterministic method slice. Never create one runtime per discipline, a general CAS, a formula dump, or a giant model-visible catalog.

## Current single next action

**P0 is complete and the logical contract is `FROZEN_FOR_IMPLEMENTATION`. Proceed immediately through P1-P5: freeze machine-readable profile/schemas, implement the provider-neutral grounding path, complete no-inference conformance/security/package/preregistration checks, and stop at `READY_FOR_GROUNDING_BENCHMARK` without launching model inference.**
