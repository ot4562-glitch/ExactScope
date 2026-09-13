# Runtime Amplifier Landscape

Status: **adjacent-system / material-research input for unreleased v1.1; no longer the umbrella product definition**
Updated: 2026-09-13

## Product wedge

ExactScope should not become another inference engine, RAG framework, model trainer, generic optimizer, agent runtime, or observability proxy.

This document predates the final Astra direction reframe and should now be read as **ownership/landscape evidence**, not as the product sentence. The current hierarchy is:

- internal architecture hypothesis: **Semantic Inference Policy Compiler**;
- proposed customer deliverable: **Qualified Execution Profile**;
- first conservative Stage 1 algorithm: **Reference-Preserving Cost Reduction**.

The old "tiny attachable runtime amplifier" phrase remains useful as historical material-search shorthand, but it is not an established category or current external claim.

The retained design constraints are:

1. **lightweight** — no mandatory second model, embedding service, vector database, verifier model, retry/reflection loop, or large owned index;
2. **semantic value above host mechanisms** — evidence sufficiency/context admission and answer-contract lowering/finalization must earn value without duplicating runtime machinery;
3. **easy attachment across environments** — keep the engine the user already has and integrate through a small explicit protocol rather than replacing its serving stack.

## What mature runtimes already do well

Do not reimplement these mechanisms in ExactScope core. Detect or negotiate them and let the backend execute them.

### llama.cpp

Current server documentation exposes prompt/KV reuse (`cache_prompt`, `cache_reuse`), GBNF grammar and JSON-Schema-constrained generation. Its documentation also warns that prompt caching can change numerical execution enough that outputs are not guaranteed bit-for-bit identical across batching conditions. ExactScope should therefore keep prefix caching backend-owned and parity-gated rather than pretending cache implementation is part of its own core.

Reference:
- https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md

### vLLM

vLLM V1 already owns Automatic Prefix Caching, speculative decoding, structured output backends, scheduling and high-throughput serving. Reimplementing any of that would make ExactScope larger and slower while competing directly with a specialized engine.

References:
- https://docs.vllm.ai/en/latest/design/prefix_caching/
- https://docs.vllm.ai/en/latest/features/structured_outputs/
- https://docs.vllm.ai/en/latest/usage/v1_guide/

### TensorRT-LLM

TensorRT-LLM owns high-end GPU serving mechanics: paged KV cache, cross-request block reuse, host offload, speculative decoding and guided decoding integration. This is infrastructure ExactScope should exploit through capability negotiation, never duplicate.

References:
- https://nvidia.github.io/TensorRT-LLM/latest/legacy/advanced/kv-cache-reuse.html
- https://nvidia.github.io/TensorRT-LLM/release-notes.html

### OpenVINO / ONNX Runtime GenAI

OpenVINO Model Server already combines structured output, prefix caching and continuous batching on Intel CPU/GPU/NPU, including Windows deployment. ONNX Runtime GenAI provides the generation loop, KV-cache management and structured output while exposing execution providers including CUDA, DirectML, OpenVINO, QNN, WebGPU and others.

These projects show why ExactScope should stay above hardware-specific inference rather than linking itself to one accelerator stack.

References:
- https://docs.openvino.ai/2026/model-server/ovms_structured_output.html
- https://docs.openvino.ai/2026/model-server/ovms_docs_llm_reference.html
- https://onnxruntime.ai/docs/genai/
- https://onnxruntime.ai/docs/execution-providers/

### Large-vendor pattern

The large vendors reinforce the same boundary from different directions:

