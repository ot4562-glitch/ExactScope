# Core ABI v0.1

This document defines the logical ABI major `1`, minor `0`. The generated `exactscope.h` is the final C syntax authority and must conform to this document.

## 1. ABI goals

- usable from C99, C++, Rust, Kotlin/JNI, Swift bridging, Zig, Go/cgo, and other FFI-capable hosts;
- no mandatory heap or process-wide initialization;
- no filesystem or network dependency;
- no Rust-specific layout exposed;
- no exception or unwind crossing the boundary; malformed input returns typed status rather than panic/trap;
- fixed-width status and identity fields;
- caller-owned buffers and explicit lifetimes;
- same logical surface in no-import WebAssembly.

## 2. Common types

```c
typedef uint16_t xs_status;
typedef struct xs_context xs_context;
```

The public header defines numeric constants rather than C enums for versioned values.

### 2.1 Byte slice

```c
typedef struct xs_bytes_v1 {
    const uint8_t* ptr;
    uint32_t len;
} xs_bytes_v1;
```

A zero-length slice may use a null pointer. A nonzero length with a null pointer is invalid.

### 2.2 Decimal value

```c
typedef struct xs_decimal_v1 {
    int64_t coefficient;
    int8_t exponent;
    uint8_t semantic_kind;
    uint16_t unit_id;
    uint32_t flags;
} xs_decimal_v1;
```

Required size: 16 bytes on conforming ABIs. Fields are host-endian in memory. Pack and wire representations are decoded explicitly.

Value flags v1:

| Bit | Key | Meaning |
|---:|---|---|
| 0 | `INEXACT` | value depends on a bounded irrational/numerical result |
| 1 | `ROUNDED` | final output differs from the exact work value |
| 2–31 | reserved | must be zero on input |

### 2.3 Value reference

```c
#define XS_VALUE_SCALAR_V1 0u
#define XS_VALUE_VECTOR_V1 1u

typedef struct xs_value_ref_v1 {
    uint32_t struct_size;
    uint8_t value_kind;
    uint8_t reserved0;
    uint16_t reserved1;
    const xs_decimal_v1* values;
    uint32_t value_count;
    uint32_t reserved2;
} xs_value_ref_v1;
```

For a scalar, `value_count` is exactly one. For a vector, it is within the operation/global bound. Referenced values need remain valid only for the duration of `xs_eval`.

## 3. Configuration

```c
typedef struct xs_config_v1 {
    uint32_t struct_size;
    uint16_t abi_major;
    uint16_t abi_minor;
    uint16_t max_packs;
    uint16_t max_find_matches;
    uint16_t max_vector_len;
    uint16_t flags;
    uint32_t max_tinywire_frame;
    uint32_t reserved[3];
} xs_config_v1;
```

Configuration flags:

| Bit | Key | Meaning |
|---:|---|---|
| 0 | `ALLOW_DYNAMIC_PACKS` | caller may mount validated `.xsp` bytes |
| 1 | `FREEZE_AFTER_INIT` | registry is immutable after initialization callback/sequence |
| 2 | `ENABLE_DISCOVERY` | include alias lookup support |
| 3–15 | reserved | zero |

A minimum fused build may ignore dynamic pack fields and expose a fixed-size context.

## 4. Match structure

```c
typedef struct xs_match_v1 {
    uint32_t struct_size;
    uint16_t pack_slot;
    uint16_t operation_revision;
    uint32_t operation_id;
    uint16_t rank;
    uint16_t flags;
    xs_bytes_v1 operation_key;
    xs_bytes_v1 signature;
    xs_bytes_v1 method_key;
    uint32_t reserved[2];
} xs_match_v1;
```

Returned slices borrow immutable pack/context memory and remain valid until pack unmount, registry mutation, or context reset. Frozen registries keep them valid for context lifetime.

Rank is deterministic ordering, not a probabilistic confidence score.

## 5. Evaluation options

```c
#define XS_USE_OPERATION_SCALE_V1 (-128)
#define XS_USE_OPERATION_ROUNDING_V1 255u

typedef struct xs_eval_options_v1 {
    uint32_t struct_size;
    int8_t output_scale;
    uint8_t rounding_mode;
    uint16_t flags;
    uint32_t reserved[3];
} xs_eval_options_v1;
```

