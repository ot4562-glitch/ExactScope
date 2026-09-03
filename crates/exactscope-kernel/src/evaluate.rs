//! Typed deterministic evaluation pipeline.

use core::cmp::Ordering;

use crate::{
    execute_formula, execute_predicate, validate_same_unit, ConstraintKind, Decimal64,
    OperationDecl, RuntimeOperation, ScalarValue, Status, WorkRational, VALUE_FLAGS_V1,
    VALUE_FLAG_ROUNDED,
};

/// Sentinel when an error does not identify a positional argument.
pub const ARGUMENT_INDEX_NONE: u16 = u16::MAX;
/// Maximum scalar outputs in ABI major 1.
pub const MAX_RESULT_VALUES: usize = 4;

/// One typed scalar result value.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ResultValue {
    /// Canonical decimal output.
    pub decimal: Decimal64,
    /// Stable semantic kind.
    pub semantic_kind: u8,
    /// Output unit identity.
    pub unit_id: u16,
    /// Stable value flags.
    pub flags: u32,
}

impl ResultValue {
    const ZERO: Self = Self {
        decimal: Decimal64::ZERO,
        semantic_kind: 0,
        unit_id: 0,
        flags: 0,
    };
}

/// Fully initialized normalized evaluation result.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct EvaluationResult {
    /// Stable core status.
    pub status: Status,
    /// Aggregate result flags.
    pub flags: u16,
    /// Number of usable entries in `values`.
    pub value_count: u16,
    /// Operation-local deterministic classification ID.
    pub classification_id: u16,
    /// Fused/dynamic pack slot.
    pub pack_slot: u16,
    /// Immutable operation semantic revision.
    pub operation_revision: u16,
    /// Pack-local operation ID.
    pub operation_id: u32,
    /// Effective output decimal scale.
    pub output_scale: i8,
    /// Stable rounding mode ID.
    pub rounding_mode: u8,
    /// Operation-local error detail ID.
    pub detail_code: u16,
    /// Zero-based failing argument index or [`ARGUMENT_INDEX_NONE`].
    pub argument_index: u16,
    /// Required storage size for buffer-related failures.
    pub required_size: u32,
    /// Fixed result storage.
    pub values: [ResultValue; MAX_RESULT_VALUES],
}

impl EvaluationResult {
    /// Creates a fully zeroed failure tied to a known operation.
    #[must_use]
    pub fn failure(
        status: Status,
        pack_slot: u16,
        operation: &OperationDecl,
        argument_index: u16,
        detail_code: u16,
    ) -> Self {
        Self::failure_runtime(
            status,
            pack_slot,
            &operation.runtime(),
            argument_index,
            detail_code,
        )
    }

    /// Creates a fully zeroed failure tied to a borrowed runtime operation.
    #[must_use]
    pub fn failure_runtime(
        status: Status,
        pack_slot: u16,
        operation: &RuntimeOperation<'_>,
        argument_index: u16,
        detail_code: u16,
    ) -> Self {
        Self {
            status,
            flags: 0,
            value_count: 0,
            classification_id: 0,
            pack_slot,
            operation_revision: operation.revision,
            operation_id: operation.id,
            output_scale: i8::try_from(operation.output_scale).unwrap_or(0),
            rounding_mode: operation.rounding_mode.id(),
            detail_code,
            argument_index,
            required_size: 0,
            values: [ResultValue::ZERO; MAX_RESULT_VALUES],
        }
    }

    /// Creates a failure when no operation identity is known.
    #[must_use]
    pub const fn unidentified_failure(status: Status) -> Self {
        Self {
            status,
            flags: 0,
            value_count: 0,
            classification_id: 0,
            pack_slot: 0,
            operation_revision: 0,
            operation_id: 0,
            output_scale: 0,
            rounding_mode: 0,
            detail_code: 0,
            argument_index: ARGUMENT_INDEX_NONE,
            required_size: 0,
            values: [ResultValue::ZERO; MAX_RESULT_VALUES],
        }
    }
}

