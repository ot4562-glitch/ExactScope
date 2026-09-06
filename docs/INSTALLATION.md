# Installation and embedding profiles

Release target: **rc4 grounding candidate source `125ad9403f22eece7f552701d4c7376bba3b697f` is READY_FOR_GROUNDING_BENCHMARK after Linux/Windows clean-room package and five-model preregistration verification; v1.0.0-rc.3 remains the latest frozen public prerelease artifact and is primarily the quantitative SDK**

> rc4 grounding change: the common everyday path is original-question prefetch into a compact Grounding Frame. Retrieval providers are replaceable behind one contract, and native model tool calls are not required. The first exact/lexical reference profile and grounding evaluation-package format are implemented for benchmark qualification, but no rc4 grounding release or accuracy claim is public yet.
Status: **benchmark-ready freeze complete for the candidate above; legacy `xs_recall`/fact-pack prototypes are not the installable product contract; rc4 model efficacy remains unmeasured**

ExactScope is loaded as a component of another AI runtime. The runtime consumer is the AI system; a developer/OEM engineer is the integrator. The planned grounding layer does not require a human-facing tool workflow. A fully local profile need not require a daemon, account or network service; a host may optionally adapt application/network providers under explicit source/privacy policy.

## rc4 grounding installation contract — implemented reference package, provider-neutral behavior

The pre-inference grounding evaluation package binds **behavior**, not merely a search index. A future supported product package must preserve the same principle:

```text
verify source/provider/profile manifests
  -> bind user/application/source scope
  -> bind authoritative vs supplemental policy
  -> bind freshness/revision/conflict/ambiguity policy
  -> bind retrieval provider + index/preprocessing identity
  -> bind evidence top-k/byte/token budget
  -> run provider/policy self-test
  -> prefetch Grounding Frame before existing model answer call
```

A local lexical profile, a frozen embedding/vector profile, and an application-native provider may have different files/dependencies while remaining compatible with the same logical Grounding Contract. Therefore the final package format must not assume every provider is a single ExactScope fact-pack file or that every provider executes inside the no-import Wasm core.

The target host must keep private/user/tenant scope outside unauthorized providers and must record `unavailable` separately from a true no-hit.

For the rc4 grounding evaluation package, Python entrypoints must not write interpreter cache files into the extracted package. The package verifier intentionally rejects unmanifested extra files, so packaged commands disable bytecode-cache writes and the payload remains re-verifiable after first use on Linux and Windows.

## 1. Prefer a published rc3 release asset for quantitative evaluation

For external evaluation of the current public quantitative runtime, use the immutable GitHub release rather than a developer checkout.

Expected rc3 asset shapes:

| Platform | Archive | Role |
|---|---|---|
| Windows x86-64 | `exactscope-eval-1.0.0-rc.3-x86_64-pc-windows-msvc.tar.gz` | model/local-AI evaluation SDK |
| Linux x86-64 | `exactscope-eval-1.0.0-rc.3-x86_64-unknown-linux-gnu.tar.gz` | model/local-AI evaluation SDK |
| Android ARM64 | `exactscope-wearable-sdk-1.0.0-rc.3-aarch64-linux-android.tar.gz` | Android/edge static OEM SDK |
| Linux ARM64 musl | `exactscope-wearable-sdk-1.0.0-rc.3-aarch64-unknown-linux-musl.tar.gz` | embedded Linux/wearable static OEM SDK |

Only claim a platform asset that actually appears on the release page.

For every archive:

1. download `SHA256SUMS` and `release-manifest.json`;
2. verify the outer SHA-256 before extraction;
3. extract into an application-owned directory;
4. inspect the archive's own manifest/checksums when present;
5. run the bundled smoke/integration path;
6. bind only the selected model-facing surface.

See [QUICKSTART.md](QUICKSTART.md).

## 2. Evaluation SDK layout

The x86-64 evaluation archive is intended to make model integration possible without building Rust first. Its logical contents include:

