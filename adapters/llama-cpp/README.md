# llama.cpp reference integration

This directory demonstrates the ExactScope **direct hot path** against llama.cpp's OpenAI-compatible chat-completions server.

It is intentionally an adapter only. It does not calculate, round, classify, convert units, or repair semantic errors. Its job is to present the generated ExactScope tool/hot-set metadata to the model and validate the returned `xs_eval` call before the real host forwards that call to ExactScope.

## Server

Use a model/chat template that supports tool calling. Current llama.cpp server builds expose an OpenAI-compatible `/v1/chat/completions` route and Jinja-based tool calling.

Example shape:

```text
llama-server -m <model.gguf> --jinja --host 127.0.0.1 --port 8080
```

Exact flags and model/template compatibility are llama.cpp concerns and can change. The smoke runner deliberately fails if the server returns ordinary text instead of a tool call; it never treats a silently ignored `tools` array as success.

## Adapter self-test

No model or network is needed to verify the local envelope/parser contract:

```text
python3 adapters/llama-cpp/direct_eval_smoke.py --self-test
```

The output identifies the bound hot-set digest, operation revision, and exact decimal-string arguments.

## Inspect the request without sending it

```text
python3 adapters/llama-cpp/direct_eval_smoke.py --dry-run --model local-model
```

This loads `adapters/generated/p0-smoke/` and prints the exact request that would be sent to llama.cpp.

## Run against llama.cpp

```text
python3 adapters/llama-cpp/direct_eval_smoke.py \
  --base-url http://127.0.0.1:8080/v1 \
  --model <server-model-name>
```

Expected model output is one tool call logically equivalent to:

```json
{
  "op": "econ.ped.mid",
  "a": ["10000", "12000", "100", "80"]
}
```

The runner validates:

- exactly one tool call is present;
- function name is `xs_eval`;
- only `op` and `a` are present;
- the operation belongs to the bound generated hot set;
- every argument is an exact decimal string;
- argument count matches generated operation metadata.

It then prints the validated call. **It does not execute the arithmetic.** A host integration forwards that validated call to the native C ABI, no-import Wasm, or another conforming ExactScope execution profile.

## Why `tool_choice=auto` is the default

Tool-template behavior varies by model and llama.cpp version. The smoke prompt strongly requests ExactScope, and the runner requires an actual tool call to pass. `--tool-choice required` is available for configurations where the server/model template reliably enforces it.

## GBNF

The same hot-set generator writes `xs-eval.gbnf`. It is useful for raw/constrained-generation benchmark paths and pins the exact operation key and scalar argument count. The OpenAI-compatible server tool path uses the generated JSON tool asset; the checked-in GBNF is kept as a separate reproducible artifact rather than depending on runtime JSON-Schema conversion behavior.
