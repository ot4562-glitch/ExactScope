#![no_std]
#![forbid(unsafe_code)]
#![doc = "Bounded two-tool Tiny JSON adapter for `ExactScope`."]

//! This first implementation accepts the canonical, allocation-free subset
//! emitted by constrained tool-call grammars. It exposes separate `find` and
//! `eval` entry points, preserves exact decimal strings, and delegates every
//! calculation and classification decision to `exactscope-kernel`.

pub use exactscope_kernel::{DESIGN_ABI_MAJOR, DESIGN_ABI_MINOR};

#[cfg(test)]
extern crate std;

use exactscope_kernel::{
    classification_key, evaluate_operation, evaluate_statistics_operation,
    statistics_kernel_output_names, Decimal64, EvaluationResult, ScalarValue, Status,
    ARGUMENT_INDEX_NONE,
};
use exactscope_pack::{
    empty_matches, empty_statistics_matches, FusedRegistry, Match, StatisticsMatch,
    StatisticsRegistry,
};

/// Hard v0.1 request-size cap.
pub const MAX_TINY_JSON_REQUEST_BYTES: usize = 512;
/// Hard v0.1 top-level argument cap.
pub const MAX_TINY_JSON_ARGUMENTS: usize = 12;
/// Hard cap on the total number of decimal values carried by scalar/vector
/// model-facing arguments in one Tiny JSON request.
pub const MAX_TINY_JSON_VECTOR_VALUES: usize = 64;
/// Internal bounded response staging capacity for the first slice.
pub const MAX_TINY_JSON_RESPONSE_BYTES: usize = 512;

const EMPTY_SCALAR: ScalarValue = ScalarValue::new(Decimal64::ZERO, 0, 0);
const ARGUMENT_SCALAR: u8 = 0;
const ARGUMENT_VECTOR: u8 = 1;

/// Result of one bounded Tiny JSON adapter call.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct AdapterResult {
    /// Semantic/transport status. `BUFFER_TOO_SMALL` takes precedence when the
    /// caller output cannot contain the complete response.
    pub status: Status,
    /// Bytes written on success, or complete required capacity when the caller
    /// buffer is too small.
    pub written_or_required: u32,
}

/// Evaluates one canonical Tiny JSON `xs_eval` argument object.
///
/// Supported first-slice request:
///
/// ```text
/// {"op":"econ.ped.mid","a":["10000","12000","100","80"]}
/// ```
///
/// The parser intentionally rejects string escapes in operation keys and
/// decimal arguments. Grammar-constrained clients should emit their canonical
/// ASCII spelling directly; accepting an equivalent escaped spelling adds no
/// quantitative capability and increases parser surface on tiny devices.
///
/// # Errors
///
/// Errors are returned as [`AdapterResult::status`] and, when the output buffer
/// is large enough, are also serialized as compact Tiny JSON.
#[must_use]
pub fn eval(input: &[u8], output: &mut [u8]) -> AdapterResult {
    let response = match parse_eval_request(input) {
        Ok(request) => evaluate_request(input, &request),
        Err(status) => Response::Error(ErrorResponse::new(status)),
    };
    write_response(&response, output)
}

/// Discovers one method-specific fused operation using `xs_find` Tiny JSON.
///
/// # Errors
///
/// Errors are returned and serialized without guessing an operation.
#[must_use]
pub fn find(input: &[u8], output: &mut [u8]) -> AdapterResult {
    let response = match parse_find_request(input) {
        Ok(request) => find_request(input, request),
        Err(status) => Response::Error(ErrorResponse::new(status)),
    };
    write_response(&response, output)
}

