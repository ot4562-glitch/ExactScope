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

pub use dynamic::{DynamicInputMeta, DynamicOperation, PackView};

use exactscope_kernel::{
    OperationDecl, StatisticsOperationDecl, Status, OFFICIAL_ECON_OPERATIONS,
    OFFICIAL_STATS_OPERATIONS, PED_MID_OPERATION, STATS_SUM_OPERATION,
};

/// Fused pack slot reserved for the first official economics pack.
pub const ECON_UNDERGRAD_PACK_SLOT: u16 = 1;
/// Globally meaningful source pack identity.
pub const ECON_UNDERGRAD_PACK_ID: &str = "org.exactscope.econ-undergrad";
/// Compact machine provenance used by Tiny JSON.
pub const ECON_UNDERGRAD_PROVENANCE: &str = "econ-undergrad@0.1.0";
/// Source pack semantic version.
pub const ECON_UNDERGRAD_VERSION: &str = "0.1.0";
/// Fused pack slot reserved for the first statistics pack.
pub const STATISTICS_CORE_PACK_SLOT: u16 = 2;
/// Globally meaningful statistics source-pack identity.
pub const STATISTICS_CORE_PACK_ID: &str = "org.exactscope.statistics-core";
/// Compact statistics provenance used by host adapters.
pub const STATISTICS_CORE_PROVENANCE: &str = "statistics-core@0.1.0";
/// Maximum discovery matches in the v0.1 tiny profile.
pub const MAX_FIND_MATCHES: usize = 5;

const PED_ALIASES: [&str; 5] = [
    "price elasticity of demand midpoint",
    "midpoint price elasticity",
    "arc elasticity of demand",
    "ped midpoint",
    "econ.ped.mid",
];

const GDP_DEFLATOR_ALIASES: [&str; 3] = [
    "gdp deflator",
    "nominal real gdp deflator",
    "deflator from nominal and real gdp",
];
const CPI_INFLATION_ALIASES: [&str; 3] = [
    "cpi inflation",
    "inflation from cpi",
    "consumer price index inflation",
];
const MONEY_VELOCITY_ALIASES: [&str; 3] = [
    "money velocity",
    "velocity of money",
    "quantity equation velocity",
];
const REAL_RATE_EXACT_ALIASES: [&str; 3] = [
    "exact real interest rate",
    "fisher exact real rate",
    "exact fisher equation",
];
const REAL_RATE_APPROX_ALIASES: [&str; 3] = [
    "approx real interest rate",
    "approximate real interest rate",
    "fisher approximation real rate",
];
const OUTPUT_GAP_ALIASES: [&str; 2] = ["output gap", "gdp output gap"];
const MPC_ALIASES: [&str; 3] = ["mpc", "marginal propensity to consume", "consumption mpc"];
const MPS_ALIASES: [&str; 3] = ["mps", "marginal propensity to save", "saving mps"];
const TERMS_OF_TRADE_ALIASES: [&str; 3] = [
    "terms of trade",
    "terms of trade index",
    "export import price index ratio",
];
const OPPORTUNITY_COST_ALIASES: [&str; 2] = ["opportunity cost", "output opportunity cost"];
const GROWTH_RATE_ALIASES: [&str; 3] = ["growth rate", "percent growth", "percentage growth"];
const RULE70_ALIASES: [&str; 3] = ["rule of 70", "rule70", "doubling time rule 70"];
const RULE72_ALIASES: [&str; 3] = ["rule of 72", "rule72", "doubling time rule 72"];
const PER_CAPITA_GROWTH_ALIASES: [&str; 3] = [
    "per capita growth approximation",
    "approx per capita growth",
    "per capita growth difference",
];

const ECON_ALIASES: [&[&str]; 15] = [
    &PED_ALIASES,
    &GDP_DEFLATOR_ALIASES,
    &CPI_INFLATION_ALIASES,
    &MONEY_VELOCITY_ALIASES,
    &REAL_RATE_EXACT_ALIASES,
    &REAL_RATE_APPROX_ALIASES,
    &OUTPUT_GAP_ALIASES,
    &MPC_ALIASES,
    &MPS_ALIASES,
    &TERMS_OF_TRADE_ALIASES,
    &OPPORTUNITY_COST_ALIASES,
    &GROWTH_RATE_ALIASES,
    &RULE70_ALIASES,
    &RULE72_ALIASES,
    &PER_CAPITA_GROWTH_ALIASES,
];

const STATS_SUM_ALIASES: [&str; 3] = ["sum", "statistics sum", "stats.sum"];
const STATS_MEAN_ALIASES: [&str; 4] = ["mean", "arithmetic mean", "average", "stats.mean"];
const STATS_WEIGHTED_MEAN_ALIASES: [&str; 3] =
    ["weighted mean", "weighted average", "stats.mean.weighted"];
