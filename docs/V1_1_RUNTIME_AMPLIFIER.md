# ExactScope v1.1 Runtime Amplifier

Status: **historical amplifier/material research reference; not released; current v1.1 product work is narrowed to qualification/configuration optimization and competence-gated document-QA validation**

## Product thesis

ExactScope v1.1 is investigating a tiny, provider-neutral semantic layer that attaches around an existing LLM. It does not replace model weights and it does not compete with fine-tuning, LoRA, personalization, or a better base model. Those can all sit behind the same semantic boundary.

> **Make the model better without making the model bigger.**

That remains a research target, not a current universal claim. The later preregistered FEVER compiler-value study also stopped at `ReferenceOnly` before held-out: no cheaper frozen candidate matched the Reference's aggregate calibration success count. The current milestone is therefore different: establish **competent customer-like value and total economics** on bounded enterprise document QA with real host retrieval. A cheaper reference-preserving compiler branch is now conditional research rather than the product's gating premise. Small/local/on-device systems remain important longer-term targets and architecture constraints.

## Research mode: amplification first, lightweighting second

The historical 994,148-byte native archive and later unified standalone/host-attached checkpoints are useful packaging references, **not evidence that the global architecture optimum or final v1.1 shipping form has been found**. The current product boundary is native-free-first. Material experiments may still exceed any future release size/CPU/RAM/token envelope during causal discovery, but package minimization is not the current product gate.

The research sequence is now split into two tracks:

```text
product proof
  bounded enterprise document QA + real host retrieval
    -> establish competent Base / integrated-style configuration on development data
    -> freeze workload-owner quality + evidence + abstention + total-economic gates
    -> fresh independent integrated-style vs Base qualification
    -> optional cheaper-policy branch only if calibration admits P

material / compiler research
  interaction / phase-transition discovery
    -> small prospectively testable policy families
    -> no FEVER held-out rescue
    -> no cross-host/adaptive program until a useful source policy exists
```

Pareto analysis remains useful for **material research and architecture tradeoffs**. It is not the current product-selection claim. Reference-preserving cost reduction remains available as a conditional research objective when a competent workload and a useful candidate frontier exist.

The normative experiment charter is [`V1_1_EXPERIMENT_PROGRAM.md`](V1_1_EXPERIMENT_PROGRAM.md). External runtimes are used as pressure tests through the experimental [`../adapters/bridge/`](../adapters/bridge/) layer; integration friction is recorded in [`V1_1_INTEGRATION_FEEDBACK.md`](V1_1_INTEGRATION_FEEDBACK.md) before any core API change is considered.

## Product invariants and promotion constraints

These are product-identity constraints even when individual research modules are aggressive:

- no mandatory additional verifier/reasoner model in the intended product;
- no hidden request-time retry, reflection, or semantic repair loop;
- no mandatory embedding model, vector database, or learned reranker;
- no mandatory agent/tool loop;
- zero or one answer-generation call on the normal product path;
- provider-neutral host integration;
- local/offline operation remains possible;
- inference execution, KV management, scheduling and hardware acceleration remain host-runtime responsibilities;
- no expansion of the stable native C ABI merely to accommodate a backend-specific optimization;
- stable v1 native code keeps its existing `no_std`/allocation-free/`forbid(unsafe_code)` contract, but **v1.1 does not assume native code is a required default surface**;
- a v1.1 native kernel must earn its place through a Python-free-host requirement or measured bottleneck/integration advantage;
- a future release candidate must again satisfy its selected footprint/resource promotion gates after the winning research behavior is distilled.

A research ceiling may temporarily violate size or local-compute targets, but it must be explicitly labelled and removable. It may not quietly redefine a larger model, model cascade, heavyweight index, or external inference service as an ExactScope amplification win.

## Current reference execution architecture

v1.1 is deliberately split by **when a fact can be known**, not by adding defensive wrappers around every operation.

```text
                 COLD PATH — once per immutable identity

 profile / policy ── validate ──┐
                               │
 corpus / XSGI ─── validate ───┼──> GroundingSession
                               │         │
 answer contract ── compile ───┤         ├─ immutable CorpusSnapshot
                               │         ├─ CompiledAnswerSpec
 model/runtime ─── preflight ──┘         ├─ prepared prompt prefixes
                                         └─ capability identity/cache
                                                    │
                                                    v
                                          PreparedAmplifier
                                                    │
                 HOT PATH — once per question       │
                                                    v
 question ──> bounded retrieval ──> evidence policy/projection
                         │                      │
                         │                      └─ 512 / 1024 / 2048 B
                         │
                         ├─ authoritative scalar resolvable ──> 0 model calls
                         │
                         └─ generation still useful ─────────> 1 model call
                                                                  │
                                                          typed constrained answer
```

The important boundary is `GroundingSession.prepare(...) -> PreparedAmplifier`.
Long-lived hosts should prepare once and call `PreparedAmplifier.plan(...)` repeatedly.
`session.plan(...)` and `plan_question(...)` remain compatibility entrypoints, not the preferred hot path.

## Precision instead of hot-path armor

