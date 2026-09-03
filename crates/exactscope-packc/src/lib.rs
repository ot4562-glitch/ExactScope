#![forbid(unsafe_code)]
#![allow(clippy::alloc_instead_of_core, clippy::std_instead_of_core)]
#![doc = "`ExactScope` build-time canonical pack compiler."]

//! The compiler is desktop/build-time only. The first implementation slice
//! supports one formula operation per source pack, emits canonical `.xsp`
//! bytes, reparses them with the same allocation-free runtime loader, and runs
//! the source golden vectors before returning the artifact.

use std::{
    collections::{BTreeMap, BTreeSet},
    error::Error,
    fmt,
};

use exactscope_kernel::{
    validate_program, Decimal64, Instruction, ProgramKind, RoundingMode, ScalarValue, Status,
    VALUE_FLAG_ROUNDED,
};
use exactscope_pack::{
    format::{
        crc32_iso_hdlc, ALIAS_RECORD_SIZE, CLASSIFICATION_RECORD_SIZE, CONSTANT_RECORD_SIZE,
        CONSTRAINT_GE, CONSTRAINT_GT, CONSTRAINT_RECORD_SIZE, FORMAT_MAJOR, FORMAT_MINOR,
        HEADER_SIZE, INPUT_FLAG_UNIT_REQUIRED, INPUT_RECORD_SIZE, INSTRUCTION_RECORD_SIZE,
        META_RECORD_SIZE, NUMERIC_PROFILE_DECIMAL64_V1, OPERATION_KIND_FORMULA,
        OPERATION_RECORD_SIZE, OP_FLAG_CLASSIFICATION_REQUIRED, OP_FLAG_ROUNDING_OVERRIDE,
        OP_FLAG_SCALE_OVERRIDE, OUTPUT_RECORD_SIZE, SECTION_ALIASES, SECTION_CLASSIFICATIONS,
        SECTION_CONSTANTS, SECTION_CONSTRAINTS, SECTION_ENTRY_SIZE, SECTION_INPUTS, SECTION_META,
        SECTION_OPERATIONS, SECTION_OUTPUTS, SECTION_PROGRAMS, SECTION_STRINGS,
    },
    PackView,
};
use serde_json::{Map, Value};

const SOURCE_FORMAT: &str = "exactscope.scopepack.source";
const SOURCE_VERSION: &str = "0.1";
const ABI_V1_0: u32 = 0x0001_0000;
const ABSENT_STRING: u32 = u32::MAX;
const MAX_SOURCE_BYTES: usize = 1024 * 1024;

/// Returns the source format identifier frozen by the v0.1 specification.
#[must_use]
pub const fn source_format() -> &'static str {
    SOURCE_FORMAT
}

/// Build-time compiler failure.
#[derive(Debug)]
pub enum CompileError {
    /// Source JSON could not be decoded.
    Json(serde_json::Error),
    /// Source shape or semantic contract is invalid.
    Invalid(&'static str),
    /// The source uses a feature intentionally deferred by the first slice.
    Unsupported(&'static str),
    /// The shared kernel/pack validator rejected compiled semantics.
    Runtime(Status),
}

impl fmt::Display for CompileError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Json(error) => write!(formatter, "invalid source JSON: {error}"),
            Self::Invalid(message) => write!(formatter, "invalid scope-pack source: {message}"),
            Self::Unsupported(message) => {
                write!(formatter, "unsupported v0.1 compiler feature: {message}")
            }
            Self::Runtime(status) => write!(
                formatter,
                "runtime validator rejected pack with status {}",
                status.code()
            ),
        }
    }
}

impl Error for CompileError {}

impl From<serde_json::Error> for CompileError {
    fn from(value: serde_json::Error) -> Self {
        Self::Json(value)
    }
}

impl From<Status> for CompileError {
    fn from(value: Status) -> Self {
        Self::Runtime(value)
    }
}

#[derive(Debug)]
struct PackSource {
    id: String,
    name: String,
    version: (u16, u16, u16),
    license: String,
    description: String,
    locale: String,
    limits: Limits,
    operation: OperationSource,
}

#[derive(Clone, Copy, Debug)]
struct Limits {
    vector_len: u16,
    vm_steps: u16,
    stack: u16,
}

#[derive(Debug)]
struct OperationSource {
    id: u32,
    revision: u16,
    key: String,
    name: String,
    method: String,
    signature: String,
    aliases: Vec<String>,
    inputs: Vec<InputSource>,
    output: OutputSource,
    scale: u8,
    rounding: RoundingMode,
    allow_scale_override: bool,
    allow_rounding_override: bool,
    classification_required: bool,
    constants: Vec<Decimal64>,
    formula: Vec<Instruction>,
    formula_max_stack: usize,
    classifications: Vec<ClassificationSource>,
    tests: Vec<TestSource>,
}

#[derive(Debug)]
struct InputSource {
    name: String,
    semantic: u8,
    unit_namespace: Option<String>,
    same_unit_group: Option<String>,
    unit_required: bool,
    constraint_kind: u8,
    constraint_constant: usize,
    detail_id: u16,
}

#[derive(Debug)]
struct OutputSource {
    name: String,
    semantic: u8,
    unit_rule: String,
}

#[derive(Debug)]
struct ClassificationSource {
    id: u16,
    key: String,
    priority: u16,
    program: Vec<Instruction>,
}

#[derive(Debug)]
struct TestSource {
    name: String,
    args: Vec<String>,
    status: String,
    values: Vec<String>,
    classification: Option<String>,
    rounded: Option<bool>,
    argument_index: Option<u16>,
    detail_id: Option<u16>,
}

#[derive(Clone, Debug)]
struct SectionData {
    kind: u16,
    count: u32,
    bytes: Vec<u8>,
}

/// Compiles reviewed source JSON into canonical runtime `.xsp` bytes.
///
/// The first slice intentionally accepts exactly one scalar `formula`
/// operation. This proves the complete plugin boundary before multi-operation
/// compilation and vector kernels are enabled.
///
/// # Errors
///
/// Returns a descriptive build-time error when source, VM semantics, compiled
/// binary structure, or source golden vectors fail validation.
pub fn compile_source(source: &str) -> Result<Vec<u8>, CompileError> {
    if source.len() > MAX_SOURCE_BYTES {
        return Err(CompileError::Invalid(
            "source exceeds one MiB build-time limit",
        ));
    }
    let root: Value = serde_json::from_str(source)?;
    let parsed = parse_source(&root)?;
    let bytes = emit_pack(&parsed)?;
    validate_compiled(&bytes, &parsed)?;
    Ok(bytes)
}

