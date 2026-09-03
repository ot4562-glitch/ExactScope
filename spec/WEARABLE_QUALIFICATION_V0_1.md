# ExactScope Wearable Qualification v0.1

Status: **normative evidence and release-claim procedure** for [`wearable-edge-v0.1`](WEARABLE_EDGE_PROFILE_V0_1.md).

This document defines what a device team must measure, preserve, and sign off before describing one ExactScope integration as `measured` or `qualified`. It is vendor-neutral and does not claim knowledge of unpublished hardware-vendor requirements.

The machine-readable record is [`examples/wearable-qualification-record.json`](examples/wearable-qualification-record.json), validated against [`schemas/wearable-qualification-record.schema.json`](schemas/wearable-qualification-record.schema.json) and the current wearable profile.

## 1. Evidence states

A record has exactly one top-level status:

| Status | Meaning |
|---|---|
| `draft` | Template or incomplete run. Placeholders and `not-run` evidence are permitted. No performance/product claim is allowed. |
| `measured` | Every physical evidence category has actually been run. Categories may pass or fail. Placeholders and zero digests are forbidden. |
| `qualified` | Every mandatory category passes every `wearable-edge-v0.1` limit and destructive test. |

`qualified` is not a human-entered opinion. The repository validator recomputes the relevant pass conditions from recorded measurements.

The evidence categories are:

- latency;
- energy;
- footprint;
- conformance/product destructive tests.

A `qualified` record with any category marked `fail` or `not-run` is invalid.

## 2. Execution mode identity

Every qualification record is bound to one exact execution mode:

- `native-fused-discovery`;
- `native-dynamic-exact`;
- `wasm-fused-discovery`.

Evidence MUST NOT be copied between modes without rerunning the applicable measurements and conformance suite.

In particular:

- dynamic-pack mount latency applies to `native-dynamic-exact`;
- dynamic mode requires at least one immutable pack artifact in the evidence record;
- dynamic discovery is not a v0.1 qualified mode because the current core intentionally fails that configuration closed;
- native and Wasm result-identity conformance remains mandatory even when only one of those modes ships, because it guards portability drift in the shared calculation authority.

## 3. Device identity

A measured record MUST identify the exact or shipping-equivalent unit by recording:

- product/board identifier;
- board revision;
- SoC;
- CPU architecture;
- OS name and OS build;
- firmware build;
- power/performance mode;
- thermal state;
- battery voltage in millivolts;
- display state;
- radio state.

`TBD`, `TODO`, `UNKNOWN`, empty strings, and zero battery voltage are not valid measured evidence.

If a firmware, OS, compiler, CPU governor policy, or board revision changes in a way that could affect timing, power, memory, ABI behavior, or pack handling, previous physical qualification MUST NOT automatically transfer.

## 4. Artifact identity

Measured evidence MUST be bound to immutable artifacts:

- exact 40-hex source commit;
- runtime SHA-256;
- runtime artifact byte size;
- SHA-256 of the canonical wearable profile JSON;
- each separately mounted `.xsp` pack ID, SHA-256, and byte size.

The qualification validator recomputes the canonical profile digest from the repository and rejects a measured/qualified record whose `profile_sha256` differs.

For dynamic mode:

- at least one pack artifact is required;
- no pack may exceed 256 KiB;
- at most four packs may be listed;
- total listed pack bytes may not exceed 512 KiB.

For a fused build, `packs` MAY be empty when the pack data is part of the runtime artifact digest.

## 5. Latency evidence

The executable collection boundary, canonical raw CSV, upward nanosecond-to-microsecond conversion, and nearest-rank percentile rule are normative in [`WEARABLE_BENCHMARK_V0_1.md`](WEARABLE_BENCHMARK_V0_1.md). A measured/qualified latency section SHOULD be populated from that reducer output rather than a separately implemented percentile script.

### 5.1 Required sample procedure

A latency run MUST use:

- shipping release optimization and feature set;
- the exact evidence-bound runtime artifact;
- one ExactScope worker/context;
- no concurrent benchmark workload;
- at least **1,000 warm-up iterations**;
- at least **10,000 recorded iterations**;
- a monotonic target-device clock documented in `latency.clock`.

Timing MUST exclude:

- camera/ISP work;
- microphone capture;
- OCR/ASR;
- LLM inference;
- UI/audio rendering;
- network access;
- the host wake-up that caused the operation.

The benchmark stores integer microsecond values for p50, p95, p99, and maximum. For each metric:

```text
p50 <= p95 <= p99 <= max
```

must hold.

### 5.2 Required targets

A `pass` latency state requires:

