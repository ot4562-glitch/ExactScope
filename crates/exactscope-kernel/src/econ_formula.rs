//! Deterministic scalar economics operations beyond the first PED slice.
//!
//! These declarations intentionally reuse the same bounded rational VM as the
//! original midpoint elasticity implementation. They are executable runtime
//! operations, not catalog-only metadata.

use crate::operation::PED_MID_OPERATION;
use crate::{
    ConstraintKind, InputDecl, Instruction, OperationDecl, RoundingMode, WorkRational,
    SEMANTIC_CURRENCY_AMOUNT, SEMANTIC_INDEX, SEMANTIC_NUMBER, SEMANTIC_QUANTITY,
    SEMANTIC_RATE_PERCENT, SEMANTIC_RATE_RATIO, SEMANTIC_TIME_PERIODS,
};

const ZERO: WorkRational = WorkRational::ZERO;
const NEG_HUNDRED: WorkRational = WorkRational::from_integer(-100);
const HUNDRED: WorkRational = WorkRational::from_integer(100);

const CONSTANT_100: [WorkRational; 1] = [HUNDRED];
const CONSTANT_70: [WorkRational; 1] = [WorkRational::from_integer(70)];
const CONSTANT_72: [WorkRational; 1] = [WorkRational::from_integer(72)];
const NO_CONSTANTS: [WorkRational; 0] = [];
const NO_CLASSIFICATIONS: [crate::ClassificationDecl; 0] = [];

const fn input(
    name: &'static str,
    semantic_kind: u8,
    same_unit_group: u8,
    constraint: ConstraintKind,
    constraint_value: WorkRational,
    detail_id: u16,
) -> InputDecl {
    InputDecl {
        name,
        semantic_kind,
        same_unit_group,
        unit_required: false,
        constraint,
        constraint_value,
        detail_id,
    }
}

const GDP_DEFLATOR_INPUTS: [InputDecl; 2] = [
    input(
        "nominal_gdp",
        SEMANTIC_CURRENCY_AMOUNT,
        1,
        ConstraintKind::None,
        ZERO,
        0,
    ),
    input(
        "real_gdp",
        SEMANTIC_CURRENCY_AMOUNT,
        1,
        ConstraintKind::GreaterThan,
        ZERO,
        2,
    ),
];
const GDP_DEFLATOR_PROGRAM: [Instruction; 6] = [
    Instruction::new(1, 0),
    Instruction::new(1, 1),
    Instruction::new(7, 0),
    Instruction::new(2, 0),
    Instruction::new(6, 0),
    Instruction::new(0, 0),
];

/// GDP deflator with base 100: `nominal_gdp / real_gdp * 100`.
pub static GDP_DEFLATOR100_OPERATION: OperationDecl = OperationDecl {
    id: 401,
    revision: 1,
    key: "econ.gdp.deflator100",
    signature: "econ.gdp.deflator100(nominal_gdp,real_gdp)",
    method: "deflator100",
    inputs: &GDP_DEFLATOR_INPUTS,
    constants: &CONSTANT_100,
    program: &GDP_DEFLATOR_PROGRAM,
    classifications: &NO_CLASSIFICATIONS,
    output_semantic_kind: SEMANTIC_INDEX,
    output_scale: 6,
    rounding_mode: RoundingMode::HalfEven,
};

const CPI_INFLATION_INPUTS: [InputDecl; 2] = [
    input(
        "cpi1",
        SEMANTIC_INDEX,
        1,
        ConstraintKind::GreaterThan,
        ZERO,
        1,
    ),
    input(
        "cpi2",
        SEMANTIC_INDEX,
        1,
        ConstraintKind::GreaterOrEqual,
        ZERO,
        2,
    ),
];
const CPI_INFLATION_PROGRAM: [Instruction; 8] = [
    Instruction::new(1, 1),
    Instruction::new(1, 0),
    Instruction::new(5, 0),
    Instruction::new(1, 0),
    Instruction::new(7, 0),
    Instruction::new(2, 0),
    Instruction::new(6, 0),
    Instruction::new(0, 0),
];

