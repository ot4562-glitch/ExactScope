# ExactScope v1.1 research status

Status: **active local research; FEVER Stage 1 closed at `ReferenceOnly`; frozen NQ 3K/cap8 and real-host `host-ranked-hybrid-h1-v0` completed the final 20-model NQ/Hotpot A/G public robustness panel with positive mean uplift across 16 valid models; public benchmark-driven policy tuning is now closed; enterprise document-QA confirmatory infrastructure is implemented but real workload/owner/economic/statistical inputs are not yet frozen; v1.1 remains unreleased**
Updated: **2026-09-13**

This document is the continuity checkpoint for the current v1.1 research program. It records what is already established, what is still experimental, what external work is waiting, and what the next research step is. When another session or contributor resumes v1.1 work, read this document before choosing a new task.

## Current handoff checkpoint: qualification core

The north-star reference core now validates all six artifact schemas, including
local-only nested profile references. Candidate/profile construction detaches
mutable input objects. Compilation requires an exact host-declared implementation
binding for each deterministic obligation; an arbitrary check name cannot satisfy
an obligation. Duplicate gate/lowering IDs fail closed.

Finalization requires the trusted host's current request, evidence, rendered-request
and settings binding, and rejects changed or malformed admission receipts. Profile
and dependency expiry are checked even when the caller omits the clock. Declared
observation policies require affirmative host checks at admission and finalization.
Capability/check-surface drift forces full requalification; targeted refresh remains
restricted to prospectively declared dependency IDs.

These are reference conformance properties, not a deployed integration or empirical
answer-truth guarantee. Hosts still authenticate receipts, execute the declared checks,
prevent same-request replay, and enforce admission/finalization before qualified release.
The qualification authority must authenticate evidence and apply the commercial
ordinary-alternative and total-economics requirements; generic artifact validation
alone does not establish commercial qualification. No model inference was used for
these implementation tests. The later attached diagnostic and fresh policy studies remain development evidence rather than commercial qualification. Hotpot selected a frozen 3K coverage-first policy that improved untouched-validation F1 by **+6.82 pp** over the prior precision path and later beat stable v1 by **+6.22 pp F1** on another untouched32. NQ separately exposed a 2K precision regression, selected 3K/cap8 on pre-frozen development32, improved **+8.47 pp F1** over 2K on untouched validation32, and later beat stable v1 by **+1.63 pp F1** on another untouched32.

The enterprise confirmation path is now implemented as a fail-closed reference chain rather than a one-shot benchmark script: preregistration freezes workload/retrieval/competence/config/timing/economic/analysis records and evidence semantics; the Study Contract validates and pre-binds the exact Candidate Execution Policy + Workload Contract + Host Capability Manifest, a competent ordinary alternative, the exact gold-free confirmatory question-set digest/count, runner/readiness/scorer/paired-analysis/decision source identities, and non-serving economic counters before outcomes. `enterprise_docqa_readiness.py` performs no inference or retrieval and must revalidate that complete frozen bundle immediately before launch; its receipt is then part of the run identity, every observation carries that receipt digest, and `enterprise_docqa_observations.py --seal-run-output ...` deterministically constructs the run manifest instead of accepting a free-form post-outcome identity record. The observation validator enforces the complete three-arm/no-gold/no-retry/budget-cap matrix; deterministic scoring consumes frozen offline adjudication and can emit only `GATES_PASSED_CANDIDATE`; `enterprise_docqa_analysis.py` recomputes the frozen score core and performs the preregistered paired quality/economic comparison against Base and the ordinary alternative; the workload-owner decision is separately bound; finally `enterprise_docqa_attest.py` remaps the Integrated score to every pre-bound Workload Contract empirical requirement and calls the generic Qualification Attestation validator while exposing the canonical evaluation package, including question/readiness/source identities. Even that bridge emits no Qualified Execution Profile. None of these synthetic/conformance tests constitute enterprise product evidence, and no real confirmatory model call is authorized yet.

Current 2026-09-13 verification checkpoint after the final panel and big-tech review-surface hardening: the enterprise-to-generic qualification chain remains at its **106/106** targeted checkpoint; benchmark discovery passes **165/165**; `tools.test_qualified_execution` passes **36/36**; the bridge/common + ORT + LiteRT-LM conformance group passes **48/48**; the tracked H1 projector reproduces the already-scored stability64 H1 payload **64/64 byte-for-byte**; the final panel aggregator/README renderer remains **2/2**; the new tracked public-evidence verifier reports PASS and its tamper/overclaim/comparison/model-set tests pass **5/5**; `tools/demo_qualified_execution.py` executes the lifecycle and fail-closed drift cases as `CONFORMANCE_DEMO_ONLY`; `tools/validate_design.py` passes on **805 repository files**; and `tools/audit_publication.py` reports **PASS (614 public-candidate files checked)**. The final panel itself remains **40/40 scheduled serving attempts**, **32 scored model-task pairs / 8 reason-coded protocol N/A**, with **383 non-detached artifacts** still matching the frozen checksum set exactly and README's final-panel marker still byte-for-text equivalent to the frozen `README_SNIPPET.md`. These are public-development robustness/conformance checks only, not enterprise product evidence.

