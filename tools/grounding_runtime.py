#!/usr/bin/env python3
"""Provider-neutral ExactScope grounding reference runtime. No model inference."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any, Protocol

sys.dont_write_bytecode = True

from grounding_canonical import canonical_bytes, canonical_sha256, loads
from grounding_match import ascii_words, frozen_alias, matches as alias_matches


class GroundingError(RuntimeError):
    """Fail-closed grounding configuration or execution error."""


class RetrievalProvider(Protocol):
    """Provider-neutral retrieval boundary used by the host runtime."""

    provider_id: str

    def retrieve(
        self,
        envelope: dict[str, Any],
        target: dict[str, Any],
        binding: dict[str, Any],
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class GroundingBundle:
    root: Path
    profile: dict[str, Any]
    profile_sha256: str
    manifest: dict[str, Any]
    provider_identity: dict[str, Any]
    source_snapshots: dict[str, dict[str, Any]]
    source_items: dict[tuple[str, str, str], dict[str, Any]]
    index_entries: tuple[dict[str, Any], ...]
    router: dict[str, Any]
    merge: dict[str, Any]
    adapter_config: dict[str, Any]
    template: bytes
    policy: bytes
    renderer_path: Path


def _safe_asset(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise GroundingError(f"unsafe asset path: {relative}")
    path = root / rel
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise GroundingError(f"invalid asset path: {relative}")
    return path


def _asset_digest(root: Path, ref: dict[str, Any]) -> str:
    if set(ref) != {"path", "sha256", "encoding"}:
        raise GroundingError("invalid asset reference")
    path = _safe_asset(root, ref["path"])
    data = path.read_bytes()
    if ref["encoding"] == "grounding-cjson-v0.1":
        value = loads(data)
        canonical = canonical_bytes(value)
        if data != canonical:
            raise GroundingError(f"noncanonical JSON asset: {ref['path']}")
        data = canonical
    elif ref["encoding"] != "raw":
        raise GroundingError(f"unsupported asset encoding: {ref['encoding']}")
    actual = hashlib.sha256(data).hexdigest()
    if actual != ref["sha256"]:
        raise GroundingError(f"asset digest mismatch: {ref['path']}")
    return actual


def _walk_refs(root: Path, value: Any) -> None:
    if isinstance(value, dict):
        if set(value) == {"path", "sha256", "encoding"}:
            _asset_digest(root, value)
        for child in value.values():
            _walk_refs(root, child)
    elif isinstance(value, list):
        for child in value:
            _walk_refs(root, child)


def _read_cjson(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    value = loads(data)
    if not isinstance(value, dict) or data != canonical_bytes(value):
        raise GroundingError(f"expected canonical JSON object: {path.name}")
    return value


def load_bundle(profile_dir: Path) -> GroundingBundle:
    root = profile_dir.resolve()
    if not root.is_dir() or root.is_symlink():
        raise GroundingError("profile directory is not a normal directory")
    manifest = _read_cjson(root / "manifest.json")
    listed = [entry["path"] for entry in manifest.get("assets", [])]
    if len(listed) != len(set(listed)):
        raise GroundingError("duplicate manifest asset")
    actual = {path.name for path in root.iterdir() if path.is_file()} - {"manifest.json", "README.md"}
    if set(listed) != actual:
        raise GroundingError("profile asset inventory mismatch")
    _walk_refs(root, manifest)
    profile_ref = manifest.get("profile")
    if not isinstance(profile_ref, dict):
        raise GroundingError("manifest lacks profile reference")
    _asset_digest(root, profile_ref)
    profile = _read_cjson(_safe_asset(root, profile_ref["path"]))
    profile_sha256 = canonical_sha256(profile)
    if profile_sha256 != profile_ref["sha256"]:
        raise GroundingError("profile digest mismatch")
    _walk_refs(root, profile)

    if profile.get("v") != 1 or profile.get("canonical_encoding") != "grounding-cjson-v0.1":
        raise GroundingError("unsupported grounding profile")
    if profile.get("rewrite", {}).get("enabled") is not False:
        raise GroundingError("reference runtime supports frozen no-rewrite profile only")
    if profile.get("privacy", {}).get("network") != "denied":
        raise GroundingError("reference runtime requires network-denied profile")
    if profile.get("limits", {}).get("answer_calls") != 1 or profile.get("limits", {}).get("rewrite_calls") != 0:
        raise GroundingError("reference A/G call-count contract mismatch")

    provider_ref = profile["providers"][0]["identity"]
    provider_identity = _read_cjson(_safe_asset(root, provider_ref["path"]))
    if canonical_sha256(provider_identity) != provider_ref["sha256"]:
        raise GroundingError("provider identity digest mismatch")
    _walk_refs(root, provider_identity)

    source_snapshots: dict[str, dict[str, Any]] = {}
    for ref in profile["source_snapshots"]:
        snapshot = _read_cjson(_safe_asset(root, ref["path"]))
        if canonical_sha256(snapshot) != ref["sha256"]:
            raise GroundingError("source snapshot digest mismatch")
        source_id = snapshot.get("source_id")
        if not isinstance(source_id, str) or source_id in source_snapshots:
            raise GroundingError("duplicate/invalid source snapshot")
        source_snapshots[source_id] = snapshot

    expected_snapshot_sha256 = [ref["sha256"] for ref in profile["source_snapshots"]]
    if provider_identity.get("source_snapshot_sha256") != expected_snapshot_sha256:
        raise GroundingError("provider/source snapshot identity mismatch")

    source_file_owners: dict[str, set[str]] = {}
    for source_id, snapshot in source_snapshots.items():
        files = snapshot.get("files")
        if not isinstance(files, list) or not files:
            raise GroundingError("source snapshot files are missing")
        for file_ref in files:
            if not isinstance(file_ref, dict):
                raise GroundingError("malformed source snapshot file reference")
            _asset_digest(root, file_ref)
            if file_ref.get("path") == "adapter-config.json":
                continue
            source_file_owners.setdefault(file_ref["path"], set()).add(source_id)
    if not source_file_owners:
        raise GroundingError("no source data files are bound")

    source_items: dict[tuple[str, str, str], dict[str, Any]] = {}
    for source_path, owners in sorted(source_file_owners.items()):
        source = _read_cjson(_safe_asset(root, source_path))
        items = source.get("items")
        if not isinstance(items, list):
            raise GroundingError(f"source items are missing: {source_path}")
        for item in items:
            if not isinstance(item, dict):
                raise GroundingError("malformed source item")
            identity = (item.get("source_id"), item.get("item_id"), item.get("source_revision"))
            if not all(isinstance(value, str) and value for value in identity):
                raise GroundingError("invalid evidence identity")
            if item["source_id"] not in owners:
                continue
            if item.get("content_sha256") != canonical_sha256(item.get("content")):
                raise GroundingError("evidence content digest mismatch")
            if any(field in item for field in ("observed_at", "valid_from", "valid_until")):
                raise GroundingError("reference static profile rejects timestamp-bearing evidence")
            snapshot = source_snapshots.get(item["source_id"])
            if snapshot is None or snapshot.get("source_revision") != item["source_revision"]:
                raise GroundingError("evidence source revision is not bound")
            existing = source_items.get(identity)
            if existing is not None and existing != item:
                raise GroundingError("evidence identity collision across source files")
            source_items[identity] = item
    if not source_items:
        raise GroundingError("no source items are bound")

    index = _read_cjson(root / "index.json")
    entries = index.get("entries")
    if not isinstance(entries, list):
        raise GroundingError("index entries are missing")
    seen_index: set[tuple[str, str, str, str]] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise GroundingError("malformed index entry")
        identity = (entry.get("source_id"), entry.get("item_id"), entry.get("source_revision"))
        target_key = entry.get("target_key")
        source_item = source_items.get(identity)
        if source_item is None or source_item.get("target_key") != target_key:
            raise GroundingError("index entry is not bound to one source item")
        for key in ("content", "content_sha256"):
            if entry.get(key) != source_item.get(key):
                raise GroundingError("index/source content mismatch")
        key = (entry["source_id"], entry["source_revision"], entry["item_id"], entry["target_key"])
        if key in seen_index:
            raise GroundingError("duplicate index identity")
        seen_index.add(key)
        aliases = entry.get("aliases")
        if not isinstance(aliases, list) or any(not isinstance(alias, str) for alias in aliases):
            raise GroundingError("invalid index aliases")
        normalized_aliases = sorted({frozen_alias(alias) for alias in aliases}, key=lambda value: value.encode("utf-8"))
        if aliases != normalized_aliases:
            raise GroundingError("index aliases are not frozen normalized/sorted unique values")
    entry_order = [
        tuple(entry[key].encode("utf-8") for key in ("source_id", "source_revision", "item_id", "target_key"))
        for entry in entries
    ]
    if entry_order != sorted(entry_order):
        raise GroundingError("index entries are not in frozen tuple order")

    router = _read_cjson(root / profile["router"]["path"])
    merge = _read_cjson(root / profile["merge_policy"]["path"])
    adapter_config = _read_cjson(root / "adapter-config.json")
    for snapshot in source_snapshots.values():
        if snapshot.get("adapter_config_sha256") != canonical_sha256(adapter_config):
            raise GroundingError("source adapter config mismatch")

    targets = {target["target_key"]: target for target in profile.get("targets", [])}
    if len(targets) != len(profile.get("targets", [])):
        raise GroundingError("duplicate target key")
    allowed_namespaces = set(profile.get("allowed_namespaces", []))
    provider_id = provider_identity.get("provider_id")
    for target in targets.values():
        if target.get("namespace") not in allowed_namespaces:
            raise GroundingError("target namespace is not allowed")
        if target.get("sufficiency_rule_id") != merge.get("id"):
            raise GroundingError("unknown sufficiency rule")
        for binding in target.get("bindings", []):
            if binding.get("provider_id") != provider_id:
                raise GroundingError("target/provider binding mismatch")
            if not set(binding.get("source_ids", [])) <= source_snapshots.keys():
                raise GroundingError("target/source binding mismatch")

    route_map: dict[str, tuple[str, ...]] = {}
    for route in router.get("routes", []):
        target_keys = tuple(sorted(route.get("target_keys", []), key=lambda value: value.encode("utf-8")))
        if any(target_key not in targets for target_key in target_keys):
            raise GroundingError("router references unknown target")
        for alias in route.get("aliases", []):
            normalized = frozen_alias(alias)
            existing = route_map.get(normalized)
            if existing is not None and existing != target_keys:
                raise GroundingError("ambiguous router alias")
            route_map[normalized] = target_keys

    template = _safe_asset(root, profile["projection"]["template"]["path"]).read_bytes()
    policy = _safe_asset(root, profile["projection"]["policy"]["path"]).read_bytes()
    renderer_path = _safe_asset(root, profile["projection"]["renderer"]["path"])
    return GroundingBundle(
        root=root,
        profile=profile,
        profile_sha256=profile_sha256,
        manifest=manifest,
        provider_identity=provider_identity,
        source_snapshots=source_snapshots,
        source_items=source_items,
        index_entries=tuple(entries),
        router=router,
        merge=merge,
        adapter_config=adapter_config,
        template=template,
        policy=policy,
        renderer_path=renderer_path,
    )


_TOKEN_RE = re.compile(r"[a-z0-9]+", re.ASCII)
_ASCII_LOWER = str.maketrans({chr(code): chr(code + 32) for code in range(ord("A"), ord("Z") + 1)})


def normalize_query(value: str) -> str:
    if not isinstance(value, str):
        raise GroundingError("query must be text")
    return " ".join(_TOKEN_RE.findall(value.translate(_ASCII_LOWER)))


def validate_query(bundle: GroundingBundle, envelope: dict[str, Any]) -> None:
    if set(envelope) - {"v", "qid", "profile_sha256", "q", "security_scope_id", "as_of"}:
        raise GroundingError("unexpected QueryEnvelope field")
    if envelope.get("v") != 1:
        raise GroundingError("unsupported QueryEnvelope version")
    if envelope.get("profile_sha256") != bundle.profile_sha256:
        raise GroundingError("QueryEnvelope profile mismatch")
    if not isinstance(envelope.get("qid"), str) or not envelope["qid"]:
        raise GroundingError("invalid qid")
    query = envelope.get("q")
    if not isinstance(query, str) or not query or len(query.encode("utf-8")) > bundle.profile["limits"]["query_bytes"]:
        raise GroundingError("query exceeds frozen bounds")
    expected_scope = bundle.adapter_config.get("scope")
    if envelope.get("security_scope_id") != expected_scope:
        raise GroundingError("security scope mismatch")
    if "as_of" in envelope:
        raise GroundingError("reference profile is static and rejects as_of")


def route_query(bundle: GroundingBundle, envelope: dict[str, Any]) -> dict[str, Any]:
    validate_query(bundle, envelope)
    targets_by_key = {target["target_key"]: target for target in bundle.profile["targets"]}
    router_id = bundle.router.get("id")
    if router_id == "exact-alias-router-v1":
        exact_ascii = True
    elif router_id == "token-subset-router-v1":
        exact_ascii = False
    else:
        raise GroundingError("unsupported router implementation")
    matched: set[str] = set()
    for route in bundle.router.get("routes", []):
        if any(alias_matches(envelope["q"], alias, exact_ascii=exact_ascii) for alias in route.get("aliases", [])):
            matched.update(route.get("target_keys", []))
    target_keys = tuple(sorted(matched, key=lambda value: value.encode("utf-8")))
    if len(target_keys) > bundle.profile["limits"]["target_groups"]:
        raise GroundingError("router target-group budget exceeded")
    targets = [targets_by_key[target_key] for target_key in target_keys]
    return {
        "v": 1,
        "qid": envelope["qid"],
        "profile_sha256": bundle.profile_sha256,
        "security_scope_id": envelope["security_scope_id"],
        "router_id": bundle.router["id"],
        "router_config_sha256": canonical_sha256(bundle.router),
        "targets": targets,
    }


class LocalExactLexicalProvider:
    provider_id = "local-exact-lexical"

    def __init__(self, bundle: GroundingBundle) -> None:
        self.bundle = bundle
        if bundle.provider_identity.get("provider_id") != self.provider_id:
            raise GroundingError("provider identity mismatch")

    def _failure(
        self,
        envelope: dict[str, Any],
        target: dict[str, Any],
        binding: dict[str, Any],
        status: str,
        reason: str,
    ) -> dict[str, Any]:
        return {
            "v": 1,
            "qid": envelope["qid"],
            "profile_sha256": self.bundle.profile_sha256,
            "security_scope_id": envelope["security_scope_id"],
            "target_key": target["target_key"],
            "provider_id": self.provider_id,
            "attempt": 1,
            "source_snapshot_refs": self._snapshot_refs(binding),
            "status": status,
            "complete": False,
            "candidates": [],
            "reason": reason,
        }

    def _snapshot_refs(self, binding: dict[str, Any]) -> list[str]:
        return [canonical_sha256(self.bundle.source_snapshots[source_id]) for source_id in binding["source_ids"]]

    def retrieve(
        self,
        envelope: dict[str, Any],
        target: dict[str, Any],
        binding: dict[str, Any],
    ) -> dict[str, Any]:
        if envelope.get("security_scope_id") != self.bundle.adapter_config.get("scope"):
            return self._failure(envelope, target, binding, "denied", "scope-mismatch")
        if binding.get("provider_id") != self.provider_id:
            return self._failure(envelope, target, binding, "error", "provider-binding-mismatch")
        source_ids = set(binding.get("source_ids", []))
        if not source_ids or not source_ids <= self.bundle.source_snapshots.keys():
            return self._failure(envelope, target, binding, "error", "source-binding-mismatch")

        query = normalize_query(envelope["q"])
        query_tokens = set(query.split()) if query else set()
        ranked: list[tuple[int, int, tuple[bytes, bytes, bytes, bytes], dict[str, Any]]] = []
        for entry in self.bundle.index_entries:
            if entry["source_id"] not in source_ids or entry["target_key"] != target["target_key"]:
                continue
            exact = 0
            overlap = 0
            for alias in entry["aliases"]:
                normalized_alias = frozen_alias(alias)
                if any(not char.isascii() for char in normalized_alias):
                    if normalized_alias in envelope["q"]:
                        exact = 1
                        overlap = max(overlap, 2)
                    continue
                exact = max(exact, int(bool(query) and query == normalized_alias))
                overlap = max(overlap, len(query_tokens & set(normalized_alias.split())))
            if exact == 0 and overlap < 2:
                continue
            identity = (entry["source_id"], entry["item_id"], entry["source_revision"])
            source_item = self.bundle.source_items.get(identity)
            if source_item is None or source_item["target_key"] != target["target_key"]:
                return self._failure(envelope, target, binding, "error", "index-source-mismatch")
            tie = tuple(
                entry[key].encode("utf-8")
                for key in ("source_id", "source_revision", "item_id", "target_key")
            )
            ranked.append((-exact, -overlap, tie, source_item))

        ranked.sort(key=lambda row: (row[0], row[1], row[2]))
        limit = self.bundle.profile["limits"]["candidates_per_invocation"]
        if len(ranked) > limit:
            return self._failure(envelope, target, binding, "budget_exceeded", "candidate-limit")
        candidates = [row[3] for row in ranked]
        return {
            "v": 1,
            "qid": envelope["qid"],
            "profile_sha256": self.bundle.profile_sha256,
            "security_scope_id": envelope["security_scope_id"],
            "target_key": target["target_key"],
            "provider_id": self.provider_id,
            "attempt": 1,
            "source_snapshot_refs": self._snapshot_refs(binding),
            "status": "ok" if candidates else "none",
            "complete": True,
            "candidates": candidates,
            "reason": None,
        }


def _validate_outcome(
    bundle: GroundingBundle,
    envelope: dict[str, Any],
    target: dict[str, Any],
    binding: dict[str, Any],
    outcome: dict[str, Any],
) -> None:
    if outcome.get("qid") != envelope["qid"] or outcome.get("profile_sha256") != bundle.profile_sha256:
        raise GroundingError("provider outcome identity mismatch")
    if outcome.get("security_scope_id") != envelope["security_scope_id"]:
        raise GroundingError("provider outcome scope mismatch")
    if outcome.get("target_key") != target["target_key"] or outcome.get("provider_id") != binding["provider_id"]:
        raise GroundingError("provider outcome binding mismatch")
    if outcome.get("attempt") != 1:
        raise GroundingError("unexpected provider attempt")
    expected_refs = [canonical_sha256(bundle.source_snapshots[source_id]) for source_id in binding["source_ids"]]
    if outcome.get("source_snapshot_refs") != expected_refs:
        raise GroundingError("provider outcome snapshot mismatch")
    status = outcome.get("status")
    complete = outcome.get("complete")
    candidates = outcome.get("candidates")
    reason = outcome.get("reason")
    if status not in {"ok", "none", "timeout", "error", "denied", "budget_exceeded"} or not isinstance(candidates, list):
        raise GroundingError("invalid provider outcome")
    if status == "ok" and (complete is not True or not candidates or reason is not None):
        raise GroundingError("invalid ok outcome")
    if status == "none" and (complete is not True or candidates or reason is not None):
        raise GroundingError("invalid none outcome")
    if status in {"timeout", "error", "denied", "budget_exceeded"} and (
        complete is not False or candidates or not isinstance(reason, str) or not reason
    ):
        raise GroundingError("invalid failure outcome")
    allowed_sources = set(binding["source_ids"])
    for item in candidates:
        identity = (item.get("source_id"), item.get("item_id"), item.get("source_revision"))
        if item.get("target_key") != target["target_key"] or item.get("source_id") not in allowed_sources:
            raise GroundingError("provider candidate escaped binding")
        if bundle.source_items.get(identity) != item:
            raise GroundingError("provider candidate is not source-bound")
        if item.get("content_sha256") != canonical_sha256(item.get("content")):
            raise GroundingError("provider candidate content digest mismatch")


def build_frame(
    bundle: GroundingBundle,
    envelope: dict[str, Any],
    routing_plan: dict[str, Any],
    outcomes: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    by_key: dict[tuple[str, str, tuple[str, ...]], list[dict[str, Any]]] = {}
    for outcome in outcomes:
        refs = outcome.get("source_snapshot_refs")
        ref_key = tuple(refs) if isinstance(refs, list) and all(isinstance(ref, str) for ref in refs) else ()
        key = (outcome.get("target_key"), outcome.get("provider_id"), ref_key)
        by_key.setdefault(key, []).append(outcome)

    groups: list[dict[str, Any]] = []
    reasons: list[dict[str, Any]] = []
    for target in routing_plan["targets"]:
        approved: list[dict[str, Any]] = []
        unavailable = False
        for binding in target["bindings"]:
            expected_refs = tuple(
                canonical_sha256(bundle.source_snapshots[source_id])
                for source_id in binding["source_ids"]
            )
            matches = by_key.get((target["target_key"], binding["provider_id"], expected_refs), [])
            if len(matches) != 1:
                if binding["required"]:
                    unavailable = True
                continue
            outcome = matches[0]
            _validate_outcome(bundle, envelope, target, binding, outcome)
            if outcome["status"] not in {"ok", "none"} or not outcome["complete"]:
                if binding["required"]:
                    unavailable = True
                continue
            approved.extend(outcome["candidates"])

        state_reason = ""
        items: list[dict[str, Any]] = []
        if unavailable:
            state = "unavailable"
            state_reason = "required-coverage-incomplete"
        else:
            dedup: dict[tuple[str, str, str], dict[str, Any]] = {}
            for item in approved:
                identity = (item["source_id"], item["item_id"], item["source_revision"])
                existing = dedup.get(identity)
                if existing is not None and existing != item:
                    raise GroundingError("evidence identity collision")
                dedup[identity] = item
            ordered = sorted(
                dedup.values(),
                key=lambda item: tuple(
                    item[key].encode("utf-8")
                    for key in ("source_id", "source_revision", "item_id", "target_key")
                ),
            )
            content_identities = {canonical_sha256(item["content"]) for item in ordered}
            source_identities = {item["source_id"] for item in ordered}
            if len(content_identities) > 1:
                if bundle.merge.get("ambiguity_rule") == "single-source-multiple-content-v1" and len(source_identities) == 1:
                    state = "ambiguous"
                    state_reason = "multiple-plausible-items-one-source"
                else:
                    state = "conflict"
                    state_reason = "conflicting-canonical-content"
            elif not ordered:
                state = "none"
                state_reason = "complete-required-coverage-no-evidence"
            else:
                item_limit = bundle.profile["limits"]["items_per_target"]
                content_limit = bundle.profile["limits"]["content_bytes"]
                if len(ordered) > item_limit or any(len(canonical_bytes(item["content"])) > content_limit for item in ordered):
                    state = "unavailable"
                    state_reason = "evidence-budget-exceeded"
                else:
                    state = "grounded"
                    state_reason = "policy-approved-evidence"
                    items = ordered
        groups.append(
            {
                "target_key": target["target_key"],
                "target_label": target["target_label"],
                "authority": target["authority"],
                "state": state,
                "items": items,
            }
        )
        reasons.append({"target_key": target["target_key"], "state": state, "reason": state_reason})

    groups.sort(key=lambda group: group["target_key"].encode("utf-8"))
    frame = {"v": 1, "qid": envelope["qid"], "profile_sha256": bundle.profile_sha256, "groups": groups}
    if len(canonical_bytes(frame)) > bundle.profile["limits"]["frame_bytes"]:
        raise GroundingError("frame budget exceeded")
    audit = {
        "v": 1,
        "qid": envelope["qid"],
        "profile_sha256": bundle.profile_sha256,
        "routing_plan": routing_plan,
        "provider_outcomes": outcomes,
        "group_reasons": reasons,
    }
    return frame, audit


def render_projection(bundle: GroundingBundle, frame: dict[str, Any]) -> dict[str, bytes]:
    # Execute verified renderer bytes directly so a read-only/frozen candidate is
    # never mutated by Python bytecode cache creation.
    namespace: dict[str, Any] = {"__name__": "exactscope_grounding_projection"}
    renderer_bytes = bundle.renderer_path.read_bytes()
    code = compile(renderer_bytes, str(bundle.renderer_path), "exec")
    exec(code, namespace)
    renderer = namespace.get("render")
    if not callable(renderer):
        raise GroundingError("projection renderer lacks render()")
    rendered = renderer(frame, bundle.profile, bundle.template, bundle.policy)
    if not isinstance(rendered, dict) or set(rendered) != {"policy", "evidence"}:
        raise GroundingError("projection renderer returned invalid result")
    if not all(isinstance(rendered[key], bytes) for key in rendered):
        raise GroundingError("projection renderer must return bytes")
    return rendered


def run_grounding(
    bundle: GroundingBundle,
    envelope: dict[str, Any],
    provider: RetrievalProvider | None = None,
) -> dict[str, Any]:
    routing_plan = route_query(bundle, envelope)
    active_provider: RetrievalProvider = provider or LocalExactLexicalProvider(bundle)
    outcomes: list[dict[str, Any]] = []
    for target in routing_plan["targets"]:
        for binding in target["bindings"]:
            if binding["provider_id"] != active_provider.provider_id:
                raise GroundingError("no provider for target binding")
            outcomes.append(active_provider.retrieve(envelope, target, binding))
    frame, audit = build_frame(bundle, envelope, routing_plan, outcomes)
    projection = render_projection(bundle, frame)
    return {"frame": frame, "audit": audit, "projection": projection}


def _jsonable(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "frame": result["frame"],
        "audit": result["audit"],
        "projection": {
            "policy": result["projection"]["policy"].decode("utf-8"),
            "evidence": result["projection"]["evidence"].decode("utf-8"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    verify = sub.add_parser("verify", help="verify the frozen grounding profile bundle only")
    verify.add_argument("--profile-dir", type=Path, required=True)
    run = sub.add_parser("run", help="run retrieval/policy/projection only; never invokes a model")
    run.add_argument("--profile-dir", type=Path, required=True)
    run.add_argument("--query", required=True)
    run.add_argument("--qid", default="grounding-cli-1")
    run.add_argument("--security-scope", default="reference-public")
    args = parser.parse_args()

    bundle = load_bundle(args.profile_dir)
    if args.command == "verify":
        print(
            json.dumps(
                {
                    "status": "ok",
                    "profile_id": bundle.profile["profile_id"],
                    "profile_sha256": bundle.profile_sha256,
                    "provider_id": bundle.provider_identity["provider_id"],
                    "source_count": len(bundle.source_snapshots),
                    "no_model_inference": True,
                },
                sort_keys=True,
            )
        )
        return 0

    envelope = {
        "v": 1,
        "qid": args.qid,
        "profile_sha256": bundle.profile_sha256,
        "q": args.query,
        "security_scope_id": args.security_scope,
    }
    print(json.dumps(_jsonable(run_grounding(bundle, envelope)), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GroundingError, OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        print(f"ExactScope grounding: FAIL: {exc}")
        raise SystemExit(1) from exc
