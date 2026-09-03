#![no_std]
#![forbid(unsafe_code)]
#![doc = "Data-only pack registry for `ExactScope`."]

//! The first runtime slice exposes one immutable fused operation while keeping
//! the same identity that a later validated `.xsp` loader will use. The
//! registry owns no numeric semantics; evaluation remains in
//! `exactscope-kernel`.

pub use exactscope_kernel::{DESIGN_ABI_MAJOR, DESIGN_ABI_MINOR};

mod dynamic;
pub mod format;

pub use dynamic::{DynamicOperation, PackView};

use exactscope_kernel::{OperationDecl, Status, PED_MID_OPERATION};

/// Fused pack slot reserved for the first official economics pack.
pub const ECON_UNDERGRAD_PACK_SLOT: u16 = 1;
/// Globally meaningful source pack identity.
pub const ECON_UNDERGRAD_PACK_ID: &str = "org.exactscope.econ-undergrad";
/// Compact machine provenance used by Tiny JSON.
pub const ECON_UNDERGRAD_PROVENANCE: &str = "econ-undergrad@0.1.0";
/// Source pack semantic version.
pub const ECON_UNDERGRAD_VERSION: &str = "0.1.0";
/// Maximum discovery matches in the v0.1 tiny profile.
pub const MAX_FIND_MATCHES: usize = 5;

const PED_ALIASES: [&str; 5] = [
    "price elasticity of demand midpoint",
    "midpoint price elasticity",
    "arc elasticity of demand",
    "ped midpoint",
    "econ.ped.mid",
];

/// Immutable reference to one installed operation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct OperationRef {
    /// Fused/dynamic registry slot.
    pub pack_slot: u16,
    /// Pack identity.
    pub pack_id: &'static str,
    /// Compact pack provenance.
    pub provenance: &'static str,
    /// Deterministic operation declaration.
    pub operation: &'static OperationDecl,
}

/// Compact deterministic discovery result.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Match {
    /// Installed operation.
    pub operation: OperationRef,
    /// Deterministic rank; lower values are better.
    pub rank: u16,
}

impl Match {
    const EMPTY: Self = Self {
        operation: OperationRef {
            pack_slot: 0,
            pack_id: "",
            provenance: "",
            operation: &PED_MID_OPERATION,
        },
        rank: u16::MAX,
    };
}

/// Zero-allocation immutable registry for fused official operations.
#[derive(Clone, Copy, Debug, Default)]
pub struct FusedRegistry;

impl FusedRegistry {
    /// Creates the immutable fused registry.
    #[must_use]
    pub const fn new() -> Self {
        Self
    }

    /// Looks up an exact canonical operation key.
    ///
    /// # Errors
    ///
    /// Returns [`Status::UNKNOWN_OPERATION`] when the exact key is not fused.
    pub fn lookup(self, key: &[u8]) -> Result<OperationRef, Status> {
        if key == PED_MID_OPERATION.key.as_bytes() {
            Ok(ped_operation_ref())
        } else {
            Err(Status::UNKNOWN_OPERATION)
        }
    }

    /// Resolves a deliberately narrow discovery query into installed matches.
    ///
    /// The first slice refuses the vague query `price elasticity` because it
    /// does not identify midpoint versus point elasticity. This is intentional
    /// fail-closed behavior, not a weak search implementation.
    ///
    /// # Errors
    ///
    /// Returns a stable status for malformed, ambiguous, unknown, or
    /// undersized discovery requests.
    pub fn find(self, query: &[u8], output: &mut [Match]) -> Result<usize, Status> {
        if query.is_empty() || query.len() > 96 {
            return Err(Status::INVALID_REQUEST);
        }

        let mut normalized = [0u8; 96];
        let normalized_len = normalize_query(query, &mut normalized)?;
        let query = &normalized[..normalized_len];
        if query.is_empty() {
            return Err(Status::INVALID_REQUEST);
        }

        if mentions_price_elasticity(query) && !has_midpoint_cue(query) {
            return Err(Status::AMBIGUOUS_METHOD);
        }

        let mut best_rank = u16::MAX;
        for alias in PED_ALIASES {
            let rank = alias_rank(query, alias.as_bytes());
            best_rank = best_rank.min(rank);
        }
        if best_rank == u16::MAX {
            return Err(Status::UNKNOWN_OPERATION);
        }
        if output.is_empty() {
            return Err(Status::BUFFER_TOO_SMALL);
        }

        output[0] = Match {
            operation: ped_operation_ref(),
            rank: best_rank,
        };
        Ok(1)
    }

    /// Returns the number of fused operations.
    #[must_use]
    pub const fn operation_count(self) -> usize {
        1
    }
}

/// Creates an initialized fixed discovery buffer.
#[must_use]
pub const fn empty_matches() -> [Match; MAX_FIND_MATCHES] {
    [Match::EMPTY; MAX_FIND_MATCHES]
}