The redesign intentionally removes checks whose truth was already established before request traffic.
This is not equivalent to trusting unvalidated files or disabling memory safety.

### Cold path performs the expensive checks

`GroundingSession.open`:

- validates the grounding profile and its bound artifacts;
- fixes effective scope and runtime limits;
- binds provider state;
- hashes the immutable policy once.

`GroundingSession.bind_corpus`:

- canonical-validates the corpus once;
- compiles it to immutable `ValidatedIndex` state;
- records its digest;
- caches the resulting `CorpusSnapshot`.

`GroundingSession.prepare`:

- validates stable retrieval/projection configuration;
- canonicalizes and compiles typed answer contracts once, with a bounded 64-entry per-session compile cache;
- prebuilds model system prefixes with and without evidence policy;
- precomputes stable prefix-cache identities;
- binds the corpus snapshot directly into the executable plan.

### Hot path keeps only checks that depend on the request

`PreparedAmplifier.plan` does **not** reopen or stat profile/corpus files, rebuild the model prefix, recompile the answer contract, or recompute the model-surface identity.
It still enforces values that cannot be proven ahead of time:

- question/retrieval-query byte bounds;
- request-specific evidence/item/context bounds;
- explicit unresolved/ambiguous/conflict/unavailable states;
- strict final model-output parsing.

This is the safety model: prove stable invariants once, keep validated bundle state behind the session boundary, and make the normal prepared request path independent of later artifact-file changes. Python callers are still expected not to mutate private session internals directly; this is an execution contract, not a language sandbox.
Opening a new session is the explicit operation that adopts changed artifacts.

## Amplification mechanisms

### 1. Compiled typed answer contracts

The runtime supports small generic output domains:

- `text`;
- `choice`;
- `boolean`;
- `integer`;
- `number`.

Integer/number contracts may include inclusive bounds. A `CompiledAnswerSpec` contains the canonical spec, digest, JSON Schema, GBNF, prompt instruction, and deterministic validator. Passing an already compiled object is an O(1) identity reuse rather than recompilation.

The llama.cpp adapter maps the same prepared contract onto the pre-negotiated backend surface. Invalid output is rejected; it is not repaired through another model call.

### 2. Precision evidence projection

The default local-corpus renderer is `precision-context-v5`. Earlier v2-v4 projectors remain explicit compatibility/experiment paths.
It combines:

1. deterministic lexical retrieval with bounded candidate overfetch;
2. exact full-body duplicate elimination while preserving distinct titles when those titles carry different query terms;
3. normalized exact-span suppression for repeated context;
4. directional contiguous context: anchor + successor for a first-sentence anchor, otherwise predecessor + anchor;
5. complete-anchor fallback when a two-sentence unit does not fit, never sentence truncation;
6. conservative evidence budgeting at 512, 1024, or 2048 bytes, with tier promotion only when no complete useful unit fits the initially selected tier;
7. a final `model_items` cap after deduplication/projection rather than before candidate selection.

Weak/ambiguous retrieval keeps the larger budget. Strongly separated, well-covered retrieval can shrink it. The diversity logic is exact lexical/content identity, not semantic similarity, so it does not add an embedding model, learned reranker, hidden similarity threshold, or extra inference call.

### 3. Zero-call completion

When authoritative state resolves to a single compatible scalar and the request contract agrees, ExactScope can return it directly.
Supported typed cases include text, boolean, integer, and finite number where type/unit/bounds are unambiguous.

That path costs:

- model calls: **0**;
- model tokens: **0**;
- model hallucination opportunity: **0**.

Finite classification choices deliberately remain model-routed unless the application has already supplied deterministic semantics for resolving them.

### 4. Identity-bound capability cache

Surface/contract preflight is tied to the host-supplied model/runtime/template identity plus ExactScope model-surface and policy digests.
A matching record skips repeated calibration. Changed identity maps to a different key or fails cold-path validation.

The capability cache is an optimization of repeated compatibility discovery, not a relaxation of compatibility requirements.

Constraint compilation deliberately uses a different cache policy. JSON Schema/GBNF generation is microsecond-scale CPU work, so persisting compiled constraints to disk would add more product weight than it removes. `GroundingSession` instead keeps a bounded 64-entry canonical in-memory cache and `PreparedAmplifier` carries the selected compiled object directly on the hot path.

### 5. Prepared stable prompt-prefix identity

`PreparedAmplifier` precomputes stable prefix identities for both:

- ordinary-knowledge requests without grounding policy in the prompt;
- evidence-bearing requests with the grounding policy.

The host may map those identities onto backend-native prefix/KV caching.
ExactScope does **not** automatically enable backend prompt cache: it remains `host-owned-parity-gated` because a backend optimization is accepted only after the relevant model/runtime combination demonstrates output-parity under the product's determinism requirements.

## Reference-adapter boundary

The llama.cpp adapter is intentionally thin.
It owns:

- literal-loopback HTTP transport;
- one-time output-surface/answer-contract preflight;
- identity-bound capability-cache persistence;
- model request/strict response parsing;
- CLI wiring.

It does **not** own retrieval, evidence projection, zero-call decisions, artifact lifetime, or session planning. Those belong to `tools/grounding_engine.py`.

