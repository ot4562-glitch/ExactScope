#![no_std]
#![forbid(unsafe_code)]
#![doc = "Deterministic, allocator-free ExactScope numeric kernel."]

#[cfg(test)]
extern crate std;

mod decimal;
mod evaluate;
mod operation;
mod rational;
mod rounding;
mod semantic;
mod status;
mod vm;

pub use decimal::{Decimal64, MAX_DECIMAL_EXPONENT, MAX_DECIMAL_TEXT_BYTES, MIN_DECIMAL_EXPONENT};
pub use evaluate::{
    evaluate_operation, EvaluationResult, ResultValue, ARGUMENT_INDEX_NONE, MAX_RESULT_VALUES,
};
pub use operation::{
    classification_key, ClassificationDecl, ConstraintKind, InputDecl, OperationDecl,
    PED_MID_OPERATION,
};
pub use rational::{RoundedDecimal, WorkRational};
pub use rounding::RoundingMode;
pub use semantic::{
    validate_same_unit, ScalarValue, SEMANTIC_COUNT, SEMANTIC_CURRENCY_AMOUNT, SEMANTIC_ELASTICITY,
    SEMANTIC_INDEX, SEMANTIC_NUMBER, SEMANTIC_PRICE, SEMANTIC_PROBABILITY, SEMANTIC_QUANTITY,
    SEMANTIC_RATE_PERCENT, SEMANTIC_RATE_RATIO, SEMANTIC_TIME_PERIODS, VALUE_FLAGS_V1,
    VALUE_FLAG_INEXACT, VALUE_FLAG_ROUNDED,
};
pub use status::Status;
pub use vm::{
    execute_formula, execute_predicate, validate_program, Instruction, ProgramKind,
    MAX_VM_INSTRUCTIONS, MAX_VM_STACK,
};

/// ABI major implemented by the first runtime slice.
pub const DESIGN_ABI_MAJOR: u16 = 1;
/// ABI minor implemented by the first runtime slice.
pub const DESIGN_ABI_MINOR: u16 = 0;
