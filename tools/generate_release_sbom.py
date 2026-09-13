#!/usr/bin/env python3
"""Generate a deterministic CycloneDX SBOM for the native release graph."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TARGET_PACKAGE = "exactscope-cabi"


class SbomError(RuntimeError):
    pass


def cargo_metadata() -> dict[str, Any]:
    result = subprocess.run(
        ["cargo", "metadata", "--format-version", "1"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SbomError("cargo metadata failed:\n" + result.stderr)
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise SbomError("cargo metadata returned invalid JSON")
    return value


def normal_dependency_graph(metadata: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    packages = {package["id"]: package for package in metadata.get("packages", [])}
    resolve = metadata.get("resolve") or {}
    nodes = {node["id"]: node for node in resolve.get("nodes", [])}
    roots = [package_id for package_id, package in packages.items() if package.get("name") == TARGET_PACKAGE]
    if len(roots) != 1:
        raise SbomError(f"expected one {TARGET_PACKAGE!r} package, found {len(roots)}")

    visited: set[str] = set()
    edges: dict[str, list[str]] = {}
    stack = [roots[0]]
    while stack:
        package_id = stack.pop()
        if package_id in visited:
            continue
        visited.add(package_id)
        node = nodes.get(package_id)
        if node is None:
            raise SbomError(f"cargo resolve node missing: {package_id}")
        normal: list[str] = []
        for dep in node.get("deps", []):
            dep_kinds = dep.get("dep_kinds", [])
            if not any(kind.get("kind") is None for kind in dep_kinds):
                continue
            dep_id = dep["pkg"]
            normal.append(dep_id)
            stack.append(dep_id)
        edges[package_id] = sorted(set(normal))

    selected = [packages[package_id] for package_id in visited]
    selected.sort(key=lambda package: (package["name"], package["version"], package["id"]))
    return selected, edges


def purl(package: dict[str, Any]) -> str:
    return f"pkg:cargo/{package['name']}@{package['version']}"


def build_sbom(version: str, source_commit: str) -> dict[str, Any]:
    metadata = cargo_metadata()
    packages, edges = normal_dependency_graph(metadata)
    by_id = {package["id"]: package for package in packages}
    target = next(package for package in packages if package["name"] == TARGET_PACKAGE)
    if target["version"] != version:
        raise SbomError(f"release version {version} does not match {TARGET_PACKAGE} {target['version']}")

    components: list[dict[str, Any]] = []
    for package in packages:
        component: dict[str, Any] = {
            "type": "library",
            "bom-ref": purl(package),
            "name": package["name"],
            "version": package["version"],
            "purl": purl(package),
        }
        expression = package.get("license")
        if isinstance(expression, str) and expression.strip():
            component["licenses"] = [{"expression": expression}]
        components.append(component)

    dependencies: list[dict[str, Any]] = []
    for package in packages:
        dependencies.append({
            "ref": purl(package),
            "dependsOn": sorted(
                purl(by_id[dep_id])
                for dep_id in edges.get(package["id"], [])
                if dep_id in by_id
            ),
        })

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "bom-ref": f"pkg:generic/exactscope@{version}",
                "name": "ExactScope native grounding runtime",
                "version": version,
                "properties": [
                    {"name": "exactscope:source-commit", "value": source_commit},
                    {"name": "exactscope:stable-surface", "value": "linux-x86_64-native-grounding-c-abi-xsgi"},
                    {"name": "exactscope:host-integration-status", "value": "experimental-reference"},
                    {"name": "exactscope:qualification-architecture-status", "value": "source-reference-only"},
                ],
            }
        },
        "components": components,
        "dependencies": dependencies,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    sbom = build_sbom(args.version, args.source_commit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(sbom, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Wrote CycloneDX SBOM: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
