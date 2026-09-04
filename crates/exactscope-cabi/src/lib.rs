#![no_std]
#![doc = "Stable fused `ExactScope` C ABI implementation."]

//! This crate is the native portability boundary for the first implementation
//! slice. All raw-pointer handling is isolated here; deterministic calculation
//! remains in `exactscope-kernel` and fused identity/discovery remains in
//! `exactscope-pack`.

#[cfg(all(feature = "standalone-staticlib", not(test)))]
use core::panic::PanicInfo;
use core::{
    ffi::c_void,
    mem::{align_of, size_of},
    ptr, slice,
};

#[cfg(all(feature = "standalone-staticlib", not(test)))]
unsafe extern "C" {
    fn xs_platform_panic_abort() -> !;
}

#[cfg(all(feature = "standalone-staticlib", not(test)))]
#[panic_handler]
fn panic(_info: &PanicInfo<'_>) -> ! {
    unsafe { xs_platform_panic_abort() }
}

/// Abort-only exception personality for the standalone `no_std` static library.
///
/// ExactScope exports non-unwinding C ABI functions and does not support a
/// foreign exception crossing a Rust frame. Some hosted targets still retain a
/// `rust_eh_personality` reference even with `panic=abort`; satisfying that
/// reference with an aborting symbol keeps the library self-contained without
/// linking `std` or an unwinding runtime. Reaching this function is therefore a
/// fatal integration/runtime defect, not a recoverable calculation error.
#[cfg(all(feature = "standalone-staticlib", not(test)))]
#[unsafe(no_mangle)]
pub extern "C" fn rust_eh_personality() -> ! {
    unsafe { xs_platform_panic_abort() }
}

use exactscope_kernel::{
    evaluate_operation, Decimal64, EvaluationResult, ScalarValue, Status, ARGUMENT_INDEX_NONE,
    MAX_RESULT_VALUES, SEMANTIC_ELASTICITY,
};
use exactscope_pack::{empty_matches, FusedRegistry, ECON_UNDERGRAD_PACK_SLOT};
#[cfg(feature = "dynamic-packs")]
use exactscope_pack::{PackView, ECON_UNDERGRAD_PACK_ID};

pub use exactscope_kernel::{DESIGN_ABI_MAJOR, DESIGN_ABI_MINOR};

const CONTEXT_MAGIC: u32 = 0x5853_4331;
const ABI_VERSION: u32 = 0x0001_0000;
const CONFIG_ALLOW_DYNAMIC_PACKS: u16 = 0x0001;
const CONFIG_FREEZE_AFTER_INIT: u16 = 0x0002;
const CONFIG_ENABLE_DISCOVERY: u16 = 0x0004;
const CONFIG_KNOWN_FLAGS: u16 =
    CONFIG_ALLOW_DYNAMIC_PACKS | CONFIG_FREEZE_AFTER_INIT | CONFIG_ENABLE_DISCOVERY;
const EVAL_INCLUDE_PROVENANCE: u16 = 0x0001;
const EVAL_REQUIRE_CLASSIFICATION: u16 = 0x0002;
const EVAL_KNOWN_FLAGS: u16 = EVAL_INCLUDE_PROVENANCE | EVAL_REQUIRE_CLASSIFICATION;
const VALUE_SCALAR: u8 = 0;
const USE_OPERATION_SCALE: i8 = -128;
const USE_OPERATION_ROUNDING: u8 = 255;
#[cfg(feature = "dynamic-packs")]
const MAX_PACKS: usize = 8;
#[cfg(feature = "dynamic-packs")]
const FIRST_DYNAMIC_PACK_SLOT: u16 = 2;

#[cfg(feature = "dynamic-packs")]
#[derive(Clone, Copy)]
struct DynamicSlot {
    bytes: *const u8,
    len: u32,
}

#[cfg(feature = "dynamic-packs")]
impl DynamicSlot {
    const EMPTY: Self = Self {
        bytes: ptr::null(),
        len: 0,
    };

    const fn is_empty(self) -> bool {
        self.len == 0
    }
}

/// Opaque caller-owned context backing the C `xs_context` forward declaration.
#[repr(C)]
pub struct XsContext {
    magic: u32,
    config_flags: u16,
    max_find_matches: u16,
    max_vector_len: u16,
    #[cfg(feature = "dynamic-packs")]
    max_packs: u16,
    frozen: u8,
    reserved0: u8,
    reserved1: u32,
    #[cfg(feature = "dynamic-packs")]
    dynamic_slots: [DynamicSlot; MAX_PACKS],
}

/// Borrowed byte slice used by metadata results.
#[repr(C)]
#[derive(Clone, Copy)]
pub struct XsBytesV1 {
    /// Borrowed byte pointer.
    pub ptr: *const u8,
    /// Byte length.
    pub len: u32,
}

impl XsBytesV1 {
    #[cfg(test)]
    const EMPTY: Self = Self {
        ptr: ptr::null(),
        len: 0,
    };

    fn from_static(value: &'static str) -> Result<Self, Status> {
        Ok(Self {
            ptr: value.as_ptr(),
            len: u32::try_from(value.len()).map_err(|_| Status::RESOURCE_LIMIT)?,
        })
    }
}

/// Stable C decimal layout.
#[repr(C)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct XsDecimalV1 {
    /// Signed decimal coefficient.
    pub coefficient: i64,
    /// Base-10 exponent.
    pub exponent: i8,
    /// Stable scalar semantic kind.
    pub semantic_kind: u8,
    /// Registry-local unit identity, zero when unspecified.
    pub unit_id: u16,
    /// Stable value flags.
    pub flags: u32,
}

impl XsDecimalV1 {
    const ZERO: Self = Self {
        coefficient: 0,
        exponent: 0,
        semantic_kind: 0,
        unit_id: 0,
        flags: 0,
    };
}

/// C scalar/vector argument reference.
#[repr(C)]
pub struct XsValueRefV1 {
    /// Caller structure size.
    pub struct_size: u32,
    /// Zero for scalar, one for vector.
    pub value_kind: u8,
    /// Reserved zero.
    pub reserved0: u8,
    /// Reserved zero.
    pub reserved1: u16,
    /// Pointer to one or more decimal values.
    pub values: *const XsDecimalV1,
    /// Number of pointed-to values.
    pub value_count: u32,
    /// Reserved zero.
    pub reserved2: u32,
}

/// C context configuration.
#[repr(C)]
pub struct XsConfigV1 {
    /// Caller structure size.
    pub struct_size: u32,
    /// Requested ABI major.
    pub abi_major: u16,
    /// Requested ABI minor.
    pub abi_minor: u16,
    /// Maximum mounted packs.
    pub max_packs: u16,
    /// Maximum discovery matches.
    pub max_find_matches: u16,
    /// Maximum vector length.
    pub max_vector_len: u16,
    /// Configuration flags.
    pub flags: u16,
    /// `TinyWire` frame cap reserved for compatible adapters.
    pub max_tinywire_frame: u32,
    /// Reserved zero fields.
    pub reserved: [u32; 3],
}

/// C discovery match structure.
#[repr(C)]
pub struct XsMatchV1 {
    /// Caller structure size.
    pub struct_size: u32,
    /// Mounted pack slot.
    pub pack_slot: u16,
    /// Immutable operation revision.
    pub operation_revision: u16,
    /// Pack-local operation ID.
    pub operation_id: u32,
    /// Deterministic rank.
    pub rank: u16,
    /// Match flags.
    pub flags: u16,
    /// Borrowed canonical operation key.
    pub operation_key: XsBytesV1,
    /// Borrowed compact signature.
    pub signature: XsBytesV1,
    /// Borrowed method key.
    pub method_key: XsBytesV1,
    /// Reserved zero fields.
    pub reserved: [u32; 2],
}

