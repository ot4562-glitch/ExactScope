# ExactScope v1.1 integration feedback

Status: **active integration pressure-test log; no core change is authorized by this document and integration expansion is not the current product milestone**
Updated: **2026-09-13**
Pressure-test targets: **Microsoft ONNX Runtime GenAI 0.15.2; PyTorch ExecuTorch current IRunner API; Google LiteRT-LM 0.17.0**
Upstream status checkpoint: **reverified 2026-09-13: ORT #2549, ExecuTorch #22761 and LiteRT Samples #308 remain open with 0 maintainer comments. Their current public bodies still over-explain the ExactScope/product framing for what should be narrow downstream-consumer placement questions, so shorter upstream-centric replacements are staged locally in `UPSTREAM_ISSUE_REWRITE_DRAFTS.md`; the live issues have not yet been changed to those drafts. The upstream track remains separate and non-blocking.**

This document records friction found by connecting the ExactScope v1/v1.1-dev semantic path to structurally different inference runtimes. It is intentionally separate from the core design so integration convenience cannot silently redefine product semantics. The preregistered FEVER compiler-value branch stopped at `ReferenceOnly`; the current v1.1 foreground is the narrowed **qualification/configuration optimizer** and its next competence-gated enterprise document-QA proof, not adding more runtimes. For current semantics read [`V1_1_PRODUCT_DIFFERENTIATION.md`](V1_1_PRODUCT_DIFFERENTIATION.md), [`V1_1_STAGE1_REFERENCE_ONLY_RESULT.md`](V1_1_STAGE1_REFERENCE_ONLY_RESULT.md), and [`V1_1_STAGE1_REFERENCE_ONLY_ASTRA_REVIEW.md`](V1_1_STAGE1_REFERENCE_ONLY_ASTRA_REVIEW.md).

> **Current semantic-boundary note:** the older friction entries often shorthand admitted work as `complete | generate`. The target product boundary is now `prepare -> Complete | Generate | Reject/Unavailable -> finalize`. Stale qualification, failed context admission, or unsupported capability must have an explicit non-success outcome rather than being forced into either admitted branch.

The first prototype lives under `adapters/bridge/`. ONNX Runtime GenAI keeps ownership of model loading, tokenization, chat templates, execution providers, generation, search/sampling and KV-cache management. Microsoft currently labels the Generate API as **preview and subject to change**, which is another reason to keep all ORT-specific details behind one adapter. See <https://onnxruntime.ai/docs/genai/> and <https://onnxruntime.ai/docs/genai/api/cpp.html>.

## F-001 — stable v1 C ABI stops before the complete delivery decision

**integration friction**
The stable public C ABI exposes deterministic index initialization, search and projection, but not one complete result that losslessly distinguishes `grounded`, `none`, `ambiguous`, `conflict`, `unavailable`, deterministic host completion, and generation-required delivery. A native host would currently have to reproduce higher-level host policy outside the public ABI, which is exactly what Bridge must not do.

**현재 workaround**
`adapters/bridge/exactscope_v11.py` calls the current v1.1-dev `GroundingSession -> PreparedAmplifier.plan()` path and immediately converts the result to a narrow backend-neutral `Delivery`. No ORT code reads retrieval candidates or reimplements authority logic.

**제안하는 v1.1 interface 변화**
Before a future native delivery ABI is frozen, define a narrow public delivery view/operation whose semantic result is equivalent to: `complete(final_reply)` or `generate(approved_messages/approved_projection)`, plus bounded target-state summary and immutable identity. Keep raw provider/retrieval internals private.

**성능 영향 가능성**
Potentially positive: fewer host glue copies and no duplicate policy implementation. The semantic operation itself should add negligible work because the v1.1 planner already computes the decision.

**ABI/API 안정성 영향**
High if added to the native C ABI; low if first exposed as an experimental host API. Freeze only after at least ORT GenAI plus one structurally different runtime pressure test.

**필수 여부**
**Required for a clean long-term native multi-runtime story; not a reason to mutate the stable v1 ABI immediately.**

## F-002 — the development planner returns a broad internal dictionary

