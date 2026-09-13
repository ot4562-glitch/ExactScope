# ExactScope v1.1 — Kubernetes Operations public proxy result

Status: **development result complete; no candidate selected; public-proxy tuning closed**

Updated: **2026-09-13**

## Result in one sentence

On the frozen Kubernetes Operations development32 workload with host-owned LlamaIndex BM25 retrieval, the initial ExactScope `precision-context-v5` path and the single allowed bounded long-document diagnosis all failed the prospectively declared quality margin against ordinary RAG. No v1.1 proxy candidate was selected and untouched validation32 is not authorized.

This is a negative development result. It is not enterprise qualification and it is not evidence that ExactScope universally underperforms RAG. It does show that the current public-proxy shaping/configuration candidates do not justify a product-value claim on this workload.

## Frozen source and host

- source: official `kubernetes/website`
- commit: `ce98a43f24257385a9766003a6dadc95e962dc63`
- license: CC-BY-4.0
- domain: Pod operations and container configuration
- development items: 32
- host retrieval: LlamaIndex `BM25Retriever`, top-k 12
- model: Qwen3.5 0.8B Q4_0
- runtime: llama.cpp b10797
- answer surface: `answer-object-v4` / `json-schema-v1`
- no quality retry, hidden repair, model judge or runner-visible gold

## Evidence-integrity closeout before scoring

Three preliminary execution identities were retained rather than silently repaired:

1. `three-arm-r1` completed serving but was invalidated before scoring when the runner source digest no longer matched its frozen protocol.
2. `three-arm-r2` failed during host startup before any model call because a Windows runtime was given WSL `/mnt/c/...` model paths.
3. `three-arm-r3` completed all 96 serving observations, but its frozen scorer failed before score publication because float utilities were routed through an integer/string-only canonical JSON writer.

None of those runs is evidence eligible. The deterministic output-serialization bug was fixed before a new source digest was frozen. `three-arm-r4` then reran all 32 × B/R/G serving observations from scratch under the new protocol and is the only evidence-eligible initial run.

## Initial development32 — evidence-eligible r4

| Arm | Primary utility | Answerable F1 | Evidence support | Mean input tokens | Mean evidence bytes | Unacceptable errors |
|---|---:|---:|---:|---:|---:|---:|
| B — model only | 11.36% | 16.53% | N/A | 101.1 | 0 | 10 |
| R — ordinary LlamaIndex RAG | **28.51%** | **41.46%** | 54.55% | 930.8 | 3072 | 10 |
| G — `precision-context-v5` 3 KiB/cap8 | 17.51% | 25.47% | 50.00% | 583.3 | 1587 | 10 |

Observed deltas:

- R − B: **+17.14 pp** primary utility.
- G − B: **+6.15 pp**.
- G − R: **−10.99 pp**.
- paired bootstrap G − R 95% interval: **−22.76 pp to −0.48 pp**.
- G reduced mean evidence bytes by **48.3%** and mean input tokens by **37.3%** versus R, but the predeclared −2 pp quality margin failed.

The initial candidate therefore failed the development publication shape.

## Single bounded long-document diagnosis

Before candidate serving, exactly three alternatives and one selection rule were frozen:

- `C1`: query-weighted contiguous sentence window from host rank-1, 3072 bytes.
- `C2`: contiguous windows from host ranks 1–2, deterministic shared 3072-byte budget.
- `RAW2560`: ordinary ranked raw context reduced to 2560 bytes.

Eligibility required zero format failures, unacceptable errors no worse than R, utility no worse than R by more than 2 pp, and at least one material quality/efficiency/safety advantage. If no candidate passed, no second policy-development round was allowed.

| Candidate | Primary utility | Delta vs R | Answerable F1 | Evidence support | Evidence reduction vs R | Selection eligible |
|---|---:|---:|---:|---:|---:|---|
| C1 | 24.08% | **−4.42 pp** | 35.03% | 68.18% | 0.69% | No |
| C2 | 21.45% | **−7.06 pp** | 31.20% | 59.09% | 0.76% | No |
| RAW2560 | 23.70% | **−4.80 pp** | 34.48% | 40.91% | 16.67% | No |

`selected_arm = null`. No candidate met the frozen −2 pp quality margin, so untouched validation32 is deliberately not served and no additional tuning round is allowed on this proxy.

## Interpretation

The result separates two claims that must not be conflated:

1. **The v1.1 execution/qualification architecture can be implemented, bound, verified and fail closed.** The repository has strong conformance evidence for that statement.
2. **The current v1.1 evidence-shaping/configuration candidate adds customer-value over a competent ordinary RAG path on long operational documents.** This Kubernetes proxy does **not** support that statement.

The negative result is useful. It shows that the Hotpot/NQ public-development policies do not automatically transfer to long operational documents, and that token/evidence reduction alone is not enough when answer utility drops materially.

## Release consequence

This result closes the Kubernetes public-proxy product-value branch without a pass. It therefore must not be used to market v1.1 as superior to ordinary RAG, enterprise-qualified, economically superior, or universally better than v1.0.

A v1.1 software release may still ship the implemented qualification/guard architecture, frozen public A/G evidence, runtime integration work and this negative proxy result if its release scope is explicitly architectural/research software rather than a customer-value qualification claim. Real owner-bound qualification remains a later evidence milestone rather than something that can be fabricated to rescue the release.
