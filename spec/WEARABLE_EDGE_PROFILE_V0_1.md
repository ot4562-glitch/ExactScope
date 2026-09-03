# ExactScope Wearable Edge Profile v0.1

Status: **normative product-integration profile, contract targets only**.

This profile defines the minimum integration contract for shipping ExactScope inside a battery-constrained, camera/microphone-equipped wearable such as AI glasses. It is vendor-neutral. It does **not** claim access to or compatibility with any private Meta, Apple, Google, Qualcomm, or other unpublished platform requirement.

The goal is specific enough that a device systems team, native runtime team, companion-app team, privacy team, QA team, and release engineering team can implement and test the same product boundary without inventing missing behavior.

The machine-readable authority for numeric limits is [`examples/wearable-edge-profile.json`](examples/wearable-edge-profile.json), validated by [`schemas/wearable-edge-profile.schema.json`](schemas/wearable-edge-profile.schema.json).

## 1. Product role

ExactScope is a deterministic numeric coprocessor behind an AI interaction layer. It is not a perception stack, a speech recognizer, a language model, a display compositor, or a cloud service.

A wearable product pipeline SHALL be structured as:

```text
camera / microphone / touch / phone data
                |
                v
      perception / ASR / OCR
                |
                v
  intent + typed-value extraction
                |
                v
       ExactScope boundary
      xs_lookup / xs_eval
                |
                v
  structured deterministic result
                |
                v
  language / audio / display renderer
```

The core MUST NOT receive raw camera frames or raw microphone frames. Perception code may derive bounded numeric strings, units, operation keys, and method choices before invoking ExactScope.

Examples of suitable wearable flows include:

- compare two shelf prices after the perception layer has extracted price and quantity;
- calculate a discount or percentage change from values visible to the user;
- convert a monetary amount when the host supplies the exchange rate from a separately governed data source;
- calculate finance/economics quantities from a chart, receipt, lecture board, or dashboard;
- verify a model-proposed arithmetic/economics answer locally before speaking or displaying it.

Operation availability is determined by mounted/fused packs. These examples are product flows, not claims that every operation is already implemented.

## 2. Non-negotiable runtime boundary

A wearable-qualified build MUST satisfy all of the following during evaluation:

| Property | Requirement |
|---|---:|
| Network required by `xs_eval` | **No** |
| Core-owned background threads | **0** |
| Core-owned sockets | **0** |
| Core-owned periodic wakeups | **0** |
| Heap required in evaluation hot path | **No** |
| Persistent user storage required | **No** |
| Raw camera/audio accepted | **No** |
| Call model | synchronous, bounded |
| Default concurrency | one context per worker until shared-context qualification |

The runtime MUST NOT perform DNS, HTTP, Bluetooth, Wi-Fi, file downloads, account lookup, or telemetry upload. Those are host responsibilities.

The runtime MUST NOT create timers, worker threads, executors, event loops, file descriptors, or background wake sources.

## 3. Wearable hard limits

These values are integration ceilings, not aspirational measurements.

| Resource | v0.1 ceiling |
|---|---:|
| `xs_context_size()` | 4 KiB |
| Evaluation scratch | 4 KiB |
| Pack-mount arena | **0 B** (prebuilt-index zero-copy packs only) |
| Adapter fixed buffers | 8 KiB |
| Total mutable runtime working set | 16 KiB |
| Tiny request | 512 B |
| Tiny response | 512 B |
| One dynamic `.xsp` pack | 256 KiB |
| Total mounted dynamic pack bytes | 512 KiB |
| Mounted packs | 4 |
| Wearable vector length | 64 |
| VM instructions/evaluation | 64 |
| VM stack entries | 16 |
| Result scalar values | 4 |
| Canonical operation key | 96 B |

The general core may support a wider limit. A wearable product using this profile MUST configure or enforce the smaller wearable ceiling at the host boundary.

`max_context_bytes + max_eval_scratch_bytes + max_pack_mount_arena_bytes + max_adapter_buffer_bytes` MUST NOT exceed the declared 16 KiB mutable-runtime budget.