```text
exactscope-eval-1.0.0-rc.3-<target>/
  bin/
    exactscope-core[.exe]
  lib/<target>/
    libexactscope_cabi.a | exactscope_cabi.lib
  wasm/
    exactscope.wasm
  include/
    exactscope.h
    exactscope_platform.h
    exactscope_wasm.h
  lib/cmake/ExactScope/
    ExactScopeConfig.cmake
  adapters/generated/quant-core-16/
    catalog.json
    binding-sha256.txt
    xs-*.tool.json
    xs-*.gbnf
    prompt-fragment.txt
  capabilities/
    quant-core-16-semantic-ai/
      profile.json
      surface-contract.json
      runtime.wasm
      manifest.json
      bundle-sha256.txt
      ...exact model-facing assets...
    quant-core-16-combined-ai/
      ...same identity-bound surface plus xs_calc...
  examples/capability-host.mjs
  benchmarks/capability_surface.py
  benchmarks/run_qualification.py
  tools/
  docs/
  licenses/
  manifest.json
  SHA256SUMS
```

The exact inventory is authoritative in `manifest.json`; this document describes the integration shape, not a substitute manifest.

The deterministic native/Wasm component itself does not require Python. The packaged qualification runner is Python-stdlib-only; only model downloading needs `requirements-benchmark.txt`. On Linux distributions that enforce PEP 668, do **not** force a system-wide pip install. Use a virtual environment:

```sh
python3 -m venv .exactscope-venv
. .exactscope-venv/bin/activate
python -m pip install -r requirements-benchmark.txt
python tools/fetch_benchmark_models.py --list
```

On Windows, `py -3 -m pip install -r requirements-benchmark.txt` remains a normal per-user/dev setup where Python is configured accordingly.

## 3. Native C ABI

Public header:

```text
include/exactscope.h
```

The preferred deployment is an application/firmware-bundled static library with caller-owned bounded storage. A Unix-style integration can link directly:

```sh
cc -std=c11 -Wall -Wextra -Werror -pedantic \
  -Iinclude examples/xs_calc.c \
  lib/<target>/libexactscope_cabi.a \
  -o xs-calc
```

Windows MSVC consumers link `exactscope_cabi.lib` from the matching evaluation SDK.

CMake packaging uses the target:

```cmake
find_package(ExactScope CONFIG REQUIRED)
target_link_libraries(my_product PRIVATE ExactScope::exactscope)
```

The target application does not need Rust, Python, Node.js, Java, a system service, cloud account, or network access merely to execute the bundled deterministic library.

## 4. No-import WebAssembly

The evaluation SDK also includes a local no-import Wasm path.

Host responsibilities:

1. verify the release/archive/model-surface identity;
2. instantiate with the exact expected import policy;
3. validate ABI/version/required exports;
4. use bounded caller regions as documented by the Wasm ABI;
5. run a canonical smoke vector;
6. expose only the selected `xs_calc`/`xs_eval` surface to the model.

A selected capability build should remove excluded serving paths rather than relying only on prompt instructions to hide them.

In a source checkout the strict host is `examples/javascript/capability-host.mjs`; in the published evaluation SDK the copy-paste path is `examples/capability-host.mjs`. Use the packaged `capabilities/quant-core-16-*-ai/` directories directly rather than reconstructing them from raw hot-set assets.

## 5. ARM64 OEM SDKs

The rc3 release workflow packages two static OEM profiles:

- `aarch64-linux-android`;
- `aarch64-unknown-linux-musl`.

The wearable/edge SDK package is designed to contain the native static library, public headers, CMake metadata, reference host/update helpers, qualification contracts, license material, manifest, and checksums.

These are **prerelease qualification assets**, not a claim that every Android, wearable, smart-glasses, or embedded product is supported. Compatibility depends on the actual integration boundary, ABI, toolchain, runtime, and device evidence.

### Android

