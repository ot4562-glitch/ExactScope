# ExactScope v1.1 amplifier material registry

Status: **active experiment registry; material identities are stable for the current search round, implementations and promotion decisions are not**
Updated: **2026-09-13**

Read [`V1_1_RESEARCH_STATUS.md`](V1_1_RESEARCH_STATUS.md) first. Stable/public GitHub remains v1.0.0. This registry is for aggressive local v1.1 research and does not authorize a release, a frozen ABI, or an upstream runtime PR.

## 1. Why these materials are split this way

The amplifier search needs causal units, not feature bundles. Two mechanisms that are convenient to implement together are separate materials when one can plausibly unlock the other.

Examples:

- retrieving more candidates is **not** the same intervention as selecting the best snippets from those candidates;
- choosing a literal evidence span is **not** the same intervention as deciding where that span appears in the prompt;
- a semantic answer contract is **not** the same intervention as asking a runtime to enforce JSON Schema/GBNF/Lark;
- a byte budget is **not** a proof that the selected model/tokenizer can admit that payload;
- prefix/KV reuse changes prefill cost, while n-gram speculation changes decode cost;
- deterministic host completion is a proof path, not a stronger model prompt.

The current reference configuration already contains several of these materials. For those cases, the isolated experiment is an **ablation** against the current reference, using the existing rollback/compatibility path where possible.

For two materials `X` and `Y`, record interaction as:

```text
I(X,Y) = Score(X+Y) - Score(X) - Score(Y) + Score(Control)
```

The strongest evidence is an item-level phase transition:

```text
Control fails
X fails
Y fails
X+Y succeeds reproducibly
```

### 1.1 Product promotion criterion

The registry is no longer optimizing for quality score alone and is not optimizing for archive size alone. A material is attractive when it creates **useful amplification per total incremental cost** on the model/runtime the user already has.

For each promoted candidate, record as many of these as the experiment can measure:

- task success / exact / F1 or domain-appropriate correctness;
- item-level phase-transition wins and regressions;
- false grounding / unsupported or wrong-confident output;
- extra model-call count, including retries/repair/reflection (normally required to remain zero);
- prompt/completion token delta;
- E2E and component latency;
- incremental CPU/RAM/cold-start cost;
- compressed distribution-byte delta and, when native linking is relevant, post-link footprint;
- new runtime/dependency/integration requirements.

The product objective is **not** to spend every remaining byte. Recovered byte budget is an optimization budget and should be reinvested only when the measured amplification/safety/portability gain justifies it.

A cheap semantic intervention that repeatedly turns failures into successes across held-out tasks/runtimes is strategically more valuable than a large feature that merely saves a few tokens. Conversely, a size-only change can be promoted without a quality experiment only when behavior/parity is demonstrably unchanged.

### 1.2 Capability conditioning, not benchmark hardcoding

Materials may be selected or parameterized from observable host properties and qualification evidence, for example context capacity, evidence granularity, lexical-hint availability, constrained-output support, and cache behavior. Do **not** key product policy directly from benchmark identity or use ad-hoc model-name branches as a substitute for qualification. The desired long-term asset is transferable cross-runtime semantic optimization knowledge, not a pile of dataset-specific exceptions.

### 1.3 The registry is the bounded candidate source for Harness Distillation

The material letters are not intended to become a permanent user-facing configuration matrix. Their higher-value role is to provide **causal search dimensions** from which a small number of executable candidate policies can be defined before scoring.

The first fresh compiler transfer showed why this distinction matters: an aggregate calibration tie was not enough to justify treating two policies as quality-equivalent, and the cheaper selected policy failed the fresh reference-quality gate.

The registry previously fed the preregistered FEVER **reference-preserving cost-reduction** objective below. That study has now stopped at `ReferenceOnly`; the block is retained as historical selector semantics, not as the next execution plan:

```text
competent Base B + predeclared reference F
  x frozen calibration set
  x frozen host/cost/scorer identities
  x bounded eligible material combinations
  -> reject any candidate that loses an observed F success
  -> reject any candidate that is not strictly cheaper than F
  -> choose deterministically or return ReferenceOnly(F)
  -> fresh held-out qualification only when P exists
```

The current registry role is narrower: preserve positive/negative causal evidence and generate only small, prospectively testable development hypotheses for the enterprise document-QA program. Materials do not enter confirmatory qualification or an optimizer branch unless their exact policy definitions and fresh-data rules are frozen first.

