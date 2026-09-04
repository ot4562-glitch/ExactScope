#![allow(clippy::std_instead_of_core)]

use std::{collections::BTreeMap, error::Error, fmt};

use exactscope_kernel::{
    OperationDecl, OFFICIAL_ECON_OPERATIONS, SEMANTIC_COUNT, SEMANTIC_CURRENCY_AMOUNT,
    SEMANTIC_ELASTICITY, SEMANTIC_INDEX, SEMANTIC_NUMBER, SEMANTIC_PRICE, SEMANTIC_PROBABILITY,
    SEMANTIC_QUANTITY, SEMANTIC_RATE_PERCENT, SEMANTIC_RATE_RATIO, SEMANTIC_TIME_PERIODS,
};
use exactscope_pack::{ECON_UNDERGRAD_PACK_ID, ECON_UNDERGRAD_VERSION};
use serde_json::{json, Map, Value};

use crate::{compile_source, CompileError};

const HOTSET_SOURCE_FORMAT: &str = "exactscope.hotset.source";
const HOTSET_FORMAT: &str = "exactscope.hotset";
const HOTSET_VERSION: &str = "0.1";
const MAX_HOTSET_OPERATIONS: usize = 32;

/// One reviewed scope-pack source supplied to the hot-set generator.
#[derive(Clone, Copy, Debug)]
pub struct HotsetSource<'a> {
    /// Stable source label, normally the repository-relative source path.
    pub label: &'a str,
    /// Complete scope-pack source JSON.
    pub source: &'a str,
}

/// Parsed build-time manifest for reproducible hot-set generation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct HotsetManifest {
    /// Stable hot-set name.
    pub name: String,
    /// Scope-pack source paths, interpreted by the CLI relative to the manifest file.
    pub source_paths: Vec<String>,
    /// Built-in fused pack identifiers made available to the generator.
    pub fused_packs: Vec<String>,
    /// Canonical operation keys in the desired hot-set order.
    pub operation_keys: Vec<String>,
    /// Whether the generated bundle includes the optional discovery tool and grammar.
    pub include_find: bool,
}

/// Reproducible AI-integration assets generated from reviewed pack sources.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct HotsetBundle {
    /// SHA-256 of the canonical pack/operation binding payload.
    pub binding_sha256: String,
    /// Digest-bound compact catalog used by hosts and benchmarks.
    pub catalog_json: String,
    /// `OpenAI`-compatible direct `xs_eval` tool definition.
    pub xs_eval_tool_json: String,
    /// llama.cpp-compatible GBNF for direct hot-set evaluation.
    pub xs_eval_gbnf: String,
    /// Compact model policy fragment.
    pub prompt_fragment: String,
    /// Optional `OpenAI`-compatible `xs_find` fallback definition.
    pub xs_find_tool_json: Option<String>,
    /// Optional GBNF for `xs_find` fallback requests.
    pub xs_find_gbnf: Option<String>,
}

/// Hot-set generation failure.
#[derive(Debug)]
pub enum HotsetError {
    /// JSON could not be decoded.
    Json(serde_json::Error),
    /// A referenced scope-pack source failed the canonical pack compiler.
    Compile(CompileError),
    /// Hot-set metadata is invalid or cannot be represented by the current adapter profile.
    Invalid(String),
}

impl fmt::Display for HotsetError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Json(error) => write!(formatter, "invalid hot-set JSON: {error}"),
            Self::Compile(error) => write!(formatter, "scope-pack compilation failed: {error}"),
            Self::Invalid(message) => write!(formatter, "invalid hot set: {message}"),
        }
    }
}

impl Error for HotsetError {}

impl From<serde_json::Error> for HotsetError {
    fn from(value: serde_json::Error) -> Self {
        Self::Json(value)
    }
}

impl From<CompileError> for HotsetError {
    fn from(value: CompileError) -> Self {
        Self::Compile(value)
    }
}

#[derive(Clone, Debug)]
struct PackBinding {
    label: String,
    id: String,
    version: String,
    binding_kind: String,
    binding_sha256: String,
}

#[derive(Clone, Debug)]
struct OperationBinding {
    key: String,
    revision: u64,
    signature: String,
    method: String,
    pack_id: String,
    pack_version: String,
    pack_binding_sha256: String,
    inputs: Vec<InputBinding>,
}

#[derive(Clone, Debug)]
struct InputBinding {
    name: String,
    shape: String,
    semantic: String,
}