The real-host development path is now materially stronger than the earlier fixed multi-source projector. With host-owned LlamaIndex BM25 retrieval held fixed, the initial ExactScope multi-hop shaping lost **21.37 pp F1** to ordinary RAG on the diagnostic Hotpot32. A bounded mechanism diagnosis isolated the loss, selected `host-ranked-hybrid-h1-v0` on that already-open cohort, then froze H1 before an untouched validation32 and a separately predeclared stability64. Stability64 observed model-only A at **7.82% F1**, ordinary RAG at **35.04% F1**, and frozen H1 at **40.70% F1**: H1 was **+32.88 pp vs A** and **+5.66 pp vs ordinary RAG**, with **+7.81 pp EM vs ordinary RAG**, fewer evidence bytes/input tokens, and all declared development competence gates passing. Its paired F1 interval still crosses zero, so this is competence/robustness evidence rather than superiority or qualification. D-130 freezes H1 and stops further public Hotpot tuning; D-131 makes the new two-workload 20-model panel the last public robustness benchmark and forbids policy reselection from its results.

That final panel is now complete. On the fixed 20-model identity, **16/20 models produced valid paired results on both workloads**. NQ fresh post-freeze64 averaged **12.44% → 21.68% F1 (+9.24 pp)** with 14 improvements / 0 ties / 2 regressions. Hotpot stability64 with host-owned LlamaIndex BM25 + frozen H1 averaged **11.63% → 31.42% F1 (+19.79 pp)** with 15 improvements / 0 ties / 1 regression. Across all **32 valid model-task pairs**, the equal-weight descriptive mean uplift was **+14.52 pp**. In this reporting, A is same-model model-only and G is the frozen ExactScope path; the Hotpot cross-model number is not ordinary-RAG→H1. The full README retains negative cells and leaves four unsupported model identities as N/A rather than zero. This closes the public benchmark loop; the next empirical blocker is the real owner-bound qualification workload, not another public-data benchmark.

The external-review surface is now evidence-first rather than dependent on local `target/` output: `benchmarks/v1.1-final-public-evidence.json` carries the sanitized frozen 20-model result, `tools/verify_v11_public_evidence.py` recomputes the model set/A→G arithmetic/means/N/A/claim boundary and fails closed on comparison or qualification-claim drift, `tools/demo_qualified_execution.py` exposes the artifact/admission/finalization/drift lifecycle as `CONFORMANCE_DEMO_ONLY`, and `docs/V1_1_TECHNICAL_REVIEW.md` is the 10-minute reviewer path. A read-only GPT-6 Astra public-claims review returned `APPROVE WITH CONDITIONS`; its required edit was to make A/G comparators, 64-question counts, 16/20 denominators, four protocol N/A identities and the Hotpot ordinary-RAG limitation explicit at the headline. D-132 freezes that public-claim discipline, including the trusted-host caveat and backend-specific runtime evidence levels.

The subsequent Kubernetes Operations public proxy is a deliberate negative transfer result. In the only evidence-eligible initial run, ordinary LlamaIndex RAG utility was **28.51%** versus initial ExactScope G at **17.51%**, so **G−R = −10.99 pp** with paired-bootstrap 95% interval **−22.76 pp to −0.48 pp** and the frozen −2 pp quality margin failed. The single allowed bounded diagnostic also failed: C1 **−4.42 pp**, C2 **−7.06 pp**, RAW2560 **−4.80 pp** versus R; `selected_arm=null`; validation32 was not served. Invalidated r1/r2/r3 run identities remain preserved with provenance. Public proxy tuning is therefore closed without a pass.

A second read-only GPT-6 Astra release-scope review returned `APPROVE WITH CONDITIONS` and judged a normal `v1.1.0` tag defensible as a **software/architecture release**. Stable support is limited to the existing Linux x86-64 native grounding C ABI/XSGI path; qualification/control-plane workflows, enterprise DocQA, host integration, Bridge and demos are experimental/reference. Enterprise qualification and economic advantage remain post-release evidence gates rather than prerequisites for the software tag.

## 1. Release and development boundary

- `v1.1.0` is the authorized **software/architecture release** once the exact release commit clears the final regression/package/CI gates.
- The stable support contract remains the **Linux x86-64 native grounding C ABI/XSGI** path; new qualification/control-plane, enterprise DocQA, host-integration, Bridge and demo surfaces are experimental/reference.
- Public benchmark/proxy policy tuning is closed. The failed Kubernetes proxy remains a release-visible negative result and may not be tuned away for the tag.
- Owner-bound enterprise qualification is **not required for the software tag**, but remains required before enterprise/customer-value, production-readiness or economic-superiority claims.
- The current sub-1-MiB target is a later **promotion/distillation constraint**, not an exploration constraint.
- Stable v1 semantics and release artifacts remain the regression anchor. Experimental work must stay detachable enough that a failed idea can be removed without rewriting the stable grounding model.

The operating rule is:

```text
protect stable v1
  + aggressively explore local v1.1
  + measure causal/nonlinear gains
  + distill only after the strongest region is understood
  + publish nothing as v1.1 until separately approved
```

### 1.1 Product thesis now guiding the research

The research target is no longer "make the grounding package smaller" or "build a runtime amplifier" in isolation. After the preregistered FEVER `ReferenceOnly` stop and the post-result Astra review, the hierarchy is now:

```text
current product category           = Qualification / Configuration Optimizer
customer-facing qualified artifact = Qualified Execution Profile
research hypothesis                = Semantic Inference Policy Compiler
stopped FEVER algorithm            = Reference-Preserving Cost Reduction
```

The internal shorthand **Same model. Same runtime. Better answer.** remains a research objective, not a universal product claim. The latest evidence now supports a narrow compile-time claim: prospectively declared single-source versus multi-source evidence requirements can lower to different fixed bounded policies, and both current 3 KiB candidates survived untouched same-host stable-v1 comparison in their public development workloads. It still does **not** establish customer-qualified cost compilation, cross-host transfer, a new technical category, or a moat.

