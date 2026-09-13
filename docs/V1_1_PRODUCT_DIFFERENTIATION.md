# ExactScope v1.1 product differentiation

Status: **active narrowed product/architecture hypothesis; unreleased; FEVER Stage 1 stopped at `ReferenceOnly`; category and commercial value remain unproved**

Updated: **2026-09-13**

Read [`PRODUCT_DIRECTION.md`](PRODUCT_DIRECTION.md), [`V1_1_RESEARCH_STATUS.md`](V1_1_RESEARCH_STATUS.md), the immutable Stage 1 result [`V1_1_STAGE1_REFERENCE_ONLY_RESULT.md`](V1_1_STAGE1_REFERENCE_ONLY_RESULT.md), and the independent post-result [`V1_1_STAGE1_REFERENCE_ONLY_ASTRA_REVIEW.md`](V1_1_STAGE1_REFERENCE_ONLY_ASTRA_REVIEW.md) before changing the v1.1 product or experiment boundary. [`V1_1_STAGE1_PREREGISTRATION.md`](V1_1_STAGE1_PREREGISTRATION.md) is retained as the frozen pre-score contract for the stopped FEVER study.

## 1. The three-layer direction

The current direction is intentionally split into three layers rather than asking one phrase to carry architecture, product, and experiment semantics.

### Internal technical hypothesis — Semantic Inference Policy Compiler

ExactScope may become a **Semantic Inference Policy Compiler**: a restricted compiler that combines workload semantics, host capabilities, bounded intervention definitions, calibration evidence, and qualification constraints into a small immutable decision policy for an existing AI stack.

This is an **internal architecture hypothesis**, not an established technical category. Existing LM-program optimizers and RAG frameworks can express many of the same decisions. The compiler label is earned only if ExactScope defines stable source semantics, rejects invalid lowerings, binds host obligations explicitly, produces a reproducible artifact, and reduces integration/search/qualification effort in prospective comparisons.

### Current product category — Qualification/Configuration Optimizer

The demonstrated v1.1 shape is a **qualification/configuration optimizer with semantic enforcement and immutable qualification records**. It evaluates a bounded semantic configuration family around an existing stack, can stop without selecting a deployable candidate, and separates development/calibration evidence from independent qualification.

The proposed commercial deliverable remains a **Qualified Execution Profile** for an existing document-answering service: a candidate execution policy plus an independent qualification attestation, emitted only when prospectively declared competence and total-economics requirements pass on fresh data. This is still a hypothesis because useful customer value, low integration burden, recurring economics, willingness to pay, and refresh value have not been demonstrated.

### Research algorithm — Reference-Preserving Cost Reduction

The FEVER Stage 1 **reference-preserving cost reduction** algorithm returned `ReferenceOnly` after 120 fresh calibration claims, and the conventional aggregate comparator also returned the Reference. It remains a valid research algorithm and explicit abstention rule, but the intended useful cheaper operating point was not demonstrated. Do not use it as the v1.1 product identity.

The recommended hierarchy is therefore:

```text
Qualification / Configuration Optimizer  current product category
        |
        +--> Qualified Execution Profile             customer-facing qualified artifact
        |
        +--> Reference-Preserving Cost Reduction     stopped FEVER research algorithm
        |
        `--> Semantic Inference Policy Compiler      longer-term research hypothesis
```

## 2. What remains research shorthand

The research thesis remains:

> **Fine-tune the inference path, not the model.**

The shorthand remains:

> **Same model. Same runtime. Better answer.**

Neither is a current universal product claim. The first fresh compiler-transfer experiment rejected its selected candidate. The strongest demonstrated result is therefore **correct fail-closed rejection of an unsuccessful transfer**, not successful distillation, cross-runtime value, or customer savings.

`Harness Distillation` remains useful as a historical/internal name for the bounded calibration/qualification research machinery. It is not itself a product category or moat claim.

## 3. The product boundary

ExactScope should own only the smallest semantic and qualification delta that creates independent value.

The host owns:

- retrieval execution and authorization;
- corpus/index/vector-database management;
- tokenizer and chat-template implementation;
- exact rendered token accounting;
- model weights and inference;
- scheduling and batching;
- KV/prefix-cache implementation and eviction;
- constrained-decoding implementation;
- speculative decoding;
- accelerator selection;
- retries/fallback after ExactScope rejects or becomes unavailable;
- deployment activation and rollback.

ExactScope may own:

- a restricted workload/evidence/answer contract;
- authority, coverage, freshness and conflict requirements where the application needs them;
- bounded provenance-preserving evidence shaping;
- evidence-sufficiency/context-admission rules;
- semantic answer-contract lowering requirements;
- deterministic proof-based completion only when a registered sound verifier exists;
- strict finalization semantics;
- host/model/runtime/capability identities needed for qualification;
- the cold calibration/selection/qualification process and its evidence lineage.

ExactScope must not become another inference runtime, vector database, full RAG framework, tracing platform, generic evaluator, or agent/test-time-scaling loop.

## 4. The v1.1 semantic center is deliberately narrow

The strongest current architecture should focus on two related decisions before expanding the rack:

1. **Evidence sufficiency and context admission** — determine a bounded provenance-preserving evidence delivery under explicit coverage rules, then require the host to confirm exact rendered fit. Do not guess token fit from bytes or silently truncate.
2. **Answer-contract lowering** — express the permitted answer domain and evidence obligations, bind to a qualified host-native constraint surface when appropriate, and apply the same deterministic finalization contract afterward.

Proof-based zero-call completion is optional and only valid when the current request/evidence satisfies a registered verifier. Cache, speculation, broad zero-call QA, adaptive routing, and accelerator hints are not part of the minimum product identity.

## 5. Source representation for a credible compiler

A compiler interpretation requires a stable restricted source representation. The current proposed field groups are:

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
  evidence_composition_requirement
  evidence_projection
  evidence_budget_bytes
  evidence_ordering
  answer_contract
  constrained_output_binding
  context_fit_requirement
  proof_completion
  stable_prefix_eligibility
```

