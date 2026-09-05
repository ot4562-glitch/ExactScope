"""Static tests for reproducible-build comparison records. No artifact execution."""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from build_input_identity import file_hashes, recipe_document, write_identity
from compare_reproducible_builds import (
    RebuildComparisonError,
    compare,
    verify_record,
    write_record,
)
from compile_capability import canonical, load, source_identity


class ReproducibleBuildComparisonTests(unittest.TestCase):
    def setUp(self):
        self.source = source_identity()

    def write_build_inputs(self, root: Path) -> Path:
        profile = {
            "profile_id": "rebuild-unit",
            "profile_revision": 1,
            "domain": "statistics",
            "runtime_surface": {
                "specialization": "host-limited",
                "xs_calc": {"enabled": False, "plan_revision": None},
                "xs_eval": {"operations": ["stats.mean"]},
            },
            "device_budget": {"target_profile": "native-static"},
            "bindings": {
                "core_revision": "sha256:" + self.source,
                "surface_contract_sha256": "1" * 64,
            },
        }
        document = recipe_document(
            profile=profile,
            capability_bundle_sha256="2" * 64,
            release_profile="native-static",
            target="x86_64-unknown-linux-gnu",
            current_source_identity=self.source,
            inputs=file_hashes(),
        )
        output = root / "build-inputs.json"
        write_identity(document, output)
        return output

    def test_identical_outputs_record_match_without_claiming_builder_independence(self):
        with tempfile.TemporaryDirectory(prefix="xs-rebuild-match-") as temporary:
            root = Path(temporary)
            build_inputs = self.write_build_inputs(root)
            first = root / "builder-a.a"
            second = root / "builder-b.a"
            first.write_bytes(b"!<arch>\nbyte-identical-unit")
            second.write_bytes(first.read_bytes())
            record = compare(
                build_inputs=build_inputs,
                artifact_a=first,
                builder_a="builder-a",
                artifact_b=second,
                builder_b="builder-b",
            )
            self.assertEqual(record["status"], "MATCH")
            self.assertTrue(record["byte_identical"])
            self.assertIn("builder independence", record["claim"])
            output = root / "comparison.json"
            write_record(record, output)
            self.assertEqual(verify_record(output, build_inputs), record)

    def test_different_outputs_record_mismatch_and_no_reproducible_build_proof(self):
        with tempfile.TemporaryDirectory(prefix="xs-rebuild-mismatch-") as temporary:
            root = Path(temporary)
            build_inputs = self.write_build_inputs(root)
            first = root / "builder-a.a"
            second = root / "builder-b.a"
            first.write_bytes(b"!<arch>\nfirst")
            second.write_bytes(b"!<arch>\nsecond")
            record = compare(
                build_inputs=build_inputs,
                artifact_a=first,
                builder_a="builder-a",
                artifact_b=second,
                builder_b="builder-b",
            )
            self.assertEqual(record["status"], "MISMATCH")
            self.assertFalse(record["byte_identical"])
            self.assertEqual(record["claim"], "Build outputs differ; reproducible-build proof is not established.")

    def test_same_builder_id_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="xs-rebuild-builder-") as temporary:
            root = Path(temporary)
            build_inputs = self.write_build_inputs(root)
            first = root / "one.a"
            second = root / "two.a"
            first.write_bytes(b"one")
            second.write_bytes(b"one")
            with self.assertRaisesRegex(RebuildComparisonError, "builder IDs must be distinct"):
                compare(
                    build_inputs=build_inputs,
                    artifact_a=first,
                    builder_a="same-builder",
                    artifact_b=second,
                    builder_b="same-builder",
                )

    def test_record_tampering_and_evidence_overwrite_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="xs-rebuild-tamper-") as temporary:
            root = Path(temporary)
            build_inputs = self.write_build_inputs(root)
            first = root / "one.a"
            second = root / "two.a"
            first.write_bytes(b"same")
            second.write_bytes(b"same")
            record = compare(
                build_inputs=build_inputs,
                artifact_a=first,
                builder_a="a",
                artifact_b=second,
                builder_b="b",
            )
            output = root / "comparison.json"
            write_record(record, output)

            changed = copy.deepcopy(record)
            changed["builders"][1]["artifact_sha256"] = "0" * 64
            with self.assertRaisesRegex(RebuildComparisonError, "do not overwrite evidence"):
                write_record(changed, output)

            tampered = load(output.read_bytes())
            tampered["status"] = "MISMATCH"
            output.write_bytes(canonical(tampered))
            with self.assertRaisesRegex(RebuildComparisonError, "status disagrees"):
                verify_record(output, build_inputs)


if __name__ == "__main__":
    unittest.main()
