#![cfg_attr(target_arch = "wasm32", no_std)]
#![doc = "No-import fused WebAssembly wrapper for `ExactScope`."]

//! The release artifact targets `wasm32v1-none`. It owns no calculation
//! semantics: Tiny JSON requests are delegated to `exactscope-tinyjson`, which
//! in turn delegates to the same fused registry and deterministic kernel used
//! by the native C ABI.

pub use exactscope_kernel::{DESIGN_ABI_MAJOR, DESIGN_ABI_MINOR};

#[cfg(target_arch = "wasm32")]
mod wasm32 {
    use core::{arch::wasm32, ptr, slice};

    use exactscope_kernel::Status;

    const ABI_VERSION: u32 = 0x0001_0000;
    const MEMORY_ALIGNMENT: u32 = 8;
    const WASM_PAGE_BYTES: u64 = 65_536;
    const META_SIZE: u32 = 16;
    const META_FLAG_OUTPUT_WRITTEN: u16 = 0x0001;
    const WIRE_FORMAT_TINY_JSON: u32 = 1;
    const WIRE_FORMAT_TINY_CBOR: u32 = 2;

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

    /// Returns the encoded ExactScope ABI version.
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
            WIRE_FORMAT_TINY_CBOR => {
                initialize_meta(meta_offset, Status::UNSUPPORTED_OPERATION, 0, 0, 0);
                Status::UNSUPPORTED_OPERATION.code()
            }
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

    fn valid_nonempty_region(region: Region, reserved: u32, memory_bytes: u64) -> bool {
        if region.len == 0 || region.offset < reserved {
            return false;
        }
        region.end().is_some_and(|end| end <= memory_bytes)
    }

    fn current_memory_bytes() -> u64 {
        let pages = wasm32::memory_size(0);
        u64::try_from(pages)
            .ok()
            .and_then(|pages| pages.checked_mul(WASM_PAGE_BYTES))
            .unwrap_or(0)
    }

    fn meta_struct_size_is_valid(meta_offset: u32) -> bool {
        let offset = match usize::try_from(meta_offset) {
            Ok(offset) => offset,
            Err(_) => return false,
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
        let offset = match usize::try_from(meta_offset) {
            Ok(offset) => offset,
            Err(_) => return,
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
