# ExactScope Wearable OEM SDK Bundle v0.1

Status: **normative packaging contract for experimental cross-built artifacts**.

This document defines the files and metadata an OEM/device team receives when integrating the native ExactScope wearable runtime. A bundle produced under this contract proves that the source was cross-built for the named target and that the archive is internally reproducible and integrity-checked. It does **not** prove that a particular commercial glasses product, SoC, board, thermal envelope, or operating-system image is qualified.

## 1. Initial native targets

The v0.1 packager accepts exactly:

```text
aarch64-linux-android
aarch64-unknown-linux-musl
```

These targets deliberately cover two common integration classes:

- Android/Android-derived arm64 application or native-service environments;
- small Linux arm64 companion/edge systems that prefer a static musl-compatible boundary.

A target name in the bundle is a Rust compilation target, not a claim that every device using that OS family has passed ExactScope qualification.

## 2. Archive identity

The archive name is:

```text
exactscope-wearable-sdk-<project-version>-<target>.tar.gz
```

The archive has one top-level directory of the same name without `.tar.gz`.

The packager MUST produce byte-identical archives for identical:

- repository bytes;
- native library bytes;
- target;
- source commit;
- toolchain string.

Tar metadata is normalized:

- UID/GID: `0`;
- user/group names: empty;
- modification time: Unix epoch `0`;
- file mode: `0644`;
- directory mode: `0755`;
- member ordering: deterministic lexical ordering;
- gzip timestamp and filename: normalized.

## 3. Bundle layout

```text
exactscope-wearable-sdk-<version>-<target>/
  include/
    exactscope.h
    exactscope_platform.h
    exactscope_wasm.h
    exactscope_wearable_ref.h
    exactscope_wearable_ab.h
    exactscope_wearable_bench.h
  lib/<target>/
    libexactscope_cabi.a
  src/
    exactscope_wearable_ref.c
    exactscope_wearable_ab.c
    exactscope_wearable_bench.c
  spec/
    wearable-edge-profile.json
    wearable-qualification-record.json
    wearable-edge-profile.schema.json
    wearable-qualification-record.schema.json
  docs/
    WEARABLE_REFERENCE_HOST.md
    AB_UPDATE.md
    WEARABLE_EDGE_PROFILE_V0_1.md
    WEARABLE_QUALIFICATION_V0_1.md
    WEARABLE_BENCHMARK_V0_1.md
  licenses/
    LICENSE-MIT
    LICENSE-APACHE
  manifest.json
  SHA256SUMS
```

The C reference sources are intentionally shipped alongside the binary runtime because they are product policy adapters, not duplicate calculation implementations. OEMs may compile them directly, wrap the lower C ABI themselves, or use them as conformance references.

## 4. Runtime artifact

`libexactscope_cabi.a` is a Rust `no_std` static library built with:

```text
dynamic-packs
standalone-staticlib
```

It still contains the fused reference registry, so the same binary can be used in:

```text
native-fused-discovery
native-dynamic-exact
```

The bundle MUST state both modes in `manifest.json`.

### 4.1 Mandatory host fatal hook

A standalone static library requires the host to provide:

```c
void XS_CALL xs_platform_panic_abort(void) XS_NOEXCEPT;
```

This hook MUST NOT return.

It is **not** an ordinary error callback. Valid model/user input failures are returned through `xs_status`. Reaching the fatal hook indicates an internal panic, unsupported foreign unwind through a Rust frame, memory/ABI invariant violation, or equivalent product defect.

A shipping integration SHOULD map this hook to the product's process/component termination or watchdog recovery policy rather than rebooting the entire device unless the product safety architecture requires a device reset.

## 5. `manifest.json`

The manifest format identifier is:

```text
exactscope.wearable-sdk-manifest / 0.1
```

Required high-level fields:

```text
project_version
target
source_commit
toolchain
support
qualification
runtime
contracts
files
claim
```

The v0.1 packager MUST emit:

```json
{
  "support": "experimental",
  "qualification": "contract-only"
}
```

It MUST NOT emit `tier1`, `qualified`, or any equivalent real-device support claim merely because cross-compilation succeeded.

### 5.1 Runtime record

