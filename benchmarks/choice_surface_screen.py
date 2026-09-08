"""Synthetic finite-choice renderer calibration; never a benchmark accuracy claim.

The screen uses only invented labels/entities/rules. Every renderer receives the
same ChoiceSpec, schema, decoding settings, and one request per frozen case.
Non-null renderer selection is independent from optional-null qualification.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any
import urllib.error
import urllib.request

from choice_codec import ChoiceSuccess, parse_choice, schema_json
from choice_contract import ChoiceSpec, contract_hash, surface_hash
from choice_prompt import RENDERER_IDS, RENDERER_PREFERENCE, render_choice_variant, renderer_hash


COPY_SPEC = ChoiceSpec(
    (("dax", "Declared token dax."), ("pel", "Declared token pel."), ("vek", "Declared token vek.")),
    "For mode copy, return the exact declared label in target.",
)
EVIDENCE_SPEC = ChoiceSpec(
    (("dax", "Listed facts explicitly support the claim."),
     ("pel", "Listed facts explicitly contradict the claim."),
     ("vek", "Listed facts establish neither support nor contradiction.")),
    "For mode judge, use only listed facts and choose the label whose description matches the relation between claim and facts. Absence is not contradiction.",
)
NUMERIC_SPEC = ChoiceSpec(
    (("dax", "The integer value is less than 0."),
     ("pel", "The integer value is from 0 through 9 inclusive."),
     ("vek", "The integer value is 10 or greater.")),
    "For mode interval, read integer value and choose the label whose described numeric interval contains it.",
)
PRECEDENCE_SPEC = ChoiceSpec(
    (("dax", "Red has highest priority."),
     ("pel", "Blue has middle priority."),
     ("vek", "Green has lowest priority.")),
    "For mode precedence, enabled contains one or more colors. Choose the label whose described color has the highest priority among enabled colors.",
)
NULL_SPEC = ChoiceSpec(
    COPY_SPEC.labels,
    "For mode abstain, return null. Otherwise, for mode copy return the exact declared label in target.",
    "Mode abstain explicitly requests abstention.",
)


@dataclass(frozen=True, slots=True)
class Case:
    name: str
    family: str
    input_value: Any
    expected: str | None
    spec: ChoiceSpec


CASES = (
    Case("copy-dax", "copy", {"mode": "copy", "target": "dax"}, "dax", COPY_SPEC),
    Case("copy-pel", "copy", {"mode": "copy", "target": "pel"}, "pel", COPY_SPEC),
    Case("copy-vek", "copy", {"mode": "copy", "target": "vek"}, "vek", COPY_SPEC),
    Case("evidence-support", "evidence", {"mode": "judge", "claim": "Nemi is copper.", "facts": ["Nemi is copper."]}, "dax", EVIDENCE_SPEC),
    Case("evidence-contradict", "evidence", {"mode": "judge", "claim": "Nemi is copper.", "facts": ["Nemi is not copper."]}, "pel", EVIDENCE_SPEC),
    Case("evidence-insufficient", "evidence", {"mode": "judge", "claim": "Nemi is copper.", "facts": ["Nemi is round."]}, "vek", EVIDENCE_SPEC),
    Case("numeric-negative", "numeric", {"mode": "interval", "value": -7}, "dax", NUMERIC_SPEC),
    Case("numeric-middle", "numeric", {"mode": "interval", "value": 4}, "pel", NUMERIC_SPEC),
    Case("numeric-high", "numeric", {"mode": "interval", "value": 14}, "vek", NUMERIC_SPEC),
    Case("precedence-red", "precedence", {"mode": "precedence", "enabled": ["green", "red"]}, "dax", PRECEDENCE_SPEC),
    Case("precedence-blue", "precedence", {"mode": "precedence", "enabled": ["green", "blue"]}, "pel", PRECEDENCE_SPEC),
    Case("precedence-green", "precedence", {"mode": "precedence", "enabled": ["green"]}, "vek", PRECEDENCE_SPEC),
)
NULL_CASE = Case("null-enabled", "null", {"mode": "abstain"}, None, NULL_SPEC)
RUN_CASES = CASES + (NULL_CASE,)
SEMANTIC_FAMILIES = ("evidence", "numeric", "precedence")


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pinned_record(path, expected):
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"record hash mismatch: {path}")
    return json.loads(data)


def verify_inputs(args):
    runtime = pinned_record(args.runtime_record, args.runtime_sha256)
    inventory = pinned_record(args.inventory, args.inventory_sha256)
    matches = [record for record in inventory["records"] if record["id"] == args.model_id]
    if runtime["family"] != "llama.cpp" or len(matches) != 1:
        raise ValueError("requires llama.cpp and exactly one matching model record")
    model = matches[0]
    if model["runtime"] != "llama.cpp":
        raise ValueError("model runtime must be llama.cpp")
    executable = Path(args.executable).resolve()
    model_path = Path(args.model).resolve()
    if file_sha(executable) != runtime["executable_sha256"]:
        raise ValueError("executable hash mismatch")
    if model_path.stat().st_size != model["bytes"] or file_sha(model_path) != model["sha256"]:
        raise ValueError("model size/hash mismatch")
    identity = {
        "runtime_record_sha256": args.runtime_sha256,
        "inventory_sha256": args.inventory_sha256,
        "runtime_id": runtime["runtime_id"],
        "executable_sha256": runtime["executable_sha256"],
        "model_id": model["id"],
        "model_sha256": model["sha256"],
        "model_bytes": model["bytes"],
        "model_path": str(model_path),
    }
    return runtime, executable, model_path, identity


def server_command(runtime, executable, model):
    launch = runtime["launch"]
    if launch["host"] != "127.0.0.1":
        raise ValueError("screen requires loopback host 127.0.0.1")
    command = [str(executable), "-m", str(model)]
    for key, flag in (("alias", "--alias"), ("host", "--host"), ("port", "--port"),
                      ("context", "-c"), ("threads", "-t"), ("parallel", "--parallel")):
        command.extend([flag, str(launch[key])])
    for key, value, flag in (("jinja", True, "--jinja"), ("webui", False, "--no-webui"),
                             ("offline", True, "--offline"), ("mmproj", False, "--no-mmproj"),
                             ("cache_prompt", False, "--no-cache-prompt")):
        if launch.get(key) is value:
            command.append(flag)
    command.extend(["--reasoning", str(launch.get("reasoning", "off"))])
    return command


def wait_server(process, launch, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("llama-server exited during startup")
        try:
            with urllib.request.urlopen(f"http://{launch['host']}:{launch['port']}/health", timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.5)
    raise TimeoutError("llama-server readiness timeout")


def request_model(launch, payload):
    request = urllib.request.Request(
        f"http://{launch['host']}:{launch['port']}/v1/chat/completions",
        data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read().decode("utf-8", errors="strict")


def _run_case(launch, identity, renderer_id: str, case: Case, request) -> dict[str, Any]:
    schema = schema_json(case.spec).decode("utf-8")
    payload = {
        "model": launch["alias"],
        "stream": False,
        "temperature": 0,
        "seed": 0,
        "max_tokens": 32,
        "n": 1,
        "messages": render_choice_variant(case.spec, case.input_value, renderer_id),
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "choice_answer", "schema": json.loads(schema),
        }},
    }
    row: dict[str, Any] = {
        "renderer_id": renderer_id,
        "renderer_sha256": renderer_hash(renderer_id),
        "case": case.name,
        "family": case.family,
        "expected": case.expected,
        "surface_sha256": surface_hash(case.spec),
        "contract_sha256": contract_hash(case.spec),
        "schema_json": schema,
        "request": payload,
        "raw_response": None,
        "raw_output": None,
        "parse_result": {"type": "ChoiceFailure"},
        "correct": False,
        "input_tokens": None,
        "output_tokens": None,
        "error": None,
    }
    started = time.perf_counter_ns()
    try:
        row["raw_response"] = request(launch, payload)  # Exactly one attempt.
        raw = json.loads(row["raw_response"])
        choices = raw.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise ValueError("response must contain exactly one choice")
        row["raw_output"] = choices[0]["message"]["content"]
        result = parse_choice(row["raw_output"], case.spec)
        row["parse_result"] = {"type": type(result).__name__}
        if isinstance(result, ChoiceSuccess):
            row["parse_result"]["value"] = result.value
            row["correct"] = result.value == case.expected
        usage = raw.get("usage") or {}
        for source, target in (("prompt_tokens", "input_tokens"), ("completion_tokens", "output_tokens")):
            value = usage.get(source)
            row[target] = value if type(value) is int and value >= 0 else None
        row["finish_reason"] = choices[0].get("finish_reason")
        row["timings"] = raw.get("timings")
    except (ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
        if isinstance(exc, urllib.error.HTTPError):
            row["raw_response"] = exc.read().decode("utf-8", errors="replace")
    row["latency_us"] = (time.perf_counter_ns() - started + 500) // 1000
    return row


def _renderer_summary(renderer_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    non_null = [row for row in rows if row["family"] != "null"]
    copy_rows = [row for row in non_null if row["family"] == "copy"]
    semantic_rows = [row for row in non_null if row["family"] in SEMANTIC_FAMILIES]
    reachable = [row["expected"] for row in copy_rows if row["correct"]]
    malformed = sum(row["parse_result"]["type"] == "ChoiceFailure" for row in non_null)
    family_accuracy = {
        family: sum(row["correct"] for row in semantic_rows if row["family"] == family)
        / sum(1 for row in semantic_rows if row["family"] == family)
        for family in SEMANTIC_FAMILIES
    }
    overall_semantic = sum(row["correct"] for row in semantic_rows) / len(semantic_rows)
    copy_ok = set(reachable) == {label for label, _ in COPY_SPEC.labels} and all(not row["error"] for row in copy_rows)
    qualifies = (
        malformed == 0
        and copy_ok
        and all(row["correct"] and not row["error"] for row in semantic_rows)
    )
    null_rows = [row for row in rows if row["family"] == "null"]
    null_ok = bool(null_rows) and all(row["correct"] and not row["error"] for row in null_rows)
    return {
        "renderer_id": renderer_id,
        "renderer_sha256": renderer_hash(renderer_id),
        "qualified_non_null": qualifies,
        "reachable_labels": reachable,
        "malformed_non_null": malformed,
        "family_accuracy": family_accuracy,
        "min_family_accuracy": min(family_accuracy.values()),
        "overall_semantic_accuracy": overall_semantic,
        "null_status": "supported" if null_ok else "unsupported",
    }


def run_screen(launch, identity, request=request_model):
    all_rows: list[dict[str, Any]] = []
    summaries: dict[str, dict[str, Any]] = {}
    for renderer_id in RENDERER_IDS:
        renderer_rows = [
            _run_case(launch, identity, renderer_id, case, request)
            for case in RUN_CASES
        ]
        all_rows.extend(renderer_rows)
        summaries[renderer_id] = _renderer_summary(renderer_id, renderer_rows)

    preference = {renderer_id: position for position, renderer_id in enumerate(RENDERER_PREFERENCE)}
    qualified = [summary for summary in summaries.values() if summary["qualified_non_null"]]
    qualified.sort(key=lambda row: (
        -row["min_family_accuracy"],
        -row["overall_semantic_accuracy"],
        preference[row["renderer_id"]],
    ))
    selected = qualified[0]["renderer_id"] if qualified else None
    selected_summary = summaries.get(selected) if selected is not None else None
    malformed_total = sum(row["parse_result"]["type"] == "ChoiceFailure" for row in all_rows)
    return {
        "purpose": "Synthetic finite-choice renderer calibration; not a benchmark accuracy claim.",
        "identity": identity,
        "screen_source_sha256": file_sha(__file__),
        "status": "supported" if selected is not None else "unsupported",
        "non_null_status": "supported" if selected is not None else "unsupported",
        "null_status": selected_summary["null_status"] if selected_summary is not None else "unsupported",
        "selected_renderer": selected,
        "selected_renderer_sha256": renderer_hash(selected) if selected is not None else None,
        "renderer_preference": list(RENDERER_PREFERENCE),
        "renderers": summaries,
        "malformed_outputs": malformed_total,
        "cases": all_rows,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("runtime-record", "runtime-sha256", "executable", "inventory",
                 "inventory-sha256", "model-id", "model"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    process = None
    identity = {}
    command = None
    try:
        runtime, executable, model, identity = verify_inputs(args)
        command = server_command(runtime, executable, model)
        launch = runtime["launch"]
        with socket.socket() as probe:
            probe.bind((launch["host"], int(launch["port"])))
        env = os.environ.copy()
        if os.name != "nt":
            env["LD_LIBRARY_PATH"] = str(executable.parent) + (
                os.pathsep + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else ""
            )
        process = subprocess.Popen(
            command,
            cwd=executable.parent,
            env=env,
            stdout=sys.stderr,
            stderr=sys.stderr,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        wait_server(process, launch, float(runtime["server_ready_timeout_seconds"]))
        report = run_screen(launch, identity)
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as exc:
        report = {"status": "unsupported", "non_null_status": "unsupported",
                  "null_status": "unsupported", "identity": identity,
                  "error": f"{type(exc).__name__}: {exc}", "cases": []}
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    report["server_command"] = command
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["non_null_status"] == "supported" else 1


if __name__ == "__main__":
    raise SystemExit(main())
