# ExactScope

> **Make tiny AI reason less.**
>
> Deterministic math, statistics, and economics scope packs for tiny, local, and edge AI systems.

**Status: design-only / pre-alpha. No implementation has been published yet.**

ExactScope is a proposed headless tool runtime for AI systems that are too small, too resource-constrained, or too latency-sensitive to reliably perform common quantitative reasoning on their own.

It is **not a calculator app for humans**, not a chatbot, and not a general reasoning engine.

The intended user is another AI runtime.

A wearable, embedded assistant, local 0.5B–3B model, or other edge agent should only need to recognize a task, extract a few values, and call ExactScope. Formula selection, validation, deterministic calculation, and classification are then handled outside the language model.

```text
camera / microphone / sensors
            |
            v
      tiny local model
   intent + value extraction
            |
            v
        ExactScope
   deterministic execution
            |
            v
   compact structured result
            |
            v
      tiny local model
```

## Why

Small language models can often understand a simple quantitative request while still making avoidable mistakes in one of the following steps:

- recalling the correct formula;
- selecting between similar methods;
- arithmetic;
- units and percentage conventions;
- boundary conditions;
- classifying the result;
- silently guessing when the problem is ambiguous.

ExactScope aims to remove as much of that reasoning surface as possible.

Instead of asking a small model to *know and execute* an undergraduate economics formula, the model should be able to do something closer to this:

```json
{"q":"price elasticity"}
```

ExactScope may return a compact operation descriptor:

```json
{"id":301,"sig":"ped_mid(p1,p2,q1,q2)"}
```

The model then supplies only the extracted values:

```json
{"id":301,"a":[10000,12000,100,80]}
```

And receives a deterministic result:

```json
{"s":0,"v":-1.222222,"c":2}
```

The language model did not need to remember the midpoint formula, perform the arithmetic, or decide whether the result is elastic or inelastic.

## Primary targets

ExactScope is designed first for constrained local systems, including:

- smart-glasses companion runtimes;
- wearable and embedded AI devices;
- offline assistants;
- ARM64 Android/Linux edge systems;
- Raspberry Pi-class devices;
- local 0.5B–3B language models;
- `llama.cpp`-style runtimes;
- WebAssembly hosts;
- native C/C++/Rust applications.

Large desktop agents and MCP clients may be supported through adapters, but they are not the primary design target.

## Design principles

### AI-only interface

No human-facing GUI, dashboard, account system, or conversational layer is required.

### Offline first

The core should require no network access, cloud service, API key, or remote database.

### Deterministic execution

Supported operations should produce reproducible results from validated inputs. LLM inference is not part of the calculation path.

### Tiny discovery surface

A constrained model should not need hundreds of verbose tool schemas in context at once. ExactScope should expose compact discovery and execution primitives and reveal only the operations relevant to the current request.

### Fail closed

If a method is ambiguous, an input is invalid, or required information is missing, ExactScope should return a typed failure instead of guessing.

### No arbitrary code in packs

Scope packs should prefer a constrained formula/operation representation plus metadata and golden test vectors rather than arbitrary executable plugins.

### Embedded-friendly core

The implementation target is a small native core suitable for `no_std`-oriented design where practical, with C ABI and WebAssembly builds considered first-class deployment paths.

## Scope packs

ExactScope is intended to separate the runtime from domain knowledge.

```text
ExactScope Core
|
+-- math-basic.scopepack
+-- statistics-core.scopepack
+-- econ-undergrad.scopepack
+-- finance-basic.scopepack
`-- future domain packs
```

A scope pack should contain machine-readable operation definitions such as:

- operation ID;
- compact signature;
- formula or deterministic procedure;
- input types;
- units;
- constraints;
- assumptions;
- supported methods;
- result classification rules;
- error conditions;
- golden test vectors;
- source/version metadata.

## First showcase pack: undergraduate economics

`econ-undergrad.scopepack` is planned as the first domain pack because it contains many common tasks that small models can often recognize but needlessly miscalculate.

Initial coverage may include:

### Microeconomics

- price elasticity of demand;
- midpoint/arc elasticity;
- income elasticity;
- cross-price elasticity;
- total and marginal revenue helpers;
- consumer and producer surplus;
- break-even calculations;
- basic cost measures;
- tax incidence helpers;
- deadweight-loss calculations where assumptions are explicit.

### Macroeconomics

- nominal and real GDP relationships;
- GDP deflator;
- CPI/inflation calculations;
- unemployment rate;
- labor-force participation;
- real versus nominal wage;
- money multiplier;
- Fisher relationship;
- basic quantity-equation calculations.

### International economics

- real exchange rate;
- terms of trade;
- opportunity cost;
- comparative-advantage helpers;
- purchasing-power-parity calculations where inputs and assumptions are explicit.

### Growth and basic finance

- growth rates;
- CAGR;
- Rule of 70;
- present/future value;
- compound interest;
- basic annuity calculations;
- real return.

Open-ended policy forecasting is intentionally out of scope. ExactScope should not pretend that questions such as "How much will unemployment rise if the minimum wage increases?" have a universal deterministic formula.

## Math and statistics scopes

Economics is only the first showcase. The broader target is a compact quantitative coprocessor for edge AI.

Planned common operations include:

**Math:** percentages, percentage change, ratios, weighted averages, powers, roots, logarithms, scientific notation, rounding, common equation forms, and other high-frequency deterministic operations.

**Statistics:** mean, median, variance, standard deviation, z-scores, percentiles, covariance, correlation, simple regression, standard error, confidence intervals, and common probability distributions.

## Proposed interfaces

The core should be library-first rather than server-first.

Planned integration layers:

```text
ExactScope Core
|
+-- Native C ABI
+-- WebAssembly
+-- compact local protocol / TinyWire
+-- llama.cpp adapter
+-- OpenAI-style tool-schema adapter
`-- MCP adapter (optional compatibility layer)
```

