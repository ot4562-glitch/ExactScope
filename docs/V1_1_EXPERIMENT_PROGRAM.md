# ExactScope v1.1 experiment program

Status: **active local research charter; v1.1 is unreleased; FEVER Stage 1 is complete/stopped at `ReferenceOnly`; current execution priority is competence-gated enterprise document QA**
Updated: **2026-09-13**

## 1. Research objective

ExactScope v1.1 may still use detachable material experiments to discover causal interactions, but the product is no longer defined as a generic "runtime amplifier." The current direction is layered:

```text
current product category:         Qualification / Configuration Optimizer
customer-facing qualified artifact: Qualified Execution Profile
research hypothesis:              Semantic Inference Policy Compiler
stopped FEVER algorithm:          Reference-Preserving Cost Reduction
```

The preregistered FEVER Stage 1 returned `ReferenceOnly`, so successful cost compilation is not demonstrated. The latest independent post-result review narrows the product claim now, keeps the compiler interpretation as research only, and makes competent enterprise document QA the next empirical priority. No new-category, customer-savings, cross-runtime, or moat claim follows from the bookkeeping or architecture alone.

The research order is now:

```text
protect stable v1.0
  -> preserve the stopped FEVER Stage 1 and sealed held-out without rescue/reuse
  -> narrow v1.1 product claims to qualification/configuration optimization
  -> define one bounded enterprise document-QA workload with real host retrieval
  -> establish competent Base / integrated-style feasibility on development data
  -> freeze workload-owner quality, evidence, abstention and total-economic gates
  -> run fresh independent product-value qualification
  -> run a cheaper-policy branch only if its frozen calibration rule admits P
  -> only after a useful competent source policy, revisit cross-host transfer/adaptive research
  -> only after evidence, decide release/product/category expansion
```

The current package/staticlib checkpoints are architectural measurements, not the product definition. The latest size checkpoints are maintained in [`V1_1_RESEARCH_STATUS.md`](V1_1_RESEARCH_STATUS.md). Smallness can help distribution; it is not itself a moat.

The current technical hypothesis is:

> **ExactScope is a workload-specific policy compiler that binds bounded evidence and answer rules to explicit qualification for an existing AI stack.**

The proposed customer deliverable is:

> **A Qualified Execution Profile emitted only when a frozen candidate meets predeclared fresh-data quality and serving-economics requirements.**

ExactScope must avoid becoming an inference runtime, full RAG framework, vector database, generic evaluator, or observability system. Existing runtimes keep ownership of model execution, tokenization/templates, scheduling/batching, KV/prefix caches, constrained/speculative decoding, accelerators and fallback. The minimum v1.1 semantic center is **evidence sufficiency/context admission** plus **answer-contract lowering/finalization**. Optional proof completion requires a sound registered verifier.

### Current operating mode — 2026-09-13

