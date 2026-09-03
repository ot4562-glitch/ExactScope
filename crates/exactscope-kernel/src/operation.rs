//! Immutable operation declarations for the first fused slice.

use crate::{
    Instruction, RoundingMode, WorkRational, SEMANTIC_ELASTICITY, SEMANTIC_PRICE, SEMANTIC_QUANTITY,
};

/// Scalar constraint kind used by the first slice.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ConstraintKind {
    /// Input must be strictly greater than the constant.
    GreaterThan,
    /// Input must be greater than or equal to the constant.
    GreaterOrEqual,
}

/// One ordered scalar input declaration.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct InputDecl {
    /// Short positional input name.
    pub name: &'static str,
    /// Required stable semantic kind.
    pub semantic_kind: u8,
    /// Optional same-unit group; zero means no group.
    pub same_unit_group: u8,
    /// Whether a nonzero unit identity is mandatory.
    pub unit_required: bool,
    /// Ordered scalar constraint.
    pub constraint: ConstraintKind,
    /// Constraint comparison constant.
    pub constraint_value: WorkRational,
    /// Stable operation-local constraint detail ID.
    pub detail_id: u16,
}

/// One deterministic classification predicate.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ClassificationDecl {
    /// Stable classification ID.
    pub id: u16,
    /// Stable machine key.
    pub key: &'static str,
    /// Predicate program over the unrounded result.
    pub program: &'static [Instruction],
}

/// Immutable scalar formula declaration.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct OperationDecl {
    /// Pack-local operation ID.
    pub id: u32,
    /// Immutable semantic revision.
    pub revision: u16,
    /// Canonical operation key.
    pub key: &'static str,
    /// Compact positional signature.
    pub signature: &'static str,
    /// Method identity.
    pub method: &'static str,
    /// Ordered input declarations.
    pub inputs: &'static [InputDecl],
    /// Exact constants referenced by VM programs.
    pub constants: &'static [WorkRational],
    /// Formula program.
    pub program: &'static [Instruction],
    /// Ordered classification declarations.
    pub classifications: &'static [ClassificationDecl],
    /// Output stable semantic kind.
    pub output_semantic_kind: u8,
    /// Final decimal scale.
    pub output_scale: u8,
    /// Final rounding mode.
    pub rounding_mode: RoundingMode,
}

/// Borrowed numeric operation view shared by fused and dynamic packs.
///
/// String identity and classification labels deliberately stay outside this
/// view so runtime-loaded pack bytes never need fake `'static` lifetimes.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RuntimeOperation<'a> {
    /// Pack-local operation ID.
    pub id: u32,
    /// Immutable semantic revision.
    pub revision: u16,
    /// Ordered scalar input declarations.
    pub inputs: &'a [InputDecl],
    /// Exact constants referenced by the formula and predicates.
    pub constants: &'a [WorkRational],
    /// Formula VM program.
    pub program: &'a [Instruction],
    /// Whether successful evaluation requires a deterministic class.
    pub classification_required: bool,
    /// Output stable semantic kind.
    pub output_semantic_kind: u8,
    /// Final decimal scale.
    pub output_scale: u8,
    /// Final rounding mode.
    pub rounding_mode: RoundingMode,
}

impl OperationDecl {
    /// Returns the numeric-only view used by the shared evaluator.
    #[must_use]
    pub const fn runtime(&self) -> RuntimeOperation<'static> {
        RuntimeOperation {
            id: self.id,
            revision: self.revision,
            inputs: self.inputs,
            constants: self.constants,
            program: self.program,
            classification_required: !self.classifications.is_empty(),
            output_semantic_kind: self.output_semantic_kind,
            output_scale: self.output_scale,
            rounding_mode: self.rounding_mode,
        }
    }
}

impl InputDecl {
    /// Empty stack-storage placeholder used while decoding dynamic packs.
    pub const EMPTY: Self = Self {
        name: "",
        semantic_kind: 0,
        same_unit_group: 0,
        unit_required: false,
        constraint: ConstraintKind::GreaterOrEqual,
        constraint_value: WorkRational::ZERO,
        detail_id: 0,
    };
}