MCP is useful for desktop agent interoperability, but ExactScope should not require a full MCP stack on a wearable or embedded target.

## TinyWire concept

A compact machine protocol is planned for resource-constrained hosts.

Development/debug representation may use small JSON messages:

```json
{"id":301,"a":[10000,12000,100,80]}
```

More constrained environments may use a compact binary representation such as CBOR or a purpose-built framing format.

The goal is to keep routine requests small enough that tool invocation itself does not become the dominant context, memory, or bandwidth cost.

## Ambiguity is an error, not an invitation to hallucinate

If a user asks for "price elasticity" but the available information does not establish whether point elasticity or midpoint elasticity is intended, ExactScope should be able to return something like:

```json
{"s":4,"e":"AMBIG_METHOD","methods":[301,302]}
```

The calling model can then resolve the ambiguity from context or ask for missing information.

## Accuracy strategy

ExactScope's value is not the number of formulas it contains. The value is the amount of reasoning it can safely remove from a constrained model.

Each supported operation should eventually have extensive golden tests covering normal inputs, invalid inputs, boundaries, unit conventions, precision behavior, and classification thresholds.

Future benchmarks should compare tiny models **with and without ExactScope** on metrics such as:

- numeric-answer accuracy;
- formula/method selection accuracy;
- invalid-input detection;
- classification accuracy;
- tool-call token cost;
- latency;
- binary/runtime footprint.

Benchmark claims will only be published after they are measured.

## Related work and positioning

ExactScope is intentionally narrower than a general computer algebra system and more edge-oriented than typical LLM calculator servers.

Projects worth comparing include:

- [arithma](https://github.com/farchanjo/arithma) — a precise Rust MCP calculator engine with a broad catalog of math, statistics, finance, and engineering tools;
- [math-mcp](https://github.com/codeprimate/math-mcp) — symbolic/numerical mathematics exposed through a compact MCP tool interface;
- [needle-rs](https://github.com/geekgineer/needle-rs) — an extremely small local tool-calling model/runtime demonstrating that constrained function routing can run on tiny devices;
- [llm-tool](https://github.com/domenukk/llm-tool) — Rust tooling for strongly typed LLM tools with a `no_std`-compatible core.

ExactScope's intended niche is the intersection of these ideas:

> **a tiny, offline, deterministic quantitative tool runtime whose primary consumer is a constrained AI, with installable domain scope packs and an undergraduate-economics pack as the first showcase.**

## Non-goals

ExactScope is not intended to be:

- a human calculator application;
- a tutoring UI;
- a general-purpose chatbot;
- a replacement for SymPy, SciPy, Mathematica, R, or full numerical-computing stacks;
- an economics forecasting model;
- a source of live market or macroeconomic data;
- an excuse for an AI to hide ambiguity behind a confident answer.

## Initial roadmap

- [ ] Define the minimal operation and error model.
- [ ] Define the scope-pack manifest format.
- [ ] Prototype deterministic core evaluation.
- [ ] Establish C ABI and WebAssembly targets.
- [ ] Define compact discovery and execution protocol.
- [ ] Build `math-basic.scopepack`.
- [ ] Build `statistics-core.scopepack`.
- [ ] Build `econ-undergrad.scopepack`.
- [ ] Add llama.cpp/OpenAI-tool adapters.
- [ ] Add optional MCP adapter.
- [ ] Build golden-test corpus.
- [ ] Benchmark 0.5B–3B local models with and without ExactScope.

## Current state

This repository currently contains the project definition only. Architecture, protocol, implementation language details, pack format, and compatibility guarantees are not yet frozen.

The first implementation should optimize for **small AI systems first**, not retrofit embedded support after building a desktop-oriented server.

---

**ExactScope:** don't teach tiny AI to calculate what deterministic code can calculate exactly.
