# ExactScope benchmark contract

ExactScope must earn adoption with measured evidence, not with the claim that deterministic code is obviously better than model arithmetic.

The core product question is:

> **For an existing constrained on-device model, can a tiny ExactScope software addition remove enough quantitative error at sufficiently low binary, RAM, token, latency, energy, integration, and qualification cost that the existing hardware remains useful for capabilities that would otherwise push toward a larger model or newer device?**

The flagship comparison is therefore **small model vs small model + ExactScope**, with a larger-model reference arm added when that larger model can be run fairly on the benchmark hardware. The larger-model arm is not required to fit the target device; it represents the capability pressure that an OEM might otherwise answer with new hardware.

## 1. Required comparison arms

### 1.1 vNext generic arithmetic proof

Once the planned bounded-plan path exists, public numerical-reasoning benchmarks should separate:

| Arm | Description |
|---|---|
| A | model-only quantitative reasoning |
| B | model -> unconstrained `xs_calc` plan -> ExactScope |
| C | model -> constrained `xs_calc` plan -> ExactScope |
| D | gold plan -> ExactScope deterministic ceiling |
| E | optional larger-model reference under separately reported deployment cost |

Arm C is the target retrofit path for ordinary short arithmetic. Arm D is not a model score; it verifies that the supported dataset slice can be represented and executed correctly by ExactScope. Arm E answers the product question "how much of a model/hardware upgrade can this tiny software addition avoid?"

### 1.2 Semantic-operation proof

For reviewed semantic operations, retain the existing comparison shapes when appropriate:

- model only;
- direct `xs_eval` hot path;
- constrained direct `xs_eval`;
- optional `xs_find -> xs_eval` cold-path measurement.

Discovery is measured as a fallback cost, not promoted as the main tiny-model product path.

## 2. Model classes

The first public retrofit evidence set should include:

- at least one approximately 0.5B-0.8B local model;
- at least one approximately 1B model;
- at least one approximately 1.5B-2B model;
- at least one roughly 3B-class local model;
- stress models below the main target range when useful;
- an optional larger-model reference where hardware permits.

The core product claim should be supported across multiple model families rather than one unusually tool-capable model.

Model name, exact revision, quantization, context size, inference runtime, hardware, thread count, prompt, schema/grammar, sampling configuration, reasoning mode, and generation-token budget must be recorded.

## 3. Workload classes

The vNext proof has two distinct workload classes.

### 3.1 Public bounded-plan numerical reasoning

Use public datasets with gold programs, derivations, or metadata that permit deterministic compatibility selection without consulting model outputs. Priority candidates include FinQA and TAT-QA, followed by other reproducibly mappable numerical reasoning sets.

For every published ExactScope-compatible subset:

- selection must come from gold program/derivation/metadata, never model answers;
- a converter must produce a bounded ExactScope plan;
- that plan must execute to the dataset gold result before the item is admitted;
- coverage percentage against the full published split must be reported;
- unsupported items remain in the full model-only benchmark and are not silently removed from the dataset's official score;
- a subset score must be labeled as an `ExactScope-compatible subset`, never as the full official dataset score.

### 3.2 Reviewed semantic-operation workloads

Retain focused `math-basic`, `statistics-core`, `econ-undergrad`, and later domain-pack corpora for method-selection and semantic validation.

Each semantic item must contain:

- the user-facing prompt;
- the expected operation key/method;
- expected argument values and order;
- the deterministic expected result;
- whether the item should fail because information is missing or ambiguous;
- domain/method metadata.

## 4. Stage-level metrics

Do not publish one blended accuracy score without the failure breakdown.

Measure separately:

1. **tool-use recognition** — did the model recognize a supported deterministic calculation?
2. **plan/operation selection** — did it choose the right bounded arithmetic structure or reviewed semantic method?
3. **argument extraction** — were the correct values captured with correct identity/order/reference relationships?
4. **tool/plan syntax validity** — was the request syntactically valid for the adapter/schema/grammar?
5. **plan semantic validity** — were step references, arity, operation limits, and resource bounds valid?
6. **core acceptance** — did strict validation accept the request?
7. **final answer accuracy** — was the final reported result correct?
8. **result fidelity** — did the model preserve the returned value/classification instead of recomputing it?
9. **failure fidelity** — did ambiguity/invalid input remain an error instead of becoming a fabricated number?
10. **successful-answer rate** — fraction of tasks that produce a correct usable answer, not merely a refusal/error.
11. **incorrect numeric answer rate** — fraction that returns a plausible but wrong number.
12. **tool penalty rate** — fraction where model-only was correct but the ExactScope path became incorrect because recognition, extraction, plan formation, or tool use regressed the answer.