/// C evaluation options.
#[repr(C)]
pub struct XsEvalOptionsV1 {
    /// Caller structure size.
    pub struct_size: u32,
    /// Requested scale or operation-default sentinel.
    pub output_scale: i8,
    /// Requested rounding mode or operation-default sentinel.
    pub rounding_mode: u8,
    /// Evaluation flags.
    pub flags: u16,
    /// Reserved zero fields.
    pub reserved: [u32; 3],
}

/// C evaluation result.
#[repr(C)]
pub struct XsResultV1 {
    /// Caller structure size.
    pub struct_size: u32,
    /// Stable core status.
    pub status: u16,
    /// Aggregate result flags.
    pub flags: u16,
    /// Number of usable result values.
    pub value_count: u16,
    /// Operation-local classification ID.
    pub classification_id: u16,
    /// Mounted pack slot.
    pub pack_slot: u16,
    /// Immutable operation revision.
    pub operation_revision: u16,
    /// Pack-local operation ID.
    pub operation_id: u32,
    /// Effective output scale.
    pub output_scale: i8,
    /// Effective rounding mode.
    pub rounding_mode: u8,
    /// Operation-local error detail code.
    pub detail_code: u16,
    /// Zero-based failing argument index or `0xffff`.
    pub argument_index: u16,
    /// Reserved zero.
    pub reserved0: u16,
    /// Required storage size for sizing failures.
    pub required_size: u32,
    /// Fixed scalar result storage.
    pub values: [XsDecimalV1; 4],
    /// Reserved zero fields.
    pub reserved: [u32; 4],
}

impl XsResultV1 {
    fn empty(struct_size: u32, status: Status) -> Self {
        Self {
            struct_size,
            status: status.code(),
            flags: 0,
            value_count: 0,
            classification_id: 0,
            pack_slot: 0,
            operation_revision: 0,
            operation_id: 0,
            output_scale: 0,
            rounding_mode: 0,
            detail_code: 0,
            argument_index: ARGUMENT_INDEX_NONE,
            reserved0: 0,
            required_size: 0,
            values: [XsDecimalV1::ZERO; 4],
            reserved: [0; 4],
        }
    }
}

/// Returns the encoded ABI version `(major << 16) | minor`.
#[unsafe(no_mangle)]
pub extern "C" fn xs_abi_version() -> u32 {
    ABI_VERSION
}

/// Parses strict `ExactScope` ASCII decimal text into canonical C representation.
///
/// The output is zeroed before validation so callers never observe a plausible
/// value after a failed parse. Parsing is exact base-10 and never uses host
/// binary floating point.
///
/// # Safety
///
/// `out_value` must be a valid writable aligned pointer. For nonzero
/// `text_len`, `text` must point to `text_len` readable bytes for this call.
/// The input byte range must not overlap `out_value`.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn xs_decimal_parse_ascii(
    text: *const u8,
    text_len: u32,
    semantic_kind: u8,
    unit_id: u16,
    out_value: *mut XsDecimalV1,
) -> u16 {
    if out_value.is_null() || !out_value.is_aligned() {
        return Status::INVALID_REQUEST.code();
    }
    unsafe { out_value.write(XsDecimalV1::ZERO) };
    if semantic_kind > SEMANTIC_ELASTICITY {
        return Status::ARGUMENT_TYPE.code();
    }
    let text = match unsafe { byte_slice(text, text_len, true) } {
        Ok(text) => text,
        Err(status) => return status.code(),
    };
    let decimal = match Decimal64::parse_ascii(text) {
        Ok(decimal) => decimal,
        Err(status) => return status.code(),
    };
    let value = ScalarValue::new(decimal, semantic_kind, unit_id);
    if let Err(status) = value.validate() {
        return status.code();
    }
    unsafe {
        out_value.write(XsDecimalV1 {
            coefficient: decimal.coefficient(),
            exponent: decimal.exponent(),
            semantic_kind,
            unit_id,
            flags: 0,
        });
    };
    Status::OK.code()
}

/// Returns the required alignment of caller-owned context memory.
#[unsafe(no_mangle)]
pub extern "C" fn xs_context_align() -> u32 {
    u32::try_from(align_of::<XsContext>()).unwrap_or(0)
}

/// Returns the required context byte size, or zero for invalid/unsupported config.
///
/// # Safety
///
/// When non-null, `config` must point to a readable `XsConfigV1` whose lifetime
/// covers this call.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn xs_context_size(config: *const XsConfigV1) -> u32 {
    let Ok(config) = (unsafe { read_config(config) }) else {
        return 0;
    };
    if validate_config(config).is_err() {
        return 0;
    }
    u32::try_from(size_of::<XsContext>()).unwrap_or(0)
}

/// Initializes one context entirely inside caller-owned memory.
///
/// # Safety
///
/// `memory` must designate writable memory of `memory_len` bytes and remain
/// alive until the returned context is no longer used. `config` and
/// `out_context` must be valid readable/writable pointers for this call. These
/// regions must not overlap in a way that violates Rust aliasing rules.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn xs_context_init(
    memory: *mut c_void,
    memory_len: u32,
    config: *const XsConfigV1,
    out_context: *mut *mut XsContext,
) -> u16 {
    if !valid_mut_ptr(out_context) {
        return Status::INVALID_REQUEST.code();
    }
    unsafe { out_context.write(ptr::null_mut()) };

    let config = match unsafe { read_config(config) } {
        Ok(config) => config,
        Err(status) => return status.code(),
    };
    if let Err(status) = validate_config(config) {
        return status.code();
    }

    let required = size_u32::<XsContext>();
    if memory_len < required {
        return Status::BUFFER_TOO_SMALL.code();
    }
    let context_ptr = memory.cast::<XsContext>();
    if memory.is_null() || !context_ptr.is_aligned() {
        return Status::INVALID_REQUEST.code();
    }

    let context = XsContext {
        magic: CONTEXT_MAGIC,
        config_flags: config.flags,
        max_find_matches: config.max_find_matches,
        max_vector_len: config.max_vector_len,
        #[cfg(feature = "dynamic-packs")]
        max_packs: config.max_packs,
        frozen: u8::from(config.flags & CONFIG_FREEZE_AFTER_INIT != 0),
        reserved0: 0,
        reserved1: 0,
        #[cfg(feature = "dynamic-packs")]
        dynamic_slots: [DynamicSlot::EMPTY; MAX_PACKS],
    };
    unsafe { context_ptr.write(context) };
    unsafe { out_context.write(context_ptr) };
    Status::OK.code()
}

/// Resets mutable context state while preserving fused tables.
///
/// # Safety
///
/// `context` must be a context previously initialized by this library and not
/// concurrently accessed.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn xs_context_reset(context: *mut XsContext) -> u16 {
    let context = match unsafe { context_mut(context) } {
        Ok(context) => context,
        Err(status) => return status.code(),
    };
    context.frozen = u8::from(context.config_flags & CONFIG_FREEZE_AFTER_INIT != 0);
    #[cfg(feature = "dynamic-packs")]
    {
        context.dynamic_slots = [DynamicSlot::EMPTY; MAX_PACKS];
    }
    Status::OK.code()
}