fn parse_source(root: &Value) -> Result<PackSource, CompileError> {
    let root = object(root)?;
    if string(root, "format")? != SOURCE_FORMAT || string(root, "format_version")? != SOURCE_VERSION
    {
        return Err(CompileError::Invalid("unsupported source format/version"));
    }

    let pack = object(required(root, "pack")?)?;
    if string(pack, "numeric_profile")? != "decimal64-v1"
        || string(pack, "abi_min")? != "1.0"
        || string(pack, "abi_max")? != "1.0"
    {
        return Err(CompileError::Unsupported(
            "numeric profile or ABI outside decimal64-v1 / ABI 1.0",
        ));
    }
    let limits_value = object(required(root, "limits")?)?;
    let limits = Limits {
        vector_len: to_u16(integer(limits_value, "max_vector_len")?)?,
        vm_steps: to_u16(integer(limits_value, "max_vm_steps")?)?,
        stack: to_u16(integer(limits_value, "max_stack")?)?,
    };
    if limits.vector_len > 256 || limits.vm_steps > 64 || limits.stack > 16 {
        return Err(CompileError::Invalid(
            "declared limits exceed v0.1 runtime caps",
        ));
    }

    let operations = array(required(root, "operations")?)?;
    if operations.len() != 1 {
        return Err(CompileError::Unsupported(
            "first compiler slice requires exactly one operation",
        ));
    }
    let operation = parse_operation(&operations[0], limits)?;

    Ok(PackSource {
        id: string(pack, "id")?.to_owned(),
        name: string(pack, "name")?.to_owned(),
        version: parse_semver(string(pack, "version")?)?,
        license: string(pack, "license")?.to_owned(),
        description: string(pack, "description")?.to_owned(),
        locale: string(pack, "default_locale")?.to_owned(),
        limits,
        operation,
    })
}

#[allow(clippy::too_many_lines)]
fn parse_operation(value: &Value, limits: Limits) -> Result<OperationSource, CompileError> {
    let operation = object(value)?;
    if string(operation, "kind")? != "formula" {
        return Err(CompileError::Unsupported(
            "first compiler slice supports formula operations only",
        ));
    }
    let id = to_u32(integer(operation, "id")?)?;
    let revision = to_u16(integer(operation, "revision")?)?;
    if id == 0 || revision == 0 {
        return Err(CompileError::Invalid(
            "operation id/revision must be nonzero",
        ));
    }
    let key = string(operation, "key")?.to_owned();
    let name = string(operation, "name")?.to_owned();
    let method = string(operation, "method")?.to_owned();

    let input_values = array(required(operation, "inputs")?)?;
    if input_values.len() > 12 {
        return Err(CompileError::Invalid("too many scalar inputs"));
    }

    let source_constants = array(required(operation, "constants")?)?;
    let mut constants = Vec::<Decimal64>::new();
    let mut local_constant_map = Vec::<usize>::new();
    for value in source_constants {
        let text = value
            .as_str()
            .ok_or(CompileError::Invalid("constant must be a decimal string"))?;
        let decimal = parse_decimal(text)?;
        let index = intern_constant(&mut constants, decimal);
        local_constant_map.push(index);
    }

    let mut inputs = Vec::with_capacity(input_values.len());
    let mut input_names = Vec::with_capacity(input_values.len());
    for input_value in input_values {
        let input = object(input_value)?;
        if string(input, "shape")? != "scalar" {
            return Err(CompileError::Unsupported(
                "vector inputs are deferred until statistics kernels",
            ));
        }
        let name = string(input, "name")?.to_owned();
        input_names.push(name.clone());
        let constraints = array(required(input, "constraints")?)?;
        if constraints.len() != 1 {
            return Err(CompileError::Unsupported(
                "first compiler slice requires one scalar constraint per input",
            ));
        }
        let constraint = object(&constraints[0])?;
        let constraint_kind = match string(constraint, "kind")? {
            "gt" => CONSTRAINT_GT,
            "ge" => CONSTRAINT_GE,
            _ => {
                return Err(CompileError::Unsupported(
                    "first compiler slice supports gt/ge constraints only",
                ))
            }
        };
        let constraint_decimal = parse_decimal(string(constraint, "value")?)?;
        let constraint_constant = intern_constant(&mut constants, constraint_decimal);
        inputs.push(InputSource {
            name,
            semantic: semantic_id(string(input, "semantic")?)?,
            unit_namespace: optional_string(input, "unit_namespace")?,
            same_unit_group: optional_string(input, "same_unit_group")?,
            unit_required: optional_bool(input, "unit_required")?.unwrap_or(false),
            constraint_kind,
            constraint_constant,
            detail_id: to_u16(integer(constraint, "detail_id")?)?,
        });
    }

    let output_values = array(required(operation, "outputs")?)?;
    if output_values.len() != 1 {
        return Err(CompileError::Unsupported(
            "first compiler slice supports one scalar output",
        ));
    }
    let output_value = object(&output_values[0])?;
    let output = OutputSource {
        name: string(output_value, "name")?.to_owned(),
        semantic: semantic_id(string(output_value, "semantic")?)?,
        unit_rule: string(output_value, "unit_rule")?.to_owned(),
    };
    if output.unit_rule != "dimensionless" {
        return Err(CompileError::Unsupported(
            "first compiler slice supports dimensionless output only",
        ));
    }

    let output_policy = object(required(operation, "output_policy")?)?;
    let scale = to_u8(integer(output_policy, "scale")?)?;
    if scale > 18 {
        return Err(CompileError::Invalid("output scale exceeds decimal64-v1"));
    }
    let rounding = rounding_mode(string(output_policy, "rounding")?)?;
    let allow_scale_override = boolean(output_policy, "allow_scale_override")?;
    let allow_rounding_override = boolean(output_policy, "allow_rounding_override")?;
    let classification_required = boolean(output_policy, "classification_required")?;

    let programs = array(required(operation, "programs")?)?;
    if programs.len() != 1 {
        return Err(CompileError::Unsupported(
            "first compiler slice requires exactly one formula program",
        ));
    }
    let formula_source = object(&programs[0])?;
    if string(formula_source, "output")? != output.name {
        return Err(CompileError::Invalid(
            "formula program output does not match declared output",
        ));
    }
    let formula = parse_program(
        array(required(formula_source, "instructions")?)?,
        &local_constant_map,
    )?;
    let formula_max_stack = validate_program(
        &formula,
        ProgramKind::Formula,
        inputs.len(),
        constants.len(),
        0,
    )?;
    if formula.len() > usize::from(limits.vm_steps) || formula_max_stack > usize::from(limits.stack)
    {
        return Err(CompileError::Invalid(
            "formula exceeds source-declared VM limits",
        ));
    }

    let classification_values = array(required(operation, "classifications")?)?;
    let mut classifications = Vec::with_capacity(classification_values.len());
    let mut previous_priority = 0u16;
    let mut seen_ids = BTreeSet::new();
    let mut seen_keys = BTreeSet::new();
    for (index, classification_value) in classification_values.iter().enumerate() {
        let classification = object(classification_value)?;
        let id = to_u16(integer(classification, "id")?)?;
        let priority = to_u16(integer(classification, "priority")?)?;
        let key = string(classification, "key")?.to_owned();
        if id == 0
            || !seen_ids.insert(id)
            || !seen_keys.insert(key.clone())
            || (index != 0 && priority < previous_priority)
            || to_u8(integer(classification, "output_index")?)? != 0
        {
            return Err(CompileError::Invalid(
                "invalid or duplicate classification declaration",
            ));
        }
        let program = parse_program(
            array(required(classification, "program")?)?,
            &local_constant_map,
        )?;
        validate_program(&program, ProgramKind::Classification, 0, constants.len(), 1)?;
        classifications.push(ClassificationSource {
            id,
            key,
            priority,
            program,
        });
        previous_priority = priority;
    }
    if classification_required && classifications.is_empty() {
        return Err(CompileError::Invalid(
            "classification is required but no classes are declared",
        ));
    }

    let mut aliases = Vec::new();
    for value in array(required(operation, "aliases")?)? {
        let alias = value
            .as_str()
            .ok_or(CompileError::Invalid("alias must be a string"))?;
        aliases.push(alias.to_owned());
    }
    aliases.sort();
    aliases.dedup();

    let signature = format!("{}({})", key, input_names.join(","));
    let tests = parse_tests(array(required(operation, "tests")?)?)?;

    Ok(OperationSource {
        id,
        revision,
        key,
        name,
        method,
        signature,
        aliases,
        inputs,
        output,
        scale,
        rounding,
        allow_scale_override,
        allow_rounding_override,
        classification_required,
        constants,
        formula,
        formula_max_stack,
        classifications,
        tests,
    })
}