The compiler must not rediscover arbitrary prompt strings, thresholds, benchmark-specific branches, or model-name exceptions from scored gold. A quarantined material remains unavailable until independently revived.

**Automatic prompt optimization** remains one possible search dimension alongside evidence projection, context packing, answer-contract selection, host-native constraint/cache eligibility and zero-call rules. But for the current compiler milestone, a shorter/cheaper prompt may win only when it preserves the predeclared reference's observed calibration successes and passes fresh held-out qualification.

Adaptive per-query cost allocation is deferred. Proof-based zero-call completion remains a separate semantic proof path; broader request-dependent policy selection returns only after a fixed compiled candidate demonstrates fresh reference-preserving cost reduction.

See [`V1_1_PRODUCT_DIFFERENTIATION.md`](V1_1_PRODUCT_DIFFERENTIATION.md) and [`V1_1_ASTRA_HIGH_REVIEW.md`](V1_1_ASTRA_HIGH_REVIEW.md).

## 2. Material registry

### A — Retrieval-query / model-instruction separation

**Ownership:** ExactScope/host semantic input.
**State:** **validated material for the next interaction round**; FEVER evidence-only A×B screen showed +2 pp complete-evidence interaction, three item-level phase transitions, and zero Control→A+B complete-evidence regressions.
**Control:** the exact user/model question is also the retrieval query.
**Intervention:** retrieval receives a separate bounded lexical query while the model still receives the original instruction.

**Direct hypothesis**

A retrieval-oriented query can raise useful lexical candidate probability without contaminating the model-visible question with search syntax or extra terms.

**Likely unlocks**

- B candidate overfetch, because the overfetched pool becomes less noisy;
- C global snippet selection, because more candidate snippets contain useful query terms;
- D precision projection, because its sentence anchor sees a better retrieval query.

**Risk / falsifier**

A rewritten retrieval query can drift from the actual instruction. When the two differ, deterministic host completion must not assume semantic equivalence. Current `grounding_engine.py` already disables the typed scalar shortcut in that case. A wins only if retrieval/evidence quality improves without higher false-grounding or downstream answer penalty.

**Smallest useful screen**

Run the same questions with `retrieval_query=None` versus an explicitly supplied retrieval query. Compare complete-evidence recall, any-evidence recall, false grounding, retrieved candidate identities and projected evidence bytes before involving a model.

---

### B — Candidate overfetch

**Ownership:** ExactScope retrieval.
**State:** **validated material for the next interaction round**; FEVER top-4→top-12 raised projected complete evidence 88%→94%, A×B showed positive interaction, and Hotpot B×D showed strong nonlinear gain.
**Control:** smaller fixed candidate pool.
**Intervention:** retrieve a larger bounded pool while keeping final model-visible item/byte limits unchanged.

**Direct hypothesis**

More bounded candidates can increase recall without increasing model context if later stages discard weak/redundant candidates before projection.

**Likely unlocks**

- C global snippet selection;
- O near-duplicate diversity filtering;
- D precision projection when top-ranked documents contain duplicate or non-fitting spans.

**Risk / falsifier**

If the projection simply consumes candidates in rank order, overfetch can add CPU without changing final evidence. It is not a win merely because retrieval recall rises; the final projected evidence or downstream answer must improve.

**Smallest useful screen**

Compare `top_k` 4/8/12/16 while holding final evidence bytes and `model_items` fixed. Record whether the selected final spans actually change and whether complete evidence appears more often.

---

### C — Global snippet selection after overfetch

**Ownership:** ExactScope projection.
**State:** **quarantined negative material**. C v1 caused six FEVER Control→B+C complete-evidence regressions and no real phase-transition wins; head-preserving C2 still reduced B complete evidence 94%→92% with zero gains. Do not tune C3 on the same scored FEVER items.
**Control:** current document-rank order; each hit chooses its best local anchor and qualifying rows are emitted in hit order.
**Intervention:** prepare complete candidate snippets for the bounded overfetch pool once, score those snippets globally with deterministic lexical/provenance features, then select the bounded final set.

Candidate score inputs may include only already available deterministic data in the first experiment:

- query-IDF coverage in the complete snippet;
- parent BM25 score / matched-query-term count;
- exact title query identity;
- complete-span byte cost;
- duplicate identity.

No embedding model, cross-encoder, LLM reranker, or learned threshold is part of C.

