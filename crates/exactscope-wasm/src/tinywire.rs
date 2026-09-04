//! Bounded deterministic-CBOR `TinyWire` adapter for the fused v0.1 runtime.
//!
//! This module owns transport parsing/encoding only. All calculations delegate
//! to `exactscope-kernel`, and operation identity/discovery remains in
//! `exactscope-pack`.

use core::str;

use exactscope_kernel::{
    evaluate_operation, evaluate_statistics_operation, Decimal64, DecimalVector, EvaluationResult,
    ScalarValue, Status, ARGUMENT_INDEX_NONE, MAX_STATS_VECTOR_LEN, SEMANTIC_NUMBER,
};
use exactscope_pack::{
    empty_matches, empty_statistics_matches, FusedRegistry, Match, StatisticsMatch,
    StatisticsRegistry, ECON_UNDERGRAD_PACK_SLOT, STATISTICS_CORE_PACK_SLOT,
};

const PROTOCOL_MAJOR: u64 = 1;
const MESSAGE_FIND: u64 = 0;
const MESSAGE_EVAL: u64 = 1;
const MESSAGE_FIND_RESPONSE: u64 = 128;
const MESSAGE_EVAL_RESPONSE: u64 = 129;
const MESSAGE_ERROR_RESPONSE: u64 = 255;
const MAX_PAYLOAD: usize = 4_084;
const MAX_FIND_MATCHES: usize = 5;
const MAX_SCALAR_ARGS: usize = 12;
const MAX_STATS_ARGS: usize = 2;
const OUTPUT_SCALE_DEFAULT: i64 = -128;
const ROUNDING_DEFAULT: u64 = 255;
const EVAL_KNOWN_FLAGS: u64 = 0x0003;
const MAX_NESTING_DEPTH: u8 = 4;

/// Adapter result returned to the WebAssembly memory wrapper.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct WireResult {
    /// Semantic/transport status.
    pub status: Status,
    /// Bytes written on success/error response, or required bytes for
    /// [`Status::BUFFER_TOO_SMALL`].
    pub written_or_required: u32,
}

#[derive(Clone, Copy)]
struct WireFailure {
    status: Status,
    detail_code: u16,
    argument_index: u16,
    required_size: u32,
}

impl WireFailure {
    const fn new(status: Status) -> Self {
        Self {
            status,
            detail_code: 0,
            argument_index: ARGUMENT_INDEX_NONE,
            required_size: 0,
        }
    }

    const fn argument(status: Status, argument_index: u16) -> Self {
        Self {
            status,
            detail_code: 0,
            argument_index,
            required_size: 0,
        }
    }
}

#[derive(Clone, Copy)]
enum FindItem {
    Economics(Match),
    Statistics(StatisticsMatch),
}

#[derive(Clone, Copy)]
struct FindResponse {
    items: [Option<FindItem>; MAX_FIND_MATCHES],
    count: u8,
}

impl FindResponse {
    const fn empty() -> Self {
        Self {
            items: [None; MAX_FIND_MATCHES],
            count: 0,
        }
    }
}

#[derive(Clone, Copy)]
enum WireResponse {
    Eval(EvaluationResult),
    Find(FindResponse),
    Error(WireFailure),
}

impl WireResponse {
    const fn status(&self) -> Status {
        match self {
            Self::Eval(result) => result.status,
            Self::Find(_) => Status::OK,
            Self::Error(failure) => failure.status,
        }
    }
}

#[derive(Clone, Copy)]
enum OperationKind {
    Economics(&'static exactscope_kernel::OperationDecl),
    Statistics(&'static exactscope_kernel::StatisticsOperationDecl),
    UnknownPack,
    UnknownOperation,
}

#[derive(Clone, Copy)]
struct CborVector<'a> {
    bytes: &'a [u8],
    offsets: [u16; MAX_STATS_VECTOR_LEN],
    len: u16,
}

impl<'a> CborVector<'a> {
    fn empty(bytes: &'a [u8]) -> Self {
        Self {
            bytes,
            offsets: [0; MAX_STATS_VECTOR_LEN],
            len: 0,
        }
    }
}

impl DecimalVector for CborVector<'_> {
    fn len(&self) -> usize {
        usize::from(self.len)
    }

    fn value_at(&self, index: usize) -> Result<Decimal64, Status> {
        if index >= self.len() {
            return Err(Status::INTERNAL_ERROR);
        }
        let offset = usize::from(self.offsets[index]);
        let mut reader = CborReader::at(self.bytes, offset)?;
        reader.read_decimal()
    }
}

struct CborReader<'a> {
    bytes: &'a [u8],
    cursor: usize,
}

impl<'a> CborReader<'a> {
    const fn new(bytes: &'a [u8]) -> Self {
        Self { bytes, cursor: 0 }
    }

    fn at(bytes: &'a [u8], cursor: usize) -> Result<Self, Status> {
        if cursor > bytes.len() {
            return Err(Status::INVALID_REQUEST);
        }
        Ok(Self { bytes, cursor })
    }

    const fn position(&self) -> usize {
        self.cursor
    }

    fn finish(&self) -> Result<(), Status> {
        if self.cursor == self.bytes.len() {
            Ok(())
        } else {
            Err(Status::INVALID_REQUEST)
        }
    }