/// Parses a deterministic hot-set source manifest.
///
/// # Errors
///
/// Returns [`HotsetError`] for malformed JSON, an unsupported manifest version,
/// duplicate keys/paths, or an operation count outside the bounded v0.1 range.
pub fn parse_hotset_manifest(source: &str) -> Result<HotsetManifest, HotsetError> {
    let root: Value = serde_json::from_str(source)?;
    let object = root
        .as_object()
        .ok_or_else(|| HotsetError::Invalid("manifest root must be an object".to_owned()))?;
    if required_string(object, "format")? != HOTSET_SOURCE_FORMAT
        || required_string(object, "format_version")? != HOTSET_VERSION
    {
        return Err(HotsetError::Invalid(
            "unsupported hot-set source format/version".to_owned(),
        ));
    }

    let name = required_string(object, "name")?.to_owned();
    validate_name(&name)?;
    let source_paths = optional_string_array(object, "sources")?;
    let fused_packs = optional_string_array(object, "fused_packs")?;
    let operation_keys = string_array(object, "operations")?;
    if source_paths.is_empty() && fused_packs.is_empty() {
        return Err(HotsetError::Invalid(
            "at least one scope-pack source or fused pack is required".to_owned(),
        ));
    }
    ensure_unique(&source_paths, "scope-pack source path")?;
    ensure_unique(&fused_packs, "fused pack")?;
    for fused_pack in &fused_packs {
        if fused_pack != "econ-undergrad" {
            return Err(HotsetError::Invalid(format!(
                "unsupported fused pack {fused_pack}; v0.1 model-facing hot sets currently support econ-undergrad"
            )));
        }
    }
    validate_operation_keys(&operation_keys)?;

    let include_find = object.get("include_find").map_or(Ok(false), |value| {
        value
            .as_bool()
            .ok_or_else(|| HotsetError::Invalid("include_find must be a boolean".to_owned()))
    })?;

    Ok(HotsetManifest {
        name,
        source_paths,
        fused_packs,
        operation_keys,
        include_find,
    })
}

