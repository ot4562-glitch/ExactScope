# ExactScope roadmap

No dates are promised. This roadmap is ordered by **capability density, weak-model usability, evidence quality, and retrofit economics**, not by operation count.

Release context: **v1.0.0-rc.2 integration & qualification candidate**.

The product question is:

> Can a tiny deterministic capability component let an already-deployed small/on-device model recover a useful narrow quantitative skill cheaply enough that keeping the existing model/hardware is the better engineering choice for that task family?

## Current checkpoint — rc2

The active code architecture and public prerelease packaging are implemented.

### Product code implemented

- [x] deterministic `no_std` decimal/rational numeric kernel;
- [x] explicit deterministic rounding/domain/status behavior;
- [x] bounded scalar VM and Plan v0.1;
- [x] `xs_calc`: 1–8 steps over `add/sub/mul/div/powi/sqrt`, backward-only references;
- [x] strict bounded Tiny JSON boundary;
- [x] native typed C ABI;
- [x] no-import Wasm boundary;
- [x] TinyWire optional binary transport;
- [x] reviewed Statistics and Economics semantic execution;
- [x] selected `xs_eval` surface and optional/cold `xs_find`;
- [x] pack/packc infrastructure and optional dynamic packs;
- [x] profile-driven selected specialization;
- [x] D-057 Statistics metadata phase 2: generated/drift-checked operation declarations, stable kernel IDs, arity/output contracts, selected lookup, dispatch and packc kernel-name lookup;
- [x] Economics selected operation/Cargo wiring checks;
- [x] exact capability/model-surface contracts and fail-closed negotiation;
- [x] operation revision compatibility policy/checks;
- [x] source-level public export/unsafe-boundary audit;
- [x] build-input identity and reproducibility/compatibility-record infrastructure;
- [x] maintained strict llama.cpp `xs_eval` and `xs_calc` envelopes.

### Public package implemented for rc2

- [x] clean source-release policy: reviewed source/specs/generators retained, mutable generated capability/evidence directories and benchmark output payloads excluded from the product source tag;
- [x] version-driven release workflow rather than rc1 filename hardcoding;
- [x] Windows x86-64 evaluation SDK job;
- [x] Linux x86-64 evaluation SDK job;
- [x] Android ARM64 static OEM SDK job;
- [x] Linux ARM64 musl static OEM SDK job;
- [x] release manifest + SHA256SUMS;
- [x] evaluation SDK includes AI integration assets and qualification/model-download documentation;
- [x] model downloader resolves upstream repository revision and hashes downloaded model files without launching inference;
- [x] copy-paste next-session qualification prompt.

A workflow being implemented does not become “published/supporting” until the actual GitHub release asset exists and its integrity checks succeed.

## Historical evidence boundary

The older Statistics model evidence accumulated through `statistics-core-8-ai-r20` is frozen to a **45,804-byte r17 serving runtime**. It remains useful historical design evidence but is not rc2 evidence.

Historical work established two useful lessons:

1. a reviewed semantic slice can materially improve some weak-model task configurations;
2. uplift magnitude and the best semantic-only/combined surface can vary sharply by model, and a sufficiently weak model may still fail operation selection/argument extraction.

Therefore target-model qualification is part of the product, not optional marketing polish.

## P0 — publish and independently verify rc2

### P0.1 Release artifact integrity

- [ ] confirm GitHub `v1.0.0-rc.2` tag points to the intended clean commit;
- [ ] confirm release manifest source commit/tag consistency;
- [ ] verify all release-level SHA256SUMS;
- [ ] verify the internal inventory/checksums of each evaluation/OEM SDK archive;
- [ ] record exact archive bytes/digests;
- [ ] confirm the expected Windows/Linux/Android/ARM64 assets actually exist.

Success criterion: a fresh external checkout/download can identify and verify every rc2 input without relying on the developer working tree.

### P0.2 External-user integration baseline

From the published archive, not a source build:

- [ ] native static-library smoke;
- [ ] Wasm import/export/memory/static inspection;
- [ ] Wasm local smoke/conformance;
- [ ] capability/model-surface identity check;
- [ ] no-model benchmark-corpus/core self-test;
- [ ] record every command/environment/result.

Success criterion: an evaluator can attach and exercise the release artifact without modifying product source.

### P0.3 Freeze rc2 model qualification inputs

Core five:

- [ ] Gemma 3 270M IT Q8_0;
- [ ] LFM2.5 350M Q4_K_M;
- [ ] Qwen3.5 0.8B Q4_0;
- [ ] Qwen3.5 2B Q4_K_M;
- [ ] Phi-4-mini-instruct 3.8B Q4_K_M.

Optional separate product profile:

- [ ] Gemma 3n E2B IT.

Before inference:

- [ ] resolve model repository revisions;
- [ ] hash exact downloaded files;
- [ ] freeze `model-inventory.json`;
- [ ] freeze inference runtime/build/command line;
- [ ] freeze corpus/generator/SHA-256;
- [ ] freeze prompt/tool/GBNF/model-surface bytes/digests;
- [ ] freeze generation settings;
- [ ] freeze scoring/failure taxonomy;
- [ ] freeze timeout/retry/no-hidden-repair rules;
- [ ] freeze single-writer/duplicate policy and any early-stop rule.