/// Processes either canonical `xs_eval` or `xs_find` Tiny JSON arguments.
///
/// This is the fused one-call entry used by the WebAssembly helper. It parses
/// the request shape first and then delegates to the same typed paths exposed
/// by [`eval`] and [`find`].
#[must_use]
pub fn request(input: &[u8], output: &mut [u8]) -> AdapterResult {
    let response = match parse_eval_request(input) {
        Ok(request) => evaluate_request(input, &request),
        Err(eval_status) => match parse_find_request(input) {
            Ok(request) => find_request(input, request),
            Err(find_status) => Response::Error(ErrorResponse::new(select_parse_status(
                eval_status,
                find_status,
            ))),
        },
    };
    write_response(&response, output)
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct ByteSpan {
    start: u16,
    len: u16,
}

impl ByteSpan {
    const EMPTY: Self = Self { start: 0, len: 0 };

    fn new(start: usize, end: usize) -> Result<Self, Status> {
        let len = end.checked_sub(start).ok_or(Status::INTERNAL_ERROR)?;
        Ok(Self {
            start: u16::try_from(start).map_err(|_| Status::RESOURCE_LIMIT)?,
            len: u16::try_from(len).map_err(|_| Status::RESOURCE_LIMIT)?,
        })
    }

    fn resolve(self, input: &[u8]) -> &[u8] {
        let start = usize::from(self.start);
        let end = start + usize::from(self.len);
        &input[start..end]
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct EvalRequest {
    operation: ByteSpan,
    arguments: [ArgumentSpan; MAX_TINY_JSON_ARGUMENTS],
    values: [ByteSpan; MAX_TINY_JSON_VECTOR_VALUES],
    argument_count: usize,
    value_count: usize,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct ArgumentSpan {
    value_kind: u8,
    first_value: usize,
    value_count: usize,
}

impl ArgumentSpan {
    const EMPTY: Self = Self {
        value_kind: ARGUMENT_SCALAR,
        first_value: 0,
        value_count: 0,
    };
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct FindRequest {
    query: ByteSpan,
    limit: usize,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct ErrorResponse {
    status: Status,
    argument_index: u16,
    detail_code: u16,
}

impl ErrorResponse {
    const fn new(status: Status) -> Self {
        Self {
            status,
            argument_index: ARGUMENT_INDEX_NONE,
            detail_code: 0,
        }
    }

    const fn from_evaluation(result: EvaluationResult) -> Self {
        Self {
            status: result.status,
            argument_index: result.argument_index,
            detail_code: result.detail_code,
        }
    }

    fn for_argument(status: Status, argument_index: usize) -> Self {
        Self {
            status,
            argument_index: u16::try_from(argument_index).unwrap_or(ARGUMENT_INDEX_NONE),
            detail_code: 0,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct EvalSuccess {
    result: EvaluationResult,
    provenance: &'static str,
    classification: Option<&'static str>,
    output_names: &'static [&'static str],
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct FindSuccess {
    matches: [Match; exactscope_pack::MAX_FIND_MATCHES],
    count: usize,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct StatisticsFindSuccess {
    matches: [StatisticsMatch; exactscope_pack::MAX_FIND_MATCHES],
    count: usize,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Response {
    Error(ErrorResponse),
    EvalSuccess(EvalSuccess),
    FindSuccess(FindSuccess),
    StatisticsFindSuccess(StatisticsFindSuccess),
}

fn evaluate_request(input: &[u8], request: &EvalRequest) -> Response {
    let operation_key = request.operation.resolve(input);
    match FusedRegistry::new().lookup(operation_key) {
        Ok(operation) => evaluate_scalar_request(input, request, operation),
        Err(Status::UNKNOWN_OPERATION) => match StatisticsRegistry::new().lookup(operation_key) {
            Ok(operation) => evaluate_statistics_request(input, request, operation),
            Err(status) => Response::Error(ErrorResponse::new(status)),
        },
        Err(status) => Response::Error(ErrorResponse::new(status)),
    }
}

fn evaluate_scalar_request(
    input: &[u8],
    request: &EvalRequest,
    operation: exactscope_pack::OperationRef,
) -> Response {
    if request.argument_count != operation.operation.inputs.len() {
        return Response::Error(ErrorResponse::from_evaluation(EvaluationResult::failure(
            Status::ARGUMENT_COUNT,
            operation.pack_slot,
            operation.operation,
            ARGUMENT_INDEX_NONE,
            0,
        )));
    }

    let mut arguments = [EMPTY_SCALAR; MAX_TINY_JSON_ARGUMENTS];
    for (index, argument) in request.arguments[..request.argument_count]
        .iter()
        .enumerate()
    {
        if argument.value_kind != ARGUMENT_SCALAR || argument.value_count != 1 {
            return Response::Error(ErrorResponse::for_argument(Status::ARGUMENT_TYPE, index));
        }
        let span = request.values[argument.first_value];
        let decimal = match Decimal64::parse_ascii(span.resolve(input)) {
            Ok(decimal) => decimal,
            Err(status) => {
                return Response::Error(ErrorResponse::from_evaluation(EvaluationResult::failure(
                    status,
                    operation.pack_slot,
                    operation.operation,
                    u16::try_from(index).unwrap_or(ARGUMENT_INDEX_NONE),
                    0,
                )));
            }
        };
        arguments[index] =
            ScalarValue::new(decimal, operation.operation.inputs[index].semantic_kind, 0);
    }

    let result = evaluate_operation(
        operation.pack_slot,
        operation.operation,
        &arguments[..request.argument_count],
    );
    if !result.status.is_ok() {
        return Response::Error(ErrorResponse::from_evaluation(result));
    }

    let classification = classification_key(operation.operation, result.classification_id);
    Response::EvalSuccess(EvalSuccess {
        result,
        provenance: operation.provenance,
        classification,
        output_names: &[],
    })
}

fn evaluate_statistics_request(
    input: &[u8],
    request: &EvalRequest,
    operation: exactscope_pack::StatisticsOperationRef,
) -> Response {
    if request.argument_count != usize::from(operation.operation.input_count) {
        return Response::Error(ErrorResponse::new(Status::ARGUMENT_COUNT));
    }

    let mut decimals = [Decimal64::ZERO; MAX_TINY_JSON_VECTOR_VALUES];
    for (argument_index, argument) in request.arguments[..request.argument_count]
        .iter()
        .enumerate()
    {
        if argument.value_kind != ARGUMENT_VECTOR {
            return Response::Error(ErrorResponse::for_argument(
                Status::ARGUMENT_TYPE,
                argument_index,
            ));
        }
        let end = match argument.first_value.checked_add(argument.value_count) {
            Some(end) if end <= request.value_count => end,
            _ => return Response::Error(ErrorResponse::new(Status::INTERNAL_ERROR)),
        };
        for (value_index, span) in request.values[argument.first_value..end].iter().enumerate() {
            let decimal = match Decimal64::parse_ascii(span.resolve(input)) {
                Ok(decimal) => decimal,
                Err(status) => {
                    return Response::Error(ErrorResponse::for_argument(status, argument_index));
                }
            };
            decimals[argument.first_value + value_index] = decimal;
        }
    }

    let mut vector_refs: [&[Decimal64]; MAX_TINY_JSON_ARGUMENTS] = [&[]; MAX_TINY_JSON_ARGUMENTS];
    for (index, argument) in request.arguments[..request.argument_count]
        .iter()
        .enumerate()
    {
        let end = argument.first_value + argument.value_count;
        vector_refs[index] = &decimals[argument.first_value..end];
    }
    let result = evaluate_statistics_operation(
        operation.pack_slot,
        operation.operation,
        &vector_refs[..request.argument_count],
    );
    if !result.status.is_ok() {
        return Response::Error(ErrorResponse::from_evaluation(result));
    }

    Response::EvalSuccess(EvalSuccess {
        result,
        provenance: operation.provenance,
        classification: None,
        output_names: statistics_kernel_output_names(operation.operation.kernel_id),
    })
}

fn find_request(input: &[u8], request: FindRequest) -> Response {
    let query = request.query.resolve(input);
    let mut matches = empty_matches();
    match FusedRegistry::new().find(query, &mut matches[..request.limit]) {
        Ok(count) => Response::FindSuccess(FindSuccess { matches, count }),
        Err(Status::UNKNOWN_OPERATION) => {
            let mut statistics_matches = empty_statistics_matches();
            match StatisticsRegistry::new().find(query, &mut statistics_matches[..request.limit]) {
                Ok(count) => Response::StatisticsFindSuccess(StatisticsFindSuccess {
                    matches: statistics_matches,
                    count,
                }),
                Err(status) => Response::Error(ErrorResponse::new(status)),
            }
        }
        Err(status) => Response::Error(ErrorResponse::new(status)),
    }
}

fn select_parse_status(eval_status: Status, find_status: Status) -> Status {
    if eval_status == Status::RESOURCE_LIMIT || find_status == Status::RESOURCE_LIMIT {
        Status::RESOURCE_LIMIT
    } else {
        Status::INVALID_REQUEST
    }
}

fn parse_eval_request(input: &[u8]) -> Result<EvalRequest, Status> {
    validate_request_bytes(input)?;
    let mut parser = Parser::new(input);
    parser.expect_byte(b'{')?;

    let mut operation = ByteSpan::EMPTY;
    let mut arguments = [ArgumentSpan::EMPTY; MAX_TINY_JSON_ARGUMENTS];
    let mut values = [ByteSpan::EMPTY; MAX_TINY_JSON_VECTOR_VALUES];
    let mut argument_count = 0usize;
    let mut value_count = 0usize;
    let mut seen_operation = false;
    let mut seen_arguments = false;

    loop {
        parser.skip_whitespace();
        if parser.consume_byte(b'}') {
            break;
        }
        let key = parser.parse_plain_string()?;
        parser.skip_whitespace();
        parser.expect_byte(b':')?;
        parser.skip_whitespace();

        match key.resolve(input) {
            b"op" if !seen_operation => {
                operation = parser.parse_plain_string()?;
                if operation.len == 0 || operation.len > 96 {
                    return Err(Status::INVALID_REQUEST);
                }
                seen_operation = true;
            }
            b"a" if !seen_arguments => {
                (argument_count, value_count) =
                    parser.parse_argument_array(&mut arguments, &mut values)?;
                seen_arguments = true;
            }
            _ => return Err(Status::INVALID_REQUEST),
        }

        parser.skip_whitespace();
        if parser.consume_byte(b',') {
            parser.skip_whitespace();
            if parser.input.get(parser.index) == Some(&b'}') {
                return Err(Status::INVALID_REQUEST);
            }
            continue;
        }
        parser.expect_byte(b'}')?;
        break;
    }

    parser.finish()?;
    if !seen_operation || !seen_arguments {
        return Err(Status::INVALID_REQUEST);
    }
    Ok(EvalRequest {
        operation,
        arguments,
        values,
        argument_count,
        value_count,
    })
}

fn parse_find_request(input: &[u8]) -> Result<FindRequest, Status> {
    validate_request_bytes(input)?;
    let mut parser = Parser::new(input);
    parser.expect_byte(b'{')?;

    let mut query = ByteSpan::EMPTY;
    let mut limit = 0usize;
    let mut seen_query = false;
    let mut seen_limit = false;

    loop {
        parser.skip_whitespace();
        if parser.consume_byte(b'}') {
            break;
        }
        let key = parser.parse_plain_string()?;
        parser.skip_whitespace();
        parser.expect_byte(b':')?;
        parser.skip_whitespace();

        match key.resolve(input) {
            b"q" if !seen_query => {
                query = parser.parse_plain_string()?;
                if query.len == 0 || query.len > 96 {
                    return Err(Status::INVALID_REQUEST);
                }
                seen_query = true;
            }
            b"n" if !seen_limit => {
                limit = parser.parse_bounded_usize(1, exactscope_pack::MAX_FIND_MATCHES)?;
                seen_limit = true;
            }
            _ => return Err(Status::INVALID_REQUEST),
        }

        parser.skip_whitespace();
        if parser.consume_byte(b',') {
            parser.skip_whitespace();
            if parser.input.get(parser.index) == Some(&b'}') {
                return Err(Status::INVALID_REQUEST);
            }
            continue;
        }
        parser.expect_byte(b'}')?;
        break;
    }

    parser.finish()?;
    if !seen_query || !seen_limit {
        return Err(Status::INVALID_REQUEST);
    }
    Ok(FindRequest { query, limit })
}

fn validate_request_bytes(input: &[u8]) -> Result<(), Status> {
    if input.is_empty() {
        return Err(Status::INVALID_REQUEST);
    }
    if input.len() > MAX_TINY_JSON_REQUEST_BYTES {
        return Err(Status::RESOURCE_LIMIT);
    }
    core::str::from_utf8(input).map_err(|_| Status::INVALID_REQUEST)?;
    Ok(())
}

struct Parser<'a> {
    input: &'a [u8],
    index: usize,
}

impl<'a> Parser<'a> {
    const fn new(input: &'a [u8]) -> Self {
        Self { input, index: 0 }
    }

    fn skip_whitespace(&mut self) {
        while matches!(
            self.input.get(self.index),
            Some(b' ' | b'\n' | b'\r' | b'\t')
        ) {
            self.index += 1;
        }
    }

    fn consume_byte(&mut self, expected: u8) -> bool {
        self.skip_whitespace();
        if self.input.get(self.index) == Some(&expected) {
            self.index += 1;
            true
        } else {
            false
        }
    }

    fn expect_byte(&mut self, expected: u8) -> Result<(), Status> {
        if self.consume_byte(expected) {
            Ok(())
        } else {
            Err(Status::INVALID_REQUEST)
        }
    }

    fn parse_plain_string(&mut self) -> Result<ByteSpan, Status> {
        self.skip_whitespace();
        if self.input.get(self.index) != Some(&b'"') {
            return Err(Status::INVALID_REQUEST);
        }
        self.index += 1;
        let start = self.index;
        while let Some(&byte) = self.input.get(self.index) {
            match byte {
                b'"' => {
                    let end = self.index;
                    self.index += 1;
                    return ByteSpan::new(start, end);
                }
                b'\\' | 0x00..=0x1f => return Err(Status::INVALID_REQUEST),
                _ => self.index += 1,
            }
        }
        Err(Status::INVALID_REQUEST)
    }

    fn parse_argument_array(
        &mut self,
        arguments: &mut [ArgumentSpan; MAX_TINY_JSON_ARGUMENTS],
        values: &mut [ByteSpan; MAX_TINY_JSON_VECTOR_VALUES],
    ) -> Result<(usize, usize), Status> {
        self.expect_byte(b'[')?;
        self.skip_whitespace();
        if self.consume_byte(b']') {
            return Ok((0, 0));
        }

        let mut argument_count = 0usize;
        let mut value_count = 0usize;
        loop {
            if argument_count == arguments.len() {
                return Err(Status::RESOURCE_LIMIT);
            }
            self.skip_whitespace();
            match self.input.get(self.index) {
                Some(b'"') => {
                    if value_count == values.len() {
                        return Err(Status::RESOURCE_LIMIT);
                    }
                    values[value_count] = self.parse_plain_string()?;
                    arguments[argument_count] = ArgumentSpan {
                        value_kind: ARGUMENT_SCALAR,
                        first_value: value_count,
                        value_count: 1,
                    };
                    value_count += 1;
                }
                Some(b'[') => {
                    let first_value = value_count;
                    self.expect_byte(b'[')?;
                    self.skip_whitespace();
                    if !self.consume_byte(b']') {
                        loop {
                            if value_count == values.len() {
                                return Err(Status::RESOURCE_LIMIT);
                            }
                            values[value_count] = self.parse_plain_string()?;
                            value_count += 1;
                            self.skip_whitespace();
                            if self.consume_byte(b',') {
                                continue;
                            }
                            self.expect_byte(b']')?;
                            break;
                        }
                    }
                    arguments[argument_count] = ArgumentSpan {
                        value_kind: ARGUMENT_VECTOR,
                        first_value,
                        value_count: value_count - first_value,
                    };
                }
                _ => return Err(Status::INVALID_REQUEST),
            }
            argument_count += 1;
            self.skip_whitespace();
            if self.consume_byte(b',') {
                continue;
            }
            self.expect_byte(b']')?;
            return Ok((argument_count, value_count));
        }
    }

    fn parse_bounded_usize(&mut self, minimum: usize, maximum: usize) -> Result<usize, Status> {
        self.skip_whitespace();
        let start = self.index;
        match self.input.get(self.index) {
            Some(b'0') => self.index += 1,
            Some(b'1'..=b'9') => {
                self.index += 1;
                while self.input.get(self.index).is_some_and(u8::is_ascii_digit) {
                    self.index += 1;
                }
            }
            _ => return Err(Status::INVALID_REQUEST),
        }
        if self.index - start > 1 && self.input[start] == b'0' {
            return Err(Status::INVALID_REQUEST);
        }

        let mut value = 0usize;
        for &digit in &self.input[start..self.index] {
            value = value
                .checked_mul(10)
                .and_then(|current| current.checked_add(usize::from(digit - b'0')))
                .ok_or(Status::RESOURCE_LIMIT)?;
        }
        if !(minimum..=maximum).contains(&value) {
            return Err(Status::INVALID_REQUEST);
        }
        Ok(value)
    }

    fn finish(&mut self) -> Result<(), Status> {
        self.skip_whitespace();
        if self.index == self.input.len() {
            Ok(())
        } else {
            Err(Status::INVALID_REQUEST)
        }
    }
}

fn write_response(response: &Response, output: &mut [u8]) -> AdapterResult {
    let mut staging = [0u8; MAX_TINY_JSON_RESPONSE_BYTES];
    let mut writer = Writer::new(&mut staging);
    let semantic_status = match response {
        Response::Error(error) => {
            if write_error(&mut writer, *error).is_err() {
                return internal_adapter_failure(output);
            }
            error.status
        }
        Response::EvalSuccess(success) => {
            if write_eval_success(&mut writer, success).is_err() {
                return internal_adapter_failure(output);
            }
            Status::OK
        }
        Response::FindSuccess(success) => {
            if write_find_success(&mut writer, success).is_err() {
                return internal_adapter_failure(output);
            }
            Status::OK
        }
        Response::StatisticsFindSuccess(success) => {
            if write_statistics_find_success(&mut writer, success).is_err() {
                return internal_adapter_failure(output);
            }
            Status::OK
        }
    };

    let required = writer.len();
    let required_u32 = u32::try_from(required).unwrap_or(u32::MAX);
    if output.len() < required {
        return AdapterResult {
            status: Status::BUFFER_TOO_SMALL,
            written_or_required: required_u32,
        };
    }
    output[..required].copy_from_slice(&staging[..required]);
    AdapterResult {
        status: semantic_status,
        written_or_required: required_u32,
    }
}

fn internal_adapter_failure(output: &mut [u8]) -> AdapterResult {
    const FALLBACK: &[u8] = b"{\"s\":23,\"e\":\"INTERNAL_ERROR\"}";
    let required = u32::try_from(FALLBACK.len()).unwrap_or(u32::MAX);
    if output.len() >= FALLBACK.len() {
        output[..FALLBACK.len()].copy_from_slice(FALLBACK);
        AdapterResult {
            status: Status::INTERNAL_ERROR,
            written_or_required: required,
        }
    } else {
        AdapterResult {
            status: Status::BUFFER_TOO_SMALL,
            written_or_required: required,
        }
    }
}

fn write_error(writer: &mut Writer<'_>, error: ErrorResponse) -> Result<(), Status> {
    writer.bytes(b"{\"s\":")?;
    writer.u16(error.status.code())?;
    writer.bytes(b",\"e\":\"")?;
    writer.bytes(status_key(error.status).as_bytes())?;
    writer.byte(b'"')?;
    if error.argument_index != ARGUMENT_INDEX_NONE {
        writer.bytes(b",\"i\":")?;
        writer.u16(error.argument_index)?;
    }
    if error.detail_code != 0 {
        writer.bytes(b",\"d\":")?;
        writer.u16(error.detail_code)?;
    }
    if error.status == Status::AMBIGUOUS_METHOD {
        writer.bytes(b",\"need\":[\"method\"]")?;
    }
    writer.byte(b'}')
}

fn write_eval_success(writer: &mut Writer<'_>, success: &EvalSuccess) -> Result<(), Status> {
    let result = success.result;
    let value_count = usize::from(result.value_count);
    if value_count == 0 || value_count > result.values.len() {
        return Err(Status::INTERNAL_ERROR);
    }
    writer.bytes(b"{\"s\":0,\"v\":")?;
    if value_count == 1 {
        write_decimal_string(writer, result.values[0].decimal)?;
    } else {
        if success.output_names.len() != value_count {
            return Err(Status::INTERNAL_ERROR);
        }
        writer.byte(b'[')?;
        for (index, value) in result.values[..value_count].iter().enumerate() {
            if index != 0 {
                writer.byte(b',')?;
            }
            write_decimal_string(writer, value.decimal)?;
        }
        writer.byte(b']')?;
        writer.bytes(b",\"names\":[")?;
        for (index, name) in success.output_names.iter().enumerate() {
            if index != 0 {
                writer.byte(b',')?;
            }
            writer.byte(b'"')?;
            writer.bytes(name.as_bytes())?;
            writer.byte(b'"')?;
        }
        writer.byte(b']')?;
    }
    if let Some(classification) = success.classification {
        writer.bytes(b",\"c\":\"")?;
        writer.bytes(classification.as_bytes())?;
        writer.byte(b'"')?;
    }
    writer.bytes(b",\"p\":\"")?;
    writer.bytes(success.provenance.as_bytes())?;
    writer.bytes(b"\",\"r\":")?;
    writer.u16(result.operation_revision)?;
    writer.byte(b'}')
}

fn write_decimal_string(writer: &mut Writer<'_>, decimal: Decimal64) -> Result<(), Status> {
    writer.byte(b'"')?;
    let mut encoded = [0u8; 64];
    let encoded_len = decimal.write_canonical(&mut encoded)?;
    writer.bytes(&encoded[..encoded_len])?;
    writer.byte(b'"')
}

fn write_find_success(writer: &mut Writer<'_>, success: &FindSuccess) -> Result<(), Status> {
    writer.bytes(b"{\"s\":0,\"m\":[")?;
    for index in 0..success.count {
        if index != 0 {
            writer.byte(b',')?;
        }
        let operation = success.matches[index].operation.operation;
        write_find_operation(writer, operation.key, operation.signature, operation.method)?;
    }
    writer.bytes(b"]}")
}

fn write_statistics_find_success(
    writer: &mut Writer<'_>,
    success: &StatisticsFindSuccess,
) -> Result<(), Status> {
    writer.bytes(b"{\"s\":0,\"m\":[")?;
    for index in 0..success.count {
        if index != 0 {
            writer.byte(b',')?;
        }
        let operation = success.matches[index].operation.operation;
        write_find_operation(writer, operation.key, operation.signature, operation.method)?;
    }
    writer.bytes(b"]}")
}

fn write_find_operation(
    writer: &mut Writer<'_>,
    key: &str,
    signature: &str,
    method: &str,
) -> Result<(), Status> {
    writer.bytes(b"{\"op\":\"")?;
    writer.bytes(key.as_bytes())?;
    writer.bytes(b"\",\"sig\":\"")?;
    writer.bytes(signature.as_bytes())?;
    writer.bytes(b"\",\"method\":\"")?;
    writer.bytes(method.as_bytes())?;
    writer.bytes(b"\"}")
}

fn status_key(status: Status) -> &'static str {
    match status.code() {
        0 => "OK",
        1 => "INVALID_REQUEST",
        2 => "ABI_MISMATCH",
        3 => "UNKNOWN_OPERATION",
        4 => "UNKNOWN_PACK",
        5 => "ARGUMENT_COUNT",
        6 => "ARGUMENT_TYPE",
        7 => "AMBIGUOUS_METHOD",
        8 => "MISSING_INFORMATION",
        9 => "INVALID_DECIMAL",
        10 => "DOMAIN_ERROR",
        11 => "CONSTRAINT_VIOLATION",
        12 => "UNIT_MISMATCH",
        13 => "DIVIDE_BY_ZERO",
        14 => "OVERFLOW",
        15 => "PRECISION_UNRESOLVED",
        16 => "INSUFFICIENT_DATA",
        17 => "BUFFER_TOO_SMALL",
        18 => "PACK_INVALID",
        19 => "PACK_VERSION_UNSUPPORTED",
        20 => "RESOURCE_LIMIT",
        21 => "UNSUPPORTED_OPERATION",
        22 => "INTEGRITY_ERROR",
        _ => "INTERNAL_ERROR",
    }
}

struct Writer<'a> {
    output: &'a mut [u8],
    len: usize,
}

impl<'a> Writer<'a> {
    const fn new(output: &'a mut [u8]) -> Self {
        Self { output, len: 0 }
    }

    const fn len(&self) -> usize {
        self.len
    }

    fn byte(&mut self, byte: u8) -> Result<(), Status> {
        if self.len == self.output.len() {
            return Err(Status::BUFFER_TOO_SMALL);
        }
        self.output[self.len] = byte;
        self.len += 1;
        Ok(())
    }

    fn bytes(&mut self, bytes: &[u8]) -> Result<(), Status> {
        let end = self
            .len
            .checked_add(bytes.len())
            .ok_or(Status::INTERNAL_ERROR)?;
        if end > self.output.len() {
            return Err(Status::BUFFER_TOO_SMALL);
        }
        self.output[self.len..end].copy_from_slice(bytes);
        self.len = end;
        Ok(())
    }

    fn u16(&mut self, value: u16) -> Result<(), Status> {
        let mut digits = [0u8; 5];
        let mut value = value;
        let mut start = digits.len();
        loop {
            start -= 1;
            digits[start] = b'0' + u8::try_from(value % 10).map_err(|_| Status::INTERNAL_ERROR)?;
            value /= 10;
            if value == 0 {
                break;
            }
        }
        self.bytes(&digits[start..])
    }
}

#[cfg(test)]
mod tests {
    use super::{eval, find, request};
    use exactscope_kernel::Status;

    fn call_eval(input: &[u8]) -> (Status, std::string::String) {
        let mut output = [0u8; 512];
        let result = eval(input, &mut output);
        let len = usize::try_from(result.written_or_required).unwrap();
        (
            result.status,
            std::string::String::from(core::str::from_utf8(&output[..len]).unwrap()),
        )
    }

    fn call_find(input: &[u8]) -> (Status, std::string::String) {
        let mut output = [0u8; 512];
        let result = find(input, &mut output);
        let len = usize::try_from(result.written_or_required).unwrap();
        (
            result.status,
            std::string::String::from(core::str::from_utf8(&output[..len]).unwrap()),
        )
    }

    fn call_request(input: &[u8]) -> (Status, std::string::String) {
        let mut output = [0u8; 512];
        let result = request(input, &mut output);
        let len = usize::try_from(result.written_or_required).unwrap();
        (
            result.status,
            std::string::String::from(core::str::from_utf8(&output[..len]).unwrap()),
        )
    }

    #[test]
    fn request_dispatches_eval_and_find() {
        let eval_input = br#"{"op":"econ.ped.mid","a":["10000","12000","100","80"]}"#;
        assert_eq!(call_request(eval_input), call_eval(eval_input));

        let find_input = br#"{"q":"midpoint price elasticity","n":3}"#;
        assert_eq!(call_request(find_input), call_find(find_input));
    }

    #[test]
    fn request_rejects_unknown_shape_and_preserves_size_limit() {
        let (status, response) = call_request(br#"{"x":"unknown"}"#);
        assert_eq!(status, Status::INVALID_REQUEST);
        assert_eq!(response, r#"{"s":1,"e":"INVALID_REQUEST"}"#);

        let oversized = [b'x'; 513];
        let (status, response) = call_request(&oversized);
        assert_eq!(status, Status::RESOURCE_LIMIT);
        assert_eq!(response, r#"{"s":20,"e":"RESOURCE_LIMIT"}"#);
    }

    #[test]
    fn eval_golden_request_is_exact() {
        let (status, response) =
            call_eval(br#"{"op":"econ.ped.mid","a":["10000","12000","100","80"]}"#);
        assert_eq!(status, Status::OK);
        assert_eq!(
            response,
            r#"{"s":0,"v":"-1.222222","c":"elastic","p":"econ-undergrad@0.1.0","r":1}"#
        );
    }

    #[test]
    fn eval_executes_non_ped_economics_operation() {
        let (status, response) = call_eval(br#"{"op":"econ.gdp.deflator100","a":["120","100"]}"#);
        assert_eq!(status, Status::OK);
        assert_eq!(
            response,
            r#"{"s":0,"v":"120","p":"econ-undergrad@0.1.0","r":1}"#
        );
    }

    #[test]
    fn eval_executes_statistics_vectors_and_multi_output_regression() {
        let (status, response) = call_eval(br#"{"op":"stats.mean","a":[["1","2","3"]]}"#);
        assert_eq!(status, Status::OK);
        assert_eq!(
            response,
            r#"{"s":0,"v":"2","p":"statistics-core@0.1.0","r":1}"#
        );

        let (status, response) =
            call_eval(br#"{"op":"stats.corr.pearson","a":[["1","2","3"],["1","2","4"]]}"#);
        assert_eq!(status, Status::OK);
        assert!(response.contains("\"v\":\"0.981981\""));

        let (status, response) =
            call_eval(br#"{"op":"stats.regression.linear","a":[["1","2","3"],["3","5","7"]]}"#);
        assert_eq!(status, Status::OK);
        assert_eq!(
            response,
            r#"{"s":0,"v":["2","1"],"names":["slope","intercept"],"p":"statistics-core@0.1.0","r":1}"#
        );
    }

    #[test]
    fn eval_statistics_shape_and_domain_failures_remain_typed() {
        let (status, response) = call_eval(br#"{"op":"stats.mean","a":["1"]}"#);
        assert_eq!(status, Status::ARGUMENT_TYPE);
        assert_eq!(response, r#"{"s":6,"e":"ARGUMENT_TYPE","i":0}"#);

        let (status, response) =
            call_eval(br#"{"op":"econ.gdp.deflator100","a":[["120"],["100"]]}"#);
        assert_eq!(status, Status::ARGUMENT_TYPE);
        assert_eq!(response, r#"{"s":6,"e":"ARGUMENT_TYPE","i":0}"#);

        let (status, response) = call_eval(br#"{"op":"stats.mean","a":[[]]}"#);
        assert_eq!(status, Status::INSUFFICIENT_DATA);
        assert_eq!(response, r#"{"s":16,"e":"INSUFFICIENT_DATA"}"#);

        let (status, response) = call_eval(br#"{"op":"stats.mean","a":[["1","bad","3"]]}"#);
        assert_eq!(status, Status::INVALID_DECIMAL);
        assert_eq!(response, r#"{"s":9,"e":"INVALID_DECIMAL","i":0}"#);
    }

    #[test]
    fn eval_accepts_field_order_and_json_whitespace() {
        let (status, response) = call_eval(
            b" { \"a\" : [ \"10\", \"20\", \"20\", \"10\" ], \"op\" : \"econ.ped.mid\" } ",
        );
        assert_eq!(status, Status::OK);
        assert!(response.contains("\"v\":\"-1\""));
        assert!(response.contains("\"c\":\"unit_elastic\""));
    }

    #[test]
    fn eval_preserves_core_failures() {
        let (status, response) = call_eval(br#"{"op":"econ.ped.mid","a":["10","10","100","80"]}"#);
        assert_eq!(status, Status::DIVIDE_BY_ZERO);
        assert_eq!(response, r#"{"s":13,"e":"DIVIDE_BY_ZERO"}"#);

        let (status, response) = call_eval(br#"{"op":"econ.ped.mid","a":["-1","10","100","80"]}"#);
        assert_eq!(status, Status::CONSTRAINT_VIOLATION);
        assert_eq!(
            response,
            r#"{"s":11,"e":"CONSTRAINT_VIOLATION","i":0,"d":1}"#
        );
    }

    #[test]
    fn eval_checks_count_before_decimal_lexing() {
        let (status, response) = call_eval(br#"{"op":"econ.ped.mid","a":["not-a-number"]}"#);
        assert_eq!(status, Status::ARGUMENT_COUNT);
        assert_eq!(response, r#"{"s":5,"e":"ARGUMENT_COUNT"}"#);
    }

    #[test]
    fn eval_rejects_coercion_and_unknown_fields() {
        for request in [
            br#"{"op":"econ.ped.mid","a":[10000,"12000","100","80"]}"#.as_slice(),
            br#"{"op":"econ.ped.mid","a":["10000","12000","100","80"],"x":1}"#,
            br#"{"op":"econ.ped.mid","op":"econ.ped.mid","a":[]}"#,
            br#"{"op":"econ.ped.mid","a":["10000","5%","100","80"]}"#,
        ] {
            let (status, response) = call_eval(request);
            assert!(!status.is_ok(), "{request:?}");
            assert!(!response.contains("\"v\":"), "{request:?}");
        }
    }

    #[test]
    fn eval_vector_parser_bounds_and_malformed_inputs_fail_closed() {
        let sixty_four = std::format!(
            r#"{{"op":"stats.sum","a":[[{}]]}}"#,
            std::vec![r#""0""#; 64].join(",")
        );
        let (status, response) = call_eval(sixty_four.as_bytes());
        assert_eq!(status, Status::OK);
        assert_eq!(
            response,
            r#"{"s":0,"v":"0","p":"statistics-core@0.1.0","r":1}"#
        );

        let sixty_five = std::format!(
            r#"{{"op":"stats.sum","a":[[{}]]}}"#,
            std::vec![r#""0""#; 65].join(",")
        );
        assert_eq!(call_eval(sixty_five.as_bytes()).0, Status::RESOURCE_LIMIT);

        let thirteen_arguments = std::format!(
            r#"{{"op":"stats.sum","a":[{}]}}"#,
            std::vec![r#""0""#; 13].join(",")
        );
        assert_eq!(
            call_eval(thirteen_arguments.as_bytes()).0,
            Status::RESOURCE_LIMIT
        );

        let overlong_decimal =
            std::format!(r#"{{"op":"stats.mean","a":[["{}"]]}}"#, "1".repeat(97));
        assert_eq!(
            call_eval(overlong_decimal.as_bytes()).0,
            Status::RESOURCE_LIMIT
        );

        for malformed in [
            br#"{"op":"stats.mean","a":[[["1"]]]}"#.as_slice(),
            br#"{"op":"stats.mean","a":[[1]]}"#,
            br#"{"op":"stats.mean","a":[{}]}"#,
            br#"{"op":"stats.mean","a":[["1",]]}"#,
            br#"{"op":"stats.mean","a":[["1"]],}"#,
            br#"{"op":"stats.mean","a":[["1]]}"#,
            br#"{"op":"stats.mean","a":[["1"]],"a":[["1"]]}"#,
            br#"{"op":"stats.mean","a":[["1"]],"unknown":[]}"#,
            br#"{"op":"stats.mean","a":[["\u0031"]]}"#,
        ] {
            let (status, response) = call_eval(malformed);
            assert_eq!(status, Status::INVALID_REQUEST, "{malformed:?}");
            assert!(!response.contains("\"v\":"), "{malformed:?}");
        }

        for invalid_decimal in [
            br#"{"op":"stats.mean","a":[["NaN"]]}"#.as_slice(),
            br#"{"op":"stats.mean","a":[["Infinity"]]}"#,
        ] {
            assert_eq!(call_eval(invalid_decimal).0, Status::INVALID_DECIMAL);
        }

        let (status, response) =
            call_eval(br#"{"op":"stats.mean.weighted","a":[["1","2"],["1"]]}"#);
        assert_eq!(status, Status::ARGUMENT_TYPE);
        assert!(!response.contains("\"v\":"));

        let exponent_extreme =
            call_eval(br#"{"op":"stats.mean","a":[["1e999999999999999999999"]]}"#);
        assert!(matches!(
            exponent_extreme.0,
            Status::INVALID_DECIMAL | Status::OVERFLOW | Status::RESOURCE_LIMIT
        ));

        let invalid_utf8 = [
            b'{', b'"', b'o', b'p', b'"', b':', b'"', 0xff, b'"', b',', b'"', b'a', b'"', b':',
            b'[', b']', b'}',
        ];
        assert_eq!(call_eval(&invalid_utf8).0, Status::INVALID_REQUEST);
    }

    #[test]
    fn find_returns_compact_signature() {
        let (status, response) = call_find(br#"{"q":"midpoint price elasticity","n":3}"#);
        assert_eq!(status, Status::OK);
        assert_eq!(
            response,
            r#"{"s":0,"m":[{"op":"econ.ped.mid","sig":"econ.ped.mid(p1,p2,q1,q2)","method":"midpoint"}]}"#
        );
    }

    #[test]
    fn find_discovers_multiple_economics_methods() {
        let (status, response) = call_find(br#"{"q":"gdp deflator","n":3}"#);
        assert_eq!(status, Status::OK);
        assert_eq!(
            response,
            r#"{"s":0,"m":[{"op":"econ.gdp.deflator100","sig":"econ.gdp.deflator100(nominal_gdp,real_gdp)","method":"deflator100"}]}"#
        );

        let (status, response) = call_find(br#"{"q":"real interest rate","n":5}"#);
        assert_eq!(status, Status::OK);
        assert!(response.contains("\"op\":\"econ.rate.real.exact_pct\""));
        assert!(response.contains("\"op\":\"econ.rate.real.approx_pct\""));
    }

    #[test]
    fn find_discovers_statistics_operations_after_economics_miss() {
        let (status, response) = call_find(br#"{"q":"sample variance","n":3}"#);
        assert_eq!(status, Status::OK);
        assert_eq!(
            response,
            r#"{"s":0,"m":[{"op":"stats.var.sample","sig":"stats.var.sample(values)","method":"two_pass_sample"}]}"#
        );

        let (status, response) = call_find(br#"{"q":"pearson correlation","n":3}"#);
        assert_eq!(status, Status::OK);
        assert!(response.contains("\"op\":\"stats.corr.pearson\""));
    }

    #[test]
    fn find_refuses_method_ambiguity() {
        let (status, response) = call_find(br#"{"q":"price elasticity","n":5}"#);
        assert_eq!(status, Status::AMBIGUOUS_METHOD);
        assert_eq!(
            response,
            r#"{"s":7,"e":"AMBIGUOUS_METHOD","need":["method"]}"#
        );
    }

    #[test]
    fn too_small_output_writes_nothing_and_reports_capacity() {
        let mut output = [0xa5u8; 8];
        let result = eval(
            br#"{"op":"econ.ped.mid","a":["10000","12000","100","80"]}"#,
            &mut output,
        );
        assert_eq!(result.status, Status::BUFFER_TOO_SMALL);
        assert!(result.written_or_required > u32::try_from(output.len()).unwrap());
        assert_eq!(output, [0xa5; 8]);
    }
}
