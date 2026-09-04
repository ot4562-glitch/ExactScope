# First implementation slice: `econ.ped.mid`

> **Historical implementation record.** This document describes the original vertical slice that established the shared evaluator/ABI/Wasm semantics. That slice is complete and is no longer the current product-priority plan. For current sequencing use [`PRODUCT_DIRECTION.md`](PRODUCT_DIRECTION.md), [`QUICKSTART.md`](QUICKSTART.md), [`BENCHMARK.md`](BENCHMARK.md), and [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md). Statements below such as “no later milestone begins” apply to the historical first-slice acceptance process, not to the current v0.1 release order.

This document is the executable coding plan for the first ExactScope runtime commit. It deliberately implements one complete operation across every portability boundary before expanding the catalog.

The goal is not “some Rust code that calculates elasticity.” The goal is one semantic implementation that produces the same status, canonical value, classification, flags, and provenance through:

```text
reviewed source-pack fixture
        -> deterministic kernel/VM
        -> fused registry
        -> typed Rust call
        -> C ABI call
        -> wasm32v1-none call
        -> Tiny JSON call
```

No later milestone begins until the shared vectors pass on every available path.

## 1. Frozen scope

Implement exactly one operation:

```text
key:       econ.ped.mid
pack:      org.exactscope.econ-undergrad
pack ver:  0.1.0
op id:     301
revision:  1
method:    midpoint
signature: econ.ped.mid(p1,p2,q1,q2)
```

Definition:

```text
quantity_change = (q2 - q1) / ((q1 + q2) / 2)
price_change    = (p2 - p1) / ((p1 + p2) / 2)
elasticity      = quantity_change / price_change
```

Equivalent exact rational identity, useful for reference tests but not a license to change the checked VM execution order:

```text
elasticity = ((q2 - q1) * (p1 + p2)) / ((q1 + q2) * (p2 - p1))
```

Input semantics:

| Index | Name | Semantic | Constraint | Unit relationship |
|---:|---|---|---|---|
| 0 | `p1` | `price` | `> 0` | same group as `p2` |
| 1 | `p2` | `price` | `> 0` | same group as `p1` |
| 2 | `q1` | `quantity` | `>= 0` | same group as `q2` |
| 3 | `q2` | `quantity` | `>= 0` | same group as `q1` |

Output:

```text
name:                  elasticity
semantic:              elasticity
unit:                  dimensionless
scale:                 6
rounding:              half_even
classification source: exact unrounded rational
```

Classification:

```text
abs(elasticity) < 1 -> inelastic    (id 1)
abs(elasticity) = 1 -> unit_elastic (id 2)
abs(elasticity) > 1 -> elastic      (id 3)
```

The source fixture at `spec/examples/econ-undergrad-minimal.xsp.json` is normative for operation metadata and instruction order. This document is normative for implementation sequence and acceptance.

## 2. Explicit non-scope

Do not add any of the following to the first slice:

- another formula or operation;
- vector/statistics kernels;
- arbitrary expression parsing;
- dynamic `.xsp` loading;
- general alias search beyond the one fused operation;
- HTTP, MCP, CLI product UI, database, logging, telemetry, or network code;
- locale parsing or translated aliases;
- binary floating-point fallback;
- an allocator requirement in a runtime crate;
- model-specific calculation prompts;
- optimized/SIMD paths;
- general square root or integer-power support unless required by a later reviewed slice.

`xs_find` may return the one fused operation for exact normalized aliases, but full ranked discovery indexing belongs to the pack-loader milestone.

## 3. Repository modules to create

The first code change creates these modules. File names are internal organization, not stable Rust API, but responsibility boundaries are required.

