**Verdict: NARROW ExactScope v1.1 to a qualification/configuration optimizer, and pivot the next empirical test to a bounded enterprise document QA workload with a defensible competence floor.** Continue the broader compiler thesis only as a research hypothesis. Do not continue the stopped FEVER selector study or prioritize cross-host transfer.

This review uses only the supplied packet. Its results support a valid calibration stop, not qualification or a general finding that semantic policies cannot improve inference.

1. **What the result weakens—and what it actually tested**

   **Evidence:** The experiment evaluated ten frozen policies on 120 calibration claims within one controlled oracle-page-pooled FEVER workload, one model/quantization, and one Windows runtime. No cheaper candidate preserved every observed F success. More strongly, no cheaper candidate matched F’s aggregate success count. All candidates also fell short of the descriptive 15% calibration cost reduction.

   That decisively establishes **failure to produce an eligible candidate in this catalog under this calibration protocol**. It does not establish population-wide impossibility for these policies, much less for other policy families or workloads. The 600-item held-out question was never evaluated.

   The study also could not test preservation of a *competent* reference in the intended product sense: absolute competence was not established, and the study was prospectively classified as algorithm-diagnostic-only.

   **Recommendation:** Treat this as a material downgrade to the evidence supporting the compiler thesis, because its proposed first conservative algorithm failed to produce a candidate. The broader thesis was not directly falsified: policy generation, useful transfer, incremental value over conventional tuning, and commercially meaningful economics remain unproven. Those untested possibilities are research questions, not grounds for retaining the compiler category in product claims.

   The strongest defensible conclusion is: **the frozen fixed-catalog algorithm returned its valid abstention outcome; the intended useful operating point was not demonstrated.** A correct stop validates the discipline of the qualification process, not the economic value of the optimizer.

2. **Why the bottleneck is not merely paired preservation**

   **Evidence:** `T = F` means relaxing the paired success-preservation condition to the frozen aggregate-quality condition would still have selected no cheaper policy. For example, A+D saves 10.20% of measured service time but loses ten F successes and gains seven, ending three successes below F.

   Thus, on the observed calibration frontier, there are two separate obstacles:

   - No cheaper candidate satisfies even the aggregate quality constraint.
   - No candidate offers the targeted 15% cost reduction, regardless of quality.

   **Recommendation:** Do not spend the next iteration relaxing or refining the paired selector. The immediate empirical bottleneck is the candidate frontier exposed by this catalog and workload. The conventional tuner’s failure does **not** show that paired preservation is redundant generally, nor that ExactScope outperforms conventional tuning. Here, both approaches decline to select a cheaper candidate, so their incremental value was not tested on held-out data.

3. **Ranking the next moves**

   These options mix strategic decisions and experiments. My priority order is **E → A → C → B → D**, with C implemented inside A rather than as another platform effort.

   - **First — E: Narrow the product claim now.** Describe ExactScope as a constrained configuration optimizer with semantic enforcement and qualification records. Keep “Semantic Inference Policy Compiler” as an internal hypothesis with explicit evidence requirements. This aligns the claimed product with what has actually been built and avoids committing architecture to an unearned category.
   - **Second — A: Make competent enterprise document QA the next empirical priority.** A bounded, customer-like task can test whether a policy delivers useful answers, acceptable failures, and favorable total economics. Establish that the task and reference are viable before investing in another selector study.
   - **Third — C: Test an integrated-style policy against Base within that workload.** Treat it as a candidate quality/cost tradeoff. Define and freeze its workload-specific meaning prospectively; the packet does not establish that the FEVER configuration transfers unchanged. Success could support a useful semantic configuration product without establishing cost compilation.
   - **Fourth — B: Permit only a bounded development investigation.** It may help explain interactions or propose a new family, but it should not delay the competence/economics test. Use calibration or explicitly designated development data only, with a fixed investigation budget and a concrete deliverable: a small set of testable intervention hypotheses.
   - **Last — D: Defer cross-host transfer.** First establish a useful source profile. Transferring an unqualified policy could measure consistency without demonstrating customer value or cheaper reference-preserving execution.

   **Evidence correction relevant to B:** The packet’s “10 F-only wins” wording is misleading if it refers to Base. F has **13 successes where Base fails**, while Base has three where F fails: the net gain is ten. F-only ten versus alternative-only seven describes A+D. Decomposition must distinguish those sets. Success-set differences alone do not identify which intervention caused an outcome.