| Vendor/runtime | What it owns well | ExactScope implication |
|---|---|---|
| Microsoft ONNX Runtime | Broad execution-provider portability across CPU, CUDA/TensorRT, DirectML, OpenVINO, CoreML, QNN, Android and WebGPU | Do not own accelerator selection; remain usable above whichever EP the host chose |
| NVIDIA NIM + vLLM | Production container, health/readiness, model lifecycle and OpenAI-compatible serving around a specialized inference backend | Do not become another deployment proxy; attach through the inference API and exploit capability metadata |
| Intel OpenVINO / OVMS | Windows/Linux CPU/GPU/NPU deployment, structured output and OpenAI-compatible `/v3` serving | Treat hardware breadth as a host property; ExactScope should add evidence/contract efficiency without device-specific code |
| Apple MLX / MLX-LM | Apple-Silicon-native model inference, quantization and fine-tuning | Support it through a thin serving adapter when an OpenAI-compatible host is present instead of importing MLX into core |
| Google LiteRT-LM | Efficient Gemma/LLM execution across Windows, Linux, macOS, Android and iOS with CPU/GPU/NPU acceleration | Do not reproduce device delegates or model formats; attach above a host/server boundary where available |
| Meta ExecuTorch | Portable edge runtime spanning Android, iOS, desktops, embedded/MCUs and multiple accelerator backends | Treat deep edge portability as the host runtime's job; keep ExactScope's value independent of the hardware backend |
| AMD Ryzen AI | Windows AI-PC NPU/iGPU deployment built around ONNX Runtime/OGA and llama.cpp paths | Prefer interoperability with the runtime the OEM already ships instead of adding AMD-specific inference code |

The important competitive observation is that hardware/runtime breadth is already a mature specialization. ExactScope should therefore test a **semantic policy/qualification layer above those mechanisms**, not another kernel stack. Cross-runtime value remains a prospective hypothesis until the same semantic policy knowledge reduces target search/qualification effort on untouched runtime/workload combinations.

References:
- https://onnxruntime.ai/docs/execution-providers/
- https://docs.nvidia.com/nim/large-language-models/latest/reference/architecture.html
- https://docs.openvino.ai/2026/about-openvino/release-notes-openvino/system-requirements.html
- https://github.com/ml-explore/mlx-lm
- https://ai.google.dev/gemma/docs/run
- https://docs.pytorch.org/executorch/stable/index.html
- https://www.amd.com/en/products/software/ryzen-ai-software.html

### Ollama and OpenAI-compatible serving

Ollama exposes OpenAI-compatible endpoints and emphasizes easy local-model operation. vLLM, TensorRT-LLM and OpenVINO Model Server also expose OpenAI-compatible chat/completions APIs; SGLang tooling likewise interoperates with OpenAI-compatible serving endpoints.

This protocol convergence is the cheapest portability path for ExactScope.

References:
- https://docs.ollama.com/api/openai-compatibility
- https://docs.vllm.ai/en/latest/serving/online_serving/openai_compatible_server/
- https://nvidia.github.io/TensorRT-LLM/commands/trtllm-serve/trtllm-serve.html
- https://docs.openvino.ai/2026/model-server/ovms_docs_rest_api_chat.html
- https://docs.sglang.ai/developer_guide/bench_serving

## White space ExactScope should own

The adjacent products above optimize **how a model is served**. ExactScope should own **whether the model needs to be called, what minimum useful evidence reaches it, what output domain it is allowed to waste tokens on, and which backend-native optimizations are safe for that immutable runtime identity**.

That produces a distinct boundary:

```text
application
    |
    v
ExactScope
  - deterministic route / 0-call
  - compact high-density evidence
  - typed answer contract
  - immutable prepared session
  - capability identity/cache
  - backend acceleration hints
    |
    v
existing inference endpoint
  llama.cpp / Ollama / vLLM / SGLang / TensorRT-LLM / OpenVINO / other
```

ExactScope wins only if removing it leaves the same model server working normally. Attachment must be reversible.

## Portability architecture

Prefer one protocol layer plus thin capability shims:

```text
                  OpenAI-compatible transport
                           |
        +------------------+------------------+
        |                  |                  |
    llama.cpp shim      vLLM shim         Ollama shim
        |                  |                  |
  cache_prompt/APC     APC/structured      JSON/native
        |
  additional thin shims: SGLang / TensorRT-LLM / OpenVINO
```

A backend shim should contain only facts that cannot be expressed by the common transport:

- metadata/fingerprint discovery;
- supported structured-output surface and field spelling;
- prefix/KV-cache capability and safe activation knob;
- deterministic-generation capability;
- backend version/identity material;
- optional native speculation capability;
- endpoint path differences.

Retrieval, projection, typed contracts, zero-call policy and session state remain backend-neutral.

## Preflight cost reduction

The llama.cpp candidate now uses **proof-based preflight** instead of paying the historical 14-request calibration cost on every cold cache miss:

1. probe output surfaces in preference order and stop at the first protocol-valid surface;
2. test the tie-preferred `answer-object-v3` contract first;
3. if v3 is perfect on the frozen semantic calibration set, select it immediately — no other candidate can beat it and the frozen tie rule already prefers v3;
4. only when v3 is not perfect, test the remaining candidates and compute the same full selector result;
5. persist only evidence that actually ran and recompute the stopping proof when the record is loaded.

With two surfaces and four calibration cases the common JSON-Schema/v3-perfect path is **5 model requests**; JSON-Schema rejection followed by GBNF success is **6**; the ambiguous slow path remains **13** and still computes the full contract comparison. The old 14-call behavior is retained only as development history.

A separate `runtime_identity.py` experiment now tests the next reduction: one read-only llama.cpp `/props` request plus at most 128 KiB of local model-file head/tail sampling can generate a cheap **cache lookup candidate**. It explicitly reports that this is not a full model SHA-256 and always marks `persistent_cache_ok=false`; persistent reuse still requires a full model identity or semantic revalidation. Metadata-only identities remain session-scope.

## Accuracy-first lightweight rule

An optimization is admissible when it removes work that is already redundant; it should not guess away information merely because doing so is faster.

Examples:

- good: exact duplicate suppression, prepared immutable state, compiled contract reuse, candidate overfetch before a final item cap;
- good: query-aware duplicate collapse that preserves distinct title identity when the question names it;
- good: use a 512-byte tier only when deterministic retrieval signals justify it, then promote if no complete useful evidence unit fits;
- bad: fuzzy semantic dedup with an unqualified threshold;
- bad: truncating the only answer-bearing sentence to remain inside a small tier;
- bad: dropping validation whose truth was not established at the cold-path trust boundary;
- bad: reimplementing an engine's KV cache, scheduler or speculative decoder inside ExactScope.

## Experimental structure

Aggressive ideas should be attachable slices behind explicit identities until they earn promotion. Do not rewrite the stable core around every experiment. **The research rack is not constrained by the release byte gate.** A 5 MiB or 20 MiB experiment is acceptable if it reveals a causal interaction that can later be distilled; it is not acceptable to smuggle a second large model or a heavyweight service into the score and call that a lightweight amplifier.

```text
reference configuration
    |
    +-- retrieval/query variants
    +-- projection/density/position variants
    +-- typed-contract variants
    +-- host-completion / zero-call variants
    +-- prepared-state / identity variants
    +-- ExactScope Bridge runtime targets
    |      +-- ONNX Runtime GenAI       [working pressure-test prototype]
    |      +-- ExecuTorch               [next structural pressure test]
    |      `-- LiteRT-LM                [next portability pressure test]
    +-- backend-native cache hint       [detached, parity-gated]
    `-- backend-native speculation      [detached, parity-gated]
```

A failed experiment should be removable by deleting its slice and changing one selector, not by undoing a cross-cutting rewrite. The source tree may carry detached experiments that are deliberately absent from the default runtime archive. Interaction experiments should measure both isolated and combined effects, then use leave-one-out removal from the best rack configuration to identify the smallest causal set. See [`V1_1_EXPERIMENT_PROGRAM.md`](V1_1_EXPERIMENT_PROGRAM.md).

## External-runtime pressure test: ONNX Runtime GenAI

Microsoft currently describes ONNX Runtime GenAI as a preview Generate API that owns tokenization/pre-processing, ONNX Runtime inference, logits processing/search/sampling and KV-cache management. Its C/C++ flow exposes `Model`, `Tokenizer`, `GeneratorParams`, `Generator`, append, and token-generation operations. That is exactly the boundary ExactScope should not duplicate.

