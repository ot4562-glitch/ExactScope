#include "exactscope.h"
#include "exactscope_platform.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void xs_platform_panic_abort(void) {
    abort();
}

static int parse_value(const char* text, uint8_t semantic, xs_decimal_v1* out) {
    return xs_decimal_parse_ascii(
        (const uint8_t*)text,
        (uint32_t)strlen(text),
        semantic,
        0u,
        out) == XS_STATUS_OK;
}

int main(void) {
    xs_config_v1 config;
    xs_context* context = NULL;
    uint8_t context_storage[8192];
    uintptr_t raw;
    uintptr_t aligned;
    uint32_t alignment;
    uint32_t required;
    uint32_t available;
    uint16_t pack_slot = 0u;
    uint32_t operation_id = 0u;
    uint16_t revision = 0u;
    xs_decimal_v1 values[4];
    xs_value_ref_v1 args[4];
    xs_eval_options_v1 options;
    xs_result_v1 result;
    const char* key = "econ.ped.mid";
    const char* texts[4] = {"10000", "12000", "100", "80"};
    const uint8_t semantics[4] = {
        XS_SEMANTIC_PRICE_V1,
        XS_SEMANTIC_PRICE_V1,
        XS_SEMANTIC_QUANTITY_V1,
        XS_SEMANTIC_QUANTITY_V1,
    };
    unsigned i;

    memset(&config, 0, sizeof(config));
    config.struct_size = (uint32_t)sizeof(config);
    config.abi_major = XS_ABI_MAJOR_V1;
    config.abi_minor = XS_ABI_MINOR_V1;
    config.max_packs = 4u;
    config.max_find_matches = 5u;
    config.max_vector_len = 256u;
    config.flags = XS_CONFIG_ENABLE_DISCOVERY_V1;
    config.max_tinywire_frame = 4096u;

    if (xs_abi_version() != XS_ABI_VERSION_V1) {
        fprintf(stderr, "unexpected ABI version\n");
        return 1;
    }

    alignment = xs_context_align();
    required = xs_context_size(&config);
    if (alignment == 0u || required == 0u || required > sizeof(context_storage)) {
        fprintf(stderr, "invalid context requirements\n");
        return 2;
    }
    raw = (uintptr_t)context_storage;
    aligned = (raw + (uintptr_t)(alignment - 1u)) & ~((uintptr_t)alignment - 1u);
    available = (uint32_t)(sizeof(context_storage) - (aligned - raw));
    if (xs_context_init((void*)aligned, available, &config, &context) != XS_STATUS_OK) {
        fprintf(stderr, "context init failed\n");
        return 3;
    }
    if (xs_registry_freeze(context) != XS_STATUS_OK) {
        fprintf(stderr, "registry freeze failed\n");
        return 4;
    }
    if (xs_lookup(
            context,
            (const uint8_t*)key,
            (uint32_t)strlen(key),
            &pack_slot,
            &operation_id,
            &revision) != XS_STATUS_OK) {
        fprintf(stderr, "lookup failed\n");
        return 5;
    }

    memset(values, 0, sizeof(values));
    memset(args, 0, sizeof(args));
    for (i = 0u; i < 4u; ++i) {
        if (!parse_value(texts[i], semantics[i], &values[i])) {
            fprintf(stderr, "decimal parse failed\n");
            return 6;
        }
        args[i].struct_size = (uint32_t)sizeof(args[i]);
        args[i].value_kind = XS_VALUE_SCALAR_V1;
        args[i].values = &values[i];
        args[i].value_count = 1u;
    }

    memset(&options, 0, sizeof(options));
    options.struct_size = (uint32_t)sizeof(options);
    options.output_scale = XS_USE_OPERATION_SCALE_V1;
    options.rounding_mode = XS_USE_OPERATION_ROUNDING_V1;
    options.flags = XS_EVAL_REQUIRE_CLASSIFICATION_V1;

    memset(&result, 0, sizeof(result));
    result.struct_size = (uint32_t)sizeof(result);
    if (xs_eval(
            context,
            pack_slot,
            operation_id,
            args,
            4u,
            &options,
            NULL,
            0u,
            &result) != XS_STATUS_OK) {
        fprintf(stderr, "evaluation call failed\n");
        return 7;
    }
    if (result.status != XS_STATUS_OK || result.value_count != 1u) {
        fprintf(stderr, "evaluation status failed\n");
        return 8;
    }
    if (result.values[0].coefficient != -1222222 || result.values[0].exponent != -6) {
        fprintf(stderr, "unexpected result value\n");
        return 9;
    }
    if (result.classification_id != 3u || operation_id != 301u || revision != 1u) {
        fprintf(stderr, "unexpected operation/classification identity\n");
        return 10;
    }

    printf("PASS native-smoke op=%s value=-1.222222 classification=elastic\n", key);
    return 0;
}