ExactScope must not become a competing inference runtime, full RAG stack, vector database, generic evaluator, observability system, or agent/test-time-scaling loop. The host owns retrieval execution and authorization, corpus/index management, tokenizer/chat-template rendering, exact token accounting, inference, scheduling/batching, KV/prefix caches, constrained/speculative decoding, accelerators, application fallback, activation, and rollback.

The minimum v1.1 semantic center is deliberately narrower:

1. **evidence sufficiency and context admission** under explicit provenance/coverage rules with host-confirmed exact fit;
2. **answer-contract lowering and deterministic finalization** against the actual model output.

Proof-based `Complete` is optional and requires a sound registered verifier for the current authorized evidence. Cache/speculation/runtime adapters and broad zero-call QA do not define the product. The Workload Contract now has a restricted optional evidence-composition surface: `single-source-precision`, `multi-source-coverage`, or backward-compatible `unspecified`. Known composition policies require an explicit `evidence_budget_bytes`; the reference compiler rejects known composition/policy mismatches. Current development candidates are 3 KiB/cap8 precision and 3 KiB/cap12 coverage. This is compile-time workload semantics, not a dataset-name switch or per-request adaptive router.

The proposed compiled deliverable is not a mutable all-in-one Amplifier Profile. A frozen **Candidate Execution Policy** is a separate immutable object from its **Qualification Attestation**. The customer-facing **Qualified Execution Profile** is the qualified pair, while request-specific evidence, exact-fit confirmation and proof live in a request-bound receipt.

The first fresh compiler-transfer experiment rejected its selected cheaper candidate. The larger prospectively frozen Qwen/FEVER Stage 1 then executed all 1,200 calibration observations and stopped with:

```text
ReferenceOnly
P = null
T = F = integrated
```

The Reference achieved 52/120 calibration successes. No cheaper frozen candidate matched that aggregate success count, and none preserved every Reference success. The conventional tuner therefore also returned the Reference. The 600-item held-out was **not scored**. The formal result is `NOT_EVALUATED_REFERENCE_ONLY`, and the study was already prospectively classified algorithm-diagnostic-only because no defensible absolute FEVER product-competence floor existed.

This closes the current FEVER selector proof. The sealed 600 is retired from revised-rule confirmatory inference, the 15% cheaper-reference gate is not relaxed, and new policy families require fresh data.

The next empirical priority remains a **competence-gated bounded enterprise document-QA study with real host retrieval**, but the generic confirmatory plumbing is no longer the blocker. The study now needs one real authorized workload and owner/evaluator, viable Base/Integrated/ordinary-alternative development evidence, frozen correctness/evidence/abstention/unacceptable-error requirements, real retrieval/index identities, leakage grouping, executable total-economic counters/coefficients including fixed integration/qualification/refresh burden, and a sample-design-appropriate statistical analysis implementation frozen by source digest. Only after those inputs are real may confirmatory execution start. Integrated-style versus Base remains the primary product-value question, while the ordinary alternative prevents a protected comparison and cheaper-policy compilation remains conditional.

Package size remains important for adoption, but **smallness is not the moat**. The only plausible long-term moat hypothesis is prospective reusable interaction knowledge that makes future qualification materially cheaper or more reliable; it is not yet demonstrated and should not be tested across hosts until a useful competent source policy exists.

See [`V1_1_PRODUCT_DIFFERENTIATION.md`](V1_1_PRODUCT_DIFFERENTIATION.md), [`V1_1_STAGE1_REFERENCE_ONLY_RESULT.md`](V1_1_STAGE1_REFERENCE_ONLY_RESULT.md), and [`V1_1_STAGE1_REFERENCE_ONLY_ASTRA_REVIEW.md`](V1_1_STAGE1_REFERENCE_ONLY_ASTRA_REVIEW.md).

## 2. Current technical checkpoint

The older 994,148-byte archive remains a historical checkpoint, but it is no longer the current architecture baseline. The latest unified size checkpoints are:

- promotion gate: **1,005,099 bytes** compressed;
- unified standalone package: **1,000,137 bytes** (**4,962 B** headroom);
- unified host-attached package: `target/v11-host-attached-integrated-20260912/exactscope-grounding-1.1.0-x86_64-unknown-linux-gnu.tar.gz`;
- host-attached size: **981,955 bytes** (**23,144 B** headroom);
- host-attached SHA-256: `d962b5e12c72feb59e0881647486815662d929bfba45a396ec6271ee5ea820d3`;
- normal native staticlib: **4,616,466 B**;
- parasite-feature native staticlib: **4,587,992 B**;
- raw native reduction: only **28,474 B**;
- standalone -> host-attached compressed package reduction: **18,182 B (~1.8%)**.

This is an important negative/structural result. Removing local retrieval/index/sample/demo ownership did **not** shrink the compressed product proportionally. Much of the remaining cost is packaging/linking/runtime substrate rather than the semantic retrieval logic itself. `compiler_builtins` accounts for most archive object entries, and `exactscope-grounding` is still observed in the parasite build dependency path. Therefore the next cost question is not "which Python helper can be deleted?" but **what artifact should the host-attached product actually ship, and does it need a native kernel at all?**

Future size work must report three distinct quantities rather than allowing them to blur together:

```text
distribution bytes  = what the user must download/install
runtime payload     = what ExactScope itself must carry at runtime
post-link footprint = what survives after a concrete native consumer links/prunes it
```

Changing the measurement target is not itself a size win. If a 4.6 MB archive is still distributed, its bytes remain a distribution cost even if a final consumer links only a small subset.

Important implemented research pieces already include:

- query/instruction separation and bounded overfetch;
- precision complete-span projection with host-ranked/index-free input support;
- host lexical-stat hint parity with the full-index projection path;
- host tokenizer/context-fit negotiation integrated into the same projection path;
- deterministic host completion / zero-call paths;
- typed semantic answer contracts + strict post-generation finalization;
- backend-neutral runtime adapters and capability qualification;
- lazy local-corpus compatibility so the host-attached semantic spine can run with `grounding_corpus` unavailable;
- host-attached packaging that excludes local retrieval payload while preserving the amplifier spine.

Validation must be read in layers. A broader checkpoint before the latest unified host-attached refactor had **118/118 relevant Python tests PASS** plus `tools/validate_design.py` PASS and the ExecuTorch compile/fake-runner smokes. After the latest unified refactor, the recorded focused checks are:

- adapter + projection + corpus: **75/75 PASS**;
- host-attached packaging: **7/7 PASS**;
- parasite-without-corpus unified-spine smoke: **PASS**;
- host lexical-hint projection replay: **298/298 byte parity** across NQ/Hotpot/FEVER;
- integrated ORT context-fit replay: same recorded D+I fit metrics.

The broad 118-test checkpoint and design validator have **not yet been rerun after the latest unified host-attached changes**. Do not silently treat the earlier checkpoint as proof of the newest tree.

## 3. Multi-runtime pressure-test result so far

The experimental Bridge has now been pressure-tested against three structurally different runtime surfaces:

1. **Microsoft ONNX Runtime GenAI 0.15.2**
   - real runtime executed locally;
   - a real grounded ExactScope delivery reached ORT generation;
   - malformed tiny-fixture output was rejected fail-closed;
   - deterministic `complete` bypasses ORT.

2. **PyTorch ExecuTorch current `IRunner` API**
   - adapter compiles against the current public header;
   - fake-runner executable verifies zero-call completion and exactly one generation call;
   - final prompt rendering remains host-owned;
   - a real `.pte` + tokenizer runner smoke is still pending, so do **not** claim real-model ExecuTorch compatibility yet.

3. **Google LiteRT-LM 0.17.0**
   - real Engine/Conversation execution succeeded with official test fixtures;
   - a real ExactScope ordinary-knowledge delivery completed the runtime path and failed closed on random output;
   - grounded delivery exposed real context-capacity/vocabulary limitations in the tiny official fixtures;
   - do **not** claim grounded answer-quality success from those fixtures.

The strongest architectural result is that all three can consume the same narrow semantic decision:

```text
complete(final reply, zero model calls)
OR
generate(approved semantic messages) -> host runtime -> raw output -> ExactScope strict finalizer
```

Runtime-specific tokenizer/template/generator/KV/speculation behavior stays outside ExactScope core.

A repeated cross-runtime friction is now important: **byte budgets do not prove tokenizer/model context fit**. ORT and LiteRT independently exposed this. An optional host-supplied token/context-fit seam or deterministic projection-tier selection mechanism is therefore a strong pre-freeze experiment candidate, but it is not yet a frozen public ABI.

## 4. Upstream validation / promotion track — waiting for replies

The upstream contribution track is intentionally separate from the main v1.1 research loop. Its goals are external architecture validation, useful maintainer feedback, and promotion through a genuinely useful upstream contribution.

Current public issues:

- Microsoft ONNX Runtime GenAI **#2549** — `Proposal: minimal external grounding example before generation`
- PyTorch ExecuTorch **#22761** — `RFC: tiny external-grounding attach point for extension/llm IRunner examples`
- Google LiteRT Samples **#308** — `Proposal: LiteRT-LM sample for a minimal external grounding / zero-call delivery path`

**As of 2026-09-12, all three are open and have no maintainer comments yet. We are waiting for maintainer placement/direction feedback.**

Prepared upstream state:

- fork `ot4562-glitch/onnxruntime-genai`, branch `exactscope-grounding-example`;
- fork `ot4562-glitch/executorch`, branch `exactscope-grounding-example`;
- fork `ot4562-glitch/litert-samples`, branch `exactscope-grounding-sample`;
- the ORT fork branch already contains the minimal `examples/python/external-grounding.py` candidate.

### Waiting rule

- **Do not pause v1.1 research while waiting.** Upstream feedback gates the upstream PR shape, not local amplifier research.
- Do not interpret silence as rejection or architectural feedback.
- Do not force an upstream PR merely to obtain attention while the issues are asking maintainers for placement/language/fixture guidance.
- Branch preparation and runtime validation may continue in parallel.
- When a maintainer replies, treat the reply as experimental data: distinguish repository-placement policy from actual architecture/API criticism.
- If a maintainer explicitly invites a PR or gives the requested placement, adapt the smallest possible branch and open the corresponding PR.
- A merged PR is the strongest promotional outcome, but useful maintainer feedback is already valuable input for v1.1 and later versions.
- Do not copy ExactScope retrieval/authority/projection logic into an upstream runtime repository merely to make a PR self-contained.

See [`UPSTREAM_VALIDATION_PLAN.md`](UPSTREAM_VALIDATION_PLAN.md) for the exact per-repository scope.

## 5. Amplifier material registry and first causal screen

The bounded material registry now exists in [`V1_1_AMPLIFIER_MATERIALS.md`](V1_1_AMPLIFIER_MATERIALS.md). Material letters are assigned for the current search round so later sessions do not silently rename interventions:

- **A** retrieval-query / model-instruction separation;
- **B** bounded candidate overfetch;
- **C** global snippet selection after overfetch;
- **D** precision complete-span projection;
- **E** evidence position control;
- **F** evidence-surface encoding;
- **G** typed semantic answer contract;
- **H** backend-native constrained-output surface;
- **I** host token/context-fit negotiation;
- **J** deterministic host completion;
- **K** stable prefix identity + host-native prefix/KV reuse;
- **L** host n-gram / prompt-lookup speculation;
- **M** field-aware lexical retrieval;
- **N** guarded deterministic lexical PRF/query expansion;
- **O** conservative near-duplicate diversity filter.

