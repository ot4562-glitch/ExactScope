# ExactScope

> ExactScope is a tiny deterministic quantitative coprocessor for small and on-device AI.

**Status: `v1.0.0-rc.1` release candidate for developer evaluation. This is not a stable release, hardware qualification, or production certification.**

ExactScope takes one bounded arithmetic plan or one reviewed semantic operation and returns a deterministic exact-decimal result. It is a local library, not a model, chatbot, hosted API, daemon, database, or general expression evaluator.

```text
small / on-device AI
    -> one bounded constrained arithmetic plan
    -> ExactScope xs_calc
    -> deterministic exact result

model
    -> reviewed xs_eval operation
    -> ExactScope
    -> deterministic domain result
```

## 30-second example

Send one Tiny JSON `xs_calc` plan through the native benchmark bridge or no-import Wasm adapter:

```json
{"p":[{"o":"mul","a":["12","7"]},{"o":"sub","a":["#0","4"]},{"o":"div","a":["#1","5"]}]}
```

ExactScope preserves exact rational intermediates and returns:

```json
{"s":0,"v":"16","f":0,"p":"plan-v0.1","r":1}
```

A failed step returns a typed error and no numeric value:

```json
{"s":13,"e":"DIVIDE_BY_ZERO","step":0}
```

## 5-minute local test

With the pinned Rust toolchain, Node.js, and Python 3 available:

```powershell
cargo test --workspace
cargo build --release -p exactscope-wasm --target wasm32v1-none --no-default-features --features fused,tinyjson
python tools/inspect_wasm.py target/wasm32v1-none/release/exactscope_wasm.wasm
node examples/javascript/wasm-xs-calc.mjs target/wasm32v1-none/release/exactscope_wasm.wasm
```

Expected final output:

```json
{"s":0,"v":"16","f":0,"p":"plan-v0.1","r":1}
```

Release assets provide prebuilt evaluation archives with a manifest and `SHA256SUMS`; when using one, download it, verify it with `tools/package_evaluation_bundle.py verify`, then follow its bundled quickstart. The source build above remains the authoritative fallback.

## Two public execution paths

### `xs_calc`: bounded generic arithmetic

Plan v0.1 is deliberately small:

- 1 to 8 steps and at most 2 arguments per step;
- `add`, `sub`, `mul`, `div`, `powi`, and `sqrt`;
- `powi` exponent from -32 through 32;
- backward-only result references `#0` through `#7`;
- 512-byte Tiny JSON request limit;
- exact decimal/rational intermediates where possible;
- deterministic half-even quantization at the highest representable scale from 18 down to 0;
- fail-closed parsing and execution with no semantic repair.

The contract, JSON Schema, llama.cpp grammar, and prompt assets are in [spec/PLAN_V0_1.md](spec/PLAN_V0_1.md), [spec/schemas/xs-calc-tool.schema.json](spec/schemas/xs-calc-tool.schema.json), and [adapters/xs-calc-v0.1](adapters/xs-calc-v0.1).

### `xs_eval`: reviewed semantic operations

`xs_eval` evaluates installed operations whose method, units, constraints, rounding, and output meaning have been reviewed. Current fused packs cover economics and bounded statistics operations. `xs_find` remains an optional cold/development discovery path; it is not required for each calculation.

Example:

```json
{"op":"econ.inflation.cpi_pct","a":["100","103.2"]}
```

## Native static C ABI

The public header is [include/exactscope.h](include/exactscope.h). The typed plan ABI has fixed layouts checked in Rust, C11, and C++11:

```text
xs_decimal_v1       16 bytes
xs_plan_value_v1    32 bytes
xs_plan_step_v1     80 bytes
xs_plan_result_v1   48 bytes
```

[examples/c/xs_calc.c](examples/c/xs_calc.c) initializes a caller-owned context and evaluates `12 * 7`, `#0 - 4`, `#1 / 5` to `16`. There is no target-side Rust runtime, service, network, database, or heap requirement in the deterministic core path.

## No-import WebAssembly

The `wasm32v1-none` profile exposes `xs_wire_request`. [examples/javascript/wasm-xs-calc.mjs](examples/javascript/wasm-xs-calc.mjs) shows the complete dependency-free host flow: instantiate, write the request, call `xs_wire_request`, and read the response.

The current clean local release build with `xs_calc` is 102,971 bytes, has zero imports, and declares 17 initial memory pages. The release gate is less than 128 KiB and zero imports. Artifact measurements can vary when toolchain or source changes, so release notes and manifests must record the released artifact's own bytes and SHA-256.