**Direct hypothesis**

B increases recall only if the extra candidates can compete for scarce model-visible slots. Global snippet selection decouples retrieval pool size from final evidence order/size.

**Likely unlocks**

- B candidate overfetch — this is expected to be one of the highest-information pair tests;
- D precision projection;
- E evidence position control.

**Risk / falsifier**

A handcrafted score can demote a correct low-lexical answer. Provenance and complete spans must remain unchanged, and all negative cells must be inspected. If B+C does not beat B and C individually, the added selection layer is probably unnecessary.

**Smallest useful screen**

Use the same retrieved pool and compare current hit-order emission with global complete-snippet selection. No model is required for the first evidence-recall/density screen.

---

### D — Precision complete-span projection

**Ownership:** ExactScope projection.
**State:** **validated/promising interaction material**. Hotpot B×D raised answer-bearing evidence from Control 50% / B 50% / D 55% to B+D 65% (`I(B,D)=+10 pp`) with two phase transitions and no Control/B regressions; NQ was mostly additive but had one phase transition and no regressions.
**Control:** an earlier grouped/context projection such as the appropriate v2/v3 compatibility path.
**Intervention:** current v5 behavior: query-aware exact body dedup, title identity preservation, exact repeated-span suppression, directional adjacent context, complete-anchor fallback and bounded tier promotion.

**Direct hypothesis**

A complete literal answer-bearing span with minimal adjacent context is easier for weak models to use than either full documents or unrelated top sentences, while retaining enough context to avoid fragmentary evidence.

**Likely unlocks**

- E position control;
- F evidence-surface encoding;
- G typed answer contract;
- I token/context-fit negotiation;
- L prompt-history n-gram speculation, because literal reusable text is preserved.

**Risk / falsifier**

Over-compression can remove disambiguating context. Fewer bytes are not automatically better. Compare exact answer/evidence completeness and downstream correctness, not byte count alone.

---

### E — Evidence position control

**Ownership:** ExactScope projection/delivery ordering.
**State:** new low-cost research material.
**Control:** current selected snippet order.
**Intervention:** deterministic order variants over the exact same selected spans, initially:

1. strongest-first;
2. strongest-last;
3. outside-in for 3+ snippets: strongest first, second strongest last, then fill inward;
4. source/current order.

No text, provenance or selected evidence may change during an E-only experiment.

**Direct hypothesis**

Models can be position-sensitive even when the same relevant information is present. The classic `Lost in the Middle` result makes order a plausible amplifier, but ExactScope contexts are much shorter, so this must be measured rather than assumed.

**Likely unlocks**

- D dense projection on weak models;
- F compact evidence surfaces;
- L n-gram speculation if literal answer continuations are placed in a reusable location.

**Risk / falsifier**

Position effects are model/task dependent. If no robust cross-model benefit appears, E should remain an experiment only rather than become another permanent policy branch.

Reference: Liu et al., *Lost in the Middle: How Language Models Use Long Contexts*, TACL 2024, <https://aclanthology.org/2024.tacl-1.9/>.

---

### F — Evidence surface encoding

**Ownership:** ExactScope semantic evidence + thin model/runtime rendering profile.
**State:** **model-dependent open material; the first compact-literal surface is rejected as a universal default**. It reduced prompt tokens but hurt SmolLM2 135M and Llama 1B exact accuracy (5%→0%); Qwen 0.8B improved on the literal surface and D×F showed +5 pp exact interaction with one phase transition, so F remains a qualified profile experiment rather than a single global format.
**Control:** current grouped JSON evidence surface.
**Intervention:** render the **same selected spans and provenance** through alternative minimal surfaces, initially limited to deterministic forms such as:

- current grouped JSON;
- compact key/value rows;
- compact labelled literal text.

F must not change retrieval, chosen spans, authority/state semantics or answer contract.

**Direct hypothesis**

Historical low-end failures often involved copying/paraphrasing the whole evidence sentence rather than extracting the short value. A surface that is easier for a 135M–1B model to parse may produce a phase transition without adding evidence or model calls.

**Likely unlocks**

- G semantic answer contracts;
- H runtime-native constrained output;
- D precision literal spans.

**Risk / falsifier**

Earlier ExactScope surface experiments were model-dependent. A single universally forced surface already failed to dominate. Therefore F should be tested as a small qualified profile set, not assumed to have one global winner.

---

### G — Typed semantic answer contract

