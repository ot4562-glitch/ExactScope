# ExactScope retrofit product strategy

> **Design status: target direction. This document changes product and architecture priorities only. It does not claim that the vNext interfaces described here are implemented.**

## 1. Product thesis

ExactScope is a **tiny deterministic quantitative coprocessor for small and on-device AI**.

Its primary product value is more specific:

> **Upgrade constrained on-device AI through software instead of requiring a hardware upgrade for every quantitative capability gap.**

Many deployed AI devices have hard limits on model size and inference cost: memory capacity, memory bandwidth, accelerator capability, storage, thermal budget, battery budget, latency, and product qualification constraints. Better models, quantization, distillation, prompting, routing, and orchestration can improve an existing device, but eventually some capability gaps remain expensive to solve by making the model larger.

ExactScope targets that gap.

It does not try to make the model generally more intelligent. It removes a narrow class of work that is a poor use of scarce model capacity: bounded deterministic quantitative execution.

```text
existing device
  + existing small/local model
  + tiny ExactScope component delivered in software
  = stronger quantitative capability without replacing the device
```

This is a **capability retrofit** strategy, not a calculator-app strategy.

## 2. The customer problem

The important customer is not only a developer building a new model stack. It is also an OEM or product team with devices already designed, qualified, shipped, or physically constrained.

When the on-device model is weak on a deterministic quantitative task, the usual options include:

1. ship a larger/newer model if the hardware can support it;
2. wait for a better compressed model;
3. send the task to a cloud service;
4. improve prompts, routing, context, or tool use;
5. defer the capability to the next hardware generation.

ExactScope adds another option:

6. **retrofit the existing AI stack with a very small deterministic coprocessor.**

The product hypothesis is therefore not merely "external calculation can help an LLM." The hypothesis is:

> **For constrained on-device models, can a tiny bounded coprocessor remove enough quantitative error at sufficiently low binary, RAM, token, latency, energy, integration, and qualification cost that the existing hardware remains useful for capabilities that would otherwise push toward a larger model or newer device?**

That is the proposition every major benchmark and release decision must test.

## 3. What ExactScope is not

ExactScope is not:

- a calculator UI;
- a general Python replacement;
- a symbolic algebra system;
- an MCP server as the core product;
- an AI model;
- a model fine-tuning framework;
- a cloud calculation service;
- a general code interpreter;
- a claim that all hardware upgrades can be avoided.

Some AI limitations are recognition, world knowledge, planning, perception, language understanding, memory, or model-capacity problems. ExactScope must not pretend to solve them.

Its authority is deliberately narrow: **validated deterministic quantitative execution after the model or host has selected/extracted the required quantities and semantics.**

## 4. Target insertion point

The desired OEM integration is intentionally small.

```text
sensor / user input
        |
        v
small on-device model
        |
        | structured quantitative request
        v
ExactScope
        |
        | exact result or explicit failure
        v
small on-device model / host renderer
        |
        v
user response / product action
```

ExactScope must not require a replacement model, fine-tuning step, daemon, network connection, account, Python runtime, or target-side package manager.

The ideal retrofit is approximately:

```text
OTA/software update
  -> add ExactScope artifact
  -> add generated schema/grammar or typed binding
  -> run self-test
  -> route supported deterministic work through ExactScope
```

## 5. vNext interaction architecture

The target architecture has two first-class execution lanes.

```text
                           small/local model
                                  |
                  +---------------+---------------+
                  |                               |
                  v                               v
        generic bounded arithmetic        known semantic operation
                  |                               |
                  v                               v
          xs_calc(bounded plan)              xs_eval(op,args)
                  |                               |
                  +---------------+---------------+
                                  |
                                  v
                     ExactScope deterministic core
                                  |
                                  v
                      exact result / typed failure
```

### 5.1 `xs_calc` — target generic quantitative lane

**Status: planned, not implemented.**

`xs_calc` is the model-facing path for short arithmetic programs that do not require a large catalog of named domain operations.

The initial plan vocabulary is intentionally small:

- `add`
- `sub`
- `mul`
- `div`
- `powi`
- `sqrt`

The model emits one bounded plan rather than making a sequence of independent tool calls.

Conceptual example:

