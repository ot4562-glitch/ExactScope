//! Canonical base-10 scalar representation.

use crate::Status;

/// Maximum decoded decimal text length in the baseline profile.
pub const MAX_DECIMAL_TEXT_BYTES: usize = 96;
/// Minimum canonical decimal exponent.
pub const MIN_DECIMAL_EXPONENT: i8 = -18;
/// Maximum canonical decimal exponent.
pub const MAX_DECIMAL_EXPONENT: i8 = 18;

/// Exact base-10 value represented as `coefficient * 10^exponent`.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Decimal64 {
    coefficient: i64,
    exponent: i8,
}

impl Decimal64 {
    /// Canonical zero.
    pub const ZERO: Self = Self {
        coefficient: 0,
        exponent: 0,
    };

    /// Constructs and canonicalizes a decimal value.
    ///
    /// # Errors
    ///
    /// Returns [`Status::OVERFLOW`] when the exponent is outside the v1 profile.
    pub fn from_parts(coefficient: i64, exponent: i8) -> Result<Self, Status> {
        if !(MIN_DECIMAL_EXPONENT..=MAX_DECIMAL_EXPONENT).contains(&exponent) {
            return Err(Status::OVERFLOW);
        }
        if coefficient == 0 {
            return Ok(Self::ZERO);
        }

        let mut coefficient = coefficient;
        let mut exponent = exponent;
        while coefficient % 10 == 0 && exponent < MAX_DECIMAL_EXPONENT {
            coefficient /= 10;
            exponent += 1;
        }
        Ok(Self {
            coefficient,
            exponent,
        })
    }

    /// Parses the strict AI-facing ASCII decimal grammar.
    ///
    /// # Errors
    ///
    /// Returns a stable `ExactScope` status for malformed, oversized, or
    /// unrepresentable input.
    #[allow(clippy::too_many_lines)]
    pub fn parse_ascii(bytes: &[u8]) -> Result<Self, Status> {
        if bytes.len() > MAX_DECIMAL_TEXT_BYTES {
            return Err(Status::RESOURCE_LIMIT);
        }
        if bytes.is_empty() {
            return Err(Status::INVALID_DECIMAL);
        }

        let mut index = 0usize;
        let negative = bytes[index] == b'-';
        if negative {
            index += 1;
            if index == bytes.len() {
                return Err(Status::INVALID_DECIMAL);
            }
        }

        let integer_start = index;
        match bytes.get(index).copied() {
            Some(b'0') => {
                index += 1;
                if bytes.get(index).is_some_and(u8::is_ascii_digit) {
                    return Err(Status::INVALID_DECIMAL);
                }
            }
            Some(b'1'..=b'9') => {
                index += 1;
                while bytes.get(index).is_some_and(u8::is_ascii_digit) {
                    index += 1;
                }
            }
            _ => return Err(Status::INVALID_DECIMAL),
        }
        let integer_end = index;

        let mut fraction_start = index;
        let mut fraction_end = index;
        if bytes.get(index) == Some(&b'.') {
            index += 1;
            fraction_start = index;
            if !bytes.get(index).is_some_and(u8::is_ascii_digit) {
                return Err(Status::INVALID_DECIMAL);
            }
            while bytes.get(index).is_some_and(u8::is_ascii_digit) {
                index += 1;
            }
            fraction_end = index;
        }

        let fractional_digits = fraction_end.saturating_sub(fraction_start);
        let mut explicit_exponent = 0i64;
        if matches!(bytes.get(index), Some(b'e' | b'E')) {
            index += 1;
            let exponent_negative = match bytes.get(index) {
                Some(b'+') => {
                    index += 1;
                    false
                }
                Some(b'-') => {
                    index += 1;
                    true
                }
                _ => false,
            };
            let exponent_start = index;
            while bytes.get(index).is_some_and(u8::is_ascii_digit) {
                index += 1;
                if index - exponent_start > 10 {
                    return Err(Status::OVERFLOW);
                }
            }
            if index == exponent_start {
                return Err(Status::INVALID_DECIMAL);
            }

            for &digit in &bytes[exponent_start..index] {
                explicit_exponent = explicit_exponent
                    .checked_mul(10)
                    .and_then(|value| value.checked_add(i64::from(digit - b'0')))
                    .ok_or(Status::OVERFLOW)?;
            }
            if exponent_negative {
                explicit_exponent = explicit_exponent.checked_neg().ok_or(Status::OVERFLOW)?;
            }
        }

        if index != bytes.len() {
            return Err(Status::INVALID_DECIMAL);
        }

        let mut trailing_zeros = 0usize;
        let mut seen_nonzero = false;
        for &digit in bytes[integer_start..integer_end]
            .iter()
            .chain(bytes[fraction_start..fraction_end].iter())
            .rev()
        {
            if digit == b'0' && !seen_nonzero {
                trailing_zeros += 1;
            } else {
                seen_nonzero = true;
                break;
            }
        }

        if !seen_nonzero {
            return Ok(Self::ZERO);
        }

        let kept_digits = (integer_end - integer_start + fractional_digits)
            .checked_sub(trailing_zeros)
            .ok_or(Status::INTERNAL_ERROR)?;
        let mut magnitude = 0u128;
        for (consumed, &digit) in bytes[integer_start..integer_end]
            .iter()
            .chain(bytes[fraction_start..fraction_end].iter())
            .enumerate()
        {
            if consumed == kept_digits {
                break;
            }
            magnitude = magnitude
                .checked_mul(10)
                .and_then(|value| value.checked_add(u128::from(digit - b'0')))
                .ok_or(Status::OVERFLOW)?;
        }

        let positive_limit = u128::from(i64::MAX.unsigned_abs());
        let negative_limit = positive_limit + 1;
        let coefficient = if negative {
            if magnitude > negative_limit {
                return Err(Status::OVERFLOW);
            }
            if magnitude == negative_limit {
                i64::MIN
            } else {
                i64::try_from(magnitude)
                    .map_err(|_| Status::OVERFLOW)?
                    .checked_neg()
                    .ok_or(Status::OVERFLOW)?
            }
        } else {
            i64::try_from(magnitude).map_err(|_| Status::OVERFLOW)?
        };

        let fractional_digits = i64::try_from(fractional_digits).map_err(|_| Status::OVERFLOW)?;
        let trailing_zeros = i64::try_from(trailing_zeros).map_err(|_| Status::OVERFLOW)?;
        let exponent = explicit_exponent
            .checked_sub(fractional_digits)
            .and_then(|value| value.checked_add(trailing_zeros))
            .ok_or(Status::OVERFLOW)?;
        let exponent = i8::try_from(exponent).map_err(|_| Status::OVERFLOW)?;
        Self::from_parts(coefficient, exponent)
    }

