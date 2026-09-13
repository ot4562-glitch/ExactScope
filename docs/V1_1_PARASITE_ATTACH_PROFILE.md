# ExactScope v1.1 Parasite / Attach Profile

Status: **active local research profile; not a frozen public API or v1.1 release commitment**
Updated: **2026-09-13**

This document records the low-ownership deployment findings discovered during v1.1 amplifier research. It is now an **architecture/material input**, not the umbrella product definition. Internally the historical shorthand is **Parasite Profile** because ExactScope deliberately borrows capabilities already present in the host; public architecture discussion may use **Attach Profile**.

The current product hierarchy lives in `V1_1_PRODUCT_DIFFERENTIATION.md`: **Semantic Inference Policy Compiler** is the internal architecture hypothesis, **Qualified Execution Profile** is the proposed customer deliverable, and **Reference-Preserving Cost Reduction** is only the first Stage 1 algorithm. The goal here is to remove every component the host already owns while preserving the narrow semantic policy/qualification boundary.

## 1. Design rule

```text
Do not own a component merely because ExactScope can implement it.
Borrow it when the host already has it, and keep only the semantic delta that measurably improves the result.
```

The attach profile exists to support the product thesis, not merely to minimize files. The current evidence supports **low-ownership integration as a strong architecture direction**; it does not yet establish a moat. The long-term moat hypothesis is accumulated qualification/selection knowledge, while low runtime/distribution/integration cost is the adoption advantage.

The target public semantic shape is now intentionally narrower than the implementation history:

```text
prepare(query, host_evidence, host_profile)
    -> Complete(answer)
     | Generate(contract)

finalize(contract, model_output)
    -> Accept(answer)
     | Reject(reason)
```

Internally `prepare()` may perform authority/state handling, query/instruction policy, host-ranked evidence projection, ordering, host context-fit selection, and proof-based zero-call decisions. Those substeps should not become a growing public sidecar API merely because they were once developed as detached experiments.

The host remains responsible for the machinery it already owns:

```text
host retrieval / existing RAG
    -> bounded ranked evidence + optional cheap lexical hints

ExactScope.prepare(...)
    -> Complete
    OR
    -> Generate(semantic contract + approved payload)

host tokenizer/chat template/native constraints/cache/inference
    -> raw model output when Generate was selected

ExactScope.finalize(...)
    -> Accept | Reject
```

`host_profile` should describe **observable/qualified capabilities**, not benchmark names or ad-hoc model labels. Examples include context capacity/fit support, evidence granularity, lexical-stat availability, native constrained-output support, prefix-cache support, and measured qualification digests.

ExactScope should **not** own, in this profile:

- model weights or model graph;
- tokenizer/chat-template implementation;
- inference engine or scheduler;
- KV/prefix cache implementation;
- speculative decoder;
- network transport when the embedding host already invokes the runtime;
- corpus postings/index when the host already has adequate retrieval;
- a second model, reranker, vector database, retry/reflection/repair loop, or agent loop.

The remaining open boundary question is more fundamental than "how small can the static library become?": **does the default host-attached runtime need a native kernel at all?** Native code may still be required for Python-free hosts, embedding portability, or a stronger isolation boundary, but it must earn that requirement with measurement rather than assumption.

### 1.1 Cold compiler, hot qualified profile

The attach architecture is a possible **consumer** of the v1.1 compiler/qualification process. Stage 1 is intentionally narrower than the eventual transfer hypothesis and now includes a conventional comparator so ordinary tuning is not mistaken for special compiler value.

```text
COLD / development
  freeze competent Base B + competent predeclared Reference F
  + capability / competence / cost / timing / analysis identities
  + 120 fresh calibration evals
  + bounded candidate matrix
  -> select paired-preserving ExactScope candidate P
     OR ReferenceOnly(F) / NoQualifiedReference
  -> independently select conventional aggregate tuner T

HELD-OUT QUALIFICATION
  if and only if P exists:
  freeze P + T before outcomes
  evaluate unique B + F + P + T arms on finite-frame SRS held-out
  -> qualify P or reject P
  -> no reselection / T-or-F rescue / sample extension

HOT / production hypothesis
  load Candidate Execution Policy + matching Qualification Attestation
  -> Qualified Execution Profile
  -> prepare(...)
  -> Complete | Generate | Reject/Unavailable
  -> host inference only when required
  -> finalize(...)
```

