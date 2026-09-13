# ExactScope v1.1 Stage 1 preregistration

Status: **normative pre-score research contract; no new Stage 1 model scoring is authorized until the executable preregistration and precision/power preflight match this document**

Updated: **2026-09-13**

This document supersedes earlier 120/300 or three-arm confirmation drafts. It incorporates the independent direction-reframe review in [`V1_1_DIRECTION_REFRAME_ASTRA_REVIEW.md`](V1_1_DIRECTION_REFRAME_ASTRA_REVIEW.md). It does not retroactively reinterpret any already-scored cohort.

Stage 1 is a **within-workload compiler-value falsification study**. It is not release qualification, real-retrieval validation, cross-runtime transfer evidence, a moat demonstration, or proof that ExactScope is a distinct product category.

## 1. Questions fixed before scoring

Stage 1 answers three separate questions and reports three separate verdicts:

1. **Reference-preserving selector question:** can the provisional ExactScope selector produce a fixed policy `P` that is strictly cheaper than a competent predeclared reference `F`, preserves every observed `F` calibration success, and survives independent held-out qualification?
2. **Product-gate question:** does that same frozen `P` satisfy the accepted Base-relative quality, cost, latency, and contract gates?
3. **Incremental-selector question:** does the ExactScope paired-preservation rule provide evidence beyond a conventional aggregate quality-constrained tuner `T` given the same catalog, observations, serving constraints, and final evaluation?

A pass on question 1 does not imply a pass on question 2 or 3. A conventional-tuner tie is compatible with useful configuration tuning but is not evidence of a special selector advantage.

## 2. Frozen terminology

- **Base `B`** — competent unchanged host configuration that a skilled operator could plausibly run.
- **Reference `F`** — competent predeclared intervention configuration fixed before calibration scores are observed. `F` is not an oracle, optimum, or calibration winner.
- **ExactScope candidate `P`** — policy selected on calibration by the reference-preserving selector.
- **Conventional tuner `T`** — policy selected on the same calibration matrix by the aggregate quality-constrained comparator defined below.
- **ReferenceOnly** — no strictly cheaper policy preserves every observed `F` calibration success. This is operationally valid but does not demonstrate ExactScope selector value.
- **NoQualifiedReference** — the predeclared `F` fails frozen reference admission. No deployable profile is emitted and the main compiler-value study stops.

Historical code/configuration may still use `fixed_max_policy_id`; documentation and new artifacts must interpret that field only as the predeclared reference `F`, never as a claim of optimality.

## 3. Competence must be established before calibration

`B` and `F` require two kinds of admission:

1. **design competence** — their model, generation settings, evidence access, output contract, and serving configuration are frozen from pre-existing development evidence and are configurations a skilled team could plausibly deploy rather than intentionally weak controls;
2. **task utility competence** — a task-specific absolute utility floor is frozen from evidence available **before** fresh Stage 1 calibration scoring.

The empirical checks `S[F] > 0` and `S[F] >= S[B]` remain necessary but are not sufficient to establish competence.

Before the first fresh Stage 1 model call, create a competence record that identifies the pre-existing evidence used to justify the absolute floor and the frozen `B`/`F` settings. If no defensible absolute floor can be established without looking at fresh Stage 1 outcomes, Stage 1 must be labeled **algorithm diagnostic only** and no customer/product inference may be drawn from it. The floor may not be invented or changed after fresh scores exist.

That competence review has now been performed prospectively. Pre-existing balanced Qwen/FEVER development evidence was only 32%/35.3% for the historical A/G arms and was already marked non-qualification-eligible; the first fresh 6+6 transfer was too small and its compiled candidate was rejected. Those records do not justify an absolute deployable-task competence floor for the current `B` and `F`. Therefore this Stage 1 is **frozen as algorithm-diagnostic-only**. Even if its numerical product gates happen to pass, it may not emit a deployable Qualified Execution Profile or support a customer/product qualification claim.

## 4. Frozen study environment

