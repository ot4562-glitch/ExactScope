# ExactScope rc4 grounding benchmark-ready record

Status: **READY_FOR_GROUNDING_BENCHMARK**

Date: 2026-09-06

This is a post-freeze readiness record. The benchmark candidate source is **not** this documentation commit; it is the immutable source commit below. Do not rebuild the candidate from a later documentation-only commit and call it the same evidence identity.

## Frozen candidate identity

- source commit: `125ad9403f22eece7f552701d4c7376bba3b697f`
- candidate ID: `rc4-grounding-r3-seed-20260906`
- candidate manifest SHA-256: `0a792b15c0266f85d8dac3698d601f06fad54d593a2747f1918f4b5e18d7f30f`
- GroundingProfile SHA-256: `9575efb3fd3d0b1225e38775f2f0013a60757a639fe54fb71a0f826de26098ea`
- grounding manifest SHA-256: `4580c46be5f3df02294b18fb230e8801993514fd4de2636daad5ce1c12208649`
- serving manifest SHA-256: `8b4eeabc3053a77ba7450dc57926a22d1598bb5d7baaacd6804b6a72228f5ccd`
- gold manifest SHA-256: `03cc0c0b630afc421b3a4fadf29cf62dbc9933209d06300e1f876e895349c42f`
- dry-run serving-records SHA-256: `704cff7fc15596d3d70098524d1b5da484d88e584f5894641419d8c255d00074`
- item count: 30
- arms: `A`, `G`
- answer-generation calls: 1 per item per arm
- query rewrite calls: 0
- retries: 0
- hidden repair: false
- model inference performed during candidate qualification: **false**

## Evaluation package

- archive: `exactscope-grounding-eval-1.0.0-rc.4.tar.gz`
- archive SHA-256: `f665ec8b04a258262f343c5f5e875633b04230f588a20db4da2a3c80faf75dc5`
- package manifest SHA-256: `2879367ba76539e81bbe07a81be789fffbb796dd07aeab6c1996837c66cfa71c`
- package file count: 77
- source commit bound by package manifest: `125ad9403f22eece7f552701d4c7376bba3b697f`

The package was extracted into a fresh clean-room directory and verified before use, after Linux dry-run use, before Windows dry-run use, and after Windows dry-run use. The manifest remained valid after first use.

A pre-freeze package attempt exposed that normal Python imports could create `__pycache__` / `.pyc` files and make strict re-verification fail. That package was discarded. Candidate source `125ad940...` disables package-local bytecode-cache writes and includes a regression test proving packaged verification/dry-run/preregistration/help paths do not mutate the payload.

## No-inference clean-room results

Linux/WSL extracted-package path:

- package verify: PASS
- serving dry-run: PASS, 30 items, 0 gold reads, 0 model requests
- scorer-side gold verification: PASS
- routing correct: 30/30
- state correct: 30/30
- valid evidence only: 30/30
- no forbidden evidence: 30/30
- post-use package re-verification: PASS

Windows native Python path:

- package verify through `cmd.exe /c py -3`: PASS
- serving dry-run: PASS, 30 items, 0 gold reads, 0 model requests
- scorer-side gold verification: PASS
- routing correct: 30/30
- state correct: 30/30
- valid evidence only: 30/30
- no forbidden evidence: 30/30
- post-use package re-verification: PASS

Grounding states in the frozen corpus:

- grounded: 18/18 correct
- none: 5/5 correct
- unavailable: 5/5 correct
- ambiguous: 1/1 correct
- conflict: 1/1 correct

## Frozen inference runtime

- runtime: llama.cpp
- version: `0.4.0-dev (build 1, commit 5266f24)`
- executable SHA-256: `23cd72427da11ec0ab919699c28520b55d55ac702e7c436c2ef764c2e166b221`
- build: GNU 15.2.0 for Linux x86_64
- context: 4096
- threads: 6
- parallel: 1
- alias: `exactscope-model`
- Jinja: enabled
- reasoning: off
- prompt cache: off
- offline: enabled
- model inference during readiness checks: **not started**

## Five-model preregistrations

All local model files were re-hashed against the packaged inventory while creating the final preregistrations. Reusing the model files reuses only their byte identity, never rc3 benchmark scores.

