# Scope-pack format v0.1

A scope pack is a data-only bundle of deterministic operations. Source packs use JSON for review and compilation. Runtime packs use the compact `.xsp` binary format.

## 1. Security and execution model

A pack MUST NOT contain:

- native code;
- WebAssembly code;
- scripts;
- arbitrary expressions evaluated by a host language;
- network locations that are fetched automatically;
- unbounded loops, recursion, or dynamic calls.

A pack MAY contain:

- metadata and provenance;
- canonical operation identities;
- typed input/output declarations;
- constraints;
- constants;
- bounded scalar VM instructions;
- built-in kernel identifiers;
- classification programs;
- aliases and prebuilt indexes;
- build-time golden vectors.

The runtime treats all pack bytes as untrusted until structural and semantic validation succeeds.

## 2. Source file naming

Recommended source extension:

```text
<pack-id>.xsp.json
```

Compiled extension:

```text
<pack-id>-<version>.xsp
```

Example:

```text
econ-undergrad.xsp.json
econ-undergrad-0.1.0.xsp
```

## 3. Source root

A source document contains:

```json
{
  "$schema": "../../spec/schemas/scopepack-source.schema.json",
  "format": "exactscope.scopepack.source",
  "format_version": "0.1",
  "pack": {},
  "limits": {},
  "sources": [],
  "operations": []
}
```

The machine-readable schema is normative for shape. This specification is normative for semantics not expressible in JSON Schema.

## 4. Pack metadata

Required fields:

| Field | Rule |
|---|---|
| `id` | reverse-DNS ASCII identifier, lowercase; example `org.exactscope.econ-undergrad` |
| `name` | short display/developer name |
| `version` | SemVer without build metadata in v0.1 |
| `license` | SPDX expression |
| `description` | developer-facing summary; omitted from minimum fused runtime when desired |
| `numeric_profile` | `decimal64-v1` for official v0.1 packs |
| `abi_min` | minimum encoded ABI major/minor |
| `abi_max` | maximum tested compatible ABI major/minor |
| `default_locale` | BCP 47-style source locale; initially `en` |

Pack IDs are globally meaningful. Numeric operation IDs are meaningful only inside a pack identity and operation revision.

## 5. Limits

Source packs declare limits no greater than runtime global caps:

```json
{
  "max_scalar_args": 12,
  "max_vector_args": 4,
  "max_vector_len": 256,
  "max_vm_steps": 64,
  "max_stack": 16,
  "max_outputs": 4
}
```

The compiler rejects packs that exceed either source-declared or compiler target-profile limits. The runtime independently enforces its own limits.

## 6. Source registry

Every formula-driven official operation references one or more pack-level sources.

```json
{
  "id": "openstax.micro.ped",
  "title": "Principles of Economics — Elasticity",
  "url": "https://openstax.org/",
  "license": "CC-BY-4.0",
  "note": "Definition reference; ExactScope expression and tests are independently authored."
}
```

Source metadata supports auditability. It does not authorize automatic network access.

## 7. Operation identity

Required operation fields:

| Field | Rule |
|---|---|
| `id` | nonzero unsigned 32-bit integer unique inside the pack |
| `key` | canonical lowercase ASCII key, globally readable; example `econ.ped.mid` |
| `revision` | nonzero unsigned 16-bit semantic revision |
| `name` | developer-facing name |
| `method` | compact method key; empty only when no alternate method exists |
| `aliases` | pre-normalized discovery aliases |
| `kind` | `formula` or `kernel` |
| `inputs` | ordered typed input declarations |
| `relations` | ordered cross-input constraints; empty when none |
| `outputs` | one to four ordered output declarations |
| `output_policy` | scale, rounding, and caller-override policy |
| `classifications` | optional deterministic class table |
| `sources` | source IDs |
| `tests` | build-time golden vectors |

Canonical key grammar:

```text
segment = lowercase letter *(lowercase letter | digit | "_")
key     = segment 1*("." segment)
```

