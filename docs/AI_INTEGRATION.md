# AI integration contract

ExactScope is consumed by AI runtimes, not by human users. This document defines the minimum model-facing surface.

## 1. Two tools only

The default adapter exposes exactly two functions:

- `xs_find` — discover a deterministic operation from a short machine query;
- `xs_eval` — evaluate one canonical operation with exact decimal strings.

Do not expose every formula as an independent tool to a constrained model. Large catalogs increase prompt size, tool confusion, schema conversion risk, and installation coupling.

## 2. Tiny tool definitions

Normative model-facing definitions are generated from:

- [`spec/schemas/xs-find-tool.schema.json`](../spec/schemas/xs-find-tool.schema.json)
- [`spec/schemas/xs-eval-tool.schema.json`](../spec/schemas/xs-eval-tool.schema.json)

Logical form:

```json
{
  "name": "xs_find",
  "description": "Find an installed deterministic quantitative operation. Use before xs_eval when the exact operation key is unknown.",
  "parameters": {
    "type": "object",
    "properties": {
      "q": {"type": "string"},
      "n": {"type": "integer", "minimum": 1, "maximum": 5}
    },
    "required": ["q", "n"],
    "additionalProperties": false
  }
}
```

```json
{
  "name": "xs_eval",
  "description": "Evaluate one ExactScope operation. Pass decimal arguments as plain base-10 strings in signature order.",
  "parameters": {
    "type": "object",
    "properties": {
      "op": {"type": "string"},
      "a": {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 0,
        "maxItems": 12
      }
    },
    "required": ["op", "a"],
    "additionalProperties": false
  }
}
```

The schemas intentionally avoid unions, conditionals, recursive references, schema-only descriptions without types, complex regular expressions, and optional operational fields. The goal is compatibility with simple tool-call parsers and grammar-constrained local runtimes.

## 3. Model policy

An adapter's system prompt should communicate the following compact policy:

```text
Use ExactScope for supported quantitative calculations.
If the operation key is unknown, call xs_find.
Call xs_eval with arguments in the returned signature order.
Use plain base-10 strings: no commas, units, %, NaN, or Infinity.
Never invent an operation key.
Never repair an ExactScope error by guessing.
If ExactScope reports ambiguity or missing information, request that information.
Return the ExactScope value and classification without recalculating them.
```

The prompt should not enumerate the full operation catalog.

## 4. Canonical AI-facing decimals

Accepted lexical examples:

```text
0
-12
12.50
0.05
1000000
1e-6
```

The adapter canonicalizes valid forms before calling the core. It rejects:

```text
1,000
5%
$12
NaN
Infinity
approximately 4
12 meters
```

Whether scientific notation is accepted is fixed by the numeric specification. The adapter must not infer percent-versus-ratio semantics from the text value; the operation signature carries that meaning.

## 5. Discovery response

Compact success:

```json
{
  "s": 0,
  "m": [
    {
      "op": "econ.ped.mid",
      "sig": "econ.ped.mid(p1,p2,q1,q2)",
      "method": "midpoint"
    }
  ]
}
```

Ambiguous discovery may return multiple candidates. Ranking is deterministic and not a confidence claim.

No match:

```json
{"s":3,"e":"UNKNOWN_OPERATION"}
```

## 6. Evaluation response

Compact success:

```json
{
  "s": 0,
  "v": "-1.222222",
  "c": "elastic",
  "p": "econ-undergrad@0.1.0",
  "r": 1
}
```

Fields:

- `s`: stable numeric status, zero on success;
- `v`: canonical base-10 result string;
- `c`: optional deterministic classification key;
- `p`: pack ID/version provenance;
- `r`: operation revision.

Adapters may offer a smaller response profile that omits provenance only when the host logs it separately. They may not replace the numeric value with natural-language prose.

Typed error:

```json
{
  "s": 7,
  "e": "AMBIGUOUS_METHOD",
  "need": ["method"],
  "opts": ["econ.ped.mid", "econ.ped.point"]
}
```