The selected Candidate Execution Policy is immutable before held-out. Qualification is a **separate immutable attestation referencing its exact digest**, not a mutable `qualified` bit added to the same object. Request-specific authorized evidence, exact-fit confirmation and proof belong in a separate request receipt.

The hot path must not rerun calibration or policy search. The historical implementation names `Amplifier Profile` and `fixed_max` remain compatibility terms only; the latter means the **predeclared competent Reference `F`**, not a quality optimum.

`ReferenceOnly(F)` and `NoQualifiedReference` are stop outcomes, not compiler-selection successes. A valid Stage 1 pass still establishes only a controlled within-workload result; it must move next to customer-like real retrieval before product value is claimed.

Broader **adaptive per-query amplification remains deferred**. Proof-based deterministic completion is allowed only when a registered verifier proves the current request from authorized evidence; learned/request-dependent policy routing waits for fixed-policy and later transfer evidence.

See [`V1_1_PRODUCT_DIFFERENTIATION.md`](V1_1_PRODUCT_DIFFERENTIATION.md), [`V1_1_STAGE1_PREREGISTRATION.md`](V1_1_STAGE1_PREREGISTRATION.md), and [`V1_1_DIRECTION_REFRAME_ASTRA_REVIEW.md`](V1_1_DIRECTION_REFRAME_ASTRA_REVIEW.md) for the current product-level definition.

## 2. Deployment depth

The attach profile is better represented as increasing levels of semantic ownership rather than one mandatory bundle.

| Level | ExactScope keeps | Host supplies | Actual ZIP | Median isolated import+smoke |
| --- | --- | --- | ---: | ---: |
| P0 projection parasite | ranked-hit evidence shaping only | retrieval + tokenizer + runtime + validation integration | **4,175 B** | **28.6 ms** |
| P1 guard parasite | P0 + typed answer validation/finalizer | retrieval + tokenizer + runtime | **8,261 B** | **43.2 ms** |
| P2 hot attach | ranked-hit shaping + token-fit seam + delivery + typed finalizer | retrieval + tokenizer/template + model/runtime/cache | **12,752 B** | **60.6 ms** |
| Portable fallback | search/index/runtime orchestration + adapters | only model/runtime endpoint or local model | ~41.3 KB component reference | not comparable |

Current detached depth-packaging evidence remains useful for understanding the pure Python semantic surface:

`target/v11-parasite-depth-packages-20260912.json`

- P0 SHA-256: `e8b74f417045ccb8ac42d475b08f7a0f1cca5b53b6fa16dfeb923b62ed7e2812`;
- P1 SHA-256: `3459310276788a0681f1ca7278da9514511c6f65129fa90c06e55e1470186427`;
- P2 SHA-256: `42d385b974f97d7c80ccd012c08760c1f2722348337803f297f2ddb9352b5e41`;
- 20 isolated `python3 -I` import+smoke trials per depth: **PASS**.

These small ZIPs are **not** the current full product-size measurement. After the later unified-spine and host-attached packaging work, the comparable distribution checkpoints are:

- unified standalone tar.gz: **1,000,137 B**;
- unified host-attached tar.gz: **981,955 B**;
- promotion gate: **1,005,099 B**;
- host-attached headroom: **23,144 B**;
- standalone -> host-attached saving: only **18,182 B (~1.8%)**;
- normal native staticlib: **4,616,466 B**;
- parasite-feature staticlib: **4,587,992 B**.

Therefore the P0/P1/P2 Python depth measurements prove that the semantic hot path itself can be very small, while the full distribution result proves that **shipping/linking substrate dominates the present package boundary**. Do not confuse either measurement with the other.

The older `target/v11-parasite-kernel-20260912.zip` remains a historical P2 checkpoint. All of these packages are research artifacts, not release binaries.

## 3. Removing ExactScope-owned retrieval/index without losing D

The key attach experiment asks whether ExactScope must own the full corpus index merely to reproduce precision-context-v5 sentence-anchor behavior.

New detached module:

`adapters/bridge/ranked_hits.py`

It consumes only a bounded ranked candidate list and has no dependency on:

- `grounding_corpus`;
- `grounding_runtime`;
- HTTP libraries;
- ORT/llama.cpp/LiteRT;
- a persistent corpus index.

### 3.1 Candidate-local fallback

When the host supplies only ranked hits, candidate-local query-term rarity is enough to preserve aggregate 2048-byte evidence quality surprisingly well:

- FEVER complete/any evidence matched the full-index projector aggregate;
- Hotpot answer/support aggregate matched;
- NQ aggregate answer/source matched closely, but item-level swaps remained.

This is useful as a fallback but is not exact parity.

### 3.2 Host lexical hint path

A host lexical retriever already knows the query-term corpus statistics ExactScope needs. The preferred attach seam now borrows the host's **native integer statistics** rather than asking the host to implement an ExactScope-specific floating-point weighting formula:

```text
document_count
+ normalized query term -> doc_freq
```

ExactScope derives its tiny rarity weights locally. The older precomputed `term_weights` path remains a research/compatibility input, and candidate-local rarity remains the no-statistics fallback.

Current raw-stat parity artifact:

`target/v11-attach-host-stats-parity-20260912.json`

| Development corpus | Full-D emitted-ID parity | Full-D projection-byte parity | Mean raw-stat hint | Versus float-weight hint |
| --- | ---: | ---: | ---: | ---: |
| NQ128 | **100%** | **100%** | **~113 B / 8.5 terms** | **-49.5%** |
| Hotpot20 | **100%** | **100%** | **~168 B / 14.5 terms** | **-56.2%** |
| FEVER150 | **100%** | **100%** | **~92 B / 7.1 terms** | **-50.3%** |

The earlier float-weight artifact `target/v11-attach-host-hint-parity-20260912.json` also achieved 100% parity, but its mean hints were ~223 B, ~384 B and ~184 B respectively. Raw document frequencies therefore preserve the same measured D parity while roughly halving the hint payload and reducing host-side coupling.

This seam maps naturally onto in-process lexical engines: current Tantivy exposes `Searcher.num_docs()` and `Searcher.doc_freq()`, and current Lucene exposes `IndexReader.numDocs()` and `docFreq(Term)`. Remote/search-service integrations should keep the hint optional: Elasticsearch can return term/document statistics, but its documentation warns that term statistics may have serious performance cost and can be shard-local rather than globally exact.

**Current architectural conclusion:** roughly one hundred bytes of native query-term corpus statistics can replace ExactScope ownership of the full retrieval index for this projection function when the host exposes them cheaply. Never add a remote statistics round trip merely to satisfy ExactScope; fall back to ranked hits alone instead.

### 3.3 P-1 preprojected-host mode — only when the host already did the passage work

An even shallower diagnostic removed sentence splitting, query tokenization, IDF and anchor selection entirely. ExactScope simply packed host-ranked passage text in order, without arbitrary truncation. Artifact: `target/v11-preprojected-host-screen-20260912.json`.

- FEVER's already sentence-sized host candidates preserved complete/any evidence exactly (94% / 97%) while projection CPU fell from ~280 µs to ~82 µs.
- Hotpot answer-bearing evidence rose 70% -> 75%, but complete supporting-title evidence fell 65% -> 55%; there were 2 answer gains and 1 loss.
- NQ answer-bearing evidence fell 54.7% -> 47.7% and source evidence 97.7% -> 96.1%, with 10 gains but 19 losses. The shallow packer skipped 1,398 oversized candidate passages and emitted only ~1.02 passages/item on average.
- Projection CPU was much lower (~1.49 ms -> ~0.20 ms on NQ), proving the cost opportunity but not the generic quality requirement.

**Verdict:** P-1 is a capability-qualified mode for hosts whose retriever already returns sufficiently bounded, useful passages/snippets. It is not a universal replacement for D. ExactScope may skip projection only when the host has actually performed equivalent passage shaping; it must not infer that from the mere existence of a retrieval API.

### 3.4 External retriever pressure test — SQLite FTS5

The attach seam has now been exercised with a retriever that does **not** use ExactScope's `grounding_corpus.search()`. SQLite FTS5 owned indexing, ranking, top-k selection and document-frequency statistics; ExactScope received only ranked hits plus bounded lexical statistics.

Artifact: `target/v11-parasite-sqlite-fts5-screen-20260912.json`.

NQ128 with equal title/body weighting produced:

