#![allow(clippy::std_instead_of_core)]
#![doc = "Host-side `ExactScope` Tiny JSON bridge for conformance and benchmark tooling."]

use std::{
    env,
    io::{self, Read, Write},
    process,
};

fn main() {
    if let Err(error) = run() {
        eprintln!("exactscope-core: {error}");
        process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = env::args();
    let _program = args.next();
    let mode = args
        .next()
        .ok_or("usage: exactscope-core <eval|find|request>")?;
    if args.next().is_some() {
        return Err("usage: exactscope-core <eval|find|request>".into());
    }

    let mut input = Vec::new();
    io::stdin().read_to_end(&mut input)?;
    let mut output = [0_u8; exactscope_tinyjson::MAX_TINY_JSON_RESPONSE_BYTES];
    let result = match mode.as_str() {
        "eval" => exactscope_tinyjson::eval(&input, &mut output),
        "find" => exactscope_tinyjson::find(&input, &mut output),
        "request" => exactscope_tinyjson::request(&input, &mut output),
        _ => return Err("usage: exactscope-core <eval|find|request>".into()),
    };

    let length = usize::try_from(result.written_or_required)?;
    if length > output.len() {
        return Err(format!("response requires {length} bytes").into());
    }
    io::stdout().write_all(&output[..length])?;
    io::stdout().write_all(b"\n")?;
    Ok(())
}
