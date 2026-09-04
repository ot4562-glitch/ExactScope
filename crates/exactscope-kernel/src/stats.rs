//! Deterministic allocator-free vector statistics kernels.
//!
//! The kernels in this module implement the exact-rational algorithms frozen in
//! `spec/NUMERIC_V0_1.md`. They deliberately stop before formatting, semantic
//! validation, or ABI translation so fused, dynamic-pack, C ABI, and Wasm paths
//! can share one numeric implementation.

use crate::{
    Decimal64, EvaluationResult, ResultValue, RoundingMode, SqrtDecimal, Status, WorkRational,
    ARGUMENT_INDEX_NONE, MAX_RESULT_VALUES, SEMANTIC_NUMBER, VALUE_FLAG_INEXACT,
    VALUE_FLAG_ROUNDED,
};

/// Global v0.1 statistics-vector limit.
pub const MAX_STATS_VECTOR_LEN: usize = 256;

/// Read-only decimal vector source used by deterministic statistics kernels.
///
/// Implementations may borrow normal Rust slices, C ABI arrays, shared-memory
/// views, or other immutable storage. The kernel never retains the source and
/// requests elements only in deterministic ascending index order.
pub trait DecimalVector {
    /// Returns the immutable vector length.
    fn len(&self) -> usize;

    /// Returns one canonical decimal element.
    ///
    /// # Errors
    ///
    /// Returns a stable validation status for malformed external storage.
    fn value_at(&self, index: usize) -> Result<Decimal64, Status>;

    /// Returns whether the vector is empty.
    #[must_use]
    fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

impl DecimalVector for [Decimal64] {
    fn len(&self) -> usize {
        <[Decimal64]>::len(self)
    }

    fn value_at(&self, index: usize) -> Result<Decimal64, Status> {
        self.get(index).copied().ok_or(Status::INTERNAL_ERROR)
    }
}

impl DecimalVector for &[Decimal64] {
    fn len(&self) -> usize {
        <[Decimal64]>::len(self)
    }

    fn value_at(&self, index: usize) -> Result<Decimal64, Status> {
        self.get(index).copied().ok_or(Status::INTERNAL_ERROR)
    }
}

/// Stable kernel ID for exact ordered sum.
pub const STATS_KERNEL_SUM: u16 = 1;
/// Stable kernel ID for arithmetic mean.
pub const STATS_KERNEL_MEAN: u16 = 2;
/// Stable kernel ID for weighted arithmetic mean.
pub const STATS_KERNEL_WEIGHTED_MEAN: u16 = 3;
/// Stable kernel ID for population variance.
pub const STATS_KERNEL_VARIANCE_POPULATION: u16 = 4;
/// Stable kernel ID for sample variance.
pub const STATS_KERNEL_VARIANCE_SAMPLE: u16 = 5;
/// Stable kernel ID for population covariance.
pub const STATS_KERNEL_COVARIANCE_POPULATION: u16 = 6;
/// Stable kernel ID for sample covariance.
pub const STATS_KERNEL_COVARIANCE_SAMPLE: u16 = 7;
/// Stable kernel ID for Pearson correlation. The implementation remains gated
/// on deterministic square-root completion.
pub const STATS_KERNEL_CORRELATION: u16 = 8;
/// Stable kernel ID for simple linear regression.
pub const STATS_KERNEL_LINEAR_REGRESSION: u16 = 9;
/// Stable kernel ID for population standard deviation.
pub const STATS_KERNEL_STANDARD_DEVIATION_POPULATION: u16 = 10;
/// Stable kernel ID for sample standard deviation.
pub const STATS_KERNEL_STANDARD_DEVIATION_SAMPLE: u16 = 11;

/// Stable arity contract for one built-in statistics kernel.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct StatisticsKernelContract {
    /// Required vector argument count.
    pub input_count: u8,
    /// Produced scalar result count.
    pub output_count: u8,
}

/// Returns the immutable v0.1 arity contract for a statistics kernel ID.
#[must_use]
pub const fn statistics_kernel_contract(kernel_id: u16) -> Option<StatisticsKernelContract> {
    let input_count = match kernel_id {
        STATS_KERNEL_SUM
        | STATS_KERNEL_MEAN
        | STATS_KERNEL_VARIANCE_POPULATION
        | STATS_KERNEL_VARIANCE_SAMPLE
        | STATS_KERNEL_STANDARD_DEVIATION_POPULATION
        | STATS_KERNEL_STANDARD_DEVIATION_SAMPLE => 1,
        STATS_KERNEL_WEIGHTED_MEAN
        | STATS_KERNEL_COVARIANCE_POPULATION
        | STATS_KERNEL_COVARIANCE_SAMPLE
        | STATS_KERNEL_CORRELATION
        | STATS_KERNEL_LINEAR_REGRESSION => 2,
        _ => return None,
    };
    Some(StatisticsKernelContract {
        input_count,
        output_count: if kernel_id == STATS_KERNEL_LINEAR_REGRESSION {
            2
        } else {
            1
        },
    })
}

