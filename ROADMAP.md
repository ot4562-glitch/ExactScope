# ExactScope roadmap

No dates are promised. This roadmap is ordered by **retrofit leverage and evidence**, not by raw operation count or internal subsystem completeness.

ExactScope should prove one product proposition first:

> **Can a tiny deterministic software addition materially strengthen an existing 0.5B-3B on-device model without requiring a model-size or hardware upgrade?**

The detailed strategy is defined in [`docs/RETROFIT_PRODUCT_STRATEGY.md`](docs/RETROFIT_PRODUCT_STRATEGY.md).

## Current baseline

Implemented today:

- deterministic `no_std` numeric kernel;
- checked decimal/rational arithmetic, deterministic sqrt, explicit round;
- bounded non-Turing-complete scalar VM;
- executable economics operations;
- bounded statistics kernels;
- stable C ABI and zero-copy native vectors;
- current formula/kernel `.xsp` compile/load path;
- no-import Wasm;
- Tiny JSON and TinyWire;
- generated semantic hot sets and GBNF/OpenAI-compatible assets;
- llama.cpp reference integration;
- four-arm semantic benchmark harness;
- wearable reference integration and A/B update reference;
- experimental Android/Linux ARM64 SDK packaging;
- relocatable CMake package;
- SDK doctor and CI around implemented paths.

Current development measurements have also demonstrated that the primary artifacts can remain in a very small size class. Those observations are development evidence, not stable release guarantees.

The engine is therefore not the main blocker. The next blocker is proving the **retrofit mechanism** on public workloads.

# P0 — prove the retrofit mechanism

## P0.1 Freeze the vNext plan contract

Design only until implementation begins:

- [ ] freeze `PLAN_V0_1`;
- [ ] define one planned model-facing `xs_calc` request;
- [ ] cap the first plan at 8 arithmetic steps;
- [ ] initial operations: `add`, `sub`, `mul`, `div`, `powi`, `sqrt`;
- [ ] allow exact decimal-string leaves and backward-only previous-result references;
- [ ] forbid loops, arbitrary branches, variables, arbitrary functions, arbitrary expression text, and arbitrary code;
- [ ] define stable errors for invalid reference, arity, resource limit, domain, divide-by-zero, overflow, and precision failures;
- [ ] specify canonical lowering to the existing bounded VM/numeric kernel;
- [ ] require that the plan path introduces no second arithmetic semantics.

Success criterion: the target model surface is small enough to explain completely and validate mechanically.

## P0.2 Implement the bounded plan using the existing core

**Not started in this design-only revision.**

Future implementation sequence:

- [ ] add bounded plan representation/validator;
- [ ] lower each accepted plan to shared VM/kernel semantics;
- [ ] expose native and no-import Wasm plan evaluation without duplicating calculation logic;
- [ ] add Tiny JSON or equivalent bounded model-facing plan decoding;
- [ ] add malformed/reference/resource/domain conformance tests;
- [ ] prove no heap/network/filesystem/daemon/runtime dependency is introduced into the minimum profile.

Success criterion: `xs_calc` is a thin bounded front end to the existing deterministic engine, not a new language runtime.

## P0.3 Generate tiny-model constrained assets

- [ ] one conservative JSON Schema for `xs_calc`;
- [ ] one generated/checked-in GBNF for the same plan contract;
- [ ] whitespace/output-token termination tests;
- [ ] llama.cpp reference example;
- [ ] raw JSON and OpenAI-compatible envelope fixtures;
- [ ] immutable schema/grammar digests in benchmark metadata;
- [ ] preserve existing semantic `xs_eval` hot-set assets;
- [ ] keep `xs_find` as optional cold/development discovery.

Success criterion: a small model normally chooses between **one arithmetic-plan tool** and a small set of reviewed semantic operations, not a catalog of hundreds of tools.

## P0.4 Gold-validated public benchmark mapping

Priority:

1. FinQA;
2. TAT-QA arithmetic;
3. additional reproducibly mappable numerical reasoning sets;
4. MathQA only after annotation/mapping reliability is explicitly validated.

