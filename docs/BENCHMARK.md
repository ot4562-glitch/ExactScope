# ExactScope benchmark contract

ExactScope must earn adoption with measured evidence, not with the claim that deterministic code is obviously better than model arithmetic.

The core product question is:

> **For an existing constrained on-device model, can a tiny ExactScope capability slice recover enough useful narrow-domain ability at sufficiently low binary, RAM, token, latency, energy, integration, and qualification cost that keeping the current model/hardware becomes the better engineering choice?**

The strategic comparison is therefore often:

```text
existing small model
vs
existing small model + ExactScope capability slice
vs
larger model / newer hardware reference
```

The larger-model reference does not need to fit the original target device; it represents capability pressure that a product team might otherwise answer with a model/hardware generation jump. Its deployment cost must be reported separately.

See [`CAPABILITY_PRODUCT_ARCHITECTURE.md`](CAPABILITY_PRODUCT_ARCHITECTURE.md) for the product-unit design and [`STATISTICS_CAPABILITY_SLICE.md`](STATISTICS_CAPABILITY_SLICE.md) for the first flagship domain proof.

## 1. Required comparison shapes

### 1.1 Current generic arithmetic proof

For bounded `xs_calc` numerical reasoning, retain a reproducible arithmetic-specific comparison:

| Arm | Description |
|---|---|
| A | model-only quantitative reasoning |
| B | model -> unconstrained `xs_calc` plan -> ExactScope |
| C | model -> constrained `xs_calc` plan -> ExactScope |
| D | gold plan -> ExactScope deterministic ceiling |
| E | optional larger-model reference under separately reported deployment cost |

Arm C is the intended constrained generic arithmetic path. Arm D is not a model score; it verifies whether a gold-derived dataset slice can be represented and executed by ExactScope.

### 1.2 Flagship capability-slice proof

For a domain capability product, the required comparison changes because the key question is whether reviewed semantic operations add value beyond generic exact arithmetic.

The first Statistics proof uses:

| Arm | Surface | Purpose |
|---|---|---|
| A | small model only | baseline capability and wrong-number behavior |
| B | small model + `xs_calc` only | isolates generic exact-arithmetic value |
| C | small model + Statistics semantic slice only | isolates reviewed domain-method value |
| D | small model + `xs_calc` + Statistics semantic slice | target combined capability profile |
| E | larger-model reference | measures the capability gap that might otherwise motivate a model/hardware upgrade |

Arm E is included only where the reference model meaningfully outperforms Arm A and can be evaluated fairly. A narrow-domain result must never be generalized into overall model equivalence.

### 1.3 Discovery is an ablation, not a product arm

`xs_find -> xs_eval` may be measured when discovery cost matters, but it is a cold/development fallback and should not replace the normal one-turn capability arms above.

## 2. Model classes

The first public capability evidence should include multiple constrained model classes rather than one unusually tool-capable model:

- at least one approximately 0.5B-0.8B local model;
- at least one approximately 1B model;
- at least one approximately 1.5B-2B model;
- at least one roughly 3B-class local model;
- optional stress models below the main range;
- at least one larger-model reference where fair and useful for the flagship comparison.

For every run record:

- model name and exact revision;
- quantization;
- tokenizer identity;
- context size;
- inference runtime and exact revision;
- hardware;
- thread/device configuration;
- prompt/system policy;
- tool schema/grammar/profile identities;
- sampling/reasoning configuration;
- generation-token budget.

## 3. Workload classes

The product proof has two distinct workload classes.

### 3.1 Public bounded-plan numerical reasoning

Use public datasets with gold programs, derivations, or metadata that permit deterministic compatibility selection without consulting model outputs.

For every published `ExactScope-compatible subset`:

- selection must come from gold program/derivation/metadata, never model answers;
- exact source revision and source-file digest must be pinned;
- a converter must produce a bounded ExactScope plan;
- each candidate plan must execute through the actual ExactScope artifact;
- runtime acceptance and exact explicit-answer match must be reported separately;
- coverage against the full published split must be reported;
- unsupported items remain visible in full-dataset reporting and are not silently discarded;
- compatible-subset evidence must never be labeled as the official full-dataset model score.

Current repository evidence:

- FinQA test: 1,061 bounded programs were identified, 1,058 were runtime-accepted, and 275 exactly matched the explicit dataset answer under the conservative no-semantic-repair interpretation;
- TAT-QA dev: 717 bounded arithmetic derivations were runtime-accepted and 443 exactly matched the explicit answer.

These are gold-derived compatibility/deterministic-ceiling measurements, **not model accuracy scores**. Dataset transformations such as implicit percentage scaling or dataset-specific rounding are intentionally not guessed by generic arithmetic.

### 3.2 Reviewed domain capability workloads

A domain benchmark is organized around **task families**, not operation count.

For the first Statistics flagship slice, use the task families defined in [`STATISTICS_CAPABILITY_SLICE.md`](STATISTICS_CAPABILITY_SLICE.md):