/// Immutable fused statistics operation declaration.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct StatisticsOperationDecl {
    /// Pack-local operation ID from the official catalog.
    pub id: u32,
    /// Immutable semantic revision.
    pub revision: u16,
    /// Canonical operation key.
    pub key: &'static str,
    /// Compact positional signature.
    pub signature: &'static str,
    /// Explicit method key.
    pub method: &'static str,
    /// Stable built-in kernel ID.
    pub kernel_id: u16,
    /// Number of positional vector inputs.
    pub input_count: u8,
    /// Number of scalar outputs.
    pub output_count: u8,
    /// Final decimal scale for every output in this first statistics slice.
    pub output_scale: u8,
    /// Final deterministic rounding mode.
    pub rounding_mode: RoundingMode,
}

const fn stats_operation(
    id: u32,
    key: &'static str,
    signature: &'static str,
    method: &'static str,
    kernel_id: u16,
    input_count: u8,
    output_count: u8,
) -> StatisticsOperationDecl {
    StatisticsOperationDecl {
        id,
        revision: 1,
        key,
        signature,
        method,
        kernel_id,
        input_count,
        output_count,
        output_scale: 6,
        rounding_mode: RoundingMode::HalfEven,
    }
}

/// `stats.sum(values)`.
pub static STATS_SUM_OPERATION: StatisticsOperationDecl = stats_operation(
    1,
    "stats.sum",
    "stats.sum(values)",
    "exact_ordered",
    STATS_KERNEL_SUM,
    1,
    1,
);
/// `stats.mean(values)`.
pub static STATS_MEAN_OPERATION: StatisticsOperationDecl = stats_operation(
    2,
    "stats.mean",
    "stats.mean(values)",
    "arithmetic",
    STATS_KERNEL_MEAN,
    1,
    1,
);
/// `stats.mean.weighted(values,weights)`.
pub static STATS_WEIGHTED_MEAN_OPERATION: StatisticsOperationDecl = stats_operation(
    3,
    "stats.mean.weighted",
    "stats.mean.weighted(values,weights)",
    "weighted_arithmetic",
    STATS_KERNEL_WEIGHTED_MEAN,
    2,
    1,
);
/// `stats.var.pop(values)`.
pub static STATS_VARIANCE_POPULATION_OPERATION: StatisticsOperationDecl = stats_operation(
    4,
    "stats.var.pop",
    "stats.var.pop(values)",
    "two_pass_population",
    STATS_KERNEL_VARIANCE_POPULATION,
    1,
    1,
);
/// `stats.var.sample(values)`.
pub static STATS_VARIANCE_SAMPLE_OPERATION: StatisticsOperationDecl = stats_operation(
    5,
    "stats.var.sample",
    "stats.var.sample(values)",
    "two_pass_sample",
    STATS_KERNEL_VARIANCE_SAMPLE,
    1,
    1,
);
/// `stats.sd.pop(values)`.
pub static STATS_STANDARD_DEVIATION_POPULATION_OPERATION: StatisticsOperationDecl = stats_operation(
    6,
    "stats.sd.pop",
    "stats.sd.pop(values)",
    "population",
    STATS_KERNEL_STANDARD_DEVIATION_POPULATION,
    1,
    1,
);
/// `stats.sd.sample(values)`.
pub static STATS_STANDARD_DEVIATION_SAMPLE_OPERATION: StatisticsOperationDecl = stats_operation(
    7,
    "stats.sd.sample",
    "stats.sd.sample(values)",
    "sample",
    STATS_KERNEL_STANDARD_DEVIATION_SAMPLE,
    1,
    1,
);
/// `stats.cov.pop(x,y)`.
pub static STATS_COVARIANCE_POPULATION_OPERATION: StatisticsOperationDecl = stats_operation(
    8,
    "stats.cov.pop",
    "stats.cov.pop(x,y)",
    "population",
    STATS_KERNEL_COVARIANCE_POPULATION,
    2,
    1,
);
/// `stats.cov.sample(x,y)`.
pub static STATS_COVARIANCE_SAMPLE_OPERATION: StatisticsOperationDecl = stats_operation(
    9,
    "stats.cov.sample",
    "stats.cov.sample(x,y)",
    "sample",
    STATS_KERNEL_COVARIANCE_SAMPLE,
    2,
    1,
);
/// `stats.corr.pearson(x,y)`.
pub static STATS_CORRELATION_PEARSON_OPERATION: StatisticsOperationDecl = stats_operation(
    10,
    "stats.corr.pearson",
    "stats.corr.pearson(x,y)",
    "pearson",
    STATS_KERNEL_CORRELATION,
    2,
    1,
);
/// `stats.regression.linear(x,y)`.
pub static STATS_LINEAR_REGRESSION_OPERATION: StatisticsOperationDecl = stats_operation(
    11,
    "stats.regression.linear",
    "stats.regression.linear(x,y)",
    "least_squares",
    STATS_KERNEL_LINEAR_REGRESSION,
    2,
    2,
);

