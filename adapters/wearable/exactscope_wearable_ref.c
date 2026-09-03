#include "exactscope_wearable_ref.h"

#include <stddef.h>
#include <string.h>

static int xsw_ref_host_record_valid(const xsw_ref_host_v1* host) {
    return host != NULL && host->struct_size >= (uint32_t)sizeof(*host) && host->context != NULL;
}

static int xsw_ref_find_pack_index(const xsw_ref_host_v1* host, uint16_t pack_slot) {
    uint32_t index;
    for (index = 0u; index < XSW_REF_MAX_MOUNTED_PACKS_V1; ++index) {
        if (host->pack_slots[index] == pack_slot) {
            return (int)index;
        }
    }
    return -1;
}

static int xsw_ref_find_free_pack_index(const xsw_ref_host_v1* host) {
    uint32_t index;
    for (index = 0u; index < XSW_REF_MAX_MOUNTED_PACKS_V1; ++index) {
        if (host->pack_slots[index] == 0u) {
            return (int)index;
        }
    }
    return -1;
}

static void xsw_ref_clear_pack_tracking(xsw_ref_host_v1* host) {
    uint32_t index;
    host->mounted_pack_count = 0u;
    host->mounted_pack_bytes = 0u;
    for (index = 0u; index < XSW_REF_MAX_MOUNTED_PACKS_V1; ++index) {
        host->pack_slots[index] = 0u;
        host->pack_lengths[index] = 0u;
    }
}

static uint8_t xsw_ref_duration_bucket(uint32_t duration_us) {
    if (duration_us <= XSW_REF_TARGET_SCALAR_EVAL_P50_US_V1) {
        return XSW_REF_DURATION_LE_250_US_V1;
    }
    if (duration_us <= XSW_REF_TARGET_SCALAR_EVAL_P99_US_V1) {
        return XSW_REF_DURATION_LE_1_MS_V1;
    }
    if (duration_us <= XSW_REF_TARGET_PACK_MOUNT_256K_P99_US_V1) {
        return XSW_REF_DURATION_LE_10_MS_V1;
    }
    return XSW_REF_DURATION_GT_10_MS_V1;
}

uint32_t xsw_ref_host_size(void) XS_NOEXCEPT {
    return (uint32_t)sizeof(xsw_ref_host_v1);
}

xs_status xsw_ref_init(
    xsw_ref_host_v1* host,
    uint8_t mode,
    void* context_memory,
    uint32_t context_memory_len,
    uint32_t* required_context_bytes) XS_NOEXCEPT {
    xs_config_v1 config;
    xs_context* context;
    uint32_t caller_struct_size;
    uint32_t required;
    xs_status status;

    if (host == NULL || required_context_bytes == NULL) {
        return XS_STATUS_INVALID_REQUEST;
    }
    *required_context_bytes = 0u;
    caller_struct_size = host->struct_size;
    if (caller_struct_size < (uint32_t)sizeof(*host)) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (mode != XSW_REF_MODE_FUSED_DISCOVERY_V1 && mode != XSW_REF_MODE_DYNAMIC_EXACT_V1) {
        return XS_STATUS_INVALID_REQUEST;
    }

    memset(&config, 0, sizeof(config));
    config.struct_size = (uint32_t)sizeof(config);
    config.abi_major = XS_ABI_MAJOR_V1;
    config.abi_minor = XS_ABI_MINOR_V1;
    config.max_packs = (uint16_t)XSW_REF_MAX_MOUNTED_PACKS_V1;
    config.max_find_matches = (uint16_t)XSW_REF_MAX_FIND_MATCHES_V1;
    config.max_vector_len = (uint16_t)XSW_REF_MAX_VECTOR_LEN_V1;
    config.max_tinywire_frame = XSW_REF_MAX_TINYWIRE_FRAME_V1;
    config.flags = mode == XSW_REF_MODE_FUSED_DISCOVERY_V1
        ? XS_CONFIG_ENABLE_DISCOVERY_V1
        : XS_CONFIG_ALLOW_DYNAMIC_PACKS_V1;

    required = xs_context_size(&config);
    if (required == 0u) {
        return XS_STATUS_UNSUPPORTED_OPERATION;
    }
    if (required > XSW_REF_MAX_CONTEXT_BYTES_V1) {
        return XS_STATUS_RESOURCE_LIMIT;
    }
    *required_context_bytes = required;
    if (context_memory == NULL || context_memory_len < required) {
        return XS_STATUS_BUFFER_TOO_SMALL;
    }

    memset(host, 0, sizeof(*host));
    host->struct_size = caller_struct_size;
    host->mode = mode;
    host->state = XSW_REF_STATE_UNINITIALIZED_V1;
    context = NULL;
    status = xs_context_init(context_memory, context_memory_len, &config, &context);
    if (status != XS_STATUS_OK) {
        return status;
    }

    host->context = context;
    host->state = XSW_REF_STATE_MUTABLE_V1;
    if (mode == XSW_REF_MODE_FUSED_DISCOVERY_V1) {
        status = xs_registry_freeze(context);
        if (status != XS_STATUS_OK) {
            host->state = XSW_REF_STATE_FAULTED_V1;
            return status;
        }
        host->state = XSW_REF_STATE_FROZEN_V1;
    }
    return XS_STATUS_OK;
}

