# ExactScope v1.1 — live attached amplification/economics diagnostic

Status: **historical prospective protocol; not executed exactly as written; actual reused-screen result and later fresh multi-hop study are recorded separately**

Updated: **2026-09-13**

## 1. Purpose

This diagnostic answers one deliberately narrow historical/product question before enterprise qualification:

> **When stable v1 and fixed v1.1 Integrated are attached to the same real local model/runtime on fresh public questions, is the original semantic amplification signal still present, and is v1.1 better or cheaper than stable v1 on the same serving boundary?**

This is not a selector study, not a release gate, not an enterprise customer proof, and not permission to reuse the sealed FEVER 600.

**Execution note:** the exact fresh64 v1-vs-v1.1 protocol below was not run as a single comparison. The first completed attached comparison reused existing NQ128/Hotpot20 public development screens and is frozen in [`V1_1_LIVE_ATTACHED_DIAGNOSTIC_RESULT.md`](V1_1_LIVE_ATTACHED_DIAGNOSTIC_RESULT.md). The pre-frozen Hotpot64 sample was later used as a separate development32/untouched-validation32 mechanism study, reported in [`V1_1_MULTIHOP_POLICY_DEVELOPMENT_RESULT.md`](V1_1_MULTIHOP_POLICY_DEVELOPMENT_RESULT.md). The prospective text below is preserved for audit rather than rewritten to match outcomes.

## 2. Frozen host

Primary model/runtime cell:

- model family: Qwen3.5 0.8B;
- quantization/file: `Qwen3.5-0.8B-Q4_0.gguf`;
- exact local model path: recorded in the private execution handoff and local host-identity artifact;
- runtime: llama.cpp `b10797` Windows `llama-server.exe`;
- exact local runtime path: recorded in the private execution handoff and local host-identity artifact; no host substitution is permitted;
- same hardware, threads/context/generation settings, structured-output surface, warmup/cache rule and request-order protocol for both arms unless an arm's frozen semantics necessarily change prompt/evidence bytes;
- zero quality retries, reflection, repair, second-model judge, agent loop or hidden alternate-model path.

Before model scoring, record exact model/runtime hashes and generation/timing protocol. If the files are unavailable or their identities cannot be verified, stop rather than substitute another model/runtime silently.

## 3. Fresh diagnostic workloads

Use two separately reported public cells:

1. **Natural Questions** — factual/single-hop pressure test;
2. **HotpotQA** — multi-hop/evidence-composition pressure test.

Target **64 fresh items per cell** after exclusions/grouping. If fewer than 64 eligible representatives exist in the locally available frozen source frame, freeze the maximum eligible count **before the first model output** and record the reason. Do not extend or replace items after outcomes are visible.

### Freshness / exclusion

Before sampling:

- enumerate every item/source id previously used in ExactScope v1/v1.1 NQ/Hotpot model screens, optimization sets, qualification sets and selector/material development artifacts that can be identified from repository/target manifests;
- exclude those ids prospectively;
- keep declared duplicate/near-duplicate or same-answer-bearing-source groups within one sampling unit where existing dataset metadata supports it;
- generate one sampling seed before inspecting realized model outcomes and record seed/provenance plus exact item-set digest;
- do not use FEVER items, especially the retired Stage 1 held-out 600.

The diagnostic may inspect dataset labels/gold only in the scorer after the two serving outputs are frozen. Runner-visible retrieval construction must not use answer gold to choose the delivered evidence.

## 4. Retrieval boundary

Use the same frozen corpus/retrieval frame for both arms within each workload and execute actual retrieval/ranking rather than injecting answer-bearing oracle evidence per arm.

If the existing local public NQ/Hotpot infrastructure can only produce a pooled research corpus, that limitation must be labeled explicitly. The runner must still perform the same real retrieval operation for both arms and must not use scorer gold to select evidence.

## 5. Arms

### V1 — stable r25 behavior

Use the stable v1 grounding semantics as implemented/documented for r25:

- stable grounding contract and authority/state semantics;
- stable selected projection/host-completion behavior;
- same real local model/runtime when generation is required;
- zero or one answer-generation call according to stable v1 rules.

Do not retrofit v1.1 features into this arm.

### V11 — fixed Integrated behavior

