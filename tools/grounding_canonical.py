"""Grounding canonical JSON v0.1: stdlib-only, strict JCS-compatible subset."""
import hashlib
import json

MAX_INTEGER = 9007199254740991

def canonical_bytes(value):
    """Encode without normalization, BOM, whitespace or trailing newline.

    Only null/bool/safe integers/Unicode scalar strings/lists/string-key dicts.
    Keys sort by UTF-16 code units, as in JCS. Floats are never accepted.
    """
    def encode(v):
        if v is None:
            return "null"
        if type(v) is bool:
            return "true" if v else "false"
        if type(v) is int:
            if abs(v) > MAX_INTEGER:
                raise ValueError("integer outside safe range")
            return str(v)
        if type(v) is str:
            if any(0xD800 <= ord(c) <= 0xDFFF for c in v):
                raise ValueError("unpaired surrogate")
            return json.dumps(v, ensure_ascii=False)
        if type(v) is list:
            return "[" + ",".join(encode(x) for x in v) + "]"
        if type(v) is dict:
            if any(type(k) is not str for k in v):
                raise ValueError("object keys must be strings")
            for k in v:
                encode(k)
            keys = sorted(v, key=lambda k: k.encode("utf-16-be"))
            return "{" + ",".join(encode(k) + ":" + encode(v[k]) for k in keys) + "}"
        raise ValueError("unsupported canonical JSON value")
    return encode(value).encode("utf-8")

def canonical_sha256(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()

def loads(data):
    """Parse strict UTF-8 JSON; reject duplicate keys and non-subset numbers."""
    if isinstance(data, bytes):
        data = data.decode("utf-8", errors="strict")
    def pairs(entries):
        result = {}
        for key, value in entries:
            if key in result:
                raise ValueError("duplicate object key")
            result[key] = value
        return result
    def reject(value):
        raise ValueError("non-integer number: " + value)
    value = json.loads(data, object_pairs_hook=pairs, parse_float=reject,
                       parse_constant=reject)
    canonical_bytes(value)
    return value