- lookup p99 <= **250 us**;
- scalar evaluation p50 <= **250 us**;
- scalar evaluation p99 <= **1,000 us**;
- for `native-dynamic-exact`, 256 KiB pack-mount p99 <= **10,000 us**.

A latency category marked `pass` while exceeding any applicable target is invalid. A category marked `fail` while all applicable targets pass is also invalid, preventing stale/manual verdicts.

### 5.3 Raw data retention

The summary JSON is not the raw benchmark corpus. A product qualification package SHOULD retain immutable raw sample data separately with:

- one duration per sample;
- operation ID/key;
- pack digest/build digest;
- start/end thermal readings if available;
- CPU frequency/governor or equivalent power-mode information;
- test harness version.

Raw data SHOULD be hash-addressed from the product's evidence system even if it is too large to ship in this repository.

## 6. Energy evidence

### 6.1 Accepted methods

A measured energy record MUST use exactly one of:

- `battery-rail` measurement with a calibrated external instrument; or
- a validated `pmic-counter` exposed by the target device.

CPU utilization, cycle counts, scheduler time, or a desktop power model alone are not sufficient qualification evidence.

### 6.2 Required recorded fields

The record MUST include:

- measurement method;
- instrument/counter identity;
- sample count;
- baseline idle energy over the comparable interval;
- measured total energy;
- incremental energy per ExactScope evaluation;
- measurement sampling interval.

Measured total energy MUST be greater than or equal to baseline energy.

At least **10,000 evaluations** are required for the default v0.1 energy run.

### 6.3 Pass condition

The incremental energy attributed to one scalar ExactScope evaluation, excluding host wake/perception/model/rendering/radio work, MUST be <= **500 uJ**.

A `pass` state at 500.001 uJ or above is invalid.

## 7. Footprint evidence

The measured footprint records:

- exact `xs_context_size()` result;
- maximum evaluation scratch configured/required by the shipping hot path;
- pack mount arena;
- adapter/request/response fixed-buffer budget;
- mutable total;
- stripped runtime + fused hot-pack artifact size.

The record MUST satisfy:

```text
mutable_total_bytes =
    context_bytes
  + eval_scratch_bytes
  + pack_mount_arena_bytes
  + adapter_buffer_bytes
```

A pass requires:

- context <= **4 KiB**;
- evaluation scratch <= **4 KiB**;
- pack-mount arena = **0 B**;
- adapter buffers <= **8 KiB**;
- mutable total <= **16 KiB**;
- stripped runtime + fused hot pack <= **1 MiB**.

The context and stripped artifact sizes MUST be nonzero in measured evidence.

Immutable mapped pack bytes are tracked separately from mutable runtime memory.

## 8. Conformance evidence

The conformance section binds product qualification to executable repository and device tests.

It records:

- design-baseline CI run identifier;
- wearable-profile CI run identifier;
- conformance corpus SHA-256;
- total/passed/failed counts;
- destructive-test booleans;
- update power-loss injection count.

The invariant is:

```text
total = passed + failed
```

A conformance `pass` requires:

- total > 0;
- failed = 0;
- passed = total;
- truncation-at-every-pack-byte test passes;
- single-bit pack corruption test passes;
- fused/dynamic result-identity test passes;
- native/Wasm result-identity test passes;
- airplane-mode device test passes;
- privacy audit passes;
- at least **8 distinct A/B update power-loss cases** are executed;
- every power-loss case passes.

A record that merely links successful CI but omits the real-device offline/update/privacy evidence is not qualified.

## 9. A/B update power-loss matrix

The minimum eight injection points are:

1. before candidate write begins;
2. during candidate pack write;
3. after candidate write but before host digest verification;
4. after host digest verification but before ExactScope mount;
5. during complete pack-set mount/smoke validation;
6. after registry freeze but before activation metadata write;
7. during activation metadata commit;
8. immediately after activation commit and before old-slot retirement.

Each case MUST force process/device interruption, reboot/restart the product update state machine, and verify that exactly one complete pack set is selected.

Expected safety rule:

- interruption before committed activation -> previous active pack set remains authoritative;
- interruption after committed activation -> new complete pack set may remain active;
- a partially written/unvalidated candidate MUST never become active;
- rollback MUST not require recompilation.

A vendor MAY test additional filesystem/flash-specific injection points; eight is the v0.1 minimum, not a completeness ceiling.

## 10. Airplane-mode test

The physical device MUST enter a product-defined radios-disabled state sufficient to demonstrate that ExactScope evaluation has no network dependency.

The test SHOULD verify at least:

- exact lookup of a known operation;
- one successful scalar evaluation;
- one expected failure path;
- no ExactScope-owned socket/file/network service is started as a side effect.

