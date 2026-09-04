#![allow(clippy::std_instead_of_core)]
#![doc = "Command-line compiler and hot-set generator for `ExactScope` build-time artifacts."]

use std::{
    env,
    ffi::{OsStr, OsString},
    fs,
    path::Path,
    process,
};

fn main() {
    if let Err(error) = run() {
        eprintln!("exactscope-packc: {error}");
        process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = env::args_os();
    let _program = args.next();
    let first = args.next().ok_or(usage())?;
    if first == OsStr::new("hotset") {
        run_hotset(args)
    } else {
        run_pack_compile(first, args)
    }
}

fn run_pack_compile(
    input: OsString,
    mut args: impl Iterator<Item = OsString>,
) -> Result<(), Box<dyn std::error::Error>> {
    let output = args.next().ok_or(usage())?;
    if args.next().is_some() {
        return Err(usage().into());
    }

    let source = fs::read_to_string(input)?;
    let compiled = exactscope_packc::compile_source(&source)?;
    fs::write(output, compiled)?;
    Ok(())
}

fn run_hotset(mut args: impl Iterator<Item = OsString>) -> Result<(), Box<dyn std::error::Error>> {
    let manifest_path = args.next().ok_or(hotset_usage())?;
    let output_dir = args.next().ok_or(hotset_usage())?;
    if args.next().is_some() {
        return Err(hotset_usage().into());
    }

    let manifest_text = fs::read_to_string(&manifest_path)?;
    let manifest = exactscope_packc::parse_hotset_manifest(&manifest_text)?;
    let manifest_path = Path::new(&manifest_path);
    let base = manifest_path.parent().unwrap_or_else(|| Path::new("."));

    let mut loaded = Vec::with_capacity(manifest.source_paths.len());
    for relative in &manifest.source_paths {
        let path = base.join(relative);
        loaded.push((relative.clone(), fs::read_to_string(path)?));
    }
    let sources = loaded
        .iter()
        .map(|(label, source)| exactscope_packc::HotsetSource { label, source })
        .collect::<Vec<_>>();
    let bundle = exactscope_packc::generate_hotset(
        &manifest.name,
        &sources,
        &manifest.operation_keys,
        manifest.include_find,
    )?;

    let output_dir = Path::new(&output_dir);
    fs::create_dir_all(output_dir)?;
    fs::write(output_dir.join("catalog.json"), bundle.catalog_json)?;
    fs::write(
        output_dir.join("binding-sha256.txt"),
        format!("{}\n", bundle.binding_sha256),
    )?;
    fs::write(
        output_dir.join("xs-eval.tool.json"),
        bundle.xs_eval_tool_json,
    )?;
    fs::write(output_dir.join("xs-eval.gbnf"), bundle.xs_eval_gbnf)?;
    fs::write(
        output_dir.join("prompt-fragment.txt"),
        bundle.prompt_fragment,
    )?;

    write_optional(
        output_dir.join("xs-find.tool.json"),
        bundle.xs_find_tool_json,
    )?;
    write_optional(output_dir.join("xs-find.gbnf"), bundle.xs_find_gbnf)?;
    Ok(())
}

fn write_optional(path: impl AsRef<Path>, content: Option<String>) -> Result<(), std::io::Error> {
    let path = path.as_ref();
    if let Some(content) = content {
        fs::write(path, content)
    } else if path.exists() {
        fs::remove_file(path)
    } else {
        Ok(())
    }
}

fn usage() -> &'static str {
    "usage: exactscope-packc <source.xsp.json> <output.xsp>\n       exactscope-packc hotset <hotset.json> <output-dir>"
}

fn hotset_usage() -> &'static str {
    "usage: exactscope-packc hotset <hotset.json> <output-dir>"
}