/// CPI inflation rate in percentage points.
pub static CPI_INFLATION_PCT_OPERATION: OperationDecl = OperationDecl {
    id: 404,
    revision: 1,
    key: "econ.inflation.cpi_pct",
    signature: "econ.inflation.cpi_pct(cpi1,cpi2)",
    method: "cpi",
    inputs: &CPI_INFLATION_INPUTS,
    constants: &CONSTANT_100,
    program: &CPI_INFLATION_PROGRAM,
    classifications: &NO_CLASSIFICATIONS,
    output_semantic_kind: SEMANTIC_RATE_PERCENT,
    output_scale: 6,
    rounding_mode: RoundingMode::HalfEven,
};

const MONEY_VELOCITY_INPUTS: [InputDecl; 2] = [
    input(
        "nominal_gdp",
        SEMANTIC_CURRENCY_AMOUNT,
        1,
        ConstraintKind::None,
        ZERO,
        0,
    ),
    input(
        "money_supply",
        SEMANTIC_CURRENCY_AMOUNT,
        1,
        ConstraintKind::GreaterThan,
        ZERO,
        2,
    ),
];
const SIMPLE_RATIO_PROGRAM: [Instruction; 4] = [
    Instruction::new(1, 0),
    Instruction::new(1, 1),
    Instruction::new(7, 0),
    Instruction::new(0, 0),
];

/// Quantity-equation money velocity: `nominal_gdp / money_supply`.
pub static MONEY_VELOCITY_OPERATION: OperationDecl = OperationDecl {
    id: 413,
    revision: 1,
    key: "econ.money.velocity",
    signature: "econ.money.velocity(nominal_gdp,money_supply)",
    method: "quantity_equation",
    inputs: &MONEY_VELOCITY_INPUTS,
    constants: &NO_CONSTANTS,
    program: &SIMPLE_RATIO_PROGRAM,
    classifications: &NO_CLASSIFICATIONS,
    output_semantic_kind: SEMANTIC_NUMBER,
    output_scale: 6,
    rounding_mode: RoundingMode::HalfEven,
};

const REAL_RATE_EXACT_INPUTS: [InputDecl; 2] = [
    input(
        "nominal_pct",
        SEMANTIC_RATE_PERCENT,
        0,
        ConstraintKind::None,
        ZERO,
        0,
    ),
    input(
        "inflation_pct",
        SEMANTIC_RATE_PERCENT,
        0,
        ConstraintKind::GreaterThan,
        NEG_HUNDRED,
        2,
    ),
];
const REAL_RATE_EXACT_PROGRAM: [Instruction; 12] = [
    Instruction::new(2, 0),
    Instruction::new(1, 0),
    Instruction::new(4, 0),
    Instruction::new(2, 0),
    Instruction::new(6, 0),
    Instruction::new(2, 0),
    Instruction::new(1, 1),
    Instruction::new(4, 0),
    Instruction::new(7, 0),
    Instruction::new(2, 0),
    Instruction::new(5, 0),
    Instruction::new(0, 0),
];

/// Exact Fisher real-rate identity in percentage points.
pub static REAL_RATE_EXACT_PCT_OPERATION: OperationDecl = OperationDecl {
    id: 417,
    revision: 1,
    key: "econ.rate.real.exact_pct",
    signature: "econ.rate.real.exact_pct(nominal_pct,inflation_pct)",
    method: "fisher_exact",
    inputs: &REAL_RATE_EXACT_INPUTS,
    constants: &CONSTANT_100,
    program: &REAL_RATE_EXACT_PROGRAM,
    classifications: &NO_CLASSIFICATIONS,
    output_semantic_kind: SEMANTIC_RATE_PERCENT,
    output_scale: 6,
    rounding_mode: RoundingMode::HalfEven,
};

