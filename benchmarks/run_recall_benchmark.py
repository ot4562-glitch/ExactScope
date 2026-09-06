#!/usr/bin/env python3
"""Run a one-turn A/R factual-recall benchmark against an OpenAI-compatible local model."""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ARMS = ("A", "R")
ANSWER_SCHEMA = {
    "name": "exactscope_recall_answer",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["a", "abstain"],
        "properties": {
            "a": {"type": ["string", "null"]},
            "abstain": {"type": "boolean"},
        },
    },
}


class RecallBenchmarkError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelReply:
    content: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: float
    finish_reason: str | None


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RecallBenchmarkError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise RecallBenchmarkError(f"{path}:{line_number}: corpus record must be an object")
        records.append(value)
    if not records:
        raise RecallBenchmarkError("recall corpus is empty")
    ids = [record.get("id") for record in records]
    if any(not isinstance(value, str) or not value for value in ids) or len(set(ids)) != len(ids):
        raise RecallBenchmarkError("recall corpus IDs must be unique nonempty strings")
    return records


def optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


class Client:
    def __init__(self, *, base_url: str, model: str, timeout: float, seed: int, max_tokens: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.seed = seed
        self.max_tokens = max_tokens

    def chat(self, messages: list[dict[str, str]]) -> ModelReply:
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "seed": self.seed,
            "max_tokens": self.max_tokens,
            "stream": False,
            "response_format": {"type": "json_schema", "json_schema": ANSWER_SCHEMA},
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = time.perf_counter_ns()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RecallBenchmarkError(f"model HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RecallBenchmarkError(f"cannot reach model server: {exc}") from exc
        except TimeoutError as exc:
            raise RecallBenchmarkError("model request timed out") from exc
        latency_ms = (time.perf_counter_ns() - started) / 1_000_000
        if not isinstance(raw, dict):
            raise RecallBenchmarkError("model response root is not an object")
        choices = raw.get("choices")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise RecallBenchmarkError("model response must contain exactly one choice")
        message = choices[0].get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise RecallBenchmarkError("model response lacks textual JSON content")
        if message.get("tool_calls") not in (None, []):
            raise RecallBenchmarkError("recall benchmark forbids model tool calls in A/R one-turn mode")
        usage = raw.get("usage") if isinstance(raw.get("usage"), dict) else {}
        return ModelReply(
            content=message["content"],
            input_tokens=optional_int(usage.get("prompt_tokens")),
            output_tokens=optional_int(usage.get("completion_tokens")),
            latency_ms=latency_ms,
            finish_reason=choices[0].get("finish_reason") if isinstance(choices[0].get("finish_reason"), str) else None,
        )


def run_recall(executable: Path, fact_pack: Path, question: str, k: int) -> tuple[dict[str, Any], float]:
    started = time.perf_counter_ns()
    completed = subprocess.run(
        [str(executable), str(fact_pack), question, str(k)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    latency_ms = (time.perf_counter_ns() - started) / 1_000_000
    if completed.returncode != 0:
        raise RecallBenchmarkError(f"recall executable failed: {completed.stderr.strip()}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RecallBenchmarkError("recall executable returned invalid JSON") from exc
    if not isinstance(result, dict) or not isinstance(result.get("s"), int) or not isinstance(result.get("h"), list):
        raise RecallBenchmarkError("recall executable returned invalid response shape")
    return result, latency_ms


def parse_answer(content: str) -> dict[str, Any]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RecallBenchmarkError(f"model output is not valid JSON: {exc}") from exc
    if not isinstance(value, dict) or set(value) != {"a", "abstain"}:
        raise RecallBenchmarkError("model answer must contain exactly a and abstain")
    answer = value.get("a")
    abstain = value.get("abstain")
    if answer is not None and not isinstance(answer, str):
        raise RecallBenchmarkError("model answer a must be string or null")
    if not isinstance(abstain, bool):
        raise RecallBenchmarkError("model answer abstain must be boolean")
    if abstain and answer not in (None, ""):
        raise RecallBenchmarkError("abstaining answer must not also assert a factual value")
    return value


def normalize_answer(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def answer_correct(case: dict[str, Any], answer: dict[str, Any]) -> bool:
    if case.get("expect_abstain") is True:
        return answer["abstain"] is True and answer["a"] in (None, "")
    expected = case.get("expected_answer")
    return (
        isinstance(expected, str)
        and answer["abstain"] is False
        and isinstance(answer["a"], str)
        and normalize_answer(answer["a"]) == normalize_answer(expected)
    )


def retrieval_correct(case: dict[str, Any], recall: dict[str, Any] | None) -> bool | None:
    if recall is None:
        return None
    hits = recall["h"]
    if case.get("expect_evidence") is True:
        expected = case.get("expected_fact_id")
        return bool(hits) and isinstance(hits[0], dict) and hits[0].get("id") == expected
    return recall["s"] == 8 and hits == []


def build_messages(case: dict[str, Any], arm: str, recall: dict[str, Any] | None) -> list[dict[str, str]]:
    question = case["question"]
    if not isinstance(question, str):
        raise RecallBenchmarkError("case question must be a string")
    base = (
        "Return only the JSON object required by the response schema. "
        "Give only the shortest factual value needed to answer the question. "
        "If you cannot support a factual value, set abstain=true and a=null."
    )
    if arm == "A":
        return [
            {"role": "system", "content": base},
            {"role": "user", "content": question},
        ]
    if arm != "R" or recall is None:
        raise RecallBenchmarkError(f"unsupported arm: {arm}")
    hits = recall["h"]
    if hits:
        evidence_lines = []
        for hit in hits:
            if not isinstance(hit, dict):
                raise RecallBenchmarkError("recall hit is not an object")
            evidence_lines.append(
                f"[{hit.get('id')} rev={hit.get('rev')} src={hit.get('src')}] {hit.get('e')}"
            )
        evidence = "\n".join(evidence_lines)
    else:
        evidence = "NO_EVIDENCE"
    system = (
        base
        + " The ExactScope evidence block is authoritative for this benchmark. "
        + "Use only that block for the requested factual value. If it says NO_EVIDENCE or does not contain the answer, abstain."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Question: {question}\nExactScope evidence:\n{evidence}"},
    ]


def mean_optional(values: list[int | None]) -> float | None:
    present = [value for value in values if value is not None]
    return statistics.mean(present) if present else None


def mean_float(values: list[float]) -> float | None:
    return statistics.mean(values) if values else None


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    arms: dict[str, Any] = {}
    for arm in ARMS:
        rows = [record for record in records if record["arm"] == arm]
        if not rows:
            continue
        total = len(rows)
        correct = sum(record["answer_correct"] for record in rows)
        unsupported = sum(record["unsupported_assertion"] for record in rows)
        no_answer_rows = [record for record in rows if record["expect_abstain"]]
        arm_summary: dict[str, Any] = {
            "total": total,
            "correct": correct,
            "accuracy": correct / total,
            "unsupported_assertions": unsupported,
            "hallucination_rate": unsupported / total,
            "no_answer_total": len(no_answer_rows),
            "no_answer_correct": sum(record["answer_correct"] for record in no_answer_rows),
            "mean_input_tokens": mean_optional([record["input_tokens"] for record in rows]),
            "mean_output_tokens": mean_optional([record["output_tokens"] for record in rows]),
            "mean_model_latency_ms": mean_float([record["model_latency_ms"] for record in rows]),
        }
        if arm == "R":
            retrieval_rows = [record for record in rows if record["retrieval_correct"] is not None]
            arm_summary.update(
                {
                    "retrieval_correct": sum(record["retrieval_correct"] is True for record in retrieval_rows),
                    "retrieval_total": len(retrieval_rows),
                    "retrieval_accuracy": (
                        sum(record["retrieval_correct"] is True for record in retrieval_rows) / len(retrieval_rows)
                        if retrieval_rows
                        else None
                    ),
                    "mean_retrieval_latency_ms": mean_float([record["retrieval_latency_ms"] for record in rows]),
                    "grounding_failures": sum(record["grounding_failure"] for record in rows),
                }
            )
        arms[arm] = arm_summary

    efficiency: dict[str, Any] = {}
    if "A" in arms and "R" in arms:
        a = arms["A"]
        r = arms["R"]
        accuracy_uplift = r["accuracy"] - a["accuracy"]
        hallucination_reduction = a["hallucination_rate"] - r["hallucination_rate"]
        added_tokens = None
        if a["mean_input_tokens"] is not None and r["mean_input_tokens"] is not None:
            added_tokens = r["mean_input_tokens"] - a["mean_input_tokens"]
        added_model_latency = None
        if a["mean_model_latency_ms"] is not None and r["mean_model_latency_ms"] is not None:
            added_model_latency = r["mean_model_latency_ms"] - a["mean_model_latency_ms"]
        efficiency = {
            "accuracy_uplift": accuracy_uplift,
            "hallucination_rate_reduction": hallucination_reduction,
            "added_mean_input_tokens": added_tokens,
            "added_mean_model_latency_ms": added_model_latency,
            "accuracy_uplift_per_added_input_token": (
                accuracy_uplift / added_tokens if added_tokens not in (None, 0) else None
            ),
            "hallucination_reduction_per_added_input_token": (
                hallucination_reduction / added_tokens if added_tokens not in (None, 0) else None
            ),
        }
    return {"arms": arms, "efficiency": efficiency}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--server-model-name", required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--fact-pack", type=Path, required=True)
    parser.add_argument("--recall-executable", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--k", type=int, default=2)
    args = parser.parse_args()
    if not 1 <= args.k <= 4:
        raise RecallBenchmarkError("--k must be in 1..4")
    if args.output_dir.exists():
        raise RecallBenchmarkError("output directory already exists; use a new immutable run directory")
    args.output_dir.mkdir(parents=True)

    cases = load_jsonl(args.corpus.resolve())
    client = Client(
        base_url=args.base_url,
        model=args.server_model_name,
        timeout=args.timeout,
        seed=args.seed,
        max_tokens=args.max_tokens,
    )
    records: list[dict[str, Any]] = []
    for case in cases:
        recall, retrieval_latency_ms = run_recall(
            args.recall_executable.resolve(), args.fact_pack.resolve(), case["question"], args.k
        )
        for arm in ARMS:
            arm_recall = recall if arm == "R" else None
            reply = client.chat(build_messages(case, arm, arm_recall))
            answer = parse_answer(reply.content)
            correct = answer_correct(case, answer)
            r_correct = retrieval_correct(case, arm_recall)
            unsupported = bool(case.get("expect_abstain")) and not answer["abstain"]
            grounding_failure = arm == "R" and r_correct is True and not correct
            records.append(
                {
                    "case_id": case["id"],
                    "class": case.get("class"),
                    "arm": arm,
                    "question": case["question"],
                    "expected_answer": case.get("expected_answer"),
                    "expected_fact_id": case.get("expected_fact_id"),
                    "expect_abstain": case.get("expect_abstain") is True,
                    "answer": answer,
                    "answer_correct": correct,
                    "unsupported_assertion": unsupported,
                    "retrieval": arm_recall,
                    "retrieval_correct": r_correct,
                    "grounding_failure": grounding_failure,
                    "input_tokens": reply.input_tokens,
                    "output_tokens": reply.output_tokens,
                    "model_latency_ms": reply.latency_ms,
                    "retrieval_latency_ms": retrieval_latency_ms if arm == "R" else 0.0,
                    "finish_reason": reply.finish_reason,
                }
            )

    with (args.output_dir / "records.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    summary = summarize(records)
    summary.update(
        {
            "format": "exactscope.recall-benchmark.summary",
            "format_version": "0.1",
            "model": args.server_model_name,
            "case_count": len(cases),
            "model_calls": len(records),
            "model_calls_per_case_per_arm": 1,
            "retrieval_policy": "question-prefetch-before-model; no retry; no model tool call",
        }
    )
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RecallBenchmarkError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"ExactScope recall benchmark: FAIL: {exc}")
        raise SystemExit(1) from exc
