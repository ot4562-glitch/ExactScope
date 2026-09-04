# ExactScope bounded arithmetic plan v0.1

Status: **implemented experimental contract**. This document defines the first bounded arithmetic-plan semantics used by `exactscope-kernel` and the Tiny JSON `xs_calc` adapter. It is not yet a stable v1 ABI promise.

## 1. Purpose

`xs_calc` gives a small/on-device model one compact deterministic path for short numerical programs without exposing a large catalog of independent arithmetic tools or a general code interpreter.

The plan surface is intentionally non-Turing-complete and resource-bounded.

```text
model / typed host
    -> bounded plan
    -> ExactScope validation
    -> shared exact numeric kernel
    -> canonical decimal result or typed failure
```

The plan layer does not own natural-language understanding, retrieval, missing-value inference, unit guessing, or arbitrary symbolic reasoning.

## 2. Tiny JSON request

Canonical request:

```json
{
  "p": [
    {"o":"mul","a":["12","7"]},
    {"o":"sub","a":["#0","4"]},
    {"o":"div","a":["#1","5"]}
  ]
}
```

Top-level fields:

| Field | Meaning |
|---|---|
| `p` | required ordered plan-step array |

No additional top-level fields are accepted.

Each step contains exactly:

| Field | Meaning |
|---|---|
| `o` | operation key |
| `a` | ordered operand array |

Step field order may vary. Duplicate or unknown fields are invalid.

## 3. Resource bounds

| Bound | v0.1 value |
|---|---:|
| request bytes | 512 |
| plan steps | 1-8 |
| operands per step | 1 or 2 according to operation |
| decimal literal text | <= 96 bytes |
| result references | `#0` through `#7`, backward-only |
| output decimal scale search | 18 down to 0 |
| `powi` exponent | integer `-32..=32` |

The runtime allocates no unbounded plan collection. Plan steps and intermediate rational results use fixed storage.

## 4. Operation vocabulary

### `add(left,right)`

Checked exact rational addition.

### `sub(left,right)`

Checked exact rational subtraction.

### `mul(left,right)`

Checked exact rational multiplication with bounded intermediate arithmetic.

### `div(left,right)`

Checked exact rational division. A zero divisor returns `DIVIDE_BY_ZERO`.

### `powi(base,exponent)`

Checked integer power. The exponent must resolve to an exact integer in `-32..=32`.

- non-integer exponent -> `ARGUMENT_TYPE`
- integer outside the allowed range -> `CONSTRAINT_VIOLATION`
- zero raised to a negative exponent -> `DIVIDE_BY_ZERO`

### `sqrt(value)`

Deterministic square root. Negative input returns `DOMAIN_ERROR`.

Irrational roots are quantized using the deterministic policy in section 7 and mark `VALUE_FLAG_INEXACT`; any discarded decimal remainder marks `VALUE_FLAG_ROUNDED`.

No other operation name is part of plan v0.1.

## 5. Operand syntax

Each operand is a plain JSON string with no escape sequences.

### Decimal literal

Examples:

```text
"0"
"-12.5"
"1e3"
```

The literal is parsed by the canonical `decimal64-v1` parser. JSON numeric tokens are not accepted because model/host binary-float parsing must not alter the lexical decimal before ExactScope receives it.

### Previous result reference

Examples:

```text
"#0"
"#3"
```

A reference resolves to the exact bounded intermediate result of an earlier step.

For step index `i`, a reference is valid only when `reference_index < i`.

Forward/self references are `INVALID_REQUEST`. There are no variables, named bindings, mutable cells, or cyclic references.

## 6. Intermediate semantics

`add`, `sub`, `mul`, `div`, and `powi` keep `WorkRational` exact intermediates between steps.

This is intentional. For example:

```text
#0 = div("1","3")
#1 = mul("#0","3")
```

returns exactly `1`; the intermediate `1/3` is not prematurely truncated to a decimal string.

`sqrt` is the only v0.1 operation that may require an irrational intermediate. Its deterministic decimal result is converted back into the shared exact rational work representation before later plan steps continue.

## 7. Decimal output policy

Generic arithmetic plans do not carry an operation-specific display scale. ExactScope therefore uses one deterministic bounded policy:

1. rounding mode is half-even;
2. attempt fractional scale 18;
3. if the bounded `Decimal64` coefficient would overflow, retry scale 17, then 16, continuing down to 0;
4. the first representable result is canonicalized as `Decimal64`;
5. if nonzero remainder was discarded, set `VALUE_FLAG_ROUNDED`;
6. if a square root is mathematically irrational, set `VALUE_FLAG_INEXACT`.

This is a representation/precision policy, not model-side semantic repair.

Example:

```text
1 / 3 -> "0.333333333333333333", flags = ROUNDED
```

## 8. Tiny JSON success response

Canonical success shape:

```json
{"s":0,"v":"16","f":0,"p":"plan-v0.1","r":1}
```

| Field | Meaning |
|---|---|
| `s` | stable status code, zero on success |
| `v` | canonical exact/quantized decimal string |
| `f` | aggregate stable `VALUE_FLAG_*` bits |
| `p` | plan provenance identifier, `plan-v0.1` |
| `r` | plan contract revision, currently `1` |

## 9. Tiny JSON failure response

Global parse/resource failure example:

```json
{"s":20,"e":"RESOURCE_LIMIT"}
```

Step-attributable failure example:

```json
{"s":13,"e":"DIVIDE_BY_ZERO","step":2}
```

A failed plan never returns a plausible numeric `v` field.

The existing stable core status registry remains authoritative. Plan v0.1 does not introduce a parallel error-code namespace.

## 10. Failure ordering

Validation/execution proceeds deterministically:

1. request byte/UTF-8 bounds;
2. top-level Tiny JSON shape;
3. step-array resource bounds;
4. step field/operation/value syntax;
5. operation arity;
6. backward-reference validity;
7. operation-specific argument constraints;
8. arithmetic/domain/overflow execution;
9. final decimal quantization.

The first failure in this deterministic order is returned.

## 11. Explicit non-capabilities

Plan v0.1 has no:

- loops;
- recursion;
- jumps;
- branching;
- mutable variables;
- arbitrary expression strings;
- arbitrary function names;
- arbitrary code;
- filesystem/network/process APIs;
- random/clock/environment APIs;
- unit guessing/conversion;
- semantic formula discovery;
- hidden model retry/repair.

## 12. Relationship to `xs_eval`

`xs_calc` and `xs_eval` are complementary.

Use `xs_calc` for ordinary short arithmetic decomposition where the model already knows which quantities and arithmetic relationships are required.

Use `xs_eval` when method identity itself is reviewed semantic content, for example:

- sample vs population variance;
- economics method variants;
- future finance/physics/chemistry operations with explicit unit/method contracts.

Both paths use the same deterministic numeric core. `xs_find` remains optional cold/development discovery for semantic operations.

## 13. Compatibility status

The Rust kernel and Tiny JSON path implement this experimental contract. Native stable C ABI structures, generated tool assets, public benchmark converters, and release-level compatibility claims are separate gates and must be evidenced before v1.
