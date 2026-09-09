# ExactScope v1.0.0 — 20-model post-release qualification

Date: **2026-09-10**

This report is post-release qualification of the already-published ExactScope v1.0.0 grounding path. It does **not** change the v1 binary, retune the frozen retrieval/projection behavior, or claim an official leaderboard reproduction.

## What was tested

The matrix freezes **20 llama.cpp-compatible local models from 135M to 3.8B parameters**. Selection was based on:

- commercial edge/on-device relevance;
- mobile, single-board-computer, embedded, or ARM-class plausibility;
- popular local-model families;
- vendor/architecture diversity;
- coverage from extreme-small models through the upper end of the v1 constrained-model target.

The matrix intentionally mixes models explicitly positioned for edge/on-device use with popular local-model controls. It does **not** claim that every model in the matrix ships inside a specific retail wearable.

Examples of explicit edge/on-device positioning from model vendors include:

- Meta Llama 3.2 1B/3B: edge/mobile models, with Qualcomm/MediaTek and Arm enablement — https://ai.meta.com/blog/llama-3-2-connect-2024-vision-edge-mobile-devices/
- Google Gemma 3 270M: intended for mobile devices and single-board computers — https://ai.google.dev/gemma/docs/get_started
- Liquid LFM2.5 350M: an ultra-compact model explicitly designed for edge devices and low-latency deployments — https://docs.liquid.ai/lfm/models/lfm25-350m
- Liquid LFM2.5 1.2B: optimized for on-device/edge workflows — https://www.liquid.ai/blog/introducing-lfm2-5-the-next-generation-of-on-device-ai
- Mistral Ministral 3B: explicitly introduced for on-device and edge use cases — https://mistral.ai/news/ministraux/
- Microsoft Phi-4-mini: introduced as the local model behind Microsoft Edge's on-device Prompt and Writing Assistance APIs — https://blogs.windows.com/msedgedev/2025/05/19/introducing-the-prompt-and-writing-assistance-apis/

The exact 20-model identity, repository revision, GGUF filename, byte count and upstream LFS SHA-256 are frozen in [`v1-model-matrix-20.json`](v1-model-matrix-20.json).

## Part A — recognizable public capability screen

Six well-known benchmark datasets were used as a deterministic **24-item-per-task screen**:

- MMLU
- ARC-Challenge
- HellaSwag
- TruthfulQA MC1
- WinoGrande
- GSM8K

Each scheduled model received 144 items. This is **not** an official Open LLM Leaderboard reproduction: generation/scoring protocol, sample count and constrained output contract differ. The purpose is to show that the 20-model panel spans meaningfully different baseline capability levels before looking at ExactScope A/G uplift.

Results:

- scheduled models: **20**
- protocol-valid completed models: **18**
- fixed-runtime/protocol incompatible models: **2** (`TinyLlama 1.1B`, `Ministral 3B`)
- scored model-items: **2,592**
- mean six-task macro accuracy across the 18 completed models: **37.42%**

| Public task | Mean accuracy across 18 completed models |
|---|---:|
| MMLU | 40.51% |
| ARC-Challenge | 51.62% |
| HellaSwag | 46.30% |
| TruthfulQA MC1 | 30.79% |
| WinoGrande | 53.70% |
| GSM8K | 1.62% |

DeepSeek-R1-Distill-Qwen-1.5B completed the fixed protocol but produced **144/144 format failures**, so it remains a valid completed cell with a 0.0% macro score rather than being silently excluded.

### Full public-screen table

