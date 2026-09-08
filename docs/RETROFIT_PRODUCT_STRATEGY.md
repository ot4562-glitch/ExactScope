# ExactScope retrofit product strategy

> **Current status:** v1.0.0-rc.3 external-user qualification is complete and frozen. It confirmed the package/core path but showed that model-visible tool protocols and prompt cost are first-order constraints. Active rc4 design therefore pivots the flagship product to provider-neutral everyday grounding: original-question prefetch, compact Grounding Frames, explicit authority modes, and one-call small-model answering. Representative physical ARM64 RAM/latency/energy/thermal qualification remains NOT MEASURED.
>
> See [`GROUNDING_ARCHITECTURE.md`](GROUNDING_ARCHITECTURE.md) and [`../spec/GROUNDING_CONTRACT_V0_1.md`](../spec/GROUNDING_CONTRACT_V0_1.md) for the active flagship architecture. [`CAPABILITY_PRODUCT_ARCHITECTURE.md`](CAPABILITY_PRODUCT_ARCHITECTURE.md) and [`MODEL_INTERFACE_RC4.md`](MODEL_INTERFACE_RC4.md) remain quantitative-subsystem references; [`RC3_QUALIFICATION_CLOSEOUT.md`](RC3_QUALIFICATION_CLOSEOUT.md) records completed rc3 evidence.

## 1. Product thesis

ExactScope is a **tiny grounding and deterministic capability layer for small and on-device AI**.

Its primary product value is:

> **Upgrade an existing small model's everyday factual reliability through software instead of requiring a larger model, larger context, heavyweight remote RAG stack, or immediate hardware replacement.**

Many deployed AI devices have hard limits on model size and inference cost: memory capacity, memory bandwidth, accelerator capability, storage, thermal budget, battery budget, latency, and qualification constraints. Better models, quantization, distillation and prompting help, but small models still forget, confuse, stale, or invent facts that a compact local evidence layer can provide more cheaply.

ExactScope targets that gap first. It does not claim to make model weights generally more intelligent. It moves factual grounding outside the weights and, where appropriate, keeps deterministic calculation outside model reasoning as a secondary capability.

```text
existing device
  + existing small/local model
  + tiny provider-neutral grounding layer
  + optional deterministic calculation layer
  = better everyday factual reliability without replacing the device
```

This is a **capability retrofit** strategy, not a calculator-app or giant RAG-framework strategy. A developer or OEM engineer integrates ExactScope into the product; a human end user should experience more reliable answers without explicitly invoking an "ExactScope tool."

## 2. The customer problem

The important customer is not only a developer building a new model stack. It is also an OEM or product team with devices already designed, qualified, shipped, or physically constrained.

When the on-device model is weak on ordinary factual questions, the usual options include:

1. ship a larger/newer model if the hardware can support it;
2. increase context or bundle large documents into prompts;
3. add a heavyweight vector/RAG stack;
4. send the question to a cloud/search service;
5. improve prompts, tool routing or fine-tuning;
6. defer the capability to the next hardware generation.

ExactScope adds another option:

7. **retrofit the existing AI stack with a small provider-neutral grounding layer that supplies only the evidence needed for the current question.**

The product hypothesis is therefore not merely "RAG can help an LLM" or "external calculation can help an LLM." The hypothesis is:

> **For constrained on-device models, can compact high-precision grounding materially raise everyday factual accuracy and reduce wrong-confident answers at sufficiently low storage, RAM, token, latency, energy, integration and qualification cost that the existing hardware remains useful?**

That is the proposition every major benchmark and release decision must test. Quantitative capability is a secondary value layer inside the same retrofit thesis.

## 3. What ExactScope is not

ExactScope is not:

- a chatbot UI;
- a universal web search engine;
- a full enterprise RAG/orchestration platform;
- a model training/fine-tuning framework;
- a truth oracle for arbitrary conflicting internet claims;
- a calculator UI, general Python replacement or symbolic algebra system;
- an MCP server as the core product;
- a mandatory cloud service;
- a general code interpreter;
- a claim that all hallucinations or hardware upgrades can be avoided.

Some AI limitations are perception, deep planning, language understanding, generation quality or raw model capacity. ExactScope does not pretend to solve them.

Its flagship authority is deliberately narrower: **bind a user question to a small, scoped, provenance/revision-aware evidence frame under explicit source authority rules.** The quantitative subsystem separately provides validated deterministic execution where calculation is the actual failure mode.

## 4. Target insertion point

The desired OEM integration is intentionally small and normally runs **before** the model answer call.

```text
sensor / user input
        |
        v
Grounding Router
        |
        v
configured source/provider set
        |
        v
Evidence Policy
        |
        | compact Grounding Frame
        v
small on-device model -- one answer call
        |
        v
user response / product action
```

If the request also needs deterministic arithmetic or a reviewed quantitative method, the host may invoke `xs_calc`/`xs_eval` as a separate bounded lane. Ordinary factual questions should not be forced through that path.

