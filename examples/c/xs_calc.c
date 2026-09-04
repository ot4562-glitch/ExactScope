#include "exactscope.h"
#include "exactscope_platform.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void xs_platform_panic_abort(void) {
    abort();
}

static int literal(const char *text, xs_plan_value_v1 *value) {
    memset(value, 0, sizeof(*value));
    value->struct_size = (uint32_t)sizeof(*value);
    value->value_kind = XS_PLAN_VALUE_LITERAL_V1;
    return xs_decimal_parse_ascii((const uint8_t *)text, (uint32_t)strlen(text),
                                  XS_SEMANTIC_NUMBER_V1, 0u, &value->literal) == XS_STATUS_OK;
}

static void previous(uint8_t index, xs_plan_value_v1 *value) {
    memset(value, 0, sizeof(*value));
    value->struct_size = (uint32_t)sizeof(*value);
    value->value_kind = XS_PLAN_VALUE_PREVIOUS_V1;
    value->previous_index = index;
}

static void step(xs_plan_step_v1 *value, uint8_t operation) {
    memset(value, 0, sizeof(*value));
    value->struct_size = (uint32_t)sizeof(*value);
    value->operation = operation;
    value->argument_count = 2u;
}

int main(void) {
    xs_config_v1 config;
    xs_context *context = NULL;
    uint8_t storage[8192];
    uintptr_t raw;
    uintptr_t aligned;
    uint32_t alignment;
    uint32_t available;
    xs_plan_step_v1 steps[3];
    xs_plan_result_v1 result;

    memset(&config, 0, sizeof(config));
    config.struct_size = (uint32_t)sizeof(config);
    config.abi_major = XS_ABI_MAJOR_V1;
    config.abi_minor = XS_ABI_MINOR_V1;
    config.max_packs = 1u;
    config.max_find_matches = 1u;
    config.max_vector_len = 1u;
    config.max_tinywire_frame = 512u;

    alignment = xs_context_align();
    raw = (uintptr_t)storage;
    aligned = (raw + alignment - 1u) & ~((uintptr_t)alignment - 1u);
    available = (uint32_t)(sizeof(storage) - (aligned - raw));
    if (xs_context_init((void *)aligned, available, &config, &context) != XS_STATUS_OK) {
        fputs("context init failed\n", stderr);
        return 1;
    }

    step(&steps[0], XS_PLAN_OP_MUL_V1);
    step(&steps[1], XS_PLAN_OP_SUB_V1);
    step(&steps[2], XS_PLAN_OP_DIV_V1);
    if (!literal("12", &steps[0].arguments[0]) ||
        !literal("7", &steps[0].arguments[1]) ||
        !literal("4", &steps[1].arguments[1]) ||
        !literal("5", &steps[2].arguments[1])) {
        fputs("literal parse failed\n", stderr);
        return 2;
    }
    previous(0u, &steps[1].arguments[0]);
    previous(1u, &steps[2].arguments[0]);

    memset(&result, 0, sizeof(result));
    result.struct_size = (uint32_t)sizeof(result);
    if (xs_calc(context, steps, 3u, &result) != XS_STATUS_OK ||
        result.status != XS_STATUS_OK || result.value.coefficient != 16 ||
        result.value.exponent != 0 || result.step_count != 3u) {
        fprintf(stderr, "xs_calc failed: status=%u step=%u\n", result.status, result.step_index);
        return 3;
    }

    puts("16");
    return 0;
}
