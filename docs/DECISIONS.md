# Architecture and product decisions

These decisions are binding for v0.1 unless a later decision explicitly supersedes them. Product sequencing is part of the architecture because model turns, integration friction, and qualification scope materially affect the value of a constrained-runtime component.

## Active decisions

| ID | Decision | Reason | Consequence |
|---|---|---|---|
| D-001 | ExactScope is an AI-consumed system component, not a human calculator product. | The value is deterministic execution inside another AI product. | No core GUI/chat/account/dashboard roadmap. |
| D-002 | The core is library-first and can operate fully offline. | Services/accounts/network enlarge coupling and qualification cost. | Native/Wasm artifacts are primary; servers are optional host adapters. |
| D-003 | Rust is the implementation language; C ABI and data/wire formats are the stable portability authority. | `no_std` safety without a Rust-only ecosystem requirement. | Other languages wrap the ABI and may not reimplement calculations. |
| D-004 | The minimum kernel is `#![no_std]` and allocator-free. | Predictable embedded/on-device memory. | Fused/static evaluation uses fixed or caller-owned storage. |
| D-005 | `wasm32v1-none` is the portable WebAssembly baseline. | WebAssembly 1.0, no `std`, no host imports. | No WASI/network/filesystem/thread requirement in the primary Wasm profile. |
| D-006 | AI-facing exact decimal values use canonical base-10 strings in Tiny JSON. | JSON numeric parsing can lose precision before the core receives the value. | Adapters preserve exact lexical values. |
| D-007 | Baseline calculation uses checked decimal/rational semantics rather than host binary float. | Reproducibility and explicit rounding. | Overflow/precision failures are typed; optional scientific profiles may come later. |
| D-009 | Materially different methods are separate operation keys. | Hidden method selection recreates hallucination risk. | Population/sample, midpoint/point, exact/approx remain explicit. |
| D-010 | Scope packs are data-only. | Native plugins enlarge portability/security surface. | Packs contain metadata, bounded programs/kernel IDs/indexes/tests, not executable code. |
| D-011 | The runtime has no general expression parser. | A general language increases footprint/security cost. | Build-time typed source compiles to a bounded non-Turing-complete VM/kernel metadata. |
| D-013 | Dynamic mode uses immutable caller-owned pack bytes and caller-provided arenas. | Explicit ownership/memory is required for constrained hosts. | No hidden allocation/update service. |
| D-014 | Compatibility requires conformance and runtime evidence, not compilation. | The product promise is predictable behavior. | Tier claims attach to immutable release artifacts. |
| D-015 | TinyWire uses deterministic CBOR; Tiny JSON remains a bounded model-facing exact-decimal format for scalar strings and vector arrays. | Compact typed transport and broad tool-call compatibility serve different boundaries. | Both map to the same core semantics; Tiny JSON keeps the 512-byte/64-leaf bound and does not carry explicit unit IDs. |
| D-016 | Semantic ambiguity and invalid input fail closed. | A guessed number defeats the product purpose. | Errors are stable and contain no plausible fallback number. |
| D-017 | Classification uses the unrounded internal result. | Display rounding must not alter category boundaries. | Classification remains deterministic/tested pack semantics. |
| D-018 | Locale support is optional adapter/data functionality. | Full multilingual normalization should not enlarge every minimum runtime. | Core discovery stays bounded; hosts may add locale layers. |
| D-019 | SIMD/CPU-specific acceleration is optional. | Correctness must work on small/old targets. | Scalar path is authoritative and remains fallback. |
| D-020 | HTTP/MCP are adapters, not runtime dependencies. | The core should not inherit server stacks. | Desktop/server interoperability can evolve independently. |
| D-021 | Stable IDs live in machine-readable registries. | Hand-copied identity tables drift. | Registry files remain the authoritative source for generated constants. |
| D-022 | Abort-only artifacts do not promise panic recovery. | Minimum no_std/Wasm builds cannot reliably recover from arbitrary panics. | Malformed input must be non-panicking; a panic/abort is a conformance defect. |
| D-023 | Fused Wasm uses an exported reserved-memory boundary and caller-owned regions. | Hidden allocators/mailboxes harm footprint and integration. | Hosts grow memory and pass aligned non-overlapping regions. |
| D-024 | **Direct `xs_eval` is the primary semantic-method hot path; `xs_find` is optional cold-path discovery.** | Mandatory discovery can add another model inference turn, latency, tokens, and energy. | Known/cached semantic operation keys call `xs_eval` directly; discovery results are digest/revision-bound and cached. |
| D-025 | **Products expose the smallest capability slice required by the target task families instead of the full catalog.** | Tiny models need low prompt/tool-selection cost, and raw operation count is not product value. | Hot-set generation remains an implementation mechanism; the deployed model surface is selected by task-family coverage and model/device budget. |
| D-026 | **Adapters may repair syntax/transport but not semantics.** | A strict core is useful only if common envelope mistakes can be normalized without moving calculation authority outward. | Envelope/whitespace/field normalization is allowed; unit/method/value guessing is forbidden. |
| D-027 | **Benchmark evidence precedes accuracy/latency/energy marketing claims.** | Deterministic arithmetic alone does not prove better end-to-end UX. | Compare model-only, `xs_calc`, semantic capability slice, combined path, and a larger-model reference where fair, with failure and resource breakdowns. |
| D-028 | **Native static C ABI and no-import Wasm are the primary v0.1 release profiles.** | Requiring every internal profile/platform to mature simultaneously delays proof of value. | Dynamic packs, dynamic discovery, and broader wrappers may remain Experimental without blocking focused v0.1. |
| D-029 | **One shared calculation semantics is mandatory; universal simultaneous Tier 1 parity is not.** | Semantic forks are dangerous, but profile breadth is a sequencing choice. | Any profile exposing an operation uses the shared evaluator/kernel; release scope may be narrower. |
| D-030 | **Offline is a product capability, not the market definition.** | Bounded/auditable execution is also useful in networked products. | Positioning includes wearables, mobile, industrial, private local AI, edge/cloud agents, and certifiable systems. |
| D-031 | **The OSS core is the adoption wedge; commercialization centers on maintained capability products and assurance.** | Permissive licensing does not prevent enterprise value from reviewed domain sources, profile engineering, qualification, benchmark evidence, and LTS. | No mandatory proprietary cloud calculation path is introduced. |
| D-032 | **A smaller benchmark-proven capability slice is preferred to catalog breadth.** | Operation count does not demonstrate adoption value. | Domain expansion follows measured task-family capability, weak-model usability, and marginal footprint evidence. |
| D-033 | **On-device AI capability retrofit is a long-term product/architecture target.** **Narrowed by D-089 for first commercial validation.** | Physically constrained or deployed devices may be unable to absorb a larger model without new hardware, while software can still be updated. | Preserve low-footprint/offline/host-owned-runtime constraints, but do not require the first compiler/customer proof to occur on physical edge hardware. |
| D-034 | **A bounded `xs_calc` plan is the generic arithmetic path.** | Current tiny-model tests indicate that model-side selection across semantic operations can dominate failure, while one constrained plan can express short multi-step arithmetic. | `xs_calc` is implemented as one compact 1-8 step tool; runtime semantic validation remains authoritative. |
| D-035 | **The first `xs_calc` plan is limited to 8 steps over add/sub/mul/div/powi/sqrt.** | Public FinQA/TAT-QA planning analysis showed short gold computations while boundedness preserves footprint and qualification simplicity. | Loops, arbitrary branches, variables, arbitrary functions, arbitrary expressions, and arbitrary code remain forbidden. |
| D-036 | **`xs_eval` remains a first-class semantic fast path.** | Method identity, units, sample/population choices, and reviewed domain contracts should not be flattened into generic arithmetic when semantic validation matters. | The product has a generic plan lane plus reviewed semantic-operation lane sharing one calculation core. |
| D-037 | **`xs_find` is cold/development infrastructure, not the main tiny-model serving path.** | Discovery can add selection error, prompt cost, latency, and turns. | Keep discovery for setup/exploration/binding, but ordinary retrofit use must not depend on it. |
| D-038 | **Footprint is a release KPI equal in importance to accuracy.** | The product loses its retrofit advantage if the support runtime grows toward the cost of a model/hardware upgrade. | Record binary/RAM/scratch growth; target no-import Wasm near <=128 KiB when practical, require explanation beyond 192 KiB, and explicit design review beyond 256 KiB. |
| D-039 | **Domain series share one runtime and separate source catalogs from deployed slices.** | Separate calculators/runtimes would multiply footprint, semantics, qualification, and integration cost; exposing every domain operation would also overload weak models. | Statistics/Economics/Finance/Physics/Engineering and later domains are reviewed source catalogs compiled/selected into small capability slices over the same core and ABI. |
| D-040 | **The flagship benchmark tests the hardware-upgrade alternative.** | The customer decision is often not calculator-vs-model but existing small model vs small model + retrofit vs larger model/new hardware. | Public evidence prioritizes 0.5B-3B model-only vs ExactScope, with larger-model reference arms and resource cost where fair/feasible. |
| D-041 | **The product unit is a capability/task family, not an operation count.** | A vendor can reimplement isolated formulas cheaply; product value is a measurable task family a weak model gains. | Profiles and benchmarks name task families separately from their selected operation list. |
| D-042 | **Every deployed capability slice has a model-difficulty budget as well as a device-footprint budget.** | A 100 KiB artifact can still be unusable if tool choice, prompt, schema, or generation burden overwhelms a 0.5B-1B model. | Track model-visible tools/operations, prompt/schema/grammar size, generated request tokens, turns, valid/accepted call rate, selection, extraction, and fidelity. |
| D-043 | **Capability density and Capability Recovery Ratio are first-class evidence concepts.** | The strategic alternative is often a larger model/newer device, so raw accuracy and binary size alone do not describe the engineering trade. | Publish raw uplift and wrong-number reduction beside bytes/RAM/tokens/latency/energy; report CRR only where a larger-model reference meaningfully outperforms the small baseline. |
| D-044 | **The long-term build product is a deterministic capability compiler/profile generator.** | The defensible build-vs-buy value is maintained weak-model interfaces, reviewed semantics, footprint engineering, evidence, and qualification—not formula secrecy. | Build tooling should turn domain sources + target task/model/device budgets into minimal immutable runtime/model-surface artifacts, manifests, conformance inputs, and evidence bindings. |
| D-045 | **Constrained ExactScope request JSON/GBNF is the universal AI-facing compatibility baseline.** | rc3 showed that native tool-call support is chat-template/runtime dependent and can disappear even on a larger model. | Every AI-facing capability binds a short constrained prompt and request grammar to the same semantic/runtime identity. |
| D-046 | **Native tool calls are an optional envelope selected only from pre-inference runtime capability metadata.** | Tool definitions are useful when genuinely supported, but must not be a universal product dependency. | `auto` may choose `native_tools` only when tool definitions, assistant tool calls, and object arguments are proven; otherwise it chooses `constrained_json`. |
| D-047 | **There is no post-output envelope fallback or semantic retry.** | Retrying after seeing a malformed/wrong model output can hide failure, bias benchmark results, and become semantic repair. | The envelope is frozen before inference; malformed/invalid output remains a measured failure. |
| D-048 | **The model is responsible for intent/lane/operation selection and exact argument extraction, not supported deterministic arithmetic.** | The deterministic core is strongest after a valid request reaches it; making a weak model re-compute the same arithmetic wastes tokens and reintroduces numeric hallucination. | Accepted ExactScope results are authoritative for supported tasks; rendering may remain model/host-side without recomputation. |
| D-049 | **Model-interface efficiency is a release KPI.** | rc3 native tool serialization increased prompt tokens by several times on tested Qwen surfaces. | Report correctness uplift together with added input tokens, model-surface bytes, and model-latency milliseconds; optimize the smallest realistic slice rather than maximum tool use. |
| D-050 | **Academic/technical expansion adds reviewed domain source catalogs and task-family slices, not per-discipline runtimes.** | Separate calculators would duplicate semantics, footprint, adapters and qualification while broad model-visible catalogs would overload small models. | New domains enter through `domain-descriptors.json`, reviewed semantic sources, task-family maps and implementation bindings over the shared core/compiler. |
| D-051 | **Finance is the preferred next new domain after rc4 interface hardening; Physics/Engineering require a stronger units/dimensions/constants foundation first.** | Finance has high-value convention-explicit decimal tasks that fit current semantics, while scientific/engineering formulas become unsafe if unit/dimension assumptions are left to the model. | **Priority narrowed by D-067:** domain order remains valid if/when expansion resumes, but new academic breadth is not a current rc4 objective. |
| D-067 | **Everyday factual grounding and hallucination reduction supersede academic-domain expansion as the flagship rc4 product objective.** | Academic tool calls are relatively infrequent for consumer/embedded assistants; everyday factual accuracy and unsupported-answer reduction are broader adoption value. | Statistics/Economics/Finance/Physics work becomes secondary. Product docs, benchmarks and packaging prioritize grounding first. |
| D-068 | **Original-question prefetch is the default grounding path; model-generated retrieval/tool calls are optional fallbacks.** | Mandatory tool calls add turns, tokens, chat-template dependency and model selection failure. | Normal A/G benchmarks keep one model answer call per arm; rewrite/tool paths are separate ablations. |
| D-069 | **Grounding is provider-neutral and standardized at the Evidence/Grounding Frame boundary.** | Exact aliases alone are too narrow for general consumer use, while hard-wiring embeddings or one search stack would destroy portability. | Exact/lexical/BM25-like/vector/application/network providers may all map into one logical Grounding Contract with frozen provider identity. |
| D-070 | **Authority is assigned per factual target/source binding as `authoritative` or `supplemental`; providers and evidence never self-declare authority.** | The same source can be authoritative for one product claim and merely supplemental for another, and provider-supplied authority would be a trust-boundary violation. | Each TargetPlan carries host/profile authority and explicit provider/source bindings; unresolved authoritative targets cannot be filled by supplemental evidence or model memory. |
| D-071 | **False grounding is a first-class failure and may be worse than no grounding.** | Wrong injected evidence can make a small model confidently incorrect. | Evidence Policy prefers precision under authority, exposes `none/ambiguous/conflict/unavailable` distinctly and reports false-grounding rate. |
| D-072 | **The flagship benchmark compares model-only A with one-call grounded-prefetch G.** | Extra inference/tool turns can fake capability uplift and confound cost attribution. | A and G use the same answer-generation call count and sampling/output budget; added evidence tokens/latency are measured explicitly. |
| D-073 | **Model context receives a deterministic compact Model Projection, not retrieval internals.** | Similarity scores, vectors, provider catalogs and access metadata waste scarce context and can confuse or leak data to small models. | Projection preserves per-target meaning/authority/state/evidence while provider scores, security scope, indexes and audit details remain host-side; renderer bytes are candidate identity. |
| D-074 | **Grounding provider/source scope and privacy are host-enforced before retrieval.** | Private memory may be more sensitive than model weights and must not leak across users or to remote providers. | Requests/providers/caches remain bound to effective security scope; no implicit cross-user/tenant reuse; network use of private query/evidence is explicit policy. |
| D-075 | **Grounding state is target-group scoped, never one global frame truth bit.** | Compound questions and mixed authority require independent claim coverage. | GroundingFrame contains groups keyed by stable `target_key`; one unresolved authoritative target does not make unrelated supplemental claims authoritative or force blanket abstention. |
| D-076 | **Authoritative `none` requires completed or profile-defined sufficient authoritative coverage.** | Timeout, denial, provider error, budget exhaustion or partial search is not evidence that an authoritative fact is absent. | Required-provider coverage is explicit; incomplete required coverage becomes `unavailable` unless a frozen sufficiency rule proves the completed subset sufficient. |
| D-077 | **Provider outcomes and cross-provider merge are deterministic and identity-bound.** | Async completion order and incomparable raw relevance scores can silently change evidence. | ProviderOutcome preserves typed status; profile freezes source priority, dedup, merge, ordering, tie-break and score calibration if any; completion order is irrelevant. |
| D-078 | **Evidence is scoped untrusted data with stable content/provenance identity.** | Retrieved text can contain prompt injection or stale/misidentified content. | Evidence Items bind source/item/revision and canonical content identity; security scope remains host-side; evidence cannot grant permissions or authority; injection resistance is tested, not assumed from delimiters. |
| D-079 | **Benchmark serving inputs are physically/logically isolated from scorer gold.** | Expected target/source/evidence labels can turn routing/retrieval into an oracle and manufacture uplift. | Flagship G may read only production-visible question/context/profile/sources; expected answers/target/source/evidence/provider labels remain scorer-side, while oracle routing is a separately labeled diagnostic only. |
| D-080 | **v1.1 exploration budget is distinct from its release-promotion budget.** | A sub-1-MiB admission rule can prevent discovery of a larger intermediate combination whose causal core can later be distilled. | Experimental modules may temporarily exceed release bytes/CPU/RAM/token targets; the winning behavior must later be lightweighted and freshly qualified before promotion. |
| D-081 | **Aggressive v1.1 mechanisms are mounted as removable amplifier-rack modules and evaluated for interaction.** | Individually small gains can be superadditive or antagonistic when retrieval, projection, answer contracts and runtime acceleration change each other's operating conditions. | Record isolated effects, important pairs/neighborhoods, interaction terms, item-level phase transitions and leave-one-out loss before collapsing a winning path. |
| D-082 | **Inference ownership stays with the selected host runtime.** | llama.cpp, ONNX Runtime GenAI, vLLM, TensorRT-LLM, ExecuTorch, LiteRT-LM and future engines already specialize model graphs, tokenization, schedulers, KV state and accelerators. | ExactScope owns portable pre/post-generation decisions and hints; it does not grow a competing inference engine or hardware scheduler. |
| D-083 | **ExactScope Bridge is an experimental integration pressure test, not a second product core.** | A real external runtime reveals whether the delivery API is genuinely portable before v1.1 freezes, while copying grounding logic into adapters would create semantic forks. | Bridge adapters receive one `complete | generate` decision, never reconstruct authority/evidence, keep vendor API churn local, and make no upstream PR until the boundary is proven. |
| D-084 | **Repeated cross-runtime friction may justify a v1.1 public delivery/finalization API; one backend quirk may not.** | Freezing a native ABI from a single llama.cpp integration risks encoding provider-specific assumptions. | Record pressure-test findings in `V1_1_INTEGRATION_FEEDBACK.md`; settle semantic delivery/finalization before broad ABI freeze, while backend cache/guidance/speculation knobs remain adapter-owned. |
| D-085 | **The current Harness Distillation compiler objective is reference-preserving cost reduction, not general Pareto/expected-quality optimization.** | The first fresh transfer selected a cheaper 3/6 calibration-tied policy that fell to 2/6 while the predeclared reference scored 3/6 on held-out. Aggregate equality did not justify a cost tie-break. | Freeze Base `B`, predeclared competent reference `F`, scorer, policy definitions, total-cost function and selection rule before scoring; a candidate must preserve every observed `F` calibration success and be strictly cheaper than `F`. |
| D-086 | **`ReferenceOnly(F)` is a valid operational outcome but not evidence that compiler selection creates value.** | A good fixed intervention may be useful even when no cheaper preserving candidate exists; counting that as distillation would conflate intervention value with compiler value. | Compiler-value claims require a distinct `CompiledCandidate(P)` that is cheaper than `F`, preserves `F` on calibration, and survives independent fresh held-out qualification. |
| D-087 | **Held-out qualification may only qualify or reject the frozen candidate; it may not reselect, substitute the reference, relax thresholds, or extend the sample after scoring begins.** | Qualification must remain independent of calibration selection and resistant to outcome-driven repair. | Any outcome-motivated selector/threshold change contaminates that held-out for validating the change; a new fresh set is required. |
| D-088 | **The next substantive compiler proof uses a materially larger preregistered fresh sample.** | The first 6+6 run was useful for experiment integrity but is too small to validate selection among ten policies. | Current target is 120 fresh calibration claims (40/FEVER label) plus 600 fresh held-out claims, with selector-development items and near-duplicate/shared-evidence groups excluded prospectively. |
| D-089 | **The first commercial validation wedge is high-volume bounded enterprise document QA on a pinned/expensive-to-change model.** | It provides auditable authoritative evidence, measurable serving economics, a competent incumbent baseline, and enough repeated traffic to amortize calibration. | On-device/embedded retrofit remains a long-term market and architecture constraint, but is no longer the only or automatic first commercial proof. |
| D-090 | **v1.1 is native-free by default until native code demonstrates incremental necessity.** | Current evidence supports a small semantic boundary but does not show that an ExactScope native kernel materially improves end-to-end outcomes or deployment burden. | Keep stable-v1 native guarantees intact; require a Python-free host need or measured bottleneck/integration advantage before making native code mandatory for v1.1. |
| D-091 | **The next 120/600 compiler-value study uses preregistered practical gates rather than post-hoc significance language.** | The first 6+6 transfer was too small for substantive selection validation, and outcome-dependent margins would recreate the same overfitting problem at a larger scale. | With exact one-sided finite-population paired bounds (`alpha=0.05/3` per bound), require `Lower(g)-Upper(b) >= 3pp`, `Upper(r) <= 2pp`, at least 15% serving-cost reduction versus `F`, no serving-cost increase versus Base, p95 latency <= +5% versus Base, and zero mandatory safety/identity/observation/model-call violations; inconclusive bounds fail qualification. |
| D-092 | **v1.1 uses three distinct layers: Semantic Inference Policy Compiler internally, Qualified Execution Profile externally, and Reference-Preserving Cost Reduction as the first Stage 1 algorithm.** | Earlier amplifier/compiler language overloaded architecture, product, and one provisional selector, making a narrow tuning algorithm look like the whole category claim. | Treat the compiler as an internal hypothesis, the qualified profile as the proposed customer deliverable, and the reference-preserving selector as replaceable if fresh evidence favors another prospectively declared objective. Do not market a new category yet. |
| D-093 | **A candidate policy and its qualification evidence are separate immutable artifacts.** | Mutating a profile from unqualified to qualified blurs what was selected before held-out and permits accidental evidence/artifact mismatch. | Freeze an immutable Candidate Execution Policy before held-out; emit a separate Qualification Attestation that references its exact digest. The customer-facing Qualified Execution Profile is the qualified pair. Request-specific evidence/proof belongs in a separate receipt. |
| D-094 | **Stage 1 includes a conventional aggregate quality-constrained tuner `T` from the same calibration matrix.** | A paired-preservation selector may be useful but is algorithmically easy to reproduce; without a competent conventional comparator, a successful policy could be ordinary catalog tuning rather than ExactScope-specific value. | `T` uses the same catalog, observations, serving-cost model and mandatory gates; require `S[p] >= S[F]` and strict cost reduction, choose deterministically by cost/success/canonical ID, otherwise `T=F`. `T` never rescues a failed `P`. |
| D-095 | **Stage 1 held-out is a simple-random sample without replacement from a frozen finite representative frame, not a label-balanced FEVER split.** | Balanced calibration is useful for search, but a forced-balanced held-out changes the estimand and does not match the exact finite-population interpretation accepted for the product gates. | Keep calibration at 40 per FEVER label; freeze post-exclusion grouping/frame identity and draw held-out label-independently. Generate and commit the sampling seed before inspecting the realized sample and record its provenance to prevent seed shopping. Record realized labels descriptively. If another sample design is used, preregister its design-based analysis before scoring. |
| D-096 | **The 600 held-out count is a prospective target subject to an exact pre-score precision/power preflight.** | Six hundred observations are not automatically sufficient for conservative paired gain/loss bounds on every finite frame. | Before any fresh model score, verify the exact bound behavior for the actual frame and plausible disagreement scenarios. If 600 is inadequate, change sample size only before scoring and freeze it; never extend after outcomes are visible. |
| D-097 | **Base `B` and Reference `F` need pre-score competence evidence beyond `S[F] > 0` and `S[F] >= S[B]`.** | Those empirical checks can admit commercially useless baselines and make a weak control manufacture apparent value. | Freeze design competence and a task-specific absolute utility floor using only pre-existing evidence. If no defensible floor exists before fresh Stage 1 outcomes, classify the study as algorithm diagnostic only rather than drawing product inference. |
| D-098 | **The minimum v1.1 semantic center is evidence sufficiency/context admission plus answer-contract lowering/finalization.** | Cache, speculation, runtime adapters, broad zero-call routing, and performance knobs collide with host/runtime ownership and can make ExactScope look like a miscellaneous feature rack. | Keep retrieval/inference/cache/decoding execution host-owned. Permit proof-based `Complete` only with a sound registered verifier. Add optional host capabilities only when a workload hypothesis and measured economics require them. |
| D-099 | **The evidence ladder is Stage 1 within-workload selection, Stage 2 customer-like real retrieval, then Stage 3 prospective prior transfer.** | A FEVER pass cannot establish real-retrieval economics, cross-runtime value, or a compounding knowledge asset. | A valid Stage 1 pass moves directly to bounded enterprise document QA with competent incumbent/generic-tuner/better-model comparisons. Only after customer-like value should source-derived priors be tested against cold search on untouched host/workload combinations under the same final qualification gate. |
| D-100 | **The candidate moat is prospective search/qualification reduction, not profile size, selector code, adapter count, or runtime wrapping.** | Adjacent systems can copy a frozen config exporter, constrained selector, validator, or adapter. A real compounding asset would have to improve future qualification before target outcomes are known. | Record workload/capability/policy/intervention vectors plus positive, negative and inconclusive fresh outcomes. Test whether prior-informed search reduces candidate executions or calibration labels by a material amount (initial hypothesis >=30%) without weakening final qualification or omitting hard targets. |
| D-101 | **Stage 1 reports three separate verdicts: narrow selector transfer, full product qualification, and descriptive incremental-selector comparison against `T`.** | Astra explicitly separated these questions; collapsing them would let a small cost reduction or an ordinary-tuner outcome masquerade as full product success. | The narrow verdict requires fresh Reference tolerance, strict held-out cost reduction versus `F`, and zero mandatory violations. The full product verdict additionally applies all Base-relative/15%-cost/p95 gates. `P` versus `T` remains descriptive unless a separate inferential comparison is frozen; calibration stop outcomes consume no held-out. |
| D-102 | **The preregistered Qwen/FEVER Stage 1 is closed at `ReferenceOnly`, not repaired.** | All 1,200 calibration observations completed, but no cheaper frozen candidate matched the Reference's 52/120 aggregate successes and none preserved all Reference successes; the conventional tuner also returned `T=F`. | Keep `P=null`, leave the 600-item held-out unscored, preserve the frozen 15% cheaper-reference requirement, and record the result as algorithm-diagnostic negative-frontier evidence rather than compiler value. |
| D-103 | **The sealed FEVER 600 is retired from revised-rule confirmatory inference.** | Calibration results and the `ReferenceOnly` stop have now influenced strategy; using the same held-out for a new selector, F/T-only rescue, threshold change, or policy family would invalidate independence. | Preserve the artifact for audit/reproducibility only. Any revised policy/objective needing confirmation must use genuinely fresh grouped data. |
| D-104 | **v1.1 is currently a qualification/configuration optimizer; Semantic Inference Policy Compiler is research-only.** | Two fresh FEVER attempts established fail-closed selection/qualification behavior but did not demonstrate a useful cheaper compiled policy, category distinctness, transfer, or a compounding prior. | Product/docs may describe semantic enforcement, explicit stop outcomes, immutable candidate/attestation identities, and qualified profiles. Do not market an earned compiler category or moat until prospective transfer evidence exists. |
| D-105 | **The next product proof is competence-gated bounded enterprise document QA with real host retrieval, using Integrated-vs-Base as the primary question.** | FEVER's oracle-page-pooled task had no defensible absolute product competence floor; a customer-like workload is needed to test useful quality, evidence support, abstention and total economics. | Freeze workload-owner competence/error gates, real retrieval identities, leakage groups, Base/Integrated configs, scorer/adjudication, timing/load, total economics and inference/sample rules before confirmatory scoring. A cheaper `P/T` branch is optional and separately preregistered. |
| D-106 | **Enterprise DocQA preregistration uses canonical integer thresholds with explicit units and fails closed on placeholders/unapproved economics.** | ExactScope canonical JSON rejects floating-point numbers, and ambiguous decimals/placeholder business rules would recreate outcome flexibility across languages and tools. | Store rates/materiality as integer units such as basis points/ppm/counts, require owner approval, reject `TBD/TODO/FIXME/PLACEHOLDER`, oracle retrieval, hidden answer repair/judges, overlapping partitions, missing source bindings, and unfrozen confirmatory rules. |
| D-107 | **The frozen v1.1+ north star is Qualified AI Execution Control Plane, with Semantic Execution Policy Compiler as the technical kernel and Qualification/Configuration Optimizer as the first commercial slice.** | The narrower current product has a credible customer wedge, while the same immutable artifacts can later govern frontier-model reasoning/context/tool economics without taking over inference ownership. | Implement north-star-compatible artifacts now, but market only the evidence-backed slice. The deployable primitive remains Candidate Execution Policy + Qualification Attestation = Qualified Execution Profile. |
| D-108 | **A supported control-plane integration requires binding host admission and finalization; advisory metadata is not enough.** | Host ownership of inference/fallback means a guard cannot block stale/unqualified execution unless the integration contract makes it mandatory. | Bind admission receipts to profile/evidence/rendered-request/settings identities; require finalization before qualified release; route fallback through separately authorized paths; fail receipt reuse/settings drift/stale identities closed. |
| D-109 | **Runtime-verifiable obligations and empirically qualified properties are distinct.** | Schema/citation/capability checks can be deterministic, while factual correctness, semantic entailment and customer economics are population properties. Conflating them would turn prompt instructions into false proofs. | Unsupported hard obligations fail compilation. `Accept` means implemented deterministic checks passed, not universal semantic truth. Preserve `none` vs `unavailable` under lowering. |
| D-110 | **Qualification validity distinguishes inspectable pinned hosts from provider-observable opaque frontier hosts.** | Public APIs may not expose stable internal runtime/tokenizer identities even when model IDs remain unchanged. Exact local identity requirements would either exclude frontier providers or encourage false precision. | Record each dependency as pinned/host-asserted/provider-guaranteed/unknown; add validity windows/observation-triggered invalidation for opaque providers; model-tier changes create new candidates; use targeted corpus requalification only under prospectively defined dependency rules. |
| D-111 | **Qualified customer utility and total economics are the universal v1.1 feature gate; same-model amplification and cheaper-reference compilation are conditional modes.** | PRODUCT_DIRECTION previously treated reference-preserving cost reduction as universal even though the enterprise plan and north star allow stronger-model/simple-config winners. | Require one competent ordinary alternative in commercial proof and allow `UseTheBetterModelInstead`. Same-model v1-vs-v1.1 amplification remains a required live diagnostic, not a universal deployment condition. |
| D-112 | **Single-hop precision and multi-hop coverage are separate fixed workload-policy candidates; no per-query adaptive router is authorized.** | The same-model attached diagnostic improved NQ under precision compression but regressed Hotpot, and fresh Hotpot development showed precision 2K retained all support titles on only 56.25% versus 78.125% for the coverage 3K candidate. | Keep `precision-context-v5` as the single-hop regression anchor and carry `multihop-coverage-v1` only for workloads whose contract prospectively requires multi-source composition. Dataset names must not become production routing rules. |
| D-113 | **`multihop-coverage-v1` advances only as a candidate after fresh untouched validation, not as the universal v1.1 default.** | On pre-frozen Hotpot validation32, the development-frozen coverage 3K policy improved F1 by 6.82 pp over current precision and restored all-support projection from 46.875% to 93.75%, but used 53% more input tokens and ~10% more model service time. | Run stable v1 r25 versus the frozen coverage winner on another untouched cohort, protect NQ precision in parallel, and only then encode a restricted evidence-composition requirement in Workload Contract / Candidate Policy. |
| D-114 | **Proof-minimal surface negotiation accounting is validated against the persisted negotiation record, not the total candidate-surface count.** | v1.1 stops after the first supported structured-output surface, but public scorers still assumed every candidate surface was probed and blocked valid frozen outputs. | NQ/Hotpot/FEVER verifiers compare request and attempt counts to `negotiation.model_request_count`; serving outputs are never rerun merely to satisfy the obsolete full-sweep assumption. |
| D-115 | **The frozen multi-hop coverage policy survives direct stable-v1 comparison and is promoted into the restricted compile-time contract surface.** | On the next untouched Hotpot32 from the original seed order, `coverage-3k-cap12` matched stable v1 support coverage (81.25% all / 96.875% any), improved F1 by 6.22 pp and EM by 6.25 pp, and used 16.3% fewer input tokens / 21.9% fewer evidence bytes, although local model service time was ~21% higher. | Add `evidence_composition` to Workload Contract/Candidate Policy with `single-source-precision`, `multi-source-coverage`, and backward-compatible `unspecified`; fail compilation when known composition and evidence-policy IDs conflict; keep NQ precision regression protection before broader promotion. |
| D-116 | **The 2 KiB single-source precision cap is retired as the active candidate after a fresh stable-v1 regression.** | On a new untouched NQ32, v1.1 precision-2K lost 3.36 pp F1 and 3.125 pp EM versus stable v1 while cutting answer-bearing projection by 12.5 pp. The same run still amplified over its own model-only arm and reduced context substantially, so the failure is a budget/coverage boundary rather than loss of the entire semantic path. | Seal that NQ32 after scoring; do not tune on it. Keep `precision-context-v5` semantics but develop a new bounded budget only on the separately pre-frozen NQ64. |
| D-117 | **The active single-source candidate is `precision-context-v5` at 3,072 bytes / cap8, and evidence budget is part of the compiled workload policy.** | Pre-frozen NQ development32 selected 3K/cap8 as the smallest candidate reaching the best observed answer-bearing projection; untouched validation32 improved F1 by 8.47 pp over 2K. On another untouched NQ32, frozen 3K matched stable-v1 EM, improved F1 by 1.63 pp, and used 28.7% fewer input tokens / 37.2% fewer evidence bytes, while local model service time was ~19% higher. | Public NQ development harness defaults to 3K/cap8. Workload Contract/Candidate Policy may record `evidence_budget_bytes`; known evidence-composition policies require an explicit budget. Current validated fixed pair is single-source precision 3K/cap8 and multi-source coverage 3K/cap12; neither authorizes request-time adaptive routing. |
| D-118 | **Enterprise confirmatory execution must include a competent ordinary deployable alternative outside ExactScope.** | A Base-vs-Integrated-only study can show a local improvement while still hiding that a simpler fixed configuration or ordinary customer tooling is cheaper or equally effective. | Freeze the alternative before confirmatory outcomes, require development eligibility, same frozen retrieval boundary, no ExactScope dependency, and a distinct configuration identity. If the ordinary alternative wins deployable total economics, report that rather than redefining success. |
| D-119 | **Executable economics and non-serving fixed costs are frozen before outcomes in the Study Contract, not supplied by the run after scoring.** | Integration, qualification, refresh and maintenance costs can dominate small serving gains; allowing a run manifest to choose those counters after outcomes would make total economics outcome-flexible. | Economic components must name executable counters with integer coefficients. Base/Integrated fixed counters come from the frozen economics record; the ordinary alternative carries its own frozen fixed counters. The run manifest must copy the Study Contract counters exactly or fail integrity validation. |
| D-120 | **Enterprise scoring gate pass is not qualification.** | Deterministic scoring can establish that observed metrics meet frozen gates, but statistical uncertainty, ordinary-alternative comparison, total economics and workload-owner acceptance are separate empirical/business decisions. | `enterprise_docqa_score.py` emits at most `GATES_PASSED_CANDIDATE` and never a Qualified Execution Profile. A separate immutable decision binds the exact score, frozen analysis implementation/report and owner decision; only a full pass becomes eligible to construct the generic Qualification Attestation. |
| D-121 | **Runner, readiness, scorer, statistical-analysis and qualification-decision implementations are all frozen by digest before confirmatory outcomes.** | Freezing thresholds while leaving executable launch/scoring/analysis/decision code mutable still permits favorable post-result interpretation. | The Study Contract binds runner/readiness/scorer/analysis/decision source SHA-256 identities. Readiness must execute the exact frozen implementation; analysis reports must bind the exact frozen analysis record and source digest; decision execution must match its frozen source digest; source drift or post-score rule changes fail closed. |
| D-122 | **The exact Candidate Execution Policy, Workload Contract and Host Capability Manifest are frozen in the Study Contract before confirmatory outcomes.** | Allowing a successful benchmark result to be attached afterward to a different candidate/workload/host artifact would sever the empirical proof from the deployable behavior it supposedly qualified. | `enterprise_docqa_study_contract.py` validates the generic north-star artifacts before execution and records their canonical digests as the Integrated binding. Later observation, decision and attestation stages may only reference that exact binding; post-result candidate substitution fails closed. |
| D-123 | **A qualified enterprise decision still does not emit a Qualified Execution Profile; generic attestation gates are recomputed first.** | Enterprise score/analysis/owner approval and the generic Workload Contract empirical requirements are related but distinct integrity layers. Treating a business-study decision as the deployable profile would bypass the generic qualification semantics. | `enterprise_docqa_attest.py` accepts only a fully qualified decision bound to the frozen Study Contract, remaps Integrated score metrics to every Workload Contract empirical requirement, invokes `qualified_execution.validate_attestation()`, and emits a validated bridge plus an optional standalone Qualification Attestation, never a profile. Qualified Execution Profile construction remains the separate final generic artifact step. |
| D-124 | **Enterprise attestation evidence binds a canonical evaluation package; a score file is not allowed to masquerade as the package.** | A score digest alone omits the preregistration, Study Contract, raw-run identities, adjudications, analysis, owner/qualification decisions and exact north-star artifact identities needed to audit why an attestation exists. | `enterprise_docqa_attest.py` constructs a canonical evaluation-package record over those frozen digests, places its digest in the generic Qualification Attestation, and can emit that attestation standalone. `qualified_execution.py make-profile` is the generic final constructor and revalidates Candidate + Attestation + Workload + Host before emitting a Qualified Execution Profile. |
| D-125 | **The runner-visible confirmatory question set is frozen by digest in the Study Contract before the first confirmatory model call.** | Freezing only the planned sample size still permits a different same-sized question set to be substituted after the Study Contract exists, which breaks prospective sampling and makes the run identity outcome-flexible. | `enterprise_docqa_study_contract.py` validates canonical gold-free question JSONL, unique item/group identities and the preregistered sample count, then records `questions_sha256` and the exact count. Observation, decision and attestation stages require that frozen identity; the run manifest alone is not sufficient to establish prospective sample identity. |
| D-126 | **No enterprise confirmatory execution is authorized until a fail-closed readiness preflight revalidates the complete frozen bundle.** | Independently valid files can still form an inconsistent execution bundle if a question set, source implementation, ordinary alternative, Candidate/Workload/Host binding, fixed-cost record or output destination drifts between freeze and launch. | `enterprise_docqa_readiness.py` performs no retrieval or model inference. It revalidates the preregistration semantics, exact Study Contract, frozen question digest/count, ordinary alternative, generic north-star artifacts, runner/readiness/scorer/analysis/decision source digests, evidence/fixed-cost identities and no-resume output condition. Only `READY_FOR_CONFIRMATORY_EXECUTION` authorizes the host-owned runner to begin the first model call. |
| D-127 | **The readiness receipt is part of the confirmatory run identity, not an advisory preflight log.** | A host could otherwise run the same frozen study without executing the readiness gate, then hand-author a plausible run manifest after outcomes. | Every observation carries the exact readiness-report SHA-256. `enterprise_docqa_observations.py --seal-run-output ...` validates the complete observation matrix against that receipt and deterministically emits the run manifest from frozen identities and counters. Score and analysis carry the same readiness digest, and the canonical evaluation package exposes it explicitly. |
| D-128 | **Astra is a consequence-based senior review gate, not the routine implementation agent.** | Requiring the strongest reviewer for ordinary implementation wastes review bandwidth, while omitting it at irreversible evidence/trust/publication boundaries increases the chance of freezing a bad direction. A 2026-09-13 read-only `gpt-6-astra` review judged this cadence sound and added evidence-integrity, waiver, blast-radius and cumulative-small-change triggers. | ChatGPT + CodexPro Local handle approved implementation/tests/docs/reversible isolated work. Require Astra review before commitment when changing success criteria/methodology, evidence eligibility/leakage/provenance/stopping rules, frozen architecture/security/authority boundaries, authorizing the first real enterprise confirmatory execution, consequentially disposing major evidence/defaults, approving a release/material public claim, waiving frozen controls, or making an irreversible/expensive dependency/deployment commitment. Astra advises; the accountable human/project owner retains final go/no-go authority. |
| D-129 | **The readiness `confirmatory_run_output` is the frozen artifact root for the confirmatory execution.** | A valid readiness receipt could otherwise be reused while observations or a sealed run manifest are written somewhere unrelated, weakening the no-resume/output-destination guarantee and making run provenance unnecessarily ambiguous. | Observation validation and `--seal-run-output` require both `observations.jsonl` and the run-manifest file to resolve strictly below the absolute run root recorded by the readiness receipt. Artifacts outside that root fail closed even when their content digests are otherwise valid. |
| D-130 | **`host-ranked-hybrid-h1-v0` is frozen as the Hotpot/LlamaIndex public-development attach candidate; public Hotpot tuning stops before the final 20-model panel.** | After the initial host-attached shaping loss was isolated, H1 was selected on an already-open diagnostic cohort, then frozen before an untouched validation32 and a predeclared stability64. Stability64 passed every declared development competence gate and observed H1 over ordinary RAG at +5.66 pp F1 / +7.81 pp EM while using fewer evidence bytes/input tokens; uncertainty still crosses zero. A read-only GPT-6 Astra consequence review on 2026-09-13 returned `APPROVE WITH CONDITIONS`, and the project owner explicitly directed continuation through the final panel. | No further Hotpot policy tuning is allowed from public panel outcomes. The final robustness panel may reuse stability64 for descriptive cross-model Hotpot A/G, must disclose that Qwen's stability64 result was already known, and must preserve every scheduled model including regressions and reason-coded N/A. This is public-development robustness evidence only, not superiority, enterprise qualification, production readiness, or economic/latency proof. |
| D-131 | **The final v1.1 publication robustness panel is a frozen 20-model, two-workload A/G panel run only after policy freeze.** | The older `v11-full-20-model-20260911-serial` predates the final 3 KiB NQ policy and H1 real-host policy and includes retired FEVER, so its results cannot represent the final v1.1 behavior. | Reuse the frozen v1 20-model identity and historical Public-6 macro without rerunning it. Run fresh post-freeze NQ64 with `precision-context-v5` 3072B/cap8 and Hotpot stability64 with frozen LlamaIndex BM25 top-12 + H1. Attempt each model once, no quality retry/hidden repair, score only after serving, keep N/A distinct from zero, compute descriptive averages over valid paired results with denominators, and do not use panel outcomes to alter the frozen policies. FEVER is excluded. |
| D-132 | **The public v1.1 review surface is evidence-first and comparison-self-contained; local `target/` output or architectural naming alone is not a public claim.** | A senior external reviewer can otherwise misread A→G retrieval gains as H1-vs-ordinary-RAG gains, treat excluded models as hidden failures, confuse a synthetic attestation demo with qualification, or infer blanket runtime compatibility/control-plane authority from names. A read-only GPT-6 Astra public-claims review on 2026-09-13 returned `APPROVE WITH CONDITIONS` and required the headline comparison semantics/denominators to be explicit. | Track a sanitized frozen public evidence snapshot plus a machine verifier; headline A/G must define A=model-only and G=frozen ExactScope path, state 64 questions, 16/20 valid model pairs and four protocol N/A identities, and put the Hotpot ordinary-RAG limitation beside the result. The conformance demo must label fabricated attestation data `CONFORMANCE_DEMO_ONLY`; runtime evidence is stated per backend rather than as blanket compatibility; fail-closed claims assume a trusted host enforcing/reporting current identities. `Semantic Execution Policy Compiler` is an engineering description of restricted lowering, while `Qualification / Configuration Optimizer` remains a product hypothesis until automatic optimization/economic value is prospectively demonstrated. |
| D-133 | **Ship `v1.1.0` as a bounded software/architecture release; owner-bound enterprise qualification gates customer-value claims, not the software tag.** | The official-Kubernetes long-document proxy was a prospective transfer check and failed: evidence-eligible r4 measured G−R at −10.99 pp primary utility with 95% interval [−22.76,−0.48] pp, the frozen −2 pp margin failed, all three bounded diagnostic candidates also failed, `selected_arm=null`, and validation32 was not served. Continuing public tuning would turn the release into an open-ended sunk-cost loop. A read-only GPT-6 Astra release-scope review on 2026-09-13 returned `APPROVE WITH CONDITIONS` and judged a normal v1.1.0 tag defensible if the stability/claim boundary is explicit. | Stable support in v1.1.0 is limited to the existing Linux x86-64 native grounding C ABI/XSGI path and must pass stable-v1 regression/C ABI/clean-room gates. Qualification/control-plane workflows, enterprise DocQA, host integration, Bridge and demos are experimental/reference. The Kubernetes negative result and invalidated-run provenance remain public; byte/token reductions are not economic proof. Enterprise qualification, general RAG superiority, production readiness, automatic optimization/economic advantage and universal v1.1>v1 claims remain prohibited. After local release gates, push an exact RC commit; only tag `v1.1.0` after GitHub CI/release checks pass on that exact commit, without reopening benchmark policies. |

