# ExactScope product direction

This document defines the product boundary that implementation and packaging decisions should optimize for. It is intentionally narrower than a general AI platform.

## 1. Product sentence

ExactScope is a **tiny resident academic-computation micro-runtime for local AI**.

Its job is to remove deterministic quantitative work from a language model and execute that work with explicit methods, exact decimal/rational semantics, bounded memory, stable errors, and reproducible provenance.

The target experience is not "open the ExactScope app." It is:

```text
install/enable ExactScope component
        -> AI host discovers xs_find / xs_eval
        -> selected academic packs are available locally
        -> no service, account, network, or UI remains running
```

Where a platform permits user-installed extensions, WebAssembly modules, plugins, or shared components, ExactScope should be installable by an end user. Closed platforms that do not expose any executable extension boundary cannot be made user-installable by ExactScope alone; support there requires a host integration path.

## 2. Competitive axis

ExactScope does not try to beat large vendors by providing more model FLOPS. That would destroy the project's advantage.

The competitive axis is **less total computation for deterministic academic work**:

- a small model identifies the operation and extracts values;
- ExactScope performs the calculation instead of the model generating arithmetic tokens;
- deterministic code returns the same canonical result on conforming targets;
- a narrow hot set can remain resident in very small memory;
- no cloud round trip is required;
- provenance and failure modes are machine-readable.

The useful comparison is therefore not "ExactScope versus a datacenter GPU." It is:

```text
model-only quantitative task
vs
small model + ExactScope quantitative task
```

Measure final accuracy, model tokens, wall latency, resident bytes, scratch bytes, and energy per successful result.

## 3. Niche to own first

The first defensible niche is common formula-driven academic computation that is valuable to small local AI but wasteful or unreliable when performed through language-model reasoning.

Priority domains:

1. `math-basic` — common arithmetic, ratios, percentages, proportions, and deterministic helpers;
2. `statistics-core` — exact bounded vector statistics and formula helpers;
3. `econ-undergrad` — explicit textbook microeconomics, macroeconomics, labor, trade, and growth identities;
4. later packs only when the method can be specified deterministically and bounded tightly.

A domain belongs in ExactScope when all of the following are true:

- the operation has an explicit method or algorithm;
- the required inputs can be represented without hidden model judgment;
- success and failure semantics can be tested with golden vectors;
- the runtime cost can be bounded;
- a compact operation definition is cheaper and more reliable than model reasoning.

Forecasting, causal inference from incomplete context, open-ended policy analysis, and arbitrary symbolic mathematics remain outside the core.

## 4. Runtime product shape

The core product is not an application and not a daemon. It is one of the existing execution profiles packaged as a resident component.

Preferred forms, in order of portability:

1. **Fused no-import Wasm** — one module containing the kernel and selected hot packs;
2. **Native resident library** — one shared/static library plus manifest on hosts that expose a native extension ABI;
3. **AI-host extension bundle** — host metadata plus the same Wasm/native core, with no duplicate evaluator;
4. **Dynamic pack profile** — only when users need independent pack updates and the host already provides safe persistent storage.

A consumer package may include a tiny installer or registration command on a supported host, but installation tooling must exit after registering immutable artifacts. It must not leave an ExactScope background service running.

## 5. Small-device rules

The following rules protect the niche:

- keep `exactscope-kernel` `no_std` and allocator-free by default;
- keep the fused/static execution path heap-free;
- do not add HTTP, TLS, databases, logging frameworks, async runtimes, or package managers to the minimum runtime;
- prefer build-time validation and generated immutable tables over runtime parsing;
- bound vector length, VM steps, stack depth, outputs, and pack size before work begins;
- keep wrappers thin and forbid numeric reimplementation outside the core;
- let hosts choose a small academic hot set instead of loading every operation everywhere;
- preserve a scalar path for devices that cannot afford vector features;
- never claim platform support from compilation alone.

## 6. Accuracy rules

ExactScope should win trust by being deliberately boring and reproducible:

- decimal inputs are exact canonical base-10 values;
- baseline computation avoids binary floating point;
- operation methods are explicit in stable keys/metadata;
- ambiguous alternatives are separate operations rather than hidden heuristics;
- classification uses unrounded internal values;
- bounded overflow fails instead of wrapping or saturating;
- insufficient data, missing assumptions, domain errors, and unit mismatches are typed failures;
- successful results identify pack, operation revision, numeric profile, and rounding policy.

## 7. Enterprise/OEM adoption wedge

The project should be easy for a device or AI-platform team to adopt without asking that team to bet on an ExactScope-specific application stack.

The strongest initial enterprise value proposition is:

1. **model decoupling** — deterministic quantitative semantics stay stable while a vendor swaps or upgrades its local model;
2. **qualification isolation** — numeric behavior, memory bounds, malformed-input handling, and artifact identity can be tested independently from model quality;
3. **tiny bill of materials** — the minimum target does not inherit a network client, service process, package manager, database, or language runtime;
4. **hot-set packaging** — an OEM can fuse only the operations needed by a product SKU instead of shipping an entire symbolic or scientific-computing environment;
5. **portable integration boundary** — C ABI and no-import Wasm let the same semantic core move between firmware, Android/Linux companion compute, desktop AI hosts, and future extension runtimes;
6. **auditable updates** — manifests, digests, golden vectors, and A/B activation rules make updates reviewable by a platform security/reliability team.

This is the niche to defend: **deterministic quantitative offload for constrained local AI**. ExactScope should not expand into inference, retrieval, cloud orchestration, or a general plugin platform merely to look larger.

A large vendor should be able to evaluate ExactScope with a narrow proof-of-value: link one artifact, expose two tool calls, run the conformance/self-test bundle, and compare model-only versus model-plus-ExactScope accuracy/tokens/latency/energy on its own hardware.

## 8. Installation target

The desired supported-host experience is:

```text
1. install one ExactScope component bundle
2. host verifies manifest/digest and ABI
3. host loads the component without network access
4. ExactScope self-test evaluates a canonical vector
5. xs_find / xs_eval become available to the local AI
```

No compiler, Rust toolchain, Python, Node.js, Java runtime, administrator account, cloud login, writable home directory, or always-running process should be required on the target.

For AI glasses, support should be described by **host capability**, not marketing model name. A glasses platform is directly user-installable only if its operating environment exposes an extension/application/runtime boundary capable of loading ExactScope or a host that can do so. Otherwise the correct deployment is on the paired local host, not an attempt to bypass the device platform.

## 9. Current implementation position

The repository is past the design-only stage. It already has:

- checked deterministic `Decimal64` and exact rational work arithmetic, including correctly rounded square root;
- the bounded v0.1 scalar VM subset including integer power, comparisons/boolean/select, square root, and explicit round;
- executable economics operations including the original midpoint elasticity slice;
- a native C ABI with caller-owned context/scratch, dynamic-pack support, and zero-copy statistics vectors;
- a `statistics-core` executable slice covering sum, arithmetic/weighted mean, population/sample variance and standard deviation, population/sample covariance, Pearson correlation, and simple linear regression;
- canonical formula/kernel `.xsp` compilation/loading with fused↔dynamic statistics conformance;
- no-import WebAssembly integration with scalar Tiny JSON, typed statistics-vector evaluation, and deterministic-CBOR TinyWire `find`/scalar/vector `eval`;
- Tiny JSON model-facing scalar calls and compact TinyWire transport for bounded host/device paths;
- a wearable reference host and crash-consistent A/B update reference;
- experimental ARM64 OEM SDK packaging with a relocatable `ExactScope::exactscope` CMake target and a bundled developer-side doctor that checks integrity, ABI, and ELF architecture before target testing.

The largest remaining product gaps are:

1. complete reviewed official math/statistics/economics source packs and golden corpora;
2. Android Prefab/AAR and other host convenience packaging without duplicating the evaluator;
3. a complete target-side self-test/qualification helper and canonical smoke execution;
4. permanent signed/checksummed release artifacts and compatibility manifests;
5. measured real-device footprint, latency, energy, offline behavior, and power-loss qualification.

## 10. Decision test for future features

Before adding a feature, ask:

> Does this make deterministic academic computation smaller, more accurate, easier for a local AI host to call, or easier for an end user to install as a component?

If the answer is no, the feature should normally live outside ExactScope core.
