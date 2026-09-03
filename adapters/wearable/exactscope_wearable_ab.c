#include "exactscope_wearable_ab.h"

#include <stddef.h>
#include <string.h>

#define XSW_AB_RECORD_MAGIC_BYTES_V1 8u
#define XSW_AB_RECORD_CRC_OFFSET_V1 92u
#define XSW_AB_RECORD_KNOWN_FLAGS_V1 XSW_AB_FLAG_ROLLBACK_AVAILABLE_V1

static const uint8_t XSW_AB_RECORD_MAGIC_V1[XSW_AB_RECORD_MAGIC_BYTES_V1] = {
    (uint8_t)'X', (uint8_t)'S', (uint8_t)'W', (uint8_t)'A',
    (uint8_t)'B', (uint8_t)'0', (uint8_t)'1', 0u
};

typedef struct xsw_ab_decoded_v1 {
    uint64_t generation;
    uint8_t active_slot;
    uint8_t previous_slot;
    uint8_t rollback_available;
    uint8_t active_digest[XSW_AB_DIGEST_BYTES_V1];
    uint8_t previous_digest[XSW_AB_DIGEST_BYTES_V1];
} xsw_ab_decoded_v1;

static uint16_t xsw_ab_read_u16_le(const uint8_t* bytes) {
    return (uint16_t)((uint16_t)bytes[0] | ((uint16_t)bytes[1] << 8u));
}

static uint32_t xsw_ab_read_u32_le(const uint8_t* bytes) {
    return (uint32_t)bytes[0]
        | ((uint32_t)bytes[1] << 8u)
        | ((uint32_t)bytes[2] << 16u)
        | ((uint32_t)bytes[3] << 24u);
}

static uint64_t xsw_ab_read_u64_le(const uint8_t* bytes) {
    uint64_t value = 0u;
    uint32_t index;
    for (index = 0u; index < 8u; ++index) {
        value |= ((uint64_t)bytes[index]) << (index * 8u);
    }
    return value;
}

static void xsw_ab_write_u16_le(uint8_t* bytes, uint16_t value) {
    bytes[0] = (uint8_t)(value & 0xffu);
    bytes[1] = (uint8_t)((value >> 8u) & 0xffu);
}

static void xsw_ab_write_u32_le(uint8_t* bytes, uint32_t value) {
    bytes[0] = (uint8_t)(value & 0xffu);
    bytes[1] = (uint8_t)((value >> 8u) & 0xffu);
    bytes[2] = (uint8_t)((value >> 16u) & 0xffu);
    bytes[3] = (uint8_t)((value >> 24u) & 0xffu);
}

static void xsw_ab_write_u64_le(uint8_t* bytes, uint64_t value) {
    uint32_t index;
    for (index = 0u; index < 8u; ++index) {
        bytes[index] = (uint8_t)((value >> (index * 8u)) & 0xffu);
    }
}

static uint32_t xsw_ab_crc32(const uint8_t* bytes, uint32_t byte_len) {
    uint32_t crc = 0xffffffffu;
    uint32_t index;
    for (index = 0u; index < byte_len; ++index) {
        uint32_t value = crc ^ (uint32_t)bytes[index];
        uint32_t bit;
        for (bit = 0u; bit < 8u; ++bit) {
            uint32_t mask = (uint32_t)(0u - (value & 1u));
            value = (value >> 1u) ^ (0xedb88320u & mask);
        }
        crc = value;
    }
    return crc ^ 0xffffffffu;
}

static int xsw_ab_digest_is_zero(const uint8_t digest[XSW_AB_DIGEST_BYTES_V1]) {
    uint8_t combined = 0u;
    uint32_t index;
    for (index = 0u; index < XSW_AB_DIGEST_BYTES_V1; ++index) {
        combined = (uint8_t)(combined | digest[index]);
    }
    return combined == 0u;
}

static int xsw_ab_record_is_blank(const uint8_t bytes[XSW_AB_RECORD_BYTES_V1]) {
    uint32_t index;
    int all_zero = 1;
    int all_ff = 1;
    for (index = 0u; index < XSW_AB_RECORD_BYTES_V1; ++index) {
        if (bytes[index] != 0u) {
            all_zero = 0;
        }
        if (bytes[index] != 0xffu) {
            all_ff = 0;
        }
    }
    return all_zero || all_ff;
}

