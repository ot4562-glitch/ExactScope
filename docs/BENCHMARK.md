# ExactScope benchmark and qualification contract

Release context: **v1.0.0-rc.2**
Status: **planned/unmeasured for rc2; execute from the immutable public release in a later session**

ExactScope must earn adoption with reproducible evidence. Deterministic code alone does not prove that a small model can select the right operation, extract the right arguments, or gain enough capability to justify integration cost.

The central product question is:

> For an existing constrained/on-device model, does a tiny selected ExactScope surface improve end-to-end narrow quantitative capability enough to justify its exact binary, model-interface, latency, memory, energy, integration, and qualification cost?

The canonical rc2 continuation procedure is [`QUALIFICATION_HANDOFF.md`](QUALIFICATION_HANDOFF.md). The minimum model matrix is [`../benchmarks/NEXT_MODEL_MATRIX.md`](../benchmarks/NEXT_MODEL_MATRIX.md).

## 1. Evidence boundary

A benchmark result belongs only to the exact combination of:

- ExactScope Git tag/commit;
- source/release archive SHA-256;
- ExactScope runtime/capability/model-surface artifact digests;
- operation revisions and selected surface;
- model repository revision and model-file SHA-256;
- inference runtime/build/command line;
- corpus/generator/mapping digest;
- prompt/system/tool/schema/GBNF bytes and digests;
- generation settings;
- scoring/failure policy;
- raw output records.

Changing one of those creates a new run identity. Do not silently inherit a score across candidates.

Historical `statistics-core-8-ai-r20` evidence is tied to an older **45,804-byte r17 Statistics serving runtime**. It is historical development evidence only, not rc2 evidence.

## 2. Preregister before inference

Freeze the following before the first model request:

1. exact rc2 release/tag/commit and all release-asset hashes;
2. exact capability/profile/model-surface identity;
3. model inventory including repository revision, file name, bytes and SHA-256;
4. inference runtime build/version and launch command;
5. hardware/thread/device configuration;
6. corpus bytes/SHA-256, generator revision, task-family allocation and item count;
7. system/prompt text, chat-template behavior and tool/schema/GBNF assets;
8. context size, temperature, seed, max generated tokens and all sampling settings;
9. comparison arms;
10. failure taxonomy/scoring rules;
11. timeout/retry/no-hidden-repair rules;
12. single-writer/duplicate policy;
13. any fixed early-stop/futility rule.

If a policy is changed after results are seen, create a new run rather than rewriting the preregistration.

## 3. Minimum rc2 model matrix

The rc2 core matrix deliberately uses five models rather than a large leaderboard sweep:

| Model | Role |
|---|---|
| Gemma 3 270M IT Q8_0 | extreme-small independent lower bound |
| LFM2.5 350M Q4_K_M | edge/on-device-first lower bound |
| Qwen3.5 0.8B Q4_0 | primary modern sub-1B model |
| Qwen3.5 2B Q4_K_M | controlled same-family scaling point |
| Phi-4-mini-instruct 3.8B Q4_K_M | independent upper-small reference |

Optional, separately reported product profile: **Gemma 3n E2B IT**. It is gated/multimodal/runtime-specific and must not be mixed into the core GGUF table unless the runtime/text-only contract is made genuinely comparable.

The machine-readable list is `benchmarks/model-downloads.json`. Download with `tools/fetch_benchmark_models.py`; preserve its `model-inventory.json` unchanged with the run.

## 4. Primary comparison arms

Use the minimum useful surface comparison for each task family:

| Arm | Surface | Purpose |
|---|---|---|
| A | model only | baseline end-to-end capability |
| C | selected semantic `xs_eval` only | isolates reviewed method value |
| D | `xs_calc + xs_eval` only when the selected profile exposes both | target combined profile |
| B | `xs_calc` only, optional diagnostic | isolates generic exact arithmetic value |

Do not add `xs_find` to the normal serving benchmark just because discovery exists. Discovery can be a separate ablation when a product decision actually depends on it.

