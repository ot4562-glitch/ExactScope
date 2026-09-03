# Tiny JSON and TinyWire v0.1

ExactScope defines two related protocols:

- **Tiny JSON:** model-facing calls and compact adapter responses;
- **TinyWire:** deterministic CBOR payloads with optional low-overhead stream framing.

Tiny JSON optimizes tool-call reliability. TinyWire optimizes transport size and embedded parsing. Both delegate to the same core ABI.

## 1. Tiny JSON rules

- UTF-8 only;
- one top-level object;
- no duplicate object keys;
- maximum request size 512 bytes;
- no comments or trailing commas;
- decimal arguments are JSON strings, never JSON numbers;
- responses use canonical field order when serialized by ExactScope;
- adapters reject unknown fields in model-generated requests;
- whitespace is accepted by a development parser but canonical output contains none outside strings.

## 2. `xs_find` model arguments

```json
{"q":"midpoint price elasticity","n":3}
```

Fields:

| Field | Type | Rule |
|---|---|---|
| `q` | string | 1–96 UTF-8 bytes after JSON decoding |
| `n` | integer | 1–5 |

Canonical adapter response:

```json
{"s":0,"m":[{"op":"econ.ped.mid","sig":"econ.ped.mid(p1,p2,q1,q2)","method":"midpoint"}]}
```

No match:

```json
{"s":3,"e":"UNKNOWN_OPERATION"}
```

Matches are ordered deterministically. An adapter must not treat rank as statistical confidence.

## 3. `xs_eval` model arguments

```json
{"op":"econ.ped.mid","a":["10000","12000","100","80"]}
```

Fields:

| Field | Type | Rule |
|---|---|---|
| `op` | string | exact canonical operation key, 1–96 ASCII bytes |
| `a` | string array | positional decimal arguments, 0–12 entries |

The Tiny JSON v0.1 model profile handles scalar decimal arguments only. Operations requiring vectors or explicit unit IDs use a cached application-specific wrapper, typed C ABI, or TinyWire call. A later flat vector profile may be added without changing the core.

Canonical success response:

```json
{"s":0,"v":"-1.222222","c":"elastic","p":"econ-undergrad@0.1.0","r":1}
```

Multiple outputs:

```json
{"s":0,"v":["2.5","1.2"],"names":["slope","intercept"],"p":"statistics-core@0.1.0","r":1}
```

Canonical failure response:

```json
{"s":11,"e":"CONSTRAINT_VIOLATION","i":0,"d":1}
```

No nonzero-status response may include `v`.

## 4. Tiny JSON canonical response order

Success scalar:

```text
s, v, c, p, r, scale, round, flags
```

Success multi-output:

```text
s, v, names, c, p, r, scale, round, flags
```

Failure:

```text
s, e, i, d, need, opts, required
```

Optional fields are omitted rather than set to null. Stable field meanings:

| Field | Meaning |
|---|---|
| `s` | numeric status code |
| `v` | canonical scalar string or ordered string array |
| `names` | output names for multiple values |
| `c` | classification key |
| `p` | short pack name/version provenance |
| `r` | operation revision |
| `scale` | requested/effective decimal scale |
| `round` | rounding key |
| `flags` | compact integer result flags |
| `e` | stable error key |
| `i` | zero-based argument index |
| `d` | numeric detail/constraint ID |
| `need` | missing-information keys |
| `opts` | bounded canonical operation-key options |
| `required` | required buffer/arena bytes |

## 5. Tool-schema compatibility profile

The two request schemas use only:

- object;
- string;
- integer;
- array of strings;
- minimum/maximum;
- minItems/maxItems;
- required;
- additionalProperties false.

They deliberately avoid schema unions, references, conditionals, typeless nodes, and regex patterns. Checked-in GBNF must be generated and tested separately for runtimes that support grammar-constrained decoding.

## 6. TinyWire payload

TinyWire payloads use deterministic CBOR as defined by RFC 8949.

Required encoding rules:

- definite-length arrays/maps/text/bytes only;
- shortest integer/length representation;
- integer map keys in ascending encoded order;
- no duplicate keys;
- no CBOR floating-point values;
- decimal values use tag 4 with `[exponent, mantissa]`;
- text is valid UTF-8;
- unknown required keys reject the message;
- unknown extension keys at or above `64` may be ignored only when the message minor version permits extensions.

## 7. TinyWire common keys

| Key | Meaning |
|---:|---|
| 0 | protocol major version, value `1` |
| 1 | message type |
| 2 | status on response, type-specific field on request |
| 3+ | type-specific fields |

Message types:

| Value | Type |
|---:|---|
| 0 | find request |
| 1 | eval request |
| 128 | find response |
| 129 | eval response |
| 255 | error response |

## 8. Find messages

Find request:

```text
{
  0: 1,
  1: 0,
  2: "midpoint price elasticity",
  3: 3
}
```

Find response:

```text
{
  0: 1,
  1: 128,
  2: 0,
  3: [
    [pack_slot, operation_id, revision, "econ.ped.mid",
     "econ.ped.mid(p1,p2,q1,q2)", "midpoint"]
  ]
}
```

The match tuple fields are fixed in v1. Empty method uses an empty text string.

## 9. Eval request