These descriptors must be versioned, bounded, and interpretable. They do not imply that ExactScope can automatically infer trustworthy workload semantics from arbitrary prose or traffic. Application semantics must be supplied or explicitly derived under a validated process.

For Stage 1 these descriptors are frozen metadata only and may not influence selection unless their behavior is already part of the preregistered policy definition.

## 6. The exact compiled artifact

Do not represent qualification by mutating a candidate's `qualified` flag. Compile two immutable artifacts:

1. **Candidate Execution Policy** — the deterministic semantic policy and host obligations selected before held-out.
2. **Qualification Attestation** — a separate immutable record that references the exact policy digest and records the scope/evidence under which it passed or failed.

The customer-facing **Qualified Execution Profile** is the qualified pair, not merely a small JSON file.

A minimum candidate policy should identify:

```text
policy
  schema/canonicalization/content identity
  workload contract identity
  query/retrieval request rule
  evidence-composition requirement + explicit bounded evidence budget
  evidence transform/order/coverage/authority/freshness/conflict rules
  allowed answer domain + citation/abstention semantics
  completion rule or disabled
  exact-fit requirement
  required host capabilities
  qualified optional capability bindings
  structured-output dialect/subset when used
  bounded generation settings + max model calls
  deterministic admission/finalization/rejection rules
```

A qualification attestation should identify:

```text
attestation
  policy digest
  model/runtime/tokenizer/template identities
  adapter/executor/retrieval/evidence identities
  workload population + grouping identity
  hardware/load identity for cost/latency claims
  preregistration/calibration/held-out/scorer/analysis digests
  B/F/P/T identities
  paired counts + exact bounds
  contract/coverage/rejection outcomes
  serving economics + timing results
  compilation/qualification/integration cost
  explicit validity scope + invalidation/review rules
```

Large customer evidence and raw calibration answers do not belong in the hot artifact.

## 7. Request-bound receipt and runtime semantics

Request-time data belongs in a separate immutable receipt that binds the current operation to the policy and evidence actually used:

```text
request receipt
  request ID
  policy digest
  host identity
  authorized evidence snapshot
  selected source/revision/span IDs
  semantic delivery digest
  answer contract
  exact-fit confirmation
  proof, only when a registered completion verifier succeeds
```

The semantic spine remains:

```text
prepare(query, authorized_host_evidence, qualified_profile)
    -> Complete(answer, proof, receipt)
     | Generate(delivery, contract, requirements, receipt)
     | Reject/Unavailable(reason)

host inference only for Generate

finalize(contract, model_output, receipt)
    -> Accept(answer)
     | Reject(reason)
```

`Accept` means the declared checks passed. Structural validity is not a truth guarantee. ExactScope never silently selects another policy or initiates fallback after rejection; the host owns application fallback.

Retrieval timing must be explicit. If a profile requests bounded overfetch, the host must read that request before retrieval or participate in one specifically defined pre-generation fetch exchange. v1.1 should start with the simpler predeclared retrieval request; a multi-stage adaptive retriever is outside the minimum product.

## 8. Stage 1 compiler semantics — completed falsification

The immutable pre-score rules remain in [`V1_1_STAGE1_PREREGISTRATION.md`](V1_1_STAGE1_PREREGISTRATION.md), and the completed result is in [`V1_1_STAGE1_REFERENCE_ONLY_RESULT.md`](V1_1_STAGE1_REFERENCE_ONLY_RESULT.md).

The first fresh 6+6 experiment rejected its selected cheaper candidate. The larger prospectively frozen Stage 1 then executed 1,200 calibration observations across the ten-policy catalog and returned:

```text
ReferenceOnly
P = null
T = integrated = F
```

The predeclared Reference had 52/120 calibration successes. No cheaper candidate matched that aggregate success count; no cheaper candidate preserved every Reference success; and no frozen candidate reached the descriptive 15% cost-reduction target. Because `T = F`, the observed bottleneck is not merely the paired-preservation constraint. The sealed 600-item held-out was therefore not scored.

The formal result is `NOT_EVALUATED_REFERENCE_ONLY` for narrow selector, product and incremental-selector verdicts. The study was also prospectively classified algorithm-diagnostic-only because no defensible absolute deployable-task competence floor existed for FEVER. It cannot emit a Qualified Execution Profile or support customer/product qualification.

The frozen 15% cheaper-reference threshold is not retroactively relaxed. It remains the default threshold for any future claim specifically framed as materially cheaper reference-preserving execution unless a new customer workload and economic model prospectively justify a different requirement.

The stopped FEVER 600 remains sealed and retired from revised-rule confirmatory inference. New policy families or objectives require genuinely fresh evaluation data.

## 9. Next product proof separates product value from conditional optimization

The next study must first answer whether ExactScope supplies useful customer value on a competent workload, rather than assuming cost compilation exists.

Primary branch:

1. use one bounded enterprise document collection with real host retrieval;
2. establish competent Base and fixed integrated-style configurations on development data under workload-owner rules;
3. freeze correctness, citation/evidence support, abstention, unacceptable-error, latency and total-economics requirements;
4. independently evaluate integrated-style versus Base on fresh grouped data;
5. emit no qualified artifact unless the full competence/economic contract passes.

Conditional optimization branch:

1. freeze a small candidate family, `F`, selector `P`, conventional comparator `T`, cost model and tie breaks before calibration;
2. admit `P` only through the frozen rule;
3. if calibration yields no `P`, stop that branch without using `F`/`T` as rescue;
4. only an admitted `P` reaches its separately frozen held-out comparisons.

Human adjudication may be used offline under a frozen blinded rubric when the bounded task cannot be scored deterministically. It must not become a runtime second-model judge, retry loop, or answer-improvement mechanism.

## 10. What would make the compiler thesis real

The label `compiler` is justified as an engineering description only if the system has:

- a restricted source representation with explicit semantics;
- static validation/type checks for unsupported obligations;
- legal lowering to host capability requirements;
- a bounded calibration/selection pass;
- an immutable compiled artifact and evidence lineage;
- explicit qualification scope;
- deterministic runtime preparation/finalization semantics;
- fail-closed incompatibility behavior;
- defined recompilation/requalification triggers.

Novel optimization is not required for the word `compiler`, but distinct product value is. If v1.1 only enumerates prompt/evidence settings, saves the cheapest winner, and attaches a test report, it should be described honestly as configuration optimization with qualification artifacts.

A stronger compiler demonstration is one workload contract that lowers correctly to multiple host mechanisms, rejects invalid combinations before generation, and later uses prior interaction knowledge to reduce target search/qualification work without weakening the final gate.

## 11. Differentiation and moat hypothesis

Today the most accurate external description of demonstrated capability remains:

> **a constrained configuration optimizer with semantic enforcement and qualification records**

The plausible long-term asset is not the selector, profile file format, adapter count, or binary size. It is accumulated prospective knowledge of:

```text
workload properties
x host/runtime capabilities
x semantic intervention definitions
x intervention interactions
        ->
fresh transfer outcomes
        ->
better candidate ranking / less calibration-search effort
```

This is currently a **plausible learning asset, not a demonstrated moat**.

The hypothesis is falsified as a moat if each new host/workload still requires effectively cold exhaustive search. The registry must therefore store positive, negative, and inconclusive outcomes, not merely `policy_id -> score` winners.

Before public moat language is reasonable, the evidence should span multiple independently sourced workloads/domains, genuinely different runtime and model families, untouched target combinations, more than one customer/integrator, and at least one later runtime/model update. Even then the first honest phrase is an **emerging transfer advantage**, not an automatic durable moat.

## 12. Evidence ladder

### Stage 1 — within-workload compiler value — stopped

The Qwen/FEVER falsification completed at calibration with `ReferenceOnly`, so the intended useful cheaper candidate was not demonstrated and the 600 held-out was not consumed. This stage now contributes experiment-integrity and negative-frontier evidence only.

### Stage 2 — competence-gated real-retrieval document QA — current priority

Use genuine retrieval over authorized versioned documents. First establish workload-owner competence requirements and viable Base/fixed intervention behavior on development data; stop before confirmatory qualification if a credible reference does not exist. Include missing evidence, distractors, stale/conflicting sources, unanswerable requests, and long contexts. Compare with:

- a competent production-like Base;
- a predeclared strong fixed intervention;
- a matched-budget generic/DSPy-style tuning workflow;
- a better-model alternative where deployable.

