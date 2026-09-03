# ExactScope Wearable Benchmark v0.1

Status: **normative target-device latency evidence procedure** for [`wearable-edge-v0.1`](WEARABLE_EDGE_PROFILE_V0_1.md).

This procedure defines how a device team measures ExactScope lookup, scalar evaluation, and dynamic-pack mount latency without changing the calculation implementation or accumulating a large sample array inside the wearable runtime.

The target harness is [`../adapters/wearable/exactscope_wearable_bench.[ch]`](../adapters/wearable/exactscope_wearable_bench.h). The offline reducer is [`../tools/reduce_wearable_latency.py`](../tools/reduce_wearable_latency.py).

## 1. Design goals

The benchmark path MUST:

- measure the exact shipping operation path;
- allocate no heap inside the reference harness;
- create no thread, timer, file, socket, or network dependency;
- perform at least 1,000 untimed warm-up iterations;
- perform at least 10,000 measured iterations;
- timestamp only the operation under test;
- move sample logging/transport after the end timestamp;
- stream samples one at a time rather than storing 10,000 durations in ExactScope memory;
- reduce raw samples offline with a frozen deterministic percentile rule;
- round nanoseconds upward when reporting integer microseconds.

This separation prevents evidence collection from silently violating the 16 KiB wearable mutable-runtime budget.

## 2. Metrics

The C harness defines three stable metric IDs:

| C ID | Evidence name | Timed operation |
|---|---|---|
| `XSW_BENCH_METRIC_LOOKUP_V1` | `lookup` | exact canonical operation lookup only |
| `XSW_BENCH_METRIC_SCALAR_EVAL_V1` | `scalar_eval` | one already-resolved typed scalar evaluation only |
| `XSW_BENCH_METRIC_PACK_MOUNT_256K_V1` | `pack_mount_256k` | mount/validation of the designated 256 KiB qualification pack fixture |

Do not combine perception/model/UI work into these metrics.

For example, a glasses interaction may take hundreds of milliseconds end-to-end while ExactScope scalar evaluation is below 1 ms. These are different product metrics and must be reported separately.

## 3. Target clock callback

The product supplies:

```c
uint64_t now_ns(void* user);
```

The callback MUST represent a monotonic target-device clock suitable for interval measurement.

Requirements:

- units are nanoseconds;
- the clock cannot move backward under normal operation;
- wall-clock/NTP/user-time changes do not affect it;
- the clock source is named in `wearable-qualification-record.json`;
- clock read overhead is stable enough for the target durations or is characterized by the product performance team.

If the end timestamp is numerically below the start timestamp, the harness aborts with `INTERNAL_ERROR` rather than producing a wrapped/negative duration.

## 4. Iteration callback

The product supplies exactly one operation under test through:

```c
xs_status iteration(void* user);
```

The benchmark plan records the expected stable `xs_status`.

For normal performance qualification the expected status is `OK`.

If any warm-up or measured iteration returns an unexpected status, the run aborts. A failed computation is not silently included as a fast sample.

### 4.1 Lookup iteration

A lookup iteration SHOULD call only the exact lookup path with a fixed already-resident key.

Do not include:

- model intent extraction;
- UTF-8 generation outside the lookup call;
- storage reads;
- result rendering.

### 4.2 Scalar-eval iteration

The iteration SHOULD reuse already-constructed typed argument/output structures and invoke the exact shipping evaluation boundary.

The timed interval may include the C wrapper boundary when that is the shipping path. It SHOULD NOT include setup that a production request does not repeat, such as context creation or pack mount.

### 4.3 Pack-mount iteration

The dynamic-pack mount benchmark is measured using a designated qualification pack of 256 KiB or the nearest canonical fixture defined by the product team.

Each measured mount must start from a clean eligible context/registry state. If teardown/context reset is required between measurements, perform that work outside the timed interval unless the product's mount latency requirement explicitly includes it.

The raw evidence must identify the exact pack digest used.

## 5. Warm-up

`xsw_bench_run` enforces at least:

```text
warmup_iterations >= 1000
```

Warm-up calls execute `iteration()` but do not read the benchmark clock and do not emit samples.

Warm-up exists to reduce first-touch, page-in, branch/cache, JIT/runtime initialization, and frequency-ramp artifacts where applicable. It is not permission to hide a cold-start product requirement; cold-start should be measured separately if relevant to the product.

## 6. Measured sample loop

`xsw_bench_run` enforces at least:

```text
sample_iterations >= 10000
```

For each sequence number `i`:

```text
start_ns = now_ns()
status   = iteration()
end_ns   = now_ns()
verify expected status
verify end_ns >= start_ns
duration_ns = end_ns - start_ns
emit(sample i)
```

The emitter call is explicitly **after** `end_ns`.

This means USB/debug transport, CSV formatting, file writes, or host collection latency performed by the product emitter is not part of the ExactScope duration.

## 7. O(1) reference memory

The reference harness keeps only:

- loop counters;
- two timestamps;
- one `xsw_bench_sample_v1` record;
- callback pointers/plan state supplied by the caller.

It does not allocate or retain the 10,000-sample corpus.

A product may choose to buffer samples outside the ExactScope memory budget, but the qualification report must document that choice and ensure it does not perturb measured execution materially.

