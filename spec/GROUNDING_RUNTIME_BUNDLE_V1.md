# ExactScope grounding runtime bundle v1

Status: stable packaging contract for the v1 Linux x86-64 native grounding SDK. This contract defines software packaging and clean-room integration scope; it is not a hardware certification claim.

## Product boundary

The v1 default package contains the provider-neutral native grounding runtime and a tiny demonstration provider. It does **not** bundle a general knowledge corpus, model weights, an inference engine, a network service, or the large NQ development-mirror qualification index.

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
- format version `1.0`;
- exact product version and release tier;
- exact native target, source commit, and toolchain identity;
- static runtime path, size, and SHA-256;
- demonstration-provider path, purpose, size, and SHA-256;
- the deployment boundary;
- the public support scope;
- a complete SHA-256 inventory of every payload.

Stable semantic versions declare native status `stable` only for `x86_64-unknown-linux-gnu`. Physical ARM64 qualification is explicitly `not-claimed`, and grounding Wasm is `not-included` in v1.

## Footprint rules

Default-install package hard caps remain:

- compressed archive: **10,000,000 bytes**;
- unpacked regular-file payload: **20,000,000 bytes**.

The packager fails closed above either hard cap.

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

The clean-room test extracts the final archive, compiles `examples/c/grounding.c` against only the extracted public headers and static library, and verifies two known queries against only the extracted demonstration index.

## Security and integrity

Verification rejects unsafe paths, links, duplicate archive members, unexpected files, digest drift, malformed manifest/checksum inventory, non-static runtime input, invalid demonstration XSGI input, and footprint hard-cap violations.

The runtime itself validates the complete immutable XSGI layout and CRC during `xs_grounding_index_init`. Package-level XSGI magic checking is not a substitute for runtime validation.

## Support boundary

v1 stable support applies to the packaged **Linux x86-64 native grounding software path** and its documented C ABI/clean-room integration contract.

ARM64, smart-glasses, watch, and other wearable targets remain important design targets, but physical ARM64 RAM, latency, energy, and thermal qualification has not been performed and is not inherited from x86-64 measurements. Those target claims remain experimental until measured on representative physical hardware.