fn parse_program(
    values: &[Value],
    local_constant_map: &[usize],
) -> Result<Vec<Instruction>, CompileError> {
    if values.is_empty() || values.len() > 64 {
        return Err(CompileError::Invalid(
            "program instruction count outside v0.1 limits",
        ));
    }
    let mut output = Vec::with_capacity(values.len());
    for value in values {
        let parts = array(value)?;
        let opcode_name = parts
            .first()
            .and_then(Value::as_str)
            .ok_or(CompileError::Invalid("instruction opcode must be a string"))?;
        let (opcode, needs_operand) = opcode_id(opcode_name)?;
        let mut operand = if needs_operand {
            let raw = parts
                .get(1)
                .and_then(Value::as_i64)
                .ok_or(CompileError::Invalid(
                    "instruction operand must be an integer",
                ))?;
            i32::try_from(raw)
                .map_err(|_| CompileError::Invalid("instruction operand exceeds i32"))?
        } else {
            0
        };
        if (opcode == 2) && needs_operand {
            let local = usize::try_from(operand)
                .map_err(|_| CompileError::Invalid("constant index must be nonnegative"))?;
            let global = *local_constant_map.get(local).ok_or(CompileError::Invalid(
                "constant instruction index is out of range",
            ))?;
            operand = i32::try_from(global)
                .map_err(|_| CompileError::Invalid("compiled constant index exceeds i32"))?;
        }
        if needs_operand && parts.len() != 2 || !needs_operand && parts.len() != 1 {
            return Err(CompileError::Invalid(
                "instruction operand count is invalid",
            ));
        }
        if !(-8_388_608..=8_388_607).contains(&operand) {
            return Err(CompileError::Invalid(
                "instruction operand exceeds signed 24-bit range",
            ));
        }
        output.push(Instruction::new(opcode, operand));
    }
    Ok(output)
}

fn parse_tests(values: &[Value]) -> Result<Vec<TestSource>, CompileError> {
    let mut tests = Vec::with_capacity(values.len());
    let mut names = BTreeSet::new();
    for value in values {
        let test = object(value)?;
        let name = string(test, "name")?.to_owned();
        if !names.insert(name.clone()) {
            return Err(CompileError::Invalid("duplicate golden-test name"));
        }
        let mut args = Vec::new();
        for arg in array(required(test, "args")?)? {
            args.push(
                arg.as_str()
                    .ok_or(CompileError::Unsupported(
                        "first compiler slice supports scalar string test args only",
                    ))?
                    .to_owned(),
            );
        }
        let expect = object(required(test, "expect")?)?;
        let mut expected_values = Vec::new();
        if let Some(values) = expect.get("values") {
            for expected in array(values)? {
                expected_values.push(
                    expected
                        .as_str()
                        .ok_or(CompileError::Invalid(
                            "expected result must be a decimal string",
                        ))?
                        .to_owned(),
                );
            }
        }
        tests.push(TestSource {
            name,
            args,
            status: string(expect, "status")?.to_owned(),
            values: expected_values,
            classification: optional_string(expect, "classification")?,
            rounded: optional_bool(expect, "rounded")?,
            argument_index: optional_u16(expect, "argument_index")?,
            detail_id: optional_u16(expect, "detail_id")?,
        });
    }
    Ok(tests)
}

