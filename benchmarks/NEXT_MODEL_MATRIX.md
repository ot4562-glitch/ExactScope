# ExactScope v1.0.0-rc.2 qualification model matrix

Status: **planned, unmeasured for v1.0.0-rc.2**
As-of: 2026-09-05
Machine-readable source: [`model-downloads.json`](model-downloads.json)

This is the next-session model plan for the release artifact. It is intentionally small: five core GGUF models cover an extreme-small architecture, an edge-first architecture, a current mainstream sub-1B model, a 2B scaling point, and an independent upper-small reasoning model. One explicit low-resource product model is optional and runs as a separate runtime/device profile.

No score in this document belongs to `v1.0.0-rc.2` until the exact release tag, release asset digests, model repository revisions, model file digests, corpus, prompts, generation settings, scoring code, and output records have been frozen together.

## Core five

| ID | Model | Quantization | Approx. download | Why it is in the minimum matrix |
|---|---|---|---:|---|
| `gemma3-270m-it-q8` | Gemma 3 270M IT | Q8_0 | 292 MB | extreme-small independent architecture; deliberately tests the point where tool selection/extraction may be the limiting factor |
| `lfm25-350m-q4km` | LFM2.5 350M | Q4_K_M | 229 MB | edge/on-device-first family; closest core representative to an embedded product design target |
| `qwen35-08b-q4` | Qwen3.5 0.8B | Q4_0 | 563 MB | current mainstream sub-1B model with modern chat/tool ecosystem support |
| `qwen35-2b-q4km` | Qwen3.5 2B | Q4_K_M | 1.27 GB | same-family scale point: tests whether ExactScope remains useful when selection/extraction gets stronger |
| `phi4-mini-38b-q4km` | Phi-4-mini-instruct 3.8B | Q4_K_M | 2.49 GB | independent upper-small reasoning reference; avoids turning the study into a single-family Qwen comparison |

The two Qwen sizes are deliberate rather than redundant: they provide one controlled family scaling comparison while the remaining three rows supply architecture/vendor/use-case diversity.

## Optional product-oriented profile

`google/gemma-3n-E2B-it` is the optional sixth model. Google describes Gemma 3n as designed for efficient execution on low-resource devices; E2B has a 6B raw parameter count but an architecture intended to operate with a memory footprint comparable to a traditional 2B model. It is gated and multimodal, so do **not** mix it into the core GGUF/llama.cpp score table unless the exact runtime path and text-only evaluation contract are made comparable. Treat it as a separate embedded-product qualification profile.

## Download without running a benchmark

On Windows, keep model weights outside the repository:

```powershell
py -3 -m pip install -r requirements-benchmark.txt
py -3 tools/fetch_benchmark_models.py --list
py -3 tools/fetch_benchmark_models.py core --root C:\AIModels\ExactScopeBench
```

The downloader resolves each repository's current commit **before** downloading, downloads the requested file at that immutable revision, hashes the bytes, and writes `C:\AIModels\ExactScopeBench\model-inventory.json`. That inventory becomes a preregistration input. Downloading models is not a benchmark run.

For gated models, log in to Hugging Face / accept the model's terms first and provide `HF_TOKEN` when required. Model licenses are independent of ExactScope's MIT/Apache-2.0 source license.

## Minimum comparison shape

Do not run every historical arm for every model. The primary qualification should use three arms:

- **A — model only:** same prompt/task, no ExactScope tool surface.
- **C — selected semantic ExactScope:** only the compiled `xs_eval` surface required by the task family.
- **D — combined surface:** `xs_calc + xs_eval` only when that release capability/profile actually exposes both.

Add **B — xs_calc only** for diagnostics when generic arithmetic value needs to be isolated. Do not add a larger-model E arm automatically; `phi4-mini-38b-q4km` already gives an upper-small independent reference in the same five-model inventory. A bigger reference is justified only if it answers a specific product decision.

## Keep the benchmark fair

Before the first inference call, freeze:

1. ExactScope Git tag, commit, source archive digest, and release asset digests.
2. Exact capability/profile/model-surface contract IDs and asset digests.
3. `model-inventory.json` including repository commit, local path, bytes, and SHA-256 for every model.
4. llama.cpp build/version and command line, or the exact alternate runtime for the optional product profile.
5. corpus bytes + SHA-256, corpus generator revision, task-family allocation, and any held-out split.
6. prompt text, chat template behavior, GBNF/tool schema assets, context size, temperature, seed, and maximum generated tokens.
7. scoring code and the rule for malformed model output, tool-selection failure, argument-extraction failure, runtime failure, and final-answer mismatch.
8. single-writer output directory and a no-retry/no-hidden-repair rule unless a retry policy was preregistered.

Use identical generation budgets for comparison arms unless the preregistration explicitly justifies a difference. Report counts as well as percentages. Keep selection/extraction failures separate from deterministic runtime failures.

## Qualification order

Run cheapest-to-most-informative so weak candidates can stop early without compromising the preregistered rule:

1. Gemma 3 270M and LFM2.5 350M lower-bound checks.
2. Qwen3.5 0.8B primary small-model run.
3. Qwen3.5 2B scale comparison.
4. Phi-4-mini 3.8B independent upper-small reference.
5. Optional Gemma 3n E2B product/runtime profile only after the core result set is frozen.

A model may be stopped for a documented preregistered futility condition, e.g. catastrophic parser/tool-surface incompatibility in an initial fixed-size qualification slice. Do not invent a stop rule after seeing the full score.

## What this matrix must answer

For each model and task family:

- Does a selected ExactScope surface increase correct end-to-end task completion over model-only?
- Is semantic-only or combined surface better for that model?
- What proportion of failures comes from semantic selection, argument extraction, deterministic execution, or answer rendering?
- What binary/tool-surface cost was added for the exact artifact?
- Does the result survive at least one architecture/vendor change rather than only one model family?

Only after model-level evidence is frozen should target-device latency/RAM/stack/energy results be combined into a product qualification summary.

## Historical evidence boundary

The earlier `statistics-core-8-ai-r20` model evidence belongs to an older 45,804-byte r17 serving runtime. It may be used as historical design evidence, but it is **not** a baseline score for `v1.0.0-rc.2` and must never be copied into a new evidence manifest. Re-running a historical model on rc.2 creates new evidence.

## Completion condition

The matrix is complete only when every reported row has immutable ExactScope identity, immutable model identity, raw output coverage, zero unexplained duplicate `(arm, item)` keys, scoring provenance, and an explicit `complete` or `invalid` status. Until then README/release notes must say **unmeasured**.