| Model | Params | MMLU | ARC-C | HellaSwag | TruthfulQA | WinoGrande | GSM8K | Macro | Format failures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SmolLM2 | 135M | 25.0% | 37.5% | 25.0% | 25.0% | 41.7% | 4.2% | 26.4% | 10 |
| Gemma 3 | 270M | 12.5% | 29.2% | 37.5% | 29.2% | 45.8% | 0.0% | 25.7% | 18 |
| LFM2.5 | 350M | 50.0% | 50.0% | 37.5% | 4.2% | 45.8% | 0.0% | 31.2% | 10 |
| SmolLM2 | 360M | 20.8% | 20.8% | 45.8% | 50.0% | 50.0% | 0.0% | 31.2% | 19 |
| Qwen2.5 | 0.5B | 33.3% | 29.2% | 33.3% | 29.2% | 50.0% | 0.0% | 29.2% | 7 |
| Qwen3 | 0.6B | 54.2% | 54.2% | 54.2% | 12.5% | 45.8% | 4.2% | 37.5% | 16 |
| Qwen3.5 | 0.8B | 45.8% | 58.3% | 45.8% | 37.5% | 58.3% | 0.0% | 41.0% | 15 |
| OLMo 2 | 1B | 20.8% | 50.0% | 37.5% | 20.8% | 70.8% | 4.2% | 34.0% | 12 |
| Llama 3.2 | 1B | 33.3% | 50.0% | 41.7% | 25.0% | 54.2% | 0.0% | 34.0% | 19 |
| TinyLlama | 1.1B | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| LFM2.5 | 1.2B | 58.3% | 62.5% | 37.5% | 25.0% | 70.8% | 0.0% | 42.4% | 12 |
| DeepSeek R1 Distill Qwen | 1.5B | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 144 |
| SmolLM2 | 1.7B | 45.8% | 50.0% | 58.3% | 8.3% | 62.5% | 0.0% | 37.5% | 24 |
| Qwen3 | 1.7B | 45.8% | 70.8% | 58.3% | 45.8% | 70.8% | 0.0% | 48.6% | 19 |
| Qwen3.5 | 2B | 50.0% | 75.0% | 45.8% | 54.2% | 54.2% | 0.0% | 46.5% | 22 |
| Granite 3.3 | 2B | 50.0% | 58.3% | 70.8% | 41.7% | 58.3% | 4.2% | 47.2% | 5 |
| Llama 3.2 | 3B | 62.5% | 75.0% | 58.3% | 41.7% | 58.3% | 0.0% | 49.3% | 17 |
| SmolLM3 | 3B | 54.2% | 75.0% | 66.7% | 41.7% | 58.3% | 4.2% | 50.0% | 21 |
| Ministral | 3B | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| Phi-4 mini | 3.8B | 66.7% | 83.3% | 79.2% | 62.5% | 70.8% | 8.3% | 61.8% | 1 |

## Part B — ExactScope A/G grounding panel

The same 20-model identity was scheduled on three A/G workloads:

- Natural Questions development mirror: 128 items/model/arm
- HotpotQA pooled-distractor screen: 20 items/model/arm
- FEVER oracle-page-pooled development screen: 150 items/model/arm

`A` is model-only. `G` is the frozen ExactScope grounding intervention using the same model/runtime when a model call is needed.

The first two-worker parent run was interrupted by a real host OOM on the 16 GB qualification machine. The interrupted parent was **not** marked complete. Its sealed evidence was preserved as 35 completed cells + 3 TinyLlama terminal failures + 22 unsealed cells. A fresh, no-resume/no-retry serial recovery attempted only those 22 cells and produced 19 completed cells + 3 Ministral terminal failures. Final qualification re-authenticated all 60 dispositions before any scorer/gold access and again after scoring.

Final disposition:

- planned cells: **60**
- scored cells: **54**
- explicit N/A failures: **6**
- retries: **0**
- resumed partial children: **0**
- latency from the recovery run: **not qualifying**

### Aggregate A/G result across 18 scored models

| Workload / metric | Model only (A) | ExactScope (G) | Change | Models improved / tied / regressed |
|---|---:|---:|---:|---:|
| Natural Questions · F1 | **9.14%** | **21.35%** | **+12.21pp** | 17 / 1 / 0 |
| Natural Questions · EM | 3.47% | 13.72% | +10.24pp | — |
| HotpotQA · F1 | **12.18%** | **24.64%** | **+12.46pp** | 15 / 1 / 2 |
| HotpotQA · EM | 5.28% | 17.22% | +11.94pp | — |
| FEVER · label accuracy | **26.52%** | **30.63%** | **+4.11pp** | 11 / 3 / 4 |

**Important scope boundary:** the NQ and FEVER corpora in this qualification are marked `oracle_assisted_corpus=true` and `qualification_eligible=false` in their frozen manifests. They are useful development/diagnostic evidence, but they are not presented as official end-to-end benchmark reproductions. The HotpotQA pooled-distractor A/G screen is the cleanest broader public A/G result in this 20-model panel.

The negative cells are retained. ExactScope does not claim that grounding improves every model/workload combination.

### Full 20-model A/G table

`N/A` means the fixed llama.cpp + structured-output protocol failed before a scoreable run. It is not converted to zero accuracy.