**Ownership:** ExactScope core semantics.
**State:** **validated/promising interaction material**. A real-model 12-case typed isolation screen found strong positive G×H interaction on all three tested models: SmolLM2 135M `+41.7 pp`, Qwen 0.8B `+8.3 pp`, and Llama 1B `+25.0 pp` interaction accuracy. G alone did not solve weak-model formatting, but it made the host-native H constraint materially more semantically useful. Treat this as synthetic causal evidence, not an official task benchmark.
**Control:** generic bounded text answer.
**Intervention:** exact semantic answer domain: `choice`, `boolean`, `integer`, `number`, or tighter bounded `text`, with one canonical identity and strict validator.

**Direct hypothesis**

Reducing the legal semantic output domain can reduce ambiguity and wasted output, especially after evidence has already narrowed the factual problem.

**Likely unlocks**

- H backend-native constrained decoding;
- J deterministic host completion when the source already carries a compatible typed scalar/enum;
- F simpler evidence surfaces because output semantics are explicit.

**Risk / falsifier**

A wrong or over-tight contract can make the correct answer unreachable. G is only valid when the application can state the answer domain independently of benchmark gold.

---

### H — Backend-native constrained-output surface

**Ownership:** runtime adapter; never core vendor syntax.
**State:** **validated/promising only when capability-qualified and paired with semantics**. In the 12-case real-model isolation screen, H removed all strict-format failures on SmolLM2/Qwen/Llama. H alone reached 16.7% / 83.3% / 41.7% accuracy respectively, while G+H reached **58.3% / 91.7% / 75.0%**. The pair produced 5 / 1 / 4 item-level phase transitions where Control, G, and H all failed but G+H succeeded. Keep native syntax runtime-owned and require real-workload cross-validation before a product default.
**Control:** semantic instruction + strict ExactScope post-generation validation only.
**Intervention:** map the same G contract to the runtime's native qualified mechanism such as JSON Schema, GBNF, Lark/guidance, or equivalent.

**Direct hypothesis**

A qualified native constraint can reduce strict-format failure and completion tokens after G has defined the legal semantic answer domain.

**Likely unlocks**

- G typed contracts; the G×H pair is more important than H alone.

**Risk / falsifier**

Constrained decoding can add per-token overhead or distort the model distribution. H wins only if task correctness is preserved or improved in addition to format validity. Vendor syntax stays adapter-owned.

---

### I — Host token/context-fit negotiation

**Ownership:** optional ExactScope ↔ host preparation seam; tokenizer remains host-owned.
**State:** **validated runtime-compatibility material; strongest when combined with prompt-cost reduction**. A detached Bridge seam passes 6/6 unit tests. With a real ORT GenAI tokenizer and 512-token fixture on NQ128, byte-only adaptive projection overflowed 105/128 prompts; I produced 128/128 fitting prompts with no arbitrary truncation. With the full prompt, answer-bearing evidence fell 53.1%→40.6%. In the later attach profile, removing redundant policy text reduced mean fitted prompt length 422.09→318.75 tokens and raised answer-bearing evidence 40.625%→42.188% because larger complete D tiers fit again. Multiple alternative tier selectors/monotonic rewrites were negative; keep largest-fit rather than tuning selectors on the same NQ gold.
**Control:** byte-only evidence/context limits.
**Intervention:** the host provides a bounded token-cost/fit function or explicit capacity result for deterministic projection tiers; ExactScope chooses only among semantics-preserving candidates that fit.

The first experiment should prefer **tier selection** over arbitrary truncation:

```text
candidate tiers/spans prepared deterministically
    -> host reports fit/cost
    -> choose smallest sufficient qualified tier that fits
    -> never delete arbitrary bytes/tokens from evidence
```

**Direct hypothesis**

Avoid generation attempts that the actual tokenizer/model cannot admit, and preserve the strongest possible evidence on small-context/on-device runtimes.

**Likely unlocks**

- D precision projection;
- F evidence-surface variants;
- weak/small-context runtime compatibility.

**Risk / falsifier**

Tokenization callbacks can cost more than they save on already-large contexts. The interface must stay backend-neutral and bounded. Core must not import tokenizer libraries.

---

### J — Deterministic host completion

**Ownership:** ExactScope core proof path.
**State:** selected/high-confidence reference mechanism from unresolved-state and scalar experiments.
**Control:** send otherwise resolvable cases to the model.
**Intervention:** return a final answer/disposition only when authoritative state or typed source content proves it exactly under the answer contract.

