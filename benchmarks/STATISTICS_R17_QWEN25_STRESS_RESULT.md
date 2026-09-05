# Statistics r17 Qwen2.5 0.5B Stress Result

Status: **VALID, COMPLETE, INTERNAL EXPERIMENTAL LOWER-BOUND STRESS EVIDENCE**
Date: 2026-09-05
Run ID: `r17-qwen25-05b-stress`
Result directory: `benchmarks/output/statistics-r17-qwen25-05b-stress-v1`

This document interprets the preregistered Qwen2.5 0.5B stress run under the same frozen r17 Statistics corpus and serving contract used by the Qwen3 primary and Llama 3.2 secondary runs. It does not modify raw evidence.

## 1. Claim boundary

This run tests the lower edge of the current weak-model target range. It asks whether the reviewed Statistics surface still produces any measurable correctness uplift when the model is substantially weaker.

It is **not**:

- a public or independent benchmark score;
- evidence that every 0.5B model gains useful professional Statistics capability;
- a larger-model replacement comparison — this stress configuration has no E arm;
- target-device RAM, energy, thermal, or production qualification;
- proof that semantic-only or combined is universally the better surface.

The main result is deliberately modest: the reviewed Statistics surfaces move correctness from 0/144 to 10/144, but the absolute capability remains low.

## 2. Frozen identities

### Capability/runtime

- frozen serving source: `adapters/capabilities/statistics-core-8-ai-r17`
- accumulated evidence descendant: `adapters/capabilities/statistics-core-8-ai-r20`
- runtime artifact: **45,804 bytes**
- runtime SHA-256: `5381a32831e3eea1f4134267e341f57136e4d35d405e6d460f26b6846c051592`
- same-boundary calc-only baseline: **33,463 bytes**
- semantic marginal bytes: **12,341 bytes**
- Wasm imports: 0
- Wasm linear memory: initial=maximum=1 page
- support: `experimental`, not target-qualified

### Corpus/contract

- corpus: `benchmarks/statistics-r17-v0.1.jsonl`
- corpus SHA-256: `87ecec59161f5b44aa406ae0ca15a0ad258a47aa24555adac0e685418ebd6f60`
- items: 144; S1-S6 each contain 24 items
- model turns: 1
- temperature: 0
- seed: `20260917`
- output budget: **512 tokens for A/B/C/D equally**
- scoring: `final-line-v1`
- hidden retry or semantic repair: none
- E arm: intentionally absent in this preregistered lower-bound stress configuration

### Model

- Qwen2.5 0.5B Instruct, Q4_K_M
- model SHA-256: `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db`
- model bytes: 491,400,032
- context 4096, threads 4, GPU layers 99, parallel 1, reasoning none

Runtime: llama.cpp b10797, commit `832fd6f17`, desktop validation on Ryzen 5 5600G / RTX 3060 Ti 8 GiB / Windows.

## 3. Result integrity

- records: **576/576**
- A-D each contain 144 rows
- duplicate `(arm,id)` pairs: 0
- run status: `complete`
- summary SHA-256: `09b98630c82e841b3198a870914166dd5a70572ee7f49c8447477b4238069f5a`
- items SHA-256: `9a885c93e54e95de45d4509bb7a41f0f1ed065f6e1e07858dd1d11a761c554ec`
- metadata SHA-256: `3ea6f7c7153bc9237e12492c4b4a401dc9f8363c704712a4bca25b8a978d7310`

The completed result is attached as evidence-only revision r20:

- r20 manifest SHA-256: `451371f5727c60f66862e7f0f75fa26da8a6190509f9bcc195464ae3fcb1e42b`
- latest attached model-evidence SHA-256: `e6e3273861f2a5492e22839265ab81f726a5e2e641d14bc658efdd2447641f80`
- accumulated model evidence count: **3**
- parent r19 manifest SHA-256: `83ac3e742a5d9dc31161ec7d7919c17c7397d9cea07bebc706466704f4a27df2`

r20 accumulates Qwen3, Llama 3.2, and Qwen2.5 stress evidence without changing the r17 serving runtime.

## 4. Primary result

