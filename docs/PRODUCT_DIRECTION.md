# ExactScope product direction

Release context: **ExactScope v1.0.0 promotes the selected r25 grounding behavior into a stable Linux x86-64 native grounding software/package scope.** The native C ABI, deterministic XSGI search/projection path, footprint-gated package, and final-archive C11 clean-room integration are complete. The seven-model and public-benchmark accuracy results remain bound to their exact candidate/provider/corpus identities, and physical ARM64 RAM/latency/energy/thermal qualification remains unclaimed. See [`GROUNDING_ARCHITECTURE.md`](GROUNDING_ARCHITECTURE.md), [`../spec/GROUNDING_CONTRACT_V0_1.md`](../spec/GROUNDING_CONTRACT_V0_1.md), [`BENCHMARK.md`](BENCHMARK.md), and [`../spec/GROUNDING_RUNTIME_BUNDLE_V1.md`](../spec/GROUNDING_RUNTIME_BUNDLE_V1.md).

This document defines what ExactScope is optimizing for. It supersedes any earlier product framing that treated broad platform parity or full catalog completion as more important than proving adoption value.

> **v1.1 research note (2026-09-13):** v1.0 remains the stable product baseline. The preregistered Qwen/FEVER Stage 1 has now **stopped at `ReferenceOnly`**: `P = null`, the conventional comparator also returned `T = F`, and the sealed 600-item held-out was not consumed. This validates the stop/qualification discipline, not compiler value. The current v1.1 product identity is therefore narrowed to a **qualification/configuration optimizer with semantic enforcement and immutable qualification records**. **Semantic Inference Policy Compiler** remains an internal research hypothesis only. The next empirical priority is competence-gated bounded enterprise document QA with real host retrieval. See [`V1_1_STAGE1_REFERENCE_ONLY_RESULT.md`](V1_1_STAGE1_REFERENCE_ONLY_RESULT.md) and the independent post-result review [`V1_1_STAGE1_REFERENCE_ONLY_ASTRA_REVIEW.md`](V1_1_STAGE1_REFERENCE_ONLY_ASTRA_REVIEW.md).

## 1. Product sentence

The v1.1 target is a **small workload-specific qualification/configuration optimizer for AI systems that already own their model, retrieval path, and inference runtime**. It may evaluate semantic policy alternatives, but it earns a deployable profile only through independently frozen competence and economics gates.

Internal architecture hypothesis:

> **ExactScope is a workload-specific policy compiler that binds bounded evidence and answer rules to explicit qualification for an existing AI stack.**

Customer-facing hypothesis:

> **ExactScope evaluates bounded semantic configurations of an existing document-answering service and delivers a deployable profile only when a prospectively declared competence and total-economics contract passes on fresh evaluation data. A cheaper reference-preserving profile is one conditional outcome, not the whole product promise.**

Research shorthand:

> **Same model. Same runtime. Better answer.**

The shorthand is a research objective, not a current universal claim. Existing program optimizers and RAG frameworks can express many of the same decisions; ExactScope only earns distinct value if its typed semantic boundary, qualification artifacts, or accumulated transfer knowledge measurably reduce integration/search/qualification effort.

ExactScope should not compete with inference runtimes on tokens/second and should not become another full RAG framework. The host owns retrieval execution/authorization, corpus/index management, tokenizer/chat-template rendering, exact token accounting, inference, scheduling/batching, KV/prefix cache implementation, constrained/speculative decoding, accelerators, fallback, activation, and rollback. ExactScope should own only a restricted workload/evidence/answer contract, bounded provenance-preserving evidence shaping, evidence-sufficiency/context-admission requirements, semantic answer-contract lowering, strict finalization, identity-bound qualification, and sound proof completion where a registered verifier exists.

The minimum semantic center is intentionally narrower than the earlier amplifier rack:

