# ExactScope Bridge — LiteRT-LM prototype

Status: **real runtime pressure test complete for a small ExactScope delivery; grounded-context capacity friction recorded**

## Why this target matters

LiteRT-LM exposes a structured conversation API rather than ORT-style generator primitives or ExecuTorch's rendered-prompt `IRunner`. The official Python examples use:

```text
Engine(...)
  -> create_conversation(messages=history)
  -> conversation.send_message(last_message)
```

References:

- <https://github.com/google-ai-edge/LiteRT-LM/blob/main/python/litert_lm/examples/simple_main.py>
- <https://github.com/google-ai-edge/LiteRT-LM/blob/main/python/litert_lm_eval/runners/lm_eval_runner/litert_lm_model.py>

This maps naturally from ExactScope semantic role/content messages and is a strong test that `Delivery` is not tied to one prompt/rendering API.

## Bridge boundary

```text
ExactScope Delivery
  |
  +-- complete -> ExactScope reply, no Engine construction
  |
  `-- generate -> approved semantic messages
                    |
                    +-- history -> Engine.create_conversation(messages=...)
                    `-- final user turn -> conversation.send_message(...)
                                         |
                                         v
                                    raw LiteRT-LM response
                                         |
                                         v
                                  ExactScope finalization
```

The adapter disables automatic tool calling. It does not install tools, add an agent loop, alter grounding state, or rebuild evidence.

## Real local smoke

An isolated `target/bridge-litert-smoke/` environment installed:

- `litert-lm 0.17.0`;
- `litert-lm-api 0.17.0`;
- the official upstream `runtime/testdata/test_lm.litertlm` fixture.

The official runtime/model executed successfully on CPU.

A real current ExactScope `ordinary-knowledge` delivery for `Hello` then flowed through:

```text
ExactScope prepare_delivery
  -> Delivery(action=generate, route=ordinary-knowledge)
  -> LiteRT-LM Engine / Conversation
  -> send_message
  -> raw generated text
  -> ExactScope strict finalization
```

The tiny test model produced meaningless text, and ExactScope correctly rejected it (`finalize_generation -> None`). This is plumbing/fail-closed evidence, not model-quality evidence.

## Grounded-context pressure result

The real reference question `Where is the help desk?` produced the expected ExactScope grounded delivery containing authoritative `Room 12` evidence. Passing that approved payload unchanged into the official test model failed with:

```text
Prefill input length exceeds available state entries (remaining capacity: 128)
```

The adapter did **not** delete policy/evidence or silently truncate the delivery to make the smoke pass.

This repeats a class of friction already seen during the ORT pressure test: ExactScope's byte-level evidence budget does not by itself prove fit for an arbitrary model/tokenizer/context configuration. Because two unrelated runtimes exposed the same issue, `docs/V1_1_INTEGRATION_FEEDBACK.md` now treats an optional backend-neutral token/context-fit negotiation seam as a serious pre-freeze design candidate.

## Tests

`tools/test_litert_lm_bridge.py` verifies without the runtime dependency that:

- deterministic completion returns before Engine access;
- approved history and the final user message are mapped without grounding-policy duplication;
- automatic tool calling remains disabled;
- malformed delivery shape fails before runtime access.

## Upstream target

The preferred public validation target is `google-ai-edge/litert-samples`, not a modification to LiteRT-LM core. The proposed sequence is:

1. issue asking whether a tiny external-grounding/LiteRT-LM example fits the samples repository;
2. sample PR using the normal Engine/Conversation API;
3. no copied ExactScope core logic and no LiteRT-LM runtime changes.

A larger-context real model smoke should be added before claiming grounded-context compatibility beyond the official tiny fixture.
