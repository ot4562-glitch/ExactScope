# ExactScope documentation map

Release context: **v1.0.0-rc.2 integration & qualification candidate**
Date: 2026-09-05

This index separates current product/user contracts from historical design/evidence records so older development measurements are not mistaken for rc2 claims.

## Start here

For an evaluator or integrator:

1. [`../README.md`](../README.md) — product scope and release status.
2. [`QUICKSTART.md`](QUICKSTART.md) — install/load the published candidate.
3. [`AI_INTEGRATION.md`](AI_INTEGRATION.md) — attach the smallest model-facing surface.
4. [`QUALIFICATION_HANDOFF.md`](QUALIFICATION_HANDOFF.md) — exact rc2 benchmark/target-evidence contract.
5. [`NEXT_SESSION_PROMPT.md`](NEXT_SESSION_PROMPT.md) — copy-paste prompt for the external-user verification session.
6. [`../benchmarks/NEXT_MODEL_MATRIX.md`](../benchmarks/NEXT_MODEL_MATRIX.md) — frozen minimum model plan.

## Current normative / operational documents

These should describe the current rc2 architecture or current qualification boundary:

- [`PRODUCT_DIRECTION.md`](PRODUCT_DIRECTION.md)
- [`CAPABILITY_PRODUCT_ARCHITECTURE.md`](CAPABILITY_PRODUCT_ARCHITECTURE.md)
- [`CAPABILITY_COMPILER.md`](CAPABILITY_COMPILER.md)
- [`STATISTICS_CAPABILITY_SLICE.md`](STATISTICS_CAPABILITY_SLICE.md)
- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`INSTALLATION.md`](INSTALLATION.md)
- [`AI_INTEGRATION.md`](AI_INTEGRATION.md)
- [`EVALUATION_BUNDLE.md`](EVALUATION_BUNDLE.md)
- [`BENCHMARK.md`](BENCHMARK.md)
- [`COMPATIBILITY.md`](COMPATIBILITY.md)
- [`MARKETING_CLAIMS.md`](MARKETING_CLAIMS.md)
- [`COMMERCIALIZATION.md`](COMMERCIALIZATION.md)
- [`QUALIFICATION_HANDOFF.md`](QUALIFICATION_HANDOFF.md)
- [`CODEX_CONTEXT.md`](CODEX_CONTEXT.md)
- [`NEXT_AGENT_HANDOFF.md`](NEXT_AGENT_HANDOFF.md)

## Historical/design context

These files record how the architecture reached its current state. Historical checklists, revision names, measurements or planned phases inside them are not rc2 evidence unless a current document explicitly revalidates them:

- [`DECISIONS.md`](DECISIONS.md) — append-only decision history; old revisions are intentionally preserved.
- [`FIRST_IMPLEMENTATION_SLICE.md`](FIRST_IMPLEMENTATION_SLICE.md) — early implementation-slice context.
- [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) — historical productization sequence; current next work is in `../ROADMAP.md` and the qualification handoff.
- [`RETROFIT_PRODUCT_STRATEGY.md`](RETROFIT_PRODUCT_STRATEGY.md) — product-thesis/design rationale, updated with the rc2 evidence boundary.
- historical `STATISTICS_R17_*_RESULT.md` files — result interpretations tied to older exact runtimes, not rc2.
- [`REFERENCES.md`](REFERENCES.md) — reference material rather than a release-status document.

## rc2 evidence rule

The code-side implementation and packaging candidate can be described from source/build/package checks. Claims about model uplift, target RAM/latency/energy, production readiness, stable support, or hardware-life extension require new evidence bound to the exact immutable `v1.0.0-rc.2` release.

Historical `statistics-core-8-ai-r20` evidence belongs to an older **45,804-byte r17 Statistics serving runtime** and is never inherited by rc2.

## Clean-source rule

The public source tag keeps reviewed source/specifications, generators, adapters, benchmark harnesses/preregistration inputs, and historical interpretation documents. It intentionally does not accumulate mutable generated capability/evidence revision directories or mutable benchmark output payloads.

- `adapters/capabilities/` — policy/readme in the clean tag; generate new revisions for exact candidates.
- `benchmarks/output/` — ignored work output.
- `benchmarks/results/` — policy/readme in the clean tag; freeze publishable evidence separately with immutable identity.

Do not delete historical frozen evidence from a developer checkout to create a clean release. Prepare the release from a separate clean snapshot, as done for rc2.
