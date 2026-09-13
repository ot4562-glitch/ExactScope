# ExactScope v1.1+ — ultimate product architecture

Status: **north-star architecture frozen for implementation; individual capabilities remain evidence-gated and must not be marketed before qualification**

Updated: **2026-09-13**

## 1. Ultimate product identity

ExactScope's ultimate customer-facing form is a **Qualified AI Execution Control Plane** for an AI stack that the customer already owns.

Its technical kernel is a **Semantic Execution Policy Compiler**.

Its first shippable/commercial slice remains the narrower **Qualification / Configuration Optimizer**.

The hierarchy is therefore:

```text
Qualified AI Execution Control Plane
  customer-facing north star
        |
        +-- Semantic Execution Policy Compiler
        |     technical kernel / research thesis
        |
        +-- Qualification / Configuration Optimizer
        |     first commercial slice
        |
        +-- Qualified Execution Profile
              immutable deployable artifact
```

The control plane must not become an inference runtime, model provider, vector database, full RAG framework, scheduler, cache implementation, speculative decoder, agent framework, or generic observability product.

ExactScope owns **what behavior is allowed, under which evidence and host capabilities, after which qualification, at what economics, and when that qualification becomes stale**. The host owns **how model execution happens**.

## 2. North-star product sentence

> **ExactScope compiles workload requirements and host capabilities into a small execution policy, independently qualifies that exact policy on fresh evidence, blocks stale or unqualified execution, and requalifies only when behavior-affecting identities change.**

Long-term frontier-model sentence:

> **Use the minimum necessary model intelligence, context, tools, reasoning budget, and serving cost that still satisfies the same qualified workload contract.**

The historical shorthand `Same model. Same runtime. Better answer.` remains a useful special case. The broader north star is:

> **Same stack. Qualified behavior. Minimum necessary intelligence and cost.**

## 3. Customer reason to exist

Customers should use ExactScope only when it measurably removes one or more expensive uncertainties that ordinary prompt/config files and generic eval dashboards leave unresolved:

- which exact model/retrieval/prompt/constraint/reasoning/tool policy is safe and worthwhile to deploy;
- whether the current policy still satisfies workload-owner correctness, evidence, abstention, latency and economic requirements;
- whether a model/runtime/retriever/corpus/prompt update invalidates the prior qualification;
- whether a cheaper or simpler configuration preserves the same qualified workload behavior;
- whether a stronger model is actually the better economic choice;
- whether deployment should be blocked because no candidate is qualified.

A result of `NoQualifiedCandidate`, `ReferenceOnly`, `Stale`, or `UseTheBetterModelInstead` is a valid product outcome.

## 4. Stable ownership boundary

### ExactScope owns

- versioned Workload Contract;
- bounded semantic policy definitions;
- evidence sufficiency/context-admission semantics;
- authority/coverage/freshness/conflict requirements where the workload needs them;
- provenance-preserving evidence projection rules;
- semantic answer-contract lowering;
- deterministic finalization/rejection semantics;
- host capability requirements and legal lowerings;
- immutable Candidate Execution Policy;
- independent Qualification Attestation;
- Qualified Execution Profile pair identity;
- request-bound Execution Receipt;
- drift/invalidation evaluation;
- requalification scope planning;
- qualification/economic experiment lineage;
- later, prospectively earned transfer priors for reducing search/calibration work.

### Host owns

- model weights and provider account;
- retrieval execution, authorization, corpus and index;
- tokenizer/chat-template implementation and exact rendering;
- inference/runtime/execution provider;
- scheduling, batching and concurrency;
- KV/prefix cache implementation;
- structured/constrained decoding implementation;
- speculative decoding implementation;
- accelerator and hardware policy;
- tool execution implementation;
- retries/fallback after ExactScope rejection;
- activation, rollback and production orchestration.

### Binding host enforcement protocol

