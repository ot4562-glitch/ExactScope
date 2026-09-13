# ExactScope v1.1 — Astra High review packet

Status: **historical review input; active local research remains unreleased**
Prepared: **2026-09-13**
Purpose: provide a stable, file-based review target for an independent Astra High critique. This packet is not a product claim and must not be treated as release qualification.

> **After-review note:** the resulting critique is [`V1_1_ASTRA_HIGH_REVIEW.md`](V1_1_ASTRA_HIGH_REVIEW.md). Current product/compiler decisions in `V1_1_PRODUCT_DIFFERENTIATION.md`, `V1_1_RESEARCH_STATUS.md`, `V1_1_EXPERIMENT_PROGRAM.md`, `ROADMAP.md`, and `DECISIONS.md` supersede this packet where wording or planned next steps differ. Preserve this file as the immutable review input rather than rewriting it to match later decisions.

## 1. Review role

Act as the most skeptical senior research/product/architecture reviewer on ExactScope v1.1. Do not optimize for agreement with the current implementation. Look for conceptual errors, hidden overfitting, invalid inference, missing baselines, bad product boundaries, weak commercial assumptions, and unnecessarily large implementation ownership.

The desired outcome is not a patch. It is a sharp written review that identifies what is actually defensible, what is not, what the next highest-information experiment should be, and what should be deleted or postponed.

Do **not** use held-out results to invent a rule that merely makes the already-observed held-out pass. If a proposed algorithmic change is motivated by a failed held-out experiment, explicitly classify the old held-out as contaminated for validating that change and require a new fresh transfer proof.

## 2. Product thesis

Current intended product category:

> ExactScope is a runtime-neutral semantic/inference-path compiler that improves an existing model/runtime/retrieval stack without replacing the model or adding routine extra model calls.

Internal shorthand:

> **Same model. Same runtime. Better answer.**

This is a research target, not a universal measured claim.

Cold path:

```text
frozen representative calibration
  -> bounded justified intervention matrix
  -> causal / paired checks
  -> quality + total-cost distillation
  -> immutable Amplifier Profile
  -> frozen fresh held-out transfer gate
```

Hot path:

```text
qualified Amplifier Profile
  -> prepare(query, host_evidence, host_profile)
  -> Complete | Generate
  -> host inference only if Generate
  -> finalize(contract, model_output)
  -> Accept | Reject
```

Host owns retrieval execution, tokenizer/chat template, inference runtime, scheduling, KV/prefix cache machinery, speculation and accelerators. ExactScope should own only incremental semantic value: authority/coverage/freshness/conflict semantics, evidence shaping, proof-based completion, answer contracts, strict finalization, capability identities and the cold compiler.

The intended moat is not package byte size or any single A/B/D/G/H/etc. trick. The moat hypothesis is **cross-runtime qualification/selection knowledge + the compiler/evaluation loop**. Low footprint and low integration cost are the distribution weapon.

## 3. Current material shorthand

Important current materials:

- A — retrieval query / model instruction separation
- B — bounded candidate overfetch
- C — global snippet selection; **quarantined negative**
- D — precision complete-span projection
- G — typed semantic answer contract
- H — backend-native constrained-output surface
- I — host token/context-fit negotiation; compatibility/admission, not established quality amplification
- J — deterministic host completion / zero-call
- K — stable prefix identity + qualified host-native prefix/KV reuse
- L — n-gram/prompt-lookup speculation; **quarantined/off** for the current short workload

Previously measured signals include A×B FEVER, B×D NQ/Hotpot, synthetic G×H, real ORT I, qualified K on Qwen, and a Qwen Hotpot20 attach bundle. These results are research evidence, not a universal product guarantee. Read the source docs listed below for exact metrics and caveats.

## 4. Implemented compiler/product slice

Current implementation files:

- `tools/harness_distillation.py`
- `tools/exactscope_calibrate.py`
- `adapters/bridge/compiled_profile.py`
- `benchmarks/harness_distillation_fever.py`
- `tools/test_harness_distillation.py`
- `tools/test_exactscope_calibrate.py`
- `tools/test_bridge_compiled_profile.py`
- `benchmarks/test_harness_distillation_fever.py`

The candidate matrix is intentionally bounded, not 2^N. The current real-host executable slice includes Base, A, B, D, A+B, A+D, B+D, A+B+D, prompt_reduced and integrated when the host lacks I/G/H/J/K qualifications. Capability-unavailable policies are not executed.

The compiler already enforces:

- frozen disjoint calibration / held-out identities;
- zero-or-one generation call observations;
- fail-closed host qualification identities;
- safety/regression gates;
- K output-parity qualification where relevant;
- immutable candidate profile output;
- no held-out reselection;
- held-out comparison only against Base, predeclared fixed-max and the already-compiled policy;
- deployment profile emitted only if held-out qualification passes.

