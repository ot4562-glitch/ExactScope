# Compatibility contract

Compatibility is ExactScope's primary product requirement. A port that merely compiles is not a supported port.

## 1. Compatibility definition

A target is **supported** only when all of the following are true for the same released core and pack artifacts:

1. the target builds from a clean checkout with documented tooling;
2. the C ABI or WebAssembly ABI conformance suite passes;
3. every shared golden vector produces the same canonical result bytes;
4. malformed-pack and malformed-request negative tests pass;
5. size and memory budgets are recorded;
6. the release artifact is generated in CI or an equivalent reproducible release job;
7. at least one real target or official emulator run is recorded.

Status vocabulary:

- **Tier 1:** release-blocking CI plus real/emulated runtime conformance;
- **Tier 2:** build and conformance are automated, but hardware coverage is narrower;
- **Experimental:** builds may exist, but compatibility is not promised;
- **Planned:** design target only.

No README badge may call a target supported without meeting this definition.

## 2. v0.1 target matrix

| Environment | Target/artifact | Initial status goal | Notes |
|---|---|---|---|
| Portable WebAssembly | `wasm32v1-none` | Tier 1 | WebAssembly 1.0 baseline, no imports, no WASI, no threads, no SIMD requirement |
| Android phones/wearables | `arm64-v8a` AAR/native library | Tier 1 | Primary mobile target |
| Android older/low-cost ARM | `armeabi-v7a` | Tier 2 | Keep scalar fallback; test 32-bit overflow paths |
| Android emulator/Chromebook | `x86_64` | Tier 2 | No AVX requirement |
| Linux edge | AArch64 GNU and musl | Tier 1 | Raspberry Pi/edge companion class |
| Linux desktop/dev | x86-64 GNU and musl | Tier 1 | Reference native target |
| Windows | x86-64 MSVC | Tier 1 | DLL, import library, static library, C header |
| macOS | Apple Silicon | Tier 1 | Static/dynamic C ABI library |
| macOS Intel | x86-64 | Tier 2 | Compatibility target, not performance priority |
| iOS companion | arm64 XCFramework | Tier 2 | Same logical C ABI; no network requirement |
| Bare-metal ARM | `thumbv7em-none-eabihf` or equivalent | Experimental | Must prove no allocator and bounded stack |
| Bare-metal RISC-V | `riscv32imac-unknown-none-elf` or equivalent | Experimental | No FPU assumption in baseline |

The exact Rust target triples may change if upstream toolchain support changes; the ABI and conformance requirements do not.

## 3. WebAssembly baseline

The primary portable artifact targets `wasm32v1-none` because it is limited to the WebAssembly 1.0 feature baseline, provides no `std`, and imports nothing from the host.

The v0.1 module must not require:

- WASI;
- reference types;
- SIMD;
- threads or shared memory;
- exceptions;
- garbage collection;
- memory64;
- multiple memories;
- host clock, random, filesystem, or socket imports.

Required exports are pointer/length-oriented equivalents of the C ABI. Memory may be exported by the module or supplied according to one documented build profile, but one release profile must run with no imports.

The conformance job must inspect the module and fail if unexpected imports or post-baseline features appear.

## 4. C ABI rules

The public C header is the cross-language authority.

Required rules:

- C99-compatible declarations;
- fixed-width integer types from `<stdint.h>`;
- opaque context handles;
- explicit pointer plus `uint32_t` length pairs;
- no C++ types, exceptions, templates, STL, or name mangling;
- no Rust layout exposed directly;
- no public `bool`, compiler enum layout, bitfield, `long`, `size_t`, or `long double` in serialized or versioned structures;
- all public structs carry `struct_size` and/or version when extension is possible;
- reserved fields must be zero on input and ignored on output;
- functions return stable numeric status codes;
- caller owns all buffers;
- buffer-too-small calls return required capacity without partial semantic success;
- no callback is invoked after the initiating function returns unless an explicit asynchronous API is added in a later ABI major version;
- no panic, exception, or trap may cross the ABI.

ABI versioning:

```text
major = incompatible function/layout/semantic change
minor = backward-compatible additions
encoded ABI = (major << 16) | minor
```

