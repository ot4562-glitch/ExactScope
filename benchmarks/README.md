# ExactScope benchmark tooling

Release context: **v1.0.0-rc.2**
Status: **harness/source inputs are shipped; rc2 model results are intentionally unmeasured**

This directory contains benchmark/corpus/tooling infrastructure. It is developer/evidence tooling, not a target runtime dependency.

## Start here for rc2

Read:

1. `../docs/QUALIFICATION_HANDOFF.md`
2. `NEXT_MODEL_MATRIX.md`
3. `model-downloads.json`
4. `../docs/BENCHMARK.md`
5. `../docs/NEXT_SESSION_PROMPT.md`

Do not run the rc2 model matrix from a moving developer checkout. Start from the immutable public GitHub `v1.0.0-rc.2` release and preserve release/model/runtime/corpus identities before inference.

## Model download only

The repository provides a downloader/inventory helper that does **not** launch inference:

```powershell
py -3 -m pip install -r requirements-benchmark.txt
py -3 tools/fetch_benchmark_models.py --list
py -3 tools/fetch_benchmark_models.py core --root C:\AIModels\ExactScopeBench
```

It resolves each selected Hugging Face repository revision, downloads the named model file at that revision, hashes the local bytes and writes `model-inventory.json`.

Core rc2 matrix:

- Gemma 3 270M IT Q8_0;
- LFM2.5 350M Q4_K_M;
- Qwen3.5 0.8B Q4_0;
- Qwen3.5 2B Q4_K_M;
- Phi-4-mini-instruct 3.8B Q4_K_M.

Optional separate product profile: Gemma 3n E2B IT.

## Harness responsibilities

Benchmark tooling should keep these stages separate:

- task/tool recognition;
- lane/operation selection;
- exact argument extraction/order;
- tool/plan structural validity;
- model-surface identity validity;
- actual Tiny JSON/core status;
- final answer correctness;
- result/failure fidelity;
- wrong-number rate;
- token-limit/timeout behavior;
- model turns/tokens;
- model latency;
- ExactScope bridge/core latency.

The deterministic core must remain the calculation authority. Benchmark code must not provide a hidden formula fallback or semantic repair path.

## No-model core self-test

After building or extracting the packaged `exactscope-core`, the benchmark harness can check corpus/core agreement without running a model:

```powershell
py -3 benchmarks/run_benchmark.py --self-test --core target\release\exactscope-core.exe
```

This is a packaging/conformance check only. It is not an accuracy result.

## Primary rc2 model comparison

For the later qualification session, use:

- **A** — model only;
- **C** — selected semantic `xs_eval` only;
- **D** — `xs_calc + xs_eval` when the exact selected profile exposes both;
- **B** — `xs_calc` only when needed as a diagnostic.

Discovery is an optional ablation, not a required hot-path arm.

The existing `run_benchmark.py` and capability-specific runners are implementation infrastructure. The exact rc2 preregistration decides which harness path is authoritative for the frozen corpus/profile; do not combine incompatible historical harness contracts under one score.

## Output policy

Write new run data under ignored unique directories such as:

```text
benchmarks/output/rc2-<model-id>-<run-id>/
```

Preserve preregistration, model inventory, surface assets, raw item records, summaries, relevant logs, checksums and final status.

`benchmarks/results/` in the clean product source intentionally contains only a policy README. Do not commit mutable/ad-hoc model outputs into the product source tree. Freeze publishable evidence separately with exact identity.

## Historical evidence

Older Statistics/llama.cpp experiments remain historical design evidence only. In particular, `statistics-core-8-ai-r20` belongs to an older 45,804-byte r17 Statistics serving runtime and cannot be relabeled as rc2 evidence.

Historical result interpretation documents may still be useful to understand failure modes, but any rc2 score must be produced again from the exact public release candidate.
