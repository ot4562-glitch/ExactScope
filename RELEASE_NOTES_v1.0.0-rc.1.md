# ExactScope v1.0.0-rc.1

This release candidate is published for developer evaluation and integration feedback. It is not hardware qualification or production certification.

## What `xs_calc` is

`xs_calc` executes one bounded arithmetic plan selected by a model or host. The 1-8 step bound gives small models one compact constrained output while keeping runtime, memory, and failure behavior reviewable. ExactScope validates and executes the selected plan; it never repairs its meaning.

Plan v0.1 supports `add`, `sub`, `mul`, `div`, `powi`, and `sqrt`, at most two arguments per step, backward-only `#0` through `#7` references, `powi` exponents from -32 through 32, and a 512-byte Tiny JSON envelope. Exact rational intermediates are preserved where possible. Non-terminating final decimals and irrational square roots use bounded deterministic half-even quantization, retaining rounded/inexact flags.

## Native and Wasm paths

- The typed native C ABI exposes `xs_calc` using fixed-size, caller-owned structures. The public C example evaluates `(12 * 7 - 4) / 5` to `16`.
- The no-import `wasm32v1-none` build exposes the same Tiny JSON request through `xs_wire_request`. The dependency-free Node example shows instantiate/write/call/read end to end.
- The clean local candidate build measured 102,971 bytes, imports 0, 17 initial memory pages, and SHA-256 `8ea9729a73485041bf77d6f673eb25bd4b0219b9af27986a4cc5a9548a42ea94`. Published asset metadata records the released build's own measurement.

## Reviewed semantic operations

`xs_eval` remains the direct reviewed semantic lane. Current fused domain packs contain economics and bounded statistics operations. `xs_find` remains an optional cold/development discovery path and is not required for every calculation.

## Evidence classification

- FinQA test oracle/structural subset: 1,061 bounded supported programs, 1,058 runtime accepted, 275 exact matches to explicit dataset answers.
- TAT-QA dev oracle/structural subset: 717 bounded supported arithmetic derivations, 717 runtime accepted, 443 exact matches to explicit dataset answers.
- Five-case llama.cpp b10797 integration smoke: Qwen3 0.6B Q8_0 correct 60% / wrong numeric 20%; Qwen3 1.7B Q8_0 correct 100% / wrong numeric 0%; Llama 3.2 3B Instruct Q4_K_M correct 60% / wrong numeric 0%.
- The existing 23-case support-aligned corpus is internal architecture evidence, not a general benchmark claim. The existing normalized 100-item GSM8K run is a pilot baseline, not an official GSM8K score or an `xs_calc` benchmark.

## Known limitations

- Model planning can be wrong or rejected. Deterministic execution does not imply correct plan selection.
- Plan v0.1 does not infer percentage/unit transformations or dataset-specific rounding, and has no loops, branches, named variables, arbitrary functions, or semantic repair.
- Real-device latency, memory, energy, update/rollback, and platform qualification remain external validation work.
- Dynamic packs and discovery are secondary evaluation paths.
- Only platform archives attached to this pre-release exist as release artifacts; unsupported artifacts are not implied.

## Integration feedback

Trying ExactScope on an edge/on-device AI stack? Open an integration feedback issue and include the host platform, CPU/SoC, RAM, model, runtime, ExactScope profile, artifact SHA-256, integration method, working/not-working outcome, latency, and issues.