const REAL_RATE_APPROX_INPUTS: [InputDecl; 2] = [
    input(
        "nominal_pct",
        SEMANTIC_RATE_PERCENT,
        0,
        ConstraintKind::None,
        ZERO,
        0,
    ),
    input(
        "inflation_pct",
        SEMANTIC_RATE_PERCENT,
        0,
        ConstraintKind::None,
        ZERO,
        0,
    ),
];
const SUBTRACT_PROGRAM: [Instruction; 4] = [
    Instruction::new(1, 0),
    Instruction::new(1, 1),
    Instruction::new(5, 0),
    Instruction::new(0, 0),
];

/// Explicit Fisher approximation: `nominal_pct - inflation_pct`.
pub static REAL_RATE_APPROX_PCT_OPERATION: OperationDecl = OperationDecl {
    id: 418,
    revision: 1,
    key: "econ.rate.real.approx_pct",
    signature: "econ.rate.real.approx_pct(nominal_pct,inflation_pct)",
    method: "fisher_approx",
    inputs: &REAL_RATE_APPROX_INPUTS,
    constants: &NO_CONSTANTS,
    program: &SUBTRACT_PROGRAM,
    classifications: &NO_CLASSIFICATIONS,
    output_semantic_kind: SEMANTIC_RATE_PERCENT,
    output_scale: 6,
    rounding_mode: RoundingMode::HalfEven,
};

const OUTPUT_GAP_INPUTS: [InputDecl; 2] = [
    input(
        "actual_output",
        SEMANTIC_NUMBER,
        1,
        ConstraintKind::None,
        ZERO,
        0,
    ),
    input(
        "potential_output",
        SEMANTIC_NUMBER,
        1,
        ConstraintKind::GreaterThan,
        ZERO,
        2,
    ),
];
const OUTPUT_GAP_PROGRAM: [Instruction; 8] = [
    Instruction::new(1, 0),
    Instruction::new(1, 1),
    Instruction::new(5, 0),
    Instruction::new(1, 1),
    Instruction::new(7, 0),
    Instruction::new(2, 0),
    Instruction::new(6, 0),
    Instruction::new(0, 0),
];

/// Output gap as percentage of potential output.
pub static OUTPUT_GAP_PCT_OPERATION: OperationDecl = OperationDecl {
    id: 420,
    revision: 1,
    key: "econ.output_gap_pct",
    signature: "econ.output_gap_pct(actual_output,potential_output)",
    method: "potential_output_gap",
    inputs: &OUTPUT_GAP_INPUTS,
    constants: &CONSTANT_100,
    program: &OUTPUT_GAP_PROGRAM,
    classifications: &NO_CLASSIFICATIONS,
    output_semantic_kind: SEMANTIC_RATE_PERCENT,
    output_scale: 6,
    rounding_mode: RoundingMode::HalfEven,
};

const MPC_INPUTS: [InputDecl; 2] = [
    input(
        "delta_consumption",
        SEMANTIC_CURRENCY_AMOUNT,
        1,
        ConstraintKind::None,
        ZERO,
        0,
    ),
    input(
        "delta_income",
        SEMANTIC_CURRENCY_AMOUNT,
        1,
        ConstraintKind::NotEqual,
        ZERO,
        2,
    ),
];

/// Marginal propensity to consume ratio.
pub static MPC_RATIO_OPERATION: OperationDecl = OperationDecl {
    id: 421,
    revision: 1,
    key: "econ.mpc.ratio",
    signature: "econ.mpc.ratio(delta_consumption,delta_income)",
    method: "marginal_propensity",
    inputs: &MPC_INPUTS,
    constants: &NO_CONSTANTS,
    program: &SIMPLE_RATIO_PROGRAM,
    classifications: &NO_CLASSIFICATIONS,
    output_semantic_kind: SEMANTIC_RATE_RATIO,
    output_scale: 6,
    rounding_mode: RoundingMode::HalfEven,
};

const MPS_INPUTS: [InputDecl; 2] = [
    input(
        "delta_saving",
        SEMANTIC_CURRENCY_AMOUNT,
        1,
        ConstraintKind::None,
        ZERO,
        0,
    ),
    input(
        "delta_income",
        SEMANTIC_CURRENCY_AMOUNT,
        1,
        ConstraintKind::NotEqual,
        ZERO,
        2,
    ),
];