- top-12 source retrieval **99.22%**;
- final projected source **97.66%**;
- answer-bearing projection **53.91%**;
- attach projection ~**1.47 ms/item**;
- mean lexical hint ~**112.6 B/query**.

A 5x title boost was worse (1 answer gain / 3 losses) and is rejected. The useful conclusion is not that FTS5 is a preferred product retriever; it is that the **attach contract survives a genuinely different host lexical engine**.

The host-stat wire can be thinner still. If both sides derive the same canonical query-term order, the host can send only `document_count + df vector`. A detached encoding screen preserved **100% projection/emitted-ID parity** while reducing mean JSON hint size to ~42 B on NQ, ~47 B on Hotpot and ~30 B on FEVER. This is a wire-format/distillation option, not a new semantic material.

### 3.5 Host snippets and lazy full fetch — capability-qualified only

FTS5 `snippet()` was intentionally tested as an even more parasitic source of pre-shaped passages. Direct snippet64/snippet32 use reduced host->ExactScope candidate bytes and projection CPU, but lost too much answer-bearing evidence. Therefore host snippets are **not** a universal final-evidence substitute.

A two-stage NQ experiment used snippet64 only as a cheap scout, then fetched full text for the six selected candidate IDs and reran D. On NQ128 this preserved answer/source evidence exactly while reducing candidate transfer ~15.8%. The same fixed rule was then cross-checked without retuning:

- Hotpot: transfer **increased ~9.1%** and one answer/support item regressed;
- FEVER: transfer **increased ~50%** and three complete-evidence items regressed.

**Decision:** do not promote lazy fetch globally and do not tune the scout count further on the same NQ gold. It may be useful only when host candidate passages are genuinely long and a cost-only/capability qualification proves that the two-stage transfer is smaller without evidence loss.

## 4. Host token fit remains borrowed

The attach profile keeps the detached host-fit seam from Material I:

`adapters/bridge/context_fit.py`

The host owns rendering/tokenization and reports whether already-complete semantic candidates fit. ExactScope never truncates arbitrary tokens.

With host lexical hints, the index-free attach path exactly reproduced the earlier full-index D+I NQ128 result under the real ORT tokenizer fixture:

- no-fit: **0/128**;
- selected tiers: 1024 x124, 512 x4;
- source evidence: **96.09%**;
- answer-bearing evidence: **40.625%**;
- mean prompt: **422.09 tokens**.

The raw `document_count + doc_freq` path has now been replayed through the same real ORT tokenizer fit test. It reproduced the float-weight run exactly on all 128 items: selected tier, selected prompt-token count, source-evidence flag and answer-bearing flag produced **0 mismatches across 512 paired field comparisons**. The aggregate result remains 1024 x124 / 512 x4, no-fit 0, answer-bearing 40.625%, source 96.094% and mean prompt 422.09 tokens, while the mean hint shrinks from ~223 B to **112.625 B/query**.

Artifacts:

- `target/v11-attach-hint-fit-screen-20260912.json` — real ORT fit with float-weight hints;
- `target/v11-attach-rawstats-fit-screen-20260912.json` — real ORT fit with raw document-frequency hints;
- `target/v11-attach-host-stats-parity-20260912.json` — raw-stat full-D parity and payload-size result.

**Verdict:** raw host document statistics are now the preferred attach hint when cheaply available. They are measured through both fixed-D parity and real tokenizer-fit selection; the float-weight path is compatibility/research fallback rather than the preferred contract.

## 5. Prompt text is also a borrowable/qualifiable cost

The original full grounding policy repeats semantic rules that the attach path has often already resolved before generation. With a qualified native output surface and approved semantic evidence, the model may need less repeated instruction text.

Three steady-state prompt profiles were screened while holding evidence, model, answer contract and native JSON-schema surface fixed:

1. `full` — current contract prompt + full grounding policy;
2. `no-policy` — existing contract prompt only;
3. `compact-native` — short extraction/data-only instruction relying on the already-qualified native output surface.

### 5.1 Real Hotpot20 model results

**SmolLM2 135M**

- full: exact 0%, ~784 prompt tokens, ~2.11 s;
- compact-native: **exact 10%**, ~619 prompt tokens, ~1.69 s;
- compact-native gave **2 gains / 0 losses** versus full.

