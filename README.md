# ExactScope

> **Deterministic quantitative coprocessor for small and on-device AI.**
>
> Move bounded math, statistics, economics, and other formula-driven work out of the model and into a tiny reproducible runtime.

**Status: experimental v0.1 runtime. Core execution exists; stable public release and benchmark-backed product claims do not yet exist.**

ExactScope is not a calculator app, chatbot, cloud API, or Python replacement. It is a small system component loaded by another AI runtime.

## The 30-second example

User asks:

```text
CPI went from 100 to 103.2. What is inflation?
```

A small model should not spend tokens performing arithmetic. With a known operation key, it emits one compact call:

```json
{"op":"econ.cpi.inflation","a":["100","103.2"]}
```

ExactScope validates the method and inputs, performs deterministic base-10/rational computation, and returns the canonical result.

```text
model
  -> xs_eval(op,args)
  -> ExactScope
  -> deterministic result
```

**`xs_find` is not required on the hot path.** Discovery exists only when the operation key is unknown. Hosts bind/cache discovered operation metadata to the installed registry/pack digest and reuse direct `xs_eval` afterward.

```text
cold path: model -> xs_find -> bind/cache -> xs_eval
hot path:  model ------------------------> xs_eval
```

## Why ExactScope exists

Small models have three different failure classes on quantitative tasks:

1. choosing the wrong formula/method;
2. extracting or formatting the wrong arguments;
3. performing the arithmetic incorrectly.

ExactScope only claims authority over the deterministic part after a valid call. It does **not** pretend that a strict calculator core solves model recognition or extraction errors.

The product hypothesis is therefore measurable:

> Can a small/on-device model plus a tiny deterministic hot-path runtime produce more correct quantitative answers, with acceptable invalid-call rate, latency, memory, and energy cost, than model-only reasoning?

Until the benchmark is published, ExactScope does not claim a measured accuracy, latency, token, or energy improvement.

## 5-minute evaluation path

Start with [docs/QUICKSTART.md](docs/QUICKSTART.md).

Release packaging is being designed so integrators do **not** need to understand or install the Rust workspace. The desired native integration is:

```cmake
find_package(ExactScope CONFIG REQUIRED)
target_link_libraries(my_product PRIVATE ExactScope::exactscope)
```

The desired portable integration is a no-import `.wasm` plus immutable manifest/hot-set metadata.

The current experimental OEM SDK already contains a relocatable CMake target and developer-side `exactscope_doctor.py`; stable prebuilt release artifacts remain release work.

## Product position

ExactScope is best described as:

> **a tiny, bounded, auditable quantitative execution component for AI products that do not want model arithmetic or a general Python/scientific sandbox in the critical path.**

Target environments include:

- smart glasses and wearables;
- phones and tablets;
- embedded assistants;
- robots and industrial systems;
- automotive systems;
- private/local desktop AI;
- constrained edge services;
- regulated/certifiable products where arbitrary-code sandboxes are undesirable.

Offline operation is a capability, not the only market. A network-connected product can still value a small fixed execution surface, predictable memory, stable operation revisions, and independent qualification.

## Product priorities

The roadmap is deliberately **adoption-first**, not catalog-first.

### P0 — prove the product

1. direct one-hop `xs_eval` hot path;
2. generated 8-32 operation hot sets;
3. OpenAI-compatible tool assets and checked-in/generated GBNF;
4. llama.cpp reference integration;
5. reproducible model-only vs ExactScope benchmark;
6. 5-minute quickstart and prebuilt evaluation artifacts.

### P1 — make the first domain set worth adopting

1. reviewed `math-basic` hot set;
2. reviewed `statistics-core` hot set;
3. reviewed `econ-undergrad` hot set;
4. provenance and strong golden/negative corpora.

### P2 — broaden distribution

1. CMake/native release package;
2. no-import Wasm component;
3. Android AAR/Prefab;
4. additional host packages based on evidence.