/// Generates digest-bound hot-set metadata, `OpenAI`-compatible tool assets,
/// and `llama.cpp` GBNF from canonical scope-pack sources.
///
/// The current Tiny JSON direct-eval adapter accepts scalar decimal strings.
/// Selecting a vector operation therefore fails closed instead of generating a
/// misleading model schema. Typed/TinyWire vector adapters remain separate.
///
/// # Errors
///
/// Returns [`HotsetError`] if a source pack does not compile, a selected key is
/// missing/ambiguous, metadata is malformed, or a selected operation is not
/// compatible with the scalar Tiny JSON direct-eval profile.
pub fn generate_hotset(
    name: &str,
    sources: &[HotsetSource<'_>],
    operation_keys: &[String],
    include_find: bool,
) -> Result<HotsetBundle, HotsetError> {
    generate_hotset_with_fused(name, sources, &[], operation_keys, include_find)
}

/// Generates a hot set from reviewed scope-pack sources and/or supported fused registries.
///
/// # Errors
///
/// Returns [`HotsetError`] when any input registry/source is invalid, ambiguous,
/// or incompatible with the scalar model-facing adapter profile.
#[allow(clippy::too_many_lines)]
pub fn generate_hotset_with_fused(
    name: &str,
    sources: &[HotsetSource<'_>],
    fused_packs: &[String],
    operation_keys: &[String],
    include_find: bool,
) -> Result<HotsetBundle, HotsetError> {
    validate_name(name)?;
    validate_operation_keys(operation_keys)?;
    if sources.is_empty() && fused_packs.is_empty() {
        return Err(HotsetError::Invalid(
            "at least one scope-pack source or fused pack is required".to_owned(),
        ));
    }

    let mut pack_bindings = Vec::with_capacity(sources.len() + fused_packs.len());
    let mut operation_map = BTreeMap::<String, OperationBinding>::new();

    for source in sources {
        let root: Value = serde_json::from_str(source.source)?;
        let root_object = root.as_object().ok_or_else(|| {
            HotsetError::Invalid(format!(
                "{}: scope-pack root must be an object",
                source.label
            ))
        })?;
        if required_string(root_object, "format")? != "exactscope.scopepack.source"
            || required_string(root_object, "format_version")? != "0.1"
        {
            return Err(HotsetError::Invalid(format!(
                "{}: unsupported scope-pack source format/version",
                source.label
            )));
        }
        let pack = required_object(root_object, "pack")?;
        let pack_id = required_string(pack, "id")?.to_owned();
        let pack_version = required_string(pack, "version")?.to_owned();
        let compiled = compile_source(source.source)?;
        let pack_binding_sha256 = sha256_hex(&compiled);
        pack_bindings.push(PackBinding {
            label: source.label.to_owned(),
            id: pack_id.clone(),
            version: pack_version.clone(),
            binding_kind: "compiled_xsp_sha256".to_owned(),
            binding_sha256: pack_binding_sha256.clone(),
        });

        let operations = required_array(root_object, "operations")?;
        for operation in operations {
            let operation = operation.as_object().ok_or_else(|| {
                HotsetError::Invalid(format!("{}: operation must be an object", source.label))
            })?;
            let key = required_string(operation, "key")?.to_owned();
            let revision = required_u64(operation, "revision")?;
            let method = required_string(operation, "method")?.to_owned();
            let inputs = required_array(operation, "inputs")?
                .iter()
                .map(parse_input_binding)
                .collect::<Result<Vec<_>, _>>()?;
            let signature = format!(
                "{key}({})",
                inputs
                    .iter()
                    .map(|input| input.name.as_str())
                    .collect::<Vec<_>>()
                    .join(",")
            );
            let binding = OperationBinding {
                key: key.clone(),
                revision,
                signature,
                method,
                pack_id: pack_id.clone(),
                pack_version: pack_version.clone(),
                pack_binding_sha256: pack_binding_sha256.clone(),
                inputs,
            };
            if operation_map.insert(key.clone(), binding).is_some() {
                return Err(HotsetError::Invalid(format!(
                    "operation key {key} is ambiguous across supplied sources"
                )));
            }
        }
    }

    for fused_pack in fused_packs {
        if fused_pack != "econ-undergrad" {
            return Err(HotsetError::Invalid(format!(
                "unsupported fused pack {fused_pack}"
            )));
        }
        let pack_binding_sha256 = fused_econ_digest()?;
        pack_bindings.push(PackBinding {
            label: "fused:econ-undergrad".to_owned(),
            id: ECON_UNDERGRAD_PACK_ID.to_owned(),
            version: ECON_UNDERGRAD_VERSION.to_owned(),
            binding_kind: "fused_registry_sha256".to_owned(),
            binding_sha256: pack_binding_sha256.clone(),
        });
        for operation in OFFICIAL_ECON_OPERATIONS {
            let binding = fused_operation_binding(operation, &pack_binding_sha256)?;
            let key = binding.key.clone();
            if operation_map.insert(key.clone(), binding).is_some() {
                return Err(HotsetError::Invalid(format!(
                    "operation key {key} is ambiguous across supplied sources/fused packs"
                )));
            }
        }
    }

    let mut selected = Vec::with_capacity(operation_keys.len());
    for key in operation_keys {
        let operation = operation_map.get(key).ok_or_else(|| {
            HotsetError::Invalid(format!("selected operation {key} was not found"))
        })?;
        for input in &operation.inputs {
            if input.shape != "scalar" {
                return Err(HotsetError::Invalid(format!(
                    "selected operation {} uses {} input {}; the current Tiny JSON direct-eval hot-set profile is scalar-only",
                    operation.key, input.shape, input.name
                )));
            }
        }
        selected.push(operation.clone());
    }

    let referenced_pack_ids = selected
        .iter()
        .map(|operation| operation.pack_id.as_str())
        .collect::<std::collections::BTreeSet<_>>();
    let packs_json = pack_bindings
        .iter()
        .filter(|pack| referenced_pack_ids.contains(pack.id.as_str()))
        .map(|pack| {
            json!({
                "id": pack.id,
                "version": pack.version,
                "binding_kind": pack.binding_kind,
                "binding_sha256": pack.binding_sha256,
                "source": pack.label,
            })
        })
        .collect::<Vec<_>>();
    let operations_json = selected.iter().map(operation_json).collect::<Vec<_>>();

    let binding_payload = json!({
        "abi": "1.0",
        "packs": packs_json,
        "operations": operations_json,
    });
    let binding_bytes = serde_json::to_vec(&binding_payload)?;
    let binding_sha256 = sha256_hex(&binding_bytes);
    let catalog = json!({
        "format": HOTSET_FORMAT,
        "format_version": HOTSET_VERSION,
        "name": name,
        "binding_sha256": binding_sha256,
        "abi": "1.0",
        "packs": binding_payload["packs"].clone(),
        "operations": binding_payload["operations"].clone(),
    });

    let xs_eval_tool = eval_tool_json(operation_keys);
    let xs_find_tool = include_find.then(find_tool_json);

    Ok(HotsetBundle {
        binding_sha256,
        catalog_json: pretty_json(&catalog)?,
        xs_eval_tool_json: pretty_json(&xs_eval_tool)?,
        xs_eval_gbnf: eval_gbnf(&selected),
        prompt_fragment: prompt_fragment(),
        xs_find_tool_json: xs_find_tool.as_ref().map(pretty_json).transpose()?,
        xs_find_gbnf: include_find.then(find_gbnf),
    })
}

fn parse_input_binding(value: &Value) -> Result<InputBinding, HotsetError> {
    let object = value
        .as_object()
        .ok_or_else(|| HotsetError::Invalid("operation input must be an object".to_owned()))?;
    Ok(InputBinding {
        name: required_string(object, "name")?.to_owned(),
        shape: required_string(object, "shape")?.to_owned(),
        semantic: required_string(object, "semantic")?.to_owned(),
    })
}

fn fused_operation_binding(
    operation: &'static OperationDecl,
    pack_binding_sha256: &str,
) -> Result<OperationBinding, HotsetError> {
    let inputs = operation
        .inputs
        .iter()
        .map(|input| {
            Ok(InputBinding {
                name: input.name.to_owned(),
                shape: "scalar".to_owned(),
                semantic: semantic_name(input.semantic_kind)?.to_owned(),
            })
        })
        .collect::<Result<Vec<_>, HotsetError>>()?;
    Ok(OperationBinding {
        key: operation.key.to_owned(),
        revision: u64::from(operation.revision),
        signature: operation.signature.to_owned(),
        method: operation.method.to_owned(),
        pack_id: ECON_UNDERGRAD_PACK_ID.to_owned(),
        pack_version: ECON_UNDERGRAD_VERSION.to_owned(),
        pack_binding_sha256: pack_binding_sha256.to_owned(),
        inputs,
    })
}

fn fused_econ_digest() -> Result<String, HotsetError> {
    let operations = OFFICIAL_ECON_OPERATIONS
        .iter()
        .map(|operation| {
            let inputs = operation
                .inputs
                .iter()
                .map(|input| {
                    Ok(json!({
                        "name": input.name,
                        "shape": "scalar",
                        "semantic": semantic_name(input.semantic_kind)?,
                    }))
                })
                .collect::<Result<Vec<_>, HotsetError>>()?;
            Ok(json!({
                "op": operation.key,
                "revision": operation.revision,
                "sig": operation.signature,
                "method": operation.method,
                "args": inputs,
            }))
        })
        .collect::<Result<Vec<_>, HotsetError>>()?;
    let payload = json!({
        "abi": "1.0",
        "pack_id": ECON_UNDERGRAD_PACK_ID,
        "version": ECON_UNDERGRAD_VERSION,
        "operations": operations,
    });
    Ok(sha256_hex(&serde_json::to_vec(&payload)?))
}

fn semantic_name(kind: u8) -> Result<&'static str, HotsetError> {
    match kind {
        SEMANTIC_NUMBER => Ok("number"),
        SEMANTIC_COUNT => Ok("count"),
        SEMANTIC_CURRENCY_AMOUNT => Ok("currency_amount"),
        SEMANTIC_PRICE => Ok("price"),
        SEMANTIC_QUANTITY => Ok("quantity"),
        SEMANTIC_RATE_PERCENT => Ok("rate_percent"),
        SEMANTIC_RATE_RATIO => Ok("rate_ratio"),
        SEMANTIC_INDEX => Ok("index"),
        SEMANTIC_TIME_PERIODS => Ok("time_periods"),
        SEMANTIC_PROBABILITY => Ok("probability"),
        SEMANTIC_ELASTICITY => Ok("elasticity"),
        other => Err(HotsetError::Invalid(format!(
            "unknown semantic kind {other} in fused registry"
        ))),
    }
}

fn operation_json(operation: &OperationBinding) -> Value {
    let args = operation
        .inputs
        .iter()
        .map(|input| {
            json!({
                "name": input.name,
                "shape": input.shape,
                "semantic": input.semantic,
            })
        })
        .collect::<Vec<_>>();
    json!({
        "op": operation.key,
        "revision": operation.revision,
        "sig": operation.signature,
        "method": operation.method,
        "pack_id": operation.pack_id,
        "pack_version": operation.pack_version,
        "pack_binding_sha256": operation.pack_binding_sha256,
        "args": args,
    })
}

fn eval_tool_json(operation_keys: &[String]) -> Value {
    json!({
        "type": "function",
        "function": {
            "name": "xs_eval",
            "description": "Evaluate one deterministic ExactScope operation from the bound hot set. Pass exact base-10 decimal arguments as strings in the declared signature order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "op": {
                        "type": "string",
                        "enum": operation_keys,
                    },
                    "a": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 0,
                        "maxItems": 12,
                    }
                },
                "required": ["op", "a"],
                "additionalProperties": false,
            }
        }
    })
}