For each public dataset:

- [ ] pin exact source/revision;
- [ ] derive ExactScope compatibility from gold program/derivation/metadata only;
- [ ] convert to a bounded plan without consulting model outputs;
- [ ] execute every candidate plan through ExactScope;
- [ ] admit an item only when execution matches the dataset gold result;
- [ ] publish full-split coverage percentage;
- [ ] keep full model-only score separate from `ExactScope-compatible subset` score;
- [ ] preserve unsupported items rather than silently dropping them from official-dataset reporting.

Success criterion: the deterministic ceiling is trustworthy before a model is allowed into the experiment.

## P0.5 Retrofit benchmark

Primary model classes:

- [ ] approximately 0.5B-0.8B;
- [ ] approximately 1B;
- [ ] approximately 1.5B-2B;
- [ ] approximately 3B;
- [ ] stress models below the main range where useful;
- [ ] optional larger-model reference arm.

Required generic arithmetic arms after `xs_calc` exists:

- [ ] A: model only;
- [ ] B: model -> unconstrained `xs_calc` -> ExactScope;
- [ ] C: model -> constrained `xs_calc` -> ExactScope;
- [ ] D: gold plan -> ExactScope deterministic ceiling;
- [ ] E: optional larger-model reference with separately reported deployment cost.

Required metrics:

- [ ] final accuracy;
- [ ] incorrect numeric answer rate;
- [ ] tool penalty rate;
- [ ] recognition;
- [ ] extraction;
- [ ] plan syntax/semantic validity;
- [ ] core acceptance/rejection;
- [ ] result/failure fidelity;
- [ ] turns/tokens;
- [ ] model latency and ExactScope latency separately;
- [ ] binary/resident/scratch memory;
- [ ] energy where measurable.

Internal go/no-go target for the first public slice:

- material supported-subset improvement on multiple constrained models, with +10 percentage points as a useful initial threshold unless another effect size is better justified;
- at least 30% relative reduction in incorrect numeric answers;
- acceptable tool-penalty and rejection rates;
- no semantic repair;
- tiny footprint retained.

These are product design gates, not current public claims.

## P0.6 Footprint gate

- [ ] record Wasm/native size before and after bounded-plan support;
- [ ] target primary no-import Wasm near or below 128 KiB when practical;
- [ ] require recorded justification beyond 192 KiB;
- [ ] require explicit design review beyond 256 KiB;
- [ ] report resident RAM and scratch separately from binary size;
- [ ] reject convenience features that materially damage retrofit suitability without measured benefit.

Success criterion: ExactScope remains much cheaper to add than the model/hardware capability jump it is meant to offset.

## P0.7 Five-minute OEM/developer proof

- [x] existing native/CMake and no-import Wasm evaluation shapes exist experimentally;
- [ ] update quickstart for the bounded-plan path after implementation;
- [ ] provide prebuilt artifact + manifest + self-test;
- [ ] show integration without Rust/Python/Node/Java as target dependencies;
- [ ] provide one before/after small-model demonstration;
- [ ] provide exact artifact/schema/grammar/model/dataset digests.

Success criterion: an evaluator can reproduce the retrofit effect without learning the internal Rust workspace.

# P1 — prove the hardware-retrofit proposition on a real target

## P1.1 Real constrained device

- [ ] choose one representative smartphone/embedded/edge target;
- [ ] run the same small model with and without ExactScope;
- [ ] measure binary, resident RAM, scratch, latency distribution, and energy where possible;
- [ ] test malformed input and fail-closed behavior;
- [ ] document installation/update/rollback constraints;
- [ ] keep desktop measurements labeled `desktop_validation`.

Success criterion: at least one real device demonstrates that the integration cost is small enough for the retrofit thesis.

## P1.2 Larger-model substitution comparison

Where benchmark hardware permits:

- [ ] compare small model;
- [ ] compare small model + ExactScope;
- [ ] compare a larger model representing an upgrade path;
- [ ] record model file/VRAM/RAM/load/latency/token cost separately from ExactScope cost;
- [ ] avoid claiming device deployability for a larger model that does not fit the target.