The recorded `device.radio_state` must describe the state used.

Live-data-dependent product features are outside this assertion. For example, a currency rate may have to be supplied by the host before radios are disabled; ExactScope itself still performs only deterministic local arithmetic.

## 11. Privacy audit

A qualification privacy audit MUST inspect the default production telemetry path and verify that it does not emit:

- raw camera/audio;
- OCR/ASR transcript;
- argument values;
- result numeric values;
- user/account identifiers;
- precise location.

The wearable reference host produces only status, pack slot, operation ID, and a coarse duration bucket. Artifact digest metadata may be added by the product update layer.

Debug builds with richer host logging do not invalidate the reference design, but such logging MUST NOT be enabled by default in the qualified production configuration.

## 12. Malformed-input and fault containment

Qualification MUST include malformed requests and packs through the exact shipping boundary.

Required classes include:

- invalid/null pointer combinations that are safely testable;
- wrong structure size;
- too-small output/scratch buffers;
- malformed decimal;
- wrong semantic kind;
- wrong argument count;
- unknown operation/pack;
- unsupported option/feature combination;
- malformed `.xsp` section tables;
- CRC mismatch;
- every-byte truncation corpus.

The acceptance condition is bounded deterministic failure with the documented status code. No C ABI unwind, process abort, memory violation, or Wasm trap is acceptable for malformed external input.

## 13. CI evidence versus physical evidence

CI proves source-level and virtual-target properties such as:

- schemas/registries alignment;
- C99/C++11 compilation;
- Rust formatting/lint/test;
- Rust 1.84 MSRV;
- no-import `wasm32v1-none` build;
- shared conformance fixtures;
- dynamic pack C ABI tests;
- wearable profile/header drift checks.

CI does **not** prove:

- target SoC p99 latency;
- target battery energy;
- final firmware scheduler behavior;
- final board thermal behavior;
- actual A/B flash power-loss recovery;
- product telemetry configuration.

Those fields require target-device evidence and are deliberately represented separately.

## 14. Status transition procedure

### Draft -> measured

Before setting `status: "measured"`:

1. remove all `TBD`/placeholder device fields;
2. record nonzero source/runtime/profile digests;
3. use the exact canonical profile SHA-256;
4. run latency with required sample counts;
5. run rail/PMIC energy measurement;
6. measure memory/artifact footprint;
7. execute conformance/destructive/device tests;
8. preserve raw evidence in the product evidence store;
9. set each category state to `pass` or `fail` according to measured values.

A measured record is valuable even when it fails. It is a truthful engineering result, not a release approval.

### Measured -> qualified

`status` may become `qualified` only when:

- latency state = `pass`;
- energy state = `pass`;
- footprint state = `pass`;
- conformance state = `pass`;
- all current profile limits are satisfied;
- all required destructive/device booleans are true;
- power-loss count >= 8 and every case passes;
- profile digest matches the exact canonical profile bytes.

The validator rejects a manually forced `qualified` status when any one of these conditions is false.

## 15. Requalification triggers

A new qualification record SHOULD be created after changes to any of:

- SoC or board revision;
- firmware/OS build;
- Rust/native compiler or optimization profile;
- C ABI feature set;
- fused/dynamic/Wasm execution mode;
- runtime artifact;
- official pack contents or pack compiler affecting binary representation;
- memory budgets;
- CPU/power governor policy;
- telemetry defaults;
- update storage/activation mechanism.

A pure documentation change with identical binaries/profile semantics does not necessarily require physical rerun, but the release process must make that determination explicitly rather than silently carrying evidence forward.

## 16. Product evidence package

A release engineering handoff for one qualified wearable build SHALL contain or reference:

```text
wearable-qualification-record.json
wearable-edge-profile.json
runtime artifact + sha256
pack artifacts + sha256 (when dynamic)
source commit
raw latency samples + summary
energy trace/counter export + summary
footprint report
conformance corpus digest + result log
CI run identifiers
A/B power-loss test report
privacy audit report
known deviations: none, or explicit release blocker
```

The qualification JSON is the index of this evidence, not a substitute for the underlying raw records.

## 17. Claim language

Allowed when only the checked-in template exists:

> Wearable integration contract defined; target-device qualification not yet measured.

Allowed after a valid `measured` record:

> Target-device measurements recorded; see qualification record for pass/fail status.

Allowed only after a valid `qualified` record:

> This exact artifact/device/profile combination satisfies `wearable-edge-v0.1` qualification.

A general statement such as “works on all smart glasses” or “Meta-ready” MUST NOT be inferred from one target record. Qualification is always scoped to the artifact, device configuration, execution mode, and profile digest recorded in evidence.