```json
{
  "p": [
    {"o":"mul","a":["12","7"]},
    {"o":"sub","a":["#0","4"]},
    {"o":"div","a":["#1","5"]}
  ]
}
```

Previous-result references are explicit and backward-only. The last step is the result.

### 5.2 `xs_eval` — retained semantic fast path

`xs_eval` remains valuable and implemented for reviewed semantic operations such as:

- statistics methods;
- economics methods;
- later finance/physics/chemistry/engineering operations;
- operations where method identity, units, conventions, or domain constraints matter.

Example:

```json
{"op":"stats.var.sample","a":[["1","2","3","4"]]}
```

The product should not force a generic plan when a reviewed semantic operation is safer and more compact.

### 5.3 `xs_find` — cold/development path

`xs_find` remains available, but it is no longer a primary product path for tiny models.

It is appropriate for:

- developer tooling;
- unknown operation exploration;
- cold binding/setup;
- larger host-side routing systems.

It should not be required for common on-device quantitative requests.

## 6. Bounded plan contract

The first plan format should be deliberately boring and small.

Initial target bounds:

| Property | Target |
|---|---|
| maximum arithmetic steps | 8 |
| operations | add, sub, mul, div, powi, sqrt |
| result references | previous steps only |
| numeric leaves | canonical exact decimal strings |
| loops | forbidden |
| branches | forbidden in P0 plan surface |
| variables | forbidden |
| arbitrary expressions | forbidden |
| arbitrary functions | forbidden |
| arbitrary code | forbidden |
| filesystem/network/process access | impossible |
| semantic repair | forbidden |
| invalid/domain/overflow behavior | fail closed |

The 8-step target is evidence-driven. In the locally pinned public benchmark data examined during product planning, FinQA test programs were at most 5 operations and TAT-QA arithmetic derivations at most 7 arithmetic operations under the conservative parser used for planning. These observations are planning evidence only; final coverage claims require reproducible gold converters and validation.

## 7. Reuse the existing deterministic engine

The target plan path must not create a second arithmetic implementation.

ExactScope already has a bounded non-Turing-complete scalar VM with checked arithmetic opcodes including add, sub, mul, div, integer power, and deterministic square root.

The intended implementation architecture is:

```text
model plan
   -> bounded plan parser/validator
   -> canonical lowering
   -> existing ExactScope VM / numeric kernel
   -> canonical result/status
```

The plan layer is therefore a restricted model-facing program representation, not a new general-purpose language.

## 8. Footprint is a product KPI

Accuracy alone is insufficient. ExactScope only wins the retrofit position if the added software is materially cheaper than replacing the model/hardware path it is intended to avoid.

During current development, local prerelease artifacts have been observed at approximately:

- no-import Wasm: 97,851 bytes;
- Windows benchmark core executable: 180,736 bytes.

These are development measurements, not universal release-size guarantees.

vNext should introduce explicit footprint gates:

- **target:** keep the primary no-import Wasm artifact near or below 128 KiB when practical;
- **warning:** growth beyond 192 KiB requires a recorded explanation;
- **hard design review:** growth beyond 256 KiB requires evidence that the product value justifies the footprint change;
- native static artifacts must also publish before/after text/data/total size where tooling permits;
- resident RAM and scratch must be reported independently from binary size.

A feature that materially improves breadth but destroys the tiny retrofit profile is not automatically a product improvement.

## 9. Primary benchmark proposition

The flagship experiment should no longer be framed merely as "model arithmetic vs calculator."

It should answer:

> **How far can an existing 0.5B-3B on-device model be strengthened by adding ExactScope, and how does that compare with moving to a larger model when larger-model deployment is feasible?**

Required numerical-reasoning arms for the vNext product proof:

| Arm | Meaning |
|---|---|
| A | model only |
| B | model -> unconstrained `xs_calc` plan -> ExactScope |
| C | model -> constrained `xs_calc` plan -> ExactScope |
| D | gold plan -> ExactScope deterministic ceiling |

Semantic-operation benchmarks retain direct `xs_eval` comparisons where appropriate.

The benchmark must report more than final accuracy:

- task recognition;
- plan/operation selection;
- argument extraction;
- plan syntax validity;
- plan semantic validity;
- core accept/reject;
- final answer accuracy;
- incorrect numeric answer rate;
- tool penalty rate: model-only correct but ExactScope path incorrect;
- result fidelity;
- failure fidelity;
- turns/tokens;
- model latency;
- ExactScope latency;
- artifact/RAM/scratch cost;
- energy where measurable.