## 7. Preferred call paths

### 7.1 Cached direct call

The host already knows the canonical operation key from its application flow.

```text
xs_eval -> result
```

This is the lowest-token and lowest-latency path.

### 7.2 Discovery then evaluation

The model understands the intent but not the exact operation key.

```text
xs_find -> compact signature -> xs_eval -> result
```

### 7.3 Bounded bootstrap catalog

A dedicated appliance may preload a small catalog of its most common 8–32 signatures into the model prompt. All other operations remain discoverable. The preloaded catalog is generated from the installed pack digest so it cannot drift from runtime capability.

## 8. Never make operation methods implicit

Different methods are separate canonical operation keys.

Examples:

```text
econ.ped.mid
econ.ped.point
stats.var.pop
stats.var.sample
finance.rate.real.exact
finance.rate.real.approx
```

The model must not pass a vague `method` string to a universal calculator endpoint. Separate keys make caching, testing, provenance, and compatibility explicit.

## 9. Units and semantic names

`xs_find` signatures use short semantic argument names:

```text
finance.fv.compound(principal,rate_pct,periods)
econ.real_wage(nominal_wage,cpi_index)
stats.zscore(value,mean,stddev)
```

Names such as `_pct`, `_ratio`, `_index`, and `_periods` are deliberate model cues. The core still validates the operation's declared semantics.

If an operation requires unit identity, an extended adapter may provide parallel unit IDs through a host-owned typed call. The tiny model-facing profile avoids a general free-text unit field.

## 10. Adapter responsibilities

An adapter must:

- validate tool-call JSON before the core call;
- cap request bytes and array lengths;
- parse only the documented decimal lexical grammar;
- resolve canonical keys through the mounted registry;
- preserve argument order;
- preserve core status codes and provenance;
- avoid calculating, rounding, converting, or classifying independently;
- avoid retries that mutate values;
- log the core/pack digest when auditability is required.

An adapter may:

- map a model's native tool-call envelope to the two ExactScope functions;
- translate field names at the outermost protocol boundary;
- cache immutable discovery results by pack digest;
- provide locale aliases before `xs_find`;
- render a result after the deterministic call.

## 11. llama.cpp-compatible profile

The planned adapter should provide:

- conservative JSON tool schemas;
- pre-generated GBNF for `xs_find` and `xs_eval`;
- fixtures for OpenAI-style JSON calls, tag-wrapped JSON calls, and raw JSON calls;
- a tiny system-prompt fragment;
- tests against selected small GGUF instruct/tool models.

The GBNF must be checked into releases rather than relying exclusively on runtime JSON-Schema conversion. This reduces breakage across llama.cpp versions and allows ExactScope to test the exact grammar it recommends.

## 12. Benchmark contract

Models are evaluated on separate stages:

1. **recognition:** identify that a supported deterministic tool should be used;
2. **discovery:** produce a useful `xs_find` query or select a cached key;
3. **argument extraction:** copy the correct values in signature order;
4. **tool-call validity:** produce valid constrained JSON;
5. **result fidelity:** report the returned value/classification without alteration;
6. **failure fidelity:** preserve ambiguity or invalid-input errors rather than hallucinating an answer.

The benchmark must compare model-only and model-plus-ExactScope paths, including token count, latency, energy where measurable, and total end-to-end accuracy. ExactScope does not claim to solve recognition or extraction errors; it minimizes the calculation and method-execution burden after a correct call.

## 13. Tiny-model acceptance cases

Before an adapter is released, it must include cases covering:

- direct known operation;
- discovery with one match;
- discovery with several methods;
- negative and decimal values;
- percentages versus ratios;
- missing argument;
- invalid lexical value;
- wrong argument order;
- operation not installed;
- core overflow/domain error;
- exact result copied without model recomputation.

## 14. Human-facing surfaces

A debugging CLI may exist for developers and conformance tests. It is not a product UI and must call the same core APIs. No official roadmap item should prioritize a consumer calculator screen over AI runtime compatibility.
