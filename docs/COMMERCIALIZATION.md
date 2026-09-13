# ExactScope commercialization direction

Release context: **v1.0.0 is the stable Linux x86-64 grounding baseline; v1.1 remains unreleased.** The preregistered Qwen/FEVER Stage 1 stopped at `ReferenceOnly` before held-out, so successful cost compilation is not demonstrated. v1.1 is now narrowed to a qualification/configuration optimizer with semantic enforcement and immutable qualification records; the compiler category remains a research hypothesis. Customer value, recurring savings and willingness to pay remain unproved.

## v1.1 commercial hypothesis — Qualified Execution Profile

The proposed v1.1 customer offer is not a generic "runtime amplifier." It is a **Qualified Execution Profile**: ExactScope evaluates a bounded set of semantic configurations for a customer's existing AI stack and produces a deployable candidate policy plus independent qualification attestation only when prospectively declared competence, evidence-support, latency and total-economic requirements pass on fresh data. A lower-cost reference-preserving policy is one conditional qualified outcome, not the only form of customer value.

The current product category is a **qualification/configuration optimizer with semantic enforcement and immutable qualification records**. **Semantic Inference Policy Compiler** remains an internal research hypothesis, and reference-preserving cost reduction remains a research algorithm after the FEVER Stage 1 `ReferenceOnly` stop. Neither should be sold as established category value.

The strongest first commercial validation target remains a **high-volume bounded enterprise document-QA service with a genuinely pinned or expensive-to-change model**, but the initial task should be narrower than open-ended synthesis: short factual answers, extraction, typed decisions, and citation/provenance-bound outputs. This gives auditable authoritative evidence, measurable serving economics, and repeated traffic capable of amortizing calibration and qualification.

The likely buyer is the team jointly accountable for **application quality and inference spend**. A pinned model is a customer constraint to validate, not a moat. If a better model or simpler runtime change is deployable and wins on total economics, ExactScope should recommend that alternative rather than depend on blocking a rational upgrade.

The first commercial test should look more like a bounded paid evaluation/profile-delivery engagement than a hosted control plane. A useful pilot must measure:

- competence and economics of the customer's real incumbent configuration;
- a strong fixed intervention/reference;
- a matched-budget conventional/DSPy-style tuning workflow;
- a better-model alternative where deployable;
- actual integration engineer-hours;
- serving savings after retrieval/projection/inference/rejection/fallback accounting;
- qualification and refresh cost;
- break-even eligible volume and payback period;
- continued value through at least one profile refresh.

A project-based pilot can establish demand. Repeated bespoke delivery without reusable integration or prospective selection advantage would indicate a services business rather than a compiler moat. Reasonable initial hypotheses such as roughly five engineer-days to integrate and roughly 90-day payback must be validated with the buyer and frozen before scoring; they are not current product claims.

Long-term adoption can still include runtime/platform and on-device teams, but runtime count, adapter count, tiny profile size and bridge compatibility are not purchase reasons by themselves. `ExactScope Bridge` remains an integration pressure test rather than the commercial product.

ExactScope core may remain open infrastructure. Commercial value, if pursued, should come from the maintained **semantic contract, qualification lifecycle, profile production, source/evidence policy engineering, evidence revision/freshness handling, reproducible economics, and lower customer effort** that can be shown prospectively. It should not come from hiding arithmetic, private memory, retrieval access, generic evaluation, or inference-runtime machinery behind a proprietary layer.

The stable-v1 grounding/source products below remain valid v1.0 commercialization material; they should not be confused with the unproved v1.1 Qualified Execution Profile thesis. See [`V1_1_PRODUCT_DIFFERENTIATION.md`](V1_1_PRODUCT_DIFFERENTIATION.md), [`V1_1_STAGE1_PREREGISTRATION.md`](V1_1_STAGE1_PREREGISTRATION.md), and [`V1_1_DIRECTION_REFRAME_ASTRA_REVIEW.md`](V1_1_DIRECTION_REFRAME_ASTRA_REVIEW.md) for current v1.1 scope. See [`GROUNDING_ARCHITECTURE.md`](GROUNDING_ARCHITECTURE.md) and [`../spec/GROUNDING_CONTRACT_V0_1.md`](../spec/GROUNDING_CONTRACT_V0_1.md) for the stable-v1 grounding contract. [`CAPABILITY_PRODUCT_ARCHITECTURE.md`](CAPABILITY_PRODUCT_ARCHITECTURE.md) remains the quantitative-subsystem product-unit reference.

## 1. Customer and runtime user

ExactScope has two different roles that must not be confused:

- **runtime consumer:** the existing constrained/pinned AI system, which may be an enterprise service, local model, or on-device stack;
- **customer/integrator:** the software, AI, platform, enterprise, or device team embedding ExactScope into that system.

The consumer of the product is not a person typing equations into an ExactScope application. End users should normally never see an ExactScope UI, choose formulas, install a calculator, or configure capability packs manually.

