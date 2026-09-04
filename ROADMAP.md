# ExactScope roadmap

No dates are promised. This roadmap is ordered by **capability density, weak-model usability, and retrofit evidence**, not by raw operation count or subsystem breadth.

ExactScope must prove one product proposition:

> **Can a tiny AI-facing capability component let an already-deployed 0.5B-3B on-device model recover enough narrow-domain ability that keeping the current model and hardware becomes the better engineering choice?**

The detailed product architecture is defined in [`docs/CAPABILITY_PRODUCT_ARCHITECTURE.md`](docs/CAPABILITY_PRODUCT_ARCHITECTURE.md). The broader retrofit thesis remains in [`docs/RETROFIT_PRODUCT_STRATEGY.md`](docs/RETROFIT_PRODUCT_STRATEGY.md).

## Current baseline

Implemented today includes:

- deterministic `no_std` numeric kernel;
- checked decimal/rational arithmetic, deterministic square root, and explicit rounding;
- bounded non-Turing-complete scalar VM;
- bounded `xs_calc` plan-v0.1 execution with 1-8 steps over `add/sub/mul/div/powi/sqrt`;
- Tiny JSON `xs_calc` parsing with a 512-byte request bound;
- generated/checked-in `xs_calc` JSON Schema, GBNF, tool definition, and compact prompt guidance;
- native typed C ABI structures for the bounded plan path;
- executable economics operations and bounded statistics kernels;
- semantic `xs_eval` hot sets plus optional cold/development `xs_find`;
- no-import Wasm;
- Tiny JSON and TinyWire;
- llama.cpp reference integration;
- generated digest-bound hot-set assets;
- benchmark and conformance infrastructure;
- pinned-source `public_xs_calc_oracle.py` evidence for FinQA test (1,058 runtime-accepted / 275 exact explicit-answer matches) and TAT-QA dev (717 / 443), explicitly classified as compatibility/deterministic-ceiling evidence rather than model accuracy;
- recorded five-case three-model llama.cpp `xs_calc` integration smoke;
- public `v1.0.0-rc.1` prerelease artifacts for Windows x86-64, Linux x86-64, and Linux ARM64/wearable evaluation;
- wearable reference integration and A/B update reference;
- experimental Android/Linux ARM64 SDK packaging;
- relocatable CMake package and SDK doctor.

The engine and first weak-model arithmetic surface therefore exist. The next blocker is no longer "build a calculator path." The next blocker is proving that **small, domain-focused capability slices create enough measured model improvement per byte/token/millisecond to justify adoption.**

# P0 - prove the capability-unit product

## P0.1 Freeze the first small-model arithmetic surface

- [x] implement bounded `xs_calc` plan-v0.1;
- [x] cap the plan at 8 arithmetic steps;
- [x] restrict operations to `add`, `sub`, `mul`, `div`, `powi`, `sqrt`;
- [x] use exact decimal-string leaves and backward-only previous-result references;
- [x] forbid loops, arbitrary branches, variables, arbitrary functions, arbitrary expression text, and arbitrary code;
- [x] provide deterministic failures with no plausible numeric value on error;
- [x] reuse the shared exact numeric core rather than creating a second arithmetic implementation;
- [x] provide schema/GBNF/tool/prompt assets for constrained generation;
- [ ] freeze the public plan contract only after benchmark and integration evidence supports a stable promise.

Success criterion: even a weak model can be given one small arithmetic interface that is completely bounded and mechanically constrained.

## P0.2 Define the capability-slice profile

Create a machine-readable profile that describes a deployed ExactScope capability slice rather than only a list of operations.

The design-draft profile/schema now records:

