# ExactScope v1 quickstart

ExactScope v1 is a lightweight native grounding runtime and accuracy retrofit layer for small, local, and on-device AI. The stable public software scope is the **Linux x86-64 native C ABI grounding package**. It does not require a model replacement, fine-tuning, an agent loop, a network service, or Python on the deployed target.

ARM64/wearable hardware remains an important design target, but physical ARM64 RAM, latency, energy, and thermal qualification has not been performed. Do not inherit x86-64 measurements as wearable claims.

## 1. Download the stable grounding package

From the GitHub release page, download:

```text
exactscope-grounding-1.0.0-x86_64-unknown-linux-gnu.tar.gz
SHA256SUMS
release-manifest.json
```

Verify the outer SHA-256 before extraction, then inspect the archive's own `manifest.json` and `SHA256SUMS`.

The default archive intentionally contains no universal knowledge base and no large benchmark corpus. It ships a tiny demonstration-only provider so the integration path can be exercised immediately.

## 2. Compile the native C11 demo

From the extracted archive root:

```bash
cc -std=c11 -O2 -Wall -Wextra -Werror -pedantic \
  -Iinclude \
  examples/c/grounding.c \
  lib/x86_64-unknown-linux-gnu/libexactscope_cabi.a \
  -o grounding-demo
```

The standalone static profile requires the host `xs_platform_panic_abort` symbol; the bundled example supplies it.

## 3. Query the demonstration provider

```bash
./grounding-demo grounding/sample-index-v1.xsgi warranty period
./grounding-demo grounding/sample-index-v1.xsgi battery level
```

Expected evidence includes:

```text
The demo warranty period is 24 months.
The demo device battery level is 73 percent.
```

This proves the extracted public C ABI + static library + immutable XSGI path. It is not a benchmark and the tiny demo provider is not intended for real-world knowledge coverage.

## 4. Build deployment-specific provider data

The compiler lives in the source repository and is off-target tooling:

```bash
python3 tools/grounding_corpus.py build \
  --input-dir ./my-docs \
  --output ./my-corpus.json

python3 tools/grounding_corpus.py compile-binary \
  --index ./my-corpus.json \
  --output ./my-corpus.xsgi
```

The current compiler accepts deterministic `.txt`/`.md` corpus inputs. The native runtime binds the resulting immutable `.xsgi` bytes, validates their structure/CRC, performs bounded deterministic retrieval, and produces compact evidence projection.

Provider data is deployment-specific. Count its size in the footprint of the deployment that actually uses it; do not pretend the benchmark NQ index is part of the generic runtime install.

## 5. Integrate the C ABI

The normal native lifecycle is:

```text
load immutable .xsgi bytes
  -> xs_grounding_index_size / xs_grounding_index_align
  -> caller allocates aligned opaque handle storage
  -> xs_grounding_index_init
  -> caller allocates one scratch cell per document
  -> normalize/tokenize query under compiler-compatible contract
  -> xs_grounding_index_search
  -> xs_grounding_index_project
  -> host applies authority / policy / answer disposition
  -> model only when generation is still necessary
```

Important ownership rules:

- the `.xsgi` backing bytes remain readable and immutable for the index-handle lifetime;
- query tokens passed to the C ABI are already normalized/tokenized;
- search scratch and hit/projection output are caller-owned;
- the native search/projection core does not assign application authority;
- the native core does not open files, make network requests, or invoke a model.

See [`../include/exactscope.h`](../include/exactscope.h) and [`INSTALLATION.md`](INSTALLATION.md).

## 6. Add Grounding Contract semantics

The native runtime is the deterministic retrieval/projection core. Product behavior also needs the Grounding Contract around it:

```text
original user question
  -> application/security scope
  -> bounded retrieval provider(s)
  -> ProviderOutcome(s)
  -> evidence policy
       authority
       coverage
       freshness/revision
       ambiguity
       conflict
       budget
  -> GroundingFrame
  -> authoritative unresolved? host disposition, 0 model calls
  -> canonical scalar? host value, 0 model calls
  -> otherwise compact projection + at most one answer-generation call
```

Authoritative `none` means required source coverage completed and found no usable evidence. Timeout/error/denied/incomplete coverage is `unavailable`, not `none`. Unresolved contradictions remain `conflict` and unresolved candidates remain `ambiguous`.

See [`GROUNDING_ARCHITECTURE.md`](GROUNDING_ARCHITECTURE.md) and [`../spec/GROUNDING_CONTRACT_V0_1.md`](../spec/GROUNDING_CONTRACT_V0_1.md).

## 7. llama.cpp integration

ExactScope does not own the inference engine. A local llama.cpp deployment can remain the answer-generation runtime.

The maintained reference adapter is:

```text
adapters/llama-cpp/grounding_v1.py
```

It connects only to an already-running loopback OpenAI-compatible llama.cpp endpoint. Its calibrated path can complete authoritative unresolved or single canonical-scalar cases in the host and use at most one model answer call for the remaining cases.

See [`../adapters/llama-cpp/README.md`](../adapters/llama-cpp/README.md) and [`AI_INTEGRATION.md`](AI_INTEGRATION.md).

## 8. Reproduce the release package from source

```bash
cargo build -p exactscope-cabi --release --features standalone-staticlib

python3 tools/grounding_corpus.py build \
  --input-dir examples/grounding/sample-docs \
  --output target/sample-corpus.json

python3 tools/grounding_corpus.py compile-binary \
  --index target/sample-corpus.json \
  --output target/sample-index-v1.xsgi

python3 tools/package_grounding_runtime.py build \
  --library target/release/libexactscope_cabi.a \
  --sample-index target/sample-index-v1.xsgi \
  --target x86_64-unknown-linux-gnu \
  --source-commit <40-hex-commit> \
  --toolchain <toolchain-id> \
  --output-dir dist
```

Then verify and clean-room test the final archive:

```bash
python3 tools/package_grounding_runtime.py verify \
  dist/exactscope-grounding-1.0.0-x86_64-unknown-linux-gnu.tar.gz

python3 tools/test_grounding_runtime_bundle.py \
  dist/exactscope-grounding-1.0.0-x86_64-unknown-linux-gnu.tar.gz
```

The clean-room test extracts the final archive and recompiles/runs the C11 demo using only files from that extracted package.

## 9. Secondary quantitative subsystem

The repository still contains the earlier deterministic `xs_calc` / `xs_eval` capability subsystem and the historical rc3 evaluation SDK machinery. Those are retained capabilities and evidence, not the flagship v1 grounding product boundary.

Do not transfer old rc3 model scores or ARM64 package checks into v1 grounding claims. New claims stay bound to the exact runtime/provider/model/device evidence that produced them.