/// Executable statistics operations in the first fused kernel slice.
pub static OFFICIAL_STATS_OPERATIONS: [&StatisticsOperationDecl; 11] = [
    &STATS_SUM_OPERATION,
    &STATS_MEAN_OPERATION,
    &STATS_WEIGHTED_MEAN_OPERATION,
    &STATS_VARIANCE_POPULATION_OPERATION,
    &STATS_VARIANCE_SAMPLE_OPERATION,
    &STATS_STANDARD_DEVIATION_POPULATION_OPERATION,
    &STATS_STANDARD_DEVIATION_SAMPLE_OPERATION,
    &STATS_COVARIANCE_POPULATION_OPERATION,
    &STATS_COVARIANCE_SAMPLE_OPERATION,
    &STATS_CORRELATION_PEARSON_OPERATION,
    &STATS_LINEAR_REGRESSION_OPERATION,
];

/// Exact result of simple linear regression `y = intercept + slope*x`.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct LinearRegression {
    /// Exact slope before operation-level rounding.
    pub slope: WorkRational,
    /// Exact intercept before operation-level rounding.
    pub intercept: WorkRational,
}

/// Computes the exact ordered sum of a non-empty decimal vector.
///
/// # Errors
///
/// Returns [`Status::INSUFFICIENT_DATA`] for an empty vector,
/// [`Status::RESOURCE_LIMIT`] above the v0.1 vector bound, or the first exact
/// decimal/arithmetic status encountered while accumulating in input order.
pub fn statistics_sum<V: DecimalVector + ?Sized>(values: &V) -> Result<WorkRational, Status> {
    validate_length(values.len(), 1)?;
    sum_unchecked_nonempty(values)
}

/// Computes the exact arithmetic mean of a non-empty decimal vector.
///
/// # Errors
///
/// Returns a stable insufficient-data, resource-limit, decimal, or arithmetic
/// status when the exact v0.1 algorithm cannot complete.
pub fn statistics_mean<V: DecimalVector + ?Sized>(values: &V) -> Result<WorkRational, Status> {
    validate_length(values.len(), 1)?;
    mean_unchecked_nonempty(values)
}

/// Computes the exact weighted arithmetic mean.
///
/// # Errors
///
/// Returns [`Status::ARGUMENT_TYPE`] when lengths differ,
/// [`Status::INSUFFICIENT_DATA`] when no observations are supplied,
/// [`Status::DIVIDE_BY_ZERO`] when the exact weight sum is zero, or a stable
/// resource/decimal/arithmetic status from the bounded exact work profile.
pub fn statistics_weighted_mean<V, W>(values: &V, weights: &W) -> Result<WorkRational, Status>
where
    V: DecimalVector + ?Sized,
    W: DecimalVector + ?Sized,
{
    validate_pair(values.len(), weights.len(), 1)?;

    let mut weighted_sum = WorkRational::ZERO;
    let mut weight_sum = WorkRational::ZERO;
    for index in 0..values.len() {
        let value = WorkRational::from_decimal(values.value_at(index)?)?;
        let weight = WorkRational::from_decimal(weights.value_at(index)?)?;
        weighted_sum = weighted_sum.checked_add(value.checked_mul(weight)?)?;
        weight_sum = weight_sum.checked_add(weight)?;
    }
    weighted_sum.checked_div(weight_sum)
}

/// Computes exact population variance with the required deterministic two-pass
/// algorithm.
///
/// # Errors
///
/// Returns a stable insufficient-data, resource-limit, decimal, or arithmetic
/// status when the bounded exact-rational calculation cannot complete.
pub fn statistics_population_variance<V: DecimalVector + ?Sized>(
    values: &V,
) -> Result<WorkRational, Status> {
    validate_length(values.len(), 1)?;
    let mean = mean_unchecked_nonempty(values)?;
    centered_square_sum(values, mean)?.checked_div(count_rational(values.len())?)
}

/// Computes exact sample variance with denominator `n - 1`.
///
/// # Errors
///
/// Returns [`Status::INSUFFICIENT_DATA`] for fewer than two observations, or a
/// stable resource/decimal/arithmetic status from the bounded exact work
/// profile.
pub fn statistics_sample_variance<V: DecimalVector + ?Sized>(
    values: &V,
) -> Result<WorkRational, Status> {
    validate_length(values.len(), 2)?;
    let mean = mean_unchecked_nonempty(values)?;
    centered_square_sum(values, mean)?.checked_div(count_rational(values.len() - 1)?)
}