Success criterion: a model score cannot exist without the exact release/model/runtime/corpus identity needed to reproduce and audit it.

### P0.4 Run the minimum diverse model matrix

Primary arms:

- [ ] A — model only;
- [ ] C — selected semantic `xs_eval` only;
- [ ] D — `xs_calc + xs_eval` only where the exact selected profile contains both;
- [ ] B — `xs_calc` only where needed as a diagnostic.

Report per model/task family:

- [ ] correct count/rate;
- [ ] malformed-output count;
- [ ] wrong-tool/operation-selection count;
- [ ] argument-extraction/order count;
- [ ] deterministic runtime failure count;
- [ ] final numeric/rendering mismatch count;
- [ ] token-limit/timeout count;
- [ ] exact artifact/model bytes/digests;
- [ ] raw per-item output and run status.

Do not force a larger-model replacement headline or CRR when the baseline/reference contract makes the comparison misleading.

Success criterion: identify whether ExactScope creates useful end-to-end capability on more than one architecture/vendor/model-size class and which minimal surface each target model should receive.

### P0.5 Measure exact released footprint

For every released/qualified capability profile:

- [ ] binary bytes and SHA-256;
- [ ] selected operation/tool count;
- [ ] prompt/schema/grammar bytes/tokens;
- [ ] component linear-memory declaration;
- [ ] native context/scratch contract;
- [ ] model-visible generated request size distribution.

Guideline: a general selected no-import Wasm should normally remain near/below ~128 KiB when practical; >192 KiB needs explanation; >256 KiB requires major design review. Profile-specific budgets can be much lower.

Correctness, deterministic semantics, fail-closed behavior, and ABI stability are non-negotiable. Do not delete useful robustness for a cosmetic byte win.

## P1 — qualify representative constrained hardware

### P1.1 Android ARM64 or embedded Linux ARM64 target

Choose at least one representative product-style target and use the **exact published rc2 SDK**.

- [ ] record device/SoC/OS/toolchain/runtime identity;
- [ ] record exact installed ExactScope asset digest;
- [ ] measure artifact/storage bytes;
- [ ] measure process/VM RSS and heap where possible;
- [ ] measure stack high-water/scratch where possible;
- [ ] measure p50/p95/p99 latency with enough samples;
- [ ] separate cold/warm behavior where relevant;
- [ ] measure energy per operation/workload where the target permits credible instrumentation;
- [ ] record sustained thermal/throttling behavior where relevant;
- [ ] exercise malformed-input/fail-closed behavior;
- [ ] confirm offline operation;
- [ ] qualify update/rollback/interrupted replacement/power-loss behavior if the product uses updatable packs/runtime assets.

Success criterion: target cost is small enough for the retrofit thesis and there is no hidden device-integration failure.

A 64 KiB Wasm linear-memory ceiling must never be reported as total process/device RAM.

### P1.2 Model + target combined decision

Once model and device evidence are both frozen:

- [ ] calculate capability uplift against its exact model-visible/token/binary/memory/latency/energy cost;
- [ ] compare the candidate to a justified larger-model/newer-hardware alternative where practical;
- [ ] report raw numerators/denominators alongside any density ratio;
- [ ] separate product/task-specific conclusions from general AI claims.

Success criterion: make a real engineering choice, not only a benchmark chart.

## P2 — harden support only after evidence

### P2.1 Compatibility and release policy

- [ ] decide which exact native/Wasm targets move from prerelease/experimental to supported;
- [ ] publish compatibility records for exact release assets/toolchains;
- [ ] define ABI/operation-revision/LTS change policy for supported lines;
- [ ] define security response/support window;
- [ ] verify reproducible-build expectations with sufficiently independent builders where claimed;
- [ ] add signed provenance/attestation only when its trust model is defined.

### P2.2 Integrator feedback

- [ ] collect at least one independent external-style integration beyond the developer's own machine;
- [ ] record integration effort/friction rather than only runtime results;
- [ ] identify missing packaging surfaces from actual OEM needs;
- [ ] add convenience wrappers only where they do not create a second calculation authority.

### P2.3 Stable v1.0.0 promotion

Potential promotion gate:

- [ ] exact public candidate artifacts passed integrity/conformance;
- [ ] minimum diverse model matrix or a documented equivalent product-specific matrix completed;
- [ ] at least one representative ARM64 target qualified;
- [ ] no unresolved high-severity security/ABI defect;
- [ ] public claims rewritten from the exact frozen evidence;
- [ ] support/compatibility label explicitly chosen.

Only then consider stable `v1.0.0`.

## P3 — expand breadth selectively

New domains/operations are not blockers for rc2. Add them only when they improve a real product profile.

Possible future work:

- additional reviewed statistics/economics operations;
- finance/engineering/science slices where the method contract is narrow and evidence-worthy;
- additional host/runtime wrappers;
- AAR/Prefab convenience packaging after Android evidence;
- Apple/XCFramework only when a real integration target justifies it;
- signed/remote capability distribution only with an explicit threat/trust/update model.

Do not turn ExactScope into a general scientific runtime or a giant model-visible catalog.

## Current single next action

**Publish/verify `v1.0.0-rc.2`, then start a new external-user qualification session using `docs/NEXT_SESSION_PROMPT.md`.**

Benchmark and target evidence should be collected from the immutable public candidate, not from the release-preparation working tree.
