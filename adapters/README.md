# Adapter policy

Adapters connect AI runtimes and host platforms to the same ExactScope core. They are convenience/compatibility layers, never calculation authorities.

## 1. Product priority

The adapter goal is not “support every host.” It is to expose the smallest reliable AI-facing surface for the selected capability:

```text
small local model
  -> xs_calc for short arithmetic
  -> compact xs_eval capability slice for reviewed methods
  -> ExactScope
  -> deterministic result / explicit failure
```

`xs_find` remains an optional cold/development fallback for unknown semantic operations.

The adapter roadmap therefore prioritizes:

1. bounded `xs_calc` tool/schema/GBNF assets;
2. generated capability-slice/hot-set metadata for `xs_eval`;
3. minimal prompt/tool surfaces for weak models;
4. llama.cpp reference integration and benchmark fixtures;
5. digest-bound model-difficulty/evidence metadata;
6. platform wrappers after product proof.

## 2. Implemented integration reference

### `wearable`

[`wearable/`](wearable/) is an implemented C99/C++11-oriented reference host for constrained edge/wearable integration. It demonstrates bounded memory, frozen registry lifecycle, update/rollback patterns, and privacy-minimized telemetry.

It is not generic “smart-glasses support” and is not the primary proof-of-value adapter for the product. Real device support still requires the actual host loading boundary and qualification evidence.

## 3. Generated semantic-slice assets

`exactscope-packc hotset` consumes reviewed scope-pack source, compiles it through the canonical pack compiler, and emits a digest-bound 1-32 operation selection. This remains useful machinery for a semantic capability slice, but **8-32 is not a product rule**. The selected operation count should be the smallest set that covers the target task families under the model/device budget; tiny fixtures such as `p0-smoke` remain valid for reproducibility/conformance.

Generated outputs:

```text
adapters/generated/<hotset>/
  catalog.json
  binding-sha256.txt
  xs-eval.tool.json
  xs-eval.gbnf
  prompt-fragment.txt
  xs-find.tool.json       # only when include_find=true
  xs-find.gbnf            # only when include_find=true
```

The hot set contains only selection/integration metadata. It never duplicates formulas.

## 4. OpenAI-compatible protocol assets

The generic protocol layer now has two compact one-hop surfaces:

- bounded `xs_calc` tool definition + JSON Schema/GBNF for short arithmetic;
- conservative `xs_eval` tool definition for the selected semantic capability slice;
- optional `xs_find` fallback definition outside the normal hot path;
- compact slice hints/prompt fragment;
- valid/error response fixtures;
- exact decimal preservation;
- no calculation logic.

“OpenAI-compatible” is a protocol-envelope target, not a cloud dependency.

## 5. llama.cpp

Implemented references now cover both lanes:

- `adapters/llama-cpp/` for direct semantic `xs_eval` integration;
- `examples/llama.cpp/` for one-turn bounded `xs_calc` generation/execution;
- generated GBNF/tool assets and compact prompt fragments;
- strict returned-call/plan validation with no semantic repair;
- hot-set/profile identity propagation where applicable;
- a recorded five-case three-model `xs_calc` integration smoke.

Still required for product benchmark completion:

- larger reproducible task-family runs across the target 0.5B-3B classes;
- the Statistics capability-slice arms defined in the benchmark contract;
- larger-model reference comparisons where fair;
- exact model-difficulty, resource-cost, capability-density, and CRR records.

Neither primary lane requires `xs_find` before every calculation.

## 6. Secondary adapters

### Android

AAR/Prefab plus thin JNI/Kotlin wrapper after the product proof. Direct buffers/status transport only; no formulas or semantic repair.

### MCP

Optional desktop/server bridge. Useful interoperability, but not part of the minimum runtime or benchmark proof.

### Apple/Swift and other wrappers

Thin C ABI wrappers only, prioritized by real adoption needs.

## 7. Non-negotiable rules

An adapter must not:

- maintain a divergent formula catalog;
- calculate or reclassify results;
- use binary float in a way that changes exact decimal values;
- invent omitted values;
- silently convert units/currencies/rates;
- choose an ambiguous method;
- convert core errors into numeric answers;
- require network access for core operation;
- put the entire operation catalog into a tiny model prompt by default;
- claim compatibility without fixtures/evidence.

## 8. Allowed normalization

An adapter may normalize syntax/transport when semantics are unchanged:

- unwrap outer tool-call envelopes;
- trim protocol whitespace;
- map known field names;
- preserve/canonicalize exact decimal lexical forms where lossless;
- enforce request/array limits;
- cache immutable operation metadata by digest;
- render the returned deterministic result.

It may not perform semantic repair.

## 9. Compatibility test matrix

Every shipped adapter should test:

- direct known operation;
- cached/bound operation;
- optional discovery fallback;
- unknown operation;
- ambiguity preservation;
- missing/wrong-order arguments;
- exact large decimal preservation;
- invalid lexical input;
- core domain/overflow/status mapping;
- provenance preservation;
- buffer/response limits;
- registry/hot-set digest mismatch;
- no hidden recalculation.

## 10. Small-model prompt budget

Measure adapter prompt/tool cost.

Current product targets:

- one bounded `xs_calc` tool for generic short arithmetic;
- one compact `xs_eval` tool for the selected semantic capability slice;
- optional `xs_find` fallback outside the normal hot path;
- no full domain catalog in the prompt;
- the smallest semantic operation selection that covers the target task families;
- compact prompt/schema/grammar assets with explicit byte/token budgets;
- discovery result caps where discovery is enabled.

Prompt growth, tool/operation-selection accuracy, invalid/accepted-call rate, argument extraction, result fidelity, and inference turns belong in the model-difficulty benchmark.

## 11. Benchmark responsibility

Adapters are part of the product claim and therefore must record the exact capability-profile/hot-set, tool/schema/grammar/prompt, and runtime artifact identities in benchmark outputs.

See [`../docs/BENCHMARK.md`](../docs/BENCHMARK.md).
