# ExactScope product direction

This document defines what ExactScope is optimizing for. It supersedes any earlier product framing that treated broad platform parity or full catalog completion as more important than proving adoption value.

## 1. Product sentence

ExactScope is a **tiny deterministic quantitative coprocessor for small and on-device AI**.

Its primary customer value is:

> **Upgrade constrained on-device AI through software instead of requiring a hardware upgrade for every quantitative capability gap.**

ExactScope is designed as a **capability retrofit layer** for products whose deployed model size and inference cost are bounded by RAM, bandwidth, storage, accelerator capability, thermals, battery, latency, or qualification constraints.

It moves bounded deterministic quantitative work out of the model and executes it with checked base-10/rational semantics, bounded memory, stable errors, and reproducible provenance. It does not claim to make a model generally more intelligent or to eliminate the need for future hardware upgrades.

Smart glasses and wearables are strong use cases, but the product thesis applies more broadly to phones, robots, industrial systems, automotive systems, embedded assistants, and other constrained local-AI products.

The detailed target direction is defined in [`RETROFIT_PRODUCT_STRATEGY.md`](RETROFIT_PRODUCT_STRATEGY.md).

## 2. Product hypothesis

The product hypothesis is not assumed true merely because deterministic arithmetic is attractive.

It must be measured:

> For an existing constrained on-device model, can a tiny ExactScope software addition remove enough quantitative error at sufficiently low binary, RAM, token, latency, energy, integration, and qualification cost that the existing hardware remains useful for capabilities that would otherwise push toward a larger model or newer device?

The flagship proof should therefore compare not only model-only reasoning with ExactScope, but also — where deployment is feasible — **small model + ExactScope versus a larger model**.

The first public proof matters more than catalog breadth.

## 3. Primary interaction model

The **current implemented** generic model path is direct `xs_eval` against a small generated hot set. The **vNext target** adds one generic bounded arithmetic-plan path without replacing reviewed semantic operations.

```text
                         small/local model
                                |
                 +--------------+--------------+
                 |                             |
                 v                             v
        generic short arithmetic       known semantic method
                 |                             |
                 v                             v
        xs_calc(bounded plan)            xs_eval(op,args)
          TARGET / PLANNED                 IMPLEMENTED
                 |                             |
                 +--------------+--------------+
                                |
                                v
                     ExactScope shared core
```

`xs_calc` is planned as one compact 1-8 step model-facing plan over the initial operation vocabulary `add/sub/mul/div/powi/sqrt`. It must lower into the existing bounded VM/numeric kernel rather than introducing another arithmetic implementation.

`xs_eval` remains the preferred path when operation identity carries reviewed semantics such as sample versus population statistics, economics methods, units, or later domain-specific rules.

`xs_find` remains a cold/development fallback for unknown semantic operations. It is not a required serving hop for ordinary on-device quantitative requests.

## 4. Tiny model surface first

The small-model surface should be minimized according to task type:

- ordinary short arithmetic: one `xs_calc` plan schema/grammar once implemented;
- reviewed domain methods: a generated **8-32 operation hot set** for `xs_eval` when needed;
- unknown semantic operations: optional `xs_find` outside the common hot path.

Generated artifacts may include:

- the bounded-plan JSON schema/GBNF after `xs_calc` is implemented;
- canonical semantic operation keys/signatures;
- compact model hints;
- OpenAI-compatible tool assets;
- checked-in/generated GBNF;
- registry/pack digest binding;
- optional direct numeric operation IDs for typed hosts.

The full catalog should not be embedded in a tiny model prompt by default. Domain breadth must not force every constrained model to choose among hundreds of tools.

## 5. Strict core, syntax-tolerant boundary

The core remains fail-closed for semantics:

- missing assumptions;
- ambiguous methods;
- invalid unit relationships;
- domain errors;
- overflow/resource limits;
- unsupported operations.

However, adapters may normalize **syntax** when meaning is unchanged.

Safe examples:

- tool-envelope translation;
- whitespace normalization;
- fixed field mapping;
- exact lexical normalization that preserves the same numeric value.

Unsafe semantic repair:

- percent/ratio guessing;
- unit conversion without an explicit operation contract;
- dropping currency symbols;
- inventing missing values;
- choosing between sample/population or midpoint/point methods.

The benchmark must report both wrong-number rate and rejected-call rate. ExactScope must prove that fail-closed behavior improves practical successful-answer quality rather than merely moving the failure mode.

## 6. Competitive axis

ExactScope does not compete with large vendors on model FLOPS or with Python/scientific environments on breadth.

It competes on a narrower systems combination:

- **retrofit/OTA suitability for constrained or deployed AI devices**;
- small resident footprint;
- deterministic bounded execution;
- one compact bounded arithmetic-plan surface once implemented;
- reviewed semantic operations when method identity matters;
- no required service or target-side language runtime;
- no arbitrary model-generated code execution;
- fixed auditable operation surface;
- data-only packs rather than arbitrary native plugins;
- stable operation revisions and provenance;
- model-independent qualification;
- portability through C ABI and no-import Wasm.

A product that already has a cheap, trusted, certifiable Python sandbox may not need ExactScope. That is an acceptable non-target.

