# Next agent handoff — ExactScope v1.0.0-rc.2

Date: 2026-09-05
Current phase: **public integration/qualification candidate packaging complete; evidence run deferred to a new session**

This file is intentionally short. The full next-session procedure lives in [`QUALIFICATION_HANDOFF.md`](QUALIFICATION_HANDOFF.md), and the ready-to-paste Korean prompt lives in [`NEXT_SESSION_PROMPT.md`](NEXT_SESSION_PROMPT.md).

## What the previous implementation phase finished

The active product-code architecture is complete for the current Statistics/Economics scope:

- deterministic shared numeric core;
- bounded `xs_calc` plan execution;
- selected reviewed `xs_eval` semantic execution;
- optional/cold `xs_find` discovery;
- Tiny JSON and TinyWire boundaries;
- stable native C ABI and no-import Wasm host path;
- pack/packc and selected capability specialization;
- D-057 Statistics metadata phase 2: generated/drift-checked stable kernel IDs, operation declarations, arity/output contracts, selected lookup and dispatch plumbing;
- Economics selected operation/Cargo wiring checks;
- capability/model-surface identity and fail-closed negotiation;
- release-shaped deterministic packaging;
- operation-revision compatibility checks;
- source-level public unsafe-boundary/export auditing;
- build-input/reproducibility/compatibility-record infrastructure;
- maintained strict llama.cpp `xs_eval` and `xs_calc` envelopes.

Do not invent more Category-A product work merely because qualification checkboxes remain open.

## What rc2 packaging changes

`v1.0.0-rc.2` is prepared as a clean public source/release candidate rather than a continuation of a developer evidence directory.

The source tag keeps reviewed implementation/specs, generators, adapters, benchmark harnesses and preregistration inputs, but intentionally does not accumulate mutable generated capability/evidence directories or benchmark result payloads.

Release workflow intent:

- Windows x86-64 evaluation SDK;
- Linux x86-64 evaluation SDK;
- Android ARM64 static OEM SDK;
- Linux ARM64 musl static OEM SDK;
- release manifest + SHA256SUMS.

The release workflow derives package filenames from the project version and verifies the Git tag matches `Cargo.toml`.

## Evidence boundary

`statistics-core-8-ai-r20` is historical evidence tied to an older 45,804-byte r17 Statistics serving runtime. It is **not** rc2 evidence. Frozen evidence must never be rewritten or relabeled.

For rc2, do not claim until measured against the exact published artifacts:

- model accuracy uplift;
- production readiness;
- target latency/RAM/stack/energy;
- hardware-life savings;
- stable platform support.

A Wasm linear-memory ceiling is not process RSS/device RAM.

## Next model matrix

Core five, deliberately kept small and diverse:

1. Gemma 3 270M IT Q8_0;
2. LFM2.5 350M Q4_K_M;
3. Qwen3.5 0.8B Q4_0;
4. Qwen3.5 2B Q4_K_M;
5. Phi-4-mini-instruct 3.8B Q4_K_M.

Optional separate product profile: Gemma 3n E2B IT.

Machine-readable source: `benchmarks/model-downloads.json`.
Download helper: `tools/fetch_benchmark_models.py` (download/hash only, no inference).

## Next agent must do before model inference

1. Start from a fresh copy of the exact public `v1.0.0-rc.2` GitHub release, not a developer checkout.
2. Verify the release tag/commit, `release-manifest.json`, `SHA256SUMS`, and archive bytes.
3. Establish a no-model release/package baseline.
4. Download/core-inventory the five planned models and freeze repository revisions/file SHA-256 values.
5. Freeze corpus, prompt, tool/GBNF assets, runtime, generation parameters, scoring/failure taxonomy, timeout/retry policy, and stop rule in a preregistration record.
6. Only then run model qualification.

Primary arms: A model-only, C selected semantic-only, D combined when actually selected. Add B calc-only only for diagnostics.

No hidden repair/retry/manual answer correction unless preregistered.

## Target qualification after model results

When possible, use the exact published Android ARM64 or Linux ARM64 SDK on a representative target. Record binary/storage bytes, RSS/heap, stack/scratch, p50/p95/p99 latency, cold/warm behavior, energy measurement method/results where available, thermal behavior where relevant, malformed-input/fail-closed behavior, offline behavior, and update/rollback/power-loss behavior when applicable.

Keep desktop benchmark numbers separate from target-device qualification.

## Bug handling

Classify before modifying anything:

- product/runtime defect;
- release/package defect;
- adapter defect;
- model capability failure;
- harness/scorer defect;
- target integration defect.

If public product source/ABI/surface/corpus/scorer changes, it is a new evidence candidate. Preserve the rc2 baseline rather than silently fixing rc2 and continuing with the same label.

## Canonical continuation documents

Read in this order:

1. `docs/QUALIFICATION_HANDOFF.md`
2. `docs/NEXT_SESSION_PROMPT.md`
3. `benchmarks/NEXT_MODEL_MATRIX.md`
4. `benchmarks/model-downloads.json`
5. `docs/AI_INTEGRATION.md`
6. `docs/CODEX_CONTEXT.md`
7. `docs/QUICKSTART.md`

Until the next evidence session finishes, describe the state as:

> **ExactScope v1.0.0-rc.2 is a code-side-complete integration and qualification candidate; rc2 model and representative target qualification are not yet measured.**
