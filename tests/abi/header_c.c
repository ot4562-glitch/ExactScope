#include "exactscope.h"
#include "exactscope_wasm.h"

_Static_assert(sizeof(xs_decimal_v1) == 16u, "decimal ABI size drift");
_Static_assert(sizeof(xs_plan_value_v1) == 32u, "plan value ABI size drift");
_Static_assert(sizeof(xs_plan_step_v1) == 80u, "plan step ABI size drift");
_Static_assert(sizeof(xs_plan_result_v1) == 48u, "plan result ABI size drift");
_Static_assert(XS_PLAN_OP_ADD_V1 == 0u && XS_PLAN_OP_SQRT_V1 == 5u,
               "plan operation constants drift");
_Static_assert(XS_PLAN_VALUE_LITERAL_V1 == 0u && XS_PLAN_VALUE_PREVIOUS_V1 == 1u,
               "plan value kind constants drift");

int exactscope_header_c11_smoke(void) {
    xs_config_v1 config = {0};
    xs_decimal_v1 value = {0};
    xs_result_v1 result = {0};
    xs_wasm_io_meta_v1 meta = {0};
    xs_plan_step_v1 step = {0};
    xs_plan_result_v1 plan_result = {0};
    xs_status (*calc_fn)(xs_context *, const xs_plan_step_v1 *, uint16_t,
                         xs_plan_result_v1 *) = &xs_calc;

    config.struct_size = (uint32_t)sizeof(config);
    config.abi_major = XS_ABI_MAJOR_V1;
    config.abi_minor = XS_ABI_MINOR_V1;
    value.semantic_kind = XS_SEMANTIC_NUMBER_V1;
    result.struct_size = (uint32_t)sizeof(result);
    meta.struct_size = (uint32_t)sizeof(meta);

    step.struct_size = (uint32_t)sizeof(step);
    plan_result.struct_size = (uint32_t)sizeof(plan_result);

    return (int)(config.abi_major + value.semantic_kind + result.status + meta.status +
                 step.operation + plan_result.status + (calc_fn == 0));
}
