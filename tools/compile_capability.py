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
DOMAIN_DESCRIPTORS_PATH = ROOT / "spec/capabilities/domain-descriptors.json"

MODEL_SURFACE_FORMAT = "exactscope.model-surface.contract"
MODEL_SURFACE_VERSION = "0.1"
MODEL_SURFACE_NEGOTIATION = "exact-version-and-digest"
MODEL_SURFACE_ASSETS = {
    "xs-calc.tool.json": ("tool-schema", "exactscope.xs-calc.tool", "0.1"),
    "xs-eval.tool.json": ("tool-schema", "exactscope.xs-eval.tool", "0.1"),
    "xs-calc.gbnf": ("grammar", "exactscope.xs-calc.gbnf", "0.1"),
    "xs-eval.gbnf": ("grammar", "exactscope.xs-eval.gbnf", "0.1"),
    "prompt-fragment.txt": ("prompt", "exactscope.prompt-fragment", "0.1"),
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


def domain_descriptors():
    document = load(DOMAIN_DESCRIPTORS_PATH.read_bytes())
    if (document.get("format") != "exactscope.capability.domain-descriptors"
            or document.get("format_version") != "0.1"
            or not isinstance(document.get("domains"), dict)):
        raise ValueError("unsupported capability domain descriptor map")
    domains = document["domains"]
    if not domains:
        raise ValueError("capability domain descriptor map is empty")
    required = {"fused_pack", "semantic_source", "task_families", "implementation_bindings",
                "specialization", "specialization_feature"}
    for domain, descriptor in domains.items():
        if (not isinstance(domain, str) or not isinstance(descriptor, dict)
                or set(descriptor) != required):
            raise ValueError(f"invalid capability domain descriptor: {domain}")
        for field in ("semantic_source", "task_families", "implementation_bindings"):
            path = (ROOT / descriptor[field]).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file():
                raise ValueError(f"invalid capability domain path: {domain}.{field}")
    return domains


DOMAINS = domain_descriptors()


def domain_descriptor(domain):
    try:
        return DOMAINS[domain]
    except KeyError as error:
        raise ValueError(f"unsupported capability domain: {domain}") from error


def domain_path(domain, field):
    return (ROOT / domain_descriptor(domain)[field]).resolve()


def task_families(domain):
    document = load(domain_path(domain, "task_families").read_bytes())
    if (document.get("format") != "exactscope.capability.task-family-map"
            or document.get("format_version") != "0.1"
            or document.get("domain") != domain
            or not isinstance(document.get("families"), dict)):
        raise ValueError(f"unsupported {domain} task-family map")
    families = document["families"]
    if not families or any(not isinstance(name, str) or not isinstance(ops, list)
                           for name, ops in families.items()):
        raise ValueError(f"invalid {domain} task-family map")
    if "arithmetic-baseline" in families and set(families["arithmetic-baseline"]):
        raise ValueError("arithmetic-baseline must not select semantic operations")
    source = load(domain_path(domain, "semantic_source").read_bytes())
    source_operations = source.get("operations") if isinstance(source, dict) else None
    if not isinstance(source_operations, list):
        raise ValueError(f"{domain} semantic source has no operations array")
    source_keys = {op.get("key") for op in source_operations if isinstance(op, dict)}
    operations = [op for ops in families.values() for op in ops]
    if any(not isinstance(op, str) or op not in source_keys for op in operations):
        raise ValueError(f"{domain} task-family operation is absent from reviewed semantic source")
    return families


STATISTICS_FAMILIES = task_families("statistics")
STATISTICS_CORE_8 = sorted({op for operations in STATISTICS_FAMILIES.values() for op in operations})


def operation_features(domain):
    """Load build feature bindings while requiring exact reviewed-source key coverage."""
    source = load(domain_path(domain, "semantic_source").read_bytes())
    bindings = load(domain_path(domain, "implementation_bindings").read_bytes())
    operations = source.get("operations") if isinstance(source, dict) else None
    binding_operations = bindings.get("operations") if isinstance(bindings, dict) else None
    if not isinstance(operations, list):
        raise ValueError(f"{domain} semantic source has no operations array")
    if (bindings.get("format_version") != "0.1"
            or bindings.get("domain") != domain
            or not isinstance(bindings.get("format"), str)
            or not isinstance(binding_operations, list)):
        raise ValueError(f"unsupported {domain} implementation bindings")
    reviewed_keys = []
    for operation in operations:
        if not isinstance(operation, dict) or not isinstance(operation.get("key"), str):
            raise ValueError(f"{domain} semantic operation has no canonical key")
        reviewed_keys.append(operation["key"])
    features = {}
    for binding in binding_operations:
        if not isinstance(binding, dict):
            raise ValueError(f"invalid {domain} implementation binding")
        key, feature = binding.get("key"), binding.get("cargo_feature")
        if not isinstance(key, str) or not isinstance(feature, str):
            raise ValueError(f"invalid {domain} operation/feature binding")
        if key in features or feature in features.values():
            raise ValueError(f"duplicate {domain} operation/feature: {key}")
        features[key] = feature
    if set(features) != set(reviewed_keys):
        raise ValueError(f"{domain} implementation bindings do not cover the reviewed source exactly")
    return features


STATISTICS_OPERATION_FEATURES = operation_features("statistics")
if not set(STATISTICS_CORE_8).issubset(STATISTICS_OPERATION_FEATURES):
    raise ValueError("Statistics task-family map references operations without implementation bindings")


def specialization_features(profile):
    domain = profile["domain"]
    descriptor = domain_descriptor(domain)
    operations = profile["runtime_surface"]["xs_eval"]["operations"]
    features = operation_features(domain)
    try:
        selected_features = [features[op] for op in operations]
    except KeyError as error:
        raise ValueError(f"no build feature for selected operation: {error.args[0]}") from error
    runtime_features = ["fused", "tinyjson", descriptor["specialization_feature"]]
    if profile["runtime_surface"]["xs_calc"]["enabled"]:
        runtime_features.append("selected-calc")
    runtime_features.extend(selected_features)
    return tuple(runtime_features)


def statistics_specialization_features(profile):
    """Compatibility wrapper used by older Statistics build/bind tooling."""
    if profile.get("domain") != "statistics":
        raise ValueError("Statistics specialization requested for a non-Statistics profile")
    return specialization_features(profile)


def source_identity():
    paths = [ROOT / "Cargo.toml", ROOT / "Cargo.lock", ROOT / "rust-toolchain.toml",
             ROOT / "include/exactscope.h", ROOT / ".cargo/config.toml",
             DOMAIN_DESCRIPTORS_PATH, ROOT / "tools/generate_statistics_metadata.py",
             ROOT / "tools/generate_domain_metadata.py"]
    for descriptor in DOMAINS.values():
        for field in ("semantic_source", "task_families", "implementation_bindings"):
            paths.append((ROOT / descriptor[field]).resolve())
    for crate in ("kernel", "pack", "tinyjson", "cabi", "wasm"):
        base = ROOT / f"crates/exactscope-{crate}"
        paths += [base / "Cargo.toml", *base.glob("src/**/*.rs")]
        if (base / "build.rs").exists():
            paths.append(base / "build.rs")
    # Text normalization makes Windows and Unix checkouts identify the same source.
    return digest(canonical({p.relative_to(ROOT).as_posix(): digest(
        p.read_text(encoding="utf-8").encode("utf-8")) for p in sorted(paths)}))


def validate(profile):
    schema = load((ROOT / "spec/schemas/capability-profile.schema.json").read_bytes())
    Draft202012Validator(schema).validate(profile)
    if profile["support"] != "experimental":
        raise ValueError("compiler v0.1 only emits experimental profiles; evidence is not qualification")
    domain = profile["domain"]
    descriptor = domain_descriptor(domain)
    families_map = task_families(domain)
    feature_map = operation_features(domain)
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
    unknown = set(profile["task_families"]) - families_map.keys()
    if unknown:
        raise ValueError(f"unknown task families: {sorted(unknown)}")
    families = set(profile["task_families"])
    selected = sorted({op for family in profile["task_families"] for op in families_map[family]})
    if sorted(surface["xs_eval"]["operations"]) != selected:
        raise ValueError("selected operations do not exactly cover the requested task families")
    specialization = surface.get("specialization", "host-limited")
    calc_only = (
        domain == "statistics"
        and not selected
        and calc["enabled"]
        and specialization == descriptor["specialization"]
        and families == {"arithmetic-baseline"}
    )
    if "arithmetic-baseline" in families and not calc_only:
        raise ValueError("arithmetic-baseline is reserved for the calc-only Statistics baseline")
    if not selected and not calc_only:
        raise ValueError(f"{domain} profile requires a computational task family")
    if budget["semantic_operation_count"] != len(selected):
        raise ValueError("semantic operation count disagrees with task selection")
    specialized = specialization == descriptor["specialization"]
    historical_statistics = specialization == "statistics-core-8-wasm"
    if specialization not in ("host-limited", descriptor["specialization"], "statistics-core-8-wasm"):
        raise ValueError(f"unsupported specialization for {domain}: {specialization}")
    if historical_statistics and domain != "statistics":
        raise ValueError("historical Statistics specialization cannot serve another domain")
    if specialized or historical_statistics:
        device = profile["device_budget"]
        if historical_statistics and selected != STATISTICS_CORE_8:
            raise ValueError("Statistics-8 Wasm specialization requires the exact reviewed eight-operation surface")
        if any(op not in feature_map for op in selected):
            raise ValueError(f"selected {domain} operation has no build-time specialization feature")
        if device["target_profile"] != "no-import-wasm" or device.get("imports_max") != 0:
            raise ValueError(f"{domain} specialization requires the no-import Wasm profile")
        if (device.get("wasm_stack_bytes_max") != 16384 or
                device.get("wasm_initial_pages_max") != 1 or
                device.get("wasm_maximum_pages_max") != 1):
            raise ValueError(f"{domain} specialization requires the measured 16 KiB / fixed one-page Wasm budget")
    visible_tool_count = int(bool(selected)) + int(calc["enabled"])
    if visible_tool_count == 0 or visible_tool_count > surface["model_visible_tools_max"]:
        raise ValueError("tool count exceeds model budget or exposes no serving tool")
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


def from_requirements(request):
    """Lower task/budget requirements without asking the integrator to list operations."""
    schema = load((ROOT / "spec/schemas/capability-request.schema.json").read_bytes())
    Draft202012Validator(schema).validate(request)
    required = {"format", "format_version", "profile_id", "profile_revision", "domain",
                "task_families", "xs_calc", "model_visible_tools_max", "model_budget", "device_budget"}
    allowed = required | {"specialization"}
    if not isinstance(request, dict) or not required.issubset(request) or set(request) - allowed:
        raise ValueError("capability request fields are missing or unknown")
    if request["format"] != "exactscope.capability.request" or request["format_version"] != "0.1":
        raise ValueError("unsupported capability request format")
    if type(request["xs_calc"]) is not bool:
        raise ValueError("xs_calc must be boolean")
    domain = request["domain"]
    families_map = task_families(domain)
    families = request["task_families"]
    if not isinstance(families, list) or any(not isinstance(f, str) or f not in families_map for f in families):
        raise ValueError("unknown task family")
    selected = sorted({op for family in families for op in families_map[family]})
    budget = dict(request["model_budget"])
    if "semantic_operation_count" in budget:
        raise ValueError("semantic count is compiler-derived in a requirements request")
    budget["semantic_operation_count"] = len(selected)
    return {"format": "exactscope.capability.profile", "format_version": "0.1-draft",
            "profile_id": request["profile_id"], "profile_revision": request["profile_revision"],
            "support": "experimental", "domain": request["domain"], "task_families": families,
            "runtime_surface": {"xs_calc": {"enabled": request["xs_calc"],
                "plan_revision": "plan-v0.1" if request["xs_calc"] else None},
                "xs_eval": {"operations": selected}, "xs_find": {"enabled": False},
                "model_visible_tools_max": request["model_visible_tools_max"],
                "normal_model_turns_max": budget.get("normal_model_turns_max"),
                "specialization": request.get("specialization", "host-limited")},
            "model_budget": budget, "device_budget": request["device_budget"],
            "bindings": {key: None for key in (
                "core_revision", "abi_revision", "registry_sha256", "hotset_sha256",
                "tool_schema_sha256", "grammar_sha256", "prompt_sha256", "artifact_sha256",
                "surface_contract_sha256", "profile_generator")},
            "evidence": {"conformance_suite": None, "conformance_sha256": None,
                "benchmark_mapping": None, "benchmark_mapping_sha256": None,
                "qualification_records": [], "model_result_bundles": []}}


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


def model_surface_contract(profile, catalog, files):
    """Bind explicit model-surface contract versions to exact generated asset bytes."""
    assets = []
    for name in sorted(MODEL_SURFACE_ASSETS):
        if name not in files:
            continue
        kind, contract_id, contract_version = MODEL_SURFACE_ASSETS[name]
        assets.append({
            "path": name,
            "kind": kind,
            "contract_id": contract_id,
            "contract_version": contract_version,
            "sha256": digest(files[name]),
        })
    if not assets:
        raise ValueError("capability exposes no versioned model-surface assets")
    return {
        "format": MODEL_SURFACE_FORMAT,
        "format_version": MODEL_SURFACE_VERSION,
        "negotiation": MODEL_SURFACE_NEGOTIATION,
        "profile": {
            "id": profile["profile_id"],
            "revision": profile["profile_revision"],
            "domain": profile["domain"],
        },
        "abi_revision": catalog["abi"],
        "hotset": {
            "format": catalog["format"],
            "format_version": catalog["format_version"],
            "binding_sha256": catalog["binding_sha256"],
        },
        "assets": assets,
    }


def verify_reviewed_catalog(domain, catalog):
    """Require generated fused metadata to agree with the reviewed semantic source."""
    source = load(domain_path(domain, "semantic_source").read_bytes())
    pack = source.get("pack") if isinstance(source, dict) else None
    source_operations = source.get("operations") if isinstance(source, dict) else None
    if not isinstance(pack, dict) or not isinstance(source_operations, list):
        raise ValueError(f"invalid reviewed semantic source for {domain}")
    by_key = {op.get("key"): op for op in source_operations if isinstance(op, dict)}
    for generated in catalog["operations"]:
        key = generated["op"]
        reviewed = by_key.get(key)
        if reviewed is None:
            raise ValueError(f"generated operation is absent from reviewed {domain} source: {key}")
        inputs = reviewed.get("inputs")
        if not isinstance(inputs, list):
            raise ValueError(f"reviewed operation has invalid inputs: {key}")
        signature = f"{key}({','.join(item['name'] for item in inputs)})"
        reviewed_args = [(item.get("name"), item.get("semantic"), item.get("shape")) for item in inputs]
        generated_args = [(item.get("name"), item.get("semantic"), item.get("shape"))
                          for item in generated["args"]]
        expected = (reviewed.get("revision"), reviewed.get("method"), signature, reviewed_args,
                    pack.get("id"), pack.get("version"))
        actual = (generated.get("revision"), generated.get("method"), generated.get("sig"),
                  generated_args, generated.get("pack_id"), generated.get("pack_version"))
        if actual != expected:
            raise ValueError(f"fused/reviewed semantic metadata drift: {key}")


def position_aware_calc_grammar():
    """Derived plan-v0.1 grammar that prevents self/forward result references."""
    lines = [
        'root ::= ws "{" ws "\\\"p\\\"" ws ":" ws "[" ws s0 t1 ws "]" ws "}" ws',
    ]
    for index in range(1, 8):
        tail = f't{index + 1}' if index < 7 else ''
        suffix = f' {tail}' if tail else ''
        lines.append(f't{index} ::= "" | c s{index}{suffix}')
    for index in range(8):
        lines.append(
            f's{index} ::= pre (bop mid "[" ws v{index} c v{index} ws "]" | sq mid "[" ws v{index} ws "]") post')
    lines.append('v0 ::= dec')
    for index in range(1, 8):
        lines.append(f'v{index} ::= v{index - 1} | "\\\"#{index - 1}\\\""')
    lines += [
        'pre ::= "{" ws "\\\"o\\\"" ws ":" ws',
        'mid ::= ws "," ws "\\\"a\\\"" ws ":" ws',
        'post ::= ws "}"',
        'bop ::= "\\\"add\\\"" | "\\\"sub\\\"" | "\\\"mul\\\"" | "\\\"div\\\"" | "\\\"powi\\\""',
        'sq ::= "\\\"sqrt\\\""',
        'dec ::= "\\\"" "-"? ("0" | [1-9] [0-9]*) ("." [0-9]+)? ([eE] [+-]? [0-9]+)? "\\\""',
        'c ::= ws "," ws',
        'ws ::= [ \\t\\n\\r]{0,4}',
    ]
    return ("\n".join(lines) + "\n").encode()


def compile_profile(source, packc):
    source = load(source)
    if isinstance(source, dict) and source.get("format") == "exactscope.capability.request":
        source = from_requirements(source)
    profile = validate(source)
    domain = profile["domain"]
    descriptor = domain_descriptor(domain)
    families_map = task_families(domain)
    manifest = {"format": "exactscope.hotset.source", "format_version": "0.1",
                "name": profile["profile_id"], "fused_packs": [descriptor["fused_pack"]],
                "operations": profile["runtime_surface"]["xs_eval"]["operations"],
                "include_find": False}
    with tempfile.TemporaryDirectory(prefix="xs-capability-") as tmp:
        base = Path(tmp)
        (base / "hotset.json").write_bytes(canonical(manifest))
        subprocess.run([str(packc.resolve()), "hotset", str(base / "hotset.json"),
                        str(base / "assets")], check=True, capture_output=True)
        files = {p.name: p.read_bytes() for p in (base / "assets").iterdir()}
    catalog = load(files["catalog.json"])
    verify_reviewed_catalog(domain, catalog)
    files["catalog.json"] = canonical(catalog)
    if catalog["operations"]:
        files["xs-eval.tool.json"] = canonical(strict_tool(catalog, load(files["xs-eval.tool.json"])))
        files["xs-eval.gbnf"] = files["xs-eval.gbnf"].replace(
            b'(ws "," ws decimal-string)*', b'(ws "," ws decimal-string){0,63}')
        prompt = "Pass exact decimal strings in signature order. Never guess missing values or methods. Preserve errors.\n"
        prompt += "\n".join(op["sig"] for op in catalog["operations"]) + "\n"
    else:
        files.pop("xs-eval.tool.json", None)
        files.pop("xs-eval.gbnf", None)
        prompt = ""
    if profile["runtime_surface"]["xs_calc"]["enabled"]:
        contract = load((ROOT / "adapters/xs-calc-v0.1/contract.json").read_bytes())
        if (contract.get("plan_id"), contract.get("plan_revision"), contract.get("max_steps")) != ("plan-v0.1", 1, 8):
            raise ValueError("unsupported arithmetic contract")
        for relative, expected in contract["files"].items():
            path = (ROOT / relative).resolve()
            if not path.is_relative_to(ROOT) or digest(path.read_text(encoding="utf-8").encode()) != expected:
                raise ValueError(f"arithmetic contract drift: {relative}")
        files["xs-calc.contract.json"] = canonical(contract)
        tool_data = (ROOT / "adapters/xs-calc-v0.1/xs-calc.tool.json").read_text(encoding="utf-8").encode()
        files["xs-calc.tool.json"] = canonical(load(tool_data))
        if profile["profile_revision"] >= 7:
            files["xs-calc.gbnf"] = position_aware_calc_grammar()
            files["xs-calc.grammar-source.json"] = canonical({
                "kind": "position-aware-derived-v1",
                "base_contract_sha256": digest(files["xs-calc.contract.json"]),
                "rule": "step i permits decimal literals and only #0..#(i-1) result references",
            })
        else:
            files["xs-calc.gbnf"] = (ROOT / "adapters/xs-calc-v0.1/xs-calc.gbnf").read_bytes()
        prompt += "xs_calc: 1-8 add/sub/mul/div/powi/sqrt steps; backward # references only.\n"
    files["prompt-fragment.txt"] = prompt.encode()
    files["surface-contract.json"] = canonical(model_surface_contract(profile, catalog, files))
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
                    surface_contract_sha256=digest(files["surface-contract.json"]),
                    profile_generator="tools/compile_capability.py@0.1")
    for category, names in categories.items():
        bindings[category + "_sha256"] = digest(canonical({n: digest(files[n]) for n in names}))
    files["task-map.json"] = canonical({f: families_map[f] for f in profile["task_families"]})
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