Official prefixes `math.*`, `stats.*`, `econ.*`, and `finance.*` are reserved for ExactScope-reviewed packs. Third-party operations use `x.<vendor_id>.*`, with the globally meaningful reverse-DNS pack ID carrying ownership metadata. A mounted registry may contain each canonical operation key exactly once. Mounting a pack that collides with any existing key returns `PACK_INVALID` and leaves the registry unchanged; v0.1 does not silently shadow, merge, or replace operations. Mounting the same pack twice is also rejected rather than assigned a second slot.

An existing `(pack id, operation id, revision)` and `(canonical key, revision)` pair is immutable. Formula, input order, semantic kinds, units, constraints, output policy, classification, and method cannot change. A semantic change creates a new revision; a method change should normally create a new key.

## 8. Inputs

Example:

```json
{
  "name": "p1",
  "shape": "scalar",
  "semantic": "price",
  "same_unit_group": "price",
  "constraints": [
    {"kind": "gt", "value": "0"}
  ]
}
```

Fields:

- `name`: short ASCII argument name shown in the compact signature;
- `shape`: `scalar` or `vector`;
- `semantic`: a stable numeric semantic key from the numeric specification;
- `unit_namespace`: optional developer metadata such as `currency` or `period`;
- `same_unit_group`: optional operation-local group key;
- `unit_required`: whether unit ID zero is rejected;
- `max_len`: required for vectors and no larger than pack limit;
- `constraints`: ordered list.

Input names are part of the operation revision and cannot be reordered or renamed compatibly because tiny models use the signature to supply positional arguments.

### 8.1 Cross-input relations

Operation-level `relations` validate facts that cannot be expressed against a constant alone.

```json
{
  "kind": "arg_gt",
  "left": "price",
  "right": "variable_cost_unit",
  "detail_id": 21
}
```

Supported v0.1 relation kinds are `arg_gt`, `arg_ge`, `arg_lt`, `arg_le`, `arg_eq`, `arg_ne`, and `same_length`. `left` and `right` reference declared input names. Relations are checked after per-input constraints and before unit checks/program execution, in declaration order. The compiler resolves names to indices; binary constraint records encode the two indices and detail ID. A failed relation returns `CONSTRAINT_VIOLATION`, except `same_length`, which returns `ARGUMENT_TYPE`.

## 9. Outputs

Example:

```json
{
  "name": "elasticity",
  "semantic": "elasticity",
  "unit_rule": "dimensionless"
}
```

Output unit rules:

- `dimensionless`;
- `copy:<input-name>`;
- `derived:<declared-dimension-key>`;
- `unspecified` only for operations where a unit cannot be preserved.

Official packs should preserve compatible input unit identity whenever mathematically valid.

## 10. Output policy

```json
{
  "scale": 6,
  "rounding": "half_even",
  "allow_scale_override": false,
  "allow_rounding_override": false,
  "classification_required": true
}
```

Defaults are explicit. No pack may rely on host locale or unspecified rounding.

## 11. Formula programs

Source programs use typed reverse-Polish instructions. This avoids a runtime expression parser and makes stack/resource analysis deterministic.

Example instruction list:

```json
[
  ["arg", 3],
  ["arg", 2],
  ["sub"],
  ["arg", 2],
  ["arg", 3],
  ["add"],
  ["const", 0],
  ["div"],
  ["div"],
  ["arg", 1],
  ["arg", 0],
  ["sub"],
  ["arg", 0],
  ["arg", 1],
  ["add"],
  ["const", 0],
  ["div"],
  ["div"],
  ["div"],
  ["end"]
]
```

Constants are canonical decimal strings in an operation `constants` array. In the example, constant index zero is `"2"`.

Stack effects:

| Instruction | Operand | Pop | Push |
|---|---:|---:|---:|
| `arg` | input index | 0 | 1 |
| `const` | constant index | 0 | 1 |
| `add`, `sub`, `mul`, `div` | none | 2 | 1 |
| `neg`, `abs`, `sqrt` | none | 1 | 1 |
| `min`, `max` | none | 2 | 1 |
| `powi` | signed exponent | 1 | 1 |
| comparisons | none | 2 | 1 boolean |
| `select` | none | condition + 2 values | 1 |
| `round` | scale + rounding ID | 1 | 1 |
| `end` | none | 1 logical final | 0 program result |

