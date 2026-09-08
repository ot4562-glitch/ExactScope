#![no_std]
#![forbid(unsafe_code)]
#![doc = "Allocation-free immutable corpus search for `ExactScope` grounding v1."]

//! The runtime consumes a precompiled immutable grounding index and caller-provided
//! normalized query tokens. Unicode normalization, corpus construction, and model
//! inference stay outside this crate. Search itself is bounded, deterministic, and
//! uses only caller-owned scratch/output storage.

#[cfg(test)]
extern crate std;

use core::{cmp::Ordering, str};
use exactscope_kernel::Status;

/// Native immutable grounding-index magic.
pub const GROUNDING_INDEX_MAGIC: &[u8; 4] = b"XSGI";
/// Supported native grounding-index major version.
pub const GROUNDING_INDEX_MAJOR: u16 = 1;
/// Supported native grounding-index minor version.
pub const GROUNDING_INDEX_MINOR: u16 = 1;
/// Fixed v1 index header size.
pub const GROUNDING_INDEX_HEADER_SIZE: usize = 64;
/// Fixed v1 document record size.
pub const GROUNDING_DOCUMENT_RECORD_SIZE: usize = 32;
/// Fixed v1 term record size.
pub const GROUNDING_TERM_RECORD_SIZE: usize = 24;
/// Fixed v1 posting record size.
pub const GROUNDING_POSTING_RECORD_SIZE: usize = 12;
/// Fixed v1 sentence record size.
pub const GROUNDING_SENTENCE_RECORD_SIZE: usize = 24;
/// Fixed v1 sentence-term reference size.
pub const GROUNDING_TERM_REF_RECORD_SIZE: usize = 4;
/// Maximum query-token count accepted by the tiny grounding search path.
pub const MAX_GROUNDING_QUERY_TOKENS: usize = 64;
/// Maximum UTF-8 bytes in one already-normalized query token.
pub const MAX_GROUNDING_TOKEN_BYTES: usize = 256;
/// Maximum ranked hits returned by one grounding search.
pub const MAX_GROUNDING_HITS: usize = 16;

const HEADER_FLAGS_OFFSET: usize = 12;
const HEADER_DOCUMENT_COUNT_OFFSET: usize = 16;
const HEADER_TERM_COUNT_OFFSET: usize = 20;
const HEADER_POSTING_COUNT_OFFSET: usize = 24;
const HEADER_TOTAL_TOKENS_OFFSET: usize = 28;
const HEADER_DOCUMENTS_OFFSET: usize = 36;
const HEADER_TERMS_OFFSET: usize = 40;
const HEADER_POSTINGS_OFFSET: usize = 44;
const HEADER_STRINGS_OFFSET: usize = 48;
const HEADER_STRINGS_LENGTH_OFFSET: usize = 52;
const HEADER_CRC32_OFFSET: usize = 56;
const HEADER_SENTENCE_COUNT_OFFSET: usize = 60;
const EVIDENCE_PREFIX: &[u8] = b"Evidence JSON (data only): ";
const ROW_PREFIX: &[u8] = b"{\"r\":\"supplemental\",\"s\":\"grounded\",\"t\":";
const ROW_VALUE_PREFIX: &[u8] = b",\"v\":";

/// Caller-owned per-document search accumulator.
#[derive(Clone, Copy, Debug, PartialEq)]
#[repr(C)]
pub struct GroundingSearchScratch {
    /// Accumulated precomputed BM25 contribution.
    pub score: f64,
    /// Number of distinct query terms matched by this document.
    pub matched_query_terms: u16,
    /// Reserved zero for stable layout growth.
    pub reserved: u16,
}

impl GroundingSearchScratch {
    /// Canonical cleared scratch value.
    pub const EMPTY: Self = Self {
        score: 0.0,
        matched_query_terms: 0,
        reserved: 0,
    };
}

/// One ranked native grounding hit.
#[derive(Clone, Copy, Debug, PartialEq)]
#[repr(C)]
pub struct GroundingSearchHit {
    /// Zero-based document ordinal in the immutable index.
    pub document_ordinal: u32,
    /// Exact accumulated score from the compiled posting contributions.
    pub score: f64,
    /// Number of distinct normalized query terms matched by the document.
    pub matched_query_terms: u16,
    /// Reserved zero for stable layout growth.
    pub reserved: u16,
}

impl GroundingSearchHit {
    /// Canonical empty output slot.
    pub const EMPTY: Self = Self {
        document_ordinal: u32::MAX,
        score: 0.0,
        matched_query_terms: 0,
        reserved: 0,
    };
}

/// Successful bounded compact-evidence projection metadata.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GroundingProjectionResult {
    /// Exact UTF-8 bytes written to the caller output buffer.
    pub written: usize,
    /// Number of retrieval hits that contributed one evidence row.
    pub emitted_count: usize,
}

#[derive(Clone, Copy)]
struct ProjectionRow {
    document_ordinal: u32,
    sentence_ordinals: [u32; 4],
    sentence_count: u8,
}

impl ProjectionRow {
    const EMPTY: Self = Self {
        document_ordinal: u32::MAX,
        sentence_ordinals: [u32::MAX; 4],
        sentence_count: 0,
    };
}

/// Borrowed immutable document metadata/content from one grounding index.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GroundingDocument<'a> {
    /// Zero-based stable document ordinal.
    pub ordinal: u32,
    /// Stable document identity, sorted by UTF-8 bytes in the compiled index.
    pub id: &'a str,
    /// Optional human-readable title.
    pub title: &'a str,
    /// Complete source text for later deterministic evidence projection.
    pub text: &'a str,
    /// Token count used by the frozen BM25-v1 compiler.
    pub token_count: u32,
}

/// Borrowed immutable sentence metadata/content from one grounding index.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GroundingSentence<'a> {
    /// Global sentence ordinal in the immutable sentence table.
    pub ordinal: u32,
    /// Owning document ordinal.
    pub document_ordinal: u32,
    /// Zero-based sentence position within the document.
    pub position: u32,
    /// Exact trimmed sentence text used by the reference projector.
    pub text: &'a str,
}

#[derive(Clone, Copy)]
struct TermRecord<'a> {
    token: &'a [u8],
    first_posting: u32,
    posting_count: u32,
    idf: f64,
}

#[derive(Clone, Copy)]
struct SentenceRecord<'a> {
    document_ordinal: u32,
    position: u32,
    text: &'a str,
    first_term_ref: u32,
    term_ref_count: u32,
}

