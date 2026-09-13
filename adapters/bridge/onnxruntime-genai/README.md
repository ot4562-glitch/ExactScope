# ExactScope Bridge — ONNX Runtime GenAI prototype

Status: **working integration pressure test; not upstreamed; not production-ready**
Local smoke date: **2026-09-11**
Runtime exercised: **onnxruntime-genai 0.15.2 / onnxruntime 1.30.0** in an isolated `target/` test environment.

## Purpose

This directory proves the smallest useful connection between current ExactScope v1.1-dev delivery and Microsoft's ONNX Runtime GenAI. It does not modify ONNX Runtime GenAI and does not move inference ownership into ExactScope.

Microsoft's Generate API is currently preview and documents ownership of tokenization/pre-processing, inference, logits processing/search/sampling, KV-cache management, chat templates and structured output. The reference loop is Model -> Tokenizer -> GeneratorParams -> Generator -> AppendTokenSequences/AppendTokens -> GenerateNextToken. References:

- <https://onnxruntime.ai/docs/genai/>
- <https://onnxruntime.ai/docs/genai/api/cpp.html>
- <https://github.com/microsoft/onnxruntime-genai/blob/main/examples/python/model-qa.py>

## Actual connection point

```text
ExactScope Delivery(action=generate, approved messages)
   |
   v
ORT Tokenizer / ApplyChatTemplate
   |
   v
Encode
   |
   v
GeneratorParams
   |
   v
Generator.AppendTokens / AppendTokenSequences
   |
   v
GenerateNextToken loop
   |
   v
raw generation
   |
   v
ExactScope strict output finalizer
```

For `action=complete`, the adapter returns before importing/creating any ORT model object. The deterministic route therefore remains a real **0-generation-call path**.

## Files

- `../delivery.py` — runtime-neutral delivery data.
- `../exactscope_v11.py` — only adapter allowed to know current v1.1-dev planner/finalizer APIs.
- `bridge.py` — executable Python pressure-test adapter. ORT dependency is lazy and generation-only.
- `../bridge_contract.hpp` — tiny experimental C++ view, not the frozen ExactScope C ABI.
- `bridge_ort_genai.cpp` — ~60-line C++ ORT connection prototype.

The C++ source compiled cleanly with `-std=c++17 -Wall -Wextra -Werror -pedantic` against current upstream `ort_genai.h`/`ort_genai_c.h` during the 2026-09-11 pressure test.

## Verified flows

### Contract/control flow

The Bridge tests cover all five target states plus both delivery actions. Deterministic completion is asserted to touch no ORT API. Generation is asserted to pass only the already-approved role/content messages into the runtime adapter.

```bash
python3 -m unittest tools/test_exactscope_bridge.py tools/test_ort_genai_bridge.py -v
```

### Real ORT generation plumbing

A local smoke installed ORT GenAI only under `target/bridge-ortgenai-smoke/site` and used Microsoft's tiny random GPT-2 test graph. The official fixture graph has `vocab_size=1000` while its bundled normal GPT-2 tokenizer can emit much larger IDs, so a **test-only tokenizer copy** remapped the exact smoke-prompt token IDs into unused IDs below 1000. Model weights/graph were not changed. This fixture is connectivity evidence only, never model-quality evidence.

The real current ExactScope reference question:

```text
Where is the help desk?
```

produced a `grounded-context` delivery containing the authoritative evidence `The help desk is in Room 12.` plus supplemental evidence. The approved plain smoke prompt was 1,148 characters and 250 tokens with normal GPT-2 BPE segmentation. ORT GenAI performed two generation steps. Because the model is intentionally random, its text was meaningless and the ExactScope finalizer correctly rejected it as an invalid answer object.

Observed final shape:

```json
{
  "model_called": true,
  "prompt_tokens": 250,
  "completion_tokens": 2,
  "valid": false,
  "reply": null,
  "route": "grounded-context",
  "source": "onnxruntime-genai"
}
```

This proves **plumbing and fail-closed ownership**, not accuracy or ORT platform qualification.

## Why the test fixture is not shipped

`target/bridge-ortgenai-smoke/` contains downloaded SDK/runtime/model test material and experimental tokenizer copies. None of it is a Bridge dependency or release payload. A real host supplies its own ORT GenAI installation and compatible model export.

## Structured output

The base prototype deliberately leaves ORT guidance disabled. ExactScope currently has semantic answer contracts plus JSON Schema/GBNF representations, while ORT examples also expose Lark-based guidance. A runtime-specific constraint mapping must be independently qualified rather than assumed equivalent. Invalid raw generation is rejected instead of retried or repaired.

## Promising detached experiment: n-gram speculation

ORT GenAI currently documents n-gram speculative decoding as a no-second-model method suited to repetitive, structured and input-grounded generation. That creates a plausible interaction with ExactScope's literal compact evidence: an answer copied from approved evidence may provide reusable prompt-history n-grams.

Reference: <https://github.com/microsoft/onnxruntime-genai/blob/main/docs/SpeculativeDecoding.md>.

This is **not enabled in the base Bridge**. A future rack experiment should compare ordinary generation versus n-gram speculation under the same ExactScope delivery and record output parity, accepted draft length, wall-clock latency and resource cost.

## No upstream PR yet

Nothing in this prototype has been proposed to `microsoft/onnxruntime-genai`. The intended eventual upstream footprint, if maintainers want an external integration example, is one small example plus documentation and possibly minimal build registration. No ORT core change should be necessary.
