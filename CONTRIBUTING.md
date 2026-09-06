# Contributing to ExactScope

ExactScope is a tiny deterministic quantitative coprocessor for small/on-device AI. Contributions are evaluated by **product leverage, deterministic correctness, integration simplicity, footprint, portability, and evidence**—not by raw feature count.

## Current project phase

`v1.0.0-rc.3` is a code-side-complete **integration & qualification candidate** for the active Statistics/Economics architecture. The current priority is to keep the public candidate reproducible and small while external-user model/target qualification is performed from the immutable release. New feature breadth is not a substitute for that evidence.

Read this order first:

1. `docs/PRODUCT_DIRECTION.md`
2. `docs/QUICKSTART.md`
3. `docs/AI_INTEGRATION.md`
4. `docs/BENCHMARK.md`
5. `ROADMAP.md`
6. `docs/IMPLEMENTATION_PLAN.md`
7. `docs/ARCHITECTURE.md`
8. `docs/COMPATIBILITY.md`
9. `docs/DECISIONS.md`
10. `SECURITY.md`

`docs/FIRST_IMPLEMENTATION_SLICE.md` is historical implementation context, not the current priority plan.

## Product-priority rule

Before proposing a large feature, ask whether it improves one of these:

- correctness/security of the deterministic core and public boundaries;
- `xs_calc` / selected `xs_eval` model-surface simplicity;
- capability/model-surface identity and fail-closed compatibility;
- five-minute release-asset integration;
- reproducible model/target qualification evidence;
- exact release packaging, compatibility, update and rollback behavior;
- measured product value on a real constrained workload.

Broad platform support, dynamic-profile polish, catalog expansion, and new domains are secondary until the rc3 candidate is independently qualified.

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

The product has two normal hot paths: bounded `xs_calc` for short arithmetic and direct `xs_eval` for reviewed semantic operations in the selected capability slice. `xs_find` is fallback discovery.

Adapter/capability-slice contributions should therefore prefer:

- one compact bounded `xs_calc` tool rather than per-arithmetic-operation tools;
- the smallest semantic operation selection that covers the target task families, not a fixed operation-count target;
- OpenAI-compatible tool assets and constrained GBNF/JSON Schema where useful;
- llama.cpp fixtures/reference integration;
- digest/revision/profile-bound caching;
- measurable model-difficulty cost: prompt/schema/grammar size, tool/operation selection, invalid/accepted calls, extraction, turns, and fidelity.

Adapters may normalize syntax/transport but not semantics.

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

Benchmark contributions should follow `docs/BENCHMARK.md` and `docs/QUALIFICATION_HANDOFF.md`. For the rc3 flagship qualification, the primary arms are A model-only, C selected semantic-only, and D combined where the exact selected profile contains both lanes. Add B `xs_calc`-only only when it answers a diagnostic question; discovery is an optional ablation, not a required hot path.

Do not publish a single blended score without stage-level failures and cost metrics. Do not run a public rc3 comparison from a modified developer checkout and call it release evidence.

Any comparative claim must identify exact release/capability/model-surface/model/runtime/hardware/corpus/scorer identities and digests.

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
