# ExactScope commercialization direction

ExactScope core is open infrastructure. Commercial value, if pursued, should come from **maintained AI capability products**: reviewed domain semantics, weak-model interface engineering, capability-slice/profile generation, benchmark evidence, qualification, long-term revision support, and integration assistance.

It should not come from hiding arithmetic behind a proprietary runtime.

See [`CAPABILITY_PRODUCT_ARCHITECTURE.md`](CAPABILITY_PRODUCT_ARCHITECTURE.md) for the product-unit definition.

## 1. Customer and runtime user

ExactScope has two different roles that must not be confused:

- **runtime consumer:** the small/on-device AI system;
- **customer/integrator:** the software, AI, platform, or device team embedding ExactScope into that AI system.

The consumer of the product is not a person typing equations into an ExactScope application. End users should normally never see an ExactScope UI, choose formulas, install a calculator, or configure capability packs manually.

## 2. OSS core as the adoption wedge

The core runtime remains permissively licensed under Apache-2.0/MIT and should include enough public infrastructure for a vendor to prove the mechanism before any commercial relationship:

- deterministic numeric kernel;
- bounded `xs_calc` model-facing arithmetic path;
- stable/native C ABI direction and no-import Wasm path;
- public scope-pack/source formats where applicable;
- baseline official semantic operation metadata;
- constrained model-interface assets;
- conformance tooling;
- benchmark methodology;
- reference integrations.

A large vendor must be able to answer "does this actually improve our small model cheaply enough?" before buying anything.

## 3. Why a large vendor should adopt instead of rebuild

A large vendor can implement arithmetic, variance, correlation, elasticity, or other individual formulas internally. Formula implementation alone is therefore not a defensible commercial wedge.

The build-vs-buy value is the maintained system around those formulas:

- weak-model-friendly tool-surface design;
- minimal prompts and operation-choice surfaces;
- generated JSON Schema/GBNF/typed bindings;
- deterministic exact numeric behavior;
- explicit semantic/method/unit contracts;
- provenance and operation revision history;
- golden, negative, malformed-input, and boundary corpora;
- binary/RAM/scratch optimization;
- native C ABI and no-import Wasm portability;
- digest-bound immutable artifacts;
- model-by-model benchmark evidence;
- target qualification;
- update/rollback compatibility;
- long-term maintenance of the above as models, runtimes, and devices change.

The commercial question should become:

```text
build internally
  = own and maintain all of that forever

adopt ExactScope
  = select a proven capability slice,
    benchmark it on the target model,
    integrate one tiny component,
    consume maintained revisions and qualification evidence
```

The moat is cumulative engineering and evidence, not formula secrecy.

## 4. Commercial product layers

### 4.1 Verified domain source catalogs

A commercial or enterprise-supported domain source may provide:

- independently reviewed formulas and methods;
- explicit units, conventions, and assumptions;
- provenance and revision history;
- larger golden/negative/boundary corpora;
- long-term operation-revision support;
- change-control guarantees;
- domain-specific benchmark mappings;
- compatibility and qualification metadata.

Possible future domains include Statistics, Economics, Finance, Physics, Engineering, scientific instrumentation, insurance, regulated reporting, industrial calculations, and organization-specific deterministic methods.

A broad source catalog is a maintained build-time asset. It is not automatically exposed to the small model.

### 4.2 Capability-slice/profile engineering

A higher-value offering is the production of **minimal capability slices** for a target model/device/runtime budget.

This may include:

- task-family selection;
- operation subset selection;
- fused/static profile generation;
- minimal model prompt/tool surface;
- constrained-decoding assets;
- model-difficulty measurements;
- binary/RAM/scratch footprint reports;
- target-model benchmark reports;
- immutable profile manifests.

This directly addresses the vendor problem: "give this exact weak model the capability we need without spending more flash, RAM, tokens, latency, or engineering time than necessary."

### 4.3 Enterprise LTS and SLA

Potential offering:

- long-term supported ExactScope core/profile branches;
- security, parser, ABI, and model-surface fixes;
- reproducible release artifacts;
- operation/profile compatibility notices;
- migration guidance;
- maintained target/toolchain/runtime matrix;
- support response targets.

### 4.4 OEM/device qualification

A device/vendor engagement may cover:

- target integration review;
- flash/RAM/scratch/latency/energy qualification;
- malformed-input and fail-closed validation;
- update/rollback testing;
- artifact identity and supply-chain evidence;
- model/tool-router integration review;
- capability-density and Capability Recovery Ratio reporting;
- signed qualification records where commercially appropriate.

The value is not merely that "the formula is correct." It is evidence that a specific ExactScope artifact, capability profile, model/runtime, and target behave within a defined product contract.

### 4.5 Custom domain capability engineering

Customers may need deterministic capabilities that do not belong in a public academic source catalog. These should still reuse the same shared bounded core and capability-profile machinery rather than creating customer-specific calculation forks.

## 5. Capability compiler as a product multiplier

