# Codex / agent context — ExactScope v1.0.0-rc.2

Date: 2026-09-05
Release role: **integration & qualification candidate**

Read this before modifying ExactScope. For the next evidence session also read `docs/QUALIFICATION_HANDOFF.md` and `docs/NEXT_SESSION_PROMPT.md`.

## Product thesis

ExactScope is a tiny deterministic quantitative capability retrofit for constrained/on-device AI. The buyer/integrator is an OEM, device maker, embedded-AI team, or local-inference developer. It is not a human calculator, chatbot, hosted API, daemon, arbitrary Python replacement, or broad scientific runtime.

The win condition is narrow: `existing small model + tiny ExactScope slice` should recover a useful deterministic capability without forcing a larger model/hardware change when the task does not otherwise need one.

## Serving lanes

- `xs_calc`: bounded generic arithmetic plan, maximum 8 steps over `add/sub/mul/div/powi/sqrt`.
- `xs_eval`: reviewed selected semantic operations.
- `xs_find`: optional cold/development discovery, not a mandatory hot path.

Fewer model-visible choices are a feature.

## Hard invariants

- deterministic semantics;
- exact base-10/rational semantics where defined;
- fail-closed behavior;
- bounded memory/work;
- stable status/ABI/operation revisions;
- no arbitrary generated code execution;
- no hidden semantic repair;
- one shared numeric core;
- pack-local operation IDs and internal kernel IDs are separate namespaces;
- never renumber stable internal kernel IDs casually;
- generated metadata must be deterministic and drift-detectable;
- specialized artifacts must not retain excluded serving paths accidentally.

Correctness/determinism/fail-closed/ABI come before a small byte reduction. If a performance change threatens the tiny-runtime niche with large binary growth, prefer the smaller implementation unless evidence justifies the trade.

## Active code-side state

The active Statistics/Economics product architecture is code-side complete for rc2.

Rust crates:

- `exactscope-kernel`: deterministic decimal/rational core, plans/VM, reviewed Statistics/Economics semantics.
- `exactscope-pack`: pack identity, fused registries, optional dynamic `.xsp`, lookup/discovery, shared-kernel execution.
- `exactscope-tinyjson`: strict bounded allocation-free JSON boundary.
- `exactscope-wasm`: no-import Wasm wrapper and selected specialization.
- `exactscope-cabi`: stable native C ABI with pointer/buffer checks.
- `exactscope-packc`: canonical pack compiler/hot-set assets.
- `exactscope-conformance`: cross-path parity and local core bridge.

Build/generation tooling:

- `tools/compile_capability.py`: domain-general capability compiler driven by `spec/capabilities/domain-descriptors.json`.
- `tools/generate_statistics_metadata.py`: deterministic Statistics operation/kernel/dispatch metadata and Cargo checks.
- `tools/generate_domain_metadata.py`: domain selection/Cargo wiring metadata including Economics selection.
- `tools/package_evaluation_bundle.py`: deterministic evaluation SDK packaging.
- `tools/package_wearable_sdk.py`: deterministic ARM64 OEM SDK packaging.
- `tools/build_input_identity.py`, model-surface compatibility, operation revision, reproducibility, and compatibility-record tooling implement evidence identity/support plumbing.

D-057 metadata phase 2 is complete: Statistics stable kernel IDs, arity/output contracts, operation declarations, selected lookup, dispatch-call plumbing, packc kernel-name lookup, and Cargo forwarding are generated or drift-checked. Economics selected lookup/scalar wiring is drift-checked. Numeric algorithms remain handwritten/reviewed.

## rc2 clean-source policy

The release source keeps reviewed source/specs, deterministic generators, benchmark harnesses/preregistration inputs, and historical interpretation documents. It does **not** carry forward mutable generated capability/evidence revision directories or mutable benchmark output payloads as product source.

- `adapters/capabilities/` contains only policy/readme in a clean tag; new capability revisions are generated per exact candidate.
- `benchmarks/output/` is ignored.
- `benchmarks/results/` keeps policy/readme only in the clean source; frozen evidence should be published separately/immutably rather than overwritten.

Never delete or rewrite historical frozen evidence in a developer checkout just to make a source release look clean. The rc2 release was prepared in a separate clean clone.

## Evidence boundary

Historical `statistics-core-8-ai-r20` model evidence belongs to an older 45,804-byte r17 Statistics serving runtime. It does not transfer to rc2.

Do not claim for rc2 without new matching evidence:

- model accuracy uplift;
- current specialized artifact byte measurements as if they were old r20 numbers;
- target latency or RAM;
- energy savings;
- hardware-life extension;
- production readiness;
- stable target qualification.

A 64 KiB Wasm linear-memory ceiling is not process RSS/device RAM.

## rc2 public packaging intent

The release workflow is configured to produce:

- Windows x86-64 evaluation SDK;
- Linux x86-64 evaluation SDK;
- Android ARM64 OEM SDK;
- Linux ARM64 musl OEM SDK;
- release manifest and SHA256SUMS.

Evaluation SDKs include native library, local core bridge, no-import Wasm, model-facing/generated adapter assets, examples, benchmark/model-download tooling, qualification runbook, licenses, manifests and checksums.

Tag and Cargo version must match. Do not hardcode future release filenames in workflows.

## Next model qualification

`benchmarks/NEXT_MODEL_MATRIX.md` defines the minimal diverse core matrix:

1. Gemma 3 270M IT Q8_0;
2. LFM2.5 350M Q4_K_M;
3. Qwen3.5 0.8B Q4_0;
4. Qwen3.5 2B Q4_K_M;
5. Phi-4-mini-instruct 3.8B Q4_K_M;
6. optional separate Gemma 3n E2B product profile.

`tools/fetch_benchmark_models.py` downloads and hashes models only; it does not run inference.

The later qualification session should start from the immutable GitHub rc2 release, preregister exact identities, use A model-only / C selected semantic / D combined as the primary arms, add B calc-only only for diagnostics, then perform representative ARM64 target qualification.

## Modification rules

- Preserve dirty/unrelated developer work; never reset/clean/stash/discard it without explicit user intent.
- Do not overwrite frozen capability/evidence revisions.
- Do not change ABI/kernel IDs casually.
- Treat `UNSUPPORTED_OPERATION` in deliberate specialization/fail-closed paths as a contract, not an implementation TODO.
- New domains/new operations are reviewed product breadth, not missing rc2 plumbing.
- Keep generated metadata and checked-in outputs in deterministic sync.
- A product/public ABI/surface/corpus/scorer change after rc2 creates a new candidate for evidence purposes.

## Validation classes

Code-side release preparation may use:

- source/schema/generator drift checks;
- compiler/type checking;
- `cargo fmt/check/clippy`;
- ordinary unit/component tests;
- Python syntax/unit tests that do not launch model evaluation;
- static linkage/cross-build checks;
- static Wasm import/memory/export inspection;
- ABI/header compilation;
- bundle integrity/digest checks.

Model inference, benchmark scoring, real-device qualification, energy/latency claims, model-evidence attachment, and stable support promotion belong to the separate qualification session.

## Handoff

For external-user evaluation, use:

- `docs/QUALIFICATION_HANDOFF.md`
- `docs/NEXT_SESSION_PROMPT.md`
- `benchmarks/NEXT_MODEL_MATRIX.md`
- `benchmarks/model-downloads.json`

The correct description before that work is: **rc2 code-side implementation and release packaging candidate, not yet model/target qualified.**
