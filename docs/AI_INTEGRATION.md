# AI integration contract

Release target: **ExactScope v1.0.0-rc.2**
Status: **integration & qualification candidate**

ExactScope is consumed by AI runtimes as a constrained deterministic capability component. The integration goal is not to expose a large tool catalog. It is to give a small model the **fewest reviewed choices necessary** and route accepted calls into one shared deterministic numeric core.

## 1. Choose one narrow serving surface

```text
                         small model
                              |
                +-------------+-------------+
                |                           |
                v                           v
       arithmetic decomposition       reviewed method known
                |                           |
                v                           v
          xs_calc(plan)                xs_eval(op,args)
                |                           |
                +-------------+-------------+
                              |
                              v
                 ExactScope deterministic core
                              |
                              v
                 canonical value / typed failure
```

`xs_find` is optional discovery for setup/development or a genuinely unknown semantic operation. It is not a mandatory extra hop.

### `xs_calc`

Use when the model can decompose the task into short arithmetic. Plan v0.1 is deliberately bounded:

- maximum 8 steps;
- `add/sub/mul/div/powi/sqrt` only;
- exact decimal-string leaves;
- backward-only prior-result references;
- no loops, arbitrary branches, variables, general functions, or generated code execution.

### `xs_eval`

Use when method identity itself matters. A generated capability slice exposes only selected reviewed operations and their exact argument contracts.

### `xs_find`

Use only as an optional cold/development path. Do not inject the broad domain catalog into a weak model's normal prompt.

## 2. Start from an immutable capability/model-surface identity

A serious integration should not build tool definitions by hand and hope they match the binary. Bind the model-visible assets to the exact capability profile/runtime identity.

Generated capability assets can include:

```text
profile.json
catalog.json
binding-sha256.txt
model-surface-contract.json
model-surface-sha256.txt
xs-calc.tool.json        # only if selected
xs-calc.gbnf             # only if selected
xs-eval.tool.json        # only if selected
xs-eval.gbnf             # only if selected
xs-find.tool.json        # only if explicitly selected
xs-find.gbnf             # only if explicitly selected
prompt-fragment.txt
```

The host must fail closed when the expected capability/profile/model-surface identity does not match the files/runtime it is about to expose.

The broad operation catalog is a build-time maintenance asset. Do not copy it wholesale into the model context.

## 3. Canonical Tiny JSON boundary

Decimal values are lexical strings so ordinary JSON parsing does not silently round them before ExactScope receives them.

Example semantic request:

```json
{"op":"econ.ped.mid","a":["10","12","100","90"]}
```

Example scalar/vector conventions:

```json
{"op":"stats.mean","a":[["1","2","3.5"]]}
```

The Tiny JSON boundary is strict and bounded. JSON numeric values, nested vectors, unbounded objects, and semantic guessing are rejected when outside the declared contract.

Schemas:

- [`spec/schemas/xs-calc-tool.schema.json`](../spec/schemas/xs-calc-tool.schema.json)
- [`spec/schemas/xs-eval-tool.schema.json`](../spec/schemas/xs-eval-tool.schema.json)
- [`spec/schemas/xs-find-tool.schema.json`](../spec/schemas/xs-find-tool.schema.json)

## 4. Model policy

A compact model/system policy should communicate the actual boundary, not teach the model a full numeric library.

Recommended substance:

```text
Use ExactScope for supported deterministic quantitative calculations.
Use xs_calc only for a supported short arithmetic plan.
Use xs_eval directly for a reviewed method present in the bound capability.
Use xs_find only when discovery is explicitly enabled and the operation is genuinely unknown.
Pass exact values in the declared argument order.
Never invent missing values, units, conversions, methods, or rounding rules.
Do not recompute or repair an ExactScope result.
Preserve a typed ExactScope failure instead of guessing a numeric answer.
```

Use the generated `prompt-fragment.txt` once. Do not duplicate the same operation catalog in system text, schema descriptions, and an extra prompt table.

## 5. Adapter normalization rules

Adapters may normalize **syntax/transport**, not meaning.

Allowed examples:

- unwrap a known OpenAI-compatible/tag-wrapped JSON envelope;
- trim protocol whitespace;
- reorder JSON object fields;
- map a known outer protocol field to the canonical one;
- enforce byte/array/field caps;
- preserve an exact lexical number when the host representation is lossless.

Forbidden examples:

- assume `5%` means `0.05` when the operation contract did not specify it;
- strip currency/unit symbols and continue as if semantics were unchanged;
- invent a missing operand;
- swap arguments because another order “looks likely”;
- silently choose sample vs population statistics;
- silently choose an economics method variant;
- calculate independently in the adapter;
- replace an ExactScope error with a plausible number.

## 6. llama.cpp reference integration

The maintained strict reference adapters are:

```text
adapters/llama-cpp/direct_eval_smoke.py
adapters/llama-cpp/calc_plan_smoke.py
```

