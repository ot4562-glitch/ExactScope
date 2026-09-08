# ExactScope Grounding Contract v0.1

Status: **FROZEN_FOR_IMPLEMENTATION — rc4 logical contract; no P0 semantic blockers in final read-only Codex review (2026-09-06)**

This specification defines the provider-neutral logical boundary for ExactScope everyday grounding. It is the normative rc4 grounding contract. It does **not** standardize one search algorithm, one fact-pack format, one embedding model, one storage engine, one model tool protocol, or one transport encoding.

The intended common path is:

```text
original user question
  -> host-validated security scope
  -> deterministic/profile-bound routing plan
  -> one or more retrieval providers
  -> provider outcomes
  -> evidence policy / merge
  -> grouped Grounding Frame
  -> deterministic Model Projection
  -> one small-model answer call
```

The existing `xs_calc` / `xs_eval` quantitative subsystem is separate. A mixed host may combine grounded facts with deterministic calculation, but ordinary factual grounding does not require a model-visible tool call.

## 1. Normative language and goals

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are normative requirements in this document.

The contract exists to make grounding:

- useful for small and on-device models;
- independent from native tool-call support;
- provider-neutral;
- explicit about authority and claim coverage;
- safe under partial provider failure;
- deterministic at the policy/merge/projection boundary;
- auditable by source, provider, profile and content identity;
- compatible with private/local and supplemental public sources;
- measurable without hiding retrieval, policy or model failures;
- implementable without requiring a network, clock, tokenizer, JSON parser, or allocator inside the minimum embedded core.

## 2. Non-goals

This contract does not define:

- a universal web search engine;
- a universal embedding model;
- a universal truth-ranking algorithm for arbitrary contradictory internet sources;
- a general long-context RAG framework;
- model fine-tuning;
- user authentication or account management;
- memory write/retention consent policy;
- remote transport encryption;
- a guarantee that all model hallucinations disappear;
- a guarantee that quoting or delimiting evidence makes prompt injection impossible.

## 3. Planes and roles

The design has a **serving plane** and an **identity/evidence plane**.

### 3.1 Serving plane

1. **Host** validates user/application/tenant scope and creates a `QueryEnvelope`.
2. **Grounding Router** resolves zero or more bounded `TargetPlan` records from production-visible context.
3. **Retrieval Providers** return per-target `ProviderOutcome` records.
4. **Evidence Policy** validates coverage, freshness, authority, ambiguity, conflict, deduplication and budgets.
5. **Grounding Frame Builder** emits one `GroundingFrame` containing independent target groups.
6. **Model Projection** deterministically serializes the frame into the compact evidence block shown to the model.

### 3.2 Identity/evidence plane

The following are immutable or digest-bound for a candidate:

- `GroundingProfile`;
- source snapshot identities;
- provider/index identities;
- router identity/configuration;
- evidence-policy identity;
- projection/renderer identity;
- benchmark corpus and scorer identities when qualification is performed.

Per-run provider outcomes and remote snapshots are evidence records, not profile configuration.

### 3.3 Source

A Source owns or represents factual content, revision semantics, scope and lifecycle. Examples include device/application state, user-approved private memory, product manuals, organization records, local reference data, application-native stores and captured remote-search results.

A Source is not required to use an ExactScope file format.

### 3.4 Retrieval Provider

A Retrieval Provider accepts a bounded query under a validated target/source binding and returns candidates plus an invocation status. Exact-key lookup, lexical search, BM25-like search, n-gram search, frozen vector retrieval, application-native search and captured remote search may all implement this role.

A provider MUST NOT assign authority. Authority is host/profile policy.

## 4. `GroundingProfile` — immutable behavior configuration

A candidate MUST bind one immutable `GroundingProfile` and its SHA-256 digest. The profile defines behavior that would otherwise make two runs incomparable.

Conceptual shape:

```json
{
  "v": 1,
  "profile_id": "exactscope.grounding.consumer-small@0.1.0",
  "router": {"id":"router.lexical-hints@1","config_sha256":"..."},
  "targets": [],
  "providers": [],
  "merge_policy": {"id":"merge.v1","config_sha256":"..."},
  "projection": {"id":"projection.compact-v1","template_sha256":"..."},
  "limits": {},
  "timeouts": {},
  "rewrite": {"enabled":false},
  "privacy": {},
  "profile_sha256": "..."
}
```

The canonical serialized profile used for `profile_sha256` MUST use the candidate's declared canonical profile encoding. The first implementation MAY use canonical UTF-8 JSON, but the logical contract does not require JSON on target.