Programs have no branches, jumps, loops, calls, recursion, indirect memory access, or dynamic instruction operands.

The compiler MUST prove:

- every instruction/operand is valid;
- no stack underflow;
- declared maximum stack is sufficient;
- step count is within limits;
- `end` appears exactly once as the last instruction;
- exactly one result exists at `end` for each declared scalar output program;
- argument and constant indices are in range;
- boolean values are used only by supported boolean/select/classification operations.

Multiple outputs use one program per output in source, compiled as separate program ranges.

## 12. Kernel operations

A kernel operation names one core-defined bounded algorithm instead of a formula program.

Initial kernel keys/IDs are maintained by the core specification, for example:

```text
1 sum
2 mean
3 weighted_mean
4 variance_population
5 variance_sample
6 covariance_population
7 covariance_sample
8 correlation
9 linear_regression
```

A pack cannot define a new kernel implementation. It can only bind metadata, constraints, output policy, and tests to a core-supported kernel ID. Unsupported kernel IDs return `UNSUPPORTED_OPERATION` or cause pack rejection according to the pack's ABI requirements.

## 13. Classifications

Each classification contains:

- nonzero classification ID unique inside the operation;
- stable lowercase key;
- ordered boolean RPN predicate over `result` and constants;
- optional output index for multi-output operations;
- priority.

Classification programs use a stricter VM subset: `result`, `const`, `abs`, comparisons, boolean `and`/`or`/`not`, and `end`.

The compiler MUST detect overlapping test vectors and SHOULD symbolically reject obvious overlapping range predicates. Official operations must provide boundary tests proving every intended class. If `classification_required` is true, no successful result may remain unclassified.

## 14. Aliases and discovery

Aliases are source strings compiled into a deterministic index.

Source rules:

- canonical UTF-8;
- no control characters;
- maximum 64 bytes per alias in official v0.1 packs;
- no duplicate normalized alias inside one pack unless all duplicates point to explicitly related methods;
- canonical operation key and signature tokens are indexed automatically;
- aliases are not operation identity and may expand in compatible pack releases.

Baseline normalization:

1. validate UTF-8;
2. ASCII lowercase A–Z;
3. convert ASCII punctuation/whitespace runs to one space;
4. trim spaces;
5. preserve non-ASCII bytes unchanged.

Locale-specific normalization can occur in an adapter or separate lexicon pack. Runtime ranking is deterministic token exact/prefix scoring with tie-breaks by canonical key bytes, revision descending, then pack ID bytes.

## 15. Golden tests

Every operation contains build-time test vectors.

```json
{
  "name": "elastic",
  "args": ["10000", "12000", "100", "80"],
  "expect": {
    "status": "OK",
    "values": ["-1.222222"],
    "classification": "elastic",
    "rounded": true
  }
}
```

Invalid example:

```json
{
  "name": "unchanged-price",
  "args": ["10", "10", "100", "80"],
  "expect": {
    "status": "DIVIDE_BY_ZERO"
  }
}
```

Golden tests are not required in minimum runtime bytes. The compiler and conformance corpus preserve them separately.

## 16. Compiled `.xsp` container

All multibyte integer fields are little-endian and decoded field-by-field. Native struct casts are forbidden.

### 16.1 Header — 32 bytes

| Offset | Size | Field |
|---:|---:|---|
| 0 | 4 | ASCII magic `XSPK` |
| 4 | 2 | format major, initially `1` |
| 6 | 2 | format minor, initially `0` |
| 8 | 2 | header size, `32` |
| 10 | 2 | section entry size, `16` |
| 12 | 4 | flags |
| 16 | 4 | total file length |
| 20 | 4 | section directory offset |
| 24 | 2 | section count |
| 26 | 2 | reserved, zero |
| 28 | 4 | CRC-32/ISO-HDLC of bytes from offset 32 to end |

The CRC profile is CRC-32/ISO-HDLC (also called CRC-32/IEEE): reflected polynomial `0xedb88320` (normal form `0x04c11db7`), initial value `0xffffffff`, reflected input/output, final XOR `0xffffffff`. The ASCII check input `123456789` produces `0xcbf43926`. The stored value is little-endian. CRC is an integrity check, not authentication.

