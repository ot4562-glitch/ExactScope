# llama.cpp `xs_calc` reference

Release context: **v1.0.0-rc.2**
Status: **reference integration; rc2 model benchmark is intentionally unmeasured**

This path keeps planning and deterministic execution separate:

```text
question -> llama.cpp + xs-calc.gbnf -> bounded plan -> ExactScope -> result/failure
```

The grammar constrains structure. ExactScope still rejects invalid decimals, wrong arity, forward references, domain errors, overflow and resource violations. The host must not repair a model-selected plan.

## Local development smoke

After building the local core bridge:

```powershell
cargo build --release -p exactscope-conformance --bin exactscope-core
py -3 examples/llama.cpp/run_xs_calc.py `
  --llama-cli C:\path\to\llama-cli.exe `
  --model C:\path\to\model.gguf `
  --core target\release\exactscope-core.exe `
  --question "What is (12 * 7 - 4) / 5?"
```

The runner records the raw plan, structural/runtime acceptance, deterministic result, generated-token estimate, plan-step count and wall-clock latency. A wrong but structurally valid plan remains a model planning failure.

This is useful for adapter development, but **do not use an ad-hoc run from a dirty checkout as rc2 evidence**.

## rc2 qualification path

For actual `v1.0.0-rc.2` model evidence:

1. start from the immutable GitHub release archive;
2. verify `release-manifest.json` and `SHA256SUMS`;
3. use the five-model matrix in `../../benchmarks/NEXT_MODEL_MATRIX.md`;
4. freeze `model-inventory.json`, llama.cpp build/command, corpus, prompt/grammar/tool assets, generation settings and scorer before inference;
5. use the comparison/failure rules in `../../docs/QUALIFICATION_HANDOFF.md`.

The core five are Gemma 3 270M, LFM2.5 350M, Qwen3.5 0.8B, Qwen3.5 2B and Phi-4-mini 3.8B. The old five-case Qwen3/Llama smoke is historical integration evidence only and is not the rc2 benchmark matrix.

Use the maintained `adapters/llama-cpp/` semantic-only envelope for selected `xs_eval` qualification. The normal product path should expose only the selected surface; `xs_find` remains optional/cold.

Historical r20 Statistics model scores belong to an older 45,804-byte r17 runtime and must not be reused for rc2.