The control-plane claim is valid only for integrations that make ExactScope admission/finalization **mandatory**, not advisory.

For a supported integration, the trusted host boundary must guarantee:

1. no qualified request reaches model/tool execution before `admit(profile, current_host, workload)` succeeds;
2. the admission receipt binds the exact Qualified Execution Profile, authorized evidence snapshot, rendered request identity and execution settings;
3. behavior-affecting identities are checked again before releasing a result when the host permits in-flight changes;
4. every generated result passes ExactScope finalization before it may be labeled or returned as qualified;
5. an ExactScope rejection may enter only a **separately authorized host fallback path** and never inherits the rejected profile's qualification;
6. future tool side effects require authorization before execution, not only output validation afterward;
7. receipt reuse across a different profile/request/evidence/host identity fails closed.

An unsupported host that can bypass this protocol may still consume ExactScope reports offline, but it is **not** a Qualified AI Execution Control Plane integration.

Attestation authority is stronger than digest pairing: the Qualification Attestation must identify the qualification authority/process and bind the exact frozen evidence/analysis identities that produced the verdict.

## 5. Core artifact model

```text
Workload Contract
        +
Host Capability Manifest
        +
Semantic Policy Source
        |
        v
Semantic Execution Policy Compiler
        |
        v
Candidate Execution Policy
        |
        +---- independent qualification ----+
                                            v
                                Qualification Attestation
                                            |
                                            v
                               Qualified Execution Profile
                                            |
                                  request-time guard
                                            |
                          +-----------------+----------------+
                          |                                  |
                       ADMIT                               REJECT
                          |                                  |
                       prepare()                        stable reason
                          |
           Complete | Generate | Reject/Unavailable
                          |
                     host execution
                          |
                      finalize()
                          |
                   Accept | Reject
                          |
                   Execution Receipt
```

A Candidate Execution Policy never mutates into a qualified artifact. Qualification Attestation references the exact candidate digest. Qualified Execution Profile is the pair.

## 6. Required north-star components

### A. Workload Contract

A restricted declarative description of:

- task/population identity;
- authority/evidence requirements;
- allowed answer domain;
- citation/provenance requirements;
- abstention/unanswerable semantics;
- unacceptable-error rules;
- latency/load requirements;
- economic objective/constraints;
- invalidation policy.

It is not arbitrary user code.

### B. Host Capability Manifest

A typed declaration of what the host can actually provide:

- exact model/runtime identities;
- context capacity;
- exact-fit callback;
- structured-output dialects;
- retrieval interface identity;
- tool surfaces;
- reasoning-effort controls where available;
- cache capability declarations;
- model-call constraints;
- provider/runtime-specific lowering bindings.

Capability declaration is not qualification. Optional host capabilities may be used only when the exact combination has been qualified.

### C. Semantic Execution Policy Compiler

The compiler:

1. type-checks workload obligations;
2. rejects unsupported capability combinations;
3. binds semantic rules to host-owned mechanisms;
4. canonicalizes and hashes the policy;
5. partially evaluates fixed choices into a small execution program;
6. emits deterministic failure semantics;
7. optionally invokes a bounded offline optimizer/search procedure whose rules were frozen before target outcomes;
8. never owns runtime mechanics that belong to the host.

`Compiler` is an engineering statement only while it performs a defined source-to-artifact lowering. It becomes a meaningful product/category claim only if that lowering or accumulated priors materially reduce integration/search/qualification work compared with competent generic alternatives.

The compiler supports two explicitly different obligation classes:

**Runtime-verifiable obligations** have deterministic request-time checks, for example allowed citation/source IDs, source revisions, exact extraction constraints, output-schema membership, declared capability presence, profile/receipt identity and bounded context-admission rules. A hard obligation without a sound lowering/check is rejected as `unsupported-obligation`.

