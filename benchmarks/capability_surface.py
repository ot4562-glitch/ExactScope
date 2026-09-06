#!/usr/bin/env python3
"""Stdlib-only verifier/loader for packaged ExactScope evaluation capabilities."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MODEL_SURFACE_ASSETS = {
    "prompt-fragment.txt": ("prompt", "exactscope.prompt-fragment", "0.1"),
    "xs-calc.gbnf": ("grammar", "exactscope.xs-calc.gbnf", "0.1"),
    "xs-calc.tool.json": ("tool-schema", "exactscope.xs-calc.tool", "0.1"),
    "xs-eval.gbnf": ("grammar", "exactscope.xs-eval.gbnf", "0.1"),
    "xs-eval.tool.json": ("tool-schema", "exactscope.xs-eval.tool", "0.1"),
}


class CapabilityError(RuntimeError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    return digest(path.read_bytes())


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CapabilityError(f"cannot read JSON {path}: {exc}") from exc


@dataclass(frozen=True)
class CapabilitySurface:
    root: Path
    manifest: dict[str, Any]
    profile: dict[str, Any]
    contract: dict[str, Any]
    catalog: dict[str, Any]
    prompt: str
    tools: dict[str, dict[str, Any]]
    grammars: dict[str, str]
    bundle_sha256: str
    surface_contract_sha256: str
    artifact_sha256: str

    @property
    def operations(self) -> list[str]:
        return list(self.profile["runtime_surface"]["xs_eval"]["operations"])

    @property
    def calc_enabled(self) -> bool:
        return self.profile["runtime_surface"]["xs_calc"]["enabled"] is True


def _verify_inventory(root: Path, manifest: dict[str, Any]) -> None:
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise CapabilityError("capability manifest has no file inventory")
    expected = set(files) | {"manifest.json", "bundle-sha256.txt"}
    actual = {path.name for path in root.iterdir() if path.is_file()}
    if any(path.is_dir() or path.is_symlink() for path in root.iterdir()):
        raise CapabilityError("capability bundle may contain regular files only")
    if actual != expected:
        raise CapabilityError("capability file inventory mismatch")
    for name, expected_digest in files.items():
        if not isinstance(name, str) or Path(name).name != name:
            raise CapabilityError(f"invalid capability filename: {name!r}")
        if not isinstance(expected_digest, str) or len(expected_digest) != 64:
            raise CapabilityError(f"invalid capability digest: {name}")
        if digest_file(root / name) != expected_digest:
            raise CapabilityError(f"capability digest mismatch: {name}")


def _verify_surface_contract(
    root: Path,
    manifest: dict[str, Any],
    profile: dict[str, Any],
    catalog: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    bindings = profile.get("bindings") if isinstance(profile, dict) else None
    expected_digest = bindings.get("surface_contract_sha256") if isinstance(bindings, dict) else None
    path = root / "surface-contract.json"
    if not isinstance(expected_digest, str) or not path.is_file():
        raise CapabilityError("capability has no explicit model-surface contract")
    if digest_file(path) != expected_digest:
        raise CapabilityError("model-surface contract digest mismatch")
    contract = load_json(path)
    if (
        contract.get("format") != "exactscope.model-surface.contract"
        or contract.get("format_version") != "0.1"
        or contract.get("negotiation") != "exact-version-and-digest"
    ):
        raise CapabilityError("unsupported model-surface contract")
    if contract.get("profile") != {
        "id": profile.get("profile_id"),
        "revision": profile.get("profile_revision"),
        "domain": profile.get("domain"),
    }:
        raise CapabilityError("model-surface profile identity mismatch")
    hotset = contract.get("hotset")
    if hotset != {
        "format": catalog.get("format"),
        "format_version": catalog.get("format_version"),
        "binding_sha256": catalog.get("binding_sha256"),
    }:
        raise CapabilityError("model-surface hot-set identity mismatch")
    if contract.get("abi_revision") != bindings.get("abi_revision"):
        raise CapabilityError("model-surface ABI identity mismatch")
    assets = contract.get("assets")
    if not isinstance(assets, list) or not assets:
        raise CapabilityError("model-surface asset list is empty")
    expected_names = sorted(name for name in MODEL_SURFACE_ASSETS if name in manifest["files"])
    actual_names = [entry.get("path") for entry in assets if isinstance(entry, dict)]
    if actual_names != expected_names or len(actual_names) != len(assets):
        raise CapabilityError("model-surface asset inventory mismatch")
    for entry in assets:
        name = entry["path"]
        kind, contract_id, version = MODEL_SURFACE_ASSETS[name]
        if (entry.get("kind"), entry.get("contract_id"), entry.get("contract_version")) != (
            kind,
            contract_id,
            version,
        ):
            raise CapabilityError(f"model-surface contract version mismatch: {name}")
        if entry.get("sha256") != manifest["files"][name]:
            raise CapabilityError(f"model-surface digest binding mismatch: {name}")
    return contract, expected_digest


def load_capability(root: Path, *, corpus: Path | None = None) -> CapabilitySurface:
    root = root.resolve()
    manifest_path = root / "manifest.json"
    detached_path = root / "bundle-sha256.txt"
    if not manifest_path.is_file() or not detached_path.is_file():
        raise CapabilityError("capability is missing manifest.json or bundle-sha256.txt")
    manifest_bytes = manifest_path.read_bytes()
    detached = detached_path.read_text(encoding="ascii").strip()
    if digest(manifest_bytes) != detached:
        raise CapabilityError("capability manifest detached digest mismatch")
    manifest = load_json(manifest_path)
    if manifest.get("format") != "exactscope.capability.bundle" or manifest.get("format_version") != "0.1":
        raise CapabilityError("unsupported capability manifest")
    _verify_inventory(root, manifest)

    profile = load_json(root / "profile.json")
    catalog = load_json(root / "catalog.json")
    surface = profile.get("runtime_surface") if isinstance(profile, dict) else None
    if not isinstance(surface, dict):
        raise CapabilityError("capability runtime surface is missing")
    selected = surface.get("xs_eval", {}).get("operations")
    if not isinstance(selected, list) or not selected:
        raise CapabilityError("capability must expose xs_eval operations")
    catalog_operations = catalog.get("operations") if isinstance(catalog, dict) else None
    if not isinstance(catalog_operations, list):
        raise CapabilityError("capability catalog operations are invalid")
    catalog_keys = [entry.get("op") for entry in catalog_operations if isinstance(entry, dict)]
    if len(catalog_keys) != len(catalog_operations) or selected != catalog_keys:
        raise CapabilityError("capability profile/catalog operation order mismatch")
    bindings = profile.get("bindings")
    if not isinstance(bindings, dict) or bindings.get("hotset_sha256") != catalog.get("binding_sha256"):
        raise CapabilityError("capability hot-set binding mismatch")

    runtime = root / "runtime.wasm"
    artifact_sha = bindings.get("artifact_sha256")
    if not isinstance(artifact_sha, str) or not runtime.is_file() or digest_file(runtime) != artifact_sha:
        raise CapabilityError("capability runtime artifact binding mismatch")
    measurements = manifest.get("artifact_measurements")
    if not isinstance(measurements, dict) or measurements.get("bytes") != runtime.stat().st_size:
        raise CapabilityError("capability runtime byte measurement mismatch")

    contract, contract_sha = _verify_surface_contract(root, manifest, profile, catalog)
    calc_enabled = surface.get("xs_calc", {}).get("enabled") is True
    expected_tools = {"xs-eval"} | ({"xs-calc"} if calc_enabled else set())
    tools: dict[str, dict[str, Any]] = {}
    grammars: dict[str, str] = {}
    for lane in expected_tools:
        tool_path = root / f"{lane}.tool.json"
        grammar_path = root / f"{lane}.gbnf"
        if not tool_path.is_file() or not grammar_path.is_file():
            raise CapabilityError(f"capability is missing {lane} model surface")
        tool = load_json(tool_path)
        function = tool.get("function") if isinstance(tool, dict) else None
        if not isinstance(function, dict) or function.get("name") != lane.replace("-", "_"):
            raise CapabilityError(f"invalid {lane} tool schema")
        tools[lane.replace("-", "_")] = tool
        grammars[lane.replace("-", "_")] = grammar_path.read_text(encoding="utf-8")
    if not calc_enabled and ((root / "xs-calc.tool.json").exists() or (root / "xs-calc.gbnf").exists()):
        raise CapabilityError("semantic-only capability unexpectedly exposes xs_calc")

    prompt = (root / "prompt-fragment.txt").read_text(encoding="utf-8").strip()
    if not prompt:
        raise CapabilityError("capability prompt fragment is empty")
    if corpus is not None:
        mapping = root / "benchmark-mapping.jsonl"
        evidence = profile.get("evidence") if isinstance(profile, dict) else None
        expected_mapping = evidence.get("benchmark_mapping_sha256") if isinstance(evidence, dict) else None
        if not mapping.is_file() or not isinstance(expected_mapping, str):
            raise CapabilityError("capability lacks benchmark mapping evidence")
        if digest_file(mapping) != expected_mapping or digest_file(corpus) != expected_mapping:
            raise CapabilityError("capability benchmark mapping differs from selected corpus")

    return CapabilitySurface(
        root=root,
        manifest=manifest,
        profile=profile,
        contract=contract,
        catalog=catalog,
        prompt=prompt,
        tools=tools,
        grammars=grammars,
        bundle_sha256=detached,
        surface_contract_sha256=contract_sha,
        artifact_sha256=artifact_sha,
    )
