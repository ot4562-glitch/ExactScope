<div align="center">

# ExactScope

### Keep your AI stack. Remove the waste. Compile ExactScope away.

**A tiny cold-path attachment for an AI product you already have: it borrows your RAG, harness, eval and runtime, applies only non-overlapping performance/cost optimizations, lowers the result to host-native settings, and ideally disappears from production.**

**Development status: v1.2 is under active development and research. The latest stable release remains v1.1.0.**

[Current v1.2 direction](docs/V1_2_ZERO_RUNTIME_PARASITE_DIRECTION.md) · [v1.2 alpha.1 result](docs/V1_2_ALPHA_1_RESULT.md) · [Attach module research](docs/V1_2_ATTACH_OPTIMIZATION_MODULE_RESEARCH.md) · [Research status](docs/V1_2_RESEARCH_PENDING.md) · [Releases](https://github.com/ot4562-glitch/ExactScope/releases)

[![Development](https://img.shields.io/badge/status-v1.2%20development-yellow.svg)](docs/V1_2_ZERO_RUNTIME_PARASITE_DIRECTION.md)
[![Release](https://img.shields.io/github/v/release/ot4562-glitch/ExactScope)](https://github.com/ot4562-glitch/ExactScope/releases)
[![License](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue.svg)](#license)

</div>

---

## What is ExactScope?

Most AI stacks already have retrieval, prompt tools, evaluation and a runtime. ExactScope does **not** want to replace them.

It asks one smaller question:

> **Can this existing stack use a smaller/cheaper configuration without losing the behavior we require?**

If yes, ExactScope writes the answer as a tiny host-native profile/config and gets out of the way.

Elementary-school version:

> **Other programs teach and test the AI. ExactScope picks the cheapest good way, writes it on a tiny note, and leaves.**

## The target architecture

```text
COLD / DEVELOPMENT

existing RAG results ---------\
Promptfoo / DSPy candidates ---+--> existing eval results
runtime capability facts ------/          |
                                          v
                                  ExactScope compiler
                                          |
                              minimum sufficient setting
                                          |
                              host-native config / data
                                          v
                                        done

HOT / PRODUCTION

user request
    |
    v
existing app / RAG / runtime
    |
    +-- ordinary host-native config generated earlier
    |
    v
existing model
```

The preferred v1.2 deployment has:

- no ExactScope daemon;
- no ExactScope inference server;
- no ExactScope vector database or second index;
- no ExactScope eval engine;
- no ExactScope model call;
- no ExactScope hot-path dependency when the host can consume the lowering directly.

## What ExactScope deliberately does not compete with

ExactScope is not trying to become another:

- RAG framework or vector database;
- prompt optimizer;
- benchmark/eval harness;
- agent framework or model router;
- inference runtime;
- tokenizer/chat-template stack;
- grammar/structured-output engine;
- cache, scheduler or telemetry platform.

Promptfoo, DSPy/GEPA, lm-eval, Inspect, NeMo, LlamaIndex, llama.cpp, ExecuTorch, LiteRT and similar projects are potential **hosts or suppliers**, not targets to clone.

If they add a feature we used to own, the preferred response is often to **delete our copy**.

## How ExactScope attaches

The product target is not a permanent middleware layer. ExactScope should attach to the **configuration and measurement surface** of an AI product that already works:

```text
existing AI
  + its RAG / prompt system / eval / runtime
                 |
                 +-- measurements + existing knobs/assets
                 v
          ExactScope cold modules
                 |
        only non-overlapping choices
                 |
                 v
        native config / patch / IDs
                 |
                 v
            existing AI
```

The current research surface is deliberately narrow:

- **minimum-sufficient configuration selector (leading hypothesis)** — first evidence is prompt/few-shot minimization; choose only among externally measured existing candidates under a predeclared quality floor;
- **external-result importer (supporting plumbing)** — read only the measurements needed by the selector; never become an eval harness;
- **semantic lowering verification (export property, not a product module)** — return `SUPPORTED`, `LOSSY`, or `UNSUPPORTED`; never hide `UNSUPPORTED` behind a growing compatibility runtime;
- **output-surface selection** — next falsification target; if ordinary host config already solves it, delete it as a separate module;
- **context-budget and runtime-cost selection** — deferred until a real host exposes a concrete selection gap.

Every surviving module has to show a measurable quality/cost benefit over the unchanged host **and** less integration burden than the host's native tooling or a small script. If the host already solves the same optimization well, the ExactScope piece should disappear.

## Current v1.2 research rule

> **Remove one more thing.**

Every candidate change is tested in this order:

1. Can the host already do it?
2. Can ExactScope delete its implementation?
3. Can the remaining semantic delta become plain host-native config/data?
4. Does the required behavior survive?
5. If yes, keep the deletion. If not, restore only the smallest missing piece.

The active target is **P-2 zero-runtime lowering**: ExactScope exists during development, emits a host-native artifact, and contributes zero execution code at runtime.

Latest attach research has pushed one frozen MMLU-Pro profile from **18,114 B -> 1,389 B -> 708 B** of counted ExactScope semantic delta while preserving 96/96 request parity and zero hot-path ExactScope code. More importantly, Promptfoo `0.123.0` then represented the remaining frozen chat-message and structured-output semantics natively at **96/96 + 96/96 semantic parity**, so ExactScope will **not** build a Promptfoo-specific executor for that job.

A first data-only Promptfoo result importer also consumed 96 externally produced rows with zero Promptfoo/model invocations and correctly returned **`NO_SELECTION_EVIDENCE`** because the artifact had only one candidate. ExactScope is not allowed to manufacture an optimization decision when comparative evidence is missing.

See [the canonical v1.2 direction](docs/V1_2_ZERO_RUNTIME_PARASITE_DIRECTION.md) and the [attach optimization module program](docs/V1_2_ATTACH_OPTIMIZATION_MODULE_RESEARCH.md).

## Why this direction exists

Earlier parasite/attach research already showed that large pieces of ExactScope could be removed:

- retrieval/index ownership could be replaced by host-ranked hits plus tiny optional lexical statistics;
- host document-frequency hints reproduced measured projection behavior with payloads on the order of tens to low hundreds of bytes per query;
- detached semantic surfaces were measured around **4.2 KB (P0)**, **8.3 KB (P1)** and **12.8 KB (P2)** before distribution substrate;
- a historical Qwen/Hotpot development screen improved quality while using fewer prompt tokens after removing repeated policy text and borrowing host capabilities.

Those are research signals, not universal performance claims. The important lesson is architectural: **useful behavior sometimes survives after ExactScope owns less.**

## Frozen v1.2 alpha.1

`v1.2.0-alpha.1` remains frozen as an engineering checkpoint. It is not rewritten to fit the new zero-runtime direction.

On its 42-item / 21-document engineering study:

| Arm | Mean F1 | Critical-claim completeness | Annotated support capture |
| --- | ---: | ---: | ---: |
| Ordinary whole-chunk RAG | 0.2651 | 0.1488 | 0.2432 |
| **v1.2 alpha.1** | **0.2800** | **0.1944** | **0.7027** |

The ordinary-RAG F1 delta was **+1.49 pp**, but its paired confidence interval crossed zero, so it is **not** claimed as a statistically established RAG win.

The next alpha is allowed to contain **less ExactScope** than alpha.1.

Details: [V1_2_ALPHA_1_RESULT.md](docs/V1_2_ALPHA_1_RESULT.md).

## Research evidence that supports minimum-sufficient profiles

Fresh pilot work found that fixed public harness recipes were not universally cheapest for small local models:

- MMLU-Pro / Qwen3.5 0.8B: selected 1-shot matched the 5-shot reference at **20.83% vs 20.83%** on untouched confirmation while using **54.47% fewer input tokens**.
- GSM8K / Qwen3.5 0.8B: selected 4-shot observed **32.29% vs 26.04%** for the pinned 8-shot reference while using **46.37% fewer input tokens**; the quality-superiority interval still crossed zero.
- ARC-Challenge produced a useful negative result: a development-selected cheaper profile failed the frozen confirmation gate and was **not promoted**.
- IFEval produced another abstention result: no non-reference wrapper passed the frozen development safety/uncertainty gate, so the reference was retained and confirmation was left sealed.

These studies justify the **selection discipline**, not a new harness product. ExactScope should consume measurements from existing harnesses whenever possible rather than own them.

## Who is this for?

The best fit is a team that already has an AI stack but cannot casually replace its model/runtime/device:

- embedded or edge products;
- offline/on-prem systems;
- OEM devices with pinned local models;
- constrained CPU/RAM/context deployments;
- systems where a model/runtime change is expensive but configuration changes are cheap.

The pitch is intentionally narrow:

> **Keep your stack. Keep your model. Let ExactScope remove unnecessary execution cost and then compile itself away.**

## Stable legacy surface

The current released native grounding C ABI/XSGI path remains available as a stable earlier-generation software surface. It is retained for compatibility; it is **not** the v1.2 product identity.

Native build:

```bash
cargo build -p exactscope-cabi --release --features standalone-staticlib
cargo test -p exactscope-grounding
cargo clippy -p exactscope-grounding --all-targets -- -D warnings
```

Native quickstart: [docs/GROUNDING_NATIVE_QUICKSTART.md](docs/GROUNDING_NATIVE_QUICKSTART.md).

## v1.2 release proof we want

Before calling the new direction successful, ExactScope should demonstrate:

1. a real **P-2 zero-runtime lowering**;
2. deterministic host-native request/config parity where parity is expected;
3. zero ExactScope production process/model/retrieval/eval dependency in that mode;
4. at least one honest negative case where deleting a component is rejected;
5. a second host/runtime integration without turning ExactScope into an adapter framework;
6. broad 20-model / well-known benchmark evidence only **after** the minimal product boundary is frozen.

## Documentation

Start here:

- [Current v1.2 zero-runtime direction](docs/V1_2_ZERO_RUNTIME_PARASITE_DIRECTION.md)
- [Documentation map](docs/README.md)
- [v1.2 competitor code teardown](docs/V1_2_COMPETITOR_CODE_TEARDOWN.md)
- [v1.2 market / AI-stack research](docs/V1_2_MARKET_HARNESS_AND_AI_STACK_RESEARCH.md)
- [v1.2 research status](docs/V1_2_RESEARCH_PENDING.md)
- [Historical parasite/attach research](docs/V1_1_PARASITE_ATTACH_PROFILE.md)

Historical preregistrations, results and reviews are preserved under their original identities. They are evidence, not the current product definition.

## Repository map

```text
benchmarks/   research protocols, frozen studies, scorers
crates/       retained native implementation
adapters/     integration/reference experiments
docs/         product direction + research evidence
spec/         retained contracts and schemas
tools/        cold compilers, verifiers, publication tooling
target/       local/generated research artifacts
```

## Design rule

```text
Borrow > wrap.
Delete > duplicate.
Compile > stay resident.
Preserve behavior > add features.
```

## License

ExactScope is dual-licensed under:

- MIT License
- Apache License 2.0

See `LICENSE-MIT` and `LICENSE-APACHE`.
