#!/usr/bin/env python3
"""Deterministic pre-inference model-envelope selection for llama.cpp-compatible runtimes."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

MODEL_INTERFACES = ("auto", "constrained_json", "native_tools")
REQUIRED_NATIVE_CAPABILITIES = (
    "supports_tools",
    "supports_tool_calls",
    "supports_object_arguments",
)
OPTIONAL_CAPABILITIES = ("supports_parallel_tool_calls",)


class InterfaceSelectionError(RuntimeError):
    """Runtime metadata is missing, malformed, or incompatible with a requested envelope."""


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _server_root(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1"):
        normalized = normalized[:-3]
    return normalized.rstrip("/")


def fetch_runtime_props(base_url: str, timeout: float) -> dict[str, Any]:
    """Fetch llama.cpp /props without invoking model inference."""
    if timeout <= 0:
        raise InterfaceSelectionError("runtime capability probe timeout must be positive")
    request = urllib.request.Request(
        f"{_server_root(base_url)}/props",
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise InterfaceSelectionError(f"llama.cpp /props HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise InterfaceSelectionError(f"cannot reach llama.cpp /props: {exc}") from exc
    try:
        document = json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise InterfaceSelectionError(f"llama.cpp /props is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise InterfaceSelectionError("llama.cpp /props must return a JSON object")
    return document


def _find_first(document: Any, key: str, path: str = "$") -> tuple[Any, str] | tuple[None, None]:
    if isinstance(document, dict):
        if key in document:
            return document[key], f"{path}.{key}"
        for child_key in sorted(document):
            value, found = _find_first(document[child_key], key, f"{path}.{child_key}")
            if found is not None:
                return value, found
    elif isinstance(document, list):
        for index, child in enumerate(document):
            value, found = _find_first(child, key, f"{path}[{index}]")
            if found is not None:
                return value, found
    return None, None


def _bool_capability(props: dict[str, Any], key: str) -> tuple[bool | None, str | None]:
    value, path = _find_first(props, key)
    if isinstance(value, bool):
        return value, path
    return None, path


def _string_digest(props: dict[str, Any], key: str) -> tuple[str | None, str | None]:
    value, path = _find_first(props, key)
    if isinstance(value, str):
        return sha256_bytes(value.encode("utf-8")), path
    return None, path


def normalize_runtime_props(props: dict[str, Any]) -> dict[str, Any]:
    """Reduce runtime metadata to the interface facts ExactScope is allowed to use."""
    if not isinstance(props, dict):
        raise InterfaceSelectionError("runtime props must be an object")
    source_bytes = canonical(props)
    capabilities: dict[str, bool | None] = {}
    paths: dict[str, str | None] = {}
    for key in (*REQUIRED_NATIVE_CAPABILITIES, *OPTIONAL_CAPABILITIES):
        capabilities[key], paths[key] = _bool_capability(props, key)
    chat_template_sha256, chat_template_path = _string_digest(props, "chat_template")
    tool_template_sha256, tool_template_path = _string_digest(props, "chat_template_tool_use")
    return {
        "format": "exactscope.llama-cpp.runtime-capabilities",
        "format_version": "0.1",
        "props_sha256": sha256_bytes(source_bytes),
        "capabilities": capabilities,
        "source_paths": paths,
        "chat_template_sha256": chat_template_sha256,
        "chat_template_source_path": chat_template_path,
        "tool_template_sha256": tool_template_sha256,
        "tool_template_source_path": tool_template_path,
    }


def native_tool_support(capability_record: dict[str, Any]) -> tuple[bool, list[str]]:
    capabilities = capability_record.get("capabilities")
    if not isinstance(capabilities, dict):
        raise InterfaceSelectionError("normalized runtime capability record is malformed")
    missing = [key for key in REQUIRED_NATIVE_CAPABILITIES if capabilities.get(key) is not True]
    return not missing, missing


def select_model_interface(
    requested: str,
    capability_record: dict[str, Any] | None,
) -> dict[str, Any]:
    """Resolve one envelope before inference; never use model family names or output-driven fallback."""
    if requested not in MODEL_INTERFACES:
        raise InterfaceSelectionError(f"unsupported model interface: {requested}")
    if requested == "constrained_json":
        if capability_record is None:
            missing = list(REQUIRED_NATIVE_CAPABILITIES)
        else:
            _, missing = native_tool_support(capability_record)
        resolved = "constrained_json"
        reason = "explicit constrained_json request; native capability probe not required"
    else:
        if capability_record is None:
            raise InterfaceSelectionError(f"{requested} requires runtime capability metadata")
        native_supported, missing = native_tool_support(capability_record)
        if requested == "auto":
            resolved = "native_tools" if native_supported else "constrained_json"
            reason = (
                "required native tool capabilities proven"
                if native_supported
                else "native tool capabilities absent or unknown"
            )
        else:
            if not native_supported:
                raise InterfaceSelectionError(
                    "native_tools requested but runtime does not prove: " + ", ".join(missing)
                )
            resolved = "native_tools"
            reason = "explicit native_tools request and required capabilities proven"
    return {
        "requested": requested,
        "resolved": resolved,
        "selection_phase": "pre-inference",
        "selection_reason": reason,
        "fallback": "none",
        "required_native_capabilities": list(REQUIRED_NATIVE_CAPABILITIES),
        "missing_or_unproven_native_capabilities": missing,
        "runtime_capabilities": capability_record,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe llama.cpp model-interface capabilities without running inference."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--base-url", help="OpenAI-compatible base URL, usually http://127.0.0.1:8080/v1")
    source.add_argument("--props-file", type=Path, help="Saved llama.cpp /props JSON for offline inspection")
    parser.add_argument("--model-interface", choices=MODEL_INTERFACES, default="auto")
    parser.add_argument("--timeout", type=float, default=5.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.props_file is not None:
            document = json.loads(args.props_file.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise InterfaceSelectionError("props file must contain a JSON object")
        else:
            document = fetch_runtime_props(args.base_url, args.timeout)
        record = normalize_runtime_props(document)
        selection = select_model_interface(args.model_interface, record)
    except (InterfaceSelectionError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ExactScope llama.cpp interface probe: FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(selection, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
