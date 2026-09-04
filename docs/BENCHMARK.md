# ExactScope benchmark contract

ExactScope must earn adoption with measured evidence, not with the claim that deterministic code is obviously better than model arithmetic.

The core product question is:

> For small and on-device models, does ExactScope increase successful quantitative-task accuracy enough to justify its integration cost while reducing or preserving tokens, latency, memory, and energy?

## 1. Required comparison arms

Every published benchmark must separate at least four paths:

| Arm | Description |
|---|---|
| A | model-only quantitative reasoning |
| B | model + ExactScope **direct hot path** (`xs_eval` with known/cached operation key) |
| C | model + ExactScope **discovery path** (`xs_find` then `xs_eval`) |
| D | model + ExactScope direct hot path with constrained decoding/generated grammar |

Arm B is the primary product path. Arm C measures the cold-path cost of discovery. Arm D measures how much invalid-call failure can be removed without weakening core semantics.

## 2. Model classes

The first public evidence set should include:

- at least one sub-1B local model capable of constrained structured output;
- at least one 1B-2B model;
- at least one roughly 3B-class local model;
- optionally one routing/tool-specialized tiny model.

Model name, exact revision, quantization, context size, inference runtime, hardware, thread count, prompt, grammar, and sampling configuration must be recorded.

## 3. Workload classes

The first benchmark should deliberately use a small reviewed operation hot set before testing the full catalog.

Required domains:

- `math-basic` high-frequency arithmetic/ratio/percentage operations;
- `statistics-core` scalar and bounded vector tasks;
- `econ-undergrad` explicit textbook formula tasks.

Each item must contain:

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
2. **operation selection** — did it choose the correct canonical method/key?
3. **argument extraction** — were the correct values captured in the correct order?
4. **tool-call validity** — was the request syntactically valid for the adapter/grammar?
5. **core acceptance** — did strict validation accept the call?
6. **final answer accuracy** — was the final reported result correct?
7. **result fidelity** — did the model preserve the returned value/classification instead of recomputing it?
8. **failure fidelity** — did ambiguity/invalid input remain an error instead of becoming a fabricated number?
9. **successful-answer rate** — fraction of tasks that produce a correct usable answer, not merely a refusal/error.

This split is required to test the central tradeoff of the fail-closed design: whether fewer wrong numbers outweigh any increase in rejected calls.

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

## 7. Hot-set experiment

For each model class, compare at least:

- no catalog hints;
- an 8-operation generated hot set;
- a 16-operation generated hot set;
- a 32-operation generated hot set;
- discovery fallback enabled versus disabled.

Measure prompt growth, operation-selection accuracy, invalid-call rate, and latency. The full 99-operation catalog must not be embedded in the tiny-model prompt by default.

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

## 9. Claim policy

Until the benchmark exists, public documentation may say:

- ExactScope performs deterministic quantitative operations outside the model;
- the architecture is intended to reduce arithmetic burden and make results reproducible;
- direct hot-path integration avoids a required discovery turn for known operations.

It must **not** claim a measured model-accuracy, latency, token, or energy improvement without corresponding evidence.

## 10. Product decision rule

The first product milestone is not 99 implemented operations. It is a small reviewed hot set that produces a convincing measured result.

A useful v0.1 proof should answer:

> On at least one constrained local model, does the direct ExactScope path materially improve successful quantitative-task accuracy without unacceptable latency, invalid-call, memory, or energy cost?

If the answer is no, operation breadth and platform breadth should not be expanded merely to make the project look complete.