/// Validates and mounts one caller-owned immutable `.xsp` pack.
///
/// Dynamic-pack builds use the pack's prebuilt tables directly, so the first
/// formula slice requires zero arena bytes. Fused-only builds return
/// [`Status::UNSUPPORTED_OPERATION`].
///
/// # Safety
///
/// `context`, `out_pack_slot`, and `required_arena_len` must satisfy the public
/// C ABI pointer contract. `pack_bytes` must remain readable, immutable, and
/// alive until unmount/reset. When `arena_len` is nonzero, `arena` must be
/// non-null even though this zero-copy slice does not retain or dereference it.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn xs_pack_mount(
    context: *mut XsContext,
    pack_bytes: *const u8,
    pack_len: u32,
    arena: *mut c_void,
    arena_len: u32,
    out_pack_slot: *mut u16,
    required_arena_len: *mut u32,
) -> u16 {
    let context = match unsafe { context_mut(context) } {
        Ok(context) => context,
        Err(status) => return status.code(),
    };
    if !valid_mut_ptr(out_pack_slot) || !valid_mut_ptr(required_arena_len) {
        return Status::INVALID_REQUEST.code();
    }
    unsafe {
        out_pack_slot.write(0);
        required_arena_len.write(0);
    }

    #[cfg(not(feature = "dynamic-packs"))]
    {
        let _ = (context, pack_bytes, pack_len, arena, arena_len);
        Status::UNSUPPORTED_OPERATION.code()
    }

    #[cfg(feature = "dynamic-packs")]
    {
        if context.config_flags & CONFIG_ALLOW_DYNAMIC_PACKS == 0 {
            return Status::UNSUPPORTED_OPERATION.code();
        }
        if context.frozen != 0 || (arena.is_null() && arena_len != 0) {
            return Status::INVALID_REQUEST.code();
        }
        let bytes = match unsafe { byte_slice(pack_bytes, pack_len, false) } {
            Ok(bytes) => bytes,
            Err(status) => return status.code(),
        };
        let pack = match PackView::parse(bytes) {
            Ok(pack) => pack,
            Err(status) => return status.code(),
        };
        let declared_vector_len = match pack.max_vector_len() {
            Ok(limit) => limit,
            Err(status) => return status.code(),
        };
        if declared_vector_len > context.max_vector_len {
            return Status::RESOURCE_LIMIT.code();
        }
        if let Err(status) = unsafe { validate_dynamic_pack_registration(context, &pack) } {
            return status.code();
        }

        let mut selected_slot = 0u16;
        for pack_slot in FIRST_DYNAMIC_PACK_SLOT..=context.max_packs {
            let index = usize::from(pack_slot - 1);
            if context.dynamic_slots[index].is_empty() {
                selected_slot = pack_slot;
                break;
            }
        }
        if selected_slot == 0 {
            return Status::RESOURCE_LIMIT.code();
        }
        let index = usize::from(selected_slot - 1);
        context.dynamic_slots[index] = DynamicSlot {
            bytes: pack_bytes,
            len: pack_len,
        };
        unsafe { out_pack_slot.write(selected_slot) };
        Status::OK.code()
    }
}

/// Unmounts one dynamic pack slot.
///
/// # Safety
///
/// `context` must be valid and exclusively mutable for this call. The function
/// never dereferences the previously mounted pack after clearing its slot.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn xs_pack_unmount(context: *mut XsContext, pack_slot: u16) -> u16 {
    let context = match unsafe { context_mut(context) } {
        Ok(context) => context,
        Err(status) => return status.code(),
    };

    #[cfg(not(feature = "dynamic-packs"))]
    {
        let _ = (context, pack_slot);
        Status::UNSUPPORTED_OPERATION.code()
    }

    #[cfg(feature = "dynamic-packs")]
    {
        if context.config_flags & CONFIG_ALLOW_DYNAMIC_PACKS == 0 {
            return Status::UNSUPPORTED_OPERATION.code();
        }
        if context.frozen != 0 {
            return Status::INVALID_REQUEST.code();
        }
        let index = match dynamic_slot_index(context, pack_slot) {
            Ok(index) => index,
            Err(status) => return status.code(),
        };
        if context.dynamic_slots[index].is_empty() {
            return Status::UNKNOWN_PACK.code();
        }
        context.dynamic_slots[index] = DynamicSlot::EMPTY;
        Status::OK.code()
    }
}

/// Freezes registry mutation for this context.
///
/// # Safety
///
/// `context` must be a valid initialized context and not concurrently mutated.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn xs_registry_freeze(context: *mut XsContext) -> u16 {
    let context = match unsafe { context_mut(context) } {
        Ok(context) => context,
        Err(status) => return status.code(),
    };
    context.frozen = 1;
    Status::OK.code()
}

/// Looks up an exact canonical operation key.
///
/// # Safety
///
/// `context` and all output pointers must be valid. `operation_key` must point
/// to `operation_key_len` readable bytes when the length is nonzero.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn xs_lookup(
    context: *mut XsContext,
    operation_key: *const u8,
    operation_key_len: u32,
    out_pack_slot: *mut u16,
    out_operation_id: *mut u32,
    out_operation_revision: *mut u16,
) -> u16 {
    let context = match unsafe { context_ref(context) } {
        Ok(context) => context,
        Err(status) => return status.code(),
    };
    if !valid_mut_ptr(out_pack_slot)
        || !valid_mut_ptr(out_operation_id)
        || !valid_mut_ptr(out_operation_revision)
    {
        return Status::INVALID_REQUEST.code();
    }
    unsafe {
        out_pack_slot.write(0);
        out_operation_id.write(0);
        out_operation_revision.write(0);
    }

    let key = match unsafe { byte_slice(operation_key, operation_key_len, false) } {
        Ok(key) => key,
        Err(status) => return status.code(),
    };
    if key.len() > 96 || core::str::from_utf8(key).is_err() {
        return Status::INVALID_REQUEST.code();
    }

    match FusedRegistry::new().lookup(key) {
        Ok(operation) => {
            unsafe {
                out_pack_slot.write(operation.pack_slot);
                out_operation_id.write(operation.operation.id);
                out_operation_revision.write(operation.operation.revision);
            }
            Status::OK.code()
        }
        Err(Status::UNKNOWN_OPERATION) => {
            #[cfg(feature = "dynamic-packs")]
            {
                if context.config_flags & CONFIG_ALLOW_DYNAMIC_PACKS != 0 {
                    match unsafe { lookup_dynamic(context, key) } {
                        Ok((pack_slot, _pack, operation)) => {
                            unsafe {
                                out_pack_slot.write(pack_slot);
                                out_operation_id.write(operation.id);
                                out_operation_revision.write(operation.revision);
                            }
                            return Status::OK.code();
                        }
                        Err(status) => return status.code(),
                    }
                }
            }
            #[cfg(not(feature = "dynamic-packs"))]
            let _ = context;
            Status::UNKNOWN_OPERATION.code()
        }
        Err(status) => status.code(),
    }
}