The long-term integration product should include a deterministic build-time capability compiler/profile generator.

Input should describe:

- target model class;
- inference runtime;
- device footprint budget;
- allowed model turns/tokens;
- required task families;
- selected domain sources.

Output should include:

- the minimal deployable ExactScope artifact/profile;
- selected reviewed operations;
- `xs_calc` and compact `xs_eval` assets as needed;
- schema/grammar/prompt fragments;
- manifests and digests;
- conformance vectors;
- model-difficulty metadata;
- footprint metadata;
- benchmark mapping.

A vendor may be able to recreate one formula cheaply. Recreating and continuously maintaining this compiler + evidence system is a materially different cost.

## 6. What should not become the business model

Avoid commercial pressure that damages the technical wedge:

- mandatory cloud calls;
- per-evaluation telemetry requirements;
- account/login requirements in the runtime;
- end-user subscription calculator applications;
- user-facing formula browsers;
- proprietary target daemon;
- hidden formula semantics;
- proprietary incompatible ABI forks;
- arbitrary native plugins inside packs;
- deliberately bloated catalogs designed only to increase SKU count.

The product should remain attractive because it can be embedded invisibly into an AI product, audited, qualified, and operated offline or locally when required.

## 7. Adoption funnel

The desired funnel is technical first:

```text
public capability benchmark + prebuilt tiny artifact
        -> 5-minute developer proof
        -> customer's existing weak-model benchmark
        -> select/compile smallest useful capability slice
        -> existing-device integration
        -> OTA/update/rollback proof
        -> target qualification
        -> maintained profiles / LTS / support where valuable
```

The project should not require a sales conversation before a technical evaluator can measure value.

The strongest commercial wedge is likely **already-designed or already-deployed constrained AI hardware** where changing the SoC, RAM, thermal design, battery budget, or model-size class is expensive or impossible but software can still be updated.

## 8. Market positioning

ExactScope should not define its market as only "offline AI" and should not define itself as a calculator library.

The primary target is:

> **Physically constrained or already-deployed on-device AI products that need a narrow professional/academic capability upgrade through a tiny software component instead of a model-size or hardware generation jump.**

Representative environments include:

- smart glasses and wearables;
- phones and tablets;
- embedded assistants;
- robots and industrial systems;
- automotive systems;
- other constrained edge products;
- later regulated/certifiable product paths where arbitrary-code sandboxes are undesirable.

Desktop/server environments remain useful for evaluation and integration, but they are not the center of the product thesis.

## 9. Competitive framing

ExactScope should not primarily compare itself with Python, MCP calculators, spreadsheet engines, or symbolic-math systems. Those products solve different problems and may be perfectly adequate where runtime size and qualification cost are unimportant.

The economically relevant comparison is often:

```text
existing small model
vs
existing small model + ExactScope capability slice
vs
larger model / next hardware generation
```

The differentiating systems combination is:

- retrofit/OTA suitability;
- very small resident footprint;
- weak-model-friendly constrained interface;
- one bounded arithmetic-plan surface;
- small reviewed semantic capability slices;
- deterministic exact decimal/rational semantics;
- no arbitrary model-generated code execution;
- fail-closed validation;
- stable operation/profile provenance;
- native static C ABI and no-import Wasm;
- reproducible model and target qualification.

For a product where a larger model is already cheap, fits comfortably, and has acceptable latency/energy/qualification cost, ExactScope may provide little advantage. That is an acceptable non-target.

## 10. Commercial KPIs

The first commercial evidence should report more than accuracy.

Required product-level measurements include:

- successful-answer uplift;
- wrong-number reduction;
- tool penalty rate;
- structurally valid and accepted call rate on weak models;
- added binary/RAM/scratch;
- added prompt/completion tokens;
- added end-to-end latency;
- energy where measurable;
- capability density;
- Capability Recovery Ratio against a larger model where meaningful;
- engineering/update/qualification constraints.

A domain with 200 operations and no measured small-model uplift is commercially weaker than an 8-operation slice that closes a valuable capability gap at negligible cost.

## 11. Commercial proof gate

Before presenting ExactScope as a credible OEM capability-retrofit product, publish at least:

1. one reproducible capability-slice benchmark across multiple constrained model classes;
2. one flagship domain slice, recommended first target: Statistics;
3. incorrect-numeric-answer reduction and tool-penalty measurements;
4. model-difficulty measurements showing that weak models can actually use the interface;
5. a prebuilt tiny artifact a non-Rust integrator can run quickly;
6. one documented `xs_calc` + semantic-slice integration with a common local-AI runtime;
7. one real-target qualification record with binary, resident/scratch memory, latency, and energy where measurable;
8. an update/rollback integration note;
9. a small-model + ExactScope versus larger-model comparison where fair;
10. capability-density and CRR reporting with raw underlying values.

Until then, hardware-life extension, larger-model substitution, and customer-cost-saving language remain hypotheses rather than proven commercial claims.
