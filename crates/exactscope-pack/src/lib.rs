#![no_std]
#![forbid(unsafe_code)]
#![doc = "`ExactScope` scope-pack loader scaffold."]

//! This crate will decode validated data-only `.xsp` packs. It must not load
//! native plugins or duplicate numeric semantics from `exactscope-kernel`.

pub use exactscope_kernel::{DESIGN_ABI_MAJOR, DESIGN_ABI_MINOR};
