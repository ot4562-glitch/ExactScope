# llama.cpp constrained `xs_calc` flow

This reference path keeps planning and calculation separate:

```text
question -> llama.cpp + xs-calc.gbnf -> bounded plan -> ExactScope -> numeric result
```

The grammar constrains JSON shape only. `ExactScope` still rejects forward
references, wrong arity, invalid decimals, domain errors, overflow, and other
semantic failures. The host never repairs a model-selected plan.

From the repository root, after building `exactscope-core`, run:

```powershell
cargo build --release -p exactscope-conformance --bin exactscope-core
python examples/llama.cpp/run_xs_calc.py `
  --llama-cli C:\path\to\llama-cli.exe `
  --model C:\path\to\model.gguf `
  --core target\release\exactscope-core.exe `
  --question "What is (12 * 7 - 4) / 5?"
```

The runner prints one JSON record containing the raw plan, structural/runtime
acceptance, the deterministic result, generated-token estimate, plan-step
count, and wall-clock latency. A wrong but valid plan remains a planning
failure; it is not changed by the runner or runtime.

For the checked-in five-case reference matrix, pass `--model` three times to
`benchmark_xs_calc.py`. The intended RC matrix is Qwen3 0.6B, Qwen3 1.7B, and
Llama 3.2 3B. The resulting JSON includes per-item records and aggregate valid
plan, runtime acceptance, correctness, wrong-number, token, step, and latency
metrics. It is an integration smoke, not a general model benchmark score.