/// Validated zero-copy view over one immutable native grounding index.
#[derive(Clone, Copy)]
pub struct GroundingIndex<'a> {
    bytes: &'a [u8],
    document_count: u32,
    term_count: u32,
    posting_count: u32,
    sentence_count: u32,
    term_ref_count: u32,
    total_tokens: u64,
    documents_offset: usize,
    terms_offset: usize,
    postings_offset: usize,
    sentences_offset: usize,
    term_refs_offset: usize,
    strings_offset: usize,
    strings_length: usize,
}

impl<'a> GroundingIndex<'a> {
    /// Validates one complete `.xsgi` byte slice and returns a zero-copy index view.
    ///
    /// # Errors
    ///
    /// Returns stable pack/integrity/resource statuses on malformed, unsupported,
    /// corrupted, or platform-oversized input.
    pub fn parse(bytes: &'a [u8]) -> Result<Self, Status> {
        if bytes.len() < GROUNDING_INDEX_HEADER_SIZE {
            return Err(Status::PACK_INVALID);
        }
        if bytes.get(..4) != Some(GROUNDING_INDEX_MAGIC.as_slice()) {
            return Err(Status::PACK_INVALID);
        }
        let major = read_u16(bytes, 4)?;
        let minor = read_u16(bytes, 6)?;
        if major != GROUNDING_INDEX_MAJOR || minor != GROUNDING_INDEX_MINOR {
            return Err(Status::PACK_VERSION_UNSUPPORTED);
        }
        if read_u32(bytes, 8)? as usize != GROUNDING_INDEX_HEADER_SIZE
            || read_u32(bytes, HEADER_FLAGS_OFFSET)? != 0
        {
            return Err(Status::PACK_INVALID);
        }

        let document_count = read_u32(bytes, HEADER_DOCUMENT_COUNT_OFFSET)?;
        let term_count = read_u32(bytes, HEADER_TERM_COUNT_OFFSET)?;
        let posting_count = read_u32(bytes, HEADER_POSTING_COUNT_OFFSET)?;
        let sentence_count = read_u32(bytes, HEADER_SENTENCE_COUNT_OFFSET)?;
        let total_tokens = read_u64(bytes, HEADER_TOTAL_TOKENS_OFFSET)?;
        if document_count == 0 || sentence_count == 0 {
            return Err(Status::PACK_INVALID);
        }

        let documents_offset = usize_from_u32(read_u32(bytes, HEADER_DOCUMENTS_OFFSET)?)?;
        let terms_offset = usize_from_u32(read_u32(bytes, HEADER_TERMS_OFFSET)?)?;
        let postings_offset = usize_from_u32(read_u32(bytes, HEADER_POSTINGS_OFFSET)?)?;
        let strings_offset = usize_from_u32(read_u32(bytes, HEADER_STRINGS_OFFSET)?)?;
        let strings_length = usize_from_u32(read_u32(bytes, HEADER_STRINGS_LENGTH_OFFSET)?)?;

        if documents_offset != GROUNDING_INDEX_HEADER_SIZE {
            return Err(Status::PACK_INVALID);
        }
        let expected_terms = checked_table_end(
            documents_offset,
            usize_from_u32(document_count)?,
            GROUNDING_DOCUMENT_RECORD_SIZE,
        )?;
        let expected_postings = checked_table_end(
            expected_terms,
            usize_from_u32(term_count)?,
            GROUNDING_TERM_RECORD_SIZE,
        )?;
        let sentences_offset = checked_table_end(
            expected_postings,
            usize_from_u32(posting_count)?,
            GROUNDING_POSTING_RECORD_SIZE,
        )?;
        let term_refs_offset = checked_table_end(
            sentences_offset,
            usize_from_u32(sentence_count)?,
            GROUNDING_SENTENCE_RECORD_SIZE,
        )?;
        if strings_offset < term_refs_offset {
            return Err(Status::PACK_INVALID);
        }
        let term_ref_bytes = strings_offset - term_refs_offset;
        if term_ref_bytes % GROUNDING_TERM_REF_RECORD_SIZE != 0 {
            return Err(Status::PACK_INVALID);
        }
        let term_ref_count = u32::try_from(term_ref_bytes / GROUNDING_TERM_REF_RECORD_SIZE)
            .map_err(|_| Status::RESOURCE_LIMIT)?;
        let expected_end = strings_offset
            .checked_add(strings_length)
            .ok_or(Status::RESOURCE_LIMIT)?;
        if (terms_offset, postings_offset, expected_end)
            != (expected_terms, expected_postings, bytes.len())
        {
            return Err(Status::PACK_INVALID);
        }
        let expected_crc = read_u32(bytes, HEADER_CRC32_OFFSET)?;
        if crc32_iso_hdlc(&bytes[GROUNDING_INDEX_HEADER_SIZE..]) != expected_crc {
            return Err(Status::INTEGRITY_ERROR);
        }

        let index = Self {
            bytes,
            document_count,
            term_count,
            posting_count,
            sentence_count,
            term_ref_count,
            total_tokens,
            documents_offset,
            terms_offset,
            postings_offset,
            sentences_offset,
            term_refs_offset,
            strings_offset,
            strings_length,
        };
        index.validate_records()?;
        Ok(index)
    }

    /// Number of installed corpus documents.
    #[must_use]
    pub const fn document_count(self) -> u32 {
        self.document_count
    }

    /// Number of normalized indexed terms.
    #[must_use]
    pub const fn term_count(self) -> u32 {
        self.term_count
    }

    /// Number of term/document posting records.
    #[must_use]
    pub const fn posting_count(self) -> u32 {
        self.posting_count
    }

    /// Number of compiled baseline sentence records.
    #[must_use]
    pub const fn sentence_count(self) -> u32 {
        self.sentence_count
    }

    /// Number of sentence-to-term references used by native projection scoring.
    #[must_use]
    pub const fn term_ref_count(self) -> u32 {
        self.term_ref_count
    }

    /// Total indexed title/text tokens used by the frozen compiler.
    #[must_use]
    pub const fn total_tokens(self) -> u64 {
        self.total_tokens
    }