static int xsw_ab_slot_valid(uint8_t slot) {
    return slot == XSW_AB_SLOT_A_V1 || slot == XSW_AB_SLOT_B_V1;
}

static xs_status xsw_ab_validate_storage(const xsw_ab_storage_v1* storage) {
    if (storage == NULL || storage->struct_size < (uint32_t)sizeof(*storage)) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (storage->read_record == NULL || storage->write_record == NULL || storage->flush == NULL) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (storage->reserved[0] != 0u || storage->reserved[1] != 0u
        || storage->reserved[2] != 0u || storage->reserved[3] != 0u) {
        return XS_STATUS_INVALID_REQUEST;
    }
    return XS_STATUS_OK;
}

static xs_status xsw_ab_validate_state_output(xsw_ab_state_v1* state) {
    if (state == NULL || state->struct_size < (uint32_t)sizeof(*state)) {
        return XS_STATUS_INVALID_REQUEST;
    }
    return XS_STATUS_OK;
}

static xs_status xsw_ab_validate_state_input(const xsw_ab_state_v1* state) {
    if (state == NULL || state->struct_size < (uint32_t)sizeof(*state)) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (state->generation == 0u || !xsw_ab_slot_valid(state->active_slot)
        || !xsw_ab_slot_valid(state->previous_slot)
        || state->active_slot == state->previous_slot
        || state->selected_record_copy >= XSW_AB_RECORD_COPY_COUNT_V1
        || state->rollback_available > 1u
        || xsw_ab_digest_is_zero(state->active_digest)) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (state->rollback_available != 0u && xsw_ab_digest_is_zero(state->previous_digest)) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (state->reserved[0] != 0u || state->reserved[1] != 0u
        || state->reserved[2] != 0u || state->reserved[3] != 0u) {
        return XS_STATUS_INVALID_REQUEST;
    }
    return XS_STATUS_OK;
}

static void xsw_ab_encode_record(
    const xsw_ab_decoded_v1* decoded,
    uint8_t output[XSW_AB_RECORD_BYTES_V1]) {
    uint16_t flags = decoded->rollback_available != 0u
        ? XSW_AB_FLAG_ROLLBACK_AVAILABLE_V1
        : 0u;
    uint32_t crc;

    memset(output, 0, XSW_AB_RECORD_BYTES_V1);
    memcpy(output, XSW_AB_RECORD_MAGIC_V1, XSW_AB_RECORD_MAGIC_BYTES_V1);
    xsw_ab_write_u16_le(&output[8], 1u);
    xsw_ab_write_u16_le(&output[10], (uint16_t)XSW_AB_RECORD_BYTES_V1);
    xsw_ab_write_u64_le(&output[12], decoded->generation);
    output[20] = decoded->active_slot;
    output[21] = decoded->previous_slot;
    xsw_ab_write_u16_le(&output[22], flags);
    memcpy(&output[24], decoded->active_digest, XSW_AB_DIGEST_BYTES_V1);
    memcpy(&output[56], decoded->previous_digest, XSW_AB_DIGEST_BYTES_V1);
    crc = xsw_ab_crc32(output, XSW_AB_RECORD_CRC_OFFSET_V1);
    xsw_ab_write_u32_le(&output[XSW_AB_RECORD_CRC_OFFSET_V1], crc);
}