fn find_tool_json() -> Value {
    json!({
        "type": "function",
        "function": {
            "name": "xs_find",
            "description": "Find an installed deterministic ExactScope operation when the canonical operation key is not already known.",
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {"type": "string"},
                    "n": {"type": "integer", "minimum": 1, "maximum": 5}
                },
                "required": ["q", "n"],
                "additionalProperties": false,
            }
        }
    })
}

fn eval_gbnf(operations: &[OperationBinding]) -> String {
    let choices = (0..operations.len())
        .map(|index| format!("op_{index}"))
        .collect::<Vec<_>>()
        .join(" | ");
    let mut grammar = format!("root ::= ws ({choices}) ws\n");
    for (index, operation) in operations.iter().enumerate() {
        let escaped_key = escape_gbnf_literal(&operation.key);
        let mut line = format!(
            r#"op_{index} ::= "{{" ws "\"op\"" ws ":" ws "\"{escaped_key}\"" ws "," ws "\"a\"" ws ":" ws "[" ws "#
        );
        for argument_index in 0..operation.inputs.len() {
            if argument_index != 0 {
                line.push_str("ws \",\" ws ");
            }
            line.push_str("decimal_string ");
        }
        line.push_str(r#"ws "]" ws "}""#);
        line.push('\n');
        grammar.push_str(&line);
    }
    grammar.push_str(
        r#"decimal_string ::= "\"" "-"? ("0" | [1-9] [0-9]*) ("." [0-9]+)? ([eE] [+-]? [0-9]+)? "\""
ws ::= [ \t\n\r]*
"#,
    );
    grammar
}

fn find_gbnf() -> String {
    r#"root ::= ws "{" ws "\"q\"" ws ":" ws query ws "," ws "\"n\"" ws ":" ws [1-5] ws "}" ws
query ::= "\"" [A-Za-z0-9 _./:+-]* "\""
ws ::= [ \t\n\r]*
"#
    .to_owned()
}

fn prompt_fragment() -> String {
    concat!(
        "Use ExactScope for supported deterministic quantitative calculations. ",
        "Prefer a canonical operation key from the bound hot set and call xs_eval directly. ",
        "Pass exact base-10 strings in signature order. Never invent missing values or methods. ",
        "Do not recompute returned values; preserve ExactScope errors instead of guessing.\n"
    )
    .to_owned()
}

fn escape_gbnf_literal(value: &str) -> String {
    value.replace('\\', "\\\\").replace('"', "\\\"")
}

fn pretty_json(value: &Value) -> Result<String, HotsetError> {
    let mut output = serde_json::to_string_pretty(value)?;
    output.push('\n');
    Ok(output)
}

fn sha256_hex(bytes: &[u8]) -> String {
    let digest = sha256(bytes);
    let mut output = String::with_capacity(64);
    for byte in digest {
        use fmt::Write as _;
        write!(&mut output, "{byte:02x}").expect("writing into String cannot fail");
    }
    output
}

#[allow(clippy::many_single_char_names)]
fn sha256(bytes: &[u8]) -> [u8; 32] {
    const INITIAL: [u32; 8] = [
        0x6a09_e667,
        0xbb67_ae85,
        0x3c6e_f372,
        0xa54f_f53a,
        0x510e_527f,
        0x9b05_688c,
        0x1f83_d9ab,
        0x5be0_cd19,
    ];
    let mut state = INITIAL;
    let mut chunks = bytes.chunks_exact(64);
    for chunk in &mut chunks {
        compress_sha256(&mut state, chunk);
    }

    let remainder = chunks.remainder();
    let mut tail = [0_u8; 128];
    tail[..remainder.len()].copy_from_slice(remainder);
    tail[remainder.len()] = 0x80;
    let tail_len = if remainder.len() < 56 { 64 } else { 128 };
    let bit_len = u64::try_from(bytes.len())
        .expect("hot-set inputs fit in u64")
        .checked_mul(8)
        .expect("hot-set input bit length fits in u64");
    tail[tail_len - 8..tail_len].copy_from_slice(&bit_len.to_be_bytes());
    for chunk in tail[..tail_len].chunks_exact(64) {
        compress_sha256(&mut state, chunk);
    }

    let mut output = [0_u8; 32];
    for (index, word) in state.iter().enumerate() {
        output[index * 4..index * 4 + 4].copy_from_slice(&word.to_be_bytes());
    }
    output
}

#[allow(clippy::many_single_char_names, clippy::too_many_lines)]
fn compress_sha256(state: &mut [u32; 8], block: &[u8]) {
    const K: [u32; 64] = [
        0x428a_2f98,
        0x7137_4491,
        0xb5c0_fbcf,
        0xe9b5_dba5,
        0x3956_c25b,
        0x59f1_11f1,
        0x923f_82a4,
        0xab1c_5ed5,
        0xd807_aa98,
        0x1283_5b01,
        0x2431_85be,
        0x550c_7dc3,
        0x72be_5d74,
        0x80de_b1fe,
        0x9bdc_06a7,
        0xc19b_f174,
        0xe49b_69c1,
        0xefbe_4786,
        0x0fc1_9dc6,
        0x240c_a1cc,
        0x2de9_2c6f,
        0x4a74_84aa,
        0x5cb0_a9dc,
        0x76f9_88da,
        0x983e_5152,
        0xa831_c66d,
        0xb003_27c8,
        0xbf59_7fc7,
        0xc6e0_0bf3,
        0xd5a7_9147,
        0x06ca_6351,
        0x1429_2967,
        0x27b7_0a85,
        0x2e1b_2138,
        0x4d2c_6dfc,
        0x5338_0d13,
        0x650a_7354,
        0x766a_0abb,
        0x81c2_c92e,
        0x9272_2c85,
        0xa2bf_e8a1,
        0xa81a_664b,
        0xc24b_8b70,
        0xc76c_51a3,
        0xd192_e819,
        0xd699_0624,
        0xf40e_3585,
        0x106a_a070,
        0x19a4_c116,
        0x1e37_6c08,
        0x2748_774c,
        0x34b0_bcb5,
        0x391c_0cb3,
        0x4ed8_aa4a,
        0x5b9c_ca4f,
        0x682e_6ff3,
        0x748f_82ee,
        0x78a5_636f,
        0x84c8_7814,
        0x8cc7_0208,
        0x90be_fffa,
        0xa450_6ceb,
        0xbef9_a3f7,
        0xc671_78f2,
    ];

    let mut w = [0_u32; 64];
    for (index, chunk) in block.chunks_exact(4).take(16).enumerate() {
        w[index] = u32::from_be_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]);
    }
    for index in 16..64 {
        let s0 =
            w[index - 15].rotate_right(7) ^ w[index - 15].rotate_right(18) ^ (w[index - 15] >> 3);
        let s1 =
            w[index - 2].rotate_right(17) ^ w[index - 2].rotate_right(19) ^ (w[index - 2] >> 10);
        w[index] = w[index - 16]
            .wrapping_add(s0)
            .wrapping_add(w[index - 7])
            .wrapping_add(s1);
    }

    let mut a = state[0];
    let mut b = state[1];
    let mut c = state[2];
    let mut d = state[3];
    let mut e = state[4];
    let mut f = state[5];
    let mut g = state[6];
    let mut h = state[7];

    for index in 0..64 {
        let sigma1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
        let choose = (e & f) ^ ((!e) & g);
        let temp1 = h
            .wrapping_add(sigma1)
            .wrapping_add(choose)
            .wrapping_add(K[index])
            .wrapping_add(w[index]);
        let sigma0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
        let majority = (a & b) ^ (a & c) ^ (b & c);
        let temp2 = sigma0.wrapping_add(majority);

        h = g;
        g = f;
        f = e;
        e = d.wrapping_add(temp1);
        d = c;
        c = b;
        b = a;
        a = temp1.wrapping_add(temp2);
    }

    state[0] = state[0].wrapping_add(a);
    state[1] = state[1].wrapping_add(b);
    state[2] = state[2].wrapping_add(c);
    state[3] = state[3].wrapping_add(d);
    state[4] = state[4].wrapping_add(e);
    state[5] = state[5].wrapping_add(f);
    state[6] = state[6].wrapping_add(g);
    state[7] = state[7].wrapping_add(h);
}

