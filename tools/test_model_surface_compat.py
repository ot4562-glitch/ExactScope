"""Static unit tests for model-surface version negotiation. No runtime execution."""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from check_model_surface_compat import CompatibilityError, check_acceptance
from compile_capability import (
    ROOT,
    canonical,
    digest,
    load,
    model_surface_contract,
    source_identity,
    verify_bundle,
)


def write_bundle_fixture(root: Path) -> Path:
    """Create one internally consistent capability bundle without checked-in generated output."""
    root.mkdir()
    catalog = {
        "format": "exactscope.hotset",
        "format_version": "0.1",
        "abi": "1.0",
        "binding_sha256": "1" * 64,
        "packs": [{"id": "unit-pack", "version": "0.1"}],
        "operations": [{"op": "stats.mean", "revision": 1}],
    }
    assets = {
        "catalog.json": canonical(catalog),
        "prompt-fragment.txt": b"Use only the selected operation.\n",
        "task-map.json": canonical({"unit-family": ["stats.mean"]}),
        "xs-eval.gbnf": b"root ::= \"{}\"\n",
        "xs-eval.tool.json": b'{"type":"function"}\n',
    }
    profile = {
        "profile_id": "surface-unit",
        "profile_revision": 1,
        "domain": "statistics",
        "task_families": ["unit-family"],
        "runtime_surface": {
            "specialization": "host-limited",
            "xs_calc": {"enabled": False, "plan_revision": None},
            "xs_eval": {"operations": ["stats.mean"]},
            "xs_find": {"enabled": False},
            "model_visible_tools_max": 1,
            "normal_model_turns_max": 1,
        },
        "model_budget": {
            "semantic_operation_count": 1,
            "prompt_fragment_bytes_max": 1024,
            "schema_bytes_max": 4096,
            "grammar_bytes_max": 4096,
        },
        "device_budget": {"target_profile": "native-static"},
        "bindings": {
            "core_revision": "sha256:" + source_identity(),
            "abi_revision": "1.0",
            "registry_sha256": digest(canonical(catalog["packs"])),
            "hotset_sha256": "1" * 64,
            "tool_schema_sha256": digest(canonical({
                "xs-eval.tool.json": digest(assets["xs-eval.tool.json"]),
            })),
            "grammar_sha256": digest(canonical({
                "xs-eval.gbnf": digest(assets["xs-eval.gbnf"]),
            })),
            "prompt_sha256": digest(canonical({
                "prompt-fragment.txt": digest(assets["prompt-fragment.txt"]),
            })),
            "artifact_sha256": None,
        },
    }
    contract_bytes = canonical(model_surface_contract(profile, catalog, assets))
    profile["bindings"]["surface_contract_sha256"] = digest(contract_bytes)
    assets["surface-contract.json"] = contract_bytes
    assets["profile.json"] = canonical(profile)
    for name, data in assets.items():
        (root / name).write_bytes(data)
    manifest = {
        "format": "exactscope.capability.bundle",
        "format_version": "0.1",
        "files": {name: digest(data) for name, data in sorted(assets.items())},
        "measurements": {
            "prompt_fragment_bytes": len(assets["prompt-fragment.txt"]),
            "schema_bytes": len(assets["xs-eval.tool.json"]),
            "grammar_bytes": len(assets["xs-eval.gbnf"]),
            "top_level_tool_count": 1,
            "visible_semantic_operation_count": 1,
        },
        "operation_revisions": {"stats.mean": 1},
    }
    manifest_bytes = canonical(manifest)
    (root / "manifest.json").write_bytes(manifest_bytes)
    (root / "bundle-sha256.txt").write_text(digest(manifest_bytes) + "\n", encoding="ascii")
    verify_bundle(root)
    return root


class ModelSurfaceCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.profile = {
            "profile_id": "unit-surface",
            "profile_revision": 1,
            "domain": "statistics",
        }
        self.catalog = {
            "format": "exactscope.hotset",
            "format_version": "0.1",
            "abi": "1.0",
            "binding_sha256": "1" * 64,
        }
        self.assets = {
            "prompt-fragment.txt": b"Use only the bound surface.\n",
            "xs-eval.tool.json": b'{"type":"function"}\n',
            "xs-eval.gbnf": b"root ::= \"{}\"\n",
        }
        self.contract = model_surface_contract(self.profile, self.catalog, self.assets)
        self.policy = load(
            (ROOT / "spec/examples/model-surface-acceptance-v0.1.json").read_bytes()
        )

    def test_supported_contract_is_accepted(self):
        result = check_acceptance(self.contract, self.policy)
        self.assertEqual(result["status"], "COMPATIBLE")
        self.assertEqual(result["profile"], self.contract["profile"])
        self.assertEqual(len(result["asset_contracts"]), 3)

    def test_unknown_asset_contract_is_rejected(self):
        policy = copy.deepcopy(self.policy)
        del policy["accepted_asset_contracts"]["exactscope.xs-eval.tool"]
        with self.assertRaisesRegex(CompatibilityError, "not accepted"):
            check_acceptance(self.contract, policy)

    def test_abi_and_hotset_versions_fail_closed(self):
        for field, value in (("accepted_abi_revisions", ["2.0"]),
                             ("accepted_hotset_format_versions", ["9.9"])):
            policy = copy.deepcopy(self.policy)
            policy[field] = value
            with self.assertRaises(CompatibilityError):
                check_acceptance(self.contract, policy)

    def test_bundle_verifier_binds_contract_to_exact_assets(self):
        with tempfile.TemporaryDirectory(prefix="xs-surface-unit-") as temporary:
            root = write_bundle_fixture(Path(temporary) / "capability")
            prompt_path = root / "prompt-fragment.txt"
            prompt_path.write_bytes(b"Use only the changed operation.\n")

            profile_path = root / "profile.json"
            profile = load(profile_path.read_bytes())
            profile["bindings"]["prompt_sha256"] = digest(canonical({
                "prompt-fragment.txt": digest(prompt_path.read_bytes()),
            }))
            profile_bytes = canonical(profile)
            profile_path.write_bytes(profile_bytes)

            manifest_path = root / "manifest.json"
            manifest = load(manifest_path.read_bytes())
            manifest["files"]["prompt-fragment.txt"] = digest(prompt_path.read_bytes())
            manifest["files"]["profile.json"] = digest(profile_bytes)
            manifest["measurements"]["prompt_fragment_bytes"] = prompt_path.stat().st_size
            manifest_bytes = canonical(manifest)
            manifest_path.write_bytes(manifest_bytes)
            (root / "bundle-sha256.txt").write_text(digest(manifest_bytes) + "\n", encoding="ascii")

            with self.assertRaisesRegex(ValueError, "model-surface contract asset digest mismatch"):
                verify_bundle(root)

    def test_bundle_verifier_rejects_rehashed_cross_file_semantic_drift(self):
        with tempfile.TemporaryDirectory(prefix="xs-surface-cross-file-") as temporary:
            root = write_bundle_fixture(Path(temporary) / "capability")
            task_map_path = root / "task-map.json"
            task_map = load(task_map_path.read_bytes())
            task_map["unit-family"] = []
            task_map_path.write_bytes(canonical(task_map))

            manifest_path = root / "manifest.json"
            manifest = load(manifest_path.read_bytes())
            manifest["files"]["task-map.json"] = digest(task_map_path.read_bytes())
            manifest_bytes = canonical(manifest)
            manifest_path.write_bytes(manifest_bytes)
            (root / "bundle-sha256.txt").write_text(digest(manifest_bytes) + "\n", encoding="ascii")

            with self.assertRaisesRegex(ValueError, "task-map/runtime-surface mismatch"):
                verify_bundle(root)


if __name__ == "__main__":
    unittest.main()