The profile MUST freeze at least:

- contract major version;
- profile ID/revision;
- router implementation/configuration identity;
- allowed target namespaces;
- authority policy per target/source binding;
- provider/source bindings;
- which bindings are `required` for authoritative coverage;
- provider/index/preprocessing/ranking identity;
- source-priority and sufficiency rules;
- deduplication rule;
- cross-provider merge rule;
- deterministic ordering and tie-break rule;
- ambiguity rule;
- conflict rule;
- freshness/validity rule;
- provider timeout/retry/cancellation/late-result rule;
- candidate/item/byte/depth limits;
- model-visible item/byte/token budget policy;
- whole-item truncation rule;
- Model Projection renderer/template identity;
- whether bounded query rewrite is enabled;
- rewrite model/interface/budget identity when enabled;
- provider network/privacy permissions;
- provider-unavailable behavior;
- any rule that can change `GroundingFrame` state or model-visible evidence.

A behavior-affecting profile change creates a new candidate identity for benchmark purposes.

## 5. `QueryEnvelope`

`QueryEnvelope` is host-side. It binds the original question to the exact profile and security scope before retrieval.

Conceptual shape:

```json
{
  "v": 1,
  "qid": "q-000042",
  "profile_sha256": "...",
  "q": "What replacement filter does the hall purifier use?",
  "security_scope_id": "opaque-host-scope-7",
  "as_of": "2026-09-06T15:00:00+09:00"
}
```

Required logical values:

- `v` — contract major version;
- `qid` — run-unique query identity;
- `profile_sha256` — exact `GroundingProfile` digest;
- `q` — the original user question, unmodified by a retrieval rewrite;
- effective `security_scope_id` — opaque host-validated access/scope identity.

`as_of` is required when any selected target/source freshness rule depends on time.

An embedded integration MAY omit a serialized `security_scope_id` or `as_of` field only when the effective value is supplied by a fixed host/profile binding. The logical value still exists and MUST be part of the candidate/run identity where it affects behavior.

Rules:

- `qid` MUST bind the Routing Plan, Provider Outcomes, Grounding Frame and audit record.
- The provider MUST NOT broaden `security_scope_id`.
- `security_scope_id` MUST NOT be model-visible.
- A model-generated rewrite MUST NOT overwrite `q`; it is a separate record with its own identity.
- Benchmark gold labels/answers MUST never be present in `QueryEnvelope`.

## 6. Optional `QueryRewrite`

The default prefetch profile does not use a model-generated rewrite.

If a separate rewrite profile is enabled, record:

- `qid`;
- original `q` identity/hash;
- rewrite text;
- rewrite model/runtime/template/grammar identity;
- rewrite call/token/latency budget;
- rewrite output digest/status.

A rewrite MUST be bounded and MUST NOT contain or receive the benchmark expected answer, expected source, expected evidence ID or expected target key.

A failed rewrite MUST NOT be silently retried or replaced after seeing the final answer unless that exact retry policy was frozen in the profile.

## 7. `RoutingPlan` and claim targets

The Router runs before provider retrieval and produces zero or more `TargetPlan` records.

Conceptual shape:

```json
{
  "qid":"q-000042",
  "router_id":"router.lexical-hints@1",
  "router_config_sha256":"...",
  "targets":[
    {
      "target_key":"device.hall-purifier.filter",
      "target_label":"Hall purifier replacement filter",
      "namespace":"device.manual",
      "authority":"authoritative",
      "bindings":[
        {"provider_id":"manual-index","source_ids":["manual.hall-purifier"],"required":true}
      ],
      "sufficiency_rule_id":"all-required-v1"
    }
  ]
}
```

### 7.1 `target_key`

A `target_key` identifies the factual claim slot being grounded, such as an entity/property pair or another product-defined factual target.

Rules:

- A target key MUST come from production-realistic router/profile logic, not benchmark gold.
- `target_key` MUST be stable within its namespace/profile revision.
- `target_label` is a compact model-readable description and MUST NOT contain the answer.
- An unresolved router result MUST NOT manufacture an authoritative `none` state.
- If the router cannot safely establish an authoritative target, it emits no authoritative target or emits an explicitly unavailable/ambiguous route according to the profile; it does not claim the source was searched exhaustively.

### 7.2 Authority

`authority` is one of:

- `authoritative` — the configured source binding is product authority for this target;
- `supplemental` — evidence is useful but non-exhaustive.

