# v1.2 upstream integration status

Date: 2026-09-15

This document tracks the three upstream discussions without turning research evidence into compatibility claims. `v1.2.0-alpha.1` is a frozen research alpha; **v1.2 is now under active development** around a smaller attach/compile-away product boundary.

## Current upstream principle

The current v1.2 product does **not** require upstream runtimes to adopt ExactScope semantics or add an ExactScope-specific execution path. ExactScope should consume measurements and capabilities the host already exposes, select only a non-overlapping minimum-sufficient setting, lower that choice into the host's native configuration, and leave the production path.

```text
existing host measurements + existing host knobs
                 |
                 v
          ExactScope cold selector
                 |
                 v
          host-native config
                 |
                 v
          existing host runtime
```

An upstream issue is therefore a **coordination/feedback channel, not a product dependency**. If the host already exposes the needed configuration surface, the preferred result is no upstream runtime change at all. Historical evidence/finalizer experiments remain useful boundary research, but they are no longer the default v1.2 product shape.

## PyTorch ExecuTorch #22761

Current GitHub state:

- open;
- label: `rfc`;
- assigned to `mergennachin`;
- no public maintainer comment yet.

Current evidence and relevance boundary:

- historical local adapter/fake-runner work still demonstrates that ExactScope can remain outside model-specific rendering and execution;
- current upstream `GenerationConfig` already exposes host-native knobs including `grammar`, `grammar_type`, `max_new_tokens`, `seq_len`, and `temperature`;
- that means the current v1.2 selector/exporter direction can target ExecuTorch configuration **without requiring an ExecuTorch runtime patch or ExactScope-specific execution layer**;
- **real `.pte` + tokenizer + `TextLLMRunner` execution is still missing**, so the project still must not claim real-model ExecuTorch compatibility.

Current issue decision:

1. keep #22761 open for now because it has an `rfc` label and an assigned maintainer, making it a useful scope/placement feedback channel;
2. do **not** treat it as a blocker or requirement for ExactScope v1.2;
3. do **not** open an ExactScope example PR merely because an assignee exists;
4. update the issue to disclose that v1.2 has narrowed and may require **no upstream code change** if native `GenerationConfig` is sufficient;
5. if the maintainer still wants a generic example/docs contribution, keep it independent of ExactScope runtime code and use only public ExecuTorch configuration/execution surfaces;
6. if the maintainer says the native API/docs already cover the use case, close the proposal cleanly rather than inventing an upstream integration.

Assignment is **not** acceptance, and under the new product direction the best upstream outcome may be confirmation that no ExecuTorch change is required.

## Microsoft ONNX Runtime GenAI #2549

Current GitHub state:

- open;
- no assignee, label, or comment visible;
- proposal asks for a very small example around the normal ORT GenAI tokenizer / `GeneratorParams` / `Generator` flow.

This discussion is not a v1.2 dependency. Future follow-up should be evaluated against the same rule: prefer native configuration/export over an ExactScope-specific runtime integration.

## Google LiteRT samples #308

Current GitHub state:

- open;
- no assignee, label, or comment visible;
- proposal targets a small Python sample around `Engine.create_conversation(...)` and `conversation.send_message(...)`.

This discussion is also not a v1.2 dependency. Historical local fixture/context-limit evidence remains useful research, but it does not justify adding a permanent adapter.

## Current maintainer-facing wording

> ExactScope v1.2 is under active development. The current direction is a cold selector/exporter that consumes externally produced measurements and chooses among host-native capabilities; it does not require an ExactScope runtime layer or an upstream inference-path change. `v1.2.0-alpha.1` remains a frozen research checkpoint, not a stable release or a cross-runtime compatibility claim.

For ExecuTorch specifically, the current native `GenerationConfig` may already be enough. The upstream question is therefore whether any generic example/docs contribution is useful at all, not where to insert ExactScope into the runtime.

## Maintainer-facing follow-up principle

Do not post benchmark numbers merely to create activity. The useful upstream question is whether a small native example or documentation gap actually exists. If the host already exposes and documents the necessary surface, close the proposal rather than manufacturing integration work.
