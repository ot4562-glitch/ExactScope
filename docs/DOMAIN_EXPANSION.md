# ExactScope domain expansion architecture

Status: **deferred quantitative-subsystem guidance; not an active rc4 product priority**

> rc4 flagship work has moved to everyday factual grounding and hallucination reduction. See [`GROUNDING_ARCHITECTURE.md`](GROUNDING_ARCHITECTURE.md) and [`../spec/GROUNDING_CONTRACT_V0_1.md`](../spec/GROUNDING_CONTRACT_V0_1.md). The domain ordering below remains useful only if/when quantitative academic expansion resumes after grounding value is proven or a concrete customer workload requires it.

Within the quantitative subsystem, ExactScope expands by adding reviewed deterministic **domain source catalogs** and compiling small task-family capability slices from them. It does not grow by creating one runtime, one chatbot tool set, or one calculator application per discipline.

## 1. Expansion law

A new discipline must fit this pipeline:

```text
reviewed domain sources
        |
        v
semantic source catalog
(operation identity + method + units + provenance + tests)
        |
        v
task-family map
(real capability outcomes, not raw formula count)
        |
        v
implementation bindings
(shared kernel / bounded VM / reviewed specialized kernel)
        |
        v
capability compiler
        |
        +--> small constrained request surface
        +--> optional native-tool envelope
        +--> native / no-import Wasm artifact
        +--> manifest / digests / conformance / benchmark mapping
```

The broad academic catalog is a build-time maintenance asset. A deployed small model sees only the task families needed by that product.

## 2. What qualifies as an ExactScope domain

A candidate discipline is a good fit when the useful task can be expressed as:

- a bounded deterministic calculation;
- an explicit reviewed method or convention;
- typed, bounded inputs;
- explicit unit/rate/convention requirements;
- a deterministic value or typed failure;
- independently reviewable provenance and golden/negative cases.

A domain is a poor fit when the central task requires:

- open-ended theorem proving;
- arbitrary symbolic manipulation;
- unrestricted program execution;
- forecasting or prediction from live data;
- subjective interpretation;
- retrieval-heavy factual knowledge rather than calculation;
- hidden assumptions that cannot be made explicit in the operation contract.

ExactScope may support deterministic subproblems inside a broader discipline without claiming to implement the discipline itself.

## 3. Required files for a new reviewed domain

The current domain descriptor mechanism already establishes the minimum structural contract. A new domain should add:

```text
spec/capabilities/domain-descriptors.json
  -> new domain entry

<domain semantic source>.json
  -> pack identity
  -> reviewed operations
  -> method/convention identity
  -> input/output semantics
  -> provenance
  -> golden + negative tests

spec/capabilities/<domain>-task-families.json
  -> outcome/task-family -> reviewed operation mapping

spec/implementation/<domain>-operation-bindings.json
  -> operation -> shared kernel / bounded VM / specialized implementation binding
```

A domain also needs deterministic generator/drift checks, conformance coverage, capability-profile examples, and benchmark mappings before it can be treated as a maintained product domain.

## 4. One core, domain-specific semantics

Do not create a new numeric engine per discipline.

Preferred implementation order for every operation:

1. reuse an existing exact/shared kernel when semantics truly match;
2. lower into the bounded VM when the method can be expressed safely and compactly;
3. add a reviewed specialized kernel only when the first two are insufficient or materially worse for footprint/correctness.

A new specialized kernel must still enter the same operation/revision/ABI/conformance system. It does not become a parallel authority.

## 5. Domain sequencing

### Stage A — finish the model interface and harden current domains

Current reviewed roots:

- **Statistics** — strongest initial semantic-method domain;
- **Economics** — currently narrow, beginning with explicit reviewed elasticity semantics.

Before broadening domains, rc4 should finish:

- constrained request surface for normal capability builds;
- deterministic native-tool vs constrained envelope selection;
- model-interface efficiency reporting;
- current Statistics/Economics regression coverage.

This prevents every future domain from inheriting the rc3 tool-protocol problem.

### Stage B — Finance as the likely next flagship domain

Finance is a strong next candidate because many high-value subproblems are:

- deterministic;
- decimal-sensitive;
- convention-sensitive;
- common on constrained assistants;
- naturally expressible as small task families.

Initial finance scope should be deliberately convention-explicit, for example:

- simple interest;
- compound future/present value with explicit period count and rate basis;
- annuity present/future value with explicit timing convention;
- loan payment/amortization primitives with explicit rate/period inputs;
- percentage return / growth operations with explicit interpretation.