Their source-level/self-test role is to validate the integration envelope without running a model:

- exact capability/model-surface negotiation;
- strict duplicate-key handling;
- arity and shape checks;
- decimal lexical checks;
- resource limits;
- backward-only `xs_calc` references;
- no calculation or semantic repair inside the adapter.

For actual model inference, use the frozen generated tool/GBNF/prompt assets from the exact release/capability being qualified. A model run becomes evidence only when its model/runtime/artifact/corpus identities are recorded as described in [`QUALIFICATION_HANDOFF.md`](QUALIFICATION_HANDOFF.md).

## 7. OpenAI-compatible tool envelopes

“OpenAI-compatible” here means a common tool-call JSON shape. It does **not** require cloud use or the OpenAI API.

A product may expose one tool at a time:

- an `xs_calc` function whose arguments contain the bounded plan;
- an `xs_eval` function whose arguments contain a selected operation key and ordered values.

The generated tool JSON and grammar are the source of truth. Protocol wrappers should not independently widen types or descriptions.

## 8. Native and Wasm host choices

### Native typed host

A fixed embedded product can bypass model-facing JSON after the model adapter and call the C ABI with caller-owned structures. This is preferable when the target has a static operation set and wants the smallest runtime boundary.

### Wasm host

The evaluation SDK includes a no-import Wasm artifact for local embedding. `examples/javascript/capability-host.mjs` demonstrates identity checking and a strict local host boundary.

A selected capability build should not retain excluded serving paths merely because the fused development runtime has them.

### TinyWire

TinyWire provides a compact deterministic binary transport where JSON is undesirable. It is not required for every integration.

## 9. Integration failure taxonomy

Keep these separate in logs and benchmark output:

1. model did not recognize a supported task;
2. wrong serving lane/tool selected;
3. wrong semantic operation selected;
4. argument extraction/order failure;
5. malformed tool/plan syntax;
6. model-surface/identity mismatch;
7. bounded-plan semantic/resource rejection;
8. typed deterministic runtime failure;
9. final answer rendering/mismatch after a valid tool result;
10. token limit/timeout/runtime transport failure.

This decomposition matters because ExactScope can guarantee deterministic execution of an accepted call but cannot make an arbitrarily weak model select the right call.

## 10. Recommended qualification arms

For `v1.0.0-rc.2`, the later qualification session should use the minimum useful comparison:

- **A — model only**;
- **C — selected semantic `xs_eval` only**;
- **D — `xs_calc + xs_eval` only when the exact selected profile contains both**;
- **B — `xs_calc` only** when needed as a diagnostic.

Do not automatically expose `xs_find` or a larger catalog as another normal arm. Surface complexity itself can change weak-model behavior.

The current planned models and fairness rules are in [`../benchmarks/NEXT_MODEL_MATRIX.md`](../benchmarks/NEXT_MODEL_MATRIX.md).

## 11. Model download inventory

The release includes a download helper that does **not** run inference:

```powershell
py -3 -m pip install -r requirements-benchmark.txt
py -3 tools/fetch_benchmark_models.py --list
py -3 tools/fetch_benchmark_models.py core --root C:\AIModels\ExactScopeBench
```

It resolves the remote model repository revision, downloads the selected file at that revision, computes a local SHA-256 digest, and writes `model-inventory.json`. Preserve that file as part of preregistration/evidence.

Model terms/licenses remain independent from ExactScope's source license.

## 12. Historical evidence boundary

The old Statistics evidence accumulated through `statistics-core-8-ai-r20` belongs to a 45,804-byte r17 serving runtime. It demonstrated both potential value and a critical limitation: different weak models preferred different selected surfaces and very weak models could still fail semantic selection/argument extraction.

Do not copy those scores onto rc2. Re-running the same model against rc2 is a new evidence run.

## 13. Integration completion checklist

Before calling one host integration technically complete:

- [ ] the release archive checksum was verified;
- [ ] exact release/tag/commit identity is recorded;
- [ ] expected capability/profile/model-surface digests match;
- [ ] only intended tools/operations are model-visible;
- [ ] decimal lexicals and argument order are preserved;
- [ ] resource caps are enforced before the core boundary;
- [ ] typed failures survive the adapter unchanged;
- [ ] no semantic repair/calculation exists in the protocol wrapper;
- [ ] integration logs distinguish model, adapter, core, and host failures;
- [ ] benchmark/qualification is still treated separately from this code-level checklist.

## 14. Next step

For a real end-to-end model benchmark and ARM64 target qualification, use:

- [`QUALIFICATION_HANDOFF.md`](QUALIFICATION_HANDOFF.md)
- [`NEXT_SESSION_PROMPT.md`](NEXT_SESSION_PROMPT.md)
- [`../benchmarks/NEXT_MODEL_MATRIX.md`](../benchmarks/NEXT_MODEL_MATRIX.md)

`v1.0.0-rc.2` remains a prerelease until those exact public artifacts are independently qualified.