    fn read_byte(&mut self) -> Result<u8, Status> {
        let byte = *self.bytes.get(self.cursor).ok_or(Status::INVALID_REQUEST)?;
        self.cursor = self.cursor.checked_add(1).ok_or(Status::RESOURCE_LIMIT)?;
        Ok(byte)
    }

    fn read_exact(&mut self, len: usize) -> Result<&'a [u8], Status> {
        let end = self.cursor.checked_add(len).ok_or(Status::RESOURCE_LIMIT)?;
        let bytes = self
            .bytes
            .get(self.cursor..end)
            .ok_or(Status::INVALID_REQUEST)?;
        self.cursor = end;
        Ok(bytes)
    }

    fn read_head(&mut self) -> Result<(u8, u64), Status> {
        let initial = self.read_byte()?;
        let major = initial >> 5;
        let additional = initial & 0x1f;
        let value = match additional {
            0..=23 => u64::from(additional),
            24 => {
                let value = u64::from(self.read_byte()?);
                if value < 24 {
                    return Err(Status::INVALID_REQUEST);
                }
                value
            }
            25 => {
                let bytes: [u8; 2] = self
                    .read_exact(2)?
                    .try_into()
                    .map_err(|_| Status::INTERNAL_ERROR)?;
                let value = u64::from(u16::from_be_bytes(bytes));
                if u8::try_from(value).is_ok() {
                    return Err(Status::INVALID_REQUEST);
                }
                value
            }
            26 => {
                let bytes: [u8; 4] = self
                    .read_exact(4)?
                    .try_into()
                    .map_err(|_| Status::INTERNAL_ERROR)?;
                let value = u64::from(u32::from_be_bytes(bytes));
                if u16::try_from(value).is_ok() {
                    return Err(Status::INVALID_REQUEST);
                }
                value
            }
            27 => {
                let bytes: [u8; 8] = self
                    .read_exact(8)?
                    .try_into()
                    .map_err(|_| Status::INTERNAL_ERROR)?;
                let value = u64::from_be_bytes(bytes);
                if u32::try_from(value).is_ok() {
                    return Err(Status::INVALID_REQUEST);
                }
                value
            }
            _ => return Err(Status::INVALID_REQUEST),
        };
        Ok((major, value))
    }

    fn read_uint(&mut self) -> Result<u64, Status> {
        let (major, value) = self.read_head()?;
        if major == 0 {
            Ok(value)
        } else {
            Err(Status::INVALID_REQUEST)
        }
    }

    fn read_integer(&mut self) -> Result<i64, Status> {
        let (major, value) = self.read_head()?;
        match major {
            0 => i64::try_from(value).map_err(|_| Status::RESOURCE_LIMIT),
            1 => {
                let magnitude = i128::from(value);
                i64::try_from(-1_i128 - magnitude).map_err(|_| Status::RESOURCE_LIMIT)
            }
            _ => Err(Status::INVALID_REQUEST),
        }
    }

    fn read_len(&mut self, expected_major: u8, cap: usize) -> Result<usize, Status> {
        let (major, value) = self.read_head()?;
        if major != expected_major {
            return Err(Status::INVALID_REQUEST);
        }
        let len = usize::try_from(value).map_err(|_| Status::RESOURCE_LIMIT)?;
        if len > cap {
            return Err(Status::RESOURCE_LIMIT);
        }
        Ok(len)
    }

    fn read_text(&mut self, cap: usize) -> Result<&'a [u8], Status> {
        let len = self.read_len(3, cap)?;
        let text = self.read_exact(len)?;
        str::from_utf8(text).map_err(|_| Status::INVALID_REQUEST)?;
        Ok(text)
    }

    fn read_key(&mut self, expected: u64) -> Result<(), Status> {
        if self.read_uint()? == expected {
            Ok(())
        } else {
            Err(Status::INVALID_REQUEST)
        }
    }

    fn read_decimal(&mut self) -> Result<Decimal64, Status> {
        let (major, tag) = self.read_head()?;
        if major != 6 || tag != 4 {
            return Err(Status::ARGUMENT_TYPE);
        }
        if self.read_len(4, 2)? != 2 {
            return Err(Status::INVALID_REQUEST);
        }
        let exponent = self.read_integer()?;
        let coefficient = self.read_integer()?;
        let exponent = i8::try_from(exponent).map_err(|_| Status::INVALID_DECIMAL)?;
        let decimal = Decimal64::from_parts(coefficient, exponent)?;
        if decimal.coefficient() != coefficient || decimal.exponent() != exponent {
            return Err(Status::INVALID_DECIMAL);
        }
        Ok(decimal)
    }

    fn skip_value(&mut self, depth: u8) -> Result<(), Status> {
        if depth >= MAX_NESTING_DEPTH {
            return Err(Status::RESOURCE_LIMIT);
        }
        let (major, value) = self.read_head()?;
        match major {
            0 | 1 => Ok(()),
            2 => {
                let len = usize::try_from(value).map_err(|_| Status::RESOURCE_LIMIT)?;
                self.read_exact(len).map(|_| ())
            }
            3 => {
                let len = usize::try_from(value).map_err(|_| Status::RESOURCE_LIMIT)?;
                let text = self.read_exact(len)?;
                str::from_utf8(text).map_err(|_| Status::INVALID_REQUEST)?;
                Ok(())
            }
            4 => {
                let count = usize::try_from(value).map_err(|_| Status::RESOURCE_LIMIT)?;
                if count > MAX_STATS_VECTOR_LEN {
                    return Err(Status::RESOURCE_LIMIT);
                }
                for _ in 0..count {
                    self.skip_value(depth + 1)?;
                }
                Ok(())
            }
            5 => {
                let count = usize::try_from(value).map_err(|_| Status::RESOURCE_LIMIT)?;
                if count > 64 {
                    return Err(Status::RESOURCE_LIMIT);
                }
                let mut previous_key = None;
                for _ in 0..count {
                    let key = self.read_uint()?;
                    if previous_key.is_some_and(|previous| key <= previous) {
                        return Err(Status::INVALID_REQUEST);
                    }
                    previous_key = Some(key);
                    self.skip_value(depth + 1)?;
                }
                Ok(())
            }
            6 => {
                if value != 4 {
                    return Err(Status::INVALID_REQUEST);
                }
                self.skip_value(depth + 1)
            }
            _ => Err(Status::INVALID_REQUEST),
        }
    }
}

