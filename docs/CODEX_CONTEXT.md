# Codex / agent context — ExactScope rc4 grounding implementation

Date: 2026-09-06
Current branch intent: **post-freeze readiness record for candidate source `125ad9403f22eece7f552701d4c7376bba3b697f`; implementation is stopped at READY_FOR_GROUNDING_BENCHMARK with zero rc4 model inference**

Read this before modifying ExactScope. The current authority order is:

1. `docs/PRODUCT_DIRECTION.md`
2. `docs/GROUNDING_ARCHITECTURE.md`
3. `spec/GROUNDING_CONTRACT_V0_1.md`
4. `docs/BENCHMARK.md`
5. `docs/AI_INTEGRATION.md`
6. `ROADMAP.md`
7. `docs/ARCHITECTURE.md`
8. `docs/DECISIONS.md`
9. `SECURITY.md`
10. `docs/RC3_QUALIFICATION_CLOSEOUT.md` for historical rc3 findings

`docs/MODEL_INTERFACE_RC4.md`, `docs/CAPABILITY_PRODUCT_ARCHITECTURE.md`, `docs/DOMAIN_EXPANSION.md`, and the capability compiler documents remain valid **quantitative-subsystem** references. They no longer define the flagship rc4 product path.

`docs/QUALIFICATION_HANDOFF.md` and the older model-matrix/procedure records are historical rc3 material. Do not resume rc3 inference from them. The active future validation instructions are `docs/GROUNDING_BENCHMARK_HANDOFF.md` and `docs/NEXT_SESSION_PROMPT.md`.

## Current instruction: candidate is frozen; do not keep implementing under this identity

The logical Grounding Contract v0.1 is **FROZEN_FOR_IMPLEMENTATION** after a final read-only Codex review reported `NO_P0_BLOCKERS`. The freeze record is `docs/GROUNDING_IMPLEMENTATION_FREEZE.md`.

P1-P5 are complete for the frozen candidate source `125ad9403f22eece7f552701d4c7376bba3b697f`:

- machine-readable profile/schemas/canonical encodings are frozen for the reference candidate;
- provider-neutral host/provider/policy/frame/projection behavior is implemented;
- the exact/lexical implementation is isolated as a **reference provider**, not the universal product contract;
- serving/gold benchmark inputs, scorer, zero-inference dry-run, package tooling, five-model identity inventory, runtime identity, preregistration and benchmark runner exist;
- Linux and Windows clean-room package/dry-run/post-use re-verification pass;
- five actual model preregistrations pass runner `--verify-only` as `ready-to-run`;
- retained quantitative Rust/C/Wasm regressions remain green;
- no rc4 grounding model inference has run.

The exact hashes and gate results are in `docs/GROUNDING_BENCHMARK_READY.md`.

Do **not** continue product implementation, rewrite the corpus/provider/profile/projection/scorer, or run model inference from this implementation session. The next active phase is a separate validation session using `docs/GROUNDING_BENCHMARK_HANDOFF.md` and `docs/NEXT_SESSION_PROMPT.md`. Any behavior change creates a new candidate identity.

Do not expand Finance/Physics/other academic domains. Do not change frozen authority, coverage, state precedence, security-scope, evidence-identity, deterministic merge, Model Projection, or benchmark-isolation semantics merely to make implementation easier. If implementation discovers a genuine semantic defect, explicitly revise the contract/candidate identity rather than silently repairing it.

The earlier `RecallIndex`, `xs_recall`, and fact-pack experiments are non-normative reference/prototype material. The provider-neutral host contract, not those prototype APIs, defines the flagship product.

## Flagship product thesis

ExactScope is becoming a **tiny provider-neutral grounding layer plus a retained deterministic quantitative subsystem** for constrained/on-device AI.

The flagship question is:

> Can a small local evidence layer make an existing small model more correct and less confidently wrong on ordinary factual questions at low enough storage, context, token, latency, energy and integration cost to be preferable to a larger model, much larger context, heavyweight RAG stack or hardware upgrade?

The normal user should not need to know or invoke an ExactScope tool.

## Default serving path

The default consumer/embedded path is **original-question prefetch**, not model-generated retrieval/tool calling:

```text
user question
    |
    v
Grounding Router
    |
    v
configured Retrieval Providers
    |
    v
Evidence Policy
    |
    v
compact Grounding Frame
    |
    v
small/local model -- one answer-generation call
    |
    v
final answer
```