This registry is experimental, not a public API. Materials may be promoted, revised, quarantined, or deleted after causal evidence.

### 5.1 First real evidence-only factorial: A x B

A gold-separated, model-free diagnostic was run on the existing 150-item oracle-pooled FEVER development candidate. Only the 100 verifiable items were used for evidence recall scoring; this is **not an official FEVER score and not release qualification**.

Control deliberately reproduces the pre-A failure mode by using the long model-visible classification instruction as the retrieval query. B changes `top_k` from 4 to 12 while the projection budget remains fixed.

| Cell | Projected complete evidence | Projected any evidence |
| --- | ---: | ---: |
| no A / no B | 83% | 87% |
| A only | 88% | 95% |
| B only | 87% | 91% |
| **A + B** | **94%** | **97%** |

For complete evidence:

```text
I(A,B) = 0.94 - 0.88 - 0.87 + 0.83 = +0.02
```

The most important result is item-level, not the mean: **3 verifiable items failed under Control, A-only and B-only but succeeded under A+B**. A+B introduced **0 regressions relative to Control** on complete-evidence success. This is the first real-data phase-transition signal in the new rack search.

Artifact: `target/v11-material-ab-fever-screen-20260912.json`.

Current verdict:

- **A: promoted to validated material for the next interaction neighborhood.**
- **B: promoted to validated material for the next interaction neighborhood.**
- A and B remain subject to cross-dataset/regression checks; this result does not freeze either as release behavior.

### 5.2 Material C negative result — keep the failure, do not tune on the same gold

C v1 globally reranked every prepared complete snippet after overfetch. It produced a useful synthetic B+C phase-transition unit case, but the real FEVER diagnostic contradicted that optimistic example:

- Control `top4 + v5`: complete 88%, any 95%;
- B `top12 + v5`: complete 94%, any 97%;
- C v1 `top4 + global`: complete 88%, any 95%;
- **B + C v1**: complete **87%**, any **91%**;
- real-data phase-transition wins: **0**;
- Control -> B+C v1 complete-evidence regressions: **6**.

Regression inspection showed that C v1 displaced very strong retrieval-head evidence: five regressed items had gold at BM25 rank 1, and the sixth had gold at ranks 2 and 3.

C2 was therefore tested as a conservative correction: preserve the original top-4 head exactly and rerank only the overfetch tail. It successfully preserved the top-4 control emission/bytes on all 150 serving items, but it still failed to unlock B:

- B `top12 + v5`: complete 94%;
- B + C2: complete 92%;
- B -> B+C2 complete regressions: 2;
- B+C2 complete gains over B: 0;
- phase-transition wins: 0.

Artifacts:

- `target/v11-material-bc-fever-screen-20260912.json`;
- `target/v11-material-c-regression-analysis-20260912.json`;
- `target/v11-material-bc2-fever-screen-20260912.json`.

**C is now quarantined as a negative material. Do not create C3 by looking at the same 100 gold-scored items.** Any future revival of global/tail snippet reranking requires an independently motivated rule and fresh held-out evidence. The detached implementation remains in `tools/grounding_projection_experiments.py` for reproducibility, not as selected behavior.

### 5.3 What B taught us independently

On the current claim-only retrieval path, top-4 -> top-12 overfetch raised projected complete evidence from 88% to 94%. Top-12 retrieval itself reached 97% complete evidence, leaving only three verifiable cases where complete gold evidence was present in the retrieved pool but not fully projected. This means the immediate problem is no longer simply "retrieve more"; the next projection work must preserve strong head evidence while explaining those residual misses without gold-guided reranking.

### 5.4 B x D cross-dataset screen — strongest evidence interaction so far

Two CPU-only evidence screens were run in parallel with the projection byte/item budget held fixed. These are development diagnostics, not official benchmark scores.

**NQ 128** (`target/v11-material-bd-nq-screen-20260912.json`):

| Cell | Answer-bearing evidence | Source document projected |
| --- | ---: | ---: |
| top4 + v4 Control | 61/128 = 47.7% | 125/128 = 97.7% |
| B top12 + v4 | 66/128 = 51.6% | 125/128 = 97.7% |
| D top4 + v5 | 63/128 = 49.2% | 125/128 = 97.7% |
| **B + D top12 + v5** | **68/128 = 53.1%** | **125/128 = 97.7%** |

NQ is nearly additive in the aggregate, but one item fails under Control, B-only and D-only and succeeds under B+D. There were zero answer/source regressions from Control→B+D or B→B+D.

**HotpotQA 20** (`target/v11-material-bd-hotpot-screen-20260912.json`):

| Cell | Answer in projection | Complete supporting titles |
| --- | ---: | ---: |
| top4 + v4 Control | 50% | 45% |
| B top12 + v4 | 50% | 55% |
| D top4 + v5 | 55% | 45% |
| **B + D top12 + v5** | **65%** | **60%** |

Hotpot gives the strongest nonlinear signal so far:

```text
I(B,D) answer-bearing evidence = +10 pp
I(B,D) complete supporting titles = +5 pp
```

There are two answer-bearing phase-transition items and one complete-support phase-transition item, with zero Control/B→B+D regressions in these metrics. **A, B and D are therefore the current leading retrieval/context spine.**

### 5.5 D x F real-model screen — surface is model-dependent, not universally compact

A four-cell real llama.cpp screen fixed B=top12 and kept each model's calibrated answer contract/native constrained-output surface constant:

```text
v4 + grouped JSON         Control
v5 + grouped JSON         D
v4 + compact literal      F
v5 + compact literal      D+F
```

