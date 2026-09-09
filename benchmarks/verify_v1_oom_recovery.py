"""Gold-free verification for the interrupted, frozen r2 matrix.

Paths deliberately are not translated: run this in the original WSL environment.
The parent completion marker is never synthesized or required for cell retention.
"""
from __future__ import annotations

import copy
from pathlib import Path
import stat
import os
import sys

import run_v1_grounding_matrix as native

PARENT = native.ROOT / "target/v1-grounding-matrix-20x3-20260909-r2"
PARENT_SHA = "47e3930ff0e47f9e51d8171dedee0f5f35c8cdb2e9727f3ccf25d54a3d5d36d0"
REQUIRED = {"SHA256SUMS", "contract-calibration.json", "llama-server.log",
            "preregistration.json", "raw-results.jsonl", "run-status.json"}
TINY = "tinyllama-11b-chat-q4km"
class IntegrityError(ValueError):
    pass


def read(path):
    return native.read(safe(path))


def write(path, value):
    return native.write(safe(path), value)


def sha(path):
    path = safe(path)
    require(path.is_file(), "missing regular file")
    return native.file_sha(path)


def require(condition, message):
    if not condition:
        raise IntegrityError(message)


def safe(path, root=None):
    """Reject symlinks, junctions/reparse points, noncanonical paths and escapes."""
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts, f'unsafe path: {path}')
    require(path.resolve() == path, f'redirected path: {path}')
    for part in (path, *path.parents):
        if part.exists() or part.is_symlink():
            info = part.lstat()
            require(not stat.S_ISLNK(info.st_mode) and not
                    (getattr(info, 'st_file_attributes', 0) & 0x400), f'redirect: {part}')
            require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode), "nonregular evidence")
            if part.is_file():
                require(info.st_nlink == 1, f'hardlink: {part}')
    if root is not None:
        require(path.is_relative_to(Path(root)), f'path escape: {path}')
    return path


def inventory(root):
    root = safe(root)
    if not root.exists():
        return {'exists': False, 'directories': [], 'files': {}}
    require(root.is_dir(), 'expected directory')
    files, directories = {}, []
    for directory, dirs, names in os.walk(root, followlinks=False):
        for name in sorted(dirs):
            path = safe(Path(directory) / name, root)
            directories.append(path.relative_to(root).as_posix())
        for name in sorted(names):
            path = safe(Path(directory) / name, root)
            require(path.is_file(), 'non-file evidence')
            files[str(path)] = sha(path)
    return {'exists': True, 'directories': sorted(directories), 'files': files}


def tree(root):
    return inventory(root)["files"]


def verify_hashes(values):
    require(isinstance(values, dict) and values, "empty hash inventory")
    for path, digest in values.items():
        require(sha(safe(path)) == digest, f"evidence drift: {path}")


def load_parent(*, verify_static=True):
    root = safe(PARENT)
    require(sha(root / "preregistration.json") == PARENT_SHA, "parent preregistration checksum")
    require(read(root / "preregistration-checksum.json") == {"sha256": PARENT_SHA}, "parent checksum file")
    p = read(root / "preregistration.json")
    require(p.get("format") == "exactscope.v1-grounding-matrix-preregistration"
            and p.get("format_version") == "0.1" and p.get("output") == str(root)
            and p.get("arms") == ["A", "G"] and p.get("retry_count") == 0
            and p.get("resume") is False, "parent schema/policy/location")
    models = native.indexed(p["models"], 20)
    cells = native.indexed(p["cells"], 60)
    expected = [m + "--" + t for m in models for t in native.PANEL]
    require(list(cells) == expected, "parent cell order/coverage")
    require(set(p["candidates"]) == set(native.PANEL), "candidate coverage")
    for cell in cells.values():
        require(cell["id"] == cell["model_id"] + "--" + cell["benchmark_id"], "cell identity")
        require(safe(cell["run"], root) == root / "cells" / cell["id"], "child location")
    if verify_static:
        verify_static_environment(p)
    return p