    /// Returns one borrowed immutable document.
    ///
    /// # Errors
    ///
    /// Returns [`Status::INVALID_REQUEST`] for an out-of-range ordinal.
    pub fn document(self, ordinal: u32) -> Result<GroundingDocument<'a>, Status> {
        if ordinal >= self.document_count {
            return Err(Status::INVALID_REQUEST);
        }
        self.document_unchecked(ordinal)
    }

    /// Returns one borrowed baseline sentence.
    ///
    /// # Errors
    ///
    /// Returns [`Status::INVALID_REQUEST`] for an out-of-range sentence ordinal.
    pub fn sentence(self, ordinal: u32) -> Result<GroundingSentence<'a>, Status> {
        if ordinal >= self.sentence_count {
            return Err(Status::INVALID_REQUEST);
        }
        let record = self.sentence_record(ordinal)?;
        Ok(GroundingSentence {
            ordinal,
            document_ordinal: record.document_ordinal,
            position: record.position,
            text: record.text,
        })
    }

    /// Returns the first global sentence ordinal and count for one document.
    ///
    /// # Errors
    ///
    /// Returns [`Status::INVALID_REQUEST`] for an out-of-range document ordinal.
    pub fn sentence_range(self, document_ordinal: u32) -> Result<(u32, u32), Status> {
        if document_ordinal >= self.document_count {
            return Err(Status::INVALID_REQUEST);
        }
        let mut low = 0u32;
        let mut high = self.sentence_count;
        while low < high {
            let middle = low + (high - low) / 2;
            if self.sentence_record(middle)?.document_ordinal < document_ordinal {
                low = middle + 1;
            } else {
                high = middle;
            }
        }
        let first = low;
        high = self.sentence_count;
        while low < high {
            let middle = low + (high - low) / 2;
            if self.sentence_record(middle)?.document_ordinal <= document_ordinal {
                low = middle + 1;
            } else {
                high = middle;
            }
        }
        let count = low.checked_sub(first).ok_or(Status::PACK_INVALID)?;
        if count == 0 {
            return Err(Status::PACK_INVALID);
        }
        Ok((first, count))
    }

    /// Searches with already-normalized query tokens using caller-owned storage.
    ///
    /// The tokenization contract is intentionally outside the tiny runtime. Callers
    /// must supply the same normalized tokens used by the index compiler. Duplicate
    /// tokens are ignored after their first occurrence, matching the reference path.
    ///
    /// # Errors
    ///
    /// Returns [`Status::BUFFER_TOO_SMALL`] when scratch/output storage is too small,
    /// [`Status::RESOURCE_LIMIT`] for oversized bounded inputs, and
    /// [`Status::INVALID_REQUEST`] for malformed token bytes.
    pub fn search(
        self,
        query_tokens: &[&[u8]],
        scratch: &mut [GroundingSearchScratch],
        output: &mut [GroundingSearchHit],
    ) -> Result<usize, Status> {
        if output.is_empty() || output.len() > MAX_GROUNDING_HITS {
            return Err(Status::BUFFER_TOO_SMALL);
        }
        let document_count = usize_from_u32(self.document_count)?;
        if scratch.len() < document_count {
            return Err(Status::BUFFER_TOO_SMALL);
        }
        if query_tokens.len() > MAX_GROUNDING_QUERY_TOKENS {
            return Err(Status::RESOURCE_LIMIT);
        }
        for slot in output.iter_mut() {
            *slot = GroundingSearchHit::EMPTY;
        }
        for cell in &mut scratch[..document_count] {
            *cell = GroundingSearchScratch::EMPTY;
        }
        if query_tokens.is_empty() {
            return Ok(0);
        }

        for (position, token) in query_tokens.iter().enumerate() {
            validate_query_token(token)?;
            if query_tokens[..position]
                .iter()
                .any(|previous| previous == token)
            {
                continue;
            }
            let Some(term) = self.find_term(token)? else {
                continue;
            };
            let end = term
                .first_posting
                .checked_add(term.posting_count)
                .ok_or(Status::PACK_INVALID)?;
            for posting_ordinal in term.first_posting..end {
                let (document_ordinal, contribution) = self.posting(posting_ordinal)?;
                let cell = scratch
                    .get_mut(usize_from_u32(document_ordinal)?)
                    .ok_or(Status::PACK_INVALID)?;
                cell.score += contribution;
                cell.matched_query_terms = cell
                    .matched_query_terms
                    .checked_add(1)
                    .ok_or(Status::RESOURCE_LIMIT)?;
            }
        }

        let mut count = 0usize;
        for (ordinal, cell) in scratch[..document_count].iter().enumerate() {
            if cell.score <= 0.0 {
                continue;
            }
            let candidate = GroundingSearchHit {
                document_ordinal: u32::try_from(ordinal).map_err(|_| Status::RESOURCE_LIMIT)?,
                score: cell.score,
                matched_query_terms: cell.matched_query_terms,
                reserved: 0,
            };
            insert_hit(output, &mut count, candidate);
        }
        Ok(count)
    }

    /// Projects ranked hits into the exact compact evidence bytes used by grounding v1.
    ///
    /// Query tokens must already satisfy the same normalization contract as [`Self::search`].
    /// The projection keeps sentence zero plus the best lexical sentences, preserves source
    /// order, and falls back to sentence zero when the full row would exceed `max_bytes`.
    ///
    /// # Errors
    ///
    /// Returns a stable malformed/resource/buffer status when bounded inputs are invalid.
    pub fn compact_evidence_projection(
        self,
        hits: &[GroundingSearchHit],
        query_tokens: &[&[u8]],
        max_bytes: usize,
        max_sentences_per_document: usize,
        output: &mut [u8],
    ) -> Result<Option<GroundingProjectionResult>, Status> {
        if max_bytes < 256 {
            return Err(Status::INVALID_REQUEST);
        }
        if !(1..=4).contains(&max_sentences_per_document) {
            return Err(Status::INVALID_REQUEST);
        }
        if hits.len() > MAX_GROUNDING_HITS || query_tokens.len() > MAX_GROUNDING_QUERY_TOKENS {
            return Err(Status::RESOURCE_LIMIT);
        }

        let mut query_term_ordinals = [u32::MAX; MAX_GROUNDING_QUERY_TOKENS];
        let query_term_count = self.query_term_ordinals(query_tokens, &mut query_term_ordinals)?;
        let query_terms = &query_term_ordinals[..query_term_count];
        let mut rows = [ProjectionRow::EMPTY; MAX_GROUNDING_HITS];
        let mut emitted_count = 0usize;
        let mut encoded_len = EVIDENCE_PREFIX
            .len()
            .checked_add(2)
            .ok_or(Status::RESOURCE_LIMIT)?;

        for hit in hits {
            if hit.document_ordinal >= self.document_count || hit.document_ordinal == u32::MAX {
                return Err(Status::INVALID_REQUEST);
            }
            let full = self.select_projection_sentences(
                hit.document_ordinal,
                query_terms,
                max_sentences_per_document,
            )?;
            let full_len = self.projection_row_len(&full)?;
            let separator = usize::from(emitted_count != 0);
            let full_total = encoded_len
                .checked_add(separator)
                .and_then(|value| value.checked_add(full_len))
                .ok_or(Status::RESOURCE_LIMIT)?;

            let accepted = if full_total <= max_bytes {
                Some((full, full_total))
            } else {
                let mut lead = ProjectionRow::EMPTY;
                lead.document_ordinal = hit.document_ordinal;
                lead.sentence_ordinals[0] = full.sentence_ordinals[0];
                lead.sentence_count = 1;
                let lead_len = self.projection_row_len(&lead)?;
                let lead_total = encoded_len
                    .checked_add(separator)
                    .and_then(|value| value.checked_add(lead_len))
                    .ok_or(Status::RESOURCE_LIMIT)?;
                (lead_total <= max_bytes).then_some((lead, lead_total))
            };

            if let Some((row, total)) = accepted {
                rows[emitted_count] = row;
                emitted_count += 1;
                encoded_len = total;
            }
        }

        if emitted_count == 0 {
            return Ok(None);
        }
        if output.len() < encoded_len {
            return Err(Status::BUFFER_TOO_SMALL);
        }
        let mut writer = ByteWriter::new(output);
        writer.write(EVIDENCE_PREFIX)?;
        writer.write(b"[")?;
        for (index, row) in rows[..emitted_count].iter().enumerate() {
            if index != 0 {
                writer.write(b",")?;
            }
            self.write_projection_row(*row, &mut writer)?;
        }
        writer.write(b"]")?;
        if writer.position != encoded_len {
            return Err(Status::INTERNAL_ERROR);
        }
        Ok(Some(GroundingProjectionResult {
            written: writer.position,
            emitted_count,
        }))
    }

    fn query_term_ordinals(
        self,
        query_tokens: &[&[u8]],
        output: &mut [u32; MAX_GROUNDING_QUERY_TOKENS],
    ) -> Result<usize, Status> {
        let mut count = 0usize;
        for token in query_tokens {
            validate_query_token(token)?;
            let Some((ordinal, _)) = self.find_term_entry(token)? else {
                continue;
            };
            if output[..count].contains(&ordinal) {
                continue;
            }
            let mut insertion = count;
            while insertion > 0 && output[insertion - 1] > ordinal {
                output[insertion] = output[insertion - 1];
                insertion -= 1;
            }
            output[insertion] = ordinal;
            count += 1;
        }
        Ok(count)
    }

    fn select_projection_sentences(
        self,
        document_ordinal: u32,
        query_terms: &[u32],
        max_sentences: usize,
    ) -> Result<ProjectionRow, Status> {
        let (first, count) = self.sentence_range(document_ordinal)?;
        let mut best_ordinals = [u32::MAX; 3];
        let mut best_scores = [0.0f64; 3];
        let mut best_positions = [u32::MAX; 3];
        let mut best_count = 0usize;
        let capacity = max_sentences.saturating_sub(1).min(3);

        for offset in 1..count {
            let ordinal = first.checked_add(offset).ok_or(Status::RESOURCE_LIMIT)?;
            let record = self.sentence_record(ordinal)?;
            let score = self.sentence_score(record, query_terms)?;
            let mut insertion = best_count.min(capacity);
            for index in 0..best_count.min(capacity) {
                // Exact equality is part of the frozen deterministic tie-break contract.
                #[allow(clippy::float_cmp)]
                if score > best_scores[index]
                    || (score == best_scores[index] && record.position < best_positions[index])
                {
                    insertion = index;
                    break;
                }
            }
            if insertion >= capacity {
                continue;
            }
            let new_count = (best_count + 1).min(capacity);
            let mut index = new_count;
            while index > insertion + 1 {
                best_ordinals[index - 1] = best_ordinals[index - 2];
                best_scores[index - 1] = best_scores[index - 2];
                best_positions[index - 1] = best_positions[index - 2];
                index -= 1;
            }
            best_ordinals[insertion] = ordinal;
            best_scores[insertion] = score;
            best_positions[insertion] = record.position;
            best_count = new_count;
        }

        let mut row = ProjectionRow::EMPTY;
        row.document_ordinal = document_ordinal;
        row.sentence_ordinals[0] = first;
        let selected_nonlead = best_count.min(capacity);
        if selected_nonlead > 0 {
            row.sentence_ordinals[1..=selected_nonlead]
                .copy_from_slice(&best_ordinals[..selected_nonlead]);
        }
        row.sentence_count =
            u8::try_from(selected_nonlead + 1).map_err(|_| Status::RESOURCE_LIMIT)?;
        let selected_count = usize::from(row.sentence_count);
        for index in 1..selected_count {
            let value = row.sentence_ordinals[index];
            let mut insertion = index;
            while insertion > 0 && row.sentence_ordinals[insertion - 1] > value {
                row.sentence_ordinals[insertion] = row.sentence_ordinals[insertion - 1];
                insertion -= 1;
            }
            row.sentence_ordinals[insertion] = value;
        }
        Ok(row)
    }

    fn sentence_score(
        self,
        record: SentenceRecord<'a>,
        query_terms: &[u32],
    ) -> Result<f64, Status> {
        let mut score = 0.0f64;
        let mut query_index = 0usize;
        let mut reference_index = 0u32;
        while query_index < query_terms.len() && reference_index < record.term_ref_count {
            let reference_ordinal = record
                .first_term_ref
                .checked_add(reference_index)
                .ok_or(Status::PACK_INVALID)?;
            let term_ordinal = self.term_ref(reference_ordinal)?;
            match query_terms[query_index].cmp(&term_ordinal) {
                Ordering::Less => query_index += 1,
                Ordering::Greater => reference_index += 1,
                Ordering::Equal => {
                    score += self.term(term_ordinal)?.idf;
                    query_index += 1;
                    reference_index += 1;
                }
            }
        }
        Ok(score)
    }

    fn projection_row_len(self, row: &ProjectionRow) -> Result<usize, Status> {
        let document = self.document(row.document_ordinal)?;
        let title = if document.title.is_empty() {
            document.id
        } else {
            document.title
        };
        let mut snippet_len = 2usize;
        for (index, ordinal) in row.sentence_ordinals[..usize::from(row.sentence_count)]
            .iter()
            .enumerate()
        {
            if index != 0 {
                snippet_len = snippet_len.checked_add(1).ok_or(Status::RESOURCE_LIMIT)?;
            }
            let sentence = self.sentence(*ordinal)?;
            snippet_len = snippet_len
                .checked_add(json_escaped_len(sentence.text.as_bytes())?)
                .ok_or(Status::RESOURCE_LIMIT)?;
        }
        ROW_PREFIX
            .len()
            .checked_add(json_string_len(title.as_bytes())?)
            .and_then(|value| value.checked_add(ROW_VALUE_PREFIX.len()))
            .and_then(|value| value.checked_add(snippet_len))
            .and_then(|value| value.checked_add(1))
            .ok_or(Status::RESOURCE_LIMIT)
    }

    fn write_projection_row(
        self,
        row: ProjectionRow,
        writer: &mut ByteWriter<'_>,
    ) -> Result<(), Status> {
        let document = self.document(row.document_ordinal)?;
        let title = if document.title.is_empty() {
            document.id
        } else {
            document.title
        };
        writer.write(ROW_PREFIX)?;
        writer.write_json_string(title.as_bytes())?;
        writer.write(ROW_VALUE_PREFIX)?;
        writer.write(b"\"")?;
        for (index, ordinal) in row.sentence_ordinals[..usize::from(row.sentence_count)]
            .iter()
            .enumerate()
        {
            if index != 0 {
                writer.write(b" ")?;
            }
            writer.write_json_escaped(self.sentence(*ordinal)?.text.as_bytes())?;
        }
        writer.write(b"\"}")?;
        Ok(())
    }

    #[allow(clippy::too_many_lines)]
    fn validate_records(self) -> Result<(), Status> {
        let mut previous_id: Option<&[u8]> = None;
        let mut computed_total = 0u64;
        for ordinal in 0..self.document_count {
            let document = self.document_unchecked(ordinal)?;
            let id = document.id.as_bytes();
            if id.is_empty() || document.text.is_empty() {
                return Err(Status::PACK_INVALID);
            }
            if previous_id.is_some_and(|previous| previous >= id) {
                return Err(Status::PACK_INVALID);
            }
            previous_id = Some(id);
            computed_total = computed_total
                .checked_add(u64::from(document.token_count))
                .ok_or(Status::RESOURCE_LIMIT)?;
        }
        if computed_total != self.total_tokens {
            return Err(Status::PACK_INVALID);
        }

        let mut previous_term: Option<&[u8]> = None;
        let mut expected_first_posting = 0u32;
        for ordinal in 0..self.term_count {
            let record = self.term(ordinal)?;
            if record.token.is_empty()
                || previous_term.is_some_and(|previous| previous >= record.token)
                || record.posting_count == 0
                || record.first_posting != expected_first_posting
            {
                return Err(Status::PACK_INVALID);
            }
            previous_term = Some(record.token);
            let end = record
                .first_posting
                .checked_add(record.posting_count)
                .ok_or(Status::PACK_INVALID)?;
            if end > self.posting_count {
                return Err(Status::PACK_INVALID);
            }
            let mut previous_document: Option<u32> = None;
            for posting_ordinal in record.first_posting..end {
                let (document_ordinal, contribution) = self.posting(posting_ordinal)?;
                if document_ordinal >= self.document_count
                    || previous_document.is_some_and(|previous| previous >= document_ordinal)
                    || !contribution.is_finite()
                    || contribution <= 0.0
                {
                    return Err(Status::PACK_INVALID);
                }
                previous_document = Some(document_ordinal);
            }
            expected_first_posting = end;
        }
        if expected_first_posting != self.posting_count {
            return Err(Status::PACK_INVALID);
        }

        let mut previous_document: Option<u32> = None;
        let mut expected_position = 0u32;
        let mut expected_first_term_ref = 0u32;
        for ordinal in 0..self.sentence_count {
            let record = self.sentence_record(ordinal)?;
            match previous_document {
                None => {
                    if record.document_ordinal != 0 || record.position != 0 {
                        return Err(Status::PACK_INVALID);
                    }
                }
                Some(document) if record.document_ordinal == document => {
                    if record.position != expected_position {
                        return Err(Status::PACK_INVALID);
                    }
                }
                Some(document) => {
                    if record.document_ordinal != document + 1 || record.position != 0 {
                        return Err(Status::PACK_INVALID);
                    }
                }
            }
            if record.first_term_ref != expected_first_term_ref || record.text.is_empty() {
                return Err(Status::PACK_INVALID);
            }
            let end = record
                .first_term_ref
                .checked_add(record.term_ref_count)
                .ok_or(Status::PACK_INVALID)?;
            if end > self.term_ref_count {
                return Err(Status::PACK_INVALID);
            }
            let mut previous_term_ref: Option<u32> = None;
            for reference_ordinal in record.first_term_ref..end {
                let term_ordinal = self.term_ref(reference_ordinal)?;
                if term_ordinal >= self.term_count
                    || previous_term_ref.is_some_and(|previous| previous >= term_ordinal)
                {
                    return Err(Status::PACK_INVALID);
                }
                previous_term_ref = Some(term_ordinal);
            }
            expected_first_term_ref = end;
            previous_document = Some(record.document_ordinal);
            expected_position = record
                .position
                .checked_add(1)
                .ok_or(Status::RESOURCE_LIMIT)?;
        }
        if previous_document != Some(self.document_count - 1)
            || expected_first_term_ref != self.term_ref_count
        {
            return Err(Status::PACK_INVALID);
        }
        Ok(())
    }

    fn document_unchecked(self, ordinal: u32) -> Result<GroundingDocument<'a>, Status> {
        let base = record_offset(
            self.documents_offset,
            usize_from_u32(ordinal)?,
            GROUNDING_DOCUMENT_RECORD_SIZE,
        )?;
        let id = self.string(read_u32(self.bytes, base)?, read_u32(self.bytes, base + 4)?)?;
        let title = self.string(
            read_u32(self.bytes, base + 8)?,
            read_u32(self.bytes, base + 12)?,
        )?;
        let text = self.string(
            read_u32(self.bytes, base + 16)?,
            read_u32(self.bytes, base + 20)?,
        )?;
        let token_count = read_u32(self.bytes, base + 24)?;
        if read_u32(self.bytes, base + 28)? != 0 {
            return Err(Status::PACK_INVALID);
        }
        Ok(GroundingDocument {
            ordinal,
            id: str::from_utf8(id).map_err(|_| Status::PACK_INVALID)?,
            title: str::from_utf8(title).map_err(|_| Status::PACK_INVALID)?,
            text: str::from_utf8(text).map_err(|_| Status::PACK_INVALID)?,
            token_count,
        })
    }

    fn term(self, ordinal: u32) -> Result<TermRecord<'a>, Status> {
        if ordinal >= self.term_count {
            return Err(Status::PACK_INVALID);
        }
        let base = record_offset(
            self.terms_offset,
            usize_from_u32(ordinal)?,
            GROUNDING_TERM_RECORD_SIZE,
        )?;
        let token = self.string(read_u32(self.bytes, base)?, read_u32(self.bytes, base + 4)?)?;
        str::from_utf8(token).map_err(|_| Status::PACK_INVALID)?;
        let first_posting = read_u32(self.bytes, base + 8)?;
        let posting_count = read_u32(self.bytes, base + 12)?;
        let idf = read_f64(self.bytes, base + 16)?;
        if !idf.is_finite() || idf <= 0.0 {
            return Err(Status::PACK_INVALID);
        }
        Ok(TermRecord {
            token,
            first_posting,
            posting_count,
            idf,
        })
    }

    fn sentence_record(self, ordinal: u32) -> Result<SentenceRecord<'a>, Status> {
        if ordinal >= self.sentence_count {
            return Err(Status::PACK_INVALID);
        }
        let base = record_offset(
            self.sentences_offset,
            usize_from_u32(ordinal)?,
            GROUNDING_SENTENCE_RECORD_SIZE,
        )?;
        let document_ordinal = read_u32(self.bytes, base)?;
        let position = read_u32(self.bytes, base + 4)?;
        let text_offset = read_u32(self.bytes, base + 8)?;
        let text_length = read_u32(self.bytes, base + 12)?;
        let first_term_ref = read_u32(self.bytes, base + 16)?;
        let term_ref_count = read_u32(self.bytes, base + 20)?;
        if document_ordinal >= self.document_count || text_length == 0 {
            return Err(Status::PACK_INVALID);
        }
        let (document_text_offset, document_text_length) =
            self.document_text_span(document_ordinal)?;
        let sentence_end = text_offset
            .checked_add(text_length)
            .ok_or(Status::PACK_INVALID)?;
        let document_end = document_text_offset
            .checked_add(document_text_length)
            .ok_or(Status::PACK_INVALID)?;
        if text_offset < document_text_offset || sentence_end > document_end {
            return Err(Status::PACK_INVALID);
        }
        let text = str::from_utf8(self.string(text_offset, text_length)?)
            .map_err(|_| Status::PACK_INVALID)?;
        Ok(SentenceRecord {
            document_ordinal,
            position,
            text,
            first_term_ref,
            term_ref_count,
        })
    }

    fn document_text_span(self, ordinal: u32) -> Result<(u32, u32), Status> {
        if ordinal >= self.document_count {
            return Err(Status::PACK_INVALID);
        }
        let base = record_offset(
            self.documents_offset,
            usize_from_u32(ordinal)?,
            GROUNDING_DOCUMENT_RECORD_SIZE,
        )?;
        Ok((
            read_u32(self.bytes, base + 16)?,
            read_u32(self.bytes, base + 20)?,
        ))
    }

    fn term_ref(self, ordinal: u32) -> Result<u32, Status> {
        if ordinal >= self.term_ref_count {
            return Err(Status::PACK_INVALID);
        }
        let base = record_offset(
            self.term_refs_offset,
            usize_from_u32(ordinal)?,
            GROUNDING_TERM_REF_RECORD_SIZE,
        )?;
        read_u32(self.bytes, base)
    }

    fn posting(self, ordinal: u32) -> Result<(u32, f64), Status> {
        if ordinal >= self.posting_count {
            return Err(Status::PACK_INVALID);
        }
        let base = record_offset(
            self.postings_offset,
            usize_from_u32(ordinal)?,
            GROUNDING_POSTING_RECORD_SIZE,
        )?;
        Ok((read_u32(self.bytes, base)?, read_f64(self.bytes, base + 4)?))
    }

    fn find_term(self, token: &[u8]) -> Result<Option<TermRecord<'a>>, Status> {
        Ok(self.find_term_entry(token)?.map(|(_, record)| record))
    }

    fn find_term_entry(self, token: &[u8]) -> Result<Option<(u32, TermRecord<'a>)>, Status> {
        let mut low = 0u32;
        let mut high = self.term_count;
        while low < high {
            let middle = low + (high - low) / 2;
            let record = self.term(middle)?;
            match record.token.cmp(token) {
                Ordering::Less => low = middle + 1,
                Ordering::Greater => high = middle,
                Ordering::Equal => return Ok(Some((middle, record))),
            }
        }
        Ok(None)
    }

    fn string(self, offset: u32, length: u32) -> Result<&'a [u8], Status> {
        let relative = usize_from_u32(offset)?;
        let length = usize_from_u32(length)?;
        let end = relative.checked_add(length).ok_or(Status::PACK_INVALID)?;
        if end > self.strings_length {
            return Err(Status::PACK_INVALID);
        }
        let start = self
            .strings_offset
            .checked_add(relative)
            .ok_or(Status::PACK_INVALID)?;
        self.bytes
            .get(start..start + length)
            .ok_or(Status::PACK_INVALID)
    }
}

