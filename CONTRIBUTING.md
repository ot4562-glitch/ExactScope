# Contributing to ExactScope

ExactScope is a tiny grounding and deterministic capability layer for small/on-device AI. The flagship rc4 objective is **everyday factual accuracy and hallucination reduction at low token/latency/footprint cost**; quantitative `xs_calc`/`xs_eval` remains a secondary deterministic subsystem. Contributions are evaluated by **product leverage, grounding precision, deterministic correctness, integration simplicity, footprint, portability, privacy and evidence**—not by raw feature count.

## Current project phase

`v1.0.0-rc.3` qualification is closed and its evidence is immutable. The frozen rc4 grounding candidate source `125ad9403f22eece7f552701d4c7376bba3b697f` is **READY_FOR_GROUNDING_BENCHMARK** after no-inference Linux/Windows package and five-model preregistration gates. Do not change candidate behavior under that identity; the next phase is the separate A/G validation session. Original-question prefetch, compact Grounding Frames, authority modes and retrieval-provider identity are the active product design; constrained/native quantitative interfaces remain supporting infrastructure.

Read this order first:

1. `docs/PRODUCT_DIRECTION.md`
2. `docs/GROUNDING_ARCHITECTURE.md`
3. `spec/GROUNDING_CONTRACT_V0_1.md`
4. `docs/AI_INTEGRATION.md`
5. `docs/BENCHMARK.md`
6. `ROADMAP.md`
7. `docs/ARCHITECTURE.md`
8. `docs/QUICKSTART.md`
9. `docs/COMPATIBILITY.md`
10. `docs/DECISIONS.md`
11. `SECURITY.md`
12. `docs/IMPLEMENTATION_PLAN.md` for the quantitative subsystem/history

`docs/FIRST_IMPLEMENTATION_SLICE.md` is historical implementation context, not the current priority plan.

## Product-priority rule

Before proposing a large feature, ask whether it improves one of these:

- everyday factual accuracy or wrong-confident-answer reduction;
- retrieval precision / false-grounding avoidance;
- provider-neutral Grounding Contract simplicity;
- authoritative/supplemental, freshness, ambiguity and conflict correctness;
- evidence token/byte/latency efficiency for small models;
- private-source scope and isolation;
- correctness/security of the deterministic quantitative core and public boundaries;
- five-minute integration and reproducible model/target qualification evidence;
- exact release packaging, compatibility, update and rollback behavior.

Broad platform support, academic catalog expansion, per-domain feature work, and retrieval-algorithm novelty are secondary until the grounding contract is frozen and the everyday benchmark proves product value.

## Core invariants

Do not casually weaken:

- AI-consumed headless core;
- offline-capable/library-first operation;
- no mandatory daemon/account/network;
- `no_std` allocator-free minimum kernel;
- stable C ABI and no-import Wasm boundary;
- deterministic checked numeric semantics;
- data-only scope packs;
- bounded execution/memory;
- semantic fail-closed behavior;
- one shared calculation semantics across profiles;
- evidence-backed compatibility/marketing claims.

## AI integration changes

The normal rc4 hot path is **grounding prefetch before the answer model call**. Quantitative `xs_calc`/`xs_eval` remains available when the task actually needs deterministic calculation; `xs_find` is quantitative cold-path discovery.

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

Benchmark contributions should follow `docs/BENCHMARK.md`. The flagship rc4 comparison is **A model-only vs G original-question-prefetch grounding**, with one answer-generation model call per arm. Optional query rewrite/tool profiles are separate ablations because they spend extra inference/tokens. Historical quantitative A/B/C/D arms remain valid only for the quantitative subsystem.

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
