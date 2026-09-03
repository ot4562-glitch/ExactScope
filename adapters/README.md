# Adapter policy

Adapters connect AI runtimes and host platforms to the same ExactScope core. They are convenience and compatibility layers, never calculation authorities.

## Implemented integration references

### `wearable`

[`wearable/`](wearable/) is the product-integration reference for AI glasses and similarly constrained edge devices. It provides a C99/C++11-consumable, allocation-free host state machine around the stable C ABI and enforces the machine-readable wearable profile: frozen-before-serve registry state, 16 KiB mutable budget, zero-byte pack-mount arena, bounded pack storage, exact lookup/eval modes, and privacy-minimized telemetry.

It is a vendor-neutral reference, not a claim of compatibility with unpublished platform internals or a substitute for target-device latency/energy qualification.

## Planned adapters

### `llama-cpp`

Deliverables:

- OpenAI-style definitions for `xs_find` and `xs_eval`;
- checked-in GBNF grammars for both argument objects;
- compact system-prompt fragment;
- fixtures for raw JSON, OpenAI-compatible tool calls, and common tag-wrapped tool calls;
- integration tests with selected small GGUF models;
- catalog hot-set generator keyed by installed pack digest.

The adapter must not require llama.cpp internals in the core repository. It may provide examples for server and in-process integrations.

### `openai-tools`

Deliverables:

- conservative JSON Schema tool definitions;
- response parsing examples;
- no assumption that the remote model performs calculation itself;
- identical Tiny JSON fixtures.

This adapter demonstrates protocol compatibility; cloud use is never required by ExactScope.

### `android`

Deliverables:

- AAR/Prefab packaging of the C ABI;
- optional minimal Kotlin/JNI wrapper;
- direct byte-buffer APIs to avoid unnecessary copies;
- asset-pack and fused-library examples;
- no permissions, service, telemetry, or Google Play dependency.

### `mcp`

Optional desktop bridge exposing the same two logical operations.

The MCP adapter may be implemented in a convenient host language, but it must delegate every calculation and validation result to the native/Wasm core and preserve provenance/errors.

## Non-negotiable rules

An adapter must not:

- maintain a divergent formula catalog;
- calculate or reclassify results;
- use binary floating point to parse exact decimal arguments;
- guess omitted values or methods;
- silently convert rates, currencies, units, or periods;
- turn core errors into plausible numeric answers;
- require network access for core operation;
- expose hundreds of per-operation tools by default;
- claim compatibility without shared fixtures.

An adapter may:

- translate an outer tool-call envelope;
- validate the two model-facing schemas;
- normalize a discovery query according to the documented profile;
- cache immutable operation metadata by pack digest;
- render a core result for a product after preserving the machine value;
- add locale aliases outside the minimum runtime;
- choose native C ABI or WebAssembly according to host support.

## Generated artifacts

The following should be generated from normative schemas/catalogs to prevent drift:

```text
adapters/generated/xs-find.tool.json
adapters/generated/xs-eval.tool.json
adapters/generated/xs-find.gbnf
adapters/generated/xs-eval.gbnf
adapters/generated/status-codes.json
adapters/generated/hot-catalog.<pack-digest>.json
```

Generated files are checked for reproducibility. Release artifacts may include them; the repository should commit only stable fixtures and generators according to the implementation plan.

## Compatibility test matrix

Every adapter runs:

- valid `xs_find` and `xs_eval` fixtures;
- unknown-field rejection;
- exact large decimal string preservation;
- missing and reordered argument cases;
- ambiguity preservation;
- every core error family mapping;
- provenance preservation;
- response-size limits;
- installed-pack catalog digest matching.

Model-specific tests are additional evidence, not replacements for protocol fixtures.

## Small-model prompt budget

The default tool definitions plus policy fragment should remain within a measured compact budget. Initial target:

- two tool definitions only;
- no embedded full catalog;
- policy text below 120 English tokens where the runtime permits;
- optional hot catalog limited to 8–32 signatures;
- discovery response limited to five matches.

Prompt-size regressions must be measured because context consumption directly affects constrained-model compatibility.
