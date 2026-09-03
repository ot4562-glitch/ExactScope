#![no_std]
#![doc = "`ExactScope` C ABI wrapper scaffold."]

//! The actual exported ABI is not implemented in this design commit. When it
//! is added, all unsafe pointer handling remains isolated in this crate and
//! must conform to `include/exactscope.h` and `spec/CORE_ABI_V0_1.md`.

pub use exactscope_kernel::{DESIGN_ABI_MAJOR, DESIGN_ABI_MINOR};
