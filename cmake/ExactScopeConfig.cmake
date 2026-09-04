# ExactScope target-specific SDK package configuration.
#
# Usage:
#   find_package(ExactScope CONFIG REQUIRED PATHS <sdk-root> NO_DEFAULT_PATH)
#   target_link_libraries(my_target PRIVATE ExactScope::exactscope)
#
# The target carries only the public include directory and prebuilt ExactScope
# C ABI archive. Product code remains responsible for providing the documented
# xs_platform_panic_abort host symbol when using the standalone static profile.

if(TARGET ExactScope::exactscope)
    set(ExactScope_FOUND TRUE)
    return()
endif()

get_filename_component(_exactscope_prefix "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)

set(_exactscope_include_dir "${_exactscope_prefix}/include")
if(NOT EXISTS "${_exactscope_include_dir}/exactscope.h")
    set(ExactScope_FOUND FALSE)
    set(ExactScope_NOT_FOUND_MESSAGE "ExactScope SDK is missing include/exactscope.h")
    return()
endif()

file(GLOB _exactscope_archives LIST_DIRECTORIES FALSE
    "${_exactscope_prefix}/lib/*/libexactscope_cabi.a"
    "${_exactscope_prefix}/lib/*/exactscope_cabi.lib"
)
list(LENGTH _exactscope_archives _exactscope_archive_count)
if(NOT _exactscope_archive_count EQUAL 1)
    set(ExactScope_FOUND FALSE)
    set(ExactScope_NOT_FOUND_MESSAGE
        "ExactScope target-specific SDK must contain exactly one C ABI archive; found ${_exactscope_archive_count}"
    )
    return()
endif()

list(GET _exactscope_archives 0 _exactscope_archive)

add_library(ExactScope::exactscope STATIC IMPORTED)
set_target_properties(ExactScope::exactscope PROPERTIES
    IMPORTED_LOCATION "${_exactscope_archive}"
    INTERFACE_INCLUDE_DIRECTORIES "${_exactscope_include_dir}"
)

set(ExactScope_FOUND TRUE)
set(ExactScope_PACKAGE_ROOT "${_exactscope_prefix}")
set(ExactScope_LIBRARY "${_exactscope_archive}")
set(ExactScope_INCLUDE_DIR "${_exactscope_include_dir}")

unset(_exactscope_prefix)
unset(_exactscope_include_dir)
unset(_exactscope_archives)
unset(_exactscope_archive_count)
unset(_exactscope_archive)