The stable public release remains **v1.0.0** while v1.1 is developed locally. The three upstream validation issues (ORT GenAI #2549, ExecuTorch #22761, LiteRT Samples #308) were reverified and reframed on 2026-09-13; they remain a separate placement-gated external-validation track and do not define local product evidence.

The first executable compiler-transfer slice produced a fresh rejection. The later prospectively frozen FEVER Stage 1 then completed all 1,200 calibration observations and returned **`ReferenceOnly`**, `P = null`, `T = F`; the 600-item held-out was not consumed. That demonstrates experiment integrity and a negative candidate frontier under the frozen catalog, not successful compiler transfer.

A subsequent same-model attached diagnostic established that amplification remains measurable but that one precision policy does not dominate every workload: NQ improved while using materially less context, whereas Hotpot lost F1 because complete multi-hop support coverage fell. The reused-screen result is development evidence only and is frozen in [`V1_1_LIVE_ATTACHED_DIAGNOSTIC_RESULT.md`](V1_1_LIVE_ATTACHED_DIAGNOSTIC_RESULT.md).

The multi-source mechanism was then tested on a separately pre-frozen fresh Hotpot64 sample. Development32 selected `coverage-3k-cap12`; untouched validation32 improved F1 by **+6.82 pp** over the prior precision path, and a second untouched Hotpot32 later beat stable v1 by **+6.22 pp F1** while matching its support-title coverage and using less context. Single-source precision then received the same treatment after a fresh NQ32 exposed a 2 KiB regression: pre-frozen NQ development32 selected `precision-3k-cap8`, untouched validation32 improved **+8.47 pp F1** over 2K, and another untouched NQ32 later beat stable v1 by **+1.63 pp F1** with fewer input tokens/evidence bytes. These authorize two fixed development policy candidates, not per-query adaptive routing or product qualification.

The two public-task policy cycles are now complete at development-diagnostic level. The immediate sequence is therefore the **competence-gated bounded enterprise document-QA study with real host retrieval**, using explicit workload evidence-composition requirements and qualified evidence budgets rather than dataset-name routing. Before enterprise confirmatory scoring, workload-owner competence and unacceptable-error rules, Base/integrated-style identities, document/question leakage grouping, scorer/adjudication, load/timing, total-economic model and all optional optimizer-branch semantics must be frozen. The stopped FEVER held-out must not be repurposed.

New materials may still be studied only when they have a precise control, falsifiable measurement and host/product ownership boundary. They do not enter the enterprise product proof merely because they are interesting.

See [`V1_1_ULTIMATE_PRODUCT_ARCHITECTURE.md`](V1_1_ULTIMATE_PRODUCT_ARCHITECTURE.md), [`V1_1_PRODUCT_DIFFERENTIATION.md`](V1_1_PRODUCT_DIFFERENTIATION.md), [`V1_1_STAGE1_REFERENCE_ONLY_RESULT.md`](V1_1_STAGE1_REFERENCE_ONLY_RESULT.md), and [`V1_1_RESEARCH_STATUS.md`](V1_1_RESEARCH_STATUS.md).

## 2. Two simultaneous configurations

### Product/reference configuration

The smallest known-good configuration remains available as a regression anchor. It protects stable semantics, reproducibility, safety and a realistic future release target.

### Experimental Amplifier Rack

Aggressive ideas are mounted as detachable modules. Experimental modules may exceed release size/CPU/RAM/token budgets. A module must be removable without rewriting the stable grounding semantics.

```text
question
   |
   +-- [Q] query / instruction separation variants
   +-- [R] retrieval and candidate-selection variants
   +-- [D] exact / structural / optional semantic dedup experiments
   +-- [P] evidence projection / compression / ordering variants
   +-- [A] adaptive evidence-budget controller variants
   +-- [H] deterministic host-completion / 0-call variants
   +-- [C] typed answer-contract / constrained-output variants
   +-- [I] immutable preparation / identity / cache-reuse variants
   +-- [B] backend capability and delivery bridge
   +-- [K] backend-native prefix/KV-cache hints
   +-- [S] backend-native speculation hints
   |
   v
existing model runtime
```

The rack is intentionally not a new RAG framework, inference engine, agent runtime or model cascade. New model weights, a mandatory second model, a vector database, or a hidden retry/reflection loop do not count as a lightweight ExactScope amplification win. Such variants may be used only as explicitly labelled research ceilings, never silently folded into the product score.

## 3. Why nonlinear amplification is plausible

Several ExactScope mechanisms change the **conditions under which the next mechanism operates**. Their effects therefore need not add linearly.

Example hypothesis:

```text
better retrieval query
   -> higher useful-candidate probability
   -> denser projection can preserve the answer span
   -> shorter context makes the useful span easier to attend to
   -> typed decoding shrinks the remaining output search space
   -> weak model crosses from failure to success
```

For modules A and B, measure interaction explicitly:

```text
I(A,B) = Score(A+B) - Score(A) - Score(B) + Score(Base)
```

A positive interaction term is evidence that the combination produces more than the sum of isolated gains. More important than the aggregate number is **item-level phase transition**: a question that fails under Base, A and B separately but succeeds reliably under A+B.

For small models, track whether the capability boundary moves rather than only whether mean accuracy rises. A useful amplifier may produce its largest relative gain on the smallest deployable model and a smaller gain on an already-strong model.

## 4. Search procedure

### Phase 1 — wide screening

Run the base, every individually detachable module, and high-priority pairs. Do not reject an idea merely because it exceeds the future release footprint.

Record at minimum:

- task accuracy / exact task-specific score;
- complete-evidence recall;
- false-grounding and authoritative unsupported-assertion rates;
- wrong-confident answer rate;
- strict output-contract failure;
- model-call count;
- prompt/evidence/completion tokens;
- time to first token and end-to-end latency where a real runtime is involved;
- ExactScope CPU time, peak RAM/scratch and cold-start cost;
- source, package and optional-module bytes.

### Phase 2 — interaction neighborhoods

When a combination shows a positive interaction, explore its local neighborhood rather than the full exponential power set. Add/remove one module, swap one implementation, and vary only the budget/controller directly implicated by the result.

### Phase 3 — leave-one-out causal check

Starting from the best rack configuration, remove each module in turn. Measure the marginal loss. Features whose removal causes no meaningful loss are not part of the causal minimum even if they looked attractive in isolation.

### Phase 4 — Pareto distillation

Only after the high-amplification region is understood, optimize for the deployable frontier:

```text
quality / safety / model calls / tokens / latency / RAM / bytes / integration cost
```

A feature can be replaced by a smaller equivalent rather than simply deleted. The final v1.1 release gate is applied **after** this distillation and a fresh qualification, not during discovery.

### Phase 5 — Stage 1 policy compilation / qualification — complete and stopped

The immutable Stage 1 contract is [`V1_1_STAGE1_PREREGISTRATION.md`](V1_1_STAGE1_PREREGISTRATION.md); the completed outcome is [`V1_1_STAGE1_REFERENCE_ONLY_RESULT.md`](V1_1_STAGE1_REFERENCE_ONLY_RESULT.md). Stage 1 was deliberately not a general Pareto optimizer and did not test the full Semantic Inference Policy Compiler thesis.

The frozen protocol did what it was supposed to do: it established the data grouping/sample, competence classification, candidate catalog, `B/F/P/T` rules, cost/timing model, exact analysis, contract surface and immutable identities before fresh scoring. It then executed 120 fresh balanced calibration claims across the ten-policy matrix and returned:

```text
ReferenceOnly
P = null
T = F = integrated
```

No cheaper policy preserved all observed Reference successes, and no cheaper policy even matched the Reference's aggregate 52/120 success count. The 600-item held-out was therefore not executed. The formal narrow/product/incremental verdicts remain `NOT_EVALUATED_REFERENCE_ONLY`, and the whole study remains algorithm-diagnostic-only because no absolute product competence floor was established.

This valid failure **ends same-cohort FEVER selector repair presented as confirmation**. The frozen held-out stays sealed and is retired from revised-rule inference. The 15% cheaper-reference requirement remains untouched for that claim; it is not reduced because the cheapest observed calibration candidate saved only 11.75%.

### Phase 6 — enterprise document-QA competence and product value

The next empirical program is a new workload, not a rescue branch. It must:

1. use one bounded authorized document collection and real host retrieval;
2. define a question population containing answerable, unanswerable and materially ambiguous cases, with leakage-preventing document/question groups;
3. establish workload-owner competence rules on development data before confirmatory scoring;
4. freeze a competent Base and fixed integrated-style semantic configuration rather than assuming either is viable;
5. freeze correctness, evidence/citation support, abstention, unacceptable-error, latency/load and total-economic rules;
6. freeze independent scoring or blinded human adjudication, including tie/disagreement handling;
7. evaluate integrated-style versus Base as the primary product-value question on fresh data;
8. keep a cheaper reference-preserving `P/T` branch conditional and separately preregistered; if calibration admits no `P`, stop only that branch;
9. report better-model or simpler-host alternatives when deployable so ExactScope is not protected from a rational replacement;
10. emit a Qualified Execution Profile only from a passed independent qualification, never from calibration leadership.

Prospective transfer and adaptive per-query routing remain deferred until this program demonstrates a useful competent source policy.

## 5. Research combinations derived from prior work

This section records *combinations to test*, not claims that ExactScope implements or improves on the cited systems.

### 5.1 Selective augmentation + deterministic 0-call routing

RAG established the value of combining parametric and external non-parametric knowledge [R1]. RECOMP later showed that retrieved material can be compressed and that augmentation can be skipped when it is not useful [R2]. ExactScope combines that general lesson with a stricter systems boundary: authoritative states and canonical scalar facts can terminate in the host, while only generation-required cases receive evidence.

Experiment:

```text
selective evidence admission
  x deterministic host completion
  x adaptive projection budget
```

Measure whether fewer generation calls and denser remaining prompts reinforce each other rather than merely save independent costs.

### 5.2 Evidence density + position control

Lost in the Middle showed that relevant-information position can materially change long-context performance [R3]. LLMLingua and LongLLMLingua explored budget-controlled prompt compression and increasing key-information density [R4][R5]. ExactScope should test a deterministic, model-free version of the underlying idea: not maximum context, but **minimum sufficient evidence placed where the target runtime/model can use it reliably**.

Experiments:

- answer-bearing span first vs source order vs confidence order;
- one complete anchor vs adjacent two-sentence unit;
- per-target interleaving vs grouped targets;
- 256/512/1024/2048/custom byte tiers during research;
- sparse evidence plus explicit state vs verbose policy text;
- projection variants that preserve exact provenance while changing model-visible ordering.

Do not infer that fewer tokens are automatically better. The winning controller must be accuracy/safety measured.

### 5.3 Typed answer domain + backend-native constrained decoding

Grammar-Constrained Decoding showed that formal grammars can guarantee structural output classes without finetuning [R6]. DOMINO showed that naive token-level constraints can add overhead or hurt accuracy when constraints and subword tokenization are misaligned [R7]. Grammar-Aligned Decoding further warns that constrained decoding can distort the model distribution [R8].

ExactScope therefore should not merely switch constraints on. It should test:

```text
semantic answer contract
  x backend-native structured-output surface
  x tokenizer/runtime identity
```

A constraint is promoted only when it reduces format/token waste without damaging task correctness for the qualified identity. The semantic contract belongs to ExactScope; JSON Schema/GBNF/Lark/backend spellings belong to thin capability shims.

### 5.4 Compact literal evidence + n-gram speculative decoding

Classical speculative decoding demonstrates that exact or distribution-preserving acceleration can come from proposing several tokens and verifying them with the target model [R9]. Inference engines should own this mechanism, not ExactScope. ONNX Runtime GenAI currently exposes speculative options and an n-gram proposal mode in its upstream implementation/documentation [R12].

This suggests an unusually well-aligned experiment: ExactScope often injects a short literal answer-bearing span. If the answer copies that span, a host runtime's prompt-history n-gram drafter may achieve a higher acceptance length.

Test only as a backend-owned rack module:

```text
precision evidence projection
  x literal-span placement
  x ORT GenAI n-gram speculation
```

Measure end-to-end latency, accepted draft length, output parity and energy/CPU cost. Do not assume speculation is faster on every model/device.

### 5.5 Stable prefix identity + host KV/prefix reuse

PagedAttention/vLLM demonstrates why KV-cache allocation/reuse is an inference-engine specialization [R10]. ORT GenAI also exposes append/continuation mechanisms and documents system-prompt caching constraints for some execution providers [R13]. ExactScope's role is only to expose a stable prefix identity and immutable message boundary. The host decides whether its cache mechanism is applicable.

Experiment:

```text
PreparedAmplifier stable prefix
  x backend native prefix/system cache
  x repeated workload
```

Parity is mandatory; cache speedup is not assumed.

### 5.6 Cost-aware routing without a model cascade

FrugalGPT demonstrates the general systems value of routing work according to cost/performance [R11], although its LLM-cascade mechanism is outside ExactScope's no-second-model product goal. ExactScope can reuse the broader idea without adopting the cascade: route deterministic cases to zero inference, generation-required cases to the already-selected host model, and optional backend accelerations only when capability-qualified.

## 6. ExactScope Bridge as an integration pressure test

`adapters/bridge/` is an experimental companion layer, not a new product core. The delivery shape has now been pressure-tested across ONNX Runtime GenAI, current ExecuTorch `IRunner` structure, and LiteRT-LM fixtures.

The Bridge exists to test whether ExactScope's semantic boundary survives structurally different host runtimes without copying runtime-owned machinery or ExactScope policy into adapters:

```text
user question
  -> ExactScope GroundingSession / PreparedAmplifier
  -> Bridge Delivery
       -> complete: return ExactScope reply, 0 generation calls
       -> generate: pass only ExactScope-approved messages
  -> ORT GenAI tokenizer / GeneratorParams / Generator
  -> current ExactScope output validator
```

The ORT adapter must not inspect raw retrieval candidates, resolve authority, merge conflicts, rewrite evidence, or own inference. Current v1.1-dev dictionary details are isolated in `adapters/bridge/exactscope_v11.py` so future interface churn is one-file churn.

The same delivery shape has now also been pressure-tested against current ExecuTorch `IRunner` structure and LiteRT-LM fixtures. Those results remain structural/runtime evidence rather than cross-runtime answer-quality transfer. A runtime-specific problem stays in that runtime shim; repeated cross-runtime friction may justify a public semantic seam, but adding more runtimes is not the current foreground. The next product milestone is the preregistered reference-preserving compiler-value study.

## 7. Future-proofing rule

ExactScope should deliberately depend on **semantic contracts and narrow delivery data**, not one vendor's scheduling or tensor API.

The long-lived boundary should remain approximately:

```text
ExactScope owns                    Host runtime owns
------------------------------    ---------------------------------
source/authority semantics         model graph and weights
coverage/freshness/conflict        accelerator / execution provider
zero-call decision                 tokenizer implementation
compact approved evidence          KV allocation / paging
answer-domain semantics            batching / scheduler
stable identity/hints              speculative decoder
strict final validation            generation loop
```

If a future runtime becomes dramatically faster, supports much longer context, or changes accelerator architecture, ExactScope should still be useful because its job is to remove unnecessary probabilistic work and improve information/answer density—not to emulate the runtime.

## 8. Promotion rule

No experimental result is promoted because it is clever, fast on one machine, or small in isolation. Promotion requires:

1. a reproducible identity;
2. isolated and combined effects;
3. no hidden negative cells;
4. safety/false-grounding accounting;
5. measured runtime/token/resource cost;
6. cross-model or clearly scoped target evidence;
7. a leave-one-out reason for keeping it;
8. a credible path to the final lightweight envelope.

The final v1.1 archive may still target the existing tiny envelope. The research rack does not.

## 9. References

- **[R1]** Lewis et al., *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*, NeurIPS 2020 / arXiv:2005.11401. <https://arxiv.org/abs/2005.11401>
- **[R2]** Xu, Shi, Choi, *RECOMP: Improving Retrieval-Augmented LMs with Compression and Selective Augmentation*, 2023. <https://arxiv.org/abs/2310.04408>
- **[R3]** Liu et al., *Lost in the Middle: How Language Models Use Long Contexts*, TACL 2024. <https://aclanthology.org/2024.tacl-1.9/>
- **[R4]** Jiang et al., *LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models*, 2023. <https://arxiv.org/abs/2310.05736>
- **[R5]** Jiang et al., *LongLLMLingua: Accelerating and Enhancing LLMs in Long Context Scenarios via Prompt Compression*, ACL 2024. <https://aclanthology.org/2024.acl-long.91/>
- **[R6]** Geng et al., *Grammar-Constrained Decoding for Structured NLP Tasks without Finetuning*, EMNLP 2023. <https://aclanthology.org/2023.emnlp-main.674/>
- **[R7]** Beurer-Kellner, Fischer, Vechev, *Guiding LLMs The Right Way: Fast, Non-Invasive Constrained Generation*, ICML 2024 / arXiv:2403.06988. <https://arxiv.org/abs/2403.06988>
- **[R8]** Park et al., *Grammar-Aligned Decoding*, 2024. <https://arxiv.org/abs/2405.21047>
- **[R9]** Leviathan, Kalman, Matias, *Fast Inference from Transformers via Speculative Decoding*, 2022/2023. <https://arxiv.org/abs/2211.17192>
- **[R10]** Kwon et al., *Efficient Memory Management for Large Language Model Serving with PagedAttention*, SOSP 2023 / arXiv:2309.06180. <https://arxiv.org/abs/2309.06180>
- **[R11]** Chen, Zaharia, Zou, *FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance*, 2023. <https://arxiv.org/abs/2305.05176>
- **[R12]** Microsoft, ONNX Runtime GenAI speculative decoding implementation/documentation. <https://github.com/microsoft/onnxruntime-genai/blob/main/docs/SpeculativeDecoding.md>
- **[R13]** Microsoft, ONNX Runtime GenAI migration/system-prompt caching notes. <https://onnxruntime.ai/docs/genai/howto/migrate.html>
- **[R14]** Microsoft, ONNX Runtime GenAI Generate API overview. <https://onnxruntime.ai/docs/genai/>

See [`REFERENCES.md`](REFERENCES.md) and [`RUNTIME_AMPLIFIER_LANDSCAPE.md`](RUNTIME_AMPLIFIER_LANDSCAPE.md) for the broader runtime/compatibility bibliography.
