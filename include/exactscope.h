/*
 * ExactScope C ABI design baseline v1.0.
 *
 * This header freezes the intended portable ABI shape before runtime
 * implementation. No released library is claimed to implement it yet.
 *
 * SPDX-License-Identifier: MIT OR Apache-2.0
 */
#ifndef EXACTSCOPE_H_INCLUDED
#define EXACTSCOPE_H_INCLUDED

#include <stdint.h>

#if defined(_WIN32)
#  if defined(XS_BUILD_SHARED)
#    define XS_API __declspec(dllexport)
#  elif defined(XS_USE_SHARED)
#    define XS_API __declspec(dllimport)
#  else
#    define XS_API
#  endif
#  define XS_CALL __cdecl
#elif defined(__GNUC__) || defined(__clang__)
#  define XS_API __attribute__((visibility("default")))
#  define XS_CALL
#else
#  define XS_API
#  define XS_CALL
#endif

#if defined(__cplusplus)
#  if __cplusplus >= 201103L
#    define XS_NOEXCEPT noexcept
#  else
#    define XS_NOEXCEPT
#  endif
extern "C" {
#else
#  define XS_NOEXCEPT
#endif

#define XS_ABI_MAJOR_V1 1u
#define XS_ABI_MINOR_V1 0u
#define XS_ABI_VERSION_V1 0x00010000u

/* Stable core status codes. */
#define XS_STATUS_OK 0u
#define XS_STATUS_INVALID_REQUEST 1u
#define XS_STATUS_ABI_MISMATCH 2u
#define XS_STATUS_UNKNOWN_OPERATION 3u
#define XS_STATUS_UNKNOWN_PACK 4u
#define XS_STATUS_ARGUMENT_COUNT 5u
#define XS_STATUS_ARGUMENT_TYPE 6u
#define XS_STATUS_AMBIGUOUS_METHOD 7u
#define XS_STATUS_MISSING_INFORMATION 8u
#define XS_STATUS_INVALID_DECIMAL 9u
#define XS_STATUS_DOMAIN_ERROR 10u
#define XS_STATUS_CONSTRAINT_VIOLATION 11u
#define XS_STATUS_UNIT_MISMATCH 12u
#define XS_STATUS_DIVIDE_BY_ZERO 13u
#define XS_STATUS_OVERFLOW 14u
#define XS_STATUS_PRECISION_UNRESOLVED 15u
#define XS_STATUS_INSUFFICIENT_DATA 16u
#define XS_STATUS_BUFFER_TOO_SMALL 17u
#define XS_STATUS_PACK_INVALID 18u
#define XS_STATUS_PACK_VERSION_UNSUPPORTED 19u
#define XS_STATUS_RESOURCE_LIMIT 20u
#define XS_STATUS_UNSUPPORTED_OPERATION 21u
#define XS_STATUS_INTEGRITY_ERROR 22u
#define XS_STATUS_INTERNAL_ERROR 23u

/* Stable scalar semantic kinds. */
#define XS_SEMANTIC_NUMBER_V1 0u
#define XS_SEMANTIC_COUNT_V1 1u
#define XS_SEMANTIC_CURRENCY_AMOUNT_V1 2u
#define XS_SEMANTIC_PRICE_V1 3u
#define XS_SEMANTIC_QUANTITY_V1 4u
#define XS_SEMANTIC_RATE_PERCENT_V1 5u
#define XS_SEMANTIC_RATE_RATIO_V1 6u
#define XS_SEMANTIC_INDEX_V1 7u
#define XS_SEMANTIC_TIME_PERIODS_V1 8u
#define XS_SEMANTIC_PROBABILITY_V1 9u
#define XS_SEMANTIC_ELASTICITY_V1 10u

/* Stable rounding modes. */
#define XS_ROUND_HALF_EVEN_V1 0u
#define XS_ROUND_HALF_AWAY_V1 1u
#define XS_ROUND_TOWARD_ZERO_V1 2u
#define XS_ROUND_FLOOR_V1 3u
#define XS_ROUND_CEIL_V1 4u
#define XS_USE_OPERATION_ROUNDING_V1 255u
#define XS_USE_OPERATION_SCALE_V1 (-128)

/* Value and result flags. */
#define XS_VALUE_FLAG_INEXACT_V1 0x00000001u
#define XS_VALUE_FLAG_ROUNDED_V1 0x00000002u
#define XS_VALUE_SCALAR_V1 0u
#define XS_VALUE_VECTOR_V1 1u
#define XS_MAX_RESULT_VALUES_V1 4u
#define XS_ARGUMENT_INDEX_NONE_V1 0xffffu

/* Bounded arithmetic-plan constants. */
#define XS_PLAN_MAX_STEPS_V1 8u
#define XS_PLAN_MAX_ARGUMENTS_V1 2u
#define XS_PLAN_STEP_INDEX_NONE_V1 0xffu
#define XS_PLAN_VALUE_LITERAL_V1 0u
#define XS_PLAN_VALUE_PREVIOUS_V1 1u
#define XS_PLAN_OP_ADD_V1 0u
#define XS_PLAN_OP_SUB_V1 1u
#define XS_PLAN_OP_MUL_V1 2u
#define XS_PLAN_OP_DIV_V1 3u
#define XS_PLAN_OP_POWI_V1 4u
#define XS_PLAN_OP_SQRT_V1 5u

/* Context configuration flags. */
#define XS_CONFIG_ALLOW_DYNAMIC_PACKS_V1 0x0001u
#define XS_CONFIG_FREEZE_AFTER_INIT_V1 0x0002u
#define XS_CONFIG_ENABLE_DISCOVERY_V1 0x0004u

/* Evaluation flags. */
#define XS_EVAL_INCLUDE_PROVENANCE_V1 0x0001u
#define XS_EVAL_REQUIRE_CLASSIFICATION_V1 0x0002u

/* Match flags. */
#define XS_MATCH_TRUNCATED_V1 0x0001u

typedef uint16_t xs_status;
typedef struct xs_context xs_context;

typedef struct xs_bytes_v1 {
    const uint8_t* ptr;
    uint32_t len;
} xs_bytes_v1;

typedef struct xs_decimal_v1 {
    int64_t coefficient;
    int8_t exponent;
    uint8_t semantic_kind;
    uint16_t unit_id;
    uint32_t flags;
} xs_decimal_v1;

typedef struct xs_value_ref_v1 {
    uint32_t struct_size;
    uint8_t value_kind;
    uint8_t reserved0;
    uint16_t reserved1;
    const xs_decimal_v1* values;
    uint32_t value_count;
    uint32_t reserved2;
} xs_value_ref_v1;

typedef struct xs_plan_value_v1 {
    uint32_t struct_size;
    uint8_t value_kind;
    uint8_t previous_index;
    uint16_t reserved0;
    xs_decimal_v1 literal;
    uint32_t reserved[2];
} xs_plan_value_v1;

typedef struct xs_plan_step_v1 {
    uint32_t struct_size;
    uint8_t operation;
    uint8_t argument_count;
    uint16_t reserved0;
    xs_plan_value_v1 arguments[XS_PLAN_MAX_ARGUMENTS_V1];
    uint32_t reserved[2];
} xs_plan_step_v1;

typedef struct xs_plan_result_v1 {
    uint32_t struct_size;
    uint16_t status;
    uint16_t reserved0;
    uint32_t flags;
    uint8_t step_index;
    uint8_t step_count;
    uint16_t reserved1;
    xs_decimal_v1 value;
    uint32_t reserved[4];
} xs_plan_result_v1;

typedef struct xs_config_v1 {
    uint32_t struct_size;
    uint16_t abi_major;
    uint16_t abi_minor;
    uint16_t max_packs;
    uint16_t max_find_matches;
    uint16_t max_vector_len;
    uint16_t flags;
    uint32_t max_tinywire_frame;
    uint32_t reserved[3];
} xs_config_v1;

typedef struct xs_match_v1 {
    uint32_t struct_size;
    uint16_t pack_slot;
    uint16_t operation_revision;
    uint32_t operation_id;
    uint16_t rank;
    uint16_t flags;
    xs_bytes_v1 operation_key;
    xs_bytes_v1 signature;
    xs_bytes_v1 method_key;
    uint32_t reserved[2];
} xs_match_v1;

typedef struct xs_eval_options_v1 {
    uint32_t struct_size;
    int8_t output_scale;
    uint8_t rounding_mode;
    uint16_t flags;
    uint32_t reserved[3];
} xs_eval_options_v1;

typedef struct xs_result_v1 {
    uint32_t struct_size;
    uint16_t status;
    uint16_t flags;
    uint16_t value_count;
    uint16_t classification_id;
    uint16_t pack_slot;
    uint16_t operation_revision;
    uint32_t operation_id;
    int8_t output_scale;
    uint8_t rounding_mode;
    uint16_t detail_code;
    uint16_t argument_index;
    uint16_t reserved0;
    uint32_t required_size;
    xs_decimal_v1 values[XS_MAX_RESULT_VALUES_V1];
    uint32_t reserved[4];
} xs_result_v1;

XS_API uint32_t XS_CALL xs_abi_version(void) XS_NOEXCEPT;
XS_API xs_status XS_CALL xs_decimal_parse_ascii(
    const uint8_t* text,
    uint32_t text_len,
    uint8_t semantic_kind,
    uint16_t unit_id,
    xs_decimal_v1* out_value) XS_NOEXCEPT;
XS_API uint32_t XS_CALL xs_context_align(void) XS_NOEXCEPT;
XS_API uint32_t XS_CALL xs_context_size(const xs_config_v1* config) XS_NOEXCEPT;
XS_API xs_status XS_CALL xs_context_init(
    void* memory,
    uint32_t memory_len,
    const xs_config_v1* config,
    xs_context** out_context) XS_NOEXCEPT;
XS_API xs_status XS_CALL xs_context_reset(xs_context* context) XS_NOEXCEPT;

XS_API xs_status XS_CALL xs_pack_mount(
    xs_context* context,
    const uint8_t* pack_bytes,
    uint32_t pack_len,
    void* arena,
    uint32_t arena_len,
    uint16_t* out_pack_slot,
    uint32_t* required_arena_len) XS_NOEXCEPT;
XS_API xs_status XS_CALL xs_pack_unmount(
    xs_context* context,
    uint16_t pack_slot) XS_NOEXCEPT;
XS_API xs_status XS_CALL xs_registry_freeze(xs_context* context) XS_NOEXCEPT;

XS_API xs_status XS_CALL xs_lookup(
    xs_context* context,
    const uint8_t* operation_key,
    uint32_t operation_key_len,
    uint16_t* out_pack_slot,
    uint32_t* out_operation_id,
    uint16_t* out_operation_revision) XS_NOEXCEPT;

/*
 * On OK, out_match_count is the number written. On BUFFER_TOO_SMALL it is the
 * full required count and no match entry is semantically usable.
 */
XS_API xs_status XS_CALL xs_find(
    xs_context* context,
    const uint8_t* query,
    uint32_t query_len,
    xs_match_v1* matches,
    uint16_t match_capacity,
    uint16_t* out_match_count) XS_NOEXCEPT;

XS_API xs_status XS_CALL xs_calc(
    xs_context* context,
    const xs_plan_step_v1* steps,
    uint16_t step_count,
    xs_plan_result_v1* out_result) XS_NOEXCEPT;

XS_API xs_status XS_CALL xs_eval(
    xs_context* context,
    uint16_t pack_slot,
    uint32_t operation_id,
    const xs_value_ref_v1* args,
    uint16_t arg_count,
    const xs_eval_options_v1* options,
    void* scratch,
    uint32_t scratch_len,
    xs_result_v1* out_result) XS_NOEXCEPT;

XS_API xs_status XS_CALL xs_result_json(
    xs_context* context,
    const xs_result_v1* result,
    uint8_t* output,
    uint32_t output_capacity,
    uint32_t* out_written_or_required) XS_NOEXCEPT;
XS_API xs_status XS_CALL xs_match_json(
    const xs_match_v1* matches,
    uint16_t match_count,
    uint8_t* output,
    uint32_t output_capacity,
    uint32_t* out_written_or_required) XS_NOEXCEPT;

#if defined(__cplusplus)
} /* extern "C" */
#endif

#if defined(__cplusplus) && __cplusplus >= 201103L
static_assert(sizeof(xs_decimal_v1) == 16u, "xs_decimal_v1 ABI size must be 16 bytes");
static_assert(sizeof(xs_plan_value_v1) == 32u, "xs_plan_value_v1 ABI size must be 32 bytes");
static_assert(sizeof(xs_plan_step_v1) == 80u, "xs_plan_step_v1 ABI size must be 80 bytes");
static_assert(sizeof(xs_plan_result_v1) == 48u, "xs_plan_result_v1 ABI size must be 48 bytes");
#elif defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
_Static_assert(sizeof(xs_decimal_v1) == 16u, "xs_decimal_v1 ABI size must be 16 bytes");
_Static_assert(sizeof(xs_plan_value_v1) == 32u, "xs_plan_value_v1 ABI size must be 32 bytes");
_Static_assert(sizeof(xs_plan_step_v1) == 80u, "xs_plan_step_v1 ABI size must be 80 bytes");
_Static_assert(sizeof(xs_plan_result_v1) == 48u, "xs_plan_result_v1 ABI size must be 48 bytes");
#endif

#endif /* EXACTSCOPE_H_INCLUDED */