### P3 — breadth after proof

1. dynamic discovery maturity;
2. broader execution-profile Tier 1 parity;
3. additional academic/domain packs;
4. additional constrained hardware targets.

A smaller hot set with strong benchmark and integration evidence is more valuable than 99 operations that nobody can evaluate quickly.

## Hot-set first AI integration

The default small-model product profile should preload or generate a compact hot set tied to the installed registry digest.

Example conceptual hot set:

```text
econ.cpi.inflation(old_cpi,new_cpi)
econ.gdp.deflator(nominal_gdp,real_gdp)
econ.real_rate.exact(nominal_rate_pct,inflation_pct)
stats.mean(values)
stats.var.sample(values)
...
```

The model emits `xs_eval` directly for these known operations. `xs_find` remains available only as a cold fallback.

This avoids forcing an additional model inference turn for common operations while also avoiding hundreds of independent tool schemas.

See [AI integration](docs/AI_INTEGRATION.md).

## Strict core, forgiving syntax boundary

ExactScope remains fail-closed for semantics. That prevents the tool layer from inventing plausible numbers when assumptions or methods are wrong.

Adapters may normalize transport syntax, but must not infer meaning.

Allowed examples:

- outer tool-envelope translation;
- whitespace normalization;
- deterministic field mapping;
- exact lexical normalization where no numeric meaning changes.

Forbidden examples:

- guessing that `5%` means `0.05` for an unspecified operation;
- dropping currency/unit markers and pretending semantics are unchanged;
- guessing missing arguments;
- changing sample variance to population variance;
- silently selecting an ambiguous economics method.

The benchmark must report both wrong-number rate and rejected-call rate so the fail-closed tradeoff is visible rather than philosophical.

## Current implementation

Implemented today:

- `#![no_std]` deterministic kernel with checked decimal/rational arithmetic;
- correctly rounded deterministic square root and explicit VM rounding;
- executable economics operations;
- bounded statistics kernels including mean, weighted mean, variance, standard deviation, covariance, Pearson correlation, and simple linear regression;
- stable native C ABI with caller-owned memory and zero-copy statistics vectors;
- canonical formula/kernel `.xsp` compilation/loading for the implemented slice;
- fused and dynamic statistics execution through the same shared kernels;
- no-import `wasm32v1-none` path;
- Tiny JSON scalar adapter;
- deterministic-CBOR TinyWire `find` plus scalar/vector `eval`;
- wearable reference host and A/B update reference;
- experimental ARM64 SDK packaging;
- relocatable `ExactScope::exactscope` CMake package;
- developer-side SDK doctor;
- build-time digest-bound hot-set generator in `exactscope-packc`, including conservative OpenAI-compatible `xs_eval`, optional `xs_find`, direct-eval GBNF, source-pack/fused-registry bindings, and checked-in reproducibility fixtures;
- production-size `econ-core-8` hot set generated directly from the fused executable economics registry;
- llama.cpp OpenAI-compatible direct-eval reference runner with strict tool-call validation and an offline CI self-test;
- four-arm benchmark harness with a real Tiny JSON/core bridge, stage-level metrics, corpus/core drift self-test, and digest-bound result metadata;
- CI covering design validation, C/C++ headers, Rust/MSRV, no-import Wasm, native/dynamic conformance, hot-set reproducibility, benchmark-core validation, adapter envelope validation, wearable reference integration, and experimental Android/Linux ARM64 SDK builds.

Still missing before a stable product release:

- recorded real-model llama.cpp runs and model-only vs ExactScope benchmark evidence across the target model classes;
- stable downloadable/prebuilt release assets;
- reviewed official hot-set/domain pack coverage and large golden corpora;
- complete target self-test/qualification tooling;
- real-device latency, memory, energy, offline, and update/rollback qualification.

## Primary release profiles

For v0.1, product scope is intentionally narrower than the internal architecture supports.

