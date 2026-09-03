#include "exactscope_wearable_ab.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct memory_storage_v1 {
    uint8_t durable[XSW_AB_RECORD_COPY_COUNT_V1][XSW_AB_RECORD_BYTES_V1];
    uint8_t pending[XSW_AB_RECORD_BYTES_V1];
    uint8_t pending_copy;
    int pending_valid;
    int fail_write;
    int fail_flush;
    int tear_write;
} memory_storage_v1;

static xs_status memory_read(
    void* user,
    uint8_t record_copy,
    uint8_t* output,
    uint32_t output_len) {
    memory_storage_v1* storage = (memory_storage_v1*)user;
    if (storage == NULL || output == NULL || output_len != XSW_AB_RECORD_BYTES_V1
        || record_copy >= XSW_AB_RECORD_COPY_COUNT_V1) {
        return XS_STATUS_INVALID_REQUEST;
    }
    memcpy(output, storage->durable[record_copy], XSW_AB_RECORD_BYTES_V1);
    return XS_STATUS_OK;
}

static xs_status memory_write(
    void* user,
    uint8_t record_copy,
    const uint8_t* bytes,
    uint32_t byte_len) {
    memory_storage_v1* storage = (memory_storage_v1*)user;
    if (storage == NULL || bytes == NULL || byte_len != XSW_AB_RECORD_BYTES_V1
        || record_copy >= XSW_AB_RECORD_COPY_COUNT_V1) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (storage->fail_write) {
        storage->pending_valid = 0;
        return XS_STATUS_INTERNAL_ERROR;
    }

    memset(storage->pending, 0, XSW_AB_RECORD_BYTES_V1);
    if (storage->tear_write) {
        memcpy(storage->pending, bytes, XSW_AB_RECORD_BYTES_V1 / 2u);
    } else {
        memcpy(storage->pending, bytes, XSW_AB_RECORD_BYTES_V1);
    }
    storage->pending_copy = record_copy;
    storage->pending_valid = 1;
    return XS_STATUS_OK;
}

static xs_status memory_flush(void* user) {
    memory_storage_v1* storage = (memory_storage_v1*)user;
    if (storage == NULL) {
        return XS_STATUS_INVALID_REQUEST;
    }
    if (storage->fail_flush) {
        storage->pending_valid = 0;
        return XS_STATUS_INTERNAL_ERROR;
    }
    if (storage->pending_valid) {
        memcpy(
            storage->durable[storage->pending_copy],
            storage->pending,
            XSW_AB_RECORD_BYTES_V1);
        storage->pending_valid = 0;
    }
    return XS_STATUS_OK;
}

static xsw_ab_storage_v1 storage_api(memory_storage_v1* memory) {
    xsw_ab_storage_v1 storage;
    memset(&storage, 0, sizeof(storage));
    storage.struct_size = (uint32_t)sizeof(storage);
    storage.user = memory;
    storage.read_record = memory_read;
    storage.write_record = memory_write;
    storage.flush = memory_flush;
    return storage;
}

static void storage_blank(memory_storage_v1* storage) {
    memset(storage, 0xff, sizeof(*storage));
    storage->pending_valid = 0;
    storage->fail_write = 0;
    storage->fail_flush = 0;
    storage->tear_write = 0;
}

static void storage_crash(memory_storage_v1* storage) {
    memset(storage->pending, 0, sizeof(storage->pending));
    storage->pending_valid = 0;
    storage->fail_write = 0;
    storage->fail_flush = 0;
    storage->tear_write = 0;
}

static void fill_digest(uint8_t digest[XSW_AB_DIGEST_BYTES_V1], uint8_t seed) {
    uint32_t index;
    for (index = 0u; index < XSW_AB_DIGEST_BYTES_V1; ++index) {
        digest[index] = (uint8_t)(seed + (uint8_t)index + 1u);
    }
}

