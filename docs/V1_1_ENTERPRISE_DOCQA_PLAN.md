# ExactScope v1.1 — enterprise document-QA qualification plan

Status: **prospective non-scoring protocol; no enterprise dataset, workload-owner thresholds, or confirmatory sample is frozen yet**

Updated: **2026-09-13**

This is the next empirical plan after the preregistered Qwen/FEVER Stage 1 stopped at `ReferenceOnly`. It is not a rescue of the FEVER selector, does not reuse the sealed FEVER 600, and does not assume that a cheaper policy exists.

The product under test is currently a **qualification/configuration optimizer with semantic enforcement and immutable qualification records**. `Semantic Inference Policy Compiler` remains a research hypothesis.

## 1. Primary question

The first customer-like question is:

> **On one bounded enterprise document-QA workload with real host retrieval, does a fixed ExactScope integrated-style semantic configuration satisfy prospectively declared competence and total-economic requirements relative to a competent unchanged Base?**

The primary comparison is fixed **Integrated vs Base**. It is not a policy-search superiority test.

A cheaper reference-preserving `P` branch is optional and separately preregistered. Failure to find `P` must not invalidate or rescue the primary Integrated-vs-Base product question.

## 2. Required workload shape

The study must use one bounded, authorized, versioned document collection whose intended authority and update process are known.

The frozen question population must include at least these semantic classes:

- **answerable** — sufficient authorized evidence exists in the corpus;
- **unanswerable** — the requested fact is not supported by the authorized corpus under the declared coverage contract;
- **materially ambiguous/conflicting** — the available authorized evidence does not justify one unqualified answer;
- **retrieval-stress** — answer-bearing material competes with plausible distractors or long-document context.

Open-ended creative/synthesis work is outside the first proof. Prefer short factual answers, extraction, typed decisions, or citation/provenance-bound answers where correctness can be adjudicated consistently.

### 2.1 Freeze evidence composition and budget before confirmatory scoring

The Workload Contract must prospectively declare whether the first bounded workload requires `single-source-precision` or `multi-source-coverage`, plus an explicit `evidence_budget_bytes`. Do not route per request from retrieval/model outcomes. If the customer workload truly contains materially different evidence-composition regimes, define separate frozen workload contracts/subpopulations from application-known semantics before confirmatory scoring and report them separately; do not learn the route from confirmatory outcomes.

The public NQ/Hotpot development results provide starting priors only: current local candidates are 3 KiB/cap8 precision and 3 KiB/cap12 coverage. The enterprise study must re-establish competence and total economics on its own development data with real host retrieval before either budget becomes confirmatory. A public-task win is not an enterprise default.

## 3. Real retrieval is mandatory

The confirmatory study must use the host's actual retrieval/index path or a frozen production-representative equivalent.

Do not use:

- oracle page pools;
- scorer gold to choose retrieval candidates;
- manually injected answer-bearing evidence that bypasses the declared retriever;
- per-arm retrieval gold;
- result-dependent query repair.

Gold/reference data remains scorer-side.

## 4. Data partitions and leakage groups

Before confirmatory scoring, freeze immutable identities for:

- development data — allowed for implementation debugging and competence feasibility;
- calibration data — used only if an optional optimizer branch needs candidate selection;
- confirmatory data — used only after every relevant policy/threshold/scorer/economic rule is frozen.

Grouping must prevent semantic leakage across partitions. The grouping record must declare the actual rule. Examples may include:

- same source document/revision family;
- same factual target/entity-field;
- paraphrases or template-equivalent questions;
- same answer-bearing section/span family;
- repeated policy/process clause;
- any customer-defined relation that would make cross-split memorization or tuning misleading.

No question/group can move partitions after confirmatory outcomes are visible.

## 5. Development competence gate

A product comparison is meaningless if the baseline/reference is not competent enough for the customer's task.

Before confirmatory data is scored, a **workload owner or explicitly delegated evaluator** must freeze:

- correctness metric(s);
- minimum acceptable correctness/utility;
- evidence/citation support metric and minimum when applicable;
- abstention correctness metric and minimum for unanswerable/ambiguous cases;
- definition of an unacceptable error;
- maximum acceptable unacceptable-error rate/count;
- any class-specific minimums that matter commercially or operationally;
- whether all gates are conjunctive;
- development evidence used to conclude Base and Integrated are eligible for confirmatory comparison.

