#include "exactscope_wearable_ref.h"
#include "exactscope_platform.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void XS_CALL xs_platform_panic_abort(void) {
    abort();
}

#define CHECK_STATUS(expr, expected) do { \
    const xs_status status__ = (expr); \
    if (status__ != (expected)) { \
        fprintf(stderr, "%s:%d: status %u != %u\n", __FILE__, __LINE__, \
                (unsigned)status__, (unsigned)(expected)); \
        return 1; \
    } \
} while (0)

#define CHECK_TRUE(expr) do { \
    if (!(expr)) { \
        fprintf(stderr, "%s:%d: check failed: %s\n", __FILE__, __LINE__, #expr); \
        return 1; \
    } \
} while (0)

typedef union xsw_context_storage_v1 {
    uint64_t align_u64;
    void* align_ptr;
    uint8_t bytes[XSW_REF_MAX_CONTEXT_BYTES_V1];
} xsw_context_storage_v1;

static xs_value_ref_v1 scalar_ref(const xs_decimal_v1* value) {
    xs_value_ref_v1 ref;
    memset(&ref, 0, sizeof(ref));
    ref.struct_size = (uint32_t)sizeof(ref);
    ref.value_kind = XS_VALUE_SCALAR_V1;
    ref.values = value;
    ref.value_count = 1u;
    return ref;
}

