//! Desktop/reference CLI for deterministic `ExactScope` factual recall.

use std::{env, fs, process::ExitCode};

use exactscope_kernel::Status;
use exactscope_pack::recall::{FactRecord, RecallIndex, RecallMatch, MAX_RECALL_MATCHES};
use serde_json::{json, Value};

#[derive(Debug)]
struct OwnedFact {
    id: String,
    evidence: String,
    source: String,
    revision: u32,
    aliases: Vec<String>,
}

fn string_field<'a>(value: &'a Value, key: &str) -> Result<&'a str, String> {
    value
        .get(key)
        .and_then(Value::as_str)
        .ok_or_else(|| format!("fact field {key} must be a string"))
}

fn load_facts(path: &str) -> Result<Vec<OwnedFact>, String> {
    let bytes = fs::read(path).map_err(|error| format!("cannot read fact pack: {error}"))?;
    let root: Value = serde_json::from_slice(&bytes)
        .map_err(|error| format!("invalid fact-pack JSON: {error}"))?;
    if root.get("format").and_then(Value::as_str) != Some("exactscope.fact-pack")
        || root.get("format_version").and_then(Value::as_str) != Some("0.1")
    {
        return Err("unsupported fact-pack format".to_owned());
    }
    let facts = root
        .get("facts")
        .and_then(Value::as_array)
        .ok_or_else(|| "fact-pack facts must be an array".to_owned())?;
    if facts.is_empty() || facts.len() > usize::from(u16::MAX) {
        return Err("fact-pack fact count is outside the recall profile".to_owned());
    }

    let mut output = Vec::with_capacity(facts.len());
    for fact in facts {
        let revision_u64 = fact
            .get("revision")
            .and_then(Value::as_u64)
            .ok_or_else(|| "fact revision must be an unsigned integer".to_owned())?;
        let revision =
            u32::try_from(revision_u64).map_err(|_| "fact revision exceeds u32".to_owned())?;
        if revision == 0 {
            return Err("fact revision must be positive".to_owned());
        }
        let aliases = fact
            .get("aliases")
            .and_then(Value::as_array)
            .ok_or_else(|| "fact aliases must be an array".to_owned())?;
        if aliases.is_empty() {
            return Err("fact aliases must be nonempty".to_owned());
        }
        let aliases = aliases
            .iter()
            .map(|alias| {
                alias
                    .as_str()
                    .map(str::to_owned)
                    .ok_or_else(|| "fact alias must be a string".to_owned())
            })
            .collect::<Result<Vec<_>, _>>()?;
        output.push(OwnedFact {
            id: string_field(fact, "id")?.to_owned(),
            evidence: string_field(fact, "evidence")?.to_owned(),
            source: string_field(fact, "source")?.to_owned(),
            revision,
            aliases,
        });
    }
    Ok(output)
}

fn run() -> Result<Value, String> {
    let mut args = env::args().skip(1);
    let pack_path = args
        .next()
        .ok_or_else(|| "usage: exactscope-recall <fact-pack.json> <query> [k]".to_owned())?;
    let query = args
        .next()
        .ok_or_else(|| "usage: exactscope-recall <fact-pack.json> <query> [k]".to_owned())?;
    let k = args
        .next()
        .map(|value| {
            value
                .parse::<usize>()
                .map_err(|_| "k must be an integer".to_owned())
        })
        .transpose()?
        .unwrap_or(2);
    if args.next().is_some() || !(1..=MAX_RECALL_MATCHES).contains(&k) {
        return Err(format!("k must be in 1..={MAX_RECALL_MATCHES}"));
    }

    let owned = load_facts(&pack_path)?;
    let alias_refs = owned
        .iter()
        .map(|fact| fact.aliases.iter().map(String::as_str).collect::<Vec<_>>())
        .collect::<Vec<_>>();
    let facts = owned
        .iter()
        .zip(alias_refs.iter())
        .map(|(fact, aliases)| FactRecord {
            id: &fact.id,
            evidence: &fact.evidence,
            source: &fact.source,
            revision: fact.revision,
            aliases,
        })
        .collect::<Vec<_>>();

    let mut matches: [Option<RecallMatch<'_>>; MAX_RECALL_MATCHES] = [None; MAX_RECALL_MATCHES];
    let result = RecallIndex::new(&facts).recall(query.as_bytes(), &mut matches[..k]);
    match result {
        Ok(count) => {
            let hits = matches[..count]
                .iter()
                .flatten()
                .map(|hit| {
                    json!({
                        "id": hit.fact.id,
                        "e": hit.fact.evidence,
                        "src": hit.fact.source,
                        "rev": hit.fact.revision,
                        "rank": hit.rank
                    })
                })
                .collect::<Vec<_>>();
            Ok(json!({"s": Status::OK.code(), "h": hits}))
        }
        Err(status) if status == Status::MISSING_INFORMATION => {
            Ok(json!({"s": status.code(), "h": []}))
        }
        Err(status) => Err(format!(
            "recall request failed with status {}",
            status.code()
        )),
    }
}

fn main() -> ExitCode {
    match run() {
        Ok(value) => match serde_json::to_string(&value) {
            Ok(text) => {
                println!("{text}");
                ExitCode::SUCCESS
            }
            Err(error) => {
                eprintln!("ExactScope recall: FAIL: cannot encode JSON: {error}");
                ExitCode::from(1)
            }
        },
        Err(error) => {
            eprintln!("ExactScope recall: FAIL: {error}");
            ExitCode::from(1)
        }
    }
}
