# ExactScope marketing claims playbook

Status: internal product/marketing guidance
Release context: **v1.0.0-rc.2 integration & qualification candidate**
Date: 2026-09-05

This file prevents historical development measurements from being presented as rc2 product evidence. The strongest current public message is **a packaged, deterministic, narrow capability component that is ready to be independently evaluated**, not a new accuracy/latency/energy claim.

## 1. Default public positioning

Safe:

> ExactScope is a tiny deterministic quantitative capability component for small and on-device AI. It lets a product expose a narrow reviewed `xs_calc`/`xs_eval` surface instead of asking a weak model to perform every numerical step probabilistically.

Keep the important qualifier close:

> Determinism applies after the model has selected a valid operation/plan and arguments. Model selection and argument extraction can still fail.

Also safe:

- “ExactScope is designed for OEM/device/embedded/local-AI integration, not as a human calculator application.”
- “The deterministic core can run locally through a native C ABI or a no-import Wasm boundary.”
- “Selected capability builds are designed to minimize model-visible choices and fail closed on excluded operations.”
- “v1.0.0-rc.2 is an integration and qualification candidate, not a stable/production-qualified release.”

## 2. What rc2 may claim now

Before the separate qualification session, rc2 may claim **implementation/package properties that are verified for the exact source/release process**, such as:

- the active Statistics/Economics architecture is code-side implemented;
- the release workflow is configured to produce Windows/Linux x86-64 evaluation SDKs and Android/Linux ARM64 static OEM SDKs;
- release bundles carry manifests/checksums and model-facing integration assets;
- the model-surface identity/compatibility machinery is fail closed;
- the broad domain catalog is a build-time asset rather than a required weak-model prompt surface;
- the benchmark model downloader resolves model revisions and records local file SHA-256 values without running inference.

Do not convert a workflow/configured asset into a claim that the asset was successfully published until the GitHub release actually contains it.

## 3. What rc2 must say is unmeasured

Until the next evidence session is complete, say explicitly:

- **rc2 model uplift: unmeasured**;
- **rc2 representative target RAM/latency/energy: unmeasured**;
- **rc2 production readiness/stable support: not established**.

Do not use old r20 numbers to fill these blanks.

## 4. Historical r20 evidence — allowed only as historical evidence

The older internal preregistered Statistics development evidence accumulated through `statistics-core-8-ai-r20` belongs to a **45,804-byte r17 Statistics serving runtime**, not rc2.

When a historical example is useful, safe wording is:

> In an older preregistered synthetic internal Statistics development evaluation tied to a 45,804-byte r17 runtime, Qwen3 0.6B Q8_0 scored 111/144 with the semantic-only Statistics surface versus 0/144 model-only. Separate Llama 3.2 and Qwen2.5 0.5B runs showed much smaller uplift and different preferred surfaces. These are historical development results, not rc2 scores or general model-accuracy claims.

The key safe cross-family conclusion is:

> Historical evidence supported the need for target-model/task-specific qualification: the best selected surface and uplift magnitude varied substantially by model.

Do not put the 111/144 result in the rc2 hero area without the “older r17 / historical / synthetic internal” boundary. The rc2 README intentionally leads with release/integration status instead.

## 5. Historical larger-model comparison

Historical r17 evidence included a larger Qwen3 1.7B model-only reference. It had substantial token-limit failure under that strict benchmark contract.

Never turn it into:

- “4× better than a larger model”;
- “0.6B + ExactScope replaces 1.7B”;
- “ExactScope eliminates the need for larger models.”

At most, present the raw historical arms with the token-limit limitation and synthetic/internal scope in the same paragraph.

## 6. Binary-size claims

For rc2, use only measurements generated and bound to the exact rc2 artifact under test. Do not recycle r17/r28/r6 byte numbers as current release measurements.

Historical values may remain in historical result/decision documents with their exact revision identity.

Do not say:

- “The complete AI upgrade is only 12 KB.”
- “ExactScope only needs 12 KB.”
- “rc2 is 45 KB” unless an exact rc2 artifact has actually been built, hashed, and the statement names what that 45 KB represents.

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

No rc2 energy/thermal qualification exists before the next session.

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

> ExactScope packages deterministic numeric semantics, weak-model interfaces, constrained generation assets, capability specialization, conformance, artifact identity, and evidence tooling into one reusable subsystem.

Not safe without customer evidence:

- “cheaper than building it in-house”;
- “cuts engineering cost by 80%”;
- “eliminates model/hardware upgrade cost”;
- “production-ready across OEM platforms.”

The commercial argument is currently the **scope of reusable engineering/qualification work**, not a measured customer TCO saving.

## 11. Model-matrix wording

The planned rc2 core matrix contains five deliberately diverse models:

- Gemma 3 270M IT;
- LFM2.5 350M;
- Qwen3.5 0.8B;
- Qwen3.5 2B;
- Phi-4-mini-instruct 3.8B;
- optional separate Gemma 3n E2B product profile.

Safe wording:

> rc2 will be qualified on a deliberately small multi-vendor/multi-scale model matrix; results are currently unmeasured.

Do not publish blank rows or planned model names in a way that visually implies a score.

## 12. Stable-support wording

`v1.0.0-rc.2` is a prerelease.

Do not call it:

- production-ready;
- Tier 1 supported;
- hardware-qualified;
- stable LTS;
- certified for Android/wearables/smart glasses generally.

A future stable claim should be based on the exact release artifacts and the promotion gate in `docs/QUALIFICATION_HANDOFF.md`.

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

Use the current release-state message rather than an old score:

> **ExactScope v1.0.0-rc.2 is a code-side-complete integration and qualification candidate for adding narrow deterministic quantitative capability to small/on-device AI. rc2 model and real-device qualification are intentionally unmeasured until the public release is evaluated as an external user.**

This is less flashy than copying old r20 numbers into a new release, but it preserves the evidence boundary needed for credible qualification.
