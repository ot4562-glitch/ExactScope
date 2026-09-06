# ExactScope grounding architecture

Release context: **rc4 grounding-first product architecture after rc3 qualification closeout**

Normative logical contract: [`../spec/GROUNDING_CONTRACT_V0_1.md`](../spec/GROUNDING_CONTRACT_V0_1.md)

This document explains the system architecture behind that contract. Where examples here and the normative specification differ, the specification wins.

## 1. Product sentence

ExactScope is a **small, provider-neutral grounding layer for constrained and on-device models**. It aims to make ordinary factual answers more reliable by supplying compact, scoped evidence before answer generation instead of asking a small model to reconstruct every fact from weights or to perform a fragile retrieval tool call.

The consumer-shaped thesis is:

> **Keep the small model. Add a tiny, high-precision evidence path. Improve everyday factual reliability without requiring a larger model, a giant context window, or a heavyweight always-remote RAG stack.**

The existing deterministic quantitative subsystem remains useful, but it is secondary:

```text
ordinary factual question -> grounding -> model answer
quantitative question      -> xs_calc/xs_eval -> deterministic result -> model answer
mixed question             -> grounded facts + deterministic calculation -> model answer
```

Academic-domain breadth is not a current flagship objective.

## 2. Default serving path: prefetch before generation

The common path does not require a model-generated retrieval request.

```text
User / application question
          |
          v
+--------------------------+
| Host security scope      |
| original QueryEnvelope   |
+--------------------------+
          |
          v
+--------------------------+
| Grounding Router         |
| TargetPlan(s)            |
+--------------------------+
          |
          v
+--------------------------+
| Retrieval Providers      |
| exact / lexical / vector |
| app-native / captured net|
+--------------------------+
          |
          v
+--------------------------+
| Evidence Policy          |
| coverage / authority     |
| freshness / merge        |
| conflict / ambiguity     |
| budgets                  |
+--------------------------+
          |
          v
+--------------------------+
| grouped GroundingFrame   |
+--------------------------+
          |
          v
+--------------------------+
| deterministic            |
| Model Projection         |
+--------------------------+
          |
          v
   small model called once
          |
          v
       final answer
```

Compared with mandatory model tool calling, this removes:

- one model routing decision;
- one tool-call syntax/protocol failure class;
- the need to serialize a broad retrieval/tool schema into every prompt;
- an extra model turn in the common path;
- dependency on model-specific tool-aware chat templates.

A model-generated query rewrite is an optional separate profile and benchmark arm. It is not hidden inside the default prefetch path.

## 3. Architecture has two planes

### 3.1 Serving plane

The serving plane handles one question:

1. Host establishes security/application scope.
2. Router maps the question to bounded factual targets.
3. Providers search only their allowed source bindings.
4. Evidence Policy validates outcomes and builds independent target states.
5. Model Projection exposes the minimum safe evidence to the model.
6. The model answers once.

### 3.2 Identity/evidence plane

The identity plane makes the serving behavior auditable and benchmarkable. It binds:

- `GroundingProfile`;
- router implementation/configuration;
- source snapshots;
- provider/index/preprocessing/ranking identities;
- embedding model/index identity when semantic retrieval is used;
- merge/freshness/conflict/ambiguity policies;
- timeout/retry/budget policy;
- Model Projection renderer/template;
- exact run-time outcomes and captured remote evidence.

The system deliberately separates immutable behavior configuration from per-query outcomes. A provider timeout is evidence from a run, not a profile setting; the timeout **rule** is profile configuration.

## 4. The product boundary is provider-neutral

ExactScope does not define product value as one search algorithm.

A provider may be:

- exact-key lookup;
- alias lookup;
- compact inverted/lexical search;
- deterministic BM25-like ranking;
- prefix/n-gram search;
- frozen embedding/vector retrieval;
- application-native memory/database search;
- captured host/web/search evidence.

The stable product boundary is instead:

```text
Source -> Retrieval Provider -> ProviderOutcome
       -> Evidence Policy -> GroundingFrame -> Model Projection
```

### 4.1 Why this matters

