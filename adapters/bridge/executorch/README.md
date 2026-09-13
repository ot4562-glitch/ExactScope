# ExactScope Bridge — ExecuTorch prototype

Status: **API/ownership pressure test; current upstream `IRunner` compile + executable contract smoke complete; real model-runner smoke still pending**

## Why this target matters

ExecuTorch exposes a materially different integration surface from ONNX Runtime GenAI. The current `extension/llm/runner/IRunner` interface is explicitly marked `ET_EXPERIMENTAL`; it accepts an already rendered prompt plus `GenerationConfig`, streams generated text through a callback, and owns generation. It also exposes grammar fields in `GenerationConfig` for runtime-owned constrained decoding. Treat this as an experimental upstream seam, not a stable compatibility promise.

Reference: <https://github.com/pytorch/executorch/blob/main/extension/llm/runner/irunner.h>.

This makes ExecuTorch a useful portability test: ExactScope must not assume every runtime exposes tokenizer/chat-template primitives.

## Bridge boundary

```text
ExactScope Delivery
  |
  +-- complete -> return ExactScope reply; do not render prompt; do not call runner
  |
  `-- generate -> semantic messages_json
                    |
                    v
               host RenderMessages callback
                    |
                    v
               rendered model prompt
                    |
                    v
             ExecuTorch IRunner::generate
                    |
                    v
               raw generated text
                    |
                    v
             ExactScope finalization
```

The host owns runner construction/loading and model-specific prompt rendering. ExactScope does not load the model, choose the tokenizer, or own ExecuTorch runner lifecycle.

## Current prototype

Files:

- `bridge_executorch.hpp`
- `bridge_executorch.cpp`
- `../../../tools/test_executorch_bridge.cpp`

The adapter was compiled against the current upstream `irunner.h`. The compile test uses tiny local stubs only for transitive ExecuTorch types so the exact public `IRunner` declaration can be checked without building the full ExecuTorch repository.

The executable fake-runner smoke verifies:

- `action=complete` makes zero renderer calls and zero runner calls;
- generation is rejected if the host has not loaded the runner;
- `action=generate` invokes the host renderer once and `IRunner::generate()` once;
- generated callback text is returned as raw output, not silently accepted as an ExactScope answer;
- the adapter sets `echo=false`, `temperature=0`, and a bounded `max_new_tokens` while leaving model/runtime ownership to ExecuTorch.

The current upstream header itself emits unused-parameter warnings in its default `prefill()` implementation under `-Wextra -Werror`, so the local compatibility compile suppresses only `-Wunused-parameter` while preserving `-Werror` for the adapter.

## What remains before an upstream PR

1. run the adapter against one real `TextLLMRunner` / supported `.pte` + tokenizer path;
2. verify the model-specific renderer belongs in the example/host rather than ExactScope;
3. decide with maintainers whether an integration example belongs under `examples/` or near `extension/llm` documentation;
4. keep the upstream diff limited to an attach-point example and docs — no ExactScope grounding implementation inside ExecuTorch.

The intended upstream sequence is RFC/issue first, then a small example/extension PR after maintainers confirm placement.