The controlled environment remains the existing Qwen/FEVER oracle-page-pooled research setup, but the exact historical Linux llama.cpp executable from the first 6+6 transfer is no longer present locally. Stage 1 therefore prospectively freezes the existing Windows llama.cpp b10797 runtime that already has pre-existing Qwen/FEVER development evidence. The Qwen model artifact, frozen FEVER data construction, intervention definitions, scorer, and selection objective remain fixed independently of fresh Stage 1 outcomes; the old 6+6 is development evidence only and is **not** treated as a matched-runtime control for this study.

Freeze before scoring:

- exact model artifact, quantization and digest;
- runtime build/executable, launch flags, threads and context size; Stage 1 uses `llama.cpp-0.3.0-dev-b10797-832fd6f17-windows-x86_64`, executable SHA-256 `8537923e0297804e65c5f1f0065abff4b41d4e5361191f3f3bb3d19ade36e864`, with three CPU threads;
- output contract and structured-output surface, selected exactly once by synthetic pre-score interface calibration that consumes no Stage 1 FEVER item; scored stages may not reselect or recalibrate this choice;
- tokenizer and chat-template identity to the extent exposed by the bound model/runtime surface, with any missing standalone digest explicitly recorded rather than inferred;
- evidence-source and oracle-page-pool construction rules;
- retrieval/evidence settings and gold-isolation rules;
- candidate catalog and definition-based deduplication rule;
- `B` and `F` identities;
- scorer, safety/contract rules and observation-validity rules;
- calibration and held-out sample identities and grouping rules;
- one serving-cost model and all coefficients;
- timing/load/warm-up/cache protocol;
- selector `P`, comparator `T`, tie-breaks and failure semantics;
- exact analysis implementation and error allocation.

Gold labels and annotated evidence must remain unavailable to the model runner and policy decisions.

## 5. Freshness, grouping, and sampling

Exclude prospectively:

- all 12 source items from the first fresh 6+6 transfer;
- every item used to design, debug, or choose the revised selector;
- all source IDs from declared prior freezes used for selector/intervention development;
- exact normalized duplicate claims;
- near-duplicate/shared-evidence groups according to a frozen grouping rule.

Different FEVER claim IDs alone are not sufficient evidence of independence.

### Calibration

Target **120 fresh claims**, balanced at 40 per FEVER label. Calibration balance is a deliberate search design and is not the held-out population. Freeze any calibration weighting used by the selector.

### Held-out

Target **600 fresh representatives** selected by simple random sampling without replacement from a frozen post-exclusion finite evaluation frame of size `N`.

Requirements:

- the representative rule is label-independent;
- at most one item from each declared near-duplicate/shared-evidence group enters the frame;
- calibration and held-out groups are disjoint;
- held-out is not forced to 200 items per label or otherwise label-balanced;
- the sampling seed is generated independently and committed **before inspecting the resulting held-out sample**; record the seed plus provenance so a convenient seed cannot be chosen after seeing the realized sample;
- the manifest records `N`, the frame digest, sampling-domain/version, seed/provenance, sample digest, and realized label counts for description only;
- the estimand is the frozen representative frame, not an artificially balanced FEVER population.

If the implementation uses cluster sampling, unequal weights, or another design, the simple finite-population analysis below no longer applies. That alternative design and analysis must be frozen before any score exists.

The frozen Stage 1 cohort created on 2026-09-13 has `N = 3573` held-out-frame representatives, 120 calibration items, and a 600-item SRSWOR held-out sample. The realized held-out labels are 528 `NOT ENOUGH INFO`, 38 `REFUTES`, and 34 `SUPPORTS`; this imbalance is retained because labels did not participate in held-out sampling. The grouping rule is `exact-claim-or-overlapping-evidence-page-component-v2`. The seed was derived without redraw from a single pre-inspection `secrets.randbits(64)` draw and its canonical safe-integer transform; both values and the transform are recorded in the freeze manifest.

## 6. Prospective precision/power preflight

`600` is the target, not an unconditional magic number. Before any fresh model scoring:

1. compute the exact finite-population interval behavior for the actual frame size `N` and proposed held-out sample size;
2. evaluate defensible paired-disagreement scenarios around the minimum useful effects rather than treating the old 6+6 outcomes as reliable effect estimates;
3. verify that the planned sample can in principle support the primary Base-improvement and Reference-regression gates with useful precision;
4. record the preflight code digest, assumptions, tables, and conclusion.

