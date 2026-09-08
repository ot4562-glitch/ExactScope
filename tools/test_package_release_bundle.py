"""Static tests for generic release-shaped bundle packaging. No runtime execution."""
from __future__ import annotations

import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from build_input_identity import file_hashes, recipe_document, write_identity
from compile_capability import (ROOT, canonical, constrained_request_grammar,
                                constrained_request_prompt, digest, load,
                                model_surface_contract, model_surface_measurements,
                                source_identity)
from package_release_bundle import (
    AR_MAGIC,
    GROUNDING_RELEASE_PATH,
    ReleasePackagingError,
    build_archive,
    sha256_file,
    validate_native_input,
    verify_archive,
)

SOURCE_COMMIT = "0" * 40


def write_capability(root: Path, *, native: bool) -> Path:
    bundle = root / "capability"
    bundle.mkdir()
    catalog = {
        "format": "exactscope.hotset",
        "format_version": "0.1",
        "abi": "1.0",
        "binding_sha256": "1" * 64,
        "packs": [{"id": "unit-pack", "version": "0.1"}],
        "operations": [{"op": "stats.mean", "revision": 1, "sig": "stats.mean(v:vector)"}],
    }
    assets = {
        "catalog.json": canonical(catalog),
        "prompt-fragment.txt": b"Use only the selected operation.\n",
        "task-map.json": canonical({"unit-family": ["stats.mean"]}),
        "xs-eval.gbnf": b"root ::= \"{}\"\n",
        "xs-eval.tool.json": b'{"type":"function"}\n',
    }
    assets["constrained-prompt.txt"] = constrained_request_prompt(catalog, include_calc=False)
    assets["xs-request.gbnf"] = constrained_request_grammar(assets["xs-eval.gbnf"], None)
    profile = {
        "profile_id": "release-unit",
        "profile_revision": 1,
        "domain": "statistics",
        "task_families": ["unit-family"],
        "runtime_surface": {
            "specialization": "host-limited" if native else "statistics-selected-wasm",
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
        "device_budget": ({
            "target_profile": "native-static",
        } if native else {
            "target_profile": "no-import-wasm",
            "artifact_bytes_max": 131072,
            "imports_max": 0,
            "wasm_initial_pages_max": 1,
            "wasm_maximum_pages_max": 1,
        }),
        "bindings": {
            "core_revision": "sha256:" + source_identity(),
            "abi_revision": "1.0",
            "registry_sha256": digest(canonical(catalog["packs"])),
            "hotset_sha256": "1" * 64,
            "tool_schema_sha256": digest(canonical({"xs-eval.tool.json": digest(assets["xs-eval.tool.json"])})),
            "grammar_sha256": digest(canonical({
                name: digest(assets[name]) for name in sorted(n for n in assets if n.endswith(".gbnf"))
            })),
            "prompt_sha256": digest(canonical({
                name: digest(assets[name]) for name in ("prompt-fragment.txt", "constrained-prompt.txt")
            })),
            "artifact_sha256": None,
        },
    }
    contract = model_surface_contract(profile, catalog, assets)
    contract_bytes = canonical(contract)
    profile["bindings"]["surface_contract_sha256"] = digest(contract_bytes)
    assets["surface-contract.json"] = contract_bytes
    assets["profile.json"] = canonical(profile)
    for name, data in assets.items():
        (bundle / name).write_bytes(data)
    manifest = {
        "format": "exactscope.capability.bundle",
        "format_version": "0.1",
        "files": {name: digest(data) for name, data in sorted(assets.items())},
        "measurements": model_surface_measurements(assets, catalog),
        "operation_revisions": {"stats.mean": 1},
    }
    manifest_bytes = canonical(manifest)
    (bundle / "manifest.json").write_bytes(manifest_bytes)
    (bundle / "bundle-sha256.txt").write_text(digest(manifest_bytes) + "\n", encoding="ascii")
    return bundle


def minimal_wasm_fixture() -> bytes:
    """Return the smallest parser-valid no-import fixture with the required export surface."""
    exports = [
        ("memory", 2, 0),
        ("xs_abi_version", 0, 0),
        ("xs_wasm_reserved_end", 0, 1),
        ("xs_wasm_memory_alignment", 0, 2),
        ("xs_wasm_eval_statistics", 0, 3),
        ("xs_wire_request", 0, 4),
    ]
    export_payload = bytearray([len(exports)])
    for name, kind, index in exports:
        encoded = name.encode("ascii")
        export_payload.extend((len(encoded),))
        export_payload.extend(encoded)
        export_payload.extend((kind, index))
    memory_section = bytes((5, 4, 1, 1, 1, 1))
    export_section = bytes((7, len(export_payload))) + bytes(export_payload)
    return b"\x00asm\x01\x00\x00\x00" + memory_section + export_section


class ReleaseBundleTests(unittest.TestCase):
    def test_native_release_is_deterministic_and_keeps_capability_unbound(self):
        with tempfile.TemporaryDirectory(prefix="xs-release-unit-") as temporary:
            root = Path(temporary)
            capability = write_capability(root, native=True)
            library = root / "libexactscope_cabi.a"
            library.write_bytes(AR_MAGIC + b"unit-static-archive")
            first = build_archive(
                kind="native-static",
                capability=capability,
                target="x86_64-unknown-linux-gnu",
                source_commit=SOURCE_COMMIT,
                toolchain="unit-toolchain",
                output_dir=root / "one",
                library=library,
            )
            second = build_archive(
                kind="native-static",
                capability=capability,
                target="x86_64-unknown-linux-gnu",
                source_commit=SOURCE_COMMIT,
                toolchain="unit-toolchain",
                output_dir=root / "two",
                library=library,
            )
            self.assertEqual(first.read_bytes(), second.read_bytes())
            manifest = verify_archive(first)
            self.assertEqual(manifest["profile"], "native-static")
            self.assertEqual(manifest["support"], "experimental")
            self.assertEqual(manifest["qualification"], "unqualified")
            self.assertEqual(manifest["runtime"]["sha256"], sha256_file(library))
            self.assertEqual(manifest["capability"]["surface_negotiation"], "exact-version-and-digest")

    def test_native_release_hash_binds_optional_grounding_index(self):
        with tempfile.TemporaryDirectory(prefix="xs-release-grounding-unit-") as temporary:
            root = Path(temporary)
            capability = write_capability(root, native=True)
            library = root / "libexactscope_cabi.a"
            library.write_bytes(AR_MAGIC + b"unit-static-archive")
            grounding = root / "fixture.xsgi"
            grounding.write_bytes(b"XSGI" + bytes(range(64)))
            archive = build_archive(
                kind="native-static",
                capability=capability,
                target="x86_64-unknown-linux-gnu",
                source_commit=SOURCE_COMMIT,
                toolchain="unit-toolchain",
                output_dir=root / "out",
                library=library,
                grounding_index=grounding,
            )
            release = verify_archive(archive)
            self.assertEqual(release["grounding"]["path"], GROUNDING_RELEASE_PATH)
            self.assertEqual(release["grounding"]["size_bytes"], grounding.stat().st_size)
            self.assertEqual(release["grounding"]["sha256"], sha256_file(grounding))
            self.assertEqual(release["files"][GROUNDING_RELEASE_PATH], sha256_file(grounding))

    def test_native_release_rejects_non_xsgi_grounding_payload(self):
        with tempfile.TemporaryDirectory(prefix="xs-release-grounding-bad-unit-") as temporary:
            root = Path(temporary)
            capability = write_capability(root, native=True)
            library = root / "libexactscope_cabi.a"
            library.write_bytes(AR_MAGIC + b"unit-static-archive")
            grounding = root / "not-xsgi.bin"
            grounding.write_bytes(b"NOT-AN-XSGI")
            with self.assertRaisesRegex(ReleasePackagingError, "XSGI magic"):
                build_archive(
                    kind="native-static",
                    capability=capability,
                    target="x86_64-unknown-linux-gnu",
                    source_commit=SOURCE_COMMIT,
                    toolchain="unit-toolchain",
                    output_dir=root / "out",
                    library=library,
                    grounding_index=grounding,
                )

    def test_native_release_rejects_artifact_bound_profile(self):
        with tempfile.TemporaryDirectory(prefix="xs-release-bound-unit-") as temporary:
            root = Path(temporary)
            capability = write_capability(root, native=True)
            library = root / "libexactscope_cabi.a"
            library.write_bytes(AR_MAGIC + b"unit-static-archive")
            profile_path = capability / "profile.json"
            profile = load(profile_path.read_bytes())
            runtime = capability / "runtime.wasm"
            runtime.write_bytes(b"unit-bound-runtime")
            profile["bindings"]["artifact_sha256"] = sha256_file(runtime)
            profile_path.write_bytes(canonical(profile))
            manifest_path = capability / "manifest.json"
            manifest = load(manifest_path.read_bytes())
            manifest["files"]["profile.json"] = sha256_file(profile_path)
            manifest["files"]["runtime.wasm"] = sha256_file(runtime)
            manifest_bytes = canonical(manifest)
            manifest_path.write_bytes(manifest_bytes)
            (capability / "bundle-sha256.txt").write_text(digest(manifest_bytes) + "\n", encoding="ascii")
            with self.assertRaisesRegex(ReleasePackagingError, "unbound capability"):
                validate_native_input(capability, library)

    def test_native_release_optionally_binds_current_build_input_identity(self):
        with tempfile.TemporaryDirectory(prefix="xs-release-build-input-") as temporary:
            root = Path(temporary)
            capability = write_capability(root, native=True)
            library = root / "libexactscope_cabi.a"
            library.write_bytes(AR_MAGIC + b"unit-static-archive")
            profile = load((capability / "profile.json").read_bytes())
            document = recipe_document(
                profile=profile,
                capability_bundle_sha256=(capability / "bundle-sha256.txt").read_text(encoding="ascii").strip(),
                release_profile="native-static",
                target="x86_64-unknown-linux-gnu",
                current_source_identity=source_identity(),
                inputs=file_hashes(),
            )
            build_inputs = root / "build-inputs.json"
            write_identity(document, build_inputs)
            archive = build_archive(
                kind="native-static",
                capability=capability,
                target="x86_64-unknown-linux-gnu",
                source_commit=SOURCE_COMMIT,
                toolchain="unit-toolchain",
                output_dir=root / "out",
                library=library,
                build_inputs=build_inputs,
            )
            release = verify_archive(archive)
            self.assertEqual(release["build_inputs"]["source_identity_sha256"], source_identity())
            self.assertEqual(release["files"]["build-inputs.json"], release["build_inputs"]["sha256"])

    def test_archive_rejects_duplicate_and_link_members_before_extraction(self):
        with tempfile.TemporaryDirectory(prefix="xs-release-malformed-") as temporary:
            root = Path(temporary)
            duplicate = root / "duplicate.tar.gz"
            with tarfile.open(duplicate, mode="w:gz") as archive:
                directory = tarfile.TarInfo("unit-root/")
                directory.type = tarfile.DIRTYPE
                archive.addfile(directory)
                for payload in (b"first", b"second"):
                    member = tarfile.TarInfo("unit-root/manifest.json")
                    member.size = len(payload)
                    archive.addfile(member, io.BytesIO(payload))
            with self.assertRaisesRegex(ReleasePackagingError, "duplicate archive member path"):
                verify_archive(duplicate)

            linked = root / "linked.tar.gz"
            with tarfile.open(linked, mode="w:gz") as archive:
                directory = tarfile.TarInfo("unit-root/")
                directory.type = tarfile.DIRTYPE
                archive.addfile(directory)
                member = tarfile.TarInfo("unit-root/alias")
                member.type = tarfile.SYMTYPE
                member.linkname = "manifest.json"
                archive.addfile(member)
            with self.assertRaisesRegex(ReleasePackagingError, "forbidden archive member type"):
                verify_archive(linked)

    def test_wasm_release_static_path_accepts_artifact_bound_clean_source_fixture(self):
        with tempfile.TemporaryDirectory(prefix="xs-release-wasm-unit-") as temporary:
            root = Path(temporary)
            capability = write_capability(root, native=False)
            runtime = capability / "runtime.wasm"
            module = minimal_wasm_fixture()
            runtime.write_bytes(module)
            artifact_sha256 = digest(module)

            profile_path = capability / "profile.json"
            profile = load(profile_path.read_bytes())
            profile["bindings"]["artifact_sha256"] = artifact_sha256
            profile_bytes = canonical(profile)
            profile_path.write_bytes(profile_bytes)

            manifest_path = capability / "manifest.json"
            manifest = load(manifest_path.read_bytes())
            manifest["files"]["profile.json"] = digest(profile_bytes)
            manifest["files"]["runtime.wasm"] = artifact_sha256
            manifest["artifact_measurements"] = {
                "bytes": len(module),
                "imports": 0,
                "initial_memory_pages": 1,
                "maximum_memory_pages": 1,
            }
            manifest_bytes = canonical(manifest)
            manifest_path.write_bytes(manifest_bytes)
            (capability / "bundle-sha256.txt").write_text(
                digest(manifest_bytes) + "\n", encoding="ascii")

            archive = build_archive(
                kind="no-import-wasm",
                capability=capability,
                target="wasm32v1-none",
                source_commit=SOURCE_COMMIT,
                toolchain="unit-toolchain",
                output_dir=root / "out",
            )
            release = verify_archive(archive)
            self.assertEqual(release["profile"], "no-import-wasm")
            self.assertEqual(release["runtime"]["path"], "capability/runtime.wasm")
            self.assertEqual(release["runtime"]["size_bytes"], runtime.stat().st_size)


if __name__ == "__main__":
    unittest.main()