struct CborWriter<'a> {
    bytes: &'a mut [u8],
    cursor: usize,
}

impl<'a> CborWriter<'a> {
    fn new(bytes: &'a mut [u8]) -> Self {
        Self { bytes, cursor: 0 }
    }

    const fn written(&self) -> usize {
        self.cursor
    }

    fn write_byte(&mut self, value: u8) -> Result<(), Status> {
        let slot = self
            .bytes
            .get_mut(self.cursor)
            .ok_or(Status::BUFFER_TOO_SMALL)?;
        *slot = value;
        self.cursor = self.cursor.checked_add(1).ok_or(Status::RESOURCE_LIMIT)?;
        Ok(())
    }

    fn write_bytes(&mut self, values: &[u8]) -> Result<(), Status> {
        let end = self
            .cursor
            .checked_add(values.len())
            .ok_or(Status::RESOURCE_LIMIT)?;
        let target = self
            .bytes
            .get_mut(self.cursor..end)
            .ok_or(Status::BUFFER_TOO_SMALL)?;
        target.copy_from_slice(values);
        self.cursor = end;
        Ok(())
    }

    fn write_head(&mut self, major: u8, value: u64) -> Result<(), Status> {
        let prefix = major << 5;
        match value {
            0..=23 => self.write_byte(prefix | u8::try_from(value).unwrap_or(0)),
            24..=0xff => {
                self.write_byte(prefix | 0x18)?;
                self.write_byte(u8::try_from(value).map_err(|_| Status::INTERNAL_ERROR)?)
            }
            0x100..=0xffff => {
                self.write_byte(prefix | 0x19)?;
                self.write_bytes(
                    &u16::try_from(value)
                        .map_err(|_| Status::INTERNAL_ERROR)?
                        .to_be_bytes(),
                )
            }
            0x1_0000..=0xffff_ffff => {
                self.write_byte(prefix | 0x1a)?;
                self.write_bytes(
                    &u32::try_from(value)
                        .map_err(|_| Status::INTERNAL_ERROR)?
                        .to_be_bytes(),
                )
            }
            _ => {
                self.write_byte(prefix | 0x1b)?;
                self.write_bytes(&value.to_be_bytes())
            }
        }
    }

    fn write_uint(&mut self, value: u64) -> Result<(), Status> {
        self.write_head(0, value)
    }

    fn write_integer(&mut self, value: i64) -> Result<(), Status> {
        if value >= 0 {
            self.write_uint(u64::try_from(value).map_err(|_| Status::INTERNAL_ERROR)?)
        } else {
            let encoded =
                u64::try_from(-1_i128 - i128::from(value)).map_err(|_| Status::INTERNAL_ERROR)?;
            self.write_head(1, encoded)
        }
    }

    fn write_array(&mut self, len: usize) -> Result<(), Status> {
        self.write_head(4, u64::try_from(len).map_err(|_| Status::RESOURCE_LIMIT)?)
    }

    fn write_map(&mut self, len: usize) -> Result<(), Status> {
        self.write_head(5, u64::try_from(len).map_err(|_| Status::RESOURCE_LIMIT)?)
    }

    fn write_text(&mut self, text: &str) -> Result<(), Status> {
        self.write_head(
            3,
            u64::try_from(text.len()).map_err(|_| Status::RESOURCE_LIMIT)?,
        )?;
        self.write_bytes(text.as_bytes())
    }

    fn write_decimal(&mut self, decimal: Decimal64) -> Result<(), Status> {
        self.write_head(6, 4)?;
        self.write_array(2)?;
        self.write_integer(i64::from(decimal.exponent()))?;
        self.write_integer(decimal.coefficient())
    }
}

/// Parses and executes one raw deterministic-CBOR `TinyWire` payload.
///
/// v0.1 supports fused find and eval requests with bounded, allocation-free
/// parsing. Calculation semantics remain delegated to the shared kernel.
pub fn request(input: &[u8], output: &mut [u8]) -> WireResult {
    let response = match decode_request(input) {
        Ok(response) => response,
        Err(failure) => WireResponse::Error(failure),
    };
    let status = response.status();
    let encoded_len = match encoded_response_len(&response) {
        Ok(len) => len,
        Err(status) => {
            return WireResult {
                status,
                written_or_required: 0,
            };
        }
    };
    let required = u32::try_from(encoded_len).unwrap_or(u32::MAX);
    if output.len() < encoded_len {
        return WireResult {
            status: Status::BUFFER_TOO_SMALL,
            written_or_required: required,
        };
    }
    let written = match encode_response(&response, output) {
        Ok(written) if written == encoded_len => written,
        Ok(_) => {
            return WireResult {
                status: Status::INTERNAL_ERROR,
                written_or_required: 0,
            };
        }
        Err(status) => {
            return WireResult {
                status,
                written_or_required: 0,
            };
        }
    };
    WireResult {
        status,
        written_or_required: u32::try_from(written).unwrap_or(u32::MAX),
    }
}