Wearable v0.1 requires `max_pack_mount_arena_bytes = 0`: only packs whose prebuilt runtime tables can be mounted without copied registration state are admissible. A future profile revision must explicitly rebudget mutable memory before allowing a nonzero mount arena.

A product MUST reject a pack before registration if its declared vector, VM-step, stack, pack-size, or mount-arena requirement exceeds this profile.

## 4. Latency and energy product targets

The following are **qualification targets**, not current implementation claims:

| Metric | Target |
|---|---:|
| Scalar eval p50 | <= 250 us |
| Scalar eval p99 | <= 1,000 us |
| Exact key lookup p99 | <= 250 us |
| 256 KiB pack mount p99 | <= 10 ms |
| Scalar eval energy, excluding host wake/perception/model | <= 500 uJ |
| Stripped runtime + fused hot pack | <= 1 MiB |
| Runtime periodic wakeups/minute | 0 |

No README, release note, compatibility manifest, or product claim may state that these targets are met until evidence is recorded as `measured-pass` for the corresponding category.

### 4.1 Latency measurement procedure

A qualification run MUST:

1. use a release build with the shipping feature set;
2. run on the exact device SoC/OS image or final-equivalent development unit;
3. perform 1,000 warm-up evaluations;
4. collect at least 10,000 timed samples;
5. use one worker/context and no concurrent benchmark workload;
6. measure `xs_lookup` and `xs_eval` separately;
7. exclude ASR, OCR, camera ISP, LLM generation, UI rendering, network, and host wake-up time;
8. report p50, p95, p99, maximum, sample count, CPU frequency policy, thermal state, and build digest;
9. fail qualification if p99 exceeds the profile target even when the mean passes.

A benchmark that silently changes scale, rounding, arguments, pack, or operation between samples is invalid.

### 4.2 Energy measurement procedure

Energy SHALL be measured at the device battery rail or a validated PMIC energy counter. CPU-time-derived estimates alone are insufficient for qualification.

The integration report MUST state:

- measurement point and instrument/counter;
- sampling interval;
- device battery voltage range;
- thermal state;
- screen/display state;
- radio state;
- benchmark iteration count;
- baseline idle energy over the same interval;
- incremental ExactScope energy after baseline subtraction.

The 500 uJ target excludes device wake, camera capture, ASR/OCR, LLM inference, display rendering, and radio operation.

## 5. Sensor, privacy, and data minimization contract

The core SHALL accept only already-normalized bounded data such as operation keys, exact decimal values, units, and options.

The default telemetry path MUST NOT contain:

- camera/audio data;
- OCR/ASR transcripts;
- raw argument values;
- raw result values;
- nearby-person identifiers;
- account identifiers;
- precise location.

Default telemetry MAY contain only:

- stable status code;
- operation ID;
- pack slot;
- coarse duration bucket;
- artifact/pack digest.

A host may implement richer diagnostics only behind its own explicit privacy/debug policy. ExactScope itself does not persist user inputs.

A nonzero status MUST produce zero usable result values. The presentation layer MUST NOT ask the model to invent a replacement numeric answer after ExactScope reports failure unless the user is explicitly told the answer is unverified.

## 6. Device memory ownership

### 6.1 C ABI

The host owns context, pack, argument, scratch, and output storage. ExactScope MUST NOT free host memory.

For dynamic packs:

- pack bytes remain immutable and alive from successful `xs_pack_mount` until `xs_pack_unmount` or context reset;
- production hosts SHOULD place mounted pack memory read-only after validation when the platform supports it;
- the runtime MUST validate structure and CRC before registration;
- no partial registration may survive a failed mount.

### 6.2 WebAssembly

The no-import WebAssembly build MUST use the frozen `wasm32v1-none` memory/export contract. It MUST NOT require WASI, JavaScript timers, fetch, random, filesystem, or host imports.

A wearable product using WebAssembly MUST preallocate nonoverlapping request/output/meta regions and MUST treat any trap on malformed external input as a release-blocking defect.