fn emit_pack(source: &PackSource) -> Result<Vec<u8>, CompileError> {
    let operation = &source.operation;
    let mut strings = BTreeSet::<String>::new();
    strings.insert(String::new());
    for value in [
        &source.id,
        &source.name,
        &source.license,
        &source.description,
        &source.locale,
        &operation.key,
        &operation.name,
        &operation.method,
        &operation.signature,
        &operation.output.name,
    ] {
        strings.insert(value.clone());
    }
    for input in &operation.inputs {
        strings.insert(input.name.clone());
        if let Some(value) = &input.unit_namespace {
            strings.insert(value.clone());
        }
        if let Some(value) = &input.same_unit_group {
            strings.insert(value.clone());
        }
    }
    for classification in &operation.classifications {
        strings.insert(classification.key.clone());
    }
    for alias in &operation.aliases {
        strings.insert(alias.clone());
    }

    let (string_bytes, string_offsets) = build_strings(strings)?;
    let mut sections = Vec::<SectionData>::new();

    sections.push(SectionData {
        kind: u16::try_from(SECTION_META).expect("section kind fits u16"),
        count: 1,
        bytes: emit_meta(source, &string_offsets)?,
    });
    sections.push(SectionData {
        kind: u16::try_from(SECTION_STRINGS).expect("section kind fits u16"),
        count: u32::try_from(string_offsets.len())
            .map_err(|_| CompileError::Invalid("too many strings"))?,
        bytes: string_bytes,
    });

    let mut programs = operation.formula.clone();
    let formula_start = 0u32;
    let formula_count = to_u16_usize(operation.formula.len())?;
    let mut class_program_ranges = Vec::with_capacity(operation.classifications.len());
    for classification in &operation.classifications {
        let start = u32::try_from(programs.len())
            .map_err(|_| CompileError::Invalid("program index exceeds u32"))?;
        let count = to_u16_usize(classification.program.len())?;
        programs.extend_from_slice(&classification.program);
        class_program_ranges.push((start, count));
    }

    sections.push(SectionData {
        kind: u16::try_from(SECTION_OPERATIONS).expect("section kind fits u16"),
        count: 1,
        bytes: emit_operation(source, &string_offsets, formula_start, formula_count)?,
    });
    sections.push(SectionData {
        kind: u16::try_from(SECTION_INPUTS).expect("section kind fits u16"),
        count: to_u32_usize(operation.inputs.len())?,
        bytes: emit_inputs(operation, &string_offsets)?,
    });
    sections.push(SectionData {
        kind: u16::try_from(SECTION_OUTPUTS).expect("section kind fits u16"),
        count: 1,
        bytes: emit_output(operation, &string_offsets, formula_start, formula_count)?,
    });
    sections.push(SectionData {
        kind: u16::try_from(SECTION_CONSTRAINTS).expect("section kind fits u16"),
        count: to_u32_usize(operation.inputs.len())?,
        bytes: emit_constraints(operation)?,
    });
    sections.push(SectionData {
        kind: u16::try_from(SECTION_CONSTANTS).expect("section kind fits u16"),
        count: to_u32_usize(operation.constants.len())?,
        bytes: emit_constants(operation),
    });
    sections.push(SectionData {
        kind: u16::try_from(SECTION_PROGRAMS).expect("section kind fits u16"),
        count: to_u32_usize(programs.len())?,
        bytes: emit_programs(&programs)?,
    });
    sections.push(SectionData {
        kind: u16::try_from(SECTION_CLASSIFICATIONS).expect("section kind fits u16"),
        count: to_u32_usize(operation.classifications.len())?,
        bytes: emit_classifications(operation, &string_offsets, &class_program_ranges)?,
    });
    sections.push(SectionData {
        kind: u16::try_from(SECTION_ALIASES).expect("section kind fits u16"),
        count: to_u32_usize(operation.aliases.len())?,
        bytes: emit_aliases(operation, &string_offsets)?,
    });

    assemble_sections(&sections)
}

fn emit_meta(
    source: &PackSource,
    strings: &BTreeMap<String, u32>,
) -> Result<Vec<u8>, CompileError> {
    let mut bytes = vec![0u8; META_RECORD_SIZE];
    put_u32(&mut bytes, 0, string_offset(strings, &source.id)?)?;
    put_u32(&mut bytes, 4, string_offset(strings, &source.name)?)?;
    put_u32(&mut bytes, 8, string_offset(strings, &source.description)?)?;
    put_u32(&mut bytes, 12, string_offset(strings, &source.license)?)?;
    put_u16(&mut bytes, 16, source.version.0)?;
    put_u16(&mut bytes, 18, source.version.1)?;
    put_u16(&mut bytes, 20, source.version.2)?;
    put_u16(&mut bytes, 22, NUMERIC_PROFILE_DECIMAL64_V1)?;
    put_u32(&mut bytes, 24, ABI_V1_0)?;
    put_u32(&mut bytes, 28, ABI_V1_0)?;
    put_u32(&mut bytes, 32, string_offset(strings, &source.locale)?)?;
    put_u32(&mut bytes, 36, 1)?;
    put_u16(&mut bytes, 40, source.limits.vector_len)?;
    put_u16(&mut bytes, 42, source.limits.vm_steps)?;
    put_u16(&mut bytes, 44, source.limits.stack)?;
    Ok(bytes)
}

fn emit_operation(
    source: &PackSource,
    strings: &BTreeMap<String, u32>,
    formula_start: u32,
    formula_count: u16,
) -> Result<Vec<u8>, CompileError> {
    let operation = &source.operation;
    let mut bytes = vec![0u8; OPERATION_RECORD_SIZE];
    put_u32(&mut bytes, 0, operation.id)?;
    put_u16(&mut bytes, 4, operation.revision)?;
    bytes[6] = OPERATION_KIND_FORMULA;
    bytes[7] = (u8::from(operation.allow_scale_override) * OP_FLAG_SCALE_OVERRIDE)
        | (u8::from(operation.allow_rounding_override) * OP_FLAG_ROUNDING_OVERRIDE)
        | (u8::from(operation.classification_required) * OP_FLAG_CLASSIFICATION_REQUIRED);
    put_u32(&mut bytes, 8, string_offset(strings, &operation.key)?)?;
    put_u32(&mut bytes, 12, string_offset(strings, &operation.name)?)?;
    put_u32(
        &mut bytes,
        16,
        string_offset(strings, &operation.signature)?,
    )?;
    put_u32(
        &mut bytes,
        20,
        if operation.method.is_empty() {
            ABSENT_STRING
        } else {
            string_offset(strings, &operation.method)?
        },
    )?;
    put_u32(&mut bytes, 24, 0)?;
    put_u16(&mut bytes, 28, to_u16_usize(operation.inputs.len())?)?;
    bytes[30] = 1;
    bytes[31] = u8::try_from(operation.formula_max_stack)
        .map_err(|_| CompileError::Invalid("formula max stack exceeds u8"))?;
    put_u32(&mut bytes, 32, 0)?;
    put_u32(&mut bytes, 36, formula_start)?;
    put_u16(&mut bytes, 40, formula_count)?;
    put_u16(&mut bytes, 42, 0)?;
    put_u32(&mut bytes, 44, 0)?;
    put_u16(
        &mut bytes,
        48,
        to_u16_usize(operation.classifications.len())?,
    )?;
    bytes[50] = operation.scale;
    bytes[51] = operation.rounding.id();
    put_u32(&mut bytes, 52, 0)?;
    put_u16(&mut bytes, 56, to_u16_usize(operation.aliases.len())?)?;
    put_u16(&mut bytes, 58, 0)?;
    put_u32(&mut bytes, 60, 0)?;
    Ok(bytes)
}

