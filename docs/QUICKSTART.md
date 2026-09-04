# ExactScope 5-minute quickstart

ExactScope is a tiny deterministic quantitative coprocessor for small and on-device AI. This `v1.0.0-rc.1` path lets a developer evaluate bounded generic arithmetic without first understanding the Rust implementation.

## Fastest source evaluation

Requirements: the repository's pinned Rust toolchain, Python 3, and Node.js.

```powershell
cargo test --workspace
cargo build --release -p exactscope-wasm --target wasm32v1-none --no-default-features --features fused,tinyjson
python tools/inspect_wasm.py target/wasm32v1-none/release/exactscope_wasm.wasm
node examples/javascript/wasm-xs-calc.mjs target/wasm32v1-none/release/exactscope_wasm.wasm
```

The last command instantiates Wasm with `{}`, writes this request into exported memory, calls `xs_wire_request`, reads the response, and checks it:

```json
{"p":[{"o":"mul","a":["12","7"]},{"o":"sub","a":["#0","4"]},{"o":"div","a":["#1","5"]}]}
```

Expected output:

```json
{"s":0,"v":"16","f":0,"p":"plan-v0.1","r":1}
```

## Prebuilt release evaluation

Download the archive matching an actually published platform from the GitHub `v1.0.0-rc.1` pre-release. Do not infer support for an absent archive.

1. Verify the archive against the release `SHA256SUMS`.
2. Extract it and inspect `manifest.json` plus its internal `SHA256SUMS`.
3. Run the bundled native or Wasm smoke path in [EVALUATION_BUNDLE.md](EVALUATION_BUNDLE.md).

The bundle includes a target-native static library, `exactscope-core`, no-import Wasm, headers/CMake metadata, examples, model-facing assets, licenses, manifest, and hashes. Rust is not required to evaluate a prebuilt bundle.

## Native C ABI

The public example in `examples/c/xs_calc.c` initializes caller-owned storage and calls the typed `xs_calc` ABI. With a Unix-style release library:

```text
cc -std=c11 -Wall -Wextra -Werror -pedantic \
  -Iinclude examples/c/xs_calc.c \
  lib/<target>/libexactscope_cabi.a \
  -o xs-calc
./xs-calc
```

Expected output is `16`. Windows SDK consumers link `exactscope_cabi.lib`. The fixed plan structure sizes and constants are compiled as C11 and C++11 CI contracts.

## Model integration

The intended hot path is:

```text
generic arithmetic -> constrained xs_calc plan -> ExactScope
reviewed method     -> direct xs_eval call      -> ExactScope
unknown method      -> optional xs_find cold path
```

Use `adapters/xs-calc-v0.1/xs-calc.gbnf` with llama.cpp and run `examples/llama.cpp/run_xs_calc.py`. Grammar validity does not imply a mathematically correct plan. ExactScope enforces backward references, bounds, arity, decimal validity, domain rules, and checked arithmetic, but it does not semantically repair a model plan.

For a reproducible local matrix, `examples/llama.cpp/benchmark_xs_calc.py` reports valid-plan, runtime-accepted, correct-final, wrong-numeric, generated-token, step, and latency metrics with per-item records.

## Semantic operations

Use `xs_eval` when the quantitative method itself matters, such as a reviewed economics or statistics operation:

```json
{"op":"econ.inflation.cpi_pct","a":["100","103.2"]}
```

The host should bind/cache reviewed operation identity and call `xs_eval` directly. `xs_find` is a development or cold discovery path, not a required extra hop for every calculation.

## Fail closed

Adapters may normalize transport syntax, field order, and whitespace. They must not guess missing operands, units, percentages, currencies, rounding contracts, or methods. Failures contain a typed status and never a fabricated numeric `v`.

Before adoption, measure final correctness, wrong numeric rate, rejected plans, tokens, end-to-end latency, ExactScope compute latency, resident/scratch memory, binary size, and energy on your actual device. See [BENCHMARK.md](BENCHMARK.md) and use the integration feedback issue template to report results.
