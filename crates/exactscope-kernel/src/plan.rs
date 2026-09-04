//! Bounded deterministic arithmetic-plan execution for tiny model-facing use.

use crate::{
    Decimal64, RoundingMode, Status, WorkRational, VALUE_FLAG_INEXACT, VALUE_FLAG_ROUNDED,
};

/// Maximum number of arithmetic steps accepted by the v0.1 plan contract.
pub const MAX_PLAN_STEPS: usize = 8;
/// Maximum number of operands carried by one plan step.
pub const MAX_PLAN_ARGUMENTS: usize = 2;
/// Sentinel used when a failure is not attributable to one concrete step.
pub const PLAN_STEP_INDEX_NONE: u8 = u8::MAX;
/// Maximum decimal fractional scale attempted for generic plan results.
pub const PLAN_MAX_OUTPUT_SCALE: u8 = 18;
/// Public integer-power exponent bound for the first plan contract.
pub const PLAN_MAX_ABS_POWI_EXPONENT: i32 = 32;

/// One operation in the bounded arithmetic-plan vocabulary.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PlanOperation {
    /// Checked exact addition.
    Add,
    /// Checked exact subtraction.
    Sub,
    /// Checked exact multiplication.
    Mul,
    /// Checked exact division.
    Div,
    /// Checked integer power. The second operand must resolve to an integer in
    /// `-32..=32`.
    Powi,
    /// Deterministic square root. Exactly one operand is accepted.
    Sqrt,
}

impl PlanOperation {
    /// Required operand count for this operation.
    #[must_use]
    pub const fn argument_count(self) -> u8 {
        match self {
            Self::Sqrt => 1,
            Self::Add | Self::Sub | Self::Mul | Self::Div | Self::Powi => 2,
        }
    }
}

/// One operand in a bounded arithmetic plan.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PlanValue {
    /// Exact canonical decimal literal supplied by the caller/model.
    Literal(Decimal64),
    /// Zero-based result of an earlier plan step.
    Previous(u8),
}

impl PlanValue {
    /// Fixed placeholder used for unused operand slots.
    pub const ZERO: Self = Self::Literal(Decimal64::ZERO);
}

/// One validated-shape plan step.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PlanStep {
    /// Arithmetic operation.
    pub operation: PlanOperation,
    /// Fixed operand storage; only the first `argument_count` entries are used.
    pub arguments: [PlanValue; MAX_PLAN_ARGUMENTS],
    /// Number of populated operands.
    pub argument_count: u8,
}

impl PlanStep {
    /// Fixed placeholder used by bounded parsers before a step is populated.
    pub const EMPTY: Self = Self {
        operation: PlanOperation::Add,
        arguments: [PlanValue::ZERO; MAX_PLAN_ARGUMENTS],
        argument_count: 0,
    };

    /// Creates one step. Semantic validation occurs during plan evaluation.
    #[must_use]
    pub const fn new(
        operation: PlanOperation,
        arguments: [PlanValue; MAX_PLAN_ARGUMENTS],
        argument_count: u8,
    ) -> Self {
        Self {
            operation,
            arguments,
            argument_count,
        }
    }
}

/// Successful bounded-plan execution.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PlanResult {
    /// Canonical decimal result of the final step.
    pub value: Decimal64,
    /// Aggregate stable `VALUE_FLAG_*` bits from deterministic quantization.
    pub flags: u32,
    /// Number of executed plan steps.
    pub step_count: u8,
}

/// Typed bounded-plan failure.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PlanFailure {
    /// Stable core status.
    pub status: Status,
    /// Failing zero-based step, or [`PLAN_STEP_INDEX_NONE`].
    pub step_index: u8,
}

impl PlanFailure {
    const fn global(status: Status) -> Self {
        Self {
            status,
            step_index: PLAN_STEP_INDEX_NONE,
        }
    }

    fn at(status: Status, step_index: usize) -> Self {
        Self {
            status,
            step_index: u8::try_from(step_index).unwrap_or(PLAN_STEP_INDEX_NONE),
        }
    }
}