/// Evaluates one known scalar operation with deterministic validation order.
///
/// # Errors
///
/// This function never returns `Err`: failures are normalized into
/// [`EvaluationResult`] so ABI/wire adapters can preserve identical metadata.
#[must_use]
#[allow(clippy::too_many_lines)]
pub fn evaluate_runtime_operation<F>(
    pack_slot: u16,
    operation: &RuntimeOperation<'_>,
    arguments: &[ScalarValue],
    mut classifier: F,
) -> EvaluationResult
where
    F: FnMut(WorkRational) -> Result<u16, Status>,
{
    if arguments.len() != operation.inputs.len() {
        return EvaluationResult::failure_runtime(
            Status::ARGUMENT_COUNT,
            pack_slot,
            operation,
            ARGUMENT_INDEX_NONE,
            0,
        );
    }

    let mut work = [WorkRational::ZERO; 12];
    if arguments.len() > work.len() {
        return EvaluationResult::failure_runtime(
            Status::RESOURCE_LIMIT,
            pack_slot,
            operation,
            ARGUMENT_INDEX_NONE,
            0,
        );
    }

    for (index, (argument, declaration)) in
        arguments.iter().zip(operation.inputs.iter()).enumerate()
    {
        let argument_index = u16::try_from(index).unwrap_or(ARGUMENT_INDEX_NONE);
        if !argument.decimal.is_canonical() {
            return EvaluationResult::failure_runtime(
                Status::INVALID_DECIMAL,
                pack_slot,
                operation,
                argument_index,
                0,
            );
        }
        if argument.flags & !VALUE_FLAGS_V1 != 0 {
            return EvaluationResult::failure_runtime(
                Status::INVALID_REQUEST,
                pack_slot,
                operation,
                argument_index,
                0,
            );
        }
        if argument.semantic_kind != declaration.semantic_kind {
            return EvaluationResult::failure_runtime(
                Status::ARGUMENT_TYPE,
                pack_slot,
                operation,
                argument_index,
                0,
            );
        }
        if declaration.unit_required && argument.unit_id == 0 {
            return EvaluationResult::failure_runtime(
                Status::MISSING_INFORMATION,
                pack_slot,
                operation,
                argument_index,
                0,
            );
        }

        let value = match WorkRational::from_decimal(argument.decimal) {
            Ok(value) => value,
            Err(status) => {
                return EvaluationResult::failure_runtime(
                    status,
                    pack_slot,
                    operation,
                    argument_index,
                    0,
                );
            }
        };
        work[index] = value;
    }

    for (index, declaration) in operation.inputs.iter().enumerate() {
        let value = work[index];
        let ordering = match value.checked_cmp(declaration.constraint_value) {
            Ok(ordering) => ordering,
            Err(status) => {
                return EvaluationResult::failure_runtime(
                    status,
                    pack_slot,
                    operation,
                    u16::try_from(index).unwrap_or(ARGUMENT_INDEX_NONE),
                    declaration.detail_id,
                );
            }
        };
        let accepted = match declaration.constraint {
            ConstraintKind::GreaterThan => ordering == Ordering::Greater,
            ConstraintKind::GreaterOrEqual => {
                matches!(ordering, Ordering::Greater | Ordering::Equal)
            }
        };
        if !accepted {
            return EvaluationResult::failure_runtime(
                Status::CONSTRAINT_VIOLATION,
                pack_slot,
                operation,
                u16::try_from(index).unwrap_or(ARGUMENT_INDEX_NONE),
                declaration.detail_id,
            );
        }
    }

    for left in 0..operation.inputs.len() {
        let group = operation.inputs[left].same_unit_group;
        if group == 0 {
            continue;
        }
        for right in left + 1..operation.inputs.len() {
            if operation.inputs[right].same_unit_group != group {
                continue;
            }
            if let Err(status) =
                validate_same_unit(arguments[left].unit_id, arguments[right].unit_id)
            {
                return EvaluationResult::failure_runtime(
                    status,
                    pack_slot,
                    operation,
                    u16::try_from(right).unwrap_or(ARGUMENT_INDEX_NONE),
                    0,
                );
            }
        }
    }

    let exact = match execute_formula(
        operation.program,
        &work[..arguments.len()],
        operation.constants,
    ) {
        Ok(value) => value,
        Err(status) => {
            return EvaluationResult::failure_runtime(
                status,
                pack_slot,
                operation,
                ARGUMENT_INDEX_NONE,
                0,
            );
        }
    };

    let classification_id = match classifier(exact) {
        Ok(classification_id) => classification_id,
        Err(status) => {
            return EvaluationResult::failure_runtime(
                status,
                pack_slot,
                operation,
                ARGUMENT_INDEX_NONE,
                0,
            );
        }
    };
    if operation.classification_required && classification_id == 0 {
        return EvaluationResult::failure_runtime(
            Status::PRECISION_UNRESOLVED,
            pack_slot,
            operation,
            ARGUMENT_INDEX_NONE,
            0,
        );
    }

    let rounded = match exact.round_to_decimal(operation.output_scale, operation.rounding_mode) {
        Ok(value) => value,
        Err(status) => {
            return EvaluationResult::failure_runtime(
                status,
                pack_slot,
                operation,
                ARGUMENT_INDEX_NONE,
                0,
            );
        }
    };

    let value_flags = if rounded.rounded {
        VALUE_FLAG_ROUNDED
    } else {
        0
    };
    EvaluationResult {
        status: Status::OK,
        flags: u16::try_from(value_flags).unwrap_or(0),
        value_count: 1,
        classification_id,
        pack_slot,
        operation_revision: operation.revision,
        operation_id: operation.id,
        output_scale: i8::try_from(operation.output_scale).unwrap_or(0),
        rounding_mode: operation.rounding_mode.id(),
        detail_code: 0,
        argument_index: ARGUMENT_INDEX_NONE,
        required_size: 0,
        values: [
            ResultValue {
                decimal: rounded.value,
                semantic_kind: operation.output_semantic_kind,
                unit_id: 0,
                flags: value_flags,
            },
            ResultValue::ZERO,
            ResultValue::ZERO,
            ResultValue::ZERO,
        ],
    }
}