```text
crates/exactscope-kernel/src/
  lib.rs
  status.rs        # stable 0..23 status representation
  decimal.rs       # Decimal64 parse/canonicalize/format
  rational.rs      # checked signed-i128 exact work value
  rounding.rs      # output quantization and flags
  semantic.rs      # semantic/unit validation
  vm.rs            # bounded scalar RPN evaluator
  operation.rs     # immutable declarations and fused op table
  evaluate.rs      # one public typed evaluation pipeline

crates/exactscope-pack/src/
  lib.rs
  fused.rs          # immutable fused pack/operation descriptors only
  registry.rs       # one-pack lookup and bounded alias match

crates/exactscope-cabi/src/
  lib.rs
  layout.rs         # repr(C) mirrors/assertions
  entry.rs          # pointer/length validation and exported wrappers

crates/exactscope-tinyjson/src/
  lib.rs
  parse.rs          # bounded two-envelope parser, no DOM
  serialize.rs      # canonical compact response writer

crates/exactscope-wasm/src/
  lib.rs
  exports.rs        # reserved boundary and xs_wire_request wrapper

crates/exactscope-conformance/
  src/lib.rs
  tests/
    ped_mid.rs
    decimal.rs
    ffi_layout.rs
    tiny_json.rs
    wasm_equivalence.rs
```

`exactscope-packc` is not required to compile the first operation. The first fused table may be generated by a checked-in development script or written as an explicitly temporary generated table, but it must be byte-for-byte compared with the source fixture and replaced by `packc` before a runtime release.

## 4. Stable internal types

The implementation should use small explicit value types. Equivalent private field names are acceptable; semantics are not.

### 4.1 Status

```rust
#[repr(transparent)]
pub struct Status(u16);
```

Requirements:

- constants exactly match `spec/registries/status-codes.json`;
- unknown internal values are never emitted;
- no error carries a plausible output value;
- public precedence follows `spec/ERRORS_V0_1.md`.

### 4.2 Decimal64

```rust
pub struct Decimal64 {
    coefficient: i64,
    exponent: i8,
}
```

Required methods for the slice:

```text
parse_ascii(bytes) -> Result<Decimal64, Status>
from_parts(coefficient, exponent) -> Result<Decimal64, Status>
coefficient() -> i64
exponent() -> i8
is_zero() -> bool
format_len() -> Result<usize, Status>
write_canonical(output) -> Result<usize, Status>
```

Rules are exactly those in `NUMERIC_V0_1.md`:

- exponent after normalization is in `[-18,18]`;
- zero is only `(0,0)`;
- trailing coefficient zeroes are removed while exponent can increase;
- parsing is ASCII and bounded by the supplied slice length;
- no allocation, locale, Unicode digit, whitespace, percent, comma, unit, NaN, or infinity;
- checked parsing distinguishes invalid lexical input from representational overflow;
- canonical formatting uses plain decimal notation, never exponent notation.

### 4.3 Work rational

```rust
pub struct WorkRational {
    numerator: i128,
    denominator: i128, // strictly positive
}
```

Required methods:

```text
from_decimal(Decimal64)
checked_add
checked_sub
checked_mul
checked_div
checked_neg
checked_abs
checked_cmp
round_to_decimal(scale, mode)
```

Every constructor and operation normalizes sign and reduces by a bounded GCD when needed. Multiplication and division cross-reduce before checked multiplication. Addition/subtraction reduce denominator cross factors before multiplication. No operation falls back to `f32`/`f64`.

### 4.4 Typed value

The internal scalar input contains:

```text
Decimal64 value
semantic_kind u8
unit_id u16
flags u32
```

For Tiny JSON, the adapter assigns semantic kinds from the selected operation declaration and unit ID zero. For the typed C ABI, the caller supplies semantic/unit metadata and the core validates it.

## 5. Decimal parser algorithm

Implement one pass over at most 96 bytes:

1. reject an empty input;
2. consume an optional leading `-`;
3. consume integer digits using the exact leading-zero grammar;
4. consume an optional fractional part with at least one digit;
5. consume an optional `e`/`E`, optional sign, and at least one digit;
6. reject every trailing byte;
7. accumulate significant digits with checked `i64` arithmetic;
8. track fractional digit count and parsed exponent with bounded integers;
9. combine exponents using checked arithmetic;
10. normalize trailing coefficient zeroes;
11. require the final exponent in `[-18,18]`;
12. canonicalize all zero forms to `(0,0)`.

The parser must cap exponent-digit work. More than 10 exponent digits may be rejected immediately as `OVERFLOW` after lexical validity is known; it must not loop over a magnitude implied by exponent text.

Error selection for this parser:

- invalid grammar/character -> `INVALID_DECIMAL`;
- syntactically valid coefficient/exponent outside representation -> `OVERFLOW`;
- adapter request string over 96 bytes -> `RESOURCE_LIMIT` before numeric parsing.