**Qwen3.5 0.8B**

- full: exact 15%, F1 0.253, ~751 tokens, ~4.57 s;
- no-policy: **exact 35%, F1 0.400**, ~626 tokens, ~3.80 s;
- no-policy gave **4 gains / 0 losses** versus full.

**Llama 3.2 1B**

- full: exact 5%, F1 0.108;
- no-policy / compact-native reduced prompt cost and latency but both lost the one exact success;
- full remains the qualified quality profile in this screen.

Therefore there is **no universal shortest prompt**. The useful capability is model/runtime-specific *minimum sufficient prompting*, selected on a cold path and reused on the hot path.

### 5.2 Cross-task NQ20 validation

The prompt profiles were then re-screened on a deterministic, gold-independent NQ20 subset selected by SHA-256 of `eval_id` before gold was opened.

**SmolLM2 135M**

- full: exact 0%, ~813 prompt tokens, ~2.15 s;
- compact-native: **exact 5%**, ~648 prompt tokens, ~1.77 s;
- compact-native gave **1 gain / 0 losses**.

**Qwen3.5 0.8B**

- full: exact 25%, F1 0.400, ~778 tokens, ~4.72 s;
- no-policy: **exact 30%, F1 0.418**, ~653 tokens, ~4.01 s;
- no-policy gave **1 gain / 0 losses**.

**Llama 3.2 1B**

- full: exact 20%, F1 0.246, ~726 tokens, ~6.16 s;
- compact-native: exact 20%, F1 0.268, ~596 tokens, ~5.06 s, but **1 gain / 1 loss**;
- no-policy: exact 15% with one loss;
- full therefore remains the no-exact-regression profile for this model.

The same model-level winners therefore transfer across Hotpot20 and NQ20:

- Smol -> compact-native;
- Qwen -> no-policy;
- Llama -> full.

This materially strengthens the cold-path prompt-profile concept. Smol remains less strongly qualified because its dense synthetic probe could not semantically distinguish the profiles, even though both real-task screens favor compact-native.

### 5.3 Direct Qwen parasite-bundle comparison

A sequential isolated two-arm screen compared the original steady-state shape directly against the current Qwen parasite bundle on Hotpot20.

Baseline:

```text
full policy
+ no prompt cache
```

Parasite bundle:

```text
host-ranked candidates
+ host lexical hints
+ index-free D
+ no-policy prompt profile
+ qualified native JSON schema
+ host prefix cache
+ strict ExactScope finalization
```

Artifact:

`target/v11-parasite-bundle-qwen-20260912-r1/summary.json`

| Metric | Baseline | Parasite bundle | Delta |
| --- | ---: | ---: | ---: |
| exact | 15% | **35%** | **+20 pp** |
| mean F1 | 0.253 | **0.400** | +0.147 |
| prompt tokens | 750.7 | **625.7** | **-16.65%** |
| E2E latency | 3.379 s | **2.606 s** | **-22.87%** |
| format failures | 0 | 0 | unchanged |

Paired exact changes: **4 gains / 0 losses**.

This is the strongest direct attach-profile result so far: less ExactScope-owned infrastructure and less repeated prompt text produced **higher task quality and lower token/latency cost in the same isolated comparison**.

## 6. Prompt pruning x I creates a real cost-down / quality-up interaction

The strongest current nonlinear result came from combining prompt reduction with the real tokenizer-fit constraint.

Artifact:

`target/v11-parasite-fit-prompt-interaction-20260912.json`

NQ128, real ORT tokenizer, max input 480 tokens, host-hint attach D:

| Profile | Answer-bearing evidence | Source evidence | Mean prompt tokens | Selected 2048-byte tiers |
| --- | ---: | ---: | ---: | ---: |
| full | 40.625% | 96.094% | 422.09 | 0 |
| **no-policy** | **42.188%** | **96.875%** | **318.75** | 12 |
| compact-native | **42.188%** | **96.875%** | 319.48 | 17 |

The shorter prompt does not merely save tokens. It frees real tokenizer context so larger complete evidence tiers fit again.

Relative to full, no-policy produced:

- roughly **24.5% fewer prompt tokens**;
- 3 answer-bearing gains;
- 1 answer-bearing loss;
- 1 source-evidence gain;
- 0 source-evidence losses.

