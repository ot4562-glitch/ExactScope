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

`exactscope-packc hotset` now consumes reviewed scope-pack source, compiles it through the canonical pack compiler, and emits a digest-bound 1-32 operation hot set. Production hot sets should normally use 8-32 operations; smaller sets such as `p0-smoke` are permitted as reproducibility/conformance fixtures.

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

Implemented now:

- generated direct-eval GBNF;
- optional discovery GBNF generation;
- compact system/tool prompt fragment;
- OpenAI-compatible server-style reference runner;
- strict returned-tool-call validation against the bound hot set;
- offline synthetic envelope self-test in CI;
- hot-set binding digest/revision propagation.

Still required for benchmark completion:

- recorded runs against selected small GGUF models;
- benchmark configuration/results for those model revisions;
- additional raw/tag-wrapped model-template fixtures where they materially improve compatibility.

The primary example does not require `xs_find` before every calculation.

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