Header flags v1:

| Bit | Meaning |
|---:|---|
| 0 | alias index present |
| 1 | source metadata present |
| 2 | fused-table-compatible ordering |
| 3–31 | reserved zero |

### 16.2 Section directory entry — 16 bytes

| Offset | Size | Field |
|---:|---:|---|
| 0 | 2 | section kind |
| 2 | 2 | section flags |
| 4 | 4 | section offset |
| 8 | 4 | section byte length |
| 12 | 4 | element count or zero |

Sections must be nonoverlapping, within total length, ordered by offset, and aligned to four bytes unless their kind states otherwise. Unknown optional section kinds may be ignored only when the high optional bit is set; unknown required sections reject the pack.

### 16.3 Section kinds

| Kind | Name | Required |
|---:|---|---|
| 1 | `META` | yes |
| 2 | `STRINGS` | yes |
| 3 | `OPERATIONS` | yes |
| 4 | `INPUTS` | yes when inputs exist |
| 5 | `OUTPUTS` | yes |
| 6 | `CONSTRAINTS` | when constraints exist |
| 7 | `CONSTANTS` | when constants exist |
| 8 | `PROGRAMS` | for formula/classification programs |
| 9 | `CLASSIFICATIONS` | optional |
| 10 | `ALIASES` | optional |
| 11 | `ALIAS_INDEX` | optional |
| 12 | `SOURCES` | optional |
| 13 | `SOURCE_REFS` | optional |

## 17. Core binary records

### 17.1 `META` record — 48 bytes

| Offset | Size | Field |
|---:|---:|---|
| 0 | 4 | pack ID string offset |
| 4 | 4 | name string offset |
| 8 | 4 | description string offset |
| 12 | 4 | SPDX license string offset |
| 16 | 2 | version major |
| 18 | 2 | version minor |
| 20 | 2 | version patch |
| 22 | 2 | numeric profile ID |
| 24 | 4 | minimum encoded ABI |
| 28 | 4 | maximum encoded ABI |
| 32 | 4 | default locale string offset |
| 36 | 4 | operation count |
| 40 | 2 | max vector length |
| 42 | 2 | max VM steps |
| 44 | 2 | max stack |
| 46 | 2 | reserved zero |

String offsets are relative to the start of `STRINGS`.

### 17.2 String table

Each string entry is:

```text
u16 byte_length
byte_length UTF-8 bytes
optional one-byte padding so next entry begins at an even offset
```

Offsets point to the length field. Strings are not NUL-terminated. Offset `0xffffffff` means absent where a field is optional. The string table itself may start with a zero-length string at offset zero.

### 17.3 Operation record — 64 bytes

| Offset | Size | Field |
|---:|---:|---|
| 0 | 4 | operation ID |
| 4 | 2 | revision |
| 6 | 1 | kind: 1 formula, 2 kernel |
| 7 | 1 | flags |
| 8 | 4 | key string offset |
| 12 | 4 | name string offset |
| 16 | 4 | signature string offset |
| 20 | 4 | method string offset or absent |
| 24 | 4 | first input record index |
| 28 | 2 | input count |
| 30 | 1 | output count |
| 31 | 1 | declared max stack |
| 32 | 4 | first output record index |
| 36 | 4 | first program instruction index |
| 40 | 2 | program instruction count |
| 42 | 2 | kernel ID, zero for formula |
| 44 | 4 | first classification record index |
| 48 | 2 | classification count |
| 50 | 1 | default output scale as signed byte |
| 51 | 1 | rounding mode ID |
| 52 | 4 | first alias record index |
| 56 | 2 | alias count |
| 58 | 2 | source reference count |
| 60 | 4 | first source-reference index |

Operation flags include caller scale override, caller rounding override, required classification, and hidden-from-discovery.

### 17.4 Input record — 32 bytes