const STATS_VARIANCE_POPULATION_ALIASES: [&str; 3] = [
    "population variance",
    "variance population",
    "stats.var.pop",
];
const STATS_VARIANCE_SAMPLE_ALIASES: [&str; 3] =
    ["sample variance", "variance sample", "stats.var.sample"];
const STATS_SD_POPULATION_ALIASES: [&str; 3] = [
    "population standard deviation",
    "population stddev",
    "stats.sd.pop",
];
const STATS_SD_SAMPLE_ALIASES: [&str; 3] = [
    "sample standard deviation",
    "sample stddev",
    "stats.sd.sample",
];
const STATS_COVARIANCE_POPULATION_ALIASES: [&str; 3] = [
    "population covariance",
    "covariance population",
    "stats.cov.pop",
];
const STATS_COVARIANCE_SAMPLE_ALIASES: [&str; 3] =
    ["sample covariance", "covariance sample", "stats.cov.sample"];
const STATS_CORRELATION_ALIASES: [&str; 4] = [
    "pearson correlation",
    "pearson product moment correlation",
    "correlation",
    "stats.corr.pearson",
];
const STATS_LINEAR_REGRESSION_ALIASES: [&str; 4] = [
    "linear regression",
    "simple linear regression",
    "least squares regression",
    "stats.regression.linear",
];
const STATS_ALIASES: [&[&str]; 11] = [
    &STATS_SUM_ALIASES,
    &STATS_MEAN_ALIASES,
    &STATS_WEIGHTED_MEAN_ALIASES,
    &STATS_VARIANCE_POPULATION_ALIASES,
    &STATS_VARIANCE_SAMPLE_ALIASES,
    &STATS_SD_POPULATION_ALIASES,
    &STATS_SD_SAMPLE_ALIASES,
    &STATS_COVARIANCE_POPULATION_ALIASES,
    &STATS_COVARIANCE_SAMPLE_ALIASES,
    &STATS_CORRELATION_ALIASES,
    &STATS_LINEAR_REGRESSION_ALIASES,
];

/// Immutable reference to one fused statistics operation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct StatisticsOperationRef {
    /// Fused statistics pack slot.
    pub pack_slot: u16,
    /// Stable statistics pack identity.
    pub pack_id: &'static str,
    /// Compact pack provenance.
    pub provenance: &'static str,
    /// Deterministic built-in statistics declaration.
    pub operation: &'static StatisticsOperationDecl,
}

/// Compact deterministic statistics discovery result.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct StatisticsMatch {
    /// Installed statistics operation.
    pub operation: StatisticsOperationRef,
    /// Deterministic rank; lower values are better.
    pub rank: u16,
}

impl StatisticsMatch {
    const EMPTY: Self = Self {
        operation: StatisticsOperationRef {
            pack_slot: STATISTICS_CORE_PACK_SLOT,
            pack_id: STATISTICS_CORE_PACK_ID,
            provenance: STATISTICS_CORE_PROVENANCE,
            operation: &STATS_SUM_OPERATION,
        },
        rank: u16::MAX,
    };
}

/// Creates an initialized statistics discovery buffer.
#[must_use]
pub const fn empty_statistics_matches() -> [StatisticsMatch; MAX_FIND_MATCHES] {
    [StatisticsMatch::EMPTY; MAX_FIND_MATCHES]
}

/// Zero-allocation exact lookup for the executable statistics kernel slice.
#[derive(Clone, Copy, Debug, Default)]
pub struct StatisticsRegistry;

impl StatisticsRegistry {
    /// Creates the immutable statistics registry.
    #[must_use]
    pub const fn new() -> Self {
        Self
    }

    /// Looks up an exact canonical statistics key.
    ///
    /// # Errors
    ///
    /// Returns [`Status::UNKNOWN_OPERATION`] when the key is not part of the
    /// executable fused statistics slice.
    pub fn lookup(self, key: &[u8]) -> Result<StatisticsOperationRef, Status> {
        for operation in OFFICIAL_STATS_OPERATIONS {
            if key == operation.key.as_bytes() {
                return Ok(statistics_operation_ref(operation));
            }
        }
        Err(Status::UNKNOWN_OPERATION)
    }

    /// Looks up an executable statistics operation by pack-local ID.
    ///
    /// # Errors
    ///
    /// Returns [`Status::UNKNOWN_OPERATION`] when the ID is not fused.
    pub fn lookup_id(self, operation_id: u32) -> Result<StatisticsOperationRef, Status> {
        for operation in OFFICIAL_STATS_OPERATIONS {
            if operation.id == operation_id {
                return Ok(statistics_operation_ref(operation));
            }
        }
        Err(Status::UNKNOWN_OPERATION)
    }