Authority is assigned by host/profile policy, never by provider output and never by evidence text.

### 7.3 Provider/source bindings

Each target contains explicit bindings:

```text
(provider_id, source_ids[], required)
```

This prevents ambiguity about which provider covers which sources.

For authoritative targets, `required=true` means the binding participates in the minimum coverage needed to assert a true authoritative no-hit unless a named frozen sufficiency rule explicitly permits a smaller completed subset.

## 8. `ProviderOutcome`

Each provider invocation produces one host/audit-side outcome bound to one query and target.

Conceptual shape:

```json
{
  "qid":"q-000042",
  "target_key":"device.hall-purifier.filter",
  "provider_id":"manual-index",
  "attempt":1,
  "source_snapshot_refs":["manual.hall-purifier@sha256:..."],
  "status":"ok",
  "complete":true,
  "candidates":[],
  "reason":null
}
```

`status` is one of:

- `ok` — provider completed successfully and returned one or more candidates;
- `none` — provider completed successfully, covered the declared source binding, and returned zero candidates;
- `timeout` — deadline expired;
- `error` — provider failed for another typed reason;
- `denied` — host/provider policy denied access;
- `budget_exceeded` — provider/candidate budget prevented completion.

Rules:

- `ok` normally has at least one candidate.
- `none` MUST mean successful **complete** empty retrieval for that invocation/binding.
- `timeout`, `error`, `denied`, `budget_exceeded` and incomplete coverage MUST NOT be converted to `none`.
- Partial candidates accompanying an incomplete/failure outcome MAY be retained in audit evidence, but MAY be used in the final frame only when a frozen profile rule explicitly permits them.
- Raw scores from different providers MUST NOT be compared as though they share one scale unless the profile defines a calibrated cross-provider transform and freezes its identity.
- Provider completion order MUST NOT affect final merge order.

### 8.1 Timeout and retry semantics

The profile MUST define:

- deadline measurement domain and start point;
- timeout per provider or whole retrieval phase;
- maximum attempts;
- retryable status classes;
- retry backoff if any;
- cancellation behavior;
- treatment of results arriving after the deadline;
- whether a partial result can satisfy a target.

A late result MUST be ignored once the frozen policy declares the invocation timed out, unless the profile explicitly defines a deterministic grace rule.

## 9. `EvidenceItem`

An Evidence Item is provider-independent factual data plus provenance identity.

Conceptual shape:

```json
{
  "source_id":"manual.hall-purifier",
  "item_id":"replacement-filter",
  "source_revision":"7",
  "target_key":"device.hall-purifier.filter",
  "content":{
    "kind":"scalar",
    "type":"string",
    "value":"AF-210",
    "unit":null
  },
  "content_sha256":"...",
  "observed_at":null,
  "valid_from":null,
  "valid_until":null
}
```

### 9.1 Identity

The stable logical identity is at least `(source_id, item_id, source_revision)`.

- `item_id` needs to be unique only within `source_id` unless a profile declares a stronger rule.
- `source_revision` is opaque. It MUST NOT be compared numerically/lexically as chronology unless the source contract explicitly says to do so.
- Deduplication MUST preserve all relevant provenance references even if duplicate content is shown only once to the model.

### 9.2 Authority inheritance

Evidence Items MUST NOT be trusted to declare their own authority. Effective authority is inherited from the validated TargetPlan/source binding.

If an external adapter carries an authority field, the policy MUST verify exact equality with the inherited authority and reject mismatch.

### 9.3 Content union

`content.kind` is one of:

- `text` — UTF-8 evidence text;
- `scalar` — typed scalar factual value;
- `json` — structured canonical JSON value for profiles that explicitly support it.

#### Text

Text is treated as opaque UTF-8 data. No Unicode normalization, case folding or line-ending rewriting is implied by this contract after the Source Adapter has created the Evidence Item. The source adapter's normalization policy is part of source/provider identity.

#### Scalar

A scalar carries:

- `type`: `string | boolean | integer | decimal | timestamp`;
- canonical lexical `value`;
- optional `unit` string/ID when the source contract defines one.

`decimal` MUST use a canonical base-10 lexical representation declared by the profile/source contract. A host MUST NOT silently convert units or numeric semantics while projecting evidence.

#### JSON

A profile supporting `json` MUST declare its canonical JSON encoding. The reference rc4 profile SHOULD use RFC 8785/JCS canonical JSON or a stricter documented subset. Arbitrary host JSON serialization is not a stable digest input.

