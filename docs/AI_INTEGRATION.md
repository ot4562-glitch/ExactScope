# AI integration contract

ExactScope is consumed by AI runtimes. This document defines the model-facing behavior that product integrations should optimize for.

## 1. Current interaction model

ExactScope exposes two implemented experimental model-facing lanes: bounded `xs_calc` for short arithmetic plans and direct `xs_eval` for reviewed semantic methods. Both are intentionally small and share the same deterministic core.

```text
                         model
                           |
               +-----------+-----------+
               |                       |
               v                       v
      short arithmetic plan     known semantic method
               |                       |
               v                       v
        xs_calc(plan)              xs_eval(op,args)
  IMPLEMENTED / EXPERIMENTAL     IMPLEMENTED / REVIEWED
               |                       |
               +-----------+-----------+
                           |
                           v
                    ExactScope result
```

`xs_find` remains an optional discovery/setup path for unknown semantic operations. It is not a mandatory first step and should not be required for ordinary arithmetic retrofit use.

## 2. Model-facing surface

The logical surface contains three roles, but a deployed product should expose only what it needs:

- `xs_calc` — implemented experimental one-call bounded arithmetic plan for generic short numerical execution;
- `xs_eval` — implemented direct evaluation for reviewed semantic operations;
- `xs_find` — optional cold/development discovery fallback.

For ordinary arithmetic, the design goal is **one compact plan tool**, not six independent arithmetic tools and not hundreds of per-formula tools.

For semantic methods, a product should expose only the selected **capability slice** through a compact `xs_eval` surface. The broad domain source catalog stays build-time/host-side and is not injected into a weak-model prompt.

Plan v0.1 is limited to at most eight steps over `add/sub/mul/div/powi/sqrt`, exact decimal-string leaves, and backward-only prior-result references. Loops, arbitrary branches, variables, arbitrary functions, and arbitrary code are forbidden. The plan layer lowers to the shared bounded core semantics.

## 3. Canonical eval request

Logical form:

```json
{
  "op": "econ.cpi.inflation",
  "a": ["100", "103.2"]
}
```

The checked-in schema is [`spec/schemas/xs-eval-tool.schema.json`](../spec/schemas/xs-eval-tool.schema.json).

Scalar decimal values and every decimal leaf inside a vector are strings in the normative Tiny JSON profile, so ordinary JSON parsers cannot silently round large/precise values before the core sees them. Vectors are arrays of those strings; nested vectors and JSON numbers are rejected.

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

## 5. Capability-slice model assets

The current hot-set generator is the starting point for capability-slice output. A production capability profile should bind the runtime surface and its model assets together:

```text
capability-slice/
  profile.json
  catalog.json
  binding-sha256.txt
  xs-calc.tool.json       # when xs_calc is enabled
  xs-calc.gbnf
  xs-eval.tool.json
  xs-eval.gbnf
  xs-find.tool.json       # only when include_find=true
  xs-find.gbnf            # only when include_find=true
  prompt-fragment.txt
```

The deployed slice contains only compact immutable metadata needed to select and call the supported capability:

- target task families;
- canonical operation keys and revisions;
- compact signatures/method cues;
- argument semantic names/order;
- registry/pack/profile digest bindings;
- model-surface and footprint budgets.

The complete domain source catalog remains available to build tooling but should not be placed in a small-model prompt by default.

## 6. Model policy

A compact system/tool policy should communicate:

```text
Use ExactScope for supported deterministic quantitative calculations.
Use xs_calc for supported short arithmetic plans.
Use xs_eval directly for a known reviewed semantic method in the bound capability slice.
Use xs_find only when the required semantic operation is genuinely unknown and discovery is enabled.
Pass arguments in the declared order and obey backward-reference rules.
Use exact base-10 values; never invent missing values, units, or methods.
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

## 10. OpenAI-compatible adapter surface

The current generic adapter surface should remain compact:

- conservative OpenAI-style `xs_calc` tool definition plus bounded JSON Schema/GBNF;
- conservative `xs_eval` definition for the selected capability slice;
- optional `xs_find` definition outside the normal hot path;
- capability-slice/hot-set generation from installed operation metadata;
- examples for one-turn bounded-plan and direct semantic eval;
- fixtures for error/status preservation;
- no calculation logic in the protocol wrapper.

Cloud use is not required. "OpenAI-compatible" describes a widely used tool-call envelope format.

## 11. llama.cpp reference

The repository now contains a one-turn `xs_calc` llama.cpp reference path and small multi-model smoke evidence. The reference surface includes:

- generated/checked-in GBNF for the bounded `xs_calc` plan;
- matching JSON Schema/tool asset;
- strict bounded request/runtime validation;
- compact system/user prompt policy;
- raw plan extraction without semantic repair;
- a sample runner showing one-turn bounded-plan use;
- preserved direct semantic `xs_eval` integration patterns;
- benchmark integration points for selected small GGUF instruct/tool models.

The current smoke is integration evidence, not a general model-quality benchmark. Any grammar/schema used for public benchmark claims must be checked in or reproducibly generated and digest-recorded together with exact model/runtime/prompt/artifact identities.

## 12. TinyWire and typed hosts

TinyWire is the compact deterministic CBOR transport for scalar/vector calls where JSON is undesirable. Typed native hosts may bypass model-facing JSON entirely and call the C ABI directly.

A product with fixed operations may omit discovery and generic JSON from the runtime path completely. A fixed appliance may also construct a bounded plan through typed host structures rather than model-generated JSON.

## 13. Benchmark stages

The capability benchmark separates:

1. recognition of a supported deterministic task;
2. plan/semantic-operation selection;
3. argument extraction and prior-result reference formation;
4. tool/plan syntax validity;
5. plan semantic/resource validity;
6. core acceptance/rejection;
7. final answer accuracy;
8. incorrect numeric answer rate;
9. tool penalty rate;
10. result fidelity;
11. failure fidelity.

See [BENCHMARK.md](BENCHMARK.md).

## 14. Required comparison paths

For the implemented generic arithmetic lane, serious evaluation should compare:

- model only;
- model -> unconstrained `xs_calc` -> ExactScope;
- model -> constrained `xs_calc` -> ExactScope;
- gold plan -> ExactScope deterministic ceiling;
- optional larger-model reference with separately reported resource cost.

For semantic-operation workloads, retain direct/constrained `xs_eval` comparison and optional `xs_find -> xs_eval` cold-path measurement.

This keeps discovery overhead visible without making discovery the headline product path.

## 15. Tiny-model acceptance cases

Before a capability profile is considered usable on a weak model, cover at least:

- one-step plan;
- maximum-length valid plan;
- multi-step backward references;
- invalid forward reference;
- invalid/missing argument;
- negative/decimal values;
- division by zero;
- invalid power/domain case;
- overflow/precision/resource failure;
- malformed JSON/envelope;
- grammar whitespace/output-tail termination;
- exact result copied without model recomputation;
- model-only-correct task regressed by tool use;
- reviewed semantic `xs_eval` operation;
- optional discovery ambiguity for `xs_find` tooling.

## 16. Human-facing surfaces

A host application may render, speak, or display results. That UI is outside ExactScope core. A wrapper must not become a second calculation authority.