    /// Discovers one or more executable statistics operations by alias.
    ///
    /// # Errors
    ///
    /// Returns a stable malformed/resource/unknown status when the query cannot
    /// be normalized or no executable statistics operation matches it.
    pub fn find(self, query: &[u8], output: &mut [StatisticsMatch]) -> Result<usize, Status> {
        if query.is_empty() || query.len() > 96 {
            return Err(Status::INVALID_REQUEST);
        }
        let mut normalized = [0u8; 96];
        let normalized_len = normalize_query(query, &mut normalized)?;
        let query = &normalized[..normalized_len];
        if query.is_empty() {
            return Err(Status::INVALID_REQUEST);
        }

        let mut matches = empty_statistics_matches();
        let mut match_count = 0usize;
        for (index, operation) in OFFICIAL_STATS_OPERATIONS.iter().enumerate() {
            let mut best_rank = alias_rank(query, operation.key.as_bytes());
            for alias in STATS_ALIASES[index] {
                best_rank = best_rank.min(alias_rank(query, alias.as_bytes()));
            }
            if best_rank != u16::MAX {
                insert_statistics_match(
                    &mut matches,
                    &mut match_count,
                    StatisticsMatch {
                        operation: statistics_operation_ref(operation),
                        rank: best_rank,
                    },
                );
            }
        }
        if match_count == 0 {
            return Err(Status::UNKNOWN_OPERATION);
        }
        if output.is_empty() {
            return Err(Status::BUFFER_TOO_SMALL);
        }
        let written = output.len().min(match_count);
        output[..written].copy_from_slice(&matches[..written]);
        Ok(written)
    }

    /// Number of executable fused statistics operations in this slice.
    #[must_use]
    pub const fn operation_count(self) -> usize {
        OFFICIAL_STATS_OPERATIONS.len()
    }
}

const fn statistics_operation_ref(
    operation: &'static StatisticsOperationDecl,
) -> StatisticsOperationRef {
    StatisticsOperationRef {
        pack_slot: STATISTICS_CORE_PACK_SLOT,
        pack_id: STATISTICS_CORE_PACK_ID,
        provenance: STATISTICS_CORE_PROVENANCE,
        operation,
    }
}

fn insert_statistics_match(
    matches: &mut [StatisticsMatch; MAX_FIND_MATCHES],
    count: &mut usize,
    candidate: StatisticsMatch,
) {
    let occupied = (*count).min(MAX_FIND_MATCHES);
    let candidate_key = (candidate.rank, candidate.operation.operation.id);
    let mut insertion = occupied;
    for (index, existing) in matches[..occupied].iter().enumerate() {
        let existing_key = (existing.rank, existing.operation.operation.id);
        if candidate_key < existing_key {
            insertion = index;
            break;
        }
    }
    if insertion >= MAX_FIND_MATCHES {
        return;
    }

    let new_occupied = (occupied + 1).min(MAX_FIND_MATCHES);
    let mut index = new_occupied;
    while index > insertion + 1 {
        matches[index - 1] = matches[index - 2];
        index -= 1;
    }
    matches[insertion] = candidate;
    *count = new_occupied;
}

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
        for operation in OFFICIAL_ECON_OPERATIONS {
            if key == operation.key.as_bytes() {
                return Ok(econ_operation_ref(operation));
            }
        }
        Err(Status::UNKNOWN_OPERATION)
    }

    /// Looks up one fused economics operation by its stable pack-local ID.
    ///
    /// # Errors
    ///
    /// Returns [`Status::UNKNOWN_OPERATION`] when the ID is not fused.
    pub fn lookup_id(self, operation_id: u32) -> Result<OperationRef, Status> {
        for operation in OFFICIAL_ECON_OPERATIONS {
            if operation.id == operation_id {
                return Ok(econ_operation_ref(operation));
            }
        }
        Err(Status::UNKNOWN_OPERATION)
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

        let mut matches = empty_matches();
        let mut match_count = 0usize;
        for (index, operation) in OFFICIAL_ECON_OPERATIONS.iter().enumerate() {
            let mut best_rank = alias_rank(query, operation.key.as_bytes());
            for alias in ECON_ALIASES[index] {
                best_rank = best_rank.min(alias_rank(query, alias.as_bytes()));
            }
            if best_rank != u16::MAX {
                insert_match(
                    &mut matches,
                    &mut match_count,
                    Match {
                        operation: econ_operation_ref(operation),
                        rank: best_rank,
                    },
                );
            }
        }
        if match_count == 0 {
            return Err(Status::UNKNOWN_OPERATION);
        }
        if output.is_empty() {
            return Err(Status::BUFFER_TOO_SMALL);
        }

        let written = output.len().min(match_count);
        output[..written].copy_from_slice(&matches[..written]);
        Ok(written)
    }

    /// Returns the number of fused operations.
    #[must_use]
    pub const fn operation_count(self) -> usize {
        OFFICIAL_ECON_OPERATIONS.len()
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
    econ_operation_ref(&PED_MID_OPERATION)
}

