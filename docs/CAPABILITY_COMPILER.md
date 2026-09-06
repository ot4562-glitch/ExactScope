# ExactScope capability compiler

Release context: **retained quantitative-subsystem compiler after the rc4 grounding-first product pivot**
Status: **implemented quantitative build-time infrastructure; not the flagship grounding compiler/profile contract**

> The active rc4 flagship grounding contract is provider-neutral and is defined by `GROUNDING_ARCHITECTURE.md` plus `../spec/GROUNDING_CONTRACT_V0_1.md`. This compiler remains authoritative for quantitative `xs_calc`/`xs_eval` capability slices only. Do not extend it with grounding semantics merely because prototype recall code exists.

`tools/compile_capability.py` turns reviewed quantitative domain/task-family metadata into the smallest deterministic model-facing capability surface requested by a profile. Python/jsonschema are workstation build dependencies only; they are not target runtime dependencies.

The compiler currently supports reviewed Statistics and Economics metadata through `spec/capabilities/domain-descriptors.json` and related implementation bindings.

## 1. What the compiler does

Given a task-family request/profile, it:

- derives the required reviewed operation union;
- verifies operation key/revision/signature/arity/output metadata;
- verifies `xs_calc` enablement and plan-contract identity when selected;
- enforces model-visible tool/operation and prompt/schema/grammar budgets;
- derives Statistics specialization Cargo features from reviewed operation metadata;
- emits deterministic native-tool/schema/lane-GBNF/prompt assets when selected;
- emits `constrained-prompt.txt` plus composed `xs-request.gbnf` as the universal model-facing compatibility baseline;
- emits exact capability/model-surface contracts and digests binding both model envelopes to one semantic/runtime identity;
- binds source/profile/registry/asset identities;
- fails closed on unknown families, duplicate JSON keys, unsupported revisions, inconsistent counts/bounds, fabricated evidence, or unsupported support promotion.

It does **not** generate arbitrary formulas or numeric algorithms. New semantics still require reviewed Rust/source implementation, tests, provenance, and revision policy.

## 2. Typical source workflow

Generate a new revision into a new directory:

```powershell
cargo build -p exactscope-packc
py -3 tools/compile_capability.py <request-or-profile.json> adapters/capabilities/<new-revision>
py -3 tools/compile_capability.py --verify adapters/capabilities/<new-revision>
py -3 tools/test_compile_capability.py
```

The rc3 clean source intentionally keeps only `adapters/capabilities/README.md`; it does not carry forward every generated historical revision. A generated directory is a build/evidence artifact whose identity belongs to the exact source/profile that produced it.

Do not regenerate into or overwrite a frozen historical revision. Changed source/profile/assets require a new revision/output directory.

## 3. Task-family-driven selection

The preferred input describes required task families rather than making a user maintain another operation list by hand.

Examples:

- Statistics weighted mean selects only `stats.mean.weighted` through `xs_eval`.
- The reserved `arithmetic-baseline` family selects zero semantic operations and can emit only `xs_calc` assets.
- The Statistics flagship selection uses the reviewed eight-operation slice needed by its task families.
- Economics can select the reviewed midpoint price-elasticity operation without importing the Statistics semantic surface.

The broad domain catalog stays build-time-only.

## 4. Deterministic generated identity

Canonical generated JSON uses deterministic ordering/escaping/separators and LF termination. Argument order is preserved.

A generated capability can bind:

- normalized runtime source identity;
- ABI/registry identity;
- selected operation keys/revisions/contracts;
- file-name-to-SHA-256 maps for model-facing assets;
- model-surface contract ID/version/digest;
- profile/hot-set identity;
- declared static budgets;
- artifact/build/conformance identity once those stages exist.

`manifest.json` hashes payload identity and `bundle-sha256.txt` binds the manifest. Integrity hashes are not publisher authentication or code signing.

## 5. Model-surface contract

Generated `surface-contract.json` assigns exact ID/version/digest identity to the complete model-facing surface. For rc4 that surface includes the constrained compatibility assets (`constrained-prompt.txt`, `xs-request.gbnf`) and, when present, native tool schemas, lane grammars and `prompt-fragment.txt`. `tools/check_model_surface_compat.py` can compare this against a host acceptance policy without running model inference.

The constrained request grammar is composed from the exact selected `xs_eval`/`xs_calc` lane grammars plus an explicit fail-closed no-call sentinel. It is not a second semantic implementation.

A host must fail closed on an identity mismatch. It must not silently expose a wider catalog, substitute another method because operation names happen to look compatible, or repair a failed native-tool output by switching envelopes after inference.

