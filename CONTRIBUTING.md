# Contributing to ExactScope

ExactScope is compatibility-first infrastructure for constrained AI. Contributions are evaluated primarily by deterministic semantics, footprint, portability, and failure behavior—not feature count.

## Current repository phase

The repository contains an experimental v0.1 runtime: the deterministic scalar evaluator, C ABI, no-import Wasm path, pack compiler/loader foundations, Tiny JSON scalar adapter, wearable reference integration, executable economics formulas, and initial exact statistics kernels are present. No stable runtime release has been declared. New implementation must extend the shared core and follow `docs/PRODUCT_DIRECTION.md`, `docs/FIRST_IMPLEMENTATION_SLICE.md`, `crates/README.md`, and `docs/IMPLEMENTATION_PLAN.md` rather than creating parallel evaluators or application-specific calculation code.

Before proposing a large change, read:

- `docs/PRODUCT_DIRECTION.md`
- `docs/ARCHITECTURE.md`
- `docs/COMPATIBILITY.md`
- `docs/INSTALLATION.md`
- `docs/DECISIONS.md`
- `docs/FIRST_IMPLEMENTATION_SLICE.md`
- `spec/README.md`
- `packs/CATALOG_V0_1.md`
- `SECURITY.md`

## Core principles

A contribution must not casually weaken these properties:

- offline operation;
- AI-only headless interface;
- no mandatory daemon;
- `no_std` and no-allocation minimum profile;
- stable C ABI and no-import WebAssembly;
- deterministic base-10 numeric semantics;
- data-only scope packs;
- bounded execution and memory;
- typed fail-closed errors;
- two-tool default model surface;
- conformance-based compatibility claims.

## Contribution categories

### Specification changes

A specification pull request must include:

- the exact ambiguity or defect being fixed;
- affected ABI/pack/wire/operation versions;
- updated schemas and examples;
- compatibility and migration impact;
- new or changed conformance cases;
- an architecture-decision update when a binding decision changes.

Do not change one example while leaving the normative schema or prose inconsistent.

### Runtime changes

A runtime pull request must include:

- tests for success, invalid input, boundary, and overflow paths;
- no-default-features/`no_std` verification where applicable;
- size impact for core and fused Wasm;
- allocation behavior;
- target compatibility impact;
- safety invariants for every unsafe block;
- proof that adapters or platform wrappers do not own calculation semantics.

A new runtime dependency requires the dependency review in `crates/README.md`.

### Operation/pack changes

A new official operation requires:

- canonical key and pack-local ID;
- revision `1` or a justified new revision;
- short positional signature;
- method identity and alternatives;
- semantic kinds, units, constraints, and cross-input relations;
- exact formula or approved kernel ID;
- output and rounding policy;
- classification rules when applicable;
- source metadata;
- golden tests;
- reason it belongs in a small, frequently useful deterministic pack.

Do not add:

- open-ended forecasts;
- empirical coefficients presented as universal constants;
- live-data dependencies;
- ambiguous operations that silently choose a method;
- duplicate aliases that make discovery nondeterministic;
- arbitrary pack code.

### Adapter changes

Adapters must share generated schemas and fixtures. They may translate envelopes but may not calculate, round, classify, coerce, or repair values independently.

### Compatibility ports

A new platform contribution must provide evidence required by `docs/COMPATIBILITY.md`. A successful compile alone earns `experimental` or `planned`, not Tier 1/2.

## Pull-request checklist

- [ ] The change has one clear responsibility.
- [ ] Normative files and examples agree.
- [ ] JSON and JSONL fixtures parse.
- [ ] Machine-readable examples validate against their schemas.
- [ ] Existing operation semantics are unchanged or revisioned.
- [ ] Failure precedence remains deterministic.
- [ ] No hidden allocation/network/platform dependency entered the minimum core.
- [ ] Size/compatibility impact is measured or explicitly not applicable.
- [ ] New dependencies are justified.
- [ ] Security-sensitive parsing/ABI changes have negative tests.
- [ ] Documentation does not claim unmeasured performance or unsupported hardware.

## Style

- Use precise machine-oriented terms and stable identifiers.
- Prefer small explicit structures over flexible generic objects.
- Keep model-facing names short but understandable.
- Keep developer documentation verbose enough to remove implementation ambiguity.
- Do not use natural-language strings as program logic.
- Avoid silent defaults; defaults must be specified and tested.
- Comments should explain invariants and compatibility reasons, not restate code.

## Current baseline checks

Before runtime code exists, every change must pass:

```text
python tools/validate_design.py
cc -std=c99 -pedantic-errors -Wall -Wextra -Werror -Iinclude -fsyntax-only tests/abi/header_c.c
c++ -std=c++11 -pedantic-errors -Wall -Wextra -Werror -Iinclude -fsyntax-only tests/abi/header_cpp.cpp
cargo fmt --all -- --check
cargo check --workspace --all-targets
cargo check --target wasm32v1-none --no-default-features \
  --package exactscope-kernel --package exactscope-pack --package exactscope-wasm
```

The Rust commands are enforced in GitHub Actions with both the pinned primary toolchain and the declared minimum Rust version.

## Testing expectations after code exists

Runtime changes are expected to pass:

```text
format + lint
unit tests
schema/example validation
pack compiler reproducibility
golden conformance vectors
C and C++ ABI compile/layout tests
wasm32v1-none build and import inspection
fused/dynamic equivalence
size regression checks
parser fuzz smoke tests
```

Official pack changes additionally run the complete pack corpus and catalog semantic diff.

## Responsible disclosure

Potential vulnerabilities should follow `SECURITY.md`, not a public issue containing an exploit.

## Licensing contributions

Unless explicitly stated otherwise, contributions to ExactScope are accepted under the repository's dual Apache-2.0/MIT terms. Pack sources must declare compatible source and content licensing. Do not copy formula explanations, textbook prose, or test material without a compatible license and attribution review.
