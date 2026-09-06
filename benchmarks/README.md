# ExactScope benchmark tooling

Release context: **rc4 tooling development after completed v1.0.0-rc.3 qualification**
Status: **rc3 outputs are frozen historical evidence; harness code is being upgraded for model-envelope identity and efficiency metrics**

This directory contains benchmark/corpus/tooling infrastructure. It is developer/evidence tooling, not a target runtime dependency.

## Start here for rc4 development

Read:

1. `../docs/RC3_QUALIFICATION_CLOSEOUT.md`
2. `../docs/MODEL_INTERFACE_RC4.md`
3. `../docs/BENCHMARK.md`
4. `../ROADMAP.md`
5. `model-downloads.json` only when preparing a new candidate-bound model run.

Do not resume the old rc3 matrix. If new inference is requested, first freeze a new immutable candidate and preregister the exact release/model/runtime/corpus/model-envelope identities before inference.

## Model download only

The repository provides a downloader/inventory helper that does **not** launch inference:

```powershell
py -3 -m pip install -r requirements-benchmark.txt
py -3 tools/fetch_benchmark_models.py --list
py -3 tools/fetch_benchmark_models.py core --root C:\AIModels\ExactScopeBench
```

It resolves each selected Hugging Face repository revision, downloads the named model file at that revision, hashes the local bytes and writes `model-inventory.json`.

Core rc3 matrix:

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

## Primary rc3 model comparison

The public evaluation archive ships the authoritative primary qualification runner:

```text
benchmarks/capability_surface.py
benchmarks/run_qualification.py
capabilities/quant-core-16-semantic-ai/
capabilities/quant-core-16-combined-ai/
```

Run `run_qualification.py preregister` before starting a model. It performs zero inference and freezes the exact archive/model/runtime/corpus/core/C/D byte identities plus generation and failure policy. Then run the frozen record with `run_qualification.py run` into a new empty directory.

The primary arms are:

- **A** — model only;
- **C** — exact shipped semantic capability, `xs_eval` only;
- **D** — exact shipped combined capability, `xs_eval + xs_calc`.

The current corpus is semantic; supported C/D items expect `xs_eval`, and missing-information items expect no tool call. A D-side `xs_calc` choice is preserved as wrong-lane rather than credited. **B** calc-only and discovery remain optional diagnostics outside the primary runner and must not be added after seeing primary results.

`run_benchmark.py` remains the no-model baseline/legacy benchmark infrastructure. Do not merge its historical arm names with the immutable A/C/D qualification score.

## Output policy

Write new run data under ignored unique directories such as:

```text
benchmarks/output/rc3-<model-id>-<run-id>/
```

Preserve preregistration, model inventory, surface assets, raw item records, summaries, relevant logs, checksums and final status.

`benchmarks/results/` in the clean product source intentionally contains only a policy README. Do not commit mutable/ad-hoc model outputs into the product source tree. Freeze publishable evidence separately with exact identity.

## Historical evidence

Older Statistics/llama.cpp experiments remain historical design evidence only. In particular, `statistics-core-8-ai-r20` belongs to an older 45,804-byte r17 Statistics serving runtime and cannot be relabeled as rc3 evidence.

Historical result interpretation documents may still be useful to understand failure modes, but any rc3 score must be produced again from the exact public release candidate.
