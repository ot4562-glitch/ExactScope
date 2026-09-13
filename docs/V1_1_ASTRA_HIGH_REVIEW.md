**ExactScope v1.1 — Independent skeptical review**
**Review date: 2026-09-13. Scope: the supplied review packet only.**

“Measured” below means reported in the packet; the underlying code and artifacts were not independently inspected. Recommendations specify proposed behavior, not verified implementation semantics. Confidence scores are subjective assessments of the evidence, not statistical probabilities.

**1. Executive verdict**

- **The strongest demonstrated result is rejection of an unsuccessful transfer.** The initial compiled policy scored 2/6 against fixed-max’s 3/6, and the qualification path withheld deployment. That supports experiment integrity, not answer amplification.
- **Compiler transfer remains unproved.** The first fresh experiment failed its stated gate. The revised compiler has synthetic regression coverage and an old-calibration debugging result, but no independent transfer result.
- **The original tie-break was underjustified, but the observed failure does not establish its cause.** Equal calibration accuracy is insufficient evidence of interchangeable behavior. Different success sets also do not prove that cost-based selection caused the held-out loss.
- **Paired preservation is a defensible provisional constraint for conservative cost reduction. It is not a validated statistical correction.** It can reject useful tradeoffs, overfit observed successes, and converge to fixed-max.
- **Six calibration items are inadequate for selecting among ten configurations.** A second 6+6 run could check the experiment machinery; it should not be presented as meaningful compiler validation.
- **The next experiment must establish both useful answers and useful selection.** Beating Base while merely selecting fixed-max would support the intervention bundle, not the compiler’s selection value.
- **The proposed product is currently a configuration qualification and compilation system.** Its differentiation would come from reliable transfer, low adoption cost, and accumulated qualification knowledge. The packet does not establish a moat.
- **Ship the smallest host-owned integration that can test demand.** Keep the semantic contract and qualification logic. Defer runtime machinery, native kernels, broad capability expansion, and universal performance language.

**2. What is genuinely strong today**

**Measured evidence: the release gate performed a useful rejection.** On the first fresh held-out split, the selected policy did not meet the fixed-max quality floor, and no deployable profile was emitted. This demonstrates one important behavior under an actual negative result.

**Reported design strength: selection and qualification are separated.** Calibration preceded held-out evaluation, the held-out compared only Base, fixed-max, and the previously selected policy, and no reselection occurred. That is a substantially better experimental structure than choosing the best configuration after examining test results.

**Reported integrity strength: the packet explicitly marks the revised rule as contaminated by the first held-out.** This is scientifically correct. Excluding those examples from a new test is necessary, although independent source or evidence overlap must also be considered.

**Measured engineering evidence: the focused suite reports 22/22 passing tests.** The added swapped-success and identical-success tests exercise the intended distinction. This supports implementation consistency with those examples. It does not establish statistical validity, robust generalization, or complete enforcement of every advertised invariant.

**Reported infrastructure improvements address real experiment failure modes.** Exclusive output locking, staged atomic publication, and canonical integer serialization reduce duplicate execution and artifact corruption. Their value belongs under reproducibility and operational integrity.

**Reported scope discipline is sound.** A bounded intervention matrix, unavailable-capability exclusion, and quarantine of negative materials reduce unnecessary search and shipping ownership. Retaining negative results is more credible than describing every intervention as an amplifier.

**Architecture judgment:** host ownership of retrieval execution, inference, scheduling, caching, and accelerators is a sensible starting boundary. Its integration advantage still needs measurement.

**3. What is weak / self-deceptive / overfit**

Ranked by severity:

1. **The scientific evidence is much smaller than the product language.**
   The only detailed fresh transfer result is a rejected six-item test on an oracle-page-pooled workload. It establishes neither representative retrieval performance nor cross-runtime improvement. The other historical signals are named without sufficient metrics or protocols in this packet to support stronger conclusions.

2. **The revised rule risks being narrated as a discovered remedy.**
   The failure prompted the rule, and recompilation selected A+D. Neither observation validates the remedy. The first held-out is development evidence for this rule permanently; a successful rerun would remain development evidence.