rc3 publishes a native ARM64 static SDK, not a universal AAR/Prefab guarantee. A product team may wrap the C ABI in JNI/Kotlin or another host layer, but that wrapper may transport values/statuses only; it must not implement a second calculator, semantic repair, or error repair.

A future AAR/Prefab convenience package can be built around the same evidence-bound C ABI once the target/product integration warrants it.

### Embedded Linux / wearable

The musl ARM64 SDK is intended for application/firmware integration where the product owns a native executable boundary. Qualification must still measure the real target's RSS/heap/stack/latency/energy characteristics separately.

## 6. Capability-slice installation

Deploy the smallest slice that covers the target task families.

Preferred serving path:

```text
short arithmetic      -> xs_calc
known reviewed method -> xs_eval
unknown method        -> optional xs_find cold/development path
```

A capability/model-surface identity can bind:

- exact operation keys/revisions;
- argument names/order/shapes;
- selected tool JSON;
- selected GBNF;
- one compact prompt fragment;
- profile/hot-set/runtime digests;
- model-surface contract identity;
- footprint/conformance metadata.

Do not expose the whole domain source catalog to a weak model by default. Any digest/revision/profile mismatch invalidates a cached binding and should fail closed.

See [AI_INTEGRATION.md](AI_INTEGRATION.md).

## 7. Dynamic packs

Dynamic `.xsp` loading remains an optional architecture when a host genuinely needs capability updates independent of the runtime artifact.

The host owns:

- acquisition/storage;
- authenticity/signature policy;
- immutable pack lifetime;
- registry lifecycle;
- update/rollback.

ExactScope validates pack structure/semantics/limits/collisions but does not download packs itself.

A fixed product may omit dynamic loading and discovery entirely.

## 8. Build from source

Use source builds for development, not as a substitute for an immutable release when collecting release qualification evidence.

Basic source checks:

```powershell
cargo check --workspace --all-targets
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace --lib
```

Generic fused Wasm development build:

```powershell
cargo build --locked --release -p exactscope-wasm --target wasm32v1-none --no-default-features --features fused,tinyjson
python tools/inspect_wasm.py target/wasm32v1-none/release/exactscope_wasm.wasm
```

Source build success does not establish model accuracy or target support.

## 9. Generic release-shaped packaging tooling

The repository also contains deterministic package constructors used for explicit capability/runtime identities:

```text
python tools/package_release_bundle.py build-native ...
python tools/package_release_bundle.py build-wasm ...
python tools/package_release_bundle.py verify <archive.tar.gz>
```

The contract is in `spec/RELEASE_BUNDLE_V0_1.md`. Those formats remain evidence/qualification scoped unless a future support policy explicitly promotes them.

The user-facing rc3 GitHub release is produced by `.github/workflows/release-rc.yml` using the evaluation/OEM SDK packagers.

## 10. Updates and rollback

A product should stage a complete new component set, verify identity/integrity, run its smoke/conformance gate, and only then atomically switch the binding. When a product already has durable A/B slots, ExactScope should use that product-owned update mechanism rather than create a privileged background updater.

A partial or interrupted replacement must not leave the runtime/model-surface identities silently mismatched.

## 11. Closed devices

ExactScope can be integrated only where the product legitimately exposes a compute boundary, such as:

- application/firmware-bundled native library;
- product-owned plugin/extension;
- embedded Wasm runtime;
- host extension API;
- paired local compute host controlled by the product stack.

A completely closed device without such an integration boundary cannot be independently retrofitted by ExactScope. Do not advertise generic “wearable” or “smart-glasses” support without naming the real product boundary and evidence.

## 12. Qualification rule

Installation success means only that the component can be loaded by that host. It is not production qualification.

Before a stable/support claim, record the exact published artifact identity and measure the intended target as specified in [QUALIFICATION_HANDOFF.md](QUALIFICATION_HANDOFF.md), including model correctness/failure decomposition and representative target memory/latency/energy behavior where relevant.

Historical r20 model evidence belongs to an older runtime and is not rc3 evidence.