Freeze one fixed v1.1 Integrated policy before scoring. It may use only already-developed, host-owned-compatible semantic mechanisms, initially:

- retrieval query / model instruction separation;
- bounded candidate overfetch request;
- deterministic precision projection/order (`precision-context-v5` or its currently documented fixed successor, chosen before scoring);
- one frozen compact prompt/profile appropriate to this exact model/runtime;
- frozen typed answer contract / already-qualified structured-output surface;
- exact context-fit admission;
- strict deterministic finalization;
- proof-based Complete only where the existing verifier actually proves the current request from authorized evidence.

No learned/adaptive item router, outcome-aware branch, second model, quality retry or new intervention family may be introduced after scoring starts.

## 6. Call-budget parity

Within each item:

- stable v1 and v1.1 use the same target model/runtime;
- neither arm may use more than one answer-generation call;
- zero-call host completion is allowed only when that arm's already-declared sound rule proves the result/disposition from serving-visible evidence;
- every actual model call is counted;
- no answer is retried or selected from multiple generations.

## 7. Measurements

Report each workload independently and combined only as a descriptive secondary view.

### Quality

- NQ: existing repository NQ scorer metrics, including F1/EM where defined;
- HotpotQA: existing repository Hotpot scorer metrics, including answer F1/EM and evidence/support metrics where the frozen scorer supports them;
- paired item wins/losses/ties;
- unsupported/false-grounded or wrong-confident errors where the existing scorer can determine them without adding a model judge;
- zero-call correct/incorrect dispositions separately.

### Serving resources

For each arm report:

- model answer calls;
- prompt tokens;
- completion tokens;
- evidence/projected bytes;
- retrieval/prepare host work where measurable;
- measured model request-service time;
- E2E item latency and p50/p95;
- failures/format/finalization rejects;
- peak/steady resource measurements if already available from the runner without perturbing parity.

Do not convert token reduction into money unless a prospectively declared price/capacity model exists. This diagnostic may use measured service time and raw resources as **diagnostic economics**, not customer total economics.

## 8. Predeclared interpretations

The final report must answer these separately:

1. **Amplification signal alive?**
   - report paired v1.1-vs-v1 quality delta and paired wins/losses on each workload;
   - a positive descriptive delta is evidence of a surviving signal, not product qualification;
   - a zero/negative delta is retained and must not trigger same-cohort policy tuning.

2. **v1.1 better than v1?**
   - report quality/evidence/error dimensions separately;
   - do not collapse a quality gain plus safety loss into one success label.

3. **v1.1 cheaper than v1 on this diagnostic serving boundary?**
   - compare calls/tokens/service time/E2E/host work separately;
   - declare no cheaper result if the metrics materially conflict unless a scalar diagnostic resource model was frozen before scoring.

4. **Mechanism attribution**
   - use existing deterministic traces/receipts and predeclared arm definitions;
   - do not create post-hoc item-specific explanations as causal proof.

5. **Promotion consequence**
   - development evidence only;
   - positive result may justify carrying the fixed Integrated policy into enterprise DocQA development;
   - negative result must narrow/revisit that policy on new development data rather than consuming enterprise confirmatory data.

## 9. Hard stop conditions

Stop without scoring/continuing if:

- model/runtime identity differs from the frozen host without a new prospective diagnostic revision;
- fresh eligible item set cannot be constructed without reusing known scored/development items and this is not disclosed/frozen;
- one arm cannot run through its actual serving path;
- scorer gold leaks into runner-visible evidence selection;
- code/policy is changed in response to partial outcomes;
- output directory already contains a scored run for the same diagnostic revision.

## 10. Required artifacts

Before first model output:

- `freeze.json` — host hashes, exclusions, seed/provenance, item ids/digests, arm definitions, scorer/source hashes, timing protocol;
- frozen candidate/retrieval artifacts for both workloads;
- source-code hash manifest for the runner and relevant arm implementations.

After all outputs are frozen:

- raw serving observations;
- scorer outputs;
- paired analysis;
- resource/economic analysis;
- `V1_1_LIVE_ATTACHED_DIAGNOSTIC_RESULT.md` with explicit positive/negative/inconclusive statements and evidence limits.

No file from the retired FEVER Stage 1 held-out is an input to this diagnostic.
