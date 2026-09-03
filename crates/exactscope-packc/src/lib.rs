#![forbid(unsafe_code)]
#![doc = "ExactScope build-time pack compiler scaffold."]

//! This desktop-only crate will validate reviewed source JSON, execute golden
//! vectors, and emit canonical `.xsp` bytes. It is not linked into devices.

/// Returns the source format identifier frozen by the v0.1 specification.
#[must_use]
pub const fn source_format() -> &'static str {
    "exactscope.scopepack.source"
}
