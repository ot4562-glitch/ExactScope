#!/usr/bin/env python3
"""Resolve, download, and inventory ExactScope qualification models.

This tool downloads model files only. It does not launch inference, ExactScope,
or any benchmark/qualification workload.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "benchmarks" / "model-downloads.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_matrix(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("format") != "exactscope.benchmark-model-matrix":
        raise SystemExit(f"unsupported model matrix: {path}")
    return data


def all_entries(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    return [*matrix.get("core", []), *matrix.get("optional_product_profile", [])]


def select_entries(matrix: dict[str, Any], selectors: list[str]) -> list[dict[str, Any]]:
    entries = all_entries(matrix)
    by_id = {entry["id"]: entry for entry in entries}
    selected: list[dict[str, Any]] = []
    for selector in selectors:
        if selector == "core":
            selected.extend(matrix.get("core", []))
        elif selector == "optional":
            selected.extend(matrix.get("optional_product_profile", []))
        elif selector in by_id:
            selected.append(by_id[selector])
        else:
            raise SystemExit(f"unknown model selector: {selector}")
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in selected:
        if entry["id"] not in seen:
            seen.add(entry["id"])
            deduped.append(entry)
    return deduped


def print_models(matrix: dict[str, Any]) -> None:
    for group in ("core", "optional_product_profile"):
        print(f"[{group}]")
        for entry in matrix.get(group, []):
            filename = entry.get("file") or "<runtime-specific>"
            print(
                f"  {entry['id']}: {entry['repository']} / {filename} "
                f"({entry['parameters']}, {entry.get('quantization') or 'n/a'})"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("selectors", nargs="*", default=["core"], help="core, optional, or model ids")
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--root", type=Path, default=Path("C:/AIModels/ExactScopeBench"))
    parser.add_argument("--inventory", type=Path, default=None)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    matrix = load_matrix(args.matrix)
    if args.list:
        print_models(matrix)
        return 0

    selected = select_entries(matrix, args.selectors or ["core"])
    if args.dry_run:
        for entry in selected:
            print(f"{entry['id']}: {entry['repository']} / {entry.get('file')}")
        return 0

    try:
        from huggingface_hub import HfApi, hf_hub_download
    except ImportError as exc:
        raise SystemExit(
            "huggingface_hub is required. Run: py -3 -m pip install -r requirements-benchmark.txt"
        ) from exc

    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    inventory_path = args.inventory or root / "model-inventory.json"
    api = HfApi(token=os.environ.get("HF_TOKEN") or None)

    records: list[dict[str, Any]] = []
    for entry in selected:
        filename = entry.get("file")
        record: dict[str, Any] = {
            "id": entry["id"],
            "repository": entry["repository"],
            "requested_file": filename,
            "runtime": entry["runtime"],
            "quantization": entry.get("quantization"),
        }
        if not filename:
            record["status"] = "manual-runtime-specific"
            record["note"] = entry.get("license_note")
            records.append(record)
            print(f"SKIP {entry['id']}: runtime-specific/gated setup; see model matrix")
            continue

        info = api.model_info(entry["repository"])
        revision = info.sha
        model_dir = root / entry["id"]
        model_dir.mkdir(parents=True, exist_ok=True)
        print(f"DOWNLOAD {entry['id']} @ {revision}: {filename}")
        downloaded = Path(
            hf_hub_download(
                repo_id=entry["repository"],
                filename=filename,
                revision=revision,
                local_dir=model_dir,
                token=os.environ.get("HF_TOKEN") or None,
            )
        ).resolve()
        digest = sha256_file(downloaded)
        record.update(
            {
                "status": "ready",
                "resolved_revision": revision,
                "path": str(downloaded),
                "bytes": downloaded.stat().st_size,
                "sha256": digest,
            }
        )
        records.append(record)
        print(f"READY {entry['id']}: {downloaded.stat().st_size} bytes sha256={digest}")

    inventory = {
        "format": "exactscope.model-download-inventory",
        "format_version": "0.1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "matrix": str(args.matrix.resolve()),
        "records": records,
    }
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"inventory: {inventory_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