Success criterion: quantify how much capability ExactScope recovers per byte/millisecond/joule of added software cost.

# P2 — harden the retrofit product

## P2.1 Primary release profiles

- [ ] stable native static C ABI package;
- [ ] stable no-import Wasm package;
- [ ] immutable manifests/checksums;
- [ ] exact release-artifact conformance;
- [ ] target self-test;
- [ ] stable bounded-plan schema/ABI after evidence supports freezing it.

## P2.2 OEM integration and update safety

- [ ] minimal integration guide for existing local-model stacks;
- [ ] documented schema/grammar version negotiation;
- [ ] deterministic rollback-compatible artifact identity;
- [ ] offline/no-account/no-daemon guarantee for the primary profile;
- [ ] compatibility records for selected target toolchains/architectures;
- [ ] malformed-input/security review;
- [ ] supply-chain/reproducibility evidence.

## P2.3 Convenience packages only after evidence

- [ ] Android AAR/Prefab when a validated consumer path exists;
- [ ] Windows/Linux/macOS packages as demand requires;
- [ ] iOS/XCFramework only when a real host path justifies it;
- [ ] no wrapper may duplicate calculation semantics.

# P3 — domain series after core proof

ExactScope series are **one runtime plus reviewed capability packs**, not separate calculators.

Proposed evidence-driven order:

1. Math;
2. Statistics;
3. Economics;
4. Finance;
5. Physics;
6. Chemistry;
7. Engineering;
8. later OEM/domain-specific packs.

For every series:

- [ ] reuse the same core/ABI;
- [ ] define explicit semantic/unit/method contracts;
- [ ] provide provenance and revision history;
- [ ] provide golden/negative/boundary vectors;
- [ ] map at least one public or reproducible benchmark where possible;
- [ ] publish compatibility/qualification evidence appropriate to the domain;
- [ ] do not put every domain operation into every tiny-model prompt.

Domain breadth must not delay or weaken the core retrofit proof.

# Commercial/product work

- [x] keep the OSS core as the adoption wedge;
- [ ] document ExactScope explicitly as an **AI capability retrofit** rather than a calculator product;
- [ ] publish the small-model + ExactScope vs larger-model cost/quality comparison after evidence exists;
- [ ] create an OEM one-page integration/value brief after the benchmark is reproducible;
- [ ] publish at least one real-target case study before claiming useful hardware-life extension;
- [ ] develop verified packs/LTS/OEM qualification/custom-pack offerings only after technical pull exists.

# Explicit non-goals

- human calculator UI as the core product;
- general chatbot;
- general Python/scientific runtime;
- arbitrary model-generated code execution;
- general symbolic algebra;
- mandatory cloud/account/telemetry;
- ExactScope-owned daemon;
- hidden semantic repair;
- solving recognition/world-knowledge/perception limitations by pretending they are arithmetic failures;
- universal platform parity before product proof;
- catalog breadth for its own sake;
- claiming that ExactScope can replace every hardware or model upgrade.

# v0.1 product gate

ExactScope should not be called a stable v0.1 product until all of the following are true:

1. the bounded `xs_calc` contract is frozen and implemented through shared core semantics;
2. constrained schema/GBNF assets are reproducible and digest-bound;
3. public compatible-subset generation is gold-derived and deterministic-ceiling validated;
4. multiple 0.5B-3B models have reproducible model-only vs ExactScope results;
5. wrong-number reduction, tool penalty, rejection, turns/tokens/latency, and resource cost are reported;
6. semantic `xs_eval` remains available for reviewed method-specific operations without semantic forks;
7. stable native static and/or no-import Wasm evaluation artifacts require no Rust toolchain for adopters;
8. release artifacts pass ABI/wire/golden/malformed-input conformance;
9. at least one real constrained target has measured binary/RAM/latency evidence and energy where measurable;
10. product claims remain narrower than the evidence.

Full academic catalog completion, dynamic discovery maturity, every domain series, and universal platform Tier 1 parity are **not** prerequisites for the first focused product proof.
