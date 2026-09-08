# llama.cpp ExactScope model-interface reference

Release context: **retained quantitative-subsystem model-interface reference after completed v1.0.0-rc.3 qualification**
Status: **reference integration for model-generated quantitative requests; ordinary rc4 grounding prefetch does not depend on this path and no new model evidence is created from this source tree**

rc3 demonstrated that native OpenAI-style tool calling is not portable across all small-model chat templates. The quantitative subsystem therefore separates the model envelope from the deterministic semantic lane. The flagship rc4 everyday grounding path instead prefetches evidence before the model answer call and does not require a llama.cpp tool envelope.

```text
question
   |
   v
llama.cpp runtime /props capability probe
   |
   +--> native_tools      only when required support is proven
   |
   `--> constrained_json  compatibility baseline
              |
              v
     ExactScope request validator
              |
       +------+------+
       |             |
     xs_calc       xs_eval
       |             |
       +------+------+
              |
              v
     deterministic core
```

## 1. Probe the model interface without inference

With a running llama.cpp server:

```powershell
py -3 tools/llama_cpp_interface.py `
  --base-url http://127.0.0.1:8080/v1 `
  --model-interface auto
```

The probe performs a GET on llama.cpp `/props`. It does **not** send a model prompt. `auto` resolves to `native_tools` only when the active runtime/template explicitly reports all of:

- tool-definition support;
- assistant tool-call support;
- object-argument support.

Otherwise it resolves to `constrained_json`.

A saved `/props` document can be inspected offline:

```powershell
py -3 tools/llama_cpp_interface.py `
  --props-file C:\path\to\props.json `
  --model-interface auto
```

The output includes normalized capability booleans plus hashes of the exact props/chat-template identities used for selection.

There is no output-driven fallback. A model failure does not cause the same request to be retried through another interface.

## 2. Constrained compatibility path

Every rc4 AI-facing capability is designed to contain:

```text
constrained-prompt.txt
xs-request.gbnf
```

The request grammar composes the exact selected `xs_eval`/`xs_calc` lane grammars plus explicit fail-closed `{"n":true}`.

The model's job is only to select the lane/operation and extract explicit inputs. It should not calculate a supported answer itself.

## 3. Native tool path

When `/props` proves compatible native tool support, the same capability may expose the bound `xs-eval.tool.json` and optional `xs-calc.tool.json` assets.

The native path is an optimization, not a semantic authority. It reaches the same validators and deterministic core as constrained JSON.

## 4. Local `xs_calc` development smoke

The older direct llama-cli smoke remains useful for bounded-plan development:

```powershell
cargo build --release -p exactscope-conformance --bin exactscope-core
py -3 examples/llama.cpp/run_xs_calc.py `
  --llama-cli C:\path\to\llama-cli.exe `
  --model C:\path\to\model.gguf `
  --core target\release\exactscope-core.exe `
  --question "What is (12 * 7 - 4) / 5?"
```

The grammar constrains structure. ExactScope still rejects invalid decimals, wrong arity, forward references, domain errors, overflow and resource violations. The host must not repair a model-selected plan.

## 5. Qualification boundary

The rc3 five-model qualification is complete and frozen. Its historical plan/runbook remain under `benchmarks/NEXT_MODEL_MATRIX.md` and `docs/QUALIFICATION_HANDOFF.md`, but they are not instructions to continue rc3 inference.

Any rc4 benchmark must first freeze a new immutable candidate and record:

- exact runtime/model/capability identities;
- requested and resolved model interface;
- normalized `/props` capability record and template hashes;
- prompt/tool/grammar bytes;
- generation/scoring settings;
- raw outputs;
- input-token/model-latency deltas and efficiency ratios.

See `docs/MODEL_INTERFACE_RC4.md`, `docs/RC3_QUALIFICATION_CLOSEOUT.md`, and `docs/BENCHMARK.md`.