The v0.1 implementation starts with ABI major `1`, minor `0`. Experimental prerelease packaging may still use project version `0.x` while the C ABI is versioned independently.

## 5. ABI shape to implement

The exact header will be generated and checked against this logical surface:

```c
uint32_t xs_abi_version(void);
xs_status xs_decimal_parse_ascii(const uint8_t* text, uint32_t text_len,
                                 uint8_t semantic_kind, uint16_t unit_id,
                                 xs_decimal_v1* out_value);
uint32_t xs_context_size(const xs_config_v1* config);
uint32_t xs_context_align(void);
xs_status xs_context_init(void* memory, uint32_t memory_len,
                          const xs_config_v1* config, xs_context** out);
xs_status xs_pack_mount(xs_context* ctx, const uint8_t* bytes,
                        uint32_t bytes_len, void* arena,
                        uint32_t arena_len, uint16_t* out_slot,
                        uint32_t* required_arena_len);
xs_status xs_find(xs_context* ctx, const uint8_t* query, uint32_t query_len,
                  xs_match_v1* out, uint16_t capacity, uint16_t* out_count);
xs_status xs_eval(xs_context* ctx, uint16_t pack_slot, uint32_t operation_id,
                  const xs_value_ref_v1* args, uint16_t arg_count,
                  const xs_eval_options_v1* options,
                  void* scratch, uint32_t scratch_len,
                  xs_result_v1* out);
xs_status xs_result_json(xs_context* ctx, const xs_result_v1* result,
                         uint8_t* out, uint32_t capacity,
                         uint32_t* required);
```

The implementation may add helper functions, but it must preserve:

- in-place context initialization;
- no mandatory allocator;
- pack bytes supplied by the host;
- fixed-width operation identity;
- typed values rather than expression strings;
- caller-provided output storage.

## 6. Data representation portability

### 6.1 Runtime values

`Decimal64` is represented logically as:

```text
signed coefficient: 64 bits
signed exponent: 8 bits
semantic kind: 8 bits
unit id: 16 bits
flags/reserved: 32 bits
```

The generated C header must include compile-time size and offset assertions in C and C++ test fixtures for each target ABI.

### 6.2 Pack files

`.xsp` is canonical little-endian. Loaders on other-endian machines must decode fields explicitly rather than casting file bytes to native structs.

Pack files contain offsets, not native pointers. Every offset is relative to the beginning of the pack and uses an unsigned 32-bit field. Packs larger than 4 GiB are invalid; official packs must remain far below that limit.

### 6.3 Wire protocol

TinyWire uses deterministic CBOR with integer map keys and CBOR decimal-fraction tag 4. Tiny JSON uses decimal strings. JSON numbers are not accepted for exact decimal arguments in the normative AI adapter profile.

## 7. CPU feature policy

The correctness path is scalar.

- SIMD is optional and may only accelerate a kernel after byte-identical conformance is demonstrated.
- Android `arm64-v8a` may use the guaranteed base architecture, but optional newer instructions require runtime dispatch and a scalar fallback.
- Android x86-64 must not assume AVX.
- Baseline operation correctness must not require an FPU.
- CPU-specific builds may be offered separately but cannot replace portable release artifacts.

## 8. Android packaging

The preferred developer installation is an AAR containing:

```text
jni/arm64-v8a/libexactscope.so
jni/armeabi-v7a/libexactscope.so
jni/x86_64/libexactscope.so
assets/exactscope/econ-undergrad.xsp
prefab/modules/exactscope/include/exactscope.h
```

A fused AAR may embed the economics pack in each library and omit the asset.

Requirements:

- no Android permissions;
- no JNI requirement for native/C++ hosts;
- a minimal Kotlin/JNI wrapper may be supplied as an adapter;
- no background service;
- no network security configuration;
- no dependency on Google Play services;
- ABI splits or app bundles remain possible so devices receive only their matching native library.

The minimum Android API level must be chosen only after testing the produced library on representative devices. The core itself must avoid Android platform APIs so the minimum is determined primarily by packaging/toolchain support.

## 9. Apple packaging

Native Apple releases should provide:

- a C header;
- static libraries during early development;
- an XCFramework once macOS/iOS conformance is stable;
- an optional Swift package wrapper that forwards to the same C ABI.

