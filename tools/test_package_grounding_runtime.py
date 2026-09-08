"""Tests for the standalone ExactScope grounding runtime package."""
from __future__ import annotations

import gzip
import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from package_grounding_runtime import (
    AR_MAGIC,
    GroundingRuntimePackageError,
    SAMPLE_INDEX_PATH,
    build_archive,
    sha256_file,
    verify_archive,
)

SOURCE_COMMIT = "0" * 40


class GroundingRuntimePackageTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, Path]:
        library = root / "libexactscope_cabi.a"
        library.write_bytes(AR_MAGIC + b"unit-static-library")
        sample = root / "sample.xsgi"
        sample.write_bytes(b"XSGI" + bytes(range(64)))
        return library, sample

    def build(self, root: Path, output: str = "out") -> Path:
        library, sample = self.fixture(root)
        return build_archive(
            library=library,
            sample_index=sample,
            target="x86_64-unknown-linux-gnu",
            source_commit=SOURCE_COMMIT,
            toolchain="unit-toolchain",
            output_dir=root / output,
        )

    def test_package_is_deterministic_and_explicit_about_provider_boundary(self):
        with tempfile.TemporaryDirectory(prefix="xs-grounding-runtime-unit-") as temporary:
            root = Path(temporary)
            library, sample = self.fixture(root)
            one = build_archive(
                library=library,
                sample_index=sample,
                target="x86_64-unknown-linux-gnu",
                source_commit=SOURCE_COMMIT,
                toolchain="unit-toolchain",
                output_dir=root / "one",
            )
            two = build_archive(
                library=library,
                sample_index=sample,
                target="x86_64-unknown-linux-gnu",
                source_commit=SOURCE_COMMIT,
                toolchain="unit-toolchain",
                output_dir=root / "two",
            )
            self.assertEqual(one.read_bytes(), two.read_bytes())
            result = verify_archive(one)
            manifest = result["manifest"]
            self.assertEqual(manifest["sample_provider"]["purpose"], "demonstration-only")
            self.assertEqual(
                manifest["deployment_boundary"]["provider_data"],
                "deployment-specific-not-included",
            )
            self.assertEqual(manifest["support_scope"]["physical_arm64"], "not-claimed")
            self.assertEqual(manifest["files"][SAMPLE_INDEX_PATH], sha256_file(sample))

    def test_rejects_non_xsgi_sample(self):
        with tempfile.TemporaryDirectory(prefix="xs-grounding-runtime-bad-sample-") as temporary:
            root = Path(temporary)
            library, sample = self.fixture(root)
            sample.write_bytes(b"NOT-XSGI")
            with self.assertRaisesRegex(GroundingRuntimePackageError, "XSGI magic"):
                build_archive(
                    library=library,
                    sample_index=sample,
                    target="x86_64-unknown-linux-gnu",
                    source_commit=SOURCE_COMMIT,
                    toolchain="unit-toolchain",
                    output_dir=root / "out",
                )

    def test_rejects_unqualified_target(self):
        with tempfile.TemporaryDirectory(prefix="xs-grounding-runtime-target-") as temporary:
            root = Path(temporary)
            library, sample = self.fixture(root)
            with self.assertRaisesRegex(GroundingRuntimePackageError, "only x86_64-unknown-linux-gnu"):
                build_archive(
                    library=library,
                    sample_index=sample,
                    target="aarch64-unknown-linux-musl",
                    source_commit=SOURCE_COMMIT,
                    toolchain="unit-toolchain",
                    output_dir=root / "out",
                )

    def test_verifier_rejects_duplicate_members_before_extraction(self):
        with tempfile.TemporaryDirectory(prefix="xs-grounding-runtime-duplicate-") as temporary:
            root = Path(temporary)
            archive_path = root / "duplicate.tar.gz"
            with tarfile.open(archive_path, mode="w:gz") as archive:
                directory = tarfile.TarInfo("exactscope-grounding-1.0.0-x86_64-unknown-linux-gnu/")
                directory.type = tarfile.DIRTYPE
                archive.addfile(directory)
                for payload in (b"first", b"second"):
                    member = tarfile.TarInfo(
                        "exactscope-grounding-1.0.0-x86_64-unknown-linux-gnu/manifest.json"
                    )
                    member.size = len(payload)
                    archive.addfile(member, io.BytesIO(payload))
            with self.assertRaisesRegex(GroundingRuntimePackageError, "duplicate archive member"):
                verify_archive(archive_path)

    def test_verifier_rejects_gzip_expansion_before_tar_parsing(self):
        with tempfile.TemporaryDirectory(prefix="xs-grounding-runtime-expansion-") as temporary:
            root = Path(temporary)
            archive_path = root / "expansion.tar.gz"
            with gzip.open(archive_path, mode="wb") as compressed:
                compressed.write(b"A" * 2048)
            with patch("package_grounding_runtime.MAX_ARCHIVE_TAR_BYTES", 1024):
                with self.assertRaisesRegex(GroundingRuntimePackageError, "decompressed tar stream"):
                    verify_archive(archive_path)


if __name__ == "__main__":
    unittest.main()
