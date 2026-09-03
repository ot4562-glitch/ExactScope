# Wearable reference host

This directory is a **product-integration reference**, not a second calculation engine. It enforces the limits in [`../../spec/WEARABLE_EDGE_PROFILE_V0_1.md`](../../spec/WEARABLE_EDGE_PROFILE_V0_1.md) around the stable ExactScope C ABI.

The reference is intentionally plain C99 so a device team can compile it into a native service, firmware-facing userspace component, Android/JNI library, or C++ application without bringing in a framework, allocator, thread pool, or network stack.

## Files

- `exactscope_wearable_ref.h` — host state, constants, privacy-minimized telemetry, wrapper API.
- `exactscope_wearable_ref.c` — bounded reference state machine.
- `exactscope_wearable_ab.h` — two-slot activation journal/storage callback API.
- `exactscope_wearable_ab.c` — 96-byte dual-copy CRC journal, crash recovery, rollback retention, stale-state rejection.
- [`AB_UPDATE.md`](AB_UPDATE.md) — byte layout, durability contract, commit ordering, and real-device power-loss qualification guidance.

No function in these reference modules performs network I/O, file I/O, allocation, logging, timing, sensor capture, or model inference. Persistent pack contents and metadata I/O are supplied through product-owned storage boundaries.

## Product modes

### `XSW_REF_MODE_FUSED_DISCOVERY_V1`

Use when the shipping hot pack is compiled/fused into the runtime.

- exact lookup: yes;
- discovery: yes;
- dynamic pack mount: no;
- state after init: `FROZEN`;
- appropriate for the smallest, most deterministic on-glasses hot path.

### `XSW_REF_MODE_DYNAMIC_EXACT_V1`

Use when the host installs `.xsp` bytes at startup/update time.

- exact lookup: yes;
- discovery: intentionally no in v0.1;
- dynamic pack mount: yes;
- mount arena: exactly 0 bytes;
- state after init: `MUTABLE`;
- host mounts the complete set, calls `xsw_ref_finish_install`, then state becomes `FROZEN`.

Dynamic + discovery is not hidden behind a permissive fallback. It remains unsupported until the core implements and conforms the dynamic alias index.

## State machine

```text
                 xsw_ref_init(fused)
UNINITIALIZED ------------------------------> FROZEN
     |
     | xsw_ref_init(dynamic)
     v
  MUTABLE -- xsw_ref_mount/unmount --> MUTABLE
     |
     | xsw_ref_finish_install
     v
  FROZEN -- xsw_ref_lookup/eval --> FROZEN
     |
     | xsw_ref_reset
     +-----------------------------> MUTABLE (dynamic)
     +-----------------------------> FROZEN  (fused)

Any wrapper-detected internal bookkeeping contradiction -> FAULTED
```

User-facing lookup/evaluation is rejected unless state is `FROZEN`.

This makes “validate the whole pack set, then serve” a code property rather than a comment.

## Required memory supplied by the product

The adapter owns no heap. The product supplies:

| Storage | Maximum |
|---|---:|
| ExactScope context memory | 4 KiB |
| evaluation scratch | 4 KiB |
| pack-mount arena | 0 B |
| product adapter/request/response buffers | 8 KiB |
| total mutable ExactScope-side budget | 16 KiB |

Pack bytes are immutable caller-owned storage and are not counted as mutable runtime memory. Dynamic pack storage is capped at 256 KiB per pack and 512 KiB total.

A production host SHOULD map validated mounted pack bytes read-only when its OS/MMU permits it.

## Boot sequence: fused build

```c
xsw_ref_host_v1 host = {0};
uint32_t required = 0;

host.struct_size = (uint32_t)sizeof(host);
status = xsw_ref_init(
    &host,
    XSW_REF_MODE_FUSED_DISCOVERY_V1,
    context_memory,
    context_memory_len,
    &required);
```

Success means the registry is already frozen. The product may begin lookup/evaluation immediately.

## Boot/update sequence: dynamic pack build

The product update manager, not this adapter, owns download/signature/A-B storage.

