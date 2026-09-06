# ExactScope product direction

Release context: **v1.0.0-rc.3 integration & qualification candidate**. The active capability architecture described here is implemented code-side; the remaining adoption gates are exact public-release model evidence, representative target qualification and support promotion.

This document defines what ExactScope is optimizing for. It supersedes any earlier product framing that treated broad platform parity or full catalog completion as more important than proving adoption value.

## 1. Product sentence

ExactScope is a **tiny deterministic quantitative coprocessor for small and on-device AI**.

Its primary customer value is:

> **Upgrade constrained on-device AI through software instead of requiring a hardware upgrade for every quantitative capability gap.**

ExactScope is designed as a **capability retrofit layer** for products whose deployed model size and inference cost are bounded by RAM, bandwidth, storage, accelerator capability, thermals, battery, latency, or qualification constraints.

It moves bounded deterministic quantitative work out of the model and executes it with checked base-10/rational semantics, bounded memory, stable errors, and reproducible provenance. It does not claim to make a model generally more intelligent or to eliminate the need for future hardware upgrades.

Smart glasses and wearables are strong use cases, but the product thesis applies more broadly to phones, robots, industrial systems, automotive systems, embedded assistants, and other constrained local-AI products.

The lifecycle retrofit thesis is defined in [`RETROFIT_PRODUCT_STRATEGY.md`](RETROFIT_PRODUCT_STRATEGY.md). The next-stage product-unit, capability-slice, weak-model budget, and build-vs-buy design is defined in [`CAPABILITY_PRODUCT_ARCHITECTURE.md`](CAPABILITY_PRODUCT_ARCHITECTURE.md).

## 2. Product hypothesis

The product hypothesis is not assumed true merely because deterministic arithmetic is attractive.

It must be measured:

> For an existing constrained on-device model, can a tiny ExactScope software addition remove enough quantitative error at sufficiently low binary, RAM, token, latency, energy, integration, and qualification cost that the existing hardware remains useful for capabilities that would otherwise push toward a larger model or newer device?

The flagship proof should therefore compare not only model-only reasoning with ExactScope, but also — where deployment is feasible — **small model + ExactScope versus a larger model**.

The first public proof matters more than catalog breadth.

## 3. Primary interaction model

ExactScope now has two implemented experimental model-facing lanes: one bounded generic `xs_calc` arithmetic-plan path and one direct `xs_eval` path for reviewed semantic operations. `xs_calc` does not replace reviewed semantic methods; the two lanes share one deterministic core.

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
      IMPLEMENTED / EXPERIMENTAL       IMPLEMENTED / REVIEWED
                 |                             |
                 +--------------+--------------+
                                |
                                v
                     ExactScope shared core