static xs_status xsw_ab_decode_record(
    const uint8_t bytes[XSW_AB_RECORD_BYTES_V1],
    xsw_ab_decoded_v1* decoded) {
    uint16_t flags;
    uint32_t stored_crc;
    uint32_t actual_crc;

    if (memcmp(bytes, XSW_AB_RECORD_MAGIC_V1, XSW_AB_RECORD_MAGIC_BYTES_V1) != 0) {
        return XS_STATUS_INTEGRITY_ERROR;
    }
    if (xsw_ab_read_u16_le(&bytes[8]) != 1u
        || xsw_ab_read_u16_le(&bytes[10]) != (uint16_t)XSW_AB_RECORD_BYTES_V1) {
        return XS_STATUS_UNSUPPORTED_OPERATION;
    }
    if (bytes[88] != 0u || bytes[89] != 0u || bytes[90] != 0u || bytes[91] != 0u) {
        return XS_STATUS_INTEGRITY_ERROR;
    }

    stored_crc = xsw_ab_read_u32_le(&bytes[XSW_AB_RECORD_CRC_OFFSET_V1]);
    actual_crc = xsw_ab_crc32(bytes, XSW_AB_RECORD_CRC_OFFSET_V1);
    if (stored_crc != actual_crc) {
        return XS_STATUS_INTEGRITY_ERROR;
    }

    memset(decoded, 0, sizeof(*decoded));
    decoded->generation = xsw_ab_read_u64_le(&bytes[12]);
    decoded->active_slot = bytes[20];
    decoded->previous_slot = bytes[21];
    flags = xsw_ab_read_u16_le(&bytes[22]);
    decoded->rollback_available = (uint8_t)((flags & XSW_AB_FLAG_ROLLBACK_AVAILABLE_V1) != 0u);
    memcpy(decoded->active_digest, &bytes[24], XSW_AB_DIGEST_BYTES_V1);
    memcpy(decoded->previous_digest, &bytes[56], XSW_AB_DIGEST_BYTES_V1);

    if (decoded->generation == 0u || !xsw_ab_slot_valid(decoded->active_slot)
        || !xsw_ab_slot_valid(decoded->previous_slot)
        || decoded->active_slot == decoded->previous_slot
        || (flags & (uint16_t)(~XSW_AB_RECORD_KNOWN_FLAGS_V1)) != 0u
        || xsw_ab_digest_is_zero(decoded->active_digest)) {
        return XS_STATUS_INTEGRITY_ERROR;
    }
    if (decoded->rollback_available != 0u && xsw_ab_digest_is_zero(decoded->previous_digest)) {
        return XS_STATUS_INTEGRITY_ERROR;
    }
    return XS_STATUS_OK;
}

static void xsw_ab_state_from_decoded(
    xsw_ab_state_v1* state,
    uint8_t selected_record_copy,
    const xsw_ab_decoded_v1* decoded) {
    uint32_t caller_size = state->struct_size;
    memset(state, 0, sizeof(*state));
    state->struct_size = caller_size;
    state->generation = decoded->generation;
    state->active_slot = decoded->active_slot;
    state->previous_slot = decoded->previous_slot;
    state->rollback_available = decoded->rollback_available;
    state->selected_record_copy = selected_record_copy;
    memcpy(state->active_digest, decoded->active_digest, XSW_AB_DIGEST_BYTES_V1);
    memcpy(state->previous_digest, decoded->previous_digest, XSW_AB_DIGEST_BYTES_V1);
}

static void xsw_ab_decoded_from_state(
    const xsw_ab_state_v1* state,
    xsw_ab_decoded_v1* decoded) {
    memset(decoded, 0, sizeof(*decoded));
    decoded->generation = state->generation;
    decoded->active_slot = state->active_slot;
    decoded->previous_slot = state->previous_slot;
    decoded->rollback_available = state->rollback_available;
    memcpy(decoded->active_digest, state->active_digest, XSW_AB_DIGEST_BYTES_V1);
    memcpy(decoded->previous_digest, state->previous_digest, XSW_AB_DIGEST_BYTES_V1);
}

static int xsw_ab_decoded_equal(const xsw_ab_decoded_v1* left, const xsw_ab_decoded_v1* right) {
    return left->generation == right->generation
        && left->active_slot == right->active_slot
        && left->previous_slot == right->previous_slot
        && left->rollback_available == right->rollback_available
        && memcmp(left->active_digest, right->active_digest, XSW_AB_DIGEST_BYTES_V1) == 0
        && memcmp(left->previous_digest, right->previous_digest, XSW_AB_DIGEST_BYTES_V1) == 0;
}

static xs_status xsw_ab_read_copy(
    const xsw_ab_storage_v1* storage,
    uint8_t record_copy,
    uint8_t bytes[XSW_AB_RECORD_BYTES_V1],
    xsw_ab_decoded_v1* decoded,
    int* valid) {
    xs_status status = storage->read_record(
        storage->user,
        record_copy,
        bytes,
        XSW_AB_RECORD_BYTES_V1);
    if (status != XS_STATUS_OK) {
        *valid = 0;
        return status;
    }
    status = xsw_ab_decode_record(bytes, decoded);
    *valid = status == XS_STATUS_OK;
    return status;
}