/// Executes one bounded arithmetic plan using the shared exact numeric
/// primitives used by the formula VM.
///
/// Arithmetic remains exact in `WorkRational` form between steps except for an
/// irrational square root, which is deterministically quantized at the highest
/// supported decimal scale that fits `Decimal64`. The final result uses the
/// same bounded highest-fitting-scale policy with half-even rounding.
///
/// # Errors
///
/// Returns a typed [`PlanFailure`] for malformed resource shape, invalid prior
/// references, operation argument mismatch, domain/division failures, bounded
/// overflow, or unsupported integer-power exponents.
pub fn evaluate_plan(steps: &[PlanStep]) -> Result<PlanResult, PlanFailure> {
    if steps.is_empty() {
        return Err(PlanFailure::global(Status::INVALID_REQUEST));
    }
    if steps.len() > MAX_PLAN_STEPS {
        return Err(PlanFailure::global(Status::RESOURCE_LIMIT));
    }

    let mut results = [WorkRational::ZERO; MAX_PLAN_STEPS];
    let mut aggregate_flags = 0u32;

    for (step_index, step) in steps.iter().enumerate() {
        if step.argument_count != step.operation.argument_count() {
            return Err(PlanFailure::at(Status::ARGUMENT_COUNT, step_index));
        }
        if usize::from(step.argument_count) > MAX_PLAN_ARGUMENTS {
            return Err(PlanFailure::at(Status::RESOURCE_LIMIT, step_index));
        }

        let left = resolve_value(step.arguments[0], &results, step_index)
            .map_err(|status| PlanFailure::at(status, step_index))?;
        let value = match step.operation {
            PlanOperation::Add => {
                let right = resolve_value(step.arguments[1], &results, step_index)
                    .map_err(|status| PlanFailure::at(status, step_index))?;
                left.checked_add(right)
            }
            PlanOperation::Sub => {
                let right = resolve_value(step.arguments[1], &results, step_index)
                    .map_err(|status| PlanFailure::at(status, step_index))?;
                left.checked_sub(right)
            }
            PlanOperation::Mul => {
                let right = resolve_value(step.arguments[1], &results, step_index)
                    .map_err(|status| PlanFailure::at(status, step_index))?;
                left.checked_mul(right)
            }
            PlanOperation::Div => {
                let right = resolve_value(step.arguments[1], &results, step_index)
                    .map_err(|status| PlanFailure::at(status, step_index))?;
                left.checked_div(right)
            }
            PlanOperation::Powi => {
                let exponent_value = resolve_value(step.arguments[1], &results, step_index)
                    .map_err(|status| PlanFailure::at(status, step_index))?;
                let exponent = powi_exponent(exponent_value)
                    .map_err(|status| PlanFailure::at(status, step_index))?;
                left.checked_powi(exponent)
            }
            PlanOperation::Sqrt => {
                let (value, flags) = sqrt_max_precision(left)
                    .map_err(|status| PlanFailure::at(status, step_index))?;
                aggregate_flags |= flags;
                Ok(value)
            }
        }
        .map_err(|status| PlanFailure::at(status, step_index))?;

        results[step_index] = value;
    }

    let final_value = results[steps.len() - 1];
    let (value, final_flags) = decimal_max_precision(final_value)
        .map_err(|status| PlanFailure::at(status, steps.len() - 1))?;
    aggregate_flags |= final_flags;

    Ok(PlanResult {
        value,
        flags: aggregate_flags,
        step_count: u8::try_from(steps.len())
            .map_err(|_| PlanFailure::global(Status::RESOURCE_LIMIT))?,
    })
}

fn resolve_value(
    value: PlanValue,
    previous: &[WorkRational; MAX_PLAN_STEPS],
    current_step: usize,
) -> Result<WorkRational, Status> {
    match value {
        PlanValue::Literal(decimal) => WorkRational::from_decimal(decimal),
        PlanValue::Previous(index) => {
            let index = usize::from(index);
            if index >= current_step {
                return Err(Status::INVALID_REQUEST);
            }
            Ok(previous[index])
        }
    }
}

