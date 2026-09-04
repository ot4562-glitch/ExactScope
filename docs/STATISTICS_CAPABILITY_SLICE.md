# ExactScope Statistics flagship capability slice

Status: **product/benchmark design draft**. This document defines the first flagship semantic capability proof built from the existing `statistics-core-8` operation set. It does not claim that the slice has already passed the benchmark gates below.

See [`CAPABILITY_PRODUCT_ARCHITECTURE.md`](CAPABILITY_PRODUCT_ARCHITECTURE.md) for the product model and [`../spec/CAPABILITY_PROFILE_V0_1.md`](../spec/CAPABILITY_PROFILE_V0_1.md) for the draft profile format.

## 1. Why Statistics is first

Statistics is a useful first domain proof because:

- the repository already contains bounded reviewed statistics kernels;
- method identity matters: sample/population variance and standard deviation must not be silently conflated;
- vector extraction and argument formation stress small-model tool use more than scalar arithmetic alone;
- generic `xs_calc` can serve as a meaningful ablation, showing whether reviewed semantic operations add value beyond exact arithmetic;
- the initial surface can remain only eight semantic operations.

The goal is not to claim broad Statistics competence. The goal is to prove one narrow, useful **Statistics capability upgrade** at very small device and model-interface cost.

## 2. Initial operation selection

The first flagship slice reuses the existing `statistics-core-8` selection:

```text
stats.sum
stats.mean
stats.mean.weighted
stats.var.pop
stats.var.sample
stats.sd.pop
stats.sd.sample
stats.corr.pearson
```

No additional statistics operation should enter the flagship slice until the benchmark shows a task-family gap that justifies the extra model-surface and footprint cost.

## 3. Product task families

The product claim should be organized around task families, not operation names.

### S1 — descriptive aggregation

Target outcomes:

- sum a bounded vector;
- calculate the arithmetic mean;
- preserve exact decimal inputs;
- return explicit failures rather than model-side arithmetic guesses.

Primary operations: `stats.sum`, `stats.mean`.

### S2 — weighted mean

Target outcomes:

- distinguish ordinary mean from weighted mean;
- extract aligned value/weight vectors;
- reject malformed/mismatched input through normal ExactScope validation.

Primary operation: `stats.mean.weighted`.

### S3 — population versus sample variance

Target outcomes:

- choose population variance only when population semantics are explicit;
- choose sample variance only when sample semantics are explicit;
- avoid silently guessing when the prompt does not establish the method.

Primary operations: `stats.var.pop`, `stats.var.sample`.

### S4 — population versus sample standard deviation

Target outcomes mirror S3 while exercising deterministic square-root semantics.

Primary operations: `stats.sd.pop`, `stats.sd.sample`.

### S5 — Pearson correlation

Target outcomes:

- identify a request for Pearson correlation;
- extract two aligned vectors in the correct order;
- execute the reviewed correlation kernel;
- preserve domain/validation failures instead of fabricating a coefficient.

Primary operation: `stats.corr.pearson`.

### S6 — semantic ambiguity preservation

This is a negative capability family. The product should improve the AI not only by returning correct numbers, but also by avoiding unjustified numbers.

Cases should include prompts where:

- sample/population status is genuinely unspecified;
- weighted-mean weights are missing or ambiguous;
- correlation vectors are mismatched or incomplete;
- a requested method is outside the selected slice.

The expected behavior is not always an ExactScope call. A correct model/host may ask for clarification or preserve an unsupported/ambiguous state. The adapter must not choose semantics on its behalf.

## 4. Model-facing surface

The flagship combined profile should expose at most two top-level tools in the normal hot path:

```text
xs_calc   # bounded generic arithmetic, plan-v0.1
xs_eval   # exactly the selected statistics semantic operations
```

`xs_find` is disabled in the normal serving benchmark profile.

The Statistics `xs_eval` enum should contain only the eight selected operation keys. The model should not see economics operations or a full academic catalog.