static xsw_ab_state_v1 empty_state(void) {
    xsw_ab_state_v1 state;
    memset(&state, 0, sizeof(state));
    state.struct_size = (uint32_t)sizeof(state);
    return state;
}

static void assert_digest(
    const uint8_t actual[XSW_AB_DIGEST_BYTES_V1],
    const uint8_t expected[XSW_AB_DIGEST_BYTES_V1]) {
    assert(memcmp(actual, expected, XSW_AB_DIGEST_BYTES_V1) == 0);
}

static void assert_recovered(
    const xsw_ab_storage_v1* storage,
    uint8_t expected_slot,
    uint64_t expected_generation,
    uint8_t expected_rollback,
    const uint8_t expected_digest[XSW_AB_DIGEST_BYTES_V1]) {
    xsw_ab_state_v1 state = empty_state();
    assert(xsw_ab_recover(storage, &state) == XS_STATUS_OK);
    assert(state.active_slot == expected_slot);
    assert(state.generation == expected_generation);
    assert(state.rollback_available == expected_rollback);
    assert_digest(state.active_digest, expected_digest);
}

static void assert_pre_activation_crash_keeps_a(
    memory_storage_v1* memory,
    const xsw_ab_storage_v1* storage,
    const uint8_t digest_a[XSW_AB_DIGEST_BYTES_V1]) {
    storage_crash(memory);
    assert_recovered(storage, XSW_AB_SLOT_A_V1, 1u, 0u, digest_a);
}

