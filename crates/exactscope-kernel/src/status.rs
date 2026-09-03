//! Stable `ExactScope` status codes.

/// Stable `ExactScope` status value.
#[repr(transparent)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Status(u16);

impl Status {
    /// Operation completed successfully.
    pub const OK: Self = Self(0);
    /// Request envelope or required field is malformed.
    pub const INVALID_REQUEST: Self = Self(1);
    /// ABI versions are incompatible.
    pub const ABI_MISMATCH: Self = Self(2);
    /// Operation is not installed or known.
    pub const UNKNOWN_OPERATION: Self = Self(3);
    /// Pack is not mounted.
    pub const UNKNOWN_PACK: Self = Self(4);
    /// Argument count is wrong.
    pub const ARGUMENT_COUNT: Self = Self(5);
    /// Argument shape or type is wrong.
    pub const ARGUMENT_TYPE: Self = Self(6);
    /// Method selection is ambiguous.
    pub const AMBIGUOUS_METHOD: Self = Self(7);
    /// Required information is missing.
    pub const MISSING_INFORMATION: Self = Self(8);
    /// Decimal lexical form is invalid.
    pub const INVALID_DECIMAL: Self = Self(9);
    /// Mathematical domain is invalid.
    pub const DOMAIN_ERROR: Self = Self(10);
    /// Declared input constraint failed.
    pub const CONSTRAINT_VIOLATION: Self = Self(11);
    /// Unit relationship failed.
    pub const UNIT_MISMATCH: Self = Self(12);
    /// Exact denominator is zero.
    pub const DIVIDE_BY_ZERO: Self = Self(13);
    /// Bounded arithmetic overflowed.
    pub const OVERFLOW: Self = Self(14);
    /// Required precision or classification cannot be proven.
    pub const PRECISION_UNRESOLVED: Self = Self(15);
    /// Too few observations were supplied.
    pub const INSUFFICIENT_DATA: Self = Self(16);
    /// Caller-provided storage is too small.
    pub const BUFFER_TOO_SMALL: Self = Self(17);
    /// Pack contents are structurally or semantically invalid.
    pub const PACK_INVALID: Self = Self(18);
    /// Pack format or ABI version is unsupported.
    pub const PACK_VERSION_UNSUPPORTED: Self = Self(19);
    /// A bounded resource limit was exceeded.
    pub const RESOURCE_LIMIT: Self = Self(20);
    /// Recognized functionality is unavailable in this build.
    pub const UNSUPPORTED_OPERATION: Self = Self(21);
    /// Integrity check failed.
    pub const INTEGRITY_ERROR: Self = Self(22);
    /// Internal invariant failed.
    pub const INTERNAL_ERROR: Self = Self(23);

    /// Returns the stable numeric status code.
    #[must_use]
    pub const fn code(self) -> u16 {
        self.0
    }

    /// Creates a status from a known core code.
    #[must_use]
    pub const fn from_code(code: u16) -> Option<Self> {
        if code <= Self::INTERNAL_ERROR.0 {
            Some(Self(code))
        } else {
            None
        }
    }

    /// Returns true only for successful evaluation.
    #[must_use]
    pub const fn is_ok(self) -> bool {
        self.0 == 0
    }
}

impl From<Status> for u16 {
    fn from(value: Status) -> Self {
        value.code()
    }
}

#[cfg(test)]
mod tests {
    use super::Status;

    #[test]
    fn stable_range_is_exact() {
        for code in 0..=23 {
            assert_eq!(Status::from_code(code).map(Status::code), Some(code));
        }
        assert_eq!(Status::from_code(24), None);
        assert!(Status::OK.is_ok());
        assert!(!Status::INVALID_REQUEST.is_ok());
    }
}
