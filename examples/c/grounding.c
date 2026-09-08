#include "exactscope.h"
#include "exactscope_platform.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void XS_CALL xs_platform_panic_abort(void) XS_NOEXCEPT {
    abort();
}

static void fail(const char *message) {
    fprintf(stderr, "ExactScope grounding demo: %s\n", message);
    exit(1);
}

static void fail_status(const char *operation, xs_status status) {
    fprintf(stderr, "ExactScope grounding demo: %s failed with status %u\n",
            operation, (unsigned)status);
    exit(1);
}

static uint8_t *read_file(const char *path, uint32_t *out_len) {
    FILE *file = fopen(path, "rb");
    long length;
    uint8_t *bytes;

    if (file == NULL) {
        fail("cannot open index file");
    }
    if (fseek(file, 0L, SEEK_END) != 0) {
        fclose(file);
        fail("cannot seek index file");
    }
    length = ftell(file);
    if (length <= 0 || (unsigned long)length > UINT32_MAX) {
        fclose(file);
        fail("index file size is invalid");
    }
    if (fseek(file, 0L, SEEK_SET) != 0) {
        fclose(file);
        fail("cannot rewind index file");
    }

    bytes = (uint8_t *)malloc((size_t)length);
    if (bytes == NULL) {
        fclose(file);
        fail("cannot allocate index buffer");
    }
    if (fread(bytes, 1u, (size_t)length, file) != (size_t)length) {
        free(bytes);
        fclose(file);
        fail("cannot read complete index file");
    }
    if (fclose(file) != 0) {
        free(bytes);
        fail("cannot close index file");
    }
    *out_len = (uint32_t)length;
    return bytes;
}

int main(int argc, char **argv) {
    uint32_t index_len = 0;
    uint8_t *index_bytes;
    uint32_t handle_size;
    uint32_t handle_align;
    size_t handle_allocation;
    uint8_t *handle_storage;
    uintptr_t aligned_address;
    xs_grounding_index *index = NULL;
    uint32_t document_count = 0;
    xs_grounding_search_scratch_v1 *scratch;
    xs_grounding_search_hit_v1 hits[XS_GROUNDING_MAX_HITS_V1];
    xs_bytes_v1 query_tokens[XS_GROUNDING_MAX_QUERY_TOKENS_V1];
    uint16_t token_count;
    uint16_t hit_count = 0;
    uint8_t projection[4096];
    xs_grounding_projection_result_v1 projection_result = {0};
    xs_status status;
    int token_index;

    if (argc < 3) {
        fprintf(stderr,
                "usage: %s <index.xsgi> <normalized-query-token> [token ...]\n",
                argv[0]);
        return 2;
    }
    if ((unsigned)(argc - 2) > XS_GROUNDING_MAX_QUERY_TOKENS_V1) {
        fail("too many query tokens");
    }

    token_count = (uint16_t)(argc - 2);
    for (token_index = 0; token_index < (int)token_count; ++token_index) {
        const char *token = argv[token_index + 2];
        size_t token_len = strlen(token);
        if (token_len == 0u || token_len > XS_GROUNDING_MAX_TOKEN_BYTES_V1) {
            fail("query token length is invalid");
        }
        query_tokens[token_index].ptr = (const uint8_t *)token;
        query_tokens[token_index].len = (uint32_t)token_len;
    }

    index_bytes = read_file(argv[1], &index_len);
    handle_size = xs_grounding_index_size();
    handle_align = xs_grounding_index_align();
    if (handle_size == 0u || handle_align == 0u ||
        (handle_align & (handle_align - 1u)) != 0u) {
        free(index_bytes);
        fail("runtime returned an invalid grounding handle layout");
    }

    handle_allocation = (size_t)handle_size + (size_t)handle_align - 1u;
    handle_storage = (uint8_t *)malloc(handle_allocation);
    if (handle_storage == NULL) {
        free(index_bytes);
        fail("cannot allocate grounding handle storage");
    }
    aligned_address = ((uintptr_t)handle_storage + (uintptr_t)handle_align - 1u) &
                      ~((uintptr_t)handle_align - 1u);

    {
        xs_bytes_v1 xsgi = {index_bytes, index_len};
        status = xs_grounding_index_init((void *)aligned_address, handle_size, xsgi,
                                         &index, &document_count);
    }
    if (status != XS_STATUS_OK) {
        free(handle_storage);
        free(index_bytes);
        fail_status("index init", status);
    }

    scratch = (xs_grounding_search_scratch_v1 *)calloc(
        (size_t)document_count, sizeof(xs_grounding_search_scratch_v1));
    if (scratch == NULL) {
        free(handle_storage);
        free(index_bytes);
        fail("cannot allocate search scratch");
    }

    status = xs_grounding_index_search(index, query_tokens, token_count, scratch,
                                       document_count, hits, 4u, &hit_count);
    if (status != XS_STATUS_OK) {
        free(scratch);
        free(handle_storage);
        free(index_bytes);
        fail_status("search", status);
    }

    projection_result.struct_size = (uint32_t)sizeof(projection_result);
    status = xs_grounding_index_project(index, hits, hit_count, query_tokens,
                                        token_count, (uint32_t)sizeof(projection),
                                        2u, projection,
                                        (uint32_t)sizeof(projection),
                                        &projection_result);
    if (status != XS_STATUS_OK) {
        free(scratch);
        free(handle_storage);
        free(index_bytes);
        fail_status("projection", status);
    }

    if (projection_result.has_evidence == 0u) {
        puts("No evidence found.");
    } else {
        if (fwrite(projection, 1u, projection_result.written, stdout) !=
            projection_result.written) {
            free(scratch);
            free(handle_storage);
            free(index_bytes);
            fail("cannot write projection");
        }
        putchar('\n');
    }

    free(scratch);
    free(handle_storage);
    free(index_bytes);
    return 0;
}