If no defensible competence contract can be set before confirmatory scoring, the study remains development-only.

If Base or Integrated cannot meet the frozen development admission requirements, stop or redesign on development data. Do not lower confirmatory gates after seeing confirmatory outcomes.

## 6. Fixed configurations

### Base

Base is the competent unchanged customer/host configuration. Freeze all behavior that can affect outcomes, including:

- model and quantization;
- runtime/executor;
- tokenizer/chat-template identity or transitive bound identity;
- generation settings;
- retrieval/index version and query rule;
- top-k/budget;
- prompt/system policy;
- structured-output mode;
- retry/fallback behavior;
- context window;
- cache/load settings relevant to timing.

### Integrated-style ExactScope configuration

The fixed Integrated configuration may include only prospectively declared ExactScope-owned semantic changes, such as:

- retrieval-query / model-instruction separation;
- bounded candidate overfetch request to the host;
- frozen evidence-composition requirement + explicit evidence budget;
- deterministic provenance-preserving projection/order;
- compact prompt/profile choice;
- semantic answer contract;
- context-admission requirements;
- strict deterministic finalization;
- proof-based completion only where a sound registered verifier exists.

It must not silently add:

- a second model;
- model-as-judge at runtime;
- retry-for-quality;
- reflection;
- agent loops;
- hidden retrieval fallback;
- different model weights;
- a larger index unavailable to Base;
- outcome-aware routing.

If a mechanism is host-owned, ExactScope may only request/qualify its use; the runtime remains the mechanism owner.

## 7. Primary confirmatory metrics

The exact metrics and thresholds must be frozen before confirmatory scoring. The protocol must at minimum account for:

### Quality / safety

- task correctness / exact task utility;
- citation/evidence support correctness;
- unsupported or false-grounded answers;
- correct abstention on unanswerable/ambiguous cases;
- wrong-confident answers;
- strict contract/format violations;
- workload-owner unacceptable errors.

### Serving resources

- model call count;
- prompt/completion tokens where available;
- retrieval work;
- ExactScope/host CPU work where measurable;
- E2E latency distribution and p95 under frozen load;
- peak RAM/scratch if material;
- distribution/incremental dependency bytes if relevant to deployment.

### Total economics

The customer-value calculation must specify which costs are actually avoidable or valuable. The economic model should include applicable terms for:

- inference/compute;
- retrieval/index serving;
- human review/escalation;
- fallback to a more expensive path or model;
- unacceptable-error remediation or declared risk proxy, if the workload owner permits one;
- integration effort;
- calibration/qualification effort;
- refresh/requalification effort after corpus/model/runtime changes;
- operational maintenance.

Do not call token reduction "cost savings" unless the frozen economic model maps those resources to real avoidable cost or useful capacity.

## 8. Human adjudication

If deterministic scoring cannot fully judge the bounded task, human adjudication is allowed **offline only**.

Before confirmatory scoring, freeze:

- evaluator qualifications/role;
- rubric;
- allowed source material;
- blinding to arm identity where practical;
- primary/secondary adjudication process;
- disagreement/tie resolution;
- missing/invalid observation treatment;
- whether adjudicators can see model reasoning or only answer/evidence/receipt;
- whether a customer/workload owner must approve severe-error labels.

Human adjudication is a scorer, not a runtime mechanism. It must not be used to repair answers or trigger another model call.

## 9. Primary analysis contract

Before confirmatory scoring, freeze:

- estimand;
- sampling design;
- finite/infinite population interpretation;
- paired analysis method where the same question is run under both arms;
- uncertainty/confidence method;
- multiplicity handling if several conjunctive statistical gates are used;
- treatment of invalid/missing observations;
- minimum sample size / precision or power rationale;
- stopping rule;
- whether any subgroup/class gates are confirmatory or descriptive.

Do not copy FEVER's exact 3pp/2pp hypergeometric gates automatically. Those were specific to the frozen FEVER question. Reuse a method only if the new sampling design and customer decision justify it.

## 10. Product qualification logic

A Qualified Execution Profile may be emitted only if:

1. the exact candidate policy was frozen before confirmatory outcomes;
2. Base and Integrated passed the prospective competence-admission rules required by the study design;
3. every mandatory quality/safety/evidence gate passes;
4. every required operational/economic gate passes;
5. no mandatory identity/protocol violation occurred;
6. the analysis is conclusive under the frozen uncertainty rules;
7. the Qualification Attestation binds the exact policy, workload, data partitions, scorer/adjudication, model/runtime/retriever, timing/load and economic-model identities.

Otherwise emit a failed/inconclusive attestation, not a mutated "qualified" candidate.

## 11. Better-model / simpler alternative

The commercial proof **must include at least one competent ordinary deployable alternative outside ExactScope**, for example:

- a simpler fixed prompt/configuration change;
- a matched-budget generic tuning/evaluation workflow using the customer's existing tooling.

Where operationally feasible, also include a stronger model with the ordinary host path. If the workload is genuinely pinned to the current model, freeze the business/technical reason before confirmatory scoring rather than excluding the stronger-model option after outcomes are known.

If a simpler or better-model alternative wins total economics and is deployable, ExactScope should report that. The study must not define success in a way that protects ExactScope from replacement.

The confirmatory program must also include at least one representative **behavior-affecting update cycle** (for example corpus/retrieval/model/runtime/policy change): show that the prior profile becomes stale when required, that the requalification planner chooses the prospectively allowed targeted/full scope, and measure the incremental customer effort/cost of maintaining qualification.

## 12. Optional cheaper-policy branch

This branch is **not required** for the primary product proof.

If enabled, freeze before its calibration:

- candidate catalog and canonical IDs;
- predeclared Reference `F`;
- selector `P`;
- conventional tuner `T`;
- scalar economic objective and coefficients;
- mandatory quality/capability gates;
- tie breaks;
- calibration/confirmatory partitions;
- exact held-out qualification rule.

For a claim specifically framed as **materially cheaper reference-preserving execution**, the existing 15% cheaper-reference threshold remains the default until a new customer economic model prospectively justifies another materiality threshold. Do not lower it because FEVER produced only 11.75% descriptive savings for its cheapest calibration policy.

If calibration yields `ReferenceOnly` or `NoQualifiedReference`, stop this branch. Do not run F/T on its held-out merely to obtain another result.

## 13. Artifact model

Keep artifacts immutable and status-explicit:

```text
Candidate Execution Policy
  status = development candidate

Qualification Attestation
  status = qualified | failed | inconclusive | invalid
  binds exact candidate digest and evaluation identities

Qualified Execution Profile
  exists only for a qualified pair
```

Development/calibration leadership never changes the candidate into a qualified artifact.

## 14. Invalidation / refresh

Before production use, declare what invalidates the qualification, including relevant changes to:

- document corpus/revision policy;
- retrieval/index implementation or configuration;
- model/quantization;
- runtime;
- tokenizer/chat template;
- semantic policy;
- output constraint surface;
- hardware/load for latency/economic claims;
- workload population or business rule;
- cost model.

Define whether each change requires full requalification, targeted requalification, or only identity refresh. Do not invent this after a production incident.

## 15. What must exist before first confirmatory model call

All of the following must be real, non-placeholder records:

- workload record;
- corpus/retrieval identity record;
- partition/grouping freeze;
- competence contract;
- Base configuration;
- Integrated configuration;
- a competent ordinary deployable alternative outside ExactScope;
- scorer/adjudication contract;
- timing/load contract;
- total-economic model with executable counter identities and fixed non-serving costs frozen before outcomes;
- analysis/sample-size plan and exact analysis implementation source identity;
- invalid-observation and stopping rules;
- optional optimizer-branch record or explicit `disabled` state;
- preregistration that hashes/binds the workload/retrieval/competence/configuration/scoring/timing/economic/analysis records and runner/scorer source identities;
- a Study Contract that additionally validates and binds the exact Candidate Execution Policy + Workload Contract + Host Capability Manifest, the ordinary alternative, executable economics, exact runner/readiness/scorer/analysis/decision source digests, evidence composition/budget/cap, pre-outcome fixed economic counters, and the exact gold-free runner-visible confirmatory question-set digest/count before the first model call.

