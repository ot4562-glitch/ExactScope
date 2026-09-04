# ExactScope prerelease evaluation bundle

The evaluation bundle is the prerelease integration artifact for developers who want to test ExactScope without installing Rust or building the repository.

It is release-shaped but still prerelease. Passing these checks proves artifact integrity and deterministic execution for the included generic/semantic surfaces; it does **not** by itself prove a benchmarked capability slice, real-device qualification, or a model-accuracy improvement.

## Contents

A target-specific archive contains:

```text
bin/exactscope-core                 # prebuilt Tiny JSON/core bridge for tools and benchmarks
lib/<target>/libexactscope_cabi.a   # or exactscope_cabi.lib on Windows
lib/cmake/ExactScope/ExactScopeConfig.cmake
include/exactscope*.h
wasm/exactscope.wasm                # no-import portable artifact
adapters/generated/quant-core-16/   # mixed economics/statistics tool schemas, GBNF, catalog, binding
benchmarks/                         # corpus + four-arm benchmark runner
examples/native_smoke.c
examples/xs_calc.c
examples/wasm-xs-calc.mjs
tools/test_wasm.mjs
tools/inspect_wasm.py
manifest.json
SHA256SUMS
licenses/
```

`manifest.json` records the source commit, toolchain identity, native target, artifact sizes/digests, hot-set binding, and integration paths. `SHA256SUMS` covers every payload file including the manifest.

## 1. Verify integrity

From the extracted bundle directory, verify `SHA256SUMS` with the platform's normal checksum tool. The repository packaging verifier performs the same file-set and digest checks and rejects archive traversal, links, devices, duplicate checksum entries, or manifest/file drift.

## 2. Run the prebuilt core

Linux/macOS-style example:

```text
printf '%s' '{"op":"econ.ped.mid","a":["10000","12000","100","80"]}' \
  | ./bin/exactscope-core eval
```

Expected compact result:

```json
{"s":0,"v":"-1.222222","c":"elastic","p":"econ-undergrad@0.1.0","r":1}
```

No Rust toolchain is involved.

## 3. Run the native C smoke

For a Unix-style static library:

```text
cc -std=c11 -Wall -Wextra -Werror -pedantic \
  -Iinclude examples/native_smoke.c \
  lib/<target>/libexactscope_cabi.a \
  -o native-smoke
./native-smoke
```

Expected output:

```text
PASS native-smoke op=econ.ped.mid value=-1.222222 classification=elastic
```

The example supplies the documented `xs_platform_panic_abort` host symbol required by the standalone static profile.

CMake consumers may instead point `ExactScope_DIR` at `lib/cmake/ExactScope` and link `ExactScope::exactscope`.

To exercise the bounded arithmetic ABI directly:

```text
cc -std=c11 -Wall -Wextra -Werror -pedantic \
  -Iinclude examples/xs_calc.c \
  lib/<target>/libexactscope_cabi.a \
  -o xs-calc
./xs-calc
```

Expected output is `16`.

## 4. Run the no-import Wasm artifact

```text
python3 tools/inspect_wasm.py wasm/exactscope.wasm
node tools/test_wasm.mjs wasm/exactscope.wasm
node examples/wasm-xs-calc.mjs wasm/exactscope.wasm
```

The first command verifies the import/export/memory contract. The second executes scalar economics, bounded Tiny JSON statistics vectors including named multi-output regression, discovery, buffer-sizing, and TinyWire conformance against the packaged artifact. The public example performs one complete `xs_calc` request and verifies result `16`.

## 5. Run benchmark corpus/core self-test

```text
python3 benchmarks/run_benchmark.py \
  --self-test \
  --core ./bin/exactscope-core
```

This executes the 22 corpus cases that contain expected calls through the packaged core across economics and statistics and checks actual discovery behavior in both registries. It is a packaging/conformance check, not a model-quality benchmark.

## 6. Run a real llama.cpp benchmark

Start a tool-capable `llama-server`, then run:

```text
python3 benchmarks/run_benchmark.py \
  --core ./bin/exactscope-core \
  --base-url http://127.0.0.1:8080/v1 \
  --model <server-model-name> \
  --output-dir results/<model-id>
```

The bundle contains the current `quant-core-16` semantic evaluation assets and benchmark corpus. This is useful implementation evidence, not the final capability-product profile. A real published capability claim requires an immutable capability profile, exact model/tool/schema/grammar/prompt/artifact identities, raw per-item result files, model-difficulty metrics, and the comparison arms defined in `BENCHMARK.md`.

## 7. What remains before stable release

The prerelease evaluation bundle removes Rust from the evaluation path and `v1.0.0-rc.1` now provides permanent versioned GitHub prerelease assets. Stable capability-product release still requires:

- a frozen/reproducible capability-profile format and generator;
- a task-family-driven flagship Statistics capability slice;
- reproducible multi-arm real-model evidence across the target model classes;
- model-difficulty, capability-density, and CRR reporting with raw values;
- real-device latency/memory/energy and update/rollback qualification for claimed hardware tiers;
- long-term compatibility/change-control evidence appropriate to the support label.
