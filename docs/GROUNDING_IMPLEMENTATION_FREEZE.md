# Grounding implementation freeze — rc4

Date: 2026-09-06
Status: **FROZEN_FOR_IMPLEMENTATION**

## Frozen authority

Implementation must follow, in order:

1. `../spec/GROUNDING_CONTRACT_V0_1.md`
2. `GROUNDING_ARCHITECTURE.md`
3. `PRODUCT_DIRECTION.md`
4. `BENCHMARK.md`
5. `AI_INTEGRATION.md`
6. `SECURITY.md`
7. `DECISIONS.md`

The final read-only Codex protocol/security review reported:

```text
No P0 semantic blockers found across the requested protocol, security,
reproducibility, isolation, call-count, and metric-denominator checks.
Behavior delegated to concrete profiles is explicitly required to be frozen
and identity-bound.

NO_P0_BLOCKERS
```

Review target: `spec/GROUNDING_CONTRACT_V0_1.md` + `docs/GROUNDING_CONTRACT_REVIEW_CARD.md`.

## Frozen logical invariants

- Original-question prefetch is the default grounding path.
- Flagship G and baseline A each use one answer-generation model call.
- Host security/application scope is established before routing/retrieval.
- Router emits bounded production-realistic TargetPlans; benchmark gold is scorer-only.
- Authority is per target/source binding and host/profile controlled.
- GroundingFrame state is per target group.
- Authoritative `none` requires completed or profile-defined sufficient required coverage.
- Timeout/error/denied/budget/incomplete coverage remains `unavailable`.
- Provider outcomes are typed; merge/order/tie-break behavior is deterministic and profile-bound.
- Evidence preserves stable source/item/revision/content identity.
- Evidence is untrusted data; it cannot grant permissions, broaden scope, or redefine authority.
- Model Projection is deterministic, digest-bound, and hides security/provider internals.
- Semantic/vector and remote provider behavior is identity/replay bound for evidence.
- False grounding, grounding penalty, authoritative unsupported assertions, useful-answer/abstention and exact cost are required benchmark outputs.
- Prototype `xs_recall`, fact-pack, lexical matcher, and old recall benchmark code are non-normative.
- Quantitative `xs_calc`/`xs_eval` remains a retained secondary subsystem.

## What is not frozen yet

The following are implementation/profile choices to be created next and then frozen before benchmark inference:

- concrete machine-readable GroundingProfile schema and canonical encoding;
- QueryEnvelope / RoutingPlan / ProviderOutcome / EvidenceItem / GroundingFrame schemas;
- source snapshot and provider identity manifests;
- the first concrete reference profile and provider implementation;
- exact Model Projection template bytes;
- benchmark serving/gold corpus bytes;
- preregistration schema and runner;
- release/package identity.

Those choices may not alter the frozen logical invariants above. If implementation reveals a genuine semantic defect in the logical contract, implementation stops, the contract revision changes explicitly, and future benchmark candidate identity changes with it.

## Current execution goal

Proceed through implementation, no-inference conformance/security tests, package construction, clean-room verification, model inventory preparation, and zero-inference preregistration. Stop at:

```text
READY_FOR_GROUNDING_BENCHMARK
```

Do not launch any new rc4 grounding model inference in this implementation phase.