fn emit_inputs(
    operation: &OperationSource,
    strings: &BTreeMap<String, u32>,
) -> Result<Vec<u8>, CompileError> {
    let mut bytes = vec![0u8; operation.inputs.len() * INPUT_RECORD_SIZE];
    for (index, input) in operation.inputs.iter().enumerate() {
        let base = index * INPUT_RECORD_SIZE;
        put_u32(&mut bytes, base, string_offset(strings, &input.name)?)?;
        bytes[base + 4] = input.semantic;
        bytes[base + 5] = 0;
        put_u16(
            &mut bytes,
            base + 6,
            if input.unit_required {
                INPUT_FLAG_UNIT_REQUIRED
            } else {
                0
            },
        )?;
        put_u32(
            &mut bytes,
            base + 8,
            optional_offset(strings, input.unit_namespace.as_deref())?,
        )?;
        put_u32(
            &mut bytes,
            base + 12,
            optional_offset(strings, input.same_unit_group.as_deref())?,
        )?;
        put_u32(&mut bytes, base + 16, to_u32_usize(index)?)?;
        put_u16(&mut bytes, base + 20, 1)?;
        put_u16(&mut bytes, base + 22, 0)?;
    }
    Ok(bytes)
}

fn emit_output(
    operation: &OperationSource,
    strings: &BTreeMap<String, u32>,
    formula_start: u32,
    formula_count: u16,
) -> Result<Vec<u8>, CompileError> {
    let mut bytes = vec![0u8; OUTPUT_RECORD_SIZE];
    put_u32(
        &mut bytes,
        0,
        string_offset(strings, &operation.output.name)?,
    )?;
    bytes[4] = operation.output.semantic;
    bytes[5] = 0;
    put_u16(&mut bytes, 6, 0)?;
    put_u32(&mut bytes, 8, ABSENT_STRING)?;
    bytes[12] = operation.scale;
    bytes[13] = operation.rounding.id();
    put_u16(&mut bytes, 14, 0)?;
    put_u32(&mut bytes, 16, formula_start)?;
    put_u16(&mut bytes, 20, formula_count)?;
    put_u16(&mut bytes, 22, 0)?;
    Ok(bytes)
}

fn emit_constraints(operation: &OperationSource) -> Result<Vec<u8>, CompileError> {
    let mut bytes = vec![0u8; operation.inputs.len() * CONSTRAINT_RECORD_SIZE];
    for (index, input) in operation.inputs.iter().enumerate() {
        let base = index * CONSTRAINT_RECORD_SIZE;
        bytes[base] = input.constraint_kind;
        bytes[base + 1] = 0;
        put_u16(&mut bytes, base + 2, input.detail_id)?;
        put_u32(
            &mut bytes,
            base + 4,
            to_u32_usize(input.constraint_constant)?,
        )?;
    }
    Ok(bytes)
}

fn emit_constants(operation: &OperationSource) -> Vec<u8> {
    let mut bytes = vec![0u8; operation.constants.len() * CONSTANT_RECORD_SIZE];
    for (index, constant) in operation.constants.iter().enumerate() {
        let base = index * CONSTANT_RECORD_SIZE;
        bytes[base..base + 8].copy_from_slice(&constant.coefficient().to_le_bytes());
        bytes[base + 8] = constant.exponent().to_ne_bytes()[0];
        bytes[base + 9] = 0;
    }
    bytes
}

fn emit_programs(programs: &[Instruction]) -> Result<Vec<u8>, CompileError> {
    let mut bytes = vec![0u8; programs.len() * INSTRUCTION_RECORD_SIZE];
    for (index, instruction) in programs.iter().enumerate() {
        if !(-8_388_608..=8_388_607).contains(&instruction.operand) {
            return Err(CompileError::Invalid(
                "instruction operand exceeds signed 24-bit range",
            ));
        }
        let operand_bits = u32::from_ne_bytes(instruction.operand.to_ne_bytes()) & 0x00ff_ffff;
        let raw = u32::from(instruction.opcode) | (operand_bits << 8);
        bytes[index * 4..index * 4 + 4].copy_from_slice(&raw.to_le_bytes());
    }
    Ok(bytes)
}

fn emit_classifications(
    operation: &OperationSource,
    strings: &BTreeMap<String, u32>,
    ranges: &[(u32, u16)],
) -> Result<Vec<u8>, CompileError> {
    let mut bytes = vec![0u8; operation.classifications.len() * CLASSIFICATION_RECORD_SIZE];
    for (index, classification) in operation.classifications.iter().enumerate() {
        let base = index * CLASSIFICATION_RECORD_SIZE;
        put_u16(&mut bytes, base, classification.id)?;
        put_u16(&mut bytes, base + 2, classification.priority)?;
        put_u32(
            &mut bytes,
            base + 4,
            string_offset(strings, &classification.key)?,
        )?;
        put_u32(&mut bytes, base + 8, ranges[index].0)?;
        put_u16(&mut bytes, base + 12, ranges[index].1)?;
        put_u16(&mut bytes, base + 14, 0)?;
    }
    Ok(bytes)
}

fn emit_aliases(
    operation: &OperationSource,
    strings: &BTreeMap<String, u32>,
) -> Result<Vec<u8>, CompileError> {
    let mut bytes = vec![0u8; operation.aliases.len() * ALIAS_RECORD_SIZE];
    for (index, alias) in operation.aliases.iter().enumerate() {
        let base = index * ALIAS_RECORD_SIZE;
        put_u32(&mut bytes, base, string_offset(strings, alias)?)?;
        put_u32(&mut bytes, base + 4, 0)?;
        put_u16(&mut bytes, base + 8, 100)?;
        put_u16(&mut bytes, base + 10, 0)?;
    }
    Ok(bytes)
}