**Empirically qualified properties** are estimated by frozen evaluation rather than proved at request time, for example factual correctness, semantic entailment, useful-answer rate, serious-error rate and customer economics. `Accept` means all implemented deterministic checks passed; it never means the system proved every semantic truth claim.

Retrieval semantics preserve the stable distinction between `none` and `unavailable`: a top-k miss or incomplete coverage cannot be lowered into authoritative absence unless the Workload Contract contains a sound prospectively registered coverage rule.

### D. Qualification Engine

The qualification engine must:

- bind exact model/runtime/retrieval/workload/scorer/economic identities;
- support development, diagnostic, failed, inconclusive and qualified status explicitly;
- keep calibration/selection separate from independent qualification;
- allow hard stop outcomes;
- report quality, evidence support, abstention, latency, resource and total-economic results;
- emit no Qualified Execution Profile on failure/inconclusive results.

### E. Execution Guard

Before serving, the guard checks:

- candidate/attestation digest pairing;
- workload identity;
- host/model/runtime/tokenizer-template/retrieval identities;
- qualification status;
- invalidation state;
- required capabilities;
- workload-specific activation constraints.

If any mandatory identity is stale or unsupported, fail closed before model generation.

### F. Drift + Requalification Planner

Changes are classified prospectively:

```text
identity-only / non-behavioral
  -> no behavioral requalification

targeted behavior-affecting change
  -> targeted requalification if prospectively authorized

major behavior-affecting change
  -> full requalification

unknown change
  -> fail closed / full requalification
```

The planner emits the reason, affected obligations and required evidence; it does not silently carry old scores forward.

Qualification validity has two deployment scopes:

- **inspectable/pinned host scope** — behavior-affecting local model/runtime/tokenizer/retrieval identities can be cryptographically or host-assertedly pinned;
- **provider-observable scope** — frontier/cloud providers may expose only model IDs, API capabilities and provider guarantees. The profile records each dependency as `pinned`, `host-asserted`, `provider-guaranteed`, or `unknown`, plus any expiry/observation-triggered invalidation rule.

Unknown or opaque provider behavior must never be represented as an exact internal identity. A provider model-tier change creates a separate candidate. Provider-observable profiles require an explicit validity window or observation-triggered requalification policy where stronger pinning is impossible.

For corpus/retrieval updates, targeted requalification is allowed only when the Workload Contract prospectively defines dependency/coverage partitions that prove which obligations are unaffected. Otherwise the planner requires full requalification.

### G. Total-Economics Optimizer

Optimization targets **customer economics**, not token count alone.

Potential components include:

- inference/compute;
- retrieval/index work;
- model calls/tokens;
- latency/capacity value;
- human review/escalation;
- fallback to a stronger path;
- unacceptable-error remediation/risk proxy when approved;
- integration effort;
- calibration/qualification cost;
- refresh/requalification cost;
- maintenance burden.

A stronger model may be selected if it wins total economics and satisfies the workload contract.

### H. Transfer Prior Registry — deferred until earned

Only after multiple fresh qualified outcomes may ExactScope learn a reusable mapping:

```text
workload descriptor
x host capability vector
x policy/intervention vector
      ->
quality / regression / economics / qualification outcome
```

A transfer prior is valuable only if, before target outcomes, it reduces candidate executions, labels, integration work or time-to-qualified policy while preserving the same independent qualification strength.

## 7. Frontier-model extension

ExactScope must remain useful even when the underlying model is very strong.

For frontier models the primary optimization surface shifts from raw answer uplift toward **qualified reliability and minimum necessary intelligence/cost**:

- reasoning effort / thinking budget;
- context/evidence budget;
- retrieval depth;
- tool eligibility;
- structured-output mode;
- citation/evidence requirements;
- abstention/rejection rules;
- cache eligibility hints;
- model tier/model choice when the host permits it.

A frontier-model result may therefore look like:

```text
same model/provider
same workload contract
same independent qualification strength
less reasoning/context/tool work
lower latency or lower total economics
```