- [x] profile ID/revision;
- [x] target domain and task families;
- [x] selected semantic operations;
- [x] whether `xs_calc` is enabled and its plan revision;
- [x] model-visible tool/operation budgets;
- [x] prompt/schema/grammar identity slots and digests;
- [x] binary/RAM/scratch budget fields;
- [x] normal hot-path model-turn budget;
- [x] runtime/profile binding fields;
- [x] conformance/golden evidence identity fields;
- [x] benchmark mapping/result identity fields;
- [ ] implement deterministic validation/generation from repository source metadata;
- [ ] replace experimental null bindings/evidence with released immutable identities before a benchmarked claim;
- [ ] freeze the format only after real benchmark/integration evidence.

Success criterion: a capability slice can be reproduced, benchmarked, qualified, and updated as one immutable product unit.

## P0.3 Add the model-difficulty budget

A slice is not tiny enough merely because its binary is small. It must also be easy for the target model to call.

The draft profile defines fields/ceilings for the static parts; benchmark tooling must measure and publish the dynamic parts:

- [x] model-visible tool-count budget field;
- [x] visible semantic-operation-count budget field;
- [x] prompt/schema/grammar byte budget fields;
- [x] maximum generated-request-token field;
- [x] normal inference-turn budget field;
- [ ] tokenizer-specific prompt token counts;
- [ ] actual structurally valid-call rate;
- [ ] actual core-accepted-call rate;
- [ ] correct plan/operation selection rate;
- [ ] argument extraction rate;
- [ ] result/failure-fidelity rate.

Success criterion: widening a domain catalog cannot silently make the product unusable for the 0.5B-1B class.

## P0.4 Build the first flagship Statistics capability slice

Statistics is the first recommended domain proof because reviewed method identity matters and the core already contains relevant bounded kernels.

The first slice is task-family-driven, not catalog-driven. The design draft in [`docs/STATISTICS_CAPABILITY_SLICE.md`](docs/STATISTICS_CAPABILITY_SLICE.md) selects:

- [x] descriptive aggregation (`sum`, arithmetic mean);
- [x] weighted mean;
- [x] sample/population variance and standard deviation;
- [x] Pearson correlation;
- [x] explicit ambiguity/failure preservation where method assumptions are missing.

For the first slice:

- [x] select the existing `statistics-core-8` semantic operation set;
- [x] keep the normal model-facing surface to `xs_calc` + one compact `xs_eval` tool, with `xs_find` disabled;
- [x] define draft model/device budgets in the capability profile;
- [ ] freeze exact operation/profile bindings and provenance digests;
- [ ] implement the checked-in 240-case target corpus/gold generator or revise the target with documented coverage evidence;
- [ ] add/verify golden, negative, and boundary vectors for the benchmark corpus;
- [ ] create a reproducible benchmark mapping/result bundle;
- [ ] measure marginal artifact, prompt, and runtime cost versus `xs_calc` alone.

Success criterion: the slice is demonstrably a **Statistics capability upgrade**, not merely a collection of statistics functions.

## P0.5 Run the five-arm capability benchmark

Primary small-model classes:

- [ ] approximately 0.5B-0.8B;
- [ ] approximately 1B;
- [ ] approximately 1.5B-2B;
- [ ] approximately 3B;
- [ ] optional stress models below the main range;
- [ ] at least one larger-model reference where fair and feasible.

For the flagship domain proof compare:

- [ ] A: small model only;
- [ ] B: small model + `xs_calc` only;
- [ ] C: small model + Statistics semantic slice;
- [ ] D: small model + `xs_calc` + Statistics semantic slice;
- [ ] E: larger-model reference with its deployment cost reported separately.

Required quality metrics:

- [ ] correct usable answer rate;
- [ ] incorrect numeric answer rate;
- [ ] tool penalty rate;
- [ ] recognition;
- [ ] plan/operation selection;
- [ ] argument extraction;
- [ ] syntax/semantic validity;
- [ ] core acceptance/rejection;
- [ ] result/failure fidelity.

Required cost metrics:

