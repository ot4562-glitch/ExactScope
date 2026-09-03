#include "exactscope_wearable_bench.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct bench_fixture_v1 {
    uint64_t clock_ns;
    uint32_t clock_calls;
    uint32_t iterations;
    uint32_t emitted;
    uint32_t fail_iteration_at;
    uint32_t fail_emit_at;
    int reverse_clock;
} bench_fixture_v1;

static uint64_t fixture_now_ns(void* user) {
    bench_fixture_v1* fixture = (bench_fixture_v1*)user;
    ++fixture->clock_calls;
    if (fixture->reverse_clock && fixture->clock_calls == 2u) {
        return 500u;
    }
    fixture->clock_ns += 1000u;
    return fixture->clock_ns;
}

static xs_status fixture_iteration(void* user) {
    bench_fixture_v1* fixture = (bench_fixture_v1*)user;
    ++fixture->iterations;
    if (fixture->fail_iteration_at != 0u && fixture->iterations == fixture->fail_iteration_at) {
        return XS_STATUS_CONSTRAINT_VIOLATION;
    }
    return XS_STATUS_OK;
}

static xs_status fixture_emit(void* user, const xsw_bench_sample_v1* sample) {
    bench_fixture_v1* fixture = (bench_fixture_v1*)user;
    assert(sample != NULL);
    assert(sample->struct_size == (uint32_t)sizeof(*sample));
    assert(sample->metric == XSW_BENCH_METRIC_SCALAR_EVAL_V1);
    assert(sample->status == XS_STATUS_OK);
    assert(sample->sequence == fixture->emitted);
    assert(sample->duration_ns == 1000u);
    ++fixture->emitted;
    if (fixture->fail_emit_at != 0u && fixture->emitted == fixture->fail_emit_at) {
        return XS_STATUS_INTERNAL_ERROR;
    }
    return XS_STATUS_OK;
}

static xsw_bench_plan_v1 valid_plan(void) {
    xsw_bench_plan_v1 plan;
    memset(&plan, 0, sizeof(plan));
    plan.struct_size = (uint32_t)sizeof(plan);
    plan.metric = XSW_BENCH_METRIC_SCALAR_EVAL_V1;
    plan.expected_status = XS_STATUS_OK;
    plan.warmup_iterations = XSW_BENCH_MIN_WARMUP_ITERATIONS_V1;
    plan.sample_iterations = XSW_BENCH_MIN_SAMPLE_ITERATIONS_V1;
    return plan;
}

static xsw_bench_callbacks_v1 callbacks(bench_fixture_v1* fixture) {
    xsw_bench_callbacks_v1 result;
    memset(&result, 0, sizeof(result));
    result.struct_size = (uint32_t)sizeof(result);
    result.user = fixture;
    result.now_ns = fixture_now_ns;
    result.iteration = fixture_iteration;
    result.emit = fixture_emit;
    return result;
}

int main(void) {
    bench_fixture_v1 fixture;
    xsw_bench_plan_v1 plan;
    xsw_bench_callbacks_v1 cb;

    memset(&fixture, 0, sizeof(fixture));
    plan = valid_plan();
    cb = callbacks(&fixture);
    assert(xsw_bench_run(&plan, &cb) == XS_STATUS_OK);
    assert(fixture.iterations == 11000u);
    assert(fixture.emitted == 10000u);
    assert(fixture.clock_calls == 20000u);

    memset(&fixture, 0, sizeof(fixture));
    plan = valid_plan();
    plan.sample_iterations = XSW_BENCH_MIN_SAMPLE_ITERATIONS_V1 - 1u;
    cb = callbacks(&fixture);
    assert(xsw_bench_run(&plan, &cb) == XS_STATUS_RESOURCE_LIMIT);
    assert(fixture.iterations == 0u);

    memset(&fixture, 0, sizeof(fixture));
    plan = valid_plan();
    fixture.fail_iteration_at = 1u;
    cb = callbacks(&fixture);
    assert(xsw_bench_run(&plan, &cb) == XS_STATUS_CONSTRAINT_VIOLATION);
    assert(fixture.emitted == 0u);

    memset(&fixture, 0, sizeof(fixture));
    plan = valid_plan();
    fixture.fail_emit_at = 1u;
    cb = callbacks(&fixture);
    assert(xsw_bench_run(&plan, &cb) == XS_STATUS_INTERNAL_ERROR);
    assert(fixture.iterations == 1001u);
    assert(fixture.emitted == 1u);

    memset(&fixture, 0, sizeof(fixture));
    plan = valid_plan();
    plan.warmup_iterations = 0u;
    assert(xsw_bench_run(&plan, &cb) == XS_STATUS_RESOURCE_LIMIT);

    /* Use the legal warmup, then force the first measured end timestamp backwards. */
    memset(&fixture, 0, sizeof(fixture));
    plan = valid_plan();
    cb = callbacks(&fixture);
    fixture.reverse_clock = 1;
    /* reverse_clock triggers on the second clock call; warmups do not read the clock. */
    assert(xsw_bench_run(&plan, &cb) == XS_STATUS_INTERNAL_ERROR);
    assert(fixture.iterations == 1001u);
    assert(fixture.emitted == 0u);

    printf("wearable benchmark stream: PASS (1000 warmup + 10000 streamed samples)\n");
    return 0;
}
