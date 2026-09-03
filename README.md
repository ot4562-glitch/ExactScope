# ExactScope

> **Make tiny AI reason less.**
>
> A tiny, offline, deterministic quantitative coprocessor for local, wearable, embedded, and edge AI.

**Status: implementation-ready v0.1 scaffold. The evaluator is not implemented and no runtime artifact has been released.**

ExactScope is an AI-only tool runtime. It gives constrained language models reliable access to common mathematics, statistics, and undergraduate economics operations without asking the model to remember formulas, perform arithmetic, infer unit conventions, or silently choose between ambiguous methods.

ExactScope is not a calculator application, chatbot, tutoring interface, cloud API, or general computer-algebra system. Human developers integrate it; another AI runtime is the consumer.

```text
camera / microphone / sensors
            |
            v
      tiny local model
  recognize intent + extract values
            |
            v
        ExactScope
 validate + select + calculate + classify
            |
            v
    compact structured result
```

## The intended interaction

The model sees only two simple tools: `xs_find` and `xs_eval`.

```json
{"q":"midpoint price elasticity","n":3}
```

```json
{"s":0,"m":[{"op":"econ.ped.mid","sig":"econ.ped.mid(p1,p2,q1,q2)","method":"midpoint"}]}
```

```json
{"op":"econ.ped.mid","a":["10000","12000","100","80"]}
```

```json
{"s":0,"v":"-1.222222","c":"elastic","p":"econ-undergrad@0.1.0","r":1}
```

Decimal arguments are strings in the AI-facing adapter so JSON parsers cannot silently round large or precise values. The core uses a compact typed representation and never relies on LLM inference for calculation.

## Design commitments

- **AI-only:** no human-facing GUI or conversational layer in the core project.
- **Offline first:** no network, account, cloud service, API key, telemetry, or remote database.
- **Library first:** no daemon is required. Embed a static/shared library or a no-import WebAssembly module.
- **Small-model friendly:** two flat tool schemas instead of hundreds of verbose per-formula schemas.
- **Deterministic:** baseline operations use checked base-10 decimal arithmetic, explicit rounding, bounded algorithms, and stable result codes.
- **Fail closed:** missing assumptions, ambiguous methods, invalid units, overflow, and unsupported operations return typed errors.
- **Data-only packs:** scope packs contain validated metadata, bounded bytecode, aliases, and test vectors—not arbitrary native code.
- **Compatibility first:** C ABI and WebAssembly are first-class; language-specific SDKs are adapters.
- **Static mode first:** the smallest deployment can compile one or more packs directly into the binary and evaluate without a heap.

## Architecture

```text
                    AI runtime
                        |
       +----------------+----------------+
       |                                 |
  Tiny JSON adapter                  direct C ABI
       |                                 |
       +---------------+-----------------+
                       |
                ExactScope Core
       +---------------+----------------+
       |               |                |
  pack registry   validation/VM    numeric kernels
       |               |                |
       +---------------+----------------+
                       |
       math-basic / statistics-core / econ-undergrad
```

The checked-in implementation scaffold is a Rust workspace with `#![no_std]` runtime crates, caller-provided memory for dynamic mode, concrete C99/C++11 ABI headers, and a `wasm32v1-none` contract that requires zero host imports and the WebAssembly 1.0 baseline. Actual numeric and pack execution code is deliberately still absent.

See:

- [Architecture](docs/ARCHITECTURE.md)
- [Compatibility contract](docs/COMPATIBILITY.md)
- [Installation and embedding profiles](docs/INSTALLATION.md)
- [AI integration contract](docs/AI_INTEGRATION.md)
- [Architecture decisions](docs/DECISIONS.md)
- [First implementation slice](docs/FIRST_IMPLEMENTATION_SLICE.md)
- [Full implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [Specification index](spec/README.md)
- [C ABI header](include/exactscope.h)
- [No-import WebAssembly ABI](spec/WASM_ABI_V0_1.md)
- [Initial operation catalog](packs/CATALOG_V0_1.md)
- [External compatibility references](docs/REFERENCES.md)
- [Roadmap](ROADMAP.md)

## Scope packs

```text
ExactScope Core
|
+-- math-basic.xsp
+-- statistics-core.xsp
+-- econ-undergrad.xsp
`-- future data-only packs
```

A pack defines stable operation keys, compact signatures, argument semantics, unit constraints, deterministic programs or built-in kernel IDs, output precision, classification rules, aliases, sources, and golden tests.

The first showcase pack is `econ-undergrad`, covering formula-driven undergraduate tasks such as elasticity, surplus, cost and revenue measures, GDP relationships, inflation, labor-market rates, money and interest relationships, exchange-rate calculations, and growth-rate helpers. Compound time-value-of-money functions remain deferred until their deterministic integer-power kernels are specified and measured.

Open-ended forecasting is outside the scope. ExactScope must not pretend that policy questions with model-dependent answers have one universal formula.

## Runtime profiles

ExactScope is designed for four embedding profiles:

1. **Fused WebAssembly:** one no-import `.wasm` containing the core and selected packs. This is the simplest cross-runtime wearable profile.
2. **Fused native static:** C header plus one `.a`/`.lib`; no pack parser, filesystem, or heap is required at runtime.
3. **Static data packs:** packs are embedded as immutable byte arrays and validated at startup through caller-owned storage.
4. **Dynamic data packs:** the host passes `.xsp` bytes into a caller-provided arena. No native plugin loading or ExactScope-owned update service exists.

Android uses a thin AAR/JNI wrapper around the same C ABI, and Apple platforms use the same ABI through a static library or XCFramework. The initial release target is one or two drop-in artifacts per platform, never a mandatory service installation.

## v0.1 engineering budgets

These are implementation gates, not current performance claims:

| Area | v0.1 budget |
|---|---:|
| Stripped no-pack WebAssembly core | <= 128 KiB |
| Fused core + initial economics pack | <= 256 KiB |
| Required heap in fused/static mode | 0 bytes |
| Default evaluation scratch | <= 2 KiB |
| Scalar VM instructions per operation | <= 64 |
| Scalar VM stack depth | <= 16 |
| Default vector length | <= 256 values |
| Typical Tiny JSON request | <= 256 bytes |
| Network dependencies | 0 |

Budgets may only be changed with measurements and a documented compatibility decision.

## Planned interfaces

- stable C ABI using fixed-width types and opaque handles;
- no-import WebAssembly exports;
- Tiny JSON for model-generated calls;
- deterministic CBOR-based TinyWire for compact host transport;
- generated adapters for `llama.cpp`-style JSON/GBNF tool calling;
- OpenAI-compatible tool definitions;
- optional MCP adapter for desktop agents.

MCP and HTTP are compatibility adapters, not foundations of the runtime.

## Accuracy and provenance

Every successful result can identify:

- the stable operation key;
- pack ID and semantic version;
- operation revision;
- numeric profile;
- output precision and rounding mode;
- classification code;
- whether rounding occurred.

A result is reproducible when core version, pack digest, operation revision, canonical inputs, and requested output policy are identical.

Each official operation must ship with valid, invalid, boundary, overflow, precision, and classification test vectors. Benchmark claims for 0.5B–3B models will be published only after measurement.

## Compatibility priorities

The first implementation must prove conformance on:

- `wasm32v1-none`;
- Android `arm64-v8a`, `armeabi-v7a`, and `x86_64`;
- Linux AArch64 and x86-64;
- Windows x86-64;
- Apple Silicon macOS, with iOS packaging following the same C ABI;
- at least one constrained embedded target before claiming embedded support.

A platform is not called supported merely because it compiles. Support requires the conformance vectors and ABI tests defined in [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).

## Related work

Existing projects demonstrate demand for LLM calculators, precise MCP tools, offline local models, and tiny tool-routing runtimes. ExactScope is deliberately narrower and more device-oriented: its primary artifact is a small embeddable deterministic runtime with installable domain packs, not a human calculator or desktop MCP server.

Relevant comparisons include [arithma](https://github.com/farchanjo/arithma), [math-mcp](https://github.com/codeprimate/math-mcp), [needle-rs](https://github.com/geekgineer/needle-rs), and [llama.cpp](https://github.com/ggml-org/llama.cpp).

## Repository state

The repository now freezes the v0.1 architecture, numeric/error semantics, C ABI, no-import WebAssembly memory contract, scope-pack and TinyWire formats, stable ID registries, model-facing schemas, installation profiles, and first economics fixture. It also contains a compile-oriented Rust workspace scaffold and contract CI.

No evaluator, pack loader, compiler, wire parser, released library, or released `.wasm` exists yet. The next commit can begin directly with the `Decimal64 -> econ.ped.mid -> C ABI -> fused Wasm -> Tiny JSON` vertical slice in [FIRST_IMPLEMENTATION_SLICE.md](docs/FIRST_IMPLEMENTATION_SLICE.md).

## License

ExactScope is dual-licensed under [Apache-2.0](LICENSE-APACHE) or [MIT](LICENSE-MIT), at your option. Scope-pack source data must declare its own compatible license and source metadata. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md) before submitting code or parser/ABI findings.

---

**ExactScope:** do not teach a tiny model to calculate what deterministic code can calculate exactly.
