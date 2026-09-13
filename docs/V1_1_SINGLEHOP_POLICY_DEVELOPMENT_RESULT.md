# ExactScope v1.1 — single-source precision policy development result

Status: **fresh development/validation + untouched stable-v1 confirmation; positive for frozen 3K precision; not product qualification**
Updated: **2026-09-13**

## 1. Why this study was required

The first reused-screen attached diagnostic made `precision-context-v5` look strong on NQ128, but a later fresh untouched NQ32 regression cell showed that the then-current 2 KiB product cap was not robust enough.

On that untouched NQ32:

| Metric | stable v1 r25 G | v1.1 precision 2K G | v1.1 − v1 |
|---|---:|---:|---:|
| EM | 21.875% | 18.75% | -3.125 pp |
| F1 | **36.56%** | 33.20% | **-3.36 pp** |
| answer-bearing projection | **65.625%** | 53.125% | **-12.5 pp** |
| input tokens | 38,016 | **22,217** | -15,799 (-41.6%) |
| evidence bytes | 125,241 | **60,516** | -64,725 (-51.7%) |

The 2K path still amplified over its own model-only arm, but the direct stable-v1 comparator failed. That cohort was sealed after scoring and was not used for budget tuning.

Primary artifact: `target/v11-nq-policy-regression-20260913-r1/`.

## 2. Independent pre-frozen development source

Budget development used the separate NQ64 sample already selected label-blind in `target/v11-live-attached-20260913-r1/freshness-preflight.json` before this repair existed.

The existing randomized frozen order was split prospectively:

- first 32 representatives: development;
- last 32 representatives: untouched validation.

Development/validation membership was written before `short_answers` was opened. The validation serving runner never opened gold; scoring opened gold only after all model outputs were frozen.

Primary artifact: `target/v11-nq-precision-policy-dev-20260913-r1/`.

## 3. Predeclared precision catalog

All candidates kept the same `precision-context-v5` semantics. Only bounded evidence budget/item cap varied:

| Candidate | Budget | Cap |
|---|---:|---:|
| `precision-2k-cap8` | 2,048 B | 8 |
| `precision-3k-cap8` | 3,072 B | 8 |
| `precision-3k-cap12` | 3,072 B | 12 |
| `precision-4k-cap12` | 4,096 B | 12 |

Selection was frozen before development gold:

1. highest answer-bearing projection rate;
2. lowest mean evidence bytes;
3. lowest mean projected chunk count;
4. UTF-8 policy ID.

## 4. Development32 screen

Raw retrieval contained an answer-bearing chunk in the top 12 for `81.25%` of development items.

| Candidate | Answer-bearing projection | Mean evidence bytes | Mean projected chunks |
|---|---:|---:|---:|
| `precision-2k-cap8` | 50.0% | **1,768** | **5.16** |
| `precision-3k-cap8` | **53.125%** | **2,495** | **6.06** |
| `precision-3k-cap12` | 53.125% | 2,561 | 6.31 |
| `precision-4k-cap12` | 53.125% | 3,320 | 7.63 |

The frozen winner was **`precision-3k-cap8`**. Increasing from 3 KiB to 4 KiB produced no additional development answer-bearing coverage, so the deterministic tie-break selected the smaller 3 KiB policy.

## 5. Untouched validation32

Validation arms:

- `A`: model only;
- `P`: previous production candidate, precision 2K/cap8;
- `W`: development-frozen precision 3K/cap8.

| Arm | EM | F1 | Answer-bearing projection | Input tokens | Evidence bytes | Model service time |
|---|---:|---:|---:|---:|---:|---:|
| A | 0.0% | 7.35% | — | 3,116 | 0 | 7.256 s |
| P | 15.625% | 20.91% | 46.875% | 21,454 | 55,816 | 7.276 s |
| W | **25.0%** | **29.38%** | **56.25%** | 26,449 | 75,886 | 7.491 s |

Frozen W versus previous 2K P:

- EM: **+9.375 pp**;
- F1: **+8.47 pp**;
- answer-bearing projection: **+9.375 pp**;
- input tokens: `+4,995` (`+23.3%`);
- evidence bytes: `+20,070` (`+36.0%`);
- model service time: about `+3%`.

Frozen W versus model-only A:

- EM: **+25.0 pp**;
- F1: **+22.03 pp**.

## 6. Direct stable-v1 confirmation on another untouched NQ32

The validation32 above did not contain stable v1 as a preregistered arm. A second untouched NQ32 was therefore constructed from the original label-blind seed ordering after excluding:

1. historical exclusions;
2. the pre-frozen NQ64 used for development/validation;
3. the earlier failed-regression next32 cohort.

Membership was again frozen before opening `short_answers`. The already-frozen `precision-3k-cap8` policy was then compared directly against stable v1 r25 on the same Qwen3.5 0.8B Q4 / llama.cpp `b10797` host.

Artifact: `target/v11-nq-v1-confirmation-20260913-r1/`.

| Metric | stable v1 r25 G | frozen v1.1 precision 3K | v1.1 − v1 |
|---|---:|---:|---:|
| EM | 18.75% | **18.75%** | 0 pp |
| F1 | 27.65% | **29.28%** | **+1.63 pp** |
| answer-bearing projection | **78.125%** | 62.5% | -15.625 pp |
| input tokens | 37,964 | **27,071** | **-10,893 (-28.7%)** |
| evidence bytes | 126,701 | **79,618** | **-47,083 (-37.2%)** |
| model service time | **6.914 s** | 8.223 s | +1.309 s (~+19%) |

The final-model quality result matters more than raw projection rate here: despite preserving fewer literal answer-bearing projected snippets than stable v1, the v1.1 combination of bounded precision evidence plus the newer answer contract matched EM, improved F1, and used materially less input context. This does **not** make local CPU latency a win.

## 7. Decision

The previous **2 KiB precision cap is no longer the active single-source candidate**. It remains historical evidence for aggressive compression but failed one fresh stable-v1 comparator.

The current fixed single-source candidate is:

```text
evidence_composition = single-source-precision
evidence_policy_id   = precision-context-v5
evidence_budget      = 3072 bytes
max projected items  = 8
```

This is paired with the independently validated multi-source candidate:

```text
evidence_composition = multi-source-coverage
evidence_policy_id   = multihop-coverage-v1
evidence_budget      = 3072 bytes
max projected items  = 12
```

Both are compile-time workload-policy candidates. Neither is a request-time adaptive router.

## 8. Claim boundary

These are local public-task development diagnostics, not enterprise product qualification. They do not establish production pricing savings, provider latency savings, statistically powered population superiority, or automatic semantic classification of arbitrary workloads. The evidence supports only the narrower engineering claim that **different prospectively declared evidence-composition requirements can lower to different fixed bounded policies, and both current 3 KiB candidates survived untouched same-host comparison against stable v1 in their respective development workloads.**