fn assemble_sections(sections: &[SectionData]) -> Result<Vec<u8>, CompileError> {
    let directory_offset = HEADER_SIZE;
    let directory_len = sections
        .len()
        .checked_mul(SECTION_ENTRY_SIZE)
        .ok_or(CompileError::Invalid("section directory overflow"))?;
    let data_start = align4(
        directory_offset
            .checked_add(directory_len)
            .ok_or(CompileError::Invalid("section layout overflow"))?,
    )?;
    let mut output = vec![0u8; data_start];
    let mut entries = Vec::with_capacity(sections.len());
    let mut previous_kind = 0u16;
    for section in sections {
        if section.kind <= previous_kind {
            return Err(CompileError::Invalid(
                "sections are not in canonical kind order",
            ));
        }
        pad4(&mut output);
        let offset = to_u32_usize(output.len())?;
        output.extend_from_slice(&section.bytes);
        entries.push((
            section.kind,
            offset,
            to_u32_usize(section.bytes.len())?,
            section.count,
        ));
        previous_kind = section.kind;
    }

    let total_len = to_u32_usize(output.len())?;
    output[0..4].copy_from_slice(b"XSPK");
    put_u16(&mut output, 4, FORMAT_MAJOR)?;
    put_u16(&mut output, 6, FORMAT_MINOR)?;
    put_u16(&mut output, 8, to_u16_usize(HEADER_SIZE)?)?;
    put_u16(&mut output, 10, to_u16_usize(SECTION_ENTRY_SIZE)?)?;
    put_u32(&mut output, 12, 0x0000_0004)?;
    put_u32(&mut output, 16, total_len)?;
    put_u32(&mut output, 20, to_u32_usize(directory_offset)?)?;
    put_u16(&mut output, 24, to_u16_usize(entries.len())?)?;
    put_u16(&mut output, 26, 0)?;

    for (index, (kind, offset, len, count)) in entries.iter().copied().enumerate() {
        let base = directory_offset + index * SECTION_ENTRY_SIZE;
        put_u16(&mut output, base, kind)?;
        put_u16(&mut output, base + 2, 0)?;
        put_u32(&mut output, base + 4, offset)?;
        put_u32(&mut output, base + 8, len)?;
        put_u32(&mut output, base + 12, count)?;
    }
    let crc = crc32_iso_hdlc(&output[HEADER_SIZE..]);
    put_u32(&mut output, 28, crc)?;
    Ok(output)
}

fn validate_compiled(bytes: &[u8], source: &PackSource) -> Result<(), CompileError> {
    let pack = PackView::parse(bytes)?;
    if pack.pack_id()? != source.id
        || pack.version()? != source.version
        || pack.operation_count() != 1
    {
        return Err(CompileError::Invalid(
            "compiled pack metadata drifted from source",
        ));
    }
    let operation = pack.operation_by_key(source.operation.key.as_bytes())?;
    for test in &source.operation.tests {
        if test.args.len() != source.operation.inputs.len() {
            return Err(CompileError::Invalid(
                "golden test argument count differs from operation signature",
            ));
        }
        let mut arguments = Vec::with_capacity(test.args.len());
        for (index, text) in test.args.iter().enumerate() {
            arguments.push(ScalarValue::new(
                parse_decimal(text)?,
                source.operation.inputs[index].semantic,
                0,
            ));
        }
        let result = pack.evaluate(1, operation, &arguments)?;
        let expected_status = status_from_key(&test.status)?;
        if result.status != expected_status {
            return Err(CompileError::Invalid(
                "compiled golden-test status mismatch",
            ));
        }
        if let Some(argument_index) = test.argument_index {
            if result.argument_index != argument_index {
                return Err(CompileError::Invalid(
                    "compiled golden-test argument index mismatch",
                ));
            }
        }
        if let Some(detail_id) = test.detail_id {
            if result.detail_code != detail_id {
                return Err(CompileError::Invalid(
                    "compiled golden-test detail id mismatch",
                ));
            }
        }
        if expected_status.is_ok() {
            let expected_value_count = u16::try_from(test.values.len())
                .map_err(|_| CompileError::Invalid("golden-test value count exceeds u16"))?;
            if result.value_count != expected_value_count {
                return Err(CompileError::Invalid(
                    "compiled golden-test value-count mismatch",
                ));
            }
            for (index, expected) in test.values.iter().enumerate() {
                let mut buffer = [0u8; 64];
                let written = result.values[index].decimal.write_canonical(&mut buffer)?;
                let actual = std::str::from_utf8(&buffer[..written])
                    .map_err(|_| CompileError::Invalid("non-UTF8 canonical decimal"))?;
                if actual != expected {
                    return Err(CompileError::Invalid("compiled golden-test value mismatch"));
                }
            }
            if let Some(expected_class) = &test.classification {
                if pack.classification_key(operation, result.classification_id)? != expected_class {
                    return Err(CompileError::Invalid(
                        "compiled golden-test classification mismatch",
                    ));
                }
            }
            if let Some(expected_rounded) = test.rounded {
                let rounded = result.values[0].flags & VALUE_FLAG_ROUNDED != 0;
                if rounded != expected_rounded {
                    return Err(CompileError::Invalid(
                        "compiled golden-test rounded flag mismatch",
                    ));
                }
            }
        } else if result.value_count != 0 {
            return Err(CompileError::Invalid(
                "failed golden test exposed a numeric result",
            ));
        }
        let _ = &test.name;
    }
    Ok(())
}

fn build_strings(
    strings: BTreeSet<String>,
) -> Result<(Vec<u8>, BTreeMap<String, u32>), CompileError> {
    let mut bytes = Vec::new();
    let mut offsets = BTreeMap::new();
    for value in strings {
        let offset = to_u32_usize(bytes.len())?;
        let len = u16::try_from(value.len())
            .map_err(|_| CompileError::Invalid("string exceeds u16 length"))?;
        bytes.extend_from_slice(&len.to_le_bytes());
        bytes.extend_from_slice(value.as_bytes());
        if bytes.len() % 2 != 0 {
            bytes.push(0);
        }
        offsets.insert(value, offset);
    }
    Ok((bytes, offsets))
}

fn intern_constant(constants: &mut Vec<Decimal64>, decimal: Decimal64) -> usize {
    if let Some(index) = constants.iter().position(|candidate| *candidate == decimal) {
        index
    } else {
        constants.push(decimal);
        constants.len() - 1
    }
}

