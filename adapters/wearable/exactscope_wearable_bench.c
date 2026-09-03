#include "exactscope_wearable_bench.h"

#include <stddef.h>
#include <string.h>

static int xsw_bench_metric_valid(uint8_t metric) {
    return metric == XSW_BENCH_METRIC_LOOKUP_V1
        || metric == XSW_BENCH_METRIC_SCALAR_EVAL_V1
        || metric == XSW_BENCH_METRIC_PACK_MOUNT_256K_V1;
}

static xs_status xsw_bench_validate_plan(const xsw_bench_plan_v1* plan) {
    if (plan == NULL || plan->struct_size < (uint32_t)sizeof(*plan)) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (!xsw_bench_metric_valid(plan->metric) || plan->reserved0 != 0u
        || plan->reserved[0] != 0u || plan->reserved[1] != 0u || plan->reserved[2] != 0u) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (plan->warmup_iterations < XSW_BENCH_MIN_WARMUP_ITERATIONS_V1
        || plan->sample_iterations < XSW_BENCH_MIN_SAMPLE_ITERATIONS_V1
        || plan->warmup_iterations > XSW_BENCH_MAX_ITERATIONS_V1
        || plan->sample_iterations > XSW_BENCH_MAX_ITERATIONS_V1) {
        return XS_STATUS_RESOURCE_LIMIT;
    }
    return XS_STATUS_OK;
}

static xs_status xsw_bench_validate_callbacks(const xsw_bench_callbacks_v1* callbacks) {
    if (callbacks == NULL || callbacks->struct_size < (uint32_t)sizeof(*callbacks)) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (callbacks->now_ns == NULL || callbacks->iteration == NULL || callbacks->emit == NULL) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (callbacks->reserved[0] != 0u || callbacks->reserved[1] != 0u
        || callbacks->reserved[2] != 0u || callbacks->reserved[3] != 0u) {
        return XS_STATUS_INVALID_REQUEST;
    }
    return XS_STATUS_OK;
}

static xs_status xsw_bench_check_iteration_status(xs_status actual, xs_status expected) {
    if (actual == expected) {
        return XS_STATUS_OK;
    }
    if (actual != XS_STATUS_OK) {
        return actual;
    }
    return XS_STATUS_INTERNAL_ERROR;
}

xs_status xsw_bench_run(
    const xsw_bench_plan_v1* plan,
    const xsw_bench_callbacks_v1* callbacks) XS_NOEXCEPT {
    uint32_t index;
    xs_status status;

    status = xsw_bench_validate_plan(plan);
    if (status != XS_STATUS_OK) {
        return status;
    }
    status = xsw_bench_validate_callbacks(callbacks);
    if (status != XS_STATUS_OK) {
        return status;
    }

    for (index = 0u; index < plan->warmup_iterations; ++index) {
        xs_status iteration_status = callbacks->iteration(callbacks->user);
        status = xsw_bench_check_iteration_status(iteration_status, plan->expected_status);
        if (status != XS_STATUS_OK) {
            return status;
        }
    }

    for (index = 0u; index < plan->sample_iterations; ++index) {
        xsw_bench_sample_v1 sample;
        uint64_t start_ns = callbacks->now_ns(callbacks->user);
        xs_status iteration_status = callbacks->iteration(callbacks->user);
        uint64_t end_ns = callbacks->now_ns(callbacks->user);

        status = xsw_bench_check_iteration_status(iteration_status, plan->expected_status);
        if (status != XS_STATUS_OK) {
            return status;
        }
        if (end_ns < start_ns) {
            return XS_STATUS_INTERNAL_ERROR;
        }

        memset(&sample, 0, sizeof(sample));
        sample.struct_size = (uint32_t)sizeof(sample);
        sample.sequence = index;
        sample.metric = plan->metric;
        sample.status = iteration_status;
        sample.duration_ns = end_ns - start_ns;

        status = callbacks->emit(callbacks->user, &sample);
        if (status != XS_STATUS_OK) {
            return status;
        }
    }

    return XS_STATUS_OK;
}
