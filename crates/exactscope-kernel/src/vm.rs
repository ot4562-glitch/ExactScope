//! Bounded non-Turing-complete scalar formula VM.

use core::cmp::Ordering;

use crate::{RoundingMode, Status, WorkRational, VALUE_FLAG_INEXACT, VALUE_FLAG_ROUNDED};

/// Maximum v0.1 scalar program length.
pub const MAX_VM_INSTRUCTIONS: usize = 64;
/// Maximum v0.1 scalar stack depth.
pub const MAX_VM_STACK: usize = 16;
/// Low-byte mask for the explicit-round scale operand.
pub const ROUND_SCALE_MASK: i32 = 0xff;
/// Bit shift for the explicit-round mode operand.
pub const ROUND_MODE_SHIFT: u32 = 8;
/// Bits reserved above the v0.1 explicit-round fields.
pub const ROUND_RESERVED_MASK: i32 = 0x007f_0000;

/// One compact VM instruction.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Instruction {
    /// Stable opcode ID from `spec/registries/vm-opcodes.json`.
    pub opcode: u8,
    /// Signed operand storage. Unsigned operands must be nonnegative.
    pub operand: i32,
}

impl Instruction {
    /// Constructs an instruction.
    #[must_use]
    pub const fn new(opcode: u8, operand: i32) -> Self {
        Self { opcode, operand }
    }
}

/// Program execution domain.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProgramKind {
    /// Produces one numeric formula result.
    Formula,
    /// Produces one boolean classification predicate.
    Classification,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ValueType {
    Number,
    Boolean,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum VmValue {
    Number(WorkRational),
    Boolean(bool),
}

impl VmValue {
    const EMPTY: Self = Self::Number(WorkRational::ZERO);
}

/// Numeric result and aggregate intermediate flags from formula execution.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct FormulaExecution {
    /// Exact rational value, or the canonical rational representation of an
    /// explicitly rounded/square-root intermediate.
    pub value: WorkRational,
    /// Stable `VALUE_FLAG_*` bits accumulated by non-exact VM instructions.
    pub flags: u32,
}

