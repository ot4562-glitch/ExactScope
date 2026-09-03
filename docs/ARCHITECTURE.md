# ExactScope architecture baseline v0.1

This document is normative for the first implementation unless a later architecture decision explicitly supersedes it.

## 1. System boundary

ExactScope is a deterministic quantitative execution component embedded inside another AI system.

The host owns:

- camera, microphone, sensor, and user interaction;
- speech recognition and natural-language understanding;
- extraction of values from the user request;
- deciding when to call `xs_find` or `xs_eval`;
- rendering or speaking the returned machine result;
- optional pack signature/checksum policy;
- persistent storage and updates.

ExactScope owns:

- operation discovery over installed aliases;
- exact operation identity and method selection;
- argument count/type/constraint validation;
- unit compatibility checks;
- deterministic calculation;
- explicit rounding;
- deterministic result classification;
- typed failure codes;
- operation and pack provenance.

ExactScope does not own natural-language generation, general symbolic reasoning, forecasting, internet data retrieval, or model inference.

## 2. Frozen workspace boundaries

```text
crates/
  exactscope-kernel/      # no_std numeric model, VM, validation, kernels
  exactscope-pack/        # pack parser, registry, alias index; alloc optional
  exactscope-cabi/        # stable C ABI wrapper
  exactscope-wasm/        # wasm32v1-none exports, no imports
  exactscope-tinyjson/    # optional host adapter, not linked into minimum core
  exactscope-packc/       # desktop build-time pack compiler and validator
  exactscope-conformance/ # shared golden-vector runner
adapters/
  llama-cpp/
  openai-tools/
  mcp/
packs/
  math-basic/
  statistics-core/
  econ-undergrad/
include/
  exactscope.h
  exactscope_wasm.h
spec/
  schemas/
  registries/
  examples/
docs/
```

Only `exactscope-kernel`, the minimal pack registry, and one selected pack are required for a fused deployment. Files under `spec/registries/` are the machine-readable source of truth for stable IDs and generated constants; prose tables cannot override them.

## 3. Component model

### 3.1 `exactscope-kernel`

Required properties:

- `#![no_std]`;
- no filesystem, sockets, clocks, environment variables, process APIs, locale APIs, or random-number source;
- no global allocator in the default feature set;
- malformed external input follows non-panicking checked paths; no unwind crosses public boundaries, and any panic/abort is a conformance defect;
- no binary floating-point in the baseline deterministic profile;
- no unsafe code except in narrowly reviewed ABI/memory adapters;
- no mutable global state;
- bounded instruction count, stack depth, vector length, and output size.

Responsibilities:

- `Decimal64` parsing and canonicalization;
- checked scalar arithmetic;
- deterministic bounded numeric kernels;
- scalar formula VM;
- input constraints and same-unit groups;
- classification rules;
- canonical result encoding.

### 3.2 `exactscope-pack`

Responsibilities:

- validate `.xsp` headers and section bounds;
- reject unsupported format/ABI versions;
- reject duplicate operation IDs or keys;
- validate VM stack behavior before registration;
- build or reference a deterministic alias index;
- mount packs from immutable caller-owned bytes;
- support static/fused registries without allocation;
- support dynamic registries through a caller-provided arena.

The loader never dynamically links code. Pack contents are data interpreted by bounded core logic.

### 3.3 `exactscope-packc`

Desktop/build-time tool only. It may use `std` and normal development dependencies.

Responsibilities:

1. validate source JSON against the scope-pack schema;
2. validate unique pack/operation identity;
3. validate program stack and resource limits;
4. validate aliases and canonical keys;
5. run every golden test vector;
6. compile source operations into canonical `.xsp` bytes;
7. produce a manifest containing pack digest, operation count, and size;
8. optionally generate fused Rust/C byte arrays and adapter catalogs.

The runtime contains no general expression parser. Source programs use a typed RPN instruction list that maps directly to validated VM bytecode.

### 3.4 ABI and adapters

The C ABI is the portability foundation and is frozen syntactically by `include/exactscope.h`. WebAssembly exposes the same logical operations through 32-bit offset/length exports and the memory contract in `spec/WASM_ABI_V0_1.md`. Language SDKs wrap these boundaries rather than reimplementing calculations.