xs_status xsw_ref_mount(
    xsw_ref_host_v1* host,
    const uint8_t* pack_bytes,
    uint32_t pack_len,
    uint16_t* out_pack_slot) XS_NOEXCEPT {
    uint16_t pack_slot;
    uint32_t required_arena;
    xs_status status;
    int index;

    if (out_pack_slot == NULL) {
        return XS_STATUS_INVALID_REQUEST;
    }
    *out_pack_slot = 0u;
    if (!xsw_ref_host_record_valid(host)) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (host->mode != XSW_REF_MODE_DYNAMIC_EXACT_V1) {
        return XS_STATUS_UNSUPPORTED_OPERATION;
    }
    if (host->state != XSW_REF_STATE_MUTABLE_V1) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (pack_bytes == NULL || pack_len == 0u) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (pack_len > XSW_REF_MAX_PACK_BYTES_V1) {
        return XS_STATUS_RESOURCE_LIMIT;
    }
    if (host->mounted_pack_count >= XSW_REF_MAX_MOUNTED_PACKS_V1) {
        return XS_STATUS_RESOURCE_LIMIT;
    }
    if (pack_len > XSW_REF_MAX_TOTAL_PACK_BYTES_V1 - host->mounted_pack_bytes) {
        return XS_STATUS_RESOURCE_LIMIT;
    }
    index = xsw_ref_find_free_pack_index(host);
    if (index < 0) {
        host->state = XSW_REF_STATE_FAULTED_V1;
        return XS_STATUS_INTERNAL_ERROR;
    }

    pack_slot = 0u;
    required_arena = 0u;
    status = xs_pack_mount(
        host->context,
        pack_bytes,
        pack_len,
        NULL,
        XSW_REF_MAX_PACK_MOUNT_ARENA_BYTES_V1,
        &pack_slot,
        &required_arena);
    if (status == XS_STATUS_BUFFER_TOO_SMALL && required_arena != 0u) {
        return XS_STATUS_RESOURCE_LIMIT;
    }
    if (status != XS_STATUS_OK) {
        return status;
    }
    if (required_arena != 0u || pack_slot == 0u) {
        (void)xs_pack_unmount(host->context, pack_slot);
        return XS_STATUS_RESOURCE_LIMIT;
    }

    host->pack_slots[index] = pack_slot;
    host->pack_lengths[index] = pack_len;
    host->mounted_pack_count = (uint16_t)(host->mounted_pack_count + 1u);
    host->mounted_pack_bytes += pack_len;
    *out_pack_slot = pack_slot;
    return XS_STATUS_OK;
}

xs_status xsw_ref_unmount(xsw_ref_host_v1* host, uint16_t pack_slot) XS_NOEXCEPT {
    xs_status status;
    int index;

    if (!xsw_ref_host_record_valid(host)) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (host->mode != XSW_REF_MODE_DYNAMIC_EXACT_V1) {
        return XS_STATUS_UNSUPPORTED_OPERATION;
    }
    if (host->state != XSW_REF_STATE_MUTABLE_V1) {
        return XS_STATUS_INVALID_REQUEST;
    }
    index = xsw_ref_find_pack_index(host, pack_slot);
    if (index < 0) {
        return XS_STATUS_UNKNOWN_PACK;
    }

    status = xs_pack_unmount(host->context, pack_slot);
    if (status != XS_STATUS_OK) {
        return status;
    }
    if (host->mounted_pack_bytes < host->pack_lengths[index] || host->mounted_pack_count == 0u) {
        host->state = XSW_REF_STATE_FAULTED_V1;
        return XS_STATUS_INTERNAL_ERROR;
    }
    host->mounted_pack_bytes -= host->pack_lengths[index];
    host->mounted_pack_count = (uint16_t)(host->mounted_pack_count - 1u);
    host->pack_slots[index] = 0u;
    host->pack_lengths[index] = 0u;
    return XS_STATUS_OK;
}

