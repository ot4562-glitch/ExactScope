# Canonical ID registries

These JSON files are the machine-readable source of truth for stable ExactScope IDs and keys. Future Rust constants, C headers, pack compiler tables, TinyWire mappings, and documentation must be generated from or checked against these registries.

Rules:

- existing IDs and keys are immutable within ABI/format major 1;
- entries may be appended only when the corresponding specification permits it;
- `c_name` identifies a required public-header constant;
- registries with `unique_ids: true` reject duplicate numeric IDs;
- every registry rejects duplicate keys and duplicate `c_name` values;
- prose tables are explanatory copies and cannot override these files.

`tools/validate_design.py` checks registry uniqueness, schema enums, VM instruction names, and public C-header constants on every pull request.
