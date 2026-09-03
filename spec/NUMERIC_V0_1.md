# Numeric model v0.1

## 1. Profile identity

The required baseline numeric profile is `decimal64-v1`.

It is designed for deterministic quantitative operations on targets that may not have a floating-point unit and must not depend on host floating-point modes.

## 2. External scalar representation

A scalar is logically:

```text
value = coefficient * 10^exponent
coefficient: signed 64-bit integer
exponent: signed 8-bit integer, restricted to [-18, 18]
```

Canonical rules:

1. zero is represented only as coefficient `0`, exponent `0`;
2. a nonzero coefficient has no trailing base-10 zero while its exponent is below `18`;
3. negative zero is invalid and canonicalizes to zero at lexical boundaries;
4. no NaN or infinity values exist;
5. overflow never wraps or saturates;
6. an operation that cannot represent its required result returns a typed error.

## 3. AI-facing lexical grammar

Accepted decimal strings match this grammar:

```text
number   = ["-"] integer [fraction] [exponent]
integer  = "0" | nonzero-digit *digit
fraction = "." 1*digit
exponent = ("e" | "E") ["+" | "-"] 1*digit
```

Additional requirements:

- no leading `+` on the whole number;
- no leading zeroes except the single integer `0`;
- no whitespace;
- no comma or locale separator;
- no percent sign, currency symbol, or unit text;
- no hexadecimal, binary, or octal notation;
- exponent application must yield an exactly representable `decimal64-v1` value after trailing-zero normalization;
- total input length is at most 96 bytes in the Tiny JSON adapter;
- exponent text whose magnitude cannot be processed within bounded integer parsing returns `INVALID_DECIMAL` or `OVERFLOW` without unbounded work.

Examples accepted before canonicalization:

```text
0
-12
12.50
0.05
1000000
1e-6
1.2300E+2
```

Canonical values:

```text
12.50       -> coefficient 125, exponent -1
0.05        -> coefficient 5, exponent -2
1000000     -> coefficient 1, exponent 6
1e-6        -> coefficient 1, exponent -6
1.2300E+2   -> coefficient 123, exponent 0
```

## 4. Canonical output string

The normative compact output is plain base-10 notation without exponent syntax.

Rules:

- no leading `+`;
- no leading zeroes except `0` before a fractional point;
- no trailing fractional zeroes;
- no trailing decimal point;
- zero is `"0"`;
- values between `-1` and `1` include a leading zero;
- output is the shortest plain string that round-trips to the returned canonical scalar.

Examples:

```text
coefficient 125, exponent -1 -> "12.5"
coefficient 5, exponent -2   -> "0.05"
coefficient 1, exponent 6    -> "1000000"
```

A verbose adapter may also expose coefficient and exponent fields, but the value is unchanged.

## 5. Internal exact work values

Inputs are converted exactly to a checked rational work value:

```text
numerator / denominator
numerator: signed 128-bit integer
denominator: positive signed 128-bit integer
```

The implementation MUST normalize signs and SHOULD reduce common factors when doing so prevents overflow. Exact rational operations are used for:

- add;
- subtract;
- multiply;
- divide;
- negate;
- absolute value;
- compare;
- integer power.

No intermediate rounding is permitted for those operations unless the scope program contains an explicit `ROUND` instruction.

If the mathematically required numerator or denominator cannot be represented in the bounded work type, evaluation returns `OVERFLOW`. The implementation must not fall back to binary floating point.

## 6. Arithmetic semantics

### 6.1 Addition and subtraction

Addition/subtraction computes the exact rational result using checked arithmetic. Implementations should reduce cross factors before multiplication where possible.

### 6.2 Multiplication

Multiplication must cross-reduce numerator/denominator factors before checked multiplication to reduce avoidable overflow.

### 6.3 Division

Division by an exact zero returns `DIVIDE_BY_ZERO`. Otherwise operands are multiplied by the reciprocal using checked sign normalization and cross reduction.

### 6.4 Integer power

`POWI n` accepts a signed integer exponent in the pack-declared range. v0.1 pack validation restricts `n` to `[-32, 32]` unless a lower operation-specific bound is declared.

- exponent `0` returns one, including for a nonzero input;
- `0` raised to a negative exponent returns `DIVIDE_BY_ZERO`;
- repeated squaring is recommended;
- every intermediate is checked.

### 6.5 Square root

`SQRT` accepts nonnegative values only. Negative input returns `DOMAIN_ERROR`.

The semantic requirement is a correctly rounded base-10 result at the active working/output scale. Implementations may use integer Newton iteration, digit-by-digit extraction, or another bounded integer algorithm, but all conforming targets must produce the same canonical result.

The implementation must:

- use no binary floating-point fallback;
- cap iterations based on operand width rather than input value text;
- calculate enough guard precision to decide the requested rounding exactly;
- handle exact squares without marking the result inexact;
- set the result `inexact` flag for non-square roots.

Golden vectors, including tie-adjacent values, are normative for v0.1 conformance.

## 7. Rounding

Rounding is explicit and never locale-dependent.

Stable rounding IDs:

| ID | Key | Rule |
|---:|---|---|
| 0 | `half_even` | nearest; ties to an even retained digit |
| 1 | `half_away` | nearest; ties away from zero |
| 2 | `toward_zero` | truncate toward zero |
| 3 | `floor` | toward negative infinity |
| 4 | `ceil` | toward positive infinity |

`half_even` is the default for official packs unless the domain definition requires another mode.

The output scale is the number of fractional decimal digits requested before canonical trailing-zero removal. Scale must be in `[0, 18]` for v0.1.

