# ExactScope native grounding quickstart

This archive is the small native grounding runtime for ExactScope. It contains the C ABI, a static library, and a demonstration-only grounding index so you can prove the integration path before connecting your own provider data.

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

## 3. Connect your own evidence

ExactScope does not ship a universal knowledge corpus. Compile deployment-specific `.txt` or `.md` evidence with the off-target compiler from the ExactScope source repository:

```bash
python3 tools/grounding_corpus.py build \
  --input-dir ./my-docs \
  --output ./my-corpus.json

python3 tools/grounding_corpus.py compile-binary \
  --index ./my-corpus.json \
  --output ./my-corpus.xsgi
```

Python is a development/compiler dependency only; it is not required by the deployed native grounding runtime.

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