/// Validates one bounded program before execution.
///
/// # Errors
///
/// Returns a stable pack/resource status when opcodes, operands, types, stack
/// effects, or termination are invalid.
#[allow(clippy::too_many_lines)]
pub fn validate_program(
    instructions: &[Instruction],
    kind: ProgramKind,
    argument_count: usize,
    constant_count: usize,
    result_count: usize,
) -> Result<usize, Status> {
    if instructions.is_empty() || instructions.len() > MAX_VM_INSTRUCTIONS {
        return Err(Status::RESOURCE_LIMIT);
    }
    if instructions.last().map(|instruction| instruction.opcode) != Some(0) {
        return Err(Status::PACK_INVALID);
    }

    let mut stack = [ValueType::Number; MAX_VM_STACK];
    let mut depth = 0usize;
    let mut maximum_depth = 0usize;

    for (index, instruction) in instructions.iter().enumerate() {
        if instruction.opcode == 0 {
            if index + 1 != instructions.len() || instruction.operand != 0 || depth != 1 {
                return Err(Status::PACK_INVALID);
            }
            let expected = match kind {
                ProgramKind::Formula => ValueType::Number,
                ProgramKind::Classification => ValueType::Boolean,
            };
            if stack[0] != expected {
                return Err(Status::PACK_INVALID);
            }
            return Ok(maximum_depth);
        }

        match instruction.opcode {
            1 => {
                if kind != ProgramKind::Formula {
                    return Err(Status::PACK_INVALID);
                }
                let argument = checked_index(instruction.operand, argument_count)?;
                let _ = argument;
                push_type(&mut stack, &mut depth, ValueType::Number)?;
            }
            2 => {
                let constant = checked_index(instruction.operand, constant_count)?;
                let _ = constant;
                push_type(&mut stack, &mut depth, ValueType::Number)?;
            }
            3 => {
                if kind != ProgramKind::Classification {
                    return Err(Status::PACK_INVALID);
                }
                let result = checked_index(instruction.operand, result_count)?;
                let _ = result;
                push_type(&mut stack, &mut depth, ValueType::Number)?;
            }
            4..=7 | 10 | 11 => {
                require_zero_operand(*instruction)?;
                pop_type(&stack, &mut depth, ValueType::Number)?;
                pop_type(&stack, &mut depth, ValueType::Number)?;
                push_type(&mut stack, &mut depth, ValueType::Number)?;
            }
            8 | 9 => {
                require_zero_operand(*instruction)?;
                pop_type(&stack, &mut depth, ValueType::Number)?;
                push_type(&mut stack, &mut depth, ValueType::Number)?;
            }
            12 => {
                if !(-32..=32).contains(&instruction.operand) {
                    return Err(Status::PACK_INVALID);
                }
                pop_type(&stack, &mut depth, ValueType::Number)?;
                push_type(&mut stack, &mut depth, ValueType::Number)?;
            }
            14..=18 => {
                require_zero_operand(*instruction)?;
                pop_type(&stack, &mut depth, ValueType::Number)?;
                pop_type(&stack, &mut depth, ValueType::Number)?;
                push_type(&mut stack, &mut depth, ValueType::Boolean)?;
            }
            19 | 20 => {
                require_zero_operand(*instruction)?;
                pop_type(&stack, &mut depth, ValueType::Boolean)?;
                pop_type(&stack, &mut depth, ValueType::Boolean)?;
                push_type(&mut stack, &mut depth, ValueType::Boolean)?;
            }
            21 => {
                require_zero_operand(*instruction)?;
                pop_type(&stack, &mut depth, ValueType::Boolean)?;
                push_type(&mut stack, &mut depth, ValueType::Boolean)?;
            }
            22 => {
                require_zero_operand(*instruction)?;
                pop_type(&stack, &mut depth, ValueType::Number)?;
                pop_type(&stack, &mut depth, ValueType::Number)?;
                pop_type(&stack, &mut depth, ValueType::Boolean)?;
                push_type(&mut stack, &mut depth, ValueType::Number)?;
            }
            13 => {
                if kind != ProgramKind::Formula {
                    return Err(Status::PACK_INVALID);
                }
                require_zero_operand(*instruction)?;
                pop_type(&stack, &mut depth, ValueType::Number)?;
                push_type(&mut stack, &mut depth, ValueType::Number)?;
            }
            23 => {
                if kind != ProgramKind::Formula {
                    return Err(Status::PACK_INVALID);
                }
                decode_round_operand(instruction.operand)?;
                pop_type(&stack, &mut depth, ValueType::Number)?;
                push_type(&mut stack, &mut depth, ValueType::Number)?;
            }
            _ => return Err(Status::PACK_INVALID),
        }
        maximum_depth = maximum_depth.max(depth);
    }

    Err(Status::PACK_INVALID)
}

/// Executes one previously valid formula program.
///
/// Validation is repeated intentionally because dynamic pack bytes are an
/// untrusted boundary in later milestones.
///
/// # Errors
///
/// Returns a stable validation or arithmetic status.
pub fn execute_formula(
    instructions: &[Instruction],
    arguments: &[WorkRational],
    constants: &[WorkRational],
) -> Result<WorkRational, Status> {
    Ok(execute_formula_with_policy(
        instructions,
        arguments,
        constants,
        18,
        RoundingMode::HalfEven,
    )?
    .value)
}

/// Executes a formula with the operation's active output scale and rounding mode.
///
/// Square root uses this policy. Explicit `round` instructions carry their own
/// validated policy and contribute stable rounded/inexact flags.
///
/// # Errors
///
/// Returns a stable validation, domain, resource, or arithmetic status.
pub fn execute_formula_with_policy(
    instructions: &[Instruction],
    arguments: &[WorkRational],
    constants: &[WorkRational],
    output_scale: u8,
    rounding_mode: RoundingMode,
) -> Result<FormulaExecution, Status> {
    validate_program(
        instructions,
        ProgramKind::Formula,
        arguments.len(),
        constants.len(),
        0,
    )?;
    let execution = execute(
        instructions,
        ProgramKind::Formula,
        arguments,
        constants,
        &[],
        output_scale,
        rounding_mode,
    )?;
    match execution.value {
        VmValue::Number(value) => Ok(FormulaExecution {
            value,
            flags: execution.flags,
        }),
        VmValue::Boolean(_) => Err(Status::INTERNAL_ERROR),
    }
}