    /// Returns the signed coefficient.
    #[must_use]
    pub const fn coefficient(self) -> i64 {
        self.coefficient
    }

    /// Returns the base-10 exponent.
    #[must_use]
    pub const fn exponent(self) -> i8 {
        self.exponent
    }

    /// Returns whether this value is exactly zero.
    #[must_use]
    pub const fn is_zero(self) -> bool {
        self.coefficient == 0
    }

    /// Returns whether the stored representation is canonical.
    #[must_use]
    pub fn is_canonical(self) -> bool {
        Self::from_parts(self.coefficient, self.exponent) == Ok(self)
    }

    /// Returns the number of bytes needed by canonical plain-decimal output.
    ///
    /// # Errors
    ///
    /// Returns [`Status::OVERFLOW`] only if an internal length calculation
    /// exceeds the platform `usize` range.
    pub fn format_len(self) -> Result<usize, Status> {
        let digits = digit_count(self.coefficient.unsigned_abs());
        let sign = usize::from(self.coefficient < 0);
        if self.exponent >= 0 {
            let zeros = usize::try_from(self.exponent).map_err(|_| Status::OVERFLOW)?;
            return sign
                .checked_add(digits)
                .and_then(|value| value.checked_add(zeros))
                .ok_or(Status::OVERFLOW);
        }

        let fractional = usize::from(self.exponent.unsigned_abs());
        if fractional < digits {
            sign.checked_add(digits)
                .and_then(|value| value.checked_add(1))
                .ok_or(Status::OVERFLOW)
        } else {
            sign.checked_add(2)
                .and_then(|value| value.checked_add(fractional - digits))
                .and_then(|value| value.checked_add(digits))
                .ok_or(Status::OVERFLOW)
        }
    }

