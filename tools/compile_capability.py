#!/usr/bin/env python3
"""Build-time capability compiler; runtime semantics and catalogs come from packc.

Canonical JSON is sorted ASCII JSON, no floats, compact separators, one LF.
The manifest hashes every payload; its detached digest avoids self-reference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = {
    "descriptive-aggregation": ["stats.sum", "stats.mean"],
    "weighted-mean": ["stats.mean.weighted"],
    "variance-standard-deviation-method-selection": [
        "stats.var.pop", "stats.var.sample", "stats.sd.pop", "stats.sd.sample"],
    "pearson-correlation": ["stats.corr.pearson"],
    "ambiguity-failure-preservation": [],
}


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load(data):
    return json.loads(data, object_pairs_hook=unique_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def source_identity():
    paths = [ROOT / "Cargo.toml", ROOT / "Cargo.lock", ROOT / "rust-toolchain.toml",
             ROOT / "include/exactscope.h"]
    for crate in ("kernel", "pack", "tinyjson", "cabi", "wasm"):
        base = ROOT / f"crates/exactscope-{crate}"
        paths += [base / "Cargo.toml", *base.glob("src/**/*.rs")]
    # Text normalization makes Windows and Unix checkouts identify the same source.
    return digest(canonical({p.relative_to(ROOT).as_posix(): digest(
        p.read_text(encoding="utf-8").encode("utf-8")) for p in sorted(paths)}))


def validate(profile):
    schema = load((ROOT / "spec/schemas/capability-profile.schema.json").read_bytes())
    Draft202012Validator(schema).validate(profile)
    if profile["support"] != "experimental":
        raise ValueError("compiler v0.1 only emits experimental profiles; evidence is not qualification")
    if profile["domain"] != "statistics":
        raise ValueError("compiler v0.1 supports the reviewed statistics task map only")
    surface, budget = profile["runtime_surface"], profile["model_budget"]
    if surface["xs_find"]["enabled"]:
        raise ValueError("discovery is not a serving capability")
    calc = surface["xs_calc"]
    if calc.get("plan_revision") != ("plan-v0.1" if calc["enabled"] else None):
        raise ValueError("unsupported xs_calc revision/enablement")
    if budget["request_bytes_max"] != 512 or budget["plan_steps_max"] != (8 if calc["enabled"] else 0):
        raise ValueError("request/step budget must match the runtime contract")
    if budget["normal_model_turns_max"] != surface["normal_model_turns_max"]:
        raise ValueError("inconsistent turn budgets")
    unknown = set(profile["task_families"]) - FAMILIES.keys()
    if unknown:
        raise ValueError(f"unknown task families: {sorted(unknown)}")
    selected = sorted({op for family in profile["task_families"] for op in FAMILIES[family]})
    if sorted(surface["xs_eval"]["operations"]) != selected:
        raise ValueError("selected operations do not exactly cover the requested task families")
    if not selected:
        raise ValueError("statistics profile requires at least one computational task family")
    if budget["semantic_operation_count"] != len(selected):
        raise ValueError("semantic operation count disagrees with task selection")
    if 1 + int(calc["enabled"]) > surface["model_visible_tools_max"]:
        raise ValueError("tool count exceeds model budget")
    if any(v is not None for k, v in profile["bindings"].items()):
        raise ValueError("source bindings must be null; compiler derives immutable identities")
    if any(v not in (None, []) for v in profile["evidence"].values()):
        raise ValueError("source evidence must be empty; attach verified evidence separately")
    if budget.get("tokenizer_measurements"):
        raise ValueError("tokenizer measurements belong to measured benchmark output")
    profile.pop("$schema", None)
    profile["task_families"].sort()
    surface["xs_eval"]["operations"] = selected
    return profile


def strict_tool(catalog, tool):
    # Group equal argument shapes to avoid repeating an entire schema per operation.
    groups = {}
    for op in catalog["operations"]:
        shape = tuple(i["shape"] for i in op["args"])
        groups.setdefault(shape, []).append(op["op"])
    leaf = {"type": "string", "minLength": 1, "maxLength": 96,
            "pattern": r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$"}
    variants = []
    for shapes, keys in sorted(groups.items()):
        inputs = [leaf if shape == "scalar" else {
            "type": "array", "items": leaf, "maxItems": 64} for shape in shapes]
        variants.append({"type": "object", "additionalProperties": False,
                         "required": ["op", "a"], "properties": {
                             "op": {"enum": keys}, "a": {"type": "array",
                             "prefixItems": inputs, "minItems": len(inputs),
                             "maxItems": len(inputs)}}})
    tool["function"]["parameters"] = {"oneOf": variants}
    tool["function"]["description"] = "Evaluate one reviewed operation. Exact decimal strings; signature argument order."
    return tool


def compile_profile(source, packc):
    profile = validate(load(source))
    manifest = {"format": "exactscope.hotset.source", "format_version": "0.1",
                "name": profile["profile_id"], "fused_packs": ["statistics-core"],
                "operations": profile["runtime_surface"]["xs_eval"]["operations"],
                "include_find": False}
    with tempfile.TemporaryDirectory(prefix="xs-capability-") as tmp:
        base = Path(tmp)
        (base / "hotset.json").write_bytes(canonical(manifest))
        subprocess.run([str(packc.resolve()), "hotset", str(base / "hotset.json"),
                        str(base / "assets")], check=True, capture_output=True)
        files = {p.name: p.read_bytes() for p in (base / "assets").iterdir()}
    catalog = load(files["catalog.json"])
    files["catalog.json"] = canonical(catalog)
    files["xs-eval.tool.json"] = canonical(strict_tool(catalog, load(files["xs-eval.tool.json"])))
    files["xs-eval.gbnf"] = files["xs-eval.gbnf"].replace(
        b'(ws "," ws decimal-string)*', b'(ws "," ws decimal-string){0,63}')
    prompt = "Pass exact decimal strings in signature order. Never guess missing values or methods. Preserve errors.\n"
    prompt += "\n".join(op["sig"] for op in catalog["operations"]) + "\n"
    if profile["runtime_surface"]["xs_calc"]["enabled"]:
        for name in ("xs-calc.tool.json", "xs-calc.gbnf"):
            data = (ROOT / "adapters/xs-calc-v0.1" / name).read_text(encoding="utf-8").encode()
            files[name] = canonical(load(data)) if name.endswith("json") else data
        prompt += "xs_calc: 1-8 add/sub/mul/div/powi/sqrt steps; backward # references only.\n"
    files["prompt-fragment.txt"] = prompt.encode()
    categories = {"tool_schema": sorted(n for n in files if n.endswith(".tool.json")),
                  "grammar": sorted(n for n in files if n.endswith(".gbnf")),
                  "prompt": ["prompt-fragment.txt"]}
    measures = {"prompt_fragment_bytes": len(files["prompt-fragment.txt"]),
                "schema_bytes": sum(len(files[n]) for n in categories["tool_schema"]),
                "grammar_bytes": sum(len(files[n]) for n in categories["grammar"]),
                "top_level_tool_count": len(categories["tool_schema"]),
                "visible_semantic_operation_count": len(catalog["operations"])}
    for key in ("prompt_fragment_bytes", "schema_bytes", "grammar_bytes"):
        if measures[key] > profile["model_budget"][key + "_max"]:
            raise ValueError(f"{key}={measures[key]} exceeds budget")
    bindings = profile["bindings"]
    bindings.update(core_revision="sha256:" + source_identity(), abi_revision=catalog["abi"],
                    registry_sha256=digest(canonical(catalog["packs"])),
                    hotset_sha256=catalog["binding_sha256"],
                    profile_generator="tools/compile_capability.py@0.1")
    for category, names in categories.items():
        bindings[category + "_sha256"] = digest(canonical({n: digest(files[n]) for n in names}))
    files["task-map.json"] = canonical({f: FAMILIES[f] for f in profile["task_families"]})
    files["profile.json"] = canonical(profile)
    files["manifest.json"] = canonical({
        "format": "exactscope.capability.bundle", "format_version": "0.1",
        "files": {n: digest(data) for n, data in sorted(files.items())},
        "measurements": measures,
        "generator_sha256": digest(Path(__file__).read_text(encoding="utf-8").encode()),
        "operation_revisions": {op["op"]: op["revision"] for op in catalog["operations"]},
        "artifact_status": "unbound; host-enforced surface, not binary specialization",
    })
    files["bundle-sha256.txt"] = (digest(files["manifest.json"]) + "\n").encode()
    return files


def write_bundle(files, output):
    if output.exists():
        actual = {p.name: p.read_bytes() for p in output.iterdir() if p.is_file()}
        if actual != files or any(p.is_dir() for p in output.iterdir()):
            raise ValueError("immutable output differs; use a new directory/revision")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".xs-build-") as tmp:
        stage = Path(tmp) / "bundle"
        stage.mkdir()
        for name, data in files.items():
            (stage / name).write_bytes(data)
        stage.rename(output)


def verify_bundle(path):
    manifest_bytes = (path / "manifest.json").read_bytes()
    if (path / "bundle-sha256.txt").read_text().strip() != digest(manifest_bytes):
        raise ValueError("manifest digest mismatch")
    manifest = load(manifest_bytes)
    if canonical(manifest) != manifest_bytes:
        raise ValueError("noncanonical manifest")
    if set(p.name for p in path.iterdir()) != set(manifest["files"]) | {"manifest.json", "bundle-sha256.txt"}:
        raise ValueError("bundle file inventory mismatch")
    for name, expected in manifest["files"].items():
        if Path(name).name != name or digest((path / name).read_bytes()) != expected:
            raise ValueError(f"asset digest mismatch: {name}")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--packc", type=Path, default=ROOT / "target/debug" / (
        "exactscope-packc.exe" if os.name == "nt" else "exactscope-packc"))
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        verify_bundle(args.source)
    else:
        if args.output is None:
            parser.error("output directory required")
        write_bundle(compile_profile(args.source.read_bytes(), args.packc), args.output)
    print("PASS capability bundle")


if __name__ == "__main__":
    main()