static xs_status xsw_ab_persist_next(
    const xsw_ab_storage_v1* storage,
    xsw_ab_state_v1* state,
    const xsw_ab_decoded_v1* next) {
    uint8_t record[XSW_AB_RECORD_BYTES_V1];
    uint8_t verify_bytes[XSW_AB_RECORD_BYTES_V1];
    xsw_ab_decoded_v1 verify;
    uint8_t target_copy = (uint8_t)(1u - state->selected_record_copy);
    xs_status status;

    xsw_ab_encode_record(next, record);
    status = storage->write_record(
        storage->user,
        target_copy,
        record,
        XSW_AB_RECORD_BYTES_V1);
    if (status != XS_STATUS_OK) {
        return status;
    }
    status = storage->flush(storage->user);
    if (status != XS_STATUS_OK) {
        return status;
    }
    status = storage->read_record(
        storage->user,
        target_copy,
        verify_bytes,
        XSW_AB_RECORD_BYTES_V1);
    if (status != XS_STATUS_OK) {
        return status;
    }
    status = xsw_ab_decode_record(verify_bytes, &verify);
    if (status != XS_STATUS_OK || !xsw_ab_decoded_equal(next, &verify)) {
        return XS_STATUS_INTEGRITY_ERROR;
    }

    xsw_ab_state_from_decoded(state, target_copy, next);
    return XS_STATUS_OK;
}

static xs_status xsw_ab_refresh_and_compare(
    const xsw_ab_storage_v1* storage,
    const xsw_ab_state_v1* expected,
    xsw_ab_state_v1* current) {
    xs_status status;
    current->struct_size = (uint32_t)sizeof(*current);
    status = xsw_ab_recover(storage, current);
    if (status != XS_STATUS_OK) {
        return status;
    }
    if (expected->generation != current->generation
        || expected->active_slot != current->active_slot
        || expected->previous_slot != current->previous_slot
        || expected->rollback_available != current->rollback_available
        || expected->selected_record_copy != current->selected_record_copy
        || memcmp(expected->active_digest, current->active_digest, XSW_AB_DIGEST_BYTES_V1) != 0
        || memcmp(expected->previous_digest, current->previous_digest, XSW_AB_DIGEST_BYTES_V1) != 0) {
        return XS_STATUS_INVALID_REQUEST;
    }
    return XS_STATUS_OK;
}

uint32_t xsw_ab_record_size(void) XS_NOEXCEPT {
    return XSW_AB_RECORD_BYTES_V1;
}

xs_status xsw_ab_recover(
    const xsw_ab_storage_v1* storage,
    xsw_ab_state_v1* out_state) XS_NOEXCEPT {
    uint8_t bytes0[XSW_AB_RECORD_BYTES_V1];
    uint8_t bytes1[XSW_AB_RECORD_BYTES_V1];
    xsw_ab_decoded_v1 decoded0;
    xsw_ab_decoded_v1 decoded1;
    int valid0 = 0;
    int valid1 = 0;
    xs_status read0;
    xs_status read1;
    xs_status status;

    status = xsw_ab_validate_storage(storage);
    if (status != XS_STATUS_OK) {
        return status;
    }
    status = xsw_ab_validate_state_output(out_state);
    if (status != XS_STATUS_OK) {
        return status;
    }

    read0 = xsw_ab_read_copy(storage, 0u, bytes0, &decoded0, &valid0);
    read1 = xsw_ab_read_copy(storage, 1u, bytes1, &decoded1, &valid1);

    if (!valid0 && !valid1) {
        if (read0 != XS_STATUS_OK && read0 != XS_STATUS_INTEGRITY_ERROR
            && read0 != XS_STATUS_UNSUPPORTED_OPERATION) {
            return read0;
        }
        if (read1 != XS_STATUS_OK && read1 != XS_STATUS_INTEGRITY_ERROR
            && read1 != XS_STATUS_UNSUPPORTED_OPERATION) {
            return read1;
        }
        return XS_STATUS_INTEGRITY_ERROR;
    }
    if (valid0 && valid1 && decoded0.generation == decoded1.generation) {
        if (!xsw_ab_decoded_equal(&decoded0, &decoded1)) {
            return XS_STATUS_INTEGRITY_ERROR;
        }
        xsw_ab_state_from_decoded(out_state, 0u, &decoded0);
        return XS_STATUS_OK;
    }
    if (valid0 && (!valid1 || decoded0.generation > decoded1.generation)) {
        xsw_ab_state_from_decoded(out_state, 0u, &decoded0);
        return XS_STATUS_OK;
    }
    xsw_ab_state_from_decoded(out_state, 1u, &decoded1);
    return XS_STATUS_OK;
}