The F transform preserved the exact selected evidence identities within each projector arm.

- **SmolLM2 135M:** Control/D exact 5%; F/D+F exact 0%. Literal F saved prompt tokens but regressed quality.
- **Llama 3.2 1B:** Control/D exact 5%; F/D+F exact 0%. Same direction as SmolLM2.
- **Qwen3.5 0.8B:** Control 25%, D 20%, F 30%, D+F 30%; exact interaction `I(D,F)=+5 pp`, one exact phase transition, but also one Control→D+F exact loss.

Artifacts are under `target/v11-df-hotpot-*-20260912*`.

Verdict: **the first compact-literal F surface is rejected as a universal default, but F remains an open model/runtime-profile material.** Shorter prompts are not sufficient evidence of a better surface. Any future F variant must be selected without hiding negative model cells.

### 5.6 Material I — real ORT tokenizer turns byte overflow into a bounded fit decision

A detached experiment seam now exists at `adapters/bridge/context_fit.py`. It accepts at most four already-valid generation deliveries in semantic preference order, asks a host callback only whether each rendered/tokenized delivery fits, and returns the first fit. It does not import a tokenizer, rebuild evidence, truncate bytes/tokens, call a model, or expose a vendor type in core. `tools/test_bridge_context_fit.py` passes **6/6** focused tests.

The first real tokenizer screen used ONNX Runtime GenAI 0.15.2 with the existing 512-context test fixture, NQ128, top-k 12, and 32 tokens reserved for output. Artifact: `target/v11-material-i-ort-context-fit-screen-20260912.json`.

| Path | Runtime overflow/no-fit | Mean prompt tokens | Answer-bearing evidence | Source evidence |
| --- | ---: | ---: | ---: | ---: |
| current adaptive byte policy | **105/128 overflow (82.0%)** | 618.9 | 53.1% | 97.7% |
| **I: first fitting complete tier** | **0/128 no-fit** | **422.1** | 40.6% | 96.1% |

I had to fall back on exactly the 105 overflow items. Final selections were 1024-byte tier for 124 items and 512-byte tier for 4 items; no arbitrary truncation was used.

Interpretation: **I is validated as a runtime-compatibility material, not yet as a quality amplifier.** It changes “the runtime cannot admit this request” into “choose the strongest complete candidate that really fits,” but small-context pressure exposes a new quality problem: answer-bearing evidence retention inside the real token budget. The next D×I work should improve complete-span selection *within* the host's fit budget rather than pretending 2048 bytes always fit.

### 5.7 Parasite / Attach Profile — remove ownership, keep amplification

The main architectural result of the latest pass is that ExactScope does not need to own several components that were previously present in the portable path. The current research profile is documented in [`V1_1_PARASITE_ATTACH_PROFILE.md`](V1_1_PARASITE_ATTACH_PROFILE.md).

A detached `adapters/bridge/ranked_hits.py` projector accepts host-ranked candidates and no longer needs to own corpus postings/search/runtime/network/vendor code. Its preferred lexical-hint seam now borrows only host-native **document_count + normalized query-term doc_freq integers**; precomputed float weights remain a compatibility path and candidate-local rarity remains the no-statistics fallback.

The raw-stat attach projector reproduced full-index D **byte-for-byte and emitted-ID-for-emitted-ID** on all current screens while roughly halving the older float-hint payload:

- NQ128: 100% parity, **~113 bytes/query** versus ~223 B float hints;
- Hotpot20: 100% parity, **~168 bytes/query** versus ~384 B;
- FEVER150: 100% parity, **~92 bytes/query** versus ~184 B.

The same raw-stat path was replayed through the real ORT tokenizer D+I test and matched the older float-hint result exactly on 512 paired per-item fields: no-fit 0/128, 1024 tier x124, 512 tier x4, answer-bearing evidence 40.625%, source evidence 96.094%, mean prompt 422.09 tokens and mean raw hint 112.625 B/query.

The attach code is now measured at three explicit depths after 20 isolated `python3 -I` import+smoke trials each:

- **P0 projection parasite:** 4,279 B ZIP, median ~28.9 ms cold import+smoke;
- **P1 projection + strict guard:** 8,365 B, ~43.5 ms;
- **P2 full hot attach:** 12,856 B, ~60.3 ms.

A detached strict steady-state finalizer remains at `adapters/bridge/finalizer.py`. Cold prompt/cache/surface decisions are now separable into `adapters/bridge/capability_record.py`: a representative canonical record is 582 B and its validator module is about 2.4 KB compressed, with no model/runtime/network probe dependency.

`ranked_hits.py` also moved to incremental JSON byte accounting. On NQ128 this reduced host-stat projection CPU from about 1.466 -> **1.295 ms/item** for one 2048 tier and 1.862 -> **1.527 ms/item** for 2048/1024/512 preparation, with parity unchanged.

An ultra-shallow P-1 host-preprojected diagnostic is conditional rather than default: sentence-sized FEVER candidates preserved quality while projection CPU fell ~280 -> ~82 microseconds, but NQ answer-bearing evidence fell 54.7% -> 47.7%. Therefore ExactScope may skip D only when the host is actually qualified as already providing useful bounded passages.

### 5.8 Prompt/profile borrowing creates the strongest cost-down / quality-up result

Repeated grounding-policy text is not universally useful after ExactScope has already resolved authority/state and the host has a qualified native structured-output surface. Three steady-state prompt profiles were screened: full, no-policy, and compact-native.

The same model-level winners reproduced across Hotpot20 and a deterministic gold-independent NQ20 subset:

- **SmolLM2 135M -> compact-native**: cheaper and higher exact on both screens;
- **Qwen3.5 0.8B -> no-policy**: cheaper and higher exact on both screens, with no exact losses versus full;
- **Llama 3.2 1B -> full**: shorter profiles saved latency/tokens but introduced exact regressions, so full remains the safe profile.

The strongest direct bundle comparison is Qwen Hotpot20, sequential and isolated:

| Metric | Full + no cache | Parasite no-policy + host prefix cache |
| --- | ---: | ---: |
| exact | 15% | **35%** |
| mean F1 | 0.253 | **0.400** |
| prompt tokens | 750.7 | **625.7 (-16.65%)** |
| E2E latency | 3.379 s | **2.606 s (-22.87%)** |
| paired exact | baseline | **4 gains / 0 losses** |

This is the current strongest direct evidence that **less ExactScope ownership and less repeated instruction text can make the host model both cheaper and more accurate**.

Prompt pruning also interacts nonlinearly with I: under the 480-token real ORT fit budget, no-policy reduced mean prompt length 422.09 -> 318.75 tokens while raising answer-bearing evidence 40.625% -> 42.188% because larger complete evidence tiers could fit again. There was one answer-bearing regression, so this is a promising interaction rather than a zero-regression promotion.

Several attempted fixes for that one tier pathology were screened and rejected: strict nested/coverage-first tiers, carry-forward tiers, rank/hit-count/score-mass selectors and a singleton-expansion guard all introduced more losses elsewhere. **Do not tune those selectors further on the same NQ development gold.** Keep validated D generation + I largest-fit.

### 5.9 Host performance features are capability-qualified, not globally enabled

- **K prefix cache, Qwen no-policy:** output/value parity 100%, exact/F1 unchanged, E2E about **-9.98%**. Retain as a positive host-owned capability.
- **K prefix cache, Llama full:** about **-20.4%** latency but one raw/value mismatch in 20 items. Not parity-qualified yet.
- **L n-gram speculation, Qwen:** parity preserved but ~1.66% slower.
- **L n-gram speculation, Smol:** ~2.28% slower and one parity mismatch.

Therefore runtime feature availability is not an activation rule. ExactScope should remember only capabilities that pass model/runtime-specific quality/parity/cost gates.

### 5.10 Current next neighborhoods

Priority is now:

```text
Attach profile distillation
  host top-k + tiny lexical hints
  x index-free D
  x host tokenizer/I
  x model-qualified minimum prompt profile
  x parity-qualified host prefix cache

A x B x D
  retain as the validated semantic retrieval/context spine

G x H
  retain semantic contract in ExactScope, borrow native syntax enforcement from host

J zero-call
  continue separately as the strongest possible cost elimination when proof exists
```

C remains quarantined. F remains model/profile-specific rather than one universal surface. L n-gram speculation is off for the current extraction workload. J remains selected proof-based zero-call behavior and should be reported separately from the residual generation-required cohort.

### 5.11 External host-retriever pressure test — attach seam survives outside ExactScope BM25

A new pressure test replaced the ExactScope corpus search path with **SQLite FTS5**. FTS5 owned the index, ranking, top-12 retrieval and `fts5vocab` document-frequency statistics; ExactScope imported only the detached ranked-hit projector. Artifact: `target/v11-parasite-sqlite-fts5-screen-20260912.json`.

On NQ128 with equal title/body field weighting:

- host top-12 source retrieval: **99.22%**;
- final attach projected source: **97.66%**;
- answer-bearing projection: **53.91%**;
- attach projection CPU: ~**1.47 ms/item**;
- raw host lexical hint: ~**112.6 B/query**;
- empty retrievals: **0**.

A 5x title boost was negative (1 answer gain / 3 losses), so it is rejected rather than tuned on the same data. The important result is architectural: **the ranked-hit attach seam is not coupled to ExactScope's own BM25 implementation**.

The lexical-statistics wire can also be distilled further without changing projection behavior. Because both sides already know the canonical retrieval query, the host can send `document_count + query-order df vector` instead of repeating query-term strings. A detached encoding screen preserved 100% projection/emitted-ID parity while shrinking mean JSON hint bytes:

- NQ: 112.6 -> **42.0 B (-62.7%)**;
- Hotpot: 167.9 -> **46.9 B (-72.1%)**;
- FEVER: 91.6 -> **30.4 B (-66.8%)**.

This is a wire/distillation result, not a new quality material.

Host-native snippets were also tested. Direct FTS5 `snippet()` evidence reduced transfer/CPU substantially but lost answer-bearing evidence, so **host snippets are not a universal final-evidence replacement**. A two-stage `snippet64 scout -> selected full fetch -> D` recovered exact NQ evidence metrics at scout=6 while reducing NQ candidate transfer ~15.8%, but the rule failed fresh cross-checks: Hotpot transfer increased ~9.1% with one answer/support loss, and FEVER transfer increased ~50% with three complete-evidence losses. Therefore lazy fetch is **not a global attach default** and the scout count must not be tuned further on the same NQ gold. It may only return as a host/profile-qualified cost optimization for genuinely long candidate passages.

### 5.12 G x H — typed semantics unlock host-native constraints

A real-model 2x2 isolation screen now separates:

- **G:** typed ExactScope semantic answer contract (`choice`, `boolean`, `integer`);
- **H:** host-native JSON Schema constrained output;
- strict ExactScope parser/finalizer;
- **0 retries / 0 repair calls**.

The 12 cases were synthetic factual isolation cases, including distractor/injection-like examples. They are causal material evidence, **not an official benchmark or release qualification**.

| Model | Control | G only | H only | **G+H** | Interaction | G+H phase transitions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SmolLM2 135M | 0% | 0% | 16.7% | **58.3%** | **+41.7 pp** | **5** |
| Qwen 0.8B | 0% | 0% | 83.3% | **91.7%** | **+8.3 pp** | **1** |
| Llama 1B | 0% | 8.3% | 41.7% | **75.0%** | **+25.0 pp** | **4** |

