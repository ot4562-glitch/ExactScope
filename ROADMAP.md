# ExactScope roadmap

No dates are promised. This roadmap is ordered by **fresh compiler-value evidence, factual reliability, false-grounding avoidance, total serving cost, qualification integrity, evidence quality, and low-ownership integration economics**.

Release context: **ExactScope v1.1.0 is the software/architecture release that retains the Linux x86-64 native grounding C ABI/XSGI path as the stable software surface. New qualification/control-plane, host-integration, Bridge and enterprise DocQA surfaces are experimental/reference. Physical ARM64 qualification, enterprise/customer qualification and demonstrated economic advantage remain unclaimed.**

The current v1.1 product question is:

> Can a restricted workload-specific policy compiler produce an independently qualified execution profile for an **existing constrained or operationally pinned AI stack** that meets predeclared task-quality requirements while reducing total serving cost—and can that process eventually require less search/qualification work than competent generic tuning?

The three layers must remain separate:

```text
Semantic Execution Policy Compiler   = implemented restricted lowering / research kernel
Qualified Execution Profile          = proposed customer-facing deliverable
Reference-Preserving Cost Reduction  = first conservative Stage 1 algorithm
```

The first commercial validation wedge is high-volume bounded enterprise document QA with authoritative versioned evidence and measurable serving economics, narrowed initially toward short factual answers, extraction, typed decisions, and citation-bound outputs. Small/on-device retrofit remains an important longer-term market and architecture constraint, not the automatic first proof.

## Current checkpoint

**v1.1.0 is now the bounded software/architecture release target. The stable support promise remains the Linux x86-64 native grounding C ABI/XSGI path; new qualification/control-plane, host-integration and Bridge surfaces are experimental/reference.** Positive development evidence remains workload- and host-specific: NQ froze `precision-context-v5` at 3 KiB/cap8; real-host Hotpot froze `host-ranked-hybrid-h1-v0`; the final 20-model NQ/Hotpot A/G panel is complete. A later Kubernetes Operations long-document proxy failed its frozen ordinary-RAG quality margin (`G-R = -10.99 pp`, 95% CI `[-22.76,-0.48] pp`), every bounded diagnostic candidate failed, and `selected_arm=null`. Therefore v1.1.0 is not a universal efficacy/ordinary-RAG/enterprise qualification claim.

The active path is now:

```text
stable v1.0 reference
 -> preserve the qualified-execution core and host ownership boundary
 -> single-source precision: precision-context-v5 / 3K / cap8
 -> generic multi-source composition semantics: multihop-coverage-v1 / 3K / cap12
 -> real-host Hotpot attach: LlamaIndex BM25 top12 + frozen host-ranked-hybrid-h1-v0
 -> H1 survived fresh validation32 + predeclared stability64 against ordinary RAG
 -> final frozen 20-model NQ/Hotpot A/G panel complete; public policy tuning closed
 -> keep evidence composition + explicit qualified budget in Workload Contract / Candidate Policy without treating H1 as a universal default
 -> freeze the public NQ/Hotpot harnesses and do not retune from final-panel outcomes
 -> enterprise confirmatory pipeline implemented: prereg -> exact-artifact Study Contract -> fail-closed readiness receipt -> three-arm observations + deterministic run sealing -> offline score -> frozen paired analysis -> owner decision -> canonical evaluation package + generic attestation bridge
 -> Study Contract pre-binds exact Candidate Execution Policy + Workload Contract + Host Manifest + gold-free confirmatory question set and runner/readiness/scorer/analysis/decision implementations
 -> Kubernetes long-document proxy failed its ordinary-RAG margin; selected_arm=null; no more proxy tuning
 -> v1.1.0 release closure: stable native C ABI/XSGI + experimental/reference architecture surfaces; run regression/package/clean-room gates
 -> push exact release-candidate commit; run GitHub CI/release checks; tag the exact verified commit `v1.1.0` without reopening benchmark policies
 -> only after useful source policies exist, test prospective prior-transfer/search reduction
 -> add frontier-provider lowering only from qualified workload requirements
 -> add broader runtime/tool policies only when contract evidence requires them
 -> post-release, only real owner-bound qualification may unlock enterprise/customer/economic claims or further optimizer expansion
```

FEVER Stage 1 is closed at **`ReferenceOnly`** after all 1,200 calibration observations: `P=null`, `T=F`, and the 600-item held-out remains unscored and retired from revised-rule inference. The reused-screen same-model attached diagnostic showed that amplification is real but workload dependent: NQ initially improved under precision compression while Hotpot regressed because complete support-set coverage was overcompressed. Fresh follow-up then found the original NQ 2 KiB cap could also overcompress some single-source cohorts, so the active NQ candidate moved prospectively to 3 KiB rather than preserving a result-dependent 2 KiB default.