A model-generated retrieval rewrite is optional and belongs to a separate profile/benchmark arm because it adds inference, tokens and failure modes.

Native tool calls are never a universal grounding requirement.

## Provider-neutral architecture

The product contract is:

```text
Source -> Retrieval Provider -> ProviderOutcome
       -> Evidence Policy -> grouped GroundingFrame
       -> deterministic Model Projection -> Model
```

Retrieval Provider may be:

- exact key / alias;
- compact lexical/inverted index;
- deterministic ranked lexical search;
- n-gram/prefix search;
- frozen embedding/vector retrieval;
- application-native memory/search;
- captured host/network/search evidence.

The provider is replaceable. The model receives a deterministic evidence projection, not retrieval internals.

Every provider used for qualification must expose enough immutable identity to explain/reproduce behavior. Semantic/vector providers additionally bind embedding model/tokenizer/index/configuration identity. Live network evidence must be captured/replayable for reproducible benchmark evidence.

## Target-scoped authority and coverage

Authority is assigned by the host/profile per **TargetPlan source binding**, not globally per frame and never by provider/evidence text.

### `authoritative`

Examples: private saved memory, device/application state, installed manual revision, organization record for a specific factual target.

- `grounded` -> use current evidence for that target;
- `none` -> legal only after required/sufficient authoritative coverage completed with no usable evidence;
- `ambiguous` -> do not silently select a sibling entity/value;
- `conflict` -> do not hide incompatible current records;
- `unavailable` -> required coverage/provider/source failure is distinct from a true no-hit.

A supplemental source cannot silently fill an unresolved authoritative target.

### `supplemental`

Examples: partial local reference cache, optional FAQ subset, search snippets.

- useful evidence may improve the target answer;
- no hit does **not** mean the model must refuse or that the fact is false;
- normal model knowledge may remain available under host policy.

This distinction prevents a tiny partial knowledge source from causing blanket refusal.

## GroundingFrame and Model Projection

The host-side logical frame is provider-independent and grouped by factual target.

Top-level fields include:

- contract version;
- `qid`;
- exact `profile_sha256`;
- `groups[]`.

Each group preserves:

- stable `target_key` and compact non-answer-bearing `target_label`;
- target authority;
- state: `grounded | none | ambiguous | conflict | unavailable`;
- policy-approved Evidence Items only when grounded.

Evidence Items use source-local identity such as `source_id`, `item_id`, opaque `source_revision`, typed content, optional canonical `content_sha256`, and optional validity metadata.

The model receives a deterministic **Model Projection** of those groups. Provider scores, vectors, internal indexes, security/tenant/access metadata, rejected candidates and verbose audit provenance remain host-side. Renderer/template bytes are part of candidate identity.

## Privacy and trust boundary

Grounding data may be more sensitive than model weights.

Hard rules:

- host scopes user/tenant/application sources before retrieval;
- no implicit cross-user/tenant evidence merge;
- private query/evidence is not sent to a network provider unless explicitly authorized;
- evidence is data, not higher-priority model instruction;
- provider similarity score is not truth authority;
- `unavailable` must not collapse into `none`;
- false grounding is a first-class correctness/security failure.

See `SECURITY.md` for the expanded grounding trust boundary.

## Benchmark contract

The flagship comparison is:

- **A** — model only, one answer-generation call;
- **G** — original-question prefetch -> Grounding Frame -> same model, one answer-generation call;
- **Q** — optional bounded query rewrite, separate diagnostic arm with extra model call/cost;
- **L** — optional justified larger-model reference.

A and G should use the same model revision/runtime/sampling/output budget and the same answer-generation call count. G is allowed its preregistered evidence context because that is the product intervention; added bytes/tokens/latency are measured explicitly.

Primary workload strata:

1. stable public everyday facts;
2. synthetic/private/device memory;
3. product/manual support facts;
4. stale/revision override;
5. distractor/entity confusion;
6. authoritative no-answer after complete coverage;
7. provider unavailable / partial required coverage;
8. ambiguity and conflict;
9. multilingual/paraphrase;
10. adversarial evidence / prompt injection;
11. supplemental no-hit / over-abstention;
12. quantitative corpora only as a secondary subsystem benchmark.

Primary metrics:

- end-to-end factual accuracy;
- wrong-confident-answer rate;
- authoritative unsupported-assertion rate;
- useful-answer rate;
- correct abstention / over-abstention;
- grounding recovery and grounding penalty;
- hit@1/hit@k and precision@k;
- false-grounding rate;
- stale/revision and distractor accuracy;
- grounding adherence;
- evidence/index bytes, RAM, retrieval latency and token/context overhead.

Do not tune aliases/index/reranking/freshness/authority after seeing model results and keep the same run identity.

## Accepted rc3 findings

rc3 evidence remains immutable historical input.

The five-model A/C/D matrix showed:

- Gemma 3 270M and Phi-4-mini 3.8B almost never produced usable native tool calls under the frozen llama.cpp templates;
- LFM2.5 350M saw tool information but lacked a complete assistant tool-call path;
- Qwen3.5 0.8B and 2B recognized tools frequently but still had substantial selection/schema failures;
- the largest tested model was not the strongest tool caller;
- valid requests reaching ExactScope were much stronger than end-to-end model selection.

Representative Qwen3.5 prompt-token observations were roughly A ~86, semantic native-tool C ~613, combined D ~1047 input tokens.

Therefore native OpenAI-style tool serialization is not the universal product baseline. This finding motivates one-call grounding prefetch even more strongly.

## Retained quantitative subsystem

The following remain valuable and should not be casually broken:

- deterministic `no_std` decimal/rational kernel and bounded VM;
- `xs_calc` bounded arithmetic plan;
- selected reviewed `xs_eval` operations;
- optional quantitative `xs_find` discovery;
- strict Tiny JSON/TinyWire boundaries;
- native C ABI and no-import Wasm;
- operation/ABI revision stability;
- capability/profile compiler and specialization machinery;
- constrained JSON/GBNF compatibility for model-generated quantitative calls;
- native tools only when runtime support is proven before inference;
- packaging, conformance, security/export and qualification infrastructure.

The quantitative subsystem is secondary to the current grounding product proof, not discarded.

## Current code/prototype boundary

Mature quantitative crates/tooling include:

- `exactscope-kernel`;
- `exactscope-pack`;
- `exactscope-tinyjson`;
- `exactscope-wasm`;
- `exactscope-cabi`;
- `exactscope-packc`;
- `exactscope-conformance`;
- capability compiler/evaluation packaging and rc3 qualification tooling.

Earlier rc4 experimentation also introduced recall/fact-pack/provider-adjacent code and benchmark scripts. Treat these as prototypes until the logical Grounding Contract/profile serialization is frozen. Do not cite prototype self-tests as evidence that everyday model accuracy improved.

## Current next work

**Implementation is now authorized under the frozen logical contract. Do not launch model inference.**

1. define/freeze concrete machine-readable GroundingProfile, QueryEnvelope, RoutingPlan, ProviderOutcome, EvidenceItem, GroundingFrame, source/provider identity and preregistration schemas;
2. define the first reference profile and deterministic Model Projection bytes;
3. implement provider-neutral host types, one minimum local provider, Evidence Policy, grouped frame builder and audit records;
4. build physically separated serving/gold benchmark fixtures plus scorer and zero-inference preregistration/dry-run tooling;
5. run deterministic/security/regression tests and clean package/clean-room checks;
6. prepare/freeze model inventory inputs without starting model requests;
7. stop at `READY_FOR_GROUNDING_BENCHMARK` and write the next-session validation handoff.

## Evidence/claim boundary

Still unmeasured/unsupported as broad claims:

- rc4 everyday factual-accuracy uplift;
- rc4 hallucination/wrong-confident-answer reduction;
- rc4 false-grounding rate on a frozen candidate;
- universal small-model uplift;
- physical ARM64 process RAM/latency/energy/thermal behavior;
- battery/hardware-life savings;
- production readiness / stable Tier support.

Package/doctor checks for Android/Linux ARM64 passed in rc3, but no physical target was available. Preserve those physical-target metrics as **NOT MEASURED**.

## Modification rules

- Preserve unrelated developer work; never reset/clean/stash/discard it without explicit user intent.
- Do not overwrite frozen rc3 evidence or capability identities.
- Do not change ABI/kernel IDs casually.
- Do not promote prototype retrieval choices into normative contracts without design review.
- Do not add model-name-specific routing hacks.
- Do not expose private evidence to a wider provider scope silently.
- Keep historical rc3 quantitative records historical rather than rewriting them as grounding evidence.
- When implementation resumes, any provider/policy/prompt/index change creates a new candidate identity for model evidence.
