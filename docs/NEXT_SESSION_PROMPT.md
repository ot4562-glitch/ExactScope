# 다음 검증 세션용 프롬프트

아래 내용을 새 ChatGPT/Codex 세션의 첫 메시지로 그대로 사용한다.

```text
ExactScope v1.0.0-rc.2를 개발자 checkout이 아니라 실제 외부 사용자처럼 검증해라.

대상 저장소:
https://github.com/ot4562-glitch/ExactScope
대상 릴리즈:
v1.0.0-rc.2

목표:
1. GitHub에 공개된 정확한 rc2 소스/릴리즈 자산부터 독립적으로 받아 무결성을 검증한다.
2. 제품 소스를 먼저 고치지 말고, rc2 그대로 native/Wasm/AI integration baseline을 만든다.
3. 최소하지만 다양한 소형 모델 matrix로 model-only 대 ExactScope-equipped end-to-end benchmark를 수행한다.
4. 그 뒤 가능한 대표 Android ARM64 또는 embedded Linux ARM64 환경에서 target qualification을 수행한다.
5. 모든 결과는 정확한 Git tag/commit, release asset SHA-256, model repo revision/file SHA-256, runtime version, corpus/prompt/scoring identity에 묶는다.
6. 기존 r20 historical model evidence를 rc2 결과로 절대 상속하거나 재표기하지 않는다.

시작할 때 반드시 먼저 읽을 문서:
- docs/QUALIFICATION_HANDOFF.md
- benchmarks/NEXT_MODEL_MATRIX.md
- benchmarks/model-downloads.json
- docs/AI_INTEGRATION.md
- docs/CODEX_CONTEXT.md
- docs/QUICKSTART.md

진행 규칙:
- 처음에는 로컬 개발 저장소의 dirty state를 증거로 쓰지 말고 GitHub v1.0.0-rc.2의 immutable tag/release를 새 디렉터리에 받아라.
- release-manifest.json, SHA256SUMS, Git tag commit을 서로 대조한 뒤에만 다음 단계로 간다.
- rc2 공개 자산에서 발견되는 package/integration 문제를 임의 우회하지 말고 release/package defect로 먼저 기록한다.
- baseline이 끝나기 전에 제품 Rust/C/Python/JS source, 공개 ABI, capability/model surface, corpus, scorer를 수정하지 않는다.
- 수정이 필요하면 rc2 baseline을 먼저 보존한 뒤 별도 새 candidate 작업으로 분리하고, 수정된 결과를 rc2 evidence라고 부르지 않는다.

모델 다운로드:
- 먼저 py -3 -m pip install -r requirements-benchmark.txt
- py -3 tools/fetch_benchmark_models.py --list
- py -3 tools/fetch_benchmark_models.py core --root C:\AIModels\ExactScopeBench
- downloader가 만든 model-inventory.json을 그대로 보존한다.
- gated model은 내가 약관 동의/인증을 해야 하면 그 단계만 명확히 알려라. 임의 토큰이나 계정을 만들지 마라.

Core model 5개는 임의로 늘리지 말고 다음을 기본으로 한다:
1. Gemma 3 270M IT Q8_0 — extreme-small independent lower bound
2. LFM2.5 350M Q4_K_M — edge/on-device-first lower bound
3. Qwen3.5 0.8B Q4_0 — primary mainstream sub-1B
4. Qwen3.5 2B Q4_K_M — same-family scale comparison
5. Phi-4-mini-instruct 3.8B Q4_K_M — independent upper-small reference
Optional: Gemma 3n E2B IT는 core GGUF 표와 섞지 말고 별도 product-oriented profile로만 검증한다.

첫 inference 전에 preregistration을 파일로 만들어 freeze해라. 최소 포함 항목:
- ExactScope tag/commit/source/archive/runtime digest
- release-manifest/SHA256SUMS identity
- 각 모델 repo commit/revision, filename, bytes, SHA-256
- llama.cpp 또는 대체 runtime 정확한 version/build/command line
- corpus/generator/item count/SHA-256
- prompt/system text, chat template, GBNF/tool schema/prompt-fragment SHA-256
- context, temperature, seed, max tokens, sampling params
- arm 정의와 scoring/failure taxonomy
- timeout/retry/no-hidden-repair 규칙
- single-writer/duplicate 처리
- 사전 정의된 stop/futility rule이 있다면 그것

모델 benchmark 기본 arms:
A = model only
C = selected xs_eval semantic surface only
D = xs_calc + xs_eval only when the exact selected rc2 profile exposes both
B = xs_calc-only는 diagnostic이 필요할 때만 추가

공정성:
- 비교 arm은 같은 item set과 같은 generation budget을 사용한다.
- hidden retry, semantic repair, answer repair, 수동 정답 교정 금지. 필요하면 사전 등록한 정책만 사용.
- model이 wrong tool을 고른 경우, args를 잘못 뽑은 경우, malformed output, ExactScope typed runtime failure, final numeric mismatch, token-limit/timeout을 서로 분리한다.
- deterministic tool call 자체가 정확했다고 해서 end-to-end item을 정답 처리하지 않는다. 최종 task completion을 평가한다.
- 모델별 correct count/rate와 모든 주요 failure count를 같이 보고한다.
- 파라미터 수나 단일 CRR 숫자만으로 '더 큰 모델보다 우수' 같은 일반화 claim을 만들지 않는다.

결과 저장:
benchmarks/output/rc2-<model-id>-<run-id>/ 같은 unique directory를 사용하고, preregistration/model inventory/surface/raw items/summary/logs/checksums/status를 모두 보존한다.
중복 (arm,item_id), 불완전 결과의 complete 표기, 중간 모델/runtime identity 변경은 invalid로 처리한다.

역사적 증거 경계:
statistics-core-8-ai-r20의 수치는 45,804-byte r17 runtime에만 속한다. 디자인 참고는 가능하지만 rc2 baseline이나 rc2 uplift 숫자로 복사하지 마라. rc2에서 같은 모델을 다시 돌리면 그것은 새 evidence다.

모델 benchmark를 freeze한 다음 target qualification을 진행한다.
가능하면 공개 rc2의 Android ARM64 또는 aarch64-unknown-linux-musl SDK를 실제 target에서 사용하고 다음을 기록한다:
- artifact/storage bytes
- process/VM resident memory, heap
- stack high-water/scratch
- latency distribution(p50/p95/p99 등)
- cold/warm behavior
- energy per operation/workload(측정법 포함)
- sustained thermal/throttling if relevant
- malformed input/fail-closed
- offline behavior
- update/rollback/interrupted replacement/power-loss behavior if applicable

Wasm 64 KiB linear memory ceiling을 전체 process RSS라고 부르지 마라. Desktop latency를 target-device latency qualification로 취급하지 마라.

문제가 생기면 먼저 다음으로 분류해라:
product/runtime defect / release-package defect / adapter defect / model capability failure / harness-scorer defect / target integration defect.
소스를 고쳐 문제를 숨기지 말고 rc2 baseline defect를 먼저 문서화해라.

실사용 설치/통합 UX 검증도 독립 gate로 수행해라:
- 검증 작업공간은 기존 개발 checkout과 분리한 `C:\AIProjects\ExactScope-user-qualification-rc2` 같은 새 디렉터리를 사용한다.
- Windows x86_64 release SDK를 GitHub release asset만 보고 내려받기 -> SHA256SUMS 대조 -> 압축 해제 -> 문서 탐색 -> 첫 성공 호출까지 수행한다.
- source clone 경로도 별도로 수행해 checkout -> requirements 설치 -> pinned Rust 확인 -> build/test -> 첫 native/Wasm 성공 호출까지 기록한다.
- 환경이 있으면 Linux x86_64/WSL과 ARM64 SDK도 같은 관점에서 smoke한다. 없는 target의 수치를 추측하지 않는다.
- C/C++ static ABI, no-import Wasm + JavaScript host, llama.cpp/model-facing adapter의 최소 통합을 각각 확인한다.
- 각 경로마다 time-to-first-success, 사용한 명령 수, 사람이 직접 판단/수정해야 한 단계 수, 숨은 prerequisite, 다운로드 크기, 설치 실패, 문서 모호성, 오류 메시지 품질, rollback/cleanup 난이도를 기록한다.
- Quickstart를 복사-붙여넣기 했을 때 그대로 성공하는지와, 실패하면 정확히 어느 줄/전제에서 실패하는지를 기록한다.
- 설치 편의를 위해 rc2 소스를 몰래 수정하지 않는다. workaround가 필요하면 먼저 package/docs defect로 기록하고, frozen rc2 결과와 분리된 후속 실험에서만 workaround를 사용한다.

성능 측정은 모델과 ExactScope 비용을 분해해라:
- model generation latency와 tokens in/out;
- tool-selection/JSON generation latency;
- host bridge overhead;
- ExactScope core execution latency;
- end-to-end latency p50/p95/p99와 cold/warm start;
- 반복 호출 throughput;
- 모델 파일 bytes와 ExactScope artifact bytes;
- 실제 측정 가능한 환경에서 process RSS/working set, CPU time, startup cost;
- 에너지는 이름이 명시된 실제 하드웨어와 측정법이 있을 때만 보고한다.
모든 latency는 충분한 warmup/iteration 수와 raw sample을 보존하고, 서로 다른 하드웨어/runtime의 숫자를 한 표에서 직접 우열처럼 비교하지 않는다.

제품 가치 판정에서 최소 다음을 계산/논의해라:
- A -> C 정확도/성공률 delta;
- A -> D delta;
- 추가 artifact byte당 성공률 개선;
- 추가 end-to-end ms당 성공률 개선;
- Qwen3.5 0.8B + ExactScope와 Qwen3.5 2B model-only의 비교;
- 독립 upper-small reference Phi-4-mini-instruct model-only와의 비교;
- extreme-small/edge 모델에서 ExactScope가 모델 업그레이드 대신 실질적으로 쓸 가치가 있는지.
단, 한 workload의 결과를 일반적인 모델 우열로 과장하지 않는다.

실패 taxonomy는 최소한 다음을 서로 분리한다:
- task recognition failure;
- wrong lane/tool selection;
- wrong semantic operation;
- wrong argument extraction/order;
- malformed schema/grammar output;
- model-side arithmetic/final-answer error;
- ExactScope typed runtime error;
- unsupported/refusal;
- token limit;
- timeout/runtime unavailable;
- harness/scorer defect.

fail-closed/robustness 실사용 smoke도 포함한다:
- malformed JSON/request;
- unknown/out-of-domain operation;
- oversized request/vector/plan;
- invalid decimal string;
- invalid argument count/type;
- unsupported feature.
각 케이스에서 crash, UB, hidden repair, stale numeric output 또는 성공으로의 조용한 coercion이 없는지 확인한다.

최종 산출물은 검증 작업공간에 최소 다음 이름으로 남겨라:
- `QUALIFICATION_REPORT_rc2.md`
- `INSTALLATION_UX_REPORT_rc2.md`
- `BENCHMARK_RESULTS_rc2.md`
- `PRODUCT_DECISION_rc2.md`
- `MODEL_INVENTORY_rc2.json`
- `TARGET_MEASUREMENTS_rc2.json`
- `FAILURE_TAXONOMY_rc2.json`
- `REPRODUCIBILITY_LOG_rc2.md`
각 raw run directory와 위 요약 파일을 hash로 연결하고, 성공 사례뿐 아니라 실패/invalidated run도 이유와 함께 보존한다.

최종 verdict는 하나의 모호한 PASS가 아니라 다음 gate별로 각각 판정한다:
- release identity / reproducibility;
- installation & documentation UX;
- native/Wasm/adapter integration;
- model benchmark efficacy;
- target performance/resource cost;
- fail-closed/security behavior.
전체 verdict는 `PASS integration candidate`, `PASS WITH RELEASE BLOCKERS`, `FAIL` 중 하나로 내리고 근거를 적는다.

완료 보고 형식:
1. exact release identity
2. release/package baseline 결과
3. installation UX 및 time-to-first-success
4. model inventory
5. preregistration identity
6. model별 A/C/D(+필요시 B) 결과와 failure decomposition
7. latency/resource/product-value 분석
8. target qualification 결과
9. fail-closed/robustness 결과
10. invalid/blocked 항목
11. rc2에서 사실로 주장할 수 있는 것
12. 아직 주장하면 안 되는 것
13. 최종 gate별 verdict와 go/no-go
14. 제품 수정이 필요하다면 rc2와 분리된 후속 candidate 제안 및 최소 재현

버그를 발견하면 최소 재현, 실제 결과, 기대 결과, 영향 범위를 기록하되 benchmark 도중 제품을 조용히 patch하지 마라. patch가 필요하면 frozen rc2 baseline을 먼저 완료/보존하고 새 candidate/run id로 분리한다.

Stable/support 승격, 새 release 발행, README 성능 claim 변경은 내가 명시적으로 요청하기 전에는 하지 마라.
```