const fn econ_operation_ref(operation: &'static OperationDecl) -> OperationRef {
    OperationRef {
        pack_slot: ECON_UNDERGRAD_PACK_SLOT,
        pack_id: ECON_UNDERGRAD_PACK_ID,
        provenance: ECON_UNDERGRAD_PROVENANCE,
        operation,
    }
}

fn insert_match(matches: &mut [Match; MAX_FIND_MATCHES], count: &mut usize, candidate: Match) {
    let occupied = (*count).min(MAX_FIND_MATCHES);
    let candidate_key = (candidate.rank, candidate.operation.operation.id);
    let mut insertion = occupied;
    for (index, existing) in matches[..occupied].iter().enumerate() {
        let existing_key = (existing.rank, existing.operation.operation.id);
        if candidate_key < existing_key {
            insertion = index;
            break;
        }
    }
    if insertion >= MAX_FIND_MATCHES {
        return;
    }

    let new_occupied = (occupied + 1).min(MAX_FIND_MATCHES);
    let mut index = new_occupied;
    while index > insertion + 1 {
        matches[index - 1] = matches[index - 2];
        index -= 1;
    }
    matches[insertion] = candidate;
    *count = new_occupied;
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
    use super::{
        empty_matches, empty_statistics_matches, FusedRegistry, StatisticsRegistry,
        ECON_UNDERGRAD_PACK_SLOT, STATISTICS_CORE_PACK_SLOT,
    };
    use exactscope_kernel::Status;

    #[test]
    fn exact_lookup_is_stable() {
        let registry = FusedRegistry::new();
        let operation = registry.lookup(b"econ.ped.mid").unwrap();
        assert_eq!(operation.pack_slot, ECON_UNDERGRAD_PACK_SLOT);
        assert_eq!(operation.operation.id, 301);
        assert_eq!(operation.operation.revision, 1);

        let deflator = registry.lookup(b"econ.gdp.deflator100").unwrap();
        assert_eq!(deflator.operation.id, 401);
        assert_eq!(deflator.operation.revision, 1);
        assert_eq!(registry.lookup_id(401).unwrap(), deflator);
        assert_eq!(registry.operation_count(), 15);

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
    fn economics_discovery_finds_non_ped_operations() {
        let registry = FusedRegistry::new();
        let mut matches = empty_matches();

        let count = registry.find(b"gdp deflator", &mut matches).unwrap();
        assert_eq!(count, 1);
        assert_eq!(matches[0].operation.operation.id, 401);
        assert_eq!(matches[0].operation.operation.key, "econ.gdp.deflator100");

        let count = registry.find(b"rule of 70", &mut matches).unwrap();
        assert_eq!(count, 1);
        assert_eq!(matches[0].operation.operation.id, 702);

        let count = registry.find(b"real interest rate", &mut matches).unwrap();
        assert_eq!(count, 2);
        assert_eq!(matches[0].operation.operation.id, 417);
        assert_eq!(matches[1].operation.operation.id, 418);
    }

    #[test]
    fn statistics_lookup_and_discovery_are_stable() {
        let registry = StatisticsRegistry::new();
        let mean = registry.lookup(b"stats.mean").unwrap();
        assert_eq!(mean.pack_slot, STATISTICS_CORE_PACK_SLOT);
        assert_eq!(mean.operation.id, 2);
        assert_eq!(
            registry.lookup_id(11).unwrap().operation.key,
            "stats.regression.linear"
        );
        assert_eq!(registry.operation_count(), 11);

        let mut matches = empty_statistics_matches();
        let count = registry.find(b"linear regression", &mut matches).unwrap();
        assert_eq!(count, 1);
        assert_eq!(matches[0].operation.operation.id, 11);

        let count = registry.find(b"sample variance", &mut matches).unwrap();
        assert_eq!(count, 1);
        assert_eq!(matches[0].operation.operation.id, 5);

        let count = registry.find(b"pearson correlation", &mut matches).unwrap();
        assert_eq!(count, 1);
        assert_eq!(matches[0].operation.operation.id, 10);
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