int main(void) {
    static const uint8_t operation_key[] = "econ.ped.mid";
    static const uint8_t query[] = "midpoint price elasticity";
    xsw_context_storage_v1 context_storage;
    xsw_ref_host_v1 host;
    xsw_ref_telemetry_v1 telemetry;
    xs_decimal_v1 values[4];
    xs_decimal_v1 rejected;
    xs_value_ref_v1 args[4];
    xs_eval_options_v1 options;
    xs_result_v1 result;
    xs_match_v1 match;
    uint32_t required_context_bytes = 0u;
    uint16_t pack_slot = 0u;
    uint32_t operation_id = 0u;
    uint16_t operation_revision = 0u;
    uint16_t match_count = 0u;
    uint32_t context_align;

    memset(&context_storage, 0, sizeof(context_storage));
    memset(&host, 0, sizeof(host));
    host.struct_size = (uint32_t)sizeof(host);

    CHECK_TRUE(xs_abi_version() == XS_ABI_VERSION_V1);
    context_align = xs_context_align();
    CHECK_TRUE(context_align > 0u);
    CHECK_TRUE(context_align <= (uint32_t)sizeof(uint64_t));
    CHECK_TRUE(((uintptr_t)context_storage.bytes % context_align) == 0u);

    CHECK_STATUS(
        xsw_ref_init(
            &host,
            XSW_REF_MODE_FUSED_DISCOVERY_V1,
            context_storage.bytes,
            (uint32_t)sizeof(context_storage.bytes),
            &required_context_bytes),
        XS_STATUS_OK);
    CHECK_TRUE(required_context_bytes > 0u);
    CHECK_TRUE(required_context_bytes <= XSW_REF_MAX_CONTEXT_BYTES_V1);
    CHECK_TRUE(host.state == XSW_REF_STATE_FROZEN_V1);

    CHECK_STATUS(
        xsw_ref_lookup(
            &host,
            operation_key,
            (uint32_t)(sizeof(operation_key) - 1u),
            &pack_slot,
            &operation_id,
            &operation_revision),
        XS_STATUS_OK);
    CHECK_TRUE(pack_slot == 1u);
    CHECK_TRUE(operation_id == 301u);
    CHECK_TRUE(operation_revision == 1u);

    memset(&match, 0, sizeof(match));
    match.struct_size = (uint32_t)sizeof(match);
    CHECK_STATUS(
        xsw_ref_find(
            &host,
            query,
            (uint32_t)(sizeof(query) - 1u),
            &match,
            1u,
            &match_count),
        XS_STATUS_OK);
    CHECK_TRUE(match_count == 1u);
    CHECK_TRUE(match.pack_slot == pack_slot);
    CHECK_TRUE(match.operation_id == operation_id);
    CHECK_TRUE(match.operation_revision == operation_revision);

    CHECK_STATUS(
        xs_decimal_parse_ascii(
            (const uint8_t*)"10000",
            5u,
            XS_SEMANTIC_PRICE_V1,
            0u,
            &values[0]),
        XS_STATUS_OK);
    CHECK_STATUS(
        xs_decimal_parse_ascii(
            (const uint8_t*)"12000",
            5u,
            XS_SEMANTIC_PRICE_V1,
            0u,
            &values[1]),
        XS_STATUS_OK);
    CHECK_STATUS(
        xs_decimal_parse_ascii(
            (const uint8_t*)"100",
            3u,
            XS_SEMANTIC_QUANTITY_V1,
            0u,
            &values[2]),
        XS_STATUS_OK);
    CHECK_STATUS(
        xs_decimal_parse_ascii(
            (const uint8_t*)"80",
            2u,
            XS_SEMANTIC_QUANTITY_V1,
            0u,
            &values[3]),
        XS_STATUS_OK);
    CHECK_TRUE(values[0].coefficient == 1 && values[0].exponent == 4);
    CHECK_TRUE(values[1].coefficient == 12 && values[1].exponent == 3);
    CHECK_TRUE(values[2].coefficient == 1 && values[2].exponent == 2);
    CHECK_TRUE(values[3].coefficient == 8 && values[3].exponent == 1);

    memset(&rejected, 0x7f, sizeof(rejected));
    CHECK_STATUS(
        xs_decimal_parse_ascii(
            (const uint8_t*)"5%",
            2u,
            XS_SEMANTIC_RATE_PERCENT_V1,
            0u,
            &rejected),
        XS_STATUS_INVALID_DECIMAL);
    CHECK_TRUE(rejected.coefficient == 0);
    CHECK_TRUE(rejected.exponent == 0);
    CHECK_TRUE(rejected.semantic_kind == 0u);
    CHECK_TRUE(rejected.unit_id == 0u);
    CHECK_TRUE(rejected.flags == 0u);

    args[0] = scalar_ref(&values[0]);
    args[1] = scalar_ref(&values[1]);
    args[2] = scalar_ref(&values[2]);
    args[3] = scalar_ref(&values[3]);

    memset(&options, 0, sizeof(options));
    options.struct_size = (uint32_t)sizeof(options);
    options.output_scale = XS_USE_OPERATION_SCALE_V1;
    options.rounding_mode = XS_USE_OPERATION_ROUNDING_V1;
    options.flags = XS_EVAL_REQUIRE_CLASSIFICATION_V1;

    memset(&result, 0, sizeof(result));
    result.struct_size = (uint32_t)sizeof(result);
    CHECK_STATUS(
        xsw_ref_eval(
            &host,
            pack_slot,
            operation_id,
            args,
            4u,
            &options,
            NULL,
            0u,
            &result),
        XS_STATUS_OK);
    CHECK_TRUE(result.status == XS_STATUS_OK);
    CHECK_TRUE(result.value_count == 1u);
    CHECK_TRUE(result.classification_id == 3u);
    CHECK_TRUE(result.pack_slot == 1u);
    CHECK_TRUE(result.operation_id == 301u);
    CHECK_TRUE(result.operation_revision == 1u);
    CHECK_TRUE(result.values[0].coefficient == -1222222);
    CHECK_TRUE(result.values[0].exponent == -6);
    CHECK_TRUE(result.values[0].semantic_kind == XS_SEMANTIC_ELASTICITY_V1);

    memset(&telemetry, 0, sizeof(telemetry));
    telemetry.struct_size = (uint32_t)sizeof(telemetry);
    CHECK_STATUS(xsw_ref_make_telemetry(&result, 900u, &telemetry), XS_STATUS_OK);
    CHECK_TRUE(telemetry.status == XS_STATUS_OK);
    CHECK_TRUE(telemetry.pack_slot == 1u);
    CHECK_TRUE(telemetry.operation_id == 301u);
    CHECK_TRUE(telemetry.duration_bucket == XSW_REF_DURATION_LE_1_MS_V1);

    {
        static const uint8_t deflator_key[] = "econ.gdp.deflator100";
        CHECK_STATUS(
            xsw_ref_lookup(
                &host,
                deflator_key,
                (uint32_t)(sizeof(deflator_key) - 1u),
                &pack_slot,
                &operation_id,
                &operation_revision),
            XS_STATUS_OK);
        CHECK_TRUE(pack_slot == 1u);
        CHECK_TRUE(operation_id == 401u);
        CHECK_TRUE(operation_revision == 1u);

        CHECK_STATUS(
            xs_decimal_parse_ascii(
                (const uint8_t*)"120",
                3u,
                XS_SEMANTIC_CURRENCY_AMOUNT_V1,
                7u,
                &values[0]),
            XS_STATUS_OK);
        CHECK_STATUS(
            xs_decimal_parse_ascii(
                (const uint8_t*)"100",
                3u,
                XS_SEMANTIC_CURRENCY_AMOUNT_V1,
                7u,
                &values[1]),
            XS_STATUS_OK);
        args[0] = scalar_ref(&values[0]);
        args[1] = scalar_ref(&values[1]);
        options.flags = 0u;
        memset(&result, 0, sizeof(result));
        result.struct_size = (uint32_t)sizeof(result);
        CHECK_STATUS(
            xsw_ref_eval(
                &host,
                pack_slot,
                operation_id,
                args,
                2u,
                &options,
                NULL,
                0u,
                &result),
            XS_STATUS_OK);
        CHECK_TRUE(result.status == XS_STATUS_OK);
        CHECK_TRUE(result.operation_id == 401u);
        CHECK_TRUE(result.classification_id == 0u);
        CHECK_TRUE(result.values[0].coefficient == 12);
        CHECK_TRUE(result.values[0].exponent == 1);
        CHECK_TRUE(result.values[0].semantic_kind == XS_SEMANTIC_INDEX_V1);
    }

    puts("ExactScope wearable native C ABI runtime test: PASS");
    return 0;
}
