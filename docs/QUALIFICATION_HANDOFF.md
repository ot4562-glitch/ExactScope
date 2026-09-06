# ExactScope v1.0.0-rc.3 qualification handoff

Status: **runbook for a later verification session**
Release role: **integration & qualification candidate, not a stable/qualified product**
Date: 2026-09-06

This document is the source of truth for the next session that evaluates ExactScope as an external user would. The present release-preparation session must not create rc3 model scores or target-device claims. Qualification starts only from the immutable GitHub `v1.0.0-rc.3` release and its published assets.

## 1. Non-negotiable evidence boundary

- Treat the Git tag, commit, source archive, release assets, capability/model-surface assets, model files, benchmark corpus, prompts, runtime, scorer, and raw outputs as one evidence identity.
- Do not edit product source before establishing the baseline. A source change creates a new candidate and invalidates direct attachment of results to rc3.
- The old `statistics-core-8-ai-r20` results belong to a 45,804-byte r17 runtime. They are historical design evidence only. **Never copy or relabel them as rc3 evidence.**
- Do not hide parse, tool-selection, argument-extraction, runtime, token-limit, or final-answer failures. Keep them as separate categories.
- No hidden retries, semantic repair, answer repair, or manual correction unless a retry/repair policy was frozen before the run.
- A smoke/conformance pass does not imply model uplift, target latency, target RAM, energy efficiency, or production readiness.

## 2. Start from the release, not the developer checkout

Create a fresh directory and fetch the GitHub release assets. Keep the developer repository separate.

Record at minimum:

- release tag and commit SHA;
- GitHub source archive SHA-256;
- `release-manifest.json` and `SHA256SUMS` bytes/digests;
- each SDK archive name, byte size, and SHA-256;
- OS, CPU/SoC, RAM, runtime/toolchain version, and command lines used.

Verify `SHA256SUMS` before extracting or loading artifacts. Compare the release manifest's `source_commit` with the tag commit. If either check fails, mark the run **invalid** and do not continue as rc3 qualification.

## 3. Choose the integration asset

The rc3 release is designed to expose four practical integration routes:

| Target | Expected release asset | Primary use |
|---|---|---|
| Windows x86-64 | `exactscope-eval-1.0.0-rc.3-x86_64-pc-windows-msvc.tar.gz` | desktop/local-AI integration and model qualification |
| Linux x86-64 | `exactscope-eval-1.0.0-rc.3-x86_64-unknown-linux-gnu.tar.gz` | server/local-AI integration and model qualification |
| Android ARM64 | `exactscope-wearable-sdk-1.0.0-rc.3-aarch64-linux-android.tar.gz` | Android/edge product integration and target qualification |
| Linux ARM64 | `exactscope-wearable-sdk-1.0.0-rc.3-aarch64-unknown-linux-musl.tar.gz` | embedded Linux/wearable product integration and target qualification |

Evaluation SDKs contain the native static library, a local core bridge, no-import Wasm, model-facing assets, examples, model-download tooling, and this runbook. ARM64 SDKs contain the static library, headers, wearable reference host, A/B update helpers, benchmark stream helpers, and qualification contracts.

Do not infer support for an asset that is absent from the actual release.

## 4. Establish a no-model baseline first

Before downloading or running a model, prove that the exact release asset is internally coherent. The later session may run the bundled integrity, static ABI, and smoke/conformance commands documented in `docs/QUICKSTART.md` and the archive manifest.

Record every command and result. If a release artifact fails its bundled self-check, stop model qualification and classify the issue as a release/product integration defect rather than working around it in the benchmark harness.

## 5. Download the minimum model matrix

The machine-readable plan is `benchmarks/model-downloads.json`; rationale and fairness rules are in `benchmarks/NEXT_MODEL_MATRIX.md`.

Core five:

1. Gemma 3 270M IT Q8_0 — extreme-small independent lower bound.
2. LFM2.5 350M Q4_K_M — edge/on-device-first lower bound.
3. Qwen3.5 0.8B Q4_0 — modern mainstream sub-1B primary small model.
4. Qwen3.5 2B Q4_K_M — same-family scaling point.
5. Phi-4-mini-instruct 3.8B Q4_K_M — independent upper-small reasoning reference.

Optional product profile: Gemma 3n E2B IT, evaluated separately because it is gated, multimodal, and may require a different runtime path.

Windows download preparation:

```powershell
py -3 -m pip install -r requirements-benchmark.txt
py -3 tools/fetch_benchmark_models.py --list
py -3 tools/fetch_benchmark_models.py core --root C:\AIModels\ExactScopeBench
```

The downloader must resolve the repository revision first, download the file at that immutable revision, hash the local bytes, and write `model-inventory.json`. Preserve that inventory unchanged with the run.

For gated models, accept the upstream model terms yourself and provide `HF_TOKEN` where required. ExactScope's source license does not replace model licenses.

## 6. Preregister before the first inference call

Freeze a qualification record containing:

- ExactScope tag/commit/source/archive/runtime digests;
- exact model inventory and local SHA-256 values;
- inference runtime build/version and launch command;
- context size and chat template behavior;
- corpus path, SHA-256, generator identity, task-family split, and item count;
- prompt/system text and exact GBNF/tool schema/prompt-fragment digests;
- temperature, seed, max generated tokens, and all sampling parameters;
- arm definitions;
- failure taxonomy and scoring rules;
- duplicate/single-writer policy;
- retry/timeout policy;
- any fixed early-stop/futility rule.

If anything above changes after seeing results, create a new run identity instead of silently continuing the old one.