/// Computes correctly rounded population standard deviation.
///
/// # Errors
///
/// Returns the same stable failures as population variance or deterministic
/// square-root quantization.
pub fn statistics_population_standard_deviation<V: DecimalVector + ?Sized>(
    values: &V,
    scale: u8,
    rounding_mode: RoundingMode,
) -> Result<SqrtDecimal, Status> {
    statistics_population_variance(values)?.sqrt_to_decimal(scale, rounding_mode)
}

/// Computes correctly rounded sample standard deviation.
///
/// # Errors
///
/// Returns the same stable failures as sample variance or deterministic
/// square-root quantization.
pub fn statistics_sample_standard_deviation<V: DecimalVector + ?Sized>(
    values: &V,
    scale: u8,
    rounding_mode: RoundingMode,
) -> Result<SqrtDecimal, Status> {
    statistics_sample_variance(values)?.sqrt_to_decimal(scale, rounding_mode)
}

/// Computes exact population covariance for two paired vectors.
///
/// # Errors
///
/// Returns [`Status::ARGUMENT_TYPE`] for unequal lengths,
/// [`Status::INSUFFICIENT_DATA`] for empty input, or a stable bounded numeric
/// status while performing the deterministic two-pass calculation.
pub fn statistics_population_covariance<L, R>(left: &L, right: &R) -> Result<WorkRational, Status>
where
    L: DecimalVector + ?Sized,
    R: DecimalVector + ?Sized,
{
    validate_pair(left.len(), right.len(), 1)?;
    let left_mean = mean_unchecked_nonempty(left)?;
    let right_mean = mean_unchecked_nonempty(right)?;
    centered_cross_sum(left, right, left_mean, right_mean)?.checked_div(count_rational(left.len())?)
}

/// Computes exact sample covariance for two paired vectors.
///
/// # Errors
///
/// Returns [`Status::ARGUMENT_TYPE`] for unequal lengths,
/// [`Status::INSUFFICIENT_DATA`] for fewer than two paired observations, or a
/// stable bounded numeric status while evaluating the exact algorithm.
pub fn statistics_sample_covariance<L, R>(left: &L, right: &R) -> Result<WorkRational, Status>
where
    L: DecimalVector + ?Sized,
    R: DecimalVector + ?Sized,
{
    validate_pair(left.len(), right.len(), 2)?;
    let left_mean = mean_unchecked_nonempty(left)?;
    let right_mean = mean_unchecked_nonempty(right)?;
    centered_cross_sum(left, right, left_mean, right_mean)?
        .checked_div(count_rational(left.len() - 1)?)
}

/// Computes a correctly rounded Pearson product-moment correlation.
///
/// The exact form `Sxy / sqrt(Sxx*Syy)` is rearranged to a nonnegative
/// rational square root of `Sxy^2/(Sxx*Syy)`. This preserves exact rounding
/// decisions without introducing a binary floating-point approximation.
///
/// # Errors
///
/// Returns [`Status::ARGUMENT_TYPE`] for unequal lengths,
/// [`Status::INSUFFICIENT_DATA`] for fewer than two pairs,
/// [`Status::DOMAIN_ERROR`] when either vector has zero variance, or a stable
/// bounded arithmetic/square-root status.
pub fn statistics_pearson_correlation<X, Y>(
    x: &X,
    y: &Y,
    scale: u8,
    rounding_mode: RoundingMode,
) -> Result<SqrtDecimal, Status>
where
    X: DecimalVector + ?Sized,
    Y: DecimalVector + ?Sized,
{
    validate_pair(x.len(), y.len(), 2)?;
    let mean_x = mean_unchecked_nonempty(x)?;
    let mean_y = mean_unchecked_nonempty(y)?;
    let sxx = centered_square_sum(x, mean_x)?;
    let syy = centered_square_sum(y, mean_y)?;
    if sxx.is_zero() || syy.is_zero() {
        return Err(Status::DOMAIN_ERROR);
    }
    let sxy = centered_cross_sum(x, y, mean_x, mean_y)?;
    let negative = sxy.numerator() < 0;
    let ratio = sxy.checked_div(sxx)?.checked_mul(sxy.checked_div(syy)?)?;
    let magnitude_mode = if negative {
        match rounding_mode {
            RoundingMode::Floor => RoundingMode::Ceil,
            RoundingMode::Ceil => RoundingMode::Floor,
            mode => mode,
        }
    } else {
        rounding_mode
    };
    let mut result = ratio.sqrt_to_decimal(scale, magnitude_mode)?;
    if negative && result.value.coefficient() != 0 {
        result.value = Decimal64::from_parts(
            result
                .value
                .coefficient()
                .checked_neg()
                .ok_or(Status::OVERFLOW)?,
            result.value.exponent(),
        )?;
    }
    Ok(result)
}