fn parse_decimal(text: &str) -> Result<Decimal64, CompileError> {
    Decimal64::parse_ascii(text.as_bytes()).map_err(CompileError::Runtime)
}

fn parse_semver(text: &str) -> Result<(u16, u16, u16), CompileError> {
    if text.contains('-') || text.contains('+') {
        return Err(CompileError::Unsupported(
            "runtime pack semantic version prerelease/build metadata",
        ));
    }
    let mut parts = text.split('.');
    let major = parse_u16_part(parts.next())?;
    let minor = parse_u16_part(parts.next())?;
    let patch = parse_u16_part(parts.next())?;
    if parts.next().is_some() {
        return Err(CompileError::Invalid(
            "semantic version must have three components",
        ));
    }
    Ok((major, minor, patch))
}

fn parse_u16_part(part: Option<&str>) -> Result<u16, CompileError> {
    let part = part.ok_or(CompileError::Invalid("semantic version is incomplete"))?;
    if part.is_empty() || (part.len() > 1 && part.starts_with('0')) {
        return Err(CompileError::Invalid(
            "semantic version component is not canonical",
        ));
    }
    part.parse::<u16>()
        .map_err(|_| CompileError::Invalid("semantic version component exceeds u16"))
}

fn semantic_id(value: &str) -> Result<u8, CompileError> {
    match value {
        "number" => Ok(0),
        "count" => Ok(1),
        "currency_amount" => Ok(2),
        "price" => Ok(3),
        "quantity" => Ok(4),
        "rate_percent" => Ok(5),
        "rate_ratio" => Ok(6),
        "index" => Ok(7),
        "time_periods" => Ok(8),
        "probability" => Ok(9),
        "elasticity" => Ok(10),
        _ => Err(CompileError::Invalid("unknown semantic kind")),
    }
}

fn rounding_mode(value: &str) -> Result<RoundingMode, CompileError> {
    match value {
        "half_even" => Ok(RoundingMode::HalfEven),
        "half_away" => Ok(RoundingMode::HalfAway),
        "toward_zero" => Ok(RoundingMode::TowardZero),
        "floor" => Ok(RoundingMode::Floor),
        "ceil" => Ok(RoundingMode::Ceil),
        _ => Err(CompileError::Invalid("unknown rounding mode")),
    }
}

fn opcode_id(value: &str) -> Result<(u8, bool), CompileError> {
    let result = match value {
        "end" => (0, false),
        "arg" => (1, true),
        "const" => (2, true),
        "result" => (3, true),
        "add" => (4, false),
        "sub" => (5, false),
        "mul" => (6, false),
        "div" => (7, false),
        "neg" => (8, false),
        "abs" => (9, false),
        "min" => (10, false),
        "max" => (11, false),
        "powi" => (12, true),
        "sqrt" => (13, false),
        "cmp_lt" => (14, false),
        "cmp_le" => (15, false),
        "cmp_eq" => (16, false),
        "cmp_ge" => (17, false),
        "cmp_gt" => (18, false),
        "and" => (19, false),
        "or" => (20, false),
        "not" => (21, false),
        "select" => (22, false),
        "round" => {
            return Err(CompileError::Unsupported(
                "ROUND source operands are deferred",
            ))
        }
        _ => return Err(CompileError::Invalid("unknown VM opcode")),
    };
    Ok(result)
}

fn status_from_key(key: &str) -> Result<Status, CompileError> {
    let status = match key {
        "OK" => Status::OK,
        "INVALID_REQUEST" => Status::INVALID_REQUEST,
        "ABI_MISMATCH" => Status::ABI_MISMATCH,
        "UNKNOWN_OPERATION" => Status::UNKNOWN_OPERATION,
        "UNKNOWN_PACK" => Status::UNKNOWN_PACK,
        "ARGUMENT_COUNT" => Status::ARGUMENT_COUNT,
        "ARGUMENT_TYPE" => Status::ARGUMENT_TYPE,
        "AMBIGUOUS_METHOD" => Status::AMBIGUOUS_METHOD,
        "MISSING_INFORMATION" => Status::MISSING_INFORMATION,
        "INVALID_DECIMAL" => Status::INVALID_DECIMAL,
        "DOMAIN_ERROR" => Status::DOMAIN_ERROR,
        "CONSTRAINT_VIOLATION" => Status::CONSTRAINT_VIOLATION,
        "UNIT_MISMATCH" => Status::UNIT_MISMATCH,
        "DIVIDE_BY_ZERO" => Status::DIVIDE_BY_ZERO,
        "OVERFLOW" => Status::OVERFLOW,
        "PRECISION_UNRESOLVED" => Status::PRECISION_UNRESOLVED,
        "INSUFFICIENT_DATA" => Status::INSUFFICIENT_DATA,
        "BUFFER_TOO_SMALL" => Status::BUFFER_TOO_SMALL,
        "PACK_INVALID" => Status::PACK_INVALID,
        "PACK_VERSION_UNSUPPORTED" => Status::PACK_VERSION_UNSUPPORTED,
        "RESOURCE_LIMIT" => Status::RESOURCE_LIMIT,
        "UNSUPPORTED_OPERATION" => Status::UNSUPPORTED_OPERATION,
        "INTEGRITY_ERROR" => Status::INTEGRITY_ERROR,
        "INTERNAL_ERROR" => Status::INTERNAL_ERROR,
        _ => return Err(CompileError::Invalid("unknown expected status key")),
    };
    Ok(status)
}

fn object(value: &Value) -> Result<&Map<String, Value>, CompileError> {
    value
        .as_object()
        .ok_or(CompileError::Invalid("expected JSON object"))
}

fn array(value: &Value) -> Result<&[Value], CompileError> {
    value
        .as_array()
        .map(Vec::as_slice)
        .ok_or(CompileError::Invalid("expected JSON array"))
}

fn required<'a>(object: &'a Map<String, Value>, key: &str) -> Result<&'a Value, CompileError> {
    object
        .get(key)
        .ok_or(CompileError::Invalid("missing required source field"))
}

fn string<'a>(object: &'a Map<String, Value>, key: &str) -> Result<&'a str, CompileError> {
    required(object, key)?.as_str().ok_or(CompileError::Invalid(
        "required source field must be a string",
    ))
}