/// Discovers a method-specific fused operation.
///
/// # Safety
///
/// `context` and `out_match_count` must be valid. Query bytes must be readable.
/// When `match_capacity` is nonzero, `matches` must point to that many writable
/// `XsMatchV1` entries whose `struct_size` fields are initialized by the caller.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn xs_find(
    context: *mut XsContext,
    query: *const u8,
    query_len: u32,
    matches: *mut XsMatchV1,
    match_capacity: u16,
    out_match_count: *mut u16,
) -> u16 {
    let context = match unsafe { context_ref(context) } {
        Ok(context) => context,
        Err(status) => return status.code(),
    };
    if context.config_flags & CONFIG_ENABLE_DISCOVERY == 0 {
        return Status::UNSUPPORTED_OPERATION.code();
    }
    if !valid_mut_ptr(out_match_count) {
        return Status::INVALID_REQUEST.code();
    }
    unsafe { out_match_count.write(0) };

    let query = match unsafe { byte_slice(query, query_len, false) } {
        Ok(query) => query,
        Err(status) => return status.code(),
    };
    let mut found = empty_matches();
    let configured_limit = usize::from(context.max_find_matches).min(found.len());
    let count = match FusedRegistry::new().find(query, &mut found[..configured_limit]) {
        Ok(count) => count,
        Err(status) => return status.code(),
    };
    let Ok(count_u16) = u16::try_from(count) else {
        return Status::INTERNAL_ERROR.code();
    };
    unsafe { out_match_count.write(count_u16) };

    if usize::from(match_capacity) < count {
        return Status::BUFFER_TOO_SMALL.code();
    }
    if count == 0 {
        return Status::OK.code();
    }
    if matches.is_null() || !matches.is_aligned() {
        return Status::INVALID_REQUEST.code();
    }

    for (index, found_match) in found[..count].iter().enumerate() {
        let target = unsafe { matches.add(index) };
        // Read only the caller-initialized size field; the remainder of the
        // output record is allowed to be uninitialized before this call.
        let caller_size = unsafe { ptr::addr_of!((*target).struct_size).read() };
        if caller_size < size_u32::<XsMatchV1>() {
            return Status::INVALID_REQUEST.code();
        }
        let output = match build_match(caller_size, *found_match) {
            Ok(output) => output,
            Err(status) => return status.code(),
        };
        unsafe { target.write(output) };
    }
    Status::OK.code()
}

/// Evaluates one fused operation using typed scalar arguments.
///
/// # Safety
///
/// All non-null pointers must satisfy the sizes, alignment, mutability, and
/// lifetime requirements documented by `include/exactscope.h`. Input and output
/// regions must not overlap in a way that violates Rust aliasing rules.
#[unsafe(no_mangle)]
#[allow(clippy::too_many_arguments, clippy::too_many_lines)]
pub unsafe extern "C" fn xs_eval(
    context: *mut XsContext,
    pack_slot: u16,
    operation_id: u32,
    args: *const XsValueRefV1,
    arg_count: u16,
    options: *const XsEvalOptionsV1,
    scratch: *mut c_void,
    scratch_len: u32,
    out_result: *mut XsResultV1,
) -> u16 {
    let context = match unsafe { context_ref(context) } {
        Ok(context) => context,
        Err(status) => return status.code(),
    };
    let result_struct_size = match unsafe { result_output_size(out_result) } {
        Ok(size) => size,
        Err(status) => return status.code(),
    };

    if pack_slot != ECON_UNDERGRAD_PACK_SLOT {
        #[cfg(feature = "dynamic-packs")]
        {
            if context.config_flags & CONFIG_ALLOW_DYNAMIC_PACKS != 0 {
                return unsafe {
                    eval_dynamic(
                        context,
                        result_struct_size,
                        pack_slot,
                        operation_id,
                        args,
                        arg_count,
                        options,
                        scratch,
                        scratch_len,
                        out_result,
                    )
                };
            }
        }
        #[cfg(not(feature = "dynamic-packs"))]
        let _ = context;
        let result = unidentified_result(result_struct_size, Status::UNKNOWN_PACK);
        unsafe { out_result.write(result) };
        return Status::UNKNOWN_PACK.code();
    }

    let operation = match FusedRegistry::new().lookup_id(operation_id) {
        Ok(found) => found.operation,
        Err(status) => {
            let result = unidentified_result(result_struct_size, status);
            unsafe { out_result.write(result) };
            return status.code();
        }
    };

    if let Err(status) = unsafe { validate_options(options) } {
        let result = result_from_evaluation(
            result_struct_size,
            EvaluationResult::failure(status, pack_slot, operation, ARGUMENT_INDEX_NONE, 0),
        );
        unsafe { out_result.write(result) };
        return status.code();
    }
    if scratch.is_null() && scratch_len != 0 {
        let result = result_from_evaluation(
            result_struct_size,
            EvaluationResult::failure(
                Status::INVALID_REQUEST,
                pack_slot,
                operation,
                ARGUMENT_INDEX_NONE,
                0,
            ),
        );
        unsafe { out_result.write(result) };
        return Status::INVALID_REQUEST.code();
    }

    if usize::from(arg_count) != operation.inputs.len() {
        let result = result_from_evaluation(
            result_struct_size,
            EvaluationResult::failure(
                Status::ARGUMENT_COUNT,
                pack_slot,
                operation,
                ARGUMENT_INDEX_NONE,
                0,
            ),
        );
        unsafe { out_result.write(result) };
        return Status::ARGUMENT_COUNT.code();
    }

    let arg_refs = match unsafe { typed_slice(args, usize::from(arg_count)) } {
        Ok(args) => args,
        Err(status) => {
            let result = result_from_evaluation(
                result_struct_size,
                EvaluationResult::failure(status, pack_slot, operation, ARGUMENT_INDEX_NONE, 0),
            );
            unsafe { out_result.write(result) };
            return status.code();
        }
    };

    let mut typed_arguments = [ScalarValue::new(Decimal64::ZERO, 0, 0); 12];
    for (index, argument) in arg_refs.iter().enumerate() {
        let argument_index = u16::try_from(index).unwrap_or(ARGUMENT_INDEX_NONE);
        let value = match unsafe { scalar_from_ref(argument) } {
            Ok(value) => value,
            Err(status) => {
                let result = result_from_evaluation(
                    result_struct_size,
                    EvaluationResult::failure(status, pack_slot, operation, argument_index, 0),
                );
                unsafe { out_result.write(result) };
                return status.code();
            }
        };
        typed_arguments[index] = value;
    }

    let evaluated = evaluate_operation(
        pack_slot,
        operation,
        &typed_arguments[..usize::from(arg_count)],
    );
    let status = evaluated.status;
    unsafe { out_result.write(result_from_evaluation(result_struct_size, evaluated)) };
    status.code()
}