### 9.4 Content digest

When `content_sha256` is present it is SHA-256 over the profile/source-declared **canonical content bytes**, not over an arbitrary pretty-printed object.

A content digest MAY be omitted from every embedded item when an immutable source snapshot manifest already digest-binds the exact item bytes and the audit record preserves that binding. It SHOULD be present in benchmark/audit material when practical.

The model does not need to see content digests.

### 9.5 Validity

Optional fields:

- `observed_at` — when the source observed the value;
- `valid_from` — inclusive validity start;
- `valid_until` — exclusive validity end.

Time intervals use `[valid_from, valid_until)` semantics.

If target freshness depends on these fields, `QueryEnvelope.as_of` MUST be explicit/effective and the profile MUST define behavior for missing validity metadata.

## 10. Evidence Policy and deterministic aggregation

The policy consumes the Routing Plan and Provider Outcomes and produces one independent result per `target_key`.

The profile MUST freeze:

- candidate validation;
- source priority;
- evidence equivalence/dedup rule;
- cross-provider combination rule;
- conflict detection;
- ambiguity detection;
- freshness selection;
- required-coverage/sufficiency rule;
- deterministic candidate ordering;
- deterministic tie-breakers;
- top-k selection;
- whole-item byte/token truncation;
- state precedence.

### 10.1 Required state semantics

Each target group state is exactly one of:

- `grounded` — one or more policy-approved items support the target;
- `none` — the authoritative/supplemental search completed under its declared coverage rule and returned no usable evidence;
- `ambiguous` — plausible evidence exists but target/entity/value selection cannot be resolved safely;
- `conflict` — mutually incompatible policy-relevant evidence remains unresolved;
- `unavailable` — required coverage could not be completed or provider/source access failed.

`items` MUST be nonempty iff state is `grounded` in the model-facing frame. Audit sidecars MAY retain rejected/ambiguous/conflicting candidates separately.

### 10.2 State precedence for authoritative targets

For an authoritative target:

1. unresolved authoritative contradiction => `conflict`;
2. unresolved entity/value ambiguity => `ambiguous`;
3. missing required coverage, timeout, denied source or provider error => `unavailable`, unless a named frozen sufficiency rule proves the completed subset sufficient;
4. completed required coverage + zero usable evidence => `none`;
5. completed/sufficient coverage + valid supporting evidence => `grounded`.

A supplemental provider cannot fill or override an unresolved authoritative target unless the profile explicitly defines that source as authoritative for the same target. In practice, mixed authority SHOULD be represented as separate target groups or bindings with explicit precedence.

### 10.3 Claim coverage

A `grounded` target group supports only the factual target identified by its `target_key`/`target_label` and the contents of its items.

A grounded frame MUST NOT be interpreted as evidence for every claim in a compound user question.

If a compound question has multiple protected authoritative facts, the router SHOULD emit separate target groups. An unresolved authoritative group blocks guessing only for that target; it does not force unrelated supplemental targets to abstain.

### 10.4 Budget behavior

- Model-visible truncation MUST occur at whole-item boundaries unless a profile defines a safe deterministic content summarization mechanism and freezes its identity.
- Truncating candidates because of a model-context budget MUST NOT convert an existing hit into `none`.
- If the evidence required to satisfy a target cannot fit and no frozen safe truncation/sufficiency rule applies, the group becomes `unavailable` or a typed budget failure according to the profile.
- Provider candidate budget exhaustion is `budget_exceeded`, not `none`.

## 11. `GroundingFrame`

The logical frame contains independent target groups so authoritative and supplemental evidence can coexist safely.

Conceptual host-side frame:

```json
{
  "v":1,
  "qid":"q-000042",
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

Required logical fields:

- `v`;
- `qid`;
- `profile_sha256`;
- `groups[]`.

Each group preserves:

- `target_key`;
- compact `target_label`;
- `authority`;
- `state`;
- policy-approved `items` only when grounded.

Host/audit sidecars SHOULD additionally preserve:

- Routing Plan digest/record;
- Provider Outcomes;
- coverage/sufficiency details;
- typed state reason;
- source snapshot references;
- rejected/deduplicated candidate audit information;
- final pre-projection frame digest.

`security_scope_id`, provider raw scores, provider secrets and access-control metadata MUST NOT be copied into the model-visible projection.

## 12. Model Projection

The Grounding Frame is a logical host result. The **Model Projection** is a deterministic compact serialization designed for the target model.

The profile freezes:

- renderer/template ID and digest;
- escaping/delimiting rules;
- field ordering;
- item ordering;
- labels shown to the model;
- byte/item limits;
- handling of authoritative unresolved states;
- handling of supplemental no-hit/unavailable states.

The projection MUST preserve enough information for the model to distinguish, per target:

- what factual target is being discussed;
- whether it is authoritative or supplemental;
- whether the target is grounded, none, ambiguous, conflict or unavailable;
- the relevant evidence when grounded.

### 12.1 Data-versus-instruction boundary

Retrieved evidence and provider metadata are untrusted **data**.

The host MUST:

- place Grounding Policy instructions at a higher-priority model instruction level than evidence;
- use a fixed deterministic representation for evidence content;
- escape/delimit evidence according to the renderer contract;
- never derive tool permissions, network permissions, security scope or source authority from evidence text;
- never execute instructions found inside evidence;
- never treat provider similarity score as truth authority.

This contract does **not** claim that delimiters make LLM prompt injection impossible. Prompt-injection resistance is an end-to-end model/host property and MUST be tested with adversarial evidence cases.

### 12.2 Required model semantics

For an authoritative target:

- `grounded`: the answer MUST NOT contradict the supplied authoritative evidence for that target;
- `none`: the model MUST NOT invent that target from pretrained memory;
- `ambiguous`: the model MUST NOT silently select one candidate;
- `conflict`: the model MUST surface/handle the conflict according to host policy, not pick a hidden winner;
- `unavailable`: the model MUST distinguish source unavailability from a true no-hit and MUST NOT claim an authoritative value as retrieved.

For a supplemental target:

- `grounded`: evidence may improve the answer;
- `none`/`unavailable`: normal model knowledge MAY be used under the host's ordinary policy;
- supplemental absence MUST NOT be interpreted as proof that the fact is false or unknowable.

The exact wording shown to the model is renderer/profile data and part of candidate identity.

## 13. Security scope and privacy

The host MUST establish security scope before routing/retrieval.

Rules:

- requests, provider calls, source reads, caches and frames MUST remain bound to the effective security scope;
- a cache hit from a different security scope MUST be rejected unless the host has an explicit equivalence/share policy outside this contract;
- providers MUST NOT broaden source/user/tenant scope;
- no implicit cross-user/tenant merge is allowed;
- private queries/evidence MUST NOT be sent to a network provider unless the profile/host explicitly authorizes that provider and data class;
- security-scope IDs and access metadata MUST stay host-side;
- model-generated text MUST NOT become provenance or authority metadata;
- benchmark/public evidence SHOULD use synthetic/sanitized private-style data unless disclosure is explicitly authorized.

## 14. Provider identity and reproducibility

Every provider used in qualification MUST expose sufficient immutable identity to explain/replay retrieval behavior.

Minimum provider identity:

- provider type/name;
- implementation revision/digest;
- query preprocessing identity;
- source/index snapshot identity;
- ranking/configuration identity;
- applicable profile binding.

Semantic/vector providers additionally bind:

- embedding model repository/revision/file digest;
- tokenizer/preprocessing digest;
- vector dimension/precision;
- distance metric;
- index build digest;
- top-k/reranking configuration.

Remote providers additionally require, for reproducible evidence:

- provider/endpoint identity where disclosure is allowed;
- request options that affect results;
- exact captured response/evidence snapshot or a cryptographically bound replay fixture;
- timeout/outcome decision records.

A live remote query by itself is not reproducible benchmark evidence.

## 15. Validation and fail-closed rules

Before model invocation, the implementation MUST reject or type-fail:

- unsupported contract major version;
- profile digest mismatch;
- missing/duplicate `qid` where uniqueness is required;
- invalid target key/namespace binding;
- authority mismatch;
- source/provider not allowed by profile;
- security-scope mismatch;
- malformed Evidence Item;
- unsupported content kind/type/unit contract;
- invalid UTF-8 where text is required;
- invalid canonical scalar lexical form;
- invalid validity interval;
- invalid state/items combination;
- item count/byte/depth overflow;
- frame/projection budget violation that cannot be handled by the frozen policy.

Adapters MAY normalize transport syntax only when the logical value is unchanged. They MUST NOT repair authority, claim target, source identity, evidence value, freshness, conflict or ambiguity semantics.

## 16. Query path profiles

### 16.1 Prefetch — flagship default

```text
original question -> Routing Plan -> Providers -> Policy -> Frame -> Projection -> one model answer call
```

Properties:

- no model-generated retrieval query;
- no native tool dependency;
- exactly one answer-generation model call in the flagship benchmark arm;
- preferred consumer/embedded profile.

### 16.2 Rewrite — optional separate profile/arm

```text
original question -> one bounded rewrite call -> Providers -> Policy -> Frame -> one answer call
```

The rewrite call and answer call are counted separately. Rewrite evidence MUST never be merged into the flagship one-call arm.

### 16.3 Native retrieval tool — optional compatibility profile

A model-visible retrieval tool MAY exist for products that genuinely need it and whose runtime supports the protocol, but it is not the universal baseline and is not the flagship benchmark arm.

## 17. Resource budget contract

Every concrete profile freezes hard upper bounds for relevant resources, including:

- query bytes;
- target-group count;
- provider count per target;
- source bindings per provider;
- provider attempts;
- candidate count;
- Evidence Item count;
- Evidence Item content bytes/depth;
- host-side frame bytes;
- model-visible item count;
- model-visible evidence bytes;
- optional tokenizer-specific evidence-token ceiling;
- answer-generation calls;
- rewrite calls;
- retrieval phase deadline;
- provider memory/index/storage targets where claimed.

There are no universal numeric values in this logical specification. Concrete embedded/desktop profiles set them.

## 18. Benchmark isolation and anti-leak invariants

For any frozen flagship run:

- the corpus/query set is frozen before inference;
- source/index snapshots are frozen before inference;
- router/provider/profile/policy/projection identities are frozen before inference;
- model/runtime/generation/scorer identities are frozen before inference;
- the retrieval serving path receives only production-available inputs (`q`, effective security/application context, frozen profile, allowed source snapshots);
- benchmark expected answers, expected source IDs, expected evidence IDs and expected target keys MUST remain scorer-side and MUST NOT be readable by Router/Providers/Policy;
- an oracle target/source mapping MAY be used only in a separately labeled diagnostic arm, never flagship G;
- no alias/index/reranker/source/freshness/authority tuning after seeing model responses may remain under the same run identity;
- no hidden provider retry or answer-aware rewrite is allowed;
- raw records preserve Routing Plan, Provider Outcomes, Grounding Frame, Model Projection and final model answer, subject to privacy-safe evidence handling;
- A and flagship G MUST use the same answer-generation call count and output-token/sampling policy;
- remote provider results used as evidence MUST be captured/replayable for the frozen run;
- costs and failure rates MUST be reported with explicit raw denominators.

## 19. Failure taxonomy

Qualification MUST distinguish at least:

1. routing miss/wrong target;
2. unauthorized/wrong scope;
3. provider query failure;
4. retrieval miss despite installed relevant evidence;
5. false retrieval / false grounding;
6. stale/revision selection failure;
7. partial-provider coverage failure;
8. ambiguity handling failure;
9. conflict handling failure;
10. provider timeout/error/denied/unavailable;
11. evidence budget/truncation failure;
12. Model Projection/serialization failure;
13. grounding adherence failure;
14. authoritative unsupported assertion;
15. over-abstention;
16. prompt-injection/adversarial-evidence policy failure;
17. model output/token/timeout failure.

These MUST NOT be collapsed into one development accuracy score.

## 20. Transport compatibility

The logical contract MAY be represented through:

- Rust structs;
- C ABI structs/buffers;
- Tiny JSON;
- canonical JSON for build/audit artifacts;
- CBOR/TinyWire;
- Wasm memory regions;
- local IPC;
- host-language objects.

Transport adapters MAY change representation but MUST preserve:

- query/profile identity;
- target identity;
- authority;
- state;
- source/item/revision identity;
- evidence content/value;
- validity semantics;
- group ordering required by the profile;
- fail-closed outcomes.

The minimum embedded core is not required to parse JSON, run a tokenizer, access a clock or open a network connection.

## 21. Implementation-freeze rule

This logical v0.1 contract is frozen for rc4 implementation review once all active product/design documents agree with it and a read-only architecture review reports no P0 contradiction.

Freezing the logical contract does **not** mean:

- a provider algorithm is production-supported;
- a concrete binary ABI is stable;
- a grounding release artifact exists;
- model accuracy/hallucination reduction has been measured;
- physical-device resource/energy claims are established.

After freeze, implementation MAY choose concrete profile serialization, provider interfaces and packaging. Any semantic change to authority, coverage, state precedence, security scope, evidence identity, merge behavior or model projection requires a new contract/profile revision and new benchmark candidate identity.