The completed reused-screen attached diagnostic is recorded in [`docs/V1_1_LIVE_ATTACHED_DIAGNOSTIC_RESULT.md`](docs/V1_1_LIVE_ATTACHED_DIAGNOSTIC_RESULT.md). Hotpot's earlier generic composition development is recorded in [`docs/V1_1_MULTIHOP_POLICY_DEVELOPMENT_RESULT.md`](docs/V1_1_MULTIHOP_POLICY_DEVELOPMENT_RESULT.md), with its separate stable-v1 comparator in [`docs/V1_1_MULTIHOP_V1_CONFIRMATION_RESULT.md`](docs/V1_1_MULTIHOP_V1_CONFIRMATION_RESULT.md). NQ's failed 2K regression, 3K development/validation, and separate stable-v1 confirmation are recorded in [`docs/V1_1_SINGLEHOP_POLICY_DEVELOPMENT_RESULT.md`](docs/V1_1_SINGLEHOP_POLICY_DEVELOPMENT_RESULT.md). The later real-host LlamaIndex diagnosis, H1 freeze, validation/stability evidence, and final 20-model A/G panel are consolidated in [`docs/V1_1_AG_EFFECT_SHOWCASE.md`](docs/V1_1_AG_EFFECT_SHOWCASE.md). The final panel observed NQ mean F1 **12.44% -> 21.68% (+9.24 pp)** and Hotpot mean F1 **11.63% -> 31.42% (+19.79 pp)** across 16 valid models per workload, while retaining regressions and protocol N/A. These results close public benchmark-driven policy tuning; they do not authorize a universal default or product qualification.

The enterprise confirmation machinery is now implemented far enough that **the blocker is data/business truth rather than benchmark plumbing**. The reference chain freezes the owner-approved records and evidence contract, validates and binds the exact Candidate Execution Policy + Workload Contract + Host Capability Manifest and gold-free confirmatory question set before outcomes, requires an independent ordinary alternative, freezes runner/readiness/scorer/paired-analysis/decision implementation identities and fixed non-serving economic counters, and requires a no-inference readiness preflight to revalidate that complete frozen bundle immediately before launch. The readiness receipt is then carried by every observation; its absolute `confirmatory_run_output` is the frozen artifact root for observations and the sealed manifest, and the run manifest is deterministically generated from the frozen identities rather than supplied as a free-form post-run record. It then verifies the complete three-arm observation matrix, scores only frozen offline adjudication, reruns the frozen paired quality/economic analysis, and requires a separate workload-owner decision. A passing decision is still not a profile: `enterprise_docqa_attest.py` revalidates the decision, remaps the observed Integrated metrics to the pre-bound Workload Contract, constructs a canonical evaluation package, invokes the generic Qualification Attestation validator, and can emit the attestation standalone while still emitting no Qualified Execution Profile. The generic `qualified_execution.py make-profile` command is the separate final constructor and revalidates that attestation against the exact Candidate/Workload/Host binding before writing a profile. No real enterprise confirmatory model call is authorized until an actual workload owner, authorized corpus/retriever, competence thresholds, economic coefficients/counters and statistical parameters are supplied and frozen.

Host runtimes continue to own retrieval execution/authorization, tokenizer/template, exact token accounting, inference, scheduling/batching, cache, constrained/speculative decoding, accelerators, fallback and deployment. ExactScope owns the workload contract, semantic evidence/context policy, qualification artifacts, admission/finalization obligations and drift/requalification boundary. **Per-query adaptive routing is not authorized** by the current evidence; the supported direction is compile-time fixed workload-policy separation.

No new result may be tuned on its own held-out identity after inference. The normative v1 Grounding Contract remains the stable-v1 semantic reference. Current product semantics are in [`docs/V1_1_ULTIMATE_PRODUCT_ARCHITECTURE.md`](docs/V1_1_ULTIMATE_PRODUCT_ARCHITECTURE.md) and [`docs/V1_1_PRODUCT_DIFFERENTIATION.md`](docs/V1_1_PRODUCT_DIFFERENTIATION.md); research rules are in [`docs/V1_1_EXPERIMENT_PROGRAM.md`](docs/V1_1_EXPERIMENT_PROGRAM.md).

Academic-domain expansion, adapter count and runtime-feature wrapping are secondary to prospective compiler value, real customer-like retrieval economics, and later transfer evidence.

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