Charge fallback, integration, qualification, maintenance and refresh costs. Include a matched prompt-only or semantic-rule ablation so the semantic layer must demonstrate value beyond simple prompt pruning.

### Stage 3 — prospective transfer

Freeze source-derived knowledge before target outcomes. Compare prior-informed search with cold search, a strongest static recipe, and descriptor-blind pooled priors on untouched host/workload combinations under the same final qualification strength.

The initial transfer hypothesis is at least **30% fewer candidate executions or calibration labels** to reach a qualified result without materially reducing qualification yield. Ranking improvement does not justify weakening the independent final held-out gate.

Only Stages 2 and 3 can materially support customer value, cross-runtime value, or a compounding knowledge advantage.

## 13. First commercial validation wedge

The strongest current first wedge remains:

> **high-volume bounded enterprise document QA with a genuinely pinned or expensive-to-change model, authoritative evidence, measurable recurring serving cost, and enough eligible traffic to amortize calibration and qualification.**

Narrow initial tasks further toward:

- short factual answers;
- extraction;
- typed decisions;
- citations/provenance-bound answers.

Open-ended synthesis weakens deterministic acceptance and raises qualification cost.

The likely buyer is the team jointly responsible for application quality and inference spend. A pinned model is a constraint to validate, not a moat. If a better model or simpler runtime change wins on total economics and is deployable, ExactScope should recommend that instead.

A reasonable Stage 2 commercial hypothesis can include integration within roughly five engineer-days and payback within roughly 90 days, but those thresholds must be validated with the actual buyer and frozen before scoring. Two independent paid pilots, followed by at least one continued/renewed production use through a refresh cycle, are the kind of evidence needed before strong commercial-fit claims.

On-device/embedded retrofit remains an important long-term market and architecture constraint, not the automatic first proof.

## 14. Product metrics

Do not collapse product value into one score. Report at least:

- task correctness and domain score;
- paired Base/Reference/ExactScope/conventional-tuner outcomes;
- evidence correctness, coverage and rejection/abstention;
- unsupported, false-grounded, wrong-confident and strict-format failures;
- model-call count;
- prompt/completion tokens;
- retrieval work;
- host and ExactScope CPU work;
- E2E latency distribution and p95 under frozen load;
- CPU/RAM/cold start;
- distribution bytes and incremental dependencies;
- runtime payload and post-link contribution where relevant;
- integration and maintenance effort;
- calibration/qualification cost;
- serving-volume lifecycle break-even.

For self-hosted inference, explain how saved work becomes avoidable cost or useful throughput. Efficiency is not automatically monetary savings.

## 15. Working product language

Current product sentence:

> **ExactScope is a workload-specific qualification/configuration optimizer that binds bounded semantic policies to explicit evidence, competence and economics checks for an existing AI stack.**

Customer sentence:

> **ExactScope evaluates bounded configurations of an existing document-answering service and delivers a deployable profile only when a prospectively declared qualification contract passes on fresh evaluation data.**

Research hypothesis:

> **Can this restricted policy/qualification layer eventually earn the stronger Semantic Inference Policy Compiler interpretation by prospectively reducing search and qualification effort across workloads and hosts?**

Research shorthand:

> **Fine-tune the inference path, not the model.**

Long-term shorthand:

> **Same model. Same runtime. Better answer.**

The first two describe the intended architecture/product shape. They must not be presented as evidence that a new category, savings, low integration effort, or transfer moat has already been established.

## 16. Things not to do yet

- do not call the first 6+6 rejection successful Harness Distillation;
- do not use the old held-out to validate the post-failure selector or A+D;
- do not market `Semantic Inference Policy Compiler` as an established category;
- do not call a profile, adapter, immutable config, one-call path, evaluation gate, or small binary a moat by itself;
- do not rescue or restart the stopped FEVER Stage 1 by broadening the catalog, relaxing thresholds, running F/T alone, or scoring the sealed 600 held-out;
- do not reuse the FEVER 600 for revised-rule confirmatory inference or policy development;
- do not begin the enterprise document-QA confirmatory phase before workload-owner competence, grouping/sample, economic model, timing, adjudication/scorer and all branch semantics are frozen;
- do not add adaptive per-query routing, learned routing, judge/retry/reflection/agent loops, or a mandatory second model;
- do not make ExactScope own retrieval/runtime/tokenizer/cache/scheduler/speculation machinery;
- do not reactivate quarantined negative materials from already-scored evidence;
- do not expand runtime adapters merely to claim portability;
- do not make native code mandatory without a concrete Python-free consumer or measured bottleneck/integration benefit;
- do not claim release qualification from oracle-page-pooled FEVER;
- do not claim cross-runtime value, customer savings, category distinctness, or moat until prospective evidence supports each claim.
