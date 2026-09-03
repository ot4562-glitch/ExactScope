#![forbid(unsafe_code)]
#![doc = "ExactScope conformance harness scaffold."]

//! This host-side crate will compare canonical result bytes across native,
//! WebAssembly, fused, static, and dynamic-pack execution paths.

/// Conformance corpus format version reserved by the design baseline.
pub const CORPUS_FORMAT_VERSION: u16 = 1;