Latest focused tests after the changes below: **22/22 PASS** across the harness compiler, calibration CLI, FEVER driver and compiled-profile bridge tests.

## 5. First fresh transfer attempt — important negative result

A fresh balanced FEVER transfer experiment was frozen before scoring. This is oracle-page-pooled research data and **not release qualification**.

First Qwen 3.5 0.8B Q4 calibration run:

- calibration split: 6 items, balanced by FEVER label;
- held-out split: 6 disjoint fresh items, balanced by label;
- calibration matrix: 10 policies × 6 items = 60 observations;
- calibration and held-out model runners did not receive gold labels;
- policy order per item was deterministic but item-specific;
- held-out remained untouched until compile was complete.

Initial compiler result from calibration only:

- Base: 2/6
- prompt_reduced: 3/6
- integrated: 3/6
- compiler selected **prompt_reduced** because it tied on aggregate success but used fewer prompt tokens / less latency.

Fresh held-out result with **no reselection**:

- Base: 2/6
- prompt_reduced (compiled): 2/6
- integrated (predeclared fixed-max): 3/6
- qualification: **REJECTED**
- rejection reason: `compiled-policy-fell-below-fixed-max-quality-floor`

This is an important positive property of the system: the failed transfer did **not** emit a deployable `amplifier-profile.json`.

Artifact roots:

- calibration run: `target/harness-fever-transfer-20260912-qwen-calibration-r3/`
- calibration request: `target/harness-fever-transfer-20260912-qwen-calibration-request-r3.json`
- initial compile: `target/harness-fever-transfer-20260912-qwen-compile-r3/`
- held-out run: `target/harness-fever-transfer-20260912-qwen-heldout-r3/`
- held-out request: `target/harness-fever-transfer-20260912-qwen-heldout-request-r3.json`
- rejected qualification bundle: `target/harness-fever-transfer-20260912-qwen-qualified-r3/`

## 6. What the failed transfer exposed

The calibration aggregate tie was misleading. `prompt_reduced` and `integrated` were both 3/6, but their success sets were not identical:

- one calibration item succeeded only under `prompt_reduced`;
- one calibration item succeeded only under `integrated`.

Therefore the old compiler implicitly treated **equal success count as quality equivalence**, then let cost break the tie. That is too strong an inference for a tiny calibration split.

On the fresh held-out split, one item (`fever-dev:202468`) succeeded under integrated but failed under Base and prompt_reduced. Thus the additional evidence path had real value on that fresh item.

## 7. Post-failure compiler change — NOT YET independently validated

After seeing the failed held-out transfer, the compiler was changed conservatively. Because this rule was motivated after observing held-out failure, the old held-out is now **contaminated for validating this change**. Re-running the changed compiler on the old held-out cannot count as proof.

New deterministic calibration-only rule:

> The predeclared fixed-max policy is a paired quality reference. A lower-cost candidate may be selected only if it preserves every calibration item on which fixed-max succeeded. Aggregate equality is insufficient when the success sets differ.

Implementation name/concept: paired fixed-max calibration preservation.

This is deliberately conservative for the v0.1 skeleton:

- no benchmark-specific branch;
- no model-name branch;
- no hidden LLM judge;
- no retry/reflection/agent loop;
- no per-query adaptive selector;
- no held-out information used inside compilation.

Two synthetic regression tests were added:

1. equal success count but swapped success item -> cheap candidate must be rejected;
2. identical fixed-max success set with lower cost -> cheap candidate may still win.

All focused tests pass.

When the **old calibration data only** is recompiled with the new rule, `prompt_reduced` is rejected because it loses one fixed-max calibration success, and the compiler selects **A+D**. This is a debugging observation only, not new scientific evidence, because the rule was designed after the first held-out failure.

Debug compile artifact:

- `target/harness-fever-transfer-20260912-qwen-compile-r4-reference-gate/`

## 8. Additional harness hardening completed during the real run

The real experiment also exposed infrastructure defects that were fixed:

- cross-process exclusive output lock added so the same calibration/held-out identity cannot accidentally launch duplicate model runs;
- completed run artifacts are staged then atomically renamed into place;
- strict canonical JSON incompatibility with float latency fields fixed by recording integer milliseconds at the FEVER harness boundary;
- scorer no longer reintroduces floats before strict canonical serialization;
- fresh-freeze helper can now exclude source IDs from prior frozen transfer sets so a second transfer proof can use genuinely new examples.

These changes are experiment-integrity infrastructure, not claimed amplifier gains.

## 9. Next planned proof before this review

The planned next step is a **second independent fresh transfer proof** after freezing a new calibration and held-out split that excludes the first transfer's 12 source IDs.