## 10. Product proof gates

The first public proof should be considered convincing only if all of the following are true:

1. gold-program/deterministic-ceiling converters are validated independently of model outputs;
2. at least three constrained model classes in the 0.5B-3B range are tested;
3. the supported public subset is selected from gold metadata/programs, never model answers;
4. constrained `xs_calc` improves the supported-subset result materially over model-only reasoning;
5. wrong-number rate is materially reduced, not merely converted into silent failures;
6. model-only-correct/tool-wrong regressions are measured explicitly;
7. added binary/RAM/scratch cost remains in the tiny-device envelope;
8. latency/tokens/turns are recorded;
9. at least one real constrained target is measured before hardware-life-extension claims are marketed as proven;
10. every published result identifies exact model/runtime/dataset/ExactScope artifact digests.

A useful internal go/no-go target for the first public slice is:

- at least +10 percentage points on a supported public subset for multiple constrained models, or another clearly material quality improvement justified by the task;
- at least 30% relative reduction in incorrect numeric answers;
- no hidden semantic repair;
- acceptable tool penalty and rejection rates.

These are design gates, not current measured public claims.

## 11. Domain-series strategy

After the core retrofit mechanism is proven, ExactScope may ship as one core with optional reviewed capability series.

```text
ExactScope Core
  + Math
  + Statistics
  + Economics
  + Finance
  + Physics
  + Chemistry
  + Engineering
  + later reviewed OEM/domain packs
```

This is **not** a family of separate runtimes. All series must reuse the same deterministic core and stable ABI/wire semantics.

A domain series may add:

- reviewed semantic operation definitions;
- explicit units/method contracts;
- domain constraints;
- provenance;
- golden/negative/boundary vectors;
- benchmark mappings;
- compatibility/qualification records.

The order is evidence-driven. The current priority remains completing the core bounded-plan product proof before broad domain expansion.

## 12. OEM adoption wedge

The ideal OEM conversation is not:

> "Would you like another calculator library?"

It is:

> "Can you keep the model and hardware you already ship, add a tiny audited component, and remove a measurable class of quantitative failures through software?"

The adoption path should therefore optimize for:

```text
public reproducible proof
  -> prebuilt tiny artifact
  -> 5-minute desktop evaluation
  -> customer model benchmark
  -> target integration
  -> OTA/update-safe integration
  -> qualification/LTS/support where required
```

Retrofit compatibility, update safety, and artifact stability are first-class commercial concerns.

## 13. Competitive frame

ExactScope should not claim to invent external calculation for language models.

Its differentiation is the systems combination:

- designed for constrained on-device/local models rather than server-first agents;
- tiny resident footprint;
- bounded non-Turing-complete execution;
- one compact plan rather than a large generic tool catalog for ordinary arithmetic;
- exact decimal/rational semantics;
- fail-closed validation;
- no Python or scientific runtime requirement;
- no daemon/account/network dependency;
- native static C ABI;
- no-import Wasm;
- reviewed semantic domain packs;
- reproducible conformance and target qualification;
- retrofit/OTA suitability as a primary design objective.

## 14. Messaging hierarchy

Technical definition:

> **A tiny deterministic quantitative coprocessor for small and on-device AI.**

Customer value:

> **Upgrade on-device AI without upgrading the hardware.**

Product strategy:

> **Extend the useful capability of deployed AI devices through a tiny software retrofit.**

Short developer message:

> **Keep your small model. Give it exact quantitative execution.**

These are positioning statements and hypotheses until backed by the benchmark/target evidence required above.

## 15. Decision rule

Before adding any feature, ask in this order:

1. Does it help an existing constrained model do something useful without requiring a hardware/model-size jump?
2. Does it preserve or improve the tiny footprint?
3. Is execution bounded, deterministic, auditable, and fail-closed?
4. Can it be delivered through a simple library/Wasm integration rather than a service/runtime stack?
5. Can its value be measured on public or customer-reproducible workloads?
6. Does it reuse the shared core rather than create a semantic fork?

If the answer to the first three is no, the feature is probably outside the core product.
