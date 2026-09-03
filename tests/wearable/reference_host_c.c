#include "exactscope_wearable_ref.h"

#if XSW_REF_MAX_CONTEXT_BYTES_V1 != 4096u
#error "wearable context budget drift"
#endif

#if XSW_REF_MAX_EVAL_SCRATCH_BYTES_V1 != 4096u
#error "wearable scratch budget drift"
#endif

#if XSW_REF_MAX_PACK_MOUNT_ARENA_BYTES_V1 != 0u
#error "wearable v0.1 must remain zero-copy at pack mount"
#endif

#if XSW_REF_MAX_PACK_BYTES_V1 != 262144u
#error "wearable per-pack budget drift"
#endif

#if XSW_REF_MAX_TOTAL_PACK_BYTES_V1 != 524288u
#error "wearable total-pack budget drift"
#endif

int exactscope_wearable_reference_c99_smoke(void) {
    xsw_ref_host_v1 host = {0};
    xsw_ref_telemetry_v1 telemetry = {0};
    xs_result_v1 result = {0};

    host.struct_size = (uint32_t)sizeof(host);
    telemetry.struct_size = (uint32_t)sizeof(telemetry);
    result.struct_size = (uint32_t)sizeof(result);

    return (int)(
        host.struct_size
        + telemetry.struct_size
        + result.struct_size
        + xsw_ref_host_size()
        + XSW_REF_MAX_VECTOR_LEN_V1);
}