The published evaluation archive includes the preregistration mechanism; do not invent a parallel JSON format:

```sh
python benchmarks/run_qualification.py preregister --help
```

That command performs zero inference. It verifies and freezes the downloaded evaluation archive itself, selected model record plus the complete `model-inventory.json`, llama.cpp executable/version/launch command, `benchmarks/corpus-v0.1.jsonl`, packaged core, and both exact public capability identities. The resulting preregistration is the required input to:

```sh
python benchmarks/run_qualification.py run --preregistration <frozen.json> --output-dir <new-empty-directory>
```

`run` re-hashes every frozen file before the first request. It will not resume into an existing output directory, retry a failed model request, substitute another capability, or repair a tool call.

## 7. Model qualification arms

Use the minimum useful comparison:

- **A — model only:** no ExactScope model-facing surface.
- **C — semantic-only:** exact public `capabilities/quant-core-16-semantic-ai`, exposing only `xs_eval` over the frozen 16-operation benchmark surface.
- **D — combined:** exact public `capabilities/quant-core-16-combined-ai`, exposing the same `xs_eval` surface plus bounded `xs_calc`.

The current corpus contains reviewed semantic Economics/Statistics tasks, so a supported C/D item expects the `xs_eval` lane. A D-side `xs_calc` choice is a wrong-lane failure even when arithmetic happens to match. Missing-information items expect no tool call. **B — xs_calc-only** remains an optional diagnostic outside the primary packaged A/C/D runner; do not add it after seeing A/C/D results.

Do not expose `xs_find` or a larger maintenance catalog on the normal serving path just because those assets exist for development.

Use equal item sets and equal generation budgets for comparable arms. The deterministic runtime may be exact while the overall system remains wrong because the model selected a wrong operation or arguments; score the end-to-end result, not only the tool call.

## 8. Result structure

Write each new run under a unique directory outside tracked source, for example:

```text
benchmarks/output/rc3-<model-id>-<run-id>/
```

Preserve:

- preregistration record;
- model inventory copy;
- all model-visible surface files;
- raw item records;
- summary;
- runtime/tool logs needed for audit;
- hashes for all evidence files;
- explicit `complete`, `invalid`, or `aborted` status.

Require a single writer. Duplicate `(arm, item_id)` keys, partial output presented as complete, or unexplained model/runtime identity changes invalidate the run.

## 9. What to report for each model

At minimum report:

- total/correct count and rate per arm;
- malformed-output count;
- wrong-tool/semantic-selection count;
- argument-extraction count;
- ExactScope typed runtime failure count;
- numeric/final-answer mismatch count;
- token-limit/timeout count;
- any excluded/invalid items and the preregistered reason;
- exact ExactScope artifact bytes and SHA-256;
- exact model bytes/revision/SHA-256.

Do not use a single composite multiplier as the headline when failure budgets or model sizes are not directly comparable. Counts and transparent denominators come first.

## 10. Target-device qualification after model qualification

Run target qualification only against an immutable release asset and a recorded device/runtime configuration. For Android ARM64 or embedded Linux ARM64, use the bundled wearable profile/qualification schemas and reference host rather than inventing a new result format.

Measure, where the target allows it:

- static/runtime artifact bytes and flash/storage footprint;
- process/VM resident memory and heap behavior;
- stack high-water/scratch requirements;
- latency distribution, not only one mean (at least p50/p95/p99 where enough samples exist);
- cold/warm behavior if relevant;
- energy per operation/workload with the measurement method documented;
- thermal/throttling behavior for sustained workloads where relevant;
- malformed-input/fail-closed behavior;
- offline operation;
- A/B update, rollback, interrupted replacement, and power-loss behavior where the product uses dynamic packs/updates.

Keep desktop benchmark latency separate from target-device qualification. A 64 KiB Wasm linear-memory maximum is not process RSS and must not be reported as total device RAM usage.

## 11. Bug classification during qualification

When something fails, classify before changing code:

- **Product/runtime defect:** valid request violates documented deterministic behavior or ABI/surface contract.
- **Release/package defect:** missing, mismatched, corrupt, or unusable published asset/instructions.
- **Adapter defect:** model/runtime envelope violates its documented contract while core/runtime is correct.
- **Model capability failure:** wrong selection, arguments, or output despite a valid adapter/runtime.
- **Harness/scorer defect:** the measurement itself is wrong or ambiguous.
- **Target integration defect:** platform/linking/memory/lifecycle issue specific to the device host.

A fix to product source, public ABI, selected surface, benchmark corpus, scorer, or adapter creates a new candidate/revision for evidence purposes. Do not repair rc3 and keep the rc3 label on the new binary.

## 12. Promotion gate

`v1.0.0-rc.3` stays a prerelease until evidence exists for the exact immutable artifacts. Do not change README or release claims to stable/qualified merely because code tests pass.

A future stable/support decision should have, at minimum:

1. release-asset integrity and exact identity verified;
2. native/Wasm conformance for the exact published artifacts;
3. model qualification across the frozen minimum matrix or a documented product-specific subset;
4. at least one representative real ARM64 target qualification for the intended product path;
5. no unresolved high-severity security/ABI defect;
6. reproducibility/compatibility records appropriate to the claimed support level;
7. claims rewritten only from the exact accumulated evidence.

## 13. Continue in another ChatGPT/Codex session

Use [`NEXT_SESSION_PROMPT.md`](NEXT_SESSION_PROMPT.md) as the copy-paste starting prompt. That prompt deliberately instructs the next session to behave like an external evaluator, verify the immutable GitHub release first, and avoid changing the candidate before baseline evidence is captured.
