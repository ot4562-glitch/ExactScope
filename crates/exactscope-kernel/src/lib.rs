#![no_std]
#![forbid(unsafe_code)]
#![doc = "Deterministic, allocator-free `ExactScope` numeric kernel."]

#[cfg(test)]
extern crate std;

mod decimal;
mod econ_formula;
mod evaluate;
mod operation;
mod rational;
mod rounding;
mod semantic;
mod stats;
mod status;
mod vm;

pub use decimal::{Decimal64, MAX_DECIMAL_EXPONENT, MAX_DECIMAL_TEXT_BYTES, MIN_DECIMAL_EXPONENT};
pub use econ_formula::{
    CPI_INFLATION_PCT_OPERATION, DOUBLING_RULE70_OPERATION, DOUBLING_RULE72_OPERATION,
    GDP_DEFLATOR100_OPERATION, GROWTH_RATE_PCT_OPERATION, MONEY_VELOCITY_OPERATION,
    MPC_RATIO_OPERATION, MPS_RATIO_OPERATION, OFFICIAL_ECON_OPERATIONS, OPPORTUNITY_COST_OPERATION,
    OUTPUT_GAP_PCT_OPERATION, PER_CAPITA_GROWTH_APPROX_PCT_OPERATION,
    REAL_RATE_APPROX_PCT_OPERATION, REAL_RATE_EXACT_PCT_OPERATION,
    TERMS_OF_TRADE_INDEX100_OPERATION,
};
pub use evaluate::{
    evaluate_operation, evaluate_runtime_operation, EvaluationResult, ResultValue,
    ARGUMENT_INDEX_NONE, MAX_RESULT_VALUES,
};
pub use operation::{
    classification_key, ClassificationDecl, ConstraintKind, InputDecl, OperationDecl,
    RuntimeOperation, PED_MID_OPERATION,
};
pub use rational::{RoundedDecimal, SqrtDecimal, WorkRational};
pub use rounding::RoundingMode;
pub use semantic::{
    validate_same_unit, ScalarValue, SEMANTIC_COUNT, SEMANTIC_CURRENCY_AMOUNT, SEMANTIC_ELASTICITY,
    SEMANTIC_INDEX, SEMANTIC_NUMBER, SEMANTIC_PRICE, SEMANTIC_PROBABILITY, SEMANTIC_QUANTITY,
    SEMANTIC_RATE_PERCENT, SEMANTIC_RATE_RATIO, SEMANTIC_TIME_PERIODS, VALUE_FLAGS_V1,
    VALUE_FLAG_INEXACT, VALUE_FLAG_ROUNDED,
};
pub use stats::{
    evaluate_statistics_operation, statistics_kernel_contract, statistics_linear_regression,
    statistics_mean, statistics_pearson_correlation, statistics_population_covariance,
    statistics_population_standard_deviation, statistics_population_variance,
    statistics_sample_covariance, statistics_sample_standard_deviation, statistics_sample_variance,
    statistics_sum, statistics_weighted_mean, DecimalVector, LinearRegression,
    StatisticsKernelContract, StatisticsOperationDecl, MAX_STATS_VECTOR_LEN,
    OFFICIAL_STATS_OPERATIONS, STATS_CORRELATION_PEARSON_OPERATION,
    STATS_COVARIANCE_POPULATION_OPERATION, STATS_COVARIANCE_SAMPLE_OPERATION,
    STATS_KERNEL_CORRELATION, STATS_KERNEL_COVARIANCE_POPULATION, STATS_KERNEL_COVARIANCE_SAMPLE,
    STATS_KERNEL_LINEAR_REGRESSION, STATS_KERNEL_MEAN, STATS_KERNEL_STANDARD_DEVIATION_POPULATION,
    STATS_KERNEL_STANDARD_DEVIATION_SAMPLE, STATS_KERNEL_SUM, STATS_KERNEL_VARIANCE_POPULATION,
    STATS_KERNEL_VARIANCE_SAMPLE, STATS_KERNEL_WEIGHTED_MEAN, STATS_LINEAR_REGRESSION_OPERATION,
    STATS_MEAN_OPERATION, STATS_STANDARD_DEVIATION_POPULATION_OPERATION,
    STATS_STANDARD_DEVIATION_SAMPLE_OPERATION, STATS_SUM_OPERATION,
    STATS_VARIANCE_POPULATION_OPERATION, STATS_VARIANCE_SAMPLE_OPERATION,
    STATS_WEIGHTED_MEAN_OPERATION,
};
pub use status::Status;
pub use vm::{
    decode_round_operand, encode_round_operand, execute_formula, execute_formula_with_policy,
    execute_predicate, validate_program, FormulaExecution, Instruction, ProgramKind,
    MAX_VM_INSTRUCTIONS, MAX_VM_STACK, ROUND_MODE_SHIFT, ROUND_RESERVED_MASK, ROUND_SCALE_MASK,
};

/// ABI major implemented by the first runtime slice.
pub const DESIGN_ABI_MAJOR: u16 = 1;
/// ABI minor implemented by the first runtime slice.
pub const DESIGN_ABI_MINOR: u16 = 0;