fn decode_request(input: &[u8]) -> Result<WireResponse, WireFailure> {
    if input.is_empty() {
        return Err(WireFailure::new(Status::INVALID_REQUEST));
    }
    if input.len() > MAX_PAYLOAD {
        return Err(WireFailure::new(Status::RESOURCE_LIMIT));
    }

    let mut reader = CborReader::new(input);
    let map_len = reader.read_len(5, 8).map_err(WireFailure::new)?;
    if map_len < 2 {
        return Err(WireFailure::new(Status::INVALID_REQUEST));
    }
    reader.read_key(0).map_err(WireFailure::new)?;
    if reader.read_uint().map_err(WireFailure::new)? != PROTOCOL_MAJOR {
        return Err(WireFailure::new(Status::ABI_MISMATCH));
    }
    reader.read_key(1).map_err(WireFailure::new)?;
    let message_type = reader.read_uint().map_err(WireFailure::new)?;

    match message_type {
        MESSAGE_FIND => decode_find(&mut reader, map_len).map(WireResponse::Find),
        MESSAGE_EVAL => decode_eval(&mut reader, input, map_len).map(WireResponse::Eval),
        _ => Err(WireFailure::new(Status::INVALID_REQUEST)),
    }
}

fn decode_find(reader: &mut CborReader<'_>, map_len: usize) -> Result<FindResponse, WireFailure> {
    if map_len != 4 {
        return Err(WireFailure::new(Status::INVALID_REQUEST));
    }
    reader.read_key(2).map_err(WireFailure::new)?;
    let query = reader.read_text(96).map_err(WireFailure::new)?;
    if query.is_empty() {
        return Err(WireFailure::new(Status::INVALID_REQUEST));
    }
    reader.read_key(3).map_err(WireFailure::new)?;
    let limit = usize::try_from(reader.read_uint().map_err(WireFailure::new)?)
        .map_err(|_| WireFailure::new(Status::RESOURCE_LIMIT))?;
    if limit == 0 || limit > MAX_FIND_MATCHES {
        return Err(WireFailure::new(Status::RESOURCE_LIMIT));
    }
    reader.finish().map_err(WireFailure::new)?;

    let mut response = FindResponse::empty();
    let mut economics = empty_matches();
    match FusedRegistry::new().find(query, &mut economics[..limit]) {
        Ok(count) => {
            for (index, found) in economics[..count].iter().copied().enumerate() {
                response.items[index] = Some(FindItem::Economics(found));
            }
            response.count =
                u8::try_from(count).map_err(|_| WireFailure::new(Status::INTERNAL_ERROR))?;
            return Ok(response);
        }
        Err(Status::UNKNOWN_OPERATION) => {}
        Err(status) => return Err(WireFailure::new(status)),
    }

    let mut statistics = empty_statistics_matches();
    let count = StatisticsRegistry::new()
        .find(query, &mut statistics[..limit])
        .map_err(WireFailure::new)?;
    for (index, found) in statistics[..count].iter().copied().enumerate() {
        response.items[index] = Some(FindItem::Statistics(found));
    }
    response.count = u8::try_from(count).map_err(|_| WireFailure::new(Status::INTERNAL_ERROR))?;
    Ok(response)
}

fn decode_eval<'a>(
    reader: &mut CborReader<'a>,
    input: &'a [u8],
    map_len: usize,
) -> Result<EvaluationResult, WireFailure> {
    if map_len != 8 {
        return Err(WireFailure::new(Status::INVALID_REQUEST));
    }
    reader.read_key(2).map_err(WireFailure::new)?;
    let pack_slot = u16::try_from(reader.read_uint().map_err(WireFailure::new)?)
        .map_err(|_| WireFailure::new(Status::RESOURCE_LIMIT))?;
    reader.read_key(3).map_err(WireFailure::new)?;
    let operation_id = u32::try_from(reader.read_uint().map_err(WireFailure::new)?)
        .map_err(|_| WireFailure::new(Status::RESOURCE_LIMIT))?;
    let operation = resolve_operation(pack_slot, operation_id);

    reader.read_key(4).map_err(WireFailure::new)?;
    let mut scalar_args = [ScalarValue::new(Decimal64::ZERO, 0, 0); MAX_SCALAR_ARGS];
    let mut vector_args = [CborVector::empty(input); MAX_STATS_ARGS];
    let arg_count = parse_arguments(reader, input, operation, &mut scalar_args, &mut vector_args)?;

    reader.read_key(5).map_err(WireFailure::new)?;
    if reader.read_integer().map_err(WireFailure::new)? != OUTPUT_SCALE_DEFAULT {
        return Err(WireFailure::new(Status::INVALID_REQUEST));
    }
    reader.read_key(6).map_err(WireFailure::new)?;
    if reader.read_uint().map_err(WireFailure::new)? != ROUNDING_DEFAULT {
        return Err(WireFailure::new(Status::INVALID_REQUEST));
    }
    reader.read_key(7).map_err(WireFailure::new)?;
    let flags = reader.read_uint().map_err(WireFailure::new)?;
    if flags & !EVAL_KNOWN_FLAGS != 0 {
        return Err(WireFailure::new(Status::INVALID_REQUEST));
    }
    reader.finish().map_err(WireFailure::new)?;

    match operation {
        OperationKind::Economics(operation) => Ok(evaluate_operation(
            ECON_UNDERGRAD_PACK_SLOT,
            operation,
            &scalar_args[..arg_count],
        )),
        OperationKind::Statistics(operation) => Ok(evaluate_statistics_operation(
            STATISTICS_CORE_PACK_SLOT,
            operation,
            &vector_args[..arg_count],
        )),
        OperationKind::UnknownPack => Err(WireFailure::new(Status::UNKNOWN_PACK)),
        OperationKind::UnknownOperation => Err(WireFailure::new(Status::UNKNOWN_OPERATION)),
    }
}