| Model | Params | Public 6 macro | NQ F1 A→G | HotpotQA F1 A→G | FEVER acc A→G |
|---|---:|---:|---:|---:|---:|
| SmolLM2 | 135M | 26.4% | 4.3→4.3 (+0.0pp) | 4.3→5.8 (+1.5pp) | 0.0→0.0 (+0.0pp) |
| Gemma 3 | 270M | 25.7% | 6.2→10.1 (+3.9pp) | 12.2→10.3 (-1.9pp) | 0.0→0.0 (+0.0pp) |
| LFM2.5 | 350M | 31.2% | 4.1→4.8 (+0.7pp) | 0.0→19.0 (+19.0pp) | 10.0→0.0 (-10.0pp) |
| SmolLM2 | 360M | 31.2% | 6.1→6.2 (+0.1pp) | 4.1→7.4 (+3.3pp) | 34.0→0.7 (-33.3pp) |
| Qwen2.5 | 0.5B | 29.2% | 6.0→23.8 (+17.8pp) | 1.4→18.7 (+17.3pp) | 6.0→22.0 (+16.0pp) |
| Qwen3 | 0.6B | 37.5% | 6.5→12.6 (+6.1pp) | 11.5→22.5 (+11.0pp) | 38.0→43.3 (+5.3pp) |
| Qwen3.5 | 0.8B | 41.0% | 5.3→28.3 (+23.0pp) | 20.2→42.3 (+22.1pp) | 31.3→44.0 (+12.7pp) |
| OLMo 2 | 1B | 34.0% | 9.7→19.2 (+9.4pp) | 16.7→7.5 (-9.2pp) | 16.0→1.3 (-14.7pp) |
| Llama 3.2 | 1B | 34.0% | 11.8→23.4 (+11.6pp) | 9.9→11.7 (+1.8pp) | 19.3→26.0 (+6.7pp) |
| TinyLlama | 1.1B | N/A | N/A | N/A | N/A |
| LFM2.5 | 1.2B | 42.4% | 3.8→15.1 (+11.3pp) | 6.7→17.5 (+10.8pp) | 26.7→29.3 (+2.7pp) |
| DeepSeek R1 Distill Qwen | 1.5B | 0.0% | 0.0→0.0 (+0.0pp) | 0.0→0.0 (+0.0pp) | 0.0→0.0 (+0.0pp) |
| SmolLM2 | 1.7B | 37.5% | 10.9→15.4 (+4.5pp) | 16.2→17.4 (+1.1pp) | 46.0→40.0 (-6.0pp) |
| Qwen3 | 1.7B | 48.6% | 10.5→36.5 (+26.0pp) | 10.5→47.9 (+37.4pp) | 34.7→47.3 (+12.7pp) |
| Qwen3.5 | 2B | 46.5% | 9.2→39.8 (+30.7pp) | 27.3→56.8 (+29.5pp) | 35.3→50.7 (+15.3pp) |
| Granite 3.3 | 2B | 47.2% | 10.8→37.5 (+26.7pp) | 15.2→52.2 (+37.0pp) | 47.3→52.7 (+5.3pp) |
| Llama 3.2 | 3B | 49.3% | 26.0→29.3 (+3.3pp) | 18.0→20.6 (+2.5pp) | 43.3→67.3 (+24.0pp) |
| SmolLM3 | 3B | 50.0% | 17.1→38.6 (+21.5pp) | 25.3→46.1 (+20.8pp) | 46.0→60.0 (+14.0pp) |
| Ministral | 3B | N/A | N/A | N/A | N/A |
| Phi-4 mini | 3.8B | 61.8% | 16.1→39.5 (+23.4pp) | 19.7→39.8 (+20.2pp) | 43.3→66.7 (+23.3pp) |

## Protocol and hardware notes

- fixed llama.cpp runtime identity for all comparable cells;
- model revisions/files/bytes/SHA-256 frozen before inference;
- `temperature=0`-style deterministic generation policy from the frozen generation contract;
- retry count: **0**;
- hidden repair: **off**;
- gold inaccessible to the run phase;
- score phase starts only after complete run-evidence validation;
- qualification machine: AMD Ryzen 5 5600G, 6 cores / 12 threads, 16 GB RAM, WSL2;
- recovery execution used one model at a time and 6 inference threads after two-worker execution caused a real host OOM;
- benchmark-run latency is therefore **not** a release latency claim.

The long model-inference time is not ExactScope native grounding latency. Native ExactScope search/projection remains a separate microsecond-scale software-path measurement documented in the release evidence.

## Frozen artifact identities

| Artifact | SHA-256 |
|---|---|
| 20-model matrix | `c5f314348a55ef7bb8c7bdbfc5467594a6891971d67725e9fed3da1f08d568de` |
| public benchmark-suite contract | `d27e8e584b9a9fdd7cddb052d93eb00ec03e81b615f52f46df02f4997a3f117d` |
| public 20×6 matrix result | `4fbf37d02c28997cc5ee9df89c7541520c4157eb1dbe27c468c0afa4d4d3f805` |
| final 20×3 qualification manifest | `b6ac52b3dc81f660c9e1c3c1e3c13e61f7b4cad3cd632bd2d9c47e6f138e9fb3` |

The raw `target/` outputs are local qualification evidence and are not publication artifacts. Public claims are limited to the frozen identities, aggregate/model tables and protocol boundaries documented here.
