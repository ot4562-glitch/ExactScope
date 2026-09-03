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
    classification_key, evaluate_operation, Decimal64, EvaluationResult, ScalarValue, Status,
    ARGUMENT_INDEX_NONE,
};
use exactscope_pack::{empty_matches, FusedRegistry, Match};

/// Hard v0.1 request-size cap.
pub const MAX_TINY_JSON_REQUEST_BYTES: usize = 512;
/// Hard v0.1 scalar argument cap.
pub const MAX_TINY_JSON_ARGUMENTS: usize = 12;
/// Internal bounded response staging capacity for the first slice.
pub const MAX_TINY_JSON_RESPONSE_BYTES: usize = 512;

const EMPTY_SCALAR: ScalarValue = ScalarValue::new(Decimal64::ZERO, 0, 0);

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
        Ok(request) => evaluate_request(input, request),
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
        Ok(request) => evaluate_request(input, request),
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
    arguments: [ByteSpan; MAX_TINY_JSON_ARGUMENTS],
    argument_count: usize,
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
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct EvalSuccess {
    result: EvaluationResult,
    provenance: &'static str,
    classification: Option<&'static str>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct FindSuccess {
    matches: [Match; exactscope_pack::MAX_FIND_MATCHES],
    count: usize,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Response {
    Error(ErrorResponse),
    EvalSuccess(EvalSuccess),
    FindSuccess(FindSuccess),
}

fn evaluate_request(input: &[u8], request: EvalRequest) -> Response {
    let registry = FusedRegistry::new();
    let operation = match registry.lookup(request.operation.resolve(input)) {
        Ok(operation) => operation,
        Err(status) => return Response::Error(ErrorResponse::new(status)),
    };

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
    for (index, span) in request.arguments[..request.argument_count]
        .iter()
        .enumerate()
    {
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
    })
}

fn find_request(input: &[u8], request: FindRequest) -> Response {
    let registry = FusedRegistry::new();
    let mut matches = empty_matches();
    match registry.find(request.query.resolve(input), &mut matches[..request.limit]) {
        Ok(count) => Response::FindSuccess(FindSuccess { matches, count }),
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
    let mut arguments = [ByteSpan::EMPTY; MAX_TINY_JSON_ARGUMENTS];
    let mut argument_count = 0usize;
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
                argument_count = parser.parse_string_array(&mut arguments)?;
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
        argument_count,
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

    fn parse_string_array(
        &mut self,
        output: &mut [ByteSpan; MAX_TINY_JSON_ARGUMENTS],
    ) -> Result<usize, Status> {
        self.expect_byte(b'[')?;
        self.skip_whitespace();
        if self.consume_byte(b']') {
            return Ok(0);
        }

        let mut count = 0usize;
        loop {
            if count == output.len() {
                return Err(Status::RESOURCE_LIMIT);
            }
            output[count] = self.parse_plain_string()?;
            count += 1;
            self.skip_whitespace();
            if self.consume_byte(b',') {
                continue;
            }
            self.expect_byte(b']')?;
            return Ok(count);
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
    if result.value_count != 1 {
        return Err(Status::INTERNAL_ERROR);
    }
    writer.bytes(b"{\"s\":0,\"v\":\"")?;
    let mut decimal = [0u8; 64];
    let decimal_len = result.values[0].decimal.write_canonical(&mut decimal)?;
    writer.bytes(&decimal[..decimal_len])?;
    writer.byte(b'"')?;
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

fn write_find_success(writer: &mut Writer<'_>, success: &FindSuccess) -> Result<(), Status> {
    writer.bytes(b"{\"s\":0,\"m\":[")?;
    for index in 0..success.count {
        if index != 0 {
            writer.byte(b',')?;
        }
        let operation = success.matches[index].operation.operation;
        writer.bytes(b"{\"op\":\"")?;
        writer.bytes(operation.key.as_bytes())?;
        writer.bytes(b"\",\"sig\":\"")?;
        writer.bytes(operation.signature.as_bytes())?;
        writer.bytes(b"\",\"method\":\"")?;
        writer.bytes(operation.method.as_bytes())?;
        writer.bytes(b"\"}")?;
    }
    writer.bytes(b"]}")
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
    fn find_returns_compact_signature() {
        let (status, response) = call_find(br#"{"q":"midpoint price elasticity","n":3}"#);
        assert_eq!(status, Status::OK);
        assert_eq!(
            response,
            r#"{"s":0,"m":[{"op":"econ.ped.mid","sig":"econ.ped.mid(p1,p2,q1,q2)","method":"midpoint"}]}"#
        );
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
