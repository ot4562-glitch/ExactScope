# ExactScope v1.1 — Stage 1 ReferenceOnly result

Status: completed algorithm-diagnostic result, 2026-09-13. This is not release qualification and does not authorize a deployable Qualified Execution Profile.

## Result

The preregistered Qwen/FEVER Stage 1 stopped at calibration with:

```text
outcome = ReferenceOnly
P = null
T = integrated
held-out consumed = false
qualification_passed = false
```

All 1,200 expected calibration observations completed with zero mandatory violations. The predeclared Reference `integrated` achieved 52/120 successes at 22,946 ms aggregate measured request-service time. No cheaper frozen candidate matched its aggregate success count, and no cheaper candidate preserved all Reference successes. The conventional comparator therefore also returned `T = F`.

The nearest aggregate-quality candidate was `A+D` at 49/120, 20,606 ms: 10 Reference-only successes were lost and 7 successes occurred where Reference failed. The cheapest candidate, `D`, was 11.75% cheaper than Reference on calibration service-time totals, below the preregistered 15% material-cost target. These are calibration descriptions only; the held-out product gates were never evaluated.

## Experiment-integrity disposition

The frozen 600-item FEVER held-out was not scored. It remains sealed as the held-out artifact of the stopped study and is retired from confirmatory inference for revised policy rules or rescue questions. Do not run F/T alone, reselect a new P, relax thresholds, extend the sample, or reuse the 600 to guide policy development.

The formal verifier result is `ReferenceOnly` with `NOT_EVALUATED_REFERENCE_ONLY` for narrow selector, product, and incremental-selector verdicts. The study was prospectively classified as algorithm-diagnostic-only because no defensible absolute B/F competence floor existed, so product inference was prohibited independently of the calibration stop.

## What this demonstrates

It demonstrates that the frozen fixed-catalog reference-preserving cost-reduction algorithm correctly abstained when its eligibility conditions were not met. It also shows that, on this calibration frontier, relaxing paired preservation to the frozen aggregate-quality comparator would not have produced a cheaper policy.

It does **not** demonstrate release qualification, customer value, a general inability of semantic policies to help inference, cross-runtime transfer, an established compiler category, or a moat.

## Product consequence

Astra High independently reviewed the stopped result and recommended:

- narrow v1.1 product identity to a **qualification/configuration optimizer with semantic enforcement and immutable qualification records**;
- keep **Semantic Inference Policy Compiler** only as a research hypothesis;
- pivot the next empirical priority to **bounded enterprise document QA with real host retrieval and a defensible competence floor**;
- test an integrated-style policy versus Base as a primary product-value comparison in that new workload, while any cheaper reference-preserving branch remains conditional and separately preregistered;
- defer cross-host transfer and per-request adaptive routing until a useful competent source policy is demonstrated.

## Immutable evidence artifacts

- freeze: `target/harness-fever-stage1-freeze-20260913-r1/`
- preregistration: `target/harness-fever-stage1-preregistration-20260913-r1.json`
- calibration run: `target/harness-fever-stage1-calibration-run-20260913-r1/`
- calibration analysis: `target/harness-fever-stage1-calibration-analysis-20260913-r1.json`
- stop report: `target/harness-fever-stage1-report-20260913-r1.json`
- formal result: `target/harness-fever-stage1-result-20260913-r1.json`
- Astra review packet: `docs/V1_1_STAGE1_REFERENCE_ONLY_ASTRA_PACKET.md`
- Astra review: `docs/V1_1_STAGE1_REFERENCE_ONLY_ASTRA_REVIEW.md`

The bound Stage 1 source files and `docs/V1_1_STAGE1_PREREGISTRATION.md` should remain unchanged so the preregistration source fingerprints continue to verify.
