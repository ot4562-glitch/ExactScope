# ExactScope v1.0.0-rc.2 — Integration & Qualification Candidate

`v1.0.0-rc.2` packages the completed code-side ExactScope architecture into a release that can be consumed as an external AI/edge integration candidate. It is still a **prerelease**: model qualification and representative real-device qualification are intentionally left for the next evidence session.

## What changed since rc.1

- Completed the active Statistics/Economics specialization metadata plumbing: stable Statistics kernel IDs/contracts/dispatch and selected lookup are generated or drift-checked from reviewed metadata, while numeric algorithms remain handwritten/reviewed.
- Added exact model-surface contracts and fail-closed identity negotiation for generated capability assets.
- Added deterministic release-shaped packaging, build-input identity, operation-revision compatibility checks, reproducible-build comparison records, and experimental compatibility-record tooling.
- Hardened public C/Wasm unsafe boundaries and source-level public-export auditing.
- Added maintained one-tool llama.cpp envelopes for `xs_eval` and `xs_calc` with offline boundary self-tests.
- Cleaned the public source layout: generated capability/evidence revisions and mutable benchmark outputs are no longer carried forward as product source. Generators, reviewed specs, benchmark harnesses, corpora/preregistration inputs, and historical interpretation documents remain.
- Removed release-workflow version hardcoding. The tag must now match `Cargo.toml`, and archive verification follows the packaged project version.
- Expanded release packaging to include Android ARM64 and Linux ARM64 static SDK paths in addition to Windows/Linux x86-64 evaluation SDKs.
- Added a model-download inventory tool and a deliberately small five-model qualification matrix covering extreme-small, edge-first, modern sub-1B, 2B scale, and independent upper-small model classes.
- Added a complete external-user qualification runbook and a copy-paste next-session prompt.

## Expected release assets

The release workflow is configured to publish:

- `exactscope-eval-1.0.0-rc.2-x86_64-pc-windows-msvc.tar.gz`
- `exactscope-eval-1.0.0-rc.2-x86_64-unknown-linux-gnu.tar.gz`
- `exactscope-wearable-sdk-1.0.0-rc.2-aarch64-linux-android.tar.gz`
- `exactscope-wearable-sdk-1.0.0-rc.2-aarch64-unknown-linux-musl.tar.gz`
- `release-manifest.json`
- `SHA256SUMS`

Do not infer support for an asset that is absent from the actual GitHub release page.

## AI integration

The evaluation SDK includes native static-library and no-import Wasm integration paths plus constrained model-facing assets. ExactScope deliberately exposes a small serving surface:

- `xs_calc` for bounded generic arithmetic plans;
- `xs_eval` for selected reviewed semantic operations;
- `xs_find` remains optional/cold and should not be added to a weak model's hot path by default.

Start with `docs/QUICKSTART.md` and `docs/AI_INTEGRATION.md`.

## Qualification package

Use:

- `docs/QUALIFICATION_HANDOFF.md`
- `docs/NEXT_SESSION_PROMPT.md`
- `benchmarks/NEXT_MODEL_MATRIX.md`
- `benchmarks/model-downloads.json`
- `tools/fetch_benchmark_models.py`

The downloader resolves a model repository revision, downloads the requested model file at that revision, hashes the local bytes, and writes an inventory. It does **not** run inference or a benchmark.

## Claim boundary

There is **no rc2 model-uplift result yet** and **no rc2 real-device latency/RAM/energy qualification yet**. The release is intended to make those tests reproducible from a public immutable candidate.

Historical `statistics-core-8-ai-r20` model evidence remains tied to the older 45,804-byte r17 Statistics runtime. It is useful design evidence but is not transferred to rc2.

Do not report the specialized Wasm linear-memory ceiling as total process/device RAM. Do not promote rc2 to stable/support-qualified based only on source, unit, packaging, or smoke-test success.

## License

ExactScope source remains dual-licensed under MIT or Apache-2.0. Downloaded model weights retain their own upstream licenses/terms; the benchmark model downloader does not change those terms.
