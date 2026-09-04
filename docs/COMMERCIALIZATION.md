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

## 4. Enterprise adoption funnel

The desired funnel is:

```text
public benchmark + prebuilt artifact
        -> 5-minute local proof
        -> customer's own benchmark
        -> target integration
        -> qualification/LTS/support if needed
```

The project should not require a sales conversation before a technical evaluator can measure value.

## 5. Market positioning

ExactScope should not define its market as only "devices with no network." Offline capability is a feature, not the entire niche.

The broader target is:

> AI products that need bounded, auditable, deterministic quantitative execution without embedding Python/scientific runtimes or relying on model arithmetic.

Representative environments:

- smart glasses and wearables;
- phones and tablets;
- embedded assistants;
- robots and industrial systems;
- automotive systems;
- private/local desktop AI;
- small cloud/edge agents that still value deterministic bounded execution;
- regulated or certifiable product paths where arbitrary-code sandboxes are undesirable.

## 6. Competitive framing

ExactScope should not compete with Python, MCP calculators, or large symbolic systems on breadth.

The differentiator is the combination of:

- tiny resident footprint;
- no required service/runtime environment;
- bounded operation surface;
- deterministic semantics;
- no arbitrary code execution in packs;
- stable operation revision/provenance;
- hot-set packaging;
- target qualification potential.

For a product where a Python sandbox is already cheap, acceptable, and easy to certify, ExactScope may provide little advantage. That is an acceptable non-target.

## 7. Commercial proof gate

Commercial effort should follow evidence. Before presenting ExactScope as an enterprise optimization product, publish at least:

1. a reproducible benchmark showing a material advantage for one constrained-model scenario;
2. a prebuilt artifact that a non-Rust integrator can run quickly;
3. one documented hot-set integration with a common local-AI runtime;
4. one target qualification record with real size/latency/memory data.

Until then, commercialization remains a direction rather than a revenue claim.
