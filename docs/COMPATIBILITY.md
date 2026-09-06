# Compatibility contract

Release context: **rc4 grounding-contract design after completed v1.0.0-rc.3 qualification**. rc3 remains prerelease/historical quantitative evidence and is not automatically promoted to Tier 1/Tier 2. rc4 adds a compatibility layer above ABI/runtime: a grounding result is compatible only when source scope, authority, retrieval-provider/index identity, Evidence Policy and Grounding Frame semantics are all bound. Native-tool compatibility remains relevant only to optional model-generated quantitative/rewrite paths.

Compatibility is evidence attached to an exact artifact **and behavior-affecting grounding profile**, not a statement that source code compiled or one search query returned a plausible hit.

The current product strategy separates the already-published **rc3 quantitative profiles** from the not-yet-frozen **rc4 grounding provider/profile contract** so grounding design can converge without falsely promoting prototype retrieval code or old platform packages.

## 1. Support vocabulary

- **Tier 1:** exact release artifact is release-blocking, conformance-tested, and executed on the declared real/official-emulator target with recorded resource evidence.
- **Tier 2:** exact release artifact is automated and conformance-tested, but hardware/runtime evidence is narrower.
- **Experimental:** build/integration evidence exists but compatibility is not promised.
- **Planned:** design/roadmap target only.

No README badge or release note may call an artifact supported without the corresponding evidence.

## 2. Grounding compatibility identity — active rc4 design

Grounding compatibility is provider-neutral. Two integrations are not the same compatibility target merely because they emit the same JSON fields.

A grounding profile identity must bind, at minimum:

- Grounding Contract version;
- allowed source namespaces/scope semantics;
- authority mode per source/namespace;
- source/content revision or immutable digest;
- Retrieval Provider type and implementation revision;
- query preprocessing/normalization identity;
- index/content build identity and digest where an index exists;
- ranking/top-k configuration that can change selected evidence;
- embedding model/tokenizer/vector/index identity where semantic retrieval is used;
- freshness/revision selection policy;
- duplicate/conflict/ambiguity policy;
- provider-unavailable behavior;
- model-visible evidence item/byte/token budget;
- Grounding Frame serialization/model-policy revision;
- prefetch vs rewrite/tool query profile and model-call budget.

A change to one of those behavior-affecting fields creates a different grounding compatibility identity for qualification.

Exact/alias, lexical, semantic/vector, application-native and captured network/search providers may all be compatible with the same logical Grounding Contract. **Algorithm parity is not required; contract/failure/identity semantics are.**

### Grounding compatibility requirements

A compatible provider/profile must prove:

1. scope isolation occurs before retrieval;
2. `authoritative` and `supplemental` behavior is preserved;
3. `grounded`, `none`, `ambiguous`, `conflict`, and `unavailable` remain distinguishable;
4. evidence identity/source/revision survive provider -> policy -> model-frame transport;
5. configured evidence budgets are enforced deterministically at the policy boundary;
6. false/ambiguous/conflicting evidence is not silently upgraded into an authoritative hit;
7. provider failure is not reported as a true no-hit;
8. model-facing evidence cannot change higher-priority Grounding Policy semantics;
9. the exact provider/profile identity is recorded with benchmark evidence.

Support/Tier promotion for a grounding profile additionally requires representative end-to-end evidence; a retrieval unit test alone is insufficient.

## 3. Published rc3 quantitative compatibility scope

The currently published prerelease compatibility candidates remain:

1. **Native static C ABI**
2. **No-import `wasm32v1-none`**

These describe the rc3 quantitative subsystem and its release assets. They do not imply that an rc4 grounding SDK/profile is already published.

Secondary/experimental quantitative paths include dynamic packs/discovery, convenience wrappers, wider native OS/architecture targets, embedded/bare-metal targets and additional shared-library profiles.

The quantitative invariant remains that any profile exposing the same operation uses the same shared calculation semantics. It is not a requirement that every grounding provider and every quantitative platform reach Tier 1 simultaneously.

## 4. Current evidence snapshot