    /// Writes the canonical plain-decimal form into `output`.
    ///
    /// # Errors
    ///
    /// Returns [`Status::BUFFER_TOO_SMALL`] if `output` cannot contain the
    /// complete value.
    pub fn write_canonical(self, output: &mut [u8]) -> Result<usize, Status> {
        let required = self.format_len()?;
        if output.len() < required {
            return Err(Status::BUFFER_TOO_SMALL);
        }

        let mut digits = [0u8; 20];
        let digits_len = write_digits(self.coefficient.unsigned_abs(), &mut digits);
        let mut cursor = 0usize;
        if self.coefficient < 0 {
            output[cursor] = b'-';
            cursor += 1;
        }

        if self.exponent >= 0 {
            output[cursor..cursor + digits_len].copy_from_slice(&digits[..digits_len]);
            cursor += digits_len;
            let zeros = usize::try_from(self.exponent).map_err(|_| Status::OVERFLOW)?;
            output[cursor..cursor + zeros].fill(b'0');
            cursor += zeros;
            return Ok(cursor);
        }

        let fractional = usize::from(self.exponent.unsigned_abs());
        if fractional < digits_len {
            let integer_len = digits_len - fractional;
            output[cursor..cursor + integer_len].copy_from_slice(&digits[..integer_len]);
            cursor += integer_len;
            output[cursor] = b'.';
            cursor += 1;
            output[cursor..cursor + fractional].copy_from_slice(&digits[integer_len..digits_len]);
            cursor += fractional;
        } else {
            output[cursor] = b'0';
            output[cursor + 1] = b'.';
            cursor += 2;
            let leading_zeros = fractional - digits_len;
            output[cursor..cursor + leading_zeros].fill(b'0');
            cursor += leading_zeros;
            output[cursor..cursor + digits_len].copy_from_slice(&digits[..digits_len]);
            cursor += digits_len;
        }
        Ok(cursor)
    }
}

fn digit_count(mut value: u64) -> usize {
    if value == 0 {
        return 1;
    }
    let mut count = 0usize;
    while value != 0 {
        value /= 10;
        count += 1;
    }
    count
}

fn write_digits(mut value: u64, output: &mut [u8; 20]) -> usize {
    if value == 0 {
        output[0] = b'0';
        return 1;
    }
    let count = digit_count(value);
    let mut index = count;
    while value != 0 {
        index -= 1;
        output[index] = b'0' + u8::try_from(value % 10).unwrap_or(0);
        value /= 10;
    }
    count
}

#[cfg(test)]
mod tests {
    use super::Decimal64;
    use crate::Status;

    fn rendered(value: Decimal64) -> std::string::String {
        let mut output = [0u8; 64];
        let written = value.write_canonical(&mut output).expect("format");
        std::string::String::from(core::str::from_utf8(&output[..written]).expect("ascii"))
    }

    #[test]
    fn parses_and_canonicalizes_examples() {
        let cases = [
            ("0", Decimal64::ZERO, "0"),
            ("-0.0", Decimal64::ZERO, "0"),
            ("-12", Decimal64::from_parts(-12, 0).unwrap(), "-12"),
            ("12.50", Decimal64::from_parts(125, -1).unwrap(), "12.5"),
            ("0.05", Decimal64::from_parts(5, -2).unwrap(), "0.05"),
            ("1000000", Decimal64::from_parts(1, 6).unwrap(), "1000000"),
            ("1e-6", Decimal64::from_parts(1, -6).unwrap(), "0.000001"),
            ("1.2300E+2", Decimal64::from_parts(123, 0).unwrap(), "123"),
        ];
        for (text, expected, expected_text) in cases {
            let parsed = Decimal64::parse_ascii(text.as_bytes()).expect(text);
            assert_eq!(parsed, expected, "{text}");
            assert_eq!(rendered(parsed), expected_text, "{text}");
            assert!(parsed.is_canonical());
        }
    }

    #[test]
    fn rejects_invalid_lexical_forms() {
        for text in [
            "", "+1", "01", "1.", ".1", "1e", "1 2", "1,000", "5%", "NaN", "Infinity",
        ] {
            assert_eq!(
                Decimal64::parse_ascii(text.as_bytes()),
                Err(Status::INVALID_DECIMAL),
                "{text}"
            );
        }
    }

    #[test]
    fn distinguishes_resource_limit_and_overflow() {
        assert_eq!(
            Decimal64::parse_ascii(&[b'1'; 97]),
            Err(Status::RESOURCE_LIMIT)
        );
        assert_eq!(
            Decimal64::parse_ascii(b"9223372036854775808"),
            Err(Status::OVERFLOW)
        );
        assert_eq!(Decimal64::parse_ascii(b"1e19"), Err(Status::OVERFLOW));
    }

    #[test]
    fn accepts_i64_minimum_and_trailing_zero_compression() {
        let minimum = Decimal64::parse_ascii(b"-9223372036854775808").unwrap();
        assert_eq!(minimum.coefficient(), i64::MIN);
        assert_eq!(minimum.exponent(), 0);
        assert_eq!(rendered(minimum), "-9223372036854775808");

        let compressed = Decimal64::parse_ascii(b"92233720368547758070").unwrap();
        assert_eq!(compressed, Decimal64::from_parts(i64::MAX, 1).unwrap());
    }

    #[test]
    fn format_reports_required_capacity() {
        let value = Decimal64::parse_ascii(b"0.000001").unwrap();
        let mut short = [0u8; 7];
        assert_eq!(
            value.write_canonical(&mut short),
            Err(Status::BUFFER_TOO_SMALL)
        );
        assert_eq!(value.format_len(), Ok(8));
    }
}