```

`xs_calc` is implemented as one compact 1-8 step model-facing plan over the initial operation vocabulary `add/sub/mul/div/powi/sqrt`. It uses the existing bounded numeric kernel rather than introducing another arithmetic implementation.

`xs_eval` remains the preferred path when operation identity carries reviewed semantics such as sample versus population statistics, economics methods, units, or later domain-specific rules.

`xs_find` remains a cold/development fallback for unknown semantic operations. It is not a required serving hop for ordinary on-device quantitative requests.

## 4. Tiny model surface first

The small-model surface should be minimized according to task type:

- ordinary short arithmetic: one bounded `xs_calc` plan schema/grammar;
- reviewed domain methods: the **smallest capability slice** that covers the target task families, typically exposed through one compact `xs_eval` tool;
- unknown semantic operations: optional `xs_find` outside the common hot path.

Generated artifacts may include:

- the bounded-plan JSON Schema/GBNF for `xs_calc`;
- canonical semantic operation keys/signatures for the selected capability slice;
- compact model hints and prompt fragments;
- OpenAI-compatible tool assets;
- checked-in/generated GBNF;
- registry/pack/profile digest binding;
- model-difficulty and footprint metadata;
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
- one compact bounded arithmetic-plan surface;
- small reviewed semantic capability slices when method identity matters;
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

## 8. rc3 release scope

The product scope remains intentionally narrow even though the internal architecture supports more paths.

Primary rc3 integration candidates:

1. **Native static C ABI** — packaged for Windows/Linux x86-64 evaluation and Android/Linux ARM64 OEM integration.
2. **No-import WebAssembly** — packaged in the x86-64 evaluation SDK and intended for local embedding.

Both profiles preserve the tiny embed/update model and remain qualification candidates rather than Tier 1/Tier 2 support promises.

Secondary/experimental architecture includes dynamic data packs, dynamic discovery, convenience wrappers, broader OS/architecture parity, and additional domain breadth. All paths exposing the same computation must use shared calculation semantics. rc3 does not wait for universal platform parity.

## 9. Capability-first roadmap

### P0 — rc3 public candidate and model evidence

Implemented before qualification: bounded `xs_calc`, selected Statistics/Economics semantic slices, deterministic capability compiler, model-surface identity, native/Wasm packaging and qualification tooling.

Remaining P0 evidence:

- publish/verify the exact rc3 GitHub candidate and release assets;
- freeze the five-model minimum matrix and preregistration identities;
- run A model-only / C selected semantic / D combined comparisons, adding B calc-only only as a diagnostic;
- report end-to-end correctness plus failure decomposition and exact interface/artifact cost;
- bind all results to immutable release/model/runtime/corpus/scorer identities.

### P1 — prove the released candidate on constrained hardware

- use the exact published Android ARM64 or embedded Linux ARM64 asset on a representative target;
- record artifact/storage, RSS/heap, stack/scratch, latency distribution, energy method/results where credible, and thermal behavior where relevant;
- exercise fail-closed malformed input plus update/rollback/power-loss behavior where applicable;
- compare against a larger-model/newer-device path only where the product decision is real and fair.

### P2 — support promotion

- decide which exact artifacts/targets become supported rather than merely Experimental;
- publish compatibility/qualification/reproducibility records appropriate to that claim;
- define support/update/security/LTS policy;
- add convenience platform wrappers only when validated by real integrators.

### P3 — expand reviewed domain sources after proof

- keep one shared core and one specialization/profile mechanism;
- add Statistics/Economics breadth or Finance/Physics/Engineering only when a real capability profile justifies it;
- every new domain adds reviewed contracts/provenance/tests and emits small target-specific slices rather than another runtime or a full-catalog prompt.

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

The OSS core remains the adoption wedge. Possible commercial layers are described in [COMMERCIALIZATION.md](COMMERCIALIZATION.md): verified domain source catalogs, capability-slice/profile engineering, LTS/SLA, OEM qualification, integration support, and custom deterministic capability work.

The business model must not require a proprietary cloud calculation service or incompatible evaluator fork.

## 13. Current implementation position

Implemented code-side for rc3:

- deterministic `no_std` numeric kernel and bounded scalar VM;
- bounded `xs_calc` plan-v0.1 over `add/sub/mul/div/powi/sqrt`;
- Tiny JSON/TinyWire plus generated JSON Schema/GBNF/tool/prompt assets;
- reviewed Economics execution and bounded Statistics vector kernels;
- selected semantic `xs_eval` and optional cold/development `xs_find`;
- native typed C ABI and no-import Wasm;
- pack/packc plus optional dynamic-pack architecture;
- deterministic domain-general capability/profile compiler;
- task-family-driven Statistics/Economics slices and model-difficulty budgets;
- generated/drift-checked Statistics kernel/operation/dispatch metadata and Economics selection wiring;
- operation-selected Wasm specialization and fail-closed model-surface identity;
- strict llama.cpp reference envelopes for both normal lanes;
- deterministic evaluation/OEM SDK packaging with manifest/checksum policy;
- Windows/Linux x86-64 evaluation and Android/Linux ARM64 release-workflow paths;
- wearable reference/A-B/update/qualification infrastructure;
- relocatable CMake target, security/export audit and CI gates.

Historical model/oracle/smoke results remain design evidence only. They are not listed as rc3 implementation proof because the clean release requires new exact-artifact evidence.

Remaining product gates are public rc3 release verification, fresh revision-bound model evidence, resource/energy measurements, representative real-device qualification and long-term compatibility/LTS/support evidence. These are not missing numeric engines or compiler mechanisms. See `CODEX_CONTEXT.md` and `QUALIFICATION_HANDOFF.md`.

## 14. Decision test

Before adding a feature, ask:

> Does this help an existing physically constrained model gain a useful deterministic quantitative capability without forcing a hardware/model-size jump, while preserving the tiny bounded auditable runtime profile?

Then ask whether the value can be measured reproducibly and whether the feature reuses the shared core semantics.

If not, it is probably lower priority than the retrofit product proof.
