# ExactScope Bridge (experimental)

Status: **integration pressure test for unreleased v1.1; not a production support promise and not the current product-validation milestone**

`ExactScope Bridge` is a temporary implementation for pressure-testing the smallest useful semantic boundary between ExactScope and an external model runtime. The preregistered FEVER compiler-value branch stopped at `ReferenceOnly`; the active v1.1 product foreground is now competence-gated bounded enterprise document QA for the narrowed qualification/configuration optimizer. Bridge exists only to keep the eventual hot boundary small and host-owned.

It is deliberately not a RAG framework, inference server, agent loop, vector database or second model. The host owns retrieval execution/access control, tokenizer/chat-template rendering, model inference/scheduling, cache implementation and constrained-decoding execution. ExactScope retains only the semantic delta it can qualify: authority/coverage/freshness/conflict semantics where required, deterministic evidence shaping, proof-based completion, answer contracts, strict finalization, and profile/qualification identities.

## Architecture

```text
question + host evidence + qualified host profile
   |
   v
ExactScope semantic prepare
   |
   +-- Complete(answer, proof) ----------> return without model inference
   |
   +-- Reject/Unavailable(reason) -------> explicit admission/failure outcome
   |
   `-- Generate(contract, payload, requirements)
                                             |
                                             v
                                       Bridge Delivery v1
                                             |
                                             v
                                     runtime-specific adapter
                                             |
                                             v
                                         host LLM runtime
                                             |
                                             v
                                       raw generated output
                                             |
                                             v
                                  ExactScope strict finalization
```

The current implementation still adapts `GroundingSession -> PreparedAmplifier.plan()` through `exactscope_v11.py`; that is a development churn point, not the intended long-lived public API. `Delivery v1` currently represents admitted `complete | generate` work. The target semantic API also needs an explicit error/admission outcome rather than encoding stale qualification or context-fit failure as either successful branch.

`delivery.py` contains no ONNX Runtime/llama.cpp/ExecuTorch/LiteRT types. A future backend should consume the same `Delivery` semantic and put its own API details in one child directory.

## Current pressure-test targets

The same delivery semantic is now exercised against three structurally different local/on-device runtime surfaces:

| Target | Current evidence | Bridge ownership boundary |
|---|---|---|
| [`onnxruntime-genai/`](onnxruntime-genai/) | real ORT GenAI 0.15.2 generation smoke, real ExactScope grounded delivery, strict post-validation, current C++ header compile | ORT owns tokenizer/chat template, GeneratorParams, generation, search/sampling, KV state and execution providers |
| [`executorch/`](executorch/) | current upstream `IRunner` header compile + executable fake-runner contract smoke | host owns runner loading and message-to-prompt rendering; ExecuTorch owns `IRunner::generate`, token streaming and constrained-decoding machinery |
| [`litert-lm/`](litert-lm/) | real LiteRT-LM 0.17.0 + official `test_lm.litertlm` generation smoke; real ExactScope ordinary-knowledge delivery; grounded delivery exposed the fixture's 128-state context limit | LiteRT-LM owns Engine, conversation/template handling, decoding and backend selection |

These are deliberately different APIs. ORT exposes tokenizer/generator primitives, ExecuTorch exposes a prompt-level runner, and LiteRT-LM exposes structured conversations. Keeping `Delivery` unchanged across all three is the portability pressure test.

## What the delivery contract preserves

The common contract carries the ExactScope result without asking a backend to reinterpret it:

- per-target `grounded`, `none`, `ambiguous`, `conflict`, `unavailable` state;
- `authoritative` or `supplemental` authority;
- deterministic final reply when `action=complete`;
- ExactScope-approved semantic messages when `action=generate`;
- ExactScope profile / answer-contract / optional prefix identity.

`TargetState` is diagnostic/semantic state, **not permission for a backend to rebuild the evidence payload**. Generation uses only the approved messages.

## Churn rule

Until the v1.1 delivery API is frozen, only `exactscope_v11.py` and `delivery.py::from_v11_plan()` may understand the current development planner result. If the v1.1 internal planner changes, fix that boundary rather than editing every runtime adapter.

See [`../../docs/V1_1_INTEGRATION_FEEDBACK.md`](../../docs/V1_1_INTEGRATION_FEEDBACK.md) for API pressure discovered by the first integration.

## Dependencies

The common Bridge source uses only the Python standard library plus the existing ExactScope development modules. It ships no model, index, vector database, SDK or daemon.

Each runtime-specific directory may depend on the runtime that the host application already chose. That runtime dependency is not bundled into ExactScope Bridge.

## Upstream validation plan

The intended validation order is now:

1. **Microsoft `onnxruntime-genai`** — issue/discussion first, then the smallest useful example PR. Local evidence is already strong enough for maintainer feedback.
2. **Meta/PyTorch `executorch`** — RFC/issue around the `extension/llm` runner boundary, then a small example/extension PR after one real-model runner smoke is available.
3. **Google `litert-samples`** — issue proposing a LiteRT-LM sample, then a sample PR that keeps the runtime's conversation API intact.

No upstream PR should copy ExactScope retrieval, authority, coverage, freshness, conflict/ambiguity or projection logic. The upstream diff should demonstrate only the attach point. Maintainer review is being used as an external architecture test: repeated friction across the three runtimes may justify a v1.1 public interface change; one backend-specific quirk may not.

Maintainer-facing issues are now open for all three targets: ONNX Runtime GenAI **#2549**, ExecuTorch **#22761**, and LiteRT Samples **#308**. User forks and preparation branches also exist (`exactscope-grounding-example` for ORT/ExecuTorch and `exactscope-grounding-sample` for LiteRT Samples). The connected GitHub app itself could not write upstream, but the user's authenticated local GitHub CLI had the required issue/fork permissions. PRs should still follow maintainer placement feedback rather than forcing runtime-core changes.