3. **The compiler objective is underspecified.**
   “Quality + total-cost distillation” leaves important choices unresolved: whether quality is a constraint or an objective, which costs count, what degradation is acceptable, and what happens when the reference itself is poor. A deterministic program can consistently optimize the wrong objective.

4. **The causal interpretation exceeds the reported comparison.**
   Integrated succeeded on one held-out item where Base and prompt_reduced failed. That establishes a configuration-level difference on that item. Attributing the difference specifically to an additional evidence path requires a controlled contrast isolating that path. Generation randomness and policy differences also need to be accounted for.

5. **Oracle-page pooling changes the problem being solved.**
   It can isolate evidence consumption under favorable retrieval conditions. It does not establish resilience to missed pages, irrelevant documents, stale sources, access restrictions, or conflicting authority—the conditions central to the proposed semantic product.

6. **Fixed-max has no demonstrated special statistical status.**
   More enabled interventions do not imply higher quality. Interactions can be harmful. A predeclared reference prevents opportunistic comparison, but it does not make the reference optimal, stable, or representative of a competent customer configuration.

7. **Tiny-sample selection can hide behind conservatism.**
   Preserving three reference successes is easy to describe as robust and easy to overfit. The rule constrains observed losses; it says little about unobserved failure modes.

8. **Cost and commercial value lack an operational definition.**
   Fewer prompt tokens are not automatically lower customer cost. Reduced latency on a small run may reflect cache state or timing noise. Compilation, integration, profile refresh, qualification, and rejected-output handling can erase serving savings.

9. **Runtime neutrality, footprint advantage, and moat remain hypotheses.**
   The packet contains no comparable multi-runtime integration measurements, footprint accounting, or customer economics sufficient to establish these claims.

**4. Compiler selection critique**

**Paired preservation is acceptable as a temporary policy constraint.** It answers a narrow question: “Can we find a cheaper configuration that loses none of the reference’s observed calibration successes?” It does not answer: “Which configuration has the highest expected quality?”

The old compiler’s error was treating a tiny aggregate tie as sufficient grounds for a confident cost decision. Different success sets expose uncertainty; they do not establish that either policy is intrinsically better. The new rule replaces that uncertainty with a conservative preference for the predeclared reference.

I would retain that constraint for the next experiment, explicitly describe the compiler as **reference-preserving cost reduction**, and avoid adding a broader statistical selection framework until this narrower proposition works.

The following are my recommended deterministic semantics.

**Inputs and identities**

Freeze before any scored calibration execution:

- The ordered calibration identities and equal item weights.
- The policy definitions, canonical policy IDs, Base `B`, and reference `F`.
- Model, runtime, tokenizer/template, retrieval/evidence, generation settings, capability qualifications, and scorer identities.
- Mandatory safety conditions and observation-validity rules.
- One total-cost function, its integer units, and all coefficients.
- The selection algorithm and tie-break order.

`F` must be an independently specified configuration. It must not mean “the best policy found on calibration.” If integrated is the present reference, name it accordingly; “fixed-max” must not imply optimality.

For calibration item `i` and policy `p`, define:

- `s[p,i] ∈ {0,1}`: task success under the frozen scorer.
- `c[p,i] ∈ ℕ₀`: cost under the frozen accounting function.
- `S[p] = Σᵢ s[p,i]`.
- `C[p] = Σᵢ c[p,i]`.
- `L[p,F] = Σᵢ s[F,i] × (1 − s[p,i])`.

The cost function must include the model call, policy-induced host work, and ExactScope work being claimed as part of the intervention. It must avoid charging twice for the same resource. Token counts and latency remain separately reported diagnostics.

**Observation handling**

1. A valid task failure scores zero. A rejected finalization also scores zero unless the frozen task explicitly defines abstention as a correct result.
2. Missing, corrupt, identity-mismatched, or duplicate observations invalidate the affected comparison. Do not silently drop rows.
3. Zero calls are admissible only under the declared completion capability. One call is admissible under generation. More than one call violates this product experiment’s contract.
4. Missing required capability qualification excludes a policy before execution.
5. A recorded mandatory safety violation makes the policy ineligible. Safety conditions cannot be invented after scoring.

**Reference admission**