or, legitimately:

```text
stronger model
simpler policy
better total economics
=> recommend stronger model instead of ExactScope intervention
```

No frontier-specific adaptive router, model cascade, runtime judge, reflection loop or hidden quality retry is part of the initial implementation.

## 8. Product slices and implementation order

### Slice 1 — immutable qualification core — now

Implement:

- Workload Contract schema;
- Host Capability Manifest schema;
- Candidate Execution Policy schema;
- Qualification Attestation schema;
- Qualified Execution Profile verifier;
- Execution Receipt schema;
- deterministic canonical digests;
- fail-closed status/reason enums.

### Slice 2 — execution guard + drift/requalification — next

Implement:

- profile admission/identity checking;
- invalidation rules;
- stale-profile classification;
- targeted/full requalification planner;
- tests proving stale profiles cannot serve.

### Slice 3 — competence-gated enterprise DocQA proof

Implement/freeze:

- real retrieval adapter boundary;
- Base and Integrated fixed profiles;
- owner-approved competence/evidence/abstention/error gates;
- total-economics model;
- independent confirmatory qualification;
- better-model/simple-config comparator where practical.

### Slice 4 — live attached amplification/economics test

On a real local model/runtime, compare **v1 stable behavior vs v1.1 fixed Integrated behavior** under a fresh, separately declared diagnostic workload to answer:

1. does the semantic amplification signal still exist after the architectural narrowing?;
2. is v1.1 better on task quality/evidence behavior than v1 under the same model/runtime?;
3. is v1.1 cheaper in real serving resources or total diagnostic economics?;
4. which mechanism contributes the observed difference?;
5. does any result justify promotion into the enterprise study, or is it only development evidence?

Do not reuse the sealed FEVER 600. Do not reinterpret development attached tests as product qualification.

### Slice 5 — frontier-model host lowering

After the same artifacts work locally, add one frontier-capable host adapter that can bind capabilities such as reasoning effort, structured output, tool eligibility and context limits without owning provider execution.

The first goal is **conformance/lowering**, not a marketing benchmark.

### Slice 6 — transfer/economic compiler

Only after useful qualified source policies exist, compare prior-informed search with cold search and generic tuning on untouched workloads/hosts. Earn the stronger compiler/moat claim prospectively.

## 9. Promotion gates for the north-star claim

Do not call ExactScope a broadly established AI execution control plane merely because these modules exist.

Promotion requires, in order:

1. immutable qualification artifacts and fail-closed execution guard work correctly;
2. one competent enterprise DocQA workload shows customer-relevant value;
3. the system survives a model/retrieval/corpus change and performs correct requalification/invalidation;
4. at least one second independent workload/integrator reproduces useful value;
5. one frontier-capable host lowering preserves semantics without taking over runtime ownership;
6. transfer priors prospectively reduce search/qualification burden against competent generic baselines.

## 10. Explicit anti-goals

Do not build merely because AI can generate the code:

- a competing inference runtime;
- a vector database;
- a generic RAG framework;
- a generic experiment dashboard;
- a broad agent framework;
- a second-model judge on the normal serving path;
- hidden retries/reflection/quality repair;
- a universal optimizer over every runtime knob;
- a large compiler DSL before restricted contracts prove value;
- adaptive routing before competent fixed-policy value exists;
- speculative/cache/scheduler implementations already owned by runtimes;
- a control-plane UI before the immutable core and qualification lifecycle are useful through CLI/library APIs.

The implementation may be ambitious, but scope growth must follow evidence and ownership boundaries rather than code-generation convenience.

## 11. Invariant

The architectural invariant is:

> **No behavior-affecting decision may become deployable merely because it scored well during development. It must exist as an immutable policy, be independently qualified against a frozen workload contract and host identity, and be rejected when that qualification is stale.**

Everything else in the north-star architecture is subordinate to that invariant.