AI adapters are outside the core trust boundary. They translate model-generated Tiny JSON into typed core calls and translate typed results back into compact JSON. Adapters may not calculate results or repair invalid arguments silently.

## 4. Installation profiles

### 4.1 Fused profile

A generated artifact contains the kernel and selected pack data.

Use when:

- storage and RAM are severely constrained;
- pack updates track firmware/app releases;
- no filesystem is available;
- the smallest binary and simplest installation are priorities.

Properties:

- no pack parser required after build-time validation;
- no runtime heap required;
- direct operation table lookup;
- one distributable artifact possible.

### 4.2 Static registry profile

The host links the core and embeds one or more compiled `.xsp` byte arrays.

Properties:

- pack loader validates the embedded bytes at startup;
- no filesystem required;
- no runtime native plugin loading;
- caller controls storage location;
- evaluation remains heap-free after registration.

### 4.3 Dynamic data-pack profile

The host reads or downloads `.xsp` files and passes immutable bytes to ExactScope.

Properties:

- core performs complete structural validation;
- host provides registry/index memory;
- official and third-party packs can be replaced independently;
- cryptographic signature policy remains a host responsibility in v0.1;
- malformed or unsupported packs fail closed.

## 5. Execution pipeline

```text
AI adapter request
  -> parse flat Tiny JSON
  -> resolve canonical operation key
  -> locate mounted pack and operation
  -> validate argument count and lexical form
  -> parse canonical Decimal64 values
  -> validate semantic constraints and unit groups
  -> execute formula VM or built-in bounded kernel
  -> classify using unrounded internal result
  -> round output using operation policy
  -> attach provenance
  -> encode compact machine response
```

No stage invokes a language model.

## 6. Numeric profiles

### 6.1 Required baseline: `decimal64-v1`

Wire value:

```text
value = coefficient * 10^exponent
coefficient: signed 64-bit integer
exponent: signed integer in [-18, 18]
```

Canonical form:

- zero is `(0, 0)`;
- trailing decimal zeroes are removed when the exponent can increase;
- negative zero is forbidden;
- lexical inputs forbid NaN, Infinity, commas, locale separators, and implicit percentages;
- overflow returns an error; values never saturate or wrap.

Checked wider intermediates may use signed 128-bit arithmetic. If a target cannot provide the required semantics, it does not conform to `decimal64-v1`.

### 6.2 Optional future profiles

- `decimal128` for larger ranges;
- exact rational arithmetic for selected packs;
- explicitly non-bit-stable native floating point for optional scientific packs.

Official v0.1 packs may only require `decimal64-v1` and deterministic kernels implemented by the baseline core.

## 7. Formula VM

The scalar VM is deliberately non-Turing-complete.

Required v0.1 instruction families:

- `ARG index`
- `CONST index`
- `ADD`, `SUB`, `MUL`, `DIV`
- `NEG`, `ABS`
- `MIN`, `MAX`
- `POWI signed_exponent`
- `SQRT`
- `CMP_LT`, `CMP_LE`, `CMP_EQ`, `CMP_GE`, `CMP_GT`
- `SELECT`
- `ROUND scale mode`
- `END`

Rules:

- no jumps, loops, calls, recursion, indirect dispatch, or memory access instructions;
- program length at most 64 instructions by default;
- declared maximum stack depth at most 16 by default;
- exactly one value must remain at `END`;
- division by zero, invalid roots, overflow, and precision failure stop evaluation;
- `POWI` exponent bounds are pack-validated;
- `SQRT` uses one specified fixed-point algorithm and rounding contract on every target.

Operations over vectors use built-in kernel IDs rather than VM loops. Initial kernels may include sum, mean, weighted mean, population/sample variance, covariance, correlation, and simple linear regression. Every kernel has explicit vector limits and deterministic iteration order.

## 8. Classification

Classification is pack data, not model inference.

A classification table contains ordered, mutually exclusive predicates over the unrounded internal result. The compiler rejects overlapping or uncovered tables unless the operation explicitly permits `unclassified`.

