//! Checked exact rational work values.

use core::cmp::Ordering;

use crate::{Decimal64, RoundingMode, Status};

/// Result of explicit rational-to-decimal quantization.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RoundedDecimal {
    /// Canonical output value.
    pub value: Decimal64,
    /// Whether discarded remainder changed the exact rational value.
    pub rounded: bool,
}

/// Bounded exact rational used inside the deterministic formula VM.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct WorkRational {
    numerator: i128,
    denominator: i128,
}

impl WorkRational {
    /// Exact zero.
    pub const ZERO: Self = Self {
        numerator: 0,
        denominator: 1,
    };
    /// Exact one.
    pub const ONE: Self = Self {
        numerator: 1,
        denominator: 1,
    };

    /// Constructs an exact integer constant for static operation tables.
    #[must_use]
    pub const fn from_integer(value: i64) -> Self {
        Self {
            numerator: value as i128,
            denominator: 1,
        }
    }

    /// Constructs a normalized exact rational.
    ///
    /// # Errors
    ///
    /// Returns a typed status for zero denominator or bounded overflow.
    pub fn new(numerator: i128, denominator: i128) -> Result<Self, Status> {
        if denominator == 0 {
            return Err(Status::DIVIDE_BY_ZERO);
        }
        if numerator == 0 {
            return Ok(Self::ZERO);
        }

        let (numerator, denominator) = if denominator < 0 {
            (
                numerator.checked_neg().ok_or(Status::OVERFLOW)?,
                denominator.checked_neg().ok_or(Status::OVERFLOW)?,
            )
        } else {
            (numerator, denominator)
        };

        let gcd = gcd_u128(numerator.unsigned_abs(), denominator as u128);
        let divisor = i128::try_from(gcd).map_err(|_| Status::OVERFLOW)?;
        Ok(Self {
            numerator: numerator / divisor,
            denominator: denominator / divisor,
        })
    }

    /// Converts a canonical decimal to an exact rational.
    ///
    /// # Errors
    ///
    /// Returns [`Status::OVERFLOW`] when scaling exceeds the bounded work type.
    pub fn from_decimal(value: Decimal64) -> Result<Self, Status> {
        if !value.is_canonical() {
            return Err(Status::INVALID_DECIMAL);
        }
        let coefficient = i128::from(value.coefficient());
        let exponent = value.exponent();
        if exponent >= 0 {
            let factor = pow10_i128(exponent as u8)?;
            Self::new(
                coefficient.checked_mul(factor).ok_or(Status::OVERFLOW)?,
                1,
            )
        } else {
            let denominator = pow10_i128(exponent.unsigned_abs())?;
            Self::new(coefficient, denominator)
        }
    }

    /// Returns the normalized numerator.
    #[must_use]
    pub const fn numerator(self) -> i128 {
        self.numerator
    }

    /// Returns the strictly positive denominator.
    #[must_use]
    pub const fn denominator(self) -> i128 {
        self.denominator
    }

    /// Returns true for exact zero.
    #[must_use]
    pub const fn is_zero(self) -> bool {
        self.numerator == 0
    }

    /// Checked exact addition.
    ///
    /// # Errors
    ///
    /// Returns [`Status::OVERFLOW`] if a bounded intermediate cannot be represented.
    pub fn checked_add(self, rhs: Self) -> Result<Self, Status> {
        let gcd = gcd_u128(self.denominator as u128, rhs.denominator as u128);
        let gcd = i128::try_from(gcd).map_err(|_| Status::OVERFLOW)?;
        let left_scale = rhs.denominator / gcd;
        let right_scale = self.denominator / gcd;
        let left = self
            .numerator
            .checked_mul(left_scale)
            .ok_or(Status::OVERFLOW)?;
        let right = rhs
            .numerator
            .checked_mul(right_scale)
            .ok_or(Status::OVERFLOW)?;
        let numerator = left.checked_add(right).ok_or(Status::OVERFLOW)?;
        let denominator = self
            .denominator
            .checked_mul(left_scale)
            .ok_or(Status::OVERFLOW)?;
        Self::new(numerator, denominator)
    }

    /// Checked exact subtraction.
    ///
    /// # Errors
    ///
    /// Returns [`Status::OVERFLOW`] if negation or addition overflows.
    pub fn checked_sub(self, rhs: Self) -> Result<Self, Status> {
        self.checked_add(rhs.checked_neg()?)
    }

