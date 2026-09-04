# ExactScope 5-minute quickstart

ExactScope is a tiny deterministic quantitative coprocessor for small and on-device AI. The normal consumer of ExactScope is an AI runtime, not a person using a calculator UI.

The fastest useful path is **direct evaluation with a known operation key**. Discovery is a cold-path fallback, not a required extra model turn.

## 1. The hot path

For a product that already knows its small hot set, the model emits one call:

```json
{"op":"econ.cpi.inflation","a":["100","103.2"]}
```

ExactScope returns a deterministic result. The model should copy or render that result; it must not recalculate it.

```text
model
  -> xs_eval(op,args)
  -> ExactScope
  -> deterministic result
```

No `xs_find` call is required when the operation key is already known or has been cached against the installed registry digest.

## 2. Discovery only when needed

If the operation is not in the host's generated/cached hot set, use discovery once:

```json
{"q":"midpoint price elasticity","n":3}
```

A successful discovery returns canonical operation metadata such as:

```json
{"s":0,"m":[{"op":"econ.ped.mid","sig":"econ.ped.mid(p1,p2,q1,q2)","method":"midpoint"}]}
```

The host then binds that operation key to the current registry/pack digest and future calls use direct `xs_eval`.

```text
cold path:
model -> xs_find -> bind/cache -> xs_eval

hot path:
model ---------------------> xs_eval
```

## 3. Prebuilt evaluation artifact

Integrators should not need to build ExactScope from Rust source just to decide whether the component is useful.

The repository now builds a release-shaped prerelease evaluation archive containing:

- a target-native static library plus `ExactScope::exactscope` CMake package;
- a prebuilt `exactscope-core` executable for Tiny JSON and benchmark use;
- the no-import WebAssembly module;
- generated mixed `quant-core-16` economics/statistics OpenAI-compatible tool assets and GBNF;
- the benchmark runner/corpus;
- manifest, checksums, licenses, and native/Wasm smoke tests.

CI extracts that archive outside the source tree and executes the packaged components. See [Evaluation bundle](EVALUATION_BUNDLE.md) for the no-Rust evaluation path.

Permanent versioned GitHub Release assets remain a release task. Rust, Python, Node.js, Java, a daemon, an account, or a network connection must not be required by the target runtime itself; Python/Node are only developer-side evaluation tools in the prerelease bundle.

## 4. Native C/C++ integration

A packaged native SDK is intended to support:

```cmake
find_package(ExactScope CONFIG REQUIRED)
target_link_libraries(my_product PRIVATE ExactScope::exactscope)
```

Then the host:

1. initializes one ExactScope context;
2. binds a small operation hot set;
3. calls `xs_eval` directly for known operations;
4. optionally exposes `xs_find` as a fallback;
5. runs the SDK doctor on the developer workstation and the target self-test on the device.

The host owns model inference, UI, storage, permissions, and updates. ExactScope owns deterministic validation and calculation.

## 5. Wasm integration

The portable release profile is a no-import WebAssembly module. The host instantiates it with an empty import object, allocates non-overlapping caller regions in exported memory, and uses the documented wire exports.

TinyWire is preferred when compact typed transport, explicit semantic/unit metadata, or larger vectors matter. Tiny JSON supports bounded model-facing scalar strings and vector arrays under the 512-byte request and 64-decimal-leaf limits.

## 6. AI integration rule

The recommended model-facing order is:

1. preload or generate an 8-32 operation product hot set;
2. constrain output with generated JSON Schema/GBNF where the runtime supports it;
3. call `xs_eval` directly for known keys;
4. use `xs_find` only for an operation not present in the bound hot set;
5. cache successful discovery metadata by registry/pack digest;
6. invalidate/rebind when the digest or operation revision changes.

See [AI integration](AI_INTEGRATION.md) for the full contract.

## 7. Fail-closed without making the model brittle

The core remains strict. The adapter may normalize **syntax**, but it must not guess **meaning**.

Safe adapter normalization examples:

- trim transport whitespace;
- convert an already parsed JSON numeric token to its exact decimal lexical form when the host parser preserved that exact value;
- translate an outer tool-call envelope;
- reorder named protocol fields into the fixed adapter layout.

Unsafe semantic repair examples:

- treating `5%` as `0.05` without an explicit operation contract;
- dropping `$` or converting currencies;
- converting centimeters to meters;
- guessing a missing method or value;
- changing a sample statistic to a population statistic.

A failed call is preferable to a fabricated number, but benchmark reporting must measure whether constrained decoding and adapters keep the successful-answer rate high enough for real products.

## 8. What to measure before adoption

Do not adopt ExactScope because of an accuracy slogan. Run the benchmark harness against your model and hot set.

Compare at least:

- model-only;
- ExactScope direct hot path;
- ExactScope discovery path;
- ExactScope direct hot path with constrained decoding.

Measure final answer accuracy, operation selection, argument extraction, invalid-call rate, successful-answer rate, tokens, end-to-end latency, ExactScope compute latency, resident bytes, scratch bytes, and energy where measurable.

See [Benchmark contract](BENCHMARK.md).

## 9. Current status

The repository is still prerelease. Native C ABI, deterministic economics/statistics execution, bounded Tiny JSON scalar/vector calls, no-import Wasm, TinyWire, CMake SDK integration, the developer-side SDK doctor, digest-bound hot-set/OpenAI/GBNF generation, focused `econ-core-8`/`statistics-core-8` selections plus mixed `quant-core-16`, a llama.cpp direct-eval reference runner, a four-arm benchmark harness with a real Tiny JSON/core bridge, and deterministic release-shaped evaluation bundles with clean-room CI are implemented. Recorded real-model benchmark evidence, permanent versioned GitHub Release assets, broader official pack coverage, and real-device qualification remain release work.