## Superseded or narrowed earlier decisions

### D-008 — “default model surface contains only xs_find and xs_eval”

D-008 is superseded by the implemented bounded-plan lane and later surface decisions:

- `xs_calc` is the generic short-arithmetic lane;
- `xs_eval` is the direct reviewed semantic-method lane;
- `xs_find` is fallback discovery;
- generated capability-slice metadata constrains semantic operation choice without exposing a full domain catalog;
- a fixed appliance may omit discovery entirely from its serving path.

Therefore D-008 must not be interpreted as requiring `xs_find -> xs_eval` for every calculation or as excluding `xs_calc`.

### D-024/D-025 — “direct xs_eval semantic hot path / small generated model surface”

These decisions remain correct for the **implemented semantic-operation lane**, but D-034/D-036/D-037 and D-041/D-042 narrow their product-wide interpretation:

- generic short arithmetic uses one bounded `xs_calc` plan surface;
- `xs_eval` remains primary for reviewed semantic operations;
- semantic hot sets are an implementation mechanism for compiling a small capability slice, not a fixed 8-32-operation product rule;
- task-family coverage and model/device budgets determine the deployed slice;
- `xs_find` remains cold/development infrastructure rather than a common serving step.

### D-012 — “fused deployment is first-class; fused and dynamic results are identical”