| Path | Current evidence | Current claim |
|---|---|---|
| rc4 grounding logical contract | architecture/specification review only; no frozen provider/profile candidate or model evidence yet | design-stage / **no accuracy, hallucination-reduction, provider-support or Tier claim** |
| prototype exact/lexical recall code | local prototype/self-test evidence only | non-normative implementation probe; not the grounding compatibility definition |
| Native scalar/statistics C ABI | source/unit/conformance coverage; zero-copy vector path; rc3 evaluation packaging | implemented quantitative candidate path; not Tier 1/Tier 2 yet |
| Dynamic statistics `.xsp` path | shared kernel and fused/dynamic parity tests for implemented slice | implemented secondary path |
| No-import Wasm | source/build inspection and runtime/component tests; rc3 evaluation packaging | implemented candidate path; not Tier 1/Tier 2 yet |
| Android AArch64 static SDK | cross-build/package workflow, CMake target, doctor/reference host infrastructure | Experimental rc3 candidate until published artifact/target evidence exists |
| Linux AArch64 musl static SDK | cross-build/package workflow, doctor/ELF/reference host infrastructure | Experimental rc3 candidate until published artifact/target evidence exists |
| Wearable reference | C host, A/B, benchmark/qualification framework | integration reference, not generic device support |
| Real constrained-target performance | unmeasured for rc3 | no performance Tier claim |
| GitHub prerelease assets | rc3 workflow configured with manifest/checksum publication | candidate distribution only; actual release page is authoritative |

`tools/record_release_compatibility.py` can now create an **experimental** compatibility record for one deterministic release-shaped archive. The record binds the archive digest, release-manifest digest, exact runtime digest, capability bundle/profile revision, ABI, model-surface digest, target and toolchain. The tool deliberately refuses Tier 1/Tier 2 output; it is an identity/evidence container, not support promotion.

The legacy planned example in `spec/examples/compatibility-manifest.json` remains a design placeholder. A current release record is meaningful only when produced from the exact verified release archive it names. Target/runtime execution, conformance, resource evidence, and support promotion remain separate requirements below.

## 5. What a supported artifact/profile must prove

For a grounding profile, support evidence must bind the exact Grounding Contract/Profile plus source/provider/index/projection identities and prove, as applicable:

1. documented clean integration/install path;
2. profile/schema/canonicalization/digest conformance;
3. security-scope and provider/source binding enforcement;
4. deterministic Router/Provider/Policy/Projection replay for local components;
5. correct authoritative coverage and `none` vs `unavailable` behavior;
6. ambiguity/conflict/freshness/dedup/order/budget behavior;
7. provider/index/source-snapshot identity and reproducibility;
8. model-projection and adversarial-evidence/data-boundary tests;
9. representative end-to-end A/G evidence before an accuracy/support claim;
10. size/memory/latency/resource evidence for any target-specific cost claim.

For a quantitative runtime artifact, retain the existing requirements: clean build/integration, ABI/wire conformance, canonical vectors, malformed request/pack behavior, artifact identity/digest, size/memory records, target execution, self-tests and exact operation/hot-set scope.

Performance claims additionally require the actual target used for the claim.

## 6. Native static C ABI requirements

The C ABI remains the native cross-language authority.

Required properties:

- C99-compatible fixed-width declarations;
- no Rust layout in public ABI;
- caller-owned buffers/context/scratch;
- stable status codes;
- no required allocator in the fused/static path;
- no panic/exception/unwind crossing the boundary;
- no required runtime service/thread;
- operation semantics independent of host language.

Tier evidence should include:

- C99/C++11 header compile tests;
- ABI layout/version checks;
- buffer sizing/error tests;
- direct hot-set `xs_eval` smoke test;
- exact release archive digest;
- platform runtime execution.

## 7. WebAssembly baseline

The primary portable artifact uses `wasm32v1-none` and must not require:

- WASI;
- host imports;
- threads/shared memory;
- SIMD for correctness;
- reference types/GC/exceptions/memory64;
- filesystem/clock/random/socket imports.

Required release evidence:

- zero-import inspection;
- documented memory/export contract;
- direct eval/TinyWire smoke execution;
- canonical result conformance;
- artifact size/digest;
- execution in at least one declared runtime.

## 8. Direct-hot-path compatibility

A product integration is considered compatible only when its hot-set binding cannot silently drift from the runtime.

A hot-set artifact should bind:

- core/ABI version;
- registry/pack digest;
- operation key and revision;
- compact signature/argument order.

On mismatch:

- invalidate the binding;
- regenerate/rebind;
- never substitute a different method or operation.

`xs_find` remains available as fallback where enabled, but repeated known operations should not require discovery.

## 9. Adapter compatibility

Generated OpenAI-compatible/GBNF/llama.cpp assets are compatibility artifacts in their own right.

They require:

- deterministic/reproducible generation;
- exact decimal preservation;
- hot-set digest binding;
- no hidden calculation/semantic repair;
- fixture tests for valid/error cases;
- benchmark records identifying the exact adapter/grammar digest.

A model adapter cannot be called compatible merely because it produced parseable JSON once.

## 10. Fail-closed compatibility

The core remains strict. Compatibility testing must include both acceptance and rejection behavior.

Required negative classes include:

- wrong argument count/order;
- invalid lexical decimals;
- unsupported operation;
- ambiguous method where discovery is used;
- domain errors;
- zero denominator;
- resource/vector limits;
- pack corruption/truncation where applicable.

