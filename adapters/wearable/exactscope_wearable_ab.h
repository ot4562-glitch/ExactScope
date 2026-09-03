#ifndef EXACTSCOPE_WEARABLE_AB_H_INCLUDED
#define EXACTSCOPE_WEARABLE_AB_H_INCLUDED

#include <stdint.h>

#include "exactscope.h"

#if defined(__cplusplus)
extern "C" {
#endif

#define XSW_AB_FORMAT_VERSION_V1 0x00010000u
#define XSW_AB_RECORD_BYTES_V1 96u
#define XSW_AB_DIGEST_BYTES_V1 32u
#define XSW_AB_RECORD_COPY_COUNT_V1 2u

#define XSW_AB_SLOT_A_V1 0u
#define XSW_AB_SLOT_B_V1 1u

#define XSW_AB_FLAG_ROLLBACK_AVAILABLE_V1 0x0001u

/*
 * Storage callbacks operate only on the two fixed-size activation journal
 * records. Pack/image storage and signature authentication remain product-owned.
 *
 * write_record may stage data internally; flush is the durability barrier.
 * read_record must return only durable bytes after a successful flush.
 */
typedef xs_status (*xsw_ab_read_record_fn_v1)(
    void* user,
    uint8_t record_copy,
    uint8_t* output,
    uint32_t output_len);

typedef xs_status (*xsw_ab_write_record_fn_v1)(
    void* user,
    uint8_t record_copy,
    const uint8_t* bytes,
    uint32_t byte_len);

typedef xs_status (*xsw_ab_flush_fn_v1)(void* user);

typedef struct xsw_ab_storage_v1 {
    uint32_t struct_size;
    void* user;
    xsw_ab_read_record_fn_v1 read_record;
    xsw_ab_write_record_fn_v1 write_record;
    xsw_ab_flush_fn_v1 flush;
    uint32_t reserved[4];
} xsw_ab_storage_v1;

/*
 * RAM reconstruction of the latest durable activation record. This structure
 * itself is not persisted; the canonical persistent form is the 96-byte record.
 */
typedef struct xsw_ab_state_v1 {
    uint32_t struct_size;
    uint64_t generation;
    uint8_t active_slot;
    uint8_t previous_slot;
    uint8_t rollback_available;
    uint8_t selected_record_copy;
    uint8_t active_digest[XSW_AB_DIGEST_BYTES_V1];
    uint8_t previous_digest[XSW_AB_DIGEST_BYTES_V1];
    uint32_t reserved[4];
} xsw_ab_state_v1;

/* Returns the canonical persistent journal-record size. */
uint32_t xsw_ab_record_size(void) XS_NOEXCEPT;

/*
 * Factory/bootstrap operation. Both journal copies must be blank (all 0x00 or
 * all 0xff). It writes generation 1 and makes active_digest authoritative.
 */
xs_status xsw_ab_bootstrap(
    const xsw_ab_storage_v1* storage,
    xsw_ab_state_v1* state,
    uint8_t active_slot,
    const uint8_t active_digest[XSW_AB_DIGEST_BYTES_V1]) XS_NOEXCEPT;

/*
 * Reconstructs the latest durable state. Torn/corrupt newer records are ignored
 * when the other copy is valid. Equal-generation conflicting copies fail with
 * INTEGRITY_ERROR.
 */
xs_status xsw_ab_recover(
    const xsw_ab_storage_v1* storage,
    xsw_ab_state_v1* out_state) XS_NOEXCEPT;

/*
 * Returns the inactive slot that may be overwritten for the next candidate.
 * This is forbidden while rollback_available is true; the host must first call
 * xsw_ab_accept_active or xsw_ab_rollback so the previous known-good slot is not
 * accidentally destroyed inside the rollback window.
 */
xs_status xsw_ab_candidate_slot(
    const xsw_ab_state_v1* state,
    uint8_t* out_slot) XS_NOEXCEPT;

/*
 * Atomically activates an already authenticated + ExactScope-validated candidate.
 * Precondition: candidate_slot is the current inactive slot and candidate_digest
 * identifies the complete validated candidate image/pack set.
 *
 * The function writes the non-current metadata copy, flushes it, rereads and
 * verifies it, then updates state. After any storage error the caller must
 * discard RAM state and call xsw_ab_recover before making another decision.
 */
xs_status xsw_ab_commit_validated_candidate(
    const xsw_ab_storage_v1* storage,
    xsw_ab_state_v1* state,
    uint8_t candidate_slot,
    const uint8_t candidate_digest[XSW_AB_DIGEST_BYTES_V1]) XS_NOEXCEPT;

/*
 * Ends the rollback-retention window while keeping the current active slot.
 * After this durable commit, xsw_ab_candidate_slot may return the old slot for
 * overwrite by the next update.
 */
xs_status xsw_ab_accept_active(
    const xsw_ab_storage_v1* storage,
    xsw_ab_state_v1* state) XS_NOEXCEPT;

/*
 * Rolls back to the retained previous slot without recompilation. The rollback
 * itself is another journal generation and therefore crash-consistent.
 */
xs_status xsw_ab_rollback(
    const xsw_ab_storage_v1* storage,
    xsw_ab_state_v1* state) XS_NOEXCEPT;

#if defined(__cplusplus)
} /* extern "C" */
#endif

#endif /* EXACTSCOPE_WEARABLE_AB_H_INCLUDED */
