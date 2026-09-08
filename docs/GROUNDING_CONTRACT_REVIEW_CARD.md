# Grounding contract review card

Purpose: concise checklist for final read-only architecture review before `FROZEN_FOR_IMPLEMENTATION`. The normative authority remains `../spec/GROUNDING_CONTRACT_V0_1.md`.

## Required invariants

1. Default serving path is original-question prefetch; flagship G uses exactly one answer-generation model call, equal to A.
2. The host establishes effective security/application scope before routing/retrieval.
3. Router emits production-realistic bounded TargetPlans; it never consumes benchmark expected answer/target/source/evidence/provider labels.
4. Authority is host/profile policy per target/source binding, never provider/evidence self-assertion.
5. GroundingFrame state is per target group, not one global frame truth bit.
6. Authoritative `none` is legal only after all required or profile-defined sufficient authoritative coverage completes successfully with no usable evidence.
7. Timeout, error, denied, budget exhaustion, incomplete required coverage, or provider unavailability never silently become authoritative `none`.
8. Supplemental evidence cannot fill or override an unresolved authoritative target unless the same source is explicitly configured authoritative for that target.
9. ProviderOutcome is typed and bound to qid/target/provider/source snapshot; provider completion order cannot affect final merge.
10. Raw provider relevance scores are not compared across providers unless a frozen calibrated transform is part of profile identity.
11. Profile freezes candidate validation, source priority, dedup, merge, freshness, ambiguity, conflict, required coverage/sufficiency, deterministic ordering/tie-break, top-k, whole-item truncation, timeout/retry, and Model Projection behavior.
12. EvidenceItem identity is source-local `(source_id,item_id,source_revision)` plus typed content and optional canonical content digest/validity metadata; revision is opaque unless source contract defines chronology.
13. Evidence is untrusted data. Grounding Policy is higher priority; evidence cannot grant permissions, broaden scope, or redefine authority. Delimiting does not claim perfect prompt-injection resistance.
14. Security scope binds requests, provider calls, source reads, caches and frames; cross-scope reuse is rejected absent explicit host sharing policy; private data is not sent to network providers without explicit authorization.
15. Model Projection is deterministic/versioned/digest-bound and preserves target meaning, authority, state and useful evidence while hiding security scope, provider scores, vectors, access metadata and verbose audit internals.
16. Semantic/vector provider identity binds embedding model/tokenizer/vector/index/ranking configuration. Remote benchmark evidence is captured/replayable; live search alone is not frozen evidence.
17. Serving benchmark files are physically/logically separate from scorer gold. Oracle routing is diagnostic only and never flagship G.
18. Metrics publish raw numerators/denominators and explicitly measure factual accuracy, wrong-confident answers, authoritative unsupported assertions, useful/correct abstention/over-abstention, grounding recovery/penalty, retrieval precision/hit, false grounding, adherence, revision override, provider-unavailable handling and exact costs.
19. Prototype `xs_recall`, one fact-pack schema, one lexical provider, and old recall benchmark runner are non-normative and may be reused only behind the frozen provider-neutral contract.
20. Quantitative `xs_calc`/`xs_eval` remains a retained secondary subsystem; native/constrained model envelopes apply there, not as a requirement for everyday grounding.

## Freeze condition

No implementation freeze is allowed until a read-only review of this card plus the normative contract reports no P0 semantic contradiction. P1 implementation-detail suggestions may remain, but they must not contradict or leave ambiguous authority, coverage, failure, identity, privacy, determinism, projection, or benchmark-isolation semantics.