This is the current clearest example of the target v1.1 behavior:

> remove redundant ownership/instruction cost, then spend the recovered budget on higher-value evidence.

The one loss exposed a non-monotonic tier pathology. Multiple attempted tier rewrites/selectors were screened and rejected rather than tuning against gold.

## 7. Rejected tier fixes

The following were tested after observing that a larger fitting tier could sometimes contain worse answer evidence than a smaller tier:

- coverage-first anchors;
- strict prefix/nested tiers;
- carry-forward monotonic tiers;
- rank-coverage fit selector;
- hit-count selector;
- score-mass selector;
- singleton-expansion guard.

Results were mixed or negative. They repaired the motivating item but created more losses elsewhere. Notably, the carry-forward NQ 1024 screen produced 1 answer gain but 9 losses. The rank-coverage and singleton guard each produced 1 gain but 4 losses on NQ.

**Decision:** keep the validated D tier generator and I largest-fit rule. Record the one observed prompt-pruning regression instead of adding a fragile selector.

## 8. Host cache/speculation qualification

Host-owned performance features are useful only when they pass parity and wall-clock gates.

### 8.1 K — prefix cache

Qwen 0.8B, no-policy Hotpot20:

- no cache: ~2.847 s;
- host prefix cache: **~2.563 s (-9.98%)**;
- exact/F1 unchanged;
- raw output/value **100% parity**.

This is a positive K result. ExactScope needs only stable prefix identity/hints; cache implementation remains host-owned.

Llama 1B, full prompt:

- no cache: ~4.707 s;
- host prefix cache: ~3.749 s (**-20.4%**);
- average exact/F1 unchanged;
- but **1/20 raw/value parity mismatch** occurred.

Therefore Llama prefix caching is not yet parity-qualified despite the larger speedup.

Current llama.cpp also reported `cache_reuse` unsupported in this context, so arbitrary chunk reuse must not be assumed.

### 8.2 L — host n-gram speculation

Current CPU extraction workload does **not** benefit from llama.cpp `ngram-simple` speculation.

Qwen no-policy:

- output parity 100%;
- latency **+1.66% slower**.

Smol compact-native:

- latency **+2.28% slower**;
- raw/value parity broke on 1 item.

**Decision:** L is off/quarantined for the current short factual-extraction workload. Runtime support alone is not an activation criterion.

## 9. Cold-path prompt profile negotiation

A four-case short synthetic probe did not reliably predict the best steady-state prompt profile.

A later six-case dense synthetic probe with long distractor evidence, multilingual content and injection-like text matched the observed Hotpot winner for all three tested models:

- Smol -> compact-native;
- Qwen -> no-policy;
- Llama -> full.

However the Smol dense probe scored 0/6 under every profile, so its selection came from the cheaper tie-break rather than semantic proof. Smol prompt-profile negotiation remains research-grade rather than release-qualified.

The correct architecture remains:

```text
cold path:
  qualify contract/surface
  qualify minimum sufficient prompt profile
  qualify host cache/speculation capabilities by parity
  bind those decisions to the model/runtime identity

hot path:
  load one prequalified capability record
  execute only the tiny qualified profile
  perform zero calibration/probe model calls
```

### 9.1 Detached capability record

The cold-path result is now represented by detached research module `adapters/bridge/capability_record.py`. It records only already-qualified decisions:

- host model/runtime profile SHA-256 and whether that identity is session- or persistent-scope;
- semantic answer-contract id;
- qualified native output-surface id;
- selected prompt profile (`full`, `no-policy`, or `compact-native`);
- prompt qualification evidence digest;
- host prefix-cache mode only when an exact-parity evidence digest exists;
- host speculation mode only when an exact-parity evidence digest exists.

A stale host identity fails closed. Session-scoped identities cannot be reused as persistent records. Cache/speculation cannot be enabled merely because the runtime exposes the feature; a parity qualification digest is mandatory.

Measured research footprint:

- one Qwen-like canonical record: **582 bytes**;
- record validator module: **~2.4 KB compressed**;
- focused capability-record tests: **7/7 PASS**;
- model/runtime/network/probe dependencies in the record module: **0**.

The capability record is intentionally a **cold-sidecar format**, not part of P0/P1 hot projection cost and not a frozen core ABI.

