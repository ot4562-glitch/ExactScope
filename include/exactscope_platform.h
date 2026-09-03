/*
 * ExactScope standalone native platform hooks v1.
 *
 * These hooks are required only when exactscope-cabi is emitted as a
 * standalone no_std static library with the standalone-staticlib feature.
 *
 * SPDX-License-Identifier: MIT OR Apache-2.0
 */
#ifndef EXACTSCOPE_PLATFORM_H_INCLUDED
#define EXACTSCOPE_PLATFORM_H_INCLUDED

#include "exactscope.h"

#if defined(__cplusplus)
extern "C" {
#endif

/*
 * Host-supplied fatal panic hook.
 *
 * This function MUST NOT return. Production hosts should terminate or reset
 * only the owning process/component according to the product watchdog policy.
 * ExactScope does not call this hook for validated user/model input failures;
 * such failures are returned as xs_status values. Reaching this hook indicates
 * an internal defect or violated unsafe/ABI invariant and is release-blocking.
 */
void XS_CALL xs_platform_panic_abort(void) XS_NOEXCEPT;

#if defined(__cplusplus)
} /* extern "C" */
#endif

#endif /* EXACTSCOPE_PLATFORM_H_INCLUDED */
