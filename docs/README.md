# ExactScope documentation map

Release context: **rc4 grounding implementation complete through pre-inference packaging/preregistration work; final source-bound benchmark-ready gate in progress after v1.0.0-rc.3 qualification closeout**
Date: 2026-09-06

This index separates active rc4 product/design authority from the retained quantitative subsystem and historical rc3 release/qualification records. rc3 artifacts and evidence are frozen. Do not interpret old rc3 qualification checklists or earlier rc4 model-interface implementation notes as instructions to keep changing product code.

## Start here — active rc4 grounding work

Read in this order:

1. [`PRODUCT_DIRECTION.md`](PRODUCT_DIRECTION.md) — flagship product objective, scope and decision test.
2. [`GROUNDING_ARCHITECTURE.md`](GROUNDING_ARCHITECTURE.md) — provider-neutral Source -> Provider -> Evidence Policy -> Grounding Frame architecture.
3. [`../spec/GROUNDING_CONTRACT_V0_1.md`](../spec/GROUNDING_CONTRACT_V0_1.md) — logical grounding contract, authority modes, provider identity, failure states and benchmark invariants.
4. [`BENCHMARK.md`](BENCHMARK.md) — A/G fairness, everyday workloads, false-grounding and wrong-confident-answer metrics.
5. [`AI_INTEGRATION.md`](AI_INTEGRATION.md) — integrator-facing prefetch/Grounding Frame contract plus secondary quantitative lanes.
6. [`../ROADMAP.md`](../ROADMAP.md) — current gate: final source-bound package, five zero-inference preregistrations and benchmark-ready freeze.
7. [`GROUNDING_EVALUATION_PACKAGE.md`](GROUNDING_EVALUATION_PACKAGE.md) — clean-room pre-inference package contents and boundary.
8. [`GROUNDING_BENCHMARK_HANDOFF.md`](GROUNDING_BENCHMARK_HANDOFF.md) — active instructions for the separate later A/G validation session.
9. [`ARCHITECTURE.md`](ARCHITECTURE.md) — combined grounding + deterministic quantitative system boundary.
10. [`DECISIONS.md`](DECISIONS.md) — binding decisions, especially D-067 through D-074.
11. [`CODEX_CONTEXT.md`](CODEX_CONTEXT.md) — current agent instructions and prototype/non-normative boundary.
12. [`../SECURITY.md`](../SECURITY.md) — grounding privacy, scope, provider and prompt-injection trust boundary.
13. [`RC3_QUALIFICATION_CLOSEOUT.md`](RC3_QUALIFICATION_CLOSEOUT.md) — immutable historical findings that motivated the pivot.

## Active supporting documents

These should follow the grounding-first authority above:

- [`QUICKSTART.md`](QUICKSTART.md) — distinguishes published rc3 quantitative assets from the implemented-but-not-yet-published rc4 grounding source candidate and pre-inference gate.
- [`INSTALLATION.md`](INSTALLATION.md) — source/provider/profile installation and lifecycle boundary; public rc3 quantitative packages remain separate.
- [`COMPATIBILITY.md`](COMPATIBILITY.md) — compatibility identities; grounding provider/source/policy identity is additional to ABI/runtime identity.
- [`EVALUATION_BUNDLE.md`](EVALUATION_BUNDLE.md) — frozen public rc3 quantitative bundle only.
- [`GROUNDING_EVALUATION_PACKAGE.md`](GROUNDING_EVALUATION_PACKAGE.md) — rc4 source-candidate clean-room/pre-inference evaluation package.
- [`NEXT_SESSION_PROMPT.md`](NEXT_SESSION_PROMPT.md) — current copy-paste instructions for the later rc4 A/G validation session.
- [`MARKETING_CLAIMS.md`](MARKETING_CLAIMS.md) — prohibits unmeasured rc4 accuracy/hallucination claims.
- [`COMMERCIALIZATION.md`](COMMERCIALIZATION.md) — grounding source/provider assurance and qualification first; quantitative domains secondary.
- [`RETROFIT_PRODUCT_STRATEGY.md`](RETROFIT_PRODUCT_STRATEGY.md) — consumer/OEM retrofit thesis.
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — current contribution priority; product changes must respect the frozen grounding semantics and candidate identity rules.

## Quantitative subsystem documents

These remain valid for `xs_calc` / `xs_eval` / specialization work but **do not define the flagship rc4 product path**:

- [`MODEL_INTERFACE_RC4.md`](MODEL_INTERFACE_RC4.md) — constrained/native model envelope for model-generated quantitative requests.
- [`CAPABILITY_PRODUCT_ARCHITECTURE.md`](CAPABILITY_PRODUCT_ARCHITECTURE.md) — quantitative capability unit and model/device budgets.
- [`CAPABILITY_COMPILER.md`](CAPABILITY_COMPILER.md) — quantitative capability/profile compiler.
- [`STATISTICS_CAPABILITY_SLICE.md`](STATISTICS_CAPABILITY_SLICE.md) — Statistics-specific selected slice.
- [`DOMAIN_EXPANSION.md`](DOMAIN_EXPANSION.md) — deferred academic/technical expansion guidance.
- [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) — implementation history and quantitative subsystem planning context.

Academic breadth is deferred until everyday grounding value is proven or a real customer workload requires a narrow deterministic method slice.

## Legacy/prototype grounding experiments — non-normative

The branch still contains earlier `RecallIndex`/fact-pack/`xs_recall` experiments because they are useful implementation/reference history. They do **not** define the current product contract. The current benchmark reference provider is implemented through the provider-neutral profile/runtime path described above.

Do not infer from the legacy/prototype files that the product requires:

- a model-visible `xs_recall` tool;
- one specific fact-pack schema;
- exact/alias lexical retrieval for every product;
- C ABI/Wasm recall exports in their prototype form.

The normative boundary is `GROUNDING_ARCHITECTURE.md` + `GROUNDING_CONTRACT_V0_1.md`; the concrete first benchmark reference profile is `../grounding/reference-profile-v0.1/`. Future providers may change retrieval implementation without changing the logical ProviderOutcome/GroundingFrame semantics.

## Historical rc3 procedure / release records

The following are intentionally retained for audit/reproducibility but are **closed**. Do not use them as instructions to resume rc3 validation:

- [`QUALIFICATION_HANDOFF.md`](QUALIFICATION_HANDOFF.md) — historical rc3 qualification procedure
- [`NEXT_AGENT_HANDOFF.md`](NEXT_AGENT_HANDOFF.md) — historical rc3 pre-qualification agent handoff
- [`../benchmarks/NEXT_MODEL_MATRIX.md`](../benchmarks/NEXT_MODEL_MATRIX.md)
- [`../benchmarks/README.md`](../benchmarks/README.md) where it describes the rc3 run procedure
- [`../RELEASE_NOTES_v1.0.0-rc.3.md`](../RELEASE_NOTES_v1.0.0-rc.3.md)

The actual rc3 five-model/install/chat-template findings are summarized in [`RC3_QUALIFICATION_CLOSEOUT.md`](RC3_QUALIFICATION_CLOSEOUT.md). Raw rc3 evidence remains outside this active design rewrite and must stay immutable.

## Older historical/design context

Historical revision names, measurements and planned phases are not current evidence unless an active document explicitly revalidates them:

- [`FIRST_IMPLEMENTATION_SLICE.md`](FIRST_IMPLEMENTATION_SLICE.md)
- historical `STATISTICS_R17_*_RESULT.md` documents
- [`REFERENCES.md`](REFERENCES.md)

## rc4 evidence identity rule

Grounding evidence belongs only to the exact combination of:

- source/content revision or digest;
- retrieval-provider implementation/index/preprocessing/ranking identity;
- embedding model/tokenizer/index identity when used;
- source scope and authority mode;
- freshness/revision/conflict/ambiguity policy;
- evidence top-k/byte/token budget;
- Grounding Frame serialization/policy bytes;
- model/runtime/generation settings;
- corpus/scorer identity.

Changing any behavior-affecting field creates a new evidence candidate. Do not copy rc3 quantitative scores or one grounding prototype result into a different rc4 candidate.

For the quantitative subsystem, model-facing prompt/grammar/tool/schema/operation/interface-selection/runtime changes likewise create a new candidate identity.

## Clean-source rule

The public source keeps reviewed source/specifications, generators, adapters, benchmark/preregistration tooling and historical interpretation documents. Mutable generated evidence/output directories remain separate from source authority.

Do not delete or rewrite frozen historical evidence merely to create a clean release. Prepare each future grounding candidate from a separate clean snapshot and bind its source/provider/policy/model identities to exact digests.
