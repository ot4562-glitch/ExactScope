# ExactScope v1.0.0-rc.2 evaluation SDK

The evaluation SDK is the prerelease integration artifact for developers who want to evaluate ExactScope without first installing Rust or understanding the workspace.

It proves a release-shaped integration path. Passing bundle integrity/smoke checks does **not** by itself prove model uplift, real-device qualification, target RAM/latency/energy, or stable support.

## Contents

A target-specific x86-64 archive is designed to contain:

```text
bin/exactscope-core[.exe]                # prebuilt local Tiny JSON/core bridge
lib/<target>/libexactscope_cabi.a        # or exactscope_cabi.lib on Windows
lib/cmake/ExactScope/ExactScopeConfig.cmake
include/exactscope*.h
wasm/exactscope.wasm                     # no-import portable artifact
adapters/generated/<hot-set>/            # bound tool/GBNF/catalog/prompt assets
examples/native_smoke.c
examples/xs_calc.c
examples/wasm-xs-calc.mjs
examples/capability-host.mjs
benchmarks/corpus-v0.1.jsonl
benchmarks/NEXT_MODEL_MATRIX.md
benchmarks/model-downloads.json
benchmarks/results/README.md
tools/fetch_benchmark_models.py
tools/inspect_wasm.py
tools/test_wasm.mjs
docs/QUICKSTART.md
docs/AI_INTEGRATION.md
docs/QUALIFICATION_HANDOFF.md
docs/NEXT_SESSION_PROMPT.md
requirements-benchmark.txt
manifest.json
SHA256SUMS
licenses/
```

`manifest.json` is the authoritative inventory and records source commit, toolchain identity, native target, artifact sizes/digests, selected hot-set binding, and integration paths. `SHA256SUMS` covers the packaged payload including the manifest.

Historical mutable benchmark result JSON files are intentionally not copied into a new SDK as if they were rc2 results.

## 1. Verify the outer GitHub release first

Before extracting the SDK:

1. verify the downloaded archive against release-level `SHA256SUMS`;
2. confirm `release-manifest.json` names the expected tag/source commit and archive digest;
3. preserve those files with any later qualification result.

If these checks fail, do not continue as rc2 evidence.

## 2. Verify the extracted SDK

From the extracted directory, verify the bundle's internal `SHA256SUMS` with the platform checksum tool.

The source packaging verifier additionally checks exact file inventory/digests and rejects unsafe archive members such as traversal paths, links/devices, duplicate checksum entries, or manifest/file drift.

## 3. Run the prebuilt core smoke

Unix-style example:

```sh
printf '%s' '{"op":"econ.ped.mid","a":["10000","12000","100","80"]}' \
  | ./bin/exactscope-core eval
```

Expected compact success shape:

```json
{"s":0,"v":"-1.222222","c":"elastic","p":"econ-undergrad@0.1.0","r":1}
```

The exact packaged behavior, not this prose snippet, is authoritative. No Rust toolchain is involved.

## 4. Native C smoke

Unix-style static-library example:

```sh
cc -std=c11 -Wall -Wextra -Werror -pedantic \
  -Iinclude examples/native_smoke.c \
  lib/<target>/libexactscope_cabi.a \
  -o native-smoke
./native-smoke
```

The example supplies the documented host panic symbol required by the standalone static profile.

For bounded arithmetic:

```sh
cc -std=c11 -Wall -Wextra -Werror -pedantic \
  -Iinclude examples/xs_calc.c \
  lib/<target>/libexactscope_cabi.a \
  -o xs-calc
./xs-calc
```

Expected output: `16`.

CMake consumers can point `ExactScope_DIR` at `lib/cmake/ExactScope` and link `ExactScope::exactscope`.

## 5. Wasm smoke

```sh
python3 tools/inspect_wasm.py wasm/exactscope.wasm
node tools/test_wasm.mjs wasm/exactscope.wasm
node examples/wasm-xs-calc.mjs wasm/exactscope.wasm
```

These checks exercise the packaged integration boundary. They are not a substitute for target qualification and must not be reported as a model benchmark.

For an exact selected capability, prefer the identity-aware `examples/capability-host.mjs` and the generated model-surface assets rather than widening the serving surface manually.

## 6. Benchmark-corpus/core self-test

The included deterministic benchmark harness can run a **no-model** self-test against the packaged core:

```sh
python3 benchmarks/run_benchmark.py --self-test --core ./bin/exactscope-core
```

This is packaging/conformance evidence only. It must not be labeled model accuracy.

## 7. Prepare model weights without running inference

The SDK includes the planned minimum model matrix and a download/inventory helper:

```powershell
py -3 -m pip install -r requirements-benchmark.txt
py -3 tools/fetch_benchmark_models.py --list
py -3 tools/fetch_benchmark_models.py core --root C:\AIModels\ExactScopeBench
```

The helper resolves repository revisions, downloads selected files at those revisions, computes SHA-256, and writes `model-inventory.json`. It does **not** run a model or ExactScope benchmark.

The five core models and rationale are defined in `benchmarks/NEXT_MODEL_MATRIX.md`. Do not expand the matrix casually before the first preregistered rc2 run.

## 8. Real model benchmark belongs to the next session

Do not treat an ad-hoc `llama-server` run as release evidence. Before the first inference call, freeze the exact release, model, runtime, corpus, prompt/tool/GBNF assets, generation settings, scoring rules, retry/timeout policy, and output identity as described in:

- `docs/QUALIFICATION_HANDOFF.md`;
- `docs/NEXT_SESSION_PROMPT.md`.

Primary comparison arms are A model-only, C selected semantic-only, and D combined when the exact selected profile actually contains both. Add B calc-only only for diagnostics.

Historical r20 Statistics model scores belong to an older 45,804-byte r17 runtime and are not rc2 baseline results.

## 9. ARM64 product qualification

Android ARM64 and Linux ARM64 musl use separate OEM SDK archives rather than the x86-64 evaluation archive. Model qualification and target qualification should be kept distinguishable.

A representative target run should record at least artifact/storage bytes, resident memory/heap, stack/scratch where measurable, latency distribution, energy method/results when available, thermal behavior where relevant, fail-closed malformed-input behavior, offline behavior, and update/rollback/power-loss behavior when applicable.

A Wasm linear-memory page maximum is not total process/device RSS.

## 10. Stable-release boundary

`v1.0.0-rc.2` provides permanent versioned public candidate assets so qualification can be performed against an immutable input. Stable/support promotion still requires evidence for the exact published artifacts, including the selected model matrix or justified product-specific subset and representative target-device qualification.

Use [QUALIFICATION_HANDOFF.md](QUALIFICATION_HANDOFF.md) as the canonical continuation contract.