/// Executes one classification predicate over unrounded formula results.
///
/// # Errors
///
/// Returns a stable validation, arithmetic, or precision status.
pub fn execute_predicate(
    instructions: &[Instruction],
    results: &[WorkRational],
    constants: &[WorkRational],
) -> Result<bool, Status> {
    validate_program(
        instructions,
        ProgramKind::Classification,
        0,
        constants.len(),
        results.len(),
    )?;
    match execute(
        instructions,
        ProgramKind::Classification,
        &[],
        constants,
        results,
        0,
        RoundingMode::HalfEven,
    )?
    .value
    {
        VmValue::Boolean(value) => Ok(value),
        VmValue::Number(_) => Err(Status::INTERNAL_ERROR),
    }
}

#[allow(clippy::too_many_lines)]
fn execute(
    instructions: &[Instruction],
    kind: ProgramKind,
    arguments: &[WorkRational],
    constants: &[WorkRational],
    results: &[WorkRational],
    output_scale: u8,
    rounding_mode: RoundingMode,
) -> Result<VmExecution, Status> {
    let mut stack = [VmValue::EMPTY; MAX_VM_STACK];
    let mut depth = 0usize;
    let mut flags = 0u32;

    for instruction in instructions {
        match instruction.opcode {
            0 => {
                return Ok(VmExecution {
                    value: pop_value(&stack, &mut depth)?,
                    flags,
                })
            }
            1 => {
                if kind != ProgramKind::Formula {
                    return Err(Status::PACK_INVALID);
                }
                let index = checked_index(instruction.operand, arguments.len())?;
                push_value(&mut stack, &mut depth, VmValue::Number(arguments[index]))?;
            }
            2 => {
                let index = checked_index(instruction.operand, constants.len())?;
                push_value(&mut stack, &mut depth, VmValue::Number(constants[index]))?;
            }
            3 => {
                if kind != ProgramKind::Classification {
                    return Err(Status::PACK_INVALID);
                }
                let index = checked_index(instruction.operand, results.len())?;
                push_value(&mut stack, &mut depth, VmValue::Number(results[index]))?;
            }
            4 => {
                let rhs = pop_number(&stack, &mut depth)?;
                let lhs = pop_number(&stack, &mut depth)?;
                push_value(
                    &mut stack,
                    &mut depth,
                    VmValue::Number(lhs.checked_add(rhs)?),
                )?;
            }
            5 => {
                let rhs = pop_number(&stack, &mut depth)?;
                let lhs = pop_number(&stack, &mut depth)?;
                push_value(
                    &mut stack,
                    &mut depth,
                    VmValue::Number(lhs.checked_sub(rhs)?),
                )?;
            }
            6 => {
                let rhs = pop_number(&stack, &mut depth)?;
                let lhs = pop_number(&stack, &mut depth)?;
                push_value(
                    &mut stack,
                    &mut depth,
                    VmValue::Number(lhs.checked_mul(rhs)?),
                )?;
            }
            7 => {
                let rhs = pop_number(&stack, &mut depth)?;
                let lhs = pop_number(&stack, &mut depth)?;
                push_value(
                    &mut stack,
                    &mut depth,
                    VmValue::Number(lhs.checked_div(rhs)?),
                )?;
            }
            8 => {
                let value = pop_number(&stack, &mut depth)?;
                push_value(
                    &mut stack,
                    &mut depth,
                    VmValue::Number(value.checked_neg()?),
                )?;
            }
            9 => {
                let value = pop_number(&stack, &mut depth)?;
                push_value(
                    &mut stack,
                    &mut depth,
                    VmValue::Number(value.checked_abs()?),
                )?;
            }
            10 | 11 => {
                let rhs = pop_number(&stack, &mut depth)?;
                let lhs = pop_number(&stack, &mut depth)?;
                let order = lhs.checked_cmp(rhs)?;
                let value = if instruction.opcode == 10 {
                    if matches!(order, Ordering::Less | Ordering::Equal) {
                        lhs
                    } else {
                        rhs
                    }
                } else if matches!(order, Ordering::Greater | Ordering::Equal) {
                    lhs
                } else {
                    rhs
                };
                push_value(&mut stack, &mut depth, VmValue::Number(value))?;
            }
            12 => {
                let value = pop_number(&stack, &mut depth)?;
                push_value(
                    &mut stack,
                    &mut depth,
                    VmValue::Number(value.checked_powi(instruction.operand)?),
                )?;
            }
            13 => {
                let value = pop_number(&stack, &mut depth)?;
                let result = value.sqrt_to_decimal(output_scale, rounding_mode)?;
                if result.rounded {
                    flags |= VALUE_FLAG_ROUNDED;
                }
                if result.inexact {
                    flags |= VALUE_FLAG_INEXACT;
                }
                push_value(
                    &mut stack,
                    &mut depth,
                    VmValue::Number(WorkRational::from_decimal(result.value)?),
                )?;
            }
            14..=18 => {
                let rhs = pop_number(&stack, &mut depth)?;
                let lhs = pop_number(&stack, &mut depth)?;
                let order = lhs.checked_cmp(rhs)?;
                let value = match instruction.opcode {
                    14 => order == Ordering::Less,
                    15 => matches!(order, Ordering::Less | Ordering::Equal),
                    16 => order == Ordering::Equal,
                    17 => matches!(order, Ordering::Greater | Ordering::Equal),
                    18 => order == Ordering::Greater,
                    _ => return Err(Status::INTERNAL_ERROR),
                };
                push_value(&mut stack, &mut depth, VmValue::Boolean(value))?;
            }
            19 | 20 => {
                let rhs = pop_boolean(&stack, &mut depth)?;
                let lhs = pop_boolean(&stack, &mut depth)?;
                let value = if instruction.opcode == 19 {
                    lhs && rhs
                } else {
                    lhs || rhs
                };
                push_value(&mut stack, &mut depth, VmValue::Boolean(value))?;
            }
            21 => {
                let value = pop_boolean(&stack, &mut depth)?;
                push_value(&mut stack, &mut depth, VmValue::Boolean(!value))?;
            }
            22 => {
                let when_false = pop_number(&stack, &mut depth)?;
                let when_true = pop_number(&stack, &mut depth)?;
                let condition = pop_boolean(&stack, &mut depth)?;
                push_value(
                    &mut stack,
                    &mut depth,
                    VmValue::Number(if condition { when_true } else { when_false }),
                )?;
            }
            23 => {
                let (scale, mode) = decode_round_operand(instruction.operand)?;
                let value = pop_number(&stack, &mut depth)?;
                let result = value.round_to_decimal(scale, mode)?;
                if result.rounded {
                    flags |= VALUE_FLAG_ROUNDED;
                }
                push_value(
                    &mut stack,
                    &mut depth,
                    VmValue::Number(WorkRational::from_decimal(result.value)?),
                )?;
            }
            _ => return Err(Status::PACK_INVALID),
        }
    }

    Err(Status::PACK_INVALID)
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct VmExecution {
    value: VmValue,
    flags: u32,
}

/// Encodes the two v0.1 explicit-round fields into one signed 24-bit operand.
///
/// # Errors
///
/// Returns [`Status::INVALID_REQUEST`] for a scale above 18.
pub fn encode_round_operand(scale: u8, mode: RoundingMode) -> Result<i32, Status> {
    if scale > 18 {
        return Err(Status::INVALID_REQUEST);
    }
    Ok(i32::from(scale) | (i32::from(mode.id()) << ROUND_MODE_SHIFT))
}

/// Decodes and validates one v0.1 explicit-round operand.
///
/// # Errors
///
/// Returns [`Status::PACK_INVALID`] for reserved bits, an unsupported scale, or
/// an unknown rounding-mode ID.
pub fn decode_round_operand(operand: i32) -> Result<(u8, RoundingMode), Status> {
    if operand < 0 || operand & ROUND_RESERVED_MASK != 0 {
        return Err(Status::PACK_INVALID);
    }
    let scale = u8::try_from(operand & ROUND_SCALE_MASK).map_err(|_| Status::PACK_INVALID)?;
    if scale > 18 {
        return Err(Status::PACK_INVALID);
    }
    let mode_id =
        u8::try_from((operand >> ROUND_MODE_SHIFT) & 0xff).map_err(|_| Status::PACK_INVALID)?;
    let Ok(mode) = RoundingMode::from_id(mode_id) else {
        return Err(Status::PACK_INVALID);
    };
    Ok((scale, mode))
}

fn checked_index(operand: i32, length: usize) -> Result<usize, Status> {
    let index = usize::try_from(operand).map_err(|_| Status::PACK_INVALID)?;
    if index >= length {
        Err(Status::PACK_INVALID)
    } else {
        Ok(index)
    }
}

fn require_zero_operand(instruction: Instruction) -> Result<(), Status> {
    if instruction.operand == 0 {
        Ok(())
    } else {
        Err(Status::PACK_INVALID)
    }
}

fn push_type(
    stack: &mut [ValueType; MAX_VM_STACK],
    depth: &mut usize,
    value: ValueType,
) -> Result<(), Status> {
    if *depth >= stack.len() {
        return Err(Status::RESOURCE_LIMIT);
    }
    stack[*depth] = value;
    *depth += 1;
    Ok(())
}

fn pop_type(
    stack: &[ValueType; MAX_VM_STACK],
    depth: &mut usize,
    expected: ValueType,
) -> Result<(), Status> {
    if *depth == 0 {
        return Err(Status::PACK_INVALID);
    }
    *depth -= 1;
    if stack[*depth] == expected {
        Ok(())
    } else {
        Err(Status::PACK_INVALID)
    }
}

fn push_value(
    stack: &mut [VmValue; MAX_VM_STACK],
    depth: &mut usize,
    value: VmValue,
) -> Result<(), Status> {
    if *depth >= stack.len() {
        return Err(Status::RESOURCE_LIMIT);
    }
    stack[*depth] = value;
    *depth += 1;
    Ok(())
}

fn pop_value(stack: &[VmValue; MAX_VM_STACK], depth: &mut usize) -> Result<VmValue, Status> {
    if *depth == 0 {
        return Err(Status::PACK_INVALID);
    }
    *depth -= 1;
    Ok(stack[*depth])
}

fn pop_number(stack: &[VmValue; MAX_VM_STACK], depth: &mut usize) -> Result<WorkRational, Status> {
    match pop_value(stack, depth)? {
        VmValue::Number(value) => Ok(value),
        VmValue::Boolean(_) => Err(Status::PACK_INVALID),
    }
}

fn pop_boolean(stack: &[VmValue; MAX_VM_STACK], depth: &mut usize) -> Result<bool, Status> {
    match pop_value(stack, depth)? {
        VmValue::Boolean(value) => Ok(value),
        VmValue::Number(_) => Err(Status::PACK_INVALID),
    }
}

#[cfg(test)]
mod tests {
    use super::{
        encode_round_operand, execute_formula, execute_formula_with_policy, execute_predicate,
        validate_program, Instruction, ProgramKind,
    };
    use crate::{RoundingMode, Status, WorkRational, VALUE_FLAG_INEXACT, VALUE_FLAG_ROUNDED};

    #[test]
    fn formula_executes_exactly() {
        let program = [
            Instruction::new(1, 0),
            Instruction::new(2, 0),
            Instruction::new(5, 0),
            Instruction::new(0, 0),
        ];
        assert_eq!(
            validate_program(&program, ProgramKind::Formula, 1, 1, 0),
            Ok(2)
        );
        assert_eq!(
            execute_formula(&program, &[WorkRational::ONE], &[WorkRational::ONE]),
            Ok(WorkRational::ZERO)
        );
    }

    #[test]
    fn classification_compares_exact_result() {
        let program = [
            Instruction::new(3, 0),
            Instruction::new(9, 0),
            Instruction::new(2, 0),
            Instruction::new(18, 0),
            Instruction::new(0, 0),
        ];
        let result = WorkRational::new(-11, 10).unwrap();
        assert_eq!(
            execute_predicate(&program, &[result], &[WorkRational::ONE]),
            Ok(true)
        );
    }

    #[test]
    fn extended_numeric_vm_ops_remain_exact() {
        let power = [
            Instruction::new(1, 0),
            Instruction::new(12, -2),
            Instruction::new(0, 0),
        ];
        assert_eq!(
            execute_formula(&power, &[WorkRational::new(2, 3).unwrap()], &[]),
            Ok(WorkRational::new(9, 4).unwrap())
        );

        let select = [
            Instruction::new(1, 0),
            Instruction::new(2, 0),
            Instruction::new(17, 0),
            Instruction::new(2, 1),
            Instruction::new(2, 2),
            Instruction::new(22, 0),
            Instruction::new(0, 0),
        ];
        let constants = [
            WorkRational::from_integer(10),
            WorkRational::from_integer(1),
            WorkRational::from_integer(-1),
        ];
        assert_eq!(
            execute_formula(&select, &[WorkRational::from_integer(12)], &constants),
            Ok(WorkRational::ONE)
        );
        assert_eq!(
            execute_formula(&select, &[WorkRational::from_integer(8)], &constants),
            Ok(WorkRational::from_integer(-1))
        );
    }

    #[test]
    fn boolean_predicates_compose_deterministically() {
        let between = [
            Instruction::new(3, 0),
            Instruction::new(2, 0),
            Instruction::new(17, 0),
            Instruction::new(3, 0),
            Instruction::new(2, 1),
            Instruction::new(15, 0),
            Instruction::new(19, 0),
            Instruction::new(0, 0),
        ];
        let constants = [
            WorkRational::from_integer(10),
            WorkRational::from_integer(20),
        ];
        assert_eq!(
            execute_predicate(&between, &[WorkRational::from_integer(15)], &constants),
            Ok(true)
        );
        assert_eq!(
            execute_predicate(&between, &[WorkRational::from_integer(21)], &constants),
            Ok(false)
        );
    }

    #[test]
    fn invalid_stack_ranges_and_unknown_opcodes_fail_closed() {
        let underflow = [Instruction::new(4, 0), Instruction::new(0, 0)];
        assert_eq!(
            validate_program(&underflow, ProgramKind::Formula, 0, 0, 0),
            Err(Status::PACK_INVALID)
        );

        let invalid_power = [
            Instruction::new(1, 0),
            Instruction::new(12, 33),
            Instruction::new(0, 0),
        ];
        assert_eq!(
            validate_program(&invalid_power, ProgramKind::Formula, 1, 0, 0),
            Err(Status::PACK_INVALID)
        );

        let unknown = [
            Instruction::new(1, 0),
            Instruction::new(24, 0),
            Instruction::new(0, 0),
        ];
        assert_eq!(
            validate_program(&unknown, ProgramKind::Formula, 1, 0, 0),
            Err(Status::PACK_INVALID)
        );
    }

    #[test]
    fn sqrt_and_explicit_round_share_deterministic_decimal_quantization() {
        let sqrt = [
            Instruction::new(1, 0),
            Instruction::new(13, 0),
            Instruction::new(0, 0),
        ];
        let execution = execute_formula_with_policy(
            &sqrt,
            &[WorkRational::from_integer(2)],
            &[],
            6,
            RoundingMode::HalfEven,
        )
        .unwrap();
        assert_eq!(
            execution.value,
            WorkRational::new(707_107, 500_000).unwrap()
        );
        assert_ne!(execution.flags & VALUE_FLAG_ROUNDED, 0);
        assert_ne!(execution.flags & VALUE_FLAG_INEXACT, 0);

        let round = [
            Instruction::new(1, 0),
            Instruction::new(23, encode_round_operand(2, RoundingMode::HalfEven).unwrap()),
            Instruction::new(0, 0),
        ];
        let rounded = execute_formula_with_policy(
            &round,
            &[WorkRational::new(1, 8).unwrap()],
            &[],
            6,
            RoundingMode::HalfAway,
        )
        .unwrap();
        assert_eq!(rounded.value, WorkRational::new(3, 25).unwrap());
        assert_eq!(rounded.flags, VALUE_FLAG_ROUNDED);
    }

    #[test]
    fn malformed_round_operands_fail_validation() {
        for operand in [19, 5 << 8, 1 << 16, -1] {
            let program = [
                Instruction::new(1, 0),
                Instruction::new(23, operand),
                Instruction::new(0, 0),
            ];
            assert_eq!(
                validate_program(&program, ProgramKind::Formula, 1, 0, 0),
                Err(Status::PACK_INVALID)
            );
        }
    }
}
