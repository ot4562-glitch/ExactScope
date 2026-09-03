//! Stable output rounding modes.

use crate::Status;

/// Stable v1 rounding policy.
#[repr(u8)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RoundingMode {
    /// Nearest value; exact ties keep an even retained digit.
    HalfEven = 0,
    /// Nearest value; exact ties move away from zero.
    HalfAway = 1,
    /// Discard the fractional remainder toward zero.
    TowardZero = 2,
    /// Round toward negative infinity.
    Floor = 3,
    /// Round toward positive infinity.
    Ceil = 4,
}

impl RoundingMode {
    /// Creates a rounding mode from its stable numeric ID.
    ///
    /// # Errors
    ///
    /// Returns [`Status::INVALID_REQUEST`] for an unknown ID.
    pub const fn from_id(id: u8) -> Result<Self, Status> {
        match id {
            0 => Ok(Self::HalfEven),
            1 => Ok(Self::HalfAway),
            2 => Ok(Self::TowardZero),
            3 => Ok(Self::Floor),
            4 => Ok(Self::Ceil),
            _ => Err(Status::INVALID_REQUEST),
        }
    }

    /// Returns the stable numeric ID.
    #[must_use]
    pub const fn id(self) -> u8 {
        self as u8
    }
}