A first `adapters/bridge/onnxruntime-genai/` prototype now connects the current v1.1 planner to that flow through a backend-neutral `complete | generate` delivery object. The deterministic path returns before ORT is touched; the generation path passes only ExactScope-approved semantic messages to ORT and sends raw generation back through ExactScope's strict finalizer. The C++ prototype also compiles against current upstream headers. This is integration evidence, not accuracy or production-support evidence.

The pressure test exposed a strategically useful seam: the stable v1 C ABI ends at `search/project`, while the v1.1 host planner already owns the complete delivery decision. The resulting API questions are recorded rather than patched into core in [`V1_1_INTEGRATION_FEEDBACK.md`](V1_1_INTEGRATION_FEEDBACK.md).

ORT also documents n-gram speculative decoding that requires no draft model and is aimed at repetitive/structured/input-grounded generation. ExactScope's literal compact evidence may increase useful prompt-history reuse, so `projection × literal placement × n-gram speculation` is now an explicit nonlinear experiment candidate. It remains backend-owned and disabled by default until parity and wall-clock benefit are measured.

References:
- <https://onnxruntime.ai/docs/genai/>
- <https://onnxruntime.ai/docs/genai/api/cpp.html>
- <https://github.com/microsoft/onnxruntime-genai/blob/main/docs/SpeculativeDecoding.md>

## Current footprint checkpoint

After the query-identity protection, one-pass adaptive preparation, incremental projection byte accounting and exact-choice zero-call path, a local candidate package built on 2026-09-11 measured **994,148 compressed bytes** against the existing **1,005,099-byte promotion gate**, leaving **10,951 bytes (~1.09%)** of compressed headroom. This is a development checkpoint, not release evidence and **not the exploration ceiling**. New experiments remain detached so their individual and combined costs can be measured honestly; only the eventual distilled release candidate must return to the selected product footprint envelope.

The detached portable-amplifier experiment packages the existing standard-library Python core plus OpenAI-compatible transport as one deterministic `.pyz`. After adding fail-closed single-model discovery, the Windows execution check measured **42,281 bytes**, with zero bundled models, zero bundled corpora and zero third-party Python dependencies. It successfully executed `--help` and a real `plan` against an external profile. This proves the packaging shape on Windows only; the new three-OS CI is still an experiment until it actually passes on macOS/Linux, and it does not expand the native C ABI support claim.

## Current research priority

The runtime landscape work is now subordinate to the customer-value proof. The preregistered FEVER compiler-value study stopped at `ReferenceOnly`, with the conventional tuner also returning the Reference; therefore cross-runtime breadth, package micro-optimization and new acceleration materials must not distract from establishing competence and total economics on a bounded enterprise document-QA workload.

1. preserve the stopped FEVER evidence and sealed 600 held-out; do not expand the runtime/material matrix to rescue that result;
2. run the next **competence-gated real-retrieval enterprise document-QA** study with a prospectively frozen Base, integrated-style configuration, workload-owner quality gates and total-economic model;
3. keep any cheaper reference-preserving compiler branch conditional and separately preregistered; `ReferenceOnly` remains a valid stop, not a product success;
4. keep material-level interaction research (A×B×D, G×H, etc.) development-only unless it produces a small prospectively testable policy family;
5. pressure-test the smallest semantic delivery boundary across ORT GenAI, ExecuTorch and LiteRT-LM only when maintainers/integration questions justify it; do not call separate runtime successes cross-runtime policy transfer;
6. prefer a **native-free host-attached surface** unless a Python-free consumer or measured bottleneck shows that native code materially improves deployment/economics;
7. keep proof-based completion and runtime identity only while their trust proofs remain exact; never let a profile identity stand in for request-time proof;
8. defer backend cache/speculation expansion, cross-host transfer and adaptive routing until a useful competent source policy exists;
9. only after customer-like value is established should release distillation and broader package/platform optimization return to the foreground.

Release qualification remains intentionally deferred. The next milestone is **competent customer-like value with real retrieval and credible economics**, not runtime-count growth, another footprint headline, or a renamed compiler claim.