## 10. Current attach-profile verdict

Promising/retain:

- the **single semantic spine** concept: `prepare(...) -> Complete|Generate` followed by `finalize(...) -> Accept|Reject`;
- host-ranked candidate input with optional cheap lexical hints;
- index-free projection when the host has adequate retrieval;
- host tokenizer/context-fit borrowing rather than owning a tokenizer;
- proof-based deterministic zero-call completion;
- typed ExactScope answer semantics paired with capability-qualified host-native constrained output;
- strict fail-closed finalization;
- host prefix/cache reuse only when parity-qualified;
- model/runtime prompt minimization only when independently qualified;
- capability/profile data keyed by observable host properties and evidence, not benchmark names.

Do not promote:

- a universal compact prompt;
- model-name or benchmark-name hardcoded policy branches;
- candidate-local rarity as exact-parity replacement when cheap host hints are available;
- monotonic/carry-forward tier rewrites;
- rank/hit-count/score-mass fit selectors;
- n-gram speculation for current extraction workload;
- host-native snippet text as a universal final-evidence replacement;
- lazy snippet-scout/full-fetch as a universal default;
- runtime cache features that fail exact parity;
- a native runtime merely because the current package already contains one.

The current product-boundary hypothesis is:

> **If the semantic spine is fast, deterministic, and small enough without native code, native becomes a compatibility backend for Python-free hosts rather than the default definition of ExactScope.**

That hypothesis is not yet proven. The project must measure it before committing to either a Python-first or tiny-native default distribution.

## 11. Immediate next research

**Execution checkpoint updated 2026-09-13.** Harness Distillation has an executable compile/qualify/verify path, one fresh rejected transfer, and one larger preregistered FEVER Stage 1 that stopped at **`ReferenceOnly`** after 1,200 calibration observations. The sealed 600-item held-out was not scored. The next product step is therefore not another attachment micro-optimization or FEVER selector repair; it is a competence-gated bounded enterprise document-QA proof using real host retrieval.

Priority order:

1. **Freeze the enterprise DocQA product protocol:** authorized/versioned corpus, real retriever/index identities, question population, leakage grouping, development/confirmatory partitions, workload-owner competence gates, Base/Integrated configurations, scorer/adjudication, timing/load, total economics, sample/uncertainty plan, and invalid/stopping rules before confirmatory scoring.
2. **Primary product comparison = Integrated vs Base:** establish both as development-eligible before confirmatory scoring; emit no Qualified Execution Profile from calibration leadership alone.
3. **Optional cheaper-policy branch only if prospectively justified:** freeze a small `F/P/T` catalog and economic objective separately; `ReferenceOnly`/`NoQualifiedReference` stops that branch. Do not reuse the sealed FEVER 600 or lower the old 15% threshold to rescue it.
4. **Native-free E2E:** only where it directly supports the enterprise proof, run `prepare -> Complete|Generate|Reject/Unavailable -> finalize` with native loading unavailable and measure determinism, steady-state latency, cold import, RAM, runtime payload and integration steps.
5. **Minimal native consumer only if needed:** for a Python-free/native host requirement or measured bottleneck, link the smallest real consumer and measure the actual incremental ExactScope contribution. Native is no longer assumed to be the default v1.1 product form.
6. **Shipping-shape decision:** only after native necessity and customer value are demonstrated, compare static archive, shared library, object bundle and `no_std`/alternative-kernel shapes. Do not optimize archive object count in isolation.
7. **Degraded-host retrieval stress:** use development data to perturb host top-k quality and compare answer/evidence degradation, false grounding and fail-closed behavior before freezing a customer-facing retrieval contract.
8. Continue **G×H real-workload** and external-retriever pressure tests only as bounded causal/portability evidence that informs the enterprise study; do not widen a policy matrix merely to recover from failed FEVER results.
9. Preserve all negative experiments in `target/`; do not retune already-scored selectors, snippet widths, lazy-fetch counts, thresholds or other failed heuristics against the same scored data.

For all future size work, report at least:

```text
distribution bytes
runtime payload bytes
post-link native footprint (when applicable)
```

For all future product work, report whether the same model/runtime achieved better task success and what extra calls/tokens/latency/bytes/dependencies were required. **That combined amplification/cost result, not raw package size, is the product metric.**
