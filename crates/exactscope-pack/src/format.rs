//! Canonical `.xsp` binary primitives shared by loader and build-time compiler.

use exactscope_kernel::Status;

/// Pack magic.
pub const MAGIC: &[u8; 4] = b"XSPK";
/// Supported pack-format major.
pub const FORMAT_MAJOR: u16 = 1;
/// Supported pack-format minor.
pub const FORMAT_MINOR: u16 = 0;
/// Fixed v1 header size.
pub const HEADER_SIZE: usize = 32;
/// Fixed v1 section-directory entry size.
pub const SECTION_ENTRY_SIZE: usize = 16;
/// Highest v1 section kind.
pub const MAX_SECTION_KIND: usize = 13;

/// META section.
pub const SECTION_META: usize = 1;
/// UTF-8 string table.
pub const SECTION_STRINGS: usize = 2;
/// Operation records.
pub const SECTION_OPERATIONS: usize = 3;
/// Input records.
pub const SECTION_INPUTS: usize = 4;
/// Output records.
pub const SECTION_OUTPUTS: usize = 5;
/// Constraint records.
pub const SECTION_CONSTRAINTS: usize = 6;
/// Decimal constants.
pub const SECTION_CONSTANTS: usize = 7;
/// VM instruction records.
pub const SECTION_PROGRAMS: usize = 8;
/// Classification records.
pub const SECTION_CLASSIFICATIONS: usize = 9;
/// Alias records.
pub const SECTION_ALIASES: usize = 10;
/// Optional alias index.
pub const SECTION_ALIAS_INDEX: usize = 11;
/// Source metadata.
pub const SECTION_SOURCES: usize = 12;
/// Operation-to-source references.
pub const SECTION_SOURCE_REFS: usize = 13;

/// Fixed META record size.
pub const META_RECORD_SIZE: usize = 48;
/// Fixed operation record size.
pub const OPERATION_RECORD_SIZE: usize = 64;
/// Fixed input record size.
pub const INPUT_RECORD_SIZE: usize = 32;
/// Fixed output record size.
pub const OUTPUT_RECORD_SIZE: usize = 24;
/// Fixed constraint record size.
pub const CONSTRAINT_RECORD_SIZE: usize = 16;
/// Fixed decimal constant record size.
pub const CONSTANT_RECORD_SIZE: usize = 16;
/// Fixed VM instruction record size.
pub const INSTRUCTION_RECORD_SIZE: usize = 4;
/// Fixed classification record size.
pub const CLASSIFICATION_RECORD_SIZE: usize = 24;
/// Fixed alias record size.
pub const ALIAS_RECORD_SIZE: usize = 12;

/// Numeric-profile ID for `decimal64-v1`.
pub const NUMERIC_PROFILE_DECIMAL64_V1: u16 = 1;

/// Operation kind for scalar formula VM programs.
pub const OPERATION_KIND_FORMULA: u8 = 1;
/// Operation kind for bounded built-in kernels.
pub const OPERATION_KIND_KERNEL: u8 = 2;

/// Operation flag: caller may override scale.
pub const OP_FLAG_SCALE_OVERRIDE: u8 = 0x01;
/// Operation flag: caller may override rounding.
pub const OP_FLAG_ROUNDING_OVERRIDE: u8 = 0x02;
/// Operation flag: successful result requires classification.
pub const OP_FLAG_CLASSIFICATION_REQUIRED: u8 = 0x04;
/// Operation flag: omit from discovery.
pub const OP_FLAG_HIDDEN_DISCOVERY: u8 = 0x08;
/// All operation flags defined by v1.
pub const OP_FLAGS_V1: u8 = OP_FLAG_SCALE_OVERRIDE
    | OP_FLAG_ROUNDING_OVERRIDE
    | OP_FLAG_CLASSIFICATION_REQUIRED
    | OP_FLAG_HIDDEN_DISCOVERY;

/// Input flag: explicit nonzero unit ID is required.
pub const INPUT_FLAG_UNIT_REQUIRED: u16 = 0x0001;
/// All input flags defined by the first slice.
pub const INPUT_FLAGS_V1: u16 = INPUT_FLAG_UNIT_REQUIRED;

/// Constraint kind: greater than constant.
pub const CONSTRAINT_GT: u8 = 1;
/// Constraint kind: greater than or equal to constant.
pub const CONSTRAINT_GE: u8 = 2;
/// Constraint kind: not exactly equal to constant.
pub const CONSTRAINT_NE: u8 = 6;

/// CRC-32/ISO-HDLC over canonical pack bytes after the fixed header.
#[must_use]
pub fn crc32_iso_hdlc(bytes: &[u8]) -> u32 {
    let mut crc = 0xffff_ffffu32;
    for &byte in bytes {
        crc ^= u32::from(byte);
        for _ in 0..8 {
            let mask = 0u32.wrapping_sub(crc & 1);
            crc = (crc >> 1) ^ (0xedb8_8320 & mask);
        }
    }
    !crc
}

/// Reads one little-endian `u16`.
///
/// # Errors
///
/// Returns [`Status::PACK_INVALID`] when the range is outside `bytes`.
pub fn read_u16(bytes: &[u8], offset: usize) -> Result<u16, Status> {
    let raw = read_array::<2>(bytes, offset)?;
    Ok(u16::from_le_bytes(raw))
}

/// Reads one little-endian `i16`.
///
/// # Errors
///
/// Returns [`Status::PACK_INVALID`] when the range is outside `bytes`.
pub fn read_i16(bytes: &[u8], offset: usize) -> Result<i16, Status> {
    let raw = read_array::<2>(bytes, offset)?;
    Ok(i16::from_le_bytes(raw))
}

/// Reads one little-endian `u32`.
///
/// # Errors
///
/// Returns [`Status::PACK_INVALID`] when the range is outside `bytes`.
pub fn read_u32(bytes: &[u8], offset: usize) -> Result<u32, Status> {
    let raw = read_array::<4>(bytes, offset)?;
    Ok(u32::from_le_bytes(raw))
}

/// Reads one little-endian `i64`.
///
/// # Errors
///
/// Returns [`Status::PACK_INVALID`] when the range is outside `bytes`.
pub fn read_i64(bytes: &[u8], offset: usize) -> Result<i64, Status> {
    let raw = read_array::<8>(bytes, offset)?;
    Ok(i64::from_le_bytes(raw))
}

/// Returns one byte at `offset`.
///
/// # Errors
///
/// Returns [`Status::PACK_INVALID`] when `offset` is outside `bytes`.
pub fn read_u8(bytes: &[u8], offset: usize) -> Result<u8, Status> {
    bytes.get(offset).copied().ok_or(Status::PACK_INVALID)
}

fn read_array<const N: usize>(bytes: &[u8], offset: usize) -> Result<[u8; N], Status> {
    let end = offset.checked_add(N).ok_or(Status::PACK_INVALID)?;
    let slice = bytes.get(offset..end).ok_or(Status::PACK_INVALID)?;
    let mut output = [0u8; N];
    output.copy_from_slice(slice);
    Ok(output)
}

#[cfg(test)]
mod tests {
    use super::crc32_iso_hdlc;

    #[test]
    fn crc_matches_standard_check_value() {
        assert_eq!(crc32_iso_hdlc(b"123456789"), 0xcbf4_3926);
    }
}