**Direct hypothesis**

The strongest possible amplification for a provable case is removing probabilistic generation entirely: zero calls, zero tokens, zero hallucination opportunity.

**Likely unlocks / interactions**

J mostly changes the **remaining workload** rather than making a model smarter. Interaction analysis must therefore report two views:

1. whole-product score/cost with J active;
2. residual generation-required cohort where J cannot solve the item.

A future exact typed-enum/choice host path is allowed only when the source itself exposes a canonical typed value that exactly matches G. Raw-text guessing is not J.

**Risk / falsifier**

Any heuristic interpretation of free text would corrupt the proof boundary. J remains exact or does not fire.

---

### K — Stable prefix identity + host-native prefix/KV reuse

**Ownership:** ExactScope supplies identity/hint; runtime owns cache implementation.
**State:** **runtime-specific positive material with strict parity gating**. On Qwen 0.8B/no-policy Hotpot20, llama.cpp host prefix caching preserved raw/value output parity and exact/F1 while reducing E2E latency by ~9.98%. On Llama 1B/full, latency improved ~20.4% but one raw/value mismatch occurred, so that cell is not qualified. Arbitrary `cache_reuse` was unsupported by the current llama.cpp context and must not be assumed.
**Control:** no prefix/KV reuse.
**Intervention:** host maps the immutable ExactScope prefix identity to its native reusable cache mechanism.

**Direct hypothesis**

Repeated workloads with the same policy/system prefix can skip redundant prefill work without changing semantic behavior.

**Likely unlocks**

- prepared immutable sessions;
- repeated document/workflow workloads.

**Risk / falsifier**

K does not reduce decode cost and has little value when prefixes rarely repeat. Backend cache rules and security/lifetime remain host-owned. Exact output parity is mandatory where the runtime claims it.

Current vLLM documentation describes reuse when requests share the same prefix and explicitly notes that the gain is in prefill rather than generation: <https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/>.

---

### L — Host n-gram / prompt-lookup speculation

**Ownership:** runtime adapter/runtime.
**State:** **quarantined/off for the current short factual-extraction workload**. Current llama.cpp `ngram-simple` requires no second model, but Qwen/no-policy was ~1.66% slower with no quality change, while Smol/compact-native was ~2.28% slower and broke raw/value parity on one item. Keep L adapter-owned for future longer/copy-heavy workloads; do not enable it merely because the host exposes the feature.
**Control:** ordinary target-only decode.
**Intervention:** enable a host runtime's history/prompt n-gram proposer while keeping the same target model and output semantics.

**Direct hypothesis**

D/F can place short literal answer-bearing text in the committed prompt. If the answer copies that text, prompt-history lookup may propose several likely continuation tokens cheaply and the target model still verifies the committed output.

**Likely unlocks**

This relationship is intentionally reversed: D/F/E are expected to unlock **L**, not the other way around. Highest-value tests are D×L and D×F×L.

**Risk / falsifier**

No speedup is guaranteed. Measure wall-clock latency/throughput, lookup hit rate, proposed/accepted tokens, output parity and CPU/energy cost. Keep draft-model speculative decoding outside the intended product win because it adds another model.

ONNX Runtime GenAI currently documents an n-gram proposer that requires no additional model and identifies input-grounded/repetitive generation as a target workload: <https://github.com/microsoft/onnxruntime-genai/blob/main/docs/SpeculativeDecoding.md>.

---

### M — Field-aware lexical retrieval

**Ownership:** optional ExactScope corpus/index ranking variant.
**State:** new P1 material.
**Control:** current BM25 over combined `title + body` token counts.
**Intervention:** deterministic field-aware scoring, initially a tiny BM25F-like/title-weight experiment or exact title-query boost with a new explicit ranking identity.

**Direct hypothesis**

For named entities/manual sections/config keys, a matching title can be stronger evidence of target identity than the same token frequency in a long body.

**Likely unlocks**

- A focused retrieval query;
- B overfetch;
- C global snippet selection.

**Risk / falsifier**

Noisy or generic titles can dominate. Any ranking change creates a new index/ranking identity and must be evaluated separately; it must not silently mutate the stable corpus format.

---

### N — Guarded deterministic lexical PRF/query expansion