Example:

```text
abs(result) < 1  -> inelastic
abs(result) = 1  -> unit_elastic
abs(result) > 1  -> elastic
```

The displayed value may be rounded, but classification uses the pre-rounding value. This prevents a value such as `0.9999996` from being classified as exactly one merely because six-decimal output renders `1.000000`.

## 9. Unit model

ExactScope v0.1 performs compatibility checks, not general unit conversion.

Each argument declares:

- semantic kind, such as `price`, `quantity`, `rate_percent`, `rate_ratio`, `time_periods`, `currency_amount`, `index`, or `count`;
- optional unit dimension;
- optional same-unit group.

The adapter may attach compact unit IDs. Zero means unspecified. Operations that require comparable units reject conflicting nonzero IDs. No currency, time-period, or physical-unit conversion occurs unless a separate deterministic operation explicitly defines it.

Percentage and ratio inputs are distinct semantic kinds. An operation expecting `rate_percent` interprets `5` as five percent; an operation expecting `rate_ratio` requires `0.05`. The signature exposes this distinction through names such as `rate_pct` and `rate_ratio`.

## 10. Discovery

The core is not a semantic-search engine.

Supported paths:

1. direct canonical operation key;
2. exact alias match;
3. deterministic token/prefix ranking over pre-normalized pack aliases;
4. bounded enumeration by pack/domain.

The baseline core uses pre-normalized UTF-8 aliases and an ASCII-oriented query normalizer. Locale-heavy normalization or embeddings belong in optional host adapters. Official packs should provide concise English aliases; locale lexicons can be separate data packs so multilingual discovery does not enlarge every fused artifact.

`xs_find` returns at most the caller-specified bounded count and includes canonical operation key, compact signature, method tag, and argument semantic names.

## 11. Memory ownership

- The host owns pack bytes, request bytes, output buffers, and optional arenas.
- The core does not retain request pointers after a call.
- Registered dynamic pack bytes must remain immutable and alive until unmounted or context destruction.
- Fused/static tables are immutable.
- Output functions report required buffer size rather than allocating.
- Evaluation scratch comes from context-owned fixed storage or a caller-provided scratch buffer.

## 12. Concurrency

The kernel is stateless per evaluation. A frozen registry may be shared across threads if the host provides synchronization around context mutation. v0.1 does not require threads or atomics and the no-import WebAssembly build exposes no threading dependency.

The simplest supported integration is one context per AI worker.

## 13. Security boundary

Pack parsing is an untrusted-input boundary even though packs contain no native code.

The implementation must:

- validate every offset and length before dereference;
- avoid unaligned native reads;
- cap counts before multiplication or allocation;
- reject integer overflow in section calculations;
- validate string encoding and termination rules;
- validate VM programs before registration;
- enforce runtime resource limits independently of pack claims;
- never panic or trap on malformed pack data;
- fuzz pack loading and TinyWire decoding.

See [SECURITY.md](../SECURITY.md).

## 14. Engineering budgets

Normative v0.1 defaults:

| Resource | Default limit |
|---|---:|
| Mounted packs | 8 |
| Operations per pack | 4096 |
| Scalar args | 12 |
| Vector args | 4 |
| Vector length | 256 |
| VM instructions | 64 |
| VM stack | 16 values |
| Alias query bytes | 96 |
| Discovery matches | 5 |
| Tiny JSON request bytes | 512 hard maximum |
| TinyWire frame bytes | 4096 hard maximum |
| Evaluation scratch | 2048 bytes target |

A pack may request lower limits. Raising global limits requires an architecture decision and footprint measurements.

## 15. Non-negotiable invariants

1. The minimum core remains usable with no OS and no network.
2. Official packs never contain native executable code.
3. Baseline results never depend on locale, clock, random state, thread scheduling, or host floating-point mode.
4. Invalid or ambiguous requests never receive guessed numeric answers.
5. Language-specific adapters never become calculation authorities.
6. A new platform is not marked supported until it passes the same conformance corpus.
7. Operation semantics cannot change under an existing operation revision.
8. The smallest installation remains a fused artifact with no daemon and no heap requirement.