| Arm | Surface | Correct | Accuracy | Wrong numeric |
| --- | --- | ---: | ---: | ---: |
| A | Qwen2.5 0.5B only | 0 / 144 | **0.00%** | 17 / 144 |
| B | 0.5B + `xs_calc` | 0 / 144 | **0.00%** | 106 / 144 |
| C | 0.5B + Statistics `xs_eval` only | 10 / 144 | **6.94%** | 21 / 144 |
| D | 0.5B + `xs_calc` + Statistics `xs_eval` | 10 / 144 | **6.94%** | 25 / 144 |

The Statistics surfaces C and D both exceed A and B on correct answers, but 10/144 is still a weak absolute result. This run therefore establishes a lower-bound warning as much as an uplift signal.

## 5. What failed

Most correct answers came from only two task families:

| Family | A | B | C | D |
| --- | ---: | ---: | ---: | ---: |
| S1 sum / mean | 0 | 0 | 0 | 0 |
| S2 weighted mean | 0 | 0 | 0 | 0 |
| S3 variance | 0 | 0 | 0 | 0 |
| S4 standard deviation | 0 | 0 | 0 | 0 |
| S5 Pearson correlation | 0 | 0 | 5 | **6** |
| S6 ambiguity / typed failure | 0 | 0 | **5** | 4 |

For C, 100/144 outcomes are classified `wrong_error`; for D, 101/144 are `wrong_error`. The model often chose to emit an error instead of successfully using the available semantic operation. This is a model-interface limitation, not a deterministic-core calculation failure.

Measured operation selection and argument extraction were also weak:

- C operation selection: 19/29 = 65.5%
- C argument extraction: 6/29 = 20.7%
- D operation selection: 18/33 = 54.5%
- D argument extraction: 7/33 = 21.2%

The deterministic executor cannot recover a capability the model cannot reliably select or parameterize.

## 6. Surface-selection result

C and D tie at 10/144. Therefore this stress run provides no evidence that semantic-only or combined is the better surface for Qwen2.5 0.5B.

Across all three completed model configurations:

| Small model | A | B | C | D | Measured C/D relationship |
| --- | ---: | ---: | ---: | ---: | --- |
| Qwen3 0.6B Q8_0 | 0 | 0 | **111** | 97 | C > D by 14 |
| Llama 3.2 1B Q4_K_M | 0 | 3 | 22 | **24** | D > C by 2 |
| Qwen2.5 0.5B Q4_K_M | 0 | 0 | **10** | **10** | tie |

The product rule is now clearer:

> **Capability-surface selection must be target-model and task-family qualified. ExactScope should support multiple minimal surfaces, but no surface should be assumed useful merely because the deterministic operations exist.**

## 7. Wrong-numeric counts are not a cross-model headline

A has only 17 wrong-numeric records, while D has 25. This does not mean the tool makes the model numerically worse: A fails mostly through missing final lines and token limits, while tool arms more often reach structured outcomes.

Therefore the Qwen3 wrong-number reduction must remain a Qwen3-specific observation. It is not replicated across the current three-model evidence set.

## 8. Latency observations

Desktop mean model/model+bridge latency:

- A: ~1,295.5 ms
- B: ~447.7 / 456.9 ms
- C: ~253.8 / 256.0 ms
- D: ~179.7 / 182.0 ms

The tool arms are faster here largely because the constrained outputs are much shorter. That is a run-specific desktop observation, not an on-device latency claim.

## 9. What the three-model evidence now supports

The strongest safe cross-model statement is:

> **Across three preregistered synthetic internal development runs on the same frozen Statistics contract, reviewed Statistics surfaces improved correct-answer count over the corresponding small-model-only baseline, but the uplift ranged from 10/144 to 111/144 and the best C/D surface was model-dependent.**

That is a stronger engineering result than a single impressive score because it identifies both the opportunity and the failure boundary.

It does **not** support:

- a universal 77% Statistics accuracy claim;
- a universal larger-model replacement claim;
- a universal semantic-only preference;
- a universal wrong-number reduction claim;
- target RAM, energy, thermal, battery, or hardware-life claims.

## 10. Next evidence and product work

1. Treat the preregistered r17 model evidence set as complete and preserve it unchanged.
2. Make model-facing surface selection a first-class capability-profile/evaluation output.
3. Generalize operation identity, input shape, build feature, kernel dispatch, and direct op-ID metadata into one source of truth.
4. Add externally reviewed/public task evidence before broadening marketing claims.
5. Qualify one representative ARM64/embedded target for resident memory, stack/scratch, latency distributions, and energy.

Do not tune the frozen r17 corpus, prompts, token budget, or scoring based on these completed results.