fn resolve_operation(pack_slot: u16, operation_id: u32) -> OperationKind {
    if pack_slot == ECON_UNDERGRAD_PACK_SLOT {
        return FusedRegistry::new()
            .lookup_id(operation_id)
            .map_or(OperationKind::UnknownOperation, |found| {
                OperationKind::Economics(found.operation)
            });
    }
    if pack_slot == STATISTICS_CORE_PACK_SLOT {
        return StatisticsRegistry::new()
            .lookup_id(operation_id)
            .map_or(OperationKind::UnknownOperation, |found| {
                OperationKind::Statistics(found.operation)
            });
    }
    OperationKind::UnknownPack
}

fn parse_arguments<'a>(
    reader: &mut CborReader<'a>,
    input: &'a [u8],
    operation: OperationKind,
    scalar_args: &mut [ScalarValue; MAX_SCALAR_ARGS],
    vector_args: &mut [CborVector<'a>; MAX_STATS_ARGS],
) -> Result<usize, WireFailure> {
    let cap = match operation {
        OperationKind::Statistics(_) => MAX_STATS_ARGS,
        _ => MAX_SCALAR_ARGS,
    };
    let arg_count = reader.read_len(4, cap).map_err(WireFailure::new)?;
    let expected = match operation {
        OperationKind::Economics(operation) => Some(operation.inputs.len()),
        OperationKind::Statistics(operation) => Some(usize::from(operation.input_count)),
        OperationKind::UnknownPack | OperationKind::UnknownOperation => None,
    };

    if let Some(expected) = expected {
        if arg_count != expected {
            for _ in 0..arg_count {
                reader.skip_value(1).map_err(WireFailure::new)?;
            }
            return Err(WireFailure::new(Status::ARGUMENT_COUNT));
        }
    }

    match operation {
        OperationKind::Economics(_) => {
            for (index, slot) in scalar_args.iter_mut().take(arg_count).enumerate() {
                *slot = parse_scalar_ref(reader)
                    .map_err(|status| WireFailure::argument(status, arg_index(index)))?;
            }
        }
        OperationKind::Statistics(_) => {
            for (index, slot) in vector_args.iter_mut().take(arg_count).enumerate() {
                *slot = parse_vector_ref(reader, input)
                    .map_err(|status| WireFailure::argument(status, arg_index(index)))?;
            }
        }
        OperationKind::UnknownPack | OperationKind::UnknownOperation => {
            for _ in 0..arg_count {
                reader.skip_value(1).map_err(WireFailure::new)?;
            }
        }
    }
    Ok(arg_count)
}

fn parse_scalar_ref(reader: &mut CborReader<'_>) -> Result<ScalarValue, Status> {
    if reader.read_len(4, 4)? != 4 {
        return Err(Status::INVALID_REQUEST);
    }
    if reader.read_uint()? != 0 {
        return Err(Status::ARGUMENT_TYPE);
    }
    let semantic = u8::try_from(reader.read_uint()?).map_err(|_| Status::ARGUMENT_TYPE)?;
    let unit_id = u16::try_from(reader.read_uint()?).map_err(|_| Status::UNIT_MISMATCH)?;
    let decimal = reader.read_decimal()?;
    let value = ScalarValue::new(decimal, semantic, unit_id);
    value.validate()?;
    Ok(value)
}

fn parse_vector_ref<'a>(
    reader: &mut CborReader<'a>,
    input: &'a [u8],
) -> Result<CborVector<'a>, Status> {
    if reader.read_len(4, 4)? != 4 {
        return Err(Status::INVALID_REQUEST);
    }
    if reader.read_uint()? != 1 {
        return Err(Status::ARGUMENT_TYPE);
    }
    let semantic = u8::try_from(reader.read_uint()?).map_err(|_| Status::ARGUMENT_TYPE)?;
    if semantic != SEMANTIC_NUMBER {
        return Err(Status::ARGUMENT_TYPE);
    }
    let unit_id = u16::try_from(reader.read_uint()?).map_err(|_| Status::UNIT_MISMATCH)?;
    if unit_id != 0 {
        return Err(Status::UNIT_MISMATCH);
    }
    let len = reader.read_len(4, MAX_STATS_VECTOR_LEN)?;
    let mut vector = CborVector::empty(input);
    vector.len = u16::try_from(len).map_err(|_| Status::RESOURCE_LIMIT)?;
    for index in 0..len {
        let offset = reader.position();
        vector.offsets[index] = u16::try_from(offset).map_err(|_| Status::RESOURCE_LIMIT)?;
        reader.read_decimal()?;
    }
    Ok(vector)
}

