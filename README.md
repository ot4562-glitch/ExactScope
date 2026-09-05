<div align="center">

# ExactScope

### Tiny deterministic quantitative capability layers for small and on-device AI

**Add reviewed quantitative capability without replacing the model.**

[![Release](https://img.shields.io/badge/release-v1.0.0--rc.2-orange)](https://github.com/ot4562-glitch/ExactScope/releases/tag/v1.0.0-rc.2)
![Status](https://img.shields.io/badge/status-integration%20%26%20qualification%20candidate-yellow)
![ABI](https://img.shields.io/badge/C%20ABI-1.0-informational)
![Wasm](https://img.shields.io/badge/Wasm-no--import-success)

**Code-side implementation is complete for the active Statistics/Economics architecture. Model and real-device qualification for rc.2 are intentionally unmeasured until the public release is evaluated as an external user.**

[Quickstart](docs/QUICKSTART.md) · [AI integration](docs/AI_INTEGRATION.md) · [Qualification handoff](docs/QUALIFICATION_HANDOFF.md) · [한국어 요약](#한국어-요약)

</div>

---

## What ExactScope is

ExactScope is a **small model-adjacent quantitative coprocessor** for constrained/local AI. It is intended for OEMs, device makers, embedded-AI teams, and local-inference developers who already have a small model but need a narrow deterministic numerical capability without replacing the whole model or hardware stack.

It is not a chatbot, hosted API, general scientific runtime, or human calculator application.

The product idea is:

```text
existing small model
      |
      | tiny constrained request
      v
+--------------------+
| ExactScope surface |
|  xs_calc / xs_eval |
+--------------------+
      |
      v
bounded deterministic core
      |
      v
canonical decimal result or typed failure
```

The important constraint is **small surface, not broad catalog**. A weak model should see the fewest choices needed for its task family.

## v1.0.0-rc.2 status

`v1.0.0-rc.2` is an **integration & qualification candidate**.

| Area | rc.2 state |
|---|---|
| Deterministic numeric core | implemented |
| Native C ABI | implemented |
| No-import Wasm adapter | implemented |
| Tiny JSON bounded boundary | implemented |
| `xs_calc` bounded plan lane | implemented |
| Selected `xs_eval` semantic lane | implemented |
| Statistics specialization metadata | generated/drift-checked |
| Economics PED selected specialization | implemented/drift-checked |
| Model-surface identity negotiation | implemented, fail closed |
| Release-shaped packaging | implemented |
| Android/Linux ARM64 SDK packaging | implemented in release workflow |
| rc.2 model benchmark | **not run yet** |
| rc.2 real-device RAM/latency/energy qualification | **not run yet** |
| Stable support claim | **not made** |

That separation is deliberate: the candidate is packaged first, then benchmarked and qualified from the immutable public release so results are not attached to a moving development tree.

## Pick the right release asset

The rc.2 workflow is configured to publish these integration shapes. Only use an asset that actually exists on the GitHub release page.

| Platform | Expected archive | Use |
|---|---|---|
| Windows x86-64 | `exactscope-eval-1.0.0-rc.2-x86_64-pc-windows-msvc.tar.gz` | local-model / desktop integration |
| Linux x86-64 | `exactscope-eval-1.0.0-rc.2-x86_64-unknown-linux-gnu.tar.gz` | local-model / server integration |
| Android ARM64 | `exactscope-wearable-sdk-1.0.0-rc.2-aarch64-linux-android.tar.gz` | Android / edge OEM integration |
| Linux ARM64 musl | `exactscope-wearable-sdk-1.0.0-rc.2-aarch64-unknown-linux-musl.tar.gz` | embedded Linux / wearable integration |

Every published archive is accompanied by release-level `SHA256SUMS` and `release-manifest.json`. The evaluation archives also contain their own manifest and checksums.

### Fastest evaluation path

1. Download the matching release archive plus `SHA256SUMS` and `release-manifest.json`.
2. Verify the release checksum before extracting.
3. Follow [the 5-minute quickstart](docs/QUICKSTART.md).
4. Attach the selected model-facing surface using [AI integration](docs/AI_INTEGRATION.md).
5. For real benchmark/qualification, start a clean session with [the qualification handoff](docs/QUALIFICATION_HANDOFF.md) and [copy-paste prompt](docs/NEXT_SESSION_PROMPT.md).

## Model-facing lanes

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

Adapters may normalize syntax and transport. They must not:

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

## Next benchmark: minimum diverse model matrix

The rc.2 benchmark plan intentionally uses **five core models**, not a giant leaderboard sweep:

| Model | Role |
|---|---|
| Gemma 3 270M IT | extreme-small independent lower bound |
| LFM2.5 350M | edge/on-device-first lower bound |
| Qwen3.5 0.8B | primary modern sub-1B model |
| Qwen3.5 2B | same-family scale comparison |
| Phi-4-mini-instruct 3.8B | independent upper-small reasoning reference |

Optional: Gemma 3n E2B as a separate low-resource-device product profile.

The repository includes a downloader that **only downloads and inventories model weights**; it does not run inference:

```powershell
py -3 -m pip install -r requirements-benchmark.txt
py -3 tools/fetch_benchmark_models.py --list
py -3 tools/fetch_benchmark_models.py core --root C:\AIModels\ExactScopeBench
```

See [`benchmarks/NEXT_MODEL_MATRIX.md`](benchmarks/NEXT_MODEL_MATRIX.md). New rc.2 scores remain **unmeasured** until a separate qualification session freezes exact release/model/runtime/corpus/scoring identities and runs them.

## Historical model evidence — do not transfer to rc.2

An older internal preregistered Statistics development chain, accumulated through `statistics-core-8-ai-r20`, showed that reviewed semantic capability could materially change end-to-end results for some weak-model configurations. It also showed an important failure boundary: uplift magnitude and the best model-facing surface varied substantially by model, and a sufficiently weak model could still fail selection/argument extraction.

Those results belong to an older **45,804-byte r17 Statistics serving runtime**. They are retained as historical design evidence only and are **not rc.2 benchmark results**. Re-running those models against rc.2 creates new evidence.

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

Use [`docs/QUALIFICATION_HANDOFF.md`](docs/QUALIFICATION_HANDOFF.md) as the evidence contract.

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

ExactScope는 **작은 온디바이스/로컬 AI에 필요한 좁은 정량 계산 능력을 작은 deterministic component로 붙이는 제품**입니다. 모델 전체를 키우거나 하드웨어를 바꾸기 전에, 필요한 통계·경제·일반 산술 능력만 제한된 도구 표면으로 추가하는 것이 목적입니다.

`v1.0.0-rc.2`는 **제품 코드 구현과 공개 패키징을 끝내고 실제 사용자 방식의 검증을 시작하기 위한 릴리즈 후보**입니다. 아직 rc2에 대한 모델 성능·실기기 RAM/지연시간/에너지 결과는 만들지 않았습니다. 그 검증은 공개된 동일한 GitHub 릴리즈를 새 세션에서 내려받아 수행합니다.

가장 먼저 읽을 문서:

1. [`docs/QUICKSTART.md`](docs/QUICKSTART.md) — 설치/실행
2. [`docs/AI_INTEGRATION.md`](docs/AI_INTEGRATION.md) — AI 모델에 붙이는 방법
3. [`benchmarks/NEXT_MODEL_MATRIX.md`](benchmarks/NEXT_MODEL_MATRIX.md) — 최소 5개 모델 검증 설계
4. [`docs/QUALIFICATION_HANDOFF.md`](docs/QUALIFICATION_HANDOFF.md) — 실제 benchmark/target qualification 절차
5. [`docs/NEXT_SESSION_PROMPT.md`](docs/NEXT_SESSION_PROMPT.md) — 다음 세션에 그대로 붙여넣을 프롬프트

과거 r20 모델 성능은 이전 45,804 B r17 runtime의 역사적 증거이며 rc2에 상속하지 않습니다.
