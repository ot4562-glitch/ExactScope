#!/usr/bin/env python3
"""Build bound host-limited capability bundles for the prerelease evaluation SDK.

The evaluation capabilities deliberately bind an existing generated hot set to the
exact generic no-import Wasm shipped in the SDK. They do not create new formulas,
select hidden operations, or claim target qualification. The semantic profile
exposes xs_eval only; the combined profile exposes the same xs_eval surface plus
bounded xs_calc so A/C/D model qualification can freeze exact public assets before
inference.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from compile_capability import (
    canonical,
    constrained_request_grammar,
    constrained_request_prompt,
    digest,
    load,
    model_surface_contract,
    model_surface_measurements,
    position_aware_calc_grammar,
    source_identity,
    verify_bundle,
    write_bundle,
)
from inspect_wasm import inspect_imports, inspect_memories, parse_sections

ROOT = Path(__file__).resolve().parents[1]
PROFILE_DOMAIN = "quant"
TASK_FAMILY = "mixed-quantitative-core"
SEMANTIC_PROFILE_ID = "quant-core-16-semantic-ai"
COMBINED_PROFILE_ID = "quant-core-16-combined-ai"
PROFILE_REVISION = 1


def read_json(path: Path) -> Any:
    return load(path.read_bytes())


def category_digest(files: dict[str, bytes], names: list[str]) -> str:
    return digest(canonical({name: digest(files[name]) for name in sorted(names)}))


def artifact_measurements(runtime: bytes) -> dict[str, Any]:
    sections = parse_sections(runtime)
    imports = inspect_imports(sections)
    initial, maximum = inspect_memories(sections)
    if imports != 0:
        raise ValueError("evaluation capability runtime must have zero imports")
    return {
        "bytes": len(runtime),
        "imports": imports,
        "initial_memory_pages": initial,
        "maximum_memory_pages": maximum,
    }


def base_files(hotset_dir: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    required = ("catalog.json", "prompt-fragment.txt", "xs-eval.tool.json", "xs-eval.gbnf")
    for name in required:
        if not (hotset_dir / name).is_file():
            raise ValueError(f"hot set is missing required evaluation asset: {name}")
    catalog = read_json(hotset_dir / "catalog.json")
    operations = catalog.get("operations") if isinstance(catalog, dict) else None
    if not isinstance(operations, list) or not operations:
        raise ValueError("evaluation hot set must contain operations")
    files = {
        "catalog.json": canonical(catalog),
        "prompt-fragment.txt": (hotset_dir / "prompt-fragment.txt").read_bytes(),
        "xs-eval.tool.json": canonical(read_json(hotset_dir / "xs-eval.tool.json")),
        "xs-eval.gbnf": (hotset_dir / "xs-eval.gbnf").read_bytes(),
    }
    return files, catalog


def build_profile(
    *,
    profile_id: str,
    catalog: dict[str, Any],
    files: dict[str, bytes],
    runtime: bytes,
    combined: bool,
    measurements: dict[str, Any],
) -> dict[str, Any]:
    operations = [entry["op"] for entry in catalog["operations"]]
    tool_names = [name for name in files if name.endswith(".tool.json")]
    grammar_names = [name for name in files if name.endswith(".gbnf")]
    prompt_names = sorted(
        name for name in ("prompt-fragment.txt", "constrained-prompt.txt") if name in files
    )
    profile: dict[str, Any] = {
        "format": "exactscope.capability.profile",
        "format_version": "0.1-draft",
        "profile_id": profile_id,
        "profile_revision": PROFILE_REVISION,
        "support": "experimental",
        "domain": PROFILE_DOMAIN,
        "task_families": [TASK_FAMILY],
        "runtime_surface": {
            "xs_calc": {
                "enabled": combined,
                "plan_revision": "plan-v0.1" if combined else None,
            },
            "xs_eval": {"operations": operations},
            "xs_find": {"enabled": False},
            "model_visible_tools_max": 2 if combined else 1,
            "normal_model_turns_max": 1,
            "specialization": "host-limited",
        },
        "model_budget": {
            "semantic_operation_count": len(operations),
            "prompt_fragment_bytes_max": 1024,
            "schema_bytes_max": 4096,
            "grammar_bytes_max": 16384,
            "generated_request_tokens_max": 256,
            "request_bytes_max": 512,
            "plan_steps_max": 8 if combined else 0,
            "normal_model_turns_max": 1,
        },
        "device_budget": {
            "target_profile": "no-import-wasm",
            "artifact_bytes_max": max(131072, len(runtime)),
            "resident_bytes_max": None,
            "scratch_bytes_max": None,
            "imports_max": 0,
            "wasm_stack_bytes_max": None,
            "wasm_initial_pages_max": measurements["initial_memory_pages"],
            "wasm_maximum_pages_max": measurements["maximum_memory_pages"],
        },
        "bindings": {
            "core_revision": "sha256:" + source_identity(),
            "abi_revision": catalog["abi"],
            "registry_sha256": digest(canonical(catalog["packs"])),
            "hotset_sha256": catalog["binding_sha256"],
            "tool_schema_sha256": category_digest(files, tool_names),
            "grammar_sha256": category_digest(files, grammar_names),
            "prompt_sha256": category_digest(files, prompt_names),
            "artifact_sha256": digest(runtime),
            "surface_contract_sha256": None,
            "profile_generator": "tools/build_evaluation_capabilities.py@0.1",
        },
        "evidence": {
            "conformance_suite": None,
            "conformance_sha256": None,
            "benchmark_mapping": "benchmark-mapping.jsonl",
            "benchmark_mapping_sha256": files.get("benchmark-mapping.jsonl")
            and digest(files["benchmark-mapping.jsonl"]),
            "qualification_records": [],
            "model_result_bundles": [],
        },
    }
    return profile


def build_one(
    *,
    hotset_dir: Path,
    runtime_path: Path,
    corpus_path: Path,
    combined: bool,
) -> dict[str, bytes]:
    files, catalog = base_files(hotset_dir)
    runtime = runtime_path.read_bytes()
    if not runtime:
        raise ValueError("evaluation capability runtime is empty")
    measurements = artifact_measurements(runtime)
    files["runtime.wasm"] = runtime
    files["benchmark-mapping.jsonl"] = corpus_path.read_bytes()

    profile_id = COMBINED_PROFILE_ID if combined else SEMANTIC_PROFILE_ID
    if combined:
        calc_root = ROOT / "adapters" / "xs-calc-v0.1"
        files["xs-calc.tool.json"] = canonical(read_json(calc_root / "xs-calc.tool.json"))
        files["xs-calc.gbnf"] = position_aware_calc_grammar()
        files["xs-calc.contract.json"] = canonical(read_json(calc_root / "contract.json"))
        files["prompt-fragment.txt"] += (
            b"Use xs_calc only for generic arithmetic without a reviewed semantic method; "
            b"prefer xs_eval for bound economics/statistics methods.\n"
        )

    files["constrained-prompt.txt"] = constrained_request_prompt(
        catalog,
        include_calc=combined,
    )
    files["xs-request.gbnf"] = constrained_request_grammar(
        files.get("xs-eval.gbnf"),
        files.get("xs-calc.gbnf"),
    )

    profile = build_profile(
        profile_id=profile_id,
        catalog=catalog,
        files=files,
        runtime=runtime,
        combined=combined,
        measurements=measurements,
    )
    files["task-map.json"] = canonical({TASK_FAMILY: profile["runtime_surface"]["xs_eval"]["operations"]})
    contract = model_surface_contract(profile, catalog, files)
    files["surface-contract.json"] = canonical(contract)
    profile["bindings"]["surface_contract_sha256"] = digest(files["surface-contract.json"])
    files["profile.json"] = canonical(profile)

    manifest = {
        "format": "exactscope.capability.bundle",
        "format_version": "0.1",
        "files": {name: digest(data) for name, data in sorted(files.items())},
        "measurements": model_surface_measurements(files, catalog),
        "operation_revisions": {
            operation["op"]: operation["revision"] for operation in catalog["operations"]
        },
        "artifact_status": (
            "artifact-bound host-limited evaluation capability; prerelease qualification input, "
            "not target-qualified"
        ),
        "artifact_measurements": measurements,
        "generator_sha256": digest(Path(__file__).read_text(encoding="utf-8").encode("utf-8")),
    }
    files["manifest.json"] = canonical(manifest)
    files["bundle-sha256.txt"] = (digest(files["manifest.json"]) + "\n").encode("ascii")
    return files


def build_set(
    *,
    hotset_dir: Path,
    runtime_path: Path,
    corpus_path: Path,
    output_root: Path,
) -> dict[str, dict[str, Any]]:
    if not hotset_dir.is_dir():
        raise ValueError(f"evaluation hot set missing: {hotset_dir}")
    if not runtime_path.is_file():
        raise ValueError(f"evaluation runtime missing: {runtime_path}")
    if not corpus_path.is_file():
        raise ValueError(f"benchmark corpus missing: {corpus_path}")

    result: dict[str, dict[str, Any]] = {}
    for lane, combined in (("semantic", False), ("combined", True)):
        destination = output_root / (SEMANTIC_PROFILE_ID if not combined else COMBINED_PROFILE_ID)
        write_bundle(
            build_one(
                hotset_dir=hotset_dir,
                runtime_path=runtime_path,
                corpus_path=corpus_path,
                combined=combined,
            ),
            destination,
        )
        manifest = verify_bundle(destination)
        profile = read_json(destination / "profile.json")
        result[lane] = {
            "path": destination.name,
            "profile_id": profile["profile_id"],
            "profile_revision": profile["profile_revision"],
            "bundle_sha256": (destination / "bundle-sha256.txt").read_text(encoding="ascii").strip(),
            "surface_contract_sha256": profile["bindings"]["surface_contract_sha256"],
            "artifact_sha256": profile["bindings"]["artifact_sha256"],
            "model_visible_tools": manifest["measurements"]["top_level_tool_count"],
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hotset", type=Path, default=ROOT / "adapters/generated/quant-core-16")
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, default=ROOT / "benchmarks/corpus-v0.1.jsonl")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_set(
        hotset_dir=args.hotset,
        runtime_path=args.runtime,
        corpus_path=args.corpus,
        output_root=args.output,
    )
    print(canonical(result).decode("ascii").strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