Adapters may apply allowed syntactic normalization but cannot repair semantic errors.

## 11. Data/pack portability

`.xsp` is canonical little-endian and contains offsets rather than native pointers. Loaders decode fields explicitly and validate every offset/count/length.

Dynamic packs remain Experimental until their intended release profile has complete loader/discovery/update evidence. Their existence does not block the primary native/Wasm product release.

## 12. CPU policy

The correctness path remains scalar.

- SIMD/CPU-specific acceleration is optional;
- acceleration requires identical canonical results and scalar fallback;
- baseline correctness must not require a specific FPU mode;
- product claims must identify the artifact/CPU profile used.

## 13. Platform packaging policy

Android, Apple, Windows, Linux, or other wrappers are convenience distribution layers around the same shared core.

A wrapper:

- may translate lifecycle/protocol/buffer types;
- may package headers/libraries/manifests;
- may package the selected capability profile and its tool/schema/GBNF/prompt assets;
- may not implement formulas/rounding/classification/unit conversion.

Only ABI slices with exact release evidence belong in a supported package.

## 14. Wearable/device claims

“Wearable support” is too broad to be a compatibility claim.

Documentation must identify the actual execution boundary:

- native application/plugin;
- WebAssembly runtime;
- Android/native host;
- paired phone/compute host;
- vendor extension environment.

A closed device without a legitimate product-controlled executable boundary cannot be retrofitted by ExactScope independently. ExactScope is integrated by the product team; it is not an end-user installation target.

## 15. Conformance corpus priorities

The grounding candidate must cover, before model inference:

- GroundingProfile schema/canonicalization/digest behavior;
- QueryEnvelope/profile/security-scope binding;
- Router/TargetPlan deterministic replay;
- ProviderOutcome status/coverage semantics;
- authoritative `none` versus `unavailable`;
- mixed authoritative/supplemental target groups;
- deterministic merge/order/tie-break/dedup independent of provider completion order;
- freshness/validity and stale-revision selection;
- ambiguity/conflict preservation;
- Evidence Item canonicalization/content identity;
- whole-item evidence budget/truncation;
- Model Projection byte determinism and target-state preservation;
- adversarial evidence/data-versus-instruction fixtures;
- serving/gold benchmark isolation;
- captured remote-provider replay when such a profile is shipped.

The retained quantitative release conformance still covers decimal arithmetic, VM/kernel/statistics vectors, C ABI/TinyWire behavior, operation identity, malformed requests, no-import Wasm inspection, and shipped adapter fixtures. Dynamic pack corruption/offset/string/duplicate tests remain mandatory for any release that ships dynamic packs.

## 16. Performance/resource evidence

For any grounding target/profile used in claims, record as applicable:

- source snapshot and provider-index bytes;
- provider/runtime code bytes;
- resident memory/RSS/heap;
- GroundingFrame and Model Projection bytes;
- model-visible evidence tokens;
- retrieval p50/p95/p99 latency with cold/warm distinction;
- answer-model and end-to-end latency separately;
- energy where credibly measurable;
- runtime/hardware/toolchain/provider configuration.

For quantitative paths, continue to record artifact/context/scratch/vector transport and ExactScope compute latency separately.

Do not extrapolate one hardware/provider measurement to another platform or provider profile.

## 17. Benchmark compatibility

A published grounding benchmark must record the exact:

- ExactScope candidate/release digest;
- Grounding Contract/Profile bytes and digest;
- router/configuration identity;
- source snapshots and provider/index/preprocessing/ranking identities;
- embedding/tokenizer/index identity where semantic retrieval is used;
- merge/freshness/conflict/timeout/budget/projection identities;
- serving corpus and scorer-gold digests separately;
- model/runtime/quantization/hardware/generation settings;
- raw per-query routing/provider/frame/projection records subject to privacy policy.

A quantitative benchmark additionally binds its hot-set/pack, operation revisions, adapter schema/GBNF and model-surface identities.

See [BENCHMARK.md](BENCHMARK.md).

Operation-revision compatibility is governed by [OPERATION_REVISION_POLICY_V0_1.md](../spec/OPERATION_REVISION_POLICY_V0_1.md). Transparent upgrades of one capability profile can be checked statically with `tools/check_operation_revision_compat.py`; revision upgrades require explicit review and never inherit benchmark/qualification evidence automatically.

## 18. Release promotion rule

An Experimental path becomes Tier 2/Tier 1 only after evidence is produced for the immutable artifact being promoted.

A green source-tree CI run from another commit cannot retroactively qualify a release artifact.

## 19. Product-scope rule

A focused v0.1 may ship with a narrow operation/profile/target matrix if that scope is clearly documented and benchmark-backed.

The project should prefer:

```text
small supported scope + strong evidence
```

over:

```text
wide matrix + compile-only claims
```