**integration friction**
The current Python planner result contains useful delivery fields but also internal/audit/corpus/amplifier details. A backend adapter that indexes this dictionary directly would become coupled to v1.1 experiments.

**현재 workaround**
`delivery.py::from_v11_plan()` is the only Bridge code allowed to know the current development dictionary shape. ORT consumes only immutable `Delivery` data.

**제안하는 v1.1 interface 변화**
Expose a narrow `prepare_delivery`/`delivery` API after semantics settle. It should return only action, final deterministic reply or model-visible messages/projection, target-state summary, answer-contract identity and relevant immutable prefix/capability identity.

**성능 영향 가능성**
Neutral to slightly positive; a smaller public object may reduce serialization/copying in language bindings.

**ABI/API 안정성 영향**
Medium. The value is mostly churn containment rather than new capability.

**필수 여부**
**Optional ergonomic improvement, but high-value before public API freeze.**

## F-003 — model output validation needs an explicit post-generation boundary

**integration friction**
An inference runtime returns model text/tokens, not an ExactScope-approved answer. If every backend adapter parses/repairs output itself, ExactScope's fail-closed typed contract will fork across runtimes.

**현재 workaround**
The ORT adapter returns raw generation. `exactscope_v11.py::finalize_generation()` invokes the current ExactScope strict parser/validator. Malformed output is returned as invalid; there is no retry or semantic repair.

**제안하는 v1.1 interface 변화**
Provide one public validation/finalization operation bound to the prepared answer-contract identity: raw generated bytes/text -> validated final reply or typed failure. Backends should never duplicate JSON/choice/number validation.

**성능 영향 가능성**
Negligible CPU cost; potentially fewer bugs and no hidden repair calls.

**ABI/API 안정성 영향**
Medium. The semantics should be frozen together with the answer-contract identity.

**필수 여부**
**Strongly recommended before multi-runtime delivery API freeze.**

## F-004 — semantic messages versus model-native chat templates

**integration friction**
ExactScope knows the policy/evidence message semantics; the inference runtime/tokenizer knows the model-native chat template. Returning one pre-rendered llama.cpp-style string would couple the core to a model family and prevent ORT/ExecuTorch/LiteRT from formatting correctly.

**현재 workaround**
Bridge carries role/content messages. ORT applies its own tokenizer chat template. A separate explicit `plain` mode exists only for integration smoke fixtures; it is never an implicit fallback.

**제안하는 v1.1 interface 변화**
If a public delivery representation is added, expose semantic role/content messages or equivalent typed segments, not a backend-specific final prompt. Optionally expose stable segment/prefix identities.

**성능 영향 가능성**
Usually neutral; enables host-native template/caching optimizations.

**ABI/API 안정성 영향**
Medium because message representation can become a long-lived integration contract.

**필수 여부**
**Required design property; exact API shape can remain experimental until another runtime is tested.**

## F-005 — constrained-output surfaces are not portable by field spelling

**integration friction**
ExactScope currently compiles semantic answer constraints to JSON Schema and GBNF. ONNX Runtime GenAI exposes guidance/structured-output facilities, but its current examples include Lark-based guidance. A blind JSON-Schema/GBNF-to-Lark translation inside Bridge would create a second constraint semantics and can change model behavior.

**현재 workaround**
The first ORT Bridge does not enable backend guidance. It uses the ExactScope instruction and performs strict post-generation validation. Invalid output remains invalid.

**제안하는 v1.1 interface 변화**
Expose the semantic answer specification and canonical JSON Schema as capability material; keep backend syntax translation/negotiation in thin runtime shims. Do not add ORT-specific grammar to ExactScope core.

**성능 영향 가능성**
Potentially large positive effect on format failure/output tokens when a native surface is proven; constrained decoding can also hurt accuracy or add overhead, so parity/quality measurement is mandatory.

**ABI/API 안정성 영향**
Low for core if the semantic contract remains authoritative; backend profile identities carry syntax differences.

**필수 여부**
**Optional optimization; not required for the first Bridge.**

