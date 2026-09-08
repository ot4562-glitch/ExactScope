# ExactScope v1 installation and embedding

ExactScope v1 is installed as a component of an existing AI application. The stable public grounding package is currently scoped to **Linux x86-64 native C ABI software integration**.

It does not require a daemon, account, hosted API, model replacement, or Python runtime on the deployed target. Provider data can be fully local. A host may also adapt application/network retrieval behind the same Grounding Contract when its privacy and authority policy permits it.

Physical ARM64/wearable RAM, latency, energy, and thermal qualification has not been performed. ARM64 remains an experimental design/build target rather than a stable v1 hardware-performance claim.

## 1. Stable package

Download from GitHub Releases:

```text
exactscope-grounding-1.0.0-x86_64-unknown-linux-gnu.tar.gz
SHA256SUMS
release-manifest.json
```

Verify the release-level checksum before extracting. The archive then has its own `manifest.json` and `SHA256SUMS` covering the internal payload.

The canonical archive layout is:

```text
exactscope-grounding-1.0.0-x86_64-unknown-linux-gnu/
  include/
    exactscope.h
    exactscope_platform.h
  lib/
    x86_64-unknown-linux-gnu/
      libexactscope_cabi.a
    cmake/ExactScope/
      ExactScopeConfig.cmake
  examples/c/
    grounding.c
  examples/grounding/sample-docs/
    device-state.md
    service-policy.md
  grounding/
    sample-index-v1.xsgi
  README.md
  LICENSE-MIT
  LICENSE-APACHE
  THIRD_PARTY_NOTICES.md
  manifest.json
  SHA256SUMS
```

The sample provider is explicitly **demonstration-only**. ExactScope does not pretend a benchmark corpus is a universal product knowledge base.

## 2. Compile the package-local example

From the extracted archive root:

```bash
cc -std=c11 -O2 -Wall -Wextra -Werror -pedantic \
  -Iinclude \
  examples/c/grounding.c \
  lib/x86_64-unknown-linux-gnu/libexactscope_cabi.a \
  -o grounding-demo

./grounding-demo grounding/sample-index-v1.xsgi warranty period
./grounding-demo grounding/sample-index-v1.xsgi battery level
```

The static runtime uses a host-supplied `xs_platform_panic_abort` boundary. The bundled example provides the required symbol.

Expected demo evidence contains `24 months` and `73 percent` respectively.

## 3. Native grounding lifecycle

The native product core binds a parity-frozen `.xsgi` provider index through `exactscope.h`:

```text
host loads .xsgi bytes
  -> xs_grounding_index_size()
  -> xs_grounding_index_align()
  -> caller allocates aligned opaque-handle storage
  -> xs_grounding_index_init()
  -> caller allocates one search scratch cell per indexed document
  -> host supplies normalized query tokens
  -> xs_grounding_index_search()
  -> xs_grounding_index_project()
```

The `.xsgi` backing bytes must stay readable and immutable for the bound handle lifetime.

The native core deliberately does **not**:

- tokenize arbitrary user text;
- assign authoritative vs supplemental semantics;
- decide application/user/security scope;
- open files itself;
- allocate the corpus;
- start an inference server;
- call a model;
- make network requests.

Those responsibilities stay with the host and the Grounding Contract.

## 4. Provider installation

Real provider data is deployment-specific. For the local text provider, compile `.txt`/`.md` documents off-target:

```bash
python3 tools/grounding_corpus.py build \
  --input-dir ./my-docs \
  --output ./my-corpus.json

python3 tools/grounding_corpus.py compile-binary \
  --index ./my-corpus.json \
  --output ./my-corpus.xsgi
```

The compiler/reference path uses Python; the deployed native runtime does not.

The same logical Grounding Contract can also sit in front of other provider implementations such as application state, exact/alias lookup, frozen semantic indexes, or captured host/search results. The v1 native XSGI runtime is the qualified first reference retrieval/projection core, not a claim that every provider must use the same storage format.

### Provider footprint accounting

Default product-package size and provider-data size are separate quantities.

The default v1 archive is about 0.94 MB compressed and about 4.66 MB unpacked. The NQ development-mirror `.xsgi` used in qualification is about 19.71 MB and is **not included in the default install**.

If a deployment chooses a provider of that size, count it in that deployment's footprint. Qualification datasets should not be hidden inside a generic runtime-size claim.

## 5. Grounding Contract integration

Retrieval alone is not the whole product behavior. The host should bind:

```text
application/security scope
  -> target/source plan
  -> provider identity
  -> authoritative vs supplemental policy
  -> coverage requirements
  -> freshness/revision policy
  -> ambiguity/conflict policy
  -> evidence byte/token budget
  -> deterministic GroundingFrame
```

