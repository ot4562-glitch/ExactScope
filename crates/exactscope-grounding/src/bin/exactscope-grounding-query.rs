//! Batch parity/diagnostic CLI for the native grounding-index search core.

use exactscope_grounding::{
    GroundingIndex, GroundingSearchHit, GroundingSearchScratch, MAX_GROUNDING_HITS,
};
use std::{env, fs, process};

fn fail(message: &str) -> ! {
    eprintln!("exactscope-grounding-query: {message}");
    process::exit(1)
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 4 {
        fail("usage: exactscope-grounding-query <index.xsgi> <queries.tsv> <top-k>");
    }
    let top_k: usize = args[3].parse().unwrap_or_else(|_| fail("invalid top-k"));
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
    let mut output = [GroundingSearchHit::EMPTY; MAX_GROUNDING_HITS];

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
        let count = index
            .search(&tokens, &mut scratch, &mut output[..top_k])
            .unwrap_or_else(|status| {
                fail(&format!(
                    "search failed on line {} with status {}",
                    line_number + 1,
                    status.code()
                ))
            });
        print!("{query_id}\t");
        for (position, hit) in output[..count].iter().enumerate() {
            if position != 0 {
                print!(";");
            }
            let document = index
                .document(hit.document_ordinal)
                .unwrap_or_else(|status| {
                    fail(&format!(
                        "document lookup failed with status {}",
                        status.code()
                    ))
                });
            print!(
                "{}|{:016x}|{}",
                document.id,
                hit.score.to_bits(),
                hit.matched_query_terms
            );
        }
        println!();
    }
}
