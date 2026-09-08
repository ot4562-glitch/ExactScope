# ExactScope rc4 model-interface architecture

Status: **active quantitative-subsystem model-interface design; no longer the flagship rc4 product path**

This document defines the rc4 model-facing contract for quantitative `xs_calc`/`xs_eval` calls. The flagship everyday factual path now uses host-side grounding prefetch and normally requires no model-visible retrieval/tool envelope; see [`GROUNDING_ARCHITECTURE.md`](GROUNDING_ARCHITECTURE.md) and [`../spec/GROUNDING_CONTRACT_V0_1.md`](../spec/GROUNDING_CONTRACT_V0_1.md). This document remains the product response to the closed rc3 tool-interface findings for tasks that still require a model-generated quantitative request.

## 1. Goal

ExactScope should improve quantitative reliability for small/local models without requiring every model/runtime combination to implement the same OpenAI-style tool-call protocol.

The model's normal job is deliberately narrow:

1. decide whether the request belongs to a bound deterministic capability;
2. select the reviewed operation or bounded arithmetic lane;
3. extract exact input values in the declared order;
4. emit one constrained request or an explicit no-call/failure sentinel.

ExactScope performs the actual deterministic calculation and returns a typed result/error.

## 2. Two envelopes, one semantic contract

A capability may be presented through two model envelopes:

### Native tools

Use only when the runtime proves that the active chat template supports the required tool protocol.

The native path may expose:

- one compact `xs_eval` tool for reviewed semantic methods;
- optionally one compact `xs_calc` tool for bounded generic arithmetic.

Native tools are an optimization. They are not a required capability dependency.

### Constrained request JSON

Every shipped AI-facing capability must also contain a model-agnostic constrained request surface:

- `constrained-prompt.txt`;
- `xs-request.gbnf`;
- the same exact capability catalog/profile/runtime identity used by the native path.

The initial rc4 constrained wire shapes are intentionally tiny:

```json
{"op":"stats.mean","a":[["2","4","6"]]}
```

```json
{"p":[{"o":"add","a":["2","3"]}]}
```

```json
{"n":true}
```

`{"n":true}` means the model is not making a valid deterministic call. It is the fail-closed lane for missing information, unsupported requests or ambiguity. It does not authorize the host to guess or repair semantics.

## 3. Automatic envelope selection

A maintained runtime adapter may expose `auto`, `native_tools`, and `constrained_json` modes.

`auto` must be deterministic and inspect runtime capability metadata before inference. For llama.cpp-compatible runtimes, native tools require at least:

- tool definitions are supported by the active chat template;
- assistant tool calls are supported;
- object arguments are supported.

If those conditions are not all proven, `auto` selects `constrained_json`.

An explicit `constrained_json` request does not depend on native-tool capability and therefore does not require a live `/props` probe. This is useful for fixed integrations and no-model package smoke tests. `auto` and `native_tools` do require the pre-inference runtime capability record.

No score, expected benchmark answer, model family name or task-specific heuristic may influence this selection. The requested/resolved interface must always be frozen into benchmark/reproducibility evidence before inference; when runtime metadata participates in selection, that normalized capability/template identity must be frozen too.

## 4. Surface-size rule

The default small-model surface is the smallest product-realistic slice that covers the target task family.

Do not expose a full catalog merely because it exists.

The preferred ordering is:

1. one task-family-specific semantic slice;
2. optional bounded `xs_calc` only when the product genuinely needs generic arithmetic;
3. cold/development discovery outside the normal serving path.

Operation routing may be implemented as a genuine product component only if it uses request/domain context available in production. It may not use benchmark labels, expected operations or answers.

## 5. Fail-closed boundary

Allowed normalization is syntactic only:

- tool-envelope translation;
- whitespace normalization;
- canonical JSON parsing;
- exact decimal lexical normalization that preserves value;
- fixed mapping from a compact bound identifier to the exact operation bound in the capability.

Forbidden semantic repair includes:

- choosing sample vs population without an explicit request;
- guessing a percent-vs-ratio interpretation;
- inventing units, currencies or conversions;
- filling missing operands;
- changing an operation because another one would produce a plausible answer;
- evaluating model-generated arbitrary code.

## 6. Identity and versioning

The model-facing surface is part of the product artifact and must be byte-bound.

The capability model-surface contract must bind, when present:

- `prompt-fragment.txt`;
- `xs-eval.tool.json`;
- `xs-eval.gbnf`;
- `xs-calc.tool.json`;
- `xs-calc.gbnf`;
- `constrained-prompt.txt`;
- `xs-request.gbnf`.

A change to any prompt, grammar, tool schema, visible operation set, runtime artifact, adapter selection rule or request validator creates a new candidate identity for benchmark purposes.

## 7. Efficiency KPIs

For each model/candidate, report:

- model-only correctness;
- ExactScope correctness;
- correctness uplift;
- mean/median input tokens;
- mean output tokens;
- model latency;
- deterministic-core latency;
- fixed prompt/schema/grammar bytes;
- malformed/rejected request rate;
- operation and argument extraction accuracy.

Derived metrics:

```text
uplift_per_added_token = correctness_uplift / max(1, interface_input_tokens - model_only_input_tokens)

uplift_per_added_byte = correctness_uplift / max(1, model_surface_bytes)

uplift_per_added_model_ms = correctness_uplift / max(1, interface_model_latency_ms - model_only_model_latency_ms)
```

The metrics are diagnostic ratios, not universal quality scores. A negative denominator or negative uplift must be reported rather than hidden.

## 8. Product success criterion

rc4 succeeds only if the integration surface becomes both more portable and cheaper to drive from small models.

The desired behavior is:

```text
small model
  -> short structured request
  -> strict validator
  -> ExactScope deterministic core
  -> typed result
```

rather than:

```text
small model
  -> very large generic tool schema
  -> model-specific chat-template behavior
  -> fragile tool-call parsing
  -> deterministic core
```

Native tools remain valuable where they are genuinely supported. Constrained JSON is the compatibility baseline that prevents the product from depending on one model-family tool protocol.
