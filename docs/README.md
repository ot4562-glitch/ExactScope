# ExactScope documentation map

Release context: **ExactScope v1.1.0 is a software/architecture release that retains the Linux x86-64 native grounding C ABI/XSGI path as the stable software surface. New v1.1 qualification/control-plane, host-integration, Bridge, enterprise DocQA and demo surfaces are experimental/reference. Physical ARM64 qualification, enterprise/customer qualification and demonstrated economic advantage remain explicitly unclaimed.**

Date: 2026-09-13

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

## v1.1 release and research surfaces — start here

v1.1.0 closes the indefinite research branch as a **software/architecture release**. Stable support is deliberately narrow: Linux x86-64 native grounding C ABI/XSGI. Qualification/control-plane workflows, host integrations, Bridge, enterprise DocQA and demos remain experimental/reference. Qwen/FEVER Stage 1 stopped at `ReferenceOnly`; the frozen NQ/Hotpot 20-model panel remained positive on average, while the later Kubernetes Operations long-document proxy failed its ordinary-RAG quality margin and selected no candidate. Successful automatic cost compilation, general RAG superiority, enterprise qualification and economic advantage are not claimed.

Release essentials: [`../RELEASE_NOTES_v1.1.0.md`](../RELEASE_NOTES_v1.1.0.md) defines the stability/support contract; [`V1_1_PUBLIC_PROXY_K8S_RESULT.md`](V1_1_PUBLIC_PROXY_K8S_RESULT.md) preserves the negative long-document transfer result and invalidated-run provenance.

1. [`V1_1_TECHNICAL_REVIEW.md`](V1_1_TECHNICAL_REVIEW.md) — **10-minute external reviewer path**: architecture thesis, executable conformance demo, machine-verifiable public evidence, backend-specific runtime evidence and exact claim boundary.
2. [`../benchmarks/v1.1-final-public-evidence.json`](../benchmarks/v1.1-final-public-evidence.json) — tracked frozen 20-model public-development evidence snapshot; verify with `python3 tools/verify_v11_public_evidence.py`.
3. [`V1_1_RESEARCH_STATUS.md`](V1_1_RESEARCH_STATUS.md) — **current continuity checkpoint** and active implementation order.
4. [`V1_1_ULTIMATE_PRODUCT_ARCHITECTURE.md`](V1_1_ULTIMATE_PRODUCT_ARCHITECTURE.md) — **frozen v1.1+ north star**: Qualified AI Execution Control Plane, Semantic Execution Policy Compiler kernel, immutable qualification artifacts, binding execution guard, drift/requalification and frontier-host path.
5. [`V1_1_AG_EFFECT_SHOWCASE.md`](V1_1_AG_EFFECT_SHOWCASE.md) — final public A/G results, real-host H1 three-arm checkpoint, freeze boundary and failure disclosures.
6. [`V1_1_ENTERPRISE_DOCQA_PLAN.md`](V1_1_ENTERPRISE_DOCQA_PLAN.md) — **current prospective product-proof protocol**: real host retrieval, competence gates, Base-vs-Integrated primary comparison, total economics and ordinary-alternative comparison.
7. [`V1_1_PRODUCT_DIFFERENTIATION.md`](V1_1_PRODUCT_DIFFERENTIATION.md) — current product/architecture definition, artifact boundary, evidence ladder, commercial wedge and unsupported-claim limits.
8. [`V1_1_STAGE1_REFERENCE_ONLY_RESULT.md`](V1_1_STAGE1_REFERENCE_ONLY_RESULT.md) — **completed FEVER Stage 1 result**: `ReferenceOnly`, held-out unconsumed, product qualification not evaluated.
9. [`V1_1_STAGE1_REFERENCE_ONLY_ASTRA_REVIEW.md`](V1_1_STAGE1_REFERENCE_ONLY_ASTRA_REVIEW.md) — independent post-result Astra review; narrows v1.1 and prioritizes enterprise document QA.
10. [`V1_1_STAGE1_PREREGISTRATION.md`](V1_1_STAGE1_PREREGISTRATION.md) — immutable historical pre-score contract for the stopped FEVER Stage 1; do not reinterpret it as the next study.
11. [`V1_1_EXPERIMENT_PROGRAM.md`](V1_1_EXPERIMENT_PROGRAM.md) — broader research charter; public benchmark-driven tuning is closed and enterprise document QA is the next empirical phase.
12. [`V1_1_AMPLIFIER_MATERIALS.md`](V1_1_AMPLIFIER_MATERIALS.md) — causal material registry; materials do not automatically become selectable product policy.
13. [`V1_1_PARASITE_ATTACH_PROFILE.md`](V1_1_PARASITE_ATTACH_PROFILE.md) — low-ownership host-attached architecture pressure test; not the product identity.
14. [`V1_1_RUNTIME_AMPLIFIER.md`](V1_1_RUNTIME_AMPLIFIER.md) — historical/material reference; runtime-amplifier terminology is not the product category.
15. [`RUNTIME_AMPLIFIER_LANDSCAPE.md`](RUNTIME_AMPLIFIER_LANDSCAPE.md) — adjacent runtime ownership and collision analysis; runtime mechanisms remain host-owned.
16. [`V1_1_INTEGRATION_FEEDBACK.md`](V1_1_INTEGRATION_FEEDBACK.md) — ORT GenAI, ExecuTorch and LiteRT-LM pressure-test findings; integration evidence is not cross-runtime transfer evidence.
17. [`UPSTREAM_VALIDATION_PLAN.md`](UPSTREAM_VALIDATION_PLAN.md) — parallel placement-gated external-validation track; upstream work must be independently useful and must not derail qualification.
18. [`V1_1_DIRECTION_REFRAME_ASTRA_REVIEW.md`](V1_1_DIRECTION_REFRAME_ASTRA_REVIEW.md) — earlier independent direction review before Stage 1 scoring.
19. [`V1_1_ASTRA_HIGH_REVIEW.md`](V1_1_ASTRA_HIGH_REVIEW.md) — earlier independent skeptical review after the first rejected transfer.
20. [`REFERENCES.md`](REFERENCES.md) — papers and runtime documentation used to derive hypotheses.
21. [`../adapters/bridge/README.md`](../adapters/bridge/README.md) — experimental bridge pressure tests across external runtime surfaces.

The historical sub-1-MiB native promotion target remains a useful **comparison checkpoint**, but it is neither an experiment admission limit nor a promise about the eventual v1.1 shipping form. v1.1 is native-free-first; future release gates must be chosen for the actual selected artifact and must report distribution bytes, dependencies, runtime payload, post-link contribution, resource cost, and integration effort separately.

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