## 2. OSS core as the adoption wedge

The core runtime remains permissively licensed under Apache-2.0/MIT and should include enough public infrastructure for a vendor to prove the mechanism before any commercial relationship:

- provider-neutral Grounding Contract and reference Evidence Policy;
- at least one small local retrieval-provider baseline;
- compact Grounding Frame integration examples;
- source/provider/index identity and evidence-budget manifests;
- benchmark methodology for everyday factual accuracy, false grounding and wrong-confident answers;
- deterministic numeric kernel and bounded `xs_calc`/selected `xs_eval` subsystem;
- stable/native C ABI direction and no-import Wasm path where applicable;
- conformance tooling and reference integrations.

A large vendor must be able to answer "does this actually improve our small model cheaply enough, without creating a false-grounding/privacy problem?" before buying anything.

## 3. Why a large vendor should adopt instead of rebuild

A large vendor can build a simple keyword search, vector index, RAG prompt, or individual arithmetic formula internally. Any one of those primitives alone is therefore not a defensible commercial wedge.

The build-vs-buy value is the maintained **small-model grounding system** around those primitives:

- provider-neutral source/retrieval contracts;
- authoritative vs supplemental source behavior;
- revision/freshness/conflict/ambiguity policy;
- compact evidence/context budgeting;
- privacy/scope isolation;
- provider/index identity and reproducible evidence snapshots;
- high-precision retrieval and false-grounding evaluation;
- one-call prefetch integration that avoids model tool-protocol dependency;
- model-by-model everyday accuracy / wrong-confident-answer evidence;
- binary/RAM/index/token/latency optimization;
- target qualification and update/rollback compatibility;
- maintained deterministic calculation capability where required;
- long-term maintenance as models, runtimes, sources and devices change.

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

### 4.1 Grounding source/provider assurance

The strongest near-term commercial layer is not an academic formula catalog. It is a maintained grounding profile for a target product:

- source inventory and authority classification;
- private/application/manual/public source adapters;
- retrieval-provider selection and index construction;
- compact evidence/profile budgets for the target tokenizer/model;
- freshness/revision/conflict policy;
- privacy and tenant/user scope review;
- false-grounding and everyday-accuracy qualification;
- immutable provider/index/profile manifests;
- update/rollback and evidence drift reporting.

A vendor may keep its data fully private while using the same Grounding Contract and qualification tooling.

### 4.2 Verified domain source catalogs — quantitative subsystem

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

### 4.3 Capability-slice/profile engineering

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

### 4.4 Enterprise LTS and SLA

Potential offering:

- long-term supported ExactScope core/profile branches;
- security, parser, ABI, and model-surface fixes;
- reproducible release artifacts;
- operation/profile compatibility notices;
- migration guidance;
- maintained target/toolchain/runtime matrix;
- support response targets.

### 4.5 OEM/device qualification

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

### 4.6 Custom domain capability engineering

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

The desired funnel remains technical first, but the first commercial proof should be narrower and economically measurable:

```text
public research evidence + tiny host-attached prototype
        -> developer reproduces Base B / reference F evaluation
        -> customer's competent pinned-model document-QA benchmark
        -> preregistered calibration / qualification
        -> CompiledCandidate(P) or ReferenceOnly(F)
        -> customer-like fresh held-out proof
        -> serving-cost + quality + integration payback analysis
        -> production pilot
        -> maintained profiles / requalification / LTS where valuable
```

The project should not require a sales conversation before a technical evaluator can measure value. It also should not treat `ReferenceOnly(F)` as successful compiler commercialization: that outcome may validate the intervention/reference, but it shows no incremental selection value.

The strongest **first commercial validation wedge** is now a **high-volume, bounded enterprise document-answering service** where the model is pinned or expensive to change, authoritative source spans make correctness auditable, serving cost is measurable, and calibration can amortize across enough repeated traffic.

## 8. Market positioning

ExactScope should not define its market as only "offline AI" and should not define itself as a calculator library.

The immediate validation target is:

> **A competent existing document-QA stack whose model is operationally constrained, where ExactScope can be judged on fresh answer quality, reference preservation, serving cost, integration effort, and calibration payback.**

Longer-term markets still include:

- smart glasses and wearables;
- phones and tablets;
- embedded assistants;
- robots and industrial systems;
- automotive systems;
- privacy-sensitive or fixed enterprise stacks;
- other constrained edge products;
- later regulated/certifiable product paths where arbitrary-code sandboxes are undesirable.

On-device/retrofit suitability remains an important architecture constraint and future market. It is no longer the only or automatic first proof. A server/enterprise workload is acceptable when it provides the clearest prospective evidence that keeping the same model is economically preferable to using a better model or a heavier RAG/test-time-scaling path.

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
- a small-footprint target, with exact binary/RSS/stack/scratch measured before any product claim;
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
