# Status and error model v0.1

## 1. General rules

- Status code `0` is success.
- Every nonzero result is a typed failure.
- A failure never includes a usable guessed numeric result.
- Adapters must preserve the core status code.
- Stable numeric codes are ABI and TinyWire contract values.
- Text keys are stable machine labels, not localized prose.
- Additional diagnostic detail is optional and must not be required for program logic.

## 2. Stable status codes

| Code | Key | Meaning |
|---:|---|---|
| 0 | `OK` | Operation completed successfully |
| 1 | `INVALID_REQUEST` | Request envelope or required field is malformed |
| 2 | `ABI_MISMATCH` | Host/core ABI versions are incompatible |
| 3 | `UNKNOWN_OPERATION` | No installed canonical key or discovery match exists |
| 4 | `UNKNOWN_PACK` | Referenced pack slot/identity is not mounted |
| 5 | `ARGUMENT_COUNT` | Argument count differs from the operation signature |
| 6 | `ARGUMENT_TYPE` | Scalar/vector/type shape is wrong |
| 7 | `AMBIGUOUS_METHOD` | More than one materially different method remains possible |
| 8 | `MISSING_INFORMATION` | A required assumption, argument, or unit is absent |
| 9 | `INVALID_DECIMAL` | Decimal lexical form or canonical representation is invalid |
| 10 | `DOMAIN_ERROR` | Mathematically undefined input, excluding explicit divide-by-zero code |
| 11 | `CONSTRAINT_VIOLATION` | Declared input constraint failed |
| 12 | `UNIT_MISMATCH` | Required unit identity/dimension relationship failed |
| 13 | `DIVIDE_BY_ZERO` | Exact denominator is zero |
| 14 | `OVERFLOW` | Bounded coefficient/intermediate/offset arithmetic overflowed |
| 15 | `PRECISION_UNRESOLVED` | Required rounding/classification cannot be proven within the profile |
| 16 | `INSUFFICIENT_DATA` | Vector/sample contains too few observations |
| 17 | `BUFFER_TOO_SMALL` | Caller output/scratch/arena buffer is insufficient |
| 18 | `PACK_INVALID` | Pack structure, metadata, program, identity, or UTF-8 is invalid |
| 19 | `PACK_VERSION_UNSUPPORTED` | Pack format or required ABI version is unsupported |
| 20 | `RESOURCE_LIMIT` | Declared or actual bounded limit was exceeded |
| 21 | `UNSUPPORTED_OPERATION` | Operation or numeric feature is recognized but unavailable in this build/profile |
| 22 | `INTEGRITY_ERROR` | CRC/digest or framing integrity check failed |
| 23 | `INTERNAL_ERROR` | Invariant failure; no calculation result is returned |

Codes `24–63` are reserved for future core errors. Codes `64–127` are reserved for transport/adapters. Codes `128–255` are reserved for optional host-local mappings and must not appear as core ABI status values.

## 3. Deterministic error precedence

When several failures are possible, the public error must be selected in this order:

1. request/frame integrity and size;
2. ABI/protocol version;
3. pack slot and operation identity;
4. argument count;
5. argument shape/type;
6. decimal lexical/canonical parsing in argument order;
7. missing required unit/assumption information;
8. declared constraints in argument and declaration order;
9. same-unit/dimension checks;
10. resource limits known before execution;
11. execution errors in instruction order;
12. classification/precision resolution;
13. output buffer capacity;
14. internal invariant failure.

This precedence makes errors reproducible across targets and implementations.

## 4. Error detail structure

Logical detail fields:

```text
status_code       u16
error_key         stable ASCII key
argument_index    optional u16
constraint_id     optional u16
required_size     optional u32
operation_key     optional canonical ASCII key
pack_identity     optional pack ID/version
options           optional bounded operation-key list
```

A minimum embedded build may return only `status_code` plus numeric detail fields. The adapter can map the code to the stable key from a compiled table.

## 5. Tiny JSON error response

Minimal:

```json
{"s":14,"e":"OVERFLOW"}
```

Argument detail:

```json
{"s":11,"e":"CONSTRAINT_VIOLATION","i":0,"d":1}
```

Ambiguity:

```json
{
  "s":7,
  "e":"AMBIGUOUS_METHOD",
  "need":["method"],
  "opts":["econ.ped.mid","econ.ped.point"]
}
```

The adapter must not attach a numeric `v` field to any nonzero status.

## 6. Common mappings

### Decimal parsing

- invalid character/format -> `INVALID_DECIMAL`;
- syntactically valid but coefficient/exponent exceeds profile -> `OVERFLOW`;
- input exceeds adapter byte cap -> `RESOURCE_LIMIT`.

### Statistics

- empty mean vector -> `INSUFFICIENT_DATA`;
- sample variance with fewer than two values -> `INSUFFICIENT_DATA`;
- unequal paired vector lengths -> `ARGUMENT_TYPE` with vector detail;
- correlation with zero variance -> `DOMAIN_ERROR`.

### Economics/finance

- same initial and final price in elasticity denominator -> `DIVIDE_BY_ZERO`;
- negative price where forbidden -> `CONSTRAINT_VIOLATION`;
- unspecified point versus midpoint method -> `AMBIGUOUS_METHOD` at discovery/intent resolution, not inside a method-specific operation;
- rate passed to a `_pct` operation as text containing `%` -> `INVALID_DECIMAL`;
- nonintegral periods where integral periods are required -> `CONSTRAINT_VIOLATION`.

### Pack loading

- bad magic, bad offsets, duplicate IDs, invalid VM stack -> `PACK_INVALID`;
- unsupported format major or ABI requirement -> `PACK_VERSION_UNSUPPORTED`;
- CRC mismatch -> `INTEGRITY_ERROR`;
- operation/vector/instruction count over runtime cap -> `RESOURCE_LIMIT`.

## 7. Buffer sizing

For APIs that serialize output:

- if output fits, return `OK` and exact bytes written;
- if output does not fit, return `BUFFER_TOO_SMALL`, write no partial semantic response, and return the required byte count;
- a caller may query size with a null output pointer and capacity zero where the ABI function documents this pattern;
- required size calculation must itself be checked for overflow.

## 8. Internal errors

`INTERNAL_ERROR` indicates a bug or corrupted internal state, not user input. The implementation must:

- return no value;
- avoid exposing memory addresses or sensitive host data;
- allow the host to discard/reinitialize the context;
- make the triggering input available to local diagnostics only when the host explicitly logs it;
- add a regression vector before the bug is considered fixed.

## 9. Retry guidance

Core errors are classified for host policy:

| Class | Codes | Typical action |
|---|---|---|
| Correct request | 1, 3–12, 16 | model/host supplies corrected or missing information |
| Change magnitude/profile | 14, 15, 20, 21 | use another operation/profile or report limitation |
| Resize and retry unchanged | 17 | allocate/provide reported capacity and retry |
| Replace/reload pack | 18, 19, 22 | reject artifact and obtain a valid compatible pack |
| Reinitialize/report bug | 2, 23 | fix integration or discard context |

A retry must not silently alter numeric values, units, method, or assumptions.

## 10. Localization

The core and wire protocols return stable keys only. Human-readable localization belongs to the consuming AI/product. ExactScope must not ship large locale strings in the minimum runtime.