The result records:

- requested scale;
- rounding mode;
- whether the exact work value was changed by rounding;
- whether a kernel produced an inexact intermediate such as an irrational square root.

## 8. Classification and precision

Classification is evaluated before final display rounding.

For exact rational operations, predicates compare the exact work value. Equality is exact unless a pack explicitly declares a closed interval or tolerance operation.

Example:

```text
exact abs(result) < 1 -> inelastic
exact abs(result) = 1 -> unit_elastic
exact abs(result) > 1 -> elastic
```

A rendered value of `1.000000` does not imply exact equality with one.

For an operation involving an irrational/bounded approximation, the kernel must produce an interval or sufficient guard precision to prove the classification boundary. If it cannot prove the classification, it returns `PRECISION_UNRESOLVED` rather than guessing.

## 9. Semantic kinds

Stable scalar semantic kinds for v0.1:

| ID | Key | Meaning |
|---:|---|---|
| 0 | `number` | dimensionless general number |
| 1 | `count` | count, normally integral and nonnegative |
| 2 | `currency_amount` | monetary magnitude; no currency conversion |
| 3 | `price` | currency amount per quantity |
| 4 | `quantity` | quantity of a good/input/output |
| 5 | `rate_percent` | value expressed in percentage points; `5` means 5% |
| 6 | `rate_ratio` | ratio form; `0.05` means 5% |
| 7 | `index` | index level such as CPI |
| 8 | `time_periods` | number of periods |
| 9 | `probability` | closed interval `[0,1]` unless overridden |
| 10 | `elasticity` | dimensionless signed elasticity |

Packs may define display labels but may not redefine these semantics under the same numeric ID.

## 10. Unit IDs

Unit ID `0` means unspecified. Other IDs are registry-local unsigned 16-bit identifiers.

v0.1 uses units only for compatibility checks:

- arguments in the same `same_unit_group` must have equal nonzero unit IDs when more than one is supplied;
- unspecified ID `0` does not prove compatibility and may be rejected by operations that require explicit units;
- the core performs no implicit conversion;
- a conversion must be an explicit deterministic operation with declared factors and provenance.

Currency identity, period identity, and physical dimensions are separate unit namespaces in source metadata even if represented by the same compact integer field after pack compilation.

## 11. Constraints

Supported scalar constraints:

- `gt`, `ge`, `lt`, `le`, `eq`, `ne` against canonical decimal constants;
- `integer`;
- `nonzero`;
- `finite` is implicit because no nonfinite values exist;
- `same_unit_group`;
- `one_of` for small canonical constant sets.

Constraints are evaluated before program execution in source declaration order. The returned error identifies the first failing argument index and constraint code. Implementations may evaluate in another order internally only if they preserve the same public error selection.

## 12. Vector representation

A vector is an immutable ordered sequence of `Decimal64` values with one semantic kind and optional unit ID.

Default maximum length: `256`.

The core rejects:

- lengths above the operation or global limit;
- null pointer with nonzero length in the C ABI;
- mixed semantic kinds inside one vector;
- mixed nonzero unit IDs where the operation requires one unit;
- invalid canonical scalars.

## 13. Deterministic statistics kernels

### 13.1 Sum and mean

- iteration order is input order;
- sum uses exact rational accumulation with checked reduction;
- mean is exact sum divided by count;
- empty input returns `INSUFFICIENT_DATA`.

### 13.2 Variance

Population variance:

```text
sum((x - mean)^2) / n
```

Sample variance:

```text
sum((x - mean)^2) / (n - 1)
```

The required algorithm is a deterministic two-pass exact-rational calculation for v0.1. Sample variance requires at least two values.

### 13.3 Covariance

Population and sample covariance are distinct operations with denominators `n` and `n-1`. Paired vectors must have equal nonzero length.

### 13.4 Correlation

Correlation is:

```text
covariance(x,y) / (stddev(x) * stddev(y))
```

Zero variance returns `DOMAIN_ERROR`. Square roots follow the correctly rounded/guarded rule above. Classification near a boundary must be provable or fail with `PRECISION_UNRESOLVED`.

### 13.5 Simple linear regression

For `y = intercept + slope*x`:

```text
slope = sum((x-mean_x)(y-mean_y)) / sum((x-mean_x)^2)
intercept = mean_y - slope*mean_x
```

At least two paired points are required, lengths must match, and zero x variance returns `DOMAIN_ERROR`.

## 14. Finance and economics conventions

- Rate-percent operations divide the supplied rate by 100 exactly before use.
- Rate-ratio operations use the supplied ratio directly.
- Period counts are integral unless an operation explicitly supports fractional periods.
- Nominal-versus-real approximate and exact relationships are separate operation keys.
- Midpoint/arc and point elasticity are separate operation keys.
- Index-base conventions must be stated in operation metadata; the core does not assume base 100 unless the operation declares it.
- Monetary outputs preserve compatible currency unit IDs but never fetch exchange rates.

## 15. Result identity

Canonical result identity includes:

```text
core numeric profile
pack digest
operation ID and revision
canonical typed arguments
explicit output scale
rounding mode
canonical value/classification/status
```

Given identical identity fields, Tier 1 targets must produce byte-identical canonical result data.

## 16. Out of scope for `decimal64-v1`

- arbitrary-precision arithmetic;
- complex numbers;
- interval arithmetic as a general public type;
- host-native `float`/`double` semantics;
- locale-aware parsing;
- symbolic algebra;
- unconstrained numerical optimization;
- random sampling;
- live financial or economic data.

These may be added through future numeric profiles or operations without weakening the baseline profile.
