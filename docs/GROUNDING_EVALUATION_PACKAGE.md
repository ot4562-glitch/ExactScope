# Grounding evaluation package

Status: **benchmark/evaluation package contract retained for reproducible A/G evidence. Stable v1 deployment uses the separate Linux x86-64 native grounding runtime bundle defined in `spec/GROUNDING_RUNTIME_BUNDLE_V1.md`.**

r3 at source `125ad9403f22eece7f552701d4c7376bba3b697f` is excluded because of float latency serialization; r4 at `aac351644f8c6059721ede4c10c6ac2c0a6c7b54` is diagnostic only because run checksums preceded model-server shutdown. Integrity-corrected **r5** at `e6c3558642c77e379358b9f59aedd92abf7473f4` remains frozen historical comparison evidence. The selected r25 behavior adds serving-derived authoritative-unresolved and canonical-scalar host completion plus a one-time calibrated compact G answer surface. Model-accuracy evidence remains bound to its exact candidate/provider/corpus/model/runtime identity and is separate from the stable native software-package claim.

This package exists to let an independent session reproduce a frozen benchmark candidate without using a developer checkout. It is not a production deployment package. Every selected candidate must be packaged and preregistered independently; historical run evidence is never copied into a new package identity.

## Purpose

The package freezes and carries:

- one generated rc4 grounding candidate with physically separated `candidate/serving/` and `candidate/gold/` trees;
- the provider-neutral grounding reference runtime and its exact profile/source/provider/projection assets;
- the A/G generation configuration and gold-isolation policy;
- the selected seven-model identity inventory, without copying GGUF files into the archive;
- the frozen llama.cpp runtime/hardware configuration record, without copying the runtime binary;
- zero-inference dry-run, preregistration, package verification and scorer tools;
- the selected `grounding_v1` model surface and llama.cpp adapter bytes;
- the model runner that is permitted to perform inference only after a frozen preregistration is supplied;
- the relevant grounding contract, runtime, integration, architecture and benchmark documents.

The package intentionally keeps model weights and `llama-server` external. Preregistration resolves their local paths and verifies their byte hashes against the packaged identities before any model call.

## Package layout

```text
candidate/
  serving/
  gold/
  manifests/
benchmarks/
  grounding_dry_run.py
  grounding_preregister.py
  run_grounding_benchmark.py
  score_grounding.py
  grounding-generation-config.json
  grounding-isolation-policy.json
  grounding-model-inventory.json
  grounding-runtime-llama-v040.json
tools/
  grounding_canonical.py
  grounding_match.py
  grounding_runtime.py
  grounding_v1_surface.py
  verify_grounding_package.py
adapters/
  llama-cpp/
    grounding_v1.py
    README.md
spec/
  GROUNDING_CONTRACT_V0_1.md
  schemas/grounding-*.schema.json
docs/
  GROUNDING_ARCHITECTURE.md
  GROUNDING_RUNTIME_RC4.md
  AI_INTEGRATION.md
  BENCHMARK.md
package-manifest.json
SHA256SUMS
README.md
```

`candidate/gold/` is scorer-only. The serving dry-run and model runner must not open it. The scorer opens gold only after a complete raw A/G run exists.

The extracted package is also treated as an immutable payload. Packaged Python entrypoints disable bytecode-cache writes before importing package-local modules, so normal verification/dry-run/preregistration/help paths must not create `__pycache__` or `.pyc` files inside the package. The strict package verifier therefore remains valid after first use rather than needing to ignore interpreter-generated extra files.

## Zero-inference clean-room sequence

From the extracted package root:

```text
python tools/verify_grounding_package.py
python benchmarks/grounding_dry_run.py serve --candidate candidate --output dryrun-serving
python benchmarks/grounding_dry_run.py verify-gold --candidate candidate --records dryrun-serving/serving-records.jsonl --output dryrun-gold
python benchmarks/grounding_preregister.py create --help
```

All four commands above perform zero model inference. The first three validate package identity and the complete serving/policy path. The fourth displays the arguments required to freeze an actual model run.

For a real preregistration, provide the local model root or model path, the exact local `llama-server` executable, the package manifest/archive hash, source commit, and a unique planned output directory. Preregistration verifies those bytes and writes one canonical immutable run record.

## Model-run boundary

`run_grounding_benchmark.py` is the only package command intended to launch `llama-server` and perform model inference. It must reject:

- a missing or noncanonical preregistration;
- any model/runtime/candidate/config/scorer digest drift;
- an existing or wrong output directory;
- a changed A/G arm set, retry count, answer-call count or hidden-repair policy.

The runner uses exactly one answer-generation request per item in A. G performs grounding first and then uses either zero model calls under the two preregistered deterministic host-completion rules (one authoritative unresolved target, or one grounded canonical scalar item) or exactly one model answer request for every remaining item. G never uses more than one answer request, retries, model-visible retrieval tools, or query-rewrite calls. The run record reports unresolved-host, scalar-host, and G-model counts separately.

## Claims

Passing package verification, dry-run and preregistration proves only that the candidate is reproducible and ready to benchmark. It does **not** establish improved factual accuracy, hallucination reduction, production readiness, physical ARM64 resource cost or energy behavior. Those claims require the later frozen model and target-device evidence described in `docs/BENCHMARK.md`.