const PED_INPUTS: [InputDecl; 4] = [
    InputDecl {
        name: "p1",
        semantic_kind: SEMANTIC_PRICE,
        same_unit_group: 1,
        unit_required: false,
        constraint: ConstraintKind::GreaterThan,
        constraint_value: WorkRational::ZERO,
        detail_id: 1,
    },
    InputDecl {
        name: "p2",
        semantic_kind: SEMANTIC_PRICE,
        same_unit_group: 1,
        unit_required: false,
        constraint: ConstraintKind::GreaterThan,
        constraint_value: WorkRational::ZERO,
        detail_id: 2,
    },
    InputDecl {
        name: "q1",
        semantic_kind: SEMANTIC_QUANTITY,
        same_unit_group: 2,
        unit_required: false,
        constraint: ConstraintKind::GreaterOrEqual,
        constraint_value: WorkRational::ZERO,
        detail_id: 3,
    },
    InputDecl {
        name: "q2",
        semantic_kind: SEMANTIC_QUANTITY,
        same_unit_group: 2,
        unit_required: false,
        constraint: ConstraintKind::GreaterOrEqual,
        constraint_value: WorkRational::ZERO,
        detail_id: 4,
    },
];

const PED_CONSTANTS: [WorkRational; 2] =
    [WorkRational::from_integer(2), WorkRational::from_integer(1)];

const PED_PROGRAM: [Instruction; 20] = [
    Instruction::new(1, 3),
    Instruction::new(1, 2),
    Instruction::new(5, 0),
    Instruction::new(1, 2),
    Instruction::new(1, 3),
    Instruction::new(4, 0),
    Instruction::new(2, 0),
    Instruction::new(7, 0),
    Instruction::new(7, 0),
    Instruction::new(1, 1),
    Instruction::new(1, 0),
    Instruction::new(5, 0),
    Instruction::new(1, 0),
    Instruction::new(1, 1),
    Instruction::new(4, 0),
    Instruction::new(2, 0),
    Instruction::new(7, 0),
    Instruction::new(7, 0),
    Instruction::new(7, 0),
    Instruction::new(0, 0),
];

const CLASS_INELASTIC_PROGRAM: [Instruction; 5] = [
    Instruction::new(3, 0),
    Instruction::new(9, 0),
    Instruction::new(2, 1),
    Instruction::new(14, 0),
    Instruction::new(0, 0),
];

const CLASS_UNIT_PROGRAM: [Instruction; 5] = [
    Instruction::new(3, 0),
    Instruction::new(9, 0),
    Instruction::new(2, 1),
    Instruction::new(16, 0),
    Instruction::new(0, 0),
];

const CLASS_ELASTIC_PROGRAM: [Instruction; 5] = [
    Instruction::new(3, 0),
    Instruction::new(9, 0),
    Instruction::new(2, 1),
    Instruction::new(18, 0),
    Instruction::new(0, 0),
];

const PED_CLASSIFICATIONS: [ClassificationDecl; 3] = [
    ClassificationDecl {
        id: 1,
        key: "inelastic",
        program: &CLASS_INELASTIC_PROGRAM,
    },
    ClassificationDecl {
        id: 2,
        key: "unit_elastic",
        program: &CLASS_UNIT_PROGRAM,
    },
    ClassificationDecl {
        id: 3,
        key: "elastic",
        program: &CLASS_ELASTIC_PROGRAM,
    },
];

/// First fused implementation operation.
pub static PED_MID_OPERATION: OperationDecl = OperationDecl {
    id: 301,
    revision: 1,
    key: "econ.ped.mid",
    signature: "econ.ped.mid(p1,p2,q1,q2)",
    method: "midpoint",
    inputs: &PED_INPUTS,
    constants: &PED_CONSTANTS,
    program: &PED_PROGRAM,
    classifications: &PED_CLASSIFICATIONS,
    output_semantic_kind: SEMANTIC_ELASTICITY,
    output_scale: 6,
    rounding_mode: RoundingMode::HalfEven,
};

/// Returns a classification machine key from an operation-local ID.
#[must_use]
pub fn classification_key(operation: &OperationDecl, id: u16) -> Option<&'static str> {
    operation
        .classifications
        .iter()
        .find(|classification| classification.id == id)
        .map(|classification| classification.key)
}
