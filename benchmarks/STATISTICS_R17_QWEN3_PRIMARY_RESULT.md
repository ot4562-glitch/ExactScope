# Statistics r17 Qwen3 Primary Result

Status: **VALID, COMPLETE, INTERNAL EXPERIMENTAL EVIDENCE**
Date: 2026-09-05
Run ID: `r17-qwen3-family-primary`
Result directory: `benchmarks/output/statistics-r17-qwen3-primary-v3`

This document interprets the frozen v3 result. It does not modify or replace raw benchmark evidence. The synthetic corpus, benchmark harness snapshot, runtime artifact, model identities, and scoring contract are bound by the result metadata and summary hashes below.

## 1. Claim boundary

This run tests whether a tiny, reviewed Statistics capability surface can recover useful quantitative capability for a constrained Qwen3 0.6B model under one frozen synthetic Statistics corpus and one strict one-turn contract.

It is **not**:

- a public benchmark score;
- target-device RAM or energy qualification;
- a general proof that a 0.6B model plus ExactScope replaces a 1.7B model;
- evidence that every domain should expose the same tools;
- evidence that `xs_calc` is intrinsically harmful.

The most important product-level result is narrower: for this weak model and this frozen task distribution, the semantic-only Statistics surface was materially better than both model-only execution and the larger combined `xs_calc + xs_eval` surface.

## 2. Frozen identities

### Capability/runtime

- capability profile: `statistics-core-8-ai`, revision 17
- bound bundle: `adapters/capabilities/statistics-core-8-ai-r17`
- runtime artifact: **45,804 bytes**
- runtime artifact SHA-256: `5381a32831e3eea1f4134267e341f57136e4d35d405e6d460f26b6846c051592`
- same-boundary calc-only baseline: `statistics-calc-only-baseline-r3`
- calc-only artifact: **33,463 bytes**
- semantic marginal artifact bytes: **12,341 bytes**

### Corpus/contract

- corpus: `benchmarks/statistics-r17-v0.1.jsonl`
- corpus SHA-256: `87ecec59161f5b44aa406ae0ca15a0ad258a47aa24555adac0e685418ebd6f60`
- items: 144, with S1-S6 each containing 24 items
- executable gold calls: 132
- generation: temperature 0, seed 20260917, one model turn
- output budget: **512 tokens for A/B/C/D/E equally**
- baseline mode: `reasoning`
- scoring contract: `final-line-v1`
- hidden retries/semantic repair: none

### Models

Small model:

- Qwen3 0.6B, Q8_0
- model SHA-256: `9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031`
- model bytes: 639,446,688
- context 4096, threads 4, GPU layers 99, parallel 1, reasoning off

Larger reference:

- Qwen3 1.7B, Q8_0
- model SHA-256: `061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a`
- model bytes: 1,834,426,016
- context 4096, threads 4, GPU layers 99, parallel 1, reasoning off

Runtime: llama.cpp b10797, commit `832fd6f17`, desktop validation on Ryzen 5 5600G / RTX 3060 Ti 8 GiB / Windows.

### Result integrity

- records: **720/720**, 144 per arm
- run status: `complete`
- summary SHA-256: `c9587518f25a4b3fc0caaf8cbf6e460ab62fe390c2a29c36b5c6229ab66e8b51`
- items SHA-256: `a13ea8ead6c01d3a6b294f9f89ff942550f3758bc9a1ba5732721c2f5c9b26fe`
- metadata SHA-256: `6d5f0eec21481d1c04168b547f0fe69cacfe5e79408ce00791ef5dbc77bfc62e`
- frozen harness SHA-256: `f522cc016b06685aeb08f0409647e022feddaed6fb335a3b584e4e988c287768`
- single-writer mechanism: Windows `msvcrt.locking`

During the final E-arm execution, a duplicate invocation attempted to target the same output. The OS-level single-writer lock rejected the competing writer while the valid writer completed the run. There are no duplicate `(arm,id)` records. After completion the sidecar lock was successfully reacquired/released and no `llama-server.exe` remained running.

### Evidence-only attachment

The completed v3 result is now attached without changing the serving runtime as:

- evidence bundle: `adapters/capabilities/statistics-core-8-ai-r18`
- profile revision: **18**
- support: `experimental` (unchanged)
- r18 manifest SHA-256: `32c8060303788e160ddffd91005a01a4f62a143faa8465162a5c0043d910015a`
- model evidence SHA-256: `1828453a609d31b84e4228964b10dd7b91240471b1988db51e938acd94053174`
- benchmark source anchor: r17 manifest SHA `516a3fe1421b80643b4b4f512e1f36ed5f9defe2f41453954967ea843e9557e3`, profile revision 17
- serving-contract SHA-256: `dd96b357bf53c657affac2a91c5dc95d083e83dc325c2b928cab467cebc70cba`

r18 preserves the same 45,804-byte runtime artifact and original runtime-conformance mapping. The attached model evidence separately binds the frozen external corpus, preregistration, corpus manifest/generator, model inventory, raw rows, summary/metadata/harness, and the verified calc-only r3 semantic baseline. Evidence snapshots use a digest namespace so later preregistered runs can append in r19/r20 while remaining anchored to the exact r17 serving contract.

## 3. Primary result

