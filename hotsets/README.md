# ExactScope hot sets

Hot sets are build-time selections of canonical ExactScope operations for small-model direct evaluation. They contain no formulas and are not a second calculation catalog. In the current product architecture, a hot set is an **implementation input/build artifact for a semantic capability slice**, not the product unit by itself; task-family coverage and model/device budgets determine whether a selection is useful.

The generator lives in `exactscope-packc`:

```text
cargo run --package exactscope-packc -- hotset hotsets/p0-smoke.json adapters/generated/p0-smoke
```

A hot-set source manifest contains:

- a stable name;
- explicit `sources` and `fused_packs` arrays;
- reviewed `.xsp.json` source-pack paths and/or supported built-in fused registries such as `econ-undergrad` and `statistics-core`;
- 1-32 canonical operation keys in product order;
- whether the optional `xs_find` fallback assets should also be emitted.

For source packs, the generator compiles the source with the canonical pack compiler and records a binding for the resulting `.xsp` bytes. For fused registries, it records a binding over canonical operation identity, revision, signature, method, argument metadata, and kernel output metadata where applicable. The catalog also carries a composite binding for the selected hot set.

Tiny JSON model calls accept exact scalar decimal strings and bounded vectors encoded as arrays of exact decimal strings. The generic OpenAI-compatible tool schema exposes that scalar/vector union, while generated GBNF fixes the exact arity and scalar/vector shape for every selected operation. The runtime still enforces the 512-byte request, 12 top-level argument, and 64 decimal-leaf limits.

Generated files for a direct hot set are:

```text
catalog.json
binding-sha256.txt
xs-eval.tool.json
xs-eval.gbnf
prompt-fragment.txt
```

When `include_find` is true, the bundle also contains:

```text
xs-find.tool.json
xs-find.gbnf
```

`adapters/generated/p0-smoke/` is the minimal reproducibility fixture. `econ-core-8` and `statistics-core-8` are focused domain hot sets, while `quant-core-16` is the current mixed economics/statistics benchmark and prerelease-evaluation selection. CI regenerates all checked-in hot sets and fails on any byte drift.
