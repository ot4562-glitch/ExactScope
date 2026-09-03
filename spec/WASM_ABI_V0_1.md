# No-import WebAssembly ABI v0.1

This document defines the portable WebAssembly profile for ExactScope ABI major `1`, minor `0`. It is normative for fused `wasm32v1-none` artifacts and for any generic WebAssembly artifact that claims ExactScope conformance.

## 1. Target and feature baseline

The release target is `wasm32v1-none`.

A conforming v0.1 module:

- imports no functions, memories, tables, or globals;
- uses no WASI interface;
- requires no threads, shared memory, SIMD, exceptions, reference types, garbage collection, memory64, or multiple memories;
- exports exactly one 32-bit linear memory;
- uses `panic=abort` and must not rely on unwinding;
- performs no filesystem, network, clock, random, environment, or host-service access;
- exposes only documented `xs_*` functions plus the exported memory and explicitly allowlisted toolchain globals.

The WebAssembly 1.0 feature baseline and no-import property are release gates, not best-effort preferences.

## 2. Artifact profiles

### 2.1 Fused profile

The core and selected scope packs are compiled into one module. The registry is immutable and available immediately after instantiation.

Required exports:

```text
memory
xs_abi_version
xs_wasm_reserved_end
xs_wasm_memory_alignment
xs_wire_request
```

The typed context/evaluation exports from the C ABI may also be exposed. The one-call wire helper is required for the smallest integration profile.

### 2.2 Generic profile

A generic module may expose the complete logical C ABI for caller-supplied `.xsp` bytes. It follows the same pointer, lifetime, and result semantics as `include/exactscope.h`, with native pointers represented as 32-bit offsets.

Dynamic packs remain data. A generic module cannot instantiate, link, or execute WebAssembly received from a pack.

## 3. Linear-memory ownership

The module owns all bytes below the value returned by:

```c
uint32_t xs_wasm_reserved_end(void);
```

That boundary includes code-related data segments, immutable fused-pack data, the module stack, and any runtime-private fixed storage. The release linker layout must place the stack before static data and the host region after the exported reserved boundary. The build must export or wrap the linker heap boundary used to derive this value.

The host owns bytes at or above `xs_wasm_reserved_end()` only after it has grown the exported memory to cover them. Host-owned regions must:

- begin at an address aligned to `xs_wasm_memory_alignment()`;
- be nonoverlapping for the duration of a call;
- remain inside the current 32-bit memory size;
- not overlap module-owned bytes;
- remain immutable when passed as input;
- remain exclusively writable when passed as output, context, arena, or scratch.

ExactScope never allocates, frees, grows memory, or retains a host-region offset after the call that consumes it. The host may reuse a region once the call returns and all documented borrowed slices have expired.

The minimum fused wire helper is stateless between calls and requires no context region. Generic typed calls follow the context lifetime rules in `CORE_ABI_V0_1.md`.

## 4. Address and range validation

Every offset/length pair is validated using checked unsigned arithmetic before a byte is read or written.

For a region `[offset, offset + length)` the implementation must reject:

- addition overflow;
- an end beyond current linear memory;
- a nonzero length with offset zero when that parameter is required;
- an offset below the reserved boundary for host-owned input/output;
- insufficient alignment for typed structures;
- forbidden input/output overlap;
- overlap with context, arena, scratch, or another mutable output region.

Malformed addresses return `INVALID_REQUEST`. Insufficient output capacity returns `BUFFER_TOO_SMALL`. Valid in-memory malformed requests must not intentionally trap.

A hardware or host that passes an address outside instantiated linear memory may itself trap before ExactScope can observe the call; such a host call is outside the ABI contract.

## 5. Scalar ABI mapping

C fixed-width integers map to WebAssembly scalar parameters as follows:

| C logical type | WebAssembly value |
|---|---|
| `uint8_t`, `uint16_t`, `uint32_t`, pointers | `i32` |
| `int8_t`, `int16_t`, `int32_t` | `i32` with documented sign interpretation |
| `uint64_t`, `int64_t` | `i64` |

Public structures are transferred through linear memory and retain the byte layouts defined by `include/exactscope.h`. Structure fields use little-endian byte order in the WebAssembly profile. Callers must not rely on a host language's native object layout.

The generic exported functions use the same names and logical arguments as the C ABI where practical. Return statuses are zero-extended `i32` values containing the stable `xs_status` code.

## 6. Fused one-call helper

The AI-runtime convenience export is:

```c
xs_status xs_wire_request(
    uint32_t wire_format,
    uint32_t input_offset,
    uint32_t input_len,
    uint32_t output_offset,
    uint32_t output_capacity,
    uint32_t meta_offset);
```