## 6. Exact rounding algorithm

For output scale `s`, convert exact `n/d` to a signed integer coefficient representing `10^-s` units:

1. form `abs(n) * 10^s` using checked arithmetic;
2. divide by positive `d`, producing quotient and remainder;
3. apply the selected rounding mode from the exact remainder;
4. restore sign;
5. construct and canonicalize `Decimal64(coefficient, -s)`;
6. set `ROUNDED` when remainder is nonzero or explicit rounding changed the exact value;
7. do not set `INEXACT` for a rational result; that flag is reserved for bounded irrational/numerical kernels.

For half-even, compare `2 * remainder` with `d` using overflow-safe comparison. On equality increment the quotient only when its retained least-significant digit is odd.

If scaling or incrementing cannot be represented, return `OVERFLOW`. No partially rounded value is returned.

## 7. VM subset

Implement only these opcodes for the first slice:

```text
ARG
CONST
ADD
SUB
DIV
ABS
CMP_LT
CMP_EQ
CMP_GT
END
```

The registry still reserves all v0.1 opcode IDs in `spec/registries/vm-opcodes.json`; unimplemented recognized opcodes return `UNSUPPORTED_OPERATION` when encountered in a future non-fused program.

Validation before execution:

- instruction count `1..64`;
- final instruction is `END`;
- argument/constant/result indexes are in range;
- every instruction has the declared operand count;
- stack never underflows;
- stack depth never exceeds `16`;
- exactly one value reaches `END`;
- formula programs cannot use `RESULT` or classification-only boolean operations;
- classification programs cannot reference an unavailable output.

Runtime:

- fixed `[WorkRational;16]`-equivalent storage, with an explicit initialized-length strategy that uses no heap and no uninitialized read;
- checked instruction counter even for prevalidated programs;
- first arithmetic failure stops execution;
- no jumps, calls, loops, memory access, or dynamic dispatch from pack data.

## 8. Evaluation pipeline and error precedence

The typed `evaluate` entry performs these stages in order:

1. validate registry/operation identity;
2. validate argument count;
3. validate scalar shape;
4. validate canonical `Decimal64` structures in argument order;
5. validate semantic kinds in argument order;
6. validate required unit information;
7. validate declared input constraints in declaration order;
8. validate same-unit groups;
9. validate known resource requirements;
10. execute the formula program;
11. execute classification predicates on the exact result;
12. round to scale six using half-even;
13. create a fully initialized result with provenance.

For `econ.ped.mid`, unchanged price leads to an exact zero denominator during the price-change program and returns `DIVIDE_BY_ZERO`. Negative/zero prices are rejected earlier as `CONSTRAINT_VIOLATION`. This ordering is intentional.

The output result on success contains:

```text
status:               OK
value_count:          1
classification_id:    1, 2, or 3
pack_slot:            fused slot assigned deterministically at build time
operation_id:         301
operation_revision:   1
output_scale:         6
rounding_mode:        half_even
value semantic:       elasticity
value unit_id:        0
value flags:          ROUNDED when required; INEXACT unset
```

Every failure zeroes value count and all value slots and uses argument index `0xffff` when not applicable.

## 9. Fused registry

The first registry is immutable static data with one pack and one operation.

Requirements:

- slot zero remains reserved;
- `org.exactscope.econ-undergrad@0.1.0` uses fused slot one in the fixture build;
- direct canonical lookup of `econ.ped.mid` succeeds;
- aliases from the source fixture normalize and match deterministically;
- unknown keys/queries return `UNKNOWN_OPERATION`;
- direct evaluation uses `(slot=1,id=301)` after lookup;
- operation metadata strings are immutable static UTF-8;
- no hashmap, heap, filesystem, generated random hash seed, locale, or Unicode database.

For the one-operation slice, bounded linear comparison is authoritative. Do not prematurely add a generic hash table.

## 10. Tiny JSON parser and serializer

Implement only the exact closed schemas in `spec/schemas/`.

Parser requirements:

- maximum request 512 bytes;
- UTF-8 validation;
- object depth one plus the scalar argument array;
- no duplicate keys;
- no unknown keys;
- all required keys present exactly once;
- strings decoded into caller/fixed scratch without heap allocation;
- only the JSON escapes required by RFC-compliant strings; decoded query/key/value byte limits apply after unescaping;
- no JSON numbers for decimal arguments;
- no comments, trailing commas, NaN, or Infinity;
- `xs_eval.a` contains at most 12 strings;
- parser returns typed adapter/core status and never guesses missing fields.