The semantic part remains active: a given operation must not have separate formulas/evaluators by packaging profile.

D-028/D-029 narrow the release-sequencing consequence:

- native static and no-import Wasm are the primary v0.1 product profiles;
- dynamic packs/discovery may remain Experimental;
- v0.1 is not blocked waiting for every internal profile/platform to become Tier 1.

## Product claim rules

Before publishing a comparative claim such as “ExactScope improves small-model accuracy” or “saves energy,” the evidence must identify:

- exact ExactScope artifact digest;
- capability-profile/hot-set/pack digest and operation revisions;
- tool/schema/grammar/prompt digests;
- model/runtime/quantization/hardware;
- benchmark dataset/mapping revision;
- stage-level results, model-difficulty metrics, and resource costs;
- capability-density/CRR values only when their raw numerator/denominator evidence is also published.

See `BENCHMARK.md`.

## Change procedure

A replacement decision must state:

1. which decision it supersedes;
2. measured binary/RAM/latency/model-turn/compatibility impact where relevant;
3. ABI/pack/protocol/operation-semantic impact;
4. migration/fallback behavior;
5. benchmark or conformance evidence appropriate to the change;
6. whether product claims/documentation must change.

Convenience or feature count alone is not sufficient reason to weaken deterministic-core invariants.

