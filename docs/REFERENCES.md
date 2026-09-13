# External research and compatibility references

Reviewed: **2026-09-12**

These sources inform ExactScope experiments, compatibility boundaries and hypothesis design. They do **not** transfer their performance claims to ExactScope. ExactScope measurements remain bound to the exact source/model/runtime/provider/corpus/artifact identities used by an experiment.

## Runtime-amplifier research

### Retrieval, selective augmentation and compression

- Lewis et al., **Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks**, NeurIPS 2020 / arXiv:2005.11401: <https://arxiv.org/abs/2005.11401>
- Xu, Shi, Choi, **RECOMP: Improving Retrieval-Augmented LMs with Compression and Selective Augmentation**, 2023: <https://arxiv.org/abs/2310.04408>
- Liu et al., **Lost in the Middle: How Language Models Use Long Contexts**, TACL 2024: <https://aclanthology.org/2024.tacl-1.9/>
- Jiang et al., **LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models**, 2023: <https://arxiv.org/abs/2310.05736>
- Jiang et al., **LongLLMLingua: Accelerating and Enhancing LLMs in Long Context Scenarios via Prompt Compression**, ACL 2024: <https://aclanthology.org/2024.acl-long.91/>

ExactScope does not adopt a mandatory learned compressor from these works. The reusable design question is whether **selective augmentation, higher evidence density and model-visible ordering** can reduce wasted context without losing the evidence needed for correctness. That hypothesis is tested with deterministic/model-free variants first.

### Structured / constrained generation

- Geng et al., **Grammar-Constrained Decoding for Structured NLP Tasks without Finetuning**, EMNLP 2023: <https://aclanthology.org/2023.emnlp-main.674/>
- Beurer-Kellner, Fischer, Vechev, **Guiding LLMs The Right Way: Fast, Non-Invasive Constrained Generation (DOMINO)**, ICML 2024 / arXiv:2403.06988: <https://arxiv.org/abs/2403.06988>
- Park et al., **Grammar-Aligned Decoding**, 2024: <https://arxiv.org/abs/2405.21047>
- JSON Schema Draft 2020-12: <https://json-schema.org/draft/2020-12>

These references motivate a distinction between **ExactScope's semantic answer contract** and a runtime's token-level constrained-decoding implementation. A backend-specific grammar is never allowed to silently become a second answer semantics. Runtime/tokenizer-specific constraint behavior must be measured.

### Inference efficiency and routing

- Leviathan, Kalman, Matias, **Fast Inference from Transformers via Speculative Decoding**, arXiv:2211.17192: <https://arxiv.org/abs/2211.17192>
- Kwon et al., **Efficient Memory Management for Large Language Model Serving with PagedAttention**, SOSP 2023 / arXiv:2309.06180: <https://arxiv.org/abs/2309.06180>
- Chen, Zaharia, Zou, **FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance**, arXiv:2305.05176: <https://arxiv.org/abs/2305.05176>

ExactScope does not reimplement speculative decoding, KV paging or an LLM cascade. These sources motivate host-owned acceleration and cost-aware routing experiments. The ExactScope-specific question is whether deterministic 0-call routing, literal compact evidence and stable prefix identity create additional benefit when combined with the inference engine's native mechanisms.

### Harness optimization, adaptation and evaluation inspiration

- Hu et al., **LoRA: Low-Rank Adaptation of Large Language Models**, 2021: <https://arxiv.org/abs/2106.09685>
- Snell et al., **Scaling LLM Test-Time Compute Optimally can be More Effective than Scaling Model Parameters**, 2024 / ICLR 2025: <https://arxiv.org/abs/2408.03314>
- Mei et al., **A Survey of Context Engineering for Large Language Models**, 2025: <https://arxiv.org/abs/2507.13334>
- Stanford NLP, **DSPy Optimizers**: <https://github.com/stanfordnlp/dspy/blob/main/docs/docs/learn/optimization/optimizers.md>
- Microsoft Research, **LazyGraphRAG: Setting a new standard for quality and cost**, 2024: <https://www.microsoft.com/en-us/research/project/graphrag/news-and-awards/>
- OpenAI, **Introducing Structured Outputs in the API**, 2024: <https://openai.com/index/introducing-structured-outputs-in-the-api/>
- OpenAI, **Model Distillation in the API**, 2024: <https://openai.com/index/api-model-distillation/>
- OpenAI, **How evals drive the next chapter in AI for businesses**, 2025: <https://openai.com/index/evals-drive-next-chapter-of-ai/>
- OpenAI, **Inside OpenAI's in-house data agent**, 2026: <https://openai.com/index/inside-our-in-house-data-agent/>

