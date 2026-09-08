#!/usr/bin/env python3
"""Fetch and verify the small open-weight models used for wearable screening."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

MODELS = (
    {
        "id": "smollm2-135m-instruct-q4km",
        "repository": "unsloth/SmolLM2-135M-Instruct-GGUF",
        "requested_file": "SmolLM2-135M-Instruct-Q4_K_M.gguf",
        "quantization": "Q4_K_M",
        "expected_sha256": "ed5fa30c487b282ec156c29062f1222e5c20875a944ac98289dbd242e947f747",
    },
    {
        "id": "llama32-1b-instruct-q4km",
        "repository": "bartowski/Llama-3.2-1B-Instruct-GGUF",
        "requested_file": "Llama-3.2-1B-Instruct-Q4_K_M.gguf",
        "quantization": "Q4_K_M",
        "expected_sha256": "6f85a640a97cf2bf5b8e764087b1e83da0fdb51d7c9fab7d0fece9385611df83",
    },
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_revision(repository: str) -> str:
    request = urllib.request.Request(
        f"https://huggingface.co/api/models/{repository}",
        headers={"User-Agent": "ExactScope-wearable-benchmark/1"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    revision = payload.get("sha")
    if not isinstance(revision, str) or len(revision) != 40:
        raise RuntimeError(f"could not resolve revision for {repository}")
    return revision


def fetch_one(spec: dict[str, str], root: Path) -> dict[str, object]:
    revision = resolve_revision(spec["repository"])
    directory = root / spec["id"]
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / spec["requested_file"]
    partial = destination.with_suffix(destination.suffix + ".part")

    if destination.is_file() and sha256_file(destination) == spec["expected_sha256"]:
        state = "reused-verified"
    else:
        partial.unlink(missing_ok=True)
        url = (
            f"https://huggingface.co/{spec['repository']}/resolve/{revision}/"
            f"{spec['requested_file']}?download=true"
        )
        request = urllib.request.Request(url, headers={"User-Agent": "ExactScope-wearable-benchmark/1"})
        with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as output:
            shutil.copyfileobj(response, output, length=8 * 1024 * 1024)
        digest = sha256_file(partial)
        if digest != spec["expected_sha256"]:
            partial.unlink(missing_ok=True)
            raise RuntimeError(f"sha256 mismatch for {spec['id']}: {digest}")
        partial.replace(destination)
        state = "downloaded-verified"

    digest = sha256_file(destination)
    if digest != spec["expected_sha256"]:
        raise RuntimeError(f"post-write sha256 mismatch for {spec['id']}")
    return {
        "id": spec["id"],
        "repository": spec["repository"],
        "resolved_revision": revision,
        "requested_file": spec["requested_file"],
        "runtime": "llama.cpp",
        "quantization": spec["quantization"],
        "bytes": destination.stat().st_size,
        "sha256": digest,
        "path": str(destination),
        "acquisition_state": state,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/mnt/c/AIModels/ExactScopeBench-wearable"))
    parser.add_argument("--manifest", type=Path, default=Path("target/wearable-model-acquisition.json"))
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    args.root.mkdir(parents=True, exist_ok=True)

    records = []
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, len(MODELS)))) as pool:
        futures = {pool.submit(fetch_one, spec, args.root): spec["id"] for spec in MODELS}
        for future in as_completed(futures):
            records.append(future.result())
    records.sort(key=lambda record: record["id"])

    payload = {
        "format": "exactscope.wearable-model-acquisition",
        "format_version": "0.1",
        "records": records,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