## Historical P7/P8 — v1 productionization and release — COMPLETE FOR THE DECLARED v1.0 SOFTWARE SCOPE

The old P7/P8 sequence led to the published v1.0.0 Linux x86-64 grounding package. Its historical unchecked items must not be read as the active v1.1 plan. Physical ARM64 resource qualification remains unclaimed and may be revisited only when a real target/customer workload justifies it.

## v1.1 R0 — establish the experiment rack — ACTIVE

- [x] declare exploration budget separate from release-promotion budget;
- [x] keep the current native archive as a reference configuration rather than a fixed design;
- [x] define module families for retrieval, projection, answer contract, zero-call, preparation/identity, delivery bridge and backend-native acceleration;
- [x] define interaction and leave-one-out reasoning in `docs/V1_1_EXPERIMENT_PROGRAM.md`;
- [ ] make experiment identities/configuration mechanically reproducible without entangling the stable core;
- [ ] expose a compact result ledger for isolated, pair/neighborhood and leave-one-out experiments;
- [ ] define a Pareto report over quality/safety/model calls/tokens/latency/RAM/bytes/integration cost.

## v1.1 R1 — external runtime pressure tests — ACTIVE

- [x] analyze ONNX Runtime GenAI C/C++ generation ownership;
- [x] implement backend-neutral `complete | generate` Bridge delivery data without grounding-policy duplication;
- [x] prove deterministic completion can bypass the inference runtime;
- [x] compile a small C++ ORT adapter against current upstream headers;
- [x] execute a real ExactScope -> ORT GenAI 0.15.2 generation plumbing smoke and return raw output through ExactScope strict validation;
- [x] record v1.1 API friction in `docs/V1_1_INTEGRATION_FEEDBACK.md` instead of changing core immediately;
- [x] pressure-test the same delivery semantic against current ExecuTorch `IRunner` headers with a fake-runner executable; real `.pte` + tokenizer execution remains unclaimed;
- [x] pressure-test the same delivery semantic against LiteRT-LM Engine/Conversation using official fixtures; grounded answer-quality success remains unclaimed;
- [x] identify repeated context-fit/runtime-capability friction without freezing a broad native ABI;
- [ ] run a real-model ExecuTorch `.pte` + tokenizer smoke only if it remains useful for the product boundary rather than runtime-count collection.

## v1.1 R2 — nonlinear amplifier search

High-priority neighborhoods:

- retrieval-query separation × candidate overfetch × evidence projection;
- evidence density/order × answer-contract surface;
- deterministic host completion × remaining model workload concentration;
- immutable prefix identity × host-native prefix/system cache;
- compact literal evidence × no-second-model n-gram speculation where the runtime already supports it;
- answer-contract semantics × backend-native structured decoding.

The rack may exceed final release resource targets during this phase. Research still requires exact candidate identities, gold isolation, negative-cell reporting and safety accounting.

## v1.1 R3 — material distillation, separate from compiler selection

- select high-value causal regions for further study, not the smallest early artifact;
- remove each module in turn and measure marginal loss;
- replace expensive modules with smaller equivalents when possible;
- use Pareto analysis to understand material/architecture tradeoffs;
- do **not** treat that Pareto frontier as the current Harness Distillation selection rule;
- keep negative/quarantined materials available for reproducibility but unavailable to the product compiler.

## v1.1 R4 — reference-preserving compiler-value proof — COMPLETE / STOPPED

- [x] implement calibration-only compile + frozen held-out qualify + immutable bundle verification;
- [x] complete first fresh 6+6 transfer and record **REJECTED** candidate with no deployable profile;
- [x] add paired preservation against the predeclared reference as a provisional calibration constraint;
- [x] freeze a fresh **120 calibration / 600 held-out** FEVER study with transitive evidence-page grouping, source/claim exclusions, exact finite-population gates, cost/timing protocol, competence record, conventional tuner `T`, frozen contract surface and immutable preregistration;
- [x] execute all 1,200 calibration observations with zero mandatory violations;
- [x] stop at preregistered **`ReferenceOnly`**: `P = null`, `T = integrated`; no cheaper frozen candidate matched the Reference's aggregate success count and none preserved all Reference successes;
- [x] keep the 600-item held-out unscored and retire it from rescue/new-rule confirmatory inference;
- [x] record the result as **algorithm-diagnostic-only**; no deployable Qualified Execution Profile and no compiler-value success;
- [x] obtain Astra High post-result review: narrow the product claim, pivot the workload, keep the compiler thesis only as a research hypothesis;
- [ ] preserve the stopped FEVER evidence and bound source fingerprints; do not repair the selector against this frozen held-out.

