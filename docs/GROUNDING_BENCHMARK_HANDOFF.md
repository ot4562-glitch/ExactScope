# ExactScope rc4 grounding benchmark handoff

Status: **ACTIVE HANDOFF CONTRACT — use only after the source-bound candidate is labeled `READY_FOR_GROUNDING_BENCHMARK`**

This handoff is for the separate validation session that will run the first rc4 model inference. It does not replace the historical rc3 qualification record in `QUALIFICATION_HANDOFF.md`.

## 1. Product hypothesis being tested

The flagship rc4 claim under test is narrow:

> For small/on-device models, deterministic original-question grounding prefetch can improve everyday factual reliability and/or reduce confidently wrong answers at acceptable token, latency, storage and integration cost, without replacing the model and without requiring a model-visible retrieval tool turn.

This is **not** a test of academic-domain breadth, a general RAG framework, or model tool-call obedience.

The retained `xs_calc`/`xs_eval` subsystem is outside the primary A/G efficacy comparison except where later analysis explicitly uses quantitative historical context.

## 2. Immutable inputs

Start from the final extracted **grounding evaluation package**, not a developer checkout. Preserve the outer archive and its SHA-256.

The package must contain and bind:

- `candidate/serving/` and `candidate/gold/` with distinct manifests;
- the exact `GroundingProfile`, source snapshots, provider/index identity, merge policy and Model Projection assets;
- `grounding-generation-config.json`;
- `grounding-isolation-policy.json`;
- the five-model `grounding-model-inventory.json`;
- the frozen llama.cpp runtime record;
- `grounding_preregister.py`, `run_grounding_benchmark.py`, `score_grounding.py`;
- package manifest and `SHA256SUMS`.

Do not substitute a newer model quantization, runtime build, candidate, prompt, scorer, provider, corpus or projection while keeping the old run ID.

## 3. First action: verify package with zero inference

From a fresh extraction:

```text
python tools/verify_grounding_package.py
python benchmarks/grounding_dry_run.py serve --candidate candidate --output <fresh-serving-dryrun>
python benchmarks/grounding_dry_run.py verify-gold --candidate candidate --records <fresh-serving-dryrun>/serving-records.jsonl --output <fresh-gold-check>
```

These commands must report zero model requests/inference. If package identity, serving/gold separation, routing, state, or expected-evidence checks fail, stop. Do not patch the package in place.

## 4. Frozen five-model matrix

Use the exact five model identities already recorded in the packaged inventory:

1. Gemma 3 270M IT Q8_0;
2. LFM2.5 350M Q4_K_M;
3. Qwen3.5 0.8B Q4_0;
4. Qwen3.5 2B Q4_K_M;
5. Phi-4-mini-instruct 3.8B Q4_K_M.

The local model bytes may be reused from the earlier qualification store **only when their SHA-256 matches the packaged rc4 inventory**. This reuses model file identity, not rc3 scores or evidence.

## 5. Preregister each model before inference

Create one immutable preregistration per model from the extracted package. Use a unique planned output directory that does not yet exist.

The preregistration must bind at least:

- source commit and package manifest/archive SHA;
- candidate/serving/gold/profile/provider/source/projection identities;
- exact model file path/bytes/SHA/repository revision;
- exact llama.cpp executable path/SHA/version/commit/launch config;
- host hardware record;
- generation config, isolation policy and scorer SHA;
- arms exactly `[A,G]`;
- one answer call per item per arm;
- rewrite calls = 0;
- retries = 0;
- hidden repair = false;
- manual correction = false;
- duplicate rule = reject `(arm,item_id)`;
- drift rule = reject any bound byte/config drift.

Then run:

```text
python benchmarks/run_grounding_benchmark.py --preregistration <frozen.json> --output <planned-output> --verify-only
```

`--verify-only` must succeed before the first model request. It must not create the planned output or launch the model runtime.

## 6. A/G model benchmark

Only after all five preregistrations pass the verify-only gate may the validation session run inference.

For every item and model:

- **A — model only:** original common system prompt + original question; exactly one answer-generation request.
- **G — grounded:** deterministic original-question prefetch first, then the same common system prompt plus the frozen Grounding Projection policy/evidence and original question; exactly one answer-generation request.

Do not add model-visible retrieval tools, query-rewrite calls, hidden chain retries, answer repair, semantic repair, manual correction, or a second attempt because one arm failed.

A provider failure is `unavailable`, not `none`. `authoritative none` may be emitted only after complete required coverage. Supplemental no-hit must not force refusal if ordinary model knowledge is permitted by policy.

## 7. Preserve raw evidence before scoring

Each model run must remain single-writer and append only to its new output directory. Preserve:

- preregistration copy/hash;
- run metadata;
- raw A/G records;
- exact model responses, token counts and model latency;
- G retrieval latency, GroundingFrame, audit sidecar and projection byte/hash;
- llama-server log;
- complete/invalid/aborted status;
- `SHA256SUMS`.

An invalid or aborted run is never resumed or merged. A replacement run needs a new run ID/output directory.

## 8. Score only after a complete raw run exists

Only the scorer may open `candidate/gold/` after a raw run is complete. Report raw counts and denominators before ratios.

Headline metrics:

- factual accuracy A vs G;
- wrong-confident-answer rate A vs G;
- unsupported authoritative assertion rate;
- correct abstention/useful-answer/over-abstention rates;
- false grounding;
- grounding adherence;
- stale-revision override success;
- provider-unavailable fidelity;
- injection/bait obedience;
- grounding recovery and grounding penalty;
- input/output token delta;
- retrieval/model latency delta;
- projection/index/storage bytes;
- accuracy uplift per added token, byte and model-latency millisecond where denominators are meaningful.

Do not hide negative uplift or models for which G is worse than A.

## 9. Failure taxonomy

At minimum distinguish:

- routing failure;
- retrieval miss/false retrieval;
- provider timeout/error/denied/budget/incomplete failure;
- authority/state-policy failure;
- ambiguity/conflict handling failure;
- projection/data-boundary failure;
- malformed model output;
- unsupported authoritative assertion;
- stale-memory regression;
- over-abstention;
- ordinary model answer error despite correct grounding;
- runtime/harness/scorer defect;
- token limit/timeout.

## 10. Claims after the model matrix

Do not generalize one workload into a universal model claim. Report per-model and aggregate counts transparently.

Even a successful desktop A/G matrix does **not** establish physical ARM64 product RAM, energy, thermal or target latency. Those remain a separate target-device qualification phase.

Any product change suggested by benchmark results creates a **new candidate**. Never modify the frozen candidate and continue under the old preregistration.

## 11. Required validation-session outputs

Create at minimum:

- `GROUNDING_BENCHMARK_REPORT_rc4.md`;
- `GROUNDING_MODEL_MATRIX_rc4.json`;
- `GROUNDING_FAILURE_TAXONOMY_rc4.json`;
- `GROUNDING_COST_REPORT_rc4.json`;
- `GROUNDING_PRODUCT_DECISION_rc4.md`;
- `GROUNDING_REPRODUCIBILITY_LOG_rc4.md`;
- immutable per-model raw run directories.

The final product verdict must separate:

1. package/reproducibility;
2. grounding-path correctness;
3. model efficacy;
4. false-grounding/safety behavior;
5. token/latency/storage economics;
6. physical target qualification status;
7. support/stable-release readiness.
