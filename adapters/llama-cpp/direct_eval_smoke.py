#!/usr/bin/env python3
"""Exercise the ExactScope direct-eval hot set through llama.cpp's OAI-compatible server.

This adapter does not calculate. It only builds a bounded tool request and validates
that the model emitted an ExactScope xs_eval call compatible with the generated hot set.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEFAULT_HOTSET = ROOT / "adapters" / "generated" / "p0-smoke"
DEFAULT_PROMPT = (
    "Using the provided ExactScope tool, calculate signed midpoint price elasticity "
    "when price changes from 10000 to 12000 and quantity changes from 100 to 80."
)


class SmokeFailure(RuntimeError):
    """Raised when the llama.cpp response is not a valid direct ExactScope call."""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_request(hotset: Path, model: str, prompt: str, tool_choice: str) -> dict[str, Any]:
    tool = load_json(hotset / "xs-eval.tool.json")
    policy = (hotset / "prompt-fragment.txt").read_text(encoding="utf-8").strip()
    catalog = load_json(hotset / "catalog.json")
    signatures = "\n".join(
        f"- {operation['sig']} method={operation['method']}"
        for operation in catalog["operations"]
    )
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": f"{policy}\nBound ExactScope hot set:\n{signatures}",
            },
            {"role": "user", "content": prompt},
        ],
        "tools": [tool],
        "tool_choice": tool_choice,
        "parallel_tool_calls": False,
        "stream": False,
        "temperature": 0,
    }


def decode_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        raise SmokeFailure("tool arguments must be a JSON object or JSON string")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SmokeFailure(f"tool arguments are not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SmokeFailure("decoded tool arguments must be an object")
    return value


def validate_tool_call(response: dict[str, Any], hotset: Path) -> dict[str, Any]:
    catalog = load_json(hotset / "catalog.json")
    by_key = {operation["op"]: operation for operation in catalog["operations"]}

    try:
        message = response["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise SmokeFailure("response does not contain choices[0].message") from exc
    calls = message.get("tool_calls")
    if not isinstance(calls, list) or not calls:
        raise SmokeFailure(
            "llama.cpp returned no tool_calls; verify that the model/chat template supports tools "
            "and run llama-server with Jinja tool-call support"
        )
    if len(calls) != 1:
        raise SmokeFailure(f"expected exactly one tool call, got {len(calls)}")

    function = calls[0].get("function")
    if not isinstance(function, dict) or function.get("name") != "xs_eval":
        raise SmokeFailure("expected one xs_eval function call")
    arguments = decode_arguments(function.get("arguments"))
    if set(arguments) != {"op", "a"}:
        raise SmokeFailure("xs_eval arguments must contain exactly op and a")

    operation_key = arguments["op"]
    if not isinstance(operation_key, str) or operation_key not in by_key:
        raise SmokeFailure(f"operation {operation_key!r} is not in the bound hot set")
    values = arguments["a"]
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise SmokeFailure("xs_eval a must be an array of exact decimal strings")

    expected_count = len(by_key[operation_key]["args"])
    if len(values) != expected_count:
        raise SmokeFailure(
            f"operation {operation_key} requires {expected_count} arguments, got {len(values)}"
        )
    return {
        "binding_sha256": catalog["binding_sha256"],
        "op": operation_key,
        "revision": by_key[operation_key]["revision"],
        "a": values,
    }


def post_json(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer no-key"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SmokeFailure(f"llama.cpp HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SmokeFailure(f"cannot reach llama.cpp server: {exc}") from exc
    try:
        decoded = json.loads(body)
    except json.JSONDecodeError as exc:
        raise SmokeFailure("llama.cpp response is not JSON") from exc
    if not isinstance(decoded, dict):
        raise SmokeFailure("llama.cpp response must be an object")
    return decoded


def synthetic_response() -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "exactscope-smoke",
                            "type": "function",
                            "function": {
                                "name": "xs_eval",
                                "arguments": json.dumps(
                                    {
                                        "op": "econ.ped.mid",
                                        "a": ["10000", "12000", "100", "80"],
                                    },
                                    separators=(",", ":"),
                                ),
                            },
                        }
                    ],
                }
            }
        ]
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/v1")
    parser.add_argument("--model", default="local-model")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--hotset", type=Path, default=DEFAULT_HOTSET)
    parser.add_argument("--tool-choice", choices=("auto", "required"), default="auto")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    request = build_request(args.hotset, args.model, args.prompt, args.tool_choice)
    if args.self_test:
        validated = validate_tool_call(synthetic_response(), args.hotset)
        print(json.dumps(validated, sort_keys=True))
        return 0
    if args.dry_run:
        print(json.dumps(request, indent=2, sort_keys=True))
        return 0

    response = post_json(
        f"{args.base_url.rstrip('/')}/chat/completions",
        request,
        args.timeout,
    )
    validated = validate_tool_call(response, args.hotset)
    print(json.dumps(validated, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, KeyError, TypeError, SmokeFailure, json.JSONDecodeError) as exc:
        print(f"exactscope llama.cpp smoke: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
