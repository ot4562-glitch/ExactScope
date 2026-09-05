#!/usr/bin/env python3
"""Generate mechanical Statistics declarations; Python 3.11+, no dependencies.

Semantic authority: packs/statistics-core.xsp.json. Implementation authority:
spec/implementation/statistics-kernel-bindings.json. Never generates algorithms or edits Cargo.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PACK = Path("packs/statistics-core.xsp.json")
BINDINGS = Path("spec/implementation/statistics-kernel-bindings.json")
OUTPUT = Path("crates/exactscope-kernel/src/statistics_operations.generated.rs")
KERNEL_OUTPUT = Path("crates/exactscope-kernel/src/statistics_kernels.generated.rs")
DISPATCH_OUTPUT = Path("crates/exactscope-kernel/src/statistics_dispatch.generated.rs")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def load(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(pack, manifest, root=ROOT):
    require(set(manifest) == {"format", "format_version", "domain", "operations"}
            and manifest["format"] == "exactscope.statistics.kernel-bindings"
            and manifest["format_version"] == "0.1"
            and manifest["domain"] == "statistics", "unsupported binding manifest")
    operations = pack["operations"]
    bindings = manifest["operations"]
    fields = {"key", "kernel_id", "kernel_name", "kernel_const", "cargo_feature", "rust_operation_symbol", "rust_function", "result_kind"}
    for binding in bindings:
        require(set(binding) == fields, "binding fields must contain only implementation identity")
        for field in ("kernel_const", "rust_operation_symbol"):
            require(re.fullmatch(r"[A-Z][A-Z0-9_]*", binding[field]), f"invalid {field}")
        require(re.fullmatch(r"stats-[a-z0-9-]+", binding["cargo_feature"]), "invalid feature")
        require(type(binding["kernel_id"]) is int and 0 < binding["kernel_id"] <= 65535,
                "invalid stable kernel ID")
        require(re.fullmatch(r"statistics_[a-z_]+", binding["rust_function"]), "invalid Rust function")
        require(binding["result_kind"] in ("rational", "sqrt", "regression"), "invalid result kind")
    for field in fields - {"result_kind"}:
        require(len({b[field] for b in bindings}) == len(bindings), f"duplicate binding {field}")
    for field in ("key", "id"):
        require(len({o[field] for o in operations}) == len(operations), f"duplicate pack {field}")
    by_key = {b["key"]: b for b in bindings}
    require(set(by_key) == {o["key"] for o in operations}, "pack/binding key set differs")
    rust = (root / "crates/exactscope-kernel/src/stats.rs").read_text(encoding="utf-8")
    for op in operations:
        binding = by_key[op["key"]]
        require(op["kind"] == "kernel" and op["kernel"] == binding["kernel_name"],
                f"kernel name drift: {op['key']}")
        # Phase 1's compiler still derives features from canonical keys.
        require(binding["cargo_feature"] == op["key"].replace(".", "-"), "compiler feature convention drift")
        require(re.search(rf"pub fn {binding['rust_function']}\b", rust),
                f"missing handwritten implementation: {op['key']}")
        require(type(op["id"]) is int and 0 < op["id"] <= 0xFFFFFFFF, "invalid pack-local ID")
        require(type(op["revision"]) is int and 0 < op["revision"] <= 65535, "invalid revision")
        require(re.fullmatch(r"stats\.[a-z0-9.]+", op["key"]), "invalid canonical key")
        require(all(i["shape"] == "vector" and i["semantic"] == "number"
                    and i["max_len"] == 256 and not i["unit_required"] and not i["constraints"]
                    and re.fullmatch(r"[a-z][a-z0-9_]*", i["name"])
                    for i in op["inputs"]), "unsupported fused input semantics")
        require(all(o["semantic"] == "number" and o["unit_rule"] == "dimensionless"
                    for o in op["outputs"]), "unsupported fused output semantics")
        require(0 < len(op["inputs"]) <= 2 and len(op["outputs"]) ==
                (2 if binding["result_kind"] == "regression" else 1),
                "unsupported arity")
        policy = op["output_policy"]
        require(policy == {"scale": policy["scale"], "rounding": "half_even",
                           "allow_scale_override": False, "allow_rounding_override": False,
                           "classification_required": False}
                and type(policy["scale"]) is int and 0 <= policy["scale"] <= 18,
                "unsupported fused output policy")
        require(not op["relations"] and not op["classifications"], "unsupported fused relations/classes")
    validate_features(bindings, root)
    return [(op, by_key[op["key"]]) for op in sorted(operations, key=lambda op: op["id"])]


def validate_features(bindings, root=ROOT, prefix="stats", specialization="stats-specialized"):
    for crate, dependencies in (
        ("kernel", ()), ("tinyjson", ("kernel",)), ("wasm", ("kernel", "tinyjson"))
    ):
        path = root / f"crates/exactscope-{crate}/Cargo.toml"
        features = tomllib.loads(path.read_text(encoding="utf-8"))["features"]
        actual = {k: v for k, v in features.items() if k.startswith(prefix + "-") and k != specialization}
        expected = {b["cargo_feature"]: [f"exactscope-{dep}/{b['cargo_feature']}" for dep in dependencies]
                    for b in bindings}
        require(actual == expected, f"operation feature declaration drift: {path.relative_to(root)}")
        expected_specialization = (["tinyjson"] if crate == "wasm" else []) + [
            f"exactscope-{dep}/{specialization}" for dep in dependencies]
        require(features.get(specialization) == expected_specialization,
                f"specialization feature forwarding drift: {path.relative_to(root)}")


def render(rows):
    lines = [
        "// @generated by tools/generate_statistics_metadata.py; DO NOT EDIT.",
        "// Sources: packs/statistics-core.xsp.json + spec/implementation/statistics-kernel-bindings.json.",
        "// Regenerate: python tools/generate_statistics_metadata.py",
        "// Validate:   python tools/generate_statistics_metadata.py --check",
        "// Pack-local operation IDs are NOT stable kernel IDs. No numeric algorithms are generated.",
        "",
    ]
    quote = lambda s: json.dumps(s, ensure_ascii=False)
    for op, binding in rows:
        signature = op["key"] + "(" + ",".join(i["name"] for i in op["inputs"]) + ")"
        lines += [f"/// `{signature}`.",
                  f"pub static {binding['rust_operation_symbol']}: StatisticsOperationDecl = StatisticsOperationDecl {{"]
        values = dict(id=op["id"], revision=op["revision"], key=quote(op["key"]),
                      signature=quote(signature), method=quote(op["method"]),
                      kernel_id=binding["kernel_const"], input_count=len(op["inputs"]),
                      output_count=len(op["outputs"]), output_scale=op["output_policy"]["scale"],
                      rounding_mode="RoundingMode::HalfEven")
        lines += [f"    {key}: {value}," for key, value in values.items()]
        lines += ["};", ""]
    lines += ["/// Executable statistics operations in the first fused kernel slice.",
              f"pub static OFFICIAL_STATS_OPERATIONS: [&StatisticsOperationDecl; {len(rows)}] = ["]
    lines += [f"    &{binding['rust_operation_symbol']}," for _, binding in rows]
    lines += ["];", ""]
    for selector, arg, arg_type in (("key", "key", "&[u8]"), ("id", "operation_id", "u32")):
        lines += [f"/// Resolves a {'canonical key' if selector == 'key' else 'pack-local ID (not a kernel ID)'} against enabled operations.",
                  "#[must_use]", "#[cfg_attr(", '    feature = "stats-specialized",',
                  "    allow(unreachable_code, unused_variables)", ")]",
                  f"pub fn statistics_selected_operation_by_{selector}(",
                  f"    {arg}: {arg_type},", ") -> Option<&'static StatisticsOperationDecl> {",
                  f"    match {arg} {{"]
        for op, binding in rows:
            lines += ["        #[cfg(any(", '            not(feature = "stats-specialized"),',
                      f"            feature = {quote(binding['cargo_feature'])}", "        ))]"]
            pattern = "b" + quote(op["key"]) if selector == "key" else str(op["id"])
            lines += [f"        {pattern} => Some(&{binding['rust_operation_symbol']}),"]
        lines += ["        _ => None,", "    }", "}", ""]
    return "\n".join(lines)


def cfg(binding):
    return ('#[cfg(any(not(feature = "stats-specialized"), '
            f'feature = "{binding["cargo_feature"]}"))]')


def render_kernels(rows):
    lines = ["// @generated by tools/generate_statistics_metadata.py; DO NOT EDIT."]
    for op, binding in rows:
        lines += [f'/// Stable internal ID for `{binding["kernel_name"]}`; not a pack-local ID.',
                  f'pub const {binding["kernel_const"]}: u16 = {binding["kernel_id"]};']
    lines += ['/// Resolves a reviewed kernel name in the enabled kernel namespace.',
              '#[must_use]', 'pub fn statistics_kernel_id_by_name(name: &str) -> Option<u16> {',
              '    match name {']
    for op, b in rows:
        lines += [cfg(b), f'{json.dumps(b["kernel_name"])} => Some({b["kernel_const"]}),']
    lines += ['_ => None,', '}', '}',
              '/// Returns the enabled stable kernel arity contract.', '#[must_use]',
              'pub const fn statistics_kernel_contract(kernel_id: u16) -> Option<StatisticsKernelContract> {',
              'match kernel_id {']
    for op, b in rows:
        lines += [cfg(b), f'{b["kernel_const"]} => Some(StatisticsKernelContract {{ input_count: {len(op["inputs"])}, output_count: {len(op["outputs"])} }}),']
    lines += ['_ => None,', '}', '}',
              '/// Canonical output ordering for an enabled stable kernel ID.', '#[must_use]',
              "pub const fn statistics_kernel_output_names(kernel_id: u16) -> &'static [&'static str] {",
              'match kernel_id {']
    for op, b in rows:
        names = ', '.join(json.dumps(o['name']) for o in op['outputs'])
        lines += [cfg(b), f'{b["kernel_const"]} => &[{names}],']
    return '\n'.join(lines + ['_ => &[],', '}', '}', ''])


def render_dispatch(rows):
    # Only call plumbing is generated. Numeric algorithms remain handwritten.
    lines = ['// @generated by tools/generate_statistics_metadata.py; DO NOT EDIT.',
             '{', 'let square_root_result = match operation.kernel_id {']
    def call(op, b):
        args = [f'arguments[{i}]' for i in range(len(op['inputs']))]
        if b['result_kind'] == 'sqrt':
            args += ['operation.output_scale', 'operation.rounding_mode']
        return b['rust_function'] + '(' + ', '.join(args) + ')'
    for op, b in rows:
        if b['result_kind'] == 'sqrt':
            lines += [cfg(b), f'{b["kernel_const"]} => Some({call(op, b)}),']
    lines += ['_ => None,', '};', 'if let Some(result) = square_root_result {',
              'return match result {',
              'Ok(result) => statistics_sqrt_success(pack_slot, operation, result),',
              'Err(status) => statistics_failure(pack_slot, operation, status),', '};', '}',
              'match operation.kernel_id {']
    for op, b in rows:
        if b['result_kind'] != 'sqrt':
            assignment = ('exact[0] = value.slope; exact[1] = value.intercept; 2usize'
                          if b['result_kind'] == 'regression' else 'exact[0] = value; 1usize')
            lines += [cfg(b), f'{b["kernel_const"]} => {call(op, b)}.map(|value| {{ {assignment} }}),']
    return '\n'.join(lines + ['_ => Err(Status::INTERNAL_ERROR),', '}', '}', ''])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail on stale Rust or Cargo drift; write nothing")
    args = parser.parse_args()
    try:
        rows = validate(load(ROOT / PACK), load(ROOT / BINDINGS))
        for output, generated in ((OUTPUT, render(rows)), (KERNEL_OUTPUT, render_kernels(rows)),
                                  (DISPATCH_OUTPUT, render_dispatch(rows))):
            path = ROOT / output
            if args.check:
                require(path.exists() and path.read_bytes() == generated.encode("utf-8"),
                        f"stale {output}; run python tools/generate_statistics_metadata.py")
            else:
                path.write_text(generated, encoding="utf-8", newline="\n")
        print("Statistics metadata and all three Cargo operation feature declarations verified.")
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(f"Statistics metadata: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