def partition(p):
    root = safe(PARENT)
    require(not inventory(root / "ledger")["directories"], "extra ledger directory")
    ledger = tree(root / "ledger")
    allowed = {str(root / "ledger" / (c["id"] + ".json")) for c in p["cells"]}
    require(set(ledger) <= allowed, "unknown ledger")
    rows = []
    for cell in p["cells"]:
        path = str(root / "ledger" / (cell["id"] + ".json"))
        disposition = "recovery"
        if path in ledger:
            entry = read(path)
            require(entry.get("id") == cell["id"], "ledger identity")
            if entry.get("status") == "completed":
                require(cell["model_id"] != TINY, "Tiny completed")
                disposition = "retained_completed"
            else:
                require(entry.get("status") == "failed" and cell["model_id"] == TINY
                        and bool(entry.get("error")), "unexpected sealed failure")
                disposition = "retained_failed"
        rows.append({"id": cell["id"], "disposition": disposition})
    require([sum(r["disposition"] == d for r in rows) for d in
             ("retained_completed", "retained_failed", "recovery")] == [35, 3, 22], "35/3/22 partition")
    return rows


def snapshot(p, evidence):
    require(bool(evidence), "supplied OOM evidence is required")
    return {"parent": inventory(PARENT), "completion": tree_file(PARENT / "run-complete.json"),
            "oom": {str(safe(f)): sha(f) for f in evidence}}


def tree_file(path):
    safe(path)
    return {str(path): sha(path)} if path.exists() else {}


def verify_snapshot(p, saved):
    require(snapshot(p, saved["oom"]) == saved, "parent/OOM snapshot drift")


def verify_model_binding(p, cell):
    """Validate frozen selection metadata without reading a live GGUF."""
    model = next(m for m in p["models"] if m["id"] == cell["model_id"])
    require(cell["model_path"] == model["path"] and cell["model_sha256"] == model["sha256"], "model binding")
    return model


def verify_live_model(p, cell):
    """Authenticate only the selected model, immediately before inference."""
    model = verify_model_binding(p, cell)
    verify_hashes({cell["model_path"]: cell["model_sha256"]})
    require(Path(cell["model_path"]).stat().st_size == model["bytes"], "model size")


def verify_static_environment(p):
    """One fresh hash per distinct frozen file; never reused across barriers."""
    executing_sources(p)
    for task, candidate in p["candidates"].items():
        expected = {str(safe(Path(candidate["path"]) / f)) for f in native.SERVING_FILES[task]}
        require(set(candidate["hashes"]) == expected, "serving artifact coverage")
        require(all(p["frozen_files"].get(k) == h for k, h in candidate["hashes"].items()), "serving freeze coverage")
    verify_hashes(p["frozen_files"])
    return dict(p["frozen_files"])


def verify_environment(p, cell):
    verify_static_environment(p)
    verify_live_model(p, cell)


def verify_sealed_cell(cell, ledger, run_root=None, *, parent=None):
    """Authenticate sealed evidence, never live model bytes.

    A supplied parent must have been authenticated at the caller's current static
    barrier. Standalone calls authenticate the parent and static environment.
    """
    p = load_parent() if parent is None else parent
    original = next(c for c in p["cells"] if c["id"] == cell["id"])
    root = safe(run_root or PARENT)
    require(cell == (original if root == PARENT else relocated(original, root)), "cell protocol drift")
    run = safe(cell["run"], root)
    require(run == root / "cells" / cell["id"], "run path")
    require(ledger.get("id") == cell["id"] and ledger.get("status") == "completed"
            and ledger.get("error") is None, "unsealed cell")
    artifacts = inventory(run)
    require(not artifacts["directories"], "extra child directory")
    actual = artifacts["files"]
    require({Path(f).relative_to(run).as_posix() for f in actual} == REQUIRED, "required artifact coverage")
    require(ledger.get("artifacts") == actual, "ledger artifact hashes/coverage")
    model = verify_model_binding(p, cell)
    child = read(run / "preregistration.json")
    require(isinstance(child["model"], dict), "child model identity")
    # Parent selection/provenance metadata is not serialized into child models.
    for key in ("id", "path", "sha256", "runtime", *native.IDENTITY):
        require(key in child["model"] and child["model"][key] == model[key],
                f"child model identity: {key}")
    if "upstream_sha256" in model:
        require(model["upstream_sha256"] == model["sha256"], "parent upstream_sha256 mismatch")
    command = original["run_command"]
    for flag, field in (("--model-inventory", "model_inventory_sha256"),
                        ("--runtime-record", "runtime_record_sha256")):
        require(child.get(field) == p["frozen_files"][command[command.index(flag) + 1]], field)
    runtime = copy.deepcopy(p["runtime"])
    runtime.pop("base_port", None)
    runtime.pop("port_policy", None)
    runtime["launch"]["port"] = cell["port"]
    runtime["launch"]["threads"] = int(command[command.index("--threads") + 1])
    require(child["runtime"] == runtime, "child runtime identity")
    require(child.get("format") == f"exactscope.public-{native.FORMATS[cell['benchmark_id']]}-preregistration"
            and child.get("format_version") == "0.1" and child.get("arms") == ["A", "G"]
            and child.get("retry_count") == 0 and child.get("hidden_repair") is False
            and child.get("gold_visible_to_runner") is False, "child schema/policy")
    status = read(run / "run-status.json")
    count = p["candidates"][cell["benchmark_id"]]["items"]
    require(status.get("model_id") == cell["model_id"], "status model")
    require(status.get("state") == "complete" and status.get("record_count") == count * 2
            and status.get("preregistration_sha256") == sha(run / "preregistration.json"), "child status")
    native.verify_child_run(p, cell)  # Native A/G keys, counts, raw output and calibration checks.
    require(tree(run) == actual, "child changed during verification")
    return {"verified": True, "items_per_arm": count, "records": count * 2}