Require complete, valid observations for Base and `F`, and require `F` to pass mandatory safety conditions.

For this provisional compiler, also require:

- `S[F] > 0`, preventing vacuous preservation.
- `S[F] ≥ S[B]`, preventing a visibly weaker calibration reference from becoming the cost-reduction target.

These are empirical admission checks, not claims of statistical equivalence. If either fails, return `NoQualifiedReference`; retain Base and emit no deployment profile.

**Candidate eligibility and selection**

A policy is reference-preserving exactly when:

`L[p,F] = 0`.

A cheaper candidate is eligible exactly when it:

- Has complete, valid observations.
- Passes all mandatory capability and safety gates.
- Is reference-preserving.
- Has `C[p] < C[F]`.

Among eligible cheaper candidates, select by this lexicographic order:

1. Lowest `C[p]`.
2. Highest `S[p]`.
3. Lowest canonical policy ID under a frozen bytewise ordering.

If no cheaper candidate qualifies, return `ReferenceOnly` with `F`.

Equal-cost candidates do not displace the reference. Prompt tokens and latency do not become improvised additional tie-breakers.

This makes quality an explicit constraint and cost the optimization objective. Extra calibration successes are not treated as proven population gains.

**Profile and qualification semantics**

Compilation produces an immutable **candidate** profile with its full qualification scope. Held-out evaluation may only qualify or reject that exact candidate. It must never choose the runner-up, replace the candidate with fixed-max, or alter a threshold.

`ReferenceOnly` may qualify the reference configuration, but it must not be counted as evidence that compiler selection creates value.

**Should one reference success be traded for one new success?**

For this provisional compiler: **no**, regardless of aggregate equality. The reason is the chosen preservation objective and insufficient evidence, not an assertion that all such trades are harmful.

A later expected-quality optimizer could permit trades under a preregistered noninferiority margin and independently assessed paired uncertainty. That would be a different selection policy requiring fresh validation. There is no defensible universal rule such as “two new wins compensate for one lost win.”

**Is another reference or dominance concept better?**

Keep two distinct comparisons:

- Base represents the current host configuration.
- `F` represents a predeclared, competent intervention configuration.

For commercial validation, Base must be a credible customer configuration. An artificially weak Base makes improvement uninformative.

Do not require preservation of the union of every policy’s successes. That creates an unattainable oracle-like target and expands selection dependence on the entire matrix.

**Are the current matrix policies redundant?**

The packet cannot establish this. Before scoring, compare executable policy definitions: retrieval request, candidate budget, evidence transformation, prompt, contract, backend settings, and completion behavior. Identical definitions under the qualified host should be merged.

Identical outputs or success vectors on a small calibration set are insufficient evidence of semantic redundancy.

**5. Next fresh experiment**

The highest-information next study is a larger, fresh, same-model FEVER experiment testing the revised compiler’s narrow proposition. Changing task, model, and selector together would make the next result harder to interpret.

This remains a controlled research study under oracle-page pooling. Passing it would authorize a subsequent customer-like retrieval experiment, not release qualification.

**Sample and execution budget**

- **Calibration:** 120 fresh claims, balanced at 40 per label.
- **Held-out:** 600 fresh claims drawn by simple random sampling without replacement from a frozen, declared evaluation frame.
- **Calibration policies:** the ten executable policies currently listed in the packet, subject only to definition-based deduplication before scoring.
- **Held-out policies:** Base, predeclared `F`, and the compiled policy.
- **Maximum:** 1,200 calibration plus 1,800 held-out policy-item observations; at most 3,000 generation calls under the one-call limit.

The held-out should represent the declared population rather than being forced to match calibration’s label quotas. Report its realized label composition and label-specific outcomes.

This is a concrete budget compromise, not a universal power guarantee. Small effects or many paired disagreements can still produce an inconclusive result. Another 6+6 run offers too little information about selection to justify using it as the next scientific milestone.

**Freshness and sampling unit**

Exclude the first transfer’s 12 source IDs and any other examples used to develop the revised selector.

Also freeze a near-duplicate and shared-evidence grouping rule. Construct a frame with at most one evaluation claim per declared group, and keep calibration and held-out groups disjoint. Different claim IDs alone do not establish independence from closely related evidence.