/// Computes exact simple linear regression for `y = intercept + slope*x`.
///
/// # Errors
///
/// Returns [`Status::ARGUMENT_TYPE`] for unequal lengths,
/// [`Status::INSUFFICIENT_DATA`] for fewer than two points,
/// [`Status::DOMAIN_ERROR`] when the x vector has zero variance, or a stable
/// bounded numeric status from exact-rational evaluation.
pub fn statistics_linear_regression<X, Y>(x: &X, y: &Y) -> Result<LinearRegression, Status>
where
    X: DecimalVector + ?Sized,
    Y: DecimalVector + ?Sized,
{
    validate_pair(x.len(), y.len(), 2)?;
    let mean_x = mean_unchecked_nonempty(x)?;
    let mean_y = mean_unchecked_nonempty(y)?;
    let sxx = centered_square_sum(x, mean_x)?;
    if sxx.is_zero() {
        return Err(Status::DOMAIN_ERROR);
    }
    let sxy = centered_cross_sum(x, y, mean_x, mean_y)?;
    let slope = sxy.checked_div(sxx)?;
    let intercept = mean_y.checked_sub(slope.checked_mul(mean_x)?)?;
    Ok(LinearRegression { slope, intercept })
}

/// Evaluates one fused statistics kernel operation and normalizes its scalar
/// outputs into the same result record used by scalar formula evaluation.
///
/// The vector elements are already canonical [`Decimal64`] values. ABI/wire
/// adapters remain responsible for shape, semantic-kind, unit, pointer, and
/// caller-storage validation before invoking this function.
#[must_use]
#[allow(clippy::too_many_lines)]
pub fn evaluate_statistics_operation<V: DecimalVector>(
    pack_slot: u16,
    operation: &StatisticsOperationDecl,
    arguments: &[V],
) -> EvaluationResult {
    let Some(contract) = statistics_kernel_contract(operation.kernel_id) else {
        return statistics_failure(pack_slot, operation, Status::PACK_INVALID);
    };
    if contract.input_count != operation.input_count
        || contract.output_count != operation.output_count
    {
        return statistics_failure(pack_slot, operation, Status::PACK_INVALID);
    }
    if arguments.len() != usize::from(contract.input_count) {
        return statistics_failure(pack_slot, operation, Status::ARGUMENT_COUNT);
    }

    let square_root_result = match operation.kernel_id {
        STATS_KERNEL_STANDARD_DEVIATION_POPULATION => {
            Some(statistics_population_standard_deviation(
                &arguments[0],
                operation.output_scale,
                operation.rounding_mode,
            ))
        }
        STATS_KERNEL_STANDARD_DEVIATION_SAMPLE => Some(statistics_sample_standard_deviation(
            &arguments[0],
            operation.output_scale,
            operation.rounding_mode,
        )),
        STATS_KERNEL_CORRELATION => Some(statistics_pearson_correlation(
            &arguments[0],
            &arguments[1],
            operation.output_scale,
            operation.rounding_mode,
        )),
        _ => None,
    };
    if let Some(result) = square_root_result {
        return match result {
            Ok(result) => statistics_sqrt_success(pack_slot, operation, result),
            Err(status) => statistics_failure(pack_slot, operation, status),
        };
    }

    let mut exact = [WorkRational::ZERO; 2];
    let produced = match operation.kernel_id {
        STATS_KERNEL_SUM => statistics_sum(&arguments[0]).map(|value| {
            exact[0] = value;
            1usize
        }),
        STATS_KERNEL_MEAN => statistics_mean(&arguments[0]).map(|value| {
            exact[0] = value;
            1
        }),
        STATS_KERNEL_WEIGHTED_MEAN => {
            statistics_weighted_mean(&arguments[0], &arguments[1]).map(|value| {
                exact[0] = value;
                1
            })
        }
        STATS_KERNEL_VARIANCE_POPULATION => {
            statistics_population_variance(&arguments[0]).map(|value| {
                exact[0] = value;
                1
            })
        }
        STATS_KERNEL_VARIANCE_SAMPLE => statistics_sample_variance(&arguments[0]).map(|value| {
            exact[0] = value;
            1
        }),
        STATS_KERNEL_COVARIANCE_POPULATION => {
            statistics_population_covariance(&arguments[0], &arguments[1]).map(|value| {
                exact[0] = value;
                1
            })
        }
        STATS_KERNEL_COVARIANCE_SAMPLE => {
            statistics_sample_covariance(&arguments[0], &arguments[1]).map(|value| {
                exact[0] = value;
                1
            })
        }
        STATS_KERNEL_LINEAR_REGRESSION => {
            statistics_linear_regression(&arguments[0], &arguments[1]).map(|value| {
                exact[0] = value.slope;
                exact[1] = value.intercept;
                2
            })
        }
        _ => Err(Status::INTERNAL_ERROR),
    };

    let produced = match produced {
        Ok(produced) => produced,
        Err(status) => return statistics_failure(pack_slot, operation, status),
    };
    if produced != usize::from(operation.output_count) || produced > MAX_RESULT_VALUES {
        return statistics_failure(pack_slot, operation, Status::INTERNAL_ERROR);
    }

    let zero_value = ResultValue {
        decimal: Decimal64::ZERO,
        semantic_kind: 0,
        unit_id: 0,
        flags: 0,
    };
    let mut values = [zero_value; MAX_RESULT_VALUES];
    let mut aggregate_flags = 0u16;
    for (index, value) in exact[..produced].iter().copied().enumerate() {
        let rounded = match value.round_to_decimal(operation.output_scale, operation.rounding_mode)
        {
            Ok(rounded) => rounded,
            Err(status) => return statistics_failure(pack_slot, operation, status),
        };
        let value_flags = if rounded.rounded {
            VALUE_FLAG_ROUNDED
        } else {
            0
        };
        aggregate_flags |= u16::try_from(value_flags).unwrap_or(0);
        values[index] = ResultValue {
            decimal: rounded.value,
            semantic_kind: SEMANTIC_NUMBER,
            unit_id: 0,
            flags: value_flags,
        };
    }

    EvaluationResult {
        status: Status::OK,
        flags: aggregate_flags,
        value_count: u16::try_from(produced).unwrap_or(0),
        classification_id: 0,
        pack_slot,
        operation_revision: operation.revision,
        operation_id: operation.id,
        output_scale: i8::try_from(operation.output_scale).unwrap_or(0),
        rounding_mode: operation.rounding_mode.id(),
        detail_code: 0,
        argument_index: ARGUMENT_INDEX_NONE,
        required_size: 0,
        values,
    }
}