fn optional_string(object: &Map<String, Value>, key: &str) -> Result<Option<String>, CompileError> {
    object
        .get(key)
        .map(|value| {
            value
                .as_str()
                .map(ToOwned::to_owned)
                .ok_or(CompileError::Invalid(
                    "optional source field must be a string",
                ))
        })
        .transpose()
}

fn boolean(object: &Map<String, Value>, key: &str) -> Result<bool, CompileError> {
    required(object, key)?
        .as_bool()
        .ok_or(CompileError::Invalid(
            "required source field must be boolean",
        ))
}

fn optional_bool(object: &Map<String, Value>, key: &str) -> Result<Option<bool>, CompileError> {
    object
        .get(key)
        .map(|value| {
            value.as_bool().ok_or(CompileError::Invalid(
                "optional source field must be boolean",
            ))
        })
        .transpose()
}

fn integer(object: &Map<String, Value>, key: &str) -> Result<u64, CompileError> {
    required(object, key)?.as_u64().ok_or(CompileError::Invalid(
        "required source field must be a nonnegative integer",
    ))
}

fn optional_u16(object: &Map<String, Value>, key: &str) -> Result<Option<u16>, CompileError> {
    object
        .get(key)
        .map(|value| {
            value
                .as_u64()
                .ok_or(CompileError::Invalid(
                    "optional source field must be a nonnegative integer",
                ))
                .and_then(to_u16)
        })
        .transpose()
}

fn to_u8(value: u64) -> Result<u8, CompileError> {
    u8::try_from(value).map_err(|_| CompileError::Invalid("integer exceeds u8"))
}

fn to_u16(value: u64) -> Result<u16, CompileError> {
    u16::try_from(value).map_err(|_| CompileError::Invalid("integer exceeds u16"))
}

fn to_u32(value: u64) -> Result<u32, CompileError> {
    u32::try_from(value).map_err(|_| CompileError::Invalid("integer exceeds u32"))
}

fn to_u16_usize(value: usize) -> Result<u16, CompileError> {
    u16::try_from(value).map_err(|_| CompileError::Invalid("count exceeds u16"))
}

fn to_u32_usize(value: usize) -> Result<u32, CompileError> {
    u32::try_from(value).map_err(|_| CompileError::Invalid("count exceeds u32"))
}

fn string_offset(strings: &BTreeMap<String, u32>, value: &str) -> Result<u32, CompileError> {
    strings
        .get(value)
        .copied()
        .ok_or(CompileError::Invalid("string table lookup failed"))
}

fn optional_offset(
    strings: &BTreeMap<String, u32>,
    value: Option<&str>,
) -> Result<u32, CompileError> {
    value.map_or(Ok(ABSENT_STRING), |value| string_offset(strings, value))
}

fn align4(value: usize) -> Result<usize, CompileError> {
    value
        .checked_add(3)
        .map(|value| value & !3)
        .ok_or(CompileError::Invalid("alignment overflow"))
}

fn pad4(bytes: &mut Vec<u8>) {
    while bytes.len() % 4 != 0 {
        bytes.push(0);
    }
}

fn put_u16(bytes: &mut [u8], offset: usize, value: u16) -> Result<(), CompileError> {
    let end = offset
        .checked_add(2)
        .ok_or(CompileError::Invalid("record offset overflow"))?;
    bytes
        .get_mut(offset..end)
        .ok_or(CompileError::Invalid("record write outside buffer"))?
        .copy_from_slice(&value.to_le_bytes());
    Ok(())
}

fn put_u32(bytes: &mut [u8], offset: usize, value: u32) -> Result<(), CompileError> {
    let end = offset
        .checked_add(4)
        .ok_or(CompileError::Invalid("record offset overflow"))?;
    bytes
        .get_mut(offset..end)
        .ok_or(CompileError::Invalid("record write outside buffer"))?
        .copy_from_slice(&value.to_le_bytes());
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::compile_source;
    use exactscope_kernel::{Decimal64, ScalarValue, Status, SEMANTIC_PRICE, SEMANTIC_QUANTITY};
    use exactscope_pack::PackView;

    const SOURCE: &str = include_str!("../../../spec/examples/econ-undergrad-minimal.xsp.json");

    #[test]
    fn compilation_is_reproducible_and_runtime_valid() {
        let first = compile_source(SOURCE).expect("compile first");
        let second = compile_source(SOURCE).expect("compile second");
        assert_eq!(first, second);
        let pack = PackView::parse(&first).expect("runtime parse");
        assert_eq!(pack.pack_id(), Ok("org.exactscope.econ-undergrad"));
        assert_eq!(pack.version(), Ok((0, 1, 0)));
        assert_eq!(pack.operation_count(), 1);
    }

    #[test]
    fn dynamic_result_matches_expected_economics_value() {
        let bytes = compile_source(SOURCE).expect("compile");
        let pack = PackView::parse(&bytes).expect("parse");
        let operation = pack.operation_by_key(b"econ.ped.mid").expect("lookup");
        let arguments = [
            scalar(b"10000", SEMANTIC_PRICE),
            scalar(b"12000", SEMANTIC_PRICE),
            scalar(b"100", SEMANTIC_QUANTITY),
            scalar(b"80", SEMANTIC_QUANTITY),
        ];
        let result = pack.evaluate(7, operation, &arguments).expect("evaluate");
        assert_eq!(result.status, Status::OK);
        assert_eq!(result.pack_slot, 7);
        assert_eq!(result.operation_id, 301);
        assert_eq!(result.classification_id, 3);
        assert_eq!(
            result.values[0].decimal,
            Decimal64::from_parts(-1_222_222, -6).unwrap()
        );
        assert_eq!(
            pack.classification_key(operation, result.classification_id),
            Ok("elastic")
        );
    }

    #[test]
    fn every_truncated_compiled_pack_is_rejected() {
        let bytes = compile_source(SOURCE).expect("compile");
        for length in 0..bytes.len() {
            assert!(
                PackView::parse(&bytes[..length]).is_err(),
                "accepted truncation at {length}"
            );
        }
    }

    #[test]
    fn integrity_corruption_is_detected() {
        let mut bytes = compile_source(SOURCE).expect("compile");
        let last = bytes.len() - 1;
        bytes[last] ^= 0x01;
        assert_eq!(
            PackView::parse(&bytes).unwrap_err(),
            Status::INTEGRITY_ERROR
        );
    }

    fn scalar(text: &[u8], semantic: u8) -> ScalarValue {
        ScalarValue::new(Decimal64::parse_ascii(text).unwrap(), semantic, 0)
    }
}
