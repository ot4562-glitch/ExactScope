# llama.cpp reference integration

This directory maintains two deliberately narrow llama.cpp envelopes: the **one-tool direct `xs_eval` semantic path** and the **one-tool bounded `xs_calc` plan path**.

They are adapters only. They do not calculate, round, classify, convert units, choose a broader operation, or repair semantic errors. Each consumes one explicit ExactScope capability bundle and presents only that bundle's declared model-facing tool surface.

## Capability requirement

The maintained path requires a capability bundle with `surface-contract.json` and `bindings.surface_contract_sha256`. Legacy generated hot-set directories and frozen pre-contract capability revisions are not accepted implicitly.

Before constructing a model request the adapter verifies:

- capability manifest digest and exact regular-file inventory;
- profile/task-map/catalog/model-asset cross-file consistency;
- exact model-surface contract ID/version/digests;
- host acceptance policy for ABI/hot-set/tool/grammar/prompt contract versions;
- a semantic-only surface: `xs_calc=false`, `xs_find=false`, one `xs_eval` tool;
- the bound `xs-eval.tool.json`, `xs-eval.gbnf`, prompt fragment, and selected catalog.

This reference is deliberately narrow. A capability that also exposes `xs_calc` needs a combined adapter rather than silently hiding one of its declared tools.

## Server

Use a model/chat template that supports tool calling. llama.cpp server flags and template behavior can change independently of ExactScope. A typical shape is:

```text
llama-server -m <model.gguf> --jinja --host 127.0.0.1 --port 8080
```

The adapter fails if the server returns ordinary text instead of the expected tool call. It never treats a silently ignored `tools` array as success.

## Offline adapter self-test

No model, network, or ExactScope runtime execution is used:

```text
python3 adapters/llama-cpp/direct_eval_smoke.py --self-test
```

The self-test uses the tracked one-operation `adapters/generated/p0-smoke` assets only as semantic fixture input, then constructs a complete canonical capability/profile/manifest/surface-contract in a temporary directory. No checked-in capability revision is modified or granted new evidence.

The self-test checks rejection of:

- a legacy capability without explicit model-surface negotiation;
- unknown operations;
- wrong scalar/vector shape or arity;
- numeric JSON values where exact decimal strings are required;
- noncanonical decimal spellings such as `01`, `+1`, or `NaN`;
- overlong decimal leaves;
- duplicate JSON object keys.

## Inspect a request without sending it

Supply a newly generated capability that already contains explicit surface negotiation:

```text
python3 adapters/llama-cpp/direct_eval_smoke.py \
  --dry-run \
  --capability <capability-bundle> \
  --model local-model
```

The system message is the compiler-generated `prompt-fragment.txt` **exactly once**. The adapter no longer rebuilds and appends the catalog signatures a second time. Model-token budget is part of the constrained-AI product boundary.

## Run against llama.cpp

```text
python3 adapters/llama-cpp/direct_eval_smoke.py \
  --capability <capability-bundle> \
  --base-url http://127.0.0.1:8080/v1 \
  --model <server-model-name> \
  --prompt <task-text>
```

For a one-operation midpoint-elasticity capability, expected model arguments are logically equivalent to:

```json
{
  "op": "econ.ped.mid",
  "a": ["10000", "12000", "100", "80"]
}
```

The response validator requires:

- exactly one response choice and one function tool call;
- function name `xs_eval`;
- exactly `op` and `a` argument fields;
- no duplicate JSON keys when arguments are returned as a JSON string;
- an operation present in the exact bound capability catalog;
- exact positional arity and scalar/vector shapes;
- decimal leaves matching ExactScope's base-10 lexical grammar, at most 96 characters each;
- at most 64 values per vector and at most 64 decimal leaves across the call.

On success it prints the validated call together with capability bundle digest, model-surface digest, hot-set digest, profile id/revision, and operation revision. **It does not execute the arithmetic.** The real product host forwards that validated call to the matching native/Wasm ExactScope runtime.

## `xs_calc` bounded-plan reference

`calc_plan_smoke.py` is the matching one-tool reference for a **calc-only** capability (`xs_calc=true`, zero semantic `xs_eval` operations, `xs_find=false`). It uses the same explicit model-surface negotiation rule and never evaluates the plan itself.

```text
python3 adapters/llama-cpp/calc_plan_smoke.py --self-test

python3 adapters/llama-cpp/calc_plan_smoke.py \
  --dry-run \
  --capability <calc-only-capability> \
  --model local-model
```

The offline self-test validates 1–8 steps, operation arity, exact decimal lexical form, duplicate/unknown fields, backward-only `#` references, literal `powi` exponent constraints, and the 512-byte canonical request ceiling. A referenced `powi` exponent is left to ExactScope because the adapter does not execute earlier steps to discover that value.

The historical `examples/llama.cpp/run_xs_calc.py` has a different purpose: it runs a model, invokes the ExactScope core, and records latency/token/result information. It is benchmark/evaluation tooling, **not** the maintained execution-free integration boundary and is not required for adapter self-tests.

## Why `tool_choice=auto` remains the default

Tool-template behavior varies by model and llama.cpp version. Both reference adapters still require an actual tool call to succeed. `--tool-choice required` is available where the server/model template reliably supports it.

## GBNF

The capability bundle also binds `xs-eval.gbnf`. The OpenAI-compatible tool path uses the generated JSON tool asset, while GBNF remains a separate exact model-surface artifact for constrained-generation integrations. The adapter validates that both are part of the same negotiated surface even though it sends only the tool schema on this API path.
