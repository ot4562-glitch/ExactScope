"""Static tests for deterministic build-input identity. No build/runtime execution."""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from build_input_identity import (
    BuildInputError,
    file_hashes,
    recipe_document,
    verify_identity,
    write_identity,
)
from compile_capability import source_identity


class BuildInputIdentityTests(unittest.TestCase):
    def setUp(self):
        self.source = source_identity()
        self.inputs = file_hashes()

    def economics_wasm_profile(self) -> dict:
        return {
            "profile_id": "econ-unit",
            "profile_revision": 7,
            "domain": "economics",
            "runtime_surface": {
                "specialization": "economics-selected-wasm",
                "xs_calc": {"enabled": False, "plan_revision": None},
                "xs_eval": {"operations": ["econ.ped.mid"]},
            },
            "device_budget": {"target_profile": "no-import-wasm"},
            "bindings": {
                "core_revision": "sha256:" + self.source,
                "surface_contract_sha256": "1" * 64,
            },
        }

    def native_profile(self) -> dict:
        profile = self.economics_wasm_profile()
        profile["runtime_surface"]["specialization"] = "host-limited"
        profile["device_budget"]["target_profile"] = "native-static"
        return profile

    def test_wasm_recipe_is_deterministic_and_feature_explicit(self):
        kwargs = dict(
            profile=self.economics_wasm_profile(),
            capability_bundle_sha256="2" * 64,
            release_profile="no-import-wasm",
            target="wasm32v1-none",
            current_source_identity=self.source,
            inputs=self.inputs,
        )
        first = recipe_document(**kwargs)
        second = recipe_document(**kwargs)
        self.assertEqual(first, second)
        self.assertEqual(
            first["rust"]["features"],
            ["fused", "tinyjson", "econ-specialized", "econ-ped-mid"],
        )
        self.assertTrue(first["rust"]["locked"])
        self.assertIn("independent byte-for-byte rebuild comparison not yet performed", first["claim"])

    def test_native_recipe_records_standalone_staticlib_without_wasm_binding_assumption(self):
        document = recipe_document(
            profile=self.native_profile(),
            capability_bundle_sha256="3" * 64,
            release_profile="native-static",
            target="x86_64-unknown-linux-gnu",
            current_source_identity=self.source,
            inputs=self.inputs,
        )
        self.assertEqual(document["rust"]["features"], ["standalone-staticlib"])

    def test_stale_core_revision_and_bad_profile_fail_closed(self):
        stale = self.economics_wasm_profile()
        stale["bindings"]["core_revision"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(BuildInputError, "not current source"):
            recipe_document(
                profile=stale,
                capability_bundle_sha256="4" * 64,
                release_profile="no-import-wasm",
                target="wasm32v1-none",
                current_source_identity=self.source,
                inputs=self.inputs,
            )
        wrong = self.native_profile()
        with self.assertRaisesRegex(BuildInputError, "Wasm recipe requires"):
            recipe_document(
                profile=wrong,
                capability_bundle_sha256="4" * 64,
                release_profile="no-import-wasm",
                target="wasm32v1-none",
                current_source_identity=self.source,
                inputs=self.inputs,
            )

    def test_written_identity_is_immutable_and_verifies_against_current_tree(self):
        document = recipe_document(
            profile=self.native_profile(),
            capability_bundle_sha256="5" * 64,
            release_profile="native-static",
            target="x86_64-unknown-linux-gnu",
            current_source_identity=self.source,
            inputs=self.inputs,
        )
        with tempfile.TemporaryDirectory(prefix="xs-build-input-unit-") as temporary:
            output = Path(temporary) / "build-inputs.json"
            write_identity(document, output)
            write_identity(document, output)
            self.assertEqual(verify_identity(output), document)
            changed = copy.deepcopy(document)
            changed["target"] = "other-target"
            with self.assertRaisesRegex(BuildInputError, "do not overwrite provenance"):
                write_identity(changed, output)


if __name__ == "__main__":
    unittest.main()