Do not automatically add a still-larger E model to every row. The five-model matrix already includes an upper-small independent reference; add a bigger reference only when it answers a specific product/hardware decision and the comparison is fair.

## 5. Fairness rules

Comparable arms must use the same:

- item set;
- model revision/quantization;
- runtime/build;
- context budget;
- sampling policy;
- generation-token budget;
- scoring rule;
- target hardware for latency/resource comparisons.

No hidden semantic repair, result repair, manual answer correction, or repeated “try until valid” behavior is allowed unless a retry policy was frozen before the run.

A deterministic ExactScope call can be correct while the overall item is wrong because the model selected the wrong operation/arguments. Score the end-to-end task, not only tool execution.

## 6. Workloads

### 6.1 Controlled Statistics capability corpus

`benchmarks/statistics_corpus.py` deterministically generates/checks the 240-case synthetic Statistics corpus used for controlled method-selection/extraction work. It contains supported numeric cases and explicit ambiguity/unsupported cases and uses an independent Fraction/Decimal oracle for gold construction.

This corpus is controlled internal evidence, not a public Statistics leaderboard and not a model score by itself.

### 6.2 Public arithmetic compatibility data

FinQA/TAT-QA gold program/derivation paths may be used to establish deterministic compatibility/ceiling subsets when selection is derived only from gold metadata and exact source revisions/digests are pinned.

Compatibility/oracle coverage is not model accuracy. Unsupported items must remain visible and dataset-specific semantic repairs must not be guessed by generic arithmetic.

### 6.3 Product-specific workloads

An OEM/product benchmark may use its own representative task distribution, but the data, mapping, expected operation/arguments/result, license/privacy policy and evaluation scope must be frozen before inference. Product data must not be mixed with public/internal results under one denominator without explicit stratification.

## 7. Failure taxonomy

Record at least these categories separately:

1. model did not recognize a supported deterministic task;
2. wrong lane/tool selected;
3. wrong semantic operation selected;
4. wrong/missing/swapped argument extraction;
5. malformed tool/plan syntax;
6. capability/model-surface identity mismatch;
7. plan semantic/resource rejection;
8. typed deterministic ExactScope runtime failure;
9. final numeric/rendering mismatch after a valid ExactScope result;
10. token limit;
11. timeout/runtime transport failure;
12. intentional ambiguity/unsupported case correctly preserved.

Do not turn rejected calls into a flattering “no hallucination” headline without also reporting useful-answer rate.

## 8. Required quality metrics

Report counts and denominators before ratios:

- total items;
- correct usable answers;
- incorrect numeric answers;
- malformed outputs;
- tool/lane selection errors;
- operation/method selection errors;
- argument extraction/order errors;
- structural valid-call count;
- ExactScope accepted/rejected call count;
- typed runtime failures;
- result-fidelity failures;
- ambiguity-preserved cases;
- token-limit/timeout cases;
- tool penalty: A correct while tool-equipped arm wrong.

Stratify by model and task family.

## 9. Model-interface cost

For every selected capability/model combination record:

- visible top-level tool count;
- visible semantic operation count;
- prompt-fragment bytes and tokenizer-specific tokens;
- tool/schema bytes;
- grammar bytes;
- generated request/tool-call tokens;
- inference turns;
- plan-step distribution where `xs_calc` is used;
- structural valid-call rate;
- core accepted-call rate;
- operation/plan selection rate;
- argument extraction rate;
- result/failure fidelity.

A binary-small slice can still be a bad product if it is too difficult for the target model to call.

## 10. Artifact/device cost

For exact qualified artifacts record, as appropriate:

- runtime/archive bytes and SHA-256;
- marginal bytes versus the comparison profile;
- process/VM resident memory;
- heap behavior;
- native context/scratch bytes;
- stack high-water where measurable;
- Wasm import/export and linear-memory declaration;
- prompt/completion tokens;
- model inference latency separately;
- ExactScope compute/bridge latency separately;
- end-to-end latency distribution;
- cold/warm behavior;
- energy per operation/workload where credibly measurable;
- sustained thermal/throttling behavior where relevant.

