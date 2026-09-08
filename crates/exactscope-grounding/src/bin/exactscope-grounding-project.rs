//! Batch parity/diagnostic CLI for native grounding search + compact projection.

use exactscope_grounding::{
    GroundingIndex, GroundingSearchHit, GroundingSearchScratch, MAX_GROUNDING_HITS,
};
use std::{env, fs, process};

fn fail(message: &str) -> ! {
    eprintln!("exactscope-grounding-project: {message}");
    process::exit(1)
}

fn hex(bytes: &[u8]) -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    let mut output = String::with_capacity(bytes.len() * 2);
    for &byte in bytes {
        output.push(char::from(DIGITS[usize::from(byte >> 4)]));
        output.push(char::from(DIGITS[usize::from(byte & 0x0f)]));
    }
    output
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 6 {
        fail("usage: exactscope-grounding-project <index.xsgi> <queries.tsv> <top-k> <max-bytes> <max-sentences>");
    }
    let top_k: usize = args[3].parse().unwrap_or_else(|_| fail("invalid top-k"));
    let max_bytes: usize = args[4]
        .parse()
        .unwrap_or_else(|_| fail("invalid max-bytes"));
    let max_sentences: usize = args[5]
        .parse()
        .unwrap_or_else(|_| fail("invalid max-sentences"));
    if !(1..=MAX_GROUNDING_HITS).contains(&top_k) {
        fail("top-k out of range");
    }

    let bytes =
        fs::read(&args[1]).unwrap_or_else(|error| fail(&format!("cannot read index: {error}")));
    let index = GroundingIndex::parse(&bytes)
        .unwrap_or_else(|status| fail(&format!("index rejected with status {}", status.code())));
    let queries = fs::read_to_string(&args[2])
        .unwrap_or_else(|error| fail(&format!("cannot read queries: {error}")));
    let mut scratch = vec![GroundingSearchScratch::EMPTY; index.document_count() as usize];
    let mut hits = [GroundingSearchHit::EMPTY; MAX_GROUNDING_HITS];
    let mut projection = vec![0u8; max_bytes];

    for (line_number, line) in queries.lines().enumerate() {
        if line.is_empty() {
            continue;
        }
        let mut fields = line.split('\t');
        let query_id = fields.next().unwrap_or("");
        if query_id.is_empty() {
            fail(&format!("empty query id on line {}", line_number + 1));
        }
        let tokens: Vec<&[u8]> = fields.map(str::as_bytes).collect();
        let hit_count = index
            .search(&tokens, &mut scratch, &mut hits[..top_k])
            .unwrap_or_else(|status| {
                fail(&format!(
                    "search failed on line {} with status {}",
                    line_number + 1,
                    status.code()
                ))
            });
        let result = index
            .compact_evidence_projection(
                &hits[..hit_count],
                &tokens,
                max_bytes,
                max_sentences,
                &mut projection,
            )
            .unwrap_or_else(|status| {
                fail(&format!(
                    "projection failed on line {} with status {}",
                    line_number + 1,
                    status.code()
                ))
            });
        match result {
            Some(result) => println!("{query_id}\t{}", hex(&projection[..result.written])),
            None => println!("{query_id}\t"),
        }
    }
}
