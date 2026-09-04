# ExactScope hot sets

Hot sets are build-time selections of canonical ExactScope operations for small-model direct evaluation. They contain no formulas and are not a second calculation catalog.

The generator lives in `exactscope-packc`:

```text
cargo run --package exactscope-packc -- hotset hotsets/p0-smoke.json adapters/generated/p0-smoke
```

A hot-set source manifest contains:

- a stable name;
- one or more reviewed `.xsp.json` source-pack paths;
- 1-32 canonical operation keys in product order;
- whether the optional `xs_find` fallback assets should also be emitted.

Before emitting any adapter asset, the generator compiles every referenced source with the canonical pack compiler and hashes the resulting `.xsp` bytes. The generated catalog binds pack SHA-256, pack version, operation revision, compact signature, argument metadata, and a composite binding SHA-256.

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

`adapters/generated/p0-smoke/` is the first reproducibility fixture. CI regenerates it and fails on any byte drift.
