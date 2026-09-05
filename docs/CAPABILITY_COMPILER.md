# Experimental capability compiler

`tools/compile_capability.py` composes the existing Rust `exactscope-packc hotset`
generator. Python/jsonschema are workstation build dependencies only. It derives
the selected Statistics operations from a reviewed task-family map, checks that
the requested operation list agrees, binds their actual fused revisions, and
enforces measured combined prompt/schema/grammar budgets. No runtime dependency
or public ABI changes are introduced.

```sh
cargo build -p exactscope-packc
python tools/compile_capability.py spec/examples/statistics-capability-profile.json adapters/capabilities/statistics-core-8-ai-r2
python tools/compile_capability.py --verify adapters/capabilities/statistics-core-8-ai-r2
python tools/test_compile_capability.py
```

Change task families and their corresponding selected operations/count to compile
a smaller surface. Unknown families, duplicate JSON keys, unsupported revisions,
inconsistent counts/bounds, discovery, fabricated bindings/evidence and unsupported
support promotions fail closed. Existing identical output is idempotent; different
output requires a new directory and, for a published identity, a new revision.

Canonical JSON uses sorted keys, ASCII escaping, compact separators and one LF.
Task families and selected operations are sorted; argument order is preserved.
`profile.json` binds the LF-normalized runtime source tree, ABI and fused registry,
and file-name-to-SHA-256 maps for each model asset category. `manifest.json` hashes
all payloads including the profile and records selected operation revisions and
actual static measurements. `bundle-sha256.txt` hashes the manifest; nothing hashes
itself. Timestamps, absolute paths and Git working-directory state are excluded.
Integrity verification is not a signature or publisher authentication mechanism.

The checked-in combined Statistics surface has two tools, eight semantic
operations, a 366-byte prompt, 2,197 combined schema/tool bytes and 2,412 combined
grammar bytes. These are asset measurements, not tokenizer/model accuracy results.
The schema groups equal argument shapes and checks operation-specific arity. GBNF
bounds each vector at 64 leaves. Total 64-leaf, 512-byte, decimal representation,
back-reference and mathematical constraints remain authoritative runtime checks.
The schema uses JSON Schema 2020-12 `prefixItems`; integrations using narrower tool
schema dialects should use the GBNF path rather than silently dropping constraints.

This initial compiler emits a **host-enforced model surface**, not a specialized
runtime binary. The existing fused artifact still contains other operations and
discovery; hosts must restrict calls to the bound profile. Artifact and evidence
slots remain null and support remains experimental. A profile source must not
pretend that a filename or a declared budget is qualification evidence. Binary
specialization, verified artifact/evidence attachment, model-token measurements and
released immutable identity management remain separate work.

The baseline no-import Wasm was reproduced at 102,971 bytes, zero imports and 17
initial pages, SHA-256
`8ea9729a73485041bf77d6f673eb25bd4b0219b9af27986a4cc5a9548a42ea94`.
Build-time compiler changes do not enter the runtime dependency graph.
