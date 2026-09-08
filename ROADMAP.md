# ExactScope roadmap

No dates are promised. This roadmap is ordered by **everyday factual reliability, false-grounding avoidance, small-model cost, evidence quality, and retrofit economics**.

Release context: **ExactScope v1.0.0 is the stable Linux x86-64 native grounding software/package release. The selected r25 behavior, native C ABI, footprint-gated package, and final-archive C11 clean-room path are complete. v1.0.0-rc.3 remains immutable historical quantitative evidence; physical ARM64 qualification remains unclaimed.**

The flagship product question is:

> Can a compact provider-neutral grounding layer make an already-deployed small/on-device model more correct and less confidently wrong on ordinary factual questions, at low enough storage/RAM/token/latency/integration cost to beat a larger model, much larger context, heavyweight RAG stack, remote dependency, or hardware upgrade?

## Current checkpoint

The rc3 public release and its external-user qualification are closed and immutable. The selected **r25** grounding behavior is now integrated with the native C ABI and stable Linux x86-64 v1 package. The frozen seven-model matched screen spans 135M to 3.8B local models, and its semantic scores were unchanged after native/release integration. r5 remains frozen historical comparison evidence.

The post-v1 path is product expansion and target qualification, not another broad prompt search:

```text
stable Linux x86-64 grounding runtime
 -> preserve deterministic r25 semantics and Python/Rust/C-ABI parity
 -> add provider integrations only behind the Grounding Contract
 -> keep default-install footprint bounded and provider data accounted separately
 -> improve integration/discovery/LTS without broadening claims beyond evidence
 -> qualify representative physical ARM64 hardware before wearable resource claims
 -> add further stable targets only after target-specific clean-room/resource evidence
```

No new result may reuse historical run evidence or be tuned under the same identity after inference. The normative Grounding Contract remains v0.1; benchmark/package identities carry the selected implementation behavior and qualification evidence.

Academic-domain expansion remains secondary to grounding reliability, provider integrations, and real-device qualification.

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

Implementation and review must follow the frozen contract and preserve the public evidence/identity rules. Tool availability is never a reason to change product semantics or weaken verification.

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
- [x] fresh grounding evaluation package built from the frozen candidate source commit;
- [x] package manifest/SHA256 verifier and deterministic-package tests;
- [x] final clean-room first-use with zero model inference, including post-use package re-verification;
- [x] actual five-model preregistration dry-run from the extracted final package only;
- [x] native Windows/Linux package verification and zero-inference dry-run commands verified.

Success criterion: package is independently usable up to preregistration without a developer checkout and without launching a model. **Met by the r5 baseline and retained as a mandatory gate for every optimization candidate.**

## P5 — historical five-model baseline — COMPLETE

Integrity-corrected **r5** source `e6c3558642c77e379358b9f59aedd92abf7473f4` completed the five-model A/G benchmark with post-shutdown run checksum verification. r5 remains immutable historical comparison evidence.

## P6 — behavior selection — COMPLETE

- [x] preserve r5 as historical comparison evidence;
- [x] isolate deterministic unresolved-state host completion;
- [x] test compact evidence/policy and multiple answer contracts independently;
- [x] add one-time model-identity-bound contract calibration rather than per-question retries;
- [x] expand the model matrix to 135M and 1B wearable-class models;
- [x] preserve contract-native scalar facts instead of flattening them into text;
- [x] select r25 after the seven-model source-run comparison;
- [x] reject later forced-contract variants that regressed low-end models.

## P7 — productionize and qualify the selected behavior — ACTIVE

- [x] expose deterministic unresolved/scalar host completion in the shared grounding runtime;
- [x] implement the selected compact model surface in `tools/grounding_v1_surface.py`;
- [x] implement the loopback-only llama.cpp reference adapter;
- [x] add adapter/surface identity and regression tests;
- [ ] make the immutable-package benchmark runner execute exactly the selected r25 behavior rather than the historical r5/r6 path;
- [ ] freeze the final source commit and rebuild the scalar candidate from that exact source;
- [ ] build and verify a deterministic grounding evaluation package containing the selected adapter/surface;
- [ ] preregister and rerun the seven-model matrix from the extracted immutable package;
- [ ] replace source-run-only README claims with release-qualified evidence where appropriate;
- [ ] run clean-room package, publication, security, license, native, Wasm and SDK gates on the exact release tree.

## P8 — target qualification and release

Before a public/stable claim:

- qualify a representative physical ARM64 target for actual storage/RAM/latency/energy/thermal behavior;
- define supported provider/profile/platform identities and update/security/privacy/LTS policy;
- run `python3 tools/audit_publication.py` on the exact Git tree and again on extracted release archives;
- keep internal agent prompts, handoffs, local paths, raw runs and preregistrations outside the public repository/package;
- obtain independent external-style integration feedback;
- publish only deliberately public compatibility/qualification records;
- consider stable `v1.0.0` only after unresolved release/security/evidence gates are closed.

## Deferred — academic/technical expansion

[`docs/DOMAIN_EXPANSION.md`](docs/DOMAIN_EXPANSION.md) remains design history/guidance for the quantitative subsystem. Statistics/Economics breadth and Finance/Physics/Chemistry additions are not a near-term flagship objective.

Resume domain expansion only after grounding optimization/lightweighting demonstrates measured product value or a concrete customer workload requires a narrow deterministic method slice.

## Current single next action

**Freeze and benchmark r6, compare it with immutable r5, then let the measured result determine r7 and the final lightweighting target. Do not push or release to GitHub before the publication audit passes on the final cleaned tree.**