| Arm | Surface | Correct | Accuracy | Wrong numeric |
| --- | --- | ---: | ---: | ---: |
| A | Qwen3 0.6B only | 0 / 144 | **0.00%** | 133 / 144 |
| B | 0.6B + `xs_calc` | 0 / 144 | **0.00%** | 79 / 144 |
| C | 0.6B + Statistics `xs_eval` only | 111 / 144 | **77.08%** | 21 / 144 |
| D | 0.6B + `xs_calc` + Statistics `xs_eval` | 97 / 144 | **67.36%** | 25 / 144 |
| E | Qwen3 1.7B only | 24 / 144 | **16.67%** | 59 / 144 |

A to D reduces wrong-numeric outcomes from **92.36% to 17.36%**, an absolute reduction of **75 percentage points**.

The summary's paired CRR for D is **4.0417** because A=0%, D=67.36%, and E=16.67%. This number is valid for this preregistered contract, but it must not be promoted into a general larger-model replacement claim. The 1.7B E arm had 46 token-limit failures, and the corpus is synthetic/internal.

## 4. Most important design finding: C > D

The semantic-only C arm outperformed the combined D arm:

- C: **111/144 = 77.08%**
- D: **97/144 = 67.36%**
- difference: **14 items / 9.72 percentage points** in favor of C

D actually had slightly stronger measured operation selection than C, but much worse argument extraction:

- C operation selection: 123/130 = 94.62%
- D operation selection: 126/128 = 98.44%
- C argument extraction: 118/130 = 90.77%
- D argument extraction: 98/128 = 76.56%

This is consistent with the product thesis that a weak model benefits from a smaller, task-specific tool surface. A plausible hypothesis is model-facing surface/prompt interference: adding generic `xs_calc` alongside reviewed Statistics semantics gives the 0.6B model more routing/decomposition freedom and harms extraction on some families. This run does **not** prove that causal mechanism; it only establishes the measured surface-level difference.

Product implication: the capability compiler should be able to emit semantic-only domain hotsets and should not automatically expose `xs_calc` next to every domain pack.

## 5. Family breakdown

Each family contains 24 items.

| Family | A | B | C | D | E |
| --- | ---: | ---: | ---: | ---: | ---: |
| S1 sum / mean | 0 | 0 | **24** | 23 | 15 |
| S2 weighted mean | 0 | 0 | **16** | 5 | 3 |
| S3 variance | 0 | 0 | 20 | **22** | 2 |
| S4 standard deviation | 0 | 0 | 20 | **21** | 0 |
| S5 Pearson correlation | 0 | 0 | **20** | 18 | 0 |
| S6 ambiguity / typed failure | 0 | 0 | **11** | 8 | 4 |

The largest C-vs-D regression is weighted mean (S2): **16 correct vs 5**. D slightly improves variance and standard deviation, but C wins S1, S2, S5, and S6. This argues for model/task-family-specific surface selection rather than a universal maximal hotset.

## 6. Cost and capability-density observations

For D versus A:

- correctness uplift: **+0.673611**
- total component bytes: **45,804 B**
- semantic marginal bytes: **12,341 B**
- mean prompt-token delta: **+113 tokens**
- mean model+bridge latency delta on this desktop: **+344.656 ms**
- resident RAM delta: unmeasured
- energy delta: unmeasured

Summary density values:

- total artifact density: **1.50593 uplift units / 100 KiB**
- semantic marginal byte density: **5.58932 uplift units / 100 KiB**
- wrong-number reduction density, total artifact: **1.67671 / 100 KiB**
- wrong-number reduction density, semantic marginal: **6.22316 / 100 KiB**

These values should be reported with their raw numerator and denominator. They are not yet a single universal `Capability Density` scalar.

## 7. Latency observations

Desktop mean latency:

- A model-only: ~70.4 ms
- C semantic-only: ~415.5 ms including bridge
- D combined: ~415.0 ms including bridge
- E 1.7B model-only: ~3,390.5 ms

This is useful relative desktop evidence only. It is not wearable/phone/embedded latency, RAM, thermal, or energy qualification.

## 8. What this run says about `xs_calc`

B produced 144 syntactically valid plans but 0 correct Statistics answers. Of those, 79 plans executed to a wrong result and 65 were rejected by the runtime. This is not evidence that the arithmetic core is incorrect. It shows that the 0.6B model could not reliably infer the required Statistics semantics and decomposition using only the generic calculator surface.

The result reinforces the architectural separation:

- use `xs_calc` when the model already knows the arithmetic decomposition;
- use reviewed `xs_eval` operations when method identity/domain semantics matter;
- for weak models, expose the smallest surface that covers the target task family.

## 9. Limitations and next evidence

Before turning this into stronger product claims:

1. Replicate the same frozen contract on the preregistered Llama 3.2 1B -> 3B pair.
2. Run the preregistered Qwen2.5 0.5B stress arm.
3. Add an explicit semantic-only/minimal-surface benchmark as a first-class product profile, rather than treating D as the assumed primary arm.
4. Measure RAM, stack/scratch, latency distribution, and energy on a representative constrained target.
5. Keep the public claim boundary narrow until independent/public benchmark and real-device evidence exists.

Do not tune the frozen r17 corpus, prompts, token budget, or scoring contract based on this result before the preregistered replication runs.