| Model | Model SHA-256 | Preregistration SHA-256 | Verify-only |
|---|---|---|---|
| Gemma 3 270M IT Q8_0 | `0ef57d2c838458a1952664260dcba38e5bdda37494f3af732f06e4add24068e3` | `d5d401d36eb9ae41dd6cf83e9ad5865c59245ca5c982c821838fed871f146599` | `ready-to-run` |
| LFM2.5 350M Q4_K_M | `7e6f72643caafc9a68256686638c4d7916f2cec76d1df478d4c3ddcd95a6aed4` | `e9521b45f39bbbf0085aae43717131c90970bd6b7f0342614fa1d5231b394536` | `ready-to-run` |
| Qwen3.5 0.8B Q4_0 | `57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf` | `60aa41927accbd69c1078b2ecf9241d145f4ac73e272a49982ea06ba1548a19f` | `ready-to-run` |
| Qwen3.5 2B Q4_K_M | `0bfe35afc9f05b7fac3fa04925e051ac7939a42a8a17ea11afc99701bea826cc` | `5110941fdb3d7bcaa9fcd448e4ed400b19881f339ce68d986a08c8126b75271d` | `ready-to-run` |
| Phi-4-mini-instruct 3.8B Q4_K_M | `01999f17c39cc3074afae5e9c539bc82d45f2dd7faa3917c66cbef76fce8c0c2` | `7025ce8720461682a32ce0cbcfbbc87624744c29211b6c998c8a6989b14f0176` | `ready-to-run` |

Every `run_grounding_benchmark.py --verify-only` invocation returned:

- arms `[A,G]`;
- item count 30;
- max output tokens 96;
- `status: ready-to-run`;
- `model_inference_performed: false`.

The planned benchmark output directories were not created by `--verify-only`.

## Source and regression gates

Before freezing candidate source `125ad940...`, the current implementation passed:

- grounding profile/schema/canonicalization tests: 7/7;
- provider-neutral grounding runtime tests: 16/16;
- benchmark generator/scorer/isolation tests: 6/6;
- package/preregistration/runner tests: 5/5;
- `tools/validate_design.py`: PASS — 32 schemas, 6 registries, 61 example documents, 99 catalog operations, 5 reference vectors, 3 workflow files, 11 TOML files, ABI constants aligned;
- `tools/audit_security_surface.py`: PASS;
- grounding Python bytecode compilation: PASS;
- `cargo check --workspace --all-targets`: PASS;
- `cargo clippy --workspace --all-targets -- -D warnings`: PASS;
- retained quantitative Rust library regression suite had already passed 116/116 before the packaging-only fix; no Rust source changed in the packaging-fix commit.

The earlier P0 read-only architecture review reported `NO_P0_BLOCKERS`; the logical Grounding Contract remains frozen for this candidate.

## Product-direction boundary

This candidate tests the product pivot, not the old academic/tool-call-centered thesis.

The flagship intervention is:

```text
original user question
  -> provider-neutral host prefetch
  -> authority/freshness/conflict/budget policy
  -> compact deterministic GroundingFrame / Model Projection
  -> same small model, one answer-generation call
```

The exact/lexical provider in this candidate is a frozen **reference benchmark provider**, not the universal ExactScope product definition. Future semantic/vector/application/host providers must bind their own identity while preserving the same provider-neutral outcome/frame semantics.

`xs_calc` / `xs_eval` remain the retained quantitative subsystem. They are not the primary A/G intervention in this grounding benchmark.

## Claims that are still forbidden

`READY_FOR_GROUNDING_BENCHMARK` does **not** mean the product has already demonstrated:

- improved everyday factual accuracy;
- reduced hallucination or wrong-confident-answer rate;
- superiority to a larger model or heavier RAG system;
- production readiness;
- representative physical ARM64 RAM/latency/energy/thermal behavior.

Those require the separate frozen A/G validation session. Physical ARM64 target performance remains **NOT MEASURED** until a real target is available.

## Next action

Do not modify candidate source, package bytes, corpus, provider/profile, projection, scorer, generation config, model file, or runtime under these identities.

Start the separate validation session with:

1. [`GROUNDING_BENCHMARK_HANDOFF.md`](GROUNDING_BENCHMARK_HANDOFF.md)
2. [`NEXT_SESSION_PROMPT.md`](NEXT_SESSION_PROMPT.md)

If benchmark results motivate a product change, preserve this candidate/raw evidence and create a new candidate identity. Do not repair or resume this one in place.