fn statistics_sqrt_success(
    pack_slot: u16,
    operation: &StatisticsOperationDecl,
    result: SqrtDecimal,
) -> EvaluationResult {
    let mut value_flags = 0;
    if result.rounded {
        value_flags |= VALUE_FLAG_ROUNDED;
    }
    if result.inexact {
        value_flags |= VALUE_FLAG_INEXACT;
    }
    let zero_value = ResultValue {
        decimal: Decimal64::ZERO,
        semantic_kind: 0,
        unit_id: 0,
        flags: 0,
    };
    EvaluationResult {
        status: Status::OK,
        flags: u16::try_from(value_flags).unwrap_or(0),
        value_count: 1,
        classification_id: 0,
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
                decimal: result.value,
                semantic_kind: SEMANTIC_NUMBER,
                unit_id: 0,
                flags: value_flags,
            },
            zero_value,
            zero_value,
            zero_value,
        ],
    }
}

fn statistics_failure(
    pack_slot: u16,
    operation: &StatisticsOperationDecl,
    status: Status,
) -> EvaluationResult {
    let mut result = EvaluationResult::unidentified_failure(status);
    result.pack_slot = pack_slot;
    result.operation_revision = operation.revision;
    result.operation_id = operation.id;
    result.output_scale = i8::try_from(operation.output_scale).unwrap_or(0);
    result.rounding_mode = operation.rounding_mode.id();
    result
}

fn validate_length(length: usize, minimum: usize) -> Result<(), Status> {
    if length > MAX_STATS_VECTOR_LEN {
        return Err(Status::RESOURCE_LIMIT);
    }
    if length < minimum {
        return Err(Status::INSUFFICIENT_DATA);
    }
    Ok(())
}

fn validate_pair(left: usize, right: usize, minimum: usize) -> Result<(), Status> {
    if left != right {
        return Err(Status::ARGUMENT_TYPE);
    }
    validate_length(left, minimum)
}

fn count_rational(length: usize) -> Result<WorkRational, Status> {
    let count = i64::try_from(length).map_err(|_| Status::RESOURCE_LIMIT)?;
    Ok(WorkRational::from_integer(count))
}

fn sum_unchecked_nonempty<V: DecimalVector + ?Sized>(values: &V) -> Result<WorkRational, Status> {
    let mut sum = WorkRational::ZERO;
    for index in 0..values.len() {
        sum = sum.checked_add(WorkRational::from_decimal(values.value_at(index)?)?)?;
    }
    Ok(sum)
}

fn mean_unchecked_nonempty<V: DecimalVector + ?Sized>(values: &V) -> Result<WorkRational, Status> {
    sum_unchecked_nonempty(values)?.checked_div(count_rational(values.len())?)
}

