//! Deterministic zero-allocation factual recall for small-model grounding.
//!
//! The recall engine is deliberately not a language model and does not synthesize
//! answers. A model or host supplies a short retrieval query; `ExactScope` returns
//! only fact records that were explicitly installed in a reviewed fact pack.
//! Missing evidence is a typed miss rather than an invitation to guess.

use exactscope_kernel::Status;

/// Maximum normalized query size for the first recall profile.
pub const MAX_RECALL_QUERY_BYTES: usize = 192;
/// Maximum number of recall hits intended for the tiny-model hot path.
pub const MAX_RECALL_MATCHES: usize = 4;

/// One immutable factual record supplied by a reviewed fact pack.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct FactRecord<'a> {
    /// Stable fact identity. Pack compilers should sort records by this field.
    pub id: &'a str,
    /// Compact evidence statement the model may use verbatim as grounding.
    pub evidence: &'a str,
    /// Stable source/provenance identifier, not an inferred citation.
    pub source: &'a str,
    /// Monotonic semantic/content revision within the source pack.
    pub revision: u32,
    /// Normalized retrieval aliases/keyword phrases for this fact.
    ///
    /// Aliases are UTF-8, lowercase for ASCII letters, punctuation-separated,
    /// and single-space normalized. Non-ASCII bytes are preserved exactly.
    pub aliases: &'a [&'a str],
}

/// One deterministic factual recall result.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RecallMatch<'a> {
    /// Matched fact record.
    pub fact: &'a FactRecord<'a>,
    /// Deterministic lexical rank; smaller is better.
    pub rank: u16,
    /// Stable source-pack order, used only as a tie breaker.
    pub fact_index: u16,
}

/// Borrowed immutable fact index.
#[derive(Clone, Copy, Debug)]
pub struct RecallIndex<'a> {
    facts: &'a [FactRecord<'a>],
}

impl<'a> RecallIndex<'a> {
    /// Creates a recall index over an immutable, already-validated fact slice.
    #[must_use]
    pub const fn new(facts: &'a [FactRecord<'a>]) -> Self {
        Self { facts }
    }

    /// Returns the number of installed facts.
    #[must_use]
    pub const fn fact_count(self) -> usize {
        self.facts.len()
    }

    /// Recalls up to `output.len()` deterministic matches for a short query.
    ///
    /// The engine performs no semantic repair, embedding inference, remote I/O,
    /// or answer synthesis. A no-hit result is [`Status::MISSING_INFORMATION`].
    ///
    /// # Errors
    ///
    /// Returns a stable malformed/resource/missing-information status when the
    /// query or output violates the bounded recall contract.
    pub fn recall(
        self,
        query: &[u8],
        output: &mut [Option<RecallMatch<'a>>],
    ) -> Result<usize, Status> {
        if query.is_empty() || query.len() > MAX_RECALL_QUERY_BYTES {
            return Err(Status::INVALID_REQUEST);
        }
        if output.is_empty() || output.len() > MAX_RECALL_MATCHES {
            return Err(Status::BUFFER_TOO_SMALL);
        }
        if core::str::from_utf8(query).is_err() {
            return Err(Status::INVALID_REQUEST);
        }

        let mut normalized = [0u8; MAX_RECALL_QUERY_BYTES];
        let normalized_len = normalize_recall_query(query, &mut normalized)?;
        let normalized_query = &normalized[..normalized_len];
        if normalized_query.is_empty() {
            return Err(Status::INVALID_REQUEST);
        }

        for slot in output.iter_mut() {
            *slot = None;
        }

        let mut count = 0usize;
        for (index, fact) in self.facts.iter().enumerate() {
            let fact_index = u16::try_from(index).map_err(|_| Status::RESOURCE_LIMIT)?;
            let rank = fact_rank(query, normalized_query, fact);
            if rank == u16::MAX {
                continue;
            }
            insert_match(
                output,
                &mut count,
                RecallMatch {
                    fact,
                    rank,
                    fact_index,
                },
            );
        }

        if count == 0 {
            return Err(Status::MISSING_INFORMATION);
        }
        Ok(count)
    }
}

fn fact_rank(raw_query: &[u8], query: &[u8], fact: &FactRecord<'_>) -> u16 {
    if raw_query == fact.id.as_bytes() {
        return 0;
    }

    let mut best = u16::MAX;
    for alias in fact.aliases {
        let alias = alias.as_bytes();
        if query == alias {
            best = best.min(5);
            continue;
        }
        if token_prefix(alias, query) {
            best = best.min(10);
            continue;
        }
        if all_query_tokens_present(query, alias) {
            best = best.min(30);
            continue;
        }
        if all_query_tokens_present(alias, query) {
            best = best.min(40);
        }
    }
    best
}

fn insert_match<'a>(
    output: &mut [Option<RecallMatch<'a>>],
    count: &mut usize,
    candidate: RecallMatch<'a>,
) {
    let occupied = (*count).min(output.len());
    let candidate_key = (candidate.rank, candidate.fact_index);
    let mut insertion = occupied;
    for (index, existing) in output[..occupied].iter().enumerate() {
        let Some(existing) = existing else {
            insertion = index;
            break;
        };
        if candidate_key < (existing.rank, existing.fact_index) {
            insertion = index;
            break;
        }
    }
    if insertion >= output.len() {
        return;
    }

    let new_occupied = (occupied + 1).min(output.len());
    let mut index = new_occupied;
    while index > insertion + 1 {
        output[index - 1] = output[index - 2];
        index -= 1;
    }
    output[insertion] = Some(candidate);
    *count = new_occupied;
}

