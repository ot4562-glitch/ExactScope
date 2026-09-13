# ExactScope v1.1 — live attached v1/v1.1 diagnostic result

Status: **completed development diagnostic; reused public screens; not fresh qualification evidence**
Updated: **2026-09-13**

## 1. What actually ran

The first completed v1-versus-v1.1 attached comparison used the same local target model and runtime for both versions:

- Qwen3.5 0.8B Q4;
- Windows llama.cpp `b10797`;
- stable v1.0.0 r25 behavior versus the then-current fixed v1.1 precision/integrated behavior;
- existing NQ128 and Hotpot20 public development candidates;
- all serving outputs completed before gold scoring;
- no Astra/Codex agent executed the benchmark;
- no retries, second model, reflection loop, or outcome-aware answer selection.

This was **not** the prospective fresh-64 protocol originally described in [`V1_1_LIVE_ATTACHED_DIAGNOSTIC.md`](V1_1_LIVE_ATTACHED_DIAGNOSTIC.md). It is therefore a reused-screen regression/economics diagnostic only. The separately pre-frozen fresh Hotpot64 sample was not consumed by this comparison and was later used for the independent multi-hop policy development study documented in [`V1_1_MULTIHOP_POLICY_DEVELOPMENT_RESULT.md`](V1_1_MULTIHOP_POLICY_DEVELOPMENT_RESULT.md).

Primary artifact: `target/v1-v11-attached-compare-20260913-r1/comparison.json`.

## 2. Paired result

| Workload | Version | Model-only A F1 | Attached G F1 | G-A uplift | G input tokens | G evidence bytes |
|---|---:|---:|---:|---:|---:|---:|
| NQ128 | v1 | 0.0501 | 0.2374 | +0.1873 | 155,469 | 506,595 |
| NQ128 | v1.1 | 0.0534 | **0.3062** | **+0.2527** | **88,292** | **230,920** |
| Hotpot20 | v1 | 0.1226 | **0.3415** | **+0.2189** | 24,372 | 77,440 |
| Hotpot20 | v1.1 | 0.1400 | 0.2533 | +0.1133 | **13,074** | **31,611** |

Direct v1.1 attached-G minus v1 attached-G:

- **NQ128:** EM `+6.25 pp`, F1 `+6.88 pp`, input tokens `-43.2%`, evidence bytes `-54.4%`;
- **Hotpot20:** EM `-10.0 pp`, F1 `-8.82 pp`, input tokens `-46.4%`, evidence bytes `-59.2%`.

Model request-service time was effectively flat at this local CPU runtime. Token/context reduction therefore must not be described as an equivalent wall-clock or money reduction without a separately frozen price/capacity model.

## 3. Interpretation

The original same-model attachment signal is still present. v1.1 attached evidence improved over model-only on both workloads:

- NQ F1 uplift: `+25.27 pp`;
- Hotpot F1 uplift: `+11.33 pp`.

However, one fixed precision policy did not dominate stable v1 across workload semantics. NQ improved while using substantially less context, but Hotpot lost quality while using substantially less context.

The strongest mechanism clue was support-set retention:

- Hotpot v1 all-support-title retrieval/projection rate: `0.85`;
- Hotpot v1.1 precision path: `0.60`.

This motivated a fixed **multi-hop coverage-preserving** workload policy rather than a per-query adaptive router. The follow-up fresh development/validation result confirmed that hypothesis; see [`V1_1_MULTIHOP_POLICY_DEVELOPMENT_RESULT.md`](V1_1_MULTIHOP_POLICY_DEVELOPMENT_RESULT.md).

## 4. Scorer compatibility recovery

The v1.1 serving runs used the proof-minimal surface negotiation rule: stop at the first supported output surface. The public NQ/Hotpot scorers still contained an older invariant requiring a probe count equal to every candidate surface. This caused scoring to stop after serving outputs were already frozen.

Recovery rules:

- serving outputs were **not rerun**;
- model outputs were **not modified**;
- original serving source hashes remained unchanged;
- a score-only compatibility copy aligned the stale count check to the persisted negotiation record;
- the repository public scorers were subsequently corrected to validate `negotiation.model_request_count` rather than assume a full candidate-surface sweep.

This is a verifier compatibility correction, not a quality-policy change.

## 5. Claim boundary

This diagnostic supports only the following development conclusions:

1. same-model semantic amplification remains measurable;
2. v1.1 precision projection can improve single-hop quality while materially reducing context volume;
3. applying the same aggressive precision policy to multi-hop evidence can lose support coverage and answer quality;
4. fixed workload semantics therefore need distinct qualified policies before a universal product claim is credible.

It does **not** establish enterprise customer value, production total economics, a release claim, frontier-provider savings, or cross-workload automatic routing.