/// Marginal propensity to save ratio.
pub static MPS_RATIO_OPERATION: OperationDecl = OperationDecl {
    id: 422,
    revision: 1,
    key: "econ.mps.ratio",
    signature: "econ.mps.ratio(delta_saving,delta_income)",
    method: "marginal_propensity",
    inputs: &MPS_INPUTS,
    constants: &NO_CONSTANTS,
    program: &SIMPLE_RATIO_PROGRAM,
    classifications: &NO_CLASSIFICATIONS,
    output_semantic_kind: SEMANTIC_RATE_RATIO,
    output_scale: 6,
    rounding_mode: RoundingMode::HalfEven,
};

const TERMS_OF_TRADE_INPUTS: [InputDecl; 2] = [
    input(
        "export_price_index",
        SEMANTIC_INDEX,
        1,
        ConstraintKind::None,
        ZERO,
        0,
    ),
    input(
        "import_price_index",
        SEMANTIC_INDEX,
        1,
        ConstraintKind::GreaterThan,
        ZERO,
        2,
    ),
];

/// Terms of trade index with base 100.
pub static TERMS_OF_TRADE_INDEX100_OPERATION: OperationDecl = OperationDecl {
    id: 602,
    revision: 1,
    key: "econ.trade.terms_index100",
    signature: "econ.trade.terms_index100(export_price_index,import_price_index)",
    method: "index100",
    inputs: &TERMS_OF_TRADE_INPUTS,
    constants: &CONSTANT_100,
    program: &GDP_DEFLATOR_PROGRAM,
    classifications: &NO_CLASSIFICATIONS,
    output_semantic_kind: SEMANTIC_INDEX,
    output_scale: 6,
    rounding_mode: RoundingMode::HalfEven,
};

const OPPORTUNITY_COST_INPUTS: [InputDecl; 2] = [
    input(
        "units_forgone",
        SEMANTIC_QUANTITY,
        0,
        ConstraintKind::GreaterOrEqual,
        ZERO,
        1,
    ),
    input(
        "units_gained",
        SEMANTIC_QUANTITY,
        0,
        ConstraintKind::GreaterThan,
        ZERO,
        2,
    ),
];

/// Opportunity cost of one output in units of the forgone output.
pub static OPPORTUNITY_COST_OPERATION: OperationDecl = OperationDecl {
    id: 608,
    revision: 1,
    key: "econ.opportunity_cost.output",
    signature: "econ.opportunity_cost.output(units_forgone,units_gained)",
    method: "ratio",
    inputs: &OPPORTUNITY_COST_INPUTS,
    constants: &NO_CONSTANTS,
    program: &SIMPLE_RATIO_PROGRAM,
    classifications: &NO_CLASSIFICATIONS,
    output_semantic_kind: SEMANTIC_NUMBER,
    output_scale: 6,
    rounding_mode: RoundingMode::HalfEven,
};

const GROWTH_RATE_INPUTS: [InputDecl; 2] = [
    input(
        "initial",
        SEMANTIC_NUMBER,
        1,
        ConstraintKind::GreaterThan,
        ZERO,
        1,
    ),
    input("final", SEMANTIC_NUMBER, 1, ConstraintKind::None, ZERO, 0),
];
const GROWTH_RATE_PROGRAM: [Instruction; 8] = [
    Instruction::new(1, 1),
    Instruction::new(1, 0),
    Instruction::new(5, 0),
    Instruction::new(1, 0),
    Instruction::new(7, 0),
    Instruction::new(2, 0),
    Instruction::new(6, 0),
    Instruction::new(0, 0),
];

/// Percentage growth between two levels.
pub static GROWTH_RATE_PCT_OPERATION: OperationDecl = OperationDecl {
    id: 701,
    revision: 1,
    key: "econ.growth.rate_pct",
    signature: "econ.growth.rate_pct(initial,final)",
    method: "level_change",
    inputs: &GROWTH_RATE_INPUTS,
    constants: &CONSTANT_100,
    program: &GROWTH_RATE_PROGRAM,
    classifications: &NO_CLASSIFICATIONS,
    output_semantic_kind: SEMANTIC_RATE_PERCENT,
    output_scale: 6,
    rounding_mode: RoundingMode::HalfEven,
};