#[cfg(feature = "dynamic-packs")]
#[allow(clippy::too_many_arguments)]
unsafe fn eval_dynamic(
    context: &XsContext,
    result_struct_size: u32,
    pack_slot: u16,
    operation_id: u32,
    args: *const XsValueRefV1,
    arg_count: u16,
    options: *const XsEvalOptionsV1,
    scratch: *mut c_void,
    scratch_len: u32,
    out_result: *mut XsResultV1,
) -> u16 {
    let pack = match unsafe { dynamic_pack_view(context, pack_slot) } {
        Ok(pack) => pack,
        Err(status) => {
            unsafe { out_result.write(unidentified_result(result_struct_size, status)) };
            return status.code();
        }
    };
    let operation = match pack.operation_by_id(operation_id) {
        Ok(operation) => operation,
        Err(status) => {
            unsafe { out_result.write(unidentified_result(result_struct_size, status)) };
            return status.code();
        }
    };

    if let Err(status) = unsafe { validate_options(options) } {
        let evaluated =
            dynamic_failure(&pack, pack_slot, operation, status, ARGUMENT_INDEX_NONE, 0);
        let result_status = evaluated.status;
        unsafe { out_result.write(result_from_evaluation(result_struct_size, evaluated)) };
        return result_status.code();
    }
    if scratch.is_null() && scratch_len != 0 {
        let evaluated = dynamic_failure(
            &pack,
            pack_slot,
            operation,
            Status::INVALID_REQUEST,
            ARGUMENT_INDEX_NONE,
            0,
        );
        let result_status = evaluated.status;
        unsafe { out_result.write(result_from_evaluation(result_struct_size, evaluated)) };
        return result_status.code();
    }

    let input_count = match pack.input_count(operation) {
        Ok(input_count) => input_count,
        Err(status) => {
            unsafe { out_result.write(unidentified_result(result_struct_size, status)) };
            return status.code();
        }
    };
    if usize::from(arg_count) != input_count {
        let evaluated = dynamic_failure(
            &pack,
            pack_slot,
            operation,
            Status::ARGUMENT_COUNT,
            ARGUMENT_INDEX_NONE,
            0,
        );
        let result_status = evaluated.status;
        unsafe { out_result.write(result_from_evaluation(result_struct_size, evaluated)) };
        return result_status.code();
    }

    let arg_refs = match unsafe { typed_slice(args, usize::from(arg_count)) } {
        Ok(args) => args,
        Err(status) => {
            let evaluated =
                dynamic_failure(&pack, pack_slot, operation, status, ARGUMENT_INDEX_NONE, 0);
            let result_status = evaluated.status;
            unsafe { out_result.write(result_from_evaluation(result_struct_size, evaluated)) };
            return result_status.code();
        }
    };

    let mut typed_arguments = [ScalarValue::new(Decimal64::ZERO, 0, 0); 12];
    for (index, argument) in arg_refs.iter().enumerate() {
        let argument_index = u16::try_from(index).unwrap_or(ARGUMENT_INDEX_NONE);
        let value = match unsafe { scalar_from_ref(argument) } {
            Ok(value) => value,
            Err(status) => {
                let evaluated =
                    dynamic_failure(&pack, pack_slot, operation, status, argument_index, 0);
                let result_status = evaluated.status;
                unsafe { out_result.write(result_from_evaluation(result_struct_size, evaluated)) };
                return result_status.code();
            }
        };
        typed_arguments[index] = value;
    }

    let evaluated = match pack.evaluate(
        pack_slot,
        operation,
        &typed_arguments[..usize::from(arg_count)],
    ) {
        Ok(evaluated) => evaluated,
        Err(status) => EvaluationResult::unidentified_failure(status),
    };
    let status = evaluated.status;
    unsafe { out_result.write(result_from_evaluation(result_struct_size, evaluated)) };
    status.code()
}

#[cfg(feature = "dynamic-packs")]
fn dynamic_failure(
    pack: &PackView<'_>,
    pack_slot: u16,
    operation: exactscope_pack::DynamicOperation<'_>,
    status: Status,
    argument_index: u16,
    detail_code: u16,
) -> EvaluationResult {
    pack.failure_result(pack_slot, operation, status, argument_index, detail_code)
        .unwrap_or_else(EvaluationResult::unidentified_failure)
}

/// Optional result JSON helper; not linked into the minimal C ABI slice yet.
///
/// # Safety
///
/// Output pointers must follow the C ABI contract even though this first slice
/// returns `UNSUPPORTED_OPERATION` without dereferencing result/output data.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn xs_result_json(
    context: *mut XsContext,
    _result: *const XsResultV1,
    _output: *mut u8,
    _output_capacity: u32,
    out_written_or_required: *mut u32,
) -> u16 {
    if unsafe { context_ref(context) }.is_err() || !valid_mut_ptr(out_written_or_required) {
        return Status::INVALID_REQUEST.code();
    }
    unsafe { out_written_or_required.write(0) };
    Status::UNSUPPORTED_OPERATION.code()
}

/// Optional match JSON helper; not linked into the minimal C ABI slice yet.
///
/// # Safety
///
/// `out_written_or_required` must be a valid writable pointer.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn xs_match_json(
    _matches: *const XsMatchV1,
    _match_count: u16,
    _output: *mut u8,
    _output_capacity: u32,
    out_written_or_required: *mut u32,
) -> u16 {
    if !valid_mut_ptr(out_written_or_required) {
        return Status::INVALID_REQUEST.code();
    }
    unsafe { out_written_or_required.write(0) };
    Status::UNSUPPORTED_OPERATION.code()
}

#[cfg(feature = "dynamic-packs")]
fn dynamic_slot_index(context: &XsContext, pack_slot: u16) -> Result<usize, Status> {
    if pack_slot < FIRST_DYNAMIC_PACK_SLOT || pack_slot > context.max_packs {
        return Err(Status::UNKNOWN_PACK);
    }
    let index = usize::from(pack_slot - 1);
    if index >= MAX_PACKS {
        return Err(Status::INTERNAL_ERROR);
    }
    Ok(index)
}

#[cfg(feature = "dynamic-packs")]
unsafe fn dynamic_pack_view<'a>(
    context: &XsContext,
    pack_slot: u16,
) -> Result<PackView<'a>, Status> {
    let index = dynamic_slot_index(context, pack_slot)?;
    let slot = context.dynamic_slots[index];
    if slot.is_empty() {
        return Err(Status::UNKNOWN_PACK);
    }
    if slot.bytes.is_null() {
        return Err(Status::INTERNAL_ERROR);
    }
    let len = usize::try_from(slot.len).map_err(|_| Status::RESOURCE_LIMIT)?;
    let bytes = unsafe { slice::from_raw_parts(slot.bytes, len) };
    PackView::parse(bytes)
}

#[cfg(feature = "dynamic-packs")]
unsafe fn validate_dynamic_pack_registration(
    context: &XsContext,
    candidate: &PackView<'_>,
) -> Result<(), Status> {
    let candidate_pack_id = candidate.pack_id()?;
    if candidate_pack_id == ECON_UNDERGRAD_PACK_ID {
        return Err(Status::PACK_INVALID);
    }

    for operation_index in 0..candidate.operation_count() {
        let operation = candidate.operation(operation_index)?;
        match FusedRegistry::new().lookup(operation.key.as_bytes()) {
            Ok(_) => return Err(Status::PACK_INVALID),
            Err(Status::UNKNOWN_OPERATION) => {}
            Err(status) => return Err(status),
        }
    }

    for pack_slot in FIRST_DYNAMIC_PACK_SLOT..=context.max_packs {
        let index = usize::from(pack_slot - 1);
        if context.dynamic_slots[index].is_empty() {
            continue;
        }
        let installed = unsafe { dynamic_pack_view(context, pack_slot) }?;
        if installed.pack_id()? == candidate_pack_id {
            return Err(Status::PACK_INVALID);
        }
        for operation_index in 0..candidate.operation_count() {
            let operation = candidate.operation(operation_index)?;
            match installed.operation_by_key(operation.key.as_bytes()) {
                Ok(_) => return Err(Status::PACK_INVALID),
                Err(Status::UNKNOWN_OPERATION) => {}
                Err(status) => return Err(status),
            }
        }
    }
    Ok(())
}

#[cfg(feature = "dynamic-packs")]
unsafe fn lookup_dynamic<'a>(
    context: &XsContext,
    key: &[u8],
) -> Result<(u16, PackView<'a>, exactscope_pack::DynamicOperation<'a>), Status> {
    for pack_slot in FIRST_DYNAMIC_PACK_SLOT..=context.max_packs {
        let index = usize::from(pack_slot - 1);
        if context.dynamic_slots[index].is_empty() {
            continue;
        }
        let pack = unsafe { dynamic_pack_view(context, pack_slot) }?;
        match pack.operation_by_key(key) {
            Ok(operation) => return Ok((pack_slot, pack, operation)),
            Err(Status::UNKNOWN_OPERATION) => {}
            Err(status) => return Err(status),
        }
    }
    Err(Status::UNKNOWN_OPERATION)
}

