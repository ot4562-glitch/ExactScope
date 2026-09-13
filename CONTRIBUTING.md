# Contributing to ExactScope

ExactScope v1.1.0 is a bounded software/architecture release. The **stable support surface remains the Linux x86-64 native grounding C ABI/XSGI path**; new qualification/control-plane, enterprise DocQA, host-integration, Bridge and demo surfaces are experimental/reference. The release deliberately preserves mixed evidence, including a negative Kubernetes long-document proxy, rather than treating research success as part of the support contract. Quantitative `xs_calc`/`xs_eval` remains a secondary deterministic subsystem. Contributions are evaluated by **product leverage, qualification integrity, grounding precision, deterministic correctness, integration simplicity, total cost, portability, privacy and evidence**—not by raw feature count.

## Current project phase

`v1.1.0` retains the Linux x86-64 native grounding package/C ABI as the stable scope and adds experimental/reference source surfaces for qualification/control-plane workflows and host integration. FEVER Stage 1 stopped at `ReferenceOnly`; the frozen NQ/Hotpot public panel is complete; the later Kubernetes Operations proxy failed its ordinary-RAG quality margin and selected no candidate. Public tuning is closed. Post-release research must be justified by a real owner-bound workload or another explicitly scoped evidence question; release mechanics and stable-native regression work take priority over new policy exploration.

Read this order first for current v1.1 work:

1. `docs/V1_1_RESEARCH_STATUS.md`
2. `docs/V1_1_PRODUCT_DIFFERENTIATION.md`
3. `docs/V1_1_ASTRA_HIGH_REVIEW.md`
4. `docs/V1_1_EXPERIMENT_PROGRAM.md`
5. `docs/DECISIONS.md`
6. `ROADMAP.md`
7. `docs/PRODUCT_DIRECTION.md`
8. `docs/V1_1_PARASITE_ATTACH_PROFILE.md`
9. `docs/GROUNDING_ARCHITECTURE.md` and `spec/GROUNDING_CONTRACT_V0_1.md` for stable-v1 semantics
10. `docs/AI_INTEGRATION.md`, `docs/BENCHMARK.md`, and `docs/COMPATIBILITY.md`
11. `SECURITY.md`
12. `docs/IMPLEMENTATION_PLAN.md` for the quantitative subsystem/history

`docs/FIRST_IMPLEMENTATION_SLICE.md` is historical implementation context, not the current priority plan.

## Product-priority rule

Before proposing a large v1.1 feature, ask whether it improves one of these **without weakening qualification integrity or expanding ownership into host-runtime machinery**:

- competence and customer value on a bounded document-QA workload using real host retrieval;
- trustworthy comparison of a fixed semantic configuration against a competent Base/reference;
- total customer economics, including serving, escalation/review, integration, qualification and refresh cost;
- fresh calibration/held-out integrity, scorer validity, qualification identities, or reproducibility;
- retrieval precision / false-grounding avoidance and authoritative/supplemental/freshness/conflict correctness;
- a smaller host-attached semantic boundary with less duplicated runtime ownership;
- private-source scope and isolation;
- correctness/security of the deterministic quantitative core and public boundaries;
- five-minute integration and reproducible customer/model/runtime qualification evidence;
- honest distribution/dependency/runtime-payload/resource accounting.

Broad platform support, academic catalog expansion, adaptive per-query selection, per-domain feature work, new native machinery, cross-host transfer, and retrieval-algorithm novelty remain secondary until a **competent customer-like source policy** demonstrates useful value and economics. The preregistered 120/600 FEVER study stopped at `ReferenceOnly`; do not broaden the policy matrix or reuse its sealed held-out merely to escape that negative result.

## Core invariants

Do not casually weaken:

- AI-consumed headless core;
- offline-capable/library-first operation;
- no mandatory daemon/account/network;
- stable-v1 `no_std` allocator-free native-kernel guarantees and stable-v1 C ABI compatibility;
- **do not generalize those stable-v1 native guarantees into a requirement that v1.1 must own or ship a native kernel**;
- deterministic checked numeric semantics;
- data-only scope packs;
- bounded execution/memory;
- semantic fail-closed behavior, including explicit stale/unsupported/admission-failure outcomes;
- one shared calculation semantics across profiles;
- evidence-backed compatibility/marketing claims;
- held-out qualification that can only pass or reject the frozen candidate, never reselect it.

## AI integration changes

The normal v1 hot path is **grounding prefetch, deterministic host completion when the frame is sufficient, and an answer-model call only when interpretation is still required**. Quantitative `xs_calc`/`xs_eval` remains available when the task actually needs deterministic calculation; `xs_find` is quantitative cold-path discovery.

Grounding contributions should prefer:

- provider-neutral interfaces rather than coupling the product to one lexical/vector/search implementation;
- original-question prefetch before adding a model-generated query turn;
- explicit authoritative/supplemental source policy;
- precision and false-grounding prevention over aggressive recall for authoritative sources;
- compact Grounding Frames with minimal model-visible metadata;
- frozen source/provider/index/freshness/policy identity;
- measured evidence bytes/tokens, retrieval latency, index/RAM footprint, grounding adherence and wrong-confident-answer reduction;
- privacy/scope enforcement before retrieval.

Quantitative adapter contributions should still prefer one compact bounded `xs_calc` surface, the smallest selected `xs_eval` slice, constrained JSON/GBNF compatibility, and native tools only where proven useful.

Adapters may normalize syntax/transport but not semantics or source authority.

Allowed examples:

- envelope translation;
- whitespace normalization;
- deterministic field mapping;
- lossless decimal lexical normalization.

Forbidden examples:

- guessing values;
- percent/unit/currency conversion without explicit operation semantics;
- choosing ambiguous methods;
- calculating/rounding/classifying outside the core;
- turning an error into a plausible number.

## Benchmark changes

Benchmark contributions should follow `docs/BENCHMARK.md`. The flagship v1 comparison is **A model-only vs G original-question-prefetch grounding**; A always makes one answer-generation call, while G may use zero only under the frozen deterministic host-completion rules and otherwise makes one. Optional query rewrite/tool profiles are separate ablations because they spend extra inference/tokens. Historical quantitative A/B/C/D arms remain valid only for the quantitative subsystem.

Do not publish one blended score without retrieval/policy/model failure stages and cost metrics. Report false grounding, wrong-confident answers, correct abstention, grounding penalties and useful-answer rate together.

Any comparative claim must identify exact release/source/provider/index/policy/model/runtime/hardware/corpus/scorer identities and digests. Do not tune aliases, indexes, reranking, authority or freshness rules after seeing model results and keep the same run identity.

## Runtime changes

A runtime PR should include, as applicable:

- success/invalid/boundary/overflow/resource tests;
- no-default-features/`no_std` verification;
- allocation behavior;
- size impact;
- ABI/Wasm compatibility impact;
- malformed-input safety;
- proof no adapter/platform calculation fork is introduced.

New runtime dependencies require explicit review.

## Operation/pack changes

An official operation requires:

- canonical key and pack-local ID;
- stable revision/method identity;
- immutable argument order and semantic names;
- units/constraints/cross-input relations;
- exact formula or approved shared kernel ID;
- output/rounding/classification policy;
- provenance;
- valid/invalid/boundary/overflow/resource/precision vectors.

Before broad catalog expansion, benchmark-hot-set operations receive review priority.

Do not add:

- open-ended forecasts;
- empirical coefficients presented as universal constants;
- live-data dependencies;
- ambiguous hidden method selection;
- arbitrary pack code.

## Compatibility ports

A successful compile is not support.

New ports require the evidence defined in `docs/COMPATIBILITY.md`. The first stable product scope prioritizes native static C ABI and no-import Wasm; additional profiles may remain Experimental without blocking v0.1.

## Pull-request checklist

- [ ] The change has one clear responsibility.
- [ ] Product priority is justified.
- [ ] Normative docs/spec/examples agree.
- [ ] Existing operation semantics are unchanged or revisioned.
- [ ] Failure behavior remains deterministic.
- [ ] No hidden allocation/network/runtime dependency entered the minimum core.
- [ ] No adapter/wrapper calculation or semantic repair was added.
- [ ] Size/latency/model-turn/compatibility impact is measured where relevant.
- [ ] Security-sensitive parser/ABI changes have negative tests.
- [ ] Generated adapter/hot-set artifacts are reproducible where applicable.
- [ ] Documentation makes no unmeasured accuracy/latency/energy or unsupported-hardware claim.

## Baseline verification

Typical repository verification includes:

```text
python tools/validate_design.py
cargo fmt --all -- --check
cargo check --workspace --all-targets
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```

Relevant changes additionally require C/C++ header checks, dynamic-pack feature checks, `wasm32v1-none` build/import inspection, wearable/integration checks, pack reproducibility, and parser malformed/fuzz coverage as applicable.

## Style

- Prefer explicit bounded structures over flexible generic abstractions.
- Keep model-facing names compact but semantically useful.
- Document invariants and evidence boundaries.
- Avoid silent defaults and hidden heuristics.
- Avoid comments that merely restate code.

## Responsible disclosure

Potential vulnerabilities follow `SECURITY.md`, not public exploit reports.

## Licensing

Contributions are accepted under the repository's dual Apache-2.0/MIT terms unless explicitly stated otherwise. Pack source/provenance material must have compatible rights; do not copy textbook prose or test material without appropriate review.
