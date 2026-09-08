# ExactScope v1.0.0 — Grounding Runtime for Small & On-Device AI

ExactScope v1.0.0 is the first stable release of the grounding-first product direction.

ExactScope is a lightweight **grounding runtime and AI accuracy retrofit layer** for small LLMs, local AI, edge AI, and on-device models. It is not an LLM harness: it does not need to own sessions, agents, retries, or the inference engine. The default design moves factual uncertainty outside the model, resolves deterministic cases in the host when possible, and gives the existing model only compact approved evidence when generation is still required.

## Stable v1 scope

The stable public software/package scope is:

- **Linux x86-64 native grounding runtime** (`x86_64-unknown-linux-gnu`);
- native C ABI for immutable `.xsgi` grounding indexes;
- zero-copy index validation/binding;
- deterministic bounded BM25-v1 retrieval;
- caller-owned search scratch/output memory;
- deterministic compact evidence projection;
- a tiny demonstration-only provider and C11 integration example;
- deterministic package manifests/checksums and final-archive clean-room verification.

The runtime does not require a network service, model replacement, fine-tuning, agent loop, or Python on the deployed target. Python remains off-target compiler/reference/benchmark tooling.

## 30-second integration path

The release asset is:

```text
exactscope-grounding-1.0.0-x86_64-unknown-linux-gnu.tar.gz
```

After extraction, the bundled `examples/c/grounding.c` can be compiled against only the packaged headers and static library. The included 1.6 KB demonstration index verifies two known facts (`24 months` warranty and `73 percent` battery) without network or model inference.

Real deployments provide their own application/device/document/search evidence. ExactScope does **not** bundle a universal knowledge corpus.

## Accuracy evidence

A frozen 30-item matched factual screen across seven local models from 135M to 3.8B measured:

- model-only mean accuracy: **8.1%**;
- ExactScope grounding-path mean accuracy: **93.3%**;
- mean absolute uplift: **+85.2 percentage points**;
- false grounding in G: **0%**;
- unsupported authoritative assertions in G: **0%**;
- format failures in G: **0%**;
- deterministic host completion: **23/30** grounded items;
- model inference required: **7/30** grounded items.

The same semantic scores were reproduced after the native C-ABI/release integration work.

These are **candidate/provider/corpus/policy-bound results**, not a promise that every model or workload gains +85.2 points. Broader development evidence is intentionally reported too: HotpotQA and NQ development-mirror screens showed smaller, workload-dependent improvements. See the README and `docs/BENCHMARK.md` for exact scope and caveats.

## Native parity and release integrity

The v1 native grounding implementation preserves the Python reference behavior on the recorded qualification screens:

- NQ development mirror: 128/128 exact ranked-hit ordering, matched terms, and `f64` score bits;
- HotpotQA screen: 20/20 exact ranked-hit ordering and score bits;
- byte-exact evidence projection at 2 KiB and 4 KiB budgets;
- final-archive C11 clean-room execution using only packaged public headers, static library, and XSGI bytes.

Exact floating-point equality at deterministic tie-break points is intentional and part of the parity contract.

## Footprint

The default v1 SDK is deliberately separated from benchmark/provider data. Current Linux x86-64 package measurements are approximately:

- compressed SDK: **0.94 MB**;
- unpacked regular files: **4.66 MB**;
- native static library: **4.62 MB**;
- demonstration XSGI: **1.6 KB**.

The default-install packager fails closed above **10,000,000 compressed bytes** or **20,000,000 unpacked bytes**.

The 19.71 MB NQ `.xsgi` used for qualification is provider/benchmark data, not part of the generic product install. A deployment that selects provider data of that size must count it in that deployment's own footprint.

## Grounding semantics

ExactScope v1 keeps factual state explicit instead of collapsing retrieval outcomes into prompt prose. The Grounding Contract distinguishes states such as:

- `grounded`;
- `none`;
- `ambiguous`;
- `conflict`;
- `unavailable`.

Authoritative unresolved state does not silently fall back to model memory. Supplemental evidence may use different fallback policy. Authority is established by host/profile policy, never by retrieved text or ranking score.

## What remains experimental

This release does **not** claim stable physical ARM64/wearable performance. In particular, representative physical ARM64 RAM, latency, energy, thermal, or battery qualification has not been performed.

Also outside the stable v1 grounding asset scope:

- Windows grounding package support;
- Android/Linux ARM64 grounding support;
- grounding WebAssembly transport;
- arbitrary provider implementations without their own compatibility evidence.

Smart glasses, watches, phones, and other edge devices remain important design targets, but target-specific claims require target-specific measurements.

## Historical quantitative subsystem

The earlier deterministic `xs_calc` / `xs_eval` quantitative subsystem remains in the repository as a secondary capability. Historical rc3 results stay bound to the exact rc3 artifacts and are not transferred into v1 grounding claims.

## Verification

Download the release archive together with `SHA256SUMS` and `release-manifest.json`. Verify the outer digest before extraction; the archive also contains its own canonical `manifest.json` and `SHA256SUMS` covering every packaged payload.

See:

- `README.md` — product positioning, benchmark evidence, FAQ, and discovery terms;
- `docs/QUICKSTART.md` — shortest integration path;
- `docs/INSTALLATION.md` — embedding and ownership rules;
- `spec/GROUNDING_CONTRACT_V0_1.md` — logical grounding semantics;
- `spec/GROUNDING_RUNTIME_BUNDLE_V1.md` — stable package contract;
- `docs/BENCHMARK.md` — claim and benchmark boundaries.