Research context: Geng et al., *Grammar-Constrained Decoding for Structured NLP Tasks without Finetuning* <https://aclanthology.org/2023.emnlp-main.674/>; Beurer-Kellner et al., *Guiding LLMs The Right Way* (DOMINO) <https://arxiv.org/abs/2403.06988>; Park et al., *Grammar-Aligned Decoding* <https://arxiv.org/abs/2405.21047>.

## F-006 — byte budgets do not prove model-token/context fit

**integration friction**
ExactScope currently reasons heavily in bytes, while an inference runtime ultimately enforces token/model context limits. During the ORT smoke test, an intentionally truncated test tokenizer expanded the same 1,148-character approved prompt to 529 tokens and exceeded the tiny test graph's 512-token limit. With normal GPT-2 BPE segmentation the same prompt was 250 tokens. The lesson is general: byte length cannot by itself prove token fit for an arbitrary tokenizer/model export.

**현재 workaround**
The runtime adapter tokenizes the already-approved prompt before generation and fails closed if the host runtime rejects it. The test did **not** delete ExactScope policy/evidence to force a pass.

**제안하는 v1.1 interface 변화**
Consider an optional host-supplied token-budget/cost callback or a two-stage `project(max_model_bytes, optional_model_token_budget)` seam. ExactScope core should not import tokenizer libraries. A simpler alternative is to expose multiple deterministic projection tiers and let the prepared host select a qualified tier before generation.

**성능 영향 가능성**
Potentially positive for small-context models by avoiding overlong prompts and repeated failed preparation. Callback/tokenization overhead must be measured.

**ABI/API 안정성 영향**
Medium/high if placed in the core ABI; low if expressed as an optional host preparation interface.

**필수 여부**
**Optional pre-freeze seam worth designing; adaptive token-fit policy should remain experimental until measured across runtimes.**

## F-007 — prefix/system-prompt reuse is runtime- and provider-specific

**integration friction**
The v1.1 planner can expose a stable prefix-cache identity, but actual reusable KV state and restrictions belong to the runtime. ORT documents system-prompt caching through generator continuation and notes provider/batch-size restrictions; vLLM and TensorRT-LLM have different native cache systems.

**현재 workaround**
Bridge still treats the cache key as opaque metadata, but local llama.cpp pressure tests now activate host prompt-prefix caching only in explicitly qualified experiment profiles. Qwen 0.8B/no-policy preserved raw/value parity and exact/F1 while reducing E2E latency by about 9.98%. Llama 1B/full reduced latency by about 20.4% but changed one raw/value result in 20 items, so that model/runtime/profile cell remains disabled. The current llama.cpp context also reported arbitrary `cache_reuse` unsupported.

**제안하는 v1.1 interface 변화**
Keep only an immutable semantic prefix identity plus a separately qualified capability record in ExactScope. Never expose or own backend KV objects. Cache activation belongs to the host profile and is permitted only after exact parity/quality testing for that runtime/model/prompt profile.

**성능 영향 가능성**
Measured positive on one qualified cell (~10% Qwen E2E reduction), potentially larger on long prefixes, but not guaranteed deterministic/parity-safe across model/runtime combinations.

**ABI/API 안정성 영향**
Low if the identity remains opaque/backend-neutral and capability qualification remains adapter/profile-owned.

**필수 여부**
**Optional host optimization. The interface boundary is validated; activation must remain parity-gated.**

References: ORT migration/system prompt caching <https://onnxruntime.ai/docs/genai/howto/migrate.html>; vLLM automatic prefix caching <https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/>; TensorRT-LLM KV reuse <https://nvidia.github.io/TensorRT-LLM/latest/legacy/advanced/kv-cache-reuse.html>.

## F-008 — host n-gram speculation stays adapter-owned and is currently negative for short extraction

**integration friction**
None for core correctness. ORT GenAI and current llama.cpp both expose no-second-model n-gram/prompt-lookup speculation, making it an attractive host-owned capability in principle.

**현재 workaround**
Disabled in the base Bridge and now explicitly disabled in the current short factual-extraction profile. Local llama.cpp `ngram-simple` screens found Qwen/no-policy ~1.66% slower with output parity preserved, while Smol/compact-native was ~2.28% slower and changed one raw/value result. The observed completion lengths were too short to amortize speculation overhead.