fn centered_square_sum<V: DecimalVector + ?Sized>(
    values: &V,
    mean: WorkRational,
) -> Result<WorkRational, Status> {
    let mut total = WorkRational::ZERO;
    for index in 0..values.len() {
        let deviation = WorkRational::from_decimal(values.value_at(index)?)?.checked_sub(mean)?;
        total = total.checked_add(deviation.checked_mul(deviation)?)?;
    }
    Ok(total)
}

fn centered_cross_sum<L, R>(
    left: &L,
    right: &R,
    left_mean: WorkRational,
    right_mean: WorkRational,
) -> Result<WorkRational, Status>
where
    L: DecimalVector + ?Sized,
    R: DecimalVector + ?Sized,
{
    let mut total = WorkRational::ZERO;
    for index in 0..left.len() {
        let left_deviation =
            WorkRational::from_decimal(left.value_at(index)?)?.checked_sub(left_mean)?;
        let right_deviation =
            WorkRational::from_decimal(right.value_at(index)?)?.checked_sub(right_mean)?;
        total = total.checked_add(left_deviation.checked_mul(right_deviation)?)?;
    }
    Ok(total)
}

#[cfg(test)]
mod tests {
    use super::{
        evaluate_statistics_operation, statistics_linear_regression, statistics_mean,
        statistics_pearson_correlation, statistics_population_covariance,
        statistics_population_standard_deviation, statistics_population_variance,
        statistics_sample_covariance, statistics_sample_standard_deviation,
        statistics_sample_variance, statistics_sum, statistics_weighted_mean, MAX_STATS_VECTOR_LEN,
        STATS_CORRELATION_PEARSON_OPERATION, STATS_LINEAR_REGRESSION_OPERATION,
        STATS_MEAN_OPERATION, STATS_STANDARD_DEVIATION_POPULATION_OPERATION,
    };
    use crate::{
        Decimal64, RoundingMode, Status, WorkRational, VALUE_FLAG_INEXACT, VALUE_FLAG_ROUNDED,
    };

    fn decimals(values: &[&[u8]]) -> std::vec::Vec<Decimal64> {
        values
            .iter()
            .map(|value| Decimal64::parse_ascii(value).unwrap())
            .collect()
    }

    #[test]
    fn ordered_sum_and_mean_are_exact() {
        let values = decimals(&[b"0.1", b"0.2", b"0.3"]);
        assert_eq!(statistics_sum(values.as_slice()), WorkRational::new(3, 5));
        assert_eq!(statistics_mean(values.as_slice()), WorkRational::new(1, 5));
    }

    #[test]
    fn weighted_mean_uses_exact_weight_sum() {
        let values = decimals(&[b"10", b"20", b"40"]);
        let weights = decimals(&[b"1", b"2", b"1"]);
        assert_eq!(
            statistics_weighted_mean(values.as_slice(), weights.as_slice()),
            WorkRational::new(45, 2)
        );

        let zero_weights = decimals(&[b"1", b"-1", b"0"]);
        assert_eq!(
            statistics_weighted_mean(values.as_slice(), zero_weights.as_slice()),
            Err(Status::DIVIDE_BY_ZERO)
        );
    }

    #[test]
    fn population_and_sample_variance_follow_two_pass_definition() {
        let values = decimals(&[b"1", b"2", b"3", b"4"]);
        assert_eq!(
            statistics_population_variance(values.as_slice()),
            WorkRational::new(5, 4)
        );
        assert_eq!(
            statistics_sample_variance(values.as_slice()),
            WorkRational::new(5, 3)
        );
    }

    #[test]
    fn covariance_variants_are_exact_and_paired() {
        let left = decimals(&[b"1", b"2", b"3"]);
        let right = decimals(&[b"2", b"4", b"8"]);
        assert_eq!(
            statistics_population_covariance(left.as_slice(), right.as_slice()),
            WorkRational::new(2, 1)
        );
        assert_eq!(
            statistics_sample_covariance(left.as_slice(), right.as_slice()),
            WorkRational::new(3, 1)
        );

        assert_eq!(
            statistics_population_covariance(left.as_slice(), &right[..2]),
            Err(Status::ARGUMENT_TYPE)
        );
    }

    #[test]
    fn standard_deviation_uses_shared_deterministic_square_root() {
        let values = decimals(&[b"1", b"2", b"3"]);
        let population =
            statistics_population_standard_deviation(values.as_slice(), 6, RoundingMode::HalfEven)
                .unwrap();
        assert_eq!(
            population.value,
            Decimal64::from_parts(816_497, -6).unwrap()
        );
        assert!(population.rounded);
        assert!(population.inexact);

        let sample =
            statistics_sample_standard_deviation(values.as_slice(), 6, RoundingMode::HalfEven)
                .unwrap();
        assert_eq!(sample.value, Decimal64::from_parts(1, 0).unwrap());
        assert!(!sample.rounded);
        assert!(!sample.inexact);
    }