This prevents backend-specific transport concerns from turning the product core into a collection of adapter patches.

### Bridge pressure-test boundary

The experimental [`../adapters/bridge/`](../adapters/bridge/) layer generalizes that separation for runtimes that do not look like llama.cpp. Its first real target is Microsoft ONNX Runtime GenAI. Bridge receives only one already-decided `complete | generate` delivery semantic: deterministic replies stop before the inference runtime, while generation-required cases pass ExactScope-approved semantic messages to the host tokenizer/generator and return raw generation to ExactScope's strict finalizer.

The ORT integration does **not** copy retrieval, authority, coverage, freshness, conflict/ambiguity, evidence projection, or host-completion logic. Current v1.1-dev planner details are confined to one churn adapter. Integration friction discovered this way is logged in [`V1_1_INTEGRATION_FEEDBACK.md`](V1_1_INTEGRATION_FEEDBACK.md) and does not authorize an immediate core change.

This pressure test matters strategically: Microsoft explicitly owns tokenization/pre-processing, ONNX inference, search/sampling and KV management in ORT GenAI, while Meta ExecuTorch and Google LiteRT-LM own analogous device/runtime concerns. ExactScope should remain the small semantic/delivery amplifier above those changing engines rather than freeze itself into one vendor execution API.

References: <https://onnxruntime.ai/docs/genai/>, <https://docs.pytorch.org/executorch/stable/llm/getting-started.html>, <https://ai.google.dev/gemma/docs/run>.

## Engineering result of the prepared-path experiment

A local host-side microbenchmark on the development machine measured planning/validation overhead only; these numbers are **not model-inference latency and are not release benchmark claims**.

| Host path | Median |
|---|---:|
| New session + profile/corpus validation per request | ~682 ms |
| Warm session, corpus path lookup/re-prepare | ~303 us |
| Warm session, bound snapshot but re-prepare | ~192 us |
| **PreparedAmplifier hot path** | **~174 us** |

The same diagnostic measured typed answer-contract preparation at about **5.64 us** from a raw spec versus **0.11 us** when reusing `CompiledAnswerSpec` (~51x difference for that operation).
Cold-per-request versus prepared planning was roughly **3,913x** different in that deliberately extreme comparison.

The useful conclusion is not the multiplier itself: production hosts should never open a full session per question. The result validates the architecture decision to move stable validation/compilation out of request execution.

## What stays outside the intended product core

The research program may inspect adjacent techniques, but the intended ExactScope product does not become:

- a domain-specific BookScope/MathScope family of separate runtimes;
- a fine-tuning, LoRA, or user-learning orchestrator;
- an external CAS/solver dependency bundle;
- a mandatory embedding/reranker model or vector database;
- a mandatory second-model verifier/cascade;
- a hidden self-reflection/retry/semantic-repair loop;
- an owner of speculative decoding, KV paging, batching or accelerator scheduling;
- a broad agent/tool orchestration framework.

Backend-native caching, structured decoding and **no-second-model** speculation may nevertheless be mounted as detached experiments because the host runtime already owns them. For example, ONNX Runtime GenAI currently documents n-gram speculative decoding for input-grounded/repetitive generation without a draft model. ExactScope may test whether compact literal evidence increases its acceptance/speed, but the mechanism remains ORT-owned and is promoted only after parity and cost measurement. Reference: <https://github.com/microsoft/onnxruntime-genai/blob/main/docs/SpeculativeDecoding.md>.

## Qualification rule

The old v1.1 matrix was intentionally stopped when this redesign was authorized. Its interrupted cells are not release evidence, and later material screens remain causal research rather than automatic product policy.

The first fresh Harness Distillation transfer completed and **failed qualification**. The later preregistered 120/600 FEVER Stage 1 then stopped prospectively at calibration with **`ReferenceOnly`**, `P = null`, and `T = F`. All 1,200 calibration observations completed, but no cheaper frozen policy matched the Reference's aggregate success count. The 600-item held-out was not scored and is retired from revised-rule confirmatory inference.

That outcome closes the current FEVER compiler-value branch. It demonstrates correct stop/qualification discipline, not successful cost compilation. The frozen 15% cheaper-reference gate is not relaxed to rescue the result.

The next qualification stage is a **new competence-gated bounded enterprise document-QA study with real host retrieval**. Before confirmatory scoring it must freeze the document/question population, leakage grouping, Base and integrated-style configurations, workload-owner competence rules, evidence/citation and abstention semantics, unacceptable-error definition, model/runtime/retrieval identities, timing/load protocol, total-economic model, adjudication/scorer and uncertainty analysis. The primary product question is integrated-style versus Base. Any cheaper reference-preserving `P` branch is separately preregistered and stops if calibration admits no `P`.

Release qualification must report the selected artifact's actual quality, evidence support, abstention/error behavior, compatibility, model-call/token/latency/resource/integration/refresh costs and the **actual chosen shipping form**; it must not inherit the historical native package gate or FEVER service-time economics.

No release tag, release PR, or upstream-runtime integration PR should be created merely to accelerate the research timeline. Publication follows a stable boundary and reproducible evidence.