4. **Disposition of the untouched 600 FEVER items**

   **Evidence:** The packet says the runner has neither scored nor opened them. Nevertheless, the calibration result has already informed strategy, and the frozen protocol permits held-out execution only if P exists. P does not exist.

   **Recommendation:** **Keep the 600 sealed as the held-out artifact of the stopped study, and retire them from confirmatory inference under new rules.** They should remain associated with the original frozen question, which has stopped and therefore does not authorize scoring.

   The reason is conservative control of experiment reuse—not a claim that the labels have already leaked. A future protocol could theoretically address reuse explicitly, but that complexity is unnecessary here. Use a genuinely fresh, prospectively defined cohort for a revised policy family or question, preserving the required identity/evidence grouping and exclusions.

   Do not run F/T alone, recast the sample as a new F-versus-Base test, or use it to guide policy development. Preserve the stop report and its `NOT_EVALUATED_REFERENCE_ONLY` verdicts.

5. **The 15% cost-reduction requirement**

   **Evidence:** The cheapest observed policy saved 11.75% of calibration service time relative to F. That is not a held-out product-gate failure, because the gate was never evaluated, but it supplies no evidence that the catalog meets the target. Service time at single concurrency is also a narrower quantity than total customer economics.

   **Recommendation:** Keep the existing 15% requirement untouched for Stage 1 and retain it as the default for a future claim of materially cheaper reference-preserving execution. Do not select a smaller threshold because the observed savings happened to fall below 15%.

   A different future economic gate is defensible only with a **new, prospectively specified workload and economic model**. That model should establish:

   - Required answer correctness, evidence support, abstention behavior, and tolerable serious errors.
   - Actual demand, concurrency, infrastructure charges, and latency requirements.
   - Retrieval and inference costs, incremental policy overhead, and any material human review or escalation costs.
   - The customer’s minimum worthwhile improvement, including implementation and operating burden.

   A quality-improving policy that costs more to serve could still be useful if it reduces total handling cost or improves a valued outcome sufficiently. That would validate a different product proposition. Freeze its metric, threshold, and analysis before confirmatory outcomes are available; do not relabel it as success on the current cost-reduction claim.

6. **Whether to revisit per-request adaptive routing**

   **Evidence:** Non-nested success sets demonstrate outcome complementarity. For F and A+D, an oracle choosing the successful policy on each calibration item would obtain 59 successes: F’s 52 plus A+D’s seven additional successes. That is an in-sample oracle calculation, not an executable router result.

   The packet provides no evidence that permitted pre-inference features can predict the better policy, that such predictions generalize, or that routing overhead leaves worthwhile savings.

   **Recommendation:** Adaptive routing is premature as the next implementation. A permitted development analysis could ask whether cheap, pre-inference features explain disagreements, but it must remain hypothesis generation. Any subsequent router would need its own frozen training procedure, independent evaluation, competence gates, and complete cost accounting.

   Fixed-policy transfer is not a logical prerequisite for all routing research. Here, however, adding a learned selection problem before establishing competent fixed-policy value creates another source of uncertainty without resolving the existing one. Do not implement run-both-and-choose, a second-model judge, reflection, or quality retries.

