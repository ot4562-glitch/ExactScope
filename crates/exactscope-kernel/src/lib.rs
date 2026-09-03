#![no_std]
#![forbid(unsafe_code)]
#![doc = "`ExactScope` deterministic kernel scaffold."]

//! This crate intentionally contains no calculation implementation yet.
//! Its public responsibility is frozen by `docs/ARCHITECTURE.md` and the
//! normative files under `spec/` before implementation begins.

/// ABI major required by the v0.1 design baseline.
pub const DESIGN_ABI_MAJOR: u16 = 1;

/// ABI minor required by the v0.1 design baseline.
pub const DESIGN_ABI_MINOR: u16 = 0;