The Swift wrapper may improve installation but must not contain calculation logic.

## 10. Linux and Windows packaging

Each archive must be self-contained:

```text
include/exactscope.h
lib/<static and/or shared library>
packs/*.xsp
LICENSE-APACHE
LICENSE-MIT
SHA256SUMS
```

No package manager, daemon, Python, Node.js, Java, or system-wide install is required. Package-manager recipes may be added later as conveniences.

## 11. Fused artifacts

For the smallest devices, releases should include or make reproducible:

- `exactscope-econ.wasm` — no-import WebAssembly core with `econ-undergrad` embedded;
- `libexactscope_econ.a` — static native library with the same pack embedded;
- optional `exactscope-math-stats.wasm` and combined profiles after size measurement.

A fused artifact exposes the same operation keys and result semantics as dynamic packs. Fusing is a packaging choice, not a fork of the logic.

## 12. Tool-schema compatibility

The generated AI tool schemas deliberately use a conservative JSON Schema subset:

- root object with named properties;
- explicit primitive `type` on every property;
- all operational fields required;
- `additionalProperties: false`;
- no `oneOf`, `anyOf`, `allOf`, conditional schemas, recursive references, empty objects, or complex regex patterns;
- small bounded arrays;
- short field names only in the Tiny profile.

This avoids turning advanced schema features into a runtime compatibility dependency and reduces prompt size for small models.

## 13. Version compatibility

ExactScope versions four things independently:

1. **Core release version** — repository/package SemVer.
2. **C ABI version** — integer major/minor.
3. **Pack format version** — major/minor in `.xsp` header.
4. **Operation revision** — immutable semantics for one operation key.

Rules:

- a core may load only supported pack-format majors;
- a pack declares minimum and maximum ABI major/minor;
- an existing operation key plus revision must never change formula, units, rounding, classification, or assumptions;
- a semantic change creates a new revision and, when ambiguity would result, a new operation key;
- aliases may evolve compatibly but canonical keys remain stable;
- TinyWire major-version mismatch fails before evaluation.

## 14. Conformance corpus

Every Tier 1/2 target executes the same corpus:

- decimal lexical parsing and canonicalization;
- checked arithmetic boundaries;
- rounding modes and tie cases;
- VM stack validation;
- scalar formula vectors;
- deterministic numeric-kernel vectors;
- classification-before-rounding vectors;
- unit-group acceptance/rejection;
- pack truncation, offset overflow, duplicate identity, and malformed UTF-8 cases;
- TinyWire deterministic encoding/decoding;
- C ABI buffer sizing and alignment;
- fused versus dynamic-pack equivalence;
- adapter Tiny JSON request/response fixtures.

Canonical result bytes, not approximate textual similarity, determine pass/fail.

## 15. Reproducibility record

Each release must publish a machine-readable compatibility manifest containing:

- source commit;
- Rust toolchain;
- target triple/ABI;
- build profile and feature flags;
- artifact SHA-256;
- stripped size;
- static RAM estimate or measured peak;
- conformance corpus digest;
- pass/fail counts;
- runtime/emulator identity where tested.

## 16. Compatibility changes

Any change that increases minimum CPU features, requires a new host import, requires allocation in fused mode, enlarges a public structure incompatibly, changes canonical numeric results, or invalidates existing packs requires an explicit architecture decision and an ABI/format/version response. Convenience is not sufficient justification.

## 17. Current external baselines

The design intentionally follows stable, widely implemented boundaries:

- Rust `no_std` separates platform-independent `core` functionality from OS integration.
- Rust's `wasm32v1-none` target is limited to the WebAssembly 1.0 baseline and imports nothing from the host.
- Android's NDK documents `arm64-v8a`, `armeabi-v7a`, x86, and `x86_64` ABIs; ExactScope initially prioritizes the first three listed in the matrix.
- deterministic CBOR and decimal-fraction tag 4 are defined by RFC 8949.
- lightweight embedded Wasm runtimes such as WAMR support WebAssembly MVP across desktop, Android, ARM/Thumb, AArch64, RISC-V, and embedded operating systems.

These references justify the portability choices; ExactScope support claims still depend on its own conformance results.