fn powi_exponent(value: WorkRational) -> Result<i32, Status> {
    if value.denominator() != 1 {
        return Err(Status::ARGUMENT_TYPE);
    }
    let exponent = i32::try_from(value.numerator()).map_err(|_| Status::CONSTRAINT_VIOLATION)?;
    if !(-PLAN_MAX_ABS_POWI_EXPONENT..=PLAN_MAX_ABS_POWI_EXPONENT).contains(&exponent) {
        return Err(Status::CONSTRAINT_VIOLATION);
    }
    Ok(exponent)
}

fn decimal_max_precision(value: WorkRational) -> Result<(Decimal64, u32), Status> {
    let mut scale = PLAN_MAX_OUTPUT_SCALE;
    loop {
        match value.round_to_decimal(scale, RoundingMode::HalfEven) {
            Ok(rounded) => {
                let flags = if rounded.rounded {
                    VALUE_FLAG_ROUNDED
                } else {
                    0
                };
                return Ok((rounded.value, flags));
            }
            Err(Status::OVERFLOW) if scale != 0 => scale -= 1,
            Err(status) => return Err(status),
        }
    }
}

fn sqrt_max_precision(value: WorkRational) -> Result<(WorkRational, u32), Status> {
    let mut scale = PLAN_MAX_OUTPUT_SCALE;
    loop {
        match value.sqrt_to_decimal(scale, RoundingMode::HalfEven) {
            Ok(result) => {
                let mut flags = 0;
                if result.rounded {
                    flags |= VALUE_FLAG_ROUNDED;
                }
                if result.inexact {
                    flags |= VALUE_FLAG_INEXACT;
                }
                return Ok((WorkRational::from_decimal(result.value)?, flags));
            }
            Err(Status::OVERFLOW) if scale != 0 => scale -= 1,
            Err(status) => return Err(status),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{evaluate_plan, PlanOperation, PlanStep, PlanValue, MAX_PLAN_STEPS};
    use crate::{Decimal64, Status, VALUE_FLAG_INEXACT, VALUE_FLAG_ROUNDED};

    fn decimal(text: &[u8]) -> Decimal64 {
        Decimal64::parse_ascii(text).unwrap()
    }

    fn binary(operation: PlanOperation, left: PlanValue, right: PlanValue) -> PlanStep {
        PlanStep::new(operation, [left, right], 2)
    }

    #[test]
    fn executes_exact_multi_step_plan_without_intermediate_rounding() {
        let steps = [
            binary(
                PlanOperation::Mul,
                PlanValue::Literal(decimal(b"12")),
                PlanValue::Literal(decimal(b"7")),
            ),
            binary(
                PlanOperation::Sub,
                PlanValue::Previous(0),
                PlanValue::Literal(decimal(b"4")),
            ),
            binary(
                PlanOperation::Div,
                PlanValue::Previous(1),
                PlanValue::Literal(decimal(b"5")),
            ),
        ];
        let result = evaluate_plan(&steps).unwrap();
        assert_eq!(result.value, decimal(b"16"));
        assert_eq!(result.flags, 0);
        assert_eq!(result.step_count, 3);
    }

    #[test]
    fn preserves_rational_precision_until_final_quantization() {
        let steps = [
            binary(
                PlanOperation::Div,
                PlanValue::Literal(decimal(b"1")),
                PlanValue::Literal(decimal(b"3")),
            ),
            binary(
                PlanOperation::Mul,
                PlanValue::Previous(0),
                PlanValue::Literal(decimal(b"3")),
            ),
        ];
        let result = evaluate_plan(&steps).unwrap();
        assert_eq!(result.value, decimal(b"1"));
        assert_eq!(result.flags, 0);
    }

    #[test]
    fn rounds_non_terminating_final_result_deterministically() {
        let steps = [binary(
            PlanOperation::Div,
            PlanValue::Literal(decimal(b"1")),
            PlanValue::Literal(decimal(b"3")),
        )];
        let result = evaluate_plan(&steps).unwrap();
        assert_eq!(result.value, decimal(b"0.333333333333333333"));
        assert_eq!(result.flags & VALUE_FLAG_ROUNDED, VALUE_FLAG_ROUNDED);
    }

    #[test]
    fn sqrt_is_bounded_and_marks_inexact() {
        let steps = [PlanStep::new(
            PlanOperation::Sqrt,
            [PlanValue::Literal(decimal(b"2")), PlanValue::ZERO],
            1,
        )];
        let result = evaluate_plan(&steps).unwrap();
        assert_eq!(result.value, decimal(b"1.414213562373095049"));
        assert_eq!(result.flags & VALUE_FLAG_INEXACT, VALUE_FLAG_INEXACT);
        assert_eq!(result.flags & VALUE_FLAG_ROUNDED, VALUE_FLAG_ROUNDED);
    }

    #[test]
    fn powi_accepts_only_bounded_integer_exponents() {
        let valid = [binary(
            PlanOperation::Powi,
            PlanValue::Literal(decimal(b"2")),
            PlanValue::Literal(decimal(b"10")),
        )];
        assert_eq!(evaluate_plan(&valid).unwrap().value, decimal(b"1024"));

        let fractional = [binary(
            PlanOperation::Powi,
            PlanValue::Literal(decimal(b"2")),
            PlanValue::Literal(decimal(b"1.5")),
        )];
        assert_eq!(
            evaluate_plan(&fractional).unwrap_err().status,
            Status::ARGUMENT_TYPE
        );

        let too_large = [binary(
            PlanOperation::Powi,
            PlanValue::Literal(decimal(b"2")),
            PlanValue::Literal(decimal(b"33")),
        )];
        assert_eq!(
            evaluate_plan(&too_large).unwrap_err().status,
            Status::CONSTRAINT_VIOLATION
        );
    }

    #[test]
    fn rejects_forward_reference_and_domain_errors() {
        let forward = [binary(
            PlanOperation::Add,
            PlanValue::Previous(0),
            PlanValue::Literal(decimal(b"1")),
        )];
        let failure = evaluate_plan(&forward).unwrap_err();
        assert_eq!(failure.status, Status::INVALID_REQUEST);
        assert_eq!(failure.step_index, 0);

        let div_zero = [binary(
            PlanOperation::Div,
            PlanValue::Literal(decimal(b"1")),
            PlanValue::Literal(decimal(b"0")),
        )];
        assert_eq!(
            evaluate_plan(&div_zero).unwrap_err().status,
            Status::DIVIDE_BY_ZERO
        );

        let sqrt_negative = [PlanStep::new(
            PlanOperation::Sqrt,
            [PlanValue::Literal(decimal(b"-1")), PlanValue::ZERO],
            1,
        )];
        assert_eq!(
            evaluate_plan(&sqrt_negative).unwrap_err().status,
            Status::DOMAIN_ERROR
        );
    }

    #[test]
    fn enforces_plan_resource_and_argument_bounds() {
        assert_eq!(
            evaluate_plan(&[]).unwrap_err().status,
            Status::INVALID_REQUEST
        );

        let step = binary(
            PlanOperation::Add,
            PlanValue::Literal(decimal(b"1")),
            PlanValue::Literal(decimal(b"1")),
        );
        let too_many = [step; MAX_PLAN_STEPS + 1];
        assert_eq!(
            evaluate_plan(&too_many).unwrap_err().status,
            Status::RESOURCE_LIMIT
        );

        let wrong_arity = [PlanStep::new(
            PlanOperation::Sqrt,
            [
                PlanValue::Literal(decimal(b"4")),
                PlanValue::Literal(decimal(b"2")),
            ],
            2,
        )];
        assert_eq!(
            evaluate_plan(&wrong_arity).unwrap_err().status,
            Status::ARGUMENT_COUNT
        );
    }
}