    /// Checked exact multiplication with cross reduction.
    ///
    /// # Errors
    ///
    /// Returns [`Status::OVERFLOW`] for bounded overflow.
    pub fn checked_mul(self, rhs: Self) -> Result<Self, Status> {
        if self.is_zero() || rhs.is_zero() {
            return Ok(Self::ZERO);
        }

        let gcd_left = gcd_u128(self.numerator.unsigned_abs(), rhs.denominator as u128);
        let gcd_right = gcd_u128(rhs.numerator.unsigned_abs(), self.denominator as u128);
        let gcd_left = i128::try_from(gcd_left).map_err(|_| Status::OVERFLOW)?;
        let gcd_right = i128::try_from(gcd_right).map_err(|_| Status::OVERFLOW)?;

        let left_num = self.numerator / gcd_left;
        let right_den = rhs.denominator / gcd_left;
        let right_num = rhs.numerator / gcd_right;
        let left_den = self.denominator / gcd_right;

        Self::new(
            left_num.checked_mul(right_num).ok_or(Status::OVERFLOW)?,
            left_den.checked_mul(right_den).ok_or(Status::OVERFLOW)?,
        )
    }

    /// Checked exact division with cross reduction.
    ///
    /// # Errors
    ///
    /// Returns [`Status::DIVIDE_BY_ZERO`] for a zero divisor and
    /// [`Status::OVERFLOW`] for bounded overflow.
    pub fn checked_div(self, rhs: Self) -> Result<Self, Status> {
        if rhs.is_zero() {
            return Err(Status::DIVIDE_BY_ZERO);
        }
        if self.is_zero() {
            return Ok(Self::ZERO);
        }

        let divisor_negative = rhs.numerator < 0;
        let divisor_magnitude = rhs.numerator.unsigned_abs();
        let gcd_num = gcd_u128(self.numerator.unsigned_abs(), divisor_magnitude);
        let gcd_den = gcd_u128(rhs.denominator as u128, self.denominator as u128);
        let gcd_num_i = i128::try_from(gcd_num).map_err(|_| Status::OVERFLOW)?;
        let gcd_den_i = i128::try_from(gcd_den).map_err(|_| Status::OVERFLOW)?;

        let left_num = self.numerator / gcd_num_i;
        let right_num_abs = divisor_magnitude / gcd_num;
        let right_den = rhs.denominator / gcd_den_i;
        let left_den = self.denominator / gcd_den_i;

        let mut numerator = left_num.checked_mul(right_den).ok_or(Status::OVERFLOW)?;
        if divisor_negative {
            numerator = numerator.checked_neg().ok_or(Status::OVERFLOW)?;
        }
        let right_num = i128::try_from(right_num_abs).map_err(|_| Status::OVERFLOW)?;
        let denominator = left_den.checked_mul(right_num).ok_or(Status::OVERFLOW)?;
        Self::new(numerator, denominator)
    }

    /// Checked negation.
    ///
    /// # Errors
    ///
    /// Returns [`Status::OVERFLOW`] for `i128::MIN`.
    pub fn checked_neg(self) -> Result<Self, Status> {
        Self::new(
            self.numerator.checked_neg().ok_or(Status::OVERFLOW)?,
            self.denominator,
        )
    }

    /// Checked absolute value.
    ///
    /// # Errors
    ///
    /// Returns [`Status::OVERFLOW`] for `i128::MIN`.
    pub fn checked_abs(self) -> Result<Self, Status> {
        if self.numerator < 0 {
            self.checked_neg()
        } else {
            Ok(self)
        }
    }

    /// Exact comparison within the bounded work profile.
    ///
    /// # Errors
    ///
    /// Returns [`Status::OVERFLOW`] when cross multiplication exceeds `i128`.
    pub fn checked_cmp(self, rhs: Self) -> Result<Ordering, Status> {
        if self.numerator.is_negative() != rhs.numerator.is_negative() {
            return Ok(self.numerator.cmp(&rhs.numerator));
        }

        let gcd_left = gcd_u128(self.numerator.unsigned_abs(), rhs.denominator as u128);
        let gcd_right = gcd_u128(rhs.numerator.unsigned_abs(), self.denominator as u128);
        let gcd_left_i = i128::try_from(gcd_left).map_err(|_| Status::OVERFLOW)?;
        let gcd_right_i = i128::try_from(gcd_right).map_err(|_| Status::OVERFLOW)?;

        let left = (self.numerator / gcd_left_i)
            .checked_mul(rhs.denominator / gcd_left_i)
            .ok_or(Status::OVERFLOW)?;
        let right = (rhs.numerator / gcd_right_i)
            .checked_mul(self.denominator / gcd_right_i)
            .ok_or(Status::OVERFLOW)?;
        Ok(left.cmp(&right))
    }