fn validate_name(name: &str) -> Result<(), HotsetError> {
    if name.is_empty()
        || name.len() > 64
        || !name.bytes().all(|byte| {
            byte.is_ascii_lowercase() || byte.is_ascii_digit() || b"._-".contains(&byte)
        })
        || !name
            .as_bytes()
            .first()
            .is_some_and(u8::is_ascii_alphanumeric)
    {
        return Err(HotsetError::Invalid(
            "name must be 1-64 lowercase ASCII letters/digits/dot/underscore/hyphen and start with a letter or digit"
                .to_owned(),
        ));
    }
    Ok(())
}

fn validate_operation_keys(operation_keys: &[String]) -> Result<(), HotsetError> {
    if operation_keys.is_empty() || operation_keys.len() > MAX_HOTSET_OPERATIONS {
        return Err(HotsetError::Invalid(format!(
            "operation count must be between 1 and {MAX_HOTSET_OPERATIONS}"
        )));
    }
    ensure_unique(operation_keys, "operation key")?;
    for key in operation_keys {
        if key.is_empty()
            || !key.bytes().all(|byte| {
                byte.is_ascii_lowercase()
                    || byte.is_ascii_digit()
                    || matches!(byte, b'.' | b'_' | b'-')
            })
        {
            return Err(HotsetError::Invalid(format!(
                "operation key {key:?} is not canonical lowercase ASCII"
            )));
        }
    }
    Ok(())
}

