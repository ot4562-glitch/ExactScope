from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the bounded xs_calc reference matrix")
    parser.add_argument("--llama-cli", required=True, type=Path)
    parser.add_argument("--core", required=True, type=Path)
    parser.add_argument("--model", required=True, action="append", type=Path)
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("cases.json"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    runner = Path(__file__).with_name("run_xs_calc.py")
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    records: list[dict[str, object]] = []
    for model in args.model:
        for case in cases:
            command = [
                sys.executable, str(runner), "--llama-cli", str(args.llama_cli),
                "--model", str(model), "--core", str(args.core),
                "--question", case["question"], "--expected", case["expected"],
                "--threads", str(args.threads),
            ]
            completed = subprocess.run(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
            )
            try:
                record = json.loads(completed.stdout.strip())
            except json.JSONDecodeError:
                record = {
                    "model": model.name, "question": case["question"],
                    "valid_plan": False, "runtime_accepted": False,
                    "error": (completed.stderr or completed.stdout)[-1000:],
                }
            record["case_id"] = case["id"]
            record["expected"] = case["expected"]
            records.append(record)

    summaries: list[dict[str, object]] = []
    for model in args.model:
        selected = [record for record in records if record["model"] == model.name]
        count = len(selected)
        accepted = [record for record in selected if record.get("runtime_accepted")]
        correct = [record for record in accepted if record.get("correct_final_answer")]
        tokens = [record["generated_tokens"] for record in selected if isinstance(record.get("generated_tokens"), int)]
        steps = [record["plan_steps"] for record in selected if isinstance(record.get("plan_steps"), int)]
        latencies = [record["latency_ms"] for record in selected if isinstance(record.get("latency_ms"), (int, float))]
        summaries.append({
            "model": model.name,
            "cases": count,
            "valid_plan_rate_pct": round(100 * sum(bool(r.get("valid_plan")) for r in selected) / count, 2),
            "runtime_accepted_plan_rate_pct": round(100 * len(accepted) / count, 2),
            "correct_final_answer_rate_pct": round(100 * len(correct) / count, 2),
            "wrong_numeric_answer_rate_pct": round(100 * (len(accepted) - len(correct)) / count, 2),
            "average_generated_tokens": round(sum(tokens) / len(tokens), 2) if tokens else None,
            "average_plan_steps": round(sum(steps) / len(steps), 2) if steps else None,
            "average_latency_ms": round(sum(latencies) / len(latencies), 3) if latencies else None,
        })
    report = {
        "classification": "five-case reference integration smoke; not a general benchmark score",
        "llama_cpp": args.llama_cli.parent.name,
        "decoding": {"temperature": 0, "seed": 424242, "max_generated_tokens": 160},
        "summaries": summaries,
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