/// Returns the first fused economics operation.
#[must_use]
pub const fn ped_operation_ref() -> OperationRef {
    OperationRef {
        pack_slot: ECON_UNDERGRAD_PACK_SLOT,
        pack_id: ECON_UNDERGRAD_PACK_ID,
        provenance: ECON_UNDERGRAD_PROVENANCE,
        operation: &PED_MID_OPERATION,
    }
}

fn normalize_query(input: &[u8], output: &mut [u8; 96]) -> Result<usize, Status> {
    let mut written = 0usize;
    let mut pending_space = false;

    for &byte in input {
        if byte >= 0x80 {
            return Err(Status::UNKNOWN_OPERATION);
        }
        let normalized = match byte {
            b'A'..=b'Z' => byte + (b'a' - b'A'),
            b'a'..=b'z' | b'0'..=b'9' | b'.' | b'_' => byte,
            _ if byte.is_ascii_whitespace() || byte.is_ascii_punctuation() => {
                pending_space = written != 0;
                continue;
            }
            _ => return Err(Status::INVALID_REQUEST),
        };

        if pending_space {
            if written >= output.len() {
                return Err(Status::RESOURCE_LIMIT);
            }
            output[written] = b' ';
            written += 1;
            pending_space = false;
        }
        if written >= output.len() {
            return Err(Status::RESOURCE_LIMIT);
        }
        output[written] = normalized;
        written += 1;
    }

    Ok(written)
}

fn alias_rank(query: &[u8], alias: &[u8]) -> u16 {
    if query == alias {
        return 0;
    }
    if alias.starts_with(query) {
        return 10;
    }
    if all_query_tokens_present(query, alias) {
        return 30;
    }
    u16::MAX
}

fn all_query_tokens_present(query: &[u8], alias: &[u8]) -> bool {
    let mut start = 0usize;
    let mut saw_token = false;
    for index in 0..=query.len() {
        if index != query.len() && query[index] != b' ' {
            continue;
        }
        if index > start {
            let token = &query[start..index];
            if token.len() < 3 || !contains_token(alias, token) {
                return false;
            }
            saw_token = true;
        }
        start = index.saturating_add(1);
    }
    saw_token
}

fn contains_token(haystack: &[u8], needle: &[u8]) -> bool {
    if needle.is_empty() || needle.len() > haystack.len() {
        return false;
    }
    for start in 0..=haystack.len() - needle.len() {
        let end = start + needle.len();
        if &haystack[start..end] != needle {
            continue;
        }
        let left_ok = start == 0 || haystack[start - 1] == b' ' || haystack[start - 1] == b'.';
        let right_ok = end == haystack.len() || haystack[end] == b' ' || haystack[end] == b'.';
        if left_ok && right_ok {
            return true;
        }
    }
    false
}

fn mentions_price_elasticity(query: &[u8]) -> bool {
    contains_token(query, b"elasticity") || contains_token(query, b"ped")
}

fn has_midpoint_cue(query: &[u8]) -> bool {
    query == b"econ.ped.mid" || contains_token(query, b"midpoint") || contains_token(query, b"arc")
}

#[cfg(test)]
mod tests {
    use super::{empty_matches, FusedRegistry, ECON_UNDERGRAD_PACK_SLOT};
    use exactscope_kernel::Status;

    #[test]
    fn exact_lookup_is_stable() {
        let registry = FusedRegistry::new();
        let operation = registry.lookup(b"econ.ped.mid").unwrap();
        assert_eq!(operation.pack_slot, ECON_UNDERGRAD_PACK_SLOT);
        assert_eq!(operation.operation.id, 301);
        assert_eq!(operation.operation.revision, 1);
        assert_eq!(
            registry.lookup(b"ECON.PED.MID"),
            Err(Status::UNKNOWN_OPERATION)
        );
    }

    #[test]
    fn method_specific_discovery_succeeds() {
        let registry = FusedRegistry::new();
        let mut matches = empty_matches();
        let count = registry
            .find(b"midpoint price elasticity", &mut matches)
            .unwrap();
        assert_eq!(count, 1);
        assert_eq!(matches[0].operation.operation.key, "econ.ped.mid");
    }

    #[test]
    fn vague_discovery_fails_closed() {
        let registry = FusedRegistry::new();
        let mut matches = empty_matches();
        assert_eq!(
            registry.find(b"price elasticity", &mut matches),
            Err(Status::AMBIGUOUS_METHOD)
        );
    }

    #[test]
    fn unknown_discovery_does_not_guess() {
        let registry = FusedRegistry::new();
        let mut matches = empty_matches();
        assert_eq!(
            registry.find(b"gross domestic product", &mut matches),
            Err(Status::UNKNOWN_OPERATION)
        );
    }
}