fn ensure_unique(values: &[String], label: &str) -> Result<(), HotsetError> {
    let mut seen = std::collections::BTreeSet::new();
    for value in values {
        if !seen.insert(value) {
            return Err(HotsetError::Invalid(format!("duplicate {label}: {value}")));
        }
    }
    Ok(())
}

fn required_object<'a>(
    object: &'a Map<String, Value>,
    key: &str,
) -> Result<&'a Map<String, Value>, HotsetError> {
    object
        .get(key)
        .and_then(Value::as_object)
        .ok_or_else(|| HotsetError::Invalid(format!("{key} must be an object")))
}

fn required_array<'a>(
    object: &'a Map<String, Value>,
    key: &str,
) -> Result<&'a Vec<Value>, HotsetError> {
    object
        .get(key)
        .and_then(Value::as_array)
        .ok_or_else(|| HotsetError::Invalid(format!("{key} must be an array")))
}

fn required_string<'a>(object: &'a Map<String, Value>, key: &str) -> Result<&'a str, HotsetError> {
    object
        .get(key)
        .and_then(Value::as_str)
        .ok_or_else(|| HotsetError::Invalid(format!("{key} must be a string")))
}

fn required_u64(object: &Map<String, Value>, key: &str) -> Result<u64, HotsetError> {
    object
        .get(key)
        .and_then(Value::as_u64)
        .ok_or_else(|| HotsetError::Invalid(format!("{key} must be an unsigned integer")))
}