const DOUBLING_INPUTS: [InputDecl; 1] = [input(
    "growth_pct",
    SEMANTIC_RATE_PERCENT,
    0,
    ConstraintKind::GreaterThan,
    ZERO,
    1,
)];
const DOUBLING_PROGRAM: [Instruction; 4] = [
    Instruction::new(2, 0),
    Instruction::new(1, 0),
    Instruction::new(7, 0),
    Instruction::new(0, 0),
];

/// Rule-of-70 doubling-time approximation.
pub static DOUBLING_RULE70_OPERATION: OperationDecl = OperationDecl {
    id: 702,
    revision: 1,
    key: "econ.doubling.rule70",
    signature: "econ.doubling.rule70(growth_pct)",
    method: "rule70",
    inputs: &DOUBLING_INPUTS,
    constants: &CONSTANT_70,
    program: &DOUBLING_PROGRAM,
    classifications: &NO_CLASSIFICATIONS,
    output_semantic_kind: SEMANTIC_TIME_PERIODS,
    output_scale: 6,
    rounding_mode: RoundingMode::HalfEven,
};

/// Rule-of-72 doubling-time approximation.
pub static DOUBLING_RULE72_OPERATION: OperationDecl = OperationDecl {
    id: 703,
    revision: 1,
    key: "econ.doubling.rule72",
    signature: "econ.doubling.rule72(growth_pct)",
    method: "rule72",
    inputs: &DOUBLING_INPUTS,
    constants: &CONSTANT_72,
    program: &DOUBLING_PROGRAM,
    classifications: &NO_CLASSIFICATIONS,
    output_semantic_kind: SEMANTIC_TIME_PERIODS,
    output_scale: 6,
    rounding_mode: RoundingMode::HalfEven,
};

const PER_CAPITA_APPROX_INPUTS: [InputDecl; 2] = [
    input(
        "output_growth_pct",
        SEMANTIC_RATE_PERCENT,
        0,
        ConstraintKind::None,
        ZERO,
        0,
    ),
    input(
        "population_growth_pct",
        SEMANTIC_RATE_PERCENT,
        0,
        ConstraintKind::None,
        ZERO,
        0,
    ),
];

/// Approximate per-capita growth: output growth minus population growth.
pub static PER_CAPITA_GROWTH_APPROX_PCT_OPERATION: OperationDecl = OperationDecl {
    id: 705,
    revision: 1,
    key: "econ.growth.per_capita_approx_pct",
    signature: "econ.growth.per_capita_approx_pct(output_growth_pct,population_growth_pct)",
    method: "difference_approx",
    inputs: &PER_CAPITA_APPROX_INPUTS,
    constants: &NO_CONSTANTS,
    program: &SUBTRACT_PROGRAM,
    classifications: &NO_CLASSIFICATIONS,
    output_semantic_kind: SEMANTIC_RATE_PERCENT,
    output_scale: 6,
    rounding_mode: RoundingMode::HalfEven,
};