**Ownership:** detachable research module; not default product behavior.
**State:** P2 high-risk/high-upside wildcard.
**Control:** A's explicit retrieval query only.
**Intervention:** bounded classical pseudo-relevance feedback over the first-pass lexical results, with hard drift guards and no model/embedding call.

An initial safe research ceiling may restrict expansion terms by all of the following:

- appear in more than one high-ranked document or a high-ranked title;
- minimum IDF / maximum document frequency;
- small fixed term count;
- deterministic tie-breaking;
- second pass remains within existing top-k/byte limits;
- original model instruction is never rewritten.

**Direct hypothesis**

N can recover vocabulary mismatch that A alone cannot express, especially when relevant documents share a domain term absent from the user query.

**Likely unlocks**

- B overfetch;
- C snippet selection.

**Risk / falsifier**

Pseudo-relevance feedback is vulnerable to topic drift when first-pass results are wrong. N must have strong negative controls and is deleted if gains depend on benchmark-specific leakage or increase false grounding.

---

### O — Conservative near-duplicate diversity filter

**Ownership:** optional ExactScope projection module.
**State:** P2/P1 candidate; current exact dedup remains the control.
**Control:** exact body digest + exact normalized span suppression only.
**Intervention:** conservative deterministic lexical near-duplicate detection over the bounded candidate/snippet pool, for example token-shingle/Jaccard or compact SimHash-style identity with an explicitly versioned threshold.

**Direct hypothesis**

Near-mirror documents can waste final evidence slots even when byte-identical dedup does not catch them. Removing a redundant near-copy may let a second independent evidence span fit.

**Likely unlocks**

- B overfetch;
- C global snippet selection.

**Risk / falsifier**

This is much riskier than exact dedup because two similar passages may differ in the one fact that matters. O is promoted only if conservative settings improve evidence diversity without deleting answer-bearing/conflicting evidence.

## 3. Things that are infrastructure, not A–O materials

The following remain important but should not be counted as separate quality gains in the combinatorial search:

- `complete | generate` Bridge delivery shape — integration boundary;
- strict post-generation finalizer — correctness boundary;
- proof-based llama.cpp preflight/capability cache — cold-path compatibility/engineering optimization;
- Parasite / Attach deployment profile — ownership/distillation architecture, not a new quality material;
- model/runtime-specific minimum-sufficient prompt profile — cold-path capability qualification, not a per-request amplifier material;
- immutable `GroundingSession` / `PreparedAmplifier` validation boundary — execution architecture;
- exact provenance/audit identities — experiment validity requirement.

They stay enabled unless the experiment explicitly studies their cost. Turning off a safety boundary merely to inflate a score is not an amplifier result.

## 4. Priority ranking

### P0 — first causal search

| ID | Material | Why now |
| --- | --- | --- |
| A | query/instruction separation | validated A×B interaction with real FEVER phase transitions |
| B | candidate overfetch | validated on FEVER and strongly interacts with D on Hotpot |
| D | precision complete-span projection | strongest current evidence-level interaction: Hotpot B×D +10 pp answer-bearing interaction |
| F | evidence surface encoding | model-dependent; keep only as qualified surface-profile search, not one global literal format |
| G | typed semantic answer contract | proven important and cleanly separable from runtime syntax |
| H | native constrained surface | direct G interaction; format/token effects can be large |
| I | token/context-fit negotiation | real ORT tokenizer converts 105/128 overflow cases into 128/128 fitting deliveries; prompt reduction now shows a positive cost/quality interaction without changing tokenizer ownership |

### P1 — second neighborhood

| ID | Material | Why second |
| --- | --- | --- |
| E | evidence position control | cheap and plausible, but current contexts are short |
| K | prefix/KV reuse | Qwen parity-qualified at ~10% E2E win; keep runtime/model specific because Llama showed a parity mismatch |
| M | field-aware lexical retrieval | promising for entity/manual queries but requires new ranking identity |
| O | near-duplicate diversity | can unlock overfetch but has correctness threshold risk |

### P2 / guarded wildcard

| ID | Material | Why guarded |
| --- | --- | --- |
| N | lexical PRF/query expansion | real vocabulary-mismatch upside, but topic-drift risk is substantial |

### Quarantined after first screen

| ID | Material | Current treatment |
| --- | --- | --- |
| C | global/tail snippet reranking | two real-data variants were negative; retain detached code only for reproducibility and do not tune C3 on the same FEVER gold |
| L | host n-gram/prompt-lookup speculation | current Qwen/Smol short extraction screens were slower, and Smol also broke parity; keep off until a longer/copy-heavy workload independently justifies rescreening |

