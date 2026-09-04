# Adapter policy

Adapters connect AI runtimes and host platforms to the same ExactScope core. They are convenience/compatibility layers, never calculation authorities.

## 1. Product priority

The first adapter goal is no longer “support every host.” It is:

```text
small local model
  -> generated hot-set/direct xs_eval
  -> ExactScope
  -> deterministic result
```

`xs_find` remains an optional fallback for unknown operations.

The adapter roadmap therefore prioritizes:

1. generated hot-set metadata;
2. OpenAI-compatible direct-eval tool assets;
3. GBNF;
4. llama.cpp reference integration;
5. benchmark fixtures;
6. platform wrappers after product proof.

## 2. Implemented integration reference

### `wearable`

[`wearable/`](wearable/) is an implemented C99/C++11-oriented reference host for constrained edge/wearable integration. It demonstrates bounded memory, frozen registry lifecycle, update/rollback patterns, and privacy-minimized telemetry.

It is not generic “smart-glasses support” and is not the primary proof-of-value adapter for the product. Real device support still requires the actual host loading boundary and qualification evidence.

## 3. P0 — generated hot-set assets

A hot-set generator should consume installed operation metadata and produce a bounded 8-32 operation product subset tied to the registry/pack digest.

Expected generated outputs:

```text
adapters/generated/<hotset>/
  catalog.json
  registry-digest.txt
  xs-eval.tool.json
  xs-eval.gbnf
  prompt-fragment.txt
  optional-xs-find.tool.json
  optional-xs-find.gbnf
```

The hot set contains only selection/integration metadata. It never duplicates formulas.

## 4. P0 — OpenAI-compatible protocol assets

The first generic protocol adapter should demonstrate direct one-hop evaluation.

Deliverables:

- conservative `xs_eval` tool definition;
- optional `xs_find` fallback definition;
- compact hot-set hints;
- valid/error response fixtures;
- exact decimal preservation;
- no calculation logic.

“OpenAI-compatible” is a protocol-envelope target, not a cloud dependency.

## 5. P0 — llama.cpp

Deliverables:

- direct-eval GBNF;
- optional discovery GBNF;
- compact system/tool prompt fragment;
- OpenAI-compatible, raw JSON, and common tag-wrapped fixtures;
- one runnable in-process or server-style reference integration;
- benchmark configuration for selected small GGUF models;
- hot-set digest binding.

The primary example must not require `xs_find` before every calculation.

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

Initial design targets:

- direct `xs_eval` tool asset as primary;
- optional `xs_find` fallback;
- no full catalog in prompt;
- 8-32 operation generated hot set;
- compact prompt fragment;
- discovery result cap where discovery is enabled.

Prompt growth, operation-selection accuracy, invalid-call rate, and number of inference turns belong in the benchmark.

## 11. Benchmark responsibility

Adapters are part of the product claim and therefore must record their exact schema/grammar/hot-set digest in benchmark outputs.

See [`../docs/BENCHMARK.md`](../docs/BENCHMARK.md).