## Model integration

Use grammar-constrained generation for plan structure, then let ExactScope validate semantics and execute. [examples/llama.cpp](examples/llama.cpp) contains the reference runner. A structurally valid but mathematically wrong model plan is a planning failure; the host and ExactScope do not repair it.

The reference evaluation reports valid plan rate, runtime accepted plan rate, correct final answer rate, wrong numeric answer rate, generated tokens, plan steps, and latency.

## Current evidence

- Workspace tests cover kernel, Tiny JSON, typed C ABI, pack, conformance, and Wasm layers.
- C11/C++11 syntax checks assert plan structure sizes, operation/value constants, and the `xs_calc` declaration.
- A clean local `wasm32v1-none` release build measured 102,971 bytes, imports 0, memory 17 pages, SHA-256 `8ea9729a73485041bf77d6f673eb25bd4b0219b9af27986a4cc5a9548a42ea94`.
- The FinQA test oracle/structural analysis found 1,061 bounded programs expressible by plan v0.1; 1,058 were runtime-accepted, and 275 exactly matched the dataset's explicit answer. This is a compatible oracle subset, not a model accuracy score. Many mismatches reflect FinQA answer transformations such as implicit percentage scaling or dataset rounding that raw generic arithmetic intentionally does not guess.
- The TAT-QA dev oracle/structural analysis found 717 bounded arithmetic derivations; all 717 were runtime-accepted and 443 exactly matched the explicit answer. This is also a compatible oracle subset, not a model accuracy score; percent scaling and dataset rounding are not inferred.
- A five-case llama.cpp b10797 integration smoke produced correct-final/wrong-numeric rates of 60%/20% for Qwen3 0.6B Q8_0, 100%/0% for Qwen3 1.7B Q8_0, and 60%/0% for Llama 3.2 3B Instruct Q4_K_M. Rejected plans emitted no numeric answer. The checked-in per-item results are not a general model benchmark score.
- An internal support-aligned 23-case corpus previously measured 50.93% correctness for a constrained GBNF path versus 4.97% model-only, with incorrect numeric answers reduced from 71.43% to 27.33%. This is architecture evidence only, not a general public benchmark claim.
- A normalized 100-item GSM8K pilot exists as baseline context only; it is not an official GSM8K score and is not labeled an `xs_calc` benchmark.

## Current limitations

- This RC has not been hardware-qualified or production-certified.
- Real-device latency, RAM, energy, update/rollback, and platform compatibility evidence is still wanted.
- Model planning quality varies; deterministic execution cannot make a wrong plan correct.
- Plan v0.1 has no loops, branches, named variables, arbitrary functions, unit inference, percentage inference, or semantic repair.
- `sqrt` of irrational values and non-terminating final rationals require bounded deterministic quantization.
- Dynamic packs and discovery are secondary evaluation paths; the core public lanes are `xs_calc` and direct `xs_eval`.
- Only release artifacts actually published in the GitHub pre-release are supported claims. An absent platform archive is not implied by the source tree.

## Validation wanted

Trying ExactScope on an edge/on-device AI stack? Open an integration feedback issue and include your platform, CPU/SoC, RAM, model, runtime, ExactScope profile, artifact SHA-256, integration method, latency, and any issues.

Useful external results include build/runtime outcomes, model integration behavior, latency measurements, platform compatibility reports, bugs, API feedback, and concrete use cases. GitHub stars are not validation evidence.

## Architecture and guarantees

```text
Layer 1: bounded deterministic arithmetic plan       xs_calc
Layer 2: reviewed semantic quantitative operations  xs_eval
Layer 3: optional domain packs
Cold/development fallback                            xs_find
```

The implementation keeps `no_std` where intended, caller-owned bounded storage at public boundaries, checked arithmetic, deterministic rounding, no mandatory network/account/daemon/database, and no arbitrary native code in data packs. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/AI_INTEGRATION.md](docs/AI_INTEGRATION.md), [docs/BENCHMARK.md](docs/BENCHMARK.md), and [SECURITY.md](SECURITY.md).

## Contributing and license

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and evidence requirements. ExactScope is dual-licensed under the existing [MIT](LICENSE-MIT) or [Apache-2.0](LICENSE-APACHE) terms; this release candidate does not change that licensing model. Dependency and evaluation attribution is recorded in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
