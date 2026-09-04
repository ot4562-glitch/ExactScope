#![cfg_attr(target_arch = "wasm32", no_std)]
#![doc = "No-import fused WebAssembly wrapper for `ExactScope`."]

//! The release artifact targets `wasm32v1-none`. It owns no calculation
//! semantics: Tiny JSON requests are delegated to `exactscope-tinyjson`, which
//! in turn delegates to the same fused registry and deterministic kernel used
//! by the native C ABI.

pub use exactscope_kernel::{DESIGN_ABI_MAJOR, DESIGN_ABI_MINOR};

#[cfg(any(target_arch = "wasm32", test))]
mod tinywire;

#[cfg(target_arch = "wasm32")]
mod wasm32 {
    use core::{arch::wasm32, ptr, slice};

    use exactscope_kernel::{
        evaluate_statistics_operation, Decimal64, DecimalVector, EvaluationResult, Status,
        ARGUMENT_INDEX_NONE, MAX_STATS_VECTOR_LEN, VALUE_FLAGS_V1,
    };
    use exactscope_pack::{StatisticsRegistry, STATISTICS_CORE_PACK_SLOT};

    const ABI_VERSION: u32 = 0x0001_0000;
    const MEMORY_ALIGNMENT: u32 = 8;
    const WASM_PAGE_BYTES: u64 = 65_536;
    const META_SIZE: u32 = 16;
    const META_FLAG_OUTPUT_WRITTEN: u16 = 0x0001;
    const WIRE_FORMAT_TINY_JSON: u32 = 1;
    const WIRE_FORMAT_TINY_CBOR: u32 = 2;
    const DECIMAL_SIZE: u32 = 16;
    const RESULT_SIZE: u32 = 112;

    unsafe extern "C" {
        static __heap_base: u8;
    }

    #[derive(Clone, Copy)]
    struct Region {
        offset: u32,
        len: u32,
    }

    impl Region {
        const fn empty() -> Self {
            Self { offset: 0, len: 0 }
        }

        fn end(self) -> Option<u64> {
            u64::from(self.offset).checked_add(u64::from(self.len))
        }

        fn overlaps(self, other: Self) -> bool {
            if self.len == 0 || other.len == 0 {
                return false;
            }
            let Some(self_end) = self.end() else {
                return true;
            };
            let Some(other_end) = other.end() else {
                return true;
            };
            u64::from(self.offset) < other_end && u64::from(other.offset) < self_end
        }
    }

    /// WebAssembly metadata record written in little-endian form.
    #[repr(C)]
    struct IoMeta {
        struct_size: u32,
        status: u16,
        flags: u16,
        written: u32,
        required: u32,
    }

    /// Returns the encoded `ExactScope` ABI version.
    #[unsafe(no_mangle)]
    pub extern "C" fn xs_abi_version() -> u32 {
        ABI_VERSION
    }

    /// Returns the first byte that the host may own after growing memory.
    #[unsafe(no_mangle)]
    pub extern "C" fn xs_wasm_reserved_end() -> u32 {
        let raw = ptr::addr_of!(__heap_base).addr();
        let Ok(raw) = u32::try_from(raw) else {
            return u32::MAX;
        };
        align_up(raw, MEMORY_ALIGNMENT).unwrap_or(u32::MAX)
    }

    /// Returns the required alignment for host-owned regions.
    #[unsafe(no_mangle)]
    pub extern "C" fn xs_wasm_memory_alignment() -> u32 {
        MEMORY_ALIGNMENT
    }