**제안하는 v1.1 interface 변화**
No core change. Keep speculation as an optional adapter capability that must be independently qualified for a workload/model/runtime identity. Do not add a core speculation flag whose presence implies activation.

**성능 영향 가능성**
Negative in the current extraction cells; a future longer or highly copy-heavy workload may differ. Require wall-clock gain and output/quality parity before activation.

**ABI/API 안정성 영향**
None if kept adapter/profile-owned.

**필수 여부**
**Optional research capability; quarantined/off for the current workload.**

Reference: Microsoft, ONNX Runtime GenAI speculative decoding <https://github.com/microsoft/onnxruntime-genai/blob/main/docs/SpeculativeDecoding.md>.

## F-009 — external runtime APIs will churn

**integration friction**
ORT currently labels its GenAI API preview. The C++ header also returns runtime-specific ownership wrappers such as `OgaString`, details that should never leak into the ExactScope delivery contract.

**현재 workaround**
All ORT names/types are isolated in `adapters/bridge/onnxruntime-genai/`. The C++ prototype is compiled against current upstream headers; the common Bridge contract contains no ORT include.

**제안하는 v1.1 interface 변화**
None. This validates the decision to stabilize semantic delivery data instead of vendor C++ types.

**성능 영향 가능성**
None.

**ABI/API 안정성 영향**
Positive: vendor churn remains adapter-local.

**필수 여부**
**Required architectural rule, no core API addition required.**

## F-010 — ExecuTorch confirms prompt rendering must remain host-owned

**integration friction**
ExecuTorch's current `extension/llm/runner/IRunner` accepts a rendered prompt string plus `GenerationConfig`, rather than ORT-style tokenizer/chat-template primitives. A Bridge that insists on owning one universal rendered prompt would therefore couple ExactScope to model/template policy that the host already owns.

**현재 workaround**
The experimental C++ adapter accepts a host `RenderMessages` callback. `Delivery.messages_json` remains semantic input; the host renders it for the selected model, then the adapter invokes exactly one `IRunner::generate()` call. `action=complete` returns before the renderer or runner is touched.

**제안하는 v1.1 interface 변화**
Keep semantic messages/segments public and leave final prompt rendering outside core. Do not add a universal rendered-prompt field as the only delivery representation.

**성능 영향 가능성**
Neutral directly; positive indirectly because each runtime can use its native/model-qualified template without duplicate conversion.

**ABI/API 안정성 영향**
Positive. The delivery contract is insulated from runner/template churn.

**필수 여부**
**Required architectural property; no backend-specific core API is needed.**

Reference: ExecuTorch `IRunner` / `GenerationConfig`: <https://github.com/pytorch/executorch/blob/main/extension/llm/runner/irunner.h>.

## F-011 — LiteRT-LM validates structured-message delivery but repeats context-fit friction

**integration friction**
LiteRT-LM exposes a structured conversation API: history is supplied to `Engine.create_conversation(messages=...)` and the final turn is sent with `conversation.send_message(...)`. This maps cleanly from ExactScope semantic messages. However, the official `test_lm.litertlm` fixture has only 128 available state entries; the real grounded `Room 12` delivery exceeded that capacity and LiteRT-LM correctly rejected prefill.

**현재 workaround**
The adapter passes ExactScope messages without deleting policy/evidence. A smaller real ExactScope `ordinary-knowledge` delivery was executed end-to-end through LiteRT-LM 0.17.0 and its official test model, then the random model output was rejected by ExactScope strict finalization. The larger grounded delivery remains a recorded context-capacity failure rather than being silently truncated.

**제안하는 v1.1 interface 변화**
Same direction as F-006, now with cross-runtime evidence: define a small optional host token/context-fit seam or deterministic projection-tier selection interface. The host supplies runtime/model capacity information or a token-cost function; ExactScope remains tokenizer-library-independent and chooses only among semantics-preserving projections.

**성능 영향 가능성**
Potentially significant on small-context/on-device models: avoid constructing a delivery that cannot fit, and select the smallest sufficient projection without a failed generation attempt. The host tokenization/cost call itself must remain bounded and measured.

