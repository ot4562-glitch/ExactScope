from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path


def extract_plan(text: str) -> tuple[dict[str, object], str]:
    decoder = json.JSONDecoder()
    for start, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, end = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and set(value) == {"p"} and isinstance(value["p"], list):
            return value, text[start : start + end]
    raise ValueError("no xs_calc JSON object in model output")


def count_generated_tokens(llama_cli: Path, model: Path, generated_text: str) -> int | None:
    tokenizer = llama_cli.with_name("llama-tokenize.exe" if llama_cli.suffix else "llama-tokenize")
    if not tokenizer.is_file():
        return None
    counted = subprocess.run(
        [str(tokenizer), "-m", str(model), "--stdin", "--show-count", "--no-bos"],
        input=generated_text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    match = re.search(r"(?:total number of tokens|tokens)\D+(\d+)", counted.stdout, re.IGNORECASE)
    return int(match.group(1)) if match else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llama-cli", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--core", required=True, type=Path)
    parser.add_argument("--question", required=True)
    parser.add_argument("--expected")
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    grammar = Path(__file__).resolve().parents[2] / "adapters" / "xs-calc-v0.1" / "xs-calc.gbnf"
    system_prompt = (
        "You translate arithmetic questions into the smallest correct xs_calc JSON plan. Return JSON only. "
        "Operations mean add(x,y)=x+y, sub(x,y)=x-y, mul(x,y)=x*y, div(x,y)=x/y, "
        "powi(x,n)=x to integer power n, sqrt(x)=square root. Every number is a quoted "
        "decimal string. Steps are zero-indexed: after the first operation its result is #0 "
        "(never #1); after the second operation its result is #1. A reference may only point "
        "backward. Example: (2*3)-1 becomes "
        '{"p":[{"o":"mul","a":["2","3"]},{"o":"sub","a":["#0","1"]}]}. '
        "Do not solve or simplify the arithmetic yourself. Replace the example values with the question values."
    )
    prompt = "Produce the xs_calc plan for this question: " + args.question
    command = [
        str(args.llama_cli), "-m", str(args.model), "-sys", system_prompt, "-p", prompt,
        "--grammar-file", str(grammar), "--temp", "0", "--seed", "424242",
        "-n", "160", "-t", str(args.threads), "--no-display-prompt",
        "--single-turn", "--simple-io",
    ]
    started = time.perf_counter()
    generated = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    record: dict[str, object] = {
        "model": args.model.name,
        "question": args.question,
        "valid_plan": False,
        "runtime_accepted": False,
        "latency_ms": latency_ms,
        "generated_tokens": None,
        "plan_steps": 0,
    }
    if generated.returncode != 0:
        record["error"] = generated.stderr[-1000:]
    else:
        try:
            plan, generated_plan = extract_plan(generated.stdout)
            record["valid_plan"] = True
            record["plan"] = plan
            record["generated_tokens"] = count_generated_tokens(args.llama_cli, args.model, generated_plan)
            record["plan_steps"] = len(plan["p"])
            executed = subprocess.run(
                [str(args.core), "request"], input=json.dumps(plan, separators=(",", ":")),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            response = json.loads(executed.stdout)
            record["runtime_response"] = response
            record["runtime_accepted"] = executed.returncode == 0 and response.get("s") == 0
            if record["runtime_accepted"]:
                record["result"] = response["v"]
                if args.expected is not None:
                    record["correct_final_answer"] = response["v"] == args.expected
        except (ValueError, json.JSONDecodeError, OSError) as error:
            record["error"] = str(error)
    print(json.dumps(record, ensure_ascii=False))
    return 0 if record["runtime_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
