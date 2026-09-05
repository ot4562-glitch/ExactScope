# Statistics r17 Llama 3.2 Secondary Result

Status: **VALID, COMPLETE, INTERNAL EXPERIMENTAL REPLICATION EVIDENCE**
Date: 2026-09-05
Run ID: `r17-llama32-family-secondary`
Result directory: `benchmarks/output/statistics-r17-llama32-secondary-v1`

This document interprets the completed Llama 3.2 replication under the same frozen r17 Statistics corpus and serving contract used by the Qwen3 primary run. It does not modify raw benchmark evidence.

## 1. Claim boundary

This run asks whether the direction of the Qwen3 capability result survives a second small-model family, and whether the best model-facing surface is stable across models.

It is **not**:

- a public or independent benchmark score;
- proof that Llama 3.2 1B can generally replace Llama 3.2 3B;
- proof that semantic-only or combined tools are universally better;
- target-device memory, energy, thermal, or production qualification;
- evidence that `xs_calc` is incorrect.

The most important result is that reviewed Statistics tools again improve correct-answer count over the small-model-only and calculator-only baselines, but **the preferred surface ordering differs from Qwen3**.

## 2. Frozen identities

### Capability/runtime

- frozen serving source: `adapters/capabilities/statistics-core-8-ai-r17`
- accumulated evidence descendant: `adapters/capabilities/statistics-core-8-ai-r19`
- runtime artifact: **45,804 bytes**
- runtime SHA-256: `5381a32831e3eea1f4134267e341f57136e4d35d405e6d460f26b6846c051592`
- calc-only same-boundary baseline: **33,463 bytes**
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
- output budget: **512 tokens for A/B/C/D/E equally**
- scoring: `final-line-v1`
- hidden retry or semantic repair: none

### Models

Small model:

- Llama 3.2 1B Instruct, Q4_K_M
- SHA-256: `6f85a640a97cf2bf5b8e764087b1e83da0fdb51d7c9fab7d0fece9385611df83`
- file bytes: 807,694,464
- context 4096, threads 4, GPU layers 99, parallel 1, reasoning none

Larger same-family reference:

- Llama 3.2 3B Instruct, Q4_K_M
- SHA-256: `6c1a2b41161032677be168d354123594c0e6e67d2b9227c84f296ad037c728ff`
- file bytes: 2,019,377,696
- context 4096, threads 4, GPU layers 99, parallel 1, reasoning none

Runtime: llama.cpp b10797, commit `832fd6f17`, desktop validation on Ryzen 5 5600G / RTX 3060 Ti 8 GiB / Windows.

## 3. Result integrity

- records: **720/720**
- 144 rows per arm
- duplicate `(arm,id)` pairs: 0
- run status: `complete`
- summary SHA-256: `cc9bf767f114337b0f8a559578b5388acad54359d440463b7fc89db2e0bfdf0b`
- items SHA-256: `59cec98e98420cb412297ef778bcdd326de15170ad823c2375c9d3d0d757b4f3`
- metadata SHA-256: `049971486e657ac1c06c3d80c5320c4098e7fd35123977d776be88ff94685c2a`

The result was attached as evidence-only revision r19:

- r19 manifest SHA-256: `83ac3e742a5d9dc31161ec7d7919c17c7397d9cea07bebc706466704f4a27df2`
- latest attached model-evidence SHA-256: `ae9e1403ee5c331b48824e84973c36bd5cb2e5de0c91267eb933283ea3789154`
- model evidence count: 2
- parent r18 manifest SHA-256: `32c8060303788e160ddffd91005a01a4f62a143faa8465162a5c0043d910015a`

r19 accumulates Qwen3 and Llama 3.2 model evidence while preserving the exact r17 serving contract and 45,804-byte runtime.

## 4. Primary result

| Arm | Surface | Correct | Accuracy | Wrong numeric |
| --- | --- | ---: | ---: | ---: |
| A | Llama 3.2 1B only | 0 / 144 | **0.00%** | 10 / 144 |
| B | 1B + `xs_calc` | 3 / 144 | **2.08%** | 101 / 144 |
| C | 1B + Statistics `xs_eval` only | 22 / 144 | **15.28%** | 111 / 144 |
| D | 1B + `xs_calc` + Statistics `xs_eval` | 24 / 144 | **16.67%** | 105 / 144 |
| E | Llama 3.2 3B only | 20 / 144 | **13.89%** | 45 / 144 |

