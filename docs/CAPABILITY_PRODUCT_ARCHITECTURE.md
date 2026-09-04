# ExactScope capability product architecture

Status: product architecture target for the next ExactScope design phase. This document defines the product unit, small-model interface principles, domain-slice strategy, build-vs-buy thesis, benchmark KPIs, and adoption path. It does not by itself create a new stable ABI or release claim.

## 1. Product boundary

ExactScope is not human-facing software. The runtime consumer is an AI system, especially a small or resource-constrained on-device model. A developer or OEM engineer is an integrator, not the end user of the calculation surface.

The product exists to let an already-deployed or physically constrained AI device gain narrow, high-value quantitative capability through a very small software addition when replacing the model or hardware is expensive, impossible, or disproportionate to the capability gap.

```text
human / sensor input
        |
        v
small on-device model
        |
        | tiny constrained machine-facing request
        v
ExactScope
        |
        | deterministic result / explicit failure
        v
small model / host renderer
```

A human calculator UI, interactive worksheet, end-user formula browser, general expression language, and user-oriented installation experience are out of scope for the core product.

## 2. The product unit is capability, not a function

A raw formula is easy for a large engineering organization to reimplement. ExactScope therefore must not define product value as the number of arithmetic functions or formulas shipped.

The useful unit is an **ExactScope Capability Unit**: a bounded task family that a target small model can perform materially better after adding a tiny ExactScope slice.

Examples of capability units are outcome-oriented rather than API-oriented:

- compute and correctly distinguish common descriptive-statistics measures;
- select and execute sample versus population variance correctly;
- execute a reviewed elasticity method without silently changing the method;
- perform a short exact multi-step quantitative derivation without model-side arithmetic drift;
- execute a compact family of finance formulas with fixed unit/method semantics.

One capability unit may internally require several operations, model hints, constraints, test vectors, and evaluation cases. Conversely, one operation is not automatically a meaningful capability unit.

## 3. Four-layer product architecture

ExactScope should be designed as four cooperating layers.

```text
+--------------------------------------------------+
|  1. Small-model surface                         |
|  xs_calc / compact xs_eval hot set              |
|  schema + grammar + minimal prompt policy       |
+---------------------------+----------------------+
                            |
+---------------------------v----------------------+
|  2. Capability slice                            |
|  selected reviewed operations + semantics       |
|  model/runtime-specific binding metadata        |
+---------------------------+----------------------+
                            |
+---------------------------v----------------------+
|  3. ExactScope MicroCore                        |
|  deterministic bounded exact execution          |
|  no_std / fixed limits / C ABI / no-import Wasm |
+---------------------------+----------------------+
                            |
+---------------------------v----------------------+
|  4. Domain source catalog                       |
|  Statistics / Economics / Finance / Physics ... |
|  provenance + methods + tests + benchmark maps  |
+--------------------------------------------------+
```

The domain source catalog may be broad. The model-facing surface must remain small.

## 4. Domain source versus deployed capability slice

ExactScope should make a hard distinction between a **domain source catalog** and a **deployed capability slice**.

### Domain source catalog

A source catalog is the reviewed superset for one discipline. It may contain many operations, semantic variants, provenance records, negative cases, and golden vectors. It is primarily a build-time and maintenance artifact.

A source catalog may grow without forcing a target model to see the entire catalog.

### Capability slice

A capability slice is the small, deployable selection compiled for one product, model class, runtime, or workload.

A slice should contain only what the target AI needs, for example:

```text
statistics source catalog
        |
        +--> statistics-8   tiny default slice
        +--> statistics-16  wider product slice
        +--> custom slice   OEM/workload-specific selection
```

The numeric suffix is a convenient implementation/profile label, not the product value by itself. Two 16-operation slices can have very different capability value.

## 5. Small-model-first interface law

The weaker the model, the less interface choice it should receive.

ExactScope should assume the target model may be bad at tool selection, JSON generation, argument ordering, long prompts, and error recovery. The interface therefore has to remove choices before inference rather than asking the model to reason its way through them.

### Required principles

1. **No full catalog in the hot prompt.**
2. **One generic arithmetic lane.** `xs_calc` remains one bounded plan tool rather than many arithmetic tools.
3. **Small semantic hot sets.** A deployed `xs_eval` surface should normally expose only a compact selected set.
4. **Constrained generation where available.** JSON Schema/GBNF or an equivalent typed binding should prevent structural errors before runtime.
5. **Canonical compact names.** Operation names and argument order should be stable and short enough for weak models.
6. **No required discovery turn.** `xs_find` remains cold/development functionality, not the normal serving path.
7. **No semantic repair by the adapter.** The system may normalize transport syntax but may not guess methods, values, percentages, units, or missing assumptions.
8. **No model recomputation.** Returned ExactScope values are authoritative for the supported deterministic task.
9. **Bounded requests.** Prompt, request bytes, operation count, plan length, and result size stay explicitly capped.
10. **One-turn preference.** A capability slice should be usable in one model generation and one ExactScope execution whenever possible.