    #[test]
    fn pearson_correlation_is_signed_and_rejects_zero_variance() {
        let x = decimals(&[b"1", b"2", b"3"]);
        let y = decimals(&[b"1", b"2", b"4"]);
        let result =
            statistics_pearson_correlation(x.as_slice(), y.as_slice(), 6, RoundingMode::HalfEven)
                .unwrap();
        assert_eq!(result.value, Decimal64::from_parts(981_981, -6).unwrap());
        assert!(result.rounded);
        assert!(result.inexact);

        let descending = decimals(&[b"3", b"2", b"1"]);
        let negative = statistics_pearson_correlation(
            x.as_slice(),
            descending.as_slice(),
            6,
            RoundingMode::HalfEven,
        )
        .unwrap();
        assert_eq!(negative.value, Decimal64::from_parts(-1, 0).unwrap());
        assert!(!negative.rounded);
        assert!(!negative.inexact);

        let flat = decimals(&[b"2", b"2", b"2"]);
        assert_eq!(
            statistics_pearson_correlation(
                x.as_slice(),
                flat.as_slice(),
                6,
                RoundingMode::HalfEven
            ),
            Err(Status::DOMAIN_ERROR)
        );
    }

    #[test]
    fn linear_regression_returns_exact_slope_and_intercept() {
        let x = decimals(&[b"1", b"2", b"3"]);
        let y = decimals(&[b"3", b"5", b"7"]);
        let result = statistics_linear_regression(x.as_slice(), y.as_slice()).unwrap();
        assert_eq!(result.slope, WorkRational::from_integer(2));
        assert_eq!(result.intercept, WorkRational::from_integer(1));

        let flat_x = decimals(&[b"2", b"2"]);
        let flat_y = decimals(&[b"1", b"3"]);
        assert_eq!(
            statistics_linear_regression(flat_x.as_slice(), flat_y.as_slice()),
            Err(Status::DOMAIN_ERROR)
        );
    }

    #[test]
    fn normalized_statistics_evaluation_supports_one_and_two_outputs() {
        let values = decimals(&[b"1", b"2", b"3"]);
        let mean = evaluate_statistics_operation(2, &STATS_MEAN_OPERATION, &[values.as_slice()]);
        assert_eq!(mean.status, Status::OK);
        assert_eq!(mean.operation_id, 2);
        assert_eq!(mean.value_count, 1);
        assert_eq!(mean.values[0].decimal, Decimal64::from_parts(2, 0).unwrap());

        let x = decimals(&[b"1", b"2", b"3"]);
        let y = decimals(&[b"3", b"5", b"7"]);
        let regression = evaluate_statistics_operation(
            2,
            &STATS_LINEAR_REGRESSION_OPERATION,
            &[x.as_slice(), y.as_slice()],
        );
        assert_eq!(regression.status, Status::OK);
        assert_eq!(regression.operation_id, 11);
        assert_eq!(regression.value_count, 2);
        assert_eq!(
            regression.values[0].decimal,
            Decimal64::from_parts(2, 0).unwrap()
        );
        assert_eq!(
            regression.values[1].decimal,
            Decimal64::from_parts(1, 0).unwrap()
        );

        let standard_deviation = evaluate_statistics_operation(
            2,
            &STATS_STANDARD_DEVIATION_POPULATION_OPERATION,
            &[values.as_slice()],
        );
        assert_eq!(standard_deviation.status, Status::OK);
        assert_ne!(
            standard_deviation.flags & u16::try_from(VALUE_FLAG_ROUNDED).unwrap(),
            0
        );
        assert_ne!(
            standard_deviation.flags & u16::try_from(VALUE_FLAG_INEXACT).unwrap(),
            0
        );

        let correlation = evaluate_statistics_operation(
            2,
            &STATS_CORRELATION_PEARSON_OPERATION,
            &[x.as_slice(), y.as_slice()],
        );
        assert_eq!(correlation.status, Status::OK);
        assert_eq!(
            correlation.values[0].decimal,
            Decimal64::from_parts(1, 0).unwrap()
        );
    }

    #[test]
    fn vector_limits_and_minimum_lengths_fail_closed() {
        let empty: &[Decimal64] = &[];
        assert_eq!(statistics_mean(empty), Err(Status::INSUFFICIENT_DATA));
        assert_eq!(
            statistics_sample_variance(empty),
            Err(Status::INSUFFICIENT_DATA)
        );
        let one = decimals(&[b"1"]);
        assert_eq!(
            statistics_sample_variance(one.as_slice()),
            Err(Status::INSUFFICIENT_DATA)
        );

        let too_many = std::vec![Decimal64::ZERO; MAX_STATS_VECTOR_LEN + 1];
        assert_eq!(
            statistics_sum(too_many.as_slice()),
            Err(Status::RESOURCE_LIMIT)
        );
    }
}