ExactScope does not claim equivalence to these systems. The reusable design patterns are narrower: **adapt a frozen base cheaply (LoRA), optimize a program/harness against a metric (DSPy), allocate inference-time cost according to problem difficulty (test-time scaling/LazyGraphRAG), separate semantic intent from runtime enforcement (Structured Outputs), spend expensive optimization effort once and deploy a cheaper result repeatedly (distillation), and make evals the control loop that turns failures into product knowledge (OpenAI eval practice).**

The long-term v1.1 hypothesis combines those patterns into **Harness Distillation**, but the current compiler proof is intentionally narrower after the first fresh transfer rejection. The next milestone tests **reference-preserving cost reduction**: freeze a competent Base `B` and predeclared reference `F`, allow only strictly cheaper candidates that preserve every observed `F` calibration success, and independently qualify or reject the frozen candidate on fresh held-out work. `ReferenceOnly(F)` is not counted as compiler-selection value. See [`V1_1_PRODUCT_DIFFERENTIATION.md`](V1_1_PRODUCT_DIFFERENTIATION.md) and [`V1_1_ASTRA_HIGH_REVIEW.md`](V1_1_ASTRA_HIGH_REVIEW.md).

## Current inference-runtime references

### Microsoft ONNX Runtime GenAI

- Generate API overview (**preview**): <https://onnxruntime.ai/docs/genai/>
- C++ API: <https://onnxruntime.ai/docs/genai/api/cpp.html>
- C API: <https://onnxruntime.ai/docs/genai/api/c.html>
- Install: <https://onnxruntime.ai/docs/genai/howto/install.html>
- Build from source / C-C++ integration: <https://onnxruntime.ai/docs/genai/howto/build-from-source.html>
- Chat continuation and system-prompt caching migration notes: <https://onnxruntime.ai/docs/genai/howto/migrate.html>
- Speculative decoding, including no-draft-model n-gram mode: <https://github.com/microsoft/onnxruntime-genai/blob/main/docs/SpeculativeDecoding.md>
- Upstream Python QA example: <https://github.com/microsoft/onnxruntime-genai/blob/main/examples/python/model-qa.py>

Microsoft documents the Generate API as owning tokenization/pre-processing, ONNX Runtime inference, logits processing, search/sampling and KV-cache management. ExactScope Bridge therefore attaches **before generation** and returns raw generation to ExactScope validation afterward; it does not duplicate the engine.

### llama.cpp

- Repository: <https://github.com/ggml-org/llama.cpp>
- Server/API and prompt-cache documentation: <https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md>
- Grammars: <https://github.com/ggml-org/llama.cpp/tree/master/grammars>
- JSON Schema to grammar conversion: <https://github.com/ggml-org/llama.cpp/tree/master/examples/json_schema_to_grammar>

### vLLM

- Automatic Prefix Caching: <https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/>
- Prefix-caching design: <https://docs.vllm.ai/en/latest/design/prefix_caching/>
- Structured outputs: <https://docs.vllm.ai/en/latest/features/structured_outputs/>
- OpenAI-compatible server: <https://docs.vllm.ai/en/latest/serving/openai_compatible_server/>

### NVIDIA TensorRT-LLM / NIM

- TensorRT-LLM KV-cache reuse: <https://nvidia.github.io/TensorRT-LLM/latest/legacy/advanced/kv-cache-reuse.html>
- TensorRT-LLM serving: <https://nvidia.github.io/TensorRT-LLM/commands/trtllm-serve/trtllm-serve.html>
- NVIDIA NIM architecture: <https://docs.nvidia.com/nim/large-language-models/latest/reference/architecture.html>

### Intel OpenVINO / OVMS

