#!/usr/bin/env python3
"""Resolve, freeze, acquire, and verify the 20-model ExactScope v1 benchmark matrix.

A benchmark run must never attach a newly-resolved repository revision to stale
cached bytes.  The supported workflow is therefore two-stage:

1. ``--resolve-only --freeze-matrix ...`` resolves every repository to an exact
   revision, exact GGUF filename, upstream LFS SHA-256, and byte size.
2. Review/copy that frozen matrix into the tracked benchmark definition, then
   run normal acquisition.  Normal acquisition refuses unpinned model rows and
   verifies every reused/downloaded file against the frozen upstream digest.

Downloaded model files and acquisition manifests remain local qualification
inputs; the tracked matrix is the reproducibility contract.
To export the v1 inventory, pass
``--write-grounding-inventory benchmarks/v1-grounding-model-inventory-20.json``.
The historical grounding-model-inventory.json remains the seven-model default.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "benchmarks/v1-model-matrix-20.json"
USER_AGENT = "ExactScope-v1-20-model-matrix/2"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=False, ensure_ascii=False) + "\n").encode("utf-8")


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def request_json(url: str) -> object:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def resolve_repository_revision(repository: str) -> str:
    value = request_json(f"https://huggingface.co/api/models/{repository}")
    if not isinstance(value, dict):
        raise RuntimeError(f"malformed model API response: {repository}")
    revision = value.get("sha")
    if not isinstance(revision, str) or len(revision) != 40:
        raise RuntimeError(f"could not resolve repository revision: {repository}")
    return revision


def repository_tree(repository: str, revision: str) -> list[dict]:
    encoded_revision = urllib.parse.quote(revision, safe="")
    value = request_json(
        f"https://huggingface.co/api/models/{repository}/tree/{encoded_revision}?recursive=true&expand=true"
    )
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise RuntimeError(f"malformed repository tree: {repository}@{revision}")
    return value


def select_entry(spec: dict, tree: list[dict]) -> dict:
    entries = [row for row in tree if row.get("type") == "file" and isinstance(row.get("path"), str)]
    requested = spec.get("requested_file")
    if requested is not None:
        matches = [row for row in entries if row["path"] == requested]
        if len(matches) != 1:
            raise RuntimeError(f"requested file is absent or ambiguous in {spec['repository']}: {requested}")
        return matches[0]

    quant = str(spec["quantization"]).lower()
    candidates = [
        row for row in entries
        if row["path"].lower().endswith(".gguf")
        and quant in row["path"].lower()
        and "mmproj" not in row["path"].lower()
        and "imatrix" not in row["path"].lower()
        and "-0000" not in row["path"].lower()
    ]
    if not candidates:
        raise RuntimeError(f"no single-file {spec['quantization']} GGUF in {spec['repository']}")
    candidates.sort(key=lambda row: (len(row["path"]), row["path"].lower()))
    return candidates[0]


def upstream_identity(entry: dict, repository: str) -> tuple[int, str]:
    size = entry.get("size")
    lfs = entry.get("lfs")
    digest = lfs.get("oid") if isinstance(lfs, dict) else None
    lfs_size = lfs.get("size") if isinstance(lfs, dict) else None
    if type(size) is not int or size <= 0:
        raise RuntimeError(f"missing upstream file size: {repository}/{entry.get('path')}")
    if type(lfs_size) is int and lfs_size != size:
        raise RuntimeError(f"upstream LFS size mismatch: {repository}/{entry.get('path')}")
    if not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise RuntimeError(f"GGUF lacks upstream LFS SHA-256: {repository}/{entry.get('path')}")
    return size, digest


def resolve_spec(spec: dict) -> dict:
    repository = str(spec["repository"])
    pinned_revision = spec.get("resolved_revision")
    revision = pinned_revision if isinstance(pinned_revision, str) and len(pinned_revision) == 40 else resolve_repository_revision(repository)
    tree = repository_tree(repository, revision)
    entry = select_entry(spec, tree)
    size, digest = upstream_identity(entry, repository)

    expected_file = spec.get("requested_file")
    expected_size = spec.get("bytes")
    expected_digest = spec.get("upstream_sha256")
    if expected_file is not None and expected_file != entry["path"]:
        raise RuntimeError(f"frozen filename drift for {spec['id']}")
    if expected_size is not None and expected_size != size:
        raise RuntimeError(f"frozen byte-size drift for {spec['id']}")
    if expected_digest is not None and expected_digest != digest:
        raise RuntimeError(f"frozen upstream digest drift for {spec['id']}")

    result = dict(spec)
    result["resolved_revision"] = revision
    result["requested_file"] = entry["path"]
    result["bytes"] = size
    result["upstream_sha256"] = digest
    return result


def validate_matrix(matrix: dict, *, require_frozen: bool) -> list[dict]:
    models = matrix.get("models") if isinstance(matrix, dict) else None
    if not isinstance(models, list) or len(models) != 20:
        raise RuntimeError("v1 benchmark matrix must contain exactly 20 models")
    if len({row.get("id") for row in models if isinstance(row, dict)}) != 20:
        raise RuntimeError("v1 benchmark model ids must be unique")
    if require_frozen:
        policy = matrix.get("selection_policy")
        if not isinstance(policy, dict) or policy.get("frozen") is not True:
            raise RuntimeError("normal acquisition requires a reviewed frozen matrix")
        for row in models:
            if not isinstance(row, dict):
                raise RuntimeError("matrix model row is not an object")
            for key in ("resolved_revision", "requested_file", "bytes", "upstream_sha256"):
                if row.get(key) in (None, ""):
                    raise RuntimeError(f"frozen matrix row lacks {key}: {row.get('id')}")
    return models


def freeze_matrix(matrix: dict, resolved: list[dict], output: Path) -> dict:
    frozen = json.loads(json.dumps(matrix))
    policy = frozen.setdefault("selection_policy", {})
    policy["frozen"] = True
    policy["freeze_contract"] = "hf-revision-file-lfs-sha256-bytes-v1"
    policy["frozen_at_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    frozen["models"] = resolved
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes(frozen))
    return frozen


def existing_model(spec: dict, filename: str, digest: str, size: int) -> Path | None:
    for raw in spec.get("existing_paths", []):
        path = Path(raw)
        if not path.is_file() or path.name != filename or path.stat().st_size != size:
            continue
        if sha256_file(path) == digest:
            return path
    return None


def download(repository: str, revision: str, filename: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    partial.unlink(missing_ok=True)
    quoted = urllib.parse.quote(filename, safe="/")
    url = f"https://huggingface.co/{repository}/resolve/{revision}/{quoted}?download=true"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=180) as response, partial.open("wb") as output:
            shutil.copyfileobj(response, output, length=8 * 1024 * 1024)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    partial.replace(destination)


def acquire_one(spec: dict, output_root: Path) -> dict:
    resolved = resolve_spec(spec)
    revision = resolved["resolved_revision"]
    filename = resolved["requested_file"]
    size = resolved["bytes"]
    digest = resolved["upstream_sha256"]

    path = existing_model(resolved, filename, digest, size)
    state = "reused-existing-verified" if path is not None else ""
    if path is None:
        path = output_root / str(resolved["id"]) / filename
        if path.is_file() and path.stat().st_size == size and sha256_file(path) == digest:
            state = "reused-matrix-root-verified"
        else:
            path.unlink(missing_ok=True)
            download(str(resolved["repository"]), revision, filename, path)
            state = "downloaded-verified"

    actual_size = path.stat().st_size
    actual_digest = sha256_file(path)
    if actual_size != size or actual_digest != digest:
        raise RuntimeError(f"downloaded/reused artifact identity mismatch for {resolved['id']}")

    return {
        "id": resolved["id"],
        "family": resolved["family"],
        "parameters": resolved["parameters"],
        "bucket": resolved["bucket"],
        "repository": resolved["repository"],
        "resolved_revision": revision,
        "requested_file": filename,
        "runtime": "llama.cpp",
        "quantization": resolved["quantization"],
        "bytes": actual_size,
        "sha256": actual_digest,
        "upstream_sha256": digest,
        "path": str(path.resolve()),
        "acquisition_state": state,
    }


def write_grounding_inventory(path: Path, matrix_sha256: str, records: list[dict]) -> None:
    compact = [
        {key: record[key] for key in (
            "id", "repository", "resolved_revision", "requested_file", "runtime",
            "quantization", "bytes", "sha256",
        )}
        for record in records
    ]
    payload = {
        "format": "exactscope.grounding-model-inventory",
        "format_version": "0.1",
        "source_inventory_sha256": matrix_sha256,
        "identity_reuse_note": (
            "Twenty-model post-release v1 qualification matrix. Every model is frozen and verified by "
            "repository revision, exact GGUF filename, upstream LFS SHA-256, local SHA-256, and byte size. "
            "Scores do not alter the shipped v1.0.0 runtime."
        ),
        "records": compact,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--root", type=Path, default=Path("/mnt/c/AIModels/ExactScopeBench-v1-20"))
    parser.add_argument("--manifest", type=Path, default=ROOT / "target/v1-20-model-acquisition.json")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--write-grounding-inventory", type=Path,
                        help="v1 export path, e.g. benchmarks/v1-grounding-model-inventory-20.json")
    parser.add_argument("--resolve-only", action="store_true")
    parser.add_argument("--freeze-matrix", type=Path)
    args = parser.parse_args()

    matrix_bytes = args.matrix.read_bytes()
    matrix = json.loads(matrix_bytes)
    models = validate_matrix(matrix, require_frozen=not args.resolve_only)

    if args.resolve_only:
        resolved: list[dict] = []
        with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 6))) as pool:
            futures = {pool.submit(resolve_spec, spec): spec["id"] for spec in models}
            for future in as_completed(futures):
                model_id = futures[future]
                record = future.result()
                resolved.append(record)
                print(
                    f"RESOLVED {model_id} {record['requested_file']} {record['bytes']} {record['upstream_sha256']}",
                    flush=True,
                )
        order = {row["id"]: index for index, row in enumerate(models)}
        resolved.sort(key=lambda row: order[row["id"]])
        output = args.freeze_matrix or (ROOT / "target/v1-model-matrix-20-resolved.json")
        frozen = freeze_matrix(matrix, resolved, output)
        print(json.dumps({
            "status": "PASS",
            "mode": "resolve-only",
            "model_count": len(resolved),
            "frozen_matrix": str(output),
            "frozen_matrix_sha256": hashlib.sha256(canonical_json_bytes(frozen)).hexdigest(),
        }, sort_keys=True))
        return 0

    matrix_sha = hashlib.sha256(matrix_bytes).hexdigest()
    args.root.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 6))) as pool:
        futures = {pool.submit(acquire_one, spec, args.root): spec["id"] for spec in models}
        for future in as_completed(futures):
            model_id = futures[future]
            record = future.result()
            records.append(record)
            print(f"READY {model_id} {record['bytes']} {record['acquisition_state']}", flush=True)
    records.sort(key=lambda row: row["id"])

    payload = {
        "format": "exactscope.v1-model-acquisition",
        "format_version": "0.2",
        "matrix_sha256": matrix_sha,
        "matrix_freeze_contract": matrix["selection_policy"].get("freeze_contract"),
        "model_count": len(records),
        "records": records,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.write_grounding_inventory is not None:
        write_grounding_inventory(args.write_grounding_inventory, matrix_sha, records)
    print(json.dumps({
        "status": "PASS",
        "model_count": len(records),
        "total_bytes": sum(record["bytes"] for record in records),
        "manifest": str(args.manifest),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
