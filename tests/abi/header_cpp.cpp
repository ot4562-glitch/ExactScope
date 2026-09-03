#include "exactscope.h"
#include "exactscope_wasm.h"

#include <type_traits>

static_assert(std::is_standard_layout<xs_decimal_v1>::value,
              "public ExactScope values must have standard layout");
static_assert(sizeof(xs_decimal_v1) == 16u, "decimal ABI size drift");
static_assert(sizeof(xs_wasm_io_meta_v1) == 16u, "wasm metadata ABI size drift");

int exactscope_header_cpp11_smoke() noexcept {
    xs_eval_options_v1 options{};
    options.struct_size = static_cast<uint32_t>(sizeof(options));
    options.output_scale = XS_USE_OPERATION_SCALE_V1;
    options.rounding_mode = XS_USE_OPERATION_ROUNDING_V1;
    return static_cast<int>(options.flags);
}
