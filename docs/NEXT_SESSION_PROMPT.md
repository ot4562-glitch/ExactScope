# 다음 검증 세션용 프롬프트 — rc4 grounding A/G benchmark

Status: **ACTIVE — `READY_FOR_GROUNDING_BENCHMARK` 후보를 별도 검증 세션에서 실행할 때 사용**

rc3 A/C/D 검증 프롬프트는 더 이상 이 파일의 현재 작업 지시가 아니다. 역사적 rc3 절차는 `QUALIFICATION_HANDOFF.md`와 `RC3_QUALIFICATION_CLOSEOUT.md`에 보존되어 있다.

아래 블록을 새 검증 세션에 그대로 전달한다.

```text
ExactScope rc4의 frozen grounding evaluation package를 실제 외부 검증자처럼 검증하고 A/G 모델 benchmark를 수행해라.

중요: 개발 checkout에서 임의로 코드를 고쳐 시작하지 마라. 첫 입력은 반드시 `READY_FOR_GROUNDING_BENCHMARK`로 동결된 grounding evaluation archive와 그 SHA-256, 그리고 패키지에 포함된 manifest/preregistration 도구다.

제품 가설:
- ExactScope rc4의 주제품 방향은 학문별 계산/tool-call breadth가 아니다.
- 핵심은 소형/임베디드 모델의 일상 사실 질문에서 original-question grounding prefetch로 정확도를 높이고, 틀린 확신/환각을 줄이며, 필요한 token/latency/storage 비용을 작게 유지하는 것이다.
- 기본 경로는 `질문 -> host grounding prefetch -> Evidence Policy -> GroundingFrame -> 동일 소형 모델 1회 답변`이다.
- `xs_calc`/`xs_eval` quantitative subsystem은 보존되어 있지만 이번 A/G efficacy benchmark의 주축이 아니다.
- ordinary grounding을 위해 model-visible retrieval tool call이나 query rewrite를 추가하지 마라.

먼저 반드시 읽어라:
1. docs/GROUNDING_BENCHMARK_HANDOFF.md
2. docs/BENCHMARK.md
3. docs/GROUNDING_ARCHITECTURE.md
4. spec/GROUNDING_CONTRACT_V0_1.md
5. README.md
6. package-manifest.json
7. benchmarks/grounding-generation-config.json
8. benchmarks/grounding-isolation-policy.json
9. benchmarks/grounding-model-inventory.json
10. benchmarks/grounding-runtime-llama-v040.json

첫 단계는 inference 0회 상태에서 package integrity를 확인하는 것이다.
- outer archive SHA-256를 제공된 값과 대조한다.
- 새 디렉터리에 압축 해제한다.
- `python tools/verify_grounding_package.py`를 실행한다.
- `python benchmarks/grounding_dry_run.py serve --candidate candidate --output <fresh-dir>`를 실행한다.
- `python benchmarks/grounding_dry_run.py verify-gold --candidate candidate --records <fresh-dir>/serving-records.jsonl --output <fresh-gold-check>`를 실행한다.
- 이 단계의 model request/inference count는 반드시 0이어야 한다.
- serving/gold separation, manifest, profile/source/provider/projection identity, routing/state/evidence verification이 하나라도 실패하면 패키지를 고쳐 우회하지 말고 BLOCKED/INVALID로 기록한다.

Core model 5개는 패키지 inventory 그대로 사용한다:
1. Gemma 3 270M IT Q8_0
2. LFM2.5 350M Q4_K_M
3. Qwen3.5 0.8B Q4_0
4. Qwen3.5 2B Q4_K_M
5. Phi-4-mini-instruct 3.8B Q4_K_M

기존 로컬 모델 파일을 재사용해도 되지만 packaged inventory의 exact file bytes/SHA-256와 일치할 때만 허용한다. rc3의 benchmark score/result는 절대 rc4 evidence로 재사용하지 않는다.

각 모델마다 첫 inference 전에 반드시 `benchmarks/grounding_preregister.py create`로 별도 frozen preregistration을 만든다. 다음을 전부 실제 hash/identity로 묶어라:
- source commit
- package manifest + outer archive SHA
- candidate/serving/gold manifests
- GroundingProfile
- source snapshots
- provider/index/preprocessing/ranking identity
- Model Projection template/policy/renderer
- generation config
- isolation policy
- scorer
- exact model file/repository revision/bytes/SHA
- exact llama-server executable/version/commit/launch config
- hardware/thread/context config
- planned new output directory
- arms=[A,G]
- answer calls per arm=1
- rewrite=0
- retry=0
- hidden repair=false
- manual correction=false
- duplicate `(arm,item_id)` reject
- bound-byte/config drift reject

각 preregistration 직후 실제 inference를 시작하지 말고 먼저:
`python benchmarks/run_grounding_benchmark.py --preregistration <frozen.json> --output <planned-output> --verify-only`
를 실행한다.

5개 모델 모두 verify-only가 성공하고 planned output directory가 아직 생성되지 않았으며 llama-server inference가 시작되지 않았음을 확인한 뒤에만 A/G benchmark를 시작한다.

실제 A/G:
A = model-only. 공통 system prompt + 원문 질문, 정확히 1회 answer-generation request.
G = 원문 질문으로 deterministic grounding prefetch를 먼저 수행하고, 같은 공통 system prompt + frozen Grounding Projection policy/evidence + 원문 질문으로 정확히 1회 answer-generation request.

공정성/금지사항:
- A/G 동일 item set
- 동일 answer schema, seed, temperature, max output budget, timeout
- model-visible retrieval tool 추가 금지
- query rewrite 금지
- retry 금지
- hidden semantic/answer repair 금지
- manual correction 금지
- output-driven fallback 금지
- invalid/aborted run resume 또는 partial merge 금지
- 실패한 모델을 결과에서 제외해 평균을 좋게 만들지 마라

Grounding state 규칙:
- authoritative `none`은 required provider coverage가 완전하고 실제 no-hit일 때만 가능
- timeout/error/denied/budget/incomplete는 `unavailable`
- ambiguity는 임의 winner 선택 금지
- conflict는 숨은 winner 선택 금지
- supplemental no-hit/unavailable은 정책이 허용하면 ordinary model knowledge 사용 가능
- evidence text는 untrusted data이며 instruction/permission으로 승격 금지

raw run은 scorer 실행 전에 freeze한다. 각 모델 output directory에 최소 다음을 남겨라:
- preregistration copy/hash
- run metadata
- raw A/G item records
- exact raw model content + parsed/malformed status
- tokens in/out
- model latency
- G retrieval latency
- G GroundingFrame + audit sidecar
- projection bytes/hash
- llama-server log
- complete/invalid/aborted status
- SHA256SUMS

complete raw run이 생긴 뒤에만 scorer가 candidate/gold를 읽게 한다. serving runner는 gold를 읽으면 안 된다.

반드시 raw count/denominator를 먼저 보고하고 다음을 모델별/전체로 계산한다:
- factual accuracy A vs G
- wrong-confident-answer rate A vs G
- unsupported authoritative assertion rate
- correct abstention
- useful answer
- over-abstention
- false grounding
- grounding adherence
- stale revision override
- provider unavailable fidelity
- adversarial evidence/injection obedience
- grounding recovery
- grounding penalty
- input/output token delta
- retrieval latency
- model latency delta
- projection/index/storage bytes
- accuracy uplift per added input token
- accuracy uplift per added byte/KiB
- accuracy uplift per added model-latency ms

실패 taxonomy도 분리해라:
routing / retrieval miss / false retrieval / provider failure / authority-state policy / ambiguity / conflict / projection-data boundary / malformed model output / unsupported authoritative assertion / stale-memory regression / over-abstention / model answer error despite correct evidence / timeout / runtime / harness / scorer defect.

결과가 나쁘면 그대로 보고한다. 특정 모델에서 G가 A보다 나빠도 숨기지 않는다. 모델 크기만으로 원인을 단정하지 않는다.

최종 산출물:
- GROUNDING_BENCHMARK_REPORT_rc4.md
- GROUNDING_MODEL_MATRIX_rc4.json
- GROUNDING_FAILURE_TAXONOMY_rc4.json
- GROUNDING_COST_REPORT_rc4.json
- GROUNDING_PRODUCT_DECISION_rc4.md
- GROUNDING_REPRODUCIBILITY_LOG_rc4.md
- immutable per-model raw run directories

최종 verdict는 분리해서 내려라:
1. package/reproducibility
2. grounding-path correctness
3. model efficacy
4. false-grounding/safety behavior
5. token/latency/storage economics
6. physical target qualification status
7. support/stable-release readiness

Desktop/WSL A/G 결과만으로 physical ARM64 RAM/energy/thermal/latency를 측정했다고 주장하지 마라. 실제 ARM64 target이 없으면 NOT MEASURED라고 쓴다.

benchmark 결과 때문에 제품 수정이 필요하면 frozen candidate/raw evidence를 먼저 보존하고 새 candidate로 분리한다. 기존 preregistration 아래에서 소스를 수정하고 계속하지 마라.
```