def verify_model_surface_contract(path, manifest, profile):
    """Verify the optional v0.1 model-surface negotiation contract for a bundle."""
    bindings = profile.get("bindings") if isinstance(profile, dict) else None
    binding = bindings.get("surface_contract_sha256") if isinstance(bindings, dict) else None
    contract_path = path / "surface-contract.json"
    if binding is None and not contract_path.exists():
        return None  # Legacy immutable bundles predate explicit surface negotiation.
    if not isinstance(binding, str) or not contract_path.is_file():
        raise ValueError("model-surface contract/binding must appear together")
    contract_bytes = contract_path.read_bytes()
    if digest(contract_bytes) != binding:
        raise ValueError("model-surface contract digest mismatch")
    contract = load(contract_bytes)
    if canonical(contract) != contract_bytes:
        raise ValueError("noncanonical model-surface contract")
    if (contract.get("format"), contract.get("format_version"), contract.get("negotiation")) != (
            MODEL_SURFACE_FORMAT, MODEL_SURFACE_VERSION, MODEL_SURFACE_NEGOTIATION):
        raise ValueError("unsupported model-surface negotiation contract")
    expected_profile = {
        "id": profile.get("profile_id"),
        "revision": profile.get("profile_revision"),
        "domain": profile.get("domain"),
    }
    if contract.get("profile") != expected_profile:
        raise ValueError("model-surface contract profile identity mismatch")
    hotset = contract.get("hotset")
    if (contract.get("abi_revision") != bindings.get("abi_revision")
            or not isinstance(hotset, dict)
            or hotset.get("binding_sha256") != bindings.get("hotset_sha256")):
        raise ValueError("model-surface contract runtime binding mismatch")
    catalog = load((path / "catalog.json").read_bytes())
    if hotset != {
            "format": catalog.get("format"),
            "format_version": catalog.get("format_version"),
            "binding_sha256": catalog.get("binding_sha256")}:
        raise ValueError("model-surface contract hot-set identity mismatch")
    assets = contract.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("model-surface contract assets must be nonempty")
    expected_names = sorted(name for name in MODEL_SURFACE_ASSETS if (path / name).is_file())
    actual_names = [record.get("path") for record in assets if isinstance(record, dict)]
    if actual_names != expected_names or len(actual_names) != len(assets):
        raise ValueError("model-surface contract asset inventory mismatch")
    for record in assets:
        name = record["path"]
        kind, contract_id, contract_version = MODEL_SURFACE_ASSETS[name]
        if (record.get("kind"), record.get("contract_id"), record.get("contract_version")) != (
                kind, contract_id, contract_version):
            raise ValueError(f"model-surface contract version mismatch: {name}")
        expected_digest = manifest["files"].get(name)
        if record.get("sha256") != expected_digest or digest((path / name).read_bytes()) != expected_digest:
            raise ValueError(f"model-surface contract asset digest mismatch: {name}")
    return contract