## D-045: Compose capability compilation at build time

Reuse Rust hotset generation from a Python build orchestrator; do not add profile metadata or JSON Schema dependencies to the deterministic runtime. Canonical bundles bind source, operation revisions and actual model assets, reject static budget excess, and remain experimental until artifact and evidence bindings exist. Schema specialization groups equal argument shapes to reduce structural invalid calls without changing arithmetic or the RC ABI. See [compiler contract](CAPABILITY_COMPILER.md).

## D-046: Share Statistics dispatch across borrowed vector transports

Keep the public generic entry as a small validating adapter and use one internal
non-generic evaluator over borrowed `DecimalVector` trait objects. This reduces
the measured no-import Wasm from 102,971 to 85,671 bytes without changing numeric
algorithms, vector ownership, error order, operation revisions or the C ABI.
All existing conformance tests and 225 Statistics Wasm gold calls pass. Latency
benefit is not claimed. The source-bound profile advances to revision 2; the
revision-1 bundle is retained unchanged with its original benchmark evidence.

## D-047: Bind evidence without manufacturing support claims

An experimental capability binder packages an actual no-import Wasm and admits
the Statistics gold only after independent native and Wasm execution agree. A
new profile revision binds artifact, corpus mapping and conformance hashes, while
parent identity is preserved. Verified hashes and passing gold do not imply
target qualification, peak memory measurements, source build attestation or LTS.

