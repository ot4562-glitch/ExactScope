# ExactScope

> **Make tiny AI compute less, and compute exactly.**
>
> A tiny, offline, deterministic academic-computation micro-runtime for local, wearable, embedded, and edge AI.

**Status: experimental v0.1 runtime in active implementation. The deterministic scalar path, fused economics and statistics registries, zero-copy C ABI statistics vectors, no-import Wasm path, scope-pack compiler/loader foundation, Tiny JSON adapter, and wearable reference host exist. No stable public release has been declared yet.**

ExactScope is an AI-only quantitative system component. It gives constrained language models reliable access to common mathematics, statistics, economics, and other formula-driven academic operations without asking the model to remember formulas, perform arithmetic, infer unit conventions, or silently choose between ambiguous methods.

ExactScope is not a calculator application, chatbot, tutoring interface, cloud API, or general computer-algebra system. Its product form is a small resident component loaded by another AI runtime. On platforms that expose an extension, plugin, shared-library, or WebAssembly loading path, an end user should eventually be able to install ExactScope without installing a full application or background service.

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
- **System-component sized:** the useful product is the smallest resident runtime plus selected academic packs, not a companion application.
- **Offline first:** no network, account, cloud service, API key, telemetry, or remote database.
- **Library first:** no daemon is required. Embed a static/shared library or a no-import WebAssembly module.
- **Specialize instead of scaling:** ExactScope does not compete with large vendors on raw model FLOPS. It removes deterministic quantitative work from the model so small local models spend fewer tokens, less latency, and less energy on arithmetic they should not perform themselves.
- **Small-model friendly:** two flat tool schemas instead of hundreds of verbose per-formula schemas.
- **Deterministic:** baseline operations use checked base-10 decimal arithmetic, explicit rounding, bounded algorithms, and stable result codes.
- **Fail closed:** missing assumptions, ambiguous methods, invalid units, overflow, and unsupported operations return typed errors.
- **Data-only packs:** scope packs contain validated metadata, bounded bytecode, aliases, and test vectors—not arbitrary native code.
- **Compatibility first:** C ABI and WebAssembly are first-class; language-specific SDKs are adapters.
- **Static mode first:** the smallest deployment can compile one or more packs directly into the binary and evaluate without a heap.

## Why OEMs and local-AI vendors should care

ExactScope is intentionally aimed at a narrow systems gap that larger AI stacks often leave to each product team: **small local models still need reliable quantitative tools, but shipping a cloud calculator, a large symbolic engine, or hundreds of tool schemas is often too expensive for a wearable or embedded product.**

The integration contract is deliberately vendor-neutral:

- the model only has to select an operation and extract canonical values;
- the computation path is model-independent and can be qualified separately from the model;
- the runtime needs no account, network service, daemon, database, or target-side language runtime;
- fused/static deployments remain allocator-free and can expose only the hot operations a device actually needs;
- the same stable C ABI can sit behind Android, Linux, Windows, Apple, firmware, or an AI-host extension wrapper;
- release evidence can bind exact artifact digest, ABI, pack digest, operation revision, size, memory, and conformance results.

That makes ExactScope useful as an **OEM-owned deterministic coprocessor for model tool calls** rather than another AI application. A product team can change models without rewriting formulas, and can change packaging without creating a second evaluator.

## Current evidence level

The repository distinguishes implementation progress from platform support claims:

| Area | Current state |
|---|---|
| Deterministic scalar economics path | implemented and covered by native/dynamic/Wasm CI paths |
| Fused statistics vector path | implemented for the first exact kernels; public C ABI uses zero-copy caller-owned vectors |
| Dynamic `.xsp` vector/kernel path | implemented for the current bounded statistics kernels and covered by fused↔dynamic conformance |
| No-import WebAssembly | scalar Tiny JSON plus typed zero-copy statistics-vector evaluation implemented with zero imports |
| Android AArch64 / Linux AArch64 wearable SDKs | cross-built in CI as **experimental** artifacts |
| Real-device latency / energy / power-loss qualification | not yet sufficient for Tier 1 support |
| Stable public release | not declared yet |

See [Compatibility](docs/COMPATIBILITY.md) for the evidence required before any target is called supported.

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

