# ExactScope marketing claims playbook

Status: internal product/marketing guidance
Release context: **rc4 grounding implementation/pre-inference benchmark-ready work after completed v1.0.0-rc.3 qualification**
Date: 2026-09-06

This file prevents historical measurements from being generalized beyond their exact identities. rc3 may be described as a completed external-user quantitative/model-interface qualification input with five-model/install observations, but it does not establish universal accuracy, production support, or real-device energy/thermal claims. The strongest **pre-benchmark rc4** product message is **a tiny provider-neutral grounding layer implemented to improve everyday factual reliability without requiring a model-visible tool turn**. The contract/reference path/package harness exists and is no-inference tested; model uplift is not yet measured.

## 1. Default public positioning

Safe before the next grounding benchmark:

> ExactScope implements a compact grounding layer for small and on-device AI. The rc4 candidate prefetches scoped evidence before the model answers, presents only a small Grounding Frame, and keeps retrieval providers replaceable behind one contract. Existing deterministic `xs_calc`/`xs_eval` remains available for quantitative tasks.

Keep the important qualifier close:

> The rc4 grounding implementation has not yet established an accuracy or hallucination-reduction claim. Retrieval can miss or retrieve the wrong evidence, and the model can still ignore correct evidence; those failures are explicitly part of the frozen A/G benchmark contract.

Also safe:

- “The default rc4 grounding path is original-question prefetch followed by one model answer call.”
- “Grounding sources distinguish authoritative from supplemental no-hit behavior.”
- “ExactScope does not require one specific retrieval algorithm; exact/lexical, frozen semantic/vector and host-provided providers can share the same Grounding Contract.”
- “False grounding is treated as a first-class failure, not hidden behind final answer accuracy.”
- “ExactScope is designed for OEM/device/embedded/local-AI integration, not as a human calculator application or giant RAG framework.”
- “The deterministic quantitative core can run locally through a native C ABI or a no-import Wasm boundary.”
- “rc3 qualification found that native tool-call reliability varied by model/chat-template protocol rather than simply by model size.”
- “v1.0.0-rc.3 remains a prerelease and is not a stable/production-qualified release.”

## 2. What rc3 may claim now

rc3 may claim the following **only as exact rc3 observations**:

- the published evaluation/OEM artifacts and release-level/internal checksums were independently exercised;
- Linux and Windows clean-room first-use paths passed the recorded package/core/capability checks;
- a five-model A/C/D matrix was completed and bound to the exact rc3/model/runtime/corpus identities;
- Qwen3.5 0.8B/2B showed frequent native tool recognition while Gemma 3 270M, LFM2.5 350M and Phi-4-mini 3.8B did not produce a comparable usable native-tool path under the frozen runtime/templates;
- the largest tested model was not the most reliable tool caller, rejecting a monotonic model-size explanation;
- valid calls reaching ExactScope were much stronger than the end-to-end model-selection result;
- Android/Linux ARM64 package/doctor checks passed contract-level checks.

These are observations for the frozen rc3 setup, not universal statements about all versions/models/runtimes.

## 3. What remains unmeasured or unsupported

Say explicitly:

- **universal model uplift across small models: not established**;
- **rc4 everyday factual-accuracy uplift: not established**;
- **rc4 hallucination / wrong-confident-answer reduction: not established**;
- **rc4 false-grounding rate on a frozen candidate: not yet measured**;
- **representative physical ARM64 RAM/latency/energy/thermal behavior: NOT MEASURED**;
- **production readiness/stable support: not established**.

Do not use old r20 or rc3 numbers to fill rc4 blanks.

## 4. Historical r20 evidence — allowed only as historical evidence

The older internal preregistered Statistics development evidence accumulated through `statistics-core-8-ai-r20` belongs to a **45,804-byte r17 Statistics serving runtime**, not rc3.

When a historical example is useful, safe wording is:

> In an older preregistered synthetic internal Statistics development evaluation tied to a 45,804-byte r17 runtime, Qwen3 0.6B Q8_0 scored 111/144 with the semantic-only Statistics surface versus 0/144 model-only. Separate Llama 3.2 and Qwen2.5 0.5B runs showed much smaller uplift and different preferred surfaces. These are historical development results, not rc3 scores or general model-accuracy claims.

The key safe cross-family conclusion is:

> Historical evidence supported the need for target-model/task-specific qualification: the best selected surface and uplift magnitude varied substantially by model.

Do not put the 111/144 result in the rc3 hero area without the “older r17 / historical / synthetic internal” boundary. The rc3 README intentionally leads with release/integration status instead.

## 5. Historical larger-model comparison

Historical r17 evidence included a larger Qwen3 1.7B model-only reference. It had substantial token-limit failure under that strict benchmark contract.

Never turn it into:

- “4× better than a larger model”;
- “0.6B + ExactScope replaces 1.7B”;
- “ExactScope eliminates the need for larger models.”