fn validate_config(config: &XsConfigV1) -> Result<(), Status> {
    if config.struct_size < size_u32::<XsConfigV1>() {
        return Err(Status::INVALID_REQUEST);
    }
    if config.abi_major != DESIGN_ABI_MAJOR || config.abi_minor != DESIGN_ABI_MINOR {
        return Err(Status::ABI_MISMATCH);
    }
    if config.flags & !CONFIG_KNOWN_FLAGS != 0 || config.reserved != [0; 3] {
        return Err(Status::INVALID_REQUEST);
    }
    #[cfg(not(feature = "dynamic-packs"))]
    if config.flags & CONFIG_ALLOW_DYNAMIC_PACKS != 0 {
        return Err(Status::UNSUPPORTED_OPERATION);
    }
    #[cfg(feature = "dynamic-packs")]
    if config.flags & CONFIG_ALLOW_DYNAMIC_PACKS != 0 && config.flags & CONFIG_ENABLE_DISCOVERY != 0
    {
        return Err(Status::UNSUPPORTED_OPERATION);
    }
    if !(1..=8).contains(&config.max_packs)
        || !(1..=5).contains(&config.max_find_matches)
        || !(1..=256).contains(&config.max_vector_len)
        || config.max_tinywire_frame > 4096
    {
        return Err(Status::RESOURCE_LIMIT);
    }
    Ok(())
}

unsafe fn read_config<'a>(config: *const XsConfigV1) -> Result<&'a XsConfigV1, Status> {
    if config.is_null() || !config.is_aligned() {
        return Err(Status::INVALID_REQUEST);
    }
    Ok(unsafe { &*config })
}

unsafe fn context_ref<'a>(context: *const XsContext) -> Result<&'a XsContext, Status> {
    if context.is_null() || !context.is_aligned() {
        return Err(Status::INVALID_REQUEST);
    }
    let context = unsafe { &*context };
    if context.magic != CONTEXT_MAGIC {
        return Err(Status::INVALID_REQUEST);
    }
    Ok(context)
}

unsafe fn context_mut<'a>(context: *mut XsContext) -> Result<&'a mut XsContext, Status> {
    if context.is_null() || !context.is_aligned() {
        return Err(Status::INVALID_REQUEST);
    }
    let context = unsafe { &mut *context };
    if context.magic != CONTEXT_MAGIC {
        return Err(Status::INVALID_REQUEST);
    }
    Ok(context)
}

unsafe fn byte_slice<'a>(
    pointer: *const u8,
    length: u32,
    allow_empty: bool,
) -> Result<&'a [u8], Status> {
    let length = usize::try_from(length).map_err(|_| Status::RESOURCE_LIMIT)?;
    if length == 0 {
        return if allow_empty {
            Ok(&[])
        } else {
            Err(Status::INVALID_REQUEST)
        };
    }
    if pointer.is_null() {
        return Err(Status::INVALID_REQUEST);
    }
    Ok(unsafe { slice::from_raw_parts(pointer, length) })
}

unsafe fn typed_slice<'a, T>(pointer: *const T, length: usize) -> Result<&'a [T], Status> {
    if length == 0 {
        return Ok(&[]);
    }
    if pointer.is_null() || !pointer.is_aligned() {
        return Err(Status::INVALID_REQUEST);
    }
    Ok(unsafe { slice::from_raw_parts(pointer, length) })
}

unsafe fn scalar_from_ref(argument: &XsValueRefV1) -> Result<ScalarValue, Status> {
    if argument.struct_size < size_u32::<XsValueRefV1>()
        || argument.reserved0 != 0
        || argument.reserved1 != 0
        || argument.reserved2 != 0
    {
        return Err(Status::INVALID_REQUEST);
    }
    if argument.value_kind != VALUE_SCALAR || argument.value_count != 1 {
        return Err(Status::ARGUMENT_TYPE);
    }
    if argument.values.is_null() || !argument.values.is_aligned() {
        return Err(Status::INVALID_REQUEST);
    }
    let raw = unsafe { argument.values.read() };
    let decimal = Decimal64::from_parts(raw.coefficient, raw.exponent)?;
    if decimal.coefficient() != raw.coefficient || decimal.exponent() != raw.exponent {
        return Err(Status::INVALID_DECIMAL);
    }
    let value = ScalarValue {
        decimal,
        semantic_kind: raw.semantic_kind,
        unit_id: raw.unit_id,
        flags: raw.flags,
    };
    value.validate()?;
    Ok(value)
}

unsafe fn validate_options(options: *const XsEvalOptionsV1) -> Result<(), Status> {
    if options.is_null() {
        return Ok(());
    }
    if !options.is_aligned() {
        return Err(Status::INVALID_REQUEST);
    }
    let options = unsafe { &*options };
    if options.struct_size < size_u32::<XsEvalOptionsV1>()
        || options.flags & !EVAL_KNOWN_FLAGS != 0
        || options.reserved != [0; 3]
    {
        return Err(Status::INVALID_REQUEST);
    }
    if options.output_scale != USE_OPERATION_SCALE
        || options.rounding_mode != USE_OPERATION_ROUNDING
    {
        return Err(Status::INVALID_REQUEST);
    }
    Ok(())
}

unsafe fn result_output_size(output: *mut XsResultV1) -> Result<u32, Status> {
    if output.is_null() || !output.is_aligned() {
        return Err(Status::INVALID_REQUEST);
    }
    // Read only the caller-initialized size field; the rest of the output may
    // be uninitialized until the complete result record is written below.
    let caller_size = unsafe { ptr::addr_of!((*output).struct_size).read() };
    if caller_size < size_u32::<XsResultV1>() {
        return Err(Status::INVALID_REQUEST);
    }
    Ok(caller_size)
}

fn unidentified_result(struct_size: u32, status: Status) -> XsResultV1 {
    XsResultV1::empty(struct_size, status)
}

fn result_from_evaluation(struct_size: u32, input: EvaluationResult) -> XsResultV1 {
    let mut output = XsResultV1::empty(struct_size, input.status);
    output.flags = input.flags;
    output.value_count = input.value_count;
    output.classification_id = input.classification_id;
    output.pack_slot = input.pack_slot;
    output.operation_revision = input.operation_revision;
    output.operation_id = input.operation_id;
    output.output_scale = input.output_scale;
    output.rounding_mode = input.rounding_mode;
    output.detail_code = input.detail_code;
    output.argument_index = input.argument_index;
    output.required_size = input.required_size;

    let count = usize::from(input.value_count).min(MAX_RESULT_VALUES);
    for (index, value) in input.values[..count].iter().enumerate() {
        output.values[index] = XsDecimalV1 {
            coefficient: value.decimal.coefficient(),
            exponent: value.decimal.exponent(),
            semantic_kind: value.semantic_kind,
            unit_id: value.unit_id,
            flags: value.flags,
        };
    }
    output
}

fn build_match(caller_size: u32, found: exactscope_pack::Match) -> Result<XsMatchV1, Status> {
    let operation = found.operation.operation;
    Ok(XsMatchV1 {
        struct_size: caller_size,
        pack_slot: found.operation.pack_slot,
        operation_revision: operation.revision,
        operation_id: operation.id,
        rank: found.rank,
        flags: 0,
        operation_key: XsBytesV1::from_static(operation.key)?,
        signature: XsBytesV1::from_static(operation.signature)?,
        method_key: XsBytesV1::from_static(operation.method)?,
        reserved: [0; 2],
    })
}

fn valid_mut_ptr<T>(pointer: *mut T) -> bool {
    !pointer.is_null() && pointer.is_aligned()
}

