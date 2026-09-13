# ExactScope Bridge upstream validation plan

Status: **parallel external-validation plan; GitHub checkpoint reverified and issue bodies updated on 2026-09-13; all three issues remain open with 0 maintainer comments; upstream PRs remain placement-gated and non-blocking**
Updated: **2026-09-13**

The purpose of upstream work is external architecture review, not feature dumping or promotion by name alone. This track is separate from the current v1.1 product foreground: a competence-gated enterprise document-QA proof for the narrowed qualification/configuration optimizer. Every eventual PR should demonstrate the smallest **admitted** attach point between ExactScope delivery and a runtime that already owns inference. Request admission/qualification failure remains outside the runtime call and may surface as `Reject/Unavailable` in the product semantic boundary.

## Shared rules

Every upstream proposal must preserve these constraints:

- do not copy ExactScope retrieval, authority, coverage, freshness, conflict/ambiguity, evidence projection or host-completion logic into the runtime repository;
- do not add a model, vector database, agent loop or retry/repair loop;
- deterministic `complete` means zero inference calls;
- `generate` passes only already-approved model-visible content into the runtime's normal API;
- raw generation returns to ExactScope validation;
- do not ask the upstream runtime to adopt ExactScope as a dependency unless maintainers explicitly request that direction;
- prefer a self-contained example or documentation-level attach point that maintainers can evaluate independently.

## 1. Microsoft `microsoft/onnxruntime-genai`

### Current local evidence

- ORT GenAI 0.15.2 executed locally.
- Real current ExactScope grounded delivery containing authoritative `Room 12` evidence reached ORT generation.
- Deterministic delivery bypasses ORT completely.
- C++ adapter compiles against current upstream `ort_genai.h` / `ort_genai_c.h`.
- Tiny-random-model malformed output is rejected by ExactScope strict finalization.
- No ORT core change is currently required.

### Ready issue title

`Proposal: minimal external grounding example before generation`

### Ready issue body

> Hi maintainers — I’m prototyping a very small integration layer between an external deterministic grounding component (ExactScope) and ONNX Runtime GenAI, and I’d like guidance on the most appropriate location/shape for an example PR before opening one.
>
> The intended boundary is deliberately narrow:
>
> - ORT GenAI keeps ownership of model loading, tokenizer/chat template, GeneratorParams, generation, search/sampling, KV state, and execution providers.
> - The external component decides only one delivery action before generation: `complete` (return a deterministic answer, zero model calls) or `generate` (pass compact approved role/content messages to the existing runtime).
> - Raw model output is validated by the external component after generation; there is no retry/repair loop.
> - No additional model, vector DB, agent loop, or ORT core change is required.
>
> I have a local prototype against `onnxruntime-genai 0.15.2` that runs both the zero-call path and the normal ORT tokenizer -> GeneratorParams -> Generator flow, compiles a small C++ adapter against the current headers, and has an end-to-end smoke where a real grounding result reaches ORT generation and invalid tiny-test-model output is rejected afterward.
>
> If this direction is useful, my preferred PR would stay very small — ideally one example plus short documentation/build registration, with no inference-engine changes. Would `examples/` be the right target, and would you prefer C++ or Python for the first example?
>
> I’m also pressure-testing the same delivery contract against ExecuTorch and LiteRT-LM so the example does not encode ORT-specific grounding semantics.

### Expected PR diff

Preferred maximum scope:

- one example source file;
- one short README section/file;
- build/example registration only if required;
- no changes under generator/model core.

## 2. Meta/PyTorch `pytorch/executorch`

### Current local evidence

- Adapter targets the current `extension/llm/runner/IRunner` public interface.
- Exact upstream `irunner.h` was used for compile compatibility.
- Executable fake-runner smoke proves zero-call completion and one-call generation ownership.
- Host owns runner loading and semantic-messages-to-model-prompt rendering.
- Real `.pte`/tokenizer runner execution remains pending before a strong compatibility claim.

### Ready issue title

`RFC: tiny external-grounding attach point for extension/llm IRunner examples`

### Ready issue body

> I’m pressure-testing a minimal external-grounding integration against ExecuTorch’s `extension/llm` runner API and would appreciate maintainer guidance before proposing an example PR.
>
> The prototype deliberately leaves model execution inside ExecuTorch. An external component produces only `complete` or `generate` delivery:
>
> - `complete`: return a deterministic host answer and never render/call the LLM runner;
> - `generate`: pass already-approved semantic messages to a host-owned renderer, then call the existing `IRunner::generate(prompt, GenerationConfig, ...)` once and return raw generation for external validation.
>
> This does not add retrieval/RAG logic, a vector DB, a second model, an agent loop, or a new inference path to ExecuTorch. The current prototype compiles against the upstream `IRunner` declaration and has an executable fake-runner smoke; I’m working toward one real `TextLLMRunner` model smoke before proposing code upstream.
>
> Would this kind of integration be more appropriate as an `examples/` sample or as documentation near `extension/llm`? My goal is to keep the eventual diff to a small attach-point example, not to add framework logic to ExecuTorch.

### Expected PR diff

Preferred maximum scope:

- one small C++ example/helper demonstrating the attach point;
- optional README/build registration;
- use existing `IRunner` / `GenerationConfig` APIs unchanged;
- no runner-core or model-executor modifications.

## 3. Google `google-ai-edge/litert-samples`

### Current local evidence

- `litert-lm 0.17.0` installed and executed locally with the official `test_lm.litertlm` fixture.
- Real ExactScope `ordinary-knowledge` delivery ran end-to-end through Engine -> Conversation -> `send_message()` -> ExactScope strict finalizer.
- Real grounded `Room 12` delivery reached the LiteRT-LM boundary unchanged but the tiny fixture rejected it because only 128 state entries remained.
- The adapter did not silently drop policy/evidence to make the smoke pass.
- Structured history + final-message mapping requires no copied ExactScope grounding logic.

### Ready issue title

`Proposal: LiteRT-LM sample for a minimal external grounding / zero-call delivery path`

### Ready issue body

> I’m building a very small sample integration between an external deterministic grounding layer (ExactScope) and LiteRT-LM and would like to confirm whether it fits `litert-samples` before sending a PR.
>
> The sample would keep LiteRT-LM ownership intact:
>
> - deterministic cases return before Engine construction/model inference;
> - generation-required cases map approved role/content messages into the normal `Engine.create_conversation(messages=...)` + `conversation.send_message(...)` flow;
> - no vector DB, second model, agent loop, or LiteRT-LM runtime changes;
> - raw generation is validated outside LiteRT-LM.
>
> I have already run the path locally with `litert-lm 0.17.0` and the official `runtime/testdata/test_lm.litertlm` fixture. A small real delivery runs end-to-end. A larger grounded delivery correctly exposed the tiny test fixture’s 128-state context limit, which I’m recording rather than working around by deleting evidence.
>
> If this belongs in the samples repo, I’d like the PR to be a small Python sample/README using only the normal public LiteRT-LM conversation API. Is there a preferred directory/model fixture for an LLM integration sample of this kind?

### Expected PR diff

Preferred maximum scope:

- one small Python sample;
- one README/update explaining the external delivery boundary;
- existing LiteRT-LM Engine/Conversation API only;
- no changes to LiteRT-LM runtime core.

## Validation interpretation

Maintainer feedback is part of the integration experiment, not the compiler-value experiment:

- if all three maintainers accept approximately the same admitted `complete | generate` attach point, that is evidence the **runtime-call seam** is portable; it is not by itself evidence that compiled policy knowledge transfers across runtimes;
- if two or more require the same missing information, that becomes evidence for a public semantic seam;
- if only one runtime requires a special field/type, keep it adapter-owned;
- rejection of an example because it belongs elsewhere is still useful architecture feedback and should not trigger core changes by itself;
- the product-level `Reject/Unavailable` outcome remains outside the admitted runtime call unless an upstream maintainer explicitly needs that state represented in an example.

## Last recorded upstream state

The connected GitHub app could not write upstream, but the user's authenticated local GitHub CLI did. At the **2026-09-13 checkpoint**, the public threads were:

- Microsoft ONNX Runtime GenAI **#2549** — `Proposal: minimal qualified evidence-to-model policy example before generation`; asks for preferred example location/language while keeping generation/runtime ownership in ORT GenAI;
- PyTorch ExecuTorch **#22761** — `RFC: tiny qualified evidence-to-model policy boundary for extension/llm examples`; asks for the `extension/llm` / example attach point and keeps real `.pte` + tokenizer validation explicitly pending;
- Google LiteRT Samples **#308** — `Proposal: LiteRT-LM sample for a qualified evidence-to-model policy boundary`; asks for the preferred sample directory/model fixture around the normal conversation API.

At the 2026-09-13 checkpoint all three issues were reverified **open with 0 maintainer comments**. A later upstream-auditor pass found that the current public bodies still contain more ExactScope/product framing than is necessary for narrow placement questions. Shorter downstream-consumer rewrite drafts are maintained **outside the public repository**; the live issues have not yet been changed to those local drafts. The upstream PR track is intentionally placement-gated and remains separate from proving customer/qualification value.

User forks now exist for all three repositories. Preparation branches are `exactscope-grounding-example` in the ORT and ExecuTorch forks and `exactscope-grounding-sample` in the LiteRT Samples fork. The ORT fork branch already contains a minimal `examples/python/external-grounding.py` candidate that reads an already-decided `complete | generate` delivery and calls ORT only on the generation path.

While waiting:

- do not force a final upstream PR merely because a response has not arrived yet;
- continue branch preparation/runtime validation only when it answers a real integration question; keep the main engineering focus on the **competence-gated bounded enterprise document-QA proof**;
- when a maintainer supplies placement/language/fixture guidance or explicitly invites a PR, adapt the smallest possible branch and open the corresponding PR;
- treat maintainer feedback as architecture evidence only when it is actually about the attach point/API; repository-policy or sample-placement feedback alone should not drive ExactScope core changes;
- a merge into any upstream `main` is strong external-validation evidence and may create useful visibility as a consequence, but it is separate from proving v1.1 customer value, qualification quality, or the compiler research hypothesis.

See [`V1_1_RESEARCH_STATUS.md`](V1_1_RESEARCH_STATUS.md) for the current local-research checkpoint and resume order.
