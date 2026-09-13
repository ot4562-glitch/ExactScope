# ExactScope v1.1 — multi-hop coverage policy development result

Status: **fresh development/validation mechanism result; positive; not product qualification**
Updated: **2026-09-13**

## 1. Question

The reused v1/v1.1 attached diagnostic showed a split result: the v1.1 precision path improved NQ while reducing context, but regressed HotpotQA while also reducing context. The working mechanism hypothesis was:

> **Multi-hop quality fell because precision projection removed too much of the support set, not because same-model amplification disappeared.**

The corrective design was intentionally narrow. ExactScope did **not** add a learned router, second model, retry loop, or item-specific policy. Instead it tested a fixed workload policy for evidence-composition workloads:

- single-hop/factual workload: keep `precision-context-v5`;
- multi-source/multi-hop workload candidate: preserve document/title coverage first, then spend remaining bytes on adjacent context.

This follows the frozen north-star boundary: workload semantics compile to a fixed Candidate Execution Policy; request-time outcome-aware routing remains out of scope.

## 2. Data independence

The study used the Hotpot64 sample already selected label-blind in `target/v11-live-attached-20260913-r1/freshness-preflight.json` before this mechanism study existed.

Source frame facts:

- source rows: `7,405`;
- transitive question/title groups: `3,183`;
- historically excluded items: `2,467`;
- eligible groups: `3,167`;
- selected representatives: `64` from the previously frozen randomized order.

The 64 representatives were split prospectively by that existing randomized order:

- first 32: development;
- last 32: untouched validation.

The validation runner never opened answer/supporting-fact gold. Gold was opened only after all 96 validation model outputs were frozen.

Primary artifacts: `target/v11-multihop-policy-dev-20260913-r3/`.

## 3. Fixed candidate catalog

Before development gold analysis, the protocol froze three deterministic projection candidates:

| Policy | Budget | Max projected items | Semantics |
|---|---:|---:|---|
| `precision-2k-cap8` | 2,048 B | 8 | current `precision-context-v5` |
| `coverage-2k-cap12` | 2,048 B | 12 | one anchor per ranked document first, then adjacent-context expansion |
| `coverage-3k-cap12` | 3,072 B | 12 | same coverage-first rule with larger bounded budget |

Development selection was lexicographic and frozen before reading gold:

1. highest all-support-title projection rate;
2. highest any-support-title projection rate;
3. lowest mean evidence bytes;
4. UTF-8 policy ID.

## 4. Development32 projection screen

Raw retrieval already contained all support titles for `78.125%` of items and at least one support title for `96.875%`.

| Policy | All support | Any support | Mean projected titles | Mean evidence bytes |
|---|---:|---:|---:|---:|
| `precision-2k-cap8` | 56.25% | 90.625% | 6.09 | 1,732 |
| `coverage-2k-cap12` | 75.0% | 96.875% | 10.94 | 2,023 |
| `coverage-3k-cap12` | **78.125%** | **96.875%** | **12.0** | 3,039 |

The frozen winner was therefore **`coverage-3k-cap12`**. It preserved the full raw-retrieval all-support rate on development rather than dropping it to the precision path's 56.25%.

## 5. Untouched validation32 real-model result

Host cell:

- Qwen3.5 0.8B Q4;
- Windows llama.cpp `b10797`;
- one fixed negotiated JSON-schema surface;
- one calibrated `answer-object-v4` contract;
- zero answer retry or second-model path.

Validation arms:

- `A`: model only;
- `P`: current precision 2K/cap8;
- `W`: development-frozen coverage 3K/cap12.

| Arm | EM | F1 | All support projected | Any support projected | Input tokens | Evidence bytes | Model service time |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 18.75% | 24.39% | — | — | 3,397 | 0 | 6.118 s |
| P | 28.125% | 29.64% | 46.875% | 100% | 20,426 | 51,843 | 6.384 s |
| W | **34.375%** | **36.46%** | **93.75%** | **100%** | 31,342 | 96,447 | 7.022 s |

Frozen W versus current P:

- EM: **+6.25 pp**;
- F1: **+6.82 pp**;
- all-support projection: **+46.875 pp**;
- input tokens: `+10,916` (`+53.4%`);
- evidence bytes: `+44,604` (`+86.0%`);
- model service time: `+0.637 s` total (`~+10%`).

Frozen W versus model-only A:

- EM: **+15.625 pp**;
- F1: **+12.07 pp**.

## 6. Interpretation

The mechanism hypothesis survived untouched validation:

1. the precision path materially dropped complete support-set coverage;
2. a deterministic coverage-first projection restored support-set visibility;
3. restoring support-set visibility improved real-model answer quality on an untouched validation subset;
4. the gain was purchased with a larger, but still bounded, 3 KiB evidence surface.

This is the desired form of workload-specific compilation evidence. The system does not need a request-time model to guess whether more context is useful. A workload contract that requires multi-source composition can lower to a coverage-preserving projection, while a single-hop workload can retain the cheaper precision path.

The result does **not** yet show that `coverage-3k-cap12` beats stable v1 on the same untouched items. That direct comparator must be run as a separate prospectively frozen diagnostic because stable v1 was not one of the preregistered validation arms here.

## 7. Promotion rule

This result is sufficient to carry `multihop-coverage-v1` forward as a **candidate fixed workload policy**, but not to make it the universal v1.1 default.

Next required checks, in order:

1. compare stable v1 r25 versus frozen `coverage-3k-cap12` on another untouched Hotpot cohort with the same model/runtime;
2. keep the NQ/single-hop precision path unchanged and run regression protection in parallel;
3. if the fixed workload split survives those checks, represent the distinction in the Workload Contract / Candidate Execution Policy as a restricted evidence-composition requirement rather than a dataset-name switch;
4. then continue to the competence-gated enterprise document-QA product proof.

No per-query adaptive router is authorized by this result.
