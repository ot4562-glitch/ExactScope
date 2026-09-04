# ExactScope product direction

This document defines what ExactScope is optimizing for. It supersedes any earlier product framing that treated broad platform parity or full catalog completion as more important than proving adoption value.

## 1. Product sentence

ExactScope is a **tiny deterministic quantitative coprocessor for small and on-device AI**.

It moves bounded formula-driven work out of the model and executes it with explicit methods, checked base-10/rational semantics, bounded memory, stable errors, and reproducible provenance.

ExactScope is not primarily a wearable product. Wearables are one strong use case. The broader market is AI products that want deterministic quantitative execution without depending on model arithmetic or embedding a general Python/scientific runtime.

## 2. Product hypothesis

The product hypothesis is not assumed true merely because deterministic arithmetic is attractive.

It must be measured:

> For constrained models, does ExactScope improve the successful quantitative-task rate enough to justify its integration cost while reducing or preserving model turns, tokens, latency, memory, and energy?

The first public proof therefore matters more than the first 99 operations.

## 3. Primary interaction model

The primary product path is **one-hop direct evaluation**.

```text
model
  -> xs_eval(known_op,args)
  -> ExactScope
  -> deterministic result
```

`xs_find` is a cold-path fallback for an unknown operation, not a mandatory first hop.

```text
cold path:
model -> xs_find -> bind/cache -> xs_eval

future hot calls:
model ---------------------> xs_eval
```

Hosts bind cached operation metadata to the current registry/pack digest and operation revision. Digest/revision changes invalidate the binding.

This preserves a tiny model surface without forcing an extra model inference turn on common operations.

## 4. Hot-set first

Products should normally expose a generated **8-32 operation hot set** appropriate to the device/use case.

Generated hot-set artifacts may include:

- canonical operation keys/signatures;
- compact model hints;
- OpenAI-compatible JSON tool assets;
- checked-in/generated GBNF;
- registry/pack digest binding;
- optional direct numeric operation IDs for typed hosts.

The full catalog should not be embedded in a tiny model prompt by default.

The catalog remains a source of available deterministic operations. The hot set is the actual product-facing subset.

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

- small resident footprint;
- deterministic bounded execution;
- no required service or target-side language runtime;
- fixed auditable operation surface;
- data-only packs rather than arbitrary native plugins;
- stable operation revisions and provenance;
- model-independent qualification;
- hot-set packaging;
- portability through C ABI and no-import Wasm.

A product that already has a cheap, trusted, certifiable Python sandbox may not need ExactScope. That is an acceptable non-target.

## 7. Market definition

Representative targets:

- smart glasses and wearables;
- phones/tablets;
- embedded assistants;
- robots and industrial systems;
- automotive systems;
- private/local desktop AI;
- constrained edge services;
- regulated/certifiable systems where arbitrary code execution is undesirable.

Offline is a capability, not the whole market. Network-connected systems can still value a small deterministic coprocessor.

## 8. Release scope

The internal architecture may support multiple execution profiles, but v0.1 product scope is intentionally narrower.

### Primary v0.1 candidates

1. **Native static C ABI**
2. **No-import WebAssembly**

These are sufficient to prove the product across native and portable-host integration.

### Secondary/experimental

- dynamic data packs;
- dynamic discovery;
- additional shared-library/platform wrappers;
- broad OS/architecture parity;
- additional academic domains.

All paths that expose the same operation must use the same shared calculation semantics. But v0.1 no longer waits for every path to become Tier 1.

## 9. Adoption-first roadmap

### P0 — prove value

- direct `xs_eval` hot path documented and exercised;
- hot-set generator;
- OpenAI-compatible schema assets;
- GBNF generator/fixtures;
- llama.cpp reference integration;
- model-only vs ExactScope benchmark;
- 5-minute quickstart;
- prebuilt evaluation artifacts.

### P1 — make the initial content defensible

- reviewed math/statistics/economics hot sets;
- strong provenance;
- golden/invalid/boundary/precision corpus;
- benchmark coverage tied to those hot sets.

### P2 — broaden distribution

- stable CMake/native packages;
- stable no-import Wasm component;
- Android AAR/Prefab;
- additional platform packages when evidence justifies them.

### P3 — breadth

- dynamic discovery maturity;
- wider Tier 1 parity;
- larger catalog coverage;
- additional domain packs;
- more constrained hardware targets.

## 10. Installation target

The target integration experience is:

```text
download prebuilt artifact
  -> verify manifest/digest
  -> link/load
  -> run self-test
  -> bind hot-set schema/GBNF
  -> xs_eval direct calls
```

The target must not require:

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

1. real AI runtime adapters/hot-set generation;
2. benchmark evidence;
3. prebuilt public evaluation artifacts;
4. reviewed initial hot sets and corpora;
5. target qualification/self-test and real-device measurements.

## 14. Decision test

Before adding a feature, ask:

> Does this improve one-hop model integration, measured successful quantitative-task quality, deployment simplicity, deterministic trust, or target qualification?

If not, it is probably lower priority than the current product proof.