The runtime record contains:

```text
artifact_kind = static-library
path
size_bytes
sha256
required_host_symbol = xs_platform_panic_abort
```

### 5.2 Contract record

The contract record contains at least:

```text
core_abi = 1.0
wearable_profile = wearable-edge-v0.1
wearable_profile_sha256
pack_mount_arena_bytes = 0
execution_modes
```

### 5.3 File records

Every payload file present before `manifest.json`/`SHA256SUMS` generation receives:

```text
path
size_bytes
sha256
```

The verifier recalculates these values from archive bytes.

## 6. `SHA256SUMS`

`SHA256SUMS` includes every regular file except itself, including `manifest.json`.

Format:

```text
<64 lowercase hex chars><two spaces><relative path>
```

The verifier rejects:

- duplicate paths;
- malformed digests;
- path traversal;
- paths missing from the archive;
- archive files omitted from `SHA256SUMS`;
- digest mismatches.

## 7. Archive safety requirements

The verifier MUST reject:

- absolute paths;
- `..` traversal;
- multiple top-level roots;
- symlinks, hardlinks, devices, FIFOs, or other non-regular/non-directory members;
- non-normalized UID/GID/mtime;
- duplicate regular-file paths;
- missing manifest/checksum files;
- a target outside the v0.1 allowlist;
- runtime digest drift;
- disappearance of the mandatory panic hook contract;
- an archive that upgrades itself beyond `experimental / contract-only` without a separate qualification process.

Extraction is not required for verification; the reference verifier operates directly on archive members.

## 8. Android arm64 integration

The initial Android artifact is a static library for:

```text
aarch64-linux-android
```

An Android product team is expected to use the NDK/CMake or equivalent native build system to link:

```text
libexactscope_cabi.a
exactscope_wearable_ref.c
```

and, if used by the product:

```text
exactscope_wearable_ab.c
exactscope_wearable_bench.c
```

The host supplies `xs_platform_panic_abort`.

No Android permission, Java service, Binder service, Play Services dependency, network permission, or background worker is required by ExactScope itself.

A future AAR/Prefab wrapper is convenience packaging only; it MUST delegate to this same C ABI and MUST NOT become a second evaluator.

## 9. Embedded Linux arm64 integration

The initial Linux artifact is:

```text
aarch64-unknown-linux-musl
```

It is intended for a small native process/component with explicit caller-owned memory.

The reference runtime owns no:

```text
heap
thread
socket
file descriptor
timer
background loop
network client
```

The product may provide those facilities around ExactScope, but the calculation boundary stays synchronous and bounded.

## 10. What cross-build evidence proves

A green cross-build and verified SDK archive proves only:

1. the Rust code compiles for the target triple;
2. a static library artifact was emitted;
3. the expected public integration material was bundled;
4. the archive and manifest are deterministic/integrity-checked;
5. on the native CI host, the same static-library form linked to C99 code and executed the canonical `econ.ped.mid` flow.

It does **not** prove:

- the target device boots the library;
- the final linker/loader policy is correct on an OEM image;
- latency or energy targets pass;
- radio-off behavior passes on hardware;
- final artifact size after OEM link passes;
- thermal behavior passes;
- PMIC energy passes;
- update power-loss behavior passes on the product's real flash/filesystem;
- a proprietary wearable SDK/API is compatible.

Those claims require `WEARABLE_QUALIFICATION_V0_1.md` evidence on the actual shipping-equivalent target.

## 11. OEM handoff acceptance

Before handing a bundle to another device team, release engineering SHALL verify:

```text
python tools/package_wearable_sdk.py --verify <archive> --target <target>
```

and record the outer archive SHA-256.

The receiving team SHALL verify the same archive before using it.

The receiving team SHOULD archive together:

- SDK tarball;
- tarball SHA-256;
- source commit;
- CI run identifier;
- target-device qualification record once available.

## 12. Qualification promotion

The SDK packager itself never promotes support.

Promotion from:

```text
experimental / contract-only
```

to a product support tier requires a separate release process that consumes a valid wearable qualification record and target-device evidence. Packaging and qualification are intentionally separated so a successful compiler invocation cannot accidentally become a hardware support claim.
