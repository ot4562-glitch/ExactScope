<div align="center">

# ExactScope

### Make the model better without making the model bigger.

**A provider-neutral grounding and semantic-control layer for existing LLM stacks. ExactScope v1.1.0 retains the Linux x86-64 native grounding C ABI/XSGI path as the stable software surface and adds experimental/reference qualification, policy, admission/finalization, drift/requalification and runtime-integration architecture. Its frozen public-development evidence is published with regressions, N/A and a negative Kubernetes long-document proxy retained; enterprise qualification is not claimed.**

No fine-tuning required. No second model. No model replacement. No retry loop. No mandatory agent loop. No heavyweight RAG stack.

> **Keep the model you already have. Add reliability and efficiency around it.**

[Releases](https://github.com/ot4562-glitch/ExactScope/releases) · [10-minute v1.1 technical review](docs/V1_1_TECHNICAL_REVIEW.md) · [Machine-verifiable v1.1 evidence](benchmarks/v1.1-final-public-evidence.json) · [30-second quickstart](#30-second-native-demo) · [Grounding Contract](spec/GROUNDING_CONTRACT_V0_1.md)

[![Release](https://img.shields.io/github/v/release/ot4562-glitch/ExactScope)](https://github.com/ot4562-glitch/ExactScope/releases)
[![License](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue.svg)](#license)
[![Rust](https://img.shields.io/badge/native-Rust%20%2B%20C%20ABI-orange.svg)](crates/exactscope-grounding)
[![Grounding](https://img.shields.io/badge/runtime-no__std%20%7C%20allocation--free-informational.svg)](crates/exactscope-grounding)

</div>

---

## v1.1 technical checkpoint

The v1.1.0 software release freezes public-development policy tuning without claiming enterprise qualification. **Stable support remains the Linux x86-64 native grounding C ABI/XSGI path; the new qualification/control-plane, host-integration and demo surfaces are experimental/reference.** In the headline A→G comparisons, **A is the same model answering without attached evidence and G is that same model under the frozen ExactScope evidence/answer-contract path**. Each workload contains 64 questions; each task mean uses the 16/20 model identities with valid paired outputs, while four protocol-incompatible identities remain N/A.

- **20 frozen model identities / 40 scheduled NQ+Hotpot cells / 32 scored / 8 protocol N/A**;
- Natural Questions 64: mean F1 **12.44% → 21.68% (+9.24 pp)** across the 16 valid model pairs;
- HotpotQA 64 with host-owned LlamaIndex BM25 retrieval + frozen H1: mean F1 **11.63% → 31.42% (+19.79 pp)** across the 16 valid model pairs. **This A→G number is model-only→H1, not ordinary-RAG→H1, and does not establish H1's incremental benefit over ordinary RAG across models**;
- `python3 tools/demo_qualified_execution.py` executes a **`CONFORMANCE_DEMO_ONLY`** compiler → synthetic-attestation → profile → admission → finalization lifecycle and demonstrates fail-closed request/host drift; its fabricated gate values are not qualification evidence;
- the tracked public snapshot is machine-checked by `python3 tools/verify_v11_public_evidence.py`;
- the qualified-execution reference core implements immutable candidate/attestation/profile artifacts plus fail-closed `admit -> host execution -> finalize` semantics. This enforcement assumes a trusted host that reports current identities and cannot bypass the guard; digest binding proves consistency, not host truthfulness;
- runtime evidence is intentionally uneven and explicit: **ONNX Runtime GenAI** has real local generation plus a grounded ExactScope delivery reaching ORT; **ExecuTorch `IRunner`** has current-header compile plus executable fake-runner contract smoke but no real `.pte` claim; **LiteRT-LM** has real Engine/Conversation fixture execution plus an ExactScope ordinary-knowledge delivery and a grounded context-limit finding;
- a frozen Kubernetes Operations long-document proxy produced a **negative** development result: ordinary LlamaIndex RAG utility 28.51% vs initial ExactScope G 17.51%, **G−R = −10.99 pp** with 95% bootstrap interval **[−22.76, −0.48] pp**. The frozen −2 pp quality margin failed, all three bounded diagnostic candidates failed, `selected_arm=null`, and untouched validation32 was not served.

Negative results are retained. The 20-model panel includes regressions and four protocol-N/A identities, and the Kubernetes proxy is reported rather than tuned away. These are **public-development robustness/transfer results, not enterprise qualification, production readiness, economic advantage, or a universal improvement guarantee**.

Start with **[v1.1 release notes](RELEASE_NOTES_v1.1.0.md)** for the stability boundary and **[v1.1 technical review packet](docs/V1_1_TECHNICAL_REVIEW.md)** for the architecture/evidence path.

---

## Why ExactScope?

Small language models are now useful enough to run on laptops, phones, robots, embedded systems, smart glasses, and other constrained devices. Factual reliability is still a hard problem.

A small model often has to answer from imperfect model memory. When the fact is missing, stale, private, device-specific, or simply outside the model's capacity, the model can still produce a plausible answer with confidence.

The usual fixes are expensive or invasive:

- replace the model with a larger one;
- send requests to a cloud model;
- increase the context window;
- build a full RAG platform;
- add an agent/tool-calling loop;
- fine-tune and qualify a new model.

ExactScope takes a different approach:

> **Instead of asking the model to become better at handling facts, ExactScope moves factual grounding into a small deterministic runtime outside the model.**

```text
User question
     |
     v
Application / security scope
     |
     v
ExactScope grounding
     |
     +--> retrieve bounded evidence
     +--> apply authority / coverage / freshness policy
     +--> preserve none / ambiguity / conflict / unavailable states
     +--> resolve deterministic facts when possible
     `--> project only the evidence the model needs
                    |
             0 model calls when
             the host can decide
                    |
             otherwise at most
             1 answer-generation call
                    v
              existing small LLM
```

The model stays a model. ExactScope handles the parts that should not depend on probabilistic guessing.

---

## 30-second native demo

**v1.1.0 is a software/architecture release with a narrow stability contract.** The Linux x86-64 native grounding C ABI/XSGI path remains stable; the new qualification/control-plane and host-integration surfaces are experimental/reference. Public policy tuning is closed: the frozen 20-model NQ/Hotpot panel is final, and the negative Kubernetes proxy closed without selecting a candidate rather than being tuned until it passed.

See the [v1.1 release notes](RELEASE_NOTES_v1.1.0.md), [10-minute technical review](docs/V1_1_TECHNICAL_REVIEW.md), [Kubernetes negative-result report](docs/V1_1_PUBLIC_PROXY_K8S_RESULT.md), and the experimental [ExactScope Bridge](adapters/bridge/README.md). Runtime evidence is reported per backend rather than as a blanket compatibility claim: real generation/delivery exists for ORT and LiteRT-LM at the documented fixture levels, while ExecuTorch remains a current-header + fake-runner contract smoke until a real `.pte` + tokenizer run exists.

Use the current asset from [GitHub Releases](https://github.com/ot4562-glitch/ExactScope/releases). The enterprise DocQA qualification infrastructure is included as reference software, but no owner-bound enterprise workload has been qualified and no customer-value/economic claim follows from the `v1.1.0` tag. The stable native demo remains:

```bash
cc -std=c11 -O2 -Wall -Wextra -Werror -pedantic \
  -Iinclude \
  examples/c/grounding.c \
  lib/x86_64-unknown-linux-gnu/libexactscope_cabi.a \
  -o grounding-demo

./grounding-demo grounding/sample-index-v1.xsgi warranty period
./grounding-demo grounding/sample-index-v1.xsgi battery level
```

Expected evidence includes:

```text
The demo warranty period is 24 months.
The demo device battery level is 73 percent.
```

That executable is using only the extracted public headers, static library, and `.xsgi` provider bytes. No Python runtime, network service, inference server, or agent loop is required by the deployed grounding core.

For the package-local walkthrough see [Native grounding quickstart](docs/GROUNDING_NATIVE_QUICKSTART.md).

### Build your own local evidence index

The off-target compiler lives in the source repository. Point it at your own `.txt` or `.md` evidence:

```bash
python3 tools/grounding_corpus.py build \
  --input-dir ./my-docs \
  --output ./my-corpus.json

python3 tools/grounding_corpus.py compile-binary \
  --index ./my-corpus.json \
  --output ./my-corpus.xsgi
```

Python is compiler/reference/benchmark tooling. It is **not** a deployment dependency of the native grounding runtime.

---

## What ExactScope is

ExactScope is a **provider-neutral grounding and deterministic capability layer** designed to retrofit factual reliability around an existing constrained model.

It provides the pieces needed to:

- retrieve evidence from local or application-defined sources;
- distinguish authoritative evidence from supplemental evidence;
- preserve explicit `grounded`, `none`, `ambiguous`, `conflict`, and `unavailable` states;
- fail closed when authoritative information cannot actually be established;
- resolve simple canonical facts in the host without invoking an LLM;
- reduce arbitrary retrieval/tool decisions made by a weak model;
- project a small deterministic evidence payload instead of dumping large documents into context;
- keep provider indexes, scores, security metadata, and rejected candidates outside the model context;
- run with local/offline provider configurations;
- bind runtime/provider artifacts by exact identity for reproducible qualification.

The goal is not to make model weights universally more intelligent. The goal is to **remove factual work that the model should not have been guessing about in the first place**.

### v1.1 research: policy compiler + qualified execution profile

The redesigned v1.1 treats model training as orthogonal. A base model, quantized model, fine-tuned model, personalized model, or domain model can sit behind the same host boundary. The current strategy deliberately separates three ideas:

- **Semantic Execution Policy Compiler** — the implemented restricted source-to-artifact lowering and a broader architecture hypothesis, not an established product category;
- **Qualified Execution Profile** — the proposed customer-facing deliverable;
- **Reference-Preserving Cost Reduction** — the first conservative Stage 1 selection algorithm, not the whole product identity.

The first fresh compiler-transfer experiment selected a cheaper calibration-tied policy but rejected it on held-out. The later preregistered Qwen/FEVER Stage 1 then executed all 1,200 calibration observations and stopped at `ReferenceOnly`: no cheaper frozen candidate preserved the Reference, and the 600-item held-out was left unscored and retired. These are fail-closed qualification results, **not** evidence of successful automatic cost compilation, customer savings, or a moat.

After FEVER closed, public development moved to real attached behavior instead of changing the failed selector. NQ prospectively froze `precision-context-v5` at 3 KiB/cap8. Hotpot kept host-owned LlamaIndex BM25 retrieval and froze `host-ranked-hybrid-h1-v0` after diagnostic isolation, untouched validation and a predeclared stability64 competence screen. The final post-freeze 20-model NQ/Hotpot panel is now complete, and its outcomes may not be used to retune those policies.

The next proof is no longer another public benchmark. It is a real owner-bound enterprise document-QA qualification with an authorized workload/retriever, ordinary production alternative, owner-approved competence/error requirements, and frozen total-economic/statistical rules. Only after that evidence exists may a standalone Qualification Attestation and Qualified Execution Profile be treated as customer evidence.

The minimum v1.1 semantic center is **evidence sufficiency/context admission** plus **answer-contract lowering/finalization**. The host keeps retrieval execution/authorization, corpus/index management, tokenization/templates, exact token accounting, inference, scheduling/batching, KV/prefix cache, constrained/speculative decoding, accelerators and fallback. Cache/speculation/adapters and broad zero-call routing are not the product identity. Proof-based zero-call completion is valid only with a sound registered verifier for the current authorized evidence.

The proposed deployable object is an immutable **Candidate Execution Policy** plus a separate immutable **Qualification Attestation** that references its exact digest. Their qualified pair is the customer-facing Qualified Execution Profile; request-specific evidence/proof belongs in a separate receipt. v1.1 remains native-free-first: native code must earn a required place through a concrete Python-free host or measured bottleneck/integration advantage.

See the [v1.1 Technical Review Packet](docs/V1_1_TECHNICAL_REVIEW.md), [Product Differentiation](docs/V1_1_PRODUCT_DIFFERENTIATION.md), [Enterprise DocQA Plan](docs/V1_1_ENTERPRISE_DOCQA_PLAN.md), [latest Astra direction review](docs/V1_1_DIRECTION_REFRAME_ASTRA_REVIEW.md), and [Experiment Program](docs/V1_1_EXPERIMENT_PROGRAM.md).

---

## Product boundary

### Your application keeps control of model execution

ExactScope does not own prompt orchestration, sessions, autonomous agent loops, tool selection, retries, or model execution. Your application keeps those responsibilities.

Your inference stack stays in place. The application can keep using llama.cpp or another local model runtime exactly where generation is useful.

The normal grounding path is **zero or one answer-generation call**. The model does not need to choose a retrieval provider before answering.

### Evidence policy, not just similarity-search RAG

A common RAG path is:

```text
question
-> similarity search
-> several retrieved chunks
-> put them in the prompt
-> let the LLM decide what they mean
```

ExactScope separates retrieval from evidence policy:

```text
question
-> bounded provider retrieval
-> authority
-> coverage
-> freshness
-> ambiguity / conflict
-> deterministic evidence policy
-> compact projection
-> model only when generation is still required
```

That distinction matters. A source returning **no result** is not the same as a source being unavailable. Two authoritative sources disagreeing is not the same as one valid fact. A supplemental source is not automatically allowed to replace missing authoritative state.

ExactScope makes those states explicit instead of asking a small model to infer operational truth from prose.

### Works around the model, not inside the weights

ExactScope does not change model weights and does not require fine-tuning.

It is designed to be evaluated across different models and inference engines so that an existing device or product can gain a factual capability layer without making model replacement the default answer.

---

## Why this matters for small and on-device LLMs

Large models can sometimes hide weak application architecture behind more parameters, more context, or stronger tool-use behavior. Small models have less room to compensate.

Asking a constrained model to do all of this itself is a fragile design:

1. understand the question;
2. decide whether retrieval is needed;
3. select a tool/provider;
4. formulate a search;
5. inspect several chunks;
6. resolve conflicts;
7. determine which source is authoritative;
8. answer correctly.

ExactScope deliberately removes much of that responsibility from the model.

This makes the architecture relevant to:

- small LLMs and small language models;
- local LLM and private local AI applications;
- on-device AI and edge AI;
- embedded AI assistants;
- smart glasses and wearable AI;
- phones and mobile AI;
- robots and industrial systems;
- automotive assistants;
- offline AI;
- already-deployed devices where hardware cannot simply be upgraded.

The retrofit thesis is simple:

```text
Option A                         Option B
--------                         --------
small model                      small model
    |                                |
more RAM / compute                   + ExactScope
    |                                |
larger replacement model             v
                                 better grounded
                                 factual behavior
```

For some products, upgrading the capability around the model can be cheaper and easier than upgrading the model itself.

---

## Benchmark evidence

ExactScope is tested against model-only baselines. The project reports negative cells, protocol incompatibilities and corpus scope rather than treating retrieval as proof by itself.

**v1.1 candidate status:** the earlier pre-redesign v1.1 full-matrix run was intentionally stopped and is **not** evidence for the current candidate. The historical tables immediately below remain v1.0 evidence. A separate post-freeze v1.1 NQ/Hotpot panel is reported later in this section as **public-development robustness evidence only**; it is not enterprise qualification or release evidence. Real owner-bound enterprise qualification remains required before customer-value, production-readiness, economic, or v1.1 release claims.

See the [v1.1 Technical Review Packet](docs/V1_1_TECHNICAL_REVIEW.md) for the current candidate boundary, tracked evidence, executable conformance demo, backend-specific runtime evidence, and exact unsupported-claim limits.

### Historical v1.0 20-model post-release qualification

The v1.0.0 grounding path was re-tested across **20 frozen llama.cpp model identities from 135M to 3.8B parameters**, selected for edge/on-device relevance, popular local-model coverage and vendor/architecture diversity.

A separate model-only capability screen used 24 deterministic items from each of **MMLU, ARC-Challenge, HellaSwag, TruthfulQA MC1, WinoGrande and GSM8K**. It scheduled 20 models, completed 18 under the fixed structured-output runtime, scored **2,592 model-items**, and produced a **37.42%** six-task macro mean. This is a recognizable public-data screen, **not** an official Open LLM Leaderboard reproduction.

The ExactScope A/G panel then scheduled the same 20-model identity on Natural Questions, HotpotQA and FEVER. Final disposition was **60 planned cells / 54 scored / 6 explicit N/A protocol failures / 0 retries**.

| Public A/G workload | Model only (A) | ExactScope (G) | Change | Improved / tied / regressed |
|---|---:|---:|---:|---:|
| Natural Questions · F1 | **9.14%** | **21.35%** | **+12.21pp** | 17 / 1 / 0 |
| HotpotQA · F1 | **12.18%** | **24.64%** | **+12.46pp** | 15 / 1 / 2 |
| FEVER · label accuracy | **26.52%** | **30.63%** | **+4.11pp** | 11 / 3 / 4 |

| Model | Params | Public 6 macro | NQ F1 A→G | HotpotQA F1 A→G | FEVER acc A→G |
|---|---:|---:|---:|---:|---:|
| SmolLM2 | 135M | 26.4% | 4.3%→4.3% (+0.0pp) | 4.3%→5.8% (+1.5pp) | 0.0%→0.0% (+0.0pp) |
| Gemma 3 | 270M | 25.7% | 6.2%→10.1% (+3.9pp) | 12.2%→10.3% (-1.9pp) | 0.0%→0.0% (+0.0pp) |
| LFM2.5 | 350M | 31.2% | 4.1%→4.8% (+0.7pp) | 0.0%→19.0% (+19.0pp) | 10.0%→0.0% (-10.0pp) |
| SmolLM2 | 360M | 31.2% | 6.1%→6.2% (+0.1pp) | 4.1%→7.4% (+3.3pp) | 34.0%→0.7% (-33.3pp) |
| Qwen2.5 | 0.5B | 29.2% | 6.0%→23.8% (+17.8pp) | 1.4%→18.7% (+17.3pp) | 6.0%→22.0% (+16.0pp) |
| Qwen3 | 0.6B | 37.5% | 6.5%→12.6% (+6.1pp) | 11.5%→22.5% (+11.0pp) | 38.0%→43.3% (+5.3pp) |
| Qwen3.5 | 0.8B | 41.0% | 5.3%→28.3% (+23.0pp) | 20.2%→42.3% (+22.1pp) | 31.3%→44.0% (+12.7pp) |
| OLMo 2 | 1B | 34.0% | 9.7%→19.2% (+9.4pp) | 16.7%→7.5% (-9.2pp) | 16.0%→1.3% (-14.7pp) |
| Llama 3.2 | 1B | 34.0% | 11.8%→23.4% (+11.6pp) | 9.9%→11.7% (+1.8pp) | 19.3%→26.0% (+6.7pp) |
| TinyLlama | 1.1B | N/A | N/A | N/A | N/A |
| LFM2.5 | 1.2B | 42.4% | 3.8%→15.1% (+11.3pp) | 6.7%→17.5% (+10.8pp) | 26.7%→29.3% (+2.7pp) |
| DeepSeek R1 Distill Qwen | 1.5B | 0.0% | 0.0%→0.0% (+0.0pp) | 0.0%→0.0% (+0.0pp) | 0.0%→0.0% (+0.0pp) |
| SmolLM2 | 1.7B | 37.5% | 10.9%→15.4% (+4.5pp) | 16.2%→17.4% (+1.1pp) | 46.0%→40.0% (-6.0pp) |
| Qwen3 | 1.7B | 48.6% | 10.5%→36.5% (+26.0pp) | 10.5%→47.9% (+37.4pp) | 34.7%→47.3% (+12.7pp) |
| Qwen3.5 | 2B | 46.5% | 9.2%→39.8% (+30.7pp) | 27.3%→56.8% (+29.5pp) | 35.3%→50.7% (+15.3pp) |
| Granite 3.3 | 2B | 47.2% | 10.8%→37.5% (+26.7pp) | 15.2%→52.2% (+37.0pp) | 47.3%→52.7% (+5.3pp) |
| Llama 3.2 | 3B | 49.3% | 26.0%→29.3% (+3.3pp) | 18.0%→20.6% (+2.5pp) | 43.3%→67.3% (+24.0pp) |
| SmolLM3 | 3B | 50.0% | 17.1%→38.6% (+21.5pp) | 25.3%→46.1% (+20.8pp) | 46.0%→60.0% (+14.0pp) |
| Ministral | 3B | N/A | N/A | N/A | N/A |
| Phi-4 mini | 3.8B | 61.8% | 16.1%→39.5% (+23.4pp) | 19.7%→39.8% (+20.2pp) | 43.3%→66.7% (+23.3pp) |

<!-- V11_FINAL_PUBLIC_PANEL_START -->
### v1.1 candidate: frozen 20-model A/G robustness panel

The v1.1 candidate was frozen **before** this cross-model panel. These are observed public-development effects, not a population estimate, guarantee, enterprise qualification, or production-readiness claim. FEVER is excluded because its prior held-out is retired. The historical v1 Public-6 capability macro is shown for context and was **not rerun**.

- **Natural Questions (fresh post-freeze 64):** valid pairs **16/20**, mean F1 12.44% → **21.68%** (**+9.24pp**); improved/tied/regressed = **14 / 0 / 2**.
- **HotpotQA + host-owned LlamaIndex BM25/H1 (fixed stability64):** valid pairs **16/20**, mean F1 11.63% → **31.42%** (**+19.79pp**); improved/tied/regressed = **15 / 0 / 1**.
- Across all valid NQ/Hotpot model-task pairs, descriptive mean uplift = **+14.52pp** (n=32). A per-model two-task mean is shown only when both task pairs are valid.

| Model | Params | v1 Public-6 macro | v1.1 NQ F1 A→G | v1.1 Hotpot F1 A→G | Mean uplift (2 tasks) |
|---|---:|---:|---:|---:|---:|
| SmolLM2 | 135M | 26.4% | N/A | N/A | **N/A** |
| Gemma 3 | 270M | 25.7% | 6.28%→9.20% (**+2.92pp**) | 3.18%→4.17% (**+0.98pp**) | **+1.95pp** |
| LFM2.5 | 350M | 31.2% | 4.75%→10.72% (**+5.97pp**) | 5.83%→11.56% (**+5.73pp**) | **+5.85pp** |
| SmolLM2 | 360M | 31.2% | 6.94%→4.92% (**-2.01pp**) | 6.34%→11.22% (**+4.88pp**) | **+1.43pp** |
| Qwen2.5 | 0.5B | 29.2% | 6.70%→15.69% (**+9.00pp**) | 15.32%→33.94% (**+18.62pp**) | **+13.81pp** |
| Qwen3 | 0.6B | 37.5% | 5.84%→11.76% (**+5.92pp**) | 5.87%→29.00% (**+23.14pp**) | **+14.53pp** |
| Qwen3.5 | 0.8B | 41.0% | 10.44%→24.15% (**+13.71pp**) | 7.82%→40.70% (**+32.88pp**) | **+23.30pp** |
| OLMo 2 | 1B | 34.0% | 11.90%→23.98% (**+12.08pp**) | 23.50%→25.18% (**+1.68pp**) | **+6.88pp** |
| Llama 3.2 | 1B | 34.0% | 15.99%→20.50% (**+4.51pp**) | 12.24%→35.71% (**+23.47pp**) | **+13.99pp** |
| TinyLlama | 1.1B | N/A | N/A | N/A | **N/A** |
| LFM2.5 | 1.2B | 42.4% | N/A | N/A | **N/A** |
| DeepSeek R1 Distill Qwen | 1.5B | 0.0% | N/A | N/A | **N/A** |
| SmolLM2 | 1.7B | 37.5% | 12.63%→22.66% (**+10.03pp**) | 10.33%→21.92% (**+11.60pp**) | **+10.82pp** |
| Qwen3 | 1.7B | 48.6% | 11.83%→23.20% (**+11.36pp**) | 13.91%→41.17% (**+27.26pp**) | **+19.31pp** |
| Qwen3.5 | 2B | 46.5% | 16.00%→41.50% (**+25.49pp**) | 12.71%→66.11% (**+53.40pp**) | **+39.44pp** |
| Granite 3.3 | 2B | 47.2% | 20.56%→32.28% (**+11.72pp**) | 16.61%→40.10% (**+23.49pp**) | **+17.60pp** |
| Llama 3.2 | 3B | 49.3% | 26.84%→31.98% (**+5.14pp**) | 15.00%→51.80% (**+36.80pp**) | **+20.97pp** |
| SmolLM3 | 3B | 50.0% | 18.87%→34.82% (**+15.95pp**) | 18.14%→38.38% (**+20.24pp**) | **+18.10pp** |
| Ministral | 3B | N/A | 5.64%→1.67% (**-3.97pp**) | 0.83%→0.16% (**-0.67pp**) | **-2.32pp** |
| Phi-4 mini | 3.8B | 61.8% | 17.87%→37.89% (**+20.02pp**) | 18.39%→51.58% (**+33.20pp**) | **+26.61pp** |

**Interpretation.** On these fixed 64-item public development cohorts, each cell reports the same model as `A → G (+x.xxpp)`. Averages are descriptive over the explicitly reported valid pairs; they are not population estimates and do not guarantee improvement on another workload or model.

For Qwen3.5 0.8B specifically, the predeclared Hotpot stability64 development screen had already shown H1 over ordinary LlamaIndex RAG by **+5.66pp F1 / +7.81pp EM**, with a paired bootstrap 95% F1 interval of **−4.69pp to +16.25pp**. That earlier result was known before this panel, so the panel is not an independent replication of Qwen. Cross-model A/G does **not** establish H1's incremental benefit over ordinary RAG across all models.

This panel provides **public-workload robustness evidence only** — not enterprise qualification, production readiness, superiority/noninferiority, or demonstrated economic/latency advantage.

N/A cells are retained explicitly:

- `smollm2-135m-instruct-q4km` / `natural_questions`: **N/A** — serving_failed: serving child exit code 1
- `smollm2-135m-instruct-q4km` / `hotpotqa`: **N/A** — serving_failed: serving child exit code 1
- `tinyllama-11b-chat-q4km` / `natural_questions`: **N/A** — serving_failed: serving child incomplete
- `tinyllama-11b-chat-q4km` / `hotpotqa`: **N/A** — serving_failed: serving child exit code 1
- `lfm25-12b-instruct-q4km` / `natural_questions`: **N/A** — serving_failed: serving child exit code 1
- `lfm25-12b-instruct-q4km` / `hotpotqa`: **N/A** — serving_failed: serving child exit code 1
- `deepseek-r1-qwen-15b-q4km` / `natural_questions`: **N/A** — serving_failed: serving child exit code 1
- `deepseek-r1-qwen-15b-q4km` / `hotpotqa`: **N/A** — serving_failed: serving child exit code 1
<!-- V11_FINAL_PUBLIC_PANEL_END -->

Important boundaries for the **historical v1.0 panel above**:

- In that historical v1.0 panel, `TinyLlama 1.1B` and `Ministral 3B` are **N/A**, not zero: the frozen llama.cpp + structured-output protocol failed before a scoreable run. This does not describe the separate v1.1 panel, where Ministral produced scored negative cells.
- In the historical v1.0 public screen, DeepSeek-R1-Distill-Qwen-1.5B had **144/144 format failures**, which remain counted as 0 rather than being excluded. The separate v1.1 frozen protocol instead rejected that identity at preflight and reports it as N/A.
- In those historical v1.0 results, NQ and FEVER use frozen oracle-assisted development corpora marked `qualification_eligible=false`; they are diagnostic/development evidence, not official end-to-end reproductions.
- HotpotQA was the cleanest broader public A/G workload in the historical v1.0 panel.
- Negative cells are retained in both the historical v1.0 evidence and the current v1.1 public-development evidence. ExactScope does **not** claim that every model/workload combination improves.
- The historical v1.0 two-worker grounding run hit a real host OOM on the 16 GB qualification machine. Sealed cells were preserved and the remaining cells were attempted once in a fresh serial recovery. Recovery latency is **not** a product latency claim.

See the [full 20-model qualification report](benchmarks/V1_20_MODEL_RESULTS.md) and [benchmark methodology](docs/BENCHMARK.md) for model identities, per-task public scores, artifact hashes, recovery provenance, isolation rules and reporting requirements.

### Frozen seven-model matched causal screen

A separate frozen 30-item factual screen remains useful as a candidate-bound causal test because the facts are tied to a frozen provider/corpus/policy rather than broad pretrained public knowledge.

| Local model | Model only (A) | ExactScope (G) | Uplift |
|---|---:|---:|---:|
| SmolLM2 135M Instruct Q4_K_M | 3.3% | 86.7% | +83.3pp |
| Gemma 3 270M IT Q8 | 3.3% | 86.7% | +83.3pp |
| LFM2.5 350M Q4_K_M | 6.7% | 93.3% | +86.7pp |
| Qwen3.5 0.8B Q4 | 13.3% | 96.7% | +83.3pp |
| Llama 3.2 1B Instruct Q4_K_M | 6.7% | 90.0% | +83.3pp |
| Qwen3.5 2B Q4_K_M | 10.0% | 100.0% | +90.0pp |
| Phi-4-mini-instruct 3.8B Q4_K_M | 13.3% | 100.0% | +86.7pp |
| **Mean** | **8.1%** | **93.3%** | **+85.2pp** |

In those grounded runs, false grounding, unsupported authoritative assertions and format failures were all **0%**; deterministic host completion handled **23/30** grounded items and only **7/30** required model inference.

**Scope warning:** the +85.2pp result is a candidate-bound causal screen, not a universal expected uplift. The broader 20-model public panel above is intentionally more mixed and includes neutral/negative cells.

---

## Native runtime design

The native grounding core is implemented in Rust and exported through a stable C ABI.

`crates/exactscope-grounding` is:

- `no_std`;
- allocation-free in the grounding core;
- `forbid(unsafe_code)`;
- zero-copy over an immutable validated `.xsgi` index;
- bounded to at most 16 ranked hits;
- caller-owned for search scratch and output memory;
- deterministic in BM25-v1 ranking and evidence projection;
- independent of network and inference ownership.

The C ABI exposes:

```text
xs_grounding_index_init
xs_grounding_index_search
xs_grounding_index_project
```

Python remains the compiler/reference/benchmark layer. The deployed native core does not require Python.

### Native parity

The current native implementation has been checked against the Python reference path on the NQ development mirror and HotpotQA screen:

- top-k search ordering parity;
- exact `f64` score-bit parity;
- byte-exact evidence projection at 2 KiB and 4 KiB;
- clean-room parity using only the extracted release header, static library, and packaged `.xsgi` bytes.

Exact floating-point tie comparison in the ranker is intentional because parity is part of the deterministic contract.

---

## Grounding states and fail-closed authority

ExactScope intentionally distinguishes these target states:

| State | Meaning |
|---|---|
| `grounded` | policy-approved evidence established the target |
| `none` | required source coverage completed and found no usable evidence |
| `ambiguous` | multiple plausible targets/candidates remain unresolved |
| `conflict` | relevant evidence contradicts and policy cannot resolve it |
| `unavailable` | required evidence could not be established because retrieval/coverage failed |

For an **authoritative** target, `unavailable` or unresolved conflict must not silently become a plausible model-memory answer.

For a **supplemental** target, a miss does not mean the world contains no answer; host policy can still allow ordinary model knowledge.

This is one of the key differences between ExactScope and simply pasting search results into a prompt.

---

## Small model-visible context

ExactScope optimizes for **small evidence, not large context**.

The model normally needs only the policy-approved facts required for the current answer. These remain host-side:

- full provider indexes;
- raw retrieval scores;
- rejected candidate sets;
- security/tenant scope identifiers;
- access-control metadata;
- verbose audit state;
- unrelated document content.

The stable native reference historically used a 4 KiB flagship evidence budget. The v1.1 public-development candidates separately froze **3 KiB** budgets for NQ precision and Hotpot H1, but those research configurations are **not universal v1.1 release defaults** and the Kubernetes long-document proxy showed that the tested shaping policies do not automatically transfer to another workload.

---

## Runtime footprint and latency

The default v1 runtime package deliberately excludes benchmark-specific NQ provider data.

Current Linux x86-64 **v1.1 reference-configuration** measurements are (the tagged release must be rebuilt from the real release commit/toolchain before these bytes become release measurements):

- default compressed SDK: **994,148 bytes (~0.994 MB)**;
- demonstration index: **1,618 bytes**;
- runtime/static-library bytes: **4,616,466 bytes (~4.62 MB)**;
- unpacked file bytes: **4,871,604 bytes (~4.87 MB)**.

The existing v1.1 promotion gate is **1,005,099 compressed bytes** (+5% versus the 957,237-byte v1 stable reference package), leaving 10,951 bytes of reference headroom at this checkpoint. **That gate applies to promotion, not exploration.** Detachable v1.1 research configurations may exceed it while their causal value is measured; a future release candidate must be lightweighted and freshly qualified before publication. The broader package hard caps remain historical product constraints, not permission to bloat the final runtime.

The larger **19.71 MB NQ `.xsgi` is qualification/provider data, not a universal built-in corpus**. If a real deployment needs a provider of that size, that provider must be counted in that deployment's own footprint.

On the NQ x86-64 clean-room measurement path:

- one-time index bind/validation: about **161–163 ms**;
- warm search mean: about **100–101 µs/query**;
- 4 KiB projection mean: about **84–86 µs/query**;
- combined warm search + projection mean: about **0.185 ms/query**;
- observed whole-process max RSS: about **21.8 MiB**.

The RSS figure is a whole x86-64 process measurement, **not** a clean incremental-memory measurement excluding the base model.

Do not extrapolate these numbers to a physical ARM64 wearable. Physical ARM64 RAM, latency, energy, and thermal qualification has not yet been performed.

---

## Support matrix

| Target | v1 status | What is claimed |
|---|---|---|
| Linux x86-64 native C ABI | **Stable v1 package scope** | deterministic build/verify, C11 integration, final-archive clean-room execution |
| Windows native | Experimental/source integration | no stable v1 grounding asset claim yet |
| ARM64 / Android / wearable | Experimental design target | no physical-device RAM/energy/thermal claim yet |
| Grounding Wasm | Deferred | not included in v1 grounding release |
| Python compiler/reference tools | Development tooling | off-target corpus compilation, reference behavior, benchmarks |

“Stable” here means the declared v1 software package/API scope. It does not mean hardware certification or universal accuracy qualification for arbitrary providers.

The earlier deterministic quantitative `xs_calc` / `xs_eval` subsystem remains in the repository as a secondary capability. It is not the flagship definition of ExactScope v1.

---

## When should I use ExactScope?

ExactScope is worth evaluating if you are searching for a way to:

- **improve small LLM accuracy without fine-tuning**;
- **reduce factual hallucinations in a local LLM** by grounding answers in application evidence;
- add **grounding to an on-device LLM**;
- keep private/device facts local instead of sending them to a cloud model;
- avoid replacing a deployed small model just to improve factual reliability;
- build a **lightweight RAG alternative for edge AI** where a full RAG platform is too large;
- reduce model-driven tool selection and agent-loop complexity;
- give llama.cpp or another local inference stack compact trusted evidence;
- add deterministic authority/conflict/failure semantics around retrieval;
- retrofit factual capability onto embedded or already-shipped hardware.

You may **not** need ExactScope if your model already answers the target workload reliably, large/cloud models have no meaningful cost, your task is mainly creative generation, or you already have a small trusted grounding stack with equivalent evidence semantics.

ExactScope should solve a measured reliability problem, not become infrastructure for its own sake.

---

## FAQ for local AI / edge AI developers

### How do I improve a small local LLM without training it again?

Put volatile, private, application-specific, or high-authority facts outside model memory. ExactScope retrieves and policy-checks those facts before generation, then sends the model only compact approved evidence when generation is still needed.

### Is ExactScope a hallucination-reduction library?

It can reduce **factual errors caused by missing or unreliable model memory** when the deployment has suitable evidence. It does not claim to eliminate every type of hallucination, reasoning error, or generation failure.

### Is ExactScope a RAG alternative?

For constrained deployments, it can replace part of what teams build a larger RAG stack to accomplish: retrieval, evidence selection, compact projection, and explicit failure semantics. It is intentionally narrower than an enterprise RAG platform and does not try to own every ingestion, vector-database, orchestration, or UI concern.

### Does ExactScope work with llama.cpp?

ExactScope does not own the inference engine, so llama.cpp can remain the model runtime. The stable SDK includes the maintained [`adapters/llama-cpp`](adapters/llama-cpp) grounding integration, fixed preflight surface negotiation, and a zero-network `doctor` command that revalidates the profile/calibration binding before serving traffic.

### Does ExactScope need the internet?

No. The native runtime itself performs no network request. A deployment may use purely local provider data or adapt a host/network search provider behind the same Grounding Contract.

### Does ExactScope contain its own knowledge base?

No universal one. That would defeat the provider-neutral product boundary and make the generic package large without guaranteeing useful coverage. The stable package ships only a tiny demonstration provider; real deployments supply the evidence that matters to them.

### Why not just use a bigger model?

Sometimes you should. ExactScope is aimed at cases where RAM, storage, bandwidth, accelerator capability, latency, privacy, thermals, battery, hardware qualification, or an already-shipped device makes model replacement expensive.

---

## Build from source

Requirements for the native Linux development path include a Rust toolchain and C compiler.

```bash
git clone https://github.com/ot4562-glitch/ExactScope.git
cd ExactScope

cargo build -p exactscope-cabi --release --features standalone-staticlib
cargo test -p exactscope-grounding
cargo clippy -p exactscope-cabi --all-targets -- -D warnings
```

Build the demonstration provider:

```bash
python3 tools/grounding_corpus.py build \
  --input-dir examples/grounding/sample-docs \
  --output target/sample-corpus.json

python3 tools/grounding_corpus.py compile-binary \
  --index target/sample-corpus.json \
  --output target/sample-index-v1.xsgi
```

Compile the C example:

```bash
cc -std=c11 -O2 -Wall -Wextra -Werror -pedantic \
  -Iinclude examples/c/grounding.c \
  target/release/libexactscope_cabi.a \
  -o target/grounding-demo

target/grounding-demo target/sample-index-v1.xsgi warranty period
```

The public stable package additionally passes a clean-room test that recompiles this example from the extracted archive rather than from the repository.

---

## Release integrity

The stable grounding package has its own deterministic packaging contract: [GROUNDING_RUNTIME_BUNDLE_V1.md](spec/GROUNDING_RUNTIME_BUNDLE_V1.md).

The package binds:

- product version;
- source commit;
- toolchain identity;
- runtime size and SHA-256;
- demonstration provider size and SHA-256;
- every packaged payload;
- an explicit support/deployment boundary.

The verifier rejects unsafe archive paths, links, duplicate members, unexpected files, digest drift, malformed XSGI samples, and package hard-cap violations.

The large benchmark qualification data is distributed/accounted separately instead of being disguised as default product footprint.

---

## Documentation

- [v1.1 technical review packet](docs/V1_1_TECHNICAL_REVIEW.md)
- [v1.1 machine-verifiable public evidence](benchmarks/v1.1-final-public-evidence.json)
- [v1.1 enterprise DocQA qualification plan](docs/V1_1_ENTERPRISE_DOCQA_PLAN.md)
- [Product direction](docs/PRODUCT_DIRECTION.md)
- [Grounding architecture](docs/GROUNDING_ARCHITECTURE.md)
- [Grounding Contract v0.1](spec/GROUNDING_CONTRACT_V0_1.md)
- [Native grounding quickstart](docs/GROUNDING_NATIVE_QUICKSTART.md)
- [AI integration](docs/AI_INTEGRATION.md)
- [Installation](docs/INSTALLATION.md)
- [Benchmark methodology](docs/BENCHMARK.md)
- [Stable grounding runtime bundle](spec/GROUNDING_RUNTIME_BUNDLE_V1.md)
- [Security](SECURITY.md)
- [Roadmap](ROADMAP.md)

---

## Related concepts and discovery terms

ExactScope is relevant to developers working on **small LLM**, **local LLM**, **on-device/edge AI**, **enterprise document QA**, **pinned model stacks**, **AI grounding**, **LLM grounding**, **factual accuracy**, **hallucination reduction**, **RAG alternatives**, **lightweight RAG**, **inference-path optimization**, **offline AI**, **llama.cpp**, **deterministic AI**, **AI reliability**, **wearable AI**, and **smart-glasses AI**.

Stable v1.0 is an **accuracy-retrofit/provider-neutral grounding runtime for small, local, and on-device models**. Unreleased v1.1 is testing a broader host-attached semantic/compiler layer for **existing constrained or operationally pinned model/runtime stacks**, with enterprise document QA as the first commercial validation wedge rather than the only long-term market.

---

## License

ExactScope is dual-licensed under [MIT](LICENSE-MIT) or [Apache-2.0](LICENSE-APACHE). Model weights used for qualification retain their upstream licenses and terms.

---

# 한국어 요약

**ExactScope는 작은 로컬·온디바이스 AI의 사실 정확도를 기존 모델을 교체하지 않고 보강하는 경량 grounding runtime / accuracy retrofit layer입니다.**

모델 실행, 세션, agent loop는 기존 애플리케이션과 inference stack이 그대로 담당합니다. ExactScope는 사실 grounding, evidence authority/coverage policy, compact projection에 집중합니다. 단순히 검색 문서를 프롬프트에 넣고 LLM에게 판단을 맡기는 범용 RAG 프레임워크와도 제품 경계가 다릅니다.

기본 철학은 간단합니다.

> **모델이 사실을 더 잘 추측하게 만들지 말고, 추측해야 하는 사실 문제를 모델 밖으로 빼낸다.**

```text
사용자 질문
  -> 앱/보안 scope
  -> provider에서 근거 검색
  -> authority / coverage / freshness / conflict 판단
  -> 확정 가능한 사실은 host가 0회 모델 호출로 처리
  -> 나머지만 작은 evidence projection과 함께 모델 1회 호출
```

135M~3.8B의 7개 로컬 모델을 사용한 동결 30문항 matched screen에서는 모델 단독 평균 **8.1%**가 ExactScope 경로 **93.3%**로 상승했고 평균 uplift는 **+85.2%p**였습니다. grounded 경로에서 false grounding, unsupported authoritative assertion, format failure는 모두 0%였으며 30문항 중 23개는 모델 inference 없이 host가 처리했습니다.

다만 이 수치는 특정 frozen provider/corpus/policy에 묶인 causal benchmark 결과이며 모든 데이터셋에서 +85.2%p를 보장한다는 뜻이 아닙니다. HotpotQA와 NQ development mirror에서는 모델/조건에 따라 더 작은 개선폭도 관측됐고, README에 그 결과도 함께 공개합니다.

v1.1은 아직 출시되지 않았습니다. 현재 방향은 **Qualified AI Execution Control Plane**을 장기 north star로 두고, **Semantic Execution Policy Compiler**를 restricted source-to-artifact lowering의 기술 커널로, **Qualification / Configuration Optimizer**를 첫 제품 가설로 구분합니다. 자동 최적화나 경제적 우위, 새 시장 카테고리는 아직 입증됐다고 주장하지 않습니다. **Qualified Execution Profile**은 immutable Candidate Execution Policy와 별도의 Qualification Attestation을 묶은 qualified artifact 가설입니다.

Qwen/FEVER Stage 1은 1,200개 calibration observation 뒤 `ReferenceOnly`로 종료됐고, 600개 held-out은 점수화하지 않은 채 retired 상태로 남겼습니다. 이후 공개 개발은 selector를 사후 수정하는 대신 real attached behavior로 이동해 NQ `precision-context-v5` 3 KiB/cap8과 LlamaIndex BM25 기반 Hotpot H1을 동결했습니다. 최종 20-model NQ/Hotpot panel은 40개 serving cell을 모두 score 전에 시도했고, **32 scored / 8 protocol N/A**를 그대로 남겼습니다. NQ는 16개 valid pair 평균 **+9.24 pp**, Hotpot의 model-only→H1은 **+19.79 pp**였지만, 후자는 ordinary RAG 대비 H1 우위를 20개 모델 전체에서 증명하는 수치가 아닙니다.

따라서 다음 증거 단계는 더 이상의 공개 benchmark tuning이 아닙니다. 실제 권한이 있는 enterprise document-QA workload, accountable owner/evaluator, production retrieval/index identity, owner-approved competence/error gate, total-economic/statistical rule을 먼저 동결한 뒤 단 한 번의 confirmatory qualification을 수행해야 합니다. 그 전까지 enterprise qualification, production readiness, 자동 cost optimization 또는 customer economic advantage를 주장하지 않습니다.

제품의 최소 semantic 중심도 좁혔습니다. **evidence sufficiency/context admission**과 **answer-contract lowering/finalization**만 우선 핵심으로 두고, retrieval 실행·tokenizer/chat template·inference/scheduling·KV/cache·constrained/speculative decoding·accelerator·fallback은 host가 계속 소유합니다. proof-based 0-call은 현재 authorized evidence에 대해 sound verifier가 있을 때만 허용합니다. `ExactScope Bridge`, cache/speculation hint, adapter 수, native kernel 자체는 제품 identity가 아닙니다.

첫 commercial validation wedge는 **모델을 바꾸기 어렵고 authoritative/versioned document evidence로 정답을 감사할 수 있으며 트래픽이 충분한 enterprise document QA**로 유지하되, 초기에는 short factual answer·extraction·typed decision·citation-bound output처럼 검증 가능한 범위로 더 좁힙니다. 외부 리뷰용 현재 정의와 검증 경로는 [v1.1 Technical Review Packet](docs/V1_1_TECHNICAL_REVIEW.md), [Enterprise DocQA Plan](docs/V1_1_ENTERPRISE_DOCQA_PLAN.md), [Product Differentiation](docs/V1_1_PRODUCT_DIFFERENTIATION.md), [Experiment Program](docs/V1_1_EXPERIMENT_PROGRAM.md)에 기록합니다.

지금 처음 사용하려면 [Releases](https://github.com/ot4562-glitch/ExactScope/releases)의 공개 v1.0 asset을 사용하세요. v1.1은 실험 구조가 충분히 수렴한 뒤 경량화·새 qualification·packaging gate를 통과하기 전까지 release asset으로 간주하지 않습니다.