    /// Evaluates one fused statistics operation over zero-copy decimal vectors.
    ///
    /// `x` and optional `y` are arrays of the 16-byte little-endian
    /// `xs_decimal_v1` layout. `result_offset` points to a 112-byte
    /// `xs_result_v1` record whose `struct_size` is initialized by the host.
    #[unsafe(no_mangle)]
    pub extern "C" fn xs_wasm_eval_statistics(
        operation_id: u32,
        x_offset: u32,
        x_len: u32,
        y_offset: u32,
        y_len: u32,
        result_offset: u32,
    ) -> u16 {
        let reserved = xs_wasm_reserved_end();
        let memory_bytes = current_memory_bytes();
        let result_region = Region {
            offset: result_offset,
            len: RESULT_SIZE,
        };
        if !valid_nonempty_region(result_region, reserved, memory_bytes)
            || result_offset % MEMORY_ALIGNMENT != 0
            || read_u32_at(result_offset) != Some(RESULT_SIZE)
        {
            return Status::INVALID_REQUEST.code();
        }

        let operation = match StatisticsRegistry::new().lookup_id(operation_id) {
            Ok(operation) => operation.operation,
            Err(status) => {
                write_result(
                    result_offset,
                    EvaluationResult::unidentified_failure(status),
                );
                return status.code();
            }
        };
        let x = match decimal_vector_region(x_offset, x_len, reserved, memory_bytes) {
            Ok(region) => region,
            Err(status) => {
                let failure = statistics_failure(operation, status, 0);
                write_result(result_offset, failure);
                return status.code();
            }
        };
        let y = match decimal_vector_region(y_offset, y_len, reserved, memory_bytes) {
            Ok(region) => region,
            Err(status) => {
                let failure = statistics_failure(operation, status, 1);
                write_result(result_offset, failure);
                return status.code();
            }
        };
        if x.overlaps(result_region)
            || y.overlaps(result_region)
            || (operation.input_count == 1 && (y.offset != 0 || y.len != 0))
        {
            let failure =
                statistics_failure(operation, Status::INVALID_REQUEST, ARGUMENT_INDEX_NONE);
            write_result(result_offset, failure);
            return Status::INVALID_REQUEST.code();
        }

        let sources = [
            WasmDecimalVector { region: x },
            WasmDecimalVector { region: y },
        ];
        for (argument_index, source) in sources[..usize::from(operation.input_count)]
            .iter()
            .enumerate()
        {
            for index in 0..source.len() {
                if let Err(status) = source.value_at(index) {
                    let failure = statistics_failure(
                        operation,
                        status,
                        u16::try_from(argument_index).unwrap_or(ARGUMENT_INDEX_NONE),
                    );
                    write_result(result_offset, failure);
                    return status.code();
                }
            }
        }

        let evaluated = evaluate_statistics_operation(
            STATISTICS_CORE_PACK_SLOT,
            operation,
            &sources[..usize::from(operation.input_count)],
        );
        let status = evaluated.status;
        write_result(result_offset, evaluated);
        status.code()
    }

    /// Processes one Tiny JSON/TinyWire request from exported linear memory.
    ///
    /// The first implementation slice supports Tiny JSON only. Tiny CBOR is a
    /// recognized future wire format and therefore fails with
    /// `UNSUPPORTED_OPERATION` rather than being misparsed.
    #[unsafe(no_mangle)]
    pub extern "C" fn xs_wire_request(
        wire_format: u32,
        input_offset: u32,
        input_len: u32,
        output_offset: u32,
        output_capacity: u32,
        meta_offset: u32,
    ) -> u16 {
        let reserved = xs_wasm_reserved_end();
        let memory_bytes = current_memory_bytes();
        let meta = Region {
            offset: meta_offset,
            len: META_SIZE,
        };

        if !valid_nonempty_region(meta, reserved, memory_bytes)
            || meta_offset % 4 != 0
            || !meta_struct_size_is_valid(meta_offset)
        {
            return Status::INVALID_REQUEST.code();
        }

        initialize_meta(meta_offset, Status::INVALID_REQUEST, 0, 0, 0);

        let input = Region {
            offset: input_offset,
            len: input_len,
        };
        let output = if output_capacity == 0 {
            Region::empty()
        } else {
            Region {
                offset: output_offset,
                len: output_capacity,
            }
        };

        if input_len == 0
            || !valid_nonempty_region(input, reserved, memory_bytes)
            || input_offset % MEMORY_ALIGNMENT != 0
            || (output.len != 0
                && (!valid_nonempty_region(output, reserved, memory_bytes)
                    || output_offset % MEMORY_ALIGNMENT != 0))
            || input.overlaps(output)
            || input.overlaps(meta)
            || output.overlaps(meta)
        {
            initialize_meta(meta_offset, Status::INVALID_REQUEST, 0, 0, 0);
            return Status::INVALID_REQUEST.code();
        }

        match wire_format {
            WIRE_FORMAT_TINY_JSON => process_tiny_json(input, output, meta_offset),
            WIRE_FORMAT_TINY_CBOR => process_tiny_cbor(input, output, meta_offset),
            _ => {
                initialize_meta(meta_offset, Status::INVALID_REQUEST, 0, 0, 0);
                Status::INVALID_REQUEST.code()
            }
        }
    }

    #[cfg(feature = "tinyjson")]
    fn process_tiny_json(input: Region, output: Region, meta_offset: u32) -> u16 {
        let input = unsafe { input_slice(input) };
        let output = if output.len == 0 {
            &mut []
        } else {
            unsafe { output_slice(output) }
        };
        let result = exactscope_tinyjson::request(input, output);

        if result.status == Status::BUFFER_TOO_SMALL {
            initialize_meta(meta_offset, result.status, 0, 0, result.written_or_required);
        } else {
            initialize_meta(
                meta_offset,
                result.status,
                META_FLAG_OUTPUT_WRITTEN,
                result.written_or_required,
                0,
            );
        }
        result.status.code()
    }