## 8. Sample structure

Each emitted in-memory sample contains:

```text
struct_size
sequence
metric
status
duration_ns
```

Reserved fields are zero.

The emitter SHOULD convert this to the canonical evidence CSV without changing numeric values.

## 9. Canonical CSV

The raw latency evidence format is UTF-8 CSV with exactly this header:

```text
sequence,metric,duration_ns,status
```

Example:

```text
sequence,metric,duration_ns,status
0,scalar_eval,102000,0
1,scalar_eval,98000,0
2,scalar_eval,105000,0
```

Rules:

- sequence starts at 0 and increases by exactly 1;
- every row in one file has the same metric name;
- metric is `lookup`, `scalar_eval`, or `pack_mount_256k`;
- `duration_ns` is a base-10 nonnegative integer;
- `status` is base-10 and must be `0` for the standard successful performance corpus;
- no extra/missing columns;
- at least 10,000 rows for qualification;
- warm-up rows are not written to this file.

The product evidence package SHOULD preserve the raw file under a content digest.

## 10. Offline reduction

Run:

```text
python tools/reduce_wearable_latency.py samples.csv \
  --metric scalar_eval \
  --warmup-iterations 1000
```

The reducer verifies:

- canonical CSV header;
- contiguous sequence;
- metric identity;
- status = OK for every row;
- bounded/nonnegative duration;
- minimum sample count;
- minimum warm-up count supplied by the run metadata.

It emits a compact JSON summary containing:

```text
metric
state
warmup_iterations
sample_iterations
p50_us
p95_us
p99_us
max_us
```

The `state` is recomputed from the current wearable profile targets, not copied from the device.

## 11. Nanosecond-to-microsecond conversion

Qualification fields are integer microseconds. Raw samples remain nanoseconds.

For every sample:

```text
reported_us = ceil(duration_ns / 1000)
            = (duration_ns + 999) // 1000
```

Examples:

```text
0 ns    -> 0 us
1 ns    -> 1 us
999 ns  -> 1 us
1000 ns -> 1 us
1001 ns -> 2 us
```

The upward conversion prevents sub-microsecond fractions from being truncated into a lower qualification bucket.

## 12. Percentile definition

Percentiles use the **nearest-rank** method over the sorted integer-microsecond samples.

For percentile `p` in `{50,95,99}` and sample count `N`:

```text
rank = ceil(p * N / 100)
value = sorted_samples[rank - 1]
```

No interpolation is performed.

For exactly 10,000 samples containing integer microseconds `1..10000`, the required reducer result is:

```text
p50 = 5000 us
p95 = 9500 us
p99 = 9900 us
max = 10000 us
```

This vector is built into the reducer self-test.

## 13. Pass/fail thresholds

The reducer uses the current canonical wearable profile.

### Lookup

```text
p99 <= 250 us
```

### Scalar evaluation

```text
p50 <= 250 us
p99 <= 1000 us
```

### 256 KiB dynamic pack mount

```text
p99 <= 10000 us
```

An output `state: "pass"` means the measured raw corpus meets the applicable profile target. It does not by itself qualify energy, footprint, update recovery, privacy, or the complete product.

## 14. Frequency and thermal control

The physical test record MUST state device power/performance mode and thermal state.

Recommended procedure:

1. bring device to the product-defined starting temperature band;
2. apply the shipping CPU governor/performance policy;
3. keep unrelated workloads quiescent;
4. record battery voltage and display/radio state;
5. perform warm-up;
6. perform sample run without changing power mode;
7. record end thermal state;
8. repeat if the product team's statistical policy requires independent runs.

Do not force a non-shipping maximum-frequency mode solely to obtain a passing qualification number unless that mode is the actual product configuration being qualified.

## 15. Scheduler/preemption policy

Normal target scheduling effects remain part of the measured call latency unless the product architecture guarantees exclusive execution in production.

The test harness should not discard slow samples merely because a preemption occurred. p99 exists specifically to reflect tail behavior under the qualified configuration.

If the product requires a separate isolated-core microbenchmark, report it as supplementary evidence, not as a replacement for the shipping-path corpus.

## 16. Model/perception boundary

For glasses/AI use, measure ExactScope separately from:

```text
camera -> OCR/vision -> model intent -> ExactScope -> renderer
```

The complete interaction latency SHOULD also be measured by the product, but it is not the same as the ExactScope p99 target.

This prevents optimization work from being misdirected: a 500 ms model delay cannot be fixed by shaving 100 us from a deterministic arithmetic call, and a 5 ms ExactScope regression should not be hidden inside a 500 ms end-to-end average.

## 17. Qualification record transfer

After reducing the three applicable raw corpora, copy their summaries into the `latency` section of `wearable-qualification-record.json` for the exact artifact/device run.

The qualification validator independently checks the same profile thresholds again. Therefore:

- raw reducer;
- qualification record;
- wearable profile

must all agree before `qualified` status is possible.

## 18. Test-only nature of the harness

The benchmark harness and raw sample emitter are qualification/development components. They do not need to be linked into the shipping production runtime.

The production ExactScope reference host remains free of clocks/logging/transport. A vendor that ships benchmark hooks must secure/disable them according to its own product policy and must not expose user data through the evidence channel.
