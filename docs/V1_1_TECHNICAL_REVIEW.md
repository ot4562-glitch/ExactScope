# ExactScope v1.1 — technical review packet

Status: **v1.1.0 software/architecture release; stable support is limited to the Linux x86-64 native grounding C ABI/XSGI path; new qualification/control-plane and host-integration surfaces are experimental/reference; enterprise qualification is not claimed**

Updated: **2026-09-13**

This page is the shortest path for an external systems/ML-infrastructure reviewer who wants to understand what ExactScope v1.1 actually is, what has been implemented, what the evidence says, and where the claims stop.

## 1. Ninety-second thesis

ExactScope is exploring a control layer **around an AI stack the host already owns**.

The host keeps retrieval execution and authorization, model weights, tokenizer/chat template, inference, scheduling, batching, cache, constrained/speculative decoding, accelerators, tools, fallback, deployment and rollback.

ExactScope owns a smaller semantic/qualification boundary:

```text
Workload Contract + Host Capability Manifest + Semantic Policy
                         |
                         v
             restricted policy compiler
                         |
                         v
              Candidate Execution Policy
                         |
              independent qualification
                         v
              Qualification Attestation
                         |
                         v
              Qualified Execution Profile
                         |
              admit -> host execution -> finalize
                         |
                         v
                  Execution Receipt
```

The core design claim is not "we built another inference runtime" and not "RAG always improves a model." It is:

> **Compile workload obligations into a small immutable execution policy, qualify that exact policy against exact host identities, and fail closed when the policy, evidence, host or qualification is stale or mismatched.**

The long-term north star is a **Qualified AI Execution Control Plane**. The current commercial/research slice is narrower: a **Qualification / Configuration Optimizer** product hypothesis with semantic enforcement; demonstrated automatic optimization or economic advantage is not claimed yet. The phrase **Semantic Execution Policy Compiler** describes the implemented source-to-artifact lowering, but a broad new product category is not claimed as earned yet.

**Release stability boundary.** In v1.1.0 the existing Linux x86-64 native grounding C ABI/XSGI path is the stable supported software surface. The qualification/control-plane artifacts and Python workflows, enterprise DocQA machinery, host-attached semantic integration, Bridge backends and conformance demos are experimental/reference surfaces. Shipping them in the tagged source does not make their research efficacy or integration contracts stable APIs.

## 2. What is implemented now

The reference implementation already has concrete artifact and guard semantics rather than a slide-only architecture:

- restricted `Workload Contract` and `Host Capability Manifest` schemas;
- deterministic lowering to an immutable `Candidate Execution Policy`;
- separate `Qualification Attestation` bound to the exact candidate/workload/host digests;
- `Qualified Execution Profile` as a qualified pair rather than a mutable all-in-one config;
- request-bound admission receipts that bind evidence, rendered request and execution settings;
- mandatory finalization against the retained admission receipt and current host checks;
- fail-closed rejection on stale/mismatched profile, workload, host, evidence or receipt identity;
- explicit drift/requalification boundaries instead of silently carrying old scores forward;
- zero/one normal answer-generation call in the current grounding path;
- no second judge model, hidden repair loop, mandatory agent loop, mandatory embedding model or large index.

- Reference code: [`tools/qualified_execution.py`](../tools/qualified_execution.py)
- Schemas: [`spec/schemas/`](../spec/schemas/)
- North-star architecture: [`V1_1_ULTIMATE_PRODUCT_ARCHITECTURE.md`](V1_1_ULTIMATE_PRODUCT_ARCHITECTURE.md)

## 3. Frozen public-development evidence

The final public panel was executed **after** NQ and Hotpot attach policies were frozen. Here **A means the same model answering without attached evidence; G means that same model under the frozen ExactScope evidence/answer-contract path**. Each workload contains 64 questions. All 40 serving cells were attempted before scoring began; each task mean uses the 16/20 model identities with valid paired outputs, while four protocol-incompatible identities remain N/A. There was no quality retry, hidden repair or result-driven policy reselection.

| Workload | Questions | Valid model pairs | Mean F1 A | Mean F1 G | Mean A→G | Improved / tied / regressed |
|---|---:|---:|---:|---:|---:|---:|
| Natural Questions, fresh post-freeze64 | 64 | 16 / 20 | 12.44% | **21.68%** | **+9.24 pp** | 14 / 0 / 2 |
| HotpotQA, host-owned LlamaIndex BM25 + frozen H1 stability64 | 64 | 16 / 20 | 11.63% | **31.42%** | **+19.79 pp** | 15 / 0 / 1 |

The Hotpot headline is **model-only A → H1 G**. It does not measure ordinary-RAG → H1 across the 20-model panel and therefore does not establish H1's incremental benefit over ordinary RAG across models.