## 6. Model difficulty budget

Every capability slice should publish a **model difficulty budget** in addition to a binary-size budget.

The initial report should include at least:

- number of model-visible tools;
- number of visible semantic operations;
- prompt-fragment bytes and measured tokens for each benchmarked tokenizer;
- schema/grammar bytes;
- maximum generated request tokens;
- maximum plan steps;
- number of model inference turns in the normal hot path;
- structurally valid-call rate;
- core-accepted-call rate;
- correct operation/plan selection rate;
- argument extraction rate;
- result-fidelity rate.

A domain feature that is mathematically correct but substantially increases choice entropy for a 0.5B-1B model is not automatically a product improvement.

## 7. Capability density

ExactScope should optimize for **capability density**: useful capability recovered per unit of added device and model cost.

A single synthetic score is easy to game, so the first releases should publish a vector of density measurements instead of collapsing everything into one number.

### Required capability-density measurements

- successful-answer uplift per 100 KiB of added artifact;
- incorrect-numeric-answer reduction per 100 KiB;
- final-answer uplift per KiB of resident memory added;
- capability uplift per added prompt token;
- capability uplift per millisecond of added end-to-end latency;
- capability uplift per joule where real-device energy can be measured.

ExactScope should also report the raw numerator and denominator. Ratios must never hide a very small absolute gain.

## 8. Capability Recovery Ratio

The central competitive reference is often a larger model or newer device, not another calculator library.

For benchmark tasks where a larger-model reference is meaningful, report a **Capability Recovery Ratio (CRR)**:

```text
CRR = (small_model_plus_exactscope - small_model)
      ------------------------------------------------
      (larger_model_reference - small_model)
```

Interpretation:

- `0.0` means ExactScope recovered none of the measured larger-model advantage;
- `0.5` means it recovered half of that benchmark gap;
- `1.0` means it matched the measured larger-model reference on that benchmark slice;
- values above `1.0` are possible on narrow deterministic tasks and must be reported without implying general model superiority.

CRR is undefined or not useful when the larger-model reference does not outperform the small-model baseline. Those cases must be reported rather than forced into the ratio.

CRR must always be accompanied by added binary, RAM, latency, token, and energy cost so the product question remains economic and systems-oriented.

## 9. Why a large vendor should buy/adopt instead of rebuild

ExactScope cannot rely on formula secrecy. Large vendors can implement arithmetic and common formulas themselves.

The build-vs-buy wedge is the maintained system around the formulas:

- weak-model-friendly tool-surface design;
- constrained-decoding assets for multiple runtimes;
- deterministic exact numeric semantics;
- domain method review and provenance;
- semantic negative cases and fail-closed behavior;
- footprint engineering for flash/RAM/scratch limits;
- stable C ABI and no-import Wasm portability;
- conformance and malformed-input suites;
- model-by-model benchmark evidence;
- digest-bound generated artifacts;
- update/rollback and target qualification evidence;
- long-term operation revision management.

The vendor decision should become:

```text
Build internally:
  own formulas + semantics + weak-model interface + grammar/schema
  + footprint optimization + ABI/Wasm + conformance
  + benchmark matrix + updates + qualification forever

Adopt ExactScope:
  choose required capability slice
  benchmark against target model
  integrate one tiny deterministic component
  consume maintained revisions and qualification evidence
```

The moat is therefore not one Rust implementation. It is the accumulated reviewed domain semantics, weak-model interface engineering, profile compiler, benchmark evidence, and qualification history.

## 10. Capability compiler target

The long-term developer product should include a build-time **capability compiler** that turns a broad reviewed domain source into a minimal deployed slice.

Conceptual input:

```text
target model class: 1B instruct
target runtime: llama.cpp
device budget: <= 128 KiB Wasm
normal path turns: 1
domain: statistics
required task families:
  - mean / weighted mean
  - variance / standard deviation
  - covariance / correlation
  - simple regression
```

Conceptual output:

```text
exactscope slice artifact
  + selected fused semantic operations
  + xs_calc if enabled
  + compact xs_eval tool definition
  + GBNF / JSON Schema
  + minimal prompt fragment
  + manifest and digests
  + conformance vectors
  + capability/difficulty metadata
  + benchmark mapping
```

