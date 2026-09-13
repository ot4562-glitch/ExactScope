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
    FORMAT_VERSION,
    HOST_ATTACHED_PROFILE,
    LEGACY_FORMAT_VERSION,
    V11_COMPRESSED_BYTES_MAX,
    GroundingRuntimePackageError,
    SAMPLE_INDEX_PATH,
    build_archive,
    sha256_file,
    validate_manifest,
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
            self.assertEqual(manifest["format_version"], FORMAT_VERSION)
            self.assertEqual(manifest["sample_provider"]["purpose"], "demonstration-only")
            self.assertEqual(
                manifest["deployment_boundary"]["provider_data"],
                "deployment-specific-not-included",
            )
            self.assertEqual(manifest["support_scope"]["physical_arm64"], "not-claimed")
            self.assertEqual(manifest["host_integration"]["surface"], "v1.1-prepared-runtime-amplifier-v1")
            self.assertEqual(manifest["host_integration"]["corpus_projection"], "precision-context-v5")
            self.assertEqual(manifest["host_integration"]["corpus_evidence_policy"], "adaptive-evidence-v1")
            self.assertEqual(manifest["host_integration"]["corpus_evidence_max_bytes"], 2048)
            self.assertEqual(manifest["host_integration"]["corpus_evidence_tiers_bytes"], [512, 1024, 2048])
            self.assertEqual(manifest["host_integration"]["answer_contract"], "typed-answer-contract-v1")
            self.assertEqual(manifest["host_integration"]["answer_kinds"], ["text", "choice", "boolean", "integer", "number"])
            self.assertEqual(manifest["host_integration"]["capability_cache"], "identity-bound-capability-cache-v2")
            self.assertEqual(manifest["host_integration"]["prefix_cache_hint"], "stable-prefix-cache-key-v2")
            self.assertEqual(manifest["host_integration"]["session_cache"], "prepared-immutable-amplifier-v1")
            self.assertFalse(manifest["host_integration"]["hot_path_artifact_io"])
            self.assertEqual(manifest["host_integration"]["backend_prompt_cache"], "host-owned-parity-gated")
            self.assertEqual(manifest["host_integration"]["model_answer_calls"], "zero-or-one")
            self.assertEqual(manifest["host_integration"]["second_model_calls"], 0)
            self.assertEqual(manifest["host_integration"]["retry_count"], 0)
            self.assertEqual(
                manifest["host_integration"]["transport"],
                "direct-literal-loopback-http-no-proxy-no-redirect-v1",
            )
            self.assertEqual(manifest["host_integration"]["record_validation"], "cold-path-strict-json-recompute-v1")
            self.assertEqual(manifest["host_integration"]["diagnostic"], "doctor-zero-network-v1")
            self.assertFalse(manifest["host_integration"]["native_core_requires_python"])
            self.assertIn("adapters/llama-cpp/grounding_v1.py", manifest["files"])
            self.assertIn("grounding/reference-profile-v0.1/profile.json", manifest["files"])
            self.assertEqual(manifest["files"][SAMPLE_INDEX_PATH], sha256_file(sample))

            legacy = dict(manifest)
            legacy["release_version"] = "1.0.0"
            legacy["format_version"] = LEGACY_FORMAT_VERSION
            legacy.pop("host_integration")
            validate_manifest(legacy)
            incompatible = dict(legacy)
            incompatible["host_integration"] = manifest["host_integration"]
            with self.assertRaisesRegex(GroundingRuntimePackageError, "fields do not match"):
                validate_manifest(incompatible)

    def test_host_attached_profile_excludes_local_retrieval_payload(self):
        with tempfile.TemporaryDirectory(prefix="xs-grounding-runtime-host-attached-") as temporary:
            root = Path(temporary)
            library, sample = self.fixture(root)
            archive = build_archive(
                library=library,
                sample_index=None,
                target="x86_64-unknown-linux-gnu",
                source_commit=SOURCE_COMMIT,
                toolchain="unit-toolchain",
                output_dir=root / "out",
                package_profile=HOST_ATTACHED_PROFILE,
            )
            manifest = verify_archive(archive)["manifest"]
            self.assertEqual(manifest["package_profile"], HOST_ATTACHED_PROFILE)
            self.assertIsNone(manifest["sample_provider"])
            forbidden = {
                SAMPLE_INDEX_PATH,
                "tools/grounding_corpus.py",
                "examples/c/grounding.c",
                "examples/grounding/sample-docs/device-state.md",
                "examples/grounding/sample-docs/service-policy.md",
            }
            self.assertFalse(forbidden & set(manifest["files"]))
            self.assertIn("tools/grounding_text.py", manifest["files"])
            self.assertIn("tools/grounding_projection.py", manifest["files"])
            self.assertIn("tools/grounding_engine.py", manifest["files"])
            with self.assertRaisesRegex(GroundingRuntimePackageError, "must not receive a sample index"):
                build_archive(
                    library=library,
                    sample_index=sample,
                    target="x86_64-unknown-linux-gnu",
                    source_commit=SOURCE_COMMIT,
                    toolchain="unit-toolchain",
                    output_dir=root / "bad",
                    package_profile=HOST_ATTACHED_PROFILE,
                )

    def test_verifier_enforces_v11_promotion_gate(self):
        with tempfile.TemporaryDirectory(prefix="xs-grounding-runtime-gate-") as temporary:
            root = Path(temporary)
            archive = self.build(root)
            size = archive.stat().st_size
            self.assertLess(size, V11_COMPRESSED_BYTES_MAX)
            with patch("package_grounding_runtime.V11_COMPRESSED_BYTES_MAX", size - 1):
                with self.assertRaisesRegex(GroundingRuntimePackageError, "promotion gate"):
                    verify_archive(archive)

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
