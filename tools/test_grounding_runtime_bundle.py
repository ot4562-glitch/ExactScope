#!/usr/bin/env python3
"""Clean-room C11 smoke test for an extracted ExactScope grounding runtime package."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from package_grounding_runtime import verify_archive


def run(archive: Path) -> dict[str, object]:
    verification = verify_archive(archive)
    manifest = verification["manifest"]
    target = manifest["target"]
    if target != "x86_64-unknown-linux-gnu":
        raise RuntimeError(f"clean-room test does not qualify target {target}")

    with tempfile.TemporaryDirectory(prefix="exactscope-grounding-cleanroom-") as temporary:
        root = Path(temporary)
        with tarfile.open(archive, mode="r:gz") as tar:
            members = tar.getmembers()
            tar.extractall(root, filter="data")
        roots = {member.name.split("/", 1)[0] for member in members}
        if len(roots) != 1:
            raise RuntimeError("archive does not contain one clean-room root")
        package = root / next(iter(roots))
        executable = root / "grounding-demo"
        compile_command = [
            "cc",
            "-std=c11",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            "-Iinclude",
            "examples/c/grounding.c",
            f"lib/{target}/libexactscope_cabi.a",
            "-o",
            str(executable),
        ]
        subprocess.run(compile_command, cwd=package, check=True)

        queries = {
            "warranty": ["warranty", "period"],
            "battery": ["battery", "level"],
        }
        expected = {
            "warranty": "24 months",
            "battery": "73 percent",
        }
        outputs: dict[str, str] = {}
        for name, tokens in queries.items():
            result = subprocess.run(
                [str(executable), "grounding/sample-index-v1.xsgi", *tokens],
                cwd=package,
                check=True,
                text=True,
                capture_output=True,
            )
            output = result.stdout.strip()
            if expected[name] not in output:
                raise RuntimeError(f"clean-room {name} query did not return expected evidence")
            outputs[name] = output

        adapter_result = subprocess.run(
            [
                sys.executable,
                "adapters/llama-cpp/grounding_v1.py",
                "plan",
                "--profile",
                "grounding/reference-profile-v0.1",
                "--question",
                "Where is the help desk?",
                "--contract",
                "answer-object-v3",
            ],
            cwd=package,
            check=True,
            text=True,
            capture_output=True,
        )
        try:
            adapter_plan = json.loads(adapter_result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("bundled v1.1 adapter did not return JSON") from exc
        if adapter_plan.get("route") != "grounded-context" or adapter_plan.get("model_called") is not True:
            raise RuntimeError("bundled v1.1 adapter clean-room plan drift")
        if adapter_plan.get("selected_output_surface") != "json-schema-v1":
            raise RuntimeError("bundled v1.1 adapter default surface drift")

        model_key = "model-sha256:cleanroom;runtime-sha256:cleanroom;surface-config-sha256:cleanroom"
        record_script = r'''
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, "tools")
from grounding_runtime import load_bundle
from grounding_v1_surface import (
    AUTO_CONTRACT_CALIBRATION,
    AUTO_V2_TIE_PREFERENCE,
    OUTPUT_SURFACE_CANDIDATES,
    OUTPUT_SURFACE_PROBE,
    PREFLIGHT_STOPPING_RULE,
    surface_sha256,
)
bundle = load_bundle(Path("grounding/reference-profile-v0.1"))
preferred = AUTO_V2_TIE_PREFERENCE[0]
cases = [
    {"case_id": case_id, "expected": expected, "actual": expected, "valid": True, "correct": True}
    for case_id, _question, _evidence, expected in AUTO_CONTRACT_CALIBRATION
]
profiles = [{"contract": preferred, "score": len(cases), "case_count": len(cases), "cases": cases}]
probe_expected = OUTPUT_SURFACE_PROBE[3]
record = {
    "format": "exactscope.grounding-v1.1-contract-record",
    "format_version": "0.4",
    "model_key": sys.argv[1],
    "model_surface_sha256": surface_sha256(),
    "policy_sha256": hashlib.sha256(bundle.policy).hexdigest(),
    "selected_output_surface": OUTPUT_SURFACE_CANDIDATES[0],
    "selected_contract": preferred,
    "surface_probe_model_requests": 1,
    "contract_calibration_model_requests": len(AUTO_CONTRACT_CALIBRATION),
    "model_request_count": 1 + len(AUTO_CONTRACT_CALIBRATION),
    "retry_count": 0,
    "surface_probes": [
        {"surface": OUTPUT_SURFACE_CANDIDATES[0], "case_id": OUTPUT_SURFACE_PROBE[0], "protocol_valid": True,
         "semantic_match": True, "actual": probe_expected, "error": None}
    ],
    "tie_preference": list(AUTO_V2_TIE_PREFERENCE),
    "profiles": profiles,
    "stopping_rule": PREFLIGHT_STOPPING_RULE,
}
Path("grounding-contract.json").write_text(
    json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
    encoding="utf-8",
)
'''
        subprocess.run([sys.executable, "-B", "-c", record_script, model_key], cwd=package, check=True)
        doctor_result = subprocess.run(
            [
                sys.executable,
                "-B",
                "adapters/llama-cpp/grounding_v1.py",
                "doctor",
                "--profile",
                "grounding/reference-profile-v0.1",
                "--contract-record",
                "grounding-contract.json",
                "--model-key",
                model_key,
            ],
            cwd=package,
            check=True,
            text=True,
            capture_output=True,
        )
        try:
            doctor = json.loads(doctor_result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("bundled v1.1 doctor did not return JSON") from exc
        if doctor.get("status") != "PASS" or doctor.get("network_requests") != 0:
            raise RuntimeError("bundled v1.1 doctor clean-room validation drift")
        if doctor.get("selected_contract") != "answer-object-v3" or doctor.get("selected_output_surface") != "json-schema-v1":
            raise RuntimeError("bundled v1.1 doctor selected identity drift")
        if model_key in doctor_result.stdout:
            raise RuntimeError("bundled v1.1 doctor exposed the raw model key")

        return {
            "status": "PASS",
            "target": target,
            "archive_bytes": verification["archive_bytes"],
            "unpacked_file_bytes": verification["unpacked_file_bytes"],
            "sample_index_bytes": manifest["sample_provider"]["size_bytes"],
            "host_adapter_plan": {
                "route": adapter_plan["route"],
                "model_called": adapter_plan["model_called"],
                "selected_output_surface": adapter_plan["selected_output_surface"],
            },
            "host_adapter_doctor": {
                "status": doctor["status"],
                "network_requests": doctor["network_requests"],
                "selected_contract": doctor["selected_contract"],
                "selected_output_surface": doctor["selected_output_surface"],
            },
            "queries": outputs,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.archive), indent=2, sort_keys=True))
        return 0
    except subprocess.CalledProcessError as exc:
        detail = ""
        if isinstance(exc.stdout, str) and exc.stdout:
            detail += f"\nstdout:\n{exc.stdout}"
        if isinstance(exc.stderr, str) and exc.stderr:
            detail += f"\nstderr:\n{exc.stderr}"
        print(f"ExactScope grounding clean-room: FAIL: {exc}{detail}")
        return 2
    except (OSError, RuntimeError, tarfile.TarError) as exc:
        print(f"ExactScope grounding clean-room: FAIL: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
