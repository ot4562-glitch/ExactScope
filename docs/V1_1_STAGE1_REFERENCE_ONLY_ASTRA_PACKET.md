# ExactScope v1.1 — Stage 1 `ReferenceOnly` Astra High review packet

Status: strategic review input after a preregistered calibration stop. This packet does not authorize changing the frozen Stage 1 selector, thresholds, held-out set, or bound source files.

## 1. Review scope

Review only this packet. Do not browse the repository or the web. Separate what the evidence shows from recommendations.

The previous Astra High direction review recommended:

- internal research thesis: **Semantic Inference Policy Compiler** as a hypothesis;
- external product artifact: **Qualified Execution Profile**;
- first conservative algorithm: **Reference-Preserving Cost Reduction**;
- current honest category until transfer evidence improves: constrained configuration optimizer with semantic enforcement and qualification records;
- Stage 1 should include a conventional tuner comparator `T`, absolute competence handling, exact finite-population bounds, frozen cost/timing protocols, and unique B/F/P/T held-out arms;
- if no credible absolute B/F competence floor exists, Stage 1 must be algorithm-diagnostic-only;
- a valid `ReferenceOnly` calibration outcome stops the main held-out study rather than rescuing or reselecting on held-out.

Those recommendations were implemented prospectively before fresh Stage 1 FEVER scoring.

## 2. Frozen Stage 1 design

Workload: controlled oracle-page-pooled FEVER three-way claim verification.

Model: Qwen3.5 0.8B Q4.

Runtime: existing Windows llama.cpp b10797 / commit 832fd6f17. The exact Linux runtime from the earlier 6+6 transfer was unavailable, so the old 6+6 was explicitly demoted to development evidence rather than a matched-runtime control.

Frozen cohort:

- calibration: 120 fresh claims, balanced 40 per label;
- held-out finite frame: 3,573 post-exclusion representatives;
- held-out sample: 600 simple-random-without-replacement representatives;
- grouping: connected components under exact normalized claim identity or any overlapping evidence page;
- held-out realized labels: 528 NEI / 38 REFUTES / 34 SUPPORTS; no rebalance because labels did not participate in held-out sampling;
- prior public/first-transfer source IDs and normalized claims excluded.

The 600-item held-out has **not been scored or opened by the Stage 1 runner**.

Exact analysis gates were frozen before calibration. The finite-population gate-resolution preflight passed, but was explicitly not described as an 80% power guarantee.

Absolute competence review before scoring concluded that existing Qwen/FEVER evidence was too weak to justify deployable-task competence. Therefore the study was frozen **algorithm-diagnostic-only**. Even a numerical pass could not emit a deployable profile or customer/product qualification.

## 3. Frozen candidate/selector semantics

Predeclared Base `B` = `Base`.

Predeclared Reference `F` = `integrated` = A+B+D + no-policy prompt reduction in this minimal host.

Calibration executed exactly these ten policies:

`Base`, `A`, `B`, `D`, `A+B`, `A+D`, `B+D`, `A+B+D`, `prompt_reduced`, `integrated`.

For candidate `p`:

- `S[p]` = calibration successes;
- `C[p]` = frozen serving-cost total, here single-concurrency measured request-service milliseconds;
- `L[p,F]` = count of calibration items where F succeeds and p fails.

Reference admission required F valid, mandatory gates pass, `S[F] > 0`, and `S[F] >= S[B]`.

Paired selector `P` required valid + mandatory gates + `L[p,F] == 0` + `C[p] < C[F]`; deterministic choice was lowest cost, then highest successes, then canonical ID. No eligible cheaper candidate means `ReferenceOnly`.

Conventional tuner comparator `T` required valid + mandatory gates + `S[p] >= S[F]` + `C[p] < C[F]`; otherwise `T = F`.

Only if `P` exists may the 600 held-out run. There is no F/T rescue, held-out reselection, threshold relaxation, optional sample extension, or repeated model call for a better answer.

## 4. Fresh calibration result

All 1,200 expected observations completed. All ten policies had zero mandatory violations. The final calibration selector result was:

```text
outcome = ReferenceOnly
P = null
T = integrated
```

Policy summary:

| policy | success / 120 | F-success losses `L[p,F]` | successes where F failed | service cost ms | cost reduction vs F |
|---|---:|---:|---:|---:|---:|
| integrated F | 52 | 0 | 0 | 22,946 | 0.00% |
| A+D | 49 | 10 | 7 | 20,606 | 10.20% |
| A+B | 47 | 10 | 5 | 22,934 | 0.05% |
| prompt_reduced | 47 | 9 | 4 | 21,885 | 4.62% |
| A | 46 | 12 | 6 | 20,544 | 10.47% |
| A+B+D | 46 | 9 | 3 | 22,454 | 2.14% |
| B | 45 | 10 | 3 | 22,481 | 2.03% |
| B+D | 44 | 10 | 2 | 22,862 | 0.37% |
| Base | 42 | 13 | 3 | 20,459 | 10.84% |
| D | 42 | 13 | 3 | 20,250 | 11.75% |

Important implications directly supported by calibration:

1. This is **not only a paired-preservation failure**. `T = F`, so the conventional aggregate quality-constrained tuner also found no cheaper policy with `S[p] >= S[F]`.
2. `integrated` is the calibration aggregate-quality leader in the frozen catalog: 52/120 versus 49/120 for the next-best A+D and 42/120 for Base.
3. The success sets are materially non-nested. Example: A+D loses 10 F successes but gains 7 items where F fails.
4. No frozen candidate achieved the preregistered 15% product cost reduction relative to F on calibration service-time totals. The cheapest candidate, D, was 11.75% cheaper than F. This is descriptive calibration evidence only; the held-out product gate was not evaluated.
5. Absolute FEVER performance remains weak enough that this study is not a customer-value test.

## 5. Formal Stage 1 stop

The stop report and verifier were generated without held-out scoring.

Verifier result:

```text
verdict = ReferenceOnly
qualification_passed = false
narrow_selector_verdict = NOT_EVALUATED_REFERENCE_ONLY
product_verdict = NOT_EVALUATED_REFERENCE_ONLY
incremental_selector_verdict = NOT_EVALUATED_REFERENCE_ONLY
product_inference_allowed = false
```

Authorized claim is only that this algorithm-diagnostic Stage 1 reached a preregistered `ReferenceOnly` calibration stop. It does not support release qualification, real-retrieval customer value, universal same-model improvement, cross-runtime transfer, established category distinctness, a moat, or product qualification.

The 600-item held-out remains untouched.

## 6. Strategic problem

The prior reframe tried to distinguish ExactScope from prompt optimizers, RAG frameworks, and runtimes by making the compiled artifact a small immutable qualified semantic execution policy/profile above host-owned mechanisms.

Stage 1 was meant to answer a narrow first question: can a fixed semantic policy be prospectively selected within one workload/model/runtime while preserving a competent reference's observed successes and reducing serving cost?

Calibration now says the frozen intervention catalog contains **no cheaper candidate that even matches F's aggregate calibration success count**, let alone preserves every F success. Therefore the immediate problem may be upstream of the paired selector: the cost/quality frontier exposed by this candidate catalog may simply not contain the desired point.

At the same time, `integrated` itself shows a calibration quality/cost tradeoff versus Base: +10 successes (52 vs 42) for roughly +12% service cost. Because competence is low and this is calibration, that is not a product claim.

## 7. Questions for Astra High

Give a hard recommendation, not a naming exercise.

1. Does this `ReferenceOnly` result materially weaken the **Semantic Inference Policy Compiler** thesis, or mainly falsify the current fixed-catalog **reference-preserving cost-reduction algorithm**? Explain precisely what was and was not tested.
2. Because `T = F`, is it correct that the immediate bottleneck is **not** merely the paired preservation constraint? What does the conventional-tuner failure tell us?
3. Rank the next moves:
   - A. Stop FEVER selector work and move directly to a **customer-like bounded enterprise document QA** workload where Base/F competence can be defined and test total economics there.
   - B. Run a **separate development-only Reference Decomposition** study using calibration/development data only, to learn which integrated interactions create the 10 F-only wins and whether a new predeclared policy family can improve the frontier; do not touch the frozen 600 held-out.
   - C. Treat `integrated` itself as the candidate product policy and validate `integrated vs Base` on a new competent workload, dropping the cost-compiler claim for now.
   - D. Move to the previously proposed cross-host transfer study despite the lack of a successful within-workload cheaper compiler candidate.
   - E. Intentionally narrow ExactScope to a qualification/configuration optimizer and stop pursuing the compiler category unless later evidence reopens it.
4. What should happen to the untouched 600 FEVER held-out? Keep it sealed for a future independently preregistered question, retire it from any new-rule inference because the calibration result has now influenced strategy, or use it only for the already-frozen question (which has stopped)? Be conservative about experiment integrity.
5. Should the preregistered 15% cost-reduction requirement remain untouched for future product validation? We will not retroactively relax it to rescue this result. If a different economic gate is defensible later, state what new workload/economic model would be required to justify it prospectively.
6. Is the non-nested success pattern (for example F-only 10 vs A+D-only 7) evidence that a **per-request adaptive router** should be revisited, or is that still premature/high-risk because it would introduce a learned routing problem before fixed-policy transfer is established?
7. Which exact next experiment would most efficiently raise or falsify these scores from the prior Astra review: Product thesis 45, Compiler thesis 38, Transfer evidence 10, Cross-runtime value 20, Commercial wedge 30, Category distinctness 25, Moat plausibility 25?
8. Give a clear **continue / pivot / narrow** verdict for ExactScope v1.1, with the minimum architecture that should ship if we still intend to produce a v1.1.
9. State what we should explicitly **not build next**.

## 8. Constraints that remain

- Do not touch or score the frozen 600 held-out merely to get an answer after `ReferenceOnly`.
- No second-model judge/verifier, reflection loop, retry-for-quality loop, or agent/test-time-scaling machinery.
- No new mandatory model or large index.
- Host continues to own retrieval execution, tokenizer/template, model inference, scheduling/batching, KV/prefix cache implementation, native constrained decoder implementation, speculation, and runtime fallback.
- ExactScope may own only incremental semantic/qualification value.
- No release/tag/push as stable based on this study.
- Do not rename a failed thesis into success. If the compiler category is not yet earned, say so.