Frozen pre-contract historical bundles remain historical evidence; they do not acquire a new surface-contract claim retroactively.

## 6. Statistics implementation metadata completion

D-057 metadata phase 2 is complete.

`tools/generate_statistics_metadata.py` deterministically generates/drift-checks:

- Statistics operation declarations;
- stable internal kernel IDs;
- arity/output contracts;
- output names;
- selected key/ID lookup;
- compute-dispatch call plumbing;
- Statistics Cargo operation feature declarations/forwarding.

`tools/generate_domain_metadata.py` checks domain-descriptor-driven specialization wiring and Economics selection/scalar declarations.

Packc reuses the generated Statistics kernel-name mapping rather than maintaining a second handwritten key table.

Numeric algorithms remain handwritten/reviewed. Stable internal kernel IDs and pack-local operation IDs remain separate namespaces.

Check with:

```powershell
py -3 tools/generate_statistics_metadata.py --check
py -3 tools/generate_domain_metadata.py --check
py -3 tools/test_generate_statistics_metadata.py
```

## 7. Selected Wasm specialization

For reviewed Statistics operations, `runtime_surface.specialization=statistics-selected-wasm` drives operation-selected build features. Selected Tiny JSON and direct typed Wasm dispatch reuse centralized/generated metadata and reject excluded operations.

The specialization mechanism has historically demonstrated real reachability/footprint reduction for:

- an eight-operation Statistics slice;
- a weighted-mean-only slice;
- an `xs_calc`-only same-boundary baseline.

Those pre-rc3 byte/digest measurements are development history tied to their exact source/toolchain identities. The completed rc3 qualification likewise remains bound to its exact release artifacts and is not inherited by rc4.

Any rc4 capability/compiler change creates a new model-surface identity. Artifact size, SHA-256, import/memory declaration, conformance result and marginal semantic/interface cost must be measured from that exact new candidate if evidence is produced.

## 8. Build and bind an artifact

`tools/build_capability_wasm.py` can build an artifact-unbound selected Statistics profile and record build provenance. `tools/bind_capability.py` can then create a **new immutable revision** that binds the actual Wasm, build provenance, and selected-operation conformance evidence.

Conceptual sequence:

```powershell
py -3 tools/build_capability_wasm.py --bundle adapters/capabilities/<source-revision> --output target/<build-id>
py -3 tools/bind_capability.py --bundle adapters/capabilities/<source-revision> --artifact target/<build-id>/runtime.wasm --build-provenance target/<build-id>/build-provenance.json --corpus benchmarks/statistics-v0.1.jsonl --core target/debug/exactscope-core.exe --revision <new-revision> --output adapters/capabilities/<new-bound-revision>
```

These commands are product build/bind tools, not permission to rewrite frozen rc3 evidence. For rc4 development they may be used to create new candidate artifacts; any later benchmark must freeze those exact artifacts before inference.

A historical source profile cannot be rebound to current runtime source just because operation names or byte counts look similar.

## 9. Model evidence is a separate identity layer

Model evidence must bind the exact:

- capability/profile revision;
- runtime artifact digest;
- corpus and mapping digest;
- model/repository revision and model-file digest;
- adapter/tool/grammar/prompt identity;
- runtime/hardware/configuration;
- raw rows and summary.

Historical `statistics-core-8-ai-r20` and the completed rc3 qualification remain frozen to their exact runtime/model/surface identities. Neither can be inherited by rc4 or by a newly generated capability revision.

Re-running any historical model after changing the candidate creates new evidence.

## 10. Release packaging boundary

The compiler and capability binder are not the public release themselves.

For rc3:

- public GitHub evaluation/OEM SDKs are packaged from the clean source by the release workflow;
- evaluation SDKs contain selected integration assets, documentation, manifests/checksums, and benchmark/model-download tooling;
- generated mutable capability/evidence directories are not accumulated in the source tag;
- frozen evidence should be published as separately identifiable immutable evidence, not silently overwritten in product source.

`tools/package_release_bundle.py` remains the deterministic generic capability/runtime archive format for explicit bound identities. It stays experimental/unqualified until exact artifact/target evidence supports a stronger compatibility label.

## 11. What the compiler proves and does not prove

Compiler/generator checks can prove deterministic metadata and fail-closed selection behavior. A bound build can prove exact artifact identity and conformance for its checked contract.

They do **not** by themselves prove:

- model uplift;
- model/tool selection quality;
- target process RSS or stack high-water;
- target latency/energy/thermal behavior;
- production compatibility;
- stable support.

Those belong to the separate rc3 qualification procedure in `docs/QUALIFICATION_HANDOFF.md`.