Do **not** begin with calendar/date schedules, taxes, securities pricing, live FX/market data, or jurisdiction-specific rules. Those create hidden external-state and convention dependencies before the core finance contract is proven.

### Stage C — Units/dimensions foundation, then Physics/Engineering

Physics and engineering should not be expanded by copying formula sheets into the repository.

Before these domains become first-class, ExactScope needs a stronger reviewed unit/dimension layer covering at least:

- dimension identity;
- compatible-unit enforcement;
- explicit conversion authority;
- scale/offset conversion rules where applicable;
- constants identity, provenance and revision;
- result-unit derivation;
- rejection of dimensionally invalid inputs.

Once that foundation exists, add narrow task families such as mechanics/electrical/thermal calculations whose equations and assumptions are explicit and bounded.

A model must never be allowed to silently decide that `cm`, `m`, `N`, `J`, `C`, `K`, percent, basis points, or a currency/rate convention are interchangeable.

### Stage D — Chemistry and additional scientific/engineering slices

Chemistry and other science domains can follow the units/constants foundation where useful deterministic subproblems exist, such as bounded stoichiometric or concentration calculations with explicit quantities and conventions.

They should be added as small capability families, not as a claim that ExactScope is a general chemistry/scientific-computing engine.

### Stage E — Additional academic domains only from measured workload demand

Further disciplines should enter only when a real workload demonstrates that:

- the small model has a measurable deterministic capability gap;
- the task can be represented without semantic guessing;
- the capability slice remains small;
- ExactScope materially reduces plausible wrong numeric output;
- the new domain justifies maintenance/provenance/conformance cost.

Operation count is never a roadmap target.

## 6. Mathematics is infrastructure plus bounded capability families

Do not create a giant `math` domain that turns ExactScope into a general CAS or expression evaluator.

Generic exact arithmetic remains `xs_calc`. Additional mathematical capability should be added only as bounded reviewed families when needed, for example geometry or explicit numeric transforms whose method/domain is fixed.

Transcendental functions, advanced numerical methods or approximations require an explicit numeric-profile decision, error contract and conformance strategy before being added. They must not silently weaken the exact decimal/rational baseline.

## 7. Task-family selection rule

A new operation belongs in a domain source catalog only when its semantic identity is reviewable. It belongs in a deployed slice only when it contributes to a real task family.

For example:

```text
finance source catalog
    |
    +-- time-value-basic
    |     +-- fin.pv.compound
    |     +-- fin.fv.compound
    |
    +-- annuity-basic
    |     +-- fin.annuity.pv.ordinary
    |     +-- fin.annuity.fv.ordinary
    |
    `-- loan-basic
          +-- fin.loan.payment.fixed
```

A tiny assistant that only needs loan payment should not see all finance operations.

## 8. Model-facing rule for every future domain

Every AI-facing domain slice follows the rc4 model-interface architecture:

- constrained JSON/GBNF is the compatibility baseline;
- native tools are optional and selected only from proven runtime capability metadata before inference;
- the model performs intent/lane/operation selection and exact argument extraction;
- ExactScope performs the deterministic calculation;
- no post-output envelope retry;
- no semantic repair;
- no full-domain catalog in the weak-model prompt.

Domain expansion therefore does not multiply tool-protocol complexity.

## 9. Domain admission gate

Before adding a new domain to `domain-descriptors.json`, require a short design record answering:

1. What product/task family does this recover for a small model?
2. Which methods/conventions must be explicit?
3. What units/constants/external-state assumptions exist?
4. Can the task fail closed when information is missing?
5. Which current shared kernels/VM instructions are reusable?
6. What genuinely new deterministic semantics are required?
7. What is the expected capability-slice operation count and model-surface cost?
8. What benchmark proves end-to-end value?
9. What provenance and negative cases make the operation reviewable?
10. Why is this better than asking the model to do the same calculation itself?

If these cannot be answered, the domain is not ready to enter the product core.

## 10. Product priority

The current priority order is:

```text
rc4 model-interface productization
        > current Statistics/Economics hardening
        > first convention-explicit Finance slice
        > units/dimensions/constants foundation
        > narrow Physics/Engineering slices
        > Chemistry/additional domains from measured demand
        > broad catalog growth
```

This order preserves ExactScope's moat: reviewed deterministic semantics + weak-model interface engineering + tiny deployment slices + reproducible qualification, rather than becoming a large formula repository.
