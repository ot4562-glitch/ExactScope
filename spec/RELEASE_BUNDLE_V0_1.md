# ExactScope release-shaped integration bundle v0.1

Status: experimental packaging contract. A v0.1 archive is not, by itself, evidence of target qualification or stable support.

## Purpose

ExactScope should be consumable without forcing an integrator to understand the Rust workspace. The release bundle wraps one immutable capability identity together with exactly one deployable runtime artifact and the integration files needed for that profile.

Packaging stays off-target. It may spend host storage and validation code to keep the deployed ExactScope runtime small.

## Profiles

### `native-static`

The native profile requires:

- an **unbound** capability bundle with explicit model-surface negotiation;
- `runtime_surface.specialization = host-limited`;
- `device_budget.target_profile = native-static`;
- a canonical ExactScope static library (`libexactscope_cabi.a` or `exactscope_cabi.lib`).

The capability must not contain `runtime.wasm` and must not carry a non-null `artifact_sha256`. This prevents a Wasm artifact identity from being silently reused for a native library. The outer release manifest binds the native static-library digest instead.

The archive also carries the public C headers and CMake package metadata.

### `no-import-wasm`

The Wasm profile requires an already artifact-bound capability bundle with:

- `runtime.wasm` whose SHA-256 matches the capability profile and capability manifest;
- `device_budget.target_profile = no-import-wasm`;
- zero imports;
- declared memory within the profile budget;
- required ExactScope exports;
- static byte/import/memory measurements matching the bound capability manifest.

The packager parses the Wasm file but does not instantiate or execute it.

## Archive shape

Each archive has one root directory and contains:

```text
capability/                 immutable capability bundle
include/                    profile-relevant public headers
lib/...                     native runtime/CMake files when native
LICENSE-MIT
LICENSE-APACHE
THIRD_PARTY_NOTICES.md
manifest.json               canonical release manifest
SHA256SUMS                  digest of every payload plus manifest.json
```

`manifest.json` uses format `exactscope.release.bundle`, version `0.1`, and records:

- release version;
- profile and exact target string;
- source commit and toolchain identity;
- capability profile id/revision/domain and exact ABI revision;
- nested capability bundle digest;
- model-surface contract digest and negotiation mode;
- exact runtime path, byte size, and SHA-256;
- optional `build-inputs.json` digest/source identity when current-source reproducibility metadata is supplied;
- SHA-256 for every packaged payload.

`--build-inputs <build-inputs.json>` is optional. When present, the packager verifies it against the current source tree and exact capability/profile/target before copying it into the archive. Archive verification later checks the embedded document structurally and against the nested capability without requiring the verifier to possess the original source checkout. This metadata proves input identity only; it is not independent reproducible-build evidence.

The v0.1 schema is `spec/schemas/release-bundle.schema.json`.

## Build and verify

```text
python3 tools/package_release_bundle.py build-native \
  --capability <unbound-capability-dir> \
  --library <libexactscope_cabi.a-or-exactscope_cabi.lib> \
  --target <exact-target> \
  --source-commit <40-hex-commit> \
  --toolchain <toolchain-id> \
  --output-dir <dir>

python3 tools/package_release_bundle.py build-wasm \
  --capability <artifact-bound-capability-dir> \
  --target wasm32v1-none \
  --source-commit <40-hex-commit> \
  --toolchain <toolchain-id> \
  --output-dir <dir>

python3 tools/package_release_bundle.py verify <archive.tar.gz>
```

Archive generation is deterministic for identical inputs. If an archive with the same output identity already exists with different bytes, packaging fails closed instead of overwriting it.

## Verification boundary

`verify` rejects:

- unsafe/overlong archive paths, symlinks, hardlinks, duplicate members, non-file/non-directory members, excessive member count, or excessive uncompressed/member size;
- multiple archive roots or a root name that disagrees with the manifest identity;
- manifest/schema drift;
- missing, extra, digest-mismatched, or profile-inappropriate outer files;
- broken nested capability identity or contradictions between nested profile/task-map/catalog/model assets/measurements/bindings;
- model-surface identity or negotiation drift;
- runtime digest/size drift;
- a native package carrying a bound Wasm capability;
- a Wasm package whose static artifact properties disagree with its declared capability budget/measurements;
- any bundle claiming support other than `experimental` or qualification other than `unqualified` in this packaging revision.

The v0.1 static verifier also caps an archive at 512 members, 512 UTF-8 bytes per member path, 64 MiB per regular-file member, and 128 MiB total uncompressed regular-file payload. These are intentionally generous for a tiny runtime while bounding workstation-side parsing/extraction work.

Promotion to stable native/Wasm support remains governed by `docs/COMPATIBILITY.md` and requires the separate evidence/qualification gates. Packaging implementation is not qualification evidence.