- descriptive aggregation;
- weighted mean;
- sample/population variance distinction;
- sample/population standard-deviation distinction;
- Pearson correlation;
- semantic ambiguity/failure preservation.

Each benchmark item must contain machine-readable gold data independent of model output:

- task-family ID;
- user-facing prompt;
- expected supported/ambiguous state;
- expected operation/method when applicable;
- exact argument values/order;
- deterministic expected result or expected typed failure;
- source/template/revision/seed identity.

Every supported gold call must execute through the actual ExactScope artifact before the item is admitted to a capability benchmark.

## 4. Stage-level quality metrics

Do not publish one blended accuracy score without the failure breakdown.

Measure separately:

1. **tool-use recognition** — did the model recognize a supported deterministic task?
2. **plan/operation selection** — did it choose the correct bounded plan or reviewed semantic method?
3. **argument extraction** — were correct values captured with correct identity/order/reference relationships?
4. **tool/plan syntax validity** — was the request structurally valid for the schema/grammar?
5. **plan/semantic validity** — were references, arity, method, and resource bounds valid?
6. **core acceptance** — did strict validation accept the request?
7. **correct usable answer rate** — did the task end with the correct useful result?
8. **result fidelity** — did the model preserve the ExactScope result rather than recompute it?
9. **failure fidelity** — did ambiguity/invalid input remain an error/clarification state rather than become a fabricated number?
10. **incorrect numeric answer rate** — did the path return a plausible but wrong number?
11. **tool penalty rate** — was model-only correct while the ExactScope path became incorrect because recognition, extraction, plan formation, or tool use regressed it?
12. **ambiguity-preservation rate** — for designated negative cases, did the path avoid silently selecting an unjustified semantic method?

This split is required to test the fail-closed tradeoff: fewer wrong numbers must not be achieved only by turning useful answers into opaque failures.

## 5. Model-difficulty budget and measurements

A capability slice can be tiny in binary size and still be too difficult for a weak model to call. Model-interface cost is therefore a first-class budget.

For every benchmarked profile record:

- number of model-visible top-level tools;
- number of visible semantic operations;
- prompt-fragment bytes;
- prompt-fragment tokens for the exact model tokenizer;
- tool/JSON-Schema bytes;
- grammar bytes;
- maximum and actual generated request/tool-call tokens;
- normal and actual inference turns;
- `xs_calc` plan-step count where applicable;
- structurally valid-call rate;
- core-accepted-call rate;
- correct plan/operation-selection rate;
- argument-extraction rate;
- result/failure-fidelity rate.

The draft profile fields live in [`../spec/CAPABILITY_PROFILE_V0_1.md`](../spec/CAPABILITY_PROFILE_V0_1.md). Static ceilings are not substitutes for measured weak-model results.

## 6. Device/resource cost metrics

Measure the incremental systems cost of the exact capability profile:

- final artifact bytes;
- marginal bytes versus the comparison profile, for example `xs_calc`-only versus `xs_calc + Statistics`;
- resident memory;
- context bytes;
- ExactScope scratch/evaluation bytes;
- vector transport scratch/copy bytes where relevant;
- peak host memory where measurable;
- prompt and completion/tool-call tokens;
- model inference turns;
- end-to-end latency;
- model latency separately;
- ExactScope compute latency separately;
- cold discovery latency separately when discovery is benchmarked;
- energy per successful task where measurable;
- Wasm imports and memory pages for the no-import profile.

Desktop measurements remain desktop validation. Real-device latency/RAM/energy claims require a named physical target.

## 7. Fail-closed experiment

A dedicated subset must test malformed or semantically ambiguous requests that look recoverable.

Cover at least:

- extra whitespace/outer-envelope variations;
- JSON number versus exact decimal string where exact lexical preservation is possible;
- missing arguments;
- swapped arguments;
- invalid/forward plan references;
- percent-versus-ratio ambiguity;
- unit-bearing values;
- sample-versus-population ambiguity;
- missing weights or mismatched vectors;
- wrong/unsupported operation;
- zero denominator/domain failures.

Adapters may normalize syntax only according to the AI integration contract. Semantic repair is forbidden.

Report:

```text
invalid call rate
adapter-normalized rate
core-rejected rate
correct usable answer rate
incorrect numeric answer rate
ambiguity-preservation rate
```

## 8. Model-surface experiment

The benchmark should test whether the selected model surface is actually appropriate for weak models.

For generic arithmetic, compare where useful:

- model-only reasoning;
- one unconstrained `xs_calc` plan schema;
- one constrained `xs_calc` grammar;
- equivalent multi-tool/per-operation exposure only as an ablation.

For semantic methods, do **not** assume that 8/16/32 operations are inherently good product tiers. Instead compare the smallest task-family-complete candidate slice against wider ablations when useful.

Measure how every added operation affects:

- prompt/schema/grammar size;
- operation-selection accuracy;
- structural validity;
- argument extraction;
- tool penalty;
- latency/tokens;
- final capability gain.

The broad academic/domain source catalog must never be injected into a tiny-model prompt merely because it exists.

## 9. Capability density

ExactScope should publish capability gain together with the incremental cost required to obtain it.

