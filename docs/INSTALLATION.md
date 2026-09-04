# Installation and embedding profiles

ExactScope is loaded as a component of another AI runtime. It is not a standalone calculator application and does not require a daemon, account, database, or network service.

The product goal is that evaluators use **prebuilt artifacts**, not the Rust workspace.

## 1. Five-minute principle

A release evaluator should be able to:

```text
download
  -> verify
  -> link/load
  -> run smoke test
  -> bind hot-set metadata
  -> call xs_eval directly
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

## 4. Hot-set installation

A product should select a small 8-32 operation hot set and bind it to the installed runtime/pack registry digest.

Installation or build tooling should produce:

- canonical operation keys/signatures;
- operation revisions;
- compact argument/method hints;
- OpenAI-compatible direct eval asset;
- GBNF when supported;
- registry/pack digest.

The full operation catalog does not need to be injected into the model prompt.

At runtime:

```text
known op -> xs_eval directly
unknown op -> xs_find -> cache/bind -> future direct xs_eval
```

Any digest/revision mismatch invalidates the cached binding.

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

## 9. User-installable devices and wearables

ExactScope can be directly user-installable only when the device/host exposes a legitimate executable boundary such as:

- application installation;
- native plugin/extension loading;
- WebAssembly runtime;
- host extension API;
- paired local compute host.

A closed device with no such boundary cannot be made directly installable by ExactScope alone. In that case, execution may occur on the paired phone/host if that product design permits it.

Compatibility claims must name the actual loading boundary rather than implying generic “smart-glasses support.”

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
- target/profile;
- selected hot set/packs and revisions;
- compiler/linker metadata;
- size/memory evidence;
- conformance status;
- support label.

## 13. Installation success criterion

An integrator should not need to understand the ExactScope Rust implementation to evaluate the product.

If the normal evaluation path is “clone repo, install Rust, understand workspace features, cross-compile, then write your own AI adapter,” installation is not finished.
