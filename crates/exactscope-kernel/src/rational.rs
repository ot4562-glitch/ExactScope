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

/// Result of deterministic rational square-root quantization.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SqrtDecimal {
    /// Canonical output value.
    pub value: Decimal64,
    /// Whether the exact mathematical root differs from the returned decimal.
    pub rounded: bool,
    /// Whether the mathematical root is irrational.
    pub inexact: bool,
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
    #[allow(clippy::cast_lossless)]
    pub const fn from_integer(value: i64) -> Self {
        // `From<i64> for i128` is not const on the declared MSRV; this widening cast is exact.
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

        let gcd = gcd_u128(
            numerator.unsigned_abs(),
            positive_i128_to_u128(denominator)?,
        );
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
            let exponent = u8::try_from(exponent).map_err(|_| Status::INTERNAL_ERROR)?;
            let factor = pow10_i128(exponent)?;
            Self::new(coefficient.checked_mul(factor).ok_or(Status::OVERFLOW)?, 1)
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
        let gcd = gcd_u128(
            positive_i128_to_u128(self.denominator)?,
            positive_i128_to_u128(rhs.denominator)?,
        );
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

        let gcd_left = gcd_u128(
            self.numerator.unsigned_abs(),
            positive_i128_to_u128(rhs.denominator)?,
        );
        let gcd_right = gcd_u128(
            rhs.numerator.unsigned_abs(),
            positive_i128_to_u128(self.denominator)?,
        );
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
        let gcd_den = gcd_u128(
            positive_i128_to_u128(rhs.denominator)?,
            positive_i128_to_u128(self.denominator)?,
        );
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

    /// Checked exact integer power using repeated squaring.
    ///
    /// The VM validates the v0.1 public exponent range separately. Keeping the
    /// arithmetic primitive independent of pack validation lets fused and
    /// generated kernels share the same exact implementation.
    ///
    /// # Errors
    ///
    /// Returns [`Status::DIVIDE_BY_ZERO`] for zero raised to a negative power
    /// and [`Status::OVERFLOW`] when a bounded intermediate cannot be represented.
    pub fn checked_powi(self, exponent: i32) -> Result<Self, Status> {
        if exponent == 0 {
            return Ok(Self::ONE);
        }
        if exponent < 0 && self.is_zero() {
            return Err(Status::DIVIDE_BY_ZERO);
        }

        let mut power = exponent.unsigned_abs();
        let mut base = self;
        let mut result = Self::ONE;
        while power != 0 {
            if power & 1 == 1 {
                result = result.checked_mul(base)?;
            }
            power >>= 1;
            if power != 0 {
                base = base.checked_mul(base)?;
            }
        }

        if exponent < 0 {
            Self::ONE.checked_div(result)
        } else {
            Ok(result)
        }
    }

    /// Exact comparison within the bounded work profile.
    ///
    /// # Errors
    ///
    /// Returns [`Status::OVERFLOW`] when cross multiplication exceeds `i128`.
    pub fn checked_cmp(self, rhs: Self) -> Result<Ordering, Status> {
        let left = self
            .numerator
            .checked_mul(rhs.denominator)
            .ok_or(Status::OVERFLOW)?;
        let right = rhs
            .numerator
            .checked_mul(self.denominator)
            .ok_or(Status::OVERFLOW)?;
        Ok(left.cmp(&right))
    }

    /// Quantizes the exact rational to a canonical decimal.
    ///
    /// # Errors
    ///
    /// Returns a stable status if the scale is unsupported or the rounded
    /// coefficient cannot be represented.
    pub fn round_to_decimal(self, scale: u8, mode: RoundingMode) -> Result<RoundedDecimal, Status> {
        if scale > 18 {
            return Err(Status::INVALID_REQUEST);
        }

        let factor = pow10_u128(scale)?;
        let magnitude = self.numerator.unsigned_abs();
        let scaled = magnitude.checked_mul(factor).ok_or(Status::OVERFLOW)?;
        let denominator = positive_i128_to_u128(self.denominator)?;
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
                        Ordering::Equal => mode == RoundingMode::HalfAway || quotient % 2 == 1,
                    }
                }
            }
        };

        let magnitude = if increment {
            quotient.checked_add(1).ok_or(Status::OVERFLOW)?
        } else {
            quotient
        };
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

        let exponent = i8::try_from(scale)
            .map_err(|_| Status::OVERFLOW)?
            .checked_neg()
            .ok_or(Status::OVERFLOW)?;
        Ok(RoundedDecimal {
            value: Decimal64::from_parts(coefficient, exponent)?,
            rounded: remainder != 0,
        })
    }

    /// Computes a correctly rounded base-10 square root without binary floating point.
    ///
    /// The bounded implementation compares 256-bit integer products and performs
    /// at most 64 binary-search steps. It therefore has an input-independent work
    /// bound and can decide nearest-mode ties exactly.
    ///
    /// # Errors
    ///
    /// Returns [`Status::DOMAIN_ERROR`] for a negative input,
    /// [`Status::INVALID_REQUEST`] for a scale above 18, or [`Status::OVERFLOW`]
    /// when the rounded `decimal64-v1` coefficient cannot be represented.
    pub fn sqrt_to_decimal(self, scale: u8, mode: RoundingMode) -> Result<SqrtDecimal, Status> {
        if self.numerator < 0 {
            return Err(Status::DOMAIN_ERROR);
        }
        if scale > 18 {
            return Err(Status::INVALID_REQUEST);
        }
        if self.is_zero() {
            return Ok(SqrtDecimal {
                value: Decimal64::ZERO,
                rounded: false,
                inexact: false,
            });
        }

        let numerator = self.numerator.unsigned_abs();
        let denominator = positive_i128_to_u128(self.denominator)?;
        let factor = pow10_u128(scale)?;
        let factor_squared = factor.checked_mul(factor).ok_or(Status::OVERFLOW)?;
        let scaled_radicand = U256::multiply(numerator, factor_squared);
        let maximum = u128::from(i64::MAX.unsigned_abs());
        let beyond_maximum = maximum + 1;
        if compare_square_scaled(beyond_maximum, denominator, scaled_radicand) != Ordering::Greater
        {
            return Err(Status::OVERFLOW);
        }

        let mut low = 0u128;
        let mut high = beyond_maximum;
        while low < high {
            let middle = low + (high - low) / 2;
            if compare_square_scaled(middle, denominator, scaled_radicand) == Ordering::Greater {
                high = middle;
            } else {
                low = middle + 1;
            }
        }
        let floor = low.checked_sub(1).ok_or(Status::INTERNAL_ERROR)?;
        let exact_at_scale =
            compare_square_scaled(floor, denominator, scaled_radicand) == Ordering::Equal;

        let increment = if exact_at_scale {
            false
        } else {
            match mode {
                RoundingMode::TowardZero | RoundingMode::Floor => false,
                RoundingMode::Ceil => true,
                RoundingMode::HalfAway | RoundingMode::HalfEven => {
                    let doubled = floor.checked_mul(2).ok_or(Status::OVERFLOW)?;
                    let midpoint = doubled.checked_add(1).ok_or(Status::OVERFLOW)?;
                    let midpoint_squared =
                        midpoint.checked_mul(midpoint).ok_or(Status::OVERFLOW)?;
                    let midpoint_side = U256::multiply(midpoint_squared, denominator);
                    let radicand_side = scaled_radicand.checked_shl(2)?;
                    match radicand_side.cmp(&midpoint_side) {
                        Ordering::Greater => true,
                        Ordering::Less => false,
                        Ordering::Equal => mode == RoundingMode::HalfAway || floor % 2 == 1,
                    }
                }
            }
        };
        let coefficient = if increment {
            floor.checked_add(1).ok_or(Status::OVERFLOW)?
        } else {
            floor
        };
        let coefficient = i64::try_from(coefficient).map_err(|_| Status::OVERFLOW)?;
        let exponent = i8::try_from(scale)
            .map_err(|_| Status::OVERFLOW)?
            .checked_neg()
            .ok_or(Status::OVERFLOW)?;

        let (_, numerator_square) = integer_sqrt(numerator);
        let (_, denominator_square) = integer_sqrt(denominator);
        Ok(SqrtDecimal {
            value: Decimal64::from_parts(coefficient, exponent)?,
            rounded: !exact_at_scale,
            inexact: !(numerator_square && denominator_square),
        })
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct U256([u64; 4]);

impl U256 {
    #[allow(clippy::cast_possible_truncation)]
    fn multiply(left: u128, right: u128) -> Self {
        let mask = u128::from(u64::MAX);
        let left_low = left & mask;
        let left_high = left >> 64;
        let right_low = right & mask;
        let right_high = right >> 64;

        let low_product = left_low * right_low;
        let cross_left = left_low * right_high;
        let cross_right = left_high * right_low;
        let high_product = left_high * right_high;
        let middle = (low_product >> 64) + (cross_left & mask) + (cross_right & mask);
        let high = high_product + (cross_left >> 64) + (cross_right >> 64) + (middle >> 64);

        Self([
            low_product as u64,
            middle as u64,
            high as u64,
            (high >> 64) as u64,
        ])
    }

    fn checked_shl(self, bits: u32) -> Result<Self, Status> {
        if bits == 0 {
            return Ok(self);
        }
        if bits >= 64 || self.0[3] >> (64 - bits) != 0 {
            return Err(Status::OVERFLOW);
        }
        Ok(Self([
            self.0[0] << bits,
            (self.0[1] << bits) | (self.0[0] >> (64 - bits)),
            (self.0[2] << bits) | (self.0[1] >> (64 - bits)),
            (self.0[3] << bits) | (self.0[2] >> (64 - bits)),
        ]))
    }
}

impl Ord for U256 {
    fn cmp(&self, other: &Self) -> Ordering {
        for index in (0..4).rev() {
            match self.0[index].cmp(&other.0[index]) {
                Ordering::Equal => {}
                ordering => return ordering,
            }
        }
        Ordering::Equal
    }
}

impl PartialOrd for U256 {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

fn compare_square_scaled(coefficient: u128, denominator: u128, radicand: U256) -> Ordering {
    let square = coefficient * coefficient;
    U256::multiply(square, denominator).cmp(&radicand)
}

fn integer_sqrt(value: u128) -> (u128, bool) {
    let mut low = 0u128;
    let mut high = u128::from(u64::MAX) + 1;
    while low < high {
        let middle = low + (high - low) / 2;
        let square = middle * middle;
        if square > value {
            high = middle;
        } else {
            low = middle + 1;
        }
    }
    let floor = low - 1;
    (floor, floor * floor == value)
}

fn positive_i128_to_u128(value: i128) -> Result<u128, Status> {
    u128::try_from(value).map_err(|_| Status::INTERNAL_ERROR)
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
        assert_eq!(
            one_half.checked_div(WorkRational::ZERO),
            Err(Status::DIVIDE_BY_ZERO)
        );
    }

    #[test]
    fn integer_power_is_exact_for_positive_zero_and_negative_exponents() {
        let two_thirds = rational(2, 3);
        assert_eq!(two_thirds.checked_powi(3), Ok(rational(8, 27)));
        assert_eq!(two_thirds.checked_powi(0), Ok(WorkRational::ONE));
        assert_eq!(two_thirds.checked_powi(-2), Ok(rational(9, 4)));
        assert_eq!(
            WorkRational::ZERO.checked_powi(-1),
            Err(Status::DIVIDE_BY_ZERO)
        );
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

    #[test]
    fn square_root_is_correctly_rounded_for_every_mode() {
        let lower_tie = rational(9, 4);
        assert_eq!(
            lower_tie
                .sqrt_to_decimal(0, RoundingMode::HalfEven)
                .unwrap()
                .value,
            Decimal64::from_parts(2, 0).unwrap()
        );
        assert_eq!(
            lower_tie
                .sqrt_to_decimal(0, RoundingMode::TowardZero)
                .unwrap()
                .value,
            Decimal64::from_parts(1, 0).unwrap()
        );
        assert_eq!(
            lower_tie
                .sqrt_to_decimal(0, RoundingMode::Floor)
                .unwrap()
                .value,
            Decimal64::from_parts(1, 0).unwrap()
        );
        assert_eq!(
            lower_tie
                .sqrt_to_decimal(0, RoundingMode::Ceil)
                .unwrap()
                .value,
            Decimal64::from_parts(2, 0).unwrap()
        );

        let even_tie = rational(25, 4);
        assert_eq!(
            even_tie
                .sqrt_to_decimal(0, RoundingMode::HalfEven)
                .unwrap()
                .value,
            Decimal64::from_parts(2, 0).unwrap()
        );
        assert_eq!(
            even_tie
                .sqrt_to_decimal(0, RoundingMode::HalfAway)
                .unwrap()
                .value,
            Decimal64::from_parts(3, 0).unwrap()
        );
    }

    #[test]
    fn square_root_flags_exact_rational_and_irrational_results() {
        let exact = rational(1, 4)
            .sqrt_to_decimal(1, RoundingMode::HalfEven)
            .unwrap();
        assert_eq!(exact.value, Decimal64::from_parts(5, -1).unwrap());
        assert!(!exact.rounded);
        assert!(!exact.inexact);

        let rational_but_rounded = rational(1, 9)
            .sqrt_to_decimal(2, RoundingMode::HalfEven)
            .unwrap();
        assert_eq!(
            rational_but_rounded.value,
            Decimal64::from_parts(33, -2).unwrap()
        );
        assert!(rational_but_rounded.rounded);
        assert!(!rational_but_rounded.inexact);

        let irrational = rational(2, 1)
            .sqrt_to_decimal(6, RoundingMode::HalfEven)
            .unwrap();
        assert_eq!(
            irrational.value,
            Decimal64::from_parts(1_414_214, -6).unwrap()
        );
        assert!(irrational.rounded);
        assert!(irrational.inexact);
    }

    #[test]
    fn square_root_rejects_negative_and_overflowing_results() {
        assert_eq!(
            rational(-1, 1).sqrt_to_decimal(6, RoundingMode::HalfEven),
            Err(Status::DOMAIN_ERROR)
        );
        let too_large = WorkRational::new(i128::MAX, 1).unwrap();
        assert_eq!(
            too_large.sqrt_to_decimal(18, RoundingMode::HalfEven),
            Err(Status::OVERFLOW)
        );
    }
}