Record the resulting frame size `N`. The statistical gates below apply to this finite, declared frame. They do not automatically generalize to all FEVER claims or production traffic.

**Freeze before scoring**

Freeze the sampling frame and seed, policy definitions, reference, selector, scorer, safety rules, model/runtime settings, evidence construction, cost function, practical-effect thresholds, timing procedure, and analysis code.

Use one declared production-like execution regime for primary latency and cost reporting. Specify warm-up, cache state, concurrency, and counterbalanced policy order. No retries or output selection based on answer quality.

Gold labels remain unavailable to runners. Held-out labels remain unavailable to compiler selection.

**Calibration decision**

Run the complete frozen calibration matrix and apply the exact compiler semantics above.

- If the reference is invalid or fails admission, stop with no profile.
- If the result is `ReferenceOnly`, stop the main compiler-value study and record failure to demonstrate cost reduction at calibration. A separately labelled reference-versus-Base study may still be useful.
- Otherwise freeze the candidate artifact and execute the three held-out configurations.

**Primary paired analyses**

Report every comparison using the four paired outcome counts: both correct, both wrong, candidate-only correct, and comparator-only correct. Aggregate accuracy alone is insufficient.

For held-out size `n = 600`, define:

- `g`: compiled correct and Base wrong.
- `b`: compiled wrong and Base correct.
- `r`: compiled wrong and `F` correct.

Use exact finite-population bounds, appropriate to the specified sampling design. Let:

`X ~ Hypergeometric(N, K, n)`.

For observed count `k`, define:

- `Lower(k) = min {K : Pr(X ≥ k) > α} / N`.
- `Upper(k) = max {K : Pr(X ≤ k) > α} / N`.

Search integer `K` from `0` through `N`, with `α = 0.05/3`. Use exact rational tail comparisons and fixed endpoint handling.

Apply these three one-sided bounds to:

- `Lower(g)`.
- `Upper(b)`.
- `Upper(r)`.

Their simultaneous coverage is at least 95% by the union bound. Independence between these three counts is unnecessary.

**Held-out success requires all of the following**

1. **Meaningful improvement over Base:**
   `Lower(g) − Upper(b) ≥ 0.03`.
   The study must support at least a three-percentage-point accuracy improvement in the declared frame.

2. **Bounded reference regression:**
   `Upper(r) ≤ 0.02`.
   This bounds the frequency of losing a reference success at two percentage points. Candidate-only wins do not offset these regressions.

3. **Useful cost reduction:**
   Compiled total serving cost is at least 15% below `F` under the frozen accounting function.

4. **Useful comparison with the current stack:**
   Compiled total serving cost does not exceed Base’s, and measured end-to-end p95 latency is no more than 5% above Base’s under the frozen execution protocol.

5. **Contract compliance:**
   No mandatory safety or identity gate fails, and no observation violates the zero-or-one-call limit.

The 3%, 2%, 15%, and 5% thresholds are **proposed product requirements**, not quantities inferred from the first experiment. They should be accepted or revised before any new scoring, based on intended customer value.

Exact calibration preservation and bounded held-out regression serve different purposes. Calibration constrains selection; held-out estimates whether that choice generalizes within a declared tolerance.

Latency and cost thresholds here are operational gates for the specified measurement regime. This single study should not be used to advertise precise production latency percentiles.

**Additional reporting**

Report:

- Base, `F`, and compiled accuracy.
- Paired wins and losses against both comparators.
- Per-label outcomes and disagreements.
- Calls, prompt and output tokens, host work, preparation/finalization time, and total cost.
- Calibration cost and the serving volume needed to recover it.
- The reference’s improvement over Base, descriptively, to expose how much value comes from the intervention bundle itself.

If per-query savings against Base are `d > 0`, report break-even volume as:

`ceil((calibration + qualification + integration cost) / d)`.

Use consistent monetary or resource units. If `d ≤ 0`, there is no serving-cost payback; any business case must rest on separately valued quality improvement.

**Stop conditions and interpretation**

