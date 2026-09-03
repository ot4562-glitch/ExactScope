#![no_std]
#![doc = "ExactScope WebAssembly wrapper scaffold."]

//! The final artifact targets `wasm32v1-none`, imports no host functions, and
//! follows `spec/WASM_ABI_V0_1.md`. No export is claimed by this scaffold.

pub use exactscope_kernel::{DESIGN_ABI_MAJOR, DESIGN_ABI_MINOR};
