# Grounding evaluation package

Status: **rc4 pre-inference evaluation/qualification package contract**.

This package exists to let an independent session reach the first model request without using a developer checkout. It is not a production deployment package and does not claim that grounding improves model accuracy before the A/G benchmark is run.

## Purpose

The package freezes and carries:

- one generated rc4 grounding candidate with physically separated `candidate/serving/` and `candidate/gold/` trees;
- the provider-neutral grounding reference runtime and its exact profile/source/provider/projection assets;
- the A/G generation configuration and gold-isolation policy;
- the five-model identity inventory, without copying multi-gigabyte GGUF files into the archive;
- the frozen llama.cpp runtime/hardware configuration record, without copying the runtime binary;
- zero-inference dry-run, preregistration, package verification and scorer tools;
- the model runner that is permitted to perform inference only after a frozen preregistration is supplied;
- the relevant grounding contract, architecture and benchmark documents.

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
  verify_grounding_package.py
spec/
  GROUNDING_CONTRACT_V0_1.md
  schemas/grounding-*.schema.json
docs/
  GROUNDING_ARCHITECTURE.md
  BENCHMARK.md
package-manifest.json
SHA256SUMS
README.md
```

`candidate/gold/` is scorer-only. The serving dry-run and model runner must not open it. The scorer opens gold only after a complete raw A/G run exists.

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

The runner uses exactly one answer-generation request per item in A and one in G. G performs grounding before its one answer request; A does not. Neither arm uses model-visible retrieval tools or query-rewrite calls.

## Claims

Passing package verification, dry-run and preregistration proves only that the candidate is reproducible and ready to benchmark. It does **not** establish improved factual accuracy, hallucination reduction, production readiness, physical ARM64 resource cost or energy behavior. Those claims require the later frozen model and target-device evidence described in `docs/BENCHMARK.md`.
