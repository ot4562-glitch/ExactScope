#![no_std]
#![forbid(unsafe_code)]
#![doc = "`ExactScope` Tiny JSON adapter scaffold."]

//! This adapter will parse only the bounded `xs_find` and `xs_eval` envelopes.
//! It must not calculate, coerce, round, classify, or repair values.

pub use exactscope_kernel::{DESIGN_ABI_MAJOR, DESIGN_ABI_MINOR};