The checked-in implementation is a Rust workspace with `#![no_std]` runtime crates, caller-provided memory for dynamic mode, concrete C99/C++11 ABI headers, and a `wasm32v1-none` contract that requires zero host imports and the WebAssembly 1.0 baseline. The repository already contains deterministic decimal/rational arithmetic including correctly rounded square root, the bounded v0.1 scalar VM including explicit round/sqrt, executable economics formulas, canonical formula/kernel `.xsp` compilation/loading, fused and dynamic statistics-vector evaluation through the same shared kernel, zero-copy native C ABI vector inputs, typed no-import Wasm statistics evaluation, Tiny JSON handling, deterministic-CBOR TinyWire `find`/scalar/vector `eval`, fused↔dynamic statistics conformance, and experimental OEM SDK packaging with a relocatable CMake target plus developer-side doctor. Important v0.1 work remains, especially complete reviewed academic-pack coverage, permanent release assets, Android/other platform convenience packaging, target-side qualification tooling, and measured real-device qualification.

See:

- [Architecture](docs/ARCHITECTURE.md)
- [Product direction](docs/PRODUCT_DIRECTION.md)
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

ExactScope is designed for four execution profiles plus a consumer-installable packaging layer:

1. **Fused WebAssembly:** one no-import `.wasm` containing the core and selected packs. This is the simplest cross-runtime wearable profile.
2. **Fused native static:** C header plus one `.a`/`.lib`; no pack parser, filesystem, or heap is required at runtime.
3. **Static data packs:** packs are embedded as immutable byte arrays and validated at startup through caller-owned storage.
4. **Dynamic data packs:** the host passes `.xsp` bytes into a caller-provided arena. No native plugin loading or ExactScope-owned update service exists.

The **resident component** packaging layer wraps one of those profiles in the smallest installable unit a host platform permits: for example a no-import `.wasm`, one shared library plus manifest, or an AI-host extension containing the same core. It must not add a daemon, account, network dependency, or duplicate evaluator. Android/Apple wrappers remain convenience packaging around the same C ABI rather than the product definition.

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

## Interfaces

- stable C ABI using fixed-width types and opaque handles;
- no-import WebAssembly exports;
- Tiny JSON for model-generated scalar calls;
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

The first release sequence is evidence-driven rather than logo-driven:

1. no-import `wasm32v1-none` as the portable single-file baseline;
2. Linux AArch64/x86-64 native archives;
3. Android `arm64-v8a` packaging around the same C ABI;
4. Windows x86-64 and Apple Silicon macOS native artifacts;
5. secondary Android/Apple ABIs and one constrained embedded target only after conformance evidence exists.

The repository already cross-builds experimental Android AArch64 and Linux AArch64 wearable SDK bundles, but cross-compilation alone is not a support claim. A platform is called supported only after the release artifact itself passes the conformance, malformed-input, footprint, and real/emulated execution evidence defined in [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).

## Related work

Existing projects demonstrate demand for LLM calculators, precise MCP tools, offline local models, and tiny tool-routing runtimes. ExactScope is deliberately narrower and more device-oriented: its primary artifact is a small embeddable deterministic runtime with installable domain packs, not a human calculator or desktop MCP server.

Relevant comparisons include [arithma](https://github.com/farchanjo/arithma), [math-mcp](https://github.com/codeprimate/math-mcp), [needle-rs](https://github.com/geekgineer/needle-rs), and [llama.cpp](https://github.com/ggml-org/llama.cpp).

## Repository state

The repository freezes the v0.1 architecture, numeric/error semantics, C ABI, no-import WebAssembly memory contract, scope-pack and TinyWire formats, stable ID registries, model-facing schemas, installation profiles, and the initial academic catalog. The implementation now includes deterministic `Decimal64`/rational evaluation, correctly rounded square root, the v0.1 scalar VM subset, multiple economics formulas, native fused/dynamic execution, canonical statistics kernel packs, zero-copy C ABI vectors, typed Wasm statistics execution, deterministic-CBOR TinyWire `find` and scalar/vector `eval`, fused↔dynamic conformance, Tiny JSON, wearable reference integration, reproducible SDK packaging, a relocatable CMake target, and an SDK doctor that verifies checksums/ABI/ARM64 archive architecture before target testing.

The implementation is still alpha. The main gaps are complete reviewed math/statistics/economics pack coverage and golden corpora, permanent release artifacts, Android/other convenience packaging, a complete target-side self-test/qualification helper, and measured real-device footprint/latency/energy/offline/power-loss evidence. The roadmap tracks those gaps explicitly rather than treating the repository as a scaffold.

## License

ExactScope is dual-licensed under [Apache-2.0](LICENSE-APACHE) or [MIT](LICENSE-MIT), at your option. Scope-pack source data must declare its own compatible license and source metadata. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md) before submitting code or parser/ABI findings.

---

**ExactScope:** do not teach a tiny model to calculate what deterministic code can calculate exactly.