`wire_format` values:

| Value | Key | Payload |
|---:|---|---|
| 1 | `tiny_json` | Tiny JSON request and response |
| 2 | `tiny_cbor` | deterministic-CBOR TinyWire payload without stream frame |

The helper:

1. validates all three memory regions and their non-overlap;
2. validates request size before parsing;
3. parses exactly one request;
4. delegates to the same frozen registry and evaluator used by typed calls;
5. serializes one complete response or no response;
6. initializes the metadata structure on every return when `meta_offset` is valid.

It performs no discovery or calculation logic separate from the core.

## 7. Metadata record

`meta_offset` references this 16-byte little-endian record:

```c
typedef struct xs_wasm_io_meta_v1 {
    uint32_t struct_size;
    uint16_t status;
    uint16_t flags;
    uint32_t written;
    uint32_t required;
} xs_wasm_io_meta_v1;
```

Input requirements:

- `meta_offset` is four-byte aligned;
- at least 16 writable bytes are available;
- `struct_size` is initialized to `16` by the host;
- all other fields may contain any value and are overwritten.

Output rules:

- `status` equals the function return status;
- `written` is the complete response byte length written on `OK`;
- `required` is the exact required output capacity on `BUFFER_TOO_SMALL`, otherwise zero;
- flag bit 0 (`OUTPUT_WRITTEN`) is set only when a complete response was written;
- no partial response is semantically usable;
- reserved flag bits are zero.

If the metadata region itself is invalid, the function returns `INVALID_REQUEST` and writes nothing.

## 8. Buffer-too-small behavior

The helper validates and evaluates the request before determining the exact serialized response size. When output capacity is insufficient:

- return `BUFFER_TOO_SMALL`;
- write no partial response;
- set `written` to zero;
- set `required` to the complete required byte length;
- allow the host to resize/grow its output region and retry with identical input bytes.

A retry must not alter values, operation key, units, method, or assumptions.

## 9. Reentrancy and concurrency

The fused helper has no mutable global request state and is reentrant at the logical level. v0.1 WebAssembly uses one non-shared memory and claims no threaded execution support. A host must not interleave calls that write overlapping regions.

A generic module with mutable contexts requires one context per worker unless a later conformance record explicitly marks a frozen context safe for shared concurrent evaluation.

## 10. Panic and trap policy

`wasm32v1-none` uses aborting panics. Therefore:

- malformed external input must be handled through explicit checks and typed status returns;
- internal indexing must use validated ranges or checked access;
- the implementation must not promise to catch a panic and convert it to `INTERNAL_ERROR`;
- an internal panic/abort/trap is an implementation defect and fails conformance;
- `INTERNAL_ERROR` is returned only for invariants detected explicitly without panicking;
- malformed-input and fuzz corpora must demonstrate no unexpected traps.

This distinction prevents an impossible recovery promise on an abort-only target.

## 11. Link and export policy

The fused release build must use a reproducible linker configuration that:

- emits no start function requiring host initialization;
- exports memory;
- uses a stack-first layout or another reviewed layout that makes the reserved boundary authoritative;
- hides non-ABI functions;
- preserves the `wasm32v1-none` baseline;
- does not use linker-plugin LTO until the produced module is independently inspected for forbidden imports/features;
- emits a deterministic export allowlist checked in CI.

Size optimization may use normal LTO only after import/feature inspection and conformance pass. Toolchain or linker changes that alter layout, features, exports, or result bytes require a compatibility record.

## 12. Module inspection gates

Each released module is inspected to verify:

- zero imports;
- one exported 32-bit memory;
- required exports present;
- no unexpected exports;
- no start function that performs host-dependent work;
- no forbidden post-baseline features;
- declared minimum/maximum memory within profile policy;
- stripped byte size;
- canonical conformance digest.

The release compatibility manifest records the Rust toolchain, linker, flags, artifact hash, import count, export list digest, size, and conformance result.

## 13. Embedded-runtime acceptance

A `wasm32v1-none` artifact becomes Tier 1 only after the same binary executes the shared corpus in:

1. a desktop reference engine;
2. at least one lightweight WebAssembly 1.0 embedded runtime;
3. at least one real or official-emulator target from the compatibility matrix.

Compilation alone is not a support claim.

## 14. Versioning

The WebAssembly helper ABI follows C ABI major/minor `1.0`. Adding exports is a compatible ABI-minor change when existing memory, argument, result, and failure semantics are unchanged. Changing region ownership, structure layout, wire format IDs, or buffer behavior requires an ABI-major change.