| Offset | Size | Field |
|---:|---:|---|
| 0 | 4 | name string offset |
| 4 | 1 | semantic kind |
| 5 | 1 | shape: 0 scalar, 1 vector |
| 6 | 2 | flags |
| 8 | 4 | unit namespace string offset or absent |
| 12 | 4 | same-unit-group string offset or absent |
| 16 | 4 | first constraint record index |
| 20 | 2 | constraint count |
| 22 | 2 | max vector length, zero for scalar |
| 24 | 4 | reserved zero |
| 28 | 4 | reserved zero |

### 17.5 Output record — 24 bytes

| Offset | Size | Field |
|---:|---:|---|
| 0 | 4 | name string offset |
| 4 | 1 | semantic kind |
| 5 | 1 | unit rule ID |
| 6 | 2 | flags |
| 8 | 4 | unit rule argument/group string offset or absent |
| 12 | 1 | output scale |
| 13 | 1 | rounding mode |
| 14 | 2 | reserved zero |
| 16 | 4 | first program instruction index for this output |
| 20 | 2 | program instruction count |
| 22 | 2 | reserved zero |

### 17.6 Constant record — 16 bytes

Binary layout matches the logical `xs_decimal_v1` value but is always little-endian and must be decoded, not cast.

### 17.7 Program instruction — 4 bytes

```text
bits 0..7   opcode
bits 8..31  signed or unsigned 24-bit operand according to opcode
```

No-operand instructions require operand zero. Multi-field operands such as `ROUND` pack scale/mode into defined operand bits. The compiler and runtime share generated opcode constants.

### 17.8 Constraint record — 16 bytes

```text
u8  kind
u8  flags
u16 detail_id
u32 constant_index_or_value
u32 auxiliary
u32 reserved_zero
```

### 17.9 Classification record — 24 bytes

```text
u16 classification_id
u16 priority
u32 key_string_offset
u32 program_start
u16 program_len
u16 output_index
u32 flags
u32 reserved_zero
```

### 17.10 Alias record — 12 bytes

```text
u32 alias_string_offset
u32 operation_record_index
u16 weight
u16 flags
```

### 17.11 Source record — 16 bytes

```text
u32 source_id_string_offset
u32 title_string_offset
u32 url_string_offset
u32 license_string_offset
```

## 18. Canonical compilation

Given identical source JSON after semantic normalization and identical compiler version/profile, output `.xsp` bytes must be identical.

Canonical order:

1. operations sorted by numeric ID;
2. inputs/outputs in declared order;
3. classifications by priority then ID;
4. aliases by normalized bytes then operation ID;
5. sources by source ID;
6. strings deduplicated and sorted by raw UTF-8 bytes, except offset-zero empty string;
7. sections in numeric section-kind order;
8. padding bytes zero.

The compiler manifest records compiler version and source digest. The pack does not need to embed its own cryptographic digest because that creates self-reference; release manifests provide SHA-256.

## 19. Integrity and authenticity

CRC-32 detects accidental corruption and supports a small loader. It is not authentication.

Hosts that accept externally supplied packs should verify a release checksum or signature before mounting. v0.1 core signature verification is optional and outside the minimum footprint. Structural validation remains mandatory even for signed packs.

## 20. Fused representation

`exactscope-packc` may generate language source or object data containing validated tables directly. Fused tables must preserve the same:

- pack ID/version;
- operation IDs/keys/revisions;
- programs/constants;
- output/classification semantics;
- alias ranking;
- conformance results.

A conformance test executes every vector against both compiled `.xsp` and fused representation and compares canonical results.

## 21. Rejection requirements

A loader rejects a pack for any of the following:

- invalid magic/header/CRC;
- unsupported required format or ABI;
- section overlap, disorder, misalignment, or out-of-range arithmetic;
- duplicate required sections;
- invalid UTF-8 or string offset;
- duplicate pack operation IDs or canonical keys;
- zero operation revision;
- invalid input/output ranges;
- unsupported numeric profile or kernel;
- invalid constraint references;
- VM underflow/overflow, bad opcode/operand, missing/following `END`, or wrong final stack;
- classifications referencing invalid programs/outputs;
- count or resource limit above runtime caps;
- reserved nonzero fields unless a compatible minor version defines them.

No partial pack registration remains after rejection.
