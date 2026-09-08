# Historical Statistics multi-arm runner

Release context: **historical development tooling; not the v1.0.0-rc.3 benchmark plan**

`benchmarks/capability_benchmark.py` was built during the pre-rc3 Statistics evidence chain. It can still be useful for reproducing or inspecting that historical benchmark contract, but its old bundle defaults, five-arm A/B/C/D/E layout, token-budget compatibility knobs, and historical artifact-cost assumptions must not be treated as rc3 evidence.

For public historical context, use:

1. [`../docs/RC3_QUALIFICATION_CLOSEOUT.md`](../docs/RC3_QUALIFICATION_CLOSEOUT.md)
2. [`NEXT_MODEL_MATRIX.md`](NEXT_MODEL_MATRIX.md)
3. [`../docs/BENCHMARK.md`](../docs/BENCHMARK.md)
4. [`../docs/PUBLICATION_BOUNDARY.md`](../docs/PUBLICATION_BOUNDARY.md)

Internal rc3 evaluator prompts/handoffs are stored outside the public repository.

## Historical purpose

The runner was designed to separate:

- A — model only;
- B — `xs_calc` only;
- C — selected Statistics `xs_eval` only;
- D — combined `xs_calc + xs_eval`;
- E — a separately configured larger-model reference.

It records raw model replies, operation/argument selection, tool validity, ExactScope responses, token counts, turns, model/bridge latency, tool penalty, capability-density denominators, and conditional CRR.

That layout was useful during development because it exposed a key product fact: a wider surface could be worse for some weak models even when deterministic execution itself was correct. It also exposed cases where weak model-only or larger-model baselines were not credible enough for a headline CRR.

## Historical reproduction only

Older examples referred to generated bundles such as the r17 Statistics runtime and a calc-only baseline. The rc3 clean source intentionally does **not** ship those generated capability/evidence directories.

To reproduce an old run, use an evidence checkout/archive that contains the exact historical bundles and model/runtime metadata, pass all bundle paths explicitly, and preserve the old configuration exactly. Do not regenerate a look-alike bundle from current source and call it the historical artifact.

The historical r17 Statistics serving artifact was **45,804 bytes**. The model evidence accumulated through `statistics-core-8-ai-r20` belongs to that exact old runtime line. It is never an rc3 baseline.

Historical result interpretation is kept in files such as:

- `STATISTICS_R17_QWEN3_PRIMARY_RESULT.md`;
- `STATISTICS_R17_LLAMA32_SECONDARY_RESULT.md`;
- `STATISTICS_R17_QWEN25_STRESS_RESULT.md`.

Those documents describe old experiments and limitations; they are not planned rc3 scores.

## rc3 comparison policy

The new rc3 evidence plan is deliberately simpler:

- **A — model only**;
- **C — selected semantic `xs_eval` only**;
- **D — `xs_calc + xs_eval` only when the exact selected capability exposes both**;
- **B — `xs_calc` only when needed as a diagnostic**.

There is no automatic E arm. The frozen five-model matrix already contains multiple sizes/vendors and an upper-small independent reference. A still-larger model is added only when it answers a specific product decision and the comparison contract is fair.

The rc3 core matrix is:

- Gemma 3 270M IT Q8_0;
- LFM2.5 350M Q4_K_M;
- Qwen3.5 0.8B Q4_0;
- Qwen3.5 2B Q4_K_M;
- Phi-4-mini-instruct 3.8B Q4_K_M.

Gemma 3n E2B IT is an optional separate product-oriented profile.

## Rules that remain valid

Several principles from the historical runner remain mandatory:

- gold construction/admission is independent of model output;
- identical comparable-item sets and generation budgets are used across arms;
- syntax/tool failures never trigger hidden retries or semantic repair;
- a wrong but valid operation/plan/argument call remains a model failure;
- deterministic runtime success alone does not make the end-to-end answer correct;
- partial output is never labeled complete;
- duplicate `(arm,item_id)` records invalidate a supposedly complete run;
- capability-density ratios retain raw numerator/denominator values;
- CRR is used only when its larger-reference denominator is positive and meaningful;
- desktop bridge/model latency is not target-device qualification;
- declared Wasm memory bounds are not process RSS.

## New-run identity

Before using this or any other runner for rc3, freeze the exact:

- GitHub release/tag/commit and release asset hashes;
- capability/model-surface/runtime artifact hashes;
- model repository revisions and file hashes;
- model runtime/build/launch command;
- corpus/generator/mapping hashes;
- prompt/tool/schema/GBNF bytes;
- generation settings and token budget;
- scorer/failure taxonomy;
- timeout/retry policy;
- output directory and single-writer rule.

If the current runner does not cleanly implement the frozen rc3 preregistration, adapt or replace the harness **before inference**, record that harness identity, and do not alter it after seeing results.

## Output location

New rc3 run payloads belong under ignored unique directories such as:

```text
benchmarks/output/rc3-<model-id>-<run-id>/
```

Do not commit mutable rc3 raw results into the product source tree. Freeze publishable evidence separately with exact hashes and an explicit complete/invalid/aborted status.