```text
workload/evidence/answer contract + host capability declaration
                         |
                         v
             Candidate Execution Policy
                         |
              independent qualification
                         |
                         v
              Qualification Attestation
                         |
                         v
              Qualified Execution Profile
```

At request time the qualified policy drives only a small boundary:

```text
prepare(query, authorized evidence, profile)
  -> Complete(answer, proof, receipt)
   | Generate(delivery, contract, requirements, receipt)
   | Reject/Unavailable(reason)

host model only for Generate

finalize(contract, output, receipt)
  -> Accept(answer)
   | Reject(reason)
```

Low cost must be evaluated across installation/dependencies, host and inference work, model calls/tokens, latency, CPU/RAM, integration, qualification, maintenance, and refresh—not archive size alone. A small artifact is an adoption advantage, **not the moat**.

The long-term moat hypothesis is accumulated prospective knowledge of `workload properties x host capabilities x intervention interactions -> fresh transfer outcomes` that reduces future candidate search/calibration effort without weakening the final qualification gate. It remains unproved.

The first commercial validation wedge is **high-volume bounded enterprise document QA on a genuinely pinned or expensive-to-change model**, narrowed initially toward short factual answers, extraction, typed decisions, and citation-bound outputs. On-device/embedded retrofit remains a longer-term market and architecture constraint, not a substitute for a real customer/economic proof.

The existing quantitative `xs_calc`/`xs_eval` subsystem remains supported where deterministic calculation is the actual failure mode. The stable-v1 grounding contract remains authoritative for v1.0; v1.1 research may simplify or relocate implementation ownership before any new public contract is frozen.

### 1.1 The v1.1 qualification/configuration mechanism

The first fresh transfer rejected its selected candidate. The larger preregistered FEVER Stage 1 then executed all 1,200 calibration observations and stopped at **`ReferenceOnly`** before held-out: `P = null`, while the conventional aggregate quality-constrained comparator also returned `T = F`. No cheaper frozen candidate matched the Reference's aggregate calibration success count, so the result is not explained merely by the paired-preservation constraint. The sealed 600-item held-out remains unscored.

Current evidence therefore supports **selection/qualification separation, explicit abstention/stop outcomes, and immutable experiment identities**. It does not support successful compiler value. Reference-preserving cost reduction remains a research algorithm, not the v1.1 product identity.

The next product-value path is:

```text
bound enterprise document-QA workload + real host retrieval
  -> establish competent Base and fixed integrated-style configuration on development data
  -> freeze correctness / evidence / abstention / unacceptable-error / total-economics gates
  -> independently freeze evaluation groups, sample and adjudication
  -> evaluate integrated-style vs Base as the primary product-value question
  -> optionally admit a cheaper candidate P through a separately frozen selector branch
  -> if no P exists, stop the cost-reduction branch without rescuing it with F/T
  -> emit a Qualified Execution Profile only from an independently passed qualification
```

The FEVER 600 is retired from new-rule confirmatory inference; revised policy families require a genuinely fresh cohort. Cross-host transfer and adaptive per-query learned selection remain deferred until a useful competent source policy exists.

The deployable artifact is still an immutable **Candidate Execution Policy** plus a separate **Qualification Attestation** that references its exact digest. The customer-facing Qualified Execution Profile is the qualified pair. Request-specific evidence/proof belongs in a separate receipt. Development, diagnostic and qualified status must be explicit so a calibration leader cannot masquerade as a deployable profile.

Proof-based deterministic completion is permitted only when a registered verifier proves the current request from authorized evidence. Cache, speculation, broad zero-call QA, runtime adapters, and accelerator knobs do not define the product.

