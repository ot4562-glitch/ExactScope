# ExactScope v1.0.0-rc.2 quickstart

ExactScope is a tiny deterministic quantitative capability component for small and on-device AI. `v1.0.0-rc.2` is an **integration & qualification candidate**: code-side implementation and packaging are intended to be usable, while model and real-device qualification are deliberately performed from the published release in a later session.

## 1. Prefer the release asset when evaluating as a user

Choose only an asset that actually appears on the GitHub `v1.0.0-rc.2` release page:

| Platform | Asset role |
|---|---|
| Windows x86-64 | evaluation SDK for local-AI/model integration |
| Linux x86-64 | evaluation SDK for local-AI/model integration |
| Android ARM64 | OEM/edge static SDK |
| Linux ARM64 musl | embedded/wearable static SDK |

Download `SHA256SUMS` and `release-manifest.json` with the archive. Verify the outer checksum before extraction, then inspect the bundle's own `manifest.json` and `SHA256SUMS`.

The prebuilt evaluation SDK is designed to avoid a Rust build requirement for first integration. It includes a native static library, local core bridge, no-import Wasm, headers/CMake metadata, examples, constrained model-facing assets, qualification documentation, model-download metadata/tooling, licenses, and hashes.

See [EVALUATION_BUNDLE.md](EVALUATION_BUNDLE.md) for archive details.

## 2. Pick the smallest AI-facing lane

```text
small / on-device model
        |
        +-- knows arithmetic decomposition --> xs_calc --> ExactScope
        |
        +-- needs reviewed method -----------> xs_eval --> ExactScope
        |
        `-- operation genuinely unknown -----> xs_find  (optional cold/dev path)
```

Use fewer model-visible choices whenever possible. `xs_find` is not a mandatory serving hop.

### `xs_calc`

Plan v0.1 accepts at most eight backward-referencing steps over:

```text
add  sub  mul  div  powi  sqrt
```

Example request:

```json
{"p":[{"o":"mul","a":["12","7"]},{"o":"sub","a":["#0","4"]},{"o":"div","a":["#1","5"]}]}
```

Expected canonical result:

```json
{"s":0,"v":"16","f":0,"p":"plan-v0.1","r":1}
```

### `xs_eval`

Use a generated selected capability for reviewed domain methods. The model should see only operations needed by the task family, not the whole maintenance catalog. Decimal inputs are strings at the Tiny JSON boundary so host JSON parsing does not silently change the value.

## 3. Native C integration

Public header:

```text
include/exactscope.h
```

The release archive contains a target static library. `examples/xs_calc.c` demonstrates caller-owned context and a typed bounded-plan call. On Unix-like hosts the pattern is:

```sh
cc -std=c11 -Wall -Wextra -Werror -pedantic \
  -Iinclude examples/xs_calc.c \
  lib/<target>/libexactscope_cabi.a \
  -o xs-calc
./xs-calc
```

Expected output: `16`.

Windows consumers link the packaged `exactscope_cabi.lib`. Do not assume a native target is supported if no matching release archive exists.

## 4. Wasm integration

The evaluation SDK includes a no-import WebAssembly artifact and a dependency-free JavaScript example. The generic source-build path is:

```powershell
cargo build --locked --release -p exactscope-wasm --target wasm32v1-none --no-default-features --features fused,tinyjson
python tools/inspect_wasm.py target/wasm32v1-none/release/exactscope_wasm.wasm
node examples/javascript/wasm-xs-calc.mjs target/wasm32v1-none/release/exactscope_wasm.wasm
```

For a selected capability integration, use the generated capability/model-surface assets and `examples/javascript/capability-host.mjs`, which verifies the expected identity before compiling/loading the module.

## 5. llama.cpp / local-model hookup

Two maintained one-tool envelopes are under `adapters/llama-cpp/`:

- `direct_eval_smoke.py` — semantic-only `xs_eval` envelope;
- `calc_plan_smoke.py` — calc-only `xs_calc` envelope.

They are strict protocol adapters, not alternate calculators. They validate capability/model-surface identity and model output shape; they must not invent arguments, change methods, or repair an ExactScope error.

For model evaluation, follow [AI_INTEGRATION.md](AI_INTEGRATION.md) and the separate [qualification handoff](QUALIFICATION_HANDOFF.md). Do not use old model scores as evidence for rc2.

## 6. Source checkout sanity checks

When developing rather than evaluating the published release:

```powershell
cargo check --workspace --all-targets
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace --lib
py -3 tools/generate_statistics_metadata.py --check
py -3 tools/generate_domain_metadata.py --check
py -3 tools/validate_design.py
py -3 tools/audit_security_surface.py
```

These prove code/build contracts, not model uplift or target-device qualification.

## 7. Download the planned benchmark models without running them

Keep weights outside the repository:

```powershell
py -3 -m pip install -r requirements-benchmark.txt
py -3 tools/fetch_benchmark_models.py --list
py -3 tools/fetch_benchmark_models.py core --root C:\AIModels\ExactScopeBench
```

The downloader resolves repository revisions and records file SHA-256 values in `model-inventory.json`. It does not launch inference.

See [the minimum model matrix](../benchmarks/NEXT_MODEL_MATRIX.md) before adding more models.

## 8. Fail closed

Adapters may normalize transport syntax. They may not:

- invent a missing value;
- silently convert a percentage/unit/currency without a declared contract;
- swap argument meaning;
- choose a statistical/economic method by guess;
- recompute or repair the deterministic result;
- turn a typed failure into a plausible number.

The product boundary is valuable precisely because it can return a deterministic typed failure instead of guessing.

## 9. Before claiming the product is qualified

Use [QUALIFICATION_HANDOFF.md](QUALIFICATION_HANDOFF.md). The next session must start from the immutable GitHub rc2 release, bind every result to exact artifact/model/runtime/corpus identities, and then measure a representative real ARM64 target before making target RAM/latency/energy claims.

Historical r20 Statistics model evidence belongs to an older runtime and is not rc2 evidence.
