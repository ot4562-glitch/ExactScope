"""Static tests for release compatibility records. No ExactScope execution."""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from compile_capability import canonical
from package_release_bundle import AR_MAGIC, build_archive
from record_release_compatibility import (
    CompatibilityRecordError,
    pack_format_version,
    record_for_archive,
    validate_record,
    verify_record,
    write_record,
)
from test_package_release_bundle import SOURCE_COMMIT, write_capability


class ReleaseCompatibilityRecordTests(unittest.TestCase):
    def make_archive(self, root: Path) -> Path:
        capability = write_capability(root, native=True)
        library = root / "libexactscope_cabi.a"
        library.write_bytes(AR_MAGIC + b"compatibility-record-unit")
        return build_archive(
            kind="native-static",
            capability=capability,
            target="x86_64-unknown-linux-gnu",
            source_commit=SOURCE_COMMIT,
            toolchain="unit-toolchain",
            output_dir=root / "release",
            library=library,
        )

    def test_record_binds_exact_release_runtime_capability_and_model_surface(self):
        with tempfile.TemporaryDirectory(prefix="xs-compat-record-") as temporary:
            root = Path(temporary)
            archive = self.make_archive(root)
            document = record_for_archive(archive)
            artifact = document["artifacts"][0]
            identity = artifact["release_identity"]
            self.assertEqual(document["core_abi"], "1.0")
            self.assertEqual(document["pack_format"], "1.0")
            self.assertEqual(artifact["support"], "experimental")
            self.assertEqual(identity["release_profile"], "native-static")
            self.assertEqual(identity["abi_revision"], "1.0")
            self.assertEqual(artifact["sha256"], identity["release_archive_sha256"])
            self.assertEqual(len(identity["runtime_sha256"]), 64)
            self.assertEqual(len(identity["capability_bundle_sha256"]), 64)
            self.assertEqual(len(identity["model_surface_sha256"]), 64)

            output = root / "compatibility.json"
            write_record(document, output)
            self.assertEqual(verify_record(output, archive), document)

    def test_record_tool_refuses_support_promotion(self):
        with tempfile.TemporaryDirectory(prefix="xs-compat-tier-") as temporary:
            root = Path(temporary)
            document = record_for_archive(self.make_archive(root))
            promoted = copy.deepcopy(document)
            promoted["artifacts"][0]["support"] = "tier2"
            with self.assertRaisesRegex(CompatibilityRecordError, "experimental compatibility only"):
                validate_record(promoted)

    def test_tampered_record_does_not_verify_against_release_archive(self):
        with tempfile.TemporaryDirectory(prefix="xs-compat-tamper-") as temporary:
            root = Path(temporary)
            archive = self.make_archive(root)
            document = record_for_archive(archive)
            output = root / "compatibility.json"
            write_record(document, output)
            tampered = copy.deepcopy(document)
            tampered["artifacts"][0]["release_identity"]["runtime_sha256"] = "0" * 64
            output.write_bytes(canonical(tampered))
            with self.assertRaisesRegex(CompatibilityRecordError, "does not match the exact release archive"):
                verify_record(output, archive)

    def test_pack_format_is_derived_from_runtime_source_constants(self):
        self.assertEqual(pack_format_version(), "1.0")


if __name__ == "__main__":
    unittest.main()