- Identity leakage, scorer defects, or systematic runtime invalidity invalidate the experiment. Do not repair them selectively and continue scoring the same qualification set.
- Failure of a quality or cost gate emits no deployment profile. Do not substitute another policy.
- Inconclusive bounds count as **qualification failure**, not proof that the method is harmful.
- Any outcome-motivated algorithm change contaminates this held-out for validating that change.
- No optional sample extension after viewing scores.

If `F` beats Base and the compiler cannot deliver material savings while retaining quality, the intervention bundle has evidence and the compiler’s incremental value does not.

Repeated `ReferenceOnly` outcomes would be strong evidence that the preservation constraint eliminates most useful optimization. A fresh, adequately measured failure to reduce cost while retaining reference quality should end the present compiler-value claim for this workload. It would not logically disprove every possible future configuration optimizer.

After a pass, the next test should freeze the compiler and move to one customer-like task with real retrieval. A cross-runtime test follows with the semantic task held stable and host qualification changed.

**6. Product/moat critique**

**Current category judgment:** this is a constrained configuration optimizer with qualification artifacts and semantic enforcement. That is a coherent product shape, but “Harness Distillation” does not by itself create a distinct category.

The system becomes differentiated if it repeatedly delivers all three:

- Better task outcomes than a competent existing stack.
- Lower operating cost than the best practical fixed intervention bundle.
- Low enough integration and requalification effort that customers keep using it.

Without those results, the description collapses into prompt and retrieval configuration tuning with stronger testing.

The hardest plausible asset to copy is the accumulated relationship between **workload characteristics, host capabilities, intervention interactions, and fresh transfer outcomes**, backed by reproducible qualification procedures. That is a moat hypothesis. The packet does not establish the breadth, exclusivity, or predictive value of such an asset.

**Best first workload — speculation:** a high-volume, bounded enterprise document-answering service whose model is pinned by deployment constraints and whose answers can be checked against authoritative document spans. The buyer is the team accountable for answer quality and serving cost.

This workload offers:

- Repeated tasks over which calibration can amortize.
- Auditable answers and identifiable evidence.
- A real reason to improve the existing model.
- A bounded integration where authority, coverage, and freshness semantics may matter.

Do not choose safety-critical autonomous decisions as the initial wedge. Do not assume customers will value runtime neutrality before one integration is useful.

The commercial experiment must compare against a competent host configuration and include a better-model alternative where the customer can use one. “Same model” is only commercially valuable when retaining that model solves an actual constraint or wins on total economics.

**Claims to weaken now**

- Treat “Same model. Same runtime. Better answer.” as a research objective.
- Replace unqualified “runtime-neutral” claims with the exact qualified hosts and portability evidence.
- Describe the current profile as an immutable compiled configuration with declared qualification scope.
- Describe J as proof-based completion only for cases covered by an explicit, verifiable rule.
- Describe I as admission/compatibility, consistent with the packet.
- Avoid calling the compiler loop a moat until accumulated evidence creates a measurable selection advantage.

A commercially meaningful result would be a preregistered customer-like evaluation meeting the proposed quality and cost gates, followed by prospective use with low integration effort and a credible calibration payback period. A single favorable benchmark slice is insufficient.

**7. Architecture/size critique**

`prepare -> Complete | Generate -> finalize` is a sensible small semantic boundary. Its usefulness depends on precise failure and capability behavior.

**Keep**

- Immutable profile and qualification identities.
- Evidence authority, freshness, conflict, and coverage semantics where they change admission or answer requirements.
- Deterministic evidence shaping.
- Explicit answer contracts.
- Proof-based completion for narrowly defined cases.
- Strict finalization.
- The cold compiler and auditable qualification records.

**Make these semantics explicit**

- `Complete` must carry the answer and a verifier-checkable justification tied to the current query and evidence. Reusing a profile does not prove a new answer.
- `Generate` must carry the transformed request, answer contract, required capabilities, and profile identity.
- `finalize` must be deterministic for the same contract and output. Rejection must not silently initiate another model call.
- Unsupported capability, failed context admission, or stale qualification needs an explicit error outcome. Neither successful branch should imply admission succeeded when it did not.
- `Accept` means the output meets the checks actually implemented. Structural conformance does not establish truth. Semantic acceptance claims need verifiable evidence.

