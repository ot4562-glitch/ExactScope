# Canonical registries

These JSON files are the machine-readable source of truth for stable ExactScope IDs, keys, and public export allowlists. Rust constants, C headers, pack compiler tables, TinyWire mappings, artifact inspectors, and documentation must be generated from or checked against these registries.

Rules:

- existing IDs and keys are immutable within ABI/format major 1;
- entries may be appended only when the corresponding specification permits it;
- `c_name` identifies a required public-header constant;
- registries with `unique_ids: true` reject duplicate numeric IDs;
- every registry rejects duplicate keys and duplicate `c_name` values;
- prose tables are explanatory copies and cannot override these files.

`tools/validate_design.py` checks ID-registry uniqueness, schema enums, VM instruction names, and public C-header constants. `tools/audit_security_surface.py` separately checks the public native/Wasm export registry against the C header, Rust `no_mangle` entry points, and the Wasm inspector allowlist.