fn arg_index(index: usize) -> u16 {
    u16::try_from(index).unwrap_or(ARGUMENT_INDEX_NONE)
}

fn encoded_response_len(response: &WireResponse) -> Result<usize, Status> {
    let mut len = 0usize;
    match response {
        WireResponse::Eval(result) if result.status.is_ok() => {
            add_len(&mut len, head_len(9))?;
            add_pair_len(&mut len, 0, PROTOCOL_MAJOR)?;
            add_pair_len(&mut len, 1, MESSAGE_EVAL_RESPONSE)?;
            add_pair_len(&mut len, 2, u64::from(result.status.code()))?;
            add_len(&mut len, head_len(3))?;
            add_len(&mut len, head_len(u64::from(result.value_count)))?;
            for value in result.values.iter().take(usize::from(result.value_count)) {
                add_len(&mut len, decimal_len(value.decimal))?;
            }
            add_pair_len(&mut len, 4, u64::from(result.classification_id))?;
            add_pair_len(&mut len, 5, u64::from(result.flags))?;
            add_len(&mut len, head_len(6))?;
            add_len(&mut len, head_len(3))?;
            add_len(&mut len, head_len(u64::from(result.pack_slot)))?;
            add_len(&mut len, head_len(u64::from(result.operation_id)))?;
            add_len(&mut len, head_len(u64::from(result.operation_revision)))?;
            add_len(&mut len, head_len(7))?;
            add_len(&mut len, integer_len(i64::from(result.output_scale)))?;
            add_pair_len(&mut len, 8, u64::from(result.rounding_mode))?;
        }
        WireResponse::Eval(result) => {
            add_error_len(
                &mut len,
                result.status,
                result.detail_code,
                result.argument_index,
                result.required_size,
            )?;
        }
        WireResponse::Find(response) => {
            add_len(&mut len, head_len(4))?;
            add_pair_len(&mut len, 0, PROTOCOL_MAJOR)?;
            add_pair_len(&mut len, 1, MESSAGE_FIND_RESPONSE)?;
            add_pair_len(&mut len, 2, u64::from(Status::OK.code()))?;
            add_len(&mut len, head_len(3))?;
            add_len(&mut len, head_len(u64::from(response.count)))?;
            for item in response.items.iter().take(usize::from(response.count)) {
                let item = item.ok_or(Status::INTERNAL_ERROR)?;
                let (pack_slot, operation_id, revision, key, signature, method) =
                    find_item_fields(item);
                add_len(&mut len, head_len(6))?;
                add_len(&mut len, head_len(u64::from(pack_slot)))?;
                add_len(&mut len, head_len(u64::from(operation_id)))?;
                add_len(&mut len, head_len(u64::from(revision)))?;
                add_len(&mut len, text_len(key)?)?;
                add_len(&mut len, text_len(signature)?)?;
                add_len(&mut len, text_len(method)?)?;
            }
        }
        WireResponse::Error(failure) => {
            add_error_len(
                &mut len,
                failure.status,
                failure.detail_code,
                failure.argument_index,
                failure.required_size,
            )?;
        }
    }
    Ok(len)
}

fn encode_response(response: &WireResponse, output: &mut [u8]) -> Result<usize, Status> {
    let mut writer = CborWriter::new(output);
    match response {
        WireResponse::Eval(result) if result.status.is_ok() => {
            writer.write_map(9)?;
            writer.write_uint(0)?;
            writer.write_uint(PROTOCOL_MAJOR)?;
            writer.write_uint(1)?;
            writer.write_uint(MESSAGE_EVAL_RESPONSE)?;
            writer.write_uint(2)?;
            writer.write_uint(u64::from(result.status.code()))?;
            writer.write_uint(3)?;
            writer.write_array(usize::from(result.value_count))?;
            for value in result.values.iter().take(usize::from(result.value_count)) {
                writer.write_decimal(value.decimal)?;
            }
            writer.write_uint(4)?;
            writer.write_uint(u64::from(result.classification_id))?;
            writer.write_uint(5)?;
            writer.write_uint(u64::from(result.flags))?;
            writer.write_uint(6)?;
            writer.write_array(3)?;
            writer.write_uint(u64::from(result.pack_slot))?;
            writer.write_uint(u64::from(result.operation_id))?;
            writer.write_uint(u64::from(result.operation_revision))?;
            writer.write_uint(7)?;
            writer.write_integer(i64::from(result.output_scale))?;
            writer.write_uint(8)?;
            writer.write_uint(u64::from(result.rounding_mode))?;
        }
        WireResponse::Eval(result) => encode_error(
            &mut writer,
            result.status,
            result.detail_code,
            result.argument_index,
            result.required_size,
        )?,
        WireResponse::Find(response) => {
            writer.write_map(4)?;
            writer.write_uint(0)?;
            writer.write_uint(PROTOCOL_MAJOR)?;
            writer.write_uint(1)?;
            writer.write_uint(MESSAGE_FIND_RESPONSE)?;
            writer.write_uint(2)?;
            writer.write_uint(u64::from(Status::OK.code()))?;
            writer.write_uint(3)?;
            writer.write_array(usize::from(response.count))?;
            for item in response.items.iter().take(usize::from(response.count)) {
                let item = item.ok_or(Status::INTERNAL_ERROR)?;
                let (pack_slot, operation_id, revision, key, signature, method) =
                    find_item_fields(item);
                writer.write_array(6)?;
                writer.write_uint(u64::from(pack_slot))?;
                writer.write_uint(u64::from(operation_id))?;
                writer.write_uint(u64::from(revision))?;
                writer.write_text(key)?;
                writer.write_text(signature)?;
                writer.write_text(method)?;
            }
        }
        WireResponse::Error(failure) => encode_error(
            &mut writer,
            failure.status,
            failure.detail_code,
            failure.argument_index,
            failure.required_size,
        )?,
    }
    Ok(writer.written())
}