fn normalize_recall_query(
    input: &[u8],
    output: &mut [u8; MAX_RECALL_QUERY_BYTES],
) -> Result<usize, Status> {
    let mut written = 0usize;
    let mut pending_space = false;

    for &byte in input {
        let normalized = match byte {
            b'A'..=b'Z' => byte + (b'a' - b'A'),
            b'a'..=b'z' | b'0'..=b'9' | 0x80..=0xff => byte,
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

    while written > 0 && output[written - 1] == b' ' {
        written -= 1;
    }
    Ok(written)
}

fn token_prefix(alias: &[u8], query: &[u8]) -> bool {
    alias.starts_with(query)
        && (alias.len() == query.len() || alias.get(query.len()) == Some(&b' '))
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
            // One-byte ASCII fragments are too weak for safe factual recall.
            if (token.len() < 2 && token[0].is_ascii()) || !contains_token(alias, token) {
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
        let left_ok = start == 0 || haystack[start - 1] == b' ';
        let right_ok = end == haystack.len() || haystack[end] == b' ';
        if left_ok && right_ok {
            return true;
        }
    }
    false
}

#[cfg(test)]
mod tests {
    use super::{FactRecord, RecallIndex, RecallMatch, MAX_RECALL_MATCHES};
    use exactscope_kernel::Status;

    const FACTS: [FactRecord<'static>; 5] = [
        FactRecord {
            id: "demo.orbit.period",
            evidence: "Project Aster's orbital period is 37 hours.",
            source: "demo-pack@1",
            revision: 2,
            aliases: &["aster orbital period", "project aster orbit period"],
        },
        FactRecord {
            id: "demo.orbit.altitude",
            evidence: "Project Aster's nominal orbital altitude is 620 km.",
            source: "demo-pack@1",
            revision: 1,
            aliases: &["aster orbital altitude", "project aster orbit altitude"],
        },
        FactRecord {
            id: "demo.author",
            evidence: "The fictional handbook Red Glass was written by Mira Venn.",
            source: "demo-pack@1",
            revision: 1,
            aliases: &["red glass author", "red glass writer"],
        },
        FactRecord {
            id: "demo.korean.capital",
            evidence: "테스트 국가 아람의 수도는 누리다.",
            source: "demo-pack-ko@1",
            revision: 1,
            aliases: &["아람 수도", "아람의 수도"],
        },
        FactRecord {
            id: "demo.serial",
            evidence: "Unit Kestrel-7 uses service code QX-4917.",
            source: "demo-pack@1",
            revision: 3,
            aliases: &["kestrel 7 service code", "unit kestrel service code"],
        },
    ];

    fn output() -> [Option<RecallMatch<'static>>; MAX_RECALL_MATCHES] {
        [None; MAX_RECALL_MATCHES]
    }

    #[test]
    fn exact_fact_id_is_highest_precision() {
        let mut out = output();
        let count = RecallIndex::new(&FACTS)
            .recall(b"demo.author", &mut out)
            .unwrap();
        assert_eq!(count, 1);
        assert_eq!(out[0].unwrap().fact.id, "demo.author");
        assert_eq!(out[0].unwrap().rank, 0);
    }

    #[test]
    fn keyword_recall_returns_grounded_fact_without_synthesis() {
        let mut out = output();
        let count = RecallIndex::new(&FACTS)
            .recall(b"ASTER ORBITAL PERIOD", &mut out)
            .unwrap();
        assert_eq!(count, 1);
        let hit = out[0].unwrap();
        assert_eq!(
            hit.fact.evidence,
            "Project Aster's orbital period is 37 hours."
        );
        assert_eq!(hit.fact.revision, 2);
    }

    #[test]
    fn similar_distractors_are_separated_by_required_tokens() {
        let mut out = output();
        let count = RecallIndex::new(&FACTS)
            .recall(b"aster altitude", &mut out)
            .unwrap();
        assert_eq!(count, 1);
        assert_eq!(out[0].unwrap().fact.id, "demo.orbit.altitude");
    }

    #[test]
    fn unknown_fact_is_a_typed_miss_not_a_guess() {
        let mut out = output();
        assert_eq!(
            RecallIndex::new(&FACTS).recall(b"aster launch date", &mut out),
            Err(Status::MISSING_INFORMATION)
        );
        assert!(out.iter().all(Option::is_none));
    }

    #[test]
    fn utf8_keyword_recall_supports_korean_aliases() {
        let mut out = output();
        let count = RecallIndex::new(&FACTS)
            .recall("아람 수도".as_bytes(), &mut out)
            .unwrap();
        assert_eq!(count, 1);
        assert_eq!(out[0].unwrap().fact.id, "demo.korean.capital");
    }

    #[test]
    fn output_and_query_bounds_fail_closed() {
        let mut empty: [Option<RecallMatch<'static>>; 0] = [];
        assert_eq!(
            RecallIndex::new(&FACTS).recall(b"red glass author", &mut empty),
            Err(Status::BUFFER_TOO_SMALL)
        );

        let mut out = output();
        assert_eq!(
            RecallIndex::new(&FACTS).recall(&[0xff, 0xfe], &mut out),
            Err(Status::INVALID_REQUEST)
        );
    }
}
