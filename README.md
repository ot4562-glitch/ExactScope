<div align="center">

# ExactScope

### Improve factual accuracy in small, local, and on-device AI with application evidence — without replacing the model.

**A lightweight grounding runtime and AI accuracy retrofit layer for small LLMs, local AI, edge AI, and on-device models.**

No fine-tuning. No model replacement. No mandatory agent loop. No heavyweight RAG stack.

> **Keep the model you already have. Move factual uncertainty outside the model.**

[Releases](https://github.com/ot4562-glitch/ExactScope/releases) · [30-second quickstart](#30-second-native-demo) · [Benchmark evidence](#benchmark-evidence) · [Grounding Contract](spec/GROUNDING_CONTRACT_V0_1.md) · [Architecture](docs/GROUNDING_ARCHITECTURE.md)

[![Release](https://img.shields.io/github/v/release/ot4562-glitch/ExactScope)](https://github.com/ot4562-glitch/ExactScope/releases)
[![License](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue.svg)](#license)
[![Rust](https://img.shields.io/badge/native-Rust%20%2B%20C%20ABI-orange.svg)](crates/exactscope-grounding)
[![Grounding](https://img.shields.io/badge/runtime-no__std%20%7C%20allocation--free-informational.svg)](crates/exactscope-grounding)

</div>

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

The stable v1 product package is deliberately small. It contains the Linux x86-64 native C ABI runtime, public headers, a C11 example, and a **1.6 KB demonstration-only grounding index**.

Download `exactscope-grounding-1.0.0-x86_64-unknown-linux-gnu.tar.gz` from [GitHub Releases](https://github.com/ot4562-glitch/ExactScope/releases), extract it, and run:

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

### 20-model post-release qualification

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
| SmolLM2 | 135M | 26.4% | 4.3→4.3 | 4.3→5.8 | 0.0→0.0 |
| Gemma 3 | 270M | 25.7% | 6.2→10.1 | 12.2→10.3 | 0.0→0.0 |
| LFM2.5 | 350M | 31.2% | 4.1→4.8 | 0.0→19.0 | 10.0→0.0 |
| SmolLM2 | 360M | 31.2% | 6.1→6.2 | 4.1→7.4 | 34.0→0.7 |
| Qwen2.5 | 0.5B | 29.2% | 6.0→23.8 | 1.4→18.7 | 6.0→22.0 |
| Qwen3 | 0.6B | 37.5% | 6.5→12.6 | 11.5→22.5 | 38.0→43.3 |
| Qwen3.5 | 0.8B | 41.0% | 5.3→28.3 | 20.2→42.3 | 31.3→44.0 |
| OLMo 2 | 1B | 34.0% | 9.7→19.2 | 16.7→7.5 | 16.0→1.3 |
| Llama 3.2 | 1B | 34.0% | 11.8→23.4 | 9.9→11.7 | 19.3→26.0 |
| TinyLlama | 1.1B | N/A | N/A | N/A | N/A |
| LFM2.5 | 1.2B | 42.4% | 3.8→15.1 | 6.7→17.5 | 26.7→29.3 |
| DeepSeek R1 Distill Qwen | 1.5B | 0.0% | 0.0→0.0 | 0.0→0.0 | 0.0→0.0 |
| SmolLM2 | 1.7B | 37.5% | 10.9→15.4 | 16.2→17.4 | 46.0→40.0 |
| Qwen3 | 1.7B | 48.6% | 10.5→36.5 | 10.5→47.9 | 34.7→47.3 |
| Qwen3.5 | 2B | 46.5% | 9.2→39.8 | 27.3→56.8 | 35.3→50.7 |
| Granite 3.3 | 2B | 47.2% | 10.8→37.5 | 15.2→52.2 | 47.3→52.7 |
| Llama 3.2 | 3B | 49.3% | 26.0→29.3 | 18.0→20.6 | 43.3→67.3 |
| SmolLM3 | 3B | 50.0% | 17.1→38.6 | 25.3→46.1 | 46.0→60.0 |
| Ministral | 3B | N/A | N/A | N/A | N/A |
| Phi-4 mini | 3.8B | 61.8% | 16.1→39.5 | 19.7→39.8 | 43.3→66.7 |

Important boundaries:

- `TinyLlama 1.1B` and `Ministral 3B` are **N/A**, not zero: the frozen llama.cpp + structured-output protocol failed before a scoreable run.
- DeepSeek-R1-Distill-Qwen-1.5B completed the public screen but had **144/144 format failures**, which remain counted as 0 rather than being excluded.
- NQ and FEVER use frozen oracle-assisted development corpora marked `qualification_eligible=false`; they are diagnostic/development evidence, not official end-to-end reproductions.
- HotpotQA is the cleanest broader public A/G result in this panel.
- Negative cells are retained. ExactScope does **not** claim that every model/workload combination improves.
- The initial two-worker grounding run hit a real host OOM on the 16 GB qualification machine. Sealed cells were preserved and the remaining cells were attempted once in a fresh serial recovery. Recovery latency is **not** a product latency claim.

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

The current flagship evidence budget is 4 KiB because it outperformed 2 KiB in the measured HotpotQA screens while remaining small enough for constrained models.

---

## Runtime footprint and latency

The default v1 runtime package deliberately excludes benchmark-specific NQ provider data.

Current Linux x86-64 stable-package measurements for the v1 native path are approximately:

- default compressed SDK: **0.94 MB**;
- default unpacked files: **4.66 MB**;
- demonstration index: **1.6 KB**;
- static library: **4.62 MB**.

The default-install hard caps are 10,000,000 compressed bytes and 20,000,000 unpacked file bytes.

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

ExactScope does not own the inference engine, so llama.cpp can remain the model runtime. The repository includes a maintained llama.cpp grounding adapter for benchmark/integration work under [`adapters/llama-cpp`](adapters/llama-cpp).

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

ExactScope is relevant to developers working on **small LLM**, **local LLM**, **local AI**, **on-device AI**, **edge AI**, **embedded AI**, **AI grounding**, **LLM grounding**, **factual accuracy**, **hallucination reduction**, **RAG alternatives**, **lightweight RAG**, **offline AI**, **llama.cpp**, **deterministic AI**, **AI reliability**, **wearable AI**, and **smart-glasses AI**.

ExactScope is an **accuracy retrofit and provider-neutral grounding runtime for existing small, local, and on-device models**.

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

v1의 stable 배포 범위는 **Linux x86-64 native C ABI grounding package**입니다. 기본 패키지는 약 0.94MB 압축 크기이며 대형 NQ qualification index는 제품 기본 설치물이 아니라 별도 benchmark/provider 데이터입니다.

ARM64·스마트글래스·워치 등은 중요한 설계 타깃이지만 실제 ARM64 기기에서 RAM·지연·전력·열 qualification은 아직 수행하지 않았으므로 stable 하드웨어 성능을 주장하지 않습니다.

처음 사용하려면 [Releases](https://github.com/ot4562-glitch/ExactScope/releases)의 `exactscope-grounding-1.0.0-x86_64-unknown-linux-gnu.tar.gz`를 받아 위의 [30-second native demo](#30-second-native-demo)를 실행하면 됩니다.