    #[cfg(not(feature = "tinyjson"))]
    fn process_tiny_json(_input: Region, _output: Region, meta_offset: u32) -> u16 {
        initialize_meta(meta_offset, Status::UNSUPPORTED_OPERATION, 0, 0, 0);
        Status::UNSUPPORTED_OPERATION.code()
    }

    fn process_tiny_cbor(input: Region, output: Region, meta_offset: u32) -> u16 {
        let input = unsafe { input_slice(input) };
        let output = if output.len == 0 {
            &mut []
        } else {
            unsafe { output_slice(output) }
        };
        let result = crate::tinywire::request(input, output);
        if result.status == Status::BUFFER_TOO_SMALL {
            initialize_meta(meta_offset, result.status, 0, 0, result.written_or_required);
        } else {
            initialize_meta(
                meta_offset,
                result.status,
                META_FLAG_OUTPUT_WRITTEN,
                result.written_or_required,
                0,
            );
        }
        result.status.code()
    }

    fn valid_nonempty_region(region: Region, reserved: u32, memory_bytes: u64) -> bool {
        if region.len == 0 || region.offset < reserved {
            return false;
        }
        region.end().is_some_and(|end| end <= memory_bytes)
    }

    fn decimal_vector_region(
        offset: u32,
        count: u32,
        reserved: u32,
        memory_bytes: u64,
    ) -> Result<Region, Status> {
        let count = usize::try_from(count).map_err(|_| Status::RESOURCE_LIMIT)?;
        if count > MAX_STATS_VECTOR_LEN {
            return Err(Status::RESOURCE_LIMIT);
        }
        if count == 0 {
            return if offset == 0 {
                Ok(Region::empty())
            } else {
                Err(Status::INVALID_REQUEST)
            };
        }
        let len = u32::try_from(count)
            .ok()
            .and_then(|count| count.checked_mul(DECIMAL_SIZE))
            .ok_or(Status::RESOURCE_LIMIT)?;
        let region = Region { offset, len };
        if offset % MEMORY_ALIGNMENT != 0 || !valid_nonempty_region(region, reserved, memory_bytes)
        {
            return Err(Status::INVALID_REQUEST);
        }
        Ok(region)
    }

    #[derive(Clone, Copy)]
    struct WasmDecimalVector {
        region: Region,
    }

    impl DecimalVector for WasmDecimalVector {
        fn len(&self) -> usize {
            usize::try_from(self.region.len / DECIMAL_SIZE).unwrap_or(0)
        }

        fn value_at(&self, index: usize) -> Result<Decimal64, Status> {
            if index >= self.len() {
                return Err(Status::INTERNAL_ERROR);
            }
            let relative = index
                .checked_mul(DECIMAL_SIZE as usize)
                .ok_or(Status::RESOURCE_LIMIT)?;
            let offset = usize::try_from(self.region.offset)
                .map_err(|_| Status::INVALID_REQUEST)?
                .checked_add(relative)
                .ok_or(Status::INVALID_REQUEST)?;
            let bytes =
                unsafe { slice::from_raw_parts(offset as *const u8, DECIMAL_SIZE as usize) };
            let coefficient =
                i64::from_le_bytes(bytes[0..8].try_into().map_err(|_| Status::INTERNAL_ERROR)?);
            let exponent = i8::from_ne_bytes([bytes[8]]);
            if bytes[9] != 0
                || u16::from_le_bytes([bytes[10], bytes[11]]) != 0
                || u32::from_le_bytes(
                    bytes[12..16]
                        .try_into()
                        .map_err(|_| Status::INTERNAL_ERROR)?,
                ) & !VALUE_FLAGS_V1
                    != 0
            {
                return Err(if bytes[9] != 0 {
                    Status::ARGUMENT_TYPE
                } else if u16::from_le_bytes([bytes[10], bytes[11]]) != 0 {
                    Status::UNIT_MISMATCH
                } else {
                    Status::INVALID_REQUEST
                });
            }
            let decimal = Decimal64::from_parts(coefficient, exponent)?;
            if decimal.coefficient() != coefficient || decimal.exponent() != exponent {
                return Err(Status::INVALID_DECIMAL);
            }
            Ok(decimal)
        }
    }

    fn statistics_failure(
        operation: &exactscope_kernel::StatisticsOperationDecl,
        status: Status,
        argument_index: u16,
    ) -> EvaluationResult {
        let mut result = EvaluationResult::unidentified_failure(status);
        result.pack_slot = STATISTICS_CORE_PACK_SLOT;
        result.operation_revision = operation.revision;
        result.operation_id = operation.id;
        result.output_scale = i8::try_from(operation.output_scale).unwrap_or(0);
        result.rounding_mode = operation.rounding_mode.id();
        result.argument_index = argument_index;
        result
    }