## D-048: Avoid re-normalizing fully cross-reduced rational products

`WorkRational` fields are private and all inputs are canonical. Multiplication and
division already cancel both cross GCDs before checked products, making another
normalizing GCD redundant. Return those checked coprime parts directly. Preserve
the existing i128 intermediate-overflow contract rather than expanding numerical
acceptance. A 90,000-pair grid plus extreme-value tests and Wasm gold validate the
change. The measured artifact tradeoff is +71 bytes for lower median times in
three paired desktop wire microbenchmarks; no model or target-latency claim follows.

## D-049: Reject impossible calc references in generation, not only at runtime

Capability-profile revision 7 derives a position-aware `xs_calc` GBNF while retaining
the historical public v0.1 grammar unchanged. Step 0 accepts decimal leaves only;
step i can reference only `#0..#(i-1)`. Runtime validation remains authoritative, but
self/forward references no longer consume weak-model generations in the derived
profile. The calc grammar grows only to 1,241 bytes and the combined Statistics
profile grammar is 2,514 bytes, below its 4,096-byte ceiling. Actual llama.cpp b10797
runs exercised two-step and eight-step backward chains. This constrains syntax, not
mathematical planning correctness.

## D-050: Prove binary specialization with one narrow Statistics slice before generalizing it

Add an experimental `statistics-core-8` build path that keeps `xs_calc` and exactly
eight reviewed Statistics operations while making economics, covariance, regression,
discovery and TinyWire serving paths unreachable. The Tiny JSON path, direct
`xs_wasm_eval_statistics` export and kernel dispatcher all reject excluded operations;
225 Statistics gold calls and dedicated rejection stress pass. The first proof measured
45,834 bytes versus 85,743 bytes for its same-source full fused development build.
This established that real binary slicing was worthwhile, but explicitly did not justify
a hand-written feature matrix for every future domain/hot set. D-053 records the later
profile-derived generalization.