### Selected reference mechanism, not a broad rescreen target

| ID | Material | Treatment |
| --- | --- | --- |
| J | deterministic host completion | retain as reference; re-test only when expanding the exact proof domain or measuring total-product interactions |

## 5. First screening matrix

Do **not** start with a 2^15 factorial search. The first pass should maximize information gained per run.

### 5.1 Retrieval/evidence track — no model required for the first pass

| Cell | Intervention | Main question |
| --- | --- | --- |
| R0 | current reference retrieval/projection | control |
| R-A | A only / A ablation pair | does query separation improve complete evidence? |
| R-B | B only | does overfetch change useful candidate recall under fixed final budget? |
| R-C | C only | **completed negative**; C v1 did not improve top-4 evidence recall |
| R-B+C | B + C | **completed negative**; B+C regressed FEVER and produced no real phase transition |
| R-A+B | A + B | **completed positive**; +2 pp complete interaction and three FEVER phase transitions |
| R-A+B+C | A + B + C | **stopped** while C is quarantined; do not spend more gold on this neighborhood |
| R-D | D ablation/current | **promising**; D participates in strong Hotpot B×D interaction |
| R-C+D | C + D | **stopped** while C is quarantined |
| R-E | same spans, E order only | verify bytes/spans identical; model required only for positional effect |
| R-M | M only | does field awareness help named/entity/manual cells? |
| R-N | N only, guarded | does PRF recover vocabulary mismatch without drift? |
| R-O | O only | does conservative diversity free useful final slots? |
| R-B+O | B + O | does near-dup filtering make overfetch useful in mirror-heavy cells? |

Primary non-model metrics: complete-evidence recall, any-evidence recall, false grounding, answer-bearing-span retention, selected unique source/span count, evidence bytes, CPU time and candidate count.

### 5.2 Residual text-generation quality track

J-resolved scalar/unresolved cases should be reported in the whole-product result but **excluded from the residual text-quality denominator** so zero-call success does not hide whether the model-facing amplifier improved.

| Cell | Intervention | Main question |
| --- | --- | --- |
| Q0 | current reference model-facing path | control |
| Q-D | D ablation/current | does literal complete-span precision cause weak-model gains? |
| Q-E | E only | does order change correctness with identical evidence? |
| Q-F | F only | does surface encoding fix copy-the-whole-sentence failures? |
| Q-G | G only | does semantic type narrowing help without native grammar? |
| Q-H | H only on same semantic contract | does native enforcement improve validity without hurting correctness? |
| Q-F+G | F + G | **can a simpler evidence surface unlock a tighter answer domain?** |
| Q-G+H | G + H | **completed positive synthetic isolation**: all three real models showed positive interaction; next step is a real typed application workload with answer types fixed independently of gold |
| Q-D+F | D + F | literal span + model-readable surface |
| Q-D+F+G | D + F + G | highest-priority weak-model phase-transition candidate |
| Q-D+F+G+H | previous + H | only after G+H shows no accuracy regression |
| Q-D+I | D + token-fit tier | small-context/runtime compatibility interaction |

Suggested first model emphasis: the weakest models that historically left residual text errors, plus at least one already-strong/core model as a regression guard. Do not optimize only for the weakest cell.

### 5.3 Runtime-performance track

Quality/evidence must be held fixed before measuring these cells.

| Cell | Intervention | Main question |
| --- | --- | --- |
| P0 | target runtime ordinary decode, no prefix reuse | control |
| P-K | K only, repeated shared-prefix workload | prefill/TTFT saving with output parity? |
| P-L | L only | lookup coverage/accepted tokens enough for real speedup? |
| P-D+L | D + L | **does literal precision increase n-gram usefulness?** |
| P-D+F+L | same selected facts, compact literal surface + L | strongest prompt-lookup interaction candidate |

For L record at least wall-clock latency, decode throughput, lookup hit/miss, proposed/accepted tokens, speculative coverage and exact output parity. Analytical speed estimates alone are not sufficient.

## 6. First interaction neighborhoods to pursue

If isolated screens are non-negative, explore these neighborhoods in this order:

### Neighborhood 1 — validated retrieval/context spine

```text
A query separation
  x B overfetch
  x D precision projection
```

