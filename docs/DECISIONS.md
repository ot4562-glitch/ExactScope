# Architecture decisions

These decisions are binding for the v0.1 implementation unless an explicit replacement decision documents compatibility impact, measurements, and migration.

| ID | Decision | Reason | Consequence |
|---|---|---|---|
| D-001 | ExactScope is an AI-only embedded tool, not a human calculator product. | The underserved target is constrained local AI inside wearables and edge systems. | No GUI, account, dashboard, or conversational layer is on the core roadmap. |
| D-002 | The core is library-first and offline. | A daemon, cloud API, or network permission increases installation, latency, privacy, and platform coupling. | Native and Wasm libraries are primary; servers are optional host adapters. |
| D-003 | Rust is the planned implementation language, but the stable portability boundary is C ABI plus data formats. | Rust supports memory-safe `no_std` development; a Rust-only API would limit hosts. | Other languages wrap the C ABI and must not reimplement calculations. |
| D-004 | The minimum kernel is `#![no_std]` and allocator-free. | Wearables and embedded targets may have no OS or heap and require predictable memory. | Fused/static evaluation uses fixed or caller-provided storage; convenience adapters are separate crates. |
| D-005 | `wasm32v1-none` is the primary portable WebAssembly target. | It targets the WebAssembly 1.0 baseline, provides no `std`, and requires no host imports. | The fused Wasm artifact uses no WASI, threads, SIMD requirement, filesystem, clock, random source, or sockets. |
| D-006 | AI-facing decimal arguments are strings. | JSON numbers may be rounded by host parsers before ExactScope sees them. | Tiny JSON accepts a strict base-10 lexical grammar and rejects symbols, units, and locale formatting. |
| D-007 | Baseline calculations use checked base-10 decimal inputs and exact bounded rational intermediates, not host floats. | Binary floating behavior and rounding differ across platforms and are unnecessary for common formulas. | Overflow and unresolved precision fail explicitly; optional scientific profiles may be added later. |
| D-008 | The default model surface contains only `xs_find` and `xs_eval`. | Hundreds of per-formula schemas consume context and confuse small tool-calling models. | Catalog discovery is incremental; hosts may cache a small generated hot set. |
| D-009 | Materially different methods are different operation keys. | A universal endpoint with a vague method parameter invites silent selection errors. | Examples include midpoint versus point elasticity and population versus sample variance. |
| D-010 | Scope packs are data-only. | Native plugins undermine portability and enlarge the attack surface. | Packs contain validated metadata, bounded programs, kernel IDs, indexes, and tests; no executable code. |
| D-011 | The runtime has no general expression parser. | Parsing arbitrary expressions costs footprint and creates an unnecessary language/security surface. | Build-time source uses typed RPN instructions compiled into a non-Turing-complete VM. |
| D-012 | Fused deployment is a first-class profile. | The smallest devices need one drop-in artifact and may not have a filesystem or pack loader. | Fused and dynamic packs must produce byte-identical canonical results. |
| D-013 | Dynamic mode uses caller-owned immutable pack bytes and caller-provided arenas. | Hidden allocation and ownership rules break embedded integration. | Context sizing and buffer requirements are explicit in the C ABI. |
| D-014 | Compatibility requires conformance, not successful compilation. | Cross-platform deterministic behavior is the product, not a build checkbox. | Tier claims require common golden vectors, ABI tests, malformed-input tests, size records, and runtime evidence. |
| D-015 | TinyWire uses deterministic CBOR with decimal tag 4; Tiny JSON remains the model-facing format. | CBOR gives compact typed transport while JSON tool calls remain broadly supported by LLM runtimes. | Both protocols map to the same typed core request/result; neither performs calculation. |
| D-016 | Ambiguity and invalid input fail closed. | Returning a plausible number would recreate the hallucination problem outside the model. | Failures have stable codes and never include a usable numeric value. |
| D-017 | Classification uses the unrounded internal result. | Display rounding can falsely turn near-boundary results into equality. | Packs must define deterministic, tested class predicates; unresolved boundaries fail. |
| D-018 | Locale support is an optional data/adapter layer. | Full Unicode normalization and multilingual aliases are expensive for every fused device. | The minimum core uses compact English/ASCII-oriented discovery; locale lexicons may be mounted separately. |
| D-019 | SIMD and CPU-specific acceleration are optional. | Baseline correctness must work on small and old hardware. | Scalar conformance is authoritative; accelerated paths need byte-identical results and fallback. |
| D-020 | HTTP and MCP are adapters, not runtime dependencies. | Wearable and embedded hosts may not have either stack. | Desktop interoperability can grow without changing the core or minimum installation. |
| D-021 | Stable IDs live in machine-readable registries. | Repeated hand-maintained tables drift across Rust, C, schemas, packs, and adapters. | `spec/registries/*.json` is authoritative; generated or copied constants are checked in CI. |
| D-022 | Abort-only artifacts do not promise panic recovery. | `wasm32v1-none` and minimum `no_std` artifacts cannot reliably catch and convert an aborting panic. | Malformed input must be non-panicking; no unwind crosses FFI; any actual panic/abort is a conformance defect, while `INTERNAL_ERROR` is explicit. |
| D-023 | Fused Wasm uses an exported reserved-memory boundary and caller-owned regions. | Hidden allocators or static mailboxes create integration, reentrancy, and footprint problems. | Hosts grow exported memory and pass aligned nonoverlapping offsets according to `WASM_ABI_V0_1.md`. |

## Change procedure

A replacement decision must state:

1. which decision it supersedes;
2. measured binary, RAM, latency, and compatibility impact;
3. ABI, pack-format, protocol, and operation-semantic impact;
4. fallback behavior for existing targets;
5. migration and versioning plan;
6. conformance evidence.

A feature is not sufficient reason to weaken a v0.1 invariant without this review.