## D-051: Make the specialized Wasm memory ceiling explicit and fail closed

The generic Wasm inherited a roughly 1 MiB default link stack and therefore declared
17 initial pages even though the specialized Statistics path needs far less. Local
stack-boundary stress found 2 KiB trapping and 4 KiB passing the current stress/gold
suite. Use a conservative 16 KiB stack for the experimental Statistics-8 build and
link with a hard `--max-memory=65536`. The resulting module declares one initial and
one maximum 64 KiB page. This is a Wasm linear-memory ceiling for the component, not
peak process resident RAM, host-runtime memory, model memory, or target qualification.

## D-052: Bind build and model evidence to exact capability identity

`tools/build_capability_wasm.py` records source/profile identity, target, feature set,
toolchain versions, stack policy, artifact digest and validation results. The artifact
binder verifies that provenance when present before producing a new immutable revision.
`tools/attach_model_evidence.py` separately requires model-run corpus, bundle, runtime,
profile revision, raw rows, metadata and summary digests to match before attachment.
Historical r2/85,671-byte experiments therefore cannot be relabeled as evidence for
a newer runtime such as the later frozen r17 benchmark-source flagship. Neither provenance nor successful
binding is a signature, independent reproducible-build proof, model-equivalence proof,
or target qualification.

## D-053: Derive existing Statistics binary subsets from capability profiles