    /// Quantizes the exact rational to a canonical decimal.
    ///
    /// # Errors
    ///
    /// Returns a stable status if the scale is unsupported or the rounded
    /// coefficient cannot be represented.
    pub fn round_to_decimal(
        self,
        scale: u8,
        mode: RoundingMode,
    ) -> Result<RoundedDecimal, Status> {
        if scale > 18 {
            return Err(Status::INVALID_REQUEST);
        }

        let factor = pow10_u128(scale)?;
        let magnitude = self.numerator.unsigned_abs();
        let scaled = magnitude.checked_mul(factor).ok_or(Status::OVERFLOW)?;
        let denominator = self.denominator as u128;
        let quotient = scaled / denominator;
        let remainder = scaled % denominator;
        let negative = self.numerator < 0;

        let increment = if remainder == 0 {
            false
        } else {
            match mode {
                RoundingMode::TowardZero => false,
                RoundingMode::Floor => negative,
                RoundingMode::Ceil => !negative,
                RoundingMode::HalfAway | RoundingMode::HalfEven => {
                    let half_order = remainder.cmp(&(denominator - remainder));
                    match half_order {
                        Ordering::Greater => true,
                        Ordering::Less => false,
                        Ordering::Equal => {
                            mode == RoundingMode::HalfAway || quotient % 2 == 1
                        }
                    }
                }
            }
        };

        let magnitude = if increment {
            quotient.checked_add(1).ok_or(Status::OVERFLOW)?
        } else {
            quotient
        };
        let positive_limit = i64::MAX as u128;
        let negative_limit = positive_limit + 1;
        let coefficient = if negative {
            if magnitude > negative_limit {
                return Err(Status::OVERFLOW);
            }
            if magnitude == negative_limit {
                i64::MIN
            } else {
                -(magnitude as i64)
            }
        } else {
            if magnitude > positive_limit {
                return Err(Status::OVERFLOW);
            }
            magnitude as i64
        };

        let exponent = i8::try_from(scale)
            .map_err(|_| Status::OVERFLOW)?
            .checked_neg()
            .ok_or(Status::OVERFLOW)?;
        Ok(RoundedDecimal {
            value: Decimal64::from_parts(coefficient, exponent)?,
            rounded: remainder != 0,
        })
    }
}

fn gcd_u128(mut left: u128, mut right: u128) -> u128 {
    while right != 0 {
        let remainder = left % right;
        left = right;
        right = remainder;
    }
    left
}

fn pow10_i128(exponent: u8) -> Result<i128, Status> {
    let value = pow10_u128(exponent)?;
    i128::try_from(value).map_err(|_| Status::OVERFLOW)
}

fn pow10_u128(exponent: u8) -> Result<u128, Status> {
    let mut value = 1u128;
    for _ in 0..exponent {
        value = value.checked_mul(10).ok_or(Status::OVERFLOW)?;
    }
    Ok(value)
}

#[cfg(test)]
mod tests {
    use super::WorkRational;
    use crate::{Decimal64, RoundingMode, Status};

    fn rational(numerator: i128, denominator: i128) -> WorkRational {
        WorkRational::new(numerator, denominator).unwrap()
    }

    #[test]
    fn decimal_conversion_is_exact() {
        assert_eq!(
            WorkRational::from_decimal(Decimal64::parse_ascii(b"12.5").unwrap()).unwrap(),
            rational(25, 2)
        );
        assert_eq!(
            WorkRational::from_decimal(Decimal64::parse_ascii(b"0.000001").unwrap()).unwrap(),
            rational(1, 1_000_000)
        );
    }

    #[test]
    fn arithmetic_reduces_exactly() {
        let one_half = rational(1, 2);
        let one_third = rational(1, 3);
        assert_eq!(one_half.checked_add(one_third).unwrap(), rational(5, 6));
        assert_eq!(one_half.checked_sub(one_third).unwrap(), rational(1, 6));
        assert_eq!(one_half.checked_mul(one_third).unwrap(), rational(1, 6));
        assert_eq!(one_half.checked_div(one_third).unwrap(), rational(3, 2));
        assert_eq!(one_half.checked_div(WorkRational::ZERO), Err(Status::DIVIDE_BY_ZERO));
    }

    #[test]
    fn half_even_and_directional_rounding_are_deterministic() {
        let positive_tie = rational(5, 2);
        let negative_tie = rational(-5, 2);
        assert_eq!(
            positive_tie
                .round_to_decimal(0, RoundingMode::HalfEven)
                .unwrap()
                .value,
            Decimal64::from_parts(2, 0).unwrap()
        );
        assert_eq!(
            positive_tie
                .round_to_decimal(0, RoundingMode::HalfAway)
                .unwrap()
                .value,
            Decimal64::from_parts(3, 0).unwrap()
        );
        assert_eq!(
            negative_tie
                .round_to_decimal(0, RoundingMode::Floor)
                .unwrap()
                .value,
            Decimal64::from_parts(-3, 0).unwrap()
        );
        assert_eq!(
            negative_tie
                .round_to_decimal(0, RoundingMode::Ceil)
                .unwrap()
                .value,
            Decimal64::from_parts(-2, 0).unwrap()
        );
    }

    #[test]
    fn rounded_flag_tracks_nonzero_remainder() {
        let exact = rational(1, 2)
            .round_to_decimal(1, RoundingMode::HalfEven)
            .unwrap();
        assert!(!exact.rounded);
        let rounded = rational(1, 3)
            .round_to_decimal(6, RoundingMode::HalfEven)
            .unwrap();
        assert!(rounded.rounded);
        assert_eq!(rounded.value, Decimal64::from_parts(333_333, -6).unwrap());
    }
}
