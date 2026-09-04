# ExactScope prerelease evaluation bundle

The evaluation bundle is the product-proof artifact for developers who want to test ExactScope without installing Rust or building the repository.

It is intentionally release-shaped but still prerelease. Passing these checks proves artifact integrity and deterministic execution for the included slice; it does **not** prove real-device qualification or a model-accuracy improvement.

## Contents

A target-specific archive contains:

```text
bin/exactscope-core                 # prebuilt Tiny JSON/core bridge for tools and benchmarks
lib/<target>/libexactscope_cabi.a   # or exactscope_cabi.lib on Windows
lib/cmake/ExactScope/ExactScopeConfig.cmake
include/exactscope*.h
wasm/exactscope.wasm                # no-import portable artifact
adapters/generated/econ-core-8/     # generated tool schemas, GBNF, catalog, binding
benchmarks/                         # corpus + four-arm benchmark runner
examples/native_smoke.c
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
cc -std=c99 -Wall -Wextra -Werror -pedantic \
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

## 4. Run the no-import Wasm artifact

```text
python3 tools/inspect_wasm.py wasm/exactscope.wasm
node tools/test_wasm.mjs wasm/exactscope.wasm
```

The first command verifies the import/export/memory contract. The second executes scalar economics, statistics, discovery, buffer-sizing, and TinyWire/Tiny JSON conformance against the packaged artifact.

## 5. Run benchmark corpus/core self-test

```text
python3 benchmarks/run_benchmark.py \
  --self-test \
  --core ./bin/exactscope-core
```

This executes the corpus cases that contain expected calls through the packaged core and checks actual discovery behavior. It is a packaging/conformance check, not a model-quality benchmark.

## 6. Run a real llama.cpp benchmark

Start a tool-capable `llama-server`, then run:

```text
python3 benchmarks/run_benchmark.py \
  --core ./bin/exactscope-core \
  --base-url http://127.0.0.1:8080/v1 \
  --model <server-model-name> \
  --output-dir results/<model-id>
```

The bundle already contains `econ-core-8` OpenAI-compatible tool schemas, direct GBNF, the benchmark corpus, and the four comparison arms. A real published claim still requires immutable model revision/quantization/runtime/hardware metadata and the raw generated result files.

## 7. What remains before stable release

The prerelease evaluation bundle removes Rust from the evaluation path. Stable product release still requires:

- recorded real-model evidence across the target model classes;
- broader reviewed benchmark/domain content where justified by evidence;
- permanent versioned GitHub release assets rather than only CI artifacts;
- real-device latency/memory/energy and update/rollback qualification for claimed hardware tiers.
