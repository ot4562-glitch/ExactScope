# ExactScope v1.1 — direction reframe review packet

Status: strategic review input only; do not treat as an accepted design decision.
Date: 2026-09-13

## Purpose

The prior Astra High review scored the current thesis cautiously (Product thesis 40/100, Compiler thesis 30/100, Transfer evidence 10/100, Cross-runtime value 20/100, Footprint strategy 65/100, Commercial wedge 25/100). The project should not optimize for a score. The point of this review is to determine whether the underlying direction is actually distinct and defensible after separating inspiration from ownership.

The project deliberately borrowed patterns from three mature families:

1. LM harness/program compilers and optimizers.
2. RAG/retrieval/evaluation frameworks.
3. Big-tech inference runtimes and serving engines.

The question is whether ExactScope is merely a bundle of those ideas or whether there is a coherent layer they leave unowned.

## External landscape — current official-product patterns

### A. LM program/harness optimization

DSPy defines structured LM programs/signatures/modules and compiles them against metrics using optimizers such as GEPA, MIPROv2, BootstrapFewShot, etc. Its optimizer can change prompts/program behavior and save the optimized program. It also includes RAG, evaluation, tools and agent modules.

Relevant official source:
- https://dspy.ai/

Important implication: ExactScope cannot claim novelty merely from "compile a better LM configuration from examples" or "optimize prompts against a metric." DSPy already owns a strong version of that concept.

### B. RAG pipeline composition and evaluation

LangSmith/LangChain evaluate RAG across answer correctness, groundedness, relevance and retrieval relevance, including offline/online and intermediate-step evaluation. Haystack similarly supports component-level and end-to-end evaluation for retrievers/generators with both statistical and model-based evaluators.

Relevant official sources:
- https://docs.langchain.com/langsmith/evaluate-rag-tutorial
- https://docs.langchain.com/langsmith/evaluation-concepts
- https://docs.haystack.deepset.ai/docs/evaluation

Important implication: ExactScope cannot claim novelty merely from "evaluate retrieval and generation separately," "qualify a RAG pipeline," or "track regression across retriever/prompt/output components."

### C. Inference runtime optimization

vLLM already owns continuous/high-throughput serving, PagedAttention/KV management, Automatic Prefix Caching, speculative decoding, structured outputs, quantization and distributed scheduling. TensorRT-LLM owns paged/cross-request KV reuse, offload, guided decoding and GPU serving mechanics. ONNX Runtime GenAI owns tokenization/preprocessing, inference loop, logits/search/sampling, chat templates, structured output and KV-cache management. ExecuTorch owns on-device LLM execution/generation configuration. Similar ownership exists in SGLang, OpenVINO, LiteRT-LM and llama.cpp.

Relevant official sources:
- https://docs.vllm.ai/en/stable/
- https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/
- https://docs.vllm.ai/en/stable/features/spec_decode/
- https://nvidia.github.io/TensorRT-LLM/features/kvcache.html
- https://nvidia.github.io/TensorRT-LLM/advanced/executor.html
- https://onnxruntime.ai/docs/genai/
- https://docs.pytorch.org/executorch/stable/llm/run-on-android.html

Important implication: ExactScope must not own runtime kernels, scheduler, tokenizer, cache implementation, structured-decoding engine, speculative decoder or accelerator policy.

## Why the prior direction still may contain a real wedge

The three families above optimize different objects:

- DSPy-like systems optimize an LM program/prompt/module graph against a metric.
- RAG frameworks compose and evaluate retrieval/generation pipelines.
- Inference runtimes optimize execution of a request once the request exists.

The unresolved candidate layer is:

> Given a frozen workload contract, a competent unchanged Base, a host/runtime capability record, evidence semantics and a bounded intervention catalog, compile the smallest **qualified semantic execution policy** that decides what work should reach the model and what host-native capabilities may safely be used, while leaving retrieval execution and inference execution owned by the host.

Potential decisions encoded by such a policy include:
- whether generation is needed at all when a request-time proof can complete deterministically;
- retrieval-query / model-instruction separation;
- bounded candidate overfetch and evidence projection/ordering;
- answer-domain/output contract requirements;
- context-fit admission requirements;
- whether a host-native structured-output surface is qualified for this host/model identity;
- whether stable prefix identity/cache reuse is parity-qualified;
- strict post-generation acceptance/rejection semantics;
- capability/profile identities and qualification scope.

This object is neither the retriever, the prompt optimizer nor the runtime implementation. It is a compiled policy sitting above those mechanisms.

## Three candidate product theses to score against each other

### Thesis A — Conservative current thesis

**Reference-preserving cost compiler**

> For one competent Base B and one predeclared competent intervention reference F, compile a strictly cheaper fixed policy P that preserves every observed F calibration success, then independently qualify or reject P on fresh held-out data.

Advantages:
- precise;
- experimentally falsifiable;
- prevents post-hoc quality/cost trades;
- good for scientific integrity.

Risks:
- may collapse to a narrow tuner;
- may frequently return ReferenceOnly;
- may not justify a product category by itself;
- sounds like qualification machinery rather than a product.

### Thesis B — Candidate stronger category

**Semantic Inference Policy Compiler**

> ExactScope compiles workload semantics + host capabilities + bounded intervention knowledge into an immutable qualified execution policy that changes how an existing model/runtime is used, without changing the model weights and without owning the inference runtime.

Cold path:

```text
workload contract
+ representative calibration
+ competent Base/reference
+ host capability record
+ bounded semantic interventions
        |
        v
qualification/compiler
        |
        v
immutable execution policy + qualification scope
```

Hot path:

```text
prepare(query, host_evidence, host_profile)
   -> Complete(answer, proof)
    | Generate(contract, approved_payload, requirements)
    | Reject/Unavailable(reason)

host executes retrieval/tokenization/inference/cache/decoding

finalize(contract, raw_output)
   -> Accept(answer)
    | Reject(reason)
```

The product claim would NOT be "we invented prompt optimization" or "we invented RAG tuning." The claim would be that **semantic execution policy is a separately compilable/qualifiable artifact** across host runtimes.

Differentiation burden:
- must show one learned/compiled policy decision transfers prospectively beyond the calibration set;
- must show value over a competent fixed reference, not just Base;
- must show at least some policy knowledge survives a host/runtime change without simply re-running a fully independent search;
- must show integration/requalification cost is low enough to matter.

Potential moat:

```text
workload properties
+ host capability vector
+ intervention interaction outcomes
+ fresh transfer results
        -> reusable policy priors / qualification knowledge
```

This is a moat hypothesis only if those priors become prospectively predictive.

### Thesis C — Candidate commercial framing

**Qualified Execution Profile Compiler**

> ExactScope turns a customer workload and existing AI stack into a small immutable execution profile that has been prospectively qualified to preserve required quality while reducing serving cost.

This intentionally avoids claiming a new research category. It sells:
- measurable serving savings;
- auditable frozen qualification scope;
- no model replacement;
- no inference-runtime replacement;
- no second model/judge/retry loop;
- low operational ownership.

This may be commercially clearer even if Thesis B is the deeper technical category.

## Important distinction from adjacent categories

A strong ExactScope category must survive these comparisons:

### Versus DSPy / GEPA / prompt-program optimizers

If ExactScope only searches prompts, demonstrations or module compositions, DSPy is the stronger category owner.

To be distinct, ExactScope must compile policy over **semantic admission, evidence shaping, proof-based zero-call completion, output contracts and host capability eligibility**, not just prompt text/program topology.

### Versus RAG frameworks/evaluation systems

If ExactScope primarily builds retrievers, chunks documents, manages vector stores, or evaluates RAG, existing RAG frameworks are broader and more mature.

To be distinct, retrieval remains host-owned. ExactScope consumes host evidence/candidate records and compiles/qualifies **how much/which semantic evidence and answer contract should cross the model boundary**.

### Versus inference runtimes

If ExactScope owns KV memory, batching, kernels, structured-decoding implementation or speculation, specialized runtimes will outcompete it.

To be distinct, ExactScope says whether a capability is **eligible/qualified for a semantic policy**; the host runtime implements it.

## What the first failed 6+6 experiment really means

The failed transfer is not evidence that the whole category is wrong. It is evidence that:
- a tiny calibration set cannot safely choose among ten policies using aggregate success + cheapness;
- policy transfer is the hard part;
- qualification correctly rejected the chosen candidate;
- the post-failure preservation rule is unvalidated until a new fresh experiment.

The next 120/600 study should therefore be viewed as a test of **whether any useful fixed policy compilation exists at all under one workload**, not as a final product proof.

## Proposed evidence ladder if Thesis B survives review

1. **Within-workload compiler value**
   - fresh 120 calibration / 600 held-out.
   - competent Base B and reference F.
   - compiled candidate must preserve/reference-control quality and materially reduce cost.

2. **Customer-like real retrieval**
   - bounded enterprise document QA.
   - real retriever, real authority/freshness/conflict conditions.
   - compare Base, fixed reference, compiled policy, and better-model alternative.

3. **Prospective host transfer**
   - freeze semantic task/workload.
   - change runtime/capability vector.
   - test whether existing interaction knowledge reduces calibration/search burden or predicts the qualified policy better than a cold search.

4. **Cross-workload prior value**
   - new document QA domain/workload.
   - measure whether accumulated policy priors reduce qualification cost or improve candidate ranking prospectively.

Only stages 3-4 would justify a serious moat/cross-runtime compiler claim.

## What Astra should judge

Do not reward conservative wording. Judge whether there is a real product and category here.

For each Thesis A/B/C, score 0-100 and explain:
- product thesis coherence;
- category distinctness;
- compiler thesis;
- incremental value over DSPy-like program optimization;
- incremental value over RAG pipeline/evaluation frameworks;
- incremental value over vLLM/TensorRT/ORT-style runtime optimization;
- plausibility of cross-runtime value;
- plausibility of a defensible data/qualification moat;
- commercial wedge clarity;
- implementation ownership/size discipline.

Then answer these hard questions:

1. Is Thesis B actually a distinct technical layer, or just a renamed configuration optimizer?
2. What exact artifact/contract would make "semantic execution policy compiler" non-hand-wavy?
3. Which one or two decisions must transfer across workloads/runtimes before the category is credible?
4. What should be removed from ExactScope because adjacent systems already own it better?
5. What evidence would increase Product thesis from ~40 to >=70 without changing the model or adding a second model?
6. What evidence would increase Compiler thesis from ~30 to >=70?
7. Is 120/600 still the right immediate experiment if the target category is Thesis B, or should the experiment be redesigned?
8. Should Thesis A remain only the conservative validation algorithm inside Thesis B, rather than being the product identity itself?
9. Is Thesis C the better external commercial framing while Thesis B remains the internal architecture/category?
10. Give a ranked recommendation: ACCEPT, MODIFY, or REJECT each thesis.

Finish with:
- one recommended one-sentence category definition;
- one recommended 12-month moat hypothesis;
- one minimal next experiment that maximizes information about whether this direction deserves continued investment;
- revised confidence scores for Product thesis, Compiler thesis, Transfer evidence, Cross-runtime value, Footprint strategy and Commercial wedge.