Flags:

| Bit | Key | Meaning |
|---:|---|---|
| 0 | `INCLUDE_PROVENANCE` | adapter serialization includes pack/key/revision fields |
| 1 | `REQUIRE_CLASSIFICATION` | return `PRECISION_UNRESOLVED` if class cannot be proven |
| 2–15 | reserved | zero |

An operation may reject caller overrides and require its declared output policy.

## 6. Result structure

v0.1 supports at most four scalar outputs per operation.

```c
#define XS_MAX_RESULT_VALUES_V1 4u

typedef struct xs_result_v1 {
    uint32_t struct_size;
    uint16_t status;
    uint16_t flags;
    uint16_t value_count;
    uint16_t classification_id;
    uint16_t pack_slot;
    uint16_t operation_revision;
    uint32_t operation_id;
    int8_t output_scale;
    uint8_t rounding_mode;
    uint16_t detail_code;
    uint16_t argument_index;
    uint16_t reserved0;
    uint32_t required_size;
    xs_decimal_v1 values[XS_MAX_RESULT_VALUES_V1];
    uint32_t reserved[4];
} xs_result_v1;
```

Rules:

- `status` duplicates the function status for transport/storage convenience;
- `value_count` is zero on failure;
- unused `values` entries are zeroed;
- `classification_id` zero means no classification;
- `argument_index` is `0xffff` when not applicable;
- `required_size` is used by buffer/arena failures;
- output flags include aggregate rounded/inexact indicators;
- no borrowed pointers appear in the result.

## 7. Required functions

### 7.1 Version

```c
uint32_t xs_abi_version(void);
```

Returns `(major << 16) | minor`.

### 7.2 Context sizing and initialization

```c
uint32_t xs_context_align(void);
uint32_t xs_context_size(const xs_config_v1* config);
xs_status xs_context_init(
    void* memory,
    uint32_t memory_len,
    const xs_config_v1* config,
    xs_context** out_context);
xs_status xs_context_reset(xs_context* context);
```

Rules:

- sizing performs no allocation;
- zero return from `xs_context_size` indicates invalid/unsupported configuration;
- memory address must satisfy `xs_context_align`;
- `xs_context_init` initializes only caller memory;
- reset invalidates borrowed slices and mounted dynamic pack registrations;
- fused pack tables remain available after reset.

### 7.3 Pack mounting

```c
xs_status xs_pack_mount(
    xs_context* context,
    const uint8_t* pack_bytes,
    uint32_t pack_len,
    void* arena,
    uint32_t arena_len,
    uint16_t* out_pack_slot,
    uint32_t* required_arena_len);

xs_status xs_pack_unmount(xs_context* context, uint16_t pack_slot);
xs_status xs_registry_freeze(xs_context* context);
```

Rules:

- pack bytes remain immutable and alive while mounted;
- arena may be null/zero if the pack's prebuilt index can be used without copied state;
- insufficient arena returns `BUFFER_TOO_SMALL` with required size;
- no partial mount remains after failure;
- unmount is forbidden after freeze;
- pack slot zero is reserved; valid slots start at one.

Fused builds may pre-register packs and return `UNSUPPORTED_OPERATION` from dynamic mount functions when the feature is absent.

### 7.4 Direct lookup and discovery

```c
xs_status xs_lookup(
    xs_context* context,
    const uint8_t* operation_key,
    uint32_t operation_key_len,
    uint16_t* out_pack_slot,
    uint32_t* out_operation_id,
    uint16_t* out_operation_revision);

xs_status xs_find(
    xs_context* context,
    const uint8_t* query,
    uint32_t query_len,
    xs_match_v1* matches,
    uint16_t match_capacity,
    uint16_t* out_match_count);
```

Rules:

- keys and queries are UTF-8 byte slices;
- direct lookup is exact and case-sensitive over canonical keys;
- discovery applies the deterministic normalization/ranking contract;
- no match returns `UNKNOWN_OPERATION` and count zero;
- too-small match capacity returns `BUFFER_TOO_SMALL`, writes no semantically usable match entries, and sets `out_match_count` to the full required count; the caller may retry unchanged with that bounded capacity.

### 7.5 Evaluation

```c
xs_status xs_eval(
    xs_context* context,
    uint16_t pack_slot,
    uint32_t operation_id,
    const xs_value_ref_v1* args,
    uint16_t arg_count,
    const xs_eval_options_v1* options,
    void* scratch,
    uint32_t scratch_len,
    xs_result_v1* out_result);
```

Rules:

- evaluation is synchronous;
- scratch may be null only when required scratch is zero;
- insufficient scratch returns `BUFFER_TOO_SMALL` and required size in the result;
- the core does not retain argument/scratch pointers;
- first public error follows `ERRORS_V0_1.md` precedence;
- result is fully initialized on every return when `out_result` is valid;
- a successful result is canonical and contains no string pointers.

### 7.6 Metadata serialization

```c
xs_status xs_result_json(
    xs_context* context,
    const xs_result_v1* result,
    uint8_t* output,
    uint32_t output_capacity,
    uint32_t* out_written_or_required);

xs_status xs_match_json(
    const xs_match_v1* matches,
    uint16_t match_count,
    uint8_t* output,
    uint32_t output_capacity,
    uint32_t* out_written_or_required);
```

These helpers emit canonical Tiny JSON. They are optional in the minimum fused kernel and may live in `exactscope-tinyjson`.

## 8. Null, overlap, and lifetime rules

- Required output pointers must not be null.
- Null plus zero length is valid only for documented size-query or empty-slice cases.
- Input/output buffers must not overlap unless a function explicitly allows it; v0.1 allows no in-place serialized transformation.
- A context memory block cannot overlap pack bytes, arena, arguments, scratch, or output.
- The library does not spawn threads or retain callbacks.
- Host synchronization is required for concurrent mutation. Concurrent evaluation on one frozen context is supported only after the implementation proves internal immutability; until then, one context per worker is normative.

## 9. Panic and memory safety

Every external input path must use explicit validation and return typed failures without panicking. Minimum `no_std` native and `wasm32v1-none` release artifacts use `panic=abort`; they do not promise to catch a panic and convert it into `INTERNAL_ERROR`. A `std`-enabled desktop wrapper may use `catch_unwind` only as an additional containment layer, never as normal input validation. No unwind may cross an `extern "C"` boundary. `INTERNAL_ERROR` represents an invariant failure detected explicitly without panicking; any actual panic/abort is an implementation defect and fails conformance.

Unsafe code is permitted only for:

- converting validated pointer/length pairs to slices;
- in-place context initialization;
- exported ABI boundaries;
- narrowly documented generated tables if required.

Every unsafe block requires an adjacent safety invariant comment and dedicated tests.

## 10. WebAssembly mapping

The `wasm32v1-none` module maps this logical ABI to 32-bit linear-memory offsets. Exact memory ownership, required exports, one-call Tiny JSON/TinyWire helper, buffer metadata, trap policy, linker layout, and module-inspection gates are normative in [`WASM_ABI_V0_1.md`](WASM_ABI_V0_1.md) and `include/exactscope_wasm.h`.

The WebAssembly wrapper delegates to the same registry/evaluator and cannot become a separate calculation implementation. Canonical native and WebAssembly result bytes must match the shared conformance corpus.

## 11. Symbol visibility

Release libraries export only documented `xs_*` symbols. Internal Rust/C symbols are hidden. The ABI test compares the exported symbol list against a checked manifest.

## 12. ABI evolution

Backward-compatible additions may:

- add new functions;
- use previously reserved flag bits after a minor-version increase;
- add larger struct versions with new names;
- add optional result metadata.

Breaking changes include:

- changing existing field meaning or offset;
- changing status values;
- changing pointer ownership/lifetime;
- changing numeric semantics;
- requiring allocation where none was required;
- removing or renaming a symbol.

Breaking changes require ABI major 2 and parallel support or a clearly versioned migration.
