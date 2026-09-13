# ExactScope v1.1 — frozen multi-hop policy vs stable v1 confirmation

Status: **positive untouched diagnostic; fixed v1.1 multi-hop policy beats stable v1 on quality and context volume; latency does not improve**
Updated: **2026-09-13**

## 1. Purpose

After `multihop-coverage-v1` was selected on development32 and beat the current v1.1 precision path on untouched validation32, the next question was deliberately narrower:

> **Does the already-frozen v1.1 multi-hop policy beat stable v1 r25 on another untouched Hotpot cohort using the same Qwen model and llama.cpp runtime?**

No policy reselection was allowed.

## 2. Untouched cohort

The cohort was not drawn after seeing the first validation result. It reused the original label-blind sampling seed and ordering frozen before the multi-hop work existed:

1. keep the original historical exclusions;
2. exclude every group in the previously frozen Hotpot64;
3. reconstruct the same seed-based eligible-group ordering;
4. take the next 32 representatives;
5. write `selection-freeze.json` before opening answer/supporting-fact columns.

Artifacts: `target/v11-multihop-v1-confirmation-20260913-r1/`.

## 3. Matched host

- model: Qwen3.5 0.8B Q4;
- runtime: Windows llama.cpp `b10797`;
- same Hotpot32 serving candidate;
- same `top_k=12`;
- stable v1: shipped r25 semantics, 4 KiB evidence cap, stable contract calibration;
- v1.1: frozen `coverage-3k-cap12`, proof-minimal output-surface negotiation, `answer-object-v4`;
- serving runs completed before scoring;
- quality is primary; local request-service time is descriptive.

The stable v1 worktree received only runtime-record plumbing so the unavailable historical Linux executable was not silently substituted; its retrieval/projection/prompt/scoring semantics were unchanged.

## 4. Result

| Metric | stable v1 r25 G | frozen v1.1 W | W − v1 |
|---|---:|---:|---:|
| EM | 18.75% | **25.00%** | **+6.25 pp** |
| F1 | 26.06% | **32.28%** | **+6.22 pp** |
| all support titles | 81.25% | **81.25%** | 0 pp |
| any support title | 96.875% | **96.875%** | 0 pp |
| input tokens | 37,634 | **31,505** | **-6,129 (-16.3%)** |
| evidence bytes | 122,669 | **95,791** | **-26,878 (-21.9%)** |
| output tokens | **290** | 308 | +18 |
| model service time | **6.461 s** | 7.835 s | +1.374 s (~+21%) |

Stable v1 itself remained an amplifier on this cohort: model-only A F1 was `15.09%`, while v1 G reached `26.06%`. The frozen v1.1 multi-hop policy then increased F1 again to `32.28%` while preserving the exact same support-title coverage and using less input context.

## 5. Interpretation

This closes the immediate Hotpot regression mechanism more strongly than the prior validation alone:

- the v1.1 precision regression was not evidence that stable v1 had an inherently superior multi-hop architecture;
- preserving multi-source coverage restores the lost mechanism;
- the fixed v1.1 multi-hop policy can exceed stable v1 quality without exceeding stable v1 context volume;
- the local CPU latency path still needs work, so context/token efficiency must not be equated with wall-clock savings.

The result therefore supports a **compile-time workload-policy split**:

```text
single-source / short factual evidence
    -> precision-context-v5

multi-source composition required
    -> multihop-coverage-v1
```

This is not a dataset-name router and not permission to make request-time adaptive choices after seeing retrieval/model outcomes.

## 6. Product/contract consequence

The Workload Contract now permits a restricted semantic field:

- `single-source-precision`;
- `multi-source-coverage`;
- legacy/other workloads may remain `unspecified`.

The reference compiler fails closed if the semantic requirement and the chosen known evidence-policy implementation conflict. Candidate Execution Policy records the compiled `evidence_composition` alongside `evidence_policy_id`.

That empirical guard is now complete. Fresh NQ regression protection retired the 2 KiB precision cap, pre-frozen development/validation selected `precision-context-v5` at 3 KiB/cap8, and a separate untouched NQ32 then matched stable-v1 EM while improving F1 with less input context. The two fixed workload-policy candidates can therefore remain in the v1.1 architecture while enterprise document-QA qualification proceeds; see [`V1_1_SINGLEHOP_POLICY_DEVELOPMENT_RESULT.md`](V1_1_SINGLEHOP_POLICY_DEVELOPMENT_RESULT.md).

## 7. Claim boundary

This is still a local development diagnostic, not production qualification. It does not establish enterprise total economics, provider pricing savings, statistical population superiority, or frontier-provider transfer. It does establish a second untouched same-host signal that the multi-hop coverage repair is not merely a Hotpot20 post-hoc fit.