A small API should expose these conditions through a result/error mechanism rather than expand into orchestration.

**Push to the host**

- Retrieval execution and access control.
- Tokenization, chat-template rendering, and exact token accounting.
- Scheduling, batching, runtime loading, and accelerator selection.
- Cache allocation, eviction, and native prefix reuse.
- Constrained decoding execution.
- Retry, fallback, and rejected-output handling.

ExactScope can declare requirements and stable identities; the host performs the work.

**Native code does not currently earn a required place based on this packet.** There is no reported measurement showing that a native ExactScope component materially improves end-to-end outcomes or reduces deployment burden. Prefer a native-free initial surface. Reconsider a kernel only after profiling identifies a material bottleneck that it can resolve without unacceptable packaging cost.

**Keep size accounting honest.** Report a small vector rather than one blended footprint score:

- Download/distribution bytes.
- Incremental installed dependencies.
- Incremental post-link contribution where relevant.
- Cold-start time and peak resident memory.
- Per-request CPU, memory, and latency.
- Integration and maintenance hours.

Use the customer’s actual dependency baseline. A runtime dependency already present may have no incremental download cost for that host; it still belongs in the dependency declaration.

Choose among implementations using deployment limits plus total lifecycle cost. A smaller archive does not compensate automatically for extra engineering ownership or worse serving behavior.

**8. Top 5 decisions to make next**

1. **Commit to one compiler objective.**
   Adopt reference-preserving cost reduction for the next proof, with explicit deterministic semantics and `ReferenceOnly` as a distinct outcome.

2. **Freeze and run one sufficiently informative fresh experiment.**
   Use the proposed 120-calibration/600-held-out budget, or choose a different budget through a prospective precision calculation. Stop treating six-item transfer runs as substantive validation.

3. **Make fixed-max a serious baseline.**
   Freeze its executable meaning, deduplicate the matrix by definition, and require the compiler to demonstrate incremental value over it.

4. **Choose a customer workload before expanding the material set.**
   Identify an existing pinned-model service, its competent baseline, acceptable error tradeoffs, serving volume, and integration budget.

5. **Constrain the shipping boundary.**
   Implement the smallest semantic contract around the host, and collect evidence before committing to native code or runtime-specific machinery.

**9. Things not to do yet**

- Do not use the first held-out to validate paired preservation or A+D.
- Do not add item-, benchmark-, or model-specific exceptions to recover observed failures.
- Do not broaden the policy matrix, add per-query routing, or introduce adaptive statistical selection before the current objective passes a fresh test.
- Do not add retry, reflection, judge, or agent loops to rescue one-call results.
- Do not reactivate quarantined C or L without a separate, predeclared reason.
- Do not build a runtime, retrieval engine, tokenizer, cache manager, scheduler, or speculation layer.
- Do not claim zero-call completion correctness from a profile identity alone.
- Do not optimize package bytes before measuring adoption and lifecycle cost.
- Do not describe fixed-max selection as successful distillation.
- Do not claim cross-runtime transfer from separate runtime-specific successes.
- Do not use synthetic contract tests as evidence of real answer improvement.
- Do not qualify a release from an oracle-page-pooled FEVER result.

**10. Final confidence table**

These scores assess how well the present evidence supports each proposition.

| Proposition | Confidence, 0–100 | Reason |
|---|---:|---|
| Product thesis | 40 | Improving a pinned host stack through semantic intervention is plausible, but the packet does not establish representative quality gains and favorable total economics together. |
| Compiler thesis | 30 | Frozen selection and rejection form a credible experiment framework, while the revised selector remains unvalidated and may provide little value beyond the reference. |
| Transfer evidence | 10 | The only detailed fresh compiler transfer failed qualification, and the replacement rule has no independent fresh result. |
| Cross-runtime value | 20 | Host separation is sensible and runtime-specific signals are reported, but reusable selection knowledge across runtimes is not demonstrated here. |
| Footprint strategy | 65 | Delegating runtime machinery to the host is a sound design direction, although comparative footprint and integration measurements are absent. |
| Commercial wedge | 25 | Bounded document answering on a pinned model is a plausible initial market, but customer demand, competitive advantage, and payback remain speculative. |