For authoritative data:

- `grounded` means policy-approved evidence established the target;
- `none` means required coverage completed and found no usable evidence;
- timeout/error/denied/incomplete coverage becomes `unavailable`, not `none`;
- unresolved candidates stay `ambiguous`;
- unresolved contradictions stay `conflict`;
- unresolved authoritative state must not silently fall back to model memory.

Supplemental data has different fallback semantics: a supplemental miss does not mean a fact is false or unknowable.

See [`GROUNDING_ARCHITECTURE.md`](GROUNDING_ARCHITECTURE.md) and [`../spec/GROUNDING_CONTRACT_V0_1.md`](../spec/GROUNDING_CONTRACT_V0_1.md).

## 6. Model integration

ExactScope does not own your inference engine.

A typical product flow is:

```text
question
  -> ExactScope provider/policy path
  -> host can finish authoritative unresolved/scalar case? 0 model calls
  -> otherwise compact evidence projection
  -> existing local model, one answer-generation call
```

### llama.cpp reference adapter

The maintained reference adapter is:

```text
adapters/llama-cpp/grounding_v1.py
```

It connects only to an already-running loopback OpenAI-compatible llama.cpp endpoint. It does not start another daemon or send the user's request to a remote model service.

Its calibration record is bound to the exact model identity, grounding policy, and selected model-facing answer contract. Normal questions do not recalibrate.

See [`../adapters/llama-cpp/README.md`](../adapters/llama-cpp/README.md) and [`AI_INTEGRATION.md`](AI_INTEGRATION.md).

## 7. Build the stable package from source

Build the standalone native static runtime:

```bash
cargo build -p exactscope-cabi --release --features standalone-staticlib
```

Build the tiny demonstration index:

```bash
python3 tools/grounding_corpus.py build \
  --input-dir examples/grounding/sample-docs \
  --output target/sample-corpus.json

python3 tools/grounding_corpus.py compile-binary \
  --index target/sample-corpus.json \
  --output target/sample-index-v1.xsgi
```

Build the deterministic package:

```bash
python3 tools/package_grounding_runtime.py build \
  --library target/release/libexactscope_cabi.a \
  --sample-index target/sample-index-v1.xsgi \
  --target x86_64-unknown-linux-gnu \
  --source-commit <40-hex-commit> \
  --toolchain <toolchain-id> \
  --output-dir dist
```

Verify it structurally and in a clean-room C consumer:

```bash
python3 tools/package_grounding_runtime.py verify \
  dist/exactscope-grounding-1.0.0-x86_64-unknown-linux-gnu.tar.gz

python3 tools/test_grounding_runtime_bundle.py \
  dist/exactscope-grounding-1.0.0-x86_64-unknown-linux-gnu.tar.gz
```

The clean-room test extracts the final archive and uses only the package's own public headers, static library, example, and demonstration XSGI.

The normative packaging contract is [`../spec/GROUNDING_RUNTIME_BUNDLE_V1.md`](../spec/GROUNDING_RUNTIME_BUNDLE_V1.md).

## 8. Footprint and target boundary

The v1 packager fails closed when the default package exceeds:

- 10,000,000 compressed bytes;
- 20,000,000 unpacked regular-file bytes.

Current Linux x86-64 stable-build measurements are approximately:

- compressed SDK: **0.94 MB**;
- unpacked package files: **4.66 MB**;
- static library: **4.62 MB**;
- demonstration XSGI: **1.6 KB**.

The measured NQ x86-64 clean-room process reached about 21.8 MiB max RSS, but that is a whole-process measurement rather than isolated ExactScope incremental memory excluding a base model.

Physical ARM64 metrics remain unmeasured. Do not convert x86-64 software measurements into smartwatch/smart-glasses battery, thermal, latency, or RAM claims.

## 9. Fail-closed installation rules

Do not weaken the runtime/evidence boundary during integration:

- do not mutate or replace bound `.xsgi` bytes underneath a live index handle;
- do not treat provider errors as true no-hit;
- do not let evidence text grant itself authority;
- do not widen user/private/tenant scope from retrieved content;
- do not silently choose between conflicting authoritative records;
- do not repair a typed runtime failure into a plausible answer;
- do not expose benchmark/gold data to a serving provider during evaluation.

## 10. Secondary/historical components

The repository retains the earlier `xs_calc` / `xs_eval` deterministic quantitative subsystem and rc3 evaluation SDK/package tooling. Those remain useful secondary capabilities and historical evidence, but they do not define the flagship v1 grounding installation path.

Likewise, earlier ARM64 build/package checks do not substitute for physical v1 ARM64 grounding qualification.
