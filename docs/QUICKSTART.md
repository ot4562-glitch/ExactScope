# ExactScope quickstart

ExactScope is evolving into a tiny grounding and deterministic capability layer for small and on-device AI. `v1.0.0-rc.3` remains the latest frozen **public** prerelease and its external-user qualification is complete; that public asset is primarily the quantitative runtime/package. The rc4 grounding candidate source `125ad9403f22eece7f552701d4c7376bba3b697f` is now `READY_FOR_GROUNDING_BENCHMARK` after Linux/Windows clean-room and five-model zero-inference preregistration checks, but no rc4 grounding release or model-uplift result is public yet. The flagship path is original-question prefetch -> compact Grounding Frame -> one model answer call, with provider-neutral retrieval and explicit authoritative/supplemental policy.

## 1. Prefer the release asset when evaluating as a user

Choose only an asset that actually appears on the GitHub `v1.0.0-rc.3` release page:

| Platform | Asset role |
|---|---|
| Windows x86-64 | evaluation SDK for local-AI/model integration |
| Linux x86-64 | evaluation SDK for local-AI/model integration |
| Android ARM64 | OEM/edge static SDK |
| Linux ARM64 musl | embedded/wearable static SDK |

Download `SHA256SUMS` and `release-manifest.json` with the archive. Verify the outer checksum before extraction, then inspect the bundle's own `manifest.json` and `SHA256SUMS`.

The prebuilt evaluation SDK is designed to avoid a Rust build requirement for first integration. It includes a native static library, local core bridge, no-import Wasm, headers/CMake metadata, examples, constrained model-facing assets, qualification documentation, model-download metadata/tooling, licenses, and hashes.

See [EVALUATION_BUNDLE.md](EVALUATION_BUNDLE.md) for archive details.

## 2. rc4 grounding path — frozen benchmark-ready candidate, efficacy benchmark not yet run

For the current rc4 source candidate, start from [`GROUNDING_ARCHITECTURE.md`](GROUNDING_ARCHITECTURE.md), [`../spec/GROUNDING_CONTRACT_V0_1.md`](../spec/GROUNDING_CONTRACT_V0_1.md), [`BENCHMARK.md`](BENCHMARK.md), and [`GROUNDING_EVALUATION_PACKAGE.md`](GROUNDING_EVALUATION_PACKAGE.md):

```text
user question
  -> configured source/provider prefetch
  -> Evidence Policy
  -> compact Grounding Frame
  -> one small-model answer call
```

Choose source authority and privacy scope before choosing a retrieval algorithm. The first benchmark candidate freezes a small offline exact/lexical provider for reproducibility; that provider is **not** the universal product definition. A frozen semantic/vector provider, application memory, or captured host/search provider may implement the same ProviderOutcome/GroundingFrame contract later. Do not build a model-visible tool catalog merely to retrieve ordinary evidence.

The frozen candidate passed this source-side no-inference workflow before packaging:

```powershell
py -3 tools/test_grounding_profile.py
py -3 tools/test_grounding_runtime.py
py -3 tools/test_grounding_benchmark.py
py -3 tools/test_grounding_package.py
py -3 tools/validate_design.py
py -3 tools/audit_security_surface.py
```

The final benchmark-ready gate is complete. Exact source/package/model/runtime/preregistration hashes and Linux/Windows clean-room results are in [`GROUNDING_BENCHMARK_READY.md`](GROUNDING_BENCHMARK_READY.md). The separate validation session must follow [`GROUNDING_BENCHMARK_HANDOFF.md`](GROUNDING_BENCHMARK_HANDOFF.md); do not rebuild or modify the frozen candidate before running A/G.

The remainder of this document describes the **currently published rc3 quantitative SDK** and remains valid for evaluating that release. Its A/C/D procedure is historical and separate from the rc4 A/G grounding benchmark.

## 3. Public rc3 quantitative path: pick one model envelope, then the smallest semantic lane

```text
small / on-device model
        |
        +-- native_tools ------ only when runtime /props proves support
        |
        `-- constrained_json -- compatibility baseline
                    |
                    v
             strict request validator
                    |
        +-----------+-----------+
        |                       |
      xs_calc                  xs_eval
  bounded arithmetic       reviewed method