fn size_u32<T>() -> u32 {
    u32::try_from(size_of::<T>()).unwrap_or(u32::MAX)
}

#[cfg(test)]
extern crate std;

#[cfg(test)]
mod tests {
    use core::{mem::MaybeUninit, ptr};

    use super::*;
    use exactscope_kernel::{SEMANTIC_PRICE, SEMANTIC_QUANTITY};

    fn config(flags: u16) -> XsConfigV1 {
        XsConfigV1 {
            struct_size: size_u32::<XsConfigV1>(),
            abi_major: DESIGN_ABI_MAJOR,
            abi_minor: DESIGN_ABI_MINOR,
            max_packs: 1,
            max_find_matches: 5,
            max_vector_len: 256,
            flags,
            max_tinywire_frame: 4096,
            reserved: [0; 3],
        }
    }

    unsafe fn initialized_context(
        memory: &mut MaybeUninit<XsContext>,
        flags: u16,
    ) -> *mut XsContext {
        let config = config(flags);
        unsafe { initialized_context_with_config(memory, &config) }
    }

    unsafe fn initialized_context_with_config(
        memory: &mut MaybeUninit<XsContext>,
        config: &XsConfigV1,
    ) -> *mut XsContext {
        let mut context = ptr::null_mut();
        let status = unsafe {
            xs_context_init(
                memory.as_mut_ptr().cast::<c_void>(),
                size_u32::<XsContext>(),
                ptr::from_ref(config),
                ptr::from_mut(&mut context),
            )
        };
        assert_eq!(status, Status::OK.code());
        context
    }

    fn decimal(text: &[u8], semantic_kind: u8) -> XsDecimalV1 {
        let value = Decimal64::parse_ascii(text).unwrap();
        XsDecimalV1 {
            coefficient: value.coefficient(),
            exponent: value.exponent(),
            semantic_kind,
            unit_id: 0,
            flags: 0,
        }
    }

    #[test]
    fn abi_layout_and_version_are_stable() {
        assert_eq!(size_of::<XsDecimalV1>(), 16);
        assert_eq!(xs_abi_version(), 0x0001_0000);
        assert_eq!(
            xs_context_align(),
            u32::try_from(align_of::<XsContext>()).unwrap()
        );
    }

    #[test]
    fn decimal_ascii_helper_canonicalizes_and_fails_closed() {
        let mut output = XsDecimalV1 {
            coefficient: i64::MAX,
            exponent: 18,
            semantic_kind: SEMANTIC_PRICE,
            unit_id: u16::MAX,
            flags: u32::MAX,
        };
        let text = b"12000.00";
        let status = unsafe {
            xs_decimal_parse_ascii(
                text.as_ptr(),
                u32::try_from(text.len()).unwrap(),
                SEMANTIC_PRICE,
                42,
                ptr::from_mut(&mut output),
            )
        };
        assert_eq!(status, Status::OK.code());
        assert_eq!(output.coefficient, 12);
        assert_eq!(output.exponent, 3);
        assert_eq!(output.semantic_kind, SEMANTIC_PRICE);
        assert_eq!(output.unit_id, 42);
        assert_eq!(output.flags, 0);

        let invalid = b"5%";
        let status = unsafe {
            xs_decimal_parse_ascii(
                invalid.as_ptr(),
                u32::try_from(invalid.len()).unwrap(),
                SEMANTIC_PRICE,
                0,
                ptr::from_mut(&mut output),
            )
        };
        assert_eq!(status, Status::INVALID_DECIMAL.code());
        assert_eq!(output, XsDecimalV1::ZERO);

        let status = unsafe {
            xs_decimal_parse_ascii(
                b"1".as_ptr(),
                1,
                SEMANTIC_ELASTICITY + 1,
                0,
                ptr::from_mut(&mut output),
            )
        };
        assert_eq!(status, Status::ARGUMENT_TYPE.code());
        assert_eq!(output, XsDecimalV1::ZERO);
    }

    #[cfg(not(feature = "dynamic-packs"))]
    #[test]
    fn context_rejects_dynamic_pack_configuration() {
        let dynamic = config(CONFIG_ALLOW_DYNAMIC_PACKS);
        let size = unsafe { xs_context_size(ptr::from_ref(&dynamic)) };
        assert_eq!(size, 0);
    }

    #[cfg(feature = "dynamic-packs")]
    #[test]
    fn dynamic_discovery_configuration_fails_closed() {
        let mut dynamic = config(CONFIG_ALLOW_DYNAMIC_PACKS | CONFIG_ENABLE_DISCOVERY);
        dynamic.max_packs = 2;
        let size = unsafe { xs_context_size(ptr::from_ref(&dynamic)) };
        assert_eq!(size, 0);
    }

    #[cfg(feature = "dynamic-packs")]
    #[test]
    #[allow(clippy::too_many_lines)]
    fn dynamic_pack_mount_lookup_eval_freeze_reset_and_unmount() {
        let custom_pack = custom_dynamic_pack();
        let official_pack = exactscope_packc::compile_source(include_str!(
            "../../../spec/examples/econ-undergrad-minimal.xsp.json"
        ))
        .unwrap();

        let mut dynamic_config = config(CONFIG_ALLOW_DYNAMIC_PACKS);
        dynamic_config.max_packs = 2;
        assert_ne!(
            unsafe { xs_context_size(ptr::from_ref(&dynamic_config)) },
            0
        );

        let mut memory = MaybeUninit::<XsContext>::uninit();
        let context = unsafe { initialized_context_with_config(&mut memory, &dynamic_config) };
        let (status, slot, required_arena) = mount_pack(context, &custom_pack);
        assert_eq!(status, Status::OK.code());
        assert_eq!(slot, FIRST_DYNAMIC_PACK_SLOT);
        assert_eq!(required_arena, 0);

        let (status, collision_slot, _) = mount_pack(context, &official_pack);
        assert_eq!(status, Status::PACK_INVALID.code());
        assert_eq!(collision_slot, 0);

        let key = b"custom.ped.mid";
        let mut lookup_slot = 0u16;
        let mut operation_id = 0u32;
        let mut revision = 0u16;
        let status = unsafe {
            xs_lookup(
                context,
                key.as_ptr(),
                u32::try_from(key.len()).unwrap(),
                ptr::from_mut(&mut lookup_slot),
                ptr::from_mut(&mut operation_id),
                ptr::from_mut(&mut revision),
            )
        };
        assert_eq!(status, Status::OK.code());
        assert_eq!((lookup_slot, operation_id, revision), (slot, 301, 1));

        let mut count_failure = XsResultV1::empty(size_u32::<XsResultV1>(), Status::INTERNAL_ERROR);
        let status = unsafe {
            xs_eval(
                context,
                slot,
                301,
                ptr::null(),
                1,
                ptr::null(),
                ptr::null_mut(),
                0,
                ptr::from_mut(&mut count_failure),
            )
        };
        assert_eq!(status, Status::ARGUMENT_COUNT.code());
        assert_eq!(count_failure.status, Status::ARGUMENT_COUNT.code());
        assert_eq!(count_failure.pack_slot, slot);
        assert_eq!(count_failure.operation_id, 301);
        assert_eq!(count_failure.operation_revision, 1);
        assert_eq!(count_failure.value_count, 0);

        let decimals = [
            decimal(b"10000", SEMANTIC_PRICE),
            decimal(b"12000", SEMANTIC_PRICE),
            decimal(b"100", SEMANTIC_QUANTITY),
            decimal(b"80", SEMANTIC_QUANTITY),
        ];
        let args = [
            value_ref(&decimals[0]),
            value_ref(&decimals[1]),
            value_ref(&decimals[2]),
            value_ref(&decimals[3]),
        ];
        let mut result = XsResultV1::empty(size_u32::<XsResultV1>(), Status::INTERNAL_ERROR);
        let status = unsafe {
            xs_eval(
                context,
                slot,
                301,
                args.as_ptr(),
                4,
                ptr::null(),
                ptr::null_mut(),
                0,
                ptr::from_mut(&mut result),
            )
        };
        assert_eq!(status, Status::OK.code());
        assert_eq!(result.status, Status::OK.code());
        assert_eq!(result.pack_slot, slot);
        assert_eq!(result.operation_id, 301);
        assert_eq!(result.operation_revision, 1);
        assert_eq!(result.classification_id, 3);
        assert_eq!(result.values[0].coefficient, -1_222_222);
        assert_eq!(result.values[0].exponent, -6);

        let status = unsafe { xs_pack_unmount(context, slot) };
        assert_eq!(status, Status::OK.code());
        assert_lookup_unknown(context, key);

        let (status, remounted_slot, _) = mount_pack(context, &custom_pack);
        assert_eq!(status, Status::OK.code());
        assert_eq!(remounted_slot, slot);
        assert_eq!(unsafe { xs_registry_freeze(context) }, Status::OK.code());
        assert_eq!(
            unsafe { xs_pack_unmount(context, remounted_slot) },
            Status::INVALID_REQUEST.code()
        );
        assert_eq!(unsafe { xs_context_reset(context) }, Status::OK.code());
        assert_lookup_unknown(context, key);
    }

