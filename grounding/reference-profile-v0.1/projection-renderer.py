"""P1 byte-exact projection reference; no inference or retrieval."""
from grounding_canonical import canonical_bytes


def _visible_item(item):
    return {
        "source_id": item["source_id"],
        "item_id": item["item_id"],
        "source_revision": item["source_revision"],
        "target_key": item["target_key"],
        "content": item["content"],
    }


def render(frame, profile, template, policy):
    limits = profile["limits"]
    if len(canonical_bytes(frame)) > limits["frame_bytes"]:
        raise ValueError("frame budget exceeded")
    groups = sorted(frame["groups"], key=lambda g: g["target_key"].encode("utf-8"))
    if len({g["target_key"] for g in groups}) != len(groups):
        raise ValueError("duplicate target")
    output = []
    item_count = 0
    for group in groups:
        if group["state"] not in ("grounded", "none", "ambiguous", "conflict", "unavailable"):
            raise ValueError("invalid state")
        if group["authority"] not in ("authoritative", "supplemental"):
            raise ValueError("invalid authority")
        if bool(group["items"]) != (group["state"] == "grounded"):
            raise ValueError("invalid state/items")
        items = sorted(
            group["items"],
            key=lambda item: tuple(
                item[key].encode("utf-8")
                for key in ("source_id", "source_revision", "item_id", "target_key")
            ),
        )
        item_count += len(items)
        output.append(
            {
                "target_key": group["target_key"],
                "target_label": group["target_label"],
                "authority": group["authority"],
                "state": group["state"],
                "items": [_visible_item(item) for item in items],
            }
        )
    data = canonical_bytes(output)
    for old, new in (
        (b"<", b"\\u003c"),
        (b">", b"\\u003e"),
        (b"&", b"\\u0026"),
        (b"\xe2\x80\xa8", b"\\u2028"),
        (b"\xe2\x80\xa9", b"\\u2029"),
    ):
        data = data.replace(old, new)
    if template.count(b"{{groups_json}}") != 1:
        raise ValueError("invalid template")
    evidence = template.replace(b"{{groups_json}}", data)
    if item_count > limits["model_items"]:
        raise ValueError("model item budget exceeded")
    if len(evidence) > limits["model_evidence_bytes"]:
        raise ValueError("model evidence budget exceeded")
    if len(policy) + len(evidence) > limits["model_context_bytes"]:
        raise ValueError("model context budget exceeded")
    return {"policy": policy, "evidence": evidence}
