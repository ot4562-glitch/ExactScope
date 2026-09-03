# Installation and embedding profiles

ExactScope is installed into an AI runtime, not launched by a human. The project deliberately avoids a required daemon, package manager, database, account, network connection, or configuration UI.

No installable runtime exists yet. This document freezes the intended release layouts so implementation and packaging do not invent incompatible integration paths later.

## 1. Choose the smallest profile that fits

| Profile | Files needed by product | Runtime pack parsing | Heap required | Best target |
|---|---:|---:|---:|---|
| Fused Wasm | one `.wasm` | no | no | wearable/embedded/portable host |
| Fused native static | header + one static library | no | no | firmware/native appliance |
| Static data packs | header + library + embedded `.xsp` bytes | yes at init | caller arena only | updatable app without filesystem dependency |
| Dynamic data packs | header + library + `.xsp` files | yes | caller arena only | phone/desktop companion runtime |
| Android AAR | one `.aar` | profile-dependent | profile-dependent | Kotlin/Java companion app |

A product should not install the generic dynamic runtime when a fused pack is sufficient. A product should not embed an HTTP or MCP adapter unless its host already uses that protocol.

## 2. Fused WebAssembly

Planned release file:

```text
exactscope-<pack-set>-<version>-wasm32v1-none.wasm
```

Example:

```text
exactscope-econ-undergrad-0.1.0-wasm32v1-none.wasm
```

Host steps:

1. load the module from application/firmware resources;
2. reject it if the release SHA-256 does not match host update policy;
3. instantiate with an empty import object;
4. inspect that required exports and one memory exist;
5. read `xs_abi_version()` and reject an unsupported major;
6. call `xs_wasm_reserved_end()` and grow memory for nonoverlapping request/output regions;
7. call `xs_wire_request()` using Tiny JSON or TinyWire;
8. cache the immutable module/pack digest alongside model-tool metadata.

No extraction, installer, filesystem write, background service, environment variable, or network access is required. The complete memory contract is in `spec/WASM_ABI_V0_1.md`.

## 3. Native C ABI

Planned static archive layout:

```text
exactscope-<version>-<target>/
  include/
    exactscope.h
    exactscope_wasm.h
  lib/
    libexactscope.a        # Unix-like targets
    exactscope.lib         # Windows MSVC
  packs/                   # omitted for fused archives
  manifest.json
  SHA256SUMS
  LICENSE-MIT
  LICENSE-APACHE
```

Minimum integration:

```c
#include <exactscope.h>
```

The host allocates context, arena, scratch, input, and output memory. The library owns no global allocator and starts no threads. Static-linking is the preferred embedded/native profile because it removes loader and deployment variation.

A shared library may be published for desktop/mobile integration, but it must export only the documented `xs_*` allowlist and carry the same ABI conformance record as the static archive.

## 4. Android AAR

Planned AAR contents:

```text
jni/arm64-v8a/libexactscope_jni.so
jni/armeabi-v7a/libexactscope_jni.so       # Tier 2 after evidence
jni/x86_64/libexactscope_jni.so            # emulator/Tier 2 after evidence
headers/exactscope.h
assets/exactscope/packs/*.xsp               # dynamic profile only
META-INF/exactscope/manifest.json
```

The Kotlin/Java wrapper is intentionally small:

- load one JNI library;
- copy direct byte buffers into typed C ABI calls without recalculation;
- expose `find` and `eval` to the local AI runtime;
- preserve status, value strings, classification, pack identity, and revision;
- never implement formulas, rounding, unit conversion, or error repair in Kotlin.

The release AAR statically links private native dependencies so an application does not have to resolve a graph of native shared libraries. ABI entries are included only after their exact artifact passes the target compatibility matrix.

## 5. Apple platforms

Planned native package:

```text
ExactScope.xcframework/
  ios-arm64/
  ios-arm64_x86_64-simulator/               # after Tier evidence
  macos-arm64_x86_64/                       # per slice evidence
```

Swift bindings wrap the C header. Calculations remain in the same native core. No Swift numeric reimplementation is permitted.

## 6. Scope-pack installation

A dynamic `.xsp` installation is always host-controlled:

1. host obtains bytes through its existing application/update path;
2. host verifies distribution authenticity according to its own policy;
3. host retains immutable bytes for the complete mount lifetime;
4. `xs_pack_mount` validates all structure, CRC, IDs, programs, limits, and collisions;
5. host freezes the registry before serving model requests when mutation is no longer needed;
6. model-facing discovery metadata is generated from the mounted digest, not a separate stale catalog.

ExactScope never downloads a pack itself. Deleting or replacing files does not mutate an already mounted registry; the host creates a new context and mounts a complete new set.

## 7. Compatibility negotiation

At startup the host compares:

- ABI major/minor;
- pack format major/minor;
- numeric profile;
- enabled operation/features;
- maximum frame/vector limits;
- artifact and mounted-pack digests.

Rules:

- ABI-major mismatch: reject;
- required ABI minor newer than core: reject;
- unsupported pack format major: reject;
- operation key absent: return `UNKNOWN_OPERATION` rather than substitute another operation;
- operation revision mismatch: rediscover/rebind; never assume compatible semantics;
- disabled discovery: direct cached keys remain usable only when bound to the same registry digest.

## 8. AI tool registration

The host registers exactly two default tools:

```text
xs_find(q,n)
xs_eval(op,a)
```

The schemas are checked into `spec/schemas/`. A product may preload 8–32 generated hot-set signatures tied to the installed registry digest. It must not put the entire pack catalog into a tiny model's prompt by default.

For an appliance that always invokes known operations, discovery can be omitted entirely and the product can call the typed ABI directly.

## 9. Updates and rollback

A release package contains:

- artifact hash;
- source commit;
- Rust/compiler/linker versions;
- ABI/pack/numeric profile versions;
- feature list;
- operation pack IDs, versions, revisions, and digests;
- size and memory measurements;
- conformance results;
- support tier per target.

Updates are atomic at the host level: stage a complete artifact/set, verify it, initialize and run a smoke vector, then switch the AI tool binding. Keep the previous complete artifact for rollback. Do not replace individual bytes or operations inside a mounted pack.

## 10. No hidden installation requirements

A Tier 1 ExactScope package must not require:

- Python, Node.js, Java, Rust, or another language runtime on the target;
- a shell;
- administrator/root access;
- a writable home directory;
- network connectivity;
- dynamic package downloads;
- model-specific calculation prompts;
- locale configuration;
- background processes.

Build-time tools may require Rust and Python, but those tools are not part of device installation.