## 7. Market definition

The primary market is **physically constrained or already-deployed on-device AI** where increasing model size has meaningful hardware/product cost.

Representative targets:

- smart glasses and wearables;
- phones/tablets;
- embedded assistants;
- robots and industrial systems;
- automotive systems;
- other constrained edge products;
- later regulated/certifiable systems where arbitrary code execution is undesirable.

Private/local desktop AI remains useful for development and validation, but it is not the center of the retrofit thesis.

Offline is a capability, not the whole market. A network-connected device can still benefit from keeping supported quantitative work local, tiny, predictable, and independently qualifiable.

The strongest early adoption wedge may be **existing devices** whose hardware cannot be changed but whose AI software stack can still receive an update.

## 8. Release scope

The internal architecture may support multiple execution profiles, but v0.1 product scope is intentionally narrow.

### Primary v0.1 candidates

1. **Native static C ABI**
2. **No-import WebAssembly**

Both profiles must preserve the tiny, embed-and-update retrofit model.

### Secondary/experimental

- dynamic data packs;
- dynamic discovery;
- additional shared-library/platform wrappers;
- broad OS/architecture parity;
- domain-series breadth beyond the first evidence-backed packs.

All paths exposing the same computation must use shared calculation semantics. v0.1 does not wait for universal platform parity.

## 9. Retrofit-first roadmap

### P0 — prove the mechanism

- freeze the planned bounded `xs_calc` contract;
- lower accepted plans into existing core semantics;
- generate JSON Schema/GBNF for one compact plan surface;
- gold-validate public FinQA/TAT-QA compatible subsets;
- benchmark multiple 0.5B-3B models;
- report wrong-number reduction and tool penalty;
- enforce binary/RAM/scratch footprint gates;
- preserve `xs_eval` as the reviewed semantic fast path.

### P1 — prove it on constrained hardware

- measure the same small model with and without ExactScope on a real target;
- compare against a larger-model reference where useful;
- record binary, resident RAM, scratch, latency, tokens, and energy where measurable;
- document update/rollback and integration cost.

### P2 — harden OEM adoption

- stable C ABI/no-import Wasm artifacts;
- immutable manifests and self-test;
- compatibility/qualification records;
- update-safe integration guidance;
- convenience platform packages only when validated by real consumers.

### P3 — domain series

- one shared core;
- Math, Statistics, Economics, Finance, Physics, Chemistry, Engineering, then evidence-backed OEM/domain packs;
- every series adds reviewed contracts/provenance/tests, not another runtime.

See [`../ROADMAP.md`](../ROADMAP.md) for the detailed gates.

## 10. Installation target

The target retrofit experience is:

```text
download/receive software update
  -> verify manifest/digest
  -> link/load tiny native or Wasm artifact
  -> run self-test
  -> bind xs_calc schema/grammar and selected semantic ops
  -> route supported deterministic work through ExactScope
```

The target must not require:

- replacing or retraining the model;
- Rust;
- Python/Node/Java;
- a package-manager runtime;
- a daemon;
- an ExactScope account;
- a network connection;
- a writable home directory.

Developer-side tooling may use convenient workstation languages, but it is not a runtime dependency.

## 11. Evidence before claims

Before ExactScope markets itself as improving AI accuracy, lowering latency, or saving energy, publish reproducible evidence under [BENCHMARK.md](BENCHMARK.md).

Before a platform is called supported, publish compatibility evidence under [COMPATIBILITY.md](COMPATIBILITY.md).

Before enterprise optimization claims, publish at least one real constrained-target qualification record.

## 12. Commercial direction

The OSS core remains the adoption wedge. Possible commercial layers are described in [COMMERCIALIZATION.md](COMMERCIALIZATION.md): verified packs, LTS/SLA, OEM qualification, integration support, and custom deterministic domain packs.

The business model must not require a proprietary cloud calculation service or incompatible evaluator fork.

## 13. Current implementation position

Already implemented:

- deterministic no_std numeric kernel;
- scalar VM including sqrt/round;
- economics execution;
- bounded statistics vector kernels;
- native C ABI and zero-copy vectors;
- current formula/kernel `.xsp` path;
- no-import Wasm;
- Tiny JSON and TinyWire;
- wearable reference/A-B update reference;
- experimental ARM64 SDK packaging;
- relocatable CMake target;
- developer SDK doctor;
- strong CI around those paths.

Largest product gaps now:

1. the planned bounded `xs_calc` contract and implementation through shared core semantics;
2. gold-validated public benchmark mappings for the retrofit path;
3. reproducible multi-model evidence on 0.5B-3B classes;
4. explicit binary/RAM/scratch footprint gates;
5. prebuilt public evaluation artifacts for the vNext path;
6. target qualification and real-device measurements;
7. larger-model substitution evidence where useful.

## 14. Decision test

Before adding a feature, ask:

> Does this help an existing physically constrained model gain a useful deterministic quantitative capability without forcing a hardware/model-size jump, while preserving the tiny bounded auditable runtime profile?

Then ask whether the value can be measured reproducibly and whether the feature reuses the shared core semantics.

If not, it is probably lower priority than the retrofit product proof.