    fn read_u32_at(offset: u32) -> Option<u32> {
        let offset = usize::try_from(offset).ok()?;
        let bytes = unsafe { slice::from_raw_parts(offset as *const u8, 4) };
        Some(u32::from_le_bytes(bytes.try_into().ok()?))
    }

    fn write_result(offset: u32, result: EvaluationResult) {
        let Ok(offset) = usize::try_from(offset) else {
            return;
        };
        let bytes = unsafe { slice::from_raw_parts_mut(offset as *mut u8, RESULT_SIZE as usize) };
        bytes.fill(0);
        put_u32(bytes, 0, RESULT_SIZE);
        put_u16(bytes, 4, result.status.code());
        put_u16(bytes, 6, result.flags);
        put_u16(bytes, 8, result.value_count);
        put_u16(bytes, 10, result.classification_id);
        put_u16(bytes, 12, result.pack_slot);
        put_u16(bytes, 14, result.operation_revision);
        put_u32(bytes, 16, result.operation_id);
        bytes[20] = result.output_scale.to_ne_bytes()[0];
        bytes[21] = result.rounding_mode;
        put_u16(bytes, 22, result.detail_code);
        put_u16(bytes, 24, result.argument_index);
        put_u32(bytes, 28, result.required_size);
        for (index, value) in result.values.iter().enumerate() {
            let base = 32 + index * DECIMAL_SIZE as usize;
            bytes[base..base + 8].copy_from_slice(&value.decimal.coefficient().to_le_bytes());
            bytes[base + 8] = value.decimal.exponent().to_ne_bytes()[0];
            bytes[base + 9] = value.semantic_kind;
            bytes[base + 10..base + 12].copy_from_slice(&value.unit_id.to_le_bytes());
            bytes[base + 12..base + 16].copy_from_slice(&value.flags.to_le_bytes());
        }
    }

    fn put_u16(bytes: &mut [u8], offset: usize, value: u16) {
        bytes[offset..offset + 2].copy_from_slice(&value.to_le_bytes());
    }

    fn put_u32(bytes: &mut [u8], offset: usize, value: u32) {
        bytes[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
    }

    fn current_memory_bytes() -> u64 {
        let pages = wasm32::memory_size(0);
        u64::try_from(pages)
            .ok()
            .and_then(|pages| pages.checked_mul(WASM_PAGE_BYTES))
            .unwrap_or(0)
    }

    fn meta_struct_size_is_valid(meta_offset: u32) -> bool {
        let Ok(offset) = usize::try_from(meta_offset) else {
            return false;
        };
        let bytes = unsafe { slice::from_raw_parts(offset as *const u8, 4) };
        u32::from_le_bytes([bytes[0], bytes[1], bytes[2], bytes[3]]) == META_SIZE
    }

    fn initialize_meta(meta_offset: u32, status: Status, flags: u16, written: u32, required: u32) {
        let meta = IoMeta {
            struct_size: META_SIZE,
            status: status.code(),
            flags,
            written,
            required,
        };
        let Ok(offset) = usize::try_from(meta_offset) else {
            return;
        };
        let struct_size = meta.struct_size.to_le_bytes();
        let status = meta.status.to_le_bytes();
        let flags = meta.flags.to_le_bytes();
        let written = meta.written.to_le_bytes();
        let required = meta.required.to_le_bytes();
        let output = unsafe { slice::from_raw_parts_mut(offset as *mut u8, 16) };
        output[0..4].copy_from_slice(&struct_size);
        output[4..6].copy_from_slice(&status);
        output[6..8].copy_from_slice(&flags);
        output[8..12].copy_from_slice(&written);
        output[12..16].copy_from_slice(&required);
    }

    unsafe fn input_slice(region: Region) -> &'static [u8] {
        let offset = usize::try_from(region.offset).unwrap_or(0);
        let len = usize::try_from(region.len).unwrap_or(0);
        unsafe { slice::from_raw_parts(offset as *const u8, len) }
    }

    unsafe fn output_slice(region: Region) -> &'static mut [u8] {
        let offset = usize::try_from(region.offset).unwrap_or(0);
        let len = usize::try_from(region.len).unwrap_or(0);
        unsafe { slice::from_raw_parts_mut(offset as *mut u8, len) }
    }

    fn align_up(value: u32, alignment: u32) -> Option<u32> {
        let mask = alignment - 1;
        value.checked_add(mask).map(|value| value & !mask)
    }

    #[panic_handler]
    fn panic(_info: &core::panic::PanicInfo<'_>) -> ! {
        core::arch::wasm32::unreachable()
    }
}