See [`V1_1_PRODUCT_DIFFERENTIATION.md`](V1_1_PRODUCT_DIFFERENTIATION.md), the immutable pre-score contract [`V1_1_STAGE1_PREREGISTRATION.md`](V1_1_STAGE1_PREREGISTRATION.md), the completed result [`V1_1_STAGE1_REFERENCE_ONLY_RESULT.md`](V1_1_STAGE1_REFERENCE_ONLY_RESULT.md), and the post-result review [`V1_1_STAGE1_REFERENCE_ONLY_ASTRA_REVIEW.md`](V1_1_STAGE1_REFERENCE_ONLY_ASTRA_REVIEW.md) for the current semantics and evidence limits.

## 2. Product hypothesis

The product hypothesis is not assumed true merely because retrieval is useful in principle.

It must be measured:

> For an existing constrained model, can a compact high-precision grounding layer materially increase everyday factual accuracy and reduce wrong-confident answers at sufficiently low storage, RAM, context-token, latency, energy, privacy/integration and qualification cost that keeping the existing model/hardware is the better engineering choice than a larger model, much larger context, heavyweight RAG stack, remote dependency, or newer device?

The flagship proof compares:

- **A:** model only, one answer-generation call;
- **G:** original-question prefetch -> deterministic Grounding Frame -> host completion when serving-visible state is sufficient, otherwise compact Projection -> the same model, zero or one answer-generation call;
- optional **L:** a justified larger-model/hardware alternative;
- optional rewrite/tool profiles only as separately costed diagnostics.

The first public proof is **everyday factual accuracy + wrong-confident-answer reduction + low false grounding**, not academic catalog breadth.

## 3. Primary interaction model

The flagship v1 path is host-side grounding prefetch **before** model answer generation.

```text
original user question
        |
        v
host security/application scope
        |
        v
Grounding Router -> bounded TargetPlan(s)
        |
        v
Retrieval Providers
(exact/lexical/vector/app/captured-network)
        |
        v
ProviderOutcome(s)
        |
        v
Evidence Policy
(coverage/authority/freshness/merge/conflict/budget)
        |
        v
grouped GroundingFrame
        |
        +-- authoritative unresolved -> host disposition (0 model calls)
        |
        +-- one canonical scalar -> host value (0 model calls)
        |
        `-- remaining text/ordinary knowledge -> compact Model Projection
                                           |
                                           v
                               small/local model -- one answer call