```

Use fewer model-visible choices whenever possible. `xs_find` remains optional cold/development discovery, not a mandatory serving hop. `auto` interface selection happens before inference and never retries a failed output through another envelope.

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

## 4. Native C integration

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

## 5. Wasm integration

The evaluation SDK includes a no-import WebAssembly artifact and a dependency-free JavaScript example. The generic source-build path is:

```powershell
cargo build --locked --release -p exactscope-wasm --target wasm32v1-none --no-default-features --features fused,tinyjson
python tools/inspect_wasm.py target/wasm32v1-none/release/exactscope_wasm.wasm
node examples/javascript/wasm-xs-calc.mjs target/wasm32v1-none/release/exactscope_wasm.wasm
```

The **release archive** ships two complete artifact-bound evaluation capabilities and one archive-local host:

```text
capabilities/quant-core-16-semantic-ai/   # xs_eval only
capabilities/quant-core-16-combined-ai/   # xs_eval + xs_calc
examples/capability-host.mjs
```

The host verifies `manifest.json`, `bundle-sha256.txt`, `profile.json`, `surface-contract.json`, every bound model-surface digest, and the exact `runtime.wasm` before execution. From the extracted archive:

```sh
node examples/capability-host.mjs \
  capabilities/quant-core-16-semantic-ai \
  '{"op":"stats.mean","a":[["1","2","3"]]}'
```

The source checkout path is `examples/javascript/capability-host.mjs`; the packaged path above is intentionally shorter and is the path to use when evaluating a GitHub release.

## 6. llama.cpp / local-model interface

Probe the runtime before inference:

```sh
python tools/llama_cpp_interface.py --base-url http://127.0.0.1:8080/v1 --model-interface auto
```

The probe reads `/props` only. `auto` chooses `native_tools` only when tool definitions, assistant tool calls and object arguments are all explicitly supported; otherwise it chooses `constrained_json`.

The qualification runner freezes both the **requested** and **resolved** interface before inference:

```sh
python benchmarks/run_qualification.py preregister --help
python benchmarks/run_qualification.py run --help
```

`preregister` performs **zero inference calls**. With `auto` or `native_tools` it probes `/props`, resolves the interface, and freezes the normalized runtime capability/template identity together with release/model/runtime/corpus/capability/generation/scoring identities. With explicit `constrained_json`, the native-tool probe is skipped because that interface does not depend on native support. `run` rechecks whichever pre-inference selection inputs were frozen and never performs output-driven fallback.

The semantic arms remain:

- **A** — model only;
- **C** — selected `xs_eval` capability through the frozen envelope;
- **D** — selected `xs_eval + xs_calc` capability through the frozen envelope.

The summary also reports correctness uplift against added mean input tokens, model-surface bytes and added model latency. These are efficiency diagnostics, not permission to hide negative/no-uplift results.

The rc3 five-model qualification is complete and frozen. Any future rc4 benchmark is a new candidate-bound evidence run. Follow [MODEL_INTERFACE_RC4.md](MODEL_INTERFACE_RC4.md), [BENCHMARK.md](BENCHMARK.md), and [RC3_QUALIFICATION_CLOSEOUT.md](RC3_QUALIFICATION_CLOSEOUT.md).

## 7. Source checkout sanity checks

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

## 8. Model inventory tooling

The model downloader remains available for a **new candidate-bound** benchmark and does not launch inference:

```powershell
py -3 -m pip install -r requirements-benchmark.txt
py -3 tools/fetch_benchmark_models.py --list
py -3 tools/fetch_benchmark_models.py core --root C:\AIModels\ExactScopeBench
```

It resolves repository revisions and records file SHA-256 values in `model-inventory.json`. The old [rc3 minimum model matrix](../benchmarks/NEXT_MODEL_MATRIX.md) is a historical completed plan; reuse those models only under a new preregistration/candidate identity.

## 9. Fail closed

Grounding and quantitative adapters may normalize transport syntax. They may not:

- widen private/user/tenant scope implicitly;
- treat provider failure as a true no-hit;
- treat supplemental evidence as authoritative;
- silently choose between conflicting/ambiguous authoritative records;
- pass evidence text as higher-priority instructions;
- invent a missing value;
- silently convert a percentage/unit/currency without a declared quantitative contract;
- choose a statistical/economic method by guess;
- recompute or repair a deterministic result;
- turn a typed failure or authoritative `none/ambiguous/conflict/unavailable` state into a plausible factual value.

The product boundary is valuable precisely because it can preserve missing/ambiguous/unavailable evidence rather than converting uncertainty into confident output.

## 10. Claim boundary

The rc3 external-user qualification is complete; its procedure is preserved in [QUALIFICATION_HANDOFF.md](QUALIFICATION_HANDOFF.md) only as historical audit material. The active conclusions are in [RC3_QUALIFICATION_CLOSEOUT.md](RC3_QUALIFICATION_CLOSEOUT.md).

Do not claim stable production support or representative ARM64 RAM/latency/energy/thermal performance: no physical ARM64 target was available during rc3, so those metrics remain **NOT MEASURED**. Do not claim that rc4 currently improves hallucination or everyday accuracy merely from the new design documents or prototype retrieval code. Any such claim requires a newly frozen grounding candidate with source/provider/policy identities and preregistered A/G model evidence.