xs_status xsw_ab_bootstrap(
    const xsw_ab_storage_v1* storage,
    xsw_ab_state_v1* state,
    uint8_t active_slot,
    const uint8_t active_digest[XSW_AB_DIGEST_BYTES_V1]) XS_NOEXCEPT {
    uint8_t bytes0[XSW_AB_RECORD_BYTES_V1];
    uint8_t bytes1[XSW_AB_RECORD_BYTES_V1];
    uint8_t record[XSW_AB_RECORD_BYTES_V1];
    uint8_t verify_bytes[XSW_AB_RECORD_BYTES_V1];
    xsw_ab_decoded_v1 decoded;
    xsw_ab_decoded_v1 verify;
    xs_status status;

    status = xsw_ab_validate_storage(storage);
    if (status != XS_STATUS_OK) {
        return status;
    }
    status = xsw_ab_validate_state_output(state);
    if (status != XS_STATUS_OK) {
        return status;
    }
    if (!xsw_ab_slot_valid(active_slot) || active_digest == NULL || xsw_ab_digest_is_zero(active_digest)) {
        return XS_STATUS_INVALID_REQUEST;
    }

    status = storage->read_record(storage->user, 0u, bytes0, XSW_AB_RECORD_BYTES_V1);
    if (status != XS_STATUS_OK) {
        return status;
    }
    status = storage->read_record(storage->user, 1u, bytes1, XSW_AB_RECORD_BYTES_V1);
    if (status != XS_STATUS_OK) {
        return status;
    }
    if (!xsw_ab_record_is_blank(bytes0) || !xsw_ab_record_is_blank(bytes1)) {
        if (xsw_ab_decode_record(bytes0, &verify) == XS_STATUS_OK
            || xsw_ab_decode_record(bytes1, &verify) == XS_STATUS_OK) {
            return XS_STATUS_INVALID_REQUEST;
        }
        return XS_STATUS_INTEGRITY_ERROR;
    }

    memset(&decoded, 0, sizeof(decoded));
    decoded.generation = 1u;
    decoded.active_slot = active_slot;
    decoded.previous_slot = (uint8_t)(1u - active_slot);
    memcpy(decoded.active_digest, active_digest, XSW_AB_DIGEST_BYTES_V1);
    xsw_ab_encode_record(&decoded, record);

    status = storage->write_record(storage->user, 0u, record, XSW_AB_RECORD_BYTES_V1);
    if (status != XS_STATUS_OK) {
        return status;
    }
    status = storage->flush(storage->user);
    if (status != XS_STATUS_OK) {
        return status;
    }
    status = storage->read_record(storage->user, 0u, verify_bytes, XSW_AB_RECORD_BYTES_V1);
    if (status != XS_STATUS_OK) {
        return status;
    }
    status = xsw_ab_decode_record(verify_bytes, &verify);
    if (status != XS_STATUS_OK || !xsw_ab_decoded_equal(&decoded, &verify)) {
        return XS_STATUS_INTEGRITY_ERROR;
    }

    xsw_ab_state_from_decoded(state, 0u, &decoded);
    return XS_STATUS_OK;
}

xs_status xsw_ab_candidate_slot(
    const xsw_ab_state_v1* state,
    uint8_t* out_slot) XS_NOEXCEPT {
    xs_status status = xsw_ab_validate_state_input(state);
    if (out_slot == NULL) {
        return XS_STATUS_INVALID_REQUEST;
    }
    *out_slot = 0u;
    if (status != XS_STATUS_OK) {
        return status;
    }
    if (state->rollback_available != 0u) {
        return XS_STATUS_INVALID_REQUEST;
    }
    *out_slot = (uint8_t)(1u - state->active_slot);
    return XS_STATUS_OK;
}

