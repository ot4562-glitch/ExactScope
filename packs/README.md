# Official scope packs

Official packs are data, not runtime code. `exactscope-packc` validates/compiles them; the minimum runtime never parses arbitrary formulas or dynamically links pack code.

## 1. Product priority: hot set before full catalog

The frozen v0.1 catalog remains:

| Pack | Frozen catalog target |
|---|---:|
| `math-basic` | 16 operations |
| `statistics-core` | 18 operations |
| `econ-undergrad` | 65 operations |

However, **full 99-operation completion is no longer the first product milestone**.

The first pack objective is a small reviewed benchmark hot set that can prove ExactScope's value in direct one-hop model integration.

Preferred sequence:

```text
reviewed cross-domain hot set
  -> benchmark
  -> provenance/golden strengthening
  -> broader pack completion
```

A smaller defensible set is preferable to a large catalog with weak review or no adoption evidence.

## 2. Benchmark hot-set selection

The first public benchmark should select high-value operations from all three domains.

Selection criteria:

- common enough to matter for small-model quantitative tasks;
- explicit deterministic method;
- compact arguments/signature;
- good coverage of scalar and vector execution;
- strong valid/invalid/boundary testability;
- no hidden empirical assumption or live-data dependency.

Likely candidates include simple percentage/ratio math, mean/variance/stddev/correlation/regression statistics, and textbook economics such as CPI inflation, GDP deflator, real-rate, elasticity, and growth helpers.

The exact benchmark hot set should be machine-readable and bound to pack/operation revisions.

## 3. Operation acceptance

An official operation requires:

- one canonical key and numeric ID;
- explicit method identity;
- immutable argument order and semantic names;
- semantic kinds/unit relationships;
- all constraints;
- exact formula or shared kernel ID;
- output semantic/unit rule;
- explicit scale/rounding;
- deterministic classification where applicable;
- provenance/source metadata;
- successful/invalid/boundary/overflow/resource/precision vectors.

Stable pack release should maintain the repository's stronger golden-vector threshold, but benchmark hot-set operations receive review priority first.

## 4. No formula duplication in adapters

Hot-set catalogs, OpenAI-compatible tool assets, GBNF, and product prompts may copy only **selection metadata** such as key/signature/argument cues.

They may not become a second source of formulas, rounding rules, or classification logic.

## 5. Source layout

Target source layout:

```text
packs/<pack>/
  pack.xsp.json
  SOURCES.md
  CHANGELOG.md
  tests/
```

Compiler/release outputs may include:

```text
<pack>-<version>.xsp
<pack>-<version>.manifest.json
<pack>-<version>.catalog.json
```

Generated binary artifacts are release outputs unless a conformance fixture explicitly requires checked-in bytes.

## 6. Source/provenance policy

A source supports method/definition review; it is not fetched at runtime.

Source notes must state:

- what definition/convention is supported;
- source/license/status;
- whether ExactScope text/vectors are independently authored;
- convention differences resolved by the operation key.

Official packs must avoid pretending that empirical coefficients, forecasts, jurisdiction-specific live rules, or open-ended policy judgments are universal formulas.

## 7. Dependency policy

Official baseline packs do not depend on:

- another pack being installed;
- network data;
- host locale;
- current date/live exchange rates;
- model reasoning after typed arguments are formed;
- native extension code embedded in the pack.

## 8. Compatibility policy

- Existing operation key+revision semantics do not change.
- Alternative methods use separate keys/revisions as appropriate.
- Aliases may evolve without changing canonical identity.
- Pack format/ABI requirements are explicit.
- A pack cannot independently claim target support; support belongs to exact core+artifact+pack evidence.
- Removing/changing operations requires migration/versioning review.

## 9. Dynamic versus fused packaging

Pack semantics remain independent of packaging. A fused operation and the same dynamic-pack operation must use the same shared calculation semantics when both are shipped.

However, complete dynamic-pack/discovery maturity is a secondary v0.1 product priority. It does not block a focused native-static/no-import-Wasm release using a reviewed hot set.

## 10. Expansion rule

Add new domains only after the initial hot set and benchmark demonstrate that ExactScope's bounded resident approach provides a useful product advantage.

Operation count is not a vanity KPI.