Canonical serializer:

- no whitespace;
- field order from `TINYWIRE_V0_1.md`;
- escape only as required by JSON;
- values are canonical decimal strings;
- no partial response on insufficient capacity;
- first size pass or bounded exact size computation, then one write pass;
- failure responses never include `v`.

Required first success bytes:

```json
{"s":0,"v":"-1.222222","c":"elastic","p":"econ-undergrad@0.1.0","r":1}
```

## 11. C ABI implementation

`include/exactscope.h` is the syntax authority. The Rust ABI wrapper mirrors every public structure with `#[repr(C)]` and compile-time size/alignment/offset tests.

First slice requirements:

- implement version/context size/alignment/init/reset;
- expose one fused pack without dynamic mounting;
- implement exact lookup/find/eval;
- implement canonical result/match JSON serialization;
- dynamic pack functions return `UNSUPPORTED_OPERATION` in the fused-only build;
- validate structure size and reserved fields before other semantic fields;
- nonzero length plus null pointer is invalid;
- reject forbidden overlap before constructing Rust references/slices;
- never retain caller argument/scratch/output pointers;
- fully initialize result/output-count fields on every valid output pointer;
- no unwind crosses `extern "C"`;
- abort-only release builds do not claim panic-to-status recovery.

Unsafe code is confined to pointer validation and slice construction in `exactscope-cabi`. Each unsafe block needs an adjacent `SAFETY:` comment describing range, alignment, aliasing, and lifetime proof.

## 12. WebAssembly implementation

Use `wasm32v1-none` and `spec/WASM_ABI_V0_1.md`.

First fused module exports:

```text
memory
xs_abi_version
xs_wasm_reserved_end
xs_wasm_memory_alignment
xs_wire_request
```

Implementation requirements:

- empty import section;
- no WASI;
- no allocator or memory growth from the module;
- host-owned request/output/meta regions above the exported reserved boundary;
- exact range, alignment, and non-overlap checks;
- Tiny JSON wire format ID `1` required;
- deterministic-CBOR format ID `2` may return `UNSUPPORTED_OPERATION` in the first slice;
- no partial output on `BUFFER_TOO_SMALL`;
- metadata is fully initialized when valid;
- malformed valid-memory input produces a typed status, not an intentional trap;
- same canonical success bytes as native Tiny JSON.

A release candidate is rejected if module inspection finds any import or unsupported post-WebAssembly-1.0 feature.

## 13. Golden vectors

The five source-pack tests are minimum acceptance cases:

| Case | Inputs `(p1,p2,q1,q2)` | Expected status/value/class |
|---|---|---|
| elastic | `10000,12000,100,80` | `OK`, `-1.222222`, `elastic`, rounded |
| unit elastic | `10,20,20,10` | `OK`, `-1`, `unit_elastic`, exact |
| inelastic | `10,12,100,95` | `OK`, `-0.282051`, `inelastic`, rounded |
| unchanged price | `10,10,100,80` | `DIVIDE_BY_ZERO` |
| negative initial price | `-1,10,100,80` | `CONSTRAINT_VIOLATION`, argument `0`, detail `1` |

Add these mandatory parser/numeric/ABI vectors before the slice merges:

### Decimal lexical

```text
0, -12, 12.50, 0.05, 1000000, 1e-6, 1.2300E+2 -> accepted/canonical
-0, -0.0 -> accepted then canonical zero
+1, 01, 1., .1, 1e, 1 2, 1,000, 5%, NaN, Infinity -> INVALID_DECIMAL
coefficient/exponent beyond profile -> OVERFLOW
97-byte Tiny JSON decimal string -> RESOURCE_LIMIT
```

### Rounding

Cover positive and negative values for every mode, with half-even ties ending in even and odd retained digits. Include scale zero and scale eighteen, exact values, nonzero remainders, and scaling overflow.

### Error precedence

At minimum:

- bad operation plus bad arguments -> `UNKNOWN_OPERATION`;
- correct operation plus wrong count -> `ARGUMENT_COUNT`;
- invalid first decimal plus invalid later decimal -> first argument's `INVALID_DECIMAL`;
- negative price plus mismatched units -> price `CONSTRAINT_VIOLATION` first;
- valid constraints plus mismatched units -> `UNIT_MISMATCH`;
- zero price and unchanged price -> price `CONSTRAINT_VIOLATION`, not divide by zero;
- too-small output after valid evaluation -> `BUFFER_TOO_SMALL` with required size and no partial bytes.

### ABI/memory

- C99 and C++11 headers compile with warnings as errors;
- public structure size/alignment/offset records for 32-bit and 64-bit ABIs;
- null/zero and null/nonzero slice cases;
- misaligned context/result/meta pointers;
- integer overflow in every `offset + length` calculation;
- input/output overlap rejection;
- output/scratch/context overlap rejection;
- same context reset behavior;
- no borrowed metadata survives reset.

### Tiny JSON

- valid `xs_find` and `xs_eval`;
- reversed object field order accepted but canonical response order emitted;
- duplicate/unknown/missing keys rejected;
- JSON number instead of string rejected;
- escaped ASCII query accepted;
- malformed UTF-8 rejected;
- one-byte truncation at every request byte;
- request at maximum size and one byte above it;
- result copied exactly without model-style natural-language formatting.

## 14. Required cross-path equivalence

For every shared vector, compare this normalized tuple:

```text
status
result flags
value count
canonical value string(s)
classification key/id
pack id/version/digest
operation id/revision/key
output scale
rounding mode
argument index/detail code on failure
```

The following paths must agree:

1. direct kernel/typed Rust evaluation;
2. fused registry evaluation;
3. C ABI evaluation and C JSON serializer;
4. native Tiny JSON adapter;
5. fused `wasm32v1-none` Tiny JSON helper;
6. later dynamic `.xsp` evaluation before the operation is called complete.

Do not normalize away a mismatch in the conformance harness. Different bytes indicate a defect or a versioned semantic change.

## 15. Pull-request order

Keep reviewable commits in this order:

1. status/semantic/rounding constants generated from registries;
2. `Decimal64` parser, canonicalization, formatter, and tests;
3. exact rational arithmetic and rounding tests;
4. VM validation/execution subset;
5. operation validation and fused `econ.ped.mid` table;
6. typed evaluation and shared golden vectors;
7. C ABI layouts and calls;
8. Tiny JSON bounded parser/serializer;
9. no-import Wasm exports and memory validation;
10. native/Wasm byte-equivalence harness and size report.

Each step must keep the workspace tests green. Do not combine a failed portability experiment with semantic changes.

## 16. Commands that define completion

The first slice is complete only when equivalent repository commands exist and pass:

```text
python tools/validate_design.py
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace
cargo check --target wasm32v1-none --no-default-features \
  --package exactscope-kernel \
  --package exactscope-pack \
  --package exactscope-wasm
cc -std=c99 -pedantic-errors -Wall -Wextra -Werror \
  -Iinclude -fsyntax-only tests/abi/header_c.c
c++ -std=c++11 -pedantic-errors -Wall -Wextra -Werror \
  -Iinclude -fsyntax-only tests/abi/header_cpp.cpp
```

Additional release checks:

```text
inspect fused wasm imports/features/exports
run shared vectors through desktop Wasm engine
run shared vectors through one embedded WebAssembly runtime
compare native and Wasm canonical output bytes
record stripped core/fused sizes and maximum scratch
```

## 17. Definition of done

The slice is done only when all statements are true:

- one source of calculation semantics exists;
- no runtime crate requires `std`, a global allocator, network, filesystem, clock, random, locale, or threads;
- the exact five economics fixture cases pass;
- all new numeric, parser, ABI, and error-precedence cases pass;
- C99 and C++11 consumers compile;
- the fused Wasm module imports nothing and uses the documented memory contract;
- native and Wasm canonical results are byte-identical;
- the complete fused economics artifact and scratch stay inside the README budgets;
- no unsupported platform is called supported;
- no benchmark or accuracy improvement is claimed without measurement;
- the repository remains usable without any human-facing UI or daemon.

After this gate, implementation may proceed to the dynamic pack compiler/loader and then expand the official operation catalog. Until then, adding formulas only multiplies unproven compatibility risk.