If the product contract were "ExactScope fact pack + one lexical matcher," it would be cheap but too narrow for general assistant use.

If the contract were "ExactScope owns one embedding model/vector database," it would lose embedded portability and force one memory/storage/runtime profile on every OEM.

Provider neutrality allows:

- a tiny exact/lexical baseline on very small devices;
- a semantic provider on larger local systems;
- an existing OEM memory/search system to plug into the same policy/evidence contract;
- captured remote search to be evaluated without making the core network-dependent.

Provider neutrality does **not** mean provider behavior is untracked. Every provider that affects benchmark results is identity-bound.

## 5. Routing is claim-aware, not answer-aware

The Router decides **what factual claim slots the product is allowed to ground**, not what the correct answer is.

For example:

```text
Question: "What filter does the hall purifier use, and is it in stock?"

Target A
  key: device.hall-purifier.filter
  authority: authoritative
  provider: installed manual index

Target B
  key: retail.filter.stock
  authority: supplemental or authoritative depending on product
  provider: local inventory / captured remote provider
```

A target includes:

- stable `target_key`;
- compact non-answer-bearing `target_label`;
- namespace;
- authority;
- explicit provider/source bindings;
- required-coverage/sufficiency rule.

This solves three important problems.

### 5.1 Compound questions

A frame may contain one grounded target and one unresolved target. "Grounded" is not a global truth bit for the whole question.

### 5.2 Mixed authority

Authoritative private/device state and supplemental public reference evidence can coexist without making the whole frame globally authoritative.

### 5.3 Benchmark leakage

The router cannot consume benchmark gold target/source/answer labels in the flagship product arm. It uses only production-visible question/application context and its frozen profile.

## 6. Authority is policy, not provider metadata

There are two authority modes per target/source binding.

### Authoritative

Use when the configured source is the product authority for that factual target, for example:

- saved parking location;
- current device/application setting;
- installed product manual revision;
- organization/private record;
- a product-local state value.

An authoritative target can produce:

- `grounded`;
- `none`;
- `ambiguous`;
- `conflict`;
- `unavailable`.

A provider does not get to mark itself authoritative. The host/profile establishes that relation before retrieval.

### Supplemental

Use when a source may improve the answer but is not exhaustive, for example:

- partial local reference knowledge;
- an FAQ subset;
- cached search snippets;
- a small general-knowledge pack.

A supplemental no-hit does not force refusal and does not prove the fact false. The model may fall back to ordinary model knowledge under host policy.

This prevents a small local knowledge cache from accidentally making an assistant refuse nearly every question it does not cover.

## 7. Coverage determines the meaning of `none`

The most important fail-closed rule is:

> **Authoritative `none` means the required authoritative source coverage completed successfully and found no usable evidence. It does not mean "we failed to retrieve something."**

Therefore:

- timeout -> `unavailable`, not `none`;
- access denied -> `unavailable`, not `none`;
- provider error -> `unavailable`, not `none`;
- candidate budget exhausted before complete search -> not `none`;
- unresolved required provider -> `unavailable` unless a frozen sufficiency rule says the successful subset is enough.

This distinction is central to hallucination reduction. A model must not be told "the authoritative source has no answer" when the source was never fully searched.

## 8. Multiple providers merge deterministically

Providers may run concurrently, but concurrency must not change output.

`GroundingProfile` freezes:

- source/provider priority;
- candidate validation;
- equivalence/deduplication rule;
- freshness rule;
- ambiguity/conflict rule;
- cross-provider combination rule;
- deterministic ordering and tie-breakers;
- top-k selection;
- whole-item context truncation;
- required coverage and sufficiency rules.

Raw provider relevance scores are provider-local. They are not compared across providers unless the profile explicitly defines and identity-binds a calibrated transform.

Provider completion order never becomes a hidden ranking signal.

## 9. Grounding Frame is grouped by factual target

The host-side logical result is a grouped frame:

```json
{
  "v":1,
  "qid":"q-42",
  "profile_sha256":"...",
  "groups":[
    {
      "target_key":"device.hall-purifier.filter",
      "target_label":"Hall purifier replacement filter",
      "authority":"authoritative",
      "state":"grounded",
      "items":[
        {
          "source_id":"manual.hall-purifier",
          "item_id":"replacement-filter",
          "source_revision":"7",
          "content":{"kind":"scalar","type":"string","value":"AF-210","unit":null}
        }
      ]
    }
  ]
}
```

The frame does not expose security scope, provider secrets or raw vector/similarity data to the model.

Host/audit sidecars keep richer information:

- Routing Plan;
- Provider Outcomes;
- source snapshot references;
- coverage and sufficiency decisions;
- rejected/conflicting/deduplicated candidates;
- frame and projection hashes.

## 10. Evidence has stable content identity

Each Evidence Item has:

- `source_id`;
- source-local `item_id`;
- opaque `source_revision`;
- target association;
- typed content;
- optional canonical-content SHA-256;
- optional validity metadata.

Content may be:

- UTF-8 text;
- typed scalar (`string`, `boolean`, `integer`, `decimal`, `timestamp`, optional unit);
- canonical JSON for profiles that explicitly support it.

A semantic/vector provider can rank candidates however it wants internally, but the evidence eventually shown to the model is still an identity-bound Evidence Item, not an anonymous similarity result.

Deduplication may hide duplicate text from the model but must retain provenance in audit evidence.

## 11. Freshness is explicit and clock-independent in the core

Evidence may carry:

- `observed_at`;
- `valid_from`;
- `valid_until`.

Validity intervals use `[from, until)` semantics.

The minimum embedded core does not need a wall clock. The host provides an effective `as_of` when freshness matters. The profile defines what missing time metadata means.

`source_revision` is opaque and cannot be treated as chronology unless the source contract explicitly defines that ordering.

This allows stale-knowledge benchmarks without teaching the model or runtime to guess which revision is newer.

## 12. Model Projection is deliberately smaller than the frame

The model should see the evidence necessary to answer, not retrieval machinery.

A deterministic Model Projection keeps:

- target label;
- authority;
- target state;
- compact evidence content;
- minimal source/revision marker only when useful to answer or enforce policy.

It drops or keeps host-side:

- `security_scope_id`;
- tenant/user IDs;
- raw provider scores/distances;
- embedding vectors;
- internal indexes;
- access-control metadata;
- verbose source catalogs;
- provider error logs.

The renderer itself is versioned/digest-bound because different wording/ordering can change small-model behavior.

## 13. Evidence is data, not instructions

Retrieved text is hostile/untrusted model input even when it came from an approved source.

The host must:

- place Grounding Policy above evidence in model instruction priority;
- deterministically escape/delimit evidence;
- never grant tool/network/security permissions based on evidence text;
- never let evidence redefine its own authority or scope;
- never execute instructions found in evidence.

This architecture does not claim perfect prompt-injection resistance. Adversarial evidence such as "ignore previous instructions" must be included in security/conformance and model benchmark cases.

## 14. Security scope is established before retrieval

Grounding data may be more sensitive than the model weights.

The host owns authentication/authorization and creates an opaque effective security-scope identity before routing.

Rules:

- no cross-user/tenant source merge without explicit host sharing policy;
- a cache result from a different scope is invalid by default;
- providers cannot broaden source scope;
- private query/evidence is not sent to a network provider without explicit profile/host authorization;
- security identifiers do not enter the model projection;
- benchmark/public evidence uses synthetic/sanitized private-style facts unless disclosure is authorized.

## 15. Remote and semantic providers remain reproducible

A semantic/vector provider qualification binds:

- embedding model/revision/file digest;
- tokenizer/preprocessing digest;
- vector dimension/precision;
- distance metric;
- index build/content digest;
- ranking/reranking configuration.

A remote provider qualification captures:

- provider/endpoint identity where allowed;
- request options;
- returned response/evidence snapshot;
- timeout and provider-outcome records.

A live web/search query alone cannot be replayed and therefore is not sufficient frozen benchmark evidence.

## 16. Resource budgets are profile-level contracts