def option(command, flag):
    require(command.count(flag) == 1, f'command option: {flag}')
    return command[command.index(flag) + 1]


def relocated(cell, output, score_output=None):
    output = safe(output)
    if score_output is not None:
        score_output = safe(score_output)
    result = copy.deepcopy(cell)
    require(not any(flag in cell[key] for key in ("run_command", "score_command") for flag in ("--resume", "--retry")), "resume/retry forbidden")
    result['run'] = str(output / 'cells' / cell['id'])
    result['score'] = str((score_output or output) / 'scores' / cell['id'])
    for command, replacements in [('run_command', {'--output': result['run']}),
                                  ('score_command', {'--run': result['run'], '--output': result['score']})]:
        for flag, value in replacements.items():
            option(result[command], flag)
            result[command][result[command].index(flag) + 1] = value
    return result




def separated(output, *protected):
    output = safe(output)
    for name in (PARENT, *protected):
        root = safe(name)
        require(not output.is_relative_to(root) and not root.is_relative_to(output), "protected path overlap")
    return output


def executing_sources(p):
    root = safe(p["cwd"])
    require(root == safe(native.ROOT), "executing root drift")
    expected = {Path(name) for name in p["frozen_files"] if Path(name).suffix == ".py"
                and Path(name).parent in (root / "benchmarks", root / "tools")}
    require(root / "benchmarks/run_v1_grounding_matrix.py" in expected, "native controller not frozen")
    require(safe(native.__file__) == root / "benchmarks/run_v1_grounding_matrix.py", "shadow native controller")
    for path in expected:
        module = sys.modules.get(path.stem)
        if module is not None:
            require(safe(module.__file__) == path, f"shadow import: {path.stem}")
    require(set(native.source_paths()) <= expected, "unfrozen native dependency")
    for cell in p["cells"]:
        for key in ("run_command", "score_command"):
            command = cell[key]
            require(safe(command[1]) == safe(native.PANEL[cell["benchmark_id"]].__file__), "script drift")
            # Parent used the system interpreter alias but froze its resolved binary.
            # Only this execution alias is resolved; evidence redirects are forbidden.
            executable = Path(command[0]).resolve()
            require(executable == Path(sys.executable).resolve(), "interpreter drift")
            for path in (executable, safe(command[1])):
                require(str(path) in p["frozen_files"], "unfrozen executable/script")


def benchmark_policy(p, task):
    candidate = p["candidates"][task]
    name = "manifest.json" if task == "hotpotqa" else "serving/manifest.json"
    manifest = read(safe(Path(candidate["path"]) / name))
    return {key: value for key, value in manifest.items()
            if key in ("mode", "qualification_eligible", "oracle_assisted_corpus")}