The key scientific constraint is:

> the new paired-preservation rule must be judged only on fresh data that was not used to motivate it.

Do not assume the paired-preservation rule is correct merely because it would have avoided the first failed choice. It may be too conservative, may collapse to fixed-max-like behavior, or may still overfit in another way.

## 10. Source documents Astra should read

Read these before producing the review:

1. `docs/PRODUCT_DIRECTION.md`
2. `docs/V1_1_PRODUCT_DIFFERENTIATION.md`
3. `docs/V1_1_RESEARCH_STATUS.md`
4. `docs/V1_1_AMPLIFIER_MATERIALS.md`
5. `docs/V1_1_PARASITE_ATTACH_PROFILE.md`
6. `docs/V1_1_EXPERIMENT_PROGRAM.md`
7. `docs/V1_1_INTEGRATION_FEEDBACK.md`
8. `docs/RUNTIME_AMPLIFIER_LANDSCAPE.md`
9. `.ai-bridge/current-plan.md` — note that some test counts / most recent experiment details may be stale relative to this packet.

For exact current compiler semantics, read the implementation files in section 4 rather than inferring from older prose.

## 11. Questions that require a hard answer

### A. Compiler / statistics / causal validity

1. Is paired preservation against a predeclared fixed-max the right minimal correction, or is it an over-conservative reaction to one failed 6-item transfer?
2. What is the smallest principled selection rule you would use for tiny calibration sets without introducing a broad statistical/adaptive framework?
3. Should a candidate be allowed to trade one fixed-max success for one new success when aggregate quality is tied? If yes, under what deterministic evidence threshold? If no, why?
4. Is fixed-max the right reference at all, or should the compiler use another calibration anchor / dominance concept?
5. What minimum calibration/held-out sample design is necessary before claiming compiled-policy transfer rather than a toy demonstration?
6. Should cost optimization occur only after exact paired quality preservation, after a confidence interval / bound, or through another robust rule?
7. Are A+D / A+B+D / prompt_reduced / integrated currently distinct enough to justify the matrix, or is the matrix carrying redundant policies?

### B. Experiment design

1. Design the next highest-information fresh experiment after the first rejected transfer. Specify what must be frozen before scoring, what policies run on calibration, what policies run on held-out, what metrics and paired analyses decide success, and what result would falsify Harness Distillation as currently framed.
2. Is another 6+6 fresh balanced FEVER transfer useful, or is the sample too small to justify another model run? Recommend a concrete size/cost compromise.
3. Should the next proof stay on FEVER for controlled iteration, or move immediately to another task/model to test transfer of the compiler idea itself?
4. How should the experiment distinguish "the chosen policy transferred" from "fixed-max was already the robust default"?

### C. Product differentiation

1. Is Harness Distillation a real product category/moat, or does it collapse into prompt/RAG configuration tuning once described without internal jargon?
2. Which part is hardest to copy if the runtime/profile remains intentionally tiny?
3. What is the single best first customer workload / buyer where this product can beat simply using a better model, larger context, or existing RAG tooling?
4. Which current claims or terminology should be weakened or deleted because they run ahead of the evidence?
5. What measurable result would make you believe `Same model. Same runtime. Better answer.` is commercially meaningful rather than a lab slogan?

### D. Architecture / footprint

1. Is `prepare -> Complete|Generate -> finalize` the correct smallest product boundary?
2. Which currently ExactScope-owned components should be pushed back to the host to reduce shipping and integration ownership further?
3. Does native code currently earn its place for v1.1, or should the initial product surface be native-free unless later measurements justify a kernel?
4. How should distribution bytes, runtime payload, post-link footprint and integration effort be combined into one honest product decision without gaming the metric?

## 12. Required review output

Produce a standalone review document with these sections:

1. **Executive verdict** — 5-10 bullets, no politeness padding.
2. **What is genuinely strong today** — only evidence-supported strengths.
3. **What is weak / self-deceptive / overfit** — rank by severity.
4. **Compiler selection critique** — analyze paired-preservation and give exact recommended deterministic semantics.
5. **Next fresh experiment** — concrete preregistration-like design with sample sizes, policy cells, frozen decisions, success/failure gates and stop conditions.
6. **Product/moat critique** — state whether the category is differentiated and why.
7. **Architecture/size critique** — what to remove, keep, or defer.
8. **Top 5 decisions to make next** — ordered by expected information/product value.
9. **Things not to do yet** — explicit anti-roadmap.
10. **Final confidence table** — for product thesis, compiler thesis, transfer evidence, cross-runtime value, footprint strategy and commercial wedge: current confidence 0-100 plus one sentence why.

Be willing to say the current direction is wrong. Prefer falsifiable recommendations over broad advice. Distinguish measured evidence, inference and speculation.
