/*
 * ExactScope no-import WebAssembly helper ABI design baseline v1.0.
 *
 * SPDX-License-Identifier: MIT OR Apache-2.0
 */
#ifndef EXACTSCOPE_WASM_H_INCLUDED
#define EXACTSCOPE_WASM_H_INCLUDED

#include "exactscope.h"

#define XS_WIRE_FORMAT_TINY_JSON_V1 1u
#define XS_WIRE_FORMAT_TINY_CBOR_V1 2u
#define XS_WASM_IO_META_FLAG_OUTPUT_WRITTEN_V1 0x0001u

typedef struct xs_wasm_io_meta_v1 {
    uint32_t struct_size;
    uint16_t status;
    uint16_t flags;
    uint32_t written;
    uint32_t required;
} xs_wasm_io_meta_v1;

/*
 * These functions are exports of the fused wasm32v1-none artifact. Pointer
 * parameters are 32-bit offsets into the module's exported linear memory.
 */
XS_API uint32_t XS_CALL xs_wasm_reserved_end(void) XS_NOEXCEPT;
XS_API uint32_t XS_CALL xs_wasm_memory_alignment(void) XS_NOEXCEPT;
XS_API xs_status XS_CALL xs_wire_request(
    uint32_t wire_format,
    uint32_t input_offset,
    uint32_t input_len,
    uint32_t output_offset,
    uint32_t output_capacity,
    uint32_t meta_offset) XS_NOEXCEPT;

#if defined(__cplusplus) && __cplusplus >= 201103L
static_assert(sizeof(xs_wasm_io_meta_v1) == 16u,
              "xs_wasm_io_meta_v1 ABI size must be 16 bytes");
#elif defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
_Static_assert(sizeof(xs_wasm_io_meta_v1) == 16u,
               "xs_wasm_io_meta_v1 ABI size must be 16 bytes");
#endif

#endif /* EXACTSCOPE_WASM_H_INCLUDED */