## 7. Determinism and result identity

For identical pack bytes, operation identity, arguments, units, scale, and rounding policy:

- fused native;
- dynamic-pack native;
- C ABI;
- WebAssembly;
- Tiny JSON adapter

MUST normalize to the same status and canonical numeric result.

At minimum the following fields MUST agree wherever the interface exposes them:

- status;
- result flags;
- value count;
- canonical decimal coefficient/exponent;
- semantic kind and unit ID;
- classification ID/key;
- pack slot or stable pack identity as defined by the interface;
- operation ID and revision;
- output scale;
- rounding mode;
- failing argument index;
- detail code.

Cross-target drift is a release blocker, not an adapter concern.

## 8. Pack installation and update protocol

A shipping wearable host MUST implement pack updates as an A/B transaction.

The v0.1 reference activation contract uses two independent 96-byte journal copies. Each record carries a monotonic generation, active/previous slot identity, active/previous SHA-256 digests, rollback-retention state, and CRC-32/ISO-HDLC. The non-current metadata copy is written and durably flushed before it can become authoritative; the previous known-good slot remains protected until an explicit accept or rollback commit. The byte layout and storage-callback semantics are specified in [`../adapters/wearable/AB_UPDATE.md`](../adapters/wearable/AB_UPDATE.md).

### 8.1 Required host sequence

1. Download or receive a candidate pack through the product's existing authenticated update channel.
2. Verify publisher authenticity/signature **before** calling ExactScope.
3. Store candidate bytes in inactive slot B.
4. Verify file length and host-level digest.
5. Create a fresh ExactScope context.
6. Mount the complete candidate pack set.
7. Let ExactScope verify format, version, CRC, limits, IDs, VM programs, UTF-8, and collisions.
8. Execute a fixed local smoke corpus.
9. Freeze the registry.
10. Atomically switch the host's active-pack pointer from A to B.
11. Keep A until the new set survives the product's rollback window.

ExactScope MUST NOT download or self-update packs.

### 8.2 Power-loss behavior

A power loss at any step before atomic activation MUST leave the old active set selected. A candidate pack without a committed activation record MUST be treated as inactive on next boot.

Rollback MUST NOT require recompiling the previous pack.

## 9. Offline product behavior

All deterministic evaluation and exact lookup MUST work in airplane mode.

If the upstream product feature requires live data, the host is responsible for obtaining and timestamping that data before invoking ExactScope. Example: currency conversion requires a host-supplied exchange rate; the core does not fetch one.

When live data is unavailable, the host MUST distinguish:

- computation unavailable because required external data is missing; and
- computation failed because ExactScope rejected the input.

The host MUST NOT silently reuse stale market/economic data without a product-level freshness policy.

## 10. Failure-to-UI policy

The wearable presentation layer SHALL map ExactScope failures conservatively.

| Core class | Product behavior |
|---|---|
| `INVALID_REQUEST`, `INVALID_DECIMAL`, `ARGUMENT_*` | ask for/re-extract the value |
| `MISSING_INFORMATION`, `AMBIGUOUS_METHOD` | ask one targeted question |
| `CONSTRAINT_VIOLATION`, `DOMAIN_ERROR`, `DIVIDE_BY_ZERO` | explain that the supplied values make the calculation invalid |
| `OVERFLOW`, `PRECISION_UNRESOLVED`, `RESOURCE_LIMIT` | state that the device profile cannot safely compute it |
| `PACK_INVALID`, `PACK_VERSION_UNSUPPORTED`, `INTEGRITY_ERROR` | reject the pack; use last known-good pack set |
| `INTERNAL_ERROR` | discard/reinitialize context and log only permitted diagnostics |

A failed calculation MUST NOT be rendered as a normal numeric answer.

## 11. Wearable model-integration contract

The language/perception model may choose **which** operation to call and extract candidate values. It may not redefine the operation semantics.

Recommended interaction flow:

```text
model/perception output
  operation_key = "..."
  args = exact decimal strings + semantic kinds/units
        |
        v
xs_lookup / xs_find
        |
        v
method/identity resolved
        |
        v
xs_eval
        |
        +---- status != OK --> correction / one clarification / safe failure
        |
        v
canonical result
        |
        v
model verbalizes WITHOUT recomputing
```

The final language generator SHOULD receive the canonical value as protected structured data and SHOULD be instructed to copy rather than recalculate it.

## 12. Product qualification matrix

A vendor may claim `wearable-edge-v0.1` only after all rows pass on the shipping-equivalent target.

| Area | Required evidence |
|---|---|
| Build | reproducible artifact digest and toolchain |
| ABI | C99/C++11 header compile and structure checks |
| Wasm if shipped | no imports/WASI, required exports, malformed-input no-trap |
| Numeric | canonical golden corpus |
| Fused/dynamic | byte/result identity corpus |
| Pack loader | all-byte truncation rejection and CRC corruption rejection |
| Limits | configured wearable caps proven |
| Latency | 1k warmup + >=10k samples, p99 targets pass |
| Energy | battery-rail/PMIC measurement, incremental target passes |
| Footprint | stripped shipping artifact <= profile target |
| Offline | evaluation in airplane mode |
| Update | A/B activation + forced power-loss recovery |
| Privacy | default telemetry contains no raw values/sensor data |
| Stability | malformed corpus produces no panic, unwind across C ABI, or Wasm trap |
| Real device | exact shipping-equivalent SoC/OS evidence attached |

`contract-only` means the architecture and ceilings exist but target-device measurement is incomplete.

`measured` means latency/energy/footprint numbers have been collected but the complete qualification matrix is not necessarily satisfied.

`qualified` means every mandatory row above has evidence and passes.

## 13. Mandatory destructive tests

The qualification suite MUST include at least:

1. truncate a compiled `.xsp` at every byte position and confirm rejection;
2. flip one payload bit and confirm integrity failure;
3. corrupt each section offset/length class and confirm bounded failure;
4. request an unknown pack, unknown operation, wrong argument count, wrong semantic kind, malformed decimal, and invalid option;
5. call with minimum legal buffers and one-byte-too-small buffers;
6. reset after mount and prove dynamic registrations disappear;
7. freeze and prove registry mutation/unmount is blocked;
8. kill power/process during each A/B update phase and prove previous active set survives until activation;
9. execute the same corpus through fused and dynamic paths;
10. execute the same corpus through native and Wasm paths when Wasm ships;
11. fuzz model-facing Tiny JSON and pack bytes with malformed inputs and require no panic/trap;
12. run the offline corpus with radios disabled.

## 14. Integration handoff checklist

A device team receiving ExactScope should not need an oral explanation. The handoff package SHALL contain:

- `include/exactscope.h` and/or frozen Wasm ABI;
- exact runtime artifact and SHA-256;
- exact pack set and SHA-256 values;
- compatibility manifest;
- this wearable profile JSON;
- benchmark raw data and summary;
- energy measurement report;
- conformance corpus digest and result count;
- A/B update state-machine description;
- allowed telemetry schema;
- rollback procedure;
- known unsupported operations/features;
- one end-to-end sample from extracted values to rendered output.

If any of those are missing, the integration is not considered product-ready even if the calculation unit tests pass.

## 15. Explicit exclusions

This profile does not specify:

- camera ISP behavior;
- optical/display calibration;
- microphone beamforming;
- SLAM or spatial mapping;
- gaze/gesture recognition;
- battery cell design;
- thermal mechanical design;
- RF certification;
- model training or safety policy;
- cloud account/authentication systems.

Those systems may surround ExactScope, but none may change deterministic calculation semantics or bypass failure handling.

## 16. Claim discipline

The machine-readable profile begins at `claim_state: "contract-only"` and all physical-device evidence fields begin as `unmeasured`.

A future change to `measured` or `qualified` MUST include the corresponding immutable evidence artifact or compatibility record in the same release process. A numeric target in this specification is not evidence that the implementation already meets it.