fn encode_error(
    writer: &mut CborWriter<'_>,
    status: Status,
    detail_code: u16,
    argument_index: u16,
    required_size: u32,
) -> Result<(), Status> {
    writer.write_map(7)?;
    writer.write_uint(0)?;
    writer.write_uint(PROTOCOL_MAJOR)?;
    writer.write_uint(1)?;
    writer.write_uint(MESSAGE_ERROR_RESPONSE)?;
    writer.write_uint(2)?;
    writer.write_uint(u64::from(status.code()))?;
    writer.write_uint(3)?;
    writer.write_uint(u64::from(detail_code))?;
    writer.write_uint(4)?;
    writer.write_uint(u64::from(argument_index))?;
    writer.write_uint(5)?;
    writer.write_uint(u64::from(required_size))?;
    writer.write_uint(6)?;
    writer.write_array(0)
}

fn add_error_len(
    len: &mut usize,
    status: Status,
    detail_code: u16,
    argument_index: u16,
    required_size: u32,
) -> Result<(), Status> {
    add_len(len, head_len(7))?;
    add_pair_len(len, 0, PROTOCOL_MAJOR)?;
    add_pair_len(len, 1, MESSAGE_ERROR_RESPONSE)?;
    add_pair_len(len, 2, u64::from(status.code()))?;
    add_pair_len(len, 3, u64::from(detail_code))?;
    add_pair_len(len, 4, u64::from(argument_index))?;
    add_pair_len(len, 5, u64::from(required_size))?;
    add_len(len, head_len(6))?;
    add_len(len, head_len(0))
}

fn add_pair_len(len: &mut usize, key: u64, value: u64) -> Result<(), Status> {
    add_len(len, head_len(key))?;
    add_len(len, head_len(value))
}

fn add_len(total: &mut usize, value: usize) -> Result<(), Status> {
    *total = total.checked_add(value).ok_or(Status::RESOURCE_LIMIT)?;
    Ok(())
}

const fn head_len(value: u64) -> usize {
    match value {
        0..=23 => 1,
        24..=0xff => 2,
        0x100..=0xffff => 3,
        0x1_0000..=0xffff_ffff => 5,
        _ => 9,
    }
}

fn integer_len(value: i64) -> usize {
    if value >= 0 {
        head_len(u64::try_from(value).unwrap_or(u64::MAX))
    } else {
        let encoded = u64::try_from(-1_i128 - i128::from(value)).unwrap_or(u64::MAX);
        head_len(encoded)
    }
}

fn decimal_len(decimal: Decimal64) -> usize {
    2 + integer_len(i64::from(decimal.exponent())) + integer_len(decimal.coefficient())
}

fn text_len(text: &str) -> Result<usize, Status> {
    let len = u64::try_from(text.len()).map_err(|_| Status::RESOURCE_LIMIT)?;
    head_len(len)
        .checked_add(text.len())
        .ok_or(Status::RESOURCE_LIMIT)
}

fn find_item_fields(item: FindItem) -> (u16, u32, u16, &'static str, &'static str, &'static str) {
    match item {
        FindItem::Economics(found) => {
            let operation = found.operation.operation;
            (
                found.operation.pack_slot,
                operation.id,
                operation.revision,
                operation.key,
                operation.signature,
                operation.method,
            )
        }
        FindItem::Statistics(found) => {
            let operation = found.operation.operation;
            (
                found.operation.pack_slot,
                operation.id,
                operation.revision,
                operation.key,
                operation.signature,
                operation.method,
            )
        }
    }
}

#[cfg(test)]
#[allow(
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss,
    clippy::decimal_bitwise_operands
)]
mod tests {
    use super::{request, Status};

    fn decimal(exponent: i8, coefficient: i64) -> Vec<u8> {
        let mut output = vec![0xc4, 0x82];
        encode_i64(&mut output, i64::from(exponent));
        encode_i64(&mut output, coefficient);
        output
    }

    fn encode_i64(output: &mut Vec<u8>, value: i64) {
        if value >= 0 {
            encode_head(output, 0, value as u64);
        } else {
            encode_head(output, 1, (-1_i128 - i128::from(value)) as u64);
        }
    }

    fn encode_head(output: &mut Vec<u8>, major: u8, value: u64) {
        let prefix = major << 5;
        match value {
            0..=23 => output.push(prefix | value as u8),
            24..=0xff => {
                output.extend_from_slice(&[prefix | 24, value as u8]);
            }
            0x100..=0xffff => {
                output.push(prefix | 25);
                output.extend_from_slice(&(value as u16).to_be_bytes());
            }
            0x1_0000..=0xffff_ffff => {
                output.push(prefix | 26);
                output.extend_from_slice(&(value as u32).to_be_bytes());
            }
            _ => {
                output.push(prefix | 27);
                output.extend_from_slice(&value.to_be_bytes());
            }
        }
    }