    #[cfg(feature = "dynamic-packs")]
    fn custom_dynamic_pack() -> std::vec::Vec<u8> {
        let source = include_str!("../../../spec/examples/econ-undergrad-minimal.xsp.json")
            .replace("org.exactscope.econ-undergrad", "org.example.custom-econ")
            .replace("econ.ped.mid", "custom.ped.mid");
        exactscope_packc::compile_source(&source).unwrap()
    }

    #[cfg(feature = "dynamic-packs")]
    fn mount_pack(context: *mut XsContext, pack: &[u8]) -> (u16, u16, u32) {
        let mut slot = 0u16;
        let mut required_arena = u32::MAX;
        let status = unsafe {
            xs_pack_mount(
                context,
                pack.as_ptr(),
                u32::try_from(pack.len()).unwrap(),
                ptr::null_mut(),
                0,
                ptr::from_mut(&mut slot),
                ptr::from_mut(&mut required_arena),
            )
        };
        (status, slot, required_arena)
    }

    #[cfg(feature = "dynamic-packs")]
    fn assert_lookup_unknown(context: *mut XsContext, key: &[u8]) {
        let mut slot = u16::MAX;
        let mut operation_id = u32::MAX;
        let mut revision = u16::MAX;
        let status = unsafe {
            xs_lookup(
                context,
                key.as_ptr(),
                u32::try_from(key.len()).unwrap(),
                ptr::from_mut(&mut slot),
                ptr::from_mut(&mut operation_id),
                ptr::from_mut(&mut revision),
            )
        };
        assert_eq!(status, Status::UNKNOWN_OPERATION.code());
        assert_eq!((slot, operation_id, revision), (0, 0, 0));
    }

    #[test]
    fn lookup_and_discovery_use_fused_registry() {
        let mut memory = MaybeUninit::<XsContext>::uninit();
        let context = unsafe { initialized_context(&mut memory, CONFIG_ENABLE_DISCOVERY) };
        let mut slot = 0u16;
        let mut operation_id = 0u32;
        let mut revision = 0u16;
        let status = unsafe {
            xs_lookup(
                context,
                b"econ.ped.mid".as_ptr(),
                12,
                ptr::from_mut(&mut slot),
                ptr::from_mut(&mut operation_id),
                ptr::from_mut(&mut revision),
            )
        };
        assert_eq!(status, Status::OK.code());
        assert_eq!((slot, operation_id, revision), (1, 301, 1));

        let mut match_output = XsMatchV1 {
            struct_size: size_u32::<XsMatchV1>(),
            pack_slot: 0,
            operation_revision: 0,
            operation_id: 0,
            rank: 0,
            flags: 0,
            operation_key: XsBytesV1::EMPTY,
            signature: XsBytesV1::EMPTY,
            method_key: XsBytesV1::EMPTY,
            reserved: [0; 2],
        };
        let mut count = 0u16;
        let query = b"midpoint price elasticity";
        let status = unsafe {
            xs_find(
                context,
                query.as_ptr(),
                u32::try_from(query.len()).unwrap(),
                ptr::from_mut(&mut match_output),
                1,
                ptr::from_mut(&mut count),
            )
        };
        assert_eq!(status, Status::OK.code());
        assert_eq!(count, 1);
        assert_eq!(match_output.operation_id, 301);
    }

    #[test]
    fn eval_matches_kernel_golden_vector() {
        let mut memory = MaybeUninit::<XsContext>::uninit();
        let context = unsafe { initialized_context(&mut memory, 0) };
        let decimals = [
            decimal(b"10000", SEMANTIC_PRICE),
            decimal(b"12000", SEMANTIC_PRICE),
            decimal(b"100", SEMANTIC_QUANTITY),
            decimal(b"80", SEMANTIC_QUANTITY),
        ];
        let args = [
            value_ref(&decimals[0]),
            value_ref(&decimals[1]),
            value_ref(&decimals[2]),
            value_ref(&decimals[3]),
        ];
        let options = XsEvalOptionsV1 {
            struct_size: size_u32::<XsEvalOptionsV1>(),
            output_scale: USE_OPERATION_SCALE,
            rounding_mode: USE_OPERATION_ROUNDING,
            flags: EVAL_REQUIRE_CLASSIFICATION,
            reserved: [0; 3],
        };
        let mut result = XsResultV1::empty(size_u32::<XsResultV1>(), Status::INTERNAL_ERROR);
        let status = unsafe {
            xs_eval(
                context,
                1,
                301,
                args.as_ptr(),
                4,
                ptr::from_ref(&options),
                ptr::null_mut(),
                0,
                ptr::from_mut(&mut result),
            )
        };
        assert_eq!(status, Status::OK.code());
        assert_eq!(result.status, Status::OK.code());
        assert_eq!(result.value_count, 1);
        assert_eq!(result.classification_id, 3);
        assert_eq!(result.values[0].coefficient, -1_222_222);
        assert_eq!(result.values[0].exponent, -6);
    }

    #[test]
    fn eval_preserves_count_precedence_and_zeroes_values() {
        let mut memory = MaybeUninit::<XsContext>::uninit();
        let context = unsafe { initialized_context(&mut memory, 0) };
        let mut result = XsResultV1::empty(size_u32::<XsResultV1>(), Status::INTERNAL_ERROR);
        let status = unsafe {
            xs_eval(
                context,
                1,
                301,
                ptr::null(),
                1,
                ptr::null(),
                ptr::null_mut(),
                0,
                ptr::from_mut(&mut result),
            )
        };
        assert_eq!(status, Status::ARGUMENT_COUNT.code());
        assert_eq!(result.value_count, 0);
        assert_eq!(result.values[0], XsDecimalV1::ZERO);
    }

    fn value_ref(value: &XsDecimalV1) -> XsValueRefV1 {
        XsValueRefV1 {
            struct_size: size_u32::<XsValueRefV1>(),
            value_kind: VALUE_SCALAR,
            reserved0: 0,
            reserved1: 0,
            values: ptr::from_ref(value),
            value_count: 1,
            reserved2: 0,
        }
    }
}
