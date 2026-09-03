#ifndef EXACTSCOPE_WEARABLE_BENCH_H_INCLUDED
#define EXACTSCOPE_WEARABLE_BENCH_H_INCLUDED

#include <stdint.h>

#include "exactscope.h"

#if defined(__cplusplus)
extern "C" {
#endif

#define XSW_BENCH_METRIC_LOOKUP_V1 1u
#define XSW_BENCH_METRIC_SCALAR_EVAL_V1 2u
#define XSW_BENCH_METRIC_PACK_MOUNT_256K_V1 3u

#define XSW_BENCH_MIN_WARMUP_ITERATIONS_V1 1000u
#define XSW_BENCH_MIN_SAMPLE_ITERATIONS_V1 10000u
#define XSW_BENCH_MAX_ITERATIONS_V1 1000000u

/*
 * Monotonic target clock in nanoseconds. Qualification must document the clock
 * source and ensure it is not wall-clock time subject to backwards adjustment.
 */
typedef uint64_t (*xsw_bench_now_ns_fn_v1)(void* user);

/* Executes exactly one operation under test. */
typedef xs_status (*xsw_bench_iteration_fn_v1)(void* user);

/*
 * One measured sample. The emitter is invoked only after end timestamp capture,
 * so logging/transport overhead is outside duration_ns.
 */
typedef struct xsw_bench_sample_v1 {
    uint32_t struct_size;
    uint32_t sequence;
    uint8_t metric;
    uint8_t reserved0;
    uint16_t status;
    uint64_t duration_ns;
    uint32_t reserved[2];
} xsw_bench_sample_v1;

typedef xs_status (*xsw_bench_emit_fn_v1)(
    void* user,
    const xsw_bench_sample_v1* sample);

typedef struct xsw_bench_plan_v1 {
    uint32_t struct_size;
    uint8_t metric;
    uint8_t reserved0;
    uint16_t expected_status;
    uint32_t warmup_iterations;
    uint32_t sample_iterations;
    uint32_t reserved[3];
} xsw_bench_plan_v1;

typedef struct xsw_bench_callbacks_v1 {
    uint32_t struct_size;
    void* user;
    xsw_bench_now_ns_fn_v1 now_ns;
    xsw_bench_iteration_fn_v1 iteration;
    xsw_bench_emit_fn_v1 emit;
    uint32_t reserved[4];
} xsw_bench_callbacks_v1;

/*
 * Runs a qualification measurement with O(1) ExactScope-side memory.
 *
 * Warmup iterations are not timed or emitted. Each measured iteration is timed
 * around iteration() only. Samples are streamed one-by-one through emit().
 * The function allocates no memory and owns no clock, file, socket, or thread.
 */
xs_status xsw_bench_run(
    const xsw_bench_plan_v1* plan,
    const xsw_bench_callbacks_v1* callbacks) XS_NOEXCEPT;

#if defined(__cplusplus)
} /* extern "C" */
#endif

#endif /* EXACTSCOPE_WEARABLE_BENCH_H_INCLUDED */
