# Experimental OpenAI-compatible adapter

This directory is an **unreleased portability experiment**, not part of the stable v1 runtime bundle.

Its purpose is to prove that ExactScope can keep one provider-neutral `GroundingSession -> PreparedAmplifier` core while swapping only the model-serving wire profile.

## Current boundary

- zero third-party Python dependencies;
- `/v1`, `/v3`, or explicit `/chat/completions` base paths;
- HTTP and HTTPS;
- local endpoints by default; non-loopback model endpoints require explicit `--allow-remote-model`;
- optional Authorization value is read from a named environment variable rather than a command-line secret;
- exactly zero or one answer-model request after ExactScope planning;
- no retry or semantic repair;
- strict ExactScope typed-answer parsing remains unchanged.

The adapter does **not** infer a backend from its product name and does not assume that an OpenAI-shaped endpoint actually enforces structured output. A wire profile is explicit until capability discovery is qualified.

## Wire profiles

### `openai-json-schema-v1`

Uses:

```json
{"response_format":{"type":"json_schema","json_schema":{"name":"grounding_answer","schema":{}}}}
```

This shape is documented by current vLLM, Ollama OpenAI compatibility, and OpenVINO Model Server. llama.cpp already has its stricter dedicated reference adapter.

### `trtllm-guided-json-v1`

Uses TensorRT-LLM's currently documented guided-decoding shape:

```json
{"response_format":{"type":"json","schema":{}}}
```

The difference is deliberately isolated in `surface.py`; no ExactScope answer-contract or grounding code changes.

## Smoke usage

Planning needs no model endpoint:

```text
python3 adapters/openai-compatible/grounding_v1.py plan \
  --profile <profile-dir> \
  --question "Which replacement filter does Rover Mini use?" \
  --corpus-index <corpus.json>
```

A local vLLM/Ollama/OVMS-style endpoint can be tried with the standard JSON-Schema profile:

```text
python3 adapters/openai-compatible/grounding_v1.py answer \
  --profile <profile-dir> \
  --question "Which replacement filter does Rover Mini use?" \
  --corpus-index <corpus.json> \
  --base-url http://127.0.0.1:8000/v1 \
  --model <model-id> \
  --wire-profile openai-json-schema-v1
```

OpenVINO Model Server commonly uses a `/v3` base. TensorRT-LLM guided JSON should use `--wire-profile trtllm-guided-json-v1` after the server has been configured with a guided-decoding backend.

## Why this remains separate

The dedicated llama.cpp adapter is intentionally loopback-only and identity-calibrated. Weakening that adapter in the name of portability would destroy a useful strict reference boundary.

This experimental adapter is therefore attachable: if cross-runtime testing shows that a wire profile is unreliable, it can be removed without touching the ExactScope core or the v1 package. Once capability probing and immutable backend fingerprinting are proven across real runtimes, common transport can be promoted and duplicate adapter code can be collapsed.

## Current upstream references

- vLLM OpenAI-compatible server: https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/
- Ollama OpenAI compatibility: https://docs.ollama.com/api/openai-compatibility
- Ollama structured outputs: https://docs.ollama.com/capabilities/structured-outputs
- OpenVINO Model Server chat/completions: https://docs.openvino.ai/2026/model-server/ovms_docs_rest_api_chat.html
- OpenVINO structured output: https://docs.openvino.ai/2026/model-server/ovms_structured_output.html
- TensorRT-LLM guided decoding: https://nvidia.github.io/TensorRT-LLM/features/guided-decoding.html