fn string_array(object: &Map<String, Value>, key: &str) -> Result<Vec<String>, HotsetError> {
    required_array(object, key)?
        .iter()
        .map(|value| {
            value
                .as_str()
                .map(str::to_owned)
                .ok_or_else(|| HotsetError::Invalid(format!("{key} entries must be strings")))
        })
        .collect()
}

fn optional_string_array(
    object: &Map<String, Value>,
    key: &str,
) -> Result<Vec<String>, HotsetError> {
    match object.get(key) {
        None => Ok(Vec::new()),
        Some(value) => value
            .as_array()
            .ok_or_else(|| HotsetError::Invalid(format!("{key} must be an array")))?
            .iter()
            .map(|entry| {
                entry
                    .as_str()
                    .map(str::to_owned)
                    .ok_or_else(|| HotsetError::Invalid(format!("{key} entries must be strings")))
            })
            .collect(),
    }
}

#[cfg(test)]
mod tests {
    use super::{
        generate_hotset, generate_hotset_with_fused, parse_hotset_manifest, sha256_hex,
        HotsetSource,
    };

    const ECON: &str = include_str!("../../../spec/examples/econ-undergrad-minimal.xsp.json");
    const STATS: &str = include_str!("../../../packs/statistics-core.xsp.json");

    #[test]
    fn sha256_matches_known_vector() {
        assert_eq!(
            sha256_hex(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }

    #[test]
    fn manifest_is_bounded_and_reproducible() {
        let text = r#"{
          "format":"exactscope.hotset.source",
          "format_version":"0.1",
          "name":"p0-smoke",
          "sources":["../spec/examples/econ-undergrad-minimal.xsp.json"],
          "operations":["econ.ped.mid"],
          "include_find":false
        }"#;
        let first = parse_hotset_manifest(text).expect("parse manifest");
        let second = parse_hotset_manifest(text).expect("parse manifest again");
        assert_eq!(first, second);
        assert_eq!(first.operation_keys, ["econ.ped.mid"]);
    }

    #[test]
    fn fused_manifest_and_eight_operation_hotset_are_reproducible() {
        let text = r#"{
          "format":"exactscope.hotset.source",
          "format_version":"0.1",
          "name":"econ-core-8",
          "fused_packs":["econ-undergrad"],
          "operations":[
            "econ.ped.mid",
            "econ.gdp.deflator100",
            "econ.inflation.cpi_pct",
            "econ.money.velocity",
            "econ.rate.real.exact_pct",
            "econ.rate.real.approx_pct",
            "econ.output_gap_pct",
            "econ.growth.rate_pct"
          ],
          "include_find":true
        }"#;
        let manifest = parse_hotset_manifest(text).expect("parse fused manifest");
        assert!(manifest.source_paths.is_empty());
        assert_eq!(manifest.fused_packs, ["econ-undergrad"]);

        let first = generate_hotset_with_fused(
            &manifest.name,
            &[],
            &manifest.fused_packs,
            &manifest.operation_keys,
            manifest.include_find,
        )
        .expect("generate fused hot set");
        let second = generate_hotset_with_fused(
            &manifest.name,
            &[],
            &manifest.fused_packs,
            &manifest.operation_keys,
            manifest.include_find,
        )
        .expect("generate fused hot set again");
        assert_eq!(first, second);
        let catalog: serde_json::Value =
            serde_json::from_str(&first.catalog_json).expect("catalog json");
        assert_eq!(catalog["operations"].as_array().unwrap().len(), 8);
        assert_eq!(catalog["packs"][0]["source"], "fused:econ-undergrad");
        assert!(first.xs_find_tool_json.is_some());
        assert!(first.xs_eval_gbnf.contains("econ.gdp.deflator100"));
    }

