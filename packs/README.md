# Official scope packs

Official packs are data, not runtime code. Pack source is compiled and validated by `exactscope-packc`; the minimum runtime never parses free-form formulas or dynamically links plugins.

## Planned official packs

| Pack | Purpose | v0.1 target |
|---|---|---:|
| `math-basic` | High-frequency arithmetic, ratios, percentages, and simple equations | 16 operations |
| `statistics-core` | Bounded descriptive statistics and common inferential helpers | 18 operations |
| `econ-undergrad` | Formula-driven undergraduate economics calculations | 65 operations |

The exact initial catalog is in [CATALOG_V0_1.md](CATALOG_V0_1.md).

## Source layout

```text
packs/<pack>/
  pack.xsp.json           # reviewed source definition
  SOURCES.md              # domain/source review notes
  CHANGELOG.md            # operation/alias additions by pack version
  tests/                  # optional large external golden corpus
```

The compiler produces:

```text
<pack>-<version>.xsp
<pack>-<version>.manifest.json
<pack>-<version>.catalog.json
```

Generated binary artifacts are release outputs and are not committed unless a conformance fixture explicitly requires bytes.

## Operation acceptance

An official operation is accepted only when it has:

- one canonical key and numeric ID;
- immutable input order and short semantic names;
- explicit method identity;
- argument semantic kinds and unit relationships;
- all scalar and cross-input constraints;
- exact formula or core kernel ID;
- output semantic/unit rule;
- explicit scale and rounding;
- deterministic classification rules where applicable;
- source metadata;
- successful, invalid, boundary, overflow, and rounding vectors;
- at least 20 golden vectors before a stable pack release;
- fused/dynamic equivalence evidence.

## Dependency policy

Official v0.1 packs depend only on the core numeric profile and kernel IDs. They do not depend on:

- another pack being installed;
- network data;
- host locale;
- current date or exchange rates;
- model output beyond typed arguments;
- native extension code.

Duplicate convenience operations across packs are permitted only when they preserve a domain-friendly canonical key and compile to the same tested semantics. The catalog should prefer shared core programs without creating runtime pack dependencies.

## Source policy

Sources support definition review and provenance. A source URL never authorizes runtime fetching. Official pack formulas must be standard deterministic relationships, not empirical coefficients or forecasts that vary by dataset, jurisdiction, or date.

A source addition must state:

- what definition or convention it supports;
- its license/status;
- whether ExactScope text or test vectors are independently authored;
- any convention differences resolved by the operation key.

## Compatibility policy

- Operation meaning cannot change under the same key and revision.
- Alternative methods use alternative keys.
- Aliases may be added but canonical keys remain stable.
- Pack format/ABI requirements are explicit.
- A pack version cannot claim target support independently of core conformance.
- Removing an operation from an official pack requires a major pack version and migration note.
