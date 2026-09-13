#!/usr/bin/env python3
"""Experimental ExactScope Bridge target for ONNX Runtime GenAI.

Inference stays owned by ORT GenAI.  This adapter accepts one already-decided Bridge
Delivery, returns deterministic ExactScope replies without importing ORT, and otherwise
feeds only ExactScope-approved messages into one ORT generation.
"""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import sys
from typing import Any

HERE = Path(__file__).resolve().parent
BRIDGE = HERE.parent
ROOT = BRIDGE.parents[1]
for path in (BRIDGE, ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from delivery import Delivery  # noqa: E402
from exactscope_v11 import finalize_generation, prepare_delivery  # noqa: E402


class OrtBridgeError(RuntimeError):
    pass


def _load_ort_genai() -> Any:
    try:
        return importlib.import_module("onnxruntime_genai")
    except ImportError as exc:
        raise OrtBridgeError(
            "onnxruntime-genai is required only for generation; install the runtime chosen by the host"
        ) from exc


def _plain_prompt(delivery: Delivery) -> str:
    return "\n".join(f"{message.role}: {message.content}" for message in delivery.messages) + "\nassistant:"


def _chat_prompt(tokenizer: Any, model_path: Path, delivery: Delivery) -> str:
    template_path = model_path / "chat_template.jinja"
    template = template_path.read_text(encoding="utf-8") if template_path.is_file() else ""
    try:
        return tokenizer.apply_chat_template(
            messages=delivery.messages_json(),
            tools="",
            add_generation_prompt=True,
            template_str=template,
        )
    except TypeError:
        # Some released Python bindings do not expose `tools`/`template_str` as kwargs.
        return tokenizer.apply_chat_template(
            messages=delivery.messages_json(),
            add_generation_prompt=True,
        )


def _render_prompt(tokenizer: Any, model_path: Path, delivery: Delivery, mode: str) -> str:
    if mode == "plain":
        return _plain_prompt(delivery)
    if mode == "chat-template":
        return _chat_prompt(tokenizer, model_path, delivery)
    raise OrtBridgeError(f"unknown prompt mode: {mode}")


def run_delivery(
    delivery: Delivery,
    *,
    model_path: Path | None,
    max_new_tokens: int = 32,
    prompt_mode: str = "chat-template",
    ort_module: Any | None = None,
) -> dict[str, Any]:
    """Execute one delivery without reinterpreting ExactScope grounding semantics."""
    if delivery.action == "complete":
        return {
            "source": "exactscope",
            "model_called": False,
            "route": delivery.route,
            "reply": delivery.reply,
        }
    if delivery.action != "generate":
        raise OrtBridgeError(f"unsupported delivery action: {delivery.action}")
    if model_path is None:
        raise OrtBridgeError("--model-path is required when ExactScope requests generation")
    if type(max_new_tokens) is not int or max_new_tokens < 1:
        raise OrtBridgeError("max_new_tokens must be a positive integer")

    og = ort_module if ort_module is not None else _load_ort_genai()
    model = og.Model(str(model_path))
    tokenizer = og.Tokenizer(model)
    prompt = _render_prompt(tokenizer, model_path, delivery, prompt_mode)
    input_tokens = tokenizer.encode(prompt)
    if len(input_tokens) < 1:
        raise OrtBridgeError("ORT tokenizer produced an empty prompt")

    params = og.GeneratorParams(model)
    params.set_search_options(
        max_length=len(input_tokens) + max_new_tokens,
        do_sample=False,
        batch_size=1,
    )
    generator = og.Generator(model, params)
    generator.append_tokens(input_tokens)
    start = int(generator.token_count())
    while not generator.is_done():
        generator.generate_next_token()
    sequence = generator.get_sequence(0)
    generated = sequence[start:]
    text = tokenizer.decode(generated)
    return {
        "source": "onnxruntime-genai",
        "model_called": True,
        "route": delivery.route,
        "raw_generation": text,
        "prompt_tokens": start,
        "completion_tokens": len(generated),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--model-path", type=Path)
    parser.add_argument("--scope")
    parser.add_argument("--qid")
    parser.add_argument("--retrieval-query")
    parser.add_argument("--corpus-index", type=Path)
    parser.add_argument("--contract", default="answer-object-v3")
    parser.add_argument("--max-new-tokens", type=int, default=32)
    parser.add_argument("--prompt-mode", choices=("chat-template", "plain"), default="chat-template")
    parser.add_argument("--show-delivery", action="store_true")
    args = parser.parse_args(argv)

    try:
        delivery = prepare_delivery(
            profile_dir=args.profile,
            question=args.question,
            contract=args.contract,
            qid=args.qid,
            scope=args.scope,
            retrieval_query=args.retrieval_query,
            corpus_index=args.corpus_index,
        )
        if args.show_delivery:
            print(json.dumps(delivery.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        result = run_delivery(
            delivery,
            model_path=args.model_path,
            max_new_tokens=args.max_new_tokens,
            prompt_mode=args.prompt_mode,
        )
        if result["model_called"]:
            raw = result.pop("raw_generation")
            reply = finalize_generation(raw)
            result["valid"] = reply is not None
            result["reply"] = reply
            if reply is None:
                result["raw_generation"] = raw
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0
    except (OSError, ValueError, OrtBridgeError, RuntimeError) as exc:
        print(f"ExactScope Bridge / ORT GenAI: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
