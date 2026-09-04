# ExactScope

> **A tiny deterministic quantitative coprocessor for small and on-device AI.**
>
> **Upgrade constrained on-device AI through software instead of requiring a hardware upgrade for every quantitative capability gap.**

**Status: experimental v0.1 runtime. The deterministic core and current `xs_eval` path exist; the vNext bounded `xs_calc` plan described below is a design target and is not implemented yet. Stable release and benchmark-backed retrofit claims do not yet exist.**

ExactScope is not a calculator app, chatbot, cloud API, Python replacement, or AI model. It is a tiny capability-retrofit component intended to sit beside an existing local/on-device model.

See [Retrofit product strategy](docs/RETROFIT_PRODUCT_STRATEGY.md) for the authoritative vNext direction.

## The 30-second product idea

A deployed device may already be limited by RAM, accelerator capability, storage, thermals, battery, latency, or qualification constraints. Replacing its 0.5B-3B local model with a much larger model may require new hardware.

ExactScope asks a different question:

```text
existing device
+ existing small model
+ tiny deterministic ExactScope software update
= stronger quantitative capability without replacing the device
```

The current implemented semantic path can already evaluate known reviewed operations directly:

```json
{"op":"econ.inflation.cpi_pct","a":["100","103.2"]}
```

```text
model -> xs_eval(op,args) -> ExactScope -> deterministic result
```

The vNext design adds one planned bounded arithmetic-plan lane for short multi-step numerical reasoning:

```text
model -> xs_calc(bounded 1-8 step plan) -> ExactScope -> deterministic result
```

`xs_eval` remains the semantic fast path for reviewed methods such as statistics/economics/domain operations. `xs_find` remains optional cold/development discovery rather than a required serving hop.

## Why ExactScope exists

The product does not try to make a model generally more intelligent. It targets a narrower failure class that is expensive to solve by spending scarce on-device model capacity: **deterministic quantitative execution**.

The product hypothesis is measurable:

> Can an existing constrained on-device model plus a tiny ExactScope retrofit remove enough quantitative error at sufficiently low binary, RAM, token, latency, energy, integration, and qualification cost that the existing hardware remains useful for capabilities that would otherwise push toward a larger model or newer device?

The flagship proof should therefore compare **small model vs small model + ExactScope**, with a larger-model reference where fair and feasible.

Until reproducible public and real-target evidence is published, ExactScope does not claim proven hardware-life extension, accuracy, latency, token, or energy savings.

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

ExactScope is best described technically as:

> **a tiny deterministic quantitative coprocessor for small and on-device AI.**

Its customer value is:

> **Upgrade constrained on-device AI without requiring a hardware upgrade for every quantitative capability gap.**

The primary targets are physically constrained or already-deployed AI devices: smart glasses/wearables, phones/tablets, embedded assistants, robots/industrial systems, automotive systems, and other constrained edge products. Desktop/local AI remains useful for evaluation but is not the center of the retrofit thesis.

Offline operation is a capability, not the whole market. The important properties are tiny footprint, bounded execution, deterministic semantics, simple embedding, and qualification/update suitability.

## Product priorities

The roadmap is deliberately **retrofit-first**, not catalog-first.

### P0 — prove the retrofit mechanism

1. freeze and later implement the bounded `xs_calc` 1-8 step plan through the existing core;
2. generate constrained JSON Schema/GBNF;
3. gold-validate FinQA/TAT-QA compatible subsets;
4. benchmark multiple 0.5B-3B models;
5. measure wrong-number reduction and tool penalty;
6. enforce binary/RAM/scratch footprint gates;
7. preserve `xs_eval` for reviewed semantic operations.

### P1 — prove it on constrained hardware

1. same small model with and without ExactScope on a real target;
2. binary/RAM/scratch/latency/energy evidence;
3. optional larger-model reference comparison;
4. update/rollback integration evidence.

### P2 — harden OEM adoption

1. stable native/no-import Wasm packages;
2. immutable manifests/self-test/conformance;
3. compatibility/qualification records;
4. convenience packages only where real integrations justify them.

### P3 — domain series after core proof

One runtime, optional reviewed capability series: Math, Statistics, Economics, Finance, Physics, Chemistry, Engineering, then evidence-backed OEM/domain packs.

See [Roadmap](ROADMAP.md).

## Tiny model surface

The target small-model interface is intentionally narrow:

```text
ordinary short arithmetic
  -> xs_calc(bounded plan)      # planned

reviewed semantic method
  -> xs_eval(op,args)           # implemented

unknown semantic operation
  -> xs_find                    # optional cold/development path
```

The full academic catalog should never be injected into a tiny-model prompt by default. Domain series share the same runtime rather than becoming separate calculators.

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
- bounded Tiny JSON scalar/vector adapter with canonical multi-output names;
- deterministic-CBOR TinyWire `find` plus scalar/vector `eval`;
- wearable reference host and A/B update reference;
- experimental ARM64 SDK packaging;
- relocatable `ExactScope::exactscope` CMake package;
- developer-side SDK doctor;
- build-time digest-bound hot-set generator in `exactscope-packc`, including conservative OpenAI-compatible `xs_eval`, optional `xs_find`, direct-eval GBNF, source-pack/fused-registry bindings, and checked-in reproducibility fixtures;
- focused `econ-core-8` and `statistics-core-8` hot sets plus the mixed `quant-core-16` benchmark/evaluation selection generated from fused executable registries;
- llama.cpp OpenAI-compatible direct-eval reference runner with strict scalar/vector tool-call validation and an offline CI self-test;
- four-arm benchmark harness with a real Tiny JSON/core bridge, stage-level metrics, a 22-case executable economics/statistics corpus/core drift self-test, and digest-bound result metadata;
- deterministic prerelease evaluation-bundle packaging that combines a prebuilt native library, prebuilt benchmark/core executable, no-import Wasm, `quant-core-16`, benchmark assets, CMake/header integration, manifests/checksums, licenses, and smoke instructions without requiring Rust to evaluate;
- clean-room evaluation tests that extract the release-shaped archive outside the source tree and execute the packaged core, benchmark self-test, Wasm conformance, and host-native C smoke when the archive matches the CI host;
- CI covering design validation, C/C++ headers, Rust/MSRV, no-import Wasm, native/dynamic conformance, hot-set reproducibility, benchmark-core validation, release-shaped clean-room evaluation, adapter envelope validation, wearable reference integration, and experimental Android/Linux ARM64 SDK builds.

Still missing before a stable product release:

- the planned bounded `xs_calc` contract and implementation through shared core semantics;
- gold-validated public compatible-subset converters and deterministic ceilings;
- reproducible 0.5B-3B model-only vs ExactScope retrofit evidence;
- explicit binary/RAM/scratch footprint gates for the vNext path;
- permanent versioned GitHub Release assets; release-shaped CI evaluation bundles are implemented but are not yet a stable release channel;
- complete target self-test/qualification tooling;
- real-device latency, memory, energy, offline, and update/rollback qualification;
- larger-model substitution evidence where fair/useful.

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

After the planned bounded-plan path exists, the flagship public evidence should compare:

| Arm | Path |
|---|---|
| A | model only |
| B | model -> unconstrained `xs_calc` -> ExactScope |
| C | model -> constrained `xs_calc` -> ExactScope |
| D | gold plan -> ExactScope deterministic ceiling |
| E | optional larger-model reference with resource cost reported separately |

Semantic-operation benchmarks retain direct/constrained `xs_eval` and optional discovery measurements where relevant.

Required metrics include final answer accuracy, incorrect numeric answer rate, tool penalty rate, plan/operation selection, argument extraction, invalid/rejected-call rate, successful-answer rate, inference turns, tokens, end-to-end/model/core latency, binary/resident/scratch bytes, and energy where measurable.

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

- [Retrofit product strategy](docs/RETROFIT_PRODUCT_STRATEGY.md)
- [Product direction](docs/PRODUCT_DIRECTION.md)
- [Roadmap](ROADMAP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [AI integration](docs/AI_INTEGRATION.md)
- [Benchmark contract](docs/BENCHMARK.md)
- [5-minute quickstart](docs/QUICKSTART.md)
- [Installation](docs/INSTALLATION.md)
- [Compatibility](docs/COMPATIBILITY.md)
- [Commercialization direction](docs/COMMERCIALIZATION.md)
- [Architecture decisions](docs/DECISIONS.md)
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [Specification index](spec/README.md)

## License

ExactScope is dual-licensed under [Apache-2.0](LICENSE-APACHE) or [MIT](LICENSE-MIT), at your option. Scope-pack source data must declare compatible source/license metadata.

---

**ExactScope:** keep the small model; add exact quantitative capability.