The preregistration validator must reject missing, empty, placeholder, `TBD`, `TODO`, or unapproved owner-defined thresholds. Canonical JSON threshold values use **integers with explicit units** (for example basis points, ppm, counts, milliseconds or internal cost units); floating-point thresholds are not part of the preregistration format.

The current reference implementation intentionally separates the complete artifact chain:

```text
enterprise_docqa_preregister.py
  -> enterprise_docqa_study_contract.py
     [exact Candidate Policy + Workload Contract + Host Manifest + confirmatory question set bound before outcomes]
  -> enterprise_docqa_readiness.py
     [no inference/retrieval; complete frozen-bundle revalidation; readiness receipt]
  -> host-owned execution + enterprise_docqa_observations.py
     [observations bind the receipt; the run manifest is generated from frozen identities]
  -> offline adjudication + enterprise_docqa_score.py
  -> enterprise_docqa_analysis.py
     [frozen paired-bootstrap method/parameters; recomputes score core from raw frozen inputs]
  -> workload-owner decision + enterprise_docqa_decision.py
  -> enterprise_docqa_attest.py
     [revalidates the qualified decision, recomputes Workload Contract empirical gates,
      binds a canonical evaluation package and can emit a standalone generic Qualification Attestation]
  -> qualified_execution.py make-profile
     [revalidates Candidate + Attestation + Workload + Host]
  -> generic Qualified Execution Profile
```

The readiness report is part of the confirmatory run identity. Its absolute `confirmatory_run_output` is the frozen artifact root: observations and the sealed run manifest must both resolve strictly below that root. Every observation records the readiness digest; `enterprise_docqa_observations.py` validates the full matrix against that same receipt and can generate the run manifest from the frozen Study Contract. Score, analysis, and the final evaluation package preserve the same readiness digest.

`enterprise_docqa_readiness.py` is the only pre-run launch gate in the reference chain. It performs neither retrieval nor model inference; it must return `READY_FOR_CONFIRMATORY_EXECUTION` after revalidating the complete frozen bundle and confirming that the requested run output does not already exist. `enterprise_docqa_score.py` can only produce `GATES_PASSED_CANDIDATE`; it never emits a Qualified Execution Profile. `enterprise_docqa_analysis.py` is a reference analysis implementation whose exact source digest and method parameters are frozen before outcomes; it revalidates raw observations/adjudications and performs paired quality/economic comparisons against both Base and the ordinary alternative. `enterprise_docqa_decision.py` can mark a result `qualified` only when the frozen score, frozen analysis implementation/report, workload-owner acceptance, ordinary-alternative comparison, customer utility, total economics, uncertainty conclusion, and mandatory-violation checks all pass; the same decision rules are re-run before attestation so a hand-authored `qualified` JSON cannot bypass them. `enterprise_docqa_attest.py` then accepts only the exact north-star artifacts pre-bound in the Study Contract, remaps Integrated observations to the Workload Contract empirical requirements, constructs a canonical evaluation package over the frozen study/run/analysis/decision identities, invokes the generic attestation validator, and can emit the validated Qualification Attestation as a standalone artifact. It still does **not** emit a Qualified Execution Profile. The final step is generic: `qualified_execution.py make-profile` revalidates the Candidate Execution Policy, standalone Qualification Attestation, Workload Contract and Host Capability Manifest and only then writes the Qualified Execution Profile.

## 16. Explicit non-goals for the next proof

Do not build or test next:

- a learned/adaptive per-request policy router;
- a second-model judge or verifier;
- reflection/retry-for-quality loops;
- agent/test-time-scaling machinery;
- a mandatory new model or large index;
- cross-host transfer priors;
- broad compiler DSL/search infrastructure;
- new runtime/tokenizer/cache/scheduler ownership;
- more runtime adapters merely to claim portability;
- release packaging as a substitute for customer-value evidence.

## 17. Promotion after this study

Only a clean competent real-retrieval product result should reopen these later questions:

1. whether a cheaper-policy compiler branch is worth expanding;
2. whether source interaction knowledge prospectively reduces search/qualification work on another host/workload;
3. whether adaptive routing is worth its added learning/qualification burden;
4. whether native code materially improves deployment or economics;
5. whether v1.1 is ready for release-candidate distillation.

Until then, the smallest useful qualification/configuration optimizer is the product target.