Replace the hot-set-specific runtime branching with a shared `stats-specialized`
boundary plus one build feature per reviewed Statistics operation. The capability
compiler owns the stable operation-to-feature map and the builder derives the exact
feature list from `runtime_surface.xs_eval.operations`. Tiny JSON lookup, direct typed
Wasm op-ID dispatch and kernel dispatch all use those features, so omitting an operation
removes its serving path rather than merely hiding its schema. Keep `statistics-core-8`
as a compatibility alias only.

On the current source, the eight-operation flagship is 45,804 bytes while a profile
selecting only `stats.mean.weighted` is 38,932 bytes; both have zero imports and hard
`1..1` Wasm memory pages. The same current full fused build is 85,749 bytes. The
one-operation slice was produced by changing the capability profile/task family, not
by editing Rust for a new hot set. This generalizes **subsets of the existing reviewed
Statistics vocabulary** only. A new domain, new operation implementation, or new
semantic kernel still requires implementation, feature plumbing, review and conformance.

## D-054: Conformance evidence follows the selected binary surface

A specialized subset cannot be validated by blindly replaying calls for operations that
were intentionally removed. `tools/build_capability_wasm.py` therefore filters the
source Statistics corpus to calls whose operation is selected, requires that every
selected operation is covered, writes the filtered corpus beside build provenance, and
binds both source-corpus and filtered-corpus digests. The flagship selects all eight
reviewed operations and retains 225 calls; the weighted-mean-only proof retains 45 calls.
The calc-only baseline selects zero semantic operations and therefore binds an intentionally
empty semantic conformance corpus. `tools/test_selected_statistics_wasm.mjs` separately
verifies that unselected operations, direct op-ID bypasses, economics, discovery and
TinyWire fail closed. Filtered gold proves selected behavior; explicit negative
reachability tests prove the slice boundary.

## D-055: Measure semantic slice bytes against a same-boundary `xs_calc` baseline

Do not use a complete specialized artifact's byte size as the incremental cost of one
semantic domain capability. Add the reserved `arithmetic-baseline` task family, valid
only for `xs_calc=true` with `statistics-selected-wasm`. The compiler emits zero semantic
operations and omits `xs_eval` model assets; `exactscope-packc` supports a zero-operation
catalog and represents the eval tool/grammar as absent rather than generating an
unusable empty schema. The runtime still exports the stable Wasm ABI but rejects every
Statistics operation through Tiny JSON and direct typed dispatch.

At the D-055 benchmark-source revision this same-boundary baseline was **33,463 bytes**,
zero imports, memory `1..1` pages. Weighted mean was **38,932 bytes**, so its marginal
binary cost was **5,469 bytes**. The eight-operation flagship was **45,804 bytes**, so its
marginal semantic-slice cost was **12,341 bytes**. All three used the same 16 KiB stack
policy and 64 KiB maximum linear-memory policy. These frozen values remain the correct
binary denominator for the r20 model-evidence chain; later source revisions must publish
their own denominator rather than silently replacing it.

## D-056: Derive adapter selection metadata from the reviewed scope-pack without renumbering kernels

D-056 narrows D-053's statement that the capability compiler owns a hand-maintained
operation-to-feature map. The reviewed Statistics scope-pack remains the semantic source
for operation key, pack-local ID, revision, method, input/output shape and output policy.
The compiler now derives the existing `stats.*` -> `stats-*` specialization feature name
from that reviewed key set, while selected key/ID lookup is centralized in the kernel and
reused by Tiny JSON and direct typed Wasm dispatch. A packc parity test fails if the
scope-pack and fused Rust declarations drift in key, revision, method, signature, arity,
output names, scale or rounding.

This is **not** permission to equate pack-local operation IDs with stable internal kernel
IDs. The two number spaces already differ for covariance/correlation/regression versus
standard deviation. Existing ABI/kernel IDs therefore remain unchanged. The next metadata
phase may generate or exactly validate Cargo feature declarations and Rust implementation
bindings, but generated output must be deterministic/stale-checked and must preserve full
fused behavior, numeric semantics and existing ABI identity.

The post-change source starts a new immutable line: `statistics-core-8-ai-r21` is the
artifact-unbound profile and r22 is its artifact/gold/provenance-bound runtime. r20 remains
the frozen three-model evidence anchor for the earlier 45,804-byte r17 runtime; no model
uplift result is inherited by r21/r22 without a new matching model run. On the post-r20
source, calc-only / weighted-mean / Statistics-8 measure 33,463 / 38,932 / 45,832 bytes,
so the current-source semantic deltas are +5,469 / +12,369 bytes.

## D-057: Generate implementation plumbing and preserve frozen runtime identities

Statistics reviewed source and minimal bindings now generate stable internal IDs,
arity/output-name contracts, operation declarations, selected lookups and calls into
handwritten numeric functions. Packc consumes the shared generated name-to-kernel-ID
lookup. No numeric algorithm bodies, ABI revisions or operation/kernel IDs change.
Domain descriptors drive Cargo forwarding validation for Statistics and Economics;
scalar selected lookup is generated and scalar identity/output-policy drift is rejected.
Both generators have deterministic checked-in output and CI stale checks.

Allowed static builds of this implementation measured Statistics-8 at 45,833 bytes
(SHA-256 `dac3d5f4ca542f8e1a9f50369132f1ff3ca48886b07eb8aee1bd076fea055d36`)
and semantic-only Economics PED at 39,424 bytes
(`302541c7ef80d22113455269efa64f5fce3b5564ff3b97b907c041d9c6ddb512`).
Both declare zero imports and 1..1 memory pages. The +1/+7-byte changes versus
stored r28/r6 artifacts are accepted for removing metadata drift. These local build
measurements are not newly bound capability revisions, model evidence or qualification.
Frozen directories remain unchanged; source changes require a new revision before binding.

The JavaScript integration verifies manifest digest and exact regular-file inventory
before loading a capability. File-only component tests exercise malformed bundles.
Benchmarks, product E2E/gold execution, release and support promotion are excluded from
this implementation pass. Optional minimal-C-ABI JSON helpers and selected discovery/
TinyWire exclusions remain intentional non-goals.

## D-058: Negotiate the model-facing surface by exact contract ID, version and bytes