```text
1. authenticate candidate using product update trust root
2. write candidate pack set to inactive A/B slot
3. create fresh xsw_ref_host_v1
4. xsw_ref_init(... DYNAMIC_EXACT ...)
5. xsw_ref_mount(pack 1)
6. xsw_ref_mount(pack 2) ...
7. run fixed smoke corpus
8. xsw_ref_finish_install()
9. atomically commit active A/B slot in product metadata
10. begin serving user requests
```

If any mount or smoke test fails, discard the new context and keep the previous active slot.

`xsw_ref_mount` rejects before/around the core boundary when:

- pack pointer/length is invalid;
- one pack exceeds 256 KiB;
- total pack bytes exceed 512 KiB;
- more than four packs are installed;
- the core requires a nonzero mount arena;
- the underlying `.xsp` validation fails.

## Exact lookup/evaluation path

A product request should already contain normalized, typed values. Raw OCR/ASR text does not enter this layer.

```text
perception/model
  -> canonical operation key
  -> exact decimal strings parsed into xs_decimal_v1
  -> xsw_ref_lookup
  -> xsw_ref_eval
  -> canonical xs_result_v1
  -> renderer copies result; renderer does not recompute
```

The host should allocate `xs_result_v1` once in request-local storage and set `struct_size` before each call.

For a scalar operation requiring no scratch, pass `NULL, 0`. If a future operation needs scratch, the adapter refuses anything above 4 KiB.

## Discovery path

`xsw_ref_find` is available only in fused-discovery mode.

The wrapper caps output capacity at five matches. The product should treat discovery as method selection, not probabilistic confidence. Once a method is selected, evaluation is still by stable operation ID/key.

For dynamic-pack products that require discovery, the current v0.1 reference requires the host to wait for a future conformed dynamic alias index rather than maintaining a separate divergent alias catalog.

## Privacy-minimized telemetry

`xsw_ref_make_telemetry` creates this shape:

```text
status
pack_slot
operation_id
duration_bucket
```

It deliberately omits:

- arguments;
- result values;
- OCR/ASR text;
- camera/audio content;
- user/account identity;
- location.

The adapter does not read a clock. The host measures duration and supplies `duration_us`. The wrapper converts it to one of four coarse buckets:

- <= 250 us;
- <= 1 ms;
- <= 10 ms;
- > 10 ms.

Artifact/pack digest telemetry, if desired, belongs to the product update layer because the reference wrapper does not own a crypto implementation or pack-file identity store.

## Error behavior

The wrapper returns the core `xs_status` space. It does not turn errors into numbers.

Additional reference-host checks use existing stable codes:

- invalid state/pointer/mode -> `INVALID_REQUEST`;
- mode feature intentionally unavailable -> `UNSUPPORTED_OPERATION`;
- wearable memory/pack/arena limit exceeded -> `RESOURCE_LIMIT`;
- install freeze requested with zero dynamic packs -> `MISSING_INFORMATION`;
- wrapper bookkeeping contradiction -> `INTERNAL_ERROR` and `FAULTED` state where applicable.

A product should discard a `FAULTED` host and initialize a new context.

## Threading

The reference host contains no lock and creates no thread.

Until a later conformance record qualifies shared immutable contexts, use one `xsw_ref_host_v1`/`xs_context` per worker. Mutation (`mount`, `unmount`, `reset`, `finish_install`) must not run concurrently with evaluation.

## Timing ownership

ExactScope does not own clocks. The product should measure:

```text
t0 = monotonic_time()
xsw_ref_eval(...)
t1 = monotonic_time()
xsw_ref_make_telemetry(..., t1 - t0, ...)
```

The shipping qualification procedure requires 1,000 warmup samples and at least 10,000 measured samples on the target device.

## What a glasses/device team still owns

This reference intentionally does not implement:

- camera capture/ISP;
- OCR/ASR;
- model inference;
- display/audio rendering;
- Bluetooth/Wi-Fi;
- authentication/account services;
- pack download;
- signature verification;
- A/B persistent storage;
- PMIC/battery measurement;
- application telemetry transport.

Those are separate product domains. Their outputs/inputs meet ExactScope only at the bounded C ABI boundary.