Useful ratios include:

```text
successful-answer uplift / 100 KiB added artifact
wrong-number reduction / 100 KiB added artifact
successful-answer uplift / added resident-memory KiB
successful-answer uplift / added prompt token
successful-answer uplift / added millisecond
successful-answer uplift / joule        # only where measured
```

Always publish the raw numerator and denominator beside each ratio. A high ratio from a trivial absolute gain is not a compelling product result.

## 10. Capability Recovery Ratio (CRR)

When a larger-model reference meaningfully outperforms the small-model baseline on the declared task family, report:

```text
CRR = (small_model_plus_exactscope - small_model)
      ------------------------------------------------
      (larger_model_reference - small_model)
```

For the flagship five-arm benchmark this normally becomes:

```text
CRR = (Arm D - Arm A) / (Arm E - Arm A)
```

Interpretation on that exact benchmark slice:

- `0.0`: none of the measured larger-model advantage was recovered;
- `0.5`: half of the measured gap was recovered;
- `1.0`: the ExactScope profile matched the larger-model reference on the declared primary metric;
- `>1.0`: possible on narrow deterministic tasks, but never evidence of general model superiority.

CRR is not useful when Arm E does not beat Arm A. Do not force a denominator or hide that case.

Every CRR report must include:

- A/D/E raw scores;
- exact task-family/corpus scope;
- ExactScope binary/RAM/token/latency/energy cost;
- larger-model storage/RAM/latency/energy cost where measurable;
- exact model/runtime/artifact identities.

## 11. Reproducibility

A public benchmark result must identify:

- ExactScope source commit and release artifact digest;
- core/ABI version;
- capability-profile ID/revision and digest;
- source catalog/pack/hot-set identity and selected operation revisions;
- tool/JSON-Schema/GBNF/prompt digests;
- benchmark dataset/corpus and mapping revision/digest;
- model/runtime/tokenizer/quantization/hardware configuration;
- raw per-item results or equivalent machine-readable artifact;
- aggregation script/version;
- support/evidence label.

Published comparative claims must be reproducible from these records.

### Current repository evidence state

`benchmarks/run_benchmark.py` currently implements the existing semantic-operation four-arm harness and writes per-item JSONL plus a digest-bound summary. `crates/exactscope-conformance/src/bin/exactscope-core.rs` bridges benchmark calls into the real bounded Tiny JSON adapter rather than duplicating calculation logic.

`hotsets/quant-core-16.json` remains the mixed economics/statistics prerelease evaluation selection, with focused domain hot sets retained separately. It is implementation/evaluation infrastructure, not the final capability-product profile.

`benchmarks/public_xs_calc_oracle.py` provides the pinned-source FinQA test and TAT-QA dev arithmetic compatibility path described above. Its checked-in reports are deterministic-ceiling evidence, not model accuracy.

`examples/llama.cpp/benchmark_xs_calc.py` and checked-in/reference results provide a five-case three-model integration smoke. The current recorded smoke is:

- Qwen3 0.6B Q8_0: 60% correct final / 20% wrong numeric;
- Qwen3 1.7B Q8_0: 100% / 0%;
- Llama 3.2 3B Instruct Q4_K_M: 60% / 0%.

This smoke validates the one-turn integration path and failure behavior on a tiny fixed set. It is not the flagship multi-model capability benchmark.

The next benchmark implementation target is the Statistics capability profile/corpus in [`STATISTICS_CAPABILITY_SLICE.md`](STATISTICS_CAPABILITY_SLICE.md), including the five required arms, model-difficulty measurements, capability density, and CRR where meaningful.

## 12. Claim policy

Public documentation may say:

- ExactScope already performs bounded deterministic quantitative operations outside the model;
- bounded `xs_calc` and reviewed semantic `xs_eval` are implemented experimental model-facing lanes;
- the repository includes reproducible generic-arithmetic compatibility/oracle evidence and a small llama.cpp integration smoke;
- native static C ABI and no-import Wasm are primary RC/evaluation deployment shapes;
- the product is designed to make a narrow small-model capability upgrade much cheaper than a model/hardware jump.

It must **not** claim proven hardware-life extension, end-to-end accuracy improvement, latency/token/energy savings, Statistics capability uplift, larger-model substitution, or general model equivalence without the corresponding reproducible comparison evidence.

Development/design thresholds may guide architecture but must be labeled as such and excluded from headline product claims.

## 13. Product decision rule

The next product milestone is not more operation count. It is a convincing **capability-slice proof**.

The flagship Statistics result should answer:

1. can multiple constrained 0.5B-3B models reliably invoke the selected capability slice?
2. does reviewed Statistics semantics add useful value beyond `xs_calc` alone?
3. does wrong-number reduction outweigh any tool penalty/rejection cost?
4. what binary/RAM/token/latency/energy cost buys the measured gain?
5. where a larger-model reference is meaningful, what fraction of its measured advantage is recovered?

If those answers are weak, ExactScope should improve the interface, slice, or evidence before expanding domain/catalog/platform breadth.