```

The model does **not** need to call `xs_recall` or choose a retrieval provider in the normal path. Earlier `xs_recall`/fact-pack code is an implementation prototype, not the normative API.

A model-generated retrieval rewrite is optional and belongs to a separate profile because it adds a model call, token cost, latency and another failure mode.

The quantitative paths remain separate:

- `xs_calc` — bounded short arithmetic plan;
- `xs_eval` — reviewed semantic/method operation;
- `xs_find` — optional quantitative discovery.

Native tool vs constrained JSON/GBNF selection remains relevant only when the **model must form a quantitative request** or an explicitly selected optional retrieval-tool profile. It is not required for everyday grounding.

## 4. Small model context first

The flagship optimization target is **small evidence, not broad catalog or broad context**.

The model should normally receive only:

- target label/meaning;
- authority (`authoritative` or `supplemental`);
- target state (`grounded`, `none`, `ambiguous`, `conflict`, `unavailable`);
- the few policy-approved Evidence Items needed to answer.

Keep host-side:

- provider catalogs;
- raw similarity/vector scores;
- embedding vectors;
- tenant/security scope IDs;
- access-control metadata;
- source indexes;
- verbose audit logs;
- rejected/conflicting candidate sets.

The deterministic Model Projection is versioned and digest-bound because evidence wording, ordering and labels can materially affect a small model.

For quantitative tasks, keep the same old principle: expose the smallest realistic `xs_calc`/`xs_eval` surface rather than a large operation catalog.

## 5. Fail closed where authority is real

Grounding and calculation have different failure semantics but share one principle: **do not turn uncertainty or invalid state into a plausible successful value.**

For authoritative grounding:

- a valid hit may be used;
- `none` means required authoritative coverage completed and found no usable evidence;
- timeout/error/denied/incomplete coverage becomes `unavailable`, not `none`;
- ambiguous candidates stay `ambiguous`;
- unresolved contradictions stay `conflict`;
- an unresolved authoritative target must not be filled by model memory or a merely supplemental source.

For supplemental grounding, no-hit/unavailable does not imply the fact is false or unknowable; normal model knowledge may still be used under host policy.

For quantitative calls, adapters may normalize syntax/transport but may not invent operands, methods, units, conversions, or results.

This distinction is why benchmark reporting must include both useful-answer rate and wrong-confident-answer/false-grounding rates instead of celebrating refusal alone.

## 6. Competitive axis

ExactScope must not win by imitating the layers that large vendors already own. It is **not** trying to be a faster inference engine, another general RAG framework, another vector database, or a generic guardrail product. Its differentiation target is the combination below:

1. **Model-preserving amplification** — improve task success without replacing the user's model with a larger one.
2. **Zero/near-zero marginal inference cost** — no mandatory second model, reflection pass, semantic repair call, retry loop, or agent loop.
3. **Runtime/vendor neutrality** — the semantic policy should survive movement across llama.cpp-like local runtimes, ORT GenAI, ExecuTorch, LiteRT-class runtimes, Python hosts, C/C++ hosts, and future compatible surfaces.
4. **Semantic rather than throughput optimization** — optimize whether the same inference succeeds, not merely tokens/second.
5. **Low-friction adoption** — tiny runtime surface, bounded dependencies, easy embedding, and no requirement to rebuild the user's AI stack around ExactScope.

The long-term defensive advantage cannot be code size alone; a small feature can be copied. The harder-to-copy asset should be an accumulating body of **cross-runtime semantic optimization knowledge**:

- which small interventions actually produce item-level phase transitions;
- which combinations interact nonlinearly rather than merely additively;
- which host capabilities can safely replace ExactScope-owned infrastructure;
- which capability-conditioned policies transfer across tasks/models without benchmark-specific hardcoding;
- which optimizations preserve parity/fail-closed behavior while lowering real cost.

Current examples of that research pattern include A×B, B×D, G×H, D×I, proof-based J zero-call, and qualified host cache/prompt-profile reuse. These results are evidence for a research direction, not a claim that every model or workload will improve.

The practical competitive test is therefore stronger than "is the package small?":

> **Can ExactScope turn a meaningful number of failures into successes on the model/runtime the user already has, while adding less total cost than upgrading the model or adding another inference stage?**

A product that already has a cheap, trusted semantic optimization layer with comparable cross-runtime evidence and does not benefit from ExactScope's amplification/qualification contract may not need ExactScope. That is an acceptable non-target.

## 7. Market definition

The long-term addressable market still includes physically constrained, already-deployed, private/local, edge and enterprise AI where replacing the model or hardware is expensive. However, the **first commercial validation wedge is intentionally narrower**:

> **high-volume bounded enterprise document answering on a pinned or expensive-to-change model, with authoritative source spans, measurable serving cost, and enough repeated traffic to amortize calibration.**

This wedge is preferred for first product proof because answer correctness and evidence can be audited, the existing host configuration can be made genuinely competent, and the economics of retaining the same model can be measured against both the predeclared reference and a larger/better-model alternative.

Longer-term representative targets still include:

- smart glasses and wearables;
- phones/tablets;
- embedded assistants;
- robots and industrial systems;
- automotive systems;
- privacy-sensitive enterprise stacks;
- later regulated/certifiable systems where arbitrary code execution is undesirable.

Offline remains a capability, not the market definition. Runtime neutrality and on-device suitability are architecture constraints to preserve, not substitutes for proving one concrete customer workload first.

## 8. v1 product scope

The product scope remains intentionally narrow even though the grounding contract permits several retrieval implementations.

The rc3 native/Wasm quantitative runtime and packaging remain useful secondary infrastructure, but **they do not define the v1 flagship product boundary**. The v1 product boundary is the provider-neutral Grounding Contract plus the selected r25 host policy and the native `.xsgi` retrieval/projection core exposed through the C ABI. The stable Linux x86-64 package now ships that runtime with a tiny demonstration provider and explicit package/support boundaries; benchmark-sized NQ provider data stays outside the default install. Historical source `e6c3558642c77e379358b9f59aedd92abf7473f4` remains frozen as the r5 comparison baseline.

The primary v1 integration shape is:

1. **Host-side Grounding Router** — chooses only preregistered, scope-authorized sources/providers for the current application/user context.
2. **Retrieval Provider interface** — exact/lexical, frozen semantic/vector, application-native, or captured host/network providers may implement the same logical contract.
3. **Evidence Policy** — applies authority, revision/validity, duplicate/conflict/ambiguity and context-budget rules.
4. **Grounding Frame** — the compact authority/evidence representation used first by deterministic host completion and, only when needed, by the model projection before one answer-generation call.

The first benchmark candidate freezes a small offline exact/lexical provider **as a reference profile only**. That provider is not the universal product definition and does not grant authority by retrieval score. Vector/application/host providers remain future contract-compatible implementations if their identities, scope and behavior are frozen explicitly.

The v1 release now includes a native C grounding ABI for the deterministic `.xsgi` retrieval/projection core. Routing, provider access, application security scope, authority, and evidence policy remain host concerns and are intentionally not moved into the no-import quantitative Wasm core. A grounding Wasm transport remains deferred until it has its own parity/qualification evidence.

The existing quantitative subsystem remains available through native/Wasm `xs_calc`/`xs_eval` paths. Additional academic domains, dynamic calculation packs, convenience wrappers and broad platform parity are secondary to proving everyday grounding value.

## 9. Grounding-first release status

### Completed before model inference

- rc3 qualification evidence was closed and left immutable;
- the flagship product objective moved from academic/tool-call breadth to everyday factual grounding and hallucination-risk reduction;
- original-question prefetch became the default path, with one answer-generation call in both A and G benchmark arms;
- Source, Retrieval Provider, Evidence Policy, Grounding Frame and Model Projection were separated;
- `authoritative`/`supplemental` and `grounded`/`none`/`ambiguous`/`conflict`/`unavailable` semantics were frozen;
- the provider-neutral machine-readable profile/schemas and deterministic projection were implemented and conformance-tested;
- the first offline reference provider and merge path were implemented behind the provider boundary;
- a physically separated 30-item serving/gold candidate generator, gold-only scorer and zero-inference dry-run were implemented;
- evaluation-package, model/runtime identity, preregistration and benchmark-runner tooling were implemented with no retry, hidden repair or resume path;
- the retained quantitative Rust/C/Wasm code continues to pass its regression suite.

### Historical five-model baseline — completed

The first integrity-corrected five-model benchmark is **r5**, source `e6c3558642c77e379358b9f59aedd92abf7473f4`. It is frozen as historical behavioral comparison evidence. Raw run evidence remains checksum-bound and is never rewritten into newer candidate results.

### Selected r25 behavior — source-run complete

The optimization chain selected **r25** on the product priorities that matter: cross-model accuracy, wrong-confidence/unsupported-assertion safety, model-call count, token cost and tiny-model robustness. The frozen seven-model matched screen spans SmolLM2 135M through Phi-4-mini 3.8B. Its all-model mean moved from 8.1% model-only to 93.3% with ExactScope; the original five-model subset moved from 9.3% to 95.3%. The same semantic scores were reproduced after the native C ABI/release integration work.

The selected host path completes 10 authoritative unresolved cases and 13 canonical scalar facts deterministically in the 30-item G arm, leaving 7 model answer calls. It does not derive values from benchmark gold or regex text post-processing: scalar completion is permitted only when the source already supplied a valid Grounding Contract scalar.

### v1 software release qualification — complete for Linux x86-64

The selected native grounding core is now exposed through the C ABI, packaged into a deterministic Linux x86-64 SDK, checked against the Python reference with exact search-score bits and byte-exact projection, and exercised from a final-archive C11 clean room. The default package also enforces the release footprint hard caps and excludes benchmark-sized NQ provider data from the generic install.

Representative ARM64 storage/RSS/heap/stack/latency/energy/thermal qualification remains required before production-class embedded hardware claims. The absence of that hardware evidence narrows the v1 support matrix; it does not block the stable Linux x86-64 software package.

See [`../ROADMAP.md`](../ROADMAP.md) for the detailed gates.

## 10. Installation target

The target grounding retrofit experience is:

```text
download/receive software + source/index/profile update
  -> verify source/provider/profile manifest and digests
  -> bind allowed user/application/source scope
  -> configure authority + freshness/conflict/evidence budgets
  -> load or connect the selected retrieval provider
  -> run retrieval/policy self-test
  -> prefetch a compact Grounding Frame before the existing model answer call
  -> optionally route actual quantitative work through xs_calc/xs_eval