xs_status xsw_ref_finish_install(xsw_ref_host_v1* host) XS_NOEXCEPT {
    xs_status status;

    if (!xsw_ref_host_record_valid(host)) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (host->state == XSW_REF_STATE_FROZEN_V1) {
        return XS_STATUS_OK;
    }
    if (host->state != XSW_REF_STATE_MUTABLE_V1) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (host->mode == XSW_REF_MODE_DYNAMIC_EXACT_V1 && host->mounted_pack_count == 0u) {
        return XS_STATUS_MISSING_INFORMATION;
    }

    status = xs_registry_freeze(host->context);
    if (status != XS_STATUS_OK) {
        host->state = XSW_REF_STATE_FAULTED_V1;
        return status;
    }
    host->state = XSW_REF_STATE_FROZEN_V1;
    return XS_STATUS_OK;
}

xs_status xsw_ref_reset(xsw_ref_host_v1* host) XS_NOEXCEPT {
    xs_status status;

    if (!xsw_ref_host_record_valid(host)) {
        return XS_STATUS_INVALID_REQUEST;
    }
    status = xs_context_reset(host->context);
    if (status != XS_STATUS_OK) {
        host->state = XSW_REF_STATE_FAULTED_V1;
        return status;
    }
    xsw_ref_clear_pack_tracking(host);
    host->state = XSW_REF_STATE_MUTABLE_V1;

    if (host->mode == XSW_REF_MODE_FUSED_DISCOVERY_V1) {
        status = xs_registry_freeze(host->context);
        if (status != XS_STATUS_OK) {
            host->state = XSW_REF_STATE_FAULTED_V1;
            return status;
        }
        host->state = XSW_REF_STATE_FROZEN_V1;
    }
    return XS_STATUS_OK;
}

xs_status xsw_ref_lookup(
    xsw_ref_host_v1* host,
    const uint8_t* operation_key,
    uint32_t operation_key_len,
    uint16_t* out_pack_slot,
    uint32_t* out_operation_id,
    uint16_t* out_operation_revision) XS_NOEXCEPT {
    if (!xsw_ref_host_record_valid(host) || host->state != XSW_REF_STATE_FROZEN_V1) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (operation_key_len > XSW_REF_MAX_OPERATION_KEY_BYTES_V1) {
        return XS_STATUS_RESOURCE_LIMIT;
    }
    return xs_lookup(
        host->context,
        operation_key,
        operation_key_len,
        out_pack_slot,
        out_operation_id,
        out_operation_revision);
}

xs_status xsw_ref_find(
    xsw_ref_host_v1* host,
    const uint8_t* query,
    uint32_t query_len,
    xs_match_v1* matches,
    uint16_t match_capacity,
    uint16_t* out_match_count) XS_NOEXCEPT {
    if (!xsw_ref_host_record_valid(host) || host->state != XSW_REF_STATE_FROZEN_V1) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (host->mode != XSW_REF_MODE_FUSED_DISCOVERY_V1) {
        return XS_STATUS_UNSUPPORTED_OPERATION;
    }
    if (match_capacity > XSW_REF_MAX_FIND_MATCHES_V1) {
        return XS_STATUS_RESOURCE_LIMIT;
    }
    return xs_find(host->context, query, query_len, matches, match_capacity, out_match_count);
}

xs_status xsw_ref_eval(
    xsw_ref_host_v1* host,
    uint16_t pack_slot,
    uint32_t operation_id,
    const xs_value_ref_v1* args,
    uint16_t arg_count,
    const xs_eval_options_v1* options,
    void* scratch,
    uint32_t scratch_len,
    xs_result_v1* out_result) XS_NOEXCEPT {
    if (!xsw_ref_host_record_valid(host) || host->state != XSW_REF_STATE_FROZEN_V1) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (scratch_len > XSW_REF_MAX_EVAL_SCRATCH_BYTES_V1) {
        return XS_STATUS_RESOURCE_LIMIT;
    }
    if (scratch == NULL && scratch_len != 0u) {
        return XS_STATUS_INVALID_REQUEST;
    }
    return xs_eval(
        host->context,
        pack_slot,
        operation_id,
        args,
        arg_count,
        options,
        scratch,
        scratch_len,
        out_result);
}

xs_status xsw_ref_make_telemetry(
    const xs_result_v1* result,
    uint32_t duration_us,
    xsw_ref_telemetry_v1* out_event) XS_NOEXCEPT {
    uint32_t caller_struct_size;

    if (result == NULL || out_event == NULL) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (result->struct_size < (uint32_t)sizeof(*result)) {
        return XS_STATUS_INVALID_REQUEST;
    }
    caller_struct_size = out_event->struct_size;
    if (caller_struct_size < (uint32_t)sizeof(*out_event)) {
        return XS_STATUS_INVALID_REQUEST;
    }

    memset(out_event, 0, sizeof(*out_event));
    out_event->struct_size = caller_struct_size;
    out_event->status = result->status;
    out_event->pack_slot = result->pack_slot;
    out_event->operation_id = result->operation_id;
    out_event->duration_bucket = xsw_ref_duration_bucket(duration_us);
    return XS_STATUS_OK;
}
