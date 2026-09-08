# ExactScope v1.0.0-rc.3 qualification closeout

Status: **qualification phase closed; findings accepted as design input for rc4**

Date: 2026-09-06

This document closes the external-user qualification phase for `v1.0.0-rc.3`. The rc3 release, benchmark outputs, and evidence directories are immutable historical evidence. No rc3 score or artifact is to be rewritten after this closeout.

## 1. Decision

`v1.0.0-rc.3` successfully fixed the rc2 public integration-packaging blocker and proved that the published SDK can be consumed from clean-room Linux and Windows environments. It did **not** prove a universal model-uplift claim.

The five-model matrix rejected the simple hypothesis that tool-call reliability grows monotonically with model size. The strongest explanatory variable was the model/runtime chat-template and tool-protocol compatibility, followed by the difficulty and token cost of the currently exposed semantic surface.

Therefore rc4 changes the product-facing AI integration contract rather than changing deterministic arithmetic semantics.

## 2. Frozen five-model observation

The completed rc3 A/C/D matrix was:

| Model | A correct | C correct | D correct | C tool use | D tool use |
| --- | ---: | ---: | ---: | ---: | ---: |
| Gemma 3 270M Q8 | 0/23 | 1/23 | 1/23 | 1/23 | 1/23 |
| LFM2.5 350M Q4KM | 1/23 | 1/23 | 1/23 | 1/23 | 1/23 |
| Qwen3.5 0.8B Q4 | 4/23 | 4/23 | 6/23 | 19/23 | 23/23 |
| Qwen3.5 2B Q4KM | 4/23 | 6/23 | 5/23 | 21/23 | 20/23 |
| Phi-4-mini 3.8B Q4KM | 5/23 | 1/23 | 1/23 | 1/23 | 1/23 |

Interpretation:

- Gemma and Phi exposed no usable native tool-call path in the frozen llama.cpp configuration even though Phi was the largest tested model and the strongest model-only baseline.
- LFM serialized tool information into the prompt but did not expose a complete assistant tool-call protocol.
- Qwen3.5 0.8B and 2B were tool-aware and recognized tools frequently, yet still suffered operation/schema selection failures.
- When a valid request reached ExactScope, deterministic core behavior was materially stronger than the end-to-end model score.

The product problem is therefore **model-to-ExactScope request formation**, not a reason to replace the deterministic core.

## 3. Token and latency observation

Native OpenAI-style tool serialization was expensive for small local models. For the frozen Qwen3.5 surfaces, representative mean prompt-token counts were approximately:

- A model-only: ~86 tokens;
- C semantic tool surface: ~613 tokens;
- D combined tool surface: ~1047 tokens.

Qwen2 showed the same prompt-size pattern. This cost is not inherent to deterministic offload; it is primarily a consequence of verbose tool schema/template serialization.

For on-device inference, token cost is also systems cost: prefill latency, KV-cache pressure, memory traffic, energy and thermal load.

## 4. Installation and packaging result

The rc3 public evaluation SDK is usable as an immutable external-user input:

- release-level checksums verified;
- package-internal checksums verified;
- Linux native core smoke passed;
- Linux C ABI compile/link smoke passed;
- Wasm ABI and `xs_calc` smoke passed;
- packaged capability host smoke passed for semantic and combined capabilities;
- Windows package verification and raw-stdin core smoke passed;
- Windows capability host smoke passed;
- model downloader and qualification CLI were usable without requiring Rust for the first-use evaluation path.

One installation/documentation issue remains relevant to rc4: Unix-style stdin examples do not translate cleanly into PowerShell/CMD copy-paste commands. Windows examples must use native, verified command forms rather than assuming shell equivalence.

## 5. Physical ARM64 target result

The public Android ARM64 and Linux ARM64 musl SDKs passed package/contract/doctor checks, but no physical Android/ARM64 target was connected and no ADB path was available. Therefore real-device latency, RSS/heap, stack, energy, thermal and destructive update/power-loss measurements remain **NOT MEASURED**.

This is no longer a blocker for starting rc4 product work. It remains a future target-qualification gate before any production/energy/thermal claim.

## 6. rc4 architecture decision

The normal product path becomes:

```text
user request
   |
   v
small/local model
(intent + exact argument extraction only)
   |
   +--> native tool call, only when the runtime proves a compatible tool protocol
   |
   `--> constrained ExactScope request JSON/GBNF otherwise
              |
              v
      strict request validator
              |
              v
      ExactScope deterministic core
              |
              v
        typed result/error
```

Rules:

1. Native tool calls are an optimization, not a universal dependency.
2. Every shipped capability must include a model-agnostic constrained request surface.
3. Runtime/tool capability detection may select the envelope, but may not change semantic meaning or repair invalid model output.
4. The model performs classification and extraction, not arithmetic that ExactScope already supports.
5. The request boundary remains fail-closed: no guessed units, methods, percentages or missing values.
6. The model sees the smallest product-realistic capability slice possible.
7. rc3 evidence remains immutable; every rc4 prompt/grammar/surface change creates a new candidate identity.

## 7. New product KPIs

Accuracy alone is insufficient. rc4 and later candidates must report at least:

- end-to-end exact correctness;
- lane selection / operation selection / argument extraction;
- malformed/rejected request rate;
- input and output tokens;
- model latency and deterministic-core latency separately;
- fixed model-surface bytes;
- **accuracy uplift per added prompt token**;
- **accuracy uplift per added model-surface byte**;
- **accuracy uplift per added model-latency millisecond**;
- target RAM/energy/thermal metrics when a real device is available.

The preferred product is not the surface that produces the most tool calls. It is the surface that produces the highest useful deterministic accuracy uplift at the lowest integration and on-device cost.

## 8. Work transition

Qualification is closed. Active work moves to `fix/rc4-model-surface`.

The implementation order is:

1. make the constrained request surface a normal capability-compiler output, not an evaluation-only artifact;
2. add deterministic model-interface selection for llama.cpp-like runtimes;
3. keep native-tool and constrained-request paths byte/version bound in the model-surface contract;
4. update host/reference adapters and tests;
5. update packaging and Windows/Linux first-use examples;
6. only after the candidate is frozen, create new rc4 evidence if further qualification is requested.