- [ ] binary bytes;
- [ ] resident RAM;
- [ ] scratch/context bytes;
- [ ] prompt/completion tokens;
- [ ] model turns;
- [ ] model latency and ExactScope latency separately;
- [ ] energy where measurable.

Success criterion: show whether the semantic slice adds measurable capability beyond generic exact arithmetic.

## P0.6 Report capability density and Capability Recovery Ratio

Do not hide the product result in one aggregate accuracy number.

For each benchmarked slice report:

- [ ] successful-answer uplift per 100 KiB added artifact;
- [ ] wrong-number reduction per 100 KiB;
- [ ] capability uplift per added resident-memory KiB;
- [ ] capability uplift per added prompt token;
- [ ] capability uplift per added millisecond;
- [ ] capability uplift per joule where measured;
- [ ] raw numerators and denominators beside every density ratio.

When a larger model is a meaningful reference, report:

```text
CRR = (small + ExactScope - small)
      ----------------------------
      (larger model - small)
```

- [ ] never force CRR when the larger model does not beat the small baseline;
- [ ] report CRR only for the benchmark/task family measured;
- [ ] always pair CRR with the added ExactScope resource cost;
- [ ] never translate a narrow-domain CRR into a claim of general model equivalence.

Success criterion: answer directly how much of the larger-model capability gap is recovered per unit of tiny software cost.

## P0.7 Keep the footprint gate hard

Current product direction targets a primary no-import Wasm artifact near or below 128 KiB when practical.

- [ ] record exact released Wasm/native size for every capability profile;
- [ ] report marginal size of each capability slice, not only total binary size;
- [ ] require recorded justification beyond 192 KiB;
- [ ] require explicit design review beyond 256 KiB;
- [ ] report resident RAM and scratch separately from binary size;
- [ ] reject convenience features that materially damage capability density without measured benefit.

Success criterion: ExactScope remains dramatically cheaper than the model/hardware jump it is intended to offset.

# P1 - prove the retrofit on real constrained hardware

## P1.1 Real target qualification

- [ ] choose at least one representative constrained phone/wearable/embedded target;
- [ ] run the same small model with and without ExactScope;
- [ ] run the flagship capability slice on the actual target;
- [ ] measure binary, resident RAM, scratch, latency distribution, and energy where possible;
- [ ] test malformed input and fail-closed behavior;
- [ ] document integration/update/rollback constraints;
- [ ] keep desktop measurements labeled as desktop validation.

Success criterion: the measured target cost remains small enough for the capability-retrofit thesis.

## P1.2 Larger-model / newer-device substitution comparison

Where fair and feasible:

- [ ] compare the existing small model;
- [ ] compare the existing small model + ExactScope capability slice;
- [ ] compare a larger model representing the upgrade path;
- [ ] record model storage/RAM/load/latency/token/energy cost separately;
- [ ] state clearly when the larger model cannot fit the original target hardware.

Success criterion: quantify the engineering trade between a tiny software capability update and a model/hardware generation jump.

# P2 - productize the capability compiler and qualification system

## P2.1 Capability compiler

Build-time tooling should turn a broad reviewed domain source into a minimal deployed slice.

- [ ] input device/model/runtime budget;
- [ ] input required task families;
- [ ] select/fuse the required semantic operations;
- [ ] emit `xs_calc`/`xs_eval` model-facing assets;
- [ ] emit schema/GBNF/prompt fragments;
- [ ] emit immutable manifest/digests;
- [ ] emit conformance vectors and benchmark mapping;
- [ ] emit model-difficulty and footprint metadata.

The first compiler should be deterministic and configuration-driven. Automatic ML-based profile optimization is optional future work.

## P2.2 Stable primary deployment profiles

- [ ] stable native static C ABI package;
- [ ] stable no-import Wasm package;
- [ ] immutable manifests/checksums;
- [ ] exact release-artifact conformance;
- [ ] target self-test;
- [ ] update/rollback-compatible artifact identity;
- [ ] stable schema/ABI only after evidence supports freezing it.