Desktop latency remains desktop evidence. Real target claims require a named target/device/runtime. A 64 KiB Wasm linear-memory ceiling is **not** process/device RAM.

## 11. Fail-closed experiment

Include malformed/ambiguous cases that look tempting to repair:

- missing arguments;
- swapped arguments;
- invalid lexical decimals;
- invalid/forward plan references;
- percent-versus-ratio ambiguity;
- unit-bearing values without a declared conversion contract;
- sample-versus-population ambiguity;
- missing/mismatched vectors/weights;
- unsupported operation/method;
- zero-denominator/domain failures;
- model-surface identity mismatch.

Adapters may normalize transport syntax only. Semantic repair remains forbidden.

## 12. Capability density

After raw values are published, useful task-specific ratios may include:

```text
correct-answer uplift / 100 KiB added artifact
wrong-number reduction / 100 KiB added artifact
correct-answer uplift / added resident-memory KiB
correct-answer uplift / added prompt token
correct-answer uplift / added millisecond
correct-answer uplift / joule  # only when measured
```

Never publish a ratio without its raw numerator/denominator.

## 13. Capability Recovery Ratio

When a separately justified larger-model reference meaningfully beats the small-model baseline on the same frozen task contract, CRR may be reported:

```text
CRR = (small + ExactScope - small)
      ----------------------------
      (larger reference - small)
```

CRR is undefined/unhelpful when the larger reference does not beat the baseline. It is task-specific and must never be translated into general model equivalence or “model replacement.”

## 14. Output/evidence structure

Use a unique output directory outside tracked product source, for example:

```text
benchmarks/output/rc2-<model-id>-<run-id>/
```

Preserve:

- preregistration record;
- release/artifact manifest/checksums;
- model inventory;
- model-visible surface files/digests;
- raw per-item records;
- summary;
- scorer/runtime logs needed for audit;
- evidence-file checksums;
- explicit `complete`, `invalid`, or `aborted` status.

Require one writer. Duplicate `(arm,item_id)` keys, silent configuration changes, or partial results presented as complete invalidate the run.

`benchmarks/results/` in the clean source contains only policy/readme. Frozen benchmark evidence should be published/archived separately with immutable identity rather than overwritten as product source.

## 15. Historical evidence policy

Historical r17/r20 result interpretation documents may remain in the repository as design history. Their exact raw/generated capability payloads are not copied into rc2 clean source.

Safe conclusion from that history: different weak models showed different uplift and preferred surfaces, so **model/task-specific qualification is required**.

Unsafe conclusion: copying an old Qwen/Llama score onto rc2 or using it as proof that every small model improves.

## 16. rc2 qualification order

1. verify the immutable GitHub rc2 release/tag/checksums;
2. run no-model package/integration baseline checks;
3. download/hash/freeze the five core models;
4. freeze preregistration;
5. run Gemma 3 270M and LFM2.5 350M lower-bound checks;
6. run Qwen3.5 0.8B primary small-model matrix;
7. run Qwen3.5 2B scaling comparison;
8. run Phi-4-mini 3.8B independent upper-small reference;
9. freeze the core model evidence;
10. optionally run Gemma 3n E2B as a separate product profile;
11. then perform representative Android ARM64 or embedded Linux ARM64 target qualification.

A preregistered futility rule may stop a catastrophically incompatible lower-bound model early, but the rule must exist before the full result is observed.

## 17. Claim policy

Before rc2 model/target evidence exists, public docs may say that ExactScope implements bounded deterministic quantitative execution and packages narrow model-facing/native/Wasm integration paths for evaluation.

They must not claim rc2:

- accuracy uplift;
- general hallucination elimination;
- larger-model replacement;
- target RAM/latency/energy savings;
- hardware-life extension;
- production readiness;
- Tier 1/Tier 2 support.

Use `docs/MARKETING_CLAIMS.md` and `docs/QUALIFICATION_HANDOFF.md` for the publication boundary.