/// Evaluates one immutable fused operation through the shared runtime path.
#[must_use]
pub fn evaluate_operation(
    pack_slot: u16,
    operation: &OperationDecl,
    arguments: &[ScalarValue],
) -> EvaluationResult {
    let runtime = operation.runtime();
    evaluate_runtime_operation(pack_slot, &runtime, arguments, |exact| {
        let mut classification_id = 0u16;
        for classification in operation.classifications {
            match execute_predicate(classification.program, &[exact], operation.constants) {
                Ok(true) if classification_id == 0 => classification_id = classification.id,
                Ok(true) => return Err(Status::PACK_INVALID),
                Ok(false) => {}
                Err(status) => return Err(status),
            }
        }
        Ok(classification_id)
    })
}

#[cfg(test)]
mod tests {
    use super::evaluate_operation;
    use crate::{
        Decimal64, ScalarValue, Status, PED_MID_OPERATION, SEMANTIC_PRICE, SEMANTIC_QUANTITY,
        VALUE_FLAG_ROUNDED,
    };

    fn args(values: [&[u8]; 4]) -> [ScalarValue; 4] {
        [
            ScalarValue::new(
                Decimal64::parse_ascii(values[0]).unwrap(),
                SEMANTIC_PRICE,
                0,
            ),
            ScalarValue::new(
                Decimal64::parse_ascii(values[1]).unwrap(),
                SEMANTIC_PRICE,
                0,
            ),
            ScalarValue::new(
                Decimal64::parse_ascii(values[2]).unwrap(),
                SEMANTIC_QUANTITY,
                0,
            ),
            ScalarValue::new(
                Decimal64::parse_ascii(values[3]).unwrap(),
                SEMANTIC_QUANTITY,
                0,
            ),
        ]
    }

    fn render(result: &super::EvaluationResult) -> std::string::String {
        let mut buffer = [0u8; 64];
        let written = result.values[0]
            .decimal
            .write_canonical(&mut buffer)
            .unwrap();
        std::string::String::from(core::str::from_utf8(&buffer[..written]).unwrap())
    }

    #[test]
    fn economics_golden_vectors_match() {
        let cases = [
            (
                [b"10000".as_slice(), b"12000", b"100", b"80"],
                Status::OK,
                "-1.222222",
                3,
                true,
            ),
            (
                [b"10".as_slice(), b"20", b"20", b"10"],
                Status::OK,
                "-1",
                2,
                false,
            ),
            (
                [b"10".as_slice(), b"12", b"100", b"95"],
                Status::OK,
                "-0.282051",
                1,
                true,
            ),
        ];

        for (input, status, value, class, rounded) in cases {
            let result = evaluate_operation(1, &PED_MID_OPERATION, &args(input));
            assert_eq!(result.status, status);
            assert_eq!(render(&result), value);
            assert_eq!(result.classification_id, class);
            assert_eq!(result.values[0].flags & VALUE_FLAG_ROUNDED != 0, rounded);
        }
    }

    #[test]
    fn failure_precedence_is_deterministic() {
        let unchanged =
            evaluate_operation(1, &PED_MID_OPERATION, &args([b"10", b"10", b"100", b"80"]));
        assert_eq!(unchanged.status, Status::DIVIDE_BY_ZERO);
        assert_eq!(unchanged.value_count, 0);

        let negative =
            evaluate_operation(1, &PED_MID_OPERATION, &args([b"-1", b"10", b"100", b"80"]));
        assert_eq!(negative.status, Status::CONSTRAINT_VIOLATION);
        assert_eq!(negative.argument_index, 0);
        assert_eq!(negative.detail_code, 1);
        assert_eq!(negative.value_count, 0);
    }

    #[test]
    fn constraint_precedes_unit_mismatch() {
        let mut values = args([b"-1", b"10", b"100", b"80"]);
        values[0].unit_id = 1;
        values[1].unit_id = 2;
        let result = evaluate_operation(1, &PED_MID_OPERATION, &values);
        assert_eq!(result.status, Status::CONSTRAINT_VIOLATION);

        values[0].decimal = Decimal64::parse_ascii(b"1").unwrap();
        let result = evaluate_operation(1, &PED_MID_OPERATION, &values);
        assert_eq!(result.status, Status::UNIT_MISMATCH);
        assert_eq!(result.argument_index, 1);
    }
}
