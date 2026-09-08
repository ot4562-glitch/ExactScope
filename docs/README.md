# ExactScope documentation map

Release context: **ExactScope v1.0.0 is the stable Linux x86-64 native grounding software release. The selected r25 behavior, native C ABI, deterministic package, footprint gate, and final-archive C11 clean-room path are complete. Physical ARM64 device qualification remains explicitly unclaimed.**

Date: 2026-09-08

This index contains the documents intended for users, integrators, reviewers and public reproducibility. Internal experiment logs, agent prompts, evaluator handoffs and release-operator notes are intentionally kept outside the public repository.

## Start here — grounding product path

Read in this order:

1. [`PRODUCT_DIRECTION.md`](PRODUCT_DIRECTION.md) — product objective, scope and decision test.
2. [`GROUNDING_ARCHITECTURE.md`](GROUNDING_ARCHITECTURE.md) — provider-neutral source/provider/policy/GroundingFrame architecture.
3. [`../spec/GROUNDING_CONTRACT_V0_1.md`](../spec/GROUNDING_CONTRACT_V0_1.md) — normative authority, provider, evidence and failure-state contract.
4. [`AI_INTEGRATION.md`](AI_INTEGRATION.md) — selected host-first integration path and llama.cpp model surface.
5. [`INSTALLATION.md`](INSTALLATION.md) — embedding and package requirements.
6. [`QUICKSTART.md`](QUICKSTART.md) — shortest evaluation path.
7. [`BENCHMARK.md`](BENCHMARK.md) — A/G benchmark, gold isolation, preregistration and qualification rules.
8. [`GROUNDING_EVALUATION_PACKAGE.md`](GROUNDING_EVALUATION_PACKAGE.md) — immutable evaluation-package boundary.
9. [`../SECURITY.md`](../SECURITY.md) — scope, privacy, evidence and prompt-injection trust boundaries.
10. [`RC3_QUALIFICATION_CLOSEOUT.md`](RC3_QUALIFICATION_CLOSEOUT.md) — frozen historical findings that motivated the grounding-first product direction.

The root [`README.md`](../README.md) contains the current paired model-only vs ExactScope accuracy table and the broader HotpotQA/NQ development evidence. The frozen seven-model screen spans 135M to 3.8B and was re-scored after the native C ABI/release integration with identical semantic results. Those model-accuracy measurements remain candidate/provider/corpus scoped; the stable v1 claim is the Linux x86-64 native grounding software/package scope, not universal accuracy across arbitrary providers.

## Current selected behavior

The stable v1 host order is:

```text
GroundingFrame
  -> authoritative unresolved state: deterministic host disposition, 0 model calls
  -> one grounded canonical scalar: deterministic host value, 0 model calls
  -> no routed target / supplemental miss: ordinary model knowledge
  -> remaining grounded text: compact evidence + one model answer call
```

The reference llama.cpp integration is [`../adapters/llama-cpp/grounding_v1.py`](../adapters/llama-cpp/grounding_v1.py). It uses a loopback-only llama.cpp endpoint, no answer retry, and a one-time model-identity-bound calibration among the already measured compact answer contracts. The calibration is not paid per user question.

## Supporting public documents

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — combined grounding + deterministic quantitative system boundary.
- [`GROUNDING_RUNTIME_RC4.md`](GROUNDING_RUNTIME_RC4.md) — host reference runtime and selected completion order.
- [`COMPATIBILITY.md`](COMPATIBILITY.md) — compatibility and identity rules.
- [`EVALUATION_BUNDLE.md`](EVALUATION_BUNDLE.md) — frozen rc3 quantitative evaluation bundle.
- [`CAPABILITY_COMPILER.md`](CAPABILITY_COMPILER.md) — quantitative capability/profile compiler.
- [`MODEL_INTERFACE_RC4.md`](MODEL_INTERFACE_RC4.md) — quantitative constrained/native model envelopes.
- [`CAPABILITY_PRODUCT_ARCHITECTURE.md`](CAPABILITY_PRODUCT_ARCHITECTURE.md) — quantitative capability unit and model/device budgets.
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — contribution rules.
- [`../ROADMAP.md`](../ROADMAP.md) — public product/release milestones.

## Quantitative subsystem

`xs_calc`, `xs_eval`, native C ABI and no-import Wasm remain supported deterministic infrastructure, but they are not the default everyday factual-answering path. The grounding layer avoids requiring weak models to navigate a broad tool catalog just to answer ordinary factual questions.

Historical quantitative documents and rc3 results remain valid only for their exact recorded runtime/model/package identities. They are not v1 grounding accuracy evidence and are not transferred into stable grounding claims.

## Evidence identity rule

Grounding evidence belongs only to the exact combination of:

- source/content revision or digest;
- retrieval provider/index/preprocessing/ranking identity;
- source scope and authority mode;
- freshness/revision/conflict/ambiguity policy;
- evidence top-k/byte/token budget;
- GroundingFrame/model-projection/policy bytes;
- selected model-answer contract;
- model file/runtime/generation settings;
- corpus/scorer identity;
- candidate/package/source identity.

Changing any behavior-affecting field creates a new evidence candidate. Source-run optimization scores are never copied into release-qualified claims.

## Clean public-source rule

The public source keeps reviewed product code/specifications, public adapters, generators, benchmark/qualification tooling, user-facing documentation and intentionally public historical findings. It does **not** keep internal experiment logs, local model/server paths, raw benchmark output, agent context, handoff notes, evaluator prompts or release-operator scratch files.

`python3 tools/audit_publication.py` is a mandatory pre-push/release gate. Release packagers use explicit file maps instead of wildcard-copying the developer workspace.