- OpenVINO Model Server LLM reference: <https://docs.openvino.ai/2026/model-server/ovms_docs_llm_reference.html>
- Structured output: <https://docs.openvino.ai/2026/model-server/ovms_structured_output.html>
- REST chat API: <https://docs.openvino.ai/2026/model-server/ovms_docs_rest_api_chat.html>
- System requirements: <https://docs.openvino.ai/2026/about-openvino/release-notes-openvino/system-requirements.html>

### Microsoft ONNX Runtime execution portability

- Execution Providers: <https://onnxruntime.ai/docs/execution-providers/>

ExactScope should stay above provider/hardware scheduling rather than embed DirectML/CUDA/OpenVINO/QNN/CoreML/etc. selection into its core.

### Meta ExecuTorch

- Documentation: <https://docs.pytorch.org/executorch/stable/index.html>
- LLM deployment: <https://docs.pytorch.org/executorch/stable/llm/getting-started.html>
- Desktop Windows/Linux/macOS: <https://docs.pytorch.org/executorch/stable/platforms-desktop.html>
- Android LLM runtime: <https://docs.pytorch.org/executorch/stable/llm/run-on-android.html>

ExecuTorch is a useful second Bridge pressure test because its embedded/mobile C++ ownership model is structurally different from an OpenAI-compatible server and from ORT GenAI's current API.

### Google LiteRT-LM / Gemma

- Google Gemma runtime selection, including LiteRT-LM: <https://ai.google.dev/gemma/docs/run>

Google currently presents LiteRT-LM as an on-device LLM path with Android/iOS CPU/GPU/NPU acceleration and a desktop CLI for Windows/Linux/macOS. The ExactScope integration hypothesis is to keep that runtime's model/delegate ownership intact and adapt only the same `complete | generate` delivery semantic.

### Apple / AMD / other host stacks

- Apple MLX-LM: <https://github.com/ml-explore/mlx-lm>
- AMD Ryzen AI Software: <https://www.amd.com/en/products/software/ryzen-ai-software.html>
- Ollama OpenAI compatibility: <https://docs.ollama.com/api/openai-compatibility>
- SGLang documentation: <https://docs.sglang.ai/>

## Rust and WebAssembly

- Rust `wasm32v1-none` target: <https://doc.rust-lang.org/rustc/platform-support/wasm32v1-none.html>
- Rust platform support tiers: <https://doc.rust-lang.org/rustc/platform-support.html>
- Rust panic semantics: <https://doc.rust-lang.org/reference/panic.html>
- Rust linkage: <https://doc.rust-lang.org/reference/linkage.html>
- WebAssembly Core 1.0: <https://www.w3.org/TR/wasm-core-1/>
- WebAssembly Micro Runtime: <https://github.com/bytecodealliance/wasm-micro-runtime>

The no-import profile uses `wasm32v1-none` because Rust documents it as a stable WebAssembly 1.0-oriented target containing `core`/`alloc` without `std` or host imports. ExactScope still inspects release artifacts instead of inferring conformance from a target name.

## Android native compatibility

- Android ABIs: <https://developer.android.com/ndk/guides/abis>
- Android CMake integration: <https://developer.android.com/ndk/guides/cmake>
- Android native middleware distribution: <https://developer.android.com/ndk/guides/middleware-vendors>

## Wire and integrity formats

- CBOR, RFC 8949: <https://www.rfc-editor.org/rfc/rfc8949>
- CRC catalogue entry for CRC-32/ISO-HDLC: <https://reveng.sourceforge.io/crc-catalogue/17plus.htm#crc.cat.crc-32-iso-hdlc>

TinyWire uses deterministic CBOR rules and a precisely identified CRC profile. CRC is corruption detection, not authenticity; pack/update authenticity remains a host/distribution responsibility.

## Earlier adjacent projects

- arithma: <https://github.com/farchanjo/arithma>
- math-mcp: <https://github.com/codeprimate/math-mcp>
- needle-rs: <https://github.com/geekgineer/needle-rs>
- llm-tool: <https://github.com/domenukk/llm-tool>

These are historical adjacent calculator/MCP/typed-tool/tiny-routing references. The broader runtime-neutral amplification idea remains the long-term v1.1 hypothesis, while the **current proof is narrower**: reference-preserving cost reduction against a competent predeclared reference, independent fresh qualification, and then customer-like real-retrieval validation. Deterministic quantitative capability remains one reusable subsystem rather than the umbrella product definition.
