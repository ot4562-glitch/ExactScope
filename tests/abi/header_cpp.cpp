#include "exactscope.h"
#include "exactscope_wasm.h"

#include <type_traits>

static_assert(std::is_standard_layout<xs_decimal_v1>::value,
              "public ExactScope values must have standard layout");
static_assert(sizeof(xs_decimal_v1) == 16u, "decimal ABI size drift");
static_assert(sizeof(xs_plan_value_v1) == 32u, "plan value ABI size drift");
static_assert(sizeof(xs_plan_step_v1) == 80u, "plan step ABI size drift");
static_assert(sizeof(xs_plan_result_v1) == 48u, "plan result ABI size drift");
static_assert(sizeof(xs_wasm_io_meta_v1) == 16u, "wasm metadata ABI size drift");
static_assert(XS_PLAN_OP_ADD_V1 == 0u && XS_PLAN_OP_SQRT_V1 == 5u,
              "plan operation constants drift");
static_assert(XS_PLAN_VALUE_LITERAL_V1 == 0u && XS_PLAN_VALUE_PREVIOUS_V1 == 1u,
              "plan value kind constants drift");

int exactscope_header_cpp11_smoke() noexcept {
    xs_eval_options_v1 options{};
    xs_plan_result_v1 result{};
    xs_status (*calc_fn)(xs_context *, const xs_plan_step_v1 *, uint16_t,
                         xs_plan_result_v1 *) = &xs_calc;
    options.struct_size = static_cast<uint32_t>(sizeof(options));
    options.output_scale = XS_USE_OPERATION_SCALE_V1;
    options.rounding_mode = XS_USE_OPERATION_ROUNDING_V1;
    result.struct_size = static_cast<uint32_t>(sizeof(result));
    return static_cast<int>(options.flags + result.status + (calc_fn == nullptr));
}
