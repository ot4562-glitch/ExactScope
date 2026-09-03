#include "exactscope_wearable_ref.h"
#include "exactscope_wearable_ab.h"

static_assert(XSW_REF_MAX_CONTEXT_BYTES_V1 == 4096u, "wearable context budget drift");
static_assert(XSW_REF_MAX_EVAL_SCRATCH_BYTES_V1 == 4096u, "wearable scratch budget drift");
static_assert(XSW_REF_MAX_PACK_MOUNT_ARENA_BYTES_V1 == 0u, "wearable mount arena must stay zero");
static_assert(XSW_REF_MAX_PACK_BYTES_V1 == 262144u, "wearable per-pack budget drift");
static_assert(XSW_REF_MAX_TOTAL_PACK_BYTES_V1 == 524288u, "wearable total-pack budget drift");
static_assert(XSW_AB_RECORD_COPY_COUNT_V1 == 2u, "wearable journal copy-count drift");
static_assert(XSW_AB_RECORD_BYTES_V1 == 96u, "wearable journal record-size drift");

int exactscope_wearable_reference_cpp11_smoke() {
    xsw_ref_host_v1 host{};
    xsw_ref_telemetry_v1 telemetry{};

    host.struct_size = static_cast<uint32_t>(sizeof(host));
    telemetry.struct_size = static_cast<uint32_t>(sizeof(telemetry));

    return static_cast<int>(
        host.struct_size
        + telemetry.struct_size
        + XSW_REF_MAX_MOUNTED_PACKS_V1
        + XSW_REF_MAX_VECTOR_LEN_V1);
}
