#![allow(clippy::std_instead_of_core)]
#![doc = "Command-line compiler for canonical `ExactScope` `.xsp` packs."]

use std::{env, fs, process};

fn main() {
    if let Err(error) = run() {
        eprintln!("exactscope-packc: {error}");
        process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = env::args_os();
    let _program = args.next();
    let input = args
        .next()
        .ok_or("usage: exactscope-packc <source.xsp.json> <output.xsp>")?;
    let output = args
        .next()
        .ok_or("usage: exactscope-packc <source.xsp.json> <output.xsp>")?;
    if args.next().is_some() {
        return Err("usage: exactscope-packc <source.xsp.json> <output.xsp>".into());
    }

    let source = fs::read_to_string(input)?;
    let compiled = exactscope_packc::compile_source(&source)?;
    fs::write(output, compiled)?;
    Ok(())
}