**ABI/API 안정성 영향**
Medium. The seam should be optional and backend-neutral, not a tokenizer object in the native core ABI.

**필수 여부**
**Now strongly recommended for pre-freeze design because the same class of friction appeared independently in ORT and LiteRT-LM.**

References: LiteRT-LM Python API examples and evaluation runner: <https://github.com/google-ai-edge/LiteRT-LM/blob/main/python/litert_lm/examples/simple_main.py>, <https://github.com/google-ai-edge/LiteRT-LM/blob/main/python/litert_lm_eval/runners/lm_eval_runner/litert_lm_model.py>.

## F-012 — three runtimes strengthen the minimal delivery contract

**integration friction**
The three targets expose different generation surfaces: ORT tokenizer/generator primitives, ExecuTorch prompt-level `IRunner`, and LiteRT-LM structured conversations. Despite that difference, none requires retrieval candidates, provider scores, authority resolution internals or projection algorithms inside the runtime adapter.

**현재 workaround**
All adapters consume the same `complete | generate` decision. Runtime-specific files only translate approved model-visible content into the host's existing generation API and return raw output for ExactScope finalization.

**제안하는 v1.1 interface 변화**
Promote the semantic delivery/finalization concept, not any of the three vendor call shapes. Keep optional capability metadata separately versioned.

**성능 영향 가능성**
Positive engineering effect: less duplicate integration code and lower maintenance cost as runtimes evolve.

**ABI/API 안정성 영향**
Strongly positive if the contract stays narrow.

**필수 여부**
**Strong evidence for the current architecture; final native ABI shape should still wait for the remaining real-runner pressure tests.**

## F-013 — an existing host retriever can replace ExactScope index ownership

**integration friction**
The portable research path owns a local corpus/index because it must work standalone. In an existing RAG/search host this duplicates retrieval state, package code, memory ownership and ranking work. The precision projector appeared to need full-corpus IDF only for sentence-anchor scoring.

**현재 workaround**
The experimental `adapters/bridge/ranked_hits.py` consumes only a bounded ranked candidate list. Without hints it can estimate candidate-local rarity. When the host also lends a bounded map of normalized query-term lexical weights, the attach projector reproduces the full-index D projection exactly without importing or owning the corpus index.

Development parity screen with top-12 ranked hits plus query-term weights:

- NQ128: 100% emitted-ID and payload-byte parity; mean hint ~223 bytes/query;
- Hotpot20: 100% parity; mean hint ~384 bytes/query;
- FEVER150: 100% parity; mean hint ~184 bytes/query.

The same attach path reproduced the earlier real-ORT-tokenizer D+I result exactly.

**제안하는 v1.1 interface 변화**
Do not make a retrieval index mandatory for an attach deployment. Define an experimental bounded ranked-hit input plus optional backend-neutral query-term scoring hints. Keep host score syntax/index structures private; ExactScope sees only normalized candidate content and bounded semantic scoring material.

**성능 영향 가능성**
Strong ownership/package reduction with negligible projection CPU impact. The P0 projector compresses to roughly 3.8 KB; the current strict hot attach research ZIP is 12,430 bytes. Candidate-local fallback is useful but not exact parity under all tight-context cells, so host hints are preferred when available.

**ABI/API 안정성 영향**
Medium if frozen as a public attach API. Candidate fields and hint normalization should remain experimental until pressure-tested against a real external retriever API.

**필수 여부**
**Strong candidate for the v1.1 attach profile; not required by the portable fallback.**

## F-014 — repeated policy text should become a qualified prompt profile, not a universal hot-path constant

**integration friction**
A semantic delivery may already have resolved authority/state before generation, while the host's qualified native output surface enforces syntax. Repeating the full grounding policy on every request can therefore consume context and prefill budget that could instead hold evidence. However, removing the policy is model-dependent: one universal compact prompt produced regressions on Llama 1B.

**현재 workaround**
The research attach path treats `full`, `no-policy`, and `compact-native` as cold-qualified prompt profiles. Hotpot20 and a deterministic NQ20 subset produced the same model-level winners: Smol -> compact-native, Qwen -> no-policy, Llama -> full. The Qwen profile improved exact score on both task screens with no paired exact losses versus full while cutting prompt tokens/latency.