The reviewed Statistics surfaces C and D both exceed the small-model-only A and calculator-only B baselines on correct answers.

However, the absolute gain is much smaller than in the Qwen3 run. This matters: the replication supports the **direction of capability gain**, not a universal 77% result.

## 5. Cross-model surface result

The central design finding is the reversal between Qwen3 and Llama 3.2.

| Model family | C semantic-only | D combined | Preferred measured surface |
| --- | ---: | ---: | --- |
| Qwen3 0.6B | **111 / 144** | 97 / 144 | C by 14 |
| Llama 3.2 1B | 22 / 144 | **24 / 144** | D by 2 |

Therefore:

> **ExactScope should not hard-code a universal assumption that semantic-only or combined tools are always best. The capability compiler should support multiple model-facing surfaces and choose among them using target-model evidence.**

The Qwen result suggested that fewer visible choices can help a weak model. The Llama result shows that this is not a universal ordering. The stronger product rule is **measured model/task-specific surface minimization**.

## 6. Family breakdown

Each family contains 24 items.

| Family | A | B | C | D | E |
| --- | ---: | ---: | ---: | ---: | ---: |
| S1 sum / mean | 0 | 2 | 9 | **11** | **12** |
| S2 weighted mean | 0 | 0 | 0 | 0 | 3 |
| S3 variance | 0 | 0 | 10 | **11** | 2 |
| S4 standard deviation | 0 | 0 | **1** | 0 | 0 |
| S5 Pearson correlation | 0 | 0 | 1 | 1 | 0 |
| S6 ambiguity / typed failure | 0 | 1 | 1 | 1 | 3 |

Weighted mean remains a complete failure for both C and D on this model, while variance and basic sum/mean account for most tool-assisted correct answers. This reinforces the need to benchmark task-family coverage rather than treating operation count as capability.

## 7. Failure behavior matters

Wrong-numeric counts must not be compared naively across A and tool arms.

Llama A has only 10 wrong-numeric records because most failures are formatting/token-contract failures:

- missing final line: 94
- token limit: 33
- malformed final line: 4
- multiple final lines: 1
- wrong error: 2

By contrast, tool arms emit structured calls and therefore produce numeric outcomes more often. D has 105 wrong-numeric records while still improving correct answers from 0 to 24.

Therefore this replication **does not reproduce Qwen's wrong-number reduction claim**. Marketing must not say that ExactScope universally reduces wrong numeric outputs across models based on these two runs.

## 8. Larger-model reference

E scores 20/144, while D scores 24/144. The paired summary computes CRR 1.2.

Do **not** use this as a larger-model replacement claim. E has substantial output-contract failures:

- token limit: 35
- missing final line: 37
- wrong numeric: 45

The result is useful as a frozen technical reference only.

## 9. Latency observations

Desktop mean model latency from this run:

- A 1B model-only: ~2,067.8 ms
- B calc-only: ~882.0 ms model time
- C semantic-only: ~1,476.3 ms model time
- D combined: ~867.0 ms model time
- E 3B model-only: ~3,866.6 ms

Core-bridge time is about 9-10 ms when invoked. These values are highly model/runtime/desktop specific and are not target-device qualification.

Interestingly, D is faster than C in this run because its constrained outputs are much shorter on average. That is an empirical observation, not a general latency property of the combined surface.

## 10. What the two-model evidence now supports

The strongest safe cross-family statement is:

> **In two completed synthetic internal development runs under the same frozen Statistics contract, reviewed Statistics tool surfaces produced more correct answers than the corresponding small-model-only and calculator-only baselines. The magnitude of improvement and the best model-facing surface differed substantially by model.**

This is more useful to the product than a universal single-score claim. It supports a compiler/qualification workflow that selects a capability slice **for a target model and task family**.

## 11. Next evidence

1. Run the preregistered Qwen2.5 0.5B stress configuration without changing the frozen corpus or scoring contract.
2. Make semantic-only vs combined surface selection a first-class capability profile/evaluation choice.
3. Add domain-general operation metadata so new domains require less duplicated plumbing.
4. Add externally reviewed or public task evidence before broadening marketing claims.
5. Measure RAM, stack/scratch, latency distributions, and energy on a representative constrained target.

Do not tune the frozen r17 corpus, prompt, token budget, or scoring based on these completed results before the remaining preregistered stress run.