A concrete profile freezes the maximums appropriate to the device class:

- query bytes;
- target count;
- provider/source bindings;
- attempts/timeouts;
- candidate count;
- evidence item count/content bytes;
- host frame bytes;
- model-visible evidence items/bytes;
- optional tokenizer-specific token ceiling;
- model answer calls;
- optional rewrite calls;
- provider/index storage/RAM targets where claimed.

The logical contract intentionally does not force one universal number. A wearable exact/lexical profile and a phone vector profile should share semantics while having very different budgets.

## 17. Reference deployment profiles

These are architecture categories, not support claims.

### 17.1 Tiny local profile

```text
source snapshot
 -> compact exact/lexical provider
 -> deterministic policy
 -> compact projection
 -> one local model call
```

Use when storage/RAM are extremely constrained and source vocabulary is bounded.

### 17.2 Local semantic profile

```text
source snapshot
 -> frozen local embedding/index provider
 -> deterministic policy
 -> compact projection
 -> one local model call
```

Use when paraphrase coverage justifies embedding/index cost.

### 17.3 Application-native profile

```text
existing app memory/search API
 -> ExactScope Provider adapter
 -> Evidence Policy
 -> projection
 -> model
```

Use when an OEM already owns a trustworthy data/search system.

### 17.4 Hybrid/captured-network profile

```text
local authoritative sources + optional remote supplemental source
 -> separate provider outcomes
 -> target-aware policy
 -> grouped frame
 -> projection
 -> model
```

Remote failure never becomes authoritative no-hit, and benchmark evidence captures remote snapshots.

## 18. Relationship to the quantitative subsystem

The grounding architecture does not discard the mature exact numeric core.

A host may route after or alongside grounding:

```text
Question
  +--> factual target -> GroundingFrame
  +--> bounded arithmetic -> xs_calc
  +--> reviewed quantitative method -> xs_eval

final model/rendering receives only validated facts/results
```

Important separation:

- `xs_find` remains quantitative operation discovery;
- prototype `xs_recall` code is not the normative grounding API;
- native-tool/constrained-request negotiation remains useful when the **model** must form a quantitative request;
- ordinary grounding is host-prefetched and does not require that envelope.

## 19. Candidate identity

A grounding benchmark result belongs to the exact combination of:

- source commit/release artifact;
- Grounding Contract/profile digest;
- router/configuration;
- source snapshots;
- provider/index identities;
- embedding identity if any;
- policy/merge/freshness/timeout/budget rules;
- Model Projection bytes/template;
- model/runtime/quantization/generation settings;
- corpus/scorer identity;
- raw per-query routing/outcome/frame/projection records.

Changing one behavior-affecting component creates a new candidate identity.

## 20. Product proof

The architecture becomes a product claim only after a frozen candidate demonstrates, across several small models:

- higher everyday factual accuracy;
- lower wrong-confident-answer rate;
- lower authoritative unsupported-assertion rate;
- high retrieval/evidence precision;
- low false-grounding rate;
- correct private/device memory recovery;
- correct stale-revision override;
- correct authoritative no-answer and provider-unavailable behavior;
- robust handling of distractors and adversarial evidence;
- justified token/latency/storage/RAM overhead;
- no mandatory native tool support;
- no post-result benchmark-specific retrieval tuning.

Until then, public wording must say **design / candidate / intended to improve**, not "hallucination solved" or "accuracy improved."

## 21. Implementation rule

Implementation should follow the logical contract, not the existing prototype.

The first concrete implementation is allowed to choose a small exact/lexical provider for portability, but it must leave the provider boundary open for a later vector/application provider without changing Grounding Frame semantics.

The correct implementation order is:

1. freeze logical contract and architecture;
2. freeze concrete `GroundingProfile`/manifest/schema;
3. implement provider interface + minimum local provider;
4. implement deterministic policy/merge/frame builder;
5. implement deterministic Model Projection;
6. implement audit/preregistration/benchmark dry-run paths;
7. package and clean-room test without inference;
8. only then freeze a benchmark candidate and begin model inference.
