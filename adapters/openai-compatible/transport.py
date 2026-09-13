#!/usr/bin/env python3
"""Tiny dependency-free transport for OpenAI-compatible chat endpoints.

This is an experimental portability slice. It does not own grounding, routing,
constraint semantics, retries, authentication storage, or backend detection.
"""
from __future__ import annotations

from dataclasses import dataclass
import http.client
import json
import urllib.parse
from typing import Any

MAX_HTTP_RESPONSE_BYTES = 1024 * 1024
MAX_AUTHORIZATION_BYTES = 16 * 1024


class TransportError(RuntimeError):
    pass


class HTTPStatusError(TransportError):
    def __init__(self, status: int, detail: str) -> None:
        self.status = status
        self.detail = detail
        super().__init__(f"OpenAI-compatible HTTP {status}: {detail}")


@dataclass(frozen=True, slots=True)
class PreparedEndpoint:
    """URL parsing and endpoint-path construction paid once on the cold path."""

    scheme: str
    host: str
    port: int
    chat_path: str

    def _json_request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None,
        *,
        authorization: str | None,
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> dict[str, Any]:
        if authorization is not None:
            if not isinstance(authorization, str) or not authorization or any(ch in authorization for ch in "\r\n"):
                raise TransportError("authorization must be nonempty header text without line breaks")
            if len(authorization.encode("utf-8")) > MAX_AUTHORIZATION_BYTES:
                raise TransportError("authorization header exceeds bounded size")
        if type(max_response_bytes) is not int or max_response_bytes < 1:
            raise TransportError("max_response_bytes must be a positive integer")
        if type(timeout_seconds) not in {int, float} or timeout_seconds <= 0:
            raise TransportError("timeout_seconds must be positive")

        body = None if payload is None else json.dumps(
            payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if authorization is not None:
            headers["Authorization"] = authorization
        connection_type = http.client.HTTPSConnection if self.scheme == "https" else http.client.HTTPConnection
        connection = connection_type(self.host, self.port, timeout=timeout_seconds)
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            status = response.status
            raw = response.read(max_response_bytes + 1)
        except (http.client.HTTPException, TimeoutError, OSError) as exc:
            raise TransportError(f"OpenAI-compatible request failed: {exc}") from exc
        finally:
            connection.close()
        if len(raw) > max_response_bytes:
            raise TransportError("OpenAI-compatible response exceeds bounded size")
        if not 200 <= status < 300:
            raise HTTPStatusError(status, raw.decode("utf-8", errors="replace"))
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TransportError("OpenAI-compatible endpoint returned invalid JSON") from exc
        if not isinstance(value, dict):
            raise TransportError("OpenAI-compatible endpoint returned a non-object response")
        return value

    def request(
        self,
        payload: dict[str, Any],
        *,
        authorization: str | None = None,
        timeout_seconds: float = 60.0,
        max_response_bytes: int = MAX_HTTP_RESPONSE_BYTES,
    ) -> dict[str, Any]:
        return self._json_request(
            "POST",
            self.chat_path,
            payload,
            authorization=authorization,
            timeout_seconds=timeout_seconds,
            max_response_bytes=max_response_bytes,
        )

    def models(
        self,
        *,
        authorization: str | None = None,
        timeout_seconds: float = 5.0,
        max_response_bytes: int = MAX_HTTP_RESPONSE_BYTES,
    ) -> dict[str, Any]:
        base_path = self.chat_path[: -len("/chat/completions")]
        return self._json_request(
            "GET",
            base_path + "/models",
            None,
            authorization=authorization,
            timeout_seconds=timeout_seconds,
            max_response_bytes=max_response_bytes,
        )


def prepare_endpoint(base_url: str) -> PreparedEndpoint:
    """Prepare `/chat/completions` from a v1/v3-style base or an explicit full path."""
    if not isinstance(base_url, str) or not base_url.strip():
        raise TransportError("base_url must be nonempty")
    parsed = urllib.parse.urlparse(base_url.strip().rstrip("/"))
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        raise TransportError("base_url must use http or https")
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise TransportError("base_url must not contain credentials, query, or fragment")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise TransportError("base_url has an invalid port") from exc
    path = parsed.path.rstrip("/")
    chat_path = path if path.endswith("/chat/completions") else path + "/chat/completions"
    if not chat_path.startswith("/"):
        chat_path = "/" + chat_path
    return PreparedEndpoint(parsed.scheme, parsed.hostname, port, chat_path)


def single_model_id(response: dict[str, Any]) -> str:
    """Auto-select only when an OpenAI-compatible endpoint exposes exactly one model."""
    rows = response.get("data") if isinstance(response, dict) else None
    if not isinstance(rows, list):
        raise TransportError("models response lacks data list")
    ids = [row.get("id") for row in rows if isinstance(row, dict) and isinstance(row.get("id"), str) and row.get("id")]
    if len(ids) != len(rows):
        raise TransportError("models response contains an invalid model record")
    if len(ids) != 1:
        raise TransportError(f"automatic model selection requires exactly one model; found {len(ids)}")
    return ids[0]


def single_text_completion(response: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Return exactly one assistant text choice plus normalized usage metadata."""
    choices = response.get("choices") if isinstance(response, dict) else None
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise TransportError("response lacks exactly one completion choice")
    message = choices[0].get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise TransportError("response lacks assistant text content")
    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    normalized_usage = {
        "prompt_tokens": usage.get("prompt_tokens") if type(usage.get("prompt_tokens")) is int else None,
        "completion_tokens": usage.get("completion_tokens") if type(usage.get("completion_tokens")) is int else None,
    }
    return message["content"], normalized_usage