Across all 32 valid model-task pairs, the equal-weight descriptive mean uplift is **+14.52 pp**. Four model identities are protocol N/A on both workloads and remain N/A instead of being converted to zero. Negative cells are also retained, including SmolLM2 360M on NQ and Ministral 3B on both workloads.

For Qwen3.5 0.8B, the separately predeclared Hotpot stability64 three-arm checkpoint observed:

```text
model-only A                   7.82% F1
ordinary LlamaIndex RAG       35.04% F1
frozen ExactScope H1          40.70% F1
H1 - ordinary RAG             +5.66 pp F1 / +7.81 pp EM
paired bootstrap F1 95% CI    -4.69 pp .. +16.25 pp
```

The interval crosses zero, so this is **not** presented as a powered superiority result.

- Tracked evidence: [`benchmarks/v1.1-final-public-evidence.json`](../benchmarks/v1.1-final-public-evidence.json)
- Machine verifier: [`tools/verify_v11_public_evidence.py`](../tools/verify_v11_public_evidence.py)
- Original local panel results SHA-256: `69e91468842d9f7ac077547b80fe798a758814068a858d09eda704b00a8c34f8`
- Original frozen panel preregistration SHA-256: `506f0f4305e9c02a90da54bbf23113b8e4a9c0cd499d583dea42d354c51a3dee`

### Long-document transfer check: Kubernetes Operations proxy

A later frozen development32 proxy used official Kubernetes operational documentation with host-owned LlamaIndex BM25 retrieval. It did **not** reproduce the Hotpot/NQ shaping story: ordinary RAG primary utility was **28.51%**, while the initial ExactScope G path was **17.51%**, for **G−R = −10.99 pp** with paired-bootstrap 95% interval **−22.76 pp to −0.48 pp**. The preregistered −2 pp quality margin failed.

Exactly one bounded diagnostic round was allowed. C1, C2 and RAW2560 were respectively **−4.42 pp**, **−7.06 pp** and **−4.80 pp** versus R. All failed the frozen quality margin; `selected_arm=null`; untouched validation32 was not served; no second tuning round is allowed. The observed byte/token reductions therefore do **not** establish economic advantage. Invalidated r1/r2/r3 execution identities are retained with their source-drift/startup/serialization failure provenance rather than hidden.

Full result: [`V1_1_PUBLIC_PROXY_K8S_RESULT.md`](V1_1_PUBLIC_PROXY_K8S_RESULT.md).

## 4. Ten-minute reviewer path

From a source checkout with Python dependencies installed:

```bash
# See the artifact/guard lifecycle and fail-closed drift behavior in one command.
# The command labels its fabricated attestation as CONFORMANCE_DEMO_ONLY.
python3 tools/demo_qualified_execution.py

# Recompute every tracked public-panel aggregate and A->G delta.
python3 tools/verify_v11_public_evidence.py

# Exercise compiler/profile/admission/finalization/drift fail-closed semantics.
python3 -m unittest tools.test_qualified_execution

# Exercise the common delivery contract and runtime adapters.
python3 -m unittest \
  tools.test_exactscope_bridge \
  tools.test_bridge_capability_record \
  tools.test_bridge_compiled_profile \
  tools.test_bridge_context_fit \
  tools.test_bridge_finalizer \
  tools.test_bridge_ranked_hits \
  tools.test_ort_genai_bridge \
  tools.test_litert_lm_bridge

# Repository-wide semantic/design and publication-boundary checks.
python3 tools/validate_design.py
python3 tools/audit_publication.py
```

The public evidence verifier does **not** need model files or local `target/` artifacts. It recomputes the tracked snapshot and checks that its 20 model identities match the frozen model inventory.

## 5. Runtime portability evidence

The Bridge is intentionally small: the same semantic `complete | generate` delivery is mapped to structurally different host runtimes without moving runtime ownership into ExactScope. The evidence level is reported separately per runtime rather than collapsed into a generic compatibility claim.

| Runtime | Evidence currently available | What ExactScope does **not** own |
|---|---|---|
| Microsoft ONNX Runtime GenAI 0.15.2 | real local generation smoke; real ExactScope grounded delivery reached ORT; strict post-validation; current C++ header compile | tokenizer/template, generator/search state, KV state, execution providers |
| PyTorch ExecuTorch current `IRunner` | current upstream header compile + executable fake-runner contract smoke | runner/model loading, prompt rendering, `IRunner::generate`, token streaming, constrained decoding |
| Google LiteRT-LM 0.17.0 | real Engine/Conversation generation with official fixture; ExactScope ordinary-knowledge delivery; grounded fixture exposed real context-capacity limits | engine/conversation/template, decoding, backend selection |

A real `.pte` + tokenizer ExecuTorch model run is still pending. The repository therefore does **not** claim real-model ExecuTorch compatibility yet.

- Bridge: [`adapters/bridge/`](../adapters/bridge/)
- Integration findings: [`V1_1_INTEGRATION_FEEDBACK.md`](V1_1_INTEGRATION_FEEDBACK.md)