```text
{
  0: 1,
  1: 1,
  2: pack_slot,
  3: operation_id,
  4: [value_ref, ...],
  5: output_scale_or_-128,
  6: rounding_id_or_255,
  7: option_flags
}
```

All fields are required in the binary profile to simplify parsers. Callers use sentinel values for operation defaults.

### 9.1 Value reference

A value reference is:

```text
[value_kind, semantic_kind, unit_id, data]
```

Where:

- `value_kind` 0 = scalar, 1 = vector;
- `semantic_kind` is the numeric profile ID;
- `unit_id` is 0 when unspecified;
- scalar `data` is one tag-4 decimal fraction;
- vector `data` is a definite-length array of tag-4 decimal fractions.

Scalar example for `10000`:

```text
[0, 3, 0, 4([4, 1])]
```

This represents coefficient `1`, exponent `4`, semantic kind `price`, unspecified unit. In diagnostic notation, `4([4,1])` means CBOR tag 4 applied to `[4,1]`.

## 10. Eval response

```text
{
  0: 1,
  1: 129,
  2: 0,
  3: [tag4_decimal, ...],
  4: classification_id,
  5: result_flags,
  6: [pack_slot, operation_id, revision],
  7: output_scale,
  8: rounding_id
}
```

`classification_id` zero means none. The output array contains one to four decimals.

## 11. Error response

```text
{
  0: 1,
  1: 255,
  2: status_code,
  3: detail_code,
  4: argument_index_or_65535,
  5: required_size_or_0,
  6: [option_operation_ids]
}
```

The options array is empty unless resolving ambiguity. Text error labels are not required in TinyWire; the host maps stable codes to keys.

## 12. Stream frame

In-process and datagram transports may carry one raw CBOR payload. Byte-stream transports use this frame:

| Offset | Size | Field |
|---:|---:|---|
| 0 | 2 | ASCII `XS` |
| 2 | 1 | frame version `1` |
| 3 | 1 | flags |
| 4 | 2 | payload length, little-endian |
| 6 | 2 | request ID, little-endian |
| 8 | N | deterministic CBOR payload |
| 8+N | 4 | CRC-32/ISO-HDLC of bytes 0 through 7+N, little-endian |

The frame CRC is CRC-32/ISO-HDLC (CRC-32/IEEE): reflected polynomial `0xedb88320` (normal form `0x04c11db7`), initial value `0xffffffff`, reflected input/output, final XOR `0xffffffff`. The ASCII check input `123456789` produces `0xcbf43926`. CRC detects transport corruption and is not authentication.

Frame flags:

| Bit | Meaning |
|---:|---|
| 0 | response frame |
| 1 | error response hint |
| 2–7 | reserved zero |

Limits:

- total frame at most 4096 bytes by default;
- payload at most 4084 bytes under that default;
- request ID zero means caller does not require correlation;
- responses copy the request ID;
- malformed magic/version/length/CRC is rejected before CBOR decoding;
- parsers cap payload length before waiting for or allocating the payload.

The frame checksum profile is CRC-32/ISO-HDLC (also called CRC-32/IEEE): reflected polynomial `0xedb88320` (normal form `0x04c11db7`), initial value `0xffffffff`, reflected input/output, and final XOR `0xffffffff`. The ASCII check input `123456789` produces `0xcbf43926`. The checksum is stored little-endian. CRC detects transport corruption; it is not authentication.

## 13. Streaming parser requirements

A conforming parser:

- uses a fixed maximum nesting depth of 4 for v1 messages;
- rejects indefinite lengths;
- rejects maps/arrays over message-specific caps before iterating;
- never allocates based solely on an untrusted length;
- handles split headers and payloads;
- can discard bytes until the next `XS` candidate after a bad frame according to host policy;
- does not execute a request until CRC and complete CBOR validation succeed.

## 14. Versioning

- Frame version and TinyWire protocol major are both `1` in v0.1.
- A different major is incompatible and returns/reports version failure.
- Backward-compatible message keys use protocol minor negotiation in a future extension; v1 senders emit only defined keys.
- Tiny JSON is versioned by the adapter package and schemas; its two operation names and required fields remain stable through ABI major 1.

## 15. Transport mappings

TinyWire may be transported over:

- in-process buffers;
- stdin/stdout;
- Unix domain sockets or named pipes;
- Bluetooth/BLE application characteristics;
- serial links;
- local datagrams;
- application-owned HTTP bodies.

ExactScope core does not open any transport. The host passes complete validated frame or payload bytes to an adapter function.

## 16. No hidden coercion

Neither Tiny JSON nor TinyWire may:

- insert omitted arguments;
- reorder arguments by guessing;
- convert percent text to ratios;
- strip unit text from numeric strings;
- substitute zero for invalid values;
- change method keys after an error;
- retry with rounded values.

Any convenience transformation must be explicit in the host product before the ExactScope call and visible to that product's audit/logging policy.

## 17. Fixture requirements

Implementation must check in canonical fixtures for:

- valid find request/response;
- valid scalar eval request/response;
- multi-output response;
- vector request;
- every status-code family;
- maximum-size accepted frame;
- one-byte truncation at every frame position;
- wrong CRC;
- duplicate CBOR key;
- noncanonical integer encoding;
- CBOR float where decimal tag is required;
- wrong semantic kind;
- argument count mismatch;
- Tiny JSON large integer preserved as a string.

Binary fixture bytes become normative after the first implementation release.