```

A minimal fully local profile should not require:

- replacing or retraining the model;
- native model tool-call support;
- Rust, Python, Node or Java on the target;
- a package-manager runtime;
- a daemon;
- an ExactScope account;
- a network connection;
- a writable home directory beyond whatever storage the host already uses for its approved evidence/index.

A network-connected profile may use a host provider, but private evidence/query transmission is an explicit product policy rather than a hidden dependency. Developer-side indexing/build tooling may use convenient workstation languages, but that choice must not become a target runtime dependency.

## 11. Evidence before claims

Before ExactScope markets a broad accuracy, latency or energy claim, publish reproducible candidate-bound evidence under [BENCHMARK.md](BENCHMARK.md). rc3 qualification findings may be reported as historical observations, not generalized product claims.

Before a platform is called supported, publish compatibility evidence under [COMPATIBILITY.md](COMPATIBILITY.md).

Before enterprise optimization claims, publish at least one real constrained-target qualification record.

## 12. Commercial direction

The OSS core remains the adoption wedge. The strongest near-term commercial layers described in [COMMERCIALIZATION.md](COMMERCIALIZATION.md) are **grounding source/provider assurance, target-specific Evidence Policy/profile engineering, privacy/freshness/conflict review, benchmark/qualification, LTS/update support and OEM integration assistance**. Reviewed quantitative domain products remain an optional secondary layer.

The business model must not require a proprietary cloud calculation/search service, custody of customer private memory, or an incompatible evaluator fork. A customer should be able to keep its sources and indexes private while using the public Grounding Contract and evidence tooling.

## 13. Current implementation position

The **mature retained subsystem** from rc3 is quantitative:

- deterministic `no_std` numeric kernel and bounded scalar VM;
- bounded `xs_calc` plan-v0.1 over `add/sub/mul/div/powi/sqrt`;
- Tiny JSON/TinyWire plus generated JSON Schema/GBNF/tool/prompt assets;
- reviewed Economics execution and bounded Statistics vector kernels;
- selected semantic `xs_eval` and optional cold/development `xs_find`;
- native typed C ABI and no-import Wasm;
- pack/packc plus optional dynamic-pack architecture;
- deterministic capability/profile compiler and specialization machinery;
- model-surface identity, packaging, security/export audit and qualification infrastructure.

The **stable v1 grounding implementation** now consists of:

- [`GROUNDING_ARCHITECTURE.md`](GROUNDING_ARCHITECTURE.md) plus the normative [`../spec/GROUNDING_CONTRACT_V0_1.md`](../spec/GROUNDING_CONTRACT_V0_1.md);
- the selected host completion order and llama.cpp reference adapter;
- the `no_std`, allocation-free `exactscope-grounding` native core;
- immutable `.xsgi` provider compilation, zero-copy validation, BM25-v1 search, and compact evidence projection;
- the public C ABI in `include/exactscope.h`;
- exact Python/Rust/C-ABI parity tests on NQ development-mirror and HotpotQA screens;
- the deterministic Linux x86-64 stable package in [`../spec/GROUNDING_RUNTIME_BUNDLE_V1.md`](../spec/GROUNDING_RUNTIME_BUNDLE_V1.md);
- a package-local C11 demonstration and final-archive clean-room test;
- explicit 10 MB compressed / 20 MB unpacked default-install hard caps;
- benchmark and publication audits that keep gold, raw evidence, local paths, and internal handoff material outside the public product package.

Earlier `xs_recall`/fact-pack experiments remain non-normative implementation history. The older quantitative `xs_calc`/`xs_eval` subsystem remains available as a secondary capability, but it does not define the v1 grounding product.

Post-v1 product gates are broader provider implementations, long-term compatibility/LTS evidence, and representative physical-device qualification where target-specific RAM/latency/energy/thermal claims are desired. Physical ARM64 qualification is the most important outstanding hardware gate; it is not silently inherited from x86-64 evidence.

## 14. Decision test

Before adding a flagship v1.1 feature, ask:

> Does this materially improve **qualified customer utility or total economics** relative to the competent existing stack and a competent ordinary alternative, while preserving the host-ownership boundary and adding less integration/change-management burden than the value it creates?

Then ask:

1. **Qualified utility:** does it improve a prospectively frozen correctness/evidence/abstention/error objective or preserve the same qualified behavior at meaningfully lower total economics?
2. **Incremental value:** does it beat or simplify at least one competent ordinary alternative such as a fixed configuration or generic tuning/evaluation workflow? If not, why should a customer adopt ExactScope?
3. **Amplification diagnostic:** when the same model/runtime comparison is relevant, does it still create reproducible task-success gains or item-level phase transitions? This is a valuable experiment, not a universal product gate.
4. **Inference cost:** does it avoid mandatory extra model calls, retries, reflection, repair, or hidden agent work?
5. **Portability:** can the semantic rule survive across runtime vendors by borrowing host capabilities instead of importing vendor machinery into core?
6. **Distribution/change cost:** what is the marginal cost in dependencies, cold start, CPU/RAM, tokens, integration, qualification and requalification effort?
7. **Ownership/enforcement:** is ExactScope implementing something the host already owns, and can the supported host integration actually enforce admission/finalization rather than merely consume advisory metadata?
8. **Evidence:** is every qualified claim bound to frozen workload/host/policy/scorer/economic identities with independent qualification and explicit stale/invalidation semantics?
9. **Optional cheaper-policy branch:** if the feature is specifically claiming materially cheaper reference-preserving execution, does its separately preregistered selector satisfy that claim? If not, return `ReferenceOnly(F)` rather than inventing a trade. This is no longer the universal v1.1 feature gate.
10. **Architecture:** does it strengthen the single `admit -> prepare -> Complete|Generate|Reject/Unavailable -> host execution -> finalize -> release` spine rather than create another sidecar path?
11. If the problem is actually deterministic calculation, does it reuse the existing `xs_calc`/`xs_eval` core rather than creating a second semantics?

The long-term desired product is not "the smallest archive" and not "the most features." It is the **Qualified AI Execution Control Plane** described in [`V1_1_ULTIMATE_PRODUCT_ARCHITECTURE.md`](V1_1_ULTIMATE_PRODUCT_ARCHITECTURE.md): preserve the customer's stack, compile only a small semantic policy, qualify the exact behavior/economics prospectively, block stale/unqualified serving through supported integrations, and use no more model intelligence/context/tools/cost than the workload contract requires. Same-model amplification and reference-preserving cost reduction remain important diagnostics/conditional product modes rather than universal gates.