## 6. Why the architecture is nontrivial

### Immutable policy is not qualification

A compiled candidate cannot declare itself safe. Qualification is represented by a separate artifact bound to the exact candidate/workload/host digests, but **artifact separation alone does not make the evaluation independent**: independence comes from the frozen evidence, scorer/analysis identities and accountable qualification authority/process. A profile can only be emitted from the qualified pair. The executable reviewer demo intentionally fabricates its attestation as `CONFORMANCE_DEMO_ONLY` and is not qualification evidence.

### Qualification is not request-time truth proof

The design distinguishes deterministic runtime-verifiable obligations from empirical properties such as factual correctness or customer economics. `Accept` means the implemented deterministic checks passed; it does not pretend the runtime proved semantic truth.

### Host ownership is a hard boundary

ExactScope deliberately does not absorb the inference engine, retriever, tokenizer, scheduler, cache or deployment system. That keeps the policy artifact portable and makes capability/identity drift explicit. **Fail-closed enforcement assumes a trusted host boundary that authenticates/reports the current identities and does not bypass admission/finalization.** Digest binding proves consistency with those supplied identities; it does not prove that an untrusted host told the truth.

### Failure is a first-class product result

`ReferenceOnly`, `NoQualifiedCandidate`, stale identity, unsupported obligation, unsupported runtime surface and failed finalization are valid outcomes. The final public panel likewise retains protocol N/A and regressions rather than filtering them out.

### Requalification scope is explicit

Behavior-affecting identities are prospectively classified. Known targeted changes may use a bounded requalification path only when authorized in advance; unknown changes fail closed to full requalification.

## 7. Enterprise qualification chain

The enterprise document-QA confirmatory machinery is implemented as a fail-closed reference chain:

```text
preregistration
  -> Study Contract
  -> no-inference readiness receipt
  -> three-arm observations
  -> deterministic run sealing
  -> frozen offline scoring
  -> frozen paired quality/economic analysis
  -> workload-owner decision
  -> canonical evaluation package
  -> standalone Qualification Attestation
  -> Qualified Execution Profile constructor
```

It binds the exact candidate/workload/host, gold-free confirmatory question identity, runner/readiness/scorer/analysis/decision source identities, ordinary alternative and fixed economic counters before outcomes.

What is **not** available yet is the thing that cannot be faked responsibly: a real authorized enterprise workload, accountable owner/evaluator, production retrieval/index identity, owner-approved competence gates and real economic coefficients/counters. Until those exist, no real enterprise confirmatory run or customer qualification is claimed.

Plan and implementation map: [`V1_1_ENTERPRISE_DOCQA_PLAN.md`](V1_1_ENTERPRISE_DOCQA_PLAN.md)

## 8. What an external reviewer should challenge

The most useful review is not "does the README sound impressive?" It is whether these boundaries survive contact with a serious host stack:

1. Is the Workload Contract restricted enough to remain auditable, but expressive enough for a real owner?
2. Are host capabilities and lowerings bound strongly enough that a nominal capability cannot masquerade as an implemented check?
3. Does admission/finalization sit at the correct trust boundary for runtimes that can change model/retriever/template identities independently?
4. Is the candidate/attestation/profile split sufficient for provider-observable hosts where exact binary identity is unavailable?
5. Can requalification stay materially cheaper than cold qualification without silently weakening evidence integrity?
6. Does the control-plane layer remain smaller than the integration complexity it is meant to remove?

Those are the questions that decide whether the north-star category is earned.

## 9. Claim boundary

The current repository supports these narrow statements:

- the qualified-execution artifact/guard semantics are implemented and tested as a reference system;
- a frozen 20-model public-development A/G panel shows positive mean uplift on NQ and Hotpot while preserving regressions and N/A;
- one Qwen Hotpot stability64 checkpoint directionally beats ordinary LlamaIndex RAG, with uncertainty that still crosses zero;
- the Kubernetes Operations proxy is a negative transfer result: the initial G path missed ordinary RAG by 10.99 pp, every bounded diagnostic candidate failed the frozen quality margin, and no candidate was selected;
- the same narrow delivery contract has backend-specific evidence across ORT GenAI, ExecuTorch's current public runner surface, and LiteRT-LM at the explicitly different evidence levels stated above;
- the enterprise qualification pipeline is implemented as infrastructure but has not yet been populated with real owner-bound enterprise evidence;
- v1.1.0 may therefore be described as a software/architecture release with a stable native grounding core and experimental/reference new surfaces, **not** as a qualified efficacy upgrade.

It does **not** support claims of universal v1.1 superiority over v1.0, general ordinary-RAG superiority, cross-model H1 superiority over ordinary RAG, enterprise qualification, production readiness, economic advantage, or a proven new market category.