Current evidence: A×B is positive on FEVER; B×D is strongly nonlinear on Hotpot and has an item-level phase transition on NQ. C was tested precisely because it looked like the missing bridge between B and D, but both real-data C variants were negative and are now quarantined. Continue with A×B×D and fresh-dataset leave-one-out rather than inserting another reranker by default.

### Neighborhood 2 — weak model crosses the extraction boundary

```text
D precision literal span
  x F evidence surface
  x G semantic answer contract
  x H native constraint (only if parity-qualified)
```

Core hypothesis: D makes the fact visible, F makes the representation legible, G shrinks the semantic search space, H removes remaining syntax entropy. This is the highest-priority **quality phase-transition** neighborhood.

### Neighborhood 3 — small-context runtime compatibility

```text
D deterministic projection tiers
  x I host token/context-fit knowledge
```

Core hypothesis: byte-efficient evidence only matters if it actually fits the selected tokenizer/model. This is the first integration finding independently supported by more than one external runtime.

### Neighborhood 4 — literal evidence becomes decode acceleration

```text
D literal span
  x F compact literal surface
  x L host n-gram / prompt lookup
```

Core hypothesis: the same evidence improvement that helps factual extraction may also make host-owned no-second-model speculation cheaper/more effective. This is a particularly attractive nonlinear performance interaction because ExactScope does not implement the decoder.

### Neighborhood 5 — repeated workload prefill elimination

```text
prepared stable prefix identity
  x K runtime-native prefix/KV reuse
```

This is mostly a systems-performance neighborhood, not an accuracy amplifier. Keep it out of the main quality score.

## 7. Promotion / deletion rules

A material is promoted toward the eventual v1.1 causal minimum only when:

1. its isolated effect or interaction is reproducible under a fixed identity;
2. negative cells are inspected, not averaged away;
3. safety/false-grounding/unsupported assertions do not regress;
4. runtime/token/CPU/RAM/byte cost is recorded;
5. the gain survives at least one relevant model/runtime variation or is explicitly scoped;
6. a leave-one-out test from the best rack shows that removing it loses meaningful value;
7. the behavior can eventually be distilled into the lightweight product envelope.

Delete or quarantine a material when:

- it changes no final evidence/output after its upstream material is enabled;
- its apparent gain comes only from more model calls, retries, or hidden semantic repair;
- it wins only by leaking benchmark/gold information;
- it adds a backend-specific type to the core contract;
- it improves average score while introducing unacceptable false-grounding/wrong-confident cells;
- the same outcome is achieved by a smaller already-present material.

## 8. Immediate next implementation order

The first material screen has already changed the order. Do **not** restart from the original C-first plan.

1. Treat **A×B×D** as the current validated retrieval/context spine. Cross-check it on fresh/held-out data and use leave-one-out before adding more retrieval logic.
2. Keep **C quarantined**. Do not create C3 from the already-scored FEVER items.
3. Continue **I** as a detached Bridge/preparation seam. The first real ORT tokenizer screen removed all 105/128 byte-policy overflows but forced smaller evidence tiers; improve answer-bearing retention *within* the real host fit budget rather than reintroducing overflow or arbitrary truncation.
4. Continue **F** only as a small qualified surface-profile search. The first literal surface is negative on SmolLM2/Llama 1B and positive on Qwen 0.8B, so one universal surface is already falsified.
5. **G×H isolation is now positive** across SmolLM2 135M, Qwen 0.8B and Llama 1B. Next, cross-check it on a real typed application workload where the choice/boolean/integer answer domain is fixed by the application contract before any benchmark gold is opened; do not invent a new answer contract merely to improve scores.
6. Add **E** only as a clean order-only transform over identical selected spans; it is cheap and can test position sensitivity without changing retrieval evidence.
7. Keep **L quarantined** for the current short factual-extraction workload. Qwen and Llama paired screens showed negligible benefit and the broader Smol/Qwen evidence is negative; only rescreen on a genuinely longer/copy-heavy workload with an independent reason to expect high draft acceptance.
8. Keep **N** and **O** as guarded reserve materials until fresh evidence shows a vocabulary-mismatch or near-duplicate problem worth paying their drift risk.

The immediate scientific focus is therefore **A×B×D**, **D×I**, and model-qualified **D×F×G(×H)**. The next optimization question is not “how do we fit more bytes?” but **“within the runtime's real token budget, which complete evidence units preserve the answer-bearing information that D currently loses when I must fall back?”**