The first implementation can remain deterministic and configuration-driven. Automatic ML-based profile optimization is not required for the initial product proof.

## 11. Slice selection rule

A slice should be selected by **task-family coverage under a model/device budget**, not by maximizing operation count.

A candidate operation belongs in a target slice only when at least one of these is true:

- it materially increases benchmarked task-family coverage;
- it removes a known ambiguity the small model handles poorly;
- it replaces a common multi-step fragile plan with a safer reviewed semantic operation;
- it is required by a real integration workload;
- its marginal footprint/model-surface cost is negligible and its maintenance burden is justified.

Operations should be removed when they add prompt/tool choice cost without measured capability value.

## 12. First flagship domain proof

Statistics is a strong first vertical because the repository already contains bounded statistics kernels and focused hot sets, and because method identity matters in ways that make a reviewed semantic layer more valuable than a generic calculator.

A first flagship proof should compare at least:

```text
A. small model only
B. small model + xs_calc only
C. small model + Statistics capability slice
D. small model + xs_calc + Statistics capability slice
E. larger-model reference
```

This separation answers two different questions:

- how much generic arithmetic reliability comes from `xs_calc`;
- how much extra domain capability comes from reviewed statistics semantics.

The first Statistics slice should be intentionally narrow and designed around a task-family benchmark, not around catalog completeness.

## 13. Product KPIs

The product should prioritize these KPIs in order:

1. correct usable answers on the target small model;
2. reduction in plausible wrong numeric answers;
3. low tool penalty on tasks the model already solves;
4. small binary/resident/scratch footprint;
5. low prompt/tool-call token cost;
6. one-turn hot-path success;
7. low model-surface invalid/rejected-call rate;
8. deterministic latency and energy overhead;
9. update/rollback and compatibility stability;
10. domain coverage only after the above remain healthy.

Raw operation count, repository size, number of wrappers, and number of supported platforms are secondary metrics.

## 14. Adoption path

The intended integration flow is:

```text
1. choose device/model/runtime budget
2. choose one or more domain task families
3. build/select the smallest candidate capability slice
4. benchmark model-only vs ExactScope vs larger-model reference
5. inspect capability-density and tool-penalty results
6. integrate native static or no-import Wasm artifact
7. run target conformance/self-test
8. deploy through the product's normal software-update mechanism
9. update capability slices independently when useful
```

The end user should not have to know ExactScope exists. The AI product should simply become better at the supported task family after the software update.

## 15. Commercial product boundary

The permissive core remains an adoption wedge. Commercial value, if pursued, should concentrate on work a vendor would otherwise need to maintain repeatedly:

- verified and maintained domain source catalogs;
- capability-slice/profile engineering;
- target/model benchmark packages;
- long-term operation revisions and change control;
- OEM qualification and compatibility records;
- LTS/SLA;
- custom domain capability engineering.

The business model should not depend on a cloud calculation service, user account, telemetry requirement, proprietary runtime fork, or human-facing subscription application.

## 16. Decision rule for every new feature

Before adding a feature, ask:

1. Does it give a constrained small model a measurable new capability or reduce a measurable failure mode?
2. Can a weak model use it without increasing interface complexity disproportionately?
3. Does it preserve the tiny bounded deterministic runtime profile?
4. Can it be compiled into a small capability slice rather than exposing the full domain catalog?
5. Can its value be measured against model-only and, where meaningful, a larger-model reference?
6. Is this work expensive enough for integrators to maintain that a reusable ExactScope implementation creates real build-vs-buy value?

If the answer to the first three is no, it should not enter the core product path.

## 17. Immediate next design/implementation milestones

The product architecture now has a design-draft capability profile, JSON Schema, Statistics example, and flagship Statistics slice/benchmark plan. The next work should be:

1. implement deterministic capability-profile validation/generation from existing hot-set/domain metadata;
2. emit measured model-difficulty metadata (bytes plus tokenizer-specific counts/results) rather than only design ceilings;
3. add Capability Recovery Ratio and capability-density reporting to the benchmark aggregation path;
4. implement the checked-in Statistics flagship corpus/gold generator described in [`STATISTICS_CAPABILITY_SLICE.md`](STATISTICS_CAPABILITY_SLICE.md);
5. benchmark that slice across multiple weak model classes using the five required arms;
6. compare the measured gain with a larger-model reference and the exact added device cost;
7. only then widen Statistics or start the next domain series.

The core product question remains:

> Can a tiny ExactScope capability slice recover enough narrow-domain ability on an existing constrained model that keeping the current model and hardware becomes the better engineering choice?
