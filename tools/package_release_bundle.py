#!/usr/bin/env python3
"""Build/verify deterministic release-shaped ExactScope integration bundles.

The packager is intentionally off-target. It never executes ExactScope. Native
bundles require an unbound host-limited capability plus a static library; Wasm
bundles require an already artifact-bound no-import capability. All output is
experimental until independent release/target evidence promotes it.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import shutil
import tarfile
import tempfile
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator

from build_input_identity import BuildInputError
from build_input_identity import validate_document as validate_build_input_document
from build_input_identity import verify_identity as verify_build_input_identity
from compile_capability import ROOT, load, verify_bundle
from inspect_wasm import (
    WasmError,
    inspect_exports,
    inspect_imports,
    inspect_memories,
    parse_sections,
    validate_exports,
)

FORMAT = "exactscope.release.bundle"
FORMAT_VERSION = "0.1"
SOURCE_COMMIT_RE = re.compile(r"^[a-f0-9]{40}$")
SAFE_COMPONENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
AR_MAGIC = b"!<arch>\n"
RELEASE_SCHEMA = ROOT / "spec/schemas/release-bundle.schema.json"
MAX_ARCHIVE_MEMBERS = 512
MAX_ARCHIVE_MEMBER_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_PATH_BYTES = 512


class ReleasePackagingError(Exception):
    """Raised when an integration bundle would be ambiguous or unsafe."""


def validate_release_manifest(manifest: dict[str, Any]) -> None:
    schema = load(RELEASE_SCHEMA.read_bytes())
    errors = sorted(
        Draft202012Validator(schema).iter_errors(manifest),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path) or "<root>"
        raise ReleasePackagingError(f"release manifest schema failed at {location}: {first.message}")


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def release_version() -> str:
    with (ROOT / "Cargo.toml").open("rb") as handle:
        document = tomllib.load(handle)
    version = document.get("workspace", {}).get("package", {}).get("version")
    if not isinstance(version, str) or not SAFE_COMPONENT_RE.fullmatch(version):
        raise ReleasePackagingError("workspace release version is not archive-safe")
    return version


def safe_component(value: str, label: str) -> str:
    if not SAFE_COMPONENT_RE.fullmatch(value):
        raise ReleasePackagingError(f"invalid {label}: {value!r}")
    return value


def release_root_name(manifest: dict[str, Any]) -> str:
    capability = manifest.get("capability") if isinstance(manifest, dict) else None
    if not isinstance(capability, dict):
        raise ReleasePackagingError("release manifest capability identity is invalid")
    profile_id = safe_component(capability.get("profile_id"), "profile id")
    revision = capability.get("profile_revision")
    if not isinstance(revision, int) or revision < 1:
        raise ReleasePackagingError("invalid capability profile revision")
    return (
        f"exactscope-{safe_component(manifest.get('profile'), 'release profile')}-"
        f"{safe_component(manifest.get('release_version'), 'release version')}-"
        f"{profile_id}-r{revision}-{safe_component(manifest.get('target'), 'target')}"
    )


def normalized_member_name(name: str) -> PurePosixPath:
    if not isinstance(name, str) or len(name.encode("utf-8")) > MAX_ARCHIVE_PATH_BYTES:
        raise ReleasePackagingError("archive path is missing or too long")
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
        raise ReleasePackagingError(f"unsafe archive path: {name!r}")
    return path


def capability_metadata(capability: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    try:
        manifest = verify_bundle(capability)
        profile = load((capability / "profile.json").read_bytes())
        surface = load((capability / "surface-contract.json").read_bytes())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ReleasePackagingError(f"invalid capability bundle: {exc}") from exc
    bindings = profile.get("bindings")
    if not isinstance(bindings, dict) or bindings.get("surface_contract_sha256") != sha256_file(capability / "surface-contract.json"):
        raise ReleasePackagingError("capability is not bound to explicit model-surface negotiation")
    return manifest, profile, surface


def validate_build_inputs_for_release(
    build_inputs: Path,
    capability: Path,
    profile: dict[str, Any],
    release_profile: str,
    target: str,
) -> dict[str, Any]:
    try:
        document = verify_build_input_identity(build_inputs)
    except (BuildInputError, OSError, ValueError, json.JSONDecodeError) as exc:
        raise ReleasePackagingError(f"invalid build-input identity: {exc}") from exc
    capability_digest = (capability / "bundle-sha256.txt").read_text(encoding="ascii").strip()
    expected_capability = {
        "bundle_sha256": capability_digest,
        "profile_id": profile.get("profile_id"),
        "profile_revision": profile.get("profile_revision"),
        "domain": profile.get("domain"),
        "core_revision": profile.get("bindings", {}).get("core_revision"),
        "surface_contract_sha256": profile.get("bindings", {}).get("surface_contract_sha256"),
    }
    if document.get("capability") != expected_capability:
        raise ReleasePackagingError("build-input identity/capability mismatch")
    if document.get("release_profile") != release_profile or document.get("target") != target:
        raise ReleasePackagingError("build-input identity release profile/target mismatch")
    return document


def validate_native_input(capability: Path, library: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest, profile, surface = capability_metadata(capability)
    if (capability / "runtime.wasm").exists() or profile["bindings"].get("artifact_sha256") is not None:
        raise ReleasePackagingError("native release requires an unbound capability; do not reuse a Wasm artifact binding")
    runtime_surface = profile.get("runtime_surface", {})
    device = profile.get("device_budget", {})
    if runtime_surface.get("specialization") != "host-limited" or device.get("target_profile") != "native-static":
        raise ReleasePackagingError("native release requires host-limited specialization with native-static device profile")
    if library.name not in {"libexactscope_cabi.a", "exactscope_cabi.lib"}:
        raise ReleasePackagingError("native runtime must use the canonical ExactScope static-library filename")
    data = library.read_bytes()
    if len(data) <= len(AR_MAGIC) or not data.startswith(AR_MAGIC):
        raise ReleasePackagingError("native runtime is not an ar/COFF static archive")
    return manifest, profile, surface


def validate_wasm_input(capability: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest, profile, surface = capability_metadata(capability)
    runtime = capability / "runtime.wasm"
    artifact = profile["bindings"].get("artifact_sha256")
    if not runtime.is_file() or artifact != sha256_file(runtime) or manifest.get("files", {}).get("runtime.wasm") != artifact:
        raise ReleasePackagingError("Wasm release requires an artifact-bound capability with matching runtime.wasm")
    device = profile.get("device_budget", {})
    if device.get("target_profile") != "no-import-wasm":
        raise ReleasePackagingError("Wasm release capability does not declare the no-import-wasm device profile")

    module = runtime.read_bytes()
    budget = device.get("artifact_bytes_max")
    if not isinstance(budget, int) or len(module) > budget:
        raise ReleasePackagingError("Wasm runtime exceeds the selected capability artifact budget")
    try:
        sections = parse_sections(module)
        if any(section.section_id in (8, 13) for section in sections):
            raise ReleasePackagingError("Wasm runtime contains a forbidden start/tag section")
        imports = inspect_imports(sections)
        if imports != 0 or imports > (device.get("imports_max") if isinstance(device.get("imports_max"), int) else 0):
            raise ReleasePackagingError("Wasm release runtime must have zero imports")
        minimum, maximum = inspect_memories(sections)
        initial_limit = device.get("wasm_initial_pages_max")
        maximum_limit = device.get("wasm_maximum_pages_max")
        if isinstance(initial_limit, int) and minimum > initial_limit:
            raise ReleasePackagingError("Wasm initial memory exceeds the selected capability budget")
        if maximum is None or (isinstance(maximum_limit, int) and maximum > maximum_limit):
            raise ReleasePackagingError("Wasm maximum memory is missing or exceeds the selected capability budget")
        validate_exports(inspect_exports(sections))
        measurements = manifest.get("artifact_measurements")
        if not isinstance(measurements, dict) or (
                measurements.get("bytes"), measurements.get("imports"),
                measurements.get("initial_memory_pages"), measurements.get("maximum_memory_pages")) != (
                len(module), imports, minimum, maximum):
            raise ReleasePackagingError("Wasm manifest measurements disagree with static artifact inspection")
    except WasmError as exc:
        raise ReleasePackagingError(f"invalid no-import Wasm runtime: {exc}") from exc
    return manifest, profile, surface


def copy_file(source: Path, destination: Path) -> None:
    if source.is_symlink() or not source.is_file():
        raise ReleasePackagingError(f"release payload must be a regular file: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def copy_capability(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    for child in sorted(source.iterdir(), key=lambda item: item.name):
        if child.is_symlink() or not child.is_file():
            raise ReleasePackagingError(f"capability bundle contains a non-file payload: {child.name}")
        copy_file(child, destination / child.name)


def payload_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in {"manifest.json", "SHA256SUMS"}:
            continue
        hashes[relative] = sha256_file(path)
    return hashes


def checksum_text(root: Path, names: list[str]) -> str:
    return "".join(f"{sha256_file(root / name)}  {name}\n" for name in names)


def stage_bundle(
    stage_parent: Path,
    *,
    kind: str,
    capability: Path,
    target: str,
    source_commit: str,
    toolchain: str,
    library: Path | None = None,
    build_inputs: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    safe_component(target, "target")
    if not SOURCE_COMMIT_RE.fullmatch(source_commit):
        raise ReleasePackagingError("source commit must be exactly 40 lowercase hexadecimal characters")
    if not toolchain or len(toolchain) > 200 or any(ch in toolchain for ch in "\r\n"):
        raise ReleasePackagingError("invalid toolchain identity")

    if kind == "native-static":
        if library is None:
            raise ReleasePackagingError("native release requires a static library")
        _, profile, surface = validate_native_input(capability, library)
    elif kind == "no-import-wasm":
        if library is not None:
            raise ReleasePackagingError("Wasm release must use runtime.wasm from the bound capability")
        _, profile, surface = validate_wasm_input(capability)
    else:
        raise ReleasePackagingError(f"unsupported release kind: {kind}")

    build_input_document = None
    if build_inputs is not None:
        build_input_document = validate_build_inputs_for_release(
            build_inputs, capability, profile, kind, target
        )

    profile_id = safe_component(profile["profile_id"], "profile id")
    revision = profile["profile_revision"]
    if not isinstance(revision, int) or revision < 1:
        raise ReleasePackagingError("invalid capability profile revision")
    name = f"exactscope-{kind}-{release_version()}-{profile_id}-r{revision}-{target}"
    root = stage_parent / name
    root.mkdir(parents=True, exist_ok=False)

    copy_capability(capability, root / "capability")
    for license_name in ("LICENSE-MIT", "LICENSE-APACHE", "THIRD_PARTY_NOTICES.md"):
        copy_file(ROOT / license_name, root / license_name)
    if build_inputs is not None:
        copy_file(build_inputs, root / "build-inputs.json")

    if kind == "native-static":
        copy_file(ROOT / "include/exactscope.h", root / "include/exactscope.h")
        copy_file(ROOT / "include/exactscope_platform.h", root / "include/exactscope_platform.h")
        copy_file(ROOT / "cmake/ExactScopeConfig.cmake", root / "lib/cmake/ExactScope/ExactScopeConfig.cmake")
        runtime_path = f"lib/{target}/{library.name}"
        copy_file(library, root / runtime_path)
    else:
        copy_file(ROOT / "include/exactscope.h", root / "include/exactscope.h")
        copy_file(ROOT / "include/exactscope_wasm.h", root / "include/exactscope_wasm.h")
        runtime_path = "capability/runtime.wasm"

    files = payload_hashes(root)
    capability_digest = (capability / "bundle-sha256.txt").read_text(encoding="ascii").strip()
    manifest = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "release_version": release_version(),
        "support": "experimental",
        "qualification": "unqualified",
        "profile": kind,
        "target": target,
        "source_commit": source_commit,
        "toolchain": toolchain,
        "capability": {
            "path": "capability",
            "profile_id": profile_id,
            "profile_revision": revision,
            "domain": profile["domain"],
            "abi_revision": profile["bindings"]["abi_revision"],
            "bundle_sha256": capability_digest,
            "surface_contract_sha256": profile["bindings"]["surface_contract_sha256"],
            "surface_negotiation": surface["negotiation"],
        },
        "runtime": {
            "path": runtime_path,
            "size_bytes": (root / runtime_path).stat().st_size,
            "sha256": sha256_file(root / runtime_path),
        },
        "files": files,
    }
    if build_input_document is not None:
        manifest["build_inputs"] = {
            "path": "build-inputs.json",
            "sha256": files["build-inputs.json"],
            "source_identity_sha256": build_input_document["source_identity_sha256"],
        }
    validate_release_manifest(manifest)
    (root / "manifest.json").write_bytes(canonical(manifest))
    checksum_names = sorted([*files, "manifest.json"])
    (root / "SHA256SUMS").write_text(checksum_text(root, checksum_names), encoding="ascii", newline="\n")
    return root, manifest


def deterministic_archive_bytes(root: Path) -> bytes:
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        paths = [root, *sorted(root.rglob("*"), key=lambda path: path.relative_to(root.parent).as_posix())]
        for path in paths:
            relative = path.relative_to(root.parent).as_posix()
            if path.is_symlink():
                raise ReleasePackagingError(f"symlink forbidden in release bundle: {relative}")
            info = tarfile.TarInfo(relative + ("/" if path.is_dir() else ""))
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            if path.is_dir():
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                info.size = 0
                archive.addfile(info)
            elif path.is_file():
                data = path.read_bytes()
                info.mode = 0o644
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
            else:
                raise ReleasePackagingError(f"unsupported release payload type: {relative}")
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0, compresslevel=9) as compressed:
        compressed.write(tar_buffer.getvalue())
    return output.getvalue()


def parse_checksums(text: str) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for line in text.splitlines():
        if not line:
            continue
        match = re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9][A-Za-z0-9._/-]*)", line)
        if match is None or match.group(2) in checksums:
            raise ReleasePackagingError("invalid or duplicate SHA256SUMS entry")
        relative = normalized_member_name(match.group(2)).as_posix()
        checksums[relative] = match.group(1)
    if not checksums:
        raise ReleasePackagingError("SHA256SUMS is empty")
    return checksums


def verify_extracted(root: Path) -> dict[str, Any]:
    manifest_path = root / "manifest.json"
    checksum_path = root / "SHA256SUMS"
    if not manifest_path.is_file() or not checksum_path.is_file():
        raise ReleasePackagingError("release bundle is missing manifest.json or SHA256SUMS")
    manifest_bytes = manifest_path.read_bytes()
    manifest = load(manifest_bytes)
    if canonical(manifest) != manifest_bytes:
        raise ReleasePackagingError("release manifest is not canonical")
    validate_release_manifest(manifest)
    if (manifest.get("format"), manifest.get("format_version")) != (FORMAT, FORMAT_VERSION):
        raise ReleasePackagingError("unsupported release bundle format")
    if root.name != release_root_name(manifest):
        raise ReleasePackagingError("release root directory does not match manifest identity")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ReleasePackagingError("release manifest has no file inventory")
    expected = set(files) | {"manifest.json", "SHA256SUMS"}
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    if actual != expected:
        raise ReleasePackagingError("release file inventory mismatch")
    for relative, expected_digest in files.items():
        normalized = normalized_member_name(relative).as_posix()
        if normalized != relative or sha256_file(root / relative) != expected_digest:
            raise ReleasePackagingError(f"release payload digest mismatch: {relative}")
    checksums = parse_checksums(checksum_path.read_text(encoding="ascii"))
    checksum_expected = set(files) | {"manifest.json"}
    if set(checksums) != checksum_expected:
        raise ReleasePackagingError("SHA256SUMS inventory mismatch")
    for relative, expected_digest in checksums.items():
        if sha256_file(root / relative) != expected_digest:
            raise ReleasePackagingError(f"SHA256SUMS digest mismatch: {relative}")

    capability_relative = manifest.get("capability", {}).get("path")
    if capability_relative != "capability":
        raise ReleasePackagingError("release capability path must be exactly 'capability'")
    capability = root / capability_relative
    try:
        verify_bundle(capability)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ReleasePackagingError(f"nested capability verification failed: {exc}") from exc
    if (capability / "bundle-sha256.txt").read_text(encoding="ascii").strip() != manifest["capability"].get("bundle_sha256"):
        raise ReleasePackagingError("nested capability identity mismatch")
    profile = load((capability / "profile.json").read_bytes())
    capability_identity = manifest["capability"]
    if (profile.get("profile_id"), profile.get("profile_revision"), profile.get("domain"),
            profile.get("bindings", {}).get("abi_revision")) != (
            capability_identity.get("profile_id"), capability_identity.get("profile_revision"),
            capability_identity.get("domain"), capability_identity.get("abi_revision")):
        raise ReleasePackagingError("nested capability profile identity mismatch")
    if profile.get("bindings", {}).get("surface_contract_sha256") != capability_identity.get("surface_contract_sha256"):
        raise ReleasePackagingError("nested model-surface identity mismatch")
    surface = load((capability / "surface-contract.json").read_bytes())
    if surface.get("negotiation") != capability_identity.get("surface_negotiation"):
        raise ReleasePackagingError("nested model-surface negotiation mismatch")

    build_identity = manifest.get("build_inputs")
    if build_identity is not None:
        build_path = build_identity.get("path") if isinstance(build_identity, dict) else None
        if build_path != "build-inputs.json" or build_path not in files:
            raise ReleasePackagingError("release build-input identity path is invalid")
        build_bytes = (root / build_path).read_bytes()
        if sha256_file(root / build_path) != build_identity.get("sha256"):
            raise ReleasePackagingError("release build-input identity digest mismatch")
        try:
            build_document = load(build_bytes)
            if canonical(build_document) != build_bytes:
                raise ValueError("noncanonical build-input identity")
            validate_build_input_document(build_document)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise ReleasePackagingError(f"invalid embedded build-input identity: {exc}") from exc
        expected_build_capability = {
            "bundle_sha256": capability_identity.get("bundle_sha256"),
            "profile_id": capability_identity.get("profile_id"),
            "profile_revision": capability_identity.get("profile_revision"),
            "domain": capability_identity.get("domain"),
            "core_revision": profile.get("bindings", {}).get("core_revision"),
            "surface_contract_sha256": capability_identity.get("surface_contract_sha256"),
        }
        if build_document.get("capability") != expected_build_capability:
            raise ReleasePackagingError("embedded build-input capability identity mismatch")
        if build_document.get("release_profile") != manifest.get("profile") \
                or build_document.get("target") != manifest.get("target"):
            raise ReleasePackagingError("embedded build-input release profile/target mismatch")
        if build_document.get("source_identity_sha256") != build_identity.get("source_identity_sha256") \
                or profile.get("bindings", {}).get("core_revision") != "sha256:" + build_identity.get("source_identity_sha256", ""):
            raise ReleasePackagingError("embedded build-input source identity mismatch")

    runtime_path = manifest.get("runtime", {}).get("path")
    if not isinstance(runtime_path, str) or runtime_path not in files:
        raise ReleasePackagingError("release manifest runtime path is invalid")
    runtime = root / runtime_path
    if (manifest["runtime"].get("sha256") != sha256_file(runtime)
            or manifest["runtime"].get("size_bytes") != runtime.stat().st_size):
        raise ReleasePackagingError("release runtime measurement mismatch")
    if manifest.get("support") != "experimental" or manifest.get("qualification") != "unqualified":
        raise ReleasePackagingError("release-shaped bundles must remain experimental/unqualified")
    common_outer = {"LICENSE-MIT", "LICENSE-APACHE", "THIRD_PARTY_NOTICES.md", "manifest.json", "SHA256SUMS"}
    if build_identity is not None:
        common_outer.add("build-inputs.json")
    actual_outer = {relative for relative in actual if not relative.startswith("capability/")}
    if manifest.get("profile") == "native-static":
        if (capability / "runtime.wasm").exists() or profile.get("bindings", {}).get("artifact_sha256") is not None:
            raise ReleasePackagingError("native release contains a mismatched bound capability")
        runtime_name = PurePosixPath(runtime_path).name
        if runtime_name not in {"libexactscope_cabi.a", "exactscope_cabi.lib"} \
                or runtime_path != f"lib/{manifest['target']}/{runtime_name}":
            raise ReleasePackagingError("native release runtime path is not canonical")
        expected_outer = common_outer | {
            "include/exactscope.h",
            "include/exactscope_platform.h",
            "lib/cmake/ExactScope/ExactScopeConfig.cmake",
            runtime_path,
        }
        if actual_outer != expected_outer:
            raise ReleasePackagingError("native release contains unexpected outer payloads")
        if not runtime.read_bytes().startswith(AR_MAGIC):
            raise ReleasePackagingError("native release runtime is not a static archive")
    elif manifest.get("profile") == "no-import-wasm":
        expected_outer = common_outer | {"include/exactscope.h", "include/exactscope_wasm.h"}
        if actual_outer != expected_outer:
            raise ReleasePackagingError("Wasm release contains unexpected outer payloads")
        validate_wasm_input(capability)
        if runtime.resolve() != (capability / "runtime.wasm").resolve():
            raise ReleasePackagingError("Wasm release runtime must be the capability-bound runtime")
    else:
        raise ReleasePackagingError("unknown release profile")
    return manifest


def verify_archive(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ReleasePackagingError(f"release archive does not exist: {path}")
    with tempfile.TemporaryDirectory(prefix="exactscope-release-verify-") as temporary:
        destination = Path(temporary)
        with tarfile.open(path, mode="r:gz") as archive:
            members = archive.getmembers()
            if not members:
                raise ReleasePackagingError("release archive is empty")
            if len(members) > MAX_ARCHIVE_MEMBERS:
                raise ReleasePackagingError("release archive contains too many members")
            roots: set[str] = set()
            names: set[str] = set()
            total_size = 0
            for member in members:
                normalized = normalized_member_name(member.name.rstrip("/"))
                normalized_name = normalized.as_posix()
                if normalized_name in names:
                    raise ReleasePackagingError(f"duplicate archive member path: {member.name}")
                names.add(normalized_name)
                roots.add(normalized.parts[0])
                if not (member.isfile() or member.isdir()) or member.issym() or member.islnk():
                    raise ReleasePackagingError(f"forbidden archive member type: {member.name}")
                if member.isfile():
                    if member.size < 0 or member.size > MAX_ARCHIVE_MEMBER_BYTES:
                        raise ReleasePackagingError(f"release archive member exceeds size limit: {member.name}")
                    total_size += member.size
                    if total_size > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                        raise ReleasePackagingError("release archive exceeds uncompressed size limit")
            if len(roots) != 1:
                raise ReleasePackagingError("release archive must contain exactly one root directory")
            archive.extractall(destination, filter="data")
        root = destination / next(iter(roots))
        return verify_extracted(root)


def build_archive(
    *, kind: str, capability: Path, target: str, source_commit: str, toolchain: str,
    output_dir: Path, library: Path | None = None, build_inputs: Path | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="exactscope-release-stage-") as temporary:
        root, _ = stage_bundle(
            Path(temporary), kind=kind, capability=capability, target=target,
            source_commit=source_commit, toolchain=toolchain, library=library,
            build_inputs=build_inputs,
        )
        payload = deterministic_archive_bytes(root)
        output = output_dir / f"{root.name}.tar.gz"
        if output.exists() and output.read_bytes() != payload:
            raise ReleasePackagingError("immutable release archive already exists with different bytes")
        output.write_bytes(payload)
    verify_archive(output)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, kind in (("build-native", "native-static"), ("build-wasm", "no-import-wasm")):
        sub = subparsers.add_parser(command)
        sub.set_defaults(kind=kind)
        sub.add_argument("--capability", type=Path, required=True)
        sub.add_argument("--target", required=True)
        sub.add_argument("--source-commit", required=True)
        sub.add_argument("--toolchain", required=True)
        sub.add_argument("--output-dir", type=Path, required=True)
        sub.add_argument("--build-inputs", type=Path)
        if kind == "native-static":
            sub.add_argument("--library", type=Path, required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("archive", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "verify":
            manifest = verify_archive(args.archive)
            print(
                f"PASS release profile={manifest['profile']} target={manifest['target']} "
                f"runtime_bytes={manifest['runtime']['size_bytes']}"
            )
            return 0
        archive = build_archive(
            kind=args.kind,
            capability=args.capability,
            target=args.target,
            source_commit=args.source_commit,
            toolchain=args.toolchain,
            output_dir=args.output_dir,
            library=getattr(args, "library", None),
            build_inputs=getattr(args, "build_inputs", None),
        )
        print(f"PASS release archive={archive} sha256={sha256_file(archive)}")
        return 0
    except (OSError, ReleasePackagingError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL release: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
