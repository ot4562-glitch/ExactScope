# ExactScope v1.1 — A/G effect showcase and real-host attach checkpoint

Status: **final public-development robustness panel complete: frozen NQ 3K/cap8 and real-host H1 show positive mean A→G uplift across 16 valid models, with explicit regressions/N/A retained; public tuning is closed, but enterprise/customer qualification is still NOT authorized without a real owner-bound workload, frozen economics/statistics, readiness, Astra review, and owner approval**
Updated: **2026-09-13**

This document keeps the user-visible effect size simple: **how many percentage points does the same model gain after context/grounding is attached?** It also records the harder product question: **does ExactScope add value over an ordinary deployable RAG path, not merely over model-only A?**

## 1. Fresh v1.1 A/G showcase

Artifact: `target/v11-ag-showcase-20260913-r1/`

Model/runtime are fixed across A and G:

- model: Qwen3.5 0.8B Q4;
- runtime: llama.cpp `b10797`;
- output contract: `answer-object-v4` / `json-schema-v1`;
- no quality retry/repair loop;
- all serving outputs were completed before gold scoring;
- 32 fresh untouched groups per workload, selected before gold was opened;
- these public workloads remain development evidence, not enterprise qualification.

| Fresh workload | A F1 | G F1 | **A → G** | A EM | G EM | **A → G** |
|---|---:|---:|---:|---:|---:|---:|
| Natural Questions mirror · fresh32 | 18.64% | **22.31%** | **+3.67 pp** | 9.38% | **15.63%** | **+6.25 pp** |
| HotpotQA · fresh32 | 18.71% | **30.25%** | **+11.54 pp** | 15.63% | **18.75%** | **+3.13 pp** |
| **Two-workload unweighted descriptive mean** | **18.67%** | **26.28%** | **+7.61 pp** | **12.50%** | **17.19%** | **+4.69 pp** |

The mean row is only a compact descriptive summary across these two 32-item development screens. It is **not** a powered population estimate or qualification statistic.

### Fixed policies used

- NQ: `precision-context-v5`, 3072 B, cap8;
- Hotpot: `multihop-coverage-v1`, 3072 B, cap12.

The fresh NQ run had 93.75% source-document answer coverage, 90.63% answer-bearing hit@12, and 75% answer-bearing projection. The fresh Hotpot G arm retained all support titles on 87.5% of items and at least one support title on 100%.

## 2. Real RAG host attachment: LlamaIndex BM25

Artifact: `target/llamaindex-hotpot-three-arm-20260913-r1/`

This is the more important product checkpoint. LlamaIndex owns retrieval and freezes the top-12 before the model run:

- `llama-index-core 0.14.24`;
- `llama-index-retrievers-bm25 0.8.0`;
- `bm25s 0.3.11`;
- 320-document fresh Hotpot corpus;
- retrieval manifest explicitly records `host_owns_retrieval=true`, `exactscope_used_during_retrieval=false`, and `gold_visible_during_retrieval=false`;
- same Qwen3.5 0.8B + llama.cpp runtime for all three arms;
- 32 items × 3 arms = 96 answer outputs, retry count 0;
- gold opened only after retrieval and model serving were frozen.

Arms:

- **A** — model only;
- **R** — ordinary LlamaIndex BM25 RAG: same top-12 retrieval, rank-order context up to 3072 B;
- **G** — same LlamaIndex BM25 top-12, then ExactScope `multihop-coverage-v1` shaping at 3072 B/cap12 plus ExactScope policy.

| Real-host Hotpot32 | F1 | Δ vs A | EM | Δ vs A |
|---|---:|---:|---:|---:|
| A · model only | 18.71% | — | 15.63% | — |
| **R · ordinary LlamaIndex RAG** | **49.13%** | **+30.43 pp** | **34.38%** | **+18.75 pp** |
| G · LlamaIndex + ExactScope | 27.76% | +9.06 pp | 15.63% | +0.00 pp |

### The product-relevant delta

**G − R = -21.37 pp F1 and -18.75 pp EM.**

So this checkpoint says two things at once:

1. the ExactScope attachment still improves the same model over model-only A on F1;
2. **the current host-attached policy is not yet competent against the ordinary deployable RAG alternative.**

That second fact blocks enterprise preregistration/Study Contract freeze. The next development work must explain and remove this gap without weakening the evidence/qualification guardrails.

Per-item F1 movement:

- R vs A: 15 improved / 14 tied / 3 regressed;
- G vs A: 10 improved / 16 tied / 6 regressed;
- G vs R: 4 improved / 18 tied / 10 regressed.

