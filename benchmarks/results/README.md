# Benchmark results

Release source tags do not ship mutable or runtime-specific benchmark result payloads here.

Run outputs belong under `benchmarks/output/` (git-ignored). After a qualification run is frozen, publish its exact corpus, model identity, artifact digest, configuration, raw records, summary, and checksums as a separate evidence artifact or a new immutable evidence revision. Do not silently replace historical results and do not attach an old score to a new ExactScope runtime.

The source release keeps benchmark harnesses, corpora/preregistration inputs, and result interpretation documents so a user can reproduce or extend the evaluation without inheriting previous scores.

See `docs/QUALIFICATION_HANDOFF.md` and `benchmarks/NEXT_MODEL_MATRIX.md`.