int main(void) {
    memory_storage_v1 memory;
    xsw_ab_storage_v1 storage;
    xsw_ab_state_v1 state;
    xsw_ab_state_v1 stale;
    uint8_t digest_a[XSW_AB_DIGEST_BYTES_V1];
    uint8_t digest_b[XSW_AB_DIGEST_BYTES_V1];
    uint8_t candidate_slot = 0xffu;
    unsigned power_loss_cases = 0u;

    assert(xsw_ab_record_size() == XSW_AB_RECORD_BYTES_V1);
    fill_digest(digest_a, 0x10u);
    fill_digest(digest_b, 0x80u);
    storage_blank(&memory);
    storage = storage_api(&memory);
    state = empty_state();

    assert(xsw_ab_bootstrap(&storage, &state, XSW_AB_SLOT_A_V1, digest_a) == XS_STATUS_OK);
    assert(state.active_slot == XSW_AB_SLOT_A_V1);
    assert(state.generation == 1u);
    assert(state.rollback_available == 0u);
    assert(xsw_ab_candidate_slot(&state, &candidate_slot) == XS_STATUS_OK);
    assert(candidate_slot == XSW_AB_SLOT_B_V1);

    /* 1. Crash before candidate write begins: activation metadata is unchanged. */
    ++power_loss_cases;
    assert_pre_activation_crash_keeps_a(&memory, &storage, digest_a);

    /* 2. Crash during candidate image/pack write: journal has not been touched. */
    ++power_loss_cases;
    assert_pre_activation_crash_keeps_a(&memory, &storage, digest_a);

    /* 3. Crash after candidate write, before product authentication/digest check. */
    ++power_loss_cases;
    assert_pre_activation_crash_keeps_a(&memory, &storage, digest_a);

    /* 4. Crash after authentication, before ExactScope validation/smoke corpus. */
    ++power_loss_cases;
    assert_pre_activation_crash_keeps_a(&memory, &storage, digest_a);

    /* 5. Crash after validation, before activation journal write. */
    ++power_loss_cases;
    assert_pre_activation_crash_keeps_a(&memory, &storage, digest_a);

    /* 6. Metadata write fails: old durable copy remains authoritative. */
    ++power_loss_cases;
    memory.fail_write = 1;
    assert(
        xsw_ab_commit_validated_candidate(&storage, &state, XSW_AB_SLOT_B_V1, digest_b)
        == XS_STATUS_INTERNAL_ERROR);
    assert_pre_activation_crash_keeps_a(&memory, &storage, digest_a);

    /* 7. Durability barrier fails: staged metadata is discarded by simulated crash. */
    ++power_loss_cases;
    memory.fail_flush = 1;
    assert(
        xsw_ab_commit_validated_candidate(&storage, &state, XSW_AB_SLOT_B_V1, digest_b)
        == XS_STATUS_INTERNAL_ERROR);
    assert_pre_activation_crash_keeps_a(&memory, &storage, digest_a);

    /* 8. Torn new journal record becomes durable: CRC rejects it, old copy wins. */
    ++power_loss_cases;
    memory.tear_write = 1;
    assert(
        xsw_ab_commit_validated_candidate(&storage, &state, XSW_AB_SLOT_B_V1, digest_b)
        == XS_STATUS_INTEGRITY_ERROR);
    storage_crash(&memory);
    assert_recovered(&storage, XSW_AB_SLOT_A_V1, 1u, 0u, digest_a);

    /* Reconstruct RAM state after fault injection before the successful commit. */
    state = empty_state();
    assert(xsw_ab_recover(&storage, &state) == XS_STATUS_OK);

    /* 9. Successful activation commit survives crash and retains slot A for rollback. */
    ++power_loss_cases;
    assert(
        xsw_ab_commit_validated_candidate(&storage, &state, XSW_AB_SLOT_B_V1, digest_b)
        == XS_STATUS_OK);
    assert(state.active_slot == XSW_AB_SLOT_B_V1);
    assert(state.previous_slot == XSW_AB_SLOT_A_V1);
    assert(state.generation == 2u);
    assert(state.rollback_available == 1u);
    assert(xsw_ab_candidate_slot(&state, &candidate_slot) == XS_STATUS_INVALID_REQUEST);
    storage_crash(&memory);
    assert_recovered(&storage, XSW_AB_SLOT_B_V1, 2u, 1u, digest_b);

    /* A corrupt older copy cannot displace the valid newer committed generation. */
    memory.durable[0][0] ^= 0x01u;
    assert_recovered(&storage, XSW_AB_SLOT_B_V1, 2u, 1u, digest_b);

    /* Rollback is itself a durable generation; no recompilation is involved. */
    state = empty_state();
    assert(xsw_ab_recover(&storage, &state) == XS_STATUS_OK);
    assert(xsw_ab_rollback(&storage, &state) == XS_STATUS_OK);
    assert(state.active_slot == XSW_AB_SLOT_A_V1);
    assert(state.generation == 3u);
    assert(state.rollback_available == 0u);
    assert_digest(state.active_digest, digest_a);
    assert(xsw_ab_candidate_slot(&state, &candidate_slot) == XS_STATUS_OK);
    assert(candidate_slot == XSW_AB_SLOT_B_V1);

    /* Re-activate B and accept it, releasing A for the next candidate overwrite. */
    assert(
        xsw_ab_commit_validated_candidate(&storage, &state, XSW_AB_SLOT_B_V1, digest_b)
        == XS_STATUS_OK);
    assert(state.generation == 4u);
    stale = state;
    assert(xsw_ab_accept_active(&storage, &state) == XS_STATUS_OK);
    assert(state.generation == 5u);
    assert(state.active_slot == XSW_AB_SLOT_B_V1);
    assert(state.rollback_available == 0u);
    assert(xsw_ab_candidate_slot(&state, &candidate_slot) == XS_STATUS_OK);
    assert(candidate_slot == XSW_AB_SLOT_A_V1);

    /* A stale in-RAM decision cannot overwrite a newer durable generation. */
    assert(xsw_ab_accept_active(&storage, &stale) == XS_STATUS_INVALID_REQUEST);

    printf("wearable A/B journal: PASS (%u power-loss/activation cases)\n", power_loss_cases);
    return 0;
}
