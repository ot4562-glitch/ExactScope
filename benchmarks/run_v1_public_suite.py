#!/usr/bin/env python3
"""Run one model on the deterministic six-task ExactScope v1 public benchmark screen.

This is a post-release system screen, not an Open LLM Leaderboard reproduction.
Each public item is attempted exactly once with temperature 0 and no hidden retry.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
TASK_IDS = ("mmlu", "arc_challenge", "hellaswag", "truthfulqa_mc1", "winogrande", "gsm8k")


class FormatError(ValueError):
    """The completion violates the requested structured answer format."""


class ProtocolError(ValueError):
    """The server response violates the completion protocol."""


def strict_json(value: str | bytes) -> Any:
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = item
        return result

    def constant(value):
        raise ValueError(f"non-finite JSON constant: {value}")

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"non-finite JSON number: {value}")
        return number

    return json.loads(value, object_pairs_hook=pairs, parse_constant=constant,
                      parse_float=finite_float)


def payload_for(model_id: str, row: dict) -> dict:
    return mc_payload(model_id, row) if row["kind"] == "multiple_choice" else numeric_payload(model_id, row)


def runtime_environment(runtime: Path) -> dict[str, str]:
    # Explicit allowlist: do not inherit credentials, proxy settings or LLAMA_ARG_ overrides.
    allowed = {
        "PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "HOME",
        "LANG", "LC_ALL", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH",
        "CUDA_VISIBLE_DEVICES", "HIP_VISIBLE_DEVICES", "ROCR_VISIBLE_DEVICES",
        "GGML_VK_VISIBLE_DEVICES", "OMP_NUM_THREADS", "OMP_PROC_BIND", "OMP_PLACES",
    }
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    if os.name != "nt":
        env["LD_LIBRARY_PATH"] = str(runtime.parent) + (os.pathsep + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    return env


def freeze_protocol(args, model: dict, manifest: dict, tasks: dict, command: list[str], env: dict) -> dict:
    runtime = args.runtime_executable.resolve()
    paths = [Path(__file__).resolve(), args.acquisition_manifest.resolve(),
             args.data_dir.resolve() / "manifest.json", Path(model["path"]).resolve(), runtime]
    paths.extend(args.data_dir.resolve() / record["filename"] for record in manifest["tasks"])
    paths.extend(path for path in runtime.parent.iterdir()
                 if path.is_file() and (path.suffix.lower() in {".dll", ".so", ".dylib"} or ".so." in path.name))
    frozen_files = {str(path): file_sha(path) for path in sorted(set(paths))}
    if frozen_files[str(Path(model["path"]).resolve())] != model["sha256"]:
        raise ValueError("model changed before preregistration")
    acquisition = load_json(args.acquisition_manifest)
    matches = [record for record in acquisition.get("records", [])
               if isinstance(record, dict) and record.get("id") == model["id"]]
    if matches != [model]:
        raise ValueError("acquisition manifest changed while loading")
    for record in manifest["tasks"]:
        if frozen_files[str(args.data_dir.resolve() / record["filename"])] != record["sha256"]:
            raise ValueError("public data changed before preregistration")
    # Bind the loaded data, not just a later snapshot of files on disk.
    disk_manifest, disk_tasks = verify_data(args.data_dir)
    if disk_tasks != tasks or disk_manifest != {k: v for k, v in manifest.items() if k != "__path"}:
        raise ValueError("public data changed while loading")
    requests = [{"benchmark_id": task, "source_index": row["source_index"],
                 "payload": payload_for(model["id"], row)} for task in TASK_IDS for row in tasks[task]]
    policy = {"requests": requests, "attempts_per_item": 1, "retry_count": 0,
              "request_timeout_seconds": 120, "server_ready_timeout_seconds": 90,
              "transport": "direct loopback HTTP; no proxy, redirects, or retries",
              "scoring": "strict structured output; finite Decimal numeric equality; model format failures score zero but do not invalidate an otherwise complete run; transport/protocol failures invalidate qualification",
              "accuracy_denominator": "all attempted items, including format/protocol/infrastructure failures",
              "latency_policy": "mean_latency_us uses received model responses including format failures; transport/protocol failures reported separately"}
    # Do not use platform.platform(), processor(), or uname()._asdict():
    # their processor discovery can launch a subprocess before preregistration.
    if hasattr(os, "uname"):
        native_uname = os.uname()
        uname = dict(zip(("system", "node", "release", "version", "machine"), native_uname))
    else:
        windows = sys.getwindowsversion() if sys.platform == "win32" else None
        uname = {"system": sys.platform, "node": socket.gethostname(),
                 "release": f"{windows.major}.{windows.minor}" if windows else "",
                 "version": str(windows) if windows else "",
                 "machine": os.environ.get("PROCESSOR_ARCHITEW6432") or
                            os.environ.get("PROCESSOR_ARCHITECTURE", "")}
    processor = os.environ.get("PROCESSOR_IDENTIFIER", "") if sys.platform == "win32" else ""
    return {
        "format": "exactscope.v1-public-screen-preregistration", "format_version": "0.1",
        "model_inference_performed": False,
        "frozen_files": frozen_files,
        "runner_source_sha256": frozen_files[str(Path(__file__).resolve())],
        "data_manifest_sha256": frozen_files[str(args.data_dir.resolve() / "manifest.json")],
        "model": model, "runtime_executable_sha256": frozen_files[str(runtime)],
        "launch": {"command": command, "cwd": str(runtime.parent), "environment": env,
                   "threads": args.threads, "context": args.context, "port": args.port},
        "host": {"platform": sys.platform, "machine": uname["machine"],
                 "processor": processor, "logical_cpus": os.cpu_count(),
                 "python": sys.version, "python_executable": sys.executable,
                 "python_executable_sha256": file_sha(Path(sys.executable)),
                 "uname": uname,
                 "backend_note": "Backend auto-selection and device details are recorded in llama-server.log; driver and system library identities are not fully captured."},
        "policy": policy, "policy_sha256": hashlib.sha256(canonical(policy)).hexdigest(),
    }


def verify_frozen(protocol: dict, path: Path, digest: str) -> None:
    if file_sha(path) != digest:
        raise ValueError("preregistration drift")
    for name, expected in protocol["frozen_files"].items():
        if not Path(name).is_file() or file_sha(Path(name)) != expected:
            raise ValueError(f"frozen input drift: {name}")


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"non-object JSONL row: {path}")
                rows.append(value)
    return rows


def resolve_model(manifest: dict, model_id: str) -> dict:
    records = manifest.get("records")
    matches = [row for row in records or [] if isinstance(row, dict) and row.get("id") == model_id]
    if len(matches) != 1:
        raise ValueError(f"model id not found exactly once: {model_id}")
    record = matches[0]
    path = Path(record["path"])
    if not path.is_file() or path.stat().st_size != record["bytes"] or file_sha(path) != record["sha256"]:
        raise ValueError(f"model identity drift: {model_id}")
    return record


def verify_data(data_dir: Path) -> tuple[dict, dict[str, list[dict]]]:
    manifest_path = data_dir / "manifest.json"
    manifest = load_json(manifest_path)
    tasks: dict[str, list[dict]] = {}
    for record in manifest.get("tasks", []):
        path = data_dir / record["filename"]
        if not path.is_file() or file_sha(path) != record["sha256"]:
            raise ValueError(f"public benchmark data drift: {record['id']}")
        rows = load_jsonl(path)
        if len(rows) != record["item_count"]:
            raise ValueError(f"public benchmark row-count drift: {record['id']}")
        tasks[record["id"]] = rows
    if set(tasks) != set(TASK_IDS) or any(not rows for rows in tasks.values()):
        raise ValueError("public benchmark screen requires six tasks")
    return manifest, tasks


def server_command(executable: Path, model: Path, model_id: str, port: int, threads: int, context: int) -> list[str]:
    return [
        str(executable), "-m", str(model), "--alias", model_id,
        "--host", "127.0.0.1", "--port", str(port), "-c", str(context),
        "-t", str(threads), "--parallel", "1", "--jinja", "--no-webui",
        "--offline", "--no-mmproj", "--reasoning", "off", "--no-cache-prompt",
    ]


def wait_server(process: subprocess.Popen[bytes], port: int, timeout: float = 90.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"llama-server exited during startup: {process.returncode}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, OSError, TimeoutError):
            pass
        time.sleep(0.4)
    raise TimeoutError("llama-server readiness timeout")


def request_json(port: int, payload: dict, timeout: float = 120.0) -> tuple[dict, int]:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    # HTTPConnection sends exactly once and never follows redirects or uses proxies.
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    started = time.perf_counter_ns()
    try:
        connection.request("POST", "/v1/chat/completions", body=body,
                           headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            raise ProtocolError(f"completion HTTP status: {response.status}")
        raw = response.read()
    finally:
        connection.close()
    latency_us = (time.perf_counter_ns() - started + 500) // 1000
    value = strict_json(raw)
    if not isinstance(value, dict):
        raise ProtocolError("llama.cpp response is not an object")
    return value, latency_us


def mc_payload(model_id: str, row: dict) -> dict:
    labels = [choice["label"] for choice in row["choices"]]
    options = "\n".join(f"{choice['label']}. {choice['text']}" for choice in row["choices"])
    prompt = f"Question:\n{row['question']}\n\nOptions:\n{options}\n\nChoose the single best option."
    return {
        "model": model_id,
        "stream": False,
        "temperature": 0,
        "seed": 0,
        "max_tokens": 32,
        "messages": [
            {"role": "system", "content": "Answer the multiple-choice item. Return only the required JSON object. Do not add explanation."},
            {"role": "user", "content": prompt},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "benchmark_choice",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["choice"],
                    "properties": {"choice": {"type": "string", "enum": labels}},
                },
            },
        },
    }


def numeric_payload(model_id: str, row: dict) -> dict:
    return {
        "model": model_id,
        "stream": False,
        "temperature": 0,
        "seed": 0,
        "max_tokens": 64,
        "messages": [
            {"role": "system", "content": "Solve the math problem. Return only the required JSON object with the final numeric answer; no units or explanation."},
            {"role": "user", "content": row["question"]},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "benchmark_number",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["answer"],
                    "properties": {"answer": {"type": "string", "minLength": 1, "maxLength": 64}},
                },
            },
        },
    }


def parse_content(response: dict) -> tuple[dict | None, dict]:
    if not isinstance(response, dict) or response.get("error") is not None:
        raise ProtocolError("completion response is not a successful object")
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise ProtocolError("response lacks exactly one choice")
    message = choices[0].get("message")
    if (choices[0].get("index") != 0 or type(choices[0].get("index")) is not int
            or not isinstance(message, dict) or message.get("role") != "assistant"
            or message.get("tool_calls") or message.get("function_call")
            or message.get("refusal")):
        raise ProtocolError("invalid assistant completion")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str):
        raise ProtocolError("response lacks textual content")
    try:
        parsed = strict_json(content)
    except ValueError:
        parsed = None
    usage = response.get("usage")
    if usage is not None and not isinstance(usage, dict):
        raise ProtocolError("invalid usage object")
    usage = usage or {}
    return parsed if isinstance(parsed, dict) else None, {
        "raw_output": content,
        "input_tokens": usage.get("prompt_tokens"),
        "output_tokens": usage.get("completion_tokens"),
        "finish_reason": choices[0].get("finish_reason"),
    }


def normalize_number(value: str) -> Decimal | None:
    text = value.strip().replace(",", "").replace("$", "")
    try:
        number = Decimal(text)
        return number if number.is_finite() else None
    except InvalidOperation:
        return None


def run_item(port: int, model_id: str, row: dict, payload: dict | None = None) -> dict:
    payload = payload_for(model_id, row) if payload is None else payload
    base = {
        "benchmark_id": row["benchmark_id"],
        "source_index": row["source_index"],
        "kind": row["kind"],
        "expected": row["answer"],
        "correct": None,
        "parsed": None,
        "error": None,
        "error_kind": None,
    }
    started = time.perf_counter_ns()
    try:
        response, latency_us = request_json(port, payload)
        base["latency_us"] = latency_us
        parsed, meta = parse_content(response)
        base.update(meta)
        base["parsed"] = parsed
        if meta["finish_reason"] not in {"stop", "length"}:
            raise ProtocolError("unsupported finish reason")
        for key in ("input_tokens", "output_tokens"):
            if meta[key] is not None and (type(meta[key]) is not int or meta[key] < 0):
                raise ValueError(f"invalid usage: {key}")
        if row["kind"] == "multiple_choice":
            actual = parsed.get("choice") if isinstance(parsed, dict) else None
            if not isinstance(parsed, dict) or set(parsed) != {"choice"} or not isinstance(actual, str) or actual not in [choice["label"] for choice in row["choices"]]:
                raise FormatError("invalid structured choice output")
            base["actual"] = actual
            base["correct"] = actual == row["answer"]
        else:
            actual = parsed.get("answer") if isinstance(parsed, dict) else None
            base["actual"] = actual
            expected_number = normalize_number(str(row["answer"]))
            actual_number = normalize_number(actual) if isinstance(actual, str) else None
            if not isinstance(parsed, dict) or set(parsed) != {"answer"} or not isinstance(actual, str) or not 1 <= len(actual) <= 64 or actual_number is None:
                raise FormatError("invalid structured numeric output")
            base["correct"] = expected_number is not None and actual_number == expected_number
    except (OSError, ValueError, TypeError, KeyError, urllib.error.URLError, http.client.HTTPException) as exc:
        base["error"] = f"{type(exc).__name__}: {exc}"
        base["error_kind"] = ("format" if isinstance(exc, FormatError) else
                              "infrastructure" if isinstance(exc, (OSError, urllib.error.URLError, http.client.HTTPException)) else "protocol")
        base["correct"] = None
    finally:
        if "latency_us" not in base:
            base["latency_us"] = (time.perf_counter_ns() - started + 500) // 1000
    return base


def summarize(model: dict, rows: list[dict], data_manifest: dict, runtime_sha: str,
              *, data_manifest_sha: str | None = None) -> dict:
    task_ids = sorted({row["benchmark_id"] for row in rows})
    tasks = {}
    for task_id in task_ids:
        selected = [row for row in rows if row["benchmark_id"] == task_id]
        valid = [row for row in selected if row.get("error") is None]
        format_failed = [row for row in selected if row.get("error_kind") == "format"]
        execution_failed = [row for row in selected if row.get("error_kind") in {"infrastructure", "protocol"}]
        completed_responses = valid + format_failed
        tasks[task_id] = {
            "items": len(selected),
            "correct": sum(bool(row["correct"]) for row in selected),
            "accuracy": sum(bool(row["correct"]) for row in selected) / len(selected),
            "errors": sum(row.get("error") is not None for row in selected),
            "wrong_answers": sum(row["correct"] is False for row in valid),
            "infrastructure_errors": sum(row.get("error_kind") == "infrastructure" for row in execution_failed),
            "protocol_errors": sum(row.get("error_kind") == "protocol" for row in execution_failed),
            "format_errors": len(format_failed),
            "format_compliance": (len(selected) - len(format_failed)) / len(selected),
            "mean_latency_us": sum(row["latency_us"] for row in completed_responses) / len(completed_responses) if completed_responses else None,
            "mean_failed_latency_us": sum(row["latency_us"] for row in execution_failed) / len(execution_failed) if execution_failed else None,
            "latency_items": len(completed_responses),
            "input_tokens": sum(row.get("input_tokens") or 0 for row in completed_responses),
            "output_tokens": sum(row.get("output_tokens") or 0 for row in completed_responses),
        }
    macro = sum(value["accuracy"] for value in tasks.values()) / len(tasks) if tasks else None
    return {
        "format": "exactscope.v1-public-screen-result",
        "format_version": "0.1",
        "leaderboard_comparable": False,
        "model": {key: model[key] for key in ("id", "family", "parameters", "bucket", "repository", "resolved_revision", "requested_file", "quantization", "bytes", "sha256")},
        "runtime_sha256": runtime_sha,
        "data_manifest_sha256": data_manifest_sha or file_sha(Path(data_manifest["__path"])),
        "tasks": tasks,
        "macro_accuracy": macro,
        "total_items": len(rows),
        "total_errors": sum(row.get("error") is not None for row in rows),
        "total_wrong_answers": sum(value["wrong_answers"] for value in tasks.values()),
        "total_infrastructure_errors": sum(value["infrastructure_errors"] for value in tasks.values()),
        "total_protocol_errors": sum(value["protocol_errors"] for value in tasks.values()),
        "total_format_errors": sum(value["format_errors"] for value in tasks.values()),
        "total_execution_errors": sum(value["infrastructure_errors"] + value["protocol_errors"] for value in tasks.values()),
        "status": "FAIL" if not rows or any(row.get("error_kind") in {"infrastructure", "protocol"} for row in rows) else "PASS",
        "status_scope": "execution/protocol validity only; model format failures are explicit scored failures, not run-invalidating infrastructure errors",
    }


def stop_server(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquisition-manifest", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--runtime-executable", type=Path, required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18400)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--context", type=int, default=4096)
    args = parser.parse_args()

    if args.output.exists():
        raise RuntimeError("output already exists; benchmark runs are single-writer and non-resumable")
    acquisition = load_json(args.acquisition_manifest)
    model = resolve_model(acquisition, args.model_id)
    data_manifest, tasks = verify_data(args.data_dir)
    data_manifest["__path"] = str((args.data_dir / "manifest.json").resolve())
    runtime = args.runtime_executable.resolve()
    if not runtime.is_file():
        raise RuntimeError("llama-server executable does not exist")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", args.port))

    args.output.mkdir(parents=True)
    log = (args.output / "llama-server.log").open("wb")
    process = None
    rows: list[dict] = []
    try:
        command = server_command(runtime, Path(model["path"]).resolve(), model["id"], args.port, args.threads, args.context)
        env = runtime_environment(runtime)
        protocol = freeze_protocol(args, model, data_manifest, tasks, command, env)
        protocol_path = args.output / "preregistration.json"
        protocol_bytes = canonical(protocol)
        protocol_sha = hashlib.sha256(protocol_bytes).hexdigest()
        with protocol_path.open("xb") as frozen:
            frozen.write(protocol_bytes)
        run_errors = []
        try:
            verify_frozen(protocol, protocol_path, protocol_sha)
            process = subprocess.Popen(command, cwd=runtime.parent, env=env, stdout=log, stderr=log)
            wait_server(process, args.port)
            frozen_requests = iter(protocol["policy"]["requests"])
            raw_path = args.output / "raw-results.jsonl"
            with raw_path.open("wb") as raw:
                for task_id in TASK_IDS:
                    for item in tasks[task_id]:
                        request = next(frozen_requests)
                        result = run_item(args.port, model["id"], item, request["payload"])
                        rows.append(result)
                        raw.write(canonical(result))
                        raw.flush()
            if process.poll() is not None:
                raise RuntimeError(f"llama-server exited during run: {process.returncode}")
        except (OSError, ValueError, RuntimeError, KeyError, TypeError, http.client.HTTPException) as exc:
            run_errors.append({"error_kind": "infrastructure", "error": f"{type(exc).__name__}: {exc}"})
        finally:
            try:
                stop_server(process)
            except (OSError, subprocess.SubprocessError) as exc:
                run_errors.append({"error_kind": "infrastructure", "error": f"server cleanup: {exc}"})
            process = None
        summary = summarize(model, rows, data_manifest, protocol["runtime_executable_sha256"],
                            data_manifest_sha=protocol["data_manifest_sha256"])
        summary["run_errors"] = run_errors
        summary["total_errors"] += len(run_errors)
        summary["total_infrastructure_errors"] += len(run_errors)
        summary["expected_items"] = len(protocol["policy"]["requests"])
        summary["unattempted_items"] = summary["expected_items"] - len(rows)
        if run_errors or summary["unattempted_items"]:
            summary["status"] = "FAIL"
        summary["preregistration_sha256"] = protocol_sha
        try:
            verify_frozen(protocol, protocol_path, protocol_sha)
            summary["frozen_inputs_verified_after_run"] = True
        except (OSError, ValueError) as exc:
            summary["frozen_inputs_verified_after_run"] = False
            summary["integrity_error"] = str(exc)
            summary["total_errors"] += 1
            summary["total_protocol_errors"] += 1
            summary["status"] = "FAIL"
        (args.output / "summary.json").write_bytes(canonical(summary))
        print(json.dumps({"status": summary["status"], "model_id": model["id"], "macro_accuracy": summary["macro_accuracy"], "total_items": len(rows), "errors": summary["total_errors"]}, sort_keys=True))
        return 0 if summary["status"] == "PASS" else 1
    finally:
        stop_server(process)
        log.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        print(f"ExactScope v1 public suite: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