ExactScope must not require a replacement model, fine-tuning step, daemon, network connection, account, Python runtime, or target-side package manager.

The ideal retrofit is approximately:

```text
OTA/software update
  -> add ExactScope artifact
  -> add generated schema/grammar or typed binding
  -> run self-test
  -> route supported deterministic work through ExactScope
```

## 5. Current interaction architecture

The current architecture has two first-class execution lanes.

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

### 5.1 `xs_calc` — implemented experimental generic quantitative lane

**Status: implemented experimentally as plan-v0.1; not yet a stable v1 compatibility promise.**

`xs_calc` is the model-facing path for short arithmetic programs that do not require a large catalog of named domain operations.

The initial plan vocabulary is intentionally small:

- `add`
- `sub`
- `mul`
- `div`
- `powi`
- `sqrt`

The model emits one bounded plan rather than making a sequence of independent tool calls.

Example:

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

Plan v0.1 is deliberately boring and small.

Current experimental bounds:

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

Pre-rc3 development builds produced multiple local footprint measurements, but those values are tied to their exact source/toolchain/artifact identities. The rc3 clean source therefore does not present an old development byte count as the current product size.

Measure the exact public rc3 archive/runtime bytes and SHA-256 during qualification and bind every footprint comparison to that released artifact.

The capability product should keep explicit footprint gates:

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

Required numerical-reasoning arms for the capability product proof:

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

## 11. Domain-series and capability-slice strategy

ExactScope should maintain broad reviewed **domain source catalogs**, but deploy only the smallest **capability slice** required by the target AI product.

```text
ExactScope shared core
  + Statistics source catalog
  + Economics source catalog
  + Finance source catalog
  + Physics / Engineering / later sources
             |
             v
    compile/select target slice
             |
             +--> statistics-8
             +--> statistics-16
             +--> custom device/model profile
```

This is **not** a family of separate runtimes and not a collection of human calculators. All series reuse the same deterministic core and stable ABI/wire semantics.

A domain source may add:

- reviewed semantic operation definitions;
- explicit units/method contracts;
- domain constraints;
- provenance and revision history;
- golden/negative/boundary vectors;
- benchmark mappings;
- compatibility/qualification records.

A deployed capability slice additionally records its model-visible operation set, prompt/schema/grammar identity, target task families, footprint budget, model-difficulty budget, and benchmark identity.

The product metric is not operation count. It is whether the slice gives the target weak model a useful new task-family capability at very low binary/RAM/token/latency/energy cost.

Statistics is the recommended first flagship domain proof because the runtime already contains bounded statistics kernels and because method identity creates real value beyond generic arithmetic.

## 12. OEM adoption wedge and build-vs-buy thesis

The ideal OEM conversation is not:

> "Would you like another calculator library?"

It is:

> "Can you keep the model and hardware you already ship, add a tiny audited capability slice, and recover a measurable part of the capability you would otherwise need a larger model or newer device to obtain?"

A large vendor can implement individual formulas. ExactScope therefore earns adoption only if it removes a larger recurring engineering burden:

- weak-model interface design;
- constrained-decoding assets;
- deterministic exact semantics;
- domain review/provenance;
- footprint optimization;
- conformance/malformed-input testing;
- model benchmark maintenance;
- artifact identity and update/rollback discipline;
- target qualification and long-term revision support.

The adoption path should optimize for:

```text
public reproducible capability proof
  -> prebuilt tiny artifact
  -> 5-minute developer evaluation
  -> customer weak-model benchmark
  -> select/compile smallest useful capability slice
  -> target integration
  -> OTA/update-safe integration
  -> qualification/LTS/support where required
```

Retrofit compatibility, weak-model usability, update safety, artifact stability, and accumulated qualification evidence are first-class commercial concerns.

## 13. Competitive frame

ExactScope should not claim to invent external calculation for language models.

Its differentiation is the systems combination:

- designed for constrained on-device/local models rather than server-first agents;
- tiny resident footprint;
- bounded non-Turing-complete execution;
- one compact plan rather than a large generic tool catalog for ordinary arithmetic;
- small compiled semantic capability slices rather than full-domain prompt exposure;
- explicit model-difficulty budgets for weak-model usability;
- exact decimal/rational semantics;
- fail-closed validation;
- no Python or scientific runtime requirement;
- no daemon/account/network dependency;
- native static C ABI;
- no-import Wasm;
- reviewed domain source catalogs with provenance/revision history;
- reproducible conformance, benchmark, and target qualification;
- capability-density and larger-model-gap recovery measurement;
- retrofit/OTA suitability as a primary design objective.

## 14. Messaging hierarchy

Technical definition:

> **A tiny deterministic AI-facing capability coprocessor for small and on-device AI.**

Customer value:

> **Add narrow professional quantitative capability to the model you can already deploy.**

Product strategy:

> **Recover useful domain capability through a tiny software retrofit before paying for a larger model or new hardware.**

Short developer message:

> **Keep your small model. Add the capability slice it is missing.**

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
