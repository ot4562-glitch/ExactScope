#include "exactscope.h"
#include "exactscope_wasm.h"

int exactscope_header_c99_smoke(void) {
    xs_config_v1 config = {0};
    xs_decimal_v1 value = {0};
    xs_result_v1 result = {0};
    xs_wasm_io_meta_v1 meta = {0};

    config.struct_size = (uint32_t)sizeof(config);
    config.abi_major = XS_ABI_MAJOR_V1;
    config.abi_minor = XS_ABI_MINOR_V1;
    value.semantic_kind = XS_SEMANTIC_NUMBER_V1;
    result.struct_size = (uint32_t)sizeof(result);
    meta.struct_size = (uint32_t)sizeof(meta);

    return (int)(config.abi_major + value.semantic_kind + result.status + meta.status);
}