## P2.3 Integration and qualification moat

- [ ] maintained weak-model reference integrations;
- [ ] deterministic schema/grammar version negotiation;
- [ ] malformed-input/security review;
- [ ] supply-chain/reproducibility evidence;
- [ ] compatibility records for selected toolchains/architectures;
- [ ] model-by-model benchmark records;
- [ ] LTS operation-revision policy.

This work is part of the build-vs-buy value: a vendor adopting ExactScope should avoid recreating and maintaining this whole stack internally.

# P3 - expand domain capability sources only after proof

ExactScope domains are one shared runtime plus reviewed source catalogs from which small deployment slices are compiled. They are not separate human calculators.

Recommended order after the first Statistics proof:

1. Statistics;
2. Economics;
3. Finance;
4. Math/task-specific quantitative helpers not already covered by `xs_calc`;
5. Physics;
6. Engineering;
7. Chemistry;
8. later OEM/domain-specific sources where real product pull exists.

For every domain:

- [ ] reuse the same deterministic core/ABI;
- [ ] define explicit semantic/unit/method contracts;
- [ ] provide provenance and revision history;
- [ ] provide golden/negative/boundary vectors;
- [ ] define capability units/task families before maximizing operation count;
- [ ] compile small model-facing slices rather than exposing the full source catalog;
- [ ] benchmark weak-model usability and marginal footprint;
- [ ] publish compatibility/qualification evidence appropriate to the domain.

Domain breadth must not weaken the tiny model surface or delay measured product proof.

# Commercial/product work

- [x] define ExactScope as an AI capability retrofit rather than a calculator product;
- [x] define the runtime consumer as the AI, with the developer/OEM engineer as integrator;
- [x] define capability slice, model-difficulty budget, capability density, and CRR as product concepts;
- [ ] publish the first reproducible Statistics capability-slice benchmark;
- [ ] publish small-model + ExactScope versus larger-model cost/quality evidence;
- [ ] create an OEM/developer integration brief based on measured evidence;
- [ ] publish at least one real-target qualification case study before claiming useful hardware-life extension;
- [ ] build verified domain source/LTS/qualification/custom-profile offerings only after technical pull exists.

# Explicit non-goals

- human calculator UI or user-facing calculation product;
- end-user formula selection or formula browsing;
- general chatbot;
- general Python/scientific runtime;
- arbitrary model-generated code execution;
- general symbolic algebra;
- mandatory cloud/account/telemetry;
- ExactScope-owned daemon;
- hidden semantic repair;
- forcing a full academic catalog into a weak-model prompt;
- solving recognition/world-knowledge/perception limitations by pretending they are arithmetic failures;
- universal platform parity before product proof;
- raw catalog breadth for its own sake;
- claiming that ExactScope replaces every hardware or model upgrade.

# Stable product gate

ExactScope should not be called a stable capability-retrofit product until all of the following are true:

1. bounded `xs_calc` semantics and model-facing assets have reproducible release evidence;
2. at least one machine-readable capability-slice profile is frozen and reproducible;
3. at least one Statistics capability slice has a reviewed task-family benchmark;
4. multiple 0.5B-3B models have reproducible model-only versus ExactScope results;
5. wrong-number reduction, tool penalty, rejection, turns/tokens/latency, model-difficulty, and resource cost are reported;
6. capability-density measurements are published with raw values;
7. a larger-model reference and CRR are published where meaningful;
8. stable native static and/or no-import Wasm artifacts require no target-side language runtime or service;
9. release artifacts pass ABI/wire/golden/malformed-input conformance;
10. at least one real constrained target has measured binary/RAM/latency evidence and energy where measurable;
11. update/rollback behavior is documented;
12. product claims remain narrower than the evidence.

Full academic catalog completion, every domain series, automatic profile optimization, and universal platform Tier 1 parity are **not** prerequisites for the first focused product proof.
