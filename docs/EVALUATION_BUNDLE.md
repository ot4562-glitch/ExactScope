# ExactScope v1.0.0-rc.3 evaluation SDK — frozen public artifact

Status: **historical rc3 quantitative package contract; rc3 external-user qualification is complete**. Active rc4 work has a separate grounding contract/reference implementation and pre-inference grounding evaluation-package format; none of that mutates or reinterprets this frozen public rc3 release description.

The evaluation SDK is the prerelease **quantitative integration artifact** for developers who want to reproduce/evaluate rc3 without first installing Rust or understanding the workspace. It does **not** contain or imply the separate provider-neutral rc4 grounding product/profile now implemented in the rc4 source candidate.

It proves a release-shaped quantitative integration path. Passing bundle integrity/smoke checks does **not** by itself prove grounding accuracy, hallucination reduction, false-grounding behavior, model uplift, real-device qualification, target RAM/latency/energy, or stable support.

The separate rc4 grounding evaluation package defined in [`GROUNDING_EVALUATION_PACKAGE.md`](GROUNDING_EVALUATION_PACKAGE.md) binds source/provider/index/policy/GroundingFrame/projection/corpus/model/runtime/scorer identities separately; this rc3 capability bundle is not the grounding format.

## Contents

A target-specific x86-64 archive is designed to contain:

```text
bin/exactscope-core[.exe]                # prebuilt local Tiny JSON/core bridge
lib/<target>/libexactscope_cabi.a        # or exactscope_cabi.lib on Windows
lib/cmake/ExactScope/ExactScopeConfig.cmake
include/exactscope*.h
wasm/exactscope.wasm                     # no-import portable artifact
adapters/generated/<hot-set>/            # raw generated hot-set assets
capabilities/quant-core-16-semantic-ai/  # complete artifact-bound xs_eval capability
capabilities/quant-core-16-combined-ai/  # complete artifact-bound xs_eval + xs_calc capability
examples/native_smoke.c
examples/xs_calc.c
examples/wasm-xs-calc.mjs
examples/capability-host.mjs
benchmarks/capability_surface.py
benchmarks/run_qualification.py
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

Historical mutable benchmark result JSON files are intentionally not copied into a new SDK as if they were rc3 results.

## 1. Verify the outer GitHub release first

Before extracting the SDK:

1. verify the downloaded archive against release-level `SHA256SUMS`;
2. confirm `release-manifest.json` names the expected tag/source commit and archive digest;
3. preserve those files with any later qualification result.

If these checks fail, do not continue as rc3 evidence.

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

The archive contains two complete identity-aware capability directories. `examples/capability-host.mjs` accepts those directories directly and rejects digest/profile/surface/runtime drift before execution:

```sh
node examples/capability-host.mjs capabilities/quant-core-16-semantic-ai \
  '{"op":"stats.mean","a":[["1","2","3"]]}'

node examples/capability-host.mjs capabilities/quant-core-16-combined-ai \
  '{"p":[{"o":"mul","a":["12","7"]},{"o":"sub","a":["#0","4"]},{"o":"div","a":["#1","5"]}]}'
```

Do not reconstruct a capability from `adapters/generated/` during release qualification; the versioned `capabilities/` directories are the immutable model-facing inputs.

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

The five core models and rationale are defined in `benchmarks/NEXT_MODEL_MATRIX.md`. Do not expand the matrix casually before the first preregistered rc3 run.

## 8. Real model benchmark belongs to the next session

Do not treat an ad-hoc `llama-server` run as release evidence. Use the packaged two-phase qualification harness:

```sh
python benchmarks/run_qualification.py preregister --help
python benchmarks/run_qualification.py run --help
```

`preregister` performs no inference and freezes the exact release archive/model/runtime/corpus/core/capability byte identities plus launch command, context, seed, generation ceiling, timeout, scoring rules and no-retry policy. `run` re-verifies every frozen identity and refuses to start on drift. Completed output contains `results.jsonl`, copied C/D capability evidence, `summary.json`, `run-status.json`, the exact preregistration, and `SHA256MANIFEST.json`.

Primary comparison arms are A model-only, C the shipped semantic capability, and D the shipped combined capability. The current semantic benchmark corpus expects `xs_eval` in C/D; a D-side `xs_calc` choice is recorded as wrong-lane rather than silently credited. There is no hidden retry or semantic repair.

The detailed rules remain in `docs/QUALIFICATION_HANDOFF.md` and `docs/NEXT_SESSION_PROMPT.md`. Historical r20 Statistics model scores belong to an older 45,804-byte r17 runtime and are not rc3 baseline results.

## 9. ARM64 product qualification

Android ARM64 and Linux ARM64 musl use separate OEM SDK archives rather than the x86-64 evaluation archive. Model qualification and target qualification should be kept distinguishable.

A representative target run should record at least artifact/storage bytes, resident memory/heap, stack/scratch where measurable, latency distribution, energy method/results when available, thermal behavior where relevant, fail-closed malformed-input behavior, offline behavior, and update/rollback/power-loss behavior when applicable.

A Wasm linear-memory page maximum is not total process/device RSS.

## 10. Stable-release boundary

`v1.0.0-rc.3` provides permanent versioned public candidate assets so qualification can be performed against an immutable input. Stable/support promotion still requires evidence for the exact published artifacts, including the selected model matrix or justified product-specific subset and representative target-device qualification.

Use [QUALIFICATION_HANDOFF.md](QUALIFICATION_HANDOFF.md) as the canonical continuation contract.
