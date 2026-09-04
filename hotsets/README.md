# ExactScope hot sets

Hot sets are build-time selections of canonical ExactScope operations for small-model direct evaluation. They contain no formulas and are not a second calculation catalog.

The generator lives in `exactscope-packc`:

```text
cargo run --package exactscope-packc -- hotset hotsets/p0-smoke.json adapters/generated/p0-smoke
```

A hot-set source manifest contains:

- a stable name;
- explicit `sources` and `fused_packs` arrays;
- reviewed `.xsp.json` source-pack paths and/or a supported built-in fused registry such as `econ-undergrad`;
- 1-32 canonical operation keys in product order;
- whether the optional `xs_find` fallback assets should also be emitted.

For source packs, the generator compiles the source with the canonical pack compiler and records a binding for the resulting `.xsp` bytes. For fused registries, it records a binding over canonical operation identity, revision, signature, method, and argument metadata. The catalog also carries a composite binding for the selected hot set.

Current Tiny JSON model calls accept scalar decimal-string arguments. The generator therefore rejects vector operations for `xs-eval.tool.json`/GBNF instead of publishing a schema the runtime cannot honor. Vector operations continue to use typed/TinyWire host paths until a dedicated model-facing vector contract is implemented.

Generated files for a scalar direct hot set are:

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

`adapters/generated/p0-smoke/` is the minimal reproducibility fixture. `adapters/generated/econ-core-8/` is the first production-size economics hot set. CI regenerates both and fails on any byte drift.
