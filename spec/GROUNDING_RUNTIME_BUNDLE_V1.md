# ExactScope grounding runtime bundle v1

Status: stable packaging contract for the v1 family Linux x86-64 grounding SDK. **v1.1 is currently a candidate and is not released.** It keeps the native C runtime boundary and adds an optional standard-library Python runtime-amplifier integration around host-owned llama.cpp. This contract defines software packaging and clean-room integration scope; it is not a hardware certification claim.

## Product boundary

The v1.1 candidate package contains the provider-neutral native grounding runtime, a tiny demonstration provider, and the optional prepared runtime-amplifier integration around host-owned llama.cpp. The host path validates profile/corpus artifacts once, binds an immutable `CorpusSnapshot`, compiles stable typed answer/evidence/prompt configuration into `PreparedAmplifier`, then performs repeated request planning without profile/corpus artifact I/O or contract/prefix recompilation. The same path provides explicit retrieval-query separation and one shipping local-corpus projector, `precision-context-v5`: bounded lexical candidates are overfetched before the final model-item cap, byte-identical body mirrors collapse unless distinct titles add query-relevant identity, exact repeated spans are suppressed, the lexical anchor keeps the nearest complete directional context when it fits, a complete anchor-only span is preferred to truncation, and 512/1024-byte tiers promote only when necessary under the unchanged 2048-byte cap. It also provides typed zero-call scalar completion, identity-bound capability reuse, stable parity-gated prefix-cache identity, and fixed preflight output-surface negotiation. It does **not** bundle a general knowledge corpus, model weights, an inference engine, a second verifier model, a retry/self-reflection loop, a network service, or the large NQ development-mirror qualification index. Python remains optional: it is required only for the bundled host integration/compiler tooling, never by the native C runtime itself.

Evidence is required for grounded answers, but evidence data is deployment-specific. Application/device/manual/search providers are therefore budgeted with the deployment that actually uses them rather than being hidden inside the generic runtime footprint.

The NQ `.xsgi` used for qualification is separate benchmark data. Its size does not count as the default product install and it must not be described as a generally useful built-in corpus.

## Default archive

The canonical Linux x86-64 archive is:

```text
exactscope-grounding-<version>-x86_64-unknown-linux-gnu.tar.gz
```

It contains one root directory with:

```text
include/exactscope.h
include/exactscope_platform.h
lib/x86_64-unknown-linux-gnu/libexactscope_cabi.a
lib/cmake/ExactScope/ExactScopeConfig.cmake
examples/c/grounding.c
examples/grounding/sample-docs/device-state.md
examples/grounding/sample-docs/service-policy.md
grounding/sample-index-v1.xsgi
grounding/reference-profile-v0.1/*
adapters/llama-cpp/grounding_v1.py
tools/grounding_answer_contract.py
tools/grounding_canonical.py
tools/grounding_corpus.py
tools/grounding_engine.py
tools/grounding_match.py
tools/grounding_projection.py
tools/grounding_runtime.py
tools/grounding_v1_surface.py
README.md
LICENSE-MIT
LICENSE-APACHE
THIRD_PARTY_NOTICES.md
manifest.json
SHA256SUMS
```

`grounding/sample-index-v1.xsgi` is explicitly `demonstration-only`. It exists so an integrator can compile and run the package without obtaining private or benchmark data first.

## Manifest identity

`manifest.json` is canonical JSON with:

- format `exactscope.grounding.runtime.bundle`;
- format version `1.1` for v1.1 packages; the verifier also accepts the frozen v1.0.0 manifest format `1.0` for rollback;
- exact product version and release tier;
- exact native target, source commit, and toolchain identity;
- static runtime path, size, and SHA-256;
- demonstration-provider path, purpose, size, and SHA-256;
- the exact optional host-integration boundary (`grounding_engine.py` + thin `grounding_v1.py` transport, cold-path artifact validation, prepared immutable amplifier with zero request-time artifact I/O, direct literal-loopback HTTP to host-owned llama.cpp with no environment proxy or redirect following, bounded responses, `precision-context-v5` + adaptive evidence tiers, compiled typed answer contracts, identity-bound capability reuse, stable parity-gated prefix-cache identity, fixed v1.1 preflight negotiation, cold-path strict/recomputed calibration records, zero-network `doctor`, no retry/second-model path, native core does not require Python);
- the deployment boundary;
- the public support scope;
- a complete SHA-256 inventory of every payload.

Stable semantic versions declare native status `stable` only for `x86_64-unknown-linux-gnu`. Physical ARM64 qualification is explicitly `not-claimed`, and grounding Wasm is `not-included` in v1.

## Footprint rules

Default-install package hard caps remain:

- compressed archive: **10,000,000 bytes**;
- unpacked regular-file payload: **20,000,000 bytes**.

The packager fails closed above either hard cap. For v1.1.0 it additionally enforces a **1,005,099-byte compressed promotion gate**, equal to +5% over the 957,237-byte v1 stable reference package. Because v1.1 is being redesigned, earlier candidate archive sizes are historical only. A fresh verification package must fit this gate, and the final release measurement must be rebuilt from the real qualifying release commit/toolchain.

Optional provider data is measured separately and must also be included when reporting the footprint of a complete selected deployment. Qualification datasets and reproduction fixtures are reported separately from the default install.

## Build and verify

```bash
python3 tools/package_grounding_runtime.py build \
  --library target/release/libexactscope_cabi.a \
  --sample-index target/sample-index-v1.xsgi \
  --target x86_64-unknown-linux-gnu \
  --source-commit <40-hex-commit> \
  --toolchain <toolchain-id> \
  --output-dir dist

python3 tools/package_grounding_runtime.py verify \
  dist/exactscope-grounding-<version>-x86_64-unknown-linux-gnu.tar.gz

python3 tools/test_grounding_runtime_bundle.py \
  dist/exactscope-grounding-<version>-x86_64-unknown-linux-gnu.tar.gz
```

The clean-room test extracts the final archive, compiles `examples/c/grounding.c` against only the extracted public headers and static library, verifies two known queries against only the extracted demonstration index, executes the bundled llama.cpp adapter in no-inference `plan` mode, and exercises `doctor` against a synthetic valid calibration record to prove zero-network packaged validation.

## Security and integrity

Verification rejects unsafe paths, links, duplicate archive members, unexpected files, digest drift, malformed manifest/checksum inventory, non-static runtime input, invalid demonstration XSGI input, and footprint hard-cap violations.

The runtime itself validates the complete immutable XSGI layout and CRC during `xs_grounding_index_init`. Package-level XSGI magic checking is not a substitute for runtime validation.

## Support boundary

v1 stable support applies to the packaged **Linux x86-64 native grounding software path** and its documented C ABI/clean-room integration contract.

ARM64, smart-glasses, watch, and other wearable targets remain important design targets, but physical ARM64 RAM, latency, energy, and thermal qualification has not been performed and is not inherited from x86-64 measurements. Those target claims remain experimental until measured on representative physical hardware.