The host top-12 retrieval reaches all required support titles for 87.5% of items and at least one support title for 100%. Because ordinary RAG and G share the same frozen host retrieval, the large quality gap is downstream of retrieval and can be investigated as **context shaping / policy / prompt-surface interaction** rather than blamed on different search results.

### 2.1 Post-result mechanism diagnosis and H1 selection

Using the same frozen LlamaIndex retrieval, the diagnostic split showed that the dominant loss came from context shaping rather than the policy text alone:

- raw ordinary RAG + policy: **-1.00 pp F1 vs R**;
- ExactScope one-anchor shaping without policy: **-14.30 pp F1 vs R**;
- adding policy on shaped context: a further **-7.07 pp F1**.

A bounded hybrid family was therefore screened only on this already-open development cohort. The selected candidate, frozen as `host-ranked-hybrid-h1-v0`, keeps the top-ranked host document verbatim and spends the remaining 3072-byte budget on query-aware anchors from later ranked hits, with the stronger previously observed Qwen no-policy prompt profile. On that selection cohort H1 reached **56.69% F1 vs 49.13% R (+7.55 pp)** and **40.63% EM vs 34.38% R (+6.25 pp)**. This selection result is not treated as validation evidence.

### 2.2 Fresh H1 validation and predeclared stability64 screen

H1 was frozen before a new untouched Hotpot32 was selected. On that first fresh validation:

| Fresh H1 validation32 | F1 | Δ vs A | EM | Δ vs A |
|---|---:|---:|---:|---:|
| A · model only | 9.32% | — | 3.13% | — |
| R · ordinary LlamaIndex RAG | 35.36% | +26.04 pp | 21.88% | +18.75 pp |
| **G · frozen H1** | **36.67%** | **+27.35 pp** | **28.13%** | **+25.00 pp** |

So H1 was **+1.31 pp F1 / +6.25 pp EM over ordinary RAG** on a cohort chosen only after H1 was frozen. The paired development bootstrap remained wide, so this was treated as directional evidence rather than superiority proof.

A second stability screen was then preregistered as development-only before membership selection: next untouched 64 groups, same H1, same LlamaIndex BM25 top-12, same Qwen3.5 0.8B + llama.cpp runtime, all A/R/G serving before one score, no reselection, retry count 0. Artifact: `target/llamaindex-h1-stability64-20260913-r1/`.

| Predeclared stability64 | F1 | Δ vs A | EM | Δ vs A |
|---|---:|---:|---:|---:|
| A · model only | 7.82% | — | 3.13% | — |
| R · ordinary LlamaIndex RAG | 35.04% | +27.23 pp | 26.56% | +23.44 pp |
| **G · frozen H1** | **40.70%** | **+32.88 pp** | **34.38%** | **+31.25 pp** |

Product-relevant stability64 delta: **G − R = +5.66 pp F1 and +7.81 pp EM**. G also used fewer mean evidence bytes (`2904.5` vs `3067.1`, about **-5.3%**) and fewer mean input tokens (`840.8` vs `874.0`, about **-3.8%**). Sequential model latency was higher (`271.8 ms` vs `261.9 ms`, about **+3.8%**) and remains descriptive only.

All predeclared development competence gates passed: zero G format failures, G aggregate F1/EM not below R, and G mean evidence bytes/input tokens not above R. The paired 95% development bootstrap for G−R F1 remained wide (`-4.69 pp` to `+16.25 pp`), so this is **engineering competence evidence, not statistical qualification**.

## 3. Historical stable-v1 reference — no rerun required

The stable v1 public panel has already been measured and is retained as historical context rather than rerun merely for presentation:

| v1 public aggregate | A | G | A → G |
|---|---:|---:|---:|
| Natural Questions · F1 | 9.14% | 21.35% | **+12.21 pp** |
| HotpotQA · F1 | 12.18% | 24.64% | **+12.46 pp** |
| FEVER · label accuracy | 26.52% | 30.63% | **+4.11 pp** |

Those values come from the existing stable-v1 multi-model panel and are **not directly comparable** to the fresh single-model v1.1 32-item cohorts above.

Separate same-Qwen untouched checks already recorded elsewhere also show:

- Hotpot: stable-v1 G F1 26.06% → frozen v1.1 multi-hop 32.28% (**+6.22 pp vs v1 G**); model-only A on that cohort was 15.09%, so the frozen v1.1 path was **+17.19 pp vs A**;
- NQ: stable-v1 G F1 27.65% → frozen v1.1 precision 3K 29.28% (**+1.63 pp vs v1 G**) with 28.7% fewer input tokens and 37.2% fewer evidence bytes.

## 4. Freeze gate after this result

Current state:

```text
fresh A/G showcase                 PASS as development evidence
real LlamaIndex host retrieval     PASS operationally
three-arm execution integrity      PASS operationally
post-result mechanism diagnosis    COMPLETE
H1 frozen before fresh validation  PASS
fresh validation32                 G > R directionally
predeclared stability64            PASS all development competence gates
ExactScope vs model-only A         +32.88 pp F1 on stability64
ordinary RAG vs model-only A       +27.23 pp F1 on stability64
ExactScope vs ordinary RAG         +5.66 pp F1 / +7.81 pp EM on stability64
final 20-model public panel        COMPLETE: 32 scored / 8 protocol N/A
final NQ mean A→G                  12.44% → 21.68% (+9.24 pp), n=16
final Hotpot mean A→G              11.63% → 31.42% (+19.79 pp), n=16
pooled valid-cell mean uplift      +14.52 pp across 32 model-task pairs
public policy tuning               CLOSED / no reselection from panel
real qualification workload        NOT YET ACQUIRED / OWNER-BOUND
enterprise prereg / Study freeze   BLOCKED on real workload + economics/statistics
readiness / Astra confirmatory     NOT REACHED
```

The development question is now closed strongly enough to stop tuning H1 on these public cohorts. The next work is **not another public Hotpot optimization loop**. It is to acquire and owner-bind a real qualification workload, define its ordinary production alternative and fixed-cost/economic truth, freeze the enterprise preregistration and Study Contract, run readiness, and only then request Astra hard review plus owner authorization for the single confirmatory execution.

The stability64 bootstrap interval still crosses zero, so the `+5.66 pp` result must be presented as observed development effect, not a powered superiority claim. Any qualification margin or economic threshold must be fixed prospectively on the real workload rather than inferred from these public results.

## 5. Final frozen 20-model public robustness panel

Artifact: `target/v11-final-20-model-panel-20260913-r1/`
Preregistration SHA-256: `506f0f4305e9c02a90da54bbf23113b8e4a9c0cd499d583dea42d354c51a3dee`
Results SHA-256: `69e91468842d9f7ac077547b80fe798a758814068a858d09eda704b00a8c34f8`

The final panel was run only after D-130/D-131 froze H1, the NQ policy, failure handling, averaging rules, model matrix, runtime, prompts/contracts and scorers. All **40 serving cells were attempted before any scoring began**. No quality retry, hidden repair or post-panel policy reselection was allowed. FEVER was excluded because its prior held-out is retired. Historical v1 Public-6 macro values were reused only as context and were not rerun.

| Final panel workload | Valid pairs | Mean A F1 | Mean G F1 | Mean A→G | Improved / tied / regressed |
|---|---:|---:|---:|---:|---:|
| NQ · fresh post-freeze64 | 16 / 20 | 12.44% | **21.68%** | **+9.24 pp** | 14 / 0 / 2 |
| HotpotQA · LlamaIndex BM25 + frozen H1 stability64 | 16 / 20 | 11.63% | **31.42%** | **+19.79 pp** | 15 / 0 / 1 |

Across all **32 valid model-task pairs**, the descriptive mean F1 uplift was **+14.52 pp**. Four model identities were protocol N/A on both tasks rather than being converted to zero: SmolLM2 135M, TinyLlama 1.1B, LFM2.5 1.2B and DeepSeek-R1-Distill-Qwen 1.5B. SmolLM2 135M, LFM2.5 1.2B and DeepSeek-R1 1.5B failed the frozen semantic contract calibration with score zero; TinyLlama exposed no supported structured-output surface. These cells were not retried.

The panel also retained negative results. SmolLM2 360M regressed **-2.01 pp** on NQ while improving **+4.88 pp** on Hotpot. Ministral 3B regressed on both scored tasks (**-3.97 pp NQ, -0.67 pp Hotpot**). Positive highlights include Qwen3.5 0.8B (**+13.71 pp NQ, +32.88 pp Hotpot**) and Qwen3.5 2B (**+25.49 pp NQ, +53.40 pp Hotpot**). These are observed fixed-panel effects, not universal model guarantees.

The README now contains the full per-model table in the same `A→G (+x.xxpp)` style as v1, generated from `README_SNIPPET.md`. Final artifact integrity verification covered **383 non-detached files** with exact checksum-set equality and zero mismatches; the README marker content matched the generated snippet exactly.

This closes public benchmark-driven policy development for the current v1.1 candidate. Further public-data tuning would contaminate the stated freeze boundary. The next empirical work must move to a real authorized qualification workload with an accountable owner, ordinary production alternative, frozen economics and statistical analysis, fail-closed readiness, Astra hard review, owner go/no-go, and one confirmatory execution.
