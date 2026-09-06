#!/usr/bin/env python3
"""Run frozen ExactScope rc4 A/G model benchmark. Requires preregistration; no resume/retry."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any
import urllib.error
import urllib.request

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
if str(ROOT / "benchmarks") not in sys.path:
    sys.path.insert(0, str(ROOT / "benchmarks"))

from grounding_canonical import canonical_bytes  # noqa: E402
from grounding_dry_run import FaultProvider, load_serving  # noqa: E402
from grounding_preregister import (  # noqa: E402
    PreregistrationError,
    file_sha,
    load_cjson,
    load_json,
    verify_candidate,
    verify_document,
)
from grounding_runtime import run_grounding  # noqa: E402


class BenchmarkRunError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_frozen_inputs(prereg_path: Path, output: Path) -> tuple[dict[str, Any], Path, dict[str, Any], dict[str, Any]]:
    prereg = load_cjson(prereg_path)
    verify_document(prereg, prereg_path)
    if str(output.resolve()) != prereg["planned_output"]:
        raise BenchmarkRunError("output path differs from preregistration")
    if output.exists():
        raise BenchmarkRunError("output directory already exists; resume/reuse is forbidden")
    candidate_path = ROOT / "candidate" if (ROOT / "candidate").is_dir() else ROOT / "target/grounding-candidate-rc4-001"
    candidate = verify_candidate(candidate_path)
    if candidate != prereg["candidate"]:
        raise BenchmarkRunError("candidate identity drift")
    package_manifest = ROOT / "package-manifest.json"
    if not package_manifest.is_file():
        raise BenchmarkRunError("run must start from extracted evaluation package")
    if file_sha(package_manifest) != prereg["evaluation_package"]["package_manifest_sha256"]:
        raise BenchmarkRunError("package manifest digest drift")
    package = load_json(package_manifest)
    if package.get("source_commit") != prereg["source_commit"]:
        raise BenchmarkRunError("package/source commit drift")
    expected_files = {
        ROOT / "benchmarks/grounding-model-inventory.json": prereg["model_inventory_sha256"],
        ROOT / "benchmarks/grounding-runtime-llama-v040.json": prereg["runtime_record_sha256"],
        ROOT / "benchmarks/grounding-generation-config.json": prereg["generation_config_sha256"],
        ROOT / "benchmarks/grounding-isolation-policy.json": prereg["isolation_policy_sha256"],
        ROOT / "benchmarks/score_grounding.py": prereg["scorer_sha256"],
    }
    for path, digest in expected_files.items():
        if not path.is_file() or file_sha(path) != digest:
            raise BenchmarkRunError(f"bound file drift: {path.name}")
    model_path = Path(prereg["model"]["path"])
    if not model_path.is_file() or model_path.stat().st_size != prereg["model"]["bytes"] or file_sha(model_path) != prereg["model"]["sha256"]:
        raise BenchmarkRunError("model file drift")
    runtime_path = Path(prereg["runtime"]["executable_path"])
    if not runtime_path.is_file() or file_sha(runtime_path) != prereg["runtime"]["executable_sha256"]:
        raise BenchmarkRunError("runtime executable drift")
    generation = load_json(ROOT / "benchmarks/grounding-generation-config.json")
    isolation = load_json(ROOT / "benchmarks/grounding-isolation-policy.json")
    if isolation.get("arms") != ["A", "G"] or isolation.get("model_answer_calls_per_item_per_arm") != 1 or isolation.get("rewrite_calls") != 0:
        raise BenchmarkRunError("A/G fairness config drift")
    if generation.get("retry_count") != 0 or generation.get("hidden_repair") is not False:
        raise BenchmarkRunError("retry/repair config drift")
    return prereg, candidate_path, generation, isolation


def server_command(prereg: dict[str, Any]) -> list[str]:
    launch = prereg["runtime"]["launch"]
    command = [
        prereg["runtime"]["executable_path"],
        "-m", prereg["model"]["path"],
        "--alias", launch["alias"],
        "--host", launch["host"],
        "--port", str(launch["port"]),
        "-c", str(launch["context"]),
        "-t", str(launch["threads"]),
        "--parallel", str(launch["parallel"]),
    ]
    if launch.get("jinja"):
        command.append("--jinja")
    if launch.get("webui") is False:
        command.append("--no-webui")
    if launch.get("offline"):
        command.append("--offline")
    if launch.get("mmproj") is False:
        command.append("--no-mmproj")
    command.extend(["--reasoning", str(launch.get("reasoning", "off"))])
    if launch.get("cache_prompt") is False:
        command.append("--no-cache-prompt")
    return command


def wait_server(process: subprocess.Popen[bytes], host: str, port: int, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    urls = [f"http://{host}:{port}/health", f"http://{host}:{port}/props"]
    while time.monotonic() < deadline:
        code = process.poll()
        if code is not None:
            raise BenchmarkRunError(f"llama-server exited during startup: {code}")
        for url in urls:
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if 200 <= response.status < 300:
                        return
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
        time.sleep(0.5)
    raise BenchmarkRunError("llama-server readiness timeout")


def parse_model_output_strict(content: str) -> dict[str, Any] | None:
    def unique_object(pairs):
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value

    def reject_constant(token: str):
        raise ValueError(f"non-finite JSON constant: {token}")

    try:
        parsed = json.loads(content, object_pairs_hook=unique_object, parse_constant=reject_constant)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(parsed, dict) or set(parsed) != {"a", "disposition"}:
        return None
    answer = parsed.get("a")
    disposition = parsed.get("disposition")
    if answer is not None and not isinstance(answer, str):
        return None
    if disposition not in {"answer", "abstain", "clarify", "conflict", "unavailable"}:
        return None
    if disposition == "answer":
        if not isinstance(answer, str) or not answer.strip():
            return None
    elif answer not in (None, ""):
        return None
    return parsed


def request_model(prereg: dict[str, Any], generation: dict[str, Any], messages: list[dict[str, str]]) -> dict[str, Any]:
    launch = prereg["runtime"]["launch"]
    payload = {
        "model": launch["alias"],
        "stream": False,
        "temperature": generation["temperature"],
        "seed": generation["seed"],
        "max_tokens": generation["max_output_tokens"],
        "messages": messages,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "grounding_answer",
                "schema": generation["answer_schema"],
            },
        },
    }
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"http://{launch['host']}:{launch['port']}/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter_ns()
    try:
        with urllib.request.urlopen(request, timeout=generation["timeout_seconds"]) as response:
            raw_bytes = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise BenchmarkRunError(f"llama.cpp HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise BenchmarkRunError(f"llama.cpp request failed: {exc}") from exc
    latency_us = (time.perf_counter_ns() - started + 500) // 1_000
    raw = json.loads(raw_bytes)
    choices = raw.get("choices") if isinstance(raw, dict) else None
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise BenchmarkRunError("llama.cpp response lacks exactly one choice")
    message = choices[0].get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise BenchmarkRunError("llama.cpp response lacks textual content")
    content = message["content"]
    parsed = parse_model_output_strict(content)
    usage = raw.get("usage") if isinstance(raw.get("usage"), dict) else {}
    return {
        "raw_content": content,
        "model_output": parsed,
        "input_tokens": usage.get("prompt_tokens") if isinstance(usage.get("prompt_tokens"), int) else None,
        "output_tokens": usage.get("completion_tokens") if isinstance(usage.get("completion_tokens"), int) else None,
        "model_latency_us": latency_us,
        "finish_reason": choices[0].get("finish_reason") if isinstance(choices[0].get("finish_reason"), str) else None,
    }


def write_sums(output: Path) -> None:
    paths = sorted((path for path in output.rglob("*") if path.is_file() and path.name != "SHA256SUMS"), key=lambda p: p.relative_to(output).as_posix())
    text = "".join(f"{file_sha(path)}  {path.relative_to(output).as_posix()}\n" for path in paths)
    (output / "SHA256SUMS").write_text(text, encoding="utf-8", newline="\n")


def execute(prereg_path: Path, output: Path) -> None:
    prereg, candidate_path, generation, _ = verify_frozen_inputs(prereg_path, output)
    manifest, bundle, questions, faults = load_serving(candidate_path)
    if len(questions) != prereg["candidate"]["item_count"] or manifest["candidate_id"] != prereg["candidate"]["candidate_id"]:
        raise BenchmarkRunError("serving corpus drift")
    output.mkdir(parents=True)
    (output / "logs").mkdir()
    shutil.copyfile(prereg_path, output / "preregistration.json")
    run_status_path = output / "run-status.json"
    raw_path = output / "raw-results.jsonl"
    server_log_path = output / "logs/llama-server.log"
    command = server_command(prereg)
    metadata = {
        "format": "exactscope.grounding-benchmark.run-metadata",
        "format_version": "0.1",
        "run_id": prereg["run_id"],
        "candidate_id": prereg["candidate"]["candidate_id"],
        "model_id": prereg["model"]["id"],
        "preregistration_sha256": file_sha(prereg_path),
        "server_command": command,
        "answer_calls_per_arm": 1,
        "arms": ["A", "G"],
        "rewrite_calls": 0,
        "retry_count": 0,
        "hidden_repair": False,
    }
    (output / "run-metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    env = os.environ.copy()
    runtime_dir = str(Path(prereg["runtime"]["executable_path"]).resolve().parent)
    env["LD_LIBRARY_PATH"] = runtime_dir + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    records: list[dict[str, Any]] = []
    process: subprocess.Popen[bytes] | None = None
    try:
        with server_log_path.open("wb") as server_log:
            process = subprocess.Popen(command, cwd=runtime_dir, stdout=server_log, stderr=subprocess.STDOUT, env=env)
            launch = prereg["runtime"]["launch"]
            runtime_record = load_json(ROOT / "benchmarks/grounding-runtime-llama-v040.json")
            wait_server(process, launch["host"], int(launch["port"]), float(runtime_record["server_ready_timeout_seconds"]))
            with raw_path.open("wb") as raw_handle:
                for question in questions:
                    item_id = question["item_id"]
                    base_messages = [
                        {"role": "system", "content": generation["system_prompt"]},
                        {"role": "user", "content": question["question"]},
                    ]
                    a_reply = request_model(prereg, generation, base_messages)
                    a_record = {"v": 1, "item_id": item_id, "arm": "A", **a_reply}
                    records.append(a_record)
                    raw_handle.write(canonical_bytes(a_record) + b"\n")
                    raw_handle.flush()

                    envelope = {
                        "v": 1,
                        "qid": item_id,
                        "profile_sha256": bundle.profile_sha256,
                        "q": question["question"],
                        "security_scope_id": question["security_scope_id"],
                    }
                    retrieval_started = time.perf_counter_ns()
                    grounding = run_grounding(bundle, envelope, FaultProvider(bundle, faults.get(item_id)))
                    retrieval_us = (time.perf_counter_ns() - retrieval_started + 500) // 1_000
                    policy = grounding["projection"]["policy"].decode("utf-8")
                    evidence = grounding["projection"]["evidence"].decode("utf-8")
                    g_messages = [
                        {"role": "system", "content": generation["system_prompt"] + "\n\n" + policy},
                        {"role": "user", "content": question["question"] + "\n\n" + evidence},
                    ]
                    g_reply = request_model(prereg, generation, g_messages)
                    g_record = {
                        "v": 1,
                        "item_id": item_id,
                        "arm": "G",
                        **g_reply,
                        "retrieval_latency_us": retrieval_us,
                        "projection_bytes": len(grounding["projection"]["evidence"]),
                        "projection_sha256": sha256_bytes(grounding["projection"]["evidence"]),
                        "frame": grounding["frame"],
                        "audit": grounding["audit"],
                    }
                    records.append(g_record)
                    raw_handle.write(canonical_bytes(g_record) + b"\n")
                    raw_handle.flush()
        expected = len(questions) * 2
        if len(records) != expected or len({(row["item_id"], row["arm"]) for row in records}) != expected:
            raise BenchmarkRunError("incomplete or duplicate run records")
        status = {
            "state": "complete",
            "run_id": prereg["run_id"],
            "model_id": prereg["model"]["id"],
            "item_count": len(questions),
            "record_count": len(records),
            "model_answer_requests": len(records),
            "expected_model_answer_requests": len(questions) * 2,
            "rewrite_calls": 0,
            "retry_count": 0,
            "preregistration_sha256": file_sha(prereg_path),
        }
        run_status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        write_sums(output)
        print(json.dumps(status, indent=2, sort_keys=True))
    except KeyboardInterrupt:
        status = {
            "state": "aborted",
            "run_id": prereg["run_id"],
            "model_id": prereg["model"]["id"],
            "record_count": len(records),
            "error": "user-interrupt",
            "resume_permitted": False,
        }
        run_status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        write_sums(output)
        raise
    except Exception as exc:
        status = {
            "state": "invalid",
            "run_id": prereg["run_id"],
            "model_id": prereg["model"]["id"],
            "record_count": len(records),
            "error": str(exc),
            "resume_permitted": False,
        }
        run_status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        write_sums(output)
        raise
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true", help="verify every frozen input without launching llama-server or performing inference")
    args = parser.parse_args()
    prereg_path = args.preregistration.resolve()
    output = args.output.resolve()
    if args.verify_only:
        prereg, candidate_path, generation, isolation = verify_frozen_inputs(prereg_path, output)
        manifest, _, questions, _ = load_serving(candidate_path)
        if len(questions) != prereg["candidate"]["item_count"] or manifest["candidate_id"] != prereg["candidate"]["candidate_id"]:
            raise BenchmarkRunError("serving corpus drift")
        print(json.dumps({
            "status": "ready-to-run",
            "run_id": prereg["run_id"],
            "model_id": prereg["model"]["id"],
            "item_count": len(questions),
            "arms": isolation["arms"],
            "max_output_tokens": generation["max_output_tokens"],
            "model_inference_performed": False,
        }, indent=2, sort_keys=True))
        return 0
    execute(prereg_path, output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BenchmarkRunError, PreregistrationError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ExactScope grounding benchmark: FAIL: {exc}")
        raise SystemExit(1) from exc