    fn eval_request(pack_slot: u16, operation_id: u32, refs: &[Vec<u8>]) -> Vec<u8> {
        let mut output = vec![0xa8, 0x00, 0x01, 0x01, 0x01, 0x02];
        encode_head(&mut output, 0, u64::from(pack_slot));
        output.push(0x03);
        encode_head(&mut output, 0, u64::from(operation_id));
        output.push(0x04);
        encode_head(&mut output, 4, refs.len() as u64);
        for value in refs {
            output.extend_from_slice(value);
        }
        output.extend_from_slice(&[0x05, 0x38, 0x7f, 0x06, 0x18, 0xff, 0x07, 0x00]);
        output
    }

    fn find_request(query: &str, limit: u8) -> Vec<u8> {
        let mut output = vec![0xa4, 0x00, 0x01, 0x01, 0x00, 0x02];
        encode_head(&mut output, 3, query.len() as u64);
        output.extend_from_slice(query.as_bytes());
        output.push(0x03);
        encode_head(&mut output, 0, u64::from(limit));
        output
    }

    fn scalar_ref(semantic: u8, exponent: i8, coefficient: i64) -> Vec<u8> {
        let mut output = vec![0x84, 0x00];
        encode_head(&mut output, 0, u64::from(semantic));
        output.push(0x00);
        output.extend_from_slice(&decimal(exponent, coefficient));
        output
    }

    fn vector_ref(values: &[(i8, i64)]) -> Vec<u8> {
        let mut output = vec![0x84, 0x01, 0x00, 0x00];
        encode_head(&mut output, 4, values.len() as u64);
        for &(exponent, coefficient) in values {
            output.extend_from_slice(&decimal(exponent, coefficient));
        }
        output
    }

    #[test]
    fn scalar_economics_eval_uses_shared_kernel() {
        let input = eval_request(
            1,
            301,
            &[
                scalar_ref(3, 4, 1),
                scalar_ref(3, 3, 12),
                scalar_ref(4, 2, 1),
                scalar_ref(4, 1, 8),
            ],
        );
        let mut output = [0u8; 256];
        let result = request(&input, &mut output);
        assert_eq!(result.status, Status::OK);
        assert!(result.written_or_required > 0);
        assert_eq!(output[0], 0xa9);
    }

    #[test]
    fn statistics_vector_eval_and_domain_failure_are_encoded() {
        let input = eval_request(
            2,
            10,
            &[
                vector_ref(&[(0, 1), (0, 2), (0, 3)]),
                vector_ref(&[(0, 1), (0, 2), (0, 4)]),
            ],
        );
        let mut output = [0u8; 256];
        let result = request(&input, &mut output);
        assert_eq!(result.status, Status::OK);
        assert_eq!(output[0], 0xa9);

        let zero_variance = eval_request(
            2,
            10,
            &[
                vector_ref(&[(0, 1), (0, 2), (0, 3)]),
                vector_ref(&[(0, 2), (0, 2), (0, 2)]),
            ],
        );
        let result = request(&zero_variance, &mut output);
        assert_eq!(result.status, Status::DOMAIN_ERROR);
        assert_eq!(output[0], 0xa7);
    }

    #[test]
    fn find_matches_economics_statistics_and_ambiguity_contracts() {
        let mut output = [0u8; 512];

        let economics = find_request("midpoint price elasticity", 3);
        let result = request(&economics, &mut output);
        assert_eq!(result.status, Status::OK);
        assert_eq!(output[0], 0xa4);
        let encoded = &output[..usize::try_from(result.written_or_required).unwrap()];
        assert!(encoded
            .windows(b"econ.ped.mid".len())
            .any(|window| window == b"econ.ped.mid"));

        let statistics = find_request("pearson correlation", 3);
        let result = request(&statistics, &mut output);
        assert_eq!(result.status, Status::OK);
        let encoded = &output[..usize::try_from(result.written_or_required).unwrap()];
        assert!(encoded
            .windows(b"stats.corr.pearson".len())
            .any(|window| window == b"stats.corr.pearson"));

        let ambiguous = find_request("price elasticity", 3);
        let result = request(&ambiguous, &mut output);
        assert_eq!(result.status, Status::AMBIGUOUS_METHOD);
        assert_eq!(output[0], 0xa7);
    }

    #[test]
    fn noncanonical_cbor_and_output_sizing_fail_closed() {
        let mut request_bytes = eval_request(2, 2, &[vector_ref(&[(0, 1), (0, 2)])]);
        // Replace canonical pack-slot 2 with the non-shortest uint8 representation.
        let pack_slot_position = 6;
        request_bytes.splice(pack_slot_position..=pack_slot_position, [0x18, 0x02]);
        let mut output = [0u8; 256];
        let result = request(&request_bytes, &mut output);
        assert_eq!(result.status, Status::INVALID_REQUEST);

        let canonical = eval_request(2, 2, &[vector_ref(&[(0, 1), (0, 2)])]);
        let mut tiny_output = [0u8; 2];
        let result = request(&canonical, &mut tiny_output);
        assert_eq!(result.status, Status::BUFFER_TOO_SMALL);
        assert!(result.written_or_required > tiny_output.len() as u32);
    }
}