struct ByteWriter<'a> {
    output: &'a mut [u8],
    position: usize,
}

impl<'a> ByteWriter<'a> {
    fn new(output: &'a mut [u8]) -> Self {
        Self {
            output,
            position: 0,
        }
    }

    fn write(&mut self, bytes: &[u8]) -> Result<(), Status> {
        let end = self
            .position
            .checked_add(bytes.len())
            .ok_or(Status::RESOURCE_LIMIT)?;
        let destination = self
            .output
            .get_mut(self.position..end)
            .ok_or(Status::BUFFER_TOO_SMALL)?;
        destination.copy_from_slice(bytes);
        self.position = end;
        Ok(())
    }

    fn write_json_string(&mut self, bytes: &[u8]) -> Result<(), Status> {
        self.write(b"\"")?;
        self.write_json_escaped(bytes)?;
        self.write(b"\"")
    }

    fn write_json_escaped(&mut self, bytes: &[u8]) -> Result<(), Status> {
        const HEX: &[u8; 16] = b"0123456789abcdef";
        for &byte in bytes {
            match byte {
                b'\"' => self.write(b"\\\"")?,
                b'\\' => self.write(b"\\\\")?,
                0x08 => self.write(b"\\b")?,
                b'\t' => self.write(b"\\t")?,
                b'\n' => self.write(b"\\n")?,
                0x0c => self.write(b"\\f")?,
                b'\r' => self.write(b"\\r")?,
                0x00..=0x1f => {
                    let escaped = [
                        b'\\',
                        b'u',
                        b'0',
                        b'0',
                        HEX[usize::from(byte >> 4)],
                        HEX[usize::from(byte & 0x0f)],
                    ];
                    self.write(&escaped)?;
                }
                _ => self.write(&[byte])?,
            }
        }
        Ok(())
    }
}

