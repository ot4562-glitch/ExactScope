# External compatibility references

Reviewed: **2026-09-03**

These references justify target and integration choices. ExactScope specifications remain authoritative for ExactScope behavior; external projects do not define ExactScope semantics.

## Rust and WebAssembly

- Rust `wasm32v1-none` target: <https://doc.rust-lang.org/rustc/platform-support/wasm32v1-none.html>
- Rust platform support tiers: <https://doc.rust-lang.org/rustc/platform-support.html>
- Rust panic semantics: <https://doc.rust-lang.org/reference/panic.html>
- Rust linkage and unwinding rules: <https://doc.rust-lang.org/reference/linkage.html>
- Rust crate linkage forms: <https://doc.rust-lang.org/reference/linkage.html>
- WebAssembly Core 1.0: <https://www.w3.org/TR/wasm-core-1/>
- WebAssembly Micro Runtime: <https://github.com/bytecodealliance/wasm-micro-runtime>

The no-import profile uses `wasm32v1-none` because Rust documents it as a stable WebAssembly 1.0-oriented target containing `core`/`alloc` without `std` or host imports. ExactScope nevertheless inspects every release artifact rather than inferring conformance from the target name alone.

## Android native compatibility

- Android ABIs: <https://developer.android.com/ndk/guides/abis>
- Android CMake integration: <https://developer.android.com/ndk/guides/cmake>
- Android native middleware distribution: <https://developer.android.com/ndk/guides/middleware-vendors>

The Android package is planned as a thin AAR/JNI wrapper around one native semantic implementation. Dependencies are not allowed to create a second calculator inside Kotlin or Java.

## AI tool-call compatibility

- llama.cpp repository: <https://github.com/ggml-org/llama.cpp>
- llama.cpp grammars: <https://github.com/ggml-org/llama.cpp/tree/master/grammars>
- llama.cpp JSON Schema to grammar conversion: <https://github.com/ggml-org/llama.cpp/tree/master/examples/json_schema_to_grammar>
- JSON Schema Draft 2020-12: <https://json-schema.org/draft/2020-12>

ExactScope intentionally presents only `xs_find` and `xs_eval` by default. Checked-in conservative schemas and grammars are required because small local tool-call runtimes vary in their support for complex JSON Schema features and large tool catalogs.

## Wire and integrity formats

- CBOR, RFC 8949: <https://www.rfc-editor.org/rfc/rfc8949>
- CRC catalogue entry for CRC-32/ISO-HDLC: <https://reveng.sourceforge.io/crc-catalogue/17plus.htm#crc.cat.crc-32-iso-hdlc>

TinyWire uses deterministic CBOR rules and a precisely identified CRC profile. CRC is only corruption detection; pack or update authenticity remains a host/distribution responsibility.

## Related work

- arithma: <https://github.com/farchanjo/arithma>
- math-mcp: <https://github.com/codeprimate/math-mcp>
- needle-rs: <https://github.com/geekgineer/needle-rs>
- llm-tool: <https://github.com/domenukk/llm-tool>

These projects demonstrate adjacent calculator, MCP, typed-tool, or tiny-routing ideas. ExactScope's target remains a library-first, installable, deterministic quantitative scope system for constrained AI, with data-only domain packs and C/no-import-Wasm portability as primary interfaces.
