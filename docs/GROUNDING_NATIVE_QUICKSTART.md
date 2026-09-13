# ExactScope native grounding quickstart

The v1.1.0 release **retains the Linux x86-64 native grounding C ABI/XSGI path as the stable software surface**. The new v1.1 qualification, policy, admission/finalization, drift/requalification, enterprise DocQA, host-integration and demo surfaces are shipped as **experimental/reference** software unless a narrower document says otherwise. A `Qualified Execution Profile` or successful conformance demo establishes the implemented identity/validation relationship; it does not by itself establish enterprise suitability, workload quality, production readiness or economic advantage.

The demo index is intentionally tiny and is **not** a general factual corpus. Real accuracy depends on evidence supplied by your application, device, documents, or retrieval provider.

## 1. Compile the C11 demo

From the extracted archive root on Linux x86-64:

```bash
cc -std=c11 -O2 -Wall -Wextra -Werror -pedantic \
  -Iinclude \
  examples/c/grounding.c \
  lib/x86_64-unknown-linux-gnu/libexactscope_cabi.a \
  -o grounding-demo
```

## 2. Search the demonstration provider

Query tokens passed to the native ABI are already-normalized tokens. For the included English demo:

```bash
./grounding-demo grounding/sample-index-v1.xsgi warranty period
./grounding-demo grounding/sample-index-v1.xsgi battery level
```

Expected evidence includes `24 months` for the warranty query and `73 percent` for the battery query.

The native runtime performs no network request and owns no model inference loop.

## 3. Experimental/reference v1.1 host integrations

The source tree and v1.1 package include a maintained llama.cpp reference adapter and host-attached semantic tooling, but **their presence does not extend the stable C ABI support promise to those Python/control-plane surfaces**. The package manifest labels host integration `experimental-reference` and the qualification architecture `source-reference-only`.

The experimental [`../adapters/bridge/`](../adapters/bridge/) path has backend-specific evidence rather than a blanket compatibility claim: ONNX Runtime GenAI has real local generation plus a grounded ExactScope delivery reaching ORT; ExecuTorch currently has header/contract smoke without a real `.pte` compatibility claim; LiteRT-LM has real fixture Engine/Conversation execution plus the documented context-capacity finding. `Complete` returns without touching model inference; `Generate` carries only approved semantic messages/contracts into the host runtime and returns raw output to ExactScope finalization.

Fail-closed admission/finalization requires a **trusted enforcing host** that reports the current behavior-affecting identities and cannot bypass the guard. Digest binding proves consistency with the supplied identities; it does not prove host truthfulness or customer workload suitability.

Python remains development/reference tooling and is **not** required by the stable native C runtime. See [`V1_1_TECHNICAL_REVIEW.md`](V1_1_TECHNICAL_REVIEW.md), [`V1_1_PUBLIC_PROXY_K8S_RESULT.md`](V1_1_PUBLIC_PROXY_K8S_RESULT.md), and [`V1_1_INTEGRATION_FEEDBACK.md`](V1_1_INTEGRATION_FEEDBACK.md) for the exact evidence and claim boundaries.

## 4. Connect your own evidence

ExactScope does not ship a universal knowledge corpus. Compile deployment-specific `.txt` or `.md` evidence with the off-target compiler from the ExactScope source repository:

```bash
python3 tools/grounding_corpus.py build \
  --input-dir ./my-docs \
  --output ./my-corpus.json

python3 tools/grounding_corpus.py compile-binary \
  --index ./my-corpus.json \
  --output ./my-corpus.xsgi
```

For the native C runtime, Python remains a development/compiler dependency only. The optional bundled llama.cpp reference integration is the only packaged path here that requires Python 3.

For production integrations, normalize query tokens with the same Unicode/tokenization contract as the compiler, keep the `.xsgi` bytes immutable for the lifetime of the bound index, and apply your application authority/security policy before treating retrieved evidence as authoritative.

## What the runtime does

The native path provides:

- zero-copy validation/binding of immutable `.xsgi` provider data;
- deterministic bounded lexical retrieval;
- caller-owned search scratch and output storage;
- deterministic compact evidence projection;
- no mandatory agent loop;
- no mandatory network service;
- no runtime-owned model inference.

ExactScope's higher-level Grounding Contract adds application/provider authority, coverage, ambiguity, conflict, freshness, and failure semantics around this deterministic retrieval/projection core.

See the project README, `spec/GROUNDING_CONTRACT_V0_1.md`, and `docs/GROUNDING_ARCHITECTURE.md` in the source repository for the full integration model.
