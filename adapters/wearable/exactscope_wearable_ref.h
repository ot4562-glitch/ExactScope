#ifndef EXACTSCOPE_WEARABLE_REF_H_INCLUDED
#define EXACTSCOPE_WEARABLE_REF_H_INCLUDED

#include <stdint.h>

#include "exactscope.h"

#if defined(__cplusplus)
extern "C" {
#endif

#define XSW_REF_PROFILE_VERSION_V1 0x00010000u

#define XSW_REF_MODE_FUSED_DISCOVERY_V1 1u
#define XSW_REF_MODE_DYNAMIC_EXACT_V1 2u

#define XSW_REF_STATE_UNINITIALIZED_V1 0u
#define XSW_REF_STATE_MUTABLE_V1 1u
#define XSW_REF_STATE_FROZEN_V1 2u
#define XSW_REF_STATE_FAULTED_V1 3u

#define XSW_REF_MAX_CONTEXT_BYTES_V1 4096u
#define XSW_REF_MAX_EVAL_SCRATCH_BYTES_V1 4096u
#define XSW_REF_MAX_PACK_MOUNT_ARENA_BYTES_V1 0u
#define XSW_REF_MAX_ADAPTER_BUFFER_BYTES_V1 8192u
#define XSW_REF_MAX_MUTABLE_RUNTIME_BYTES_V1 16384u
#define XSW_REF_MAX_TINY_REQUEST_BYTES_V1 512u
#define XSW_REF_MAX_TINY_RESPONSE_BYTES_V1 512u
#define XSW_REF_MAX_PACK_BYTES_V1 262144u
#define XSW_REF_MAX_TOTAL_PACK_BYTES_V1 524288u
#define XSW_REF_MAX_MOUNTED_PACKS_V1 4u
#define XSW_REF_MAX_VECTOR_LEN_V1 64u
#define XSW_REF_MAX_RESULT_VALUES_V1 4u
#define XSW_REF_MAX_OPERATION_KEY_BYTES_V1 96u
#define XSW_REF_MAX_FIND_MATCHES_V1 5u
#define XSW_REF_MAX_TINYWIRE_FRAME_V1 512u

#define XSW_REF_TARGET_SCALAR_EVAL_P50_US_V1 250u
#define XSW_REF_TARGET_SCALAR_EVAL_P99_US_V1 1000u
#define XSW_REF_TARGET_LOOKUP_P99_US_V1 250u
#define XSW_REF_TARGET_PACK_MOUNT_256K_P99_US_V1 10000u
#define XSW_REF_TARGET_SCALAR_EVAL_ENERGY_UJ_V1 500u
#define XSW_REF_TARGET_STRIPPED_ARTIFACT_BYTES_V1 1048576u

#define XSW_REF_DURATION_LE_250_US_V1 0u
#define XSW_REF_DURATION_LE_1_MS_V1 1u
#define XSW_REF_DURATION_LE_10_MS_V1 2u
#define XSW_REF_DURATION_GT_10_MS_V1 3u

typedef struct xsw_ref_host_v1 {
    uint32_t struct_size;
    uint8_t mode;
    uint8_t state;
    uint16_t mounted_pack_count;
    uint32_t mounted_pack_bytes;
    xs_context* context;
    uint16_t pack_slots[XSW_REF_MAX_MOUNTED_PACKS_V1];
    uint32_t pack_lengths[XSW_REF_MAX_MOUNTED_PACKS_V1];
    uint32_t reserved[4];
} xsw_ref_host_v1;

typedef struct xsw_ref_telemetry_v1 {
    uint32_t struct_size;
    uint16_t status;
    uint16_t pack_slot;
    uint32_t operation_id;
    uint8_t duration_bucket;
    uint8_t reserved0[3];
    uint32_t reserved[2];
} xsw_ref_telemetry_v1;

/* Returns sizeof(xsw_ref_host_v1) for FFI/build-time checks. */
uint32_t xsw_ref_host_size(void) XS_NOEXCEPT;

/*
 * Initializes a bounded wearable host context in caller-owned memory.
 *
 * FUSED_DISCOVERY is frozen before this function returns.
 * DYNAMIC_EXACT remains mutable so the host can mount the complete pack set,
 * then must call xsw_ref_finish_install before serving user requests.
 */
xs_status xsw_ref_init(
    xsw_ref_host_v1* host,
    uint8_t mode,
    void* context_memory,
    uint32_t context_memory_len,
    uint32_t* required_context_bytes) XS_NOEXCEPT;

/* Mounts one zero-copy dynamic pack while the host is mutable. */
xs_status xsw_ref_mount(
    xsw_ref_host_v1* host,
    const uint8_t* pack_bytes,
    uint32_t pack_len,
    uint16_t* out_pack_slot) XS_NOEXCEPT;

/* Unmount is available only before xsw_ref_finish_install freezes the registry. */
xs_status xsw_ref_unmount(
    xsw_ref_host_v1* host,
    uint16_t pack_slot) XS_NOEXCEPT;

/* Freezes the complete dynamic pack set before any user-facing lookup/eval. */
xs_status xsw_ref_finish_install(xsw_ref_host_v1* host) XS_NOEXCEPT;

/* Resets the core and clears dynamic registrations. Fused mode is refrozen. */
xs_status xsw_ref_reset(xsw_ref_host_v1* host) XS_NOEXCEPT;

/* Exact canonical lookup. Serving calls require FROZEN state. */
xs_status xsw_ref_lookup(
    xsw_ref_host_v1* host,
    const uint8_t* operation_key,
    uint32_t operation_key_len,
    uint16_t* out_pack_slot,
    uint32_t* out_operation_id,
    uint16_t* out_operation_revision) XS_NOEXCEPT;

/* Discovery is intentionally exposed only in FUSED_DISCOVERY mode in v0.1. */
xs_status xsw_ref_find(
    xsw_ref_host_v1* host,
    const uint8_t* query,
    uint32_t query_len,
    xs_match_v1* matches,
    uint16_t match_capacity,
    uint16_t* out_match_count) XS_NOEXCEPT;

/* Typed deterministic evaluation. Serving calls require FROZEN state. */
xs_status xsw_ref_eval(
    xsw_ref_host_v1* host,
    uint16_t pack_slot,
    uint32_t operation_id,
    const xs_value_ref_v1* args,
    uint16_t arg_count,
    const xs_eval_options_v1* options,
    void* scratch,
    uint32_t scratch_len,
    xs_result_v1* out_result) XS_NOEXCEPT;

/*
 * Creates privacy-minimized telemetry. The event contains no argument/result
 * values, transcript, sensor content, user identity, or location.
 */
xs_status xsw_ref_make_telemetry(
    const xs_result_v1* result,
    uint32_t duration_us,
    xsw_ref_telemetry_v1* out_event) XS_NOEXCEPT;

#if defined(__cplusplus)
} /* extern "C" */
#endif

#endif /* EXACTSCOPE_WEARABLE_REF_H_INCLUDED */