def verify_bundle_internal_consistency(path, manifest, profile):
    """Verify immutable cross-file capability identity without consulting mutable source catalogs."""
    required_profile = {"profile_id", "profile_revision", "domain", "task_families",
                        "runtime_surface", "model_budget", "bindings"}
    if not isinstance(profile, dict) or not required_profile.issubset(profile):
        raise ValueError("capability profile is structurally incomplete")
    profile_bytes = (path / "profile.json").read_bytes()
    if canonical(profile) != profile_bytes:
        raise ValueError("noncanonical capability profile")

    catalog_bytes = (path / "catalog.json").read_bytes()
    catalog = load(catalog_bytes)
    if canonical(catalog) != catalog_bytes:
        raise ValueError("noncanonical capability catalog")
    if (catalog.get("format"), catalog.get("format_version")) != ("exactscope.hotset", "0.1"):
        raise ValueError("unsupported capability hot-set catalog")

    task_map_bytes = (path / "task-map.json").read_bytes()
    task_map = load(task_map_bytes)
    if canonical(task_map) != task_map_bytes or not isinstance(task_map, dict):
        raise ValueError("noncanonical capability task map")
    if set(task_map) != set(profile["task_families"]):
        raise ValueError("capability task-map/profile family mismatch")
    mapped_operations = sorted({op for operations in task_map.values() if isinstance(operations, list)
                                for op in operations})
    if any(not isinstance(operations, list) for operations in task_map.values()):
        raise ValueError("capability task map contains a non-list operation set")

    surface = profile["runtime_surface"]
    if not isinstance(surface, dict) or not isinstance(surface.get("xs_eval"), dict) \
            or not isinstance(surface.get("xs_calc"), dict):
        raise ValueError("capability runtime surface is structurally incomplete")
    selected = surface["xs_eval"].get("operations")
    if not isinstance(selected, list) or sorted(selected) != mapped_operations:
        raise ValueError("capability task-map/runtime-surface mismatch")
    catalog_operations = catalog.get("operations")
    if not isinstance(catalog_operations, list):
        raise ValueError("capability catalog operations are invalid")
    catalog_keys = [operation.get("op") for operation in catalog_operations if isinstance(operation, dict)]
    if len(catalog_keys) != len(catalog_operations) or sorted(catalog_keys) != sorted(selected):
        raise ValueError("capability catalog/runtime-surface mismatch")

    calc_enabled = surface["xs_calc"].get("enabled") is True
    expected_presence = {
        "xs-eval.tool.json": bool(selected),
        "xs-eval.gbnf": bool(selected),
        "xs-calc.tool.json": calc_enabled,
        "xs-calc.gbnf": calc_enabled,
        "xs-calc.contract.json": calc_enabled,
    }
    for name, expected in expected_presence.items():
        if (path / name).is_file() != expected:
            raise ValueError(f"capability model-surface file mismatch: {name}")
    if not (path / "prompt-fragment.txt").is_file():
        raise ValueError("capability prompt fragment is missing")

    bindings = profile["bindings"]
    if not isinstance(bindings, dict):
        raise ValueError("capability bindings are invalid")
    if bindings.get("abi_revision") != catalog.get("abi") \
            or bindings.get("hotset_sha256") != catalog.get("binding_sha256") \
            or bindings.get("registry_sha256") != digest(canonical(catalog.get("packs"))):
        raise ValueError("capability catalog/profile binding mismatch")
    categories = {
        "tool_schema": sorted(name for name in manifest["files"] if name.endswith(".tool.json")),
        "grammar": sorted(name for name in manifest["files"] if name.endswith(".gbnf")),
        "prompt": ["prompt-fragment.txt"],
    }
    for category, names in categories.items():
        expected = digest(canonical({name: digest((path / name).read_bytes()) for name in names}))
        if bindings.get(category + "_sha256") != expected:
            raise ValueError(f"capability {category} binding mismatch")

    revisions = {operation.get("op"): operation.get("revision") for operation in catalog_operations}
    if manifest.get("operation_revisions") != revisions:
        raise ValueError("capability operation revision manifest mismatch")
    measurements = manifest.get("measurements")
    if not isinstance(measurements, dict):
        raise ValueError("capability measurements are missing")
    measured = {
        "prompt_fragment_bytes": (path / "prompt-fragment.txt").stat().st_size,
        "schema_bytes": sum((path / name).stat().st_size for name in categories["tool_schema"]),
        "grammar_bytes": sum((path / name).stat().st_size for name in categories["grammar"]),
        "top_level_tool_count": len(categories["tool_schema"]),
        "visible_semantic_operation_count": len(catalog_operations),
    }
    if any(measurements.get(key) != value for key, value in measured.items()):
        raise ValueError("capability model-surface measurements mismatch")
    budget = profile["model_budget"]
    if not isinstance(budget, dict) or budget.get("semantic_operation_count") != len(catalog_operations):
        raise ValueError("capability semantic-operation budget mismatch")
    for measurement, budget_key in (("prompt_fragment_bytes", "prompt_fragment_bytes_max"),
                                    ("schema_bytes", "schema_bytes_max"),
                                    ("grammar_bytes", "grammar_bytes_max")):
        limit = budget.get(budget_key)
        if not isinstance(limit, int) or measured[measurement] > limit:
            raise ValueError(f"capability {measurement} exceeds bound model budget")

    artifact = bindings.get("artifact_sha256")
    runtime = path / "runtime.wasm"
    if artifact is None:
        if runtime.exists():
            raise ValueError("unbound capability unexpectedly contains runtime.wasm")
    elif not isinstance(artifact, str) or not runtime.is_file() \
            or manifest["files"].get("runtime.wasm") != artifact:
        raise ValueError("bound capability runtime artifact mismatch")


