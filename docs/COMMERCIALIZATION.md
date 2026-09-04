# ExactScope commercialization direction

ExactScope core is open infrastructure. Commercial value, if pursued, should come from assurance, qualification, long-term maintenance, domain packs, and integration support rather than from locking deterministic arithmetic behind a proprietary runtime.

## 1. OSS core

The core runtime remains permissively licensed under Apache-2.0/MIT and includes:

- deterministic numeric kernel;
- stable C ABI and no-import Wasm ABI;
- public scope-pack format;
- baseline official operation metadata and conformance tooling;
- reference adapter formats and benchmark methodology.

The OSS core is the adoption wedge. A large vendor should be able to prove technical value before entering a commercial relationship.

## 2. Possible commercial layers

### 2.1 Verified domain packs

Commercial or enterprise-supported packs may provide:

- independently reviewed formulas/methods;
- provenance and revision history;
- larger golden/negative corpora;
- long-term operation-revision support;
- change-control guarantees;
- domain-specific compatibility records.

Possible future domains include finance, insurance, industrial formulas, scientific instrumentation, regulated reporting, or organization-specific deterministic calculations.

### 2.2 Enterprise LTS and SLA

Potential offering:

- long-term supported ExactScope core branch;
- security and parser/ABI fixes;
- reproducible release artifacts;
- support response targets;
- compatibility notices and migration guidance;
- maintained target/toolchain matrix.

### 2.3 OEM qualification

A device/vendor engagement may cover:

- target integration review;
- memory/latency/energy qualification;
- malformed-input and update/rollback testing;
- artifact identity and supply-chain evidence;
- signed qualification reports;
- assistance integrating with the customer's local model/tool router.

The value is not merely the formula implementation. It is the evidence that a specific ExactScope artifact, pack set, and target combination behaves within a defined contract.

### 2.4 Custom domain-pack engineering

Customers may need deterministic operations that do not belong in the public academic catalog. These should still compile to the same data-only pack format or shared bounded kernel contracts rather than creating customer-specific calculation forks.

## 3. What should not become the business model

Avoid commercial pressure that would damage the technical wedge:

- mandatory cloud calls;
- per-evaluation telemetry;
- account/login requirements in the core;
- proprietary target daemon;
- hidden formula semantics;
- proprietary incompatible ABI forks;
- arbitrary native plugins inside packs.

The product should remain attractive precisely because it can be embedded, audited, and operated offline.

## 4. Enterprise/OEM adoption funnel

The desired funnel is:

```text
public retrofit benchmark + prebuilt tiny artifact
        -> 5-minute local proof
        -> customer's existing small-model benchmark
        -> existing-device integration
        -> OTA/update/rollback proof
        -> target qualification
        -> LTS/support if needed
```

The project should not require a sales conversation before a technical evaluator can measure value.

The strongest commercial wedge may be **already-designed or already-deployed devices** where replacing the SoC, memory configuration, thermal design, or model-size class is expensive or impossible but software can still be updated.

## 5. Market positioning

ExactScope should not define its market as only "devices with no network." Offline capability is a feature, not the market definition.

The primary target is:

> **Physically constrained or deployed on-device AI products that want to gain deterministic quantitative capability through a tiny software retrofit instead of requiring a hardware/model-size upgrade for every capability gap.**

Representative environments:

- smart glasses and wearables;
- phones and tablets;
- embedded assistants;
- robots and industrial systems;
- automotive systems;
- other constrained edge products;
- later regulated or certifiable product paths where arbitrary-code sandboxes are undesirable.

Desktop/server environments remain useful for evaluation and integration, but they are not the center of the product thesis.

## 6. Competitive framing

ExactScope should not compete with Python, MCP calculators, or large symbolic systems on breadth, and it should not claim to invent external computation for language models.

The differentiator is the combination of:

- **retrofit/OTA suitability as a primary design objective**;
- tiny resident footprint;
- no required service/runtime environment;
- one bounded arithmetic-plan surface for common short numerical work once implemented;
- reviewed semantic operations for method-specific work;
- deterministic exact decimal/rational semantics;
- no arbitrary model-generated code execution;
- fail-closed validation;
- stable operation revision/provenance;
- native static C ABI and no-import Wasm;
- model-independent target qualification potential.

The core competitive comparison should often be:

```text
existing small model
vs
existing small model + ExactScope
vs
larger model / next hardware generation
```

For a product where a larger model or trusted Python sandbox is already cheap, acceptable, and easy to deploy/qualify, ExactScope may provide little advantage. That is an acceptable non-target.

## 7. Commercial proof gate

Commercial effort should follow evidence. Before presenting ExactScope as an OEM retrofit/optimization product, publish at least:

1. a reproducible public benchmark showing a material advantage across multiple constrained model classes;
2. incorrect-numeric-answer reduction and tool-penalty measurements, not only aggregate accuracy;
3. a prebuilt tiny artifact that a non-Rust integrator can run quickly;
4. one documented `xs_calc`/`xs_eval` integration with a common local-AI runtime after the vNext plan path exists;
5. one real-target qualification record with measured binary size, resident/scratch memory, and latency, plus energy where measurable;
6. an update/rollback integration note showing how an existing product could add/remove the component safely;
7. where practical, a small-model + ExactScope versus larger-model comparison with resource cost reported separately.

Until then, commercialization and hardware-life-extension language remain product hypotheses rather than proven customer savings claims.
