#!/usr/bin/env python3
"""Materialize the pinned Kubernetes Pod-operations proxy corpus.

The source is intentionally fetched into target/ only. The repository tracks the
source identity and acquisition logic, not a vendored copy of Kubernetes docs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "benchmarks/kubernetes_ops_proxy_source.json"
DEFAULT_OUT = ROOT / "target/kubernetes-pod-ops-docqa-v0.1/source"


class AcquisitionError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AcquisitionError(f"expected JSON object: {path}")
    return value


def run_git(args: list[str], *, cwd: Path | None = None) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=None if cwd is None else str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise AcquisitionError(
            f"git {' '.join(args)} failed ({proc.returncode}): {proc.stderr.strip()}"
        )
    return proc.stdout.strip()


def title_from_markdown(text: str, fallback: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            if line.startswith("title:"):
                title = line.split(":", 1)[1].strip().strip('"').strip("'")
                if title:
                    return title
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            if title:
                return title
    return fallback


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("format") != "exactscope.public-proxy-source":
        raise AcquisitionError("unexpected source manifest format")
    if manifest.get("development_only") is not True:
        raise AcquisitionError("public proxy must be development-only")
    if manifest.get("qualification_eligible") is not False:
        raise AcquisitionError("public proxy must not be qualification eligible")
    source = manifest.get("source")
    if not isinstance(source, dict):
        raise AcquisitionError("source record missing")
    commit = source.get("commit")
    if not isinstance(commit, str) or len(commit) != 40:
        raise AcquisitionError("source commit must be a 40-character git SHA")
    roots = manifest.get("include_roots")
    if not isinstance(roots, list) or not roots or not all(isinstance(v, str) and v for v in roots):
        raise AcquisitionError("include_roots must be a non-empty string list")


def acquire(manifest_path: Path, out: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    validate_manifest(manifest)
    source = manifest["source"]
    commit = source["commit"]
    repo = source["repository"]
    roots: list[str] = manifest["include_roots"]
    suffixes = tuple(manifest.get("include_suffixes", [".md"]))
    excluded = set(manifest.get("exclude_names", []))

    if out.exists():
        raise AcquisitionError(f"output already exists: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="exactscope-k8s-proxy-") as td:
        checkout = Path(td) / "checkout"
        checkout.mkdir()
        run_git(["init"], cwd=checkout)
        run_git(["remote", "add", "origin", repo], cwd=checkout)
        run_git(["sparse-checkout", "init", "--cone"], cwd=checkout)
        run_git(["sparse-checkout", "set", *roots], cwd=checkout)
        run_git(["fetch", "--depth=1", "origin", commit], cwd=checkout)
        run_git(["checkout", "--detach", "FETCH_HEAD"], cwd=checkout)
        actual = run_git(["rev-parse", "HEAD"], cwd=checkout)
        if actual != commit:
            raise AcquisitionError(f"commit mismatch: expected {commit}, got {actual}")

        files: list[dict[str, Any]] = []
        corpus_documents: list[dict[str, Any]] = []
        materialized = out / "materialized"
        materialized.mkdir(parents=True)

        for root in roots:
            base = checkout / root
            if not base.is_dir():
                raise AcquisitionError(f"include root missing at pinned commit: {root}")
            for path in sorted(p for p in base.rglob("*") if p.is_file()):
                if path.name in excluded:
                    continue
                if suffixes and path.suffix not in suffixes:
                    continue
                rel = path.relative_to(checkout).as_posix()
                raw = path.read_bytes()
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise AcquisitionError(f"non-UTF8 markdown: {rel}") from exc
                dest = materialized / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(raw)
                digest = sha256_bytes(raw)
                title = title_from_markdown(text, path.stem)
                files.append(
                    {
                        "path": rel,
                        "sha256": digest,
                        "bytes": len(raw),
                        "title": title,
                    }
                )
                corpus_documents.append(
                    {
                        "id": rel,
                        "path": rel,
                        "title": title,
                        "text": text,
                        "sha256": digest,
                        "source_commit": commit,
                        "authority": "authoritative",
                    }
                )

    if len(files) < 20:
        raise AcquisitionError(f"proxy corpus unexpectedly small: {len(files)} files")

    source_manifest_sha = sha256_file(manifest_path)
    snapshot = {
        "format": "exactscope.public-proxy-source-snapshot",
        "format_version": "0.1",
        "proxy_id": manifest["proxy_id"],
        "development_only": True,
        "qualification_eligible": False,
        "source_manifest_sha256": source_manifest_sha,
        "repository": source["repository_full_name"],
        "commit": commit,
        "license_spdx": source["license_spdx"],
        "include_roots": roots,
        "file_count": len(files),
        "total_bytes": sum(int(row["bytes"]) for row in files),
        "files": files,
    }
    (out / "source-snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    corpus = {
        "format": "exactscope.public-proxy-corpus-index",
        "format_version": "0.1",
        "proxy_id": manifest["proxy_id"],
        "source_snapshot_sha256": sha256_file(out / "source-snapshot.json"),
        "documents": corpus_documents,
    }
    (out / "corpus-index.json").write_text(
        json.dumps(corpus, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    result = {
        "status": "SOURCE_SNAPSHOT_MATERIALIZED",
        "proxy_id": manifest["proxy_id"],
        "commit": commit,
        "file_count": len(files),
        "total_bytes": snapshot["total_bytes"],
        "source_snapshot_sha256": sha256_file(out / "source-snapshot.json"),
        "corpus_index_sha256": sha256_file(out / "corpus-index.json"),
        "output": str(out),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    out = args.output if args.output.is_absolute() else ROOT / args.output
    result = acquire(manifest.resolve(), out.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