    #[test]
    fn direct_eval_bundle_is_reproducible_and_digest_bound() {
        let sources = [HotsetSource {
            label: "../spec/examples/econ-undergrad-minimal.xsp.json",
            source: ECON,
        }];
        let keys = vec!["econ.ped.mid".to_owned()];
        let first = generate_hotset("p0-smoke", &sources, &keys, false).expect("generate");
        let second = generate_hotset("p0-smoke", &sources, &keys, false).expect("generate again");
        assert_eq!(first, second);

        let catalog: serde_json::Value =
            serde_json::from_str(&first.catalog_json).expect("catalog json");
        assert_eq!(catalog["operations"][0]["op"], "econ.ped.mid");
        assert_eq!(catalog["operations"][0]["revision"], 1);
        assert_eq!(
            catalog["operations"][0]["args"].as_array().unwrap().len(),
            4
        );
        assert_eq!(
            catalog["binding_sha256"]
                .as_str()
                .expect("binding digest")
                .len(),
            64
        );
        assert_eq!(
            catalog["packs"][0]["binding_sha256"]
                .as_str()
                .expect("pack binding digest")
                .len(),
            64
        );
        assert!(first.xs_eval_tool_json.contains("\"enum\": ["));
        assert!(first.xs_eval_gbnf.contains("econ.ped.mid"));
        assert!(first.xs_find_tool_json.is_none());
    }

    #[test]
    fn operation_revision_changes_binding_digest() {
        let original = [HotsetSource {
            label: "econ.json",
            source: ECON,
        }];
        let keys = vec!["econ.ped.mid".to_owned()];
        let original_bundle =
            generate_hotset("digest-test", &original, &keys, false).expect("original");

        let mut changed: serde_json::Value = serde_json::from_str(ECON).expect("source json");
        changed["operations"][0]["revision"] = serde_json::json!(2);
        let changed_text = serde_json::to_string(&changed).expect("changed source");
        let changed_sources = [HotsetSource {
            label: "econ.json",
            source: &changed_text,
        }];
        let changed_bundle =
            generate_hotset("digest-test", &changed_sources, &keys, false).expect("changed");

        let original_catalog: serde_json::Value =
            serde_json::from_str(&original_bundle.catalog_json).expect("original catalog");
        let changed_catalog: serde_json::Value =
            serde_json::from_str(&changed_bundle.catalog_json).expect("changed catalog");
        assert_ne!(
            original_catalog["binding_sha256"],
            changed_catalog["binding_sha256"]
        );
        assert_ne!(
            original_catalog["packs"][0]["binding_sha256"],
            changed_catalog["packs"][0]["binding_sha256"]
        );
    }

    #[test]
    fn unknown_and_vector_operations_fail_closed() {
        let econ_sources = [HotsetSource {
            label: "econ.json",
            source: ECON,
        }];
        assert!(generate_hotset(
            "unknown-test",
            &econ_sources,
            &["econ.nope".to_owned()],
            false
        )
        .is_err());

        let stats_sources = [HotsetSource {
            label: "stats.json",
            source: STATS,
        }];
        let error = generate_hotset(
            "vector-test",
            &stats_sources,
            &["stats.mean".to_owned()],
            false,
        )
        .expect_err("vector Tiny JSON hot set must be rejected");
        assert!(error.to_string().contains("scalar-only"));
    }

    #[test]
    fn optional_find_assets_are_explicit() {
        let sources = [HotsetSource {
            label: "econ.json",
            source: ECON,
        }];
        let bundle = generate_hotset("find-test", &sources, &["econ.ped.mid".to_owned()], true)
            .expect("generate with find");
        assert!(bundle.xs_find_tool_json.unwrap().contains("xs_find"));
        assert!(bundle.xs_find_gbnf.unwrap().contains("query"));
    }
}