This split is required to test the central tradeoff of the fail-closed design: whether fewer wrong numbers outweigh any increase in rejected calls, and whether the tool layer introduces regressions on tasks the model already solved correctly.

## 5. Cost metrics

Measure:

- prompt tokens;
- completion/tool-call tokens;
- number of model inference turns;
- end-to-end latency;
- ExactScope compute latency separately;
- cold discovery latency separately;
- resident artifact bytes;
- context bytes;
- evaluation scratch bytes;
- vector transport scratch/copy bytes;
- peak host memory where measurable;
- energy per successful task where measurable.

The direct hot path must be reported separately from the two-hop discovery path because the latter can add a full model turn.

## 6. Fail-closed experiment

A dedicated benchmark subset must test malformed but recoverable-looking model outputs.

Measure at least:

- extra whitespace;
- outer envelope variations;
- JSON number versus exact decimal string where exact lexical preservation is possible;
- missing arguments;
- swapped arguments;
- percent-versus-ratio ambiguity;
- unit-bearing values;
- wrong operation method;
- unsupported operation;
- zero denominator/domain failures.

Adapters may repair syntax only according to the AI integration contract. Semantic repair is forbidden.

Report:

```text
invalid call rate
adapter-normalized rate
core-rejected rate
correct answer rate
incorrect numeric answer rate
```

The benchmark must make visible whether ExactScope merely moves errors from arithmetic to tool-call formation.

## 7. Model-surface experiment

The vNext design should compare the cost of different model-facing surfaces rather than assuming a catalog is always best.

For generic arithmetic, compare where useful:

- model-only reasoning;
- one unconstrained `xs_calc` plan schema;
- one constrained `xs_calc` plan grammar;
- equivalent multi-tool/per-operation exposure only as an ablation if needed.

For semantic methods, compare compact 8/16/32-operation `xs_eval` hot sets and optional discovery fallback.

Measure prompt growth, plan/operation-selection accuracy, invalid-call rate, output-token tails, and latency. The full academic catalog must not be embedded in a tiny-model prompt by default.

## 8. Reproducibility

A public benchmark result must identify:

- ExactScope source commit and release artifact digest;
- core/ABI version;
- pack ID/version/digest and operation revisions;
- adapter schema/GBNF digest;
- benchmark dataset revision;
- model/runtime/hardware configuration;
- raw per-item results or an equivalent machine-readable artifact;
- aggregation script/version.

Published comparative claims must be reproducible from these records.

### Current harness state

`benchmarks/run_benchmark.py` currently implements the **existing semantic-operation** four-arm shapes and writes per-item JSONL plus a digest-bound summary. `crates/exactscope-conformance/src/bin/exactscope-core.rs` bridges benchmark calls into the real bounded Tiny JSON adapter instead of duplicating calculation logic. The offline self-test covers executable economics/statistics cases through the current core bridge.

The current mixed benchmark/evaluation selection is `hotsets/quant-core-16.json`, with focused economics/statistics hot sets retained separately. This remains useful implementation evidence for the semantic lane.

The planned `xs_calc` public-benchmark path described in this document is **not implemented in the repository yet**. Development experiments and planning observations must not be represented as stable public benchmark claims until their raw artifacts, mapping logic, and aggregation are checked in or otherwise published reproducibly.

## 9. Claim policy

Public documentation may say:

- ExactScope already performs bounded deterministic quantitative operations outside the model;
- the vNext architecture targets a tiny on-device capability retrofit using one bounded arithmetic plan plus reviewed semantic operations;
- native static C ABI and no-import Wasm are the intended primary deployment shapes;
- the product is designed to make a small-model quantitative capability upgrade cheaper than a model/hardware jump.

It must **not** claim proven hardware-life extension, accuracy improvement, latency savings, token savings, energy savings, or larger-model equivalence without corresponding reproducible evidence.

Development-only results may guide architecture but must be clearly labeled and excluded from public headline claims until reproducibility requirements are met.

## 10. Product decision rule

The first product milestone is not 99 implemented operations or a large academic catalog. It is a convincing **retrofit proof**.

A useful v0.1 proof should answer:

> On multiple constrained 0.5B-3B models, does the bounded ExactScope path materially reduce quantitative error while adding so little binary/RAM/latency/energy cost that keeping the existing model/hardware becomes a credible product option?

Where feasible, also ask:

> How does small model + ExactScope compare with a larger-model reference, and what capability is recovered per byte/millisecond/joule of added cost?

If the answer is no, domain/catalog/platform breadth should not be expanded merely to make the project look complete.