The direct Qwen Hotpot20 bundle comparison (`full + no cache` versus `no-policy + host prefix cache`) measured exact 15% -> 35%, prompt tokens -16.65%, and E2E latency -22.87%, with 4 paired gains / 0 losses.

**제안하는 v1.1 interface 변화**
Keep semantic policy/answer contract authoritative, but allow a model/runtime-specific prompt profile to be selected on a cold capability path and identified immutably. Do not make prompt shortening a per-request heuristic and do not remove policy text unless that profile has been qualified for the model/runtime/delivery semantics.

**성능 영향 가능성**
Potentially large. Besides direct prefill savings, prompt reduction can interact positively with Material I by freeing real tokenizer context for larger complete evidence tiers.

**ABI/API 안정성 영향**
Low for core if the semantic contract remains authoritative and prompt-profile identity stays capability metadata. High risk if one compact prompt is frozen as universal semantics.

**필수 여부**
**High-value attach-profile optimization; model/runtime qualification is mandatory.**

## F-015 — ExecuTorch `IRunner` default `prefill()` breaks strict downstream header builds

**integration friction**
A minimal downstream translation unit that only includes the current ExecuTorch `extension/llm/runner/irunner.h` fails under `g++ -std=c++17 -Wall -Wextra -Werror`: the default `IRunner::prefill()` implementation names `inputs`, `num_bos`, and `num_eos` but returns `NotSupported` without using them. This was discovered while compiling the bridge against the upstream declaration, not by searching for a contribution target.

**현재 workaround**
The local compatibility compile uses `-Wno-unused-parameter` only for this upstream-header warning. The bridge itself continues to compile with `-Werror`, and a rebuilt fake-runner executable passes. A five-line include-only reproduction is stored under `target/upstream-executorch-unused-parameter-repro/`.

**제안하는 v1.1 interface 변화**
None. This is not evidence for an ExactScope core/API change. It is a small upstream-consumer friction candidate: ExecuTorch already uses `[[maybe_unused]]` elsewhere, so marking these default-implementation parameters accordingly would remove the downstream warning without changing behavior or ABI.

**성능 영향 가능성**
None.

**ABI/API 안정성 영향**
None expected; the proposal changes only warning annotations on parameters of the existing experimental default method.

**필수 여부**
**Upstream contribution candidate only.** It is independently useful to strict C++ consumers and should be kept separate from the larger example/RFC discussion. Before any PR, reverify the exact upstream `main` header, contribution rules, and absence of an overlapping issue/PR.

## Integration priorities after the multi-runtime pressure test

These are **integration-boundary follow-ups**, not the current product execution order. The competence-gated enterprise document-QA proof in `V1_1_PRODUCT_DIFFERENTIATION.md` takes precedence; runtime integration work should advance only when it removes a concrete blocker for that proof or responds to maintainer guidance.

When the integration boundary is revisited, the strongest candidates to settle are:

1. one narrow `prepare -> Complete | Generate | Reject/Unavailable -> finalize` semantic boundary;
2. one strict deterministic post-generation finalization semantic;
3. `Complete` carries a request/evidence-bound verifier-checkable proof rather than relying on profile identity alone;
4. semantic messages/segments remain distinct from model-native chat templating;
5. answer-contract and qualification identities remain backend-neutral;
6. keep the optional **token/context-fit negotiation seam** while tokenizer/runtime dependencies remain outside core;
7. keep an experimental **host-ranked-candidate + bounded lexical-hint attach input** so existing RAG/search systems need not duplicate an ExactScope index;
8. represent minimum-sufficient prompt choice as cold model/runtime capability metadata rather than one universal shortened prompt;
9. run a real ExecuTorch `.pte` + tokenizer smoke or larger-context LiteRT-LM test only if it resolves a product-boundary question; runtime-count growth alone is not a milestone;
10. do not freeze a broad native ABI before the native-free host-attached path is measured and a native requirement has earned its place.

Prefix/KV reuse, native constrained-decoding syntax, speculation and provider-specific acceleration remain host/adapter capabilities. Availability never implies activation; parity/quality/cost qualification is required.
