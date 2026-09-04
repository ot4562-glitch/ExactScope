# AI integration contract

ExactScope is consumed by AI runtimes. This document defines the model-facing behavior that product integrations should optimize for.

## 1. Direct evaluation is the default hot path

The recommended steady-state interaction is one model turn followed by one deterministic call:

```text
model
  -> xs_eval(op,args)
  -> ExactScope result
```

`xs_find` exists as a fallback for an unknown operation. It is **not** a mandatory first step.

A host should preload or generate a compact hot set and bind each key to the installed registry/pack digest. Successful discovery can also be cached against that digest.

```text
cold path:
model -> xs_find -> bind/cache -> xs_eval

hot path:
model ---------------------> xs_eval
```

If the registry digest or operation revision changes, the host invalidates and regenerates the binding.

## 2. Model-facing surface

The logical surface still contains only two generic functions:

- `xs_eval` — primary direct evaluation path;
- `xs_find` — optional discovery fallback.

Do not expose hundreds of independent per-formula tools by default. Large tool catalogs increase prompt cost and selection errors.

However, a product may generate a small 8-32 operation **hot-set hint/grammar** so the model can select canonical operation keys without discovery.

## 3. Canonical eval request

Logical form:

```json
{
  "op": "econ.cpi.inflation",
  "a": ["100", "103.2"]
}
```

The checked-in schema is [`spec/schemas/xs-eval-tool.schema.json`](../spec/schemas/xs-eval-tool.schema.json).

Decimal values are strings in the normative Tiny JSON profile so ordinary JSON parsers cannot silently round large/precise values before the core sees them.

## 4. Discovery request

Logical fallback:

```json
{
  "q": "midpoint price elasticity",
  "n": 3
}
```

The checked-in schema is [`spec/schemas/xs-find-tool.schema.json`](../spec/schemas/xs-find-tool.schema.json).

A successful response returns canonical operation metadata. The host should cache/bind the result rather than forcing discovery on every repeated task.

## 5. Hot-set artifact

The intended generator output is conceptually:

```text
hotset/
  catalog.json
  binding-sha256.txt
  xs-eval.tool.json
  xs-eval.gbnf
  xs-find.tool.json       # only when include_find=true
  xs-find.gbnf            # only when include_find=true
  prompt-fragment.txt
```

A hot-set entry contains only compact immutable metadata needed to select and call an operation:

- canonical key;
- compact signature;
- method cue when needed;
- argument semantic names/order;
- registry/pack digest binding;
- operation revision.

The complete pack catalog remains available to the host/tooling but should not be placed in a small-model prompt by default.

## 6. Model policy

A compact system/tool policy should communicate:

```text
Use ExactScope for supported deterministic quantitative calculations.
Prefer a known operation key from the provided hot set.
Call xs_eval directly when the operation is known.
Use xs_find only when the required operation key is unknown.
Pass arguments in the declared order.
Use exact base-10 values; never invent missing values or methods.
Do not recompute an ExactScope result.
Preserve ExactScope errors instead of guessing a number.
```

The prompt should not enumerate the full catalog.

## 7. Fail-closed and adapter normalization

The core stays strict for semantics. Adapters are permitted to normalize **syntax/transport**, not meaning.

### Allowed

- unwrap OpenAI-compatible/tag-wrapped/raw JSON envelopes;
- trim protocol whitespace;
- map known outer field names to the canonical schema;
- convert a host numeric token to an exact decimal lexical value only if the host representation preserves that exact value;
- enforce array/field caps;
- reorder protocol object fields without reordering operation arguments.

### Forbidden

- infer that `5%` should become `0.05` when the operation contract did not specify that conversion;
- remove currency/unit symbols and continue as if semantics were unchanged;
- invent a missing value;
- swap arguments based on a guess;
- choose a population method when the request implies sample data or vice versa;
- change an ExactScope error into a plausible numeric answer;
- calculate, round, convert, or classify independently of the core.

The benchmark must measure whether constrained decoding and syntactic normalization keep core-rejected calls low enough for real use.

## 8. Canonical decimal profile

Accepted lexical examples include:

```text
0
-12
12.50
0.05
1000000
1e-6
```

Rejected unless an outer adapter has an explicit lossless lexical normalization rule:

```text
1,000
5%
$12
NaN
Infinity
approximately 4
12 meters
```

Percent/rate/unit meaning belongs to the operation signature and semantic metadata, not to string guessing.

## 9. Adapter responsibilities

An adapter must:

- validate the model/tool envelope;
- cap request bytes and array lengths;
- preserve exact lexical values;
- resolve/bind operation keys against the installed registry;
- preserve operation argument order;
- preserve core status/provenance;
- avoid calculation and semantic repair;
- record or expose the registry/pack digest when auditability is required.

An adapter may:

- translate outer tool-call protocols;
- apply allowed syntax normalization;
- provide generated hot-set metadata;
- cache immutable operation metadata by digest;
- provide locale aliases before discovery;
- render a deterministic result after the core call.

## 10. OpenAI-compatible adapter target

The first generic adapter deliverables should be:

- conservative OpenAI-style `xs_eval` tool definition;
- optional `xs_find` definition;
- hot-set generation from installed operation metadata;
- examples for direct one-hop eval;
- fixtures for error/status preservation;
- no calculation logic.

Cloud use is not required. "OpenAI-compatible" describes a widely used tool-call envelope format.

## 11. llama.cpp target

The first local-runtime reference integration should provide:

- generated/checked-in GBNF for direct eval;
- optional discovery grammar;
- a compact prompt fragment;
- OpenAI-compatible, tag-wrapped, and raw JSON fixtures;
- a sample runner/configuration showing direct hot-set calls;
- benchmark integration with selected small GGUF instruct/tool models.

The grammar used for public benchmark claims must be checked in or reproducibly generated and digest-recorded.

## 12. TinyWire and typed hosts

TinyWire is the compact deterministic CBOR transport for scalar/vector calls where JSON is undesirable. Typed native hosts may bypass model-facing JSON entirely and call the C ABI directly.

A product with fixed operations may omit discovery and generic JSON from the runtime path completely.

## 13. Benchmark stages

The adapter benchmark separates:

1. recognition of a supported deterministic task;
2. operation selection;
3. argument extraction/order;
4. tool-call syntax validity;
5. core acceptance/rejection;
6. final answer accuracy;
7. result fidelity;
8. failure fidelity.

See [BENCHMARK.md](BENCHMARK.md).

## 14. Required comparison paths

Every serious evaluation should compare:

- model only;
- model + direct `xs_eval` hot path;
- model + `xs_find -> xs_eval` cold path;
- direct `xs_eval` with constrained decoding.

This prevents the two-hop discovery cost from being hidden inside the product claim.

## 15. Tiny-model acceptance cases

Before an adapter is considered usable, cover at least:

- known direct operation;
- cached/bound operation after prior discovery;
- unknown operation requiring discovery;
- discovery ambiguity;
- negative/decimal values;
- percentage versus ratio semantics;
- missing argument;
- wrong argument order;
- invalid lexical value;
- unsupported operation;
- domain/overflow error;
- exact result copied without model recomputation.

## 16. Human-facing surfaces

A host application may render, speak, or display results. That UI is outside ExactScope core. A wrapper must not become a second calculation authority.