### Primary candidates

1. **Native static C ABI** — smallest predictable native integration; no service, no target-side Rust runtime.
2. **No-import WebAssembly** — portable single-file execution baseline.

### Secondary/experimental

- dynamic data packs;
- additional shared-library/platform wrappers;
- wider architecture/OS matrix;
- dynamic discovery beyond the fused/cached hot-set path.

All profiles must continue to share the same calculation semantics when they expose the same operation. However, v0.1 no longer waits for every possible execution profile and platform to become Tier 1 before the product can prove value.

## Architecture constraints

ExactScope keeps a deliberately narrow systems boundary:

- no mandatory daemon;
- no account or cloud dependency;
- no database;
- no arbitrary native code in scope packs;
- no general expression language in the runtime;
- no hidden model-side arithmetic inside adapters;
- no mandatory target-side Python/Node/Java/Rust runtime;
- fused/static path remains allocator-free;
- vector, VM, pack, and output limits are bounded before work begins.

Wrappers may translate protocols. Only the shared core calculates.

## Benchmark before marketing claims

See [docs/BENCHMARK.md](docs/BENCHMARK.md).

The first public evidence must compare:

| Arm | Path |
|---|---|
| A | model only |
| B | model + direct `xs_eval` hot path |
| C | model + `xs_find -> xs_eval` discovery path |
| D | direct `xs_eval` with constrained decoding/GBNF |

Required metrics include final answer accuracy, operation selection, argument extraction, invalid-call rate, core-rejected rate, successful-answer rate, inference turns, tokens, end-to-end latency, ExactScope compute latency, resident bytes, scratch bytes, and energy where measurable.

## Scope packs

The frozen catalog currently describes `math-basic`, `statistics-core`, and `econ-undergrad`, but catalog size is not the release KPI.

The pack strategy is now:

```text
reviewed benchmark hot set
    -> prove model/product value
    -> strengthen provenance/golden corpus
    -> expand operation coverage
```

Operations remain data-driven with stable keys, explicit methods, deterministic programs/kernel IDs, unit/semantic constraints, rounding policy, provenance, and test vectors.

See [packs/README.md](packs/README.md) and [packs/CATALOG_V0_1.md](packs/CATALOG_V0_1.md).

## Compatibility

A target is not called supported because it compiles.

Compatibility evidence includes ABI/wire conformance, golden vectors, malformed-input behavior, artifact identity, memory/size evidence, and actual runtime execution. Real-device qualification is required for claims that depend on latency, energy, thermal, update, or hardware behavior.

For v0.1, native static and no-import Wasm are the primary release candidates; other profiles can remain Experimental without blocking the product proof.

See [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).

## Commercial direction

The permissively licensed core can remain OSS while commercial value, if pursued, comes from:

- verified domain packs;
- enterprise LTS/SLA;
- OEM target qualification;
- integration support;
- custom deterministic domain-pack engineering.

The business model should not require a cloud service or proprietary calculation fork.

See [docs/COMMERCIALIZATION.md](docs/COMMERCIALIZATION.md).

## Documentation

- [5-minute quickstart](docs/QUICKSTART.md)
- [Product direction](docs/PRODUCT_DIRECTION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [AI integration](docs/AI_INTEGRATION.md)
- [Benchmark contract](docs/BENCHMARK.md)
- [Installation](docs/INSTALLATION.md)
- [Compatibility](docs/COMPATIBILITY.md)
- [Commercialization direction](docs/COMMERCIALIZATION.md)
- [Architecture decisions](docs/DECISIONS.md)
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [Roadmap](ROADMAP.md)
- [Specification index](spec/README.md)

## License

ExactScope is dual-licensed under [Apache-2.0](LICENSE-APACHE) or [MIT](LICENSE-MIT), at your option. Scope-pack source data must declare compatible source/license metadata.

---

**ExactScope:** let the model decide *what* to calculate; let deterministic code calculate it.
