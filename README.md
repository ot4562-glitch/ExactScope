<div align="center">

# ExactScope

### Tiny grounding and deterministic capability layers for small and on-device AI

**Make small models more useful on everyday factual questions without replacing the model.**

[![Release](https://img.shields.io/badge/release-v1.0.0--rc.3-orange)](https://github.com/ot4562-glitch/ExactScope/releases/tag/v1.0.0-rc.3)
![Status](https://img.shields.io/badge/status-rc4%20grounding%20READY__FOR__BENCHMARK-blue)
![ABI](https://img.shields.io/badge/C%20ABI-1.0-informational)
![Wasm](https://img.shields.io/badge/Wasm-no--import-success)

**v1.0.0-rc.3 external-user qualification is complete and frozen. The rc4 provider-neutral everyday-grounding candidate is now `READY_FOR_GROUNDING_BENCHMARK`: source/package/profile/corpus/scorer/runtime/model identities are frozen, Linux and Windows clean-room zero-inference checks passed, and all five model preregistrations return `ready-to-run`. Quantitative `xs_calc`/`xs_eval` remains supported as a secondary deterministic capability subsystem. No rc4 model-accuracy or hallucination-reduction result is claimed before the frozen A/G benchmark runs.**

[Grounding architecture](docs/GROUNDING_ARCHITECTURE.md) · [Grounding contract](spec/GROUNDING_CONTRACT_V0_1.md) · [Benchmark-ready record](docs/GROUNDING_BENCHMARK_READY.md) · [Benchmark handoff](docs/GROUNDING_BENCHMARK_HANDOFF.md) · [Benchmark contract](docs/BENCHMARK.md) · [rc3 qualification closeout](docs/RC3_QUALIFICATION_CLOSEOUT.md) · [한국어 요약](#한국어-요약)

</div>

---

## What ExactScope is

ExactScope is a **small model-adjacent grounding and deterministic capability layer** for constrained/local AI. It is intended for OEMs, device makers, embedded-AI teams, and local-inference developers who want a small model to answer ordinary factual questions more reliably without replacing the whole model or hardware stack.

It is not a chatbot, hosted API, universal web search engine, general RAG framework, or human calculator application.

The flagship rc4 product idea is:

```text
user question
      |
      v
provider-neutral grounding prefetch
      |
      v
compact Grounding Frame
      |
      v
existing small model -- one answer call
      |
      v
more evidence-grounded everyday answer
```

Sources may be private memory, device/application state, product manuals, local reference data, a frozen semantic index, or host-provided search. They all map into the same provider-neutral Grounding Contract.

The important constraint is **small evidence, not broad context**. A weak model should receive only the few evidence items it needs, with explicit `authoritative` versus `supplemental` behavior. Existing `xs_calc`/`xs_eval` deterministic calculation remains available for quantitative tasks without forcing ordinary factual questions through an academic/tool catalog.

## Current status: rc3 closed, rc4 grounding candidate benchmark-ready

`v1.0.0-rc.3` remains the latest frozen public prerelease. Its external-user model/install qualification is complete; its raw evidence is historical and immutable. It is **not** promoted to stable support.

| Area | Current state |
|---|---|
| Deterministic numeric core | retained / implemented |
| Native C ABI | retained / implemented |
| No-import Wasm adapter | retained / implemented |
| Tiny JSON bounded boundary | retained / implemented |
| `xs_calc` bounded plan lane | retained / implemented |
| Selected `xs_eval` semantic lane | retained / implemented |
| Model-surface identity negotiation | retained, fail closed |
| rc3 five-model A/C/D qualification | **completed / frozen historical evidence** |
| Linux/Windows clean-room install qualification | **completed for rc3** |
| Android/Linux ARM64 package/doctor checks | **completed for rc3** |
| Physical ARM64 latency/RAM/energy/thermal qualification | **NOT MEASURED** |
| rc4 Grounding Architecture / logical Grounding Contract | **frozen for implementation / provider-neutral** |
| rc4 machine-readable profile/reference path | **implemented and no-inference conformance tested** |
| rc4 default everyday path | **original-question prefetch -> compact Grounding Frame -> one model answer call** |
| rc4 benchmark candidate/scorer | **implemented; serving/gold physically separated; zero-inference dry-run 30/30** |
| rc4 retrieval provider choice | **product-neutral; exact/lexical reference provider is frozen only for the first benchmark candidate, while vector/application/host providers remain contract-compatible options** |
| rc4 evaluation package/preregistration | **READY_FOR_GROUNDING_BENCHMARK; frozen candidate source `125ad940...`, Linux/Windows clean-room PASS, 5/5 verify-only ready-to-run** |
| rc4 constrained/native quantitative envelope work | retained infrastructure / secondary subsystem |
| Stable support claim | **not made** |

The accepted rc3 finding is that native tool-call reliability is not a simple function of model size. Chat-template/tool-protocol compatibility and model-facing surface/token cost matter materially. rc4 therefore avoids making tool use the common consumer path: ordinary factual grounding is prefetched before the model call. Constrained JSON/GBNF and native-tool negotiation remain useful for the quantitative subsystem and optional retrieval-rewrite profiles, not as a requirement for everyday answering.

## Pick the right release asset

The rc.3 workflow is configured to publish these integration shapes. Only use an asset that actually exists on the GitHub release page.

| Platform | Expected archive | Use |
|---|---|---|
| Windows x86-64 | `exactscope-eval-1.0.0-rc.3-x86_64-pc-windows-msvc.tar.gz` | local-model / desktop integration |
| Linux x86-64 | `exactscope-eval-1.0.0-rc.3-x86_64-unknown-linux-gnu.tar.gz` | local-model / server integration |
| Android ARM64 | `exactscope-wearable-sdk-1.0.0-rc.3-aarch64-linux-android.tar.gz` | Android / edge OEM integration |
| Linux ARM64 musl | `exactscope-wearable-sdk-1.0.0-rc.3-aarch64-unknown-linux-musl.tar.gz` | embedded Linux / wearable integration |

Every published archive is accompanied by release-level `SHA256SUMS` and `release-manifest.json`. The evaluation archives also contain their own manifest and checksums.

### Fastest evaluation path

1. Download the matching release archive plus `SHA256SUMS` and `release-manifest.json`.
2. Verify the release checksum before extracting.
3. Follow [the 5-minute quickstart](docs/QUICKSTART.md).
4. Attach the selected model-facing surface using [AI integration](docs/AI_INTEGRATION.md).
5. For real benchmark/qualification, start a clean session with [the qualification handoff](docs/QUALIFICATION_HANDOFF.md) and [copy-paste prompt](docs/NEXT_SESSION_PROMPT.md).

## Product lanes

### Grounding — default everyday factual path

The host queries configured sources/providers using the original user question, applies authority/freshness/conflict/budget policy, and gives the model one compact Grounding Frame before its normal answer call. Native tool support is not required.

Provider choices are deliberately open: exact/alias, lexical/ranked text, frozen embedding/vector indexes, application memory, and captured host/search providers can all implement the same Grounding Contract. The first exact/lexical prototype is not the product definition.

`authoritative` sources fail closed on missing/ambiguous/conflicting evidence; `supplemental` sources may fall back to normal model knowledge when no useful evidence exists.

### `xs_calc` — bounded generic arithmetic

Use this when the model already knows the arithmetic decomposition.

Plan v0.1 deliberately limits the model's search space:

- 1–8 steps;
- at most 2 arguments per step;
- `add`, `sub`, `mul`, `div`, `powi`, `sqrt`;
- backward-only references;
- 512-byte Tiny JSON request cap;
- exact decimal/rational intermediates where defined;
- deterministic half-even quantization;
- fail-closed validation with no semantic repair.

Example:

```json
{"p":[{"o":"mul","a":["12","7"]},{"o":"sub","a":["#0","4"]},{"o":"div","a":["#1","5"]}]}
```

Canonical result:

```json
{"s":0,"v":"16","f":0,"p":"plan-v0.1","r":1}
```

A failed step returns a typed failure, not a guessed number.

### `xs_eval` — reviewed semantic operations

Use this when **method identity matters**. A selected capability can encode distinctions such as sample vs population statistics, reviewed rounding, argument order, method variants, and domain constraints that a weak model should not rediscover on every call.

The active Statistics slice includes reviewed operations such as sum, mean, weighted mean, population/sample variance and standard deviation, and Pearson correlation. The Economics proof includes a reviewed midpoint price-elasticity operation.

The deployed binary and model assets should contain only the selected task-family slice.

### `xs_find` — optional cold/development discovery

`xs_find` is not required in the normal hot path. Keep it out of small-model serving prompts unless the product genuinely needs discovery.

## Integration surfaces

### Native C

Public header: [`include/exactscope.h`](include/exactscope.h)

The native API uses caller-owned bounded storage and stable checked layouts. No daemon, account, database, or network service is required for the deterministic core path.

### WebAssembly

The Wasm adapter is designed for local embedding with a bounded request/response boundary. Selected profile builds can remove excluded serving paths instead of keeping a broad runtime hidden behind metadata.

### llama.cpp / local models

Maintained strict envelopes live in [`adapters/llama-cpp/`](adapters/llama-cpp/):

- semantic-only `xs_eval`;
- calc-only `xs_calc`.

They validate model-surface identity and output shape and do not contain alternative calculation logic or semantic repair.

## Fail-closed design

For grounding, fail-closed behavior is **target scoped**:

- authority comes from the frozen TargetPlan/source binding, never provider/evidence text;
- authoritative `none` requires completed/sufficient required coverage;
- timeout/error/denied/budget/incomplete search stays `unavailable`;
- ambiguous or conflicting authoritative evidence is not silently resolved;
- supplemental evidence does not silently fill an unresolved authoritative target;
- evidence is untrusted data and cannot grant permissions, broaden scope, or rewrite authority;
- one unresolved authoritative target does not force unrelated supplemental targets to abstain.

For the quantitative subsystem, adapters may normalize syntax and transport but must not:

- invent missing operands;
- guess unit/percentage/currency conversions;
- swap argument meaning;
- silently choose a statistical/economic method;
- recompute or repair an ExactScope result;
- turn a typed error into a plausible number.

Stable operation revisions and internal kernel IDs are treated as semantic identity. Pack-local operation IDs are a separate namespace.

## Build-time specialization

The broad domain catalog is a maintenance/build-time asset. A capability profile selects the reviewed task-family operations and derives a small model-visible surface and corresponding runtime features.

Current code-side infrastructure includes:

- domain descriptors for Statistics and Economics;
- deterministic generated/drift-checked Statistics operation/kernel/dispatch metadata;
- reviewed Economics selection metadata;
- Cargo feature-forwarding checks;
- exact model-surface contracts and asset digests;
- build-input identity;
- operation revision compatibility checks;
- deterministic release-bundle packaging;
- reproducible-build comparison records;
- experimental compatibility records.

Numeric algorithms remain handwritten/reviewed rather than generated from arbitrary formulas.

See [Capability Compiler](docs/CAPABILITY_COMPILER.md), [Architecture](docs/ARCHITECTURE.md), and [Operation Revision Policy](spec/OPERATION_REVISION_POLICY_V0_1.md).

## Build from source

Requirements: the pinned Rust toolchain, Python 3, and Node.js for Wasm examples/checks.

```powershell
cargo check --workspace --all-targets
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace --lib
cargo build --locked --release -p exactscope-wasm --target wasm32v1-none --no-default-features --features fused,tinyjson
python tools/inspect_wasm.py target/wasm32v1-none/release/exactscope_wasm.wasm
node examples/javascript/wasm-xs-calc.mjs target/wasm32v1-none/release/exactscope_wasm.wasm
```

Source/unit/static checks are not model or hardware qualification evidence.

## Next benchmark: grounding A/G after candidate freeze

The next model evidence is a **new rc4 grounding candidate**, not a continuation of rc3. The flagship comparison is:

- **A:** model only, exactly one answer-generation call;
- **G:** original-question prefetch -> target-grouped Grounding Frame/Model Projection -> the same model, exactly one answer-generation call.

A model-generated query rewrite and a larger-model reference are optional separately preregistered diagnostics; they are not merged into G.

The same diverse five-model set used historically in rc3 may be reused under a new grounding preregistration:

| Model | Role |
|---|---|
| Gemma 3 270M IT | extreme-small independent lower bound |
| LFM2.5 350M | edge/on-device-first lower bound |
| Qwen3.5 0.8B | primary modern sub-1B model |
| Qwen3.5 2B | same-family scale comparison |
| Phi-4-mini-instruct 3.8B | independent upper-small reference |

No rc3 score transfers to rc4 grounding. Before any model request, the new candidate must freeze GroundingProfile/source/provider/index/Model Projection/corpus/scorer/model/runtime identities and pass the no-inference gate in [`docs/BENCHMARK.md`](docs/BENCHMARK.md).

The current implementation task intentionally stops at **READY_FOR_GROUNDING_BENCHMARK**; actual A/G inference belongs to a separate validation session.

## Historical model evidence — do not transfer to rc.3

An older internal preregistered Statistics development chain, accumulated through `statistics-core-8-ai-r20`, showed that reviewed semantic capability could materially change end-to-end results for some weak-model configurations. It also showed an important failure boundary: uplift magnitude and the best model-facing surface varied substantially by model, and a sufficiently weak model could still fail selection/argument extraction.

Those results belong to an older **45,804-byte r17 Statistics serving runtime**. They are retained as historical design evidence only and are **not rc.3 benchmark results**. Re-running those models against rc.3 creates new evidence.

For the exact historical numbers and caveats, see the result interpretation documents under `benchmarks/STATISTICS_R17_*_RESULT.md`.

## Qualification before stable claims

Before calling ExactScope production-qualified for a target, bind results to the exact public release and measure:

- end-to-end model correctness and failure decomposition;
- exact artifact/model/runtime identities;
- binary/storage footprint;
- resident memory and stack/scratch on target;
- latency distribution on target;
- energy and thermal behavior when relevant;
- malformed-input/fail-closed behavior;
- update/rollback/power-loss behavior where relevant.

A selected Wasm linear-memory ceiling is **not** total process/device RAM.

For future rc4 grounding evidence use [`docs/BENCHMARK.md`](docs/BENCHMARK.md) and the frozen GroundingProfile/preregistration contract. [`docs/QUALIFICATION_HANDOFF.md`](docs/QUALIFICATION_HANDOFF.md) is historical rc3 audit material, not the next grounding procedure.

## Repository hygiene and evidence policy

Release source tags intentionally do not accumulate generated capability revision directories or mutable benchmark output payloads. They keep:

- reviewed source/specifications;
- generators and binders;
- model-facing source assets;
- benchmark harnesses and preregistration inputs;
- historical result interpretation documents.

New generated capability/evidence revisions and benchmark outputs are kept outside tracked product source until deliberately frozen as separate immutable evidence.

## Documentation

- [Quickstart](docs/QUICKSTART.md)
- [Installation](docs/INSTALLATION.md)
- [AI integration](docs/AI_INTEGRATION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Capability compiler](docs/CAPABILITY_COMPILER.md)
- [Evaluation bundle](docs/EVALUATION_BUNDLE.md)
- [Benchmark methodology](docs/BENCHMARK.md)
- [Minimum model matrix](benchmarks/NEXT_MODEL_MATRIX.md)
- [Qualification handoff](docs/QUALIFICATION_HANDOFF.md)
- [Next-session prompt](docs/NEXT_SESSION_PROMPT.md)
- [Marketing claim boundary](docs/MARKETING_CLAIMS.md)
- [Security](SECURITY.md)
- [Roadmap](ROADMAP.md)

## License

ExactScope is dual-licensed under [MIT](LICENSE-MIT) or [Apache-2.0](LICENSE-APACHE). Model weights downloaded for qualification keep their own upstream licenses and terms.

---

# 한국어 요약

ExactScope의 rc4 주력 방향은 **작은 온디바이스/로컬 모델의 일상 사실 질문 정확도를 높이고, 근거가 없는데도 자신 있게 값을 지어내는 오류를 줄이는 작은 grounding layer**입니다. 학문별 계산기를 늘리거나 모델에게 큰 tool catalog를 보여주는 것이 중심이 아닙니다.

기본 경로는 `원문 질문 -> 보안/앱 scope -> Grounding Router -> Retrieval Provider -> Evidence Policy -> target별 GroundingFrame -> 작은 Model Projection -> 모델 1회 응답`입니다. 모델이 `xs_recall` 같은 검색 도구를 먼저 호출할 필요가 없습니다. 검색 구현도 하나로 고정하지 않고 exact/lexical, frozen embedding/vector, 앱 내장 검색, 캡처된 host/search provider가 동일한 Grounding Contract 뒤에 붙을 수 있습니다.

각 사실 target은 `authoritative` 또는 `supplemental` 정책을 가집니다. authoritative target에서 `none`은 필요한 authoritative source 검색이 정상 완료된 경우에만 의미가 있으며, timeout/error/denied/부분 검색은 `unavailable`로 남깁니다. `ambiguous`와 `conflict`도 별도로 보존합니다. 반대로 supplemental source에 답이 없다는 이유만으로 일반 상식 질문 전체를 거절해서는 안 됩니다.

`v1.0.0-rc.3` 외부 사용자 검증은 **종료·동결**됐습니다. Linux/Windows 설치·패키징과 5개 소형 모델 A/C/D 검증은 rc3의 역사적 정량/도구 인터페이스 증거입니다. 실물 ARM64 장치가 없어 실제 RAM/지연시간/에너지/열은 **NOT MEASURED**입니다. rc3에서 native tool-call 성공률이 모델 크기에 단순 비례하지 않고 chat-template/protocol과 prompt 비용에 크게 좌우된다는 점이 확인됐기 때문에, rc4 일상 grounding은 native tool call을 필수 경로로 사용하지 않습니다.

다음 검증은 새로운 rc4 grounding candidate에서 **A=model only 1회 응답 vs G=원문 질문 prefetch + 같은 모델 1회 응답**으로 수행합니다. false grounding, authoritative unsupported assertion, grounding penalty, useful-answer/abstention, retrieval precision과 정확한 token/latency/storage 비용을 함께 측정합니다. 현재 작업은 실제 inference 직전인 `READY_FOR_GROUNDING_BENCHMARK` 상태에서 멈춥니다.

가장 먼저 읽을 문서:

1. [`docs/PRODUCT_DIRECTION.md`](docs/PRODUCT_DIRECTION.md) — 현재 제품 방향
2. [`docs/GROUNDING_ARCHITECTURE.md`](docs/GROUNDING_ARCHITECTURE.md) — grounding 시스템 설계
3. [`spec/GROUNDING_CONTRACT_V0_1.md`](spec/GROUNDING_CONTRACT_V0_1.md) — normative 논리 계약
4. [`docs/BENCHMARK.md`](docs/BENCHMARK.md) — 다음 A/G 검증 계약
5. [`ROADMAP.md`](ROADMAP.md) — benchmark 직전까지의 구현 순서

기존 `xs_calc`/`xs_eval` 정량 계산 코어는 버리지 않고 2차 subsystem으로 유지합니다. 과거 r20과 rc3 성능 결과는 각각 해당 runtime/release identity에 묶인 역사적 증거이며 rc4 grounding 결과로 복사하거나 덮어쓰지 않습니다.
