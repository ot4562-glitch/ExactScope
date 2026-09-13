#!/usr/bin/env python3
"""Fast attachable llama.cpp runtime identity experiment.

One read-only GET /props plus at most 128 KiB of local model-file sampling produces a
cheap cache identity. This is deliberately not advertised as a full model SHA-256.
The stable adapter can keep its explicit --model-key boundary until this experiment is
qualified.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import ipaddress
import json
from pathlib import Path
import sys
from typing import Any
import urllib.parse

sys.dont_write_bytecode = True
MAX_PROPS_BYTES = 1024 * 1024
FILE_SAMPLE_BYTES = 64 * 1024
IDENTITY_VERSION = "llama.cpp-fast-runtime-identity-v1"
_VOLATILE_PROP_KEYS = frozenset({"id", "id_task", "is_processing", "is_sleeping"})


class RuntimeIdentityError(RuntimeError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stable_props(value: Any) -> Any:
    """Remove known request/slot state while conservatively retaining launch settings."""
    if isinstance(value, dict):
        return {key: _stable_props(item) for key, item in sorted(value.items()) if key not in _VOLATILE_PROP_KEYS}
    if isinstance(value, list):
        return [_stable_props(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise RuntimeIdentityError("/props contains unsupported JSON data")


def _loopback_endpoint(base_url: str) -> tuple[str, int]:
    if not isinstance(base_url, str) or not base_url.strip():
        raise RuntimeIdentityError("base_url must be nonempty")
    parsed = urllib.parse.urlparse(base_url.strip().rstrip("/"))
    if parsed.scheme != "http" or parsed.hostname is None:
        raise RuntimeIdentityError("runtime identity probe accepts only loopback HTTP")
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise RuntimeIdentityError("invalid llama.cpp base URL")
    try:
        host = ipaddress.ip_address(parsed.hostname)
        port = parsed.port or 80
    except ValueError as exc:
        raise RuntimeIdentityError("invalid llama.cpp base URL") from exc
    if not host.is_loopback:
        raise RuntimeIdentityError("runtime identity probe accepts only a literal loopback IP")
    return parsed.hostname, port


def fetch_props(base_url: str, *, model: str | None = None, timeout_seconds: float = 3.0) -> dict[str, Any]:
    """Fetch bounded read-only llama.cpp metadata without environment proxy handling."""
    host, port = _loopback_endpoint(base_url)
    if model is not None and (not isinstance(model, str) or not model):
        raise RuntimeIdentityError("model must be nonempty text")
    if type(timeout_seconds) not in {int, float} or timeout_seconds <= 0:
        raise RuntimeIdentityError("timeout_seconds must be positive")
    path = "/props"
    if model is not None:
        path += "?" + urllib.parse.urlencode({"model": model})
    connection = http.client.HTTPConnection(host, port, timeout=timeout_seconds)
    try:
        connection.request("GET", path, headers={"Accept": "application/json"})
        response = connection.getresponse()
        status = response.status
        raw = response.read(MAX_PROPS_BYTES + 1)
    except (http.client.HTTPException, TimeoutError, OSError) as exc:
        raise RuntimeIdentityError(f"llama.cpp /props failed: {exc}") from exc
    finally:
        connection.close()
    if len(raw) > MAX_PROPS_BYTES:
        raise RuntimeIdentityError("llama.cpp /props exceeds bounded size")
    if not 200 <= status < 300:
        raise RuntimeIdentityError(f"llama.cpp /props HTTP {status}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeIdentityError("llama.cpp /props returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeIdentityError("llama.cpp /props returned a non-object")
    return value


def fast_file_fingerprint(model_path: Any) -> dict[str, Any] | None:
    """Sample head/tail only for an absolute local model path returned by llama.cpp."""
    if not isinstance(model_path, str) or not model_path:
        return None
    path = Path(model_path)
    if not path.is_absolute() or not path.is_file():
        return None
    try:
        stat = path.stat()
        size = stat.st_size
        with path.open("rb") as handle:
            head = handle.read(FILE_SAMPLE_BYTES)
            if size > FILE_SAMPLE_BYTES:
                handle.seek(max(0, size - FILE_SAMPLE_BYTES))
                tail = handle.read(FILE_SAMPLE_BYTES)
            else:
                tail = b""
    except OSError:
        return None
    sample_digest = _sha(
        b"exactscope-fast-file-v1\0"
        + str(size).encode("ascii")
        + b"\0"
        + str(getattr(stat, "st_mtime_ns", 0)).encode("ascii")
        + b"\0"
        + head
        + b"\0"
        + tail
    )
    return {
        "size_bytes": size,
        "mtime_ns": getattr(stat, "st_mtime_ns", 0),
        "sample_sha256": sample_digest,
        "sampled_bytes_max": FILE_SAMPLE_BYTES * 2,
    }


def discover_runtime_identity(
    base_url: str,
    *,
    model: str | None = None,
    timeout_seconds: float = 3.0,
) -> dict[str, Any]:
    """Return a cheap privacy-preserving identity candidate and its trust grade."""
    props = fetch_props(base_url, model=model, timeout_seconds=timeout_seconds)
    stable_props = _stable_props(props)
    props_digest = _sha(_canonical(stable_props))
    file_probe = fast_file_fingerprint(props.get("model_path"))
    evidence = {
        "identity_version": IDENTITY_VERSION,
        "props_sha256": props_digest,
        "model_file": file_probe,
    }
    model_key = "auto-llamacpp-v1:" + _sha(_canonical(evidence))
    strong_metadata = isinstance(props.get("build_info"), str) and isinstance(props.get("chat_template"), str)
    cache_lookup_candidate = bool(strong_metadata and file_probe is not None)
    return {
        "identity_version": IDENTITY_VERSION,
        "model_key": model_key,
        "props_sha256": props_digest,
        "model_file_sample_sha256": file_probe["sample_sha256"] if file_probe else None,
        "model_file_size_bytes": file_probe["size_bytes"] if file_probe else None,
        "sampled_model_bytes_max": file_probe["sampled_bytes_max"] if file_probe else 0,
        "cache_lookup_candidate": cache_lookup_candidate,
        "persistent_cache_ok": False,
        "confidence": "metadata+local-file-sample-candidate" if cache_lookup_candidate else "metadata-only-session-scope",
        "required_before_persistent_reuse": "full-model-identity-or-semantic-revalidation",
        "full_model_sha256": False,
        "network_model_requests": 0,
        "metadata_requests": 1,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--model")
    parser.add_argument("--timeout-seconds", type=float, default=3.0)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(discover_runtime_identity(
            args.base_url,
            model=args.model,
            timeout_seconds=args.timeout_seconds,
        ), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0
    except (RuntimeIdentityError, OSError, ValueError) as exc:
        print(f"ExactScope llama.cpp runtime identity: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