7. **The exact next experiment and what it can change**

   **Recommendation:** Run one **prospective, competence-gated enterprise document QA experiment**, with integrated-versus-Base product value as the primary comparison and reference-preserving cost reduction as a separately preregistered, conditional comparison.

   Make the experiment concrete as follows:

   - **Bound the task.** Choose one document collection and a defined population of questions requiring a supported answer with citations or an abstention. Include answerable, unanswerable, and materially ambiguous cases. Use actual host retrieval rather than an oracle evidence pool.
   - **Establish feasibility on development data.** Define competence with the workload owner before confirmatory scoring: correctness, evidential support, abstention, and unacceptable errors. Establish reference eligibility and define how an inadequate Base will be handled. If no credible reference exists, stop before optimizer qualification.
   - **Freeze a small intervention family.** Specify Base, the integrated-style reference, allowed policies, mandatory semantics, selector P, comparator T, tie breaks, model/runtime, retrieval configuration, and cost/timing protocol. Keep the existing host ownership boundaries.
   - **Freeze independent evaluation.** Define grouping to prevent relevant document/question leakage, sampling, sample size, uncertainty methods, and acceptance thresholds. Human adjudication may evaluate blinded outputs offline under a fixed rubric; it must not become an additional runtime model or answer-improvement loop.
   - **Preregister two distinct questions.** Evaluate integrated versus Base for competence and customer economics. Separately, admit a cost-reduction P only through its frozen calibration rule and evaluate unique eligible B/F/P/T arms under predefined comparisons. If P is absent, the cost-reduction branch stops. The F-versus-Base comparison may proceed only because this new study authorized it independently before calibration—not as a rescue decision.
   - **Make the product decision on held-out results.** A calibration leader is insufficient. Qualification requires the competence and economic gates, with uncertainty handled as preregistered.

   **Evidence limits and score implications:** The packet supplies no calibration for converting results into numerical score changes. Treat the prior scores as judgment labels, not probabilities, and update them by dimension:

   - **Product thesis — 45:** Competent held-out performance with worthwhile total economics would strengthen it. No viable reference, or no useful policy benefit under credible economics, would weaken the tested product proposition.
   - **Compiler thesis — 38:** A cheaper P that preserves the qualified reference under the frozen gates would strengthen the algorithmic premise. Demonstrating a meaningful benefit over T would support the distinctive selector contribution. An F-versus-Base quality gain alone would not establish compilation.
   - **Transfer evidence — 10:** This single-workload result should not materially raise it. The next evidence would require freezing the learned profile or explicitly defined compilation procedure and applying it to a separate target without target-outcome-driven adjustment.
   - **Cross-runtime value — 20:** Leave it unresolved. A later matched comparison across available runtimes is needed; the earlier unmatched development transfer cannot substitute.
   - **Commercial wedge — 30:** Representative questions, credible costs, and a customer-defined acceptance threshold would strengthen evidence of usefulness. Customer adoption or willingness to pay remains a separate question.
   - **Category distinctness — 25:** Strengthen it only if ExactScope contributes measurable value beyond conventional tuning and host-native mechanisms. Producing a profile record alone does not establish a separate category.
   - **Moat plausibility — 25:** One benchmark win should have little effect. Repeated transferable advantage or evidence of a difficult-to-reproduce capability would be needed; neither appears in this packet.

   This experiment efficiently addresses the nearest uncertainties: competence, product value, and whether a useful policy frontier exists. It should not be expanded merely to produce movement in all seven scores.

8. **Continue / pivot / narrow and the minimum v1.1 architecture**

   **Recommendation: NARROW the product; PIVOT the workload; CONTINUE bounded research.** Do not continue pursuing the compiler category as an established identity.

   If v1.1 is still produced, its minimum architecture should contain:

   - A small declarative policy format for allowed semantic settings above host-owned mechanisms.
   - Validation of mandatory semantic constraints and compatibility with a bound model/runtime/workload configuration.
   - A deterministic runner for finite policy catalogs, including the conventional comparator and explicit stop/abstention outcomes.
   - Immutable experiment and qualification records binding policies, versions, data identifiers, metrics, gates, and verdicts.
   - An exportable execution profile whose status clearly distinguishes development, diagnostic, and qualified use.

   Keep retrieval execution, tokenization/templates, inference, scheduling/batching, caching, constrained decoding, speculation, and runtime fallback with the host.

   The present FEVER study can supply a diagnostic stop record. **It cannot supply a qualified deployment profile or justify a stable release/tag/push.** If engineering distribution proceeds for other reasons, its qualification claims must remain bounded by independently established evidence.

9. **What explicitly not to build next**

   **Recommendation:**

   - No FEVER held-out rescue, F/T-only continuation, threshold relaxation, sample extension, or held-out policy reselection.
   - No per-request learned router or policy ensemble as the next product feature.
   - No second-model judge/verifier, reflection, quality retry, or agent/test-time-scaling machinery.
   - No mandatory new model, large index, or replacement retrieval/runtime stack.
   - No cross-host transfer program before a useful source policy exists.
   - No broad policy-search platform or compiler language before a small catalog demonstrates incremental value.
   - No new ownership of host scheduling, cache implementations, native decoding, speculation, or fallback.
   - No category or moat claim inferred from sound experiment bookkeeping.
   - No renaming of this stopped result into a successful cost compiler.

   The next commitment should be a bounded test of competent customer value, with failure allowed to end or further narrow the effort. The experiment-integrity machinery has already demonstrated its most important behavior here: it stopped when the frozen rules required it.