The current draft profile example is [`../spec/examples/statistics-capability-profile.json`](../spec/examples/statistics-capability-profile.json).

## 5. Model-difficulty budget

The first profile should be held to an explicit weak-model budget. Initial design ceilings in the draft profile are:

| Property | Draft ceiling |
|---|---:|
| model-visible top-level tools | 2 |
| semantic operations | 8 |
| normal model turns | 1 |
| `xs_calc` plan steps | 8 |
| Tiny JSON request bytes | 512 |
| prompt fragment | 1,024 bytes |
| tool/schema asset | 4,096 bytes |
| grammar asset | 4,096 bytes |
| generated request tokens | 256 |

These are design ceilings, not measured claims. Tokenizer-specific prompt token counts must be recorded for every benchmarked model family.

A later slice may use different ceilings, but widening the limits requires measured evidence that capability gain outweighs the model-interface cost.

## 6. Benchmark corpus design

The first controlled benchmark should be reproducible, license-clean, and deliberately bounded to the capability claim.

Recommended initial target: **240 cases**, all generated from checked-in templates/seeds or otherwise redistributed under a clear compatible license.

Suggested balance:

| Family | Cases |
|---|---:|
| S1 descriptive aggregation | 40 |
| S2 weighted mean | 40 |
| S3 variance method selection | 50 |
| S4 standard-deviation method selection | 40 |
| S5 Pearson correlation | 40 |
| S6 ambiguity/negative cases | 30 |
| **Total** | **240** |

This count is a benchmark design target, not a product metric. It may change before freezing if coverage analysis shows obvious imbalance.

### Case difficulty tiers

Within positive task families, include multiple presentation styles:

1. **direct** — values and method are explicit in one sentence;
2. **light extraction** — values are embedded in prose/table-like text;
3. **distractor** — irrelevant numbers are present;
4. **method distinction** — sample/population or weighted/unweighted wording is the critical decision;
5. **multi-sentence** — relevant values and method cues are separated without requiring outside knowledge.

The benchmark must not require OCR, live retrieval, or broad domain knowledge to answer the quantitative task. Those would measure capabilities ExactScope does not claim to provide.

## 7. Golden construction

Every case must contain machine-readable gold data separate from model output:

- task-family ID;
- expected supported/ambiguous state;
- expected semantic operation when applicable;
- exact argument vectors/order;
- deterministic ExactScope expected result or expected typed failure;
- template/source identity;
- generation seed where generated;
- case revision.

Before model evaluation, every supported gold call must execute through the actual ExactScope artifact and match the stored expected result. No model answer may influence compatibility selection or gold generation.

## 8. Five required benchmark arms

For the same prompt corpus and model configuration, compare:

| Arm | Surface | Purpose |
|---|---|---|
| A | model only | baseline capability and wrong-number behavior |
| B | model + `xs_calc` only | isolates generic exact arithmetic value |
| C | model + Statistics semantic slice only | isolates reviewed domain-method value |
| D | model + `xs_calc` + Statistics slice | target combined product profile |
| E | larger-model reference | measures the capability gap that might otherwise motivate a model/hardware upgrade |

Arm E is used only where the reference model meaningfully outperforms the small-model baseline and can be evaluated fairly. It does not need to fit the original device; its deployment cost must be reported separately.

## 9. Target model classes

The first public flagship matrix should cover multiple weak-model classes rather than one favorable model:

- approximately 0.5B-0.8B;
- approximately 1B;
- approximately 1.5B-2B;
- approximately 3B;
- optional sub-0.5B stress model;
- at least one larger-model reference where fair.

Exact model revision, quantization, tokenizer, context, runtime revision, prompt, grammar/schema, sampling, thread count, and hardware must be immutable benchmark metadata.

## 10. Required quality metrics

Report per arm and task family:

- correct usable answer rate;
- incorrect numeric answer rate;
- unsupported/clarification-preserved rate for S6;
- tool-use recognition;
- `xs_calc` plan or `xs_eval` operation selection accuracy;
- argument extraction/order accuracy;
- structural validity;
- ExactScope accepted/rejected call rate;
- result fidelity;
- failure fidelity;
- tool penalty: model-only correct but tool path incorrect.

Do not hide these behind one aggregate accuracy number.

## 11. Required model-difficulty metrics

For every model/profile combination record:

- model-visible tool count;
- semantic operation count;
- prompt fragment bytes and tokenizer-specific tokens;
- tool/schema bytes;
- grammar bytes;
- generated tool-call/request tokens;
- model inference turns;
- plan steps where `xs_calc` is used;
- structural valid-call rate;
- core accepted-call rate;
- correct plan/operation selection rate;
- argument extraction rate;
- result/failure fidelity.

This is essential because a larger semantic catalog can increase model difficulty even if runtime bytes barely change.

## 12. Required device/resource metrics

Record at least:

- exact artifact bytes;
- marginal bytes added by the Statistics slice/profile;
- resident memory;
- ExactScope scratch/context bytes;
- end-to-end latency;
- model latency separately;
- ExactScope execution latency separately;
- energy per successful task where a real target can measure it;
- Wasm imports/memory pages for the no-import profile.

Desktop measurements remain desktop validation. Real-device claims require a named physical target.

## 13. Capability-density report

For every profile, publish raw values first and then useful ratios such as:

```text
correct-answer uplift / 100 KiB added artifact
wrong-number reduction / 100 KiB added artifact
correct-answer uplift / added prompt token
correct-answer uplift / added millisecond
correct-answer uplift / added resident-memory KiB
correct-answer uplift / joule       # only when measured
```

A high ratio created by a tiny absolute gain must not be presented without the raw absolute gain.

## 14. Capability Recovery Ratio

Where Arm E beats Arm A, compute the task-family-specific Capability Recovery Ratio:

```text
CRR = (D - A) / (E - A)
```

where the score is the predeclared primary successful-answer metric for that benchmark slice.

Report CRR together with:

- A, D, and E raw scores;
- ExactScope artifact/RAM/token/latency/energy cost;
- larger-model storage/RAM/latency/energy cost where measurable;
- the exact task family/corpus scope.

A CRR near or above 1 on a narrow deterministic task does **not** mean the small model is generally equivalent or superior to the larger model.

## 15. Internal product gates

The first Statistics slice should not be promoted from design/evaluation to a benchmarked capability profile until:

1. the corpus/gold generator is checked in and reproducible;
2. all supported gold calls pass through the actual ExactScope artifact;
3. multiple constrained model classes show a material useful-answer improvement or a material wrong-number reduction;
4. tool penalty and rejected-call rates remain acceptable and fully reported;
5. the Statistics semantic arm demonstrates value beyond `xs_calc` alone on method-sensitive tasks;
6. model-difficulty budgets are met or explicitly revised with evidence;
7. the marginal binary/RAM/token/latency cost remains small enough to preserve the retrofit thesis;
8. capability-density data is published with raw values;
9. CRR is published where a meaningful larger-model reference exists;
10. the profile, model assets, benchmark mapping, and results are digest-bound.

The previously discussed +10 percentage-point supported-slice improvement and 30% relative wrong-number reduction remain useful internal reference thresholds, not public promises or universal pass criteria.

## 16. What this proof should answer

The flagship result should let a device/AI team answer four practical questions:

1. **Can my small model reliably invoke this Statistics capability?**
2. **Does the reviewed semantic slice add value beyond generic exact arithmetic?**
3. **What flash/RAM/token/latency/energy cost buys that gain?**
4. **How much of the measured larger-model advantage does this tiny software slice recover?**

If those answers are weak, ExactScope should improve the slice/interface/evidence before expanding the domain catalog.