If 600 cannot resolve the declared minimum useful effects under defensible assumptions, replace the held-out size **before scoring** and freeze the new size. There is no optional post-score extension.

For the frozen `N = 3573`, `n = 600` design, the exact gate-resolution preflight passes under the frozen screen. The 2pp Reference-regression upper-bound gate can tolerate up to 5 observed `P`-wrong/`F`-correct cases out of 600. Under the declared 1% Base-only-loss scenario (`b = 6`), at least `g = 43` P-only gains are required for the exact finite-population lower-minus-upper bound to certify the 3pp Base-improvement gate, corresponding to an observed net paired gain of about 6.17 percentage points. This is a gate-resolution result, **not** an 80%-power claim and not an effect estimate borrowed from the old 6+6 run.

## 7. Candidate matrix and semantic metadata

Calibration executes the bounded candidate catalog already justified by material research, with **definition-based deduplication only before scoring**. Do not expand the catalog in response to observed Stage 1 outcomes.

Every candidate is also described by frozen metadata so Stage 1 observations can later contribute to prospective transfer research without changing Stage 1 selection:

```text
WorkloadDescriptor
  task_family
  authority_required
  evidence_density_class
  multi_hop_class
  output_domain
  conflict_freshness_semantics
  context_pressure_class

HostCapabilityVector
  model_runtime_identity
  exact_fit_callback
  structured_output_surface
  context_window_tokenizer_identity
  prefix_cache_support
  native_constraint_support
  retrieval_externally_owned

SemanticPolicyVector
  retrieval_instruction_split
  candidate_overfetch
  evidence_projection
  evidence_ordering
  answer_contract
  constrained_output_binding
  context_fit_requirement
  proof_completion
  stable_prefix_eligibility

ObservationOutcome
  task_success
  contract_failures
  paired_relations
  model_calls
  prompt_completion_tokens
  retrieval_work
  host_work
  ExactScope_work
  serving_cost
  latency
  qualification_result
```

For Stage 1 these descriptors are **descriptive/frozen metadata only**. They may not alter the selector unless the behavior was already part of the preregistered candidate definition.

## 8. Serving-cost model

Quality is the constraint; serving cost is the optimization objective for `P` and `T`.

Before scoring, freeze a versioned integer-valued cost model tied either to actual billable resources or to an explicitly labeled internal resource model. The cost model must:

- include retrieval overfetch/work where policy-dependent;
- include evidence projection/ExactScope host work;
- include inference work;
- include normal rejection/abstention handling that occurs before the application fallback boundary;
- avoid charging both a resource and a proxy for the same resource unless the coefficients explicitly justify that accounting;
- record all coefficients and their units;
- report raw resource counts separately from the scalar cost.

Do not infer cash savings merely from fewer tokens. For self-hosted inference, document how a reduction changes avoidable capacity cost or useful throughput. Compilation, qualification, and integration cost are excluded from the per-request serving ratio but must be reported separately for lifecycle payback.

For policy `p`, calibration total cost is:

```text
C[p] = sum_i frozen_serving_cost(p, i)
```

No informal prompt-token or latency tie-break may override this scalar cost.

## 9. ExactScope selector `P`

For calibration item `i` and policy `p`:

```text
s[p,i] in {0,1}
S[p] = sum_i s[p,i]
L[p,F] = sum_i s[F,i] * (1 - s[p,i])
C[p] = sum_i frozen_serving_cost(p,i)
```

After `B` and `F` pass reference admission, a candidate is eligible for `P` only if:

- all required observations are valid and complete;
- all mandatory safety/capability/model-call constraints pass;
- `L[p,F] == 0`;
- `C[p] < C[F]`.

Choose deterministically by:

1. lowest `C[p]`;
2. highest `S[p]`;
3. lowest canonical policy ID under frozen bytewise ordering.

Equal cost does not displace `F`. If no eligible cheaper candidate exists, return `ReferenceOnly(F)` and stop the main held-out compiler-value study.