xs_status xsw_ab_commit_validated_candidate(
    const xsw_ab_storage_v1* storage,
    xsw_ab_state_v1* state,
    uint8_t candidate_slot,
    const uint8_t candidate_digest[XSW_AB_DIGEST_BYTES_V1]) XS_NOEXCEPT {
    xsw_ab_state_v1 current;
    xsw_ab_decoded_v1 next;
    xs_status status;

    status = xsw_ab_validate_storage(storage);
    if (status != XS_STATUS_OK) {
        return status;
    }
    status = xsw_ab_validate_state_input(state);
    if (status != XS_STATUS_OK) {
        return status;
    }
    if (!xsw_ab_slot_valid(candidate_slot) || candidate_digest == NULL
        || xsw_ab_digest_is_zero(candidate_digest)) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (state->rollback_available != 0u || candidate_slot == state->active_slot
        || candidate_slot != (uint8_t)(1u - state->active_slot)) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (state->generation == UINT64_MAX) {
        return XS_STATUS_OVERFLOW;
    }

    status = xsw_ab_refresh_and_compare(storage, state, &current);
    if (status != XS_STATUS_OK) {
        return status;
    }

    memset(&next, 0, sizeof(next));
    next.generation = current.generation + 1u;
    next.active_slot = candidate_slot;
    next.previous_slot = current.active_slot;
    next.rollback_available = 1u;
    memcpy(next.active_digest, candidate_digest, XSW_AB_DIGEST_BYTES_V1);
    memcpy(next.previous_digest, current.active_digest, XSW_AB_DIGEST_BYTES_V1);
    return xsw_ab_persist_next(storage, state, &next);
}

xs_status xsw_ab_accept_active(
    const xsw_ab_storage_v1* storage,
    xsw_ab_state_v1* state) XS_NOEXCEPT {
    xsw_ab_state_v1 current;
    xsw_ab_decoded_v1 next;
    xs_status status;

    status = xsw_ab_validate_storage(storage);
    if (status != XS_STATUS_OK) {
        return status;
    }
    status = xsw_ab_validate_state_input(state);
    if (status != XS_STATUS_OK) {
        return status;
    }
    if (state->rollback_available == 0u) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (state->generation == UINT64_MAX) {
        return XS_STATUS_OVERFLOW;
    }
    status = xsw_ab_refresh_and_compare(storage, state, &current);
    if (status != XS_STATUS_OK) {
        return status;
    }

    xsw_ab_decoded_from_state(&current, &next);
    next.generation = current.generation + 1u;
    next.rollback_available = 0u;
    return xsw_ab_persist_next(storage, state, &next);
}

xs_status xsw_ab_rollback(
    const xsw_ab_storage_v1* storage,
    xsw_ab_state_v1* state) XS_NOEXCEPT {
    xsw_ab_state_v1 current;
    xsw_ab_decoded_v1 next;
    xs_status status;

    status = xsw_ab_validate_storage(storage);
    if (status != XS_STATUS_OK) {
        return status;
    }
    status = xsw_ab_validate_state_input(state);
    if (status != XS_STATUS_OK) {
        return status;
    }
    if (state->rollback_available == 0u || xsw_ab_digest_is_zero(state->previous_digest)) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (state->generation == UINT64_MAX) {
        return XS_STATUS_OVERFLOW;
    }
    status = xsw_ab_refresh_and_compare(storage, state, &current);
    if (status != XS_STATUS_OK) {
        return status;
    }

    memset(&next, 0, sizeof(next));
    next.generation = current.generation + 1u;
    next.active_slot = current.previous_slot;
    next.previous_slot = current.active_slot;
    next.rollback_available = 0u;
    memcpy(next.active_digest, current.previous_digest, XSW_AB_DIGEST_BYTES_V1);
    memcpy(next.previous_digest, current.active_digest, XSW_AB_DIGEST_BYTES_V1);
    return xsw_ab_persist_next(storage, state, &next);
}