fn json_string_len(bytes: &[u8]) -> Result<usize, Status> {
    json_escaped_len(bytes)?
        .checked_add(2)
        .ok_or(Status::RESOURCE_LIMIT)
}

fn json_escaped_len(bytes: &[u8]) -> Result<usize, Status> {
    let mut length = 0usize;
    for &byte in bytes {
        let added = match byte {
            b'\"' | b'\\' | 0x08 | b'\t' | b'\n' | 0x0c | b'\r' => 2,
            0x00..=0x1f => 6,
            _ => 1,
        };
        length = length.checked_add(added).ok_or(Status::RESOURCE_LIMIT)?;
    }
    Ok(length)
}

fn validate_query_token(token: &[u8]) -> Result<(), Status> {
    if token.is_empty() {
        return Err(Status::INVALID_REQUEST);
    }
    if token.len() > MAX_GROUNDING_TOKEN_BYTES {
        return Err(Status::RESOURCE_LIMIT);
    }
    str::from_utf8(token).map_err(|_| Status::INVALID_REQUEST)?;
    if token.iter().any(u8::is_ascii_whitespace) {
        return Err(Status::INVALID_REQUEST);
    }
    Ok(())
}

fn insert_hit(output: &mut [GroundingSearchHit], count: &mut usize, candidate: GroundingSearchHit) {
    let occupied = (*count).min(output.len());
    let mut insertion = occupied;
    for (index, existing) in output[..occupied].iter().enumerate() {
        if hit_is_better(candidate, *existing) {
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
    output[insertion] = candidate;
    *count = new_occupied;
}

fn hit_is_better(left: GroundingSearchHit, right: GroundingSearchHit) -> bool {
    // Exact equality is required for bit-for-bit parity with the reference ranker.
    #[allow(clippy::float_cmp)]
    if left.score != right.score {
        return left.score > right.score;
    }
    if left.matched_query_terms != right.matched_query_terms {
        return left.matched_query_terms > right.matched_query_terms;
    }
    left.document_ordinal < right.document_ordinal
}

fn checked_table_end(start: usize, count: usize, record_size: usize) -> Result<usize, Status> {
    let bytes = count
        .checked_mul(record_size)
        .ok_or(Status::RESOURCE_LIMIT)?;
    start.checked_add(bytes).ok_or(Status::RESOURCE_LIMIT)
}

fn record_offset(start: usize, ordinal: usize, record_size: usize) -> Result<usize, Status> {
    let offset = ordinal
        .checked_mul(record_size)
        .ok_or(Status::RESOURCE_LIMIT)?;
    start.checked_add(offset).ok_or(Status::RESOURCE_LIMIT)
}

fn usize_from_u32(value: u32) -> Result<usize, Status> {
    usize::try_from(value).map_err(|_| Status::RESOURCE_LIMIT)
}

fn read_u16(bytes: &[u8], offset: usize) -> Result<u16, Status> {
    let raw = read_array::<2>(bytes, offset)?;
    Ok(u16::from_le_bytes(raw))
}

fn read_u32(bytes: &[u8], offset: usize) -> Result<u32, Status> {
    let raw = read_array::<4>(bytes, offset)?;
    Ok(u32::from_le_bytes(raw))
}

fn read_u64(bytes: &[u8], offset: usize) -> Result<u64, Status> {
    let raw = read_array::<8>(bytes, offset)?;
    Ok(u64::from_le_bytes(raw))
}

fn read_f64(bytes: &[u8], offset: usize) -> Result<f64, Status> {
    Ok(f64::from_bits(read_u64(bytes, offset)?))
}

fn read_array<const N: usize>(bytes: &[u8], offset: usize) -> Result<[u8; N], Status> {
    let end = offset.checked_add(N).ok_or(Status::PACK_INVALID)?;
    let slice = bytes.get(offset..end).ok_or(Status::PACK_INVALID)?;
    let mut output = [0u8; N];
    output.copy_from_slice(slice);
    Ok(output)
}

fn crc32_iso_hdlc(bytes: &[u8]) -> u32 {
    let mut crc = 0xffff_ffffu32;
    for &byte in bytes {
        crc ^= u32::from(byte);
        for _ in 0..8 {
            let mask = 0u32.wrapping_sub(crc & 1);
            crc = (crc >> 1) ^ (0xedb8_8320 & mask);
        }
    }
    !crc
}

#[cfg(test)]
mod tests {
    use super::{
        crc32_iso_hdlc, GroundingIndex, GroundingSearchHit, GroundingSearchScratch,
        GROUNDING_INDEX_HEADER_SIZE, GROUNDING_INDEX_MAGIC, MAX_GROUNDING_HITS,
    };
    use exactscope_kernel::Status;
    use std::vec::Vec;

    fn push_u16(out: &mut Vec<u8>, value: u16) {
        out.extend_from_slice(&value.to_le_bytes());
    }

    fn push_u32(out: &mut Vec<u8>, value: u32) {
        out.extend_from_slice(&value.to_le_bytes());
    }

    fn push_u64(out: &mut Vec<u8>, value: u64) {
        out.extend_from_slice(&value.to_le_bytes());
    }

    fn push_f64(out: &mut Vec<u8>, value: f64) {
        push_u64(out, value.to_bits());
    }

    fn fixture() -> Vec<u8> {
        let mut strings = Vec::new();
        let mut add = |value: &[u8]| {
            let offset = u32::try_from(strings.len()).unwrap();
            strings.extend_from_slice(value);
            (offset, u32::try_from(value.len()).unwrap())
        };
        let (a_id_o, a_id_l) = add(b"a");
        let (a_title_o, a_title_l) = add(b"A");
        let (a_text_o, a_text_l) = add(b"alpha beta");
        let (b_id_o, b_id_l) = add(b"b");
        let (b_title_o, b_title_l) = add(b"B");
        let (b_text_o, b_text_l) = add(b"beta beta");
        let (alpha_o, alpha_l) = add(b"alpha");
        let (beta_o, beta_l) = add(b"beta");

        let mut documents = Vec::new();
        for (id_o, id_l, title_o, title_l, text_o, text_l) in [
            (a_id_o, a_id_l, a_title_o, a_title_l, a_text_o, a_text_l),
            (b_id_o, b_id_l, b_title_o, b_title_l, b_text_o, b_text_l),
        ] {
            for value in [id_o, id_l, title_o, title_l, text_o, text_l, 2, 0] {
                push_u32(&mut documents, value);
            }
        }

        let mut terms = Vec::new();
        for (token_o, token_l, first, count, idf) in
            [(alpha_o, alpha_l, 0, 1, 1.0), (beta_o, beta_l, 1, 2, 0.5)]
        {
            for value in [token_o, token_l, first, count] {
                push_u32(&mut terms, value);
            }
            push_f64(&mut terms, idf);
        }

        let mut postings = Vec::new();
        for (document, score) in [(0, 2.0), (0, 1.0), (1, 3.0)] {
            push_u32(&mut postings, document);
            push_f64(&mut postings, score);
        }

        let mut sentences = Vec::new();
        for (document, position, text_offset, text_length, first_ref, ref_count) in [
            (0, 0, a_text_o, a_text_l, 0, 2),
            (1, 0, b_text_o, b_text_l, 2, 1),
        ] {
            for value in [
                document,
                position,
                text_offset,
                text_length,
                first_ref,
                ref_count,
            ] {
                push_u32(&mut sentences, value);
            }
        }
        let mut term_refs = Vec::new();
        for value in [0, 1, 1] {
            push_u32(&mut term_refs, value);
        }

        let documents_offset = GROUNDING_INDEX_HEADER_SIZE as u32;
        let terms_offset = documents_offset + u32::try_from(documents.len()).unwrap();
        let postings_offset = terms_offset + u32::try_from(terms.len()).unwrap();
        let strings_offset = postings_offset
            + u32::try_from(postings.len()).unwrap()
            + u32::try_from(sentences.len()).unwrap()
            + u32::try_from(term_refs.len()).unwrap();
        let mut payload = Vec::new();
        payload.extend_from_slice(&documents);
        payload.extend_from_slice(&terms);
        payload.extend_from_slice(&postings);
        payload.extend_from_slice(&sentences);
        payload.extend_from_slice(&term_refs);
        payload.extend_from_slice(&strings);

        let mut header = Vec::new();
        header.extend_from_slice(GROUNDING_INDEX_MAGIC);
        push_u16(&mut header, 1);
        push_u16(&mut header, 1);
        for value in [GROUNDING_INDEX_HEADER_SIZE as u32, 0, 2, 2, 3] {
            push_u32(&mut header, value);
        }
        push_u64(&mut header, 4);
        for value in [
            documents_offset,
            terms_offset,
            postings_offset,
            strings_offset,
            u32::try_from(strings.len()).unwrap(),
            crc32_iso_hdlc(&payload),
            2,
        ] {
            push_u32(&mut header, value);
        }
        assert_eq!(header.len(), GROUNDING_INDEX_HEADER_SIZE);
        header.extend_from_slice(&payload);
        header
    }

    #[test]
    fn fixture_parses_and_exposes_documents() {
        let bytes = fixture();
        let index = GroundingIndex::parse(&bytes).unwrap();
        assert_eq!(index.document_count(), 2);
        assert_eq!(index.term_count(), 2);
        assert_eq!(index.posting_count(), 3);
        assert_eq!(index.sentence_count(), 2);
        assert_eq!(index.term_ref_count(), 3);
        assert_eq!(index.total_tokens(), 4);
        let document = index.document(1).unwrap();
        assert_eq!(
            (document.id, document.title, document.text),
            ("b", "B", "beta beta")
        );
        assert_eq!(index.sentence_range(0).unwrap(), (0, 1));
        assert_eq!(index.sentence_range(1).unwrap(), (1, 1));
        assert_eq!(index.sentence(0).unwrap().text, "alpha beta");
        assert_eq!(index.sentence(1).unwrap().text, "beta beta");
    }

    #[test]
    fn search_matches_score_then_term_count_then_document_order() {
        let bytes = fixture();
        let index = GroundingIndex::parse(&bytes).unwrap();
        let mut scratch = [GroundingSearchScratch::EMPTY; 2];
        let mut output = [GroundingSearchHit::EMPTY; MAX_GROUNDING_HITS];
        let count = index
            .search(
                &[b"alpha".as_slice(), b"beta".as_slice()],
                &mut scratch,
                &mut output[..2],
            )
            .unwrap();
        assert_eq!(count, 2);
        assert_eq!(output[0].document_ordinal, 0);
        assert_eq!(output[0].score, 3.0);
        assert_eq!(output[0].matched_query_terms, 2);
        assert_eq!(output[1].document_ordinal, 1);
        assert_eq!(output[1].score, 3.0);
        assert_eq!(output[1].matched_query_terms, 1);

        let count = index
            .search(&[b"beta".as_slice()], &mut scratch, &mut output[..2])
            .unwrap();
        assert_eq!(count, 2);
        assert_eq!(output[0].document_ordinal, 1);
        assert_eq!(output[1].document_ordinal, 0);
    }

    #[test]
    fn duplicate_query_tokens_do_not_double_count() {
        let bytes = fixture();
        let index = GroundingIndex::parse(&bytes).unwrap();
        let mut scratch = [GroundingSearchScratch::EMPTY; 2];
        let mut output = [GroundingSearchHit::EMPTY; 2];
        index
            .search(
                &[b"beta".as_slice(), b"beta".as_slice()],
                &mut scratch,
                &mut output,
            )
            .unwrap();
        assert_eq!(output[0].score, 3.0);
        assert_eq!(output[0].matched_query_terms, 1);
    }

    #[test]
    fn corruption_and_bounds_fail_closed() {
        let mut bytes = fixture();
        let last = bytes.len() - 1;
        bytes[last] ^= 1;
        assert_eq!(
            GroundingIndex::parse(&bytes).err(),
            Some(Status::INTEGRITY_ERROR)
        );

        let bytes = fixture();
        let index = GroundingIndex::parse(&bytes).unwrap();
        let mut too_small = [GroundingSearchScratch::EMPTY; 1];
        let mut output = [GroundingSearchHit::EMPTY; 1];
        assert_eq!(
            index.search(&[b"beta".as_slice()], &mut too_small, &mut output),
            Err(Status::BUFFER_TOO_SMALL)
        );
        let mut scratch = [GroundingSearchScratch::EMPTY; 2];
        assert_eq!(
            index.search(&[b"bad token".as_slice()], &mut scratch, &mut output),
            Err(Status::INVALID_REQUEST)
        );
    }
}
