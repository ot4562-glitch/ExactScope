#!/usr/bin/env python3
"""Build a deterministic, detached ExactScope portable runtime-amplifier zipapp.

This experiment packages only the standard-library Python amplifier path. It does not
change or replace the stable native grounding bundle and it embeds no model or corpus.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FORMAT = "exactscope.runtime-amplifier.pyz"
FORMAT_VERSION = "0.1"
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)

PAYLOAD = {
    "grounding_answer_contract.py": ROOT / "tools/grounding_answer_contract.py",
    "grounding_canonical.py": ROOT / "tools/grounding_canonical.py",
    "grounding_corpus.py": ROOT / "tools/grounding_corpus.py",
    "grounding_engine.py": ROOT / "tools/grounding_engine.py",
    "grounding_match.py": ROOT / "tools/grounding_match.py",
    "grounding_projection.py": ROOT / "tools/grounding_projection.py",
    "grounding_runtime.py": ROOT / "tools/grounding_runtime.py",
    "grounding_v1_surface.py": ROOT / "tools/grounding_v1_surface.py",
    "grounding_v1.py": ROOT / "adapters/openai-compatible/grounding_v1.py",
    "surface.py": ROOT / "adapters/openai-compatible/surface.py",
    "transport.py": ROOT / "adapters/openai-compatible/transport.py",
}

MAIN = b"from grounding_v1 import main\nraise SystemExit(main())\n"


class PortablePackageError(RuntimeError):
    pass


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(output: Path) -> dict[str, object]:
    """Build one deterministic flat zipapp so imports work on Windows/macOS/Linux."""
    if output.exists():
        raise PortablePackageError("output already exists")
    if output.suffix.lower() != ".pyz":
        raise PortablePackageError("portable amplifier output must end in .pyz")

    files: dict[str, bytes] = {"__main__.py": MAIN}
    for archive_name, source in PAYLOAD.items():
        if not source.is_file():
            raise PortablePackageError(f"missing portable amplifier source: {source.relative_to(ROOT)}")
        files[archive_name] = source.read_bytes()

    manifest = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "dependency_policy": "python-standard-library-only",
        "models_included": 0,
        "corpora_included": 0,
        "entrypoint": "grounding_v1:main",
        "files": {name: _digest(data) for name, data in sorted(files.items())},
    }
    files["portable-manifest.json"] = json.dumps(
        manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8") + b"\n"

    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name in sorted(files):
                archive.writestr(_zip_info(name), files[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    except OSError as exc:
        raise PortablePackageError(f"cannot build portable amplifier: {exc}") from exc

    raw = output.read_bytes()
    return {
        "status": "PASS",
        "format": FORMAT,
        "output": str(output),
        "bytes": len(raw),
        "sha256": _digest(raw),
        "python_files": sum(name.endswith(".py") for name in files),
        "third_party_python_dependencies": 0,
        "models_included": 0,
        "corpora_included": 0,
    }


def verify(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise PortablePackageError("portable amplifier does not exist")
    try:
        with zipfile.ZipFile(path, "r") as archive:
            names = archive.namelist()
            if names != sorted(names) or len(names) != len(set(names)):
                raise PortablePackageError("portable amplifier inventory is noncanonical")
            if "portable-manifest.json" not in names or "__main__.py" not in names:
                raise PortablePackageError("portable amplifier is missing required metadata/entrypoint")
            manifest = json.loads(archive.read("portable-manifest.json"))
            expected_names = sorted({"__main__.py", *PAYLOAD, "portable-manifest.json"})
            if names != expected_names:
                raise PortablePackageError("portable amplifier payload drift")
            if not isinstance(manifest, dict) or manifest.get("format") != FORMAT or manifest.get("format_version") != FORMAT_VERSION:
                raise PortablePackageError("portable amplifier manifest identity drift")
            expected_files = manifest.get("files")
            if not isinstance(expected_files, dict) or set(expected_files) != set(names) - {"portable-manifest.json"}:
                raise PortablePackageError("portable amplifier manifest inventory drift")
            for name, digest in expected_files.items():
                if not isinstance(digest, str) or digest != _digest(archive.read(name)):
                    raise PortablePackageError(f"portable amplifier digest mismatch: {name}")
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError, KeyError) as exc:
        if isinstance(exc, PortablePackageError):
            raise
        raise PortablePackageError(f"cannot verify portable amplifier: {exc}") from exc
    raw = path.read_bytes()
    return {"status": "PASS", "format": FORMAT, "bytes": len(raw), "sha256": _digest(raw)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--output", type=Path, required=True)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    try:
        result = build(args.output) if args.command == "build" else verify(args.path)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0
    except (PortablePackageError, OSError, ValueError) as exc:
        print(f"ExactScope portable amplifier package: FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
