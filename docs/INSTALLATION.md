# Installation and embedding profiles

ExactScope is loaded as a component of another AI runtime. **The runtime consumer is the AI system; a developer/OEM engineer is the integrator. ExactScope is not a human-facing calculator or end-user application.** It does not require a daemon, account, database, or network service.

The product goal is that integrators evaluate and deploy **prebuilt capability artifacts**, not the Rust workspace. End users should normally never install, configure, or invoke ExactScope directly.

## 1. Five-minute principle

A release evaluator should be able to:

```text
download/receive product artifact
  -> verify
  -> link/load into the AI runtime
  -> run smoke test
  -> bind xs_calc plus the selected capability slice
  -> route supported AI requests through ExactScope
```

No Rust/Python/Node/Java runtime is required on the target.

See [QUICKSTART.md](QUICKSTART.md).

## 2. Primary v0.1 release profiles

### 2.1 Native static C ABI

Preferred native bundle:

```text
exactscope-native-<version>-<target>/
  include/
    exactscope.h
  lib/
    libexactscope.a      # or exactscope.lib on MSVC
    cmake/ExactScope/ExactScopeConfig.cmake
  hotset/
    catalog.json
    xs-eval.tool.json
    xs-eval.gbnf
    binding-sha256.txt
  manifest.json
  SHA256SUMS
  LICENSE-MIT
  LICENSE-APACHE
  tools/                 # workstation-only verification helpers where useful
```

Desired integration:

```cmake
find_package(ExactScope CONFIG REQUIRED)
target_link_libraries(my_product PRIVATE ExactScope::exactscope)
```

The host then initializes the context, binds its product hot set, and calls `xs_eval` directly for known operations.

`xs_find` is optional fallback functionality, not a required runtime hop.

### 2.2 No-import WebAssembly

Preferred portable bundle:

```text
exactscope-wasm-<version>/
  exactscope.wasm
  hotset/
    catalog.json
    xs-eval.tool.json
    xs-eval.gbnf
    binding-sha256.txt
  manifest.json
  SHA256SUMS
  examples/
```

Host steps:

1. verify artifact digest/manifest;
2. instantiate with no imports/WASI;
3. validate ABI/version/exports;
4. allocate caller regions according to the Wasm ABI;
5. run a canonical smoke vector;
6. register direct hot-set `xs_eval` use;
7. enable discovery only if the product needs it.

## 3. Current experimental SDK

The repository already produces experimental ARM64 OEM SDK bundles with:

- public headers;
- native static library;
- relocatable `ExactScope::exactscope` CMake package;
- manifest/checksum data;
- developer-side `exactscope_doctor.py`;
- wearable reference integration materials.

These artifacts are useful integration evidence but are not yet stable permanent release assets.

The doctor is a developer-workstation tool. It is not a target runtime dependency.

## 4. Capability-slice installation

A product should select or compile the **smallest capability slice that covers its target task families** and bind that slice to the installed runtime/pack registry digest. The broad domain source catalog is a build-time asset; it is not the normal model-facing surface.

Installation or build tooling should produce:

- selected semantic operation keys/signatures and revisions;
- compact argument/method hints;
- `xs_calc` assets when the generic bounded arithmetic lane is enabled;
- a compact OpenAI-compatible `xs_eval` asset for the selected slice;
- GBNF/JSON Schema when supported;
- minimal prompt guidance;
- registry/pack/profile digests;
- model-difficulty metadata;
- footprint/conformance metadata.

The full operation catalog must not be injected into a weak-model prompt by default.

At runtime, the preferred hot path is already bound:

```text
short arithmetic -> xs_calc
known reviewed method -> xs_eval directly
unknown semantic operation -> optional xs_find cold/development path
```

Any digest/revision/profile mismatch invalidates the cached binding.

## 5. Dynamic packs

Dynamic `.xsp` loading remains supported architecture but is not the primary v0.1 product path.

Use dynamic packs when a host genuinely needs pack updates independent of the runtime artifact.

The host owns:

- acquisition/storage;
- authenticity/signature policy;
- immutable pack lifetime;
- registry lifecycle;
- update/rollback.

ExactScope validates structure, semantics, limits, and collisions. It does not download packs itself.

Dynamic discovery maturity may remain Experimental without blocking a focused v0.1 release.

## 6. Android

Android AAR/Prefab is a P2 convenience package around the same C ABI.

Target shape:

```text
AAR
  prefab/modules/exactscope/include/exactscope.h
  jni/arm64-v8a/<native artifact>
  META-INF/exactscope/manifest.json
  assets/exactscope/hotset/*
```

The Kotlin/JNI layer may transport values/statuses but may not implement formulas, rounding, classification, unit conversion, or error repair.

Only evidenced ABIs are included in a supported release.

## 7. Apple platforms

Apple packaging is secondary to the first product proof. A future XCFramework/Swift wrapper forwards to the same C ABI and contains no calculation logic.

## 8. Linux/Windows/macOS archives

Native archives should remain self-contained and package-manager independent. System package recipes may be added later as convenience only.

The target must not require:

- Python;
- Node.js;
- Java;
- Rust;
- system-wide ExactScope service;
- administrator/root privileges merely to execute a local application-bundled library;
- network access;
- cloud login.

Platform policy may still determine how a host application or extension is installed.

## 9. Closed devices and wearables

ExactScope is **not an end-user installable product**. It is integrated by the product's software team into whatever executable boundary the AI stack legitimately exposes, such as:

- application or firmware-bundled native library loading;
- product-owned plugin/extension loading;
- an embedded WebAssembly runtime;
- a host extension API;
- a paired local compute host controlled by the product stack.

A closed device with no such integration boundary cannot be retrofitted by ExactScope independently. ExactScope never asks the consumer to sideload a calculator or manually select formulas.

Compatibility claims must name the actual product integration boundary rather than implying generic “smart-glasses support.”

## 10. Self-test and qualification

Every stable release bundle should include enough metadata to run a canonical self-test against the exact artifact.

Target evidence should record:

- artifact/core/ABI version;
- hot-set/pack digest;
- canonical smoke operation/result;
- context/scratch sizes;
- runtime status;
- optional latency/energy evidence.

A successful self-test means “ready for this target test,” not automatically “Tier 1 supported.”

## 11. Updates and rollback

The host stages a complete new component set, verifies it, runs smoke/conformance checks, then atomically switches the binding.

Where the platform offers durable A/B slots, the existing wearable A/B principles may be reused.

ExactScope does not create a privileged background updater when the host platform already owns software distribution.

## 12. Release artifact rule

Stable documentation and benchmark results must refer to permanent release-shaped artifacts, not expiring CI artifacts or an arbitrary local build.

Each release bundle should include:

- source commit;
- artifact digest;
- ABI/core version;
- target/execution profile;
- capability-profile ID/revision when used;
- selected hot set/domain-source operations and revisions;
- model-surface schema/grammar/prompt digests;
- compiler/linker/profile-generator metadata;
- size/memory/model-difficulty evidence;
- conformance status;
- support label.

## 13. Installation success criterion

An integrator should not need to understand the ExactScope Rust implementation to evaluate the product.

If the normal evaluation path is “clone repo, install Rust, understand workspace features, cross-compile, then write your own AI adapter,” installation is not finished.