## v1.1 R5 — competent enterprise document-QA product proof — ACTIVE

- [x] freeze the v1.1+ north-star architecture as **Qualified AI Execution Control Plane -> Semantic Execution Policy Compiler -> Qualification/Configuration Optimizer -> Qualified Execution Profile**, while keeping each claim evidence-gated;
- [x] obtain Astra High architectural review (`GO_WITH_FIXES`) and accept the required binding-enforcement, obligation-semantics, opaque-provider validity, lightweight acceptance, and ordinary-alternative comparison fixes;
- [x] implement immutable Workload Contract / Host Capability Manifest / Candidate Execution Policy / Qualification Attestation / Execution Receipt schemas and canonical validators;
- [x] implement the reference admission/finalization protocol, including stale-profile, cross-request receipt reuse, changed-settings and rejected-output conformance tests;
- [ ] enforce that protocol in a real supported host integration, including authenticated check results and host-owned one-shot receipt consumption;
- [x] implement qualification-validity scopes for inspectable pinned hosts and opaque/provider-observable frontier hosts;
- [x] implement drift classification and targeted/full requalification planning;
- [ ] define one bounded document collection and question population using real host retrieval rather than an oracle evidence pool;
- [ ] freeze customer/workload-owner competence gates for correctness, citation/evidence support, abstention and unacceptable errors before confirmatory scoring;
- [ ] establish eligible Base and integrated-style fixed configurations on development data before any optimizer qualification branch;
- [ ] preregister **integrated-style vs Base** as the primary product-value comparison, including total customer economics rather than single-concurrency service time alone;
- [ ] include one competent ordinary deployable configuration/tuning/eval alternative and one representative update/requalification cycle in the commercial proof;
- [ ] keep any reference-preserving cheaper-policy branch conditional: if calibration produces no eligible `P`, stop that branch without rescuing with F/T;
- [ ] include the conventional comparator `T` whenever a policy-selection branch is tested;
- [ ] keep host retrieval execution, tokenizer/template, inference, scheduling/cache, native decoding, speculation and fallback host-owned;
- [ ] defer cross-host transfer and adaptive per-query routing until a useful competent source policy exists;
- [ ] measure the native-free semantic/qualification boundary before making native code a v1.1 requirement.

## v1.1 R6 — live attached amplification/economics diagnostic

- [ ] on a fresh diagnostic cohort, attach the same real local model/runtime to stable v1 and fixed v1.1 Integrated paths;
- [ ] measure whether the original semantic amplification signal survives the narrowed architecture;
- [ ] compare task quality/evidence behavior, model calls/tokens, E2E latency, host work and diagnostic economics;
- [ ] attribute differences to declared mechanisms; do not reuse the sealed FEVER 600 or promote this diagnostic directly into product qualification;
- [ ] preserve a hard outcome where v1 is better/cheaper and report it rather than tuning the diagnostic cohort.

## v1.1 R7 — frontier-host lowering and qualification validity

- [ ] lower the same restricted policy/qualification artifacts to one frontier-capable provider surface without owning provider inference/tools;
- [ ] represent dependencies as pinned / host-asserted / provider-guaranteed / unknown rather than inventing inaccessible exact identities;
- [ ] qualify reasoning/context/tool/structured-output settings only under explicit validity/expiry/invalidation rules;
- [ ] test whether the same qualified workload behavior can be maintained with less reasoning/context/tool work or lower total economics.

## Deferred — academic/technical expansion

[`docs/DOMAIN_EXPANSION.md`](docs/DOMAIN_EXPANSION.md) remains design history/guidance for the quantitative subsystem. Statistics/Economics breadth and Finance/Physics/Chemistry additions are not a near-term flagship objective.

Resume domain expansion only when the generic amplifier architecture is understood or a concrete customer workload requires a narrow deterministic method slice.

## Current next action

**Keep v1.1 unreleased and preserve the stopped FEVER Stage 1 exactly as audited. The next execution target is one competence-gated bounded enterprise document-QA study with real host retrieval: establish viable Base/reference behavior on development data, freeze customer-relevant correctness/evidence/abstention/economic gates, preregister integrated-style vs Base as the primary product-value question, and keep any cheaper-policy compilation branch conditional. Do not score the retired FEVER 600, do not relax the 15% cost gate retroactively, and do not start cross-host transfer or adaptive routing before a useful competent source policy exists.**
