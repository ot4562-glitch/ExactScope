//! Bounded non-Turing-complete scalar formula VM.

use core::cmp::Ordering;

use crate::{Status, WorkRational};

/// Maximum v0.1 scalar program length.
pub const MAX_VM_INSTRUCTIONS: usize = 64;
/// Maximum v0.1 scalar stack depth.
pub const MAX_VM_STACK: usize = 16;

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

/// Validates one bounded program before execution.
///
/// # Errors
///
/// Returns a stable pack/resource status when opcodes, operands, types, stack
/// effects, or termination are invalid.
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
            4 | 5 | 6 | 7 => {
                require_zero_operand(*instruction)?;
                pop_type(&stack, &mut depth, ValueType::Number)?;
                pop_type(&stack, &mut depth, ValueType::Number)?;
                push_type(&mut stack, &mut depth, ValueType::Number)?;
            }
            9 => {
                require_zero_operand(*instruction)?;
                pop_type(&stack, &mut depth, ValueType::Number)?;
                push_type(&mut stack, &mut depth, ValueType::Number)?;
            }
            14 | 16 | 18 => {
                require_zero_operand(*instruction)?;
                pop_type(&stack, &mut depth, ValueType::Number)?;
                pop_type(&stack, &mut depth, ValueType::Number)?;
                push_type(&mut stack, &mut depth, ValueType::Boolean)?;
            }
            8 | 10..=13 | 15 | 17 | 19..=23 => return Err(Status::UNSUPPORTED_OPERATION),
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
    validate_program(
        instructions,
        ProgramKind::Formula,
        arguments.len(),
        constants.len(),
        0,
    )?;
    match execute(
        instructions,
        ProgramKind::Formula,
        arguments,
        constants,
        &[],
    )? {
        VmValue::Number(value) => Ok(value),
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
    )? {
        VmValue::Boolean(value) => Ok(value),
        VmValue::Number(_) => Err(Status::INTERNAL_ERROR),
    }
}

fn execute(
    instructions: &[Instruction],
    kind: ProgramKind,
    arguments: &[WorkRational],
    constants: &[WorkRational],
    results: &[WorkRational],
) -> Result<VmValue, Status> {
    let mut stack = [VmValue::EMPTY; MAX_VM_STACK];
    let mut depth = 0usize;

    for instruction in instructions {
        match instruction.opcode {
            0 => return pop_value(&stack, &mut depth),
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
            9 => {
                let value = pop_number(&stack, &mut depth)?;
                push_value(
                    &mut stack,
                    &mut depth,
                    VmValue::Number(value.checked_abs()?),
                )?;
            }
            14 | 16 | 18 => {
                let rhs = pop_number(&stack, &mut depth)?;
                let lhs = pop_number(&stack, &mut depth)?;
                let order = lhs.checked_cmp(rhs)?;
                let value = match instruction.opcode {
                    14 => order == Ordering::Less,
                    16 => order == Ordering::Equal,
                    18 => order == Ordering::Greater,
                    _ => return Err(Status::INTERNAL_ERROR),
                };
                push_value(&mut stack, &mut depth, VmValue::Boolean(value))?;
            }
            8 | 10..=13 | 15 | 17 | 19..=23 => return Err(Status::UNSUPPORTED_OPERATION),
            _ => return Err(Status::PACK_INVALID),
        }
    }

    Err(Status::PACK_INVALID)
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

#[cfg(test)]
mod tests {
    use super::{execute_formula, execute_predicate, validate_program, Instruction, ProgramKind};
    use crate::{Status, WorkRational};

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
    fn invalid_stack_and_future_opcodes_fail_closed() {
        let underflow = [Instruction::new(4, 0), Instruction::new(0, 0)];
        assert_eq!(
            validate_program(&underflow, ProgramKind::Formula, 0, 0, 0),
            Err(Status::PACK_INVALID)
        );
        let unsupported = [Instruction::new(8, 0), Instruction::new(0, 0)];
        assert_eq!(
            validate_program(&unsupported, ProgramKind::Formula, 0, 0, 0),
            Err(Status::UNSUPPORTED_OPERATION)
        );
    }
}