At most, present the raw historical arms with the token-limit limitation and synthetic/internal scope in the same paragraph.

## 6. Binary-size claims

For rc3, use only measurements generated and bound to the exact rc3 artifact under test. Do not recycle r17/r28/r6 byte numbers as current release measurements.

Historical values may remain in historical result/decision documents with their exact revision identity.

Do not say:

- “The complete AI upgrade is only 12 KB.”
- “ExactScope only needs 12 KB.”
- “rc3 is 45 KB” unless an exact rc3 artifact has actually been built, hashed, and the statement names what that 45 KB represents.

A semantic delta is not the whole integration size, and a Wasm file size is not a model/hardware footprint.

## 7. Memory claims

A selected Wasm may declare a small fixed linear-memory range. That number is **not** total product RAM.

Do not say:

- “Runs in 64 KiB RAM.”
- “Cuts RAM by X%.”

unless a representative product target was measured and the metric is clearly defined.

Safe wording before qualification:

> ExactScope uses bounded memory contracts in the component; full process/device resident memory remains a target-qualification measurement.

## 8. Latency claims

Do not use historical desktop/model-run latency as an on-device product latency claim.

Do not say:

- “adds negligible latency”;
- “8× faster on-device”;
- “sub-millisecond on embedded hardware”

without an exact representative target, workload, sample count, distribution, runtime configuration, and release-artifact identity.

Target reports should prefer p50/p95/p99 or another preregistered distribution summary rather than one favorable mean.

## 9. Energy / thermal / battery claims

The rc3 qualification did not have a physical ARM64 target, so representative target energy/thermal/battery behavior remains **NOT MEASURED**. Desktop/model latency is not a substitute.

Do not say:

- “extends battery life”;
- “uses less energy than a bigger model”;
- “avoids thermal throttling”;
- “extends hardware life.”

Safe evaluation objective:

> Evaluate whether a narrow software capability can meet the product requirement on an existing constrained device before committing to a larger model or hardware upgrade.

That is a hypothesis to test, not an established saving.

## 10. Commercial/build-vs-buy claims

Safe:

> ExactScope is designing a reusable small-model grounding subsystem around provider-neutral evidence contracts, authority/freshness/conflict policy, compact context budgets, reproducible provider/index identity and benchmark/qualification tooling, while retaining deterministic quantitative capability where needed.

Not safe without customer evidence:

- “cheaper than building it in-house”;
- “cuts engineering cost by 80%”;
- “eliminates model/hardware upgrade cost”;
- “production-ready across OEM platforms.”

The commercial argument is currently the **scope of reusable engineering/qualification work**, not a measured customer TCO saving.

## 11. Model-matrix wording

The completed rc3 core matrix used five deliberately diverse models:

- Gemma 3 270M IT;
- LFM2.5 350M;
- Qwen3.5 0.8B;
- Qwen3.5 2B;
- Phi-4-mini-instruct 3.8B.

Safe wording:

> In the frozen rc3 llama.cpp qualification, Qwen3.5 models recognized native tools much more often than Gemma/LFM/Phi, while the largest tested Phi model was not the strongest native tool caller. The result points to chat-template/tool-protocol compatibility and model-surface difficulty, not a simple model-size relationship.

When giving individual scores, include the exact rc3 identity/surface and denominator and link to the closeout/evidence. Do not imply the matrix is a general leaderboard or that rc4 inherits the scores.

## 12. Stable-support wording

`v1.0.0-rc.3` is a prerelease.

Do not call it:

- production-ready;
- Tier 1 supported;
- hardware-qualified;
- stable LTS;
- certified for Android/wearables/smart glasses generally.

A future stable claim should be based on exact immutable artifacts plus model/target/support evidence that satisfies the current `ROADMAP.md`/`COMPATIBILITY.md` gates. The rc3 qualification handoff is historical and is not the active promotion checklist.

## 13. Evidence citation checklist

Any quantitative public claim should name or link enough information to reconstruct what was measured:

- release/capability identity;
- artifact SHA-256;
- model + quantization + model file/revision SHA-256 when applicable;
- corpus/task count;
- arm/surface;
- generation/scoring contract;
- target hardware/runtime for device metrics;
- measured count/denominator;
- known invalid/timeout/exclusion counts.

If these fields are unavailable, keep the wording qualitative or explicitly historical/unmeasured.

## 14. Current recommended README hero

Use the current product-state message rather than an old score:

> **ExactScope is a tiny deterministic quantitative capability layer for small/on-device AI. The completed rc3 qualification showed that native tool-call reliability depends strongly on runtime/chat-template protocol and model-surface cost, so active rc4 development uses constrained JSON/GBNF as the compatibility baseline and native tools only when support is proven before inference.**

Keep `v1.0.0-rc.3` labeled as the latest frozen prerelease, not stable support. Link the qualification closeout when referencing rc3 results.