This rule is a **provisional conservative algorithm**, not a validated statistical correction and not the full ExactScope product identity.

## 10. Conventional tuner comparator `T`

`T` uses the **same candidate catalog, calibration observations, frozen cost model, capability/safety gates, and one-call serving constraint** as `P`.

A candidate is feasible for `T` only if:

- all observations are valid and complete;
- mandatory gates pass;
- `S[p] >= S[F]`;
- `C[p] < C[F]`.

Choose deterministically by:

1. lowest `C[p]`;
2. highest `S[p]`;
3. lowest canonical policy ID under frozen bytewise ordering.

If no such policy exists, `T = F`.

`T` is a comparator only. It is never a runner-up substituted for `P` after qualification failure. A generic enumerator implementing the `P` constraints exactly must reproduce `P`; this identity is expected and is not an ExactScope novelty claim.

## 11. Held-out arms

If and only if calibration returns a distinct `CompiledCandidate(P)`, freeze both `P` and `T` before opening held-out outcomes.

Held-out executes only the unique policies among:

```text
B
F
P
T
```

Deduplicate identical policy IDs before execution. The manifest must still record each logical role.

Held-out may only evaluate the frozen arms. It may not:

- select another candidate;
- substitute `F` or `T` after `P` fails;
- relax a threshold;
- extend the sample;
- rerun a model response to choose a better answer;
- drop ordinary task failures or inappropriate abstentions.

## 12. Primary paired counts and exact bounds

For `P` versus `B` on held-out:

- `g` = `P` correct and `B` wrong;
- `b` = `P` wrong and `B` correct.

For `P` versus `F`:

- `r` = `P` wrong and `F` correct.

Report all four paired cells for both comparators, not only aggregate accuracy.

On the frozen finite representative frame, compute exact one-sided finite-population/hypergeometric bounds with familywise error controlled by Bonferroni/union bound at:

```text
alpha_each = 0.05 / 3
```

The bound implementation and endpoint conventions must be code-reviewed and frozen before scoring. Also report the conditional reference-loss rate among requests where `F` succeeds, but the primary `Upper(r)` gate below uses the full held-out request denominator as preregistered.

## 13. Three separate Stage 1 verdicts

Stage 1 must never collapse the three Astra questions into one success label.

### 13.1 Narrow selector-transfer verdict for `P`

This asks only whether the conservative selector produced a cheaper candidate that independently stayed within the declared Reference tolerance. It passes only if:

1. calibration returned a distinct `CompiledCandidate(P)` under the frozen paired-preservation rule;
2. held-out `Upper(r) <= 0.02`;
3. held-out total serving cost satisfies `C[P] < C[F]` under the same frozen cost model;
4. `P` has zero mandatory safety, identity, observation-validity, or greater-than-one-model-call violations.

This **narrow selector pass is not a deployable product pass**. In particular, a 1% cost reduction with no Base-relative benefit may satisfy this question while failing the product requirements below.

### 13.2 Full product-qualification verdict for `P`

All of the following are mandatory for a deployable Stage 1 product-gate pass:

1. **Base improvement:** `Lower(g) - Upper(b) >= 0.03`.
2. **Reference regression:** `Upper(r) <= 0.02`.
3. **Cost vs F:** total serving cost of `P` is at most `0.85 * C[F]` on held-out.
4. **Cost vs Base:** total serving cost of `P` is no greater than Base.
5. **Latency vs Base:** measured E2E p95 of `P` is no more than `1.05 *` Base under the frozen timing protocol.
6. **Contract:** zero mandatory safety, identity, observation-validity, or greater-than-one-model-call violations.

Insufficient statistical bounds are product-qualification failure, not proof of harm.

### 13.3 Incremental-selector verdict against conventional tuner `T`

Run `T` through the same descriptive held-out measurements and full product gates. Unless a separate inferential comparison is preregistered, `P` versus `T` remains **descriptive** and must not be turned into an opportunistic superiority claim.

Classify the third verdict as:

