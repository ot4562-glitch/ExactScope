# Generated capability bundles

This directory is intentionally source-clean in release tags.

ExactScope capability bundles are generated from reviewed specifications under `spec/` by `tools/compile_capability.py` and related build/bind tooling. Historical development revisions and model-evidence descendants are not copied into new source releases because they are immutable evidence tied to older source/artifact identities, not product source code.

For a new evaluation or qualification run:

1. start from the exact release tag and its published SDK/runtime artifact;
2. generate a new capability revision from the reviewed request/profile inputs;
3. bind evidence only to that exact generated artifact;
4. never transfer historical model scores to a different runtime digest.

See `docs/AI_INTEGRATION.md`, `docs/QUALIFICATION_HANDOFF.md`, and `benchmarks/NEXT_MODEL_MATRIX.md`.