def verify_bundle(path):
    manifest_bytes = (path / "manifest.json").read_bytes()
    if (path / "bundle-sha256.txt").read_text().strip() != digest(manifest_bytes):
        raise ValueError("manifest digest mismatch")
    manifest = load(manifest_bytes)
    if canonical(manifest) != manifest_bytes:
        raise ValueError("noncanonical manifest")
    if not isinstance(manifest, dict) or (manifest.get("format"), manifest.get("format_version")) != (
            "exactscope.capability.bundle", "0.1") or not isinstance(manifest.get("files"), dict):
        raise ValueError("unsupported capability bundle manifest")
    entries = list(path.iterdir())
    if any(entry.is_symlink() or not entry.is_file() for entry in entries):
        raise ValueError("capability bundle may contain regular files only")
    if set(p.name for p in entries) != set(manifest["files"]) | {"manifest.json", "bundle-sha256.txt"}:
        raise ValueError("bundle file inventory mismatch")
    for name, expected in manifest["files"].items():
        if (not isinstance(name, str) or Path(name).name != name or not isinstance(expected, str)
                or len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected)
                or digest((path / name).read_bytes()) != expected):
            raise ValueError(f"asset digest mismatch: {name}")
    profile = load((path / "profile.json").read_bytes())
    verify_bundle_internal_consistency(path, manifest, profile)
    verify_model_surface_contract(path, manifest, profile)
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
