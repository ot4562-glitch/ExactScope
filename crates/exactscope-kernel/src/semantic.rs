//! Scalar semantics and compact typed values.

use crate::{Decimal64, Status};

/// Generic dimensionless number.
pub const SEMANTIC_NUMBER: u8 = 0;
/// Count semantic.
pub const SEMANTIC_COUNT: u8 = 1;
/// Currency amount semantic.
pub const SEMANTIC_CURRENCY_AMOUNT: u8 = 2;
/// Price semantic.
pub const SEMANTIC_PRICE: u8 = 3;
/// Quantity semantic.
pub const SEMANTIC_QUANTITY: u8 = 4;
/// Percentage-point rate semantic.
pub const SEMANTIC_RATE_PERCENT: u8 = 5;
/// Ratio-form rate semantic.
pub const SEMANTIC_RATE_RATIO: u8 = 6;
/// Index semantic.
pub const SEMANTIC_INDEX: u8 = 7;
/// Time-period semantic.
pub const SEMANTIC_TIME_PERIODS: u8 = 8;
/// Probability semantic.
pub const SEMANTIC_PROBABILITY: u8 = 9;
/// Elasticity semantic.
pub const SEMANTIC_ELASTICITY: u8 = 10;

/// Value depends on a bounded inexact numerical kernel.
pub const VALUE_FLAG_INEXACT: u32 = 0x0000_0001;
/// Value was changed by final output rounding.
pub const VALUE_FLAG_ROUNDED: u32 = 0x0000_0002;
/// All defined value flags.
pub const VALUE_FLAGS_V1: u32 = VALUE_FLAG_INEXACT | VALUE_FLAG_ROUNDED;

/// Typed scalar passed to the deterministic evaluator.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ScalarValue {
    /// Canonical decimal payload.
    pub decimal: Decimal64,
    /// Stable semantic kind.
    pub semantic_kind: u8,
    /// Registry-local unit identity, zero when unspecified.
    pub unit_id: u16,
    /// Stable value flags.
    pub flags: u32,
}

impl ScalarValue {
    /// Constructs a plain exact typed scalar.
    #[must_use]
    pub const fn new(decimal: Decimal64, semantic_kind: u8, unit_id: u16) -> Self {
        Self {
            decimal,
            semantic_kind,
            unit_id,
            flags: 0,
        }
    }

    /// Validates canonical representation, semantic kind, and reserved flags.
    ///
    /// # Errors
    ///
    /// Returns a stable typed status for malformed input.
    pub fn validate(self) -> Result<(), Status> {
        if !self.decimal.is_canonical() {
            return Err(Status::INVALID_DECIMAL);
        }
        if self.semantic_kind > SEMANTIC_ELASTICITY {
            return Err(Status::ARGUMENT_TYPE);
        }
        if self.flags & !VALUE_FLAGS_V1 != 0 {
            return Err(Status::INVALID_REQUEST);
        }
        Ok(())
    }
}

/// Ensures two supplied nonzero unit IDs agree.
///
/// Unit zero is unspecified and therefore does not prove incompatibility.
///
/// # Errors
///
/// Returns [`Status::UNIT_MISMATCH`] when two explicit IDs differ.
pub const fn validate_same_unit(left: u16, right: u16) -> Result<(), Status> {
    if left != 0 && right != 0 && left != right {
        Err(Status::UNIT_MISMATCH)
    } else {
        Ok(())
    }
}