Tool schemas, grammars and prompt fragments are compatibility artifacts, but version ranges or semantic guessing would undermine the weak-model boundary. Newly generated capability bundles therefore carry `surface-contract.json`: every selected model-facing asset has an explicit contract ID/version and SHA-256, while the contract also binds profile identity, ABI and hot-set identity. The complete contract digest is stored in the capability profile. Host acceptance is fail-closed `exact ID + exact version + exact digest`; unsupported assets are not repaired, widened or substituted. The reference JavaScript host performs this check before compiling Wasm, and a Python checker provides the same static policy boundary. Frozen pre-D-058 capability revisions remain byte-for-byte immutable and may still pass their historical manifest verification, but absence of the new contract means they do not claim explicit v0.1 model-surface negotiation.

## D-059: Keep release packaging off-target and bind one capability to one runtime identity

Primary native/Wasm integration should not require an OEM to understand the Rust workspace, but packaging convenience must not add deployed runtime weight or blur artifact identity. `exactscope.release.bundle` v0.1 is therefore a deterministic outer archive around one explicit capability identity. Native packaging accepts only an unbound `host-limited` / `native-static` capability and binds the supplied static-library digest in the outer manifest; a Wasm artifact binding cannot be silently reused for native. Wasm packaging accepts only the already artifact-bound `no-import-wasm` capability and statically rechecks its digest, byte/import/memory declarations, exports and stored measurements. Verification rejects path traversal, links, duplicate archive members, oversized archives, unexpected outer payloads and contradictions between profile/task-map/catalog/model assets/measurements/bindings. These archives are always `experimental` / `unqualified`; deterministic packaging and static inspection are implementation properties, not target execution, product conformance, benchmark evidence or support promotion.

## D-060: Treat operation revision as permanent semantic identity, not a mutable version label

`canonical key + operation revision` is the semantic public identity. Argument names/order/shapes, semantic kinds, constraints, method, output contract, rounding/classification and observable error behavior cannot change within an existing revision. Internal refactors or optimizations may keep the revision only when exact observable semantics remain unchanged; they still produce new source/artifact identity. Materially different methods should normally use different keys. A supported release line, once one exists, must publish exact operation revisions and cannot silently replace/remove them in maintenance updates. `tools/check_operation_revision_compat.py` statically rejects transparent upgrades that remove baseline operations, roll revisions backward, change same-revision observable catalog metadata, reuse a changed capability at the same profile revision, or switch capability identity. A revision increase requires explicit opt-in review and never transfers old evidence automatically. This policy creates no retroactive stable/LTS claim for current experimental artifacts.

## D-061: Make unsafe and export boundaries machine-auditable without moving policy into the tiny runtime

Numeric, pack, Tiny JSON, compiler and conformance crates continue to forbid unsafe Rust. The C ABI and Wasm memory wrappers are the intentional unsafe boundaries and deny implicit unsafe operations inside unsafe functions. `spec/registries/public-exports.json` is the reviewed public native/Wasm export allowlist, and `tools/audit_security_surface.py` checks it against the C header, Rust `no_mangle` entry points, Wasm inspector, and `# Safety` contracts on public unsafe C calls. This closes source-level drift but does not claim the broader release security gate: fuzzing, sanitizer/equivalent checks, malformed artifact execution and built native symbol-table inspection remain artifact-level work.

## D-062: Separate reproducible build inputs, byte comparison, and release-level reproducibility claims

Reproducibility must not be inferred from a deterministic packager alone. `exactscope.build-input-identity` v0.1 records the exact current source identity, pinned toolchain/Cargo inputs, feature set, target and capability identity; stale-source capability reuse fails closed. Release bundles may embed and digest-bind that document. `exactscope.reproducible-build.comparison` v0.1 then records whether two caller-labeled outputs for one build-input identity are exactly byte-identical. A `MATCH` intentionally says only that those two files match; it does not prove that the labeled builders were genuinely independent or that the artifact is qualified. Actual supply-chain/reproducibility evidence therefore remains open until separate-builder/environment evidence is attached to the exact immutable release artifact.

## D-063: Derive compatibility records from exact release identity, but never promote support statically

The earlier compatibility manifest could describe planned targets without binding the new capability/release architecture. Extend its artifact record with an optional exact release identity covering release archive/manifest/runtime digests, release profile, ABI, capability bundle/profile revision, model-surface digest and optional build-input digest. `tools/record_release_compatibility.py` generates this stronger record only from a statically verified release archive and always emits `support=experimental`; it has no Tier 1/Tier 2 mode. The selected-toolchain/architecture roadmap item therefore remains evidence work until real immutable archives and target/runtime evidence exist, even though the record/verification machinery is now implemented.

## D-064: Maintain weak-model adapters as exact one-tool capability envelopes, not broad hot-set helpers

The llama.cpp reference path now has two deliberately separate one-tool envelopes: semantic-only `xs_eval` and calc-only `xs_calc`. Both require a verified capability bundle with explicit model-surface negotiation, use the compiler-generated prompt exactly once, reject unknown/widened surfaces, and validate model output without performing the calculation. The eval envelope enforces exact operation/arity/shape and decimal lexical form; the calc envelope additionally enforces the 1–8 step plan bound, backward-only result references, literal `powi` exponent constraints, and the 512-byte canonical request ceiling. The older `examples/llama.cpp/run_xs_calc.py` remains model/core/latency evaluation tooling and is not the maintained integration boundary. Offline envelope self-tests do not establish model accuracy or runtime compatibility evidence.

## D-065: Publish rc2 as a clean integration/qualification candidate and collect evidence from the immutable public release

The active Statistics/Economics product architecture is code-side complete enough to stop using a dirty development checkout as the benchmark input. `v1.0.0-rc.2` is therefore prepared from a separate clean release snapshot and labeled **integration & qualification candidate**, not stable/production-qualified. The source tag keeps reviewed implementation/specifications, deterministic generators, adapters, benchmark harnesses/preregistration inputs and historical result interpretation documents, while mutable generated capability/evidence revision directories and mutable benchmark result payloads are excluded from the product source. Historical frozen evidence remains preserved in its original developer/evidence location and is never rewritten merely to make a source tree look clean.

The public release workflow binds the Git tag to the Cargo project version and packages x86-64 evaluation SDKs plus Android/Linux ARM64 static OEM SDK candidates with release manifests/checksums. Exact published assets remain authoritative: a configured workflow path is not a support claim until the asset actually exists and passes integrity/integration checks.

rc2 model evidence is intentionally collected in a later external-user session starting from the immutable GitHub release. The minimum core matrix is five deliberately diverse models: Gemma 3 270M IT, LFM2.5 350M, Qwen3.5 0.8B, Qwen3.5 2B and Phi-4-mini-instruct 3.8B; Gemma 3n E2B is an optional separately reported low-resource-device profile. The default comparison is A model-only, C selected semantic-only and D combined where selected, with B calc-only only as a diagnostic. Repository/model/runtime/corpus/prompt/scorer identities are frozen before inference. Historical r20 evidence remains bound only to the older 45,804-byte r17 Statistics runtime and never transfers to rc2. Representative target RAM/latency/energy/support claims likewise wait for exact released-artifact qualification.

## D-066: rc3 fixes the public model-integration evidence boundary instead of reconstructing missing rc2 inputs

External-user qualification of the published rc2 archives verified release integrity, native/Wasm execution, clean-source tests and fail-closed behavior, but stopped before model inference because the evaluation SDK did not contain a complete artifact-bound capability identity. The documented capability host required a profile, capability manifest/detached digest, model-surface contract and bound runtime that could not be derived from the raw `adapters/generated/quant-core-16` directory without creating new private evidence. The correct response is a new candidate, not an evaluator-side reconstruction.

`v1.0.0-rc.3` therefore packages two host-limited benchmark capabilities over the exact same reviewed `quant-core-16` operation catalog and generic no-import Wasm: `quant-core-16-semantic-ai` exposes only `xs_eval`, while `quant-core-16-combined-ai` exposes the same semantic surface plus bounded `xs_calc`. Both include profile, task map, prompt/tool/GBNF assets, benchmark mapping, model-surface contract, exact runtime, manifest and detached digest. They are evaluation identities, not target-qualified domain-specialized artifacts, and do not create new formulas or alter deterministic semantics.

The evaluation archive also ships a stdlib-only verifier and two-phase A/C/D qualification runner. Preregistration freezes release/model/runtime/corpus/core/capability identities before inference and the run refuses byte drift, existing-output reuse, hidden retry or semantic repair. The final archive clean-room test must execute semantic and combined capabilities and complete a zero-inference preregistration using only extracted release contents. Model/target claims still require evidence from the immutable published rc3 release.