- `FAVORS_P_DESCRIPTIVELY` — full product gates pass for `P` and fail for `T`;
- `NO_SPECIAL_SELECTOR_ADVANTAGE_DEMONSTRATED` — both pass with similar practical economics or the same policy is selected;
- `FAVORS_CONVENTIONAL_TUNER_DESCRIPTIVELY` — `T` passes the full product gates while frozen `P` fails them;
- `NO_COMPILER_VALUE_DEMONSTRATED` — both frozen policies fail the relevant product gates;
- `NOT_EVALUATED_REFERENCE_ONLY` or `NOT_EVALUATED_NO_QUALIFIED_REFERENCE` — the calibration stop rule fired, so held-out was not consumed and no P-versus-T product comparison exists.

The third verdict is evidence about this workload only. It is not a general superiority test or moat claim.

Report separately:

- all three verdicts;
- B/F/P/T task accuracy and domain score;
- paired wins/losses and all paired cells for P and T against the relevant comparators;
- realized per-label outcomes;
- evidence correctness/coverage;
- rejection and abstention counts;
- calls and raw resource counts;
- prompt/completion tokens;
- retrieval, host, preparation and finalization work;
- scalar serving cost and component resources;
- latency distribution and p95;
- compilation/calibration/qualification cost;
- measured integration hours;
- lifecycle break-even volume.

If per-query savings versus Base are non-positive, there is no serving-cost payback; any quality case must be valued separately.

## 15. Timing and load protocol

Before scoring, freeze:

- hardware and OS identity;
- runtime/model process identity;
- warm-up count;
- cache state and whether host cache is enabled;
- request order/counterbalancing rule;
- concurrency/load level;
- latency start/end boundary;
- timeout and invalid-run rules.

The measured 600-query (or prospectively revised-size) p95 is a study gate, not a universal tail-latency guarantee.

## 16. Failure and publication rules

- `NoQualifiedReference` stops the main study.
- `ReferenceOnly` stops the main compiler-value held-out study; a separate reference investigation needs a different declared purpose.
- Invalid/corrupt observations follow the frozen invalid-run rule and are not silently dropped.
- Ordinary wrong answers, inappropriate abstentions, and contract failures remain failures.
- A valid failed Stage 1 result ends further same-cohort selector repair presented as confirmation.
- Any outcome-informed selector/objective/threshold modification permanently turns this held-out into development evidence for that new rule.
- Passes, failures, ReferenceOnly, invalid and inconclusive results are all publishable outcomes.

## 17. Claims authorized by outcomes

A full `P` pass authorizes only a scoped statement of the form:

> In the frozen Qwen/FEVER oracle-page-pooled study, a fixed policy selected before held-out reduced serving cost relative to the predeclared reference while meeting the preregistered Base-relative quality, reference-regression, latency, and contract requirements on the declared finite frame.

It does **not** authorize claims of:

- release qualification;
- real-retrieval product value;
- universal same-model improvement;
- cross-runtime transfer;
- a new technical category;
- a moat;
- customer savings.

A valid pass moves the foreground directly to customer-like real retrieval rather than to a larger FEVER feature program.

## 18. Evidence ladder after Stage 1

### Stage 2 — customer-like real-retrieval document QA

Use genuine retrieval over authorized, versioned documents with missing evidence, distractors, stale/conflicting sources, unanswerable requests and long contexts. Compare against a competent production-like Base, a strong fixed intervention, a matched-budget generic/DSPy-style tuning workflow, and a better-model alternative where deployable. Charge fallback, integration, qualification and refresh costs. Prefer short factual answers, extraction, or typed decisions with citations.

### Stage 3 — prospective transfer

Freeze source-derived policy/intervention knowledge before target outcomes. On untouched host/workload combinations compare prior-informed search against cold search, a strongest static recipe, and descriptor-blind pooled priors under the same final qualification gate. The initial target hypothesis is at least **30% fewer candidate executions or calibration labels** to obtain a qualified policy without materially reducing qualification yield. Final held-out qualification strength is not weakened merely because search is faster.

Until Stages 2 and 3 succeed prospectively, `Semantic Inference Policy Compiler` remains an internal architecture hypothesis and `Qualified Execution Profile` remains a proposed commercial deliverable rather than an established category or moat.