/// All currently executable fused economics operations.
pub const OFFICIAL_ECON_OPERATIONS: [&OperationDecl; 15] = [
    &PED_MID_OPERATION,
    &GDP_DEFLATOR100_OPERATION,
    &CPI_INFLATION_PCT_OPERATION,
    &MONEY_VELOCITY_OPERATION,
    &REAL_RATE_EXACT_PCT_OPERATION,
    &REAL_RATE_APPROX_PCT_OPERATION,
    &OUTPUT_GAP_PCT_OPERATION,
    &MPC_RATIO_OPERATION,
    &MPS_RATIO_OPERATION,
    &TERMS_OF_TRADE_INDEX100_OPERATION,
    &OPPORTUNITY_COST_OPERATION,
    &GROWTH_RATE_PCT_OPERATION,
    &DOUBLING_RULE70_OPERATION,
    &DOUBLING_RULE72_OPERATION,
    &PER_CAPITA_GROWTH_APPROX_PCT_OPERATION,
];

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{evaluate_operation, Decimal64, ScalarValue, Status};

    fn scalar(text: &[u8], semantic: u8, unit_id: u16) -> ScalarValue {
        ScalarValue::new(Decimal64::parse_ascii(text).unwrap(), semantic, unit_id)
    }

    #[test]
    fn executable_operation_ids_are_unique() {
        for (index, left) in OFFICIAL_ECON_OPERATIONS.iter().enumerate() {
            for right in OFFICIAL_ECON_OPERATIONS.iter().skip(index + 1) {
                assert_ne!(left.id, right.id);
                assert_ne!(left.key, right.key);
            }
        }
    }

    #[test]
    fn gdp_deflator_executes_exactly() {
        let args = [
            scalar(b"120", SEMANTIC_CURRENCY_AMOUNT, 7),
            scalar(b"100", SEMANTIC_CURRENCY_AMOUNT, 7),
        ];
        let result = evaluate_operation(1, &GDP_DEFLATOR100_OPERATION, &args);
        assert_eq!(result.status, Status::OK);
        assert_eq!(
            result.values[0].decimal,
            Decimal64::parse_ascii(b"120").unwrap()
        );
        assert_eq!(result.values[0].semantic_kind, SEMANTIC_INDEX);
    }

    #[test]
    fn cpi_inflation_executes_and_rounds_deterministically() {
        let args = [
            scalar(b"100", SEMANTIC_INDEX, 0),
            scalar(b"103.25", SEMANTIC_INDEX, 0),
        ];
        let result = evaluate_operation(1, &CPI_INFLATION_PCT_OPERATION, &args);
        assert_eq!(result.status, Status::OK);
        assert_eq!(
            result.values[0].decimal,
            Decimal64::parse_ascii(b"3.25").unwrap()
        );
    }

    #[test]
    fn real_rate_exact_uses_rational_math_not_float() {
        let args = [
            scalar(b"5", SEMANTIC_RATE_PERCENT, 0),
            scalar(b"2", SEMANTIC_RATE_PERCENT, 0),
        ];
        let result = evaluate_operation(1, &REAL_RATE_EXACT_PCT_OPERATION, &args);
        assert_eq!(result.status, Status::OK);
        assert_eq!(
            result.values[0].decimal,
            Decimal64::parse_ascii(b"2.941176").unwrap()
        );
    }

    #[test]
    fn mpc_allows_signed_changes_but_rejects_zero_income_change() {
        let signed = [
            scalar(b"-20", SEMANTIC_CURRENCY_AMOUNT, 9),
            scalar(b"-40", SEMANTIC_CURRENCY_AMOUNT, 9),
        ];
        let result = evaluate_operation(1, &MPC_RATIO_OPERATION, &signed);
        assert_eq!(result.status, Status::OK);
        assert_eq!(
            result.values[0].decimal,
            Decimal64::parse_ascii(b"0.5").unwrap()
        );

        let zero_income = [
            scalar(b"20", SEMANTIC_CURRENCY_AMOUNT, 9),
            scalar(b"0", SEMANTIC_CURRENCY_AMOUNT, 9),
        ];
        let result = evaluate_operation(1, &MPC_RATIO_OPERATION, &zero_income);
        assert_eq!(result.status, Status::CONSTRAINT_VIOLATION);
        assert_eq!(result.argument_index, 1);
    }

    #[test]
    fn rule70_and_rule72_are_distinct_executable_approximations() {
        let args = [scalar(b"7", SEMANTIC_RATE_PERCENT, 0)];
        let rule70 = evaluate_operation(1, &DOUBLING_RULE70_OPERATION, &args);
        let rule72 = evaluate_operation(1, &DOUBLING_RULE72_OPERATION, &args);
        assert_eq!(rule70.status, Status::OK);
        assert_eq!(rule72.status, Status::OK);
        assert_eq!(
            rule70.values[0].decimal,
            Decimal64::parse_ascii(b"10").unwrap()
        );
        assert_eq!(
            rule72.values[0].decimal,
            Decimal64::parse_ascii(b"10.285714").unwrap()
        );
    }
}