H and G+H had **0 strict-format failures** on all three models. The strongest weak-model result is SmolLM2: neither semantic typing alone nor generic unconstrained generation crossed the boundary, while the **typed semantic contract combined with the host's native typed constraint produced five item-level phase transitions**.

Interpretation: this is exactly the attach-profile ownership split we want. ExactScope should own the **meaning/domain** of a valid answer; the host should own the **mechanism that constrains token generation**. Next, cross-check GxH on a real typed application workload where answer types are fixed independently of benchmark gold before promoting it as a default.

## 6. Parallel research execution policy

The development machine has 32 GB physical RAM and 12 logical CPUs. WSL2 is now configured with `memory=32GB`, `processors=12`, and `autoMemoryReclaim=dropCache`; after restart Linux reported about **30.7 GiB MemTotal**. This allows substantially more local parallel research than the previous default ~15.3 GiB WSL cap.

Operational rule:

- independent CPU-only retrieval/projection/scoring lanes should run in parallel when practical;
- independent small-model lanes may run concurrently when RAM and runtime-port identities are isolated;
- do not run multiple experiments through the same mutable model server/port/cache identity if that can contaminate latency, output, or calibration evidence;
- keep per-lane output directories and explicit candidate identities;
- reserve enough host memory that Windows remains responsive; automatic reclaim returns unused/cache memory, not active model working sets;
- do not interpret higher machine utilization as permission to weaken experiment isolation.

The default foreground is now causal search, not serial execution convenience.

## 7. Things the next research session must not accidentally do

- Do not release or tag v1.1 merely because documentation/package names say `1.1.0`.
- Do not push unstable local research as the new stable GitHub release.
- Do not shrink experiments early just to stay under the current archive gate.
- Do not add a mandatory second model, vector database, agent loop, hidden reflection loop, or semantic repair retry and call it a lightweight product win.
- Do not make ExactScope own inference scheduling, model weights, tokenizer/chat-template policy, KV objects, or speculative decoding implementation.
- Do not freeze a native multi-runtime ABI before the remaining real-runner/context-fit pressure tests justify it.
- Do not claim ExecuTorch real-model success or LiteRT grounded answer-quality success that has not been measured.
- Do not open the three upstream PRs blindly while the corresponding issues are explicitly waiting for maintainer placement guidance.
- Do not let upstream waiting stall the local v1.1 experiment program.

## 8. Active implementation order

**The completed Stage 1 `ReferenceOnly` result and post-result Astra review are now the governing checkpoint.** Do not reopen the FEVER selector proof with the sealed held-out or a revised same-cohort rule.

Continue in this order unless genuinely new pre-score evidence changes it:

1. read this status document, `PRODUCT_DIRECTION.md`, `V1_1_PRODUCT_DIFFERENTIATION.md`, `V1_1_STAGE1_REFERENCE_ONLY_RESULT.md`, and `V1_1_STAGE1_REFERENCE_ONLY_ASTRA_REVIEW.md` before choosing a v1.1 task;
2. keep product/research language explicit: **Qualification/Configuration Optimizer** is the current product category, **Qualified Execution Profile** is the qualified external artifact, and **Semantic Inference Policy Compiler** is research-only;
3. preserve the stopped FEVER artifacts and source fingerprints. Do not score the sealed 600, run F/T alone, relax the frozen 15% cost requirement, or tune a new selector against that cohort;
4. define one bounded enterprise document-QA workload using real host retrieval, authorized/versioned documents, and a question population with answerable, unanswerable and materially ambiguous cases;
5. freeze leakage-preventing document/question groups and independent development/calibration/confirmatory identities before inspecting confirmatory outcomes;
6. use development data to establish whether Base and a fixed integrated-style semantic configuration are competent enough for a meaningful product comparison. If not, stop rather than manufacture a reference;
7. obtain/freeze workload-owner requirements for correctness, evidence/citation support, abstention, unacceptable errors, latency/load and the economic meaning of review/escalation/fallback;
8. freeze scorer or blinded human-adjudication rubric, model/runtime/retrieval identities, timing/load protocol, total-economic model, uncertainty analysis and all invalid-observation rules before confirmatory scoring;
9. make **integrated-style vs Base** the primary product-value comparison. Include a better-model or simpler-host alternative when deployable so ExactScope is not shielded from rational replacement;
10. if a cheaper-policy compiler branch is still desired, preregister it separately with a small candidate catalog, `F/P/T` rules and economic threshold. If calibration returns `ReferenceOnly`/`NoQualifiedReference`, stop only that branch without rescuing it on held-out;
11. emit **Candidate Execution Policy + Qualification Attestation = Qualified Execution Profile** only after independent qualification. Every artifact must say development, diagnostic, failed or qualified explicitly;
12. after a useful competent source policy exists, consider prospective transfer on untouched host/workload combinations. Adaptive per-query routing remains later still;
13. keep the semantic center narrow: evidence sufficiency/context admission plus answer-contract lowering/finalization. Cache/speculation/adapters/native code do not become product identity;
14. native code remains optional until a Python-free consumer or measured bottleneck/integration advantage requires it. Keep footprint/economics accounting as a vector, not a single archive-size or token number;
15. cross-runtime/upstream validation remains separate. Runtime integration success is not cross-runtime policy transfer, and adapter count is not category evidence.

The immediate foreground is **freezing the enterprise document-QA competence/economic protocol and its non-scoring validator**, not new FEVER scoring, another runtime adapter, adaptive routing, or release work.
