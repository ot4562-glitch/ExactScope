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
| D-033 | **The primary product thesis is on-device AI capability retrofit.** | Physically constrained or deployed devices may be unable to absorb a larger model without new hardware, while software can still be updated. | Product, benchmark, packaging, and commercial priorities optimize for strengthening an existing small model at tiny incremental cost. |
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
