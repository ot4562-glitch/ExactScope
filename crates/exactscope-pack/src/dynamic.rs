//! Allocation-free validated view over dynamic `.xsp` pack bytes.

use core::str;

use exactscope_kernel::{
    evaluate_runtime_operation, execute_predicate, validate_program, ConstraintKind, Decimal64,
    EvaluationResult, InputDecl, Instruction, ProgramKind, RoundingMode, RuntimeOperation,
    ScalarValue, Status, WorkRational, MAX_VM_INSTRUCTIONS,
};

use crate::format::{
    crc32_iso_hdlc, read_i64, read_u16, read_u32, read_u8, ALIAS_RECORD_SIZE,
    CLASSIFICATION_RECORD_SIZE, CONSTANT_RECORD_SIZE, CONSTRAINT_GE, CONSTRAINT_GT,
    CONSTRAINT_RECORD_SIZE, FORMAT_MAJOR, FORMAT_MINOR, HEADER_SIZE, INPUT_FLAGS_V1,
    INPUT_FLAG_UNIT_REQUIRED, INPUT_RECORD_SIZE, INSTRUCTION_RECORD_SIZE, MAGIC, MAX_SECTION_KIND,
    META_RECORD_SIZE, NUMERIC_PROFILE_DECIMAL64_V1, OPERATION_KIND_FORMULA,
    OPERATION_RECORD_SIZE, OP_FLAGS_V1, OP_FLAG_CLASSIFICATION_REQUIRED, OUTPUT_RECORD_SIZE,
    SECTION_ALIASES, SECTION_CLASSIFICATIONS, SECTION_CONSTANTS, SECTION_CONSTRAINTS,
    SECTION_ENTRY_SIZE, SECTION_INPUTS, SECTION_META, SECTION_OPERATIONS, SECTION_OUTPUTS,
    SECTION_PROGRAMS, SECTION_STRINGS,
};

const ABI_V1_0: u32 = 0x0001_0000;
const ABSENT_STRING: u32 = u32::MAX;
const MAX_CONSTANTS: usize = 64;
const MAX_CLASSIFICATIONS: usize = 16;
const MAX_INPUTS: usize = 12;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct Section {
    offset: usize,
    len: usize,
    count: usize,
    present: bool,
}

impl Section {
    const EMPTY: Self = Self {
        offset: 0,
        len: 0,
        count: 0,
        present: false,
    };

    fn end(self) -> Result<usize, Status> {
        self.offset.checked_add(self.len).ok_or(Status::PACK_INVALID)
    }
}

/// One validated operation identity borrowed from a [`PackView`].
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct DynamicOperation<'a> {
    record_index: usize,
    /// Pack-local operation ID.
    pub id: u32,
    /// Immutable operation revision.
    pub revision: u16,
    /// Canonical operation key.
    pub key: &'a str,
    /// Compact positional signature.
    pub signature: &'a str,
    /// Explicit method key.
    pub method: &'a str,
}

/// Safe immutable view over one validated `.xsp` byte slice.
///
/// The view stores only offsets/counts and borrows the caller-owned pack bytes.
/// It allocates nothing and performs no native struct casts.
#[derive(Clone, Copy, Debug)]
pub struct PackView<'a> {
    bytes: &'a [u8],
    sections: [Section; MAX_SECTION_KIND + 1],
    operation_count: usize,
}

impl<'a> PackView<'a> {
    /// Validates pack structure, CRC, strings, records, VM programs, and limits.
    ///
    /// # Errors
    ///
    /// Returns a stable pack/version/integrity/resource status. No partial
    /// registration state exists because the view is produced only after all
    /// operation records validate.
    pub fn parse(bytes: &'a [u8]) -> Result<Self, Status> {
        if bytes.len() < HEADER_SIZE || bytes.get(0..4) != Some(MAGIC.as_slice()) {
            return Err(Status::PACK_INVALID);
        }
        if read_u16(bytes, 4)? != FORMAT_MAJOR || read_u16(bytes, 6)? > FORMAT_MINOR {
            return Err(Status::PACK_VERSION_UNSUPPORTED);
        }
        if usize::from(read_u16(bytes, 8)?) != HEADER_SIZE
            || usize::from(read_u16(bytes, 10)?) != SECTION_ENTRY_SIZE
        {
            return Err(Status::PACK_VERSION_UNSUPPORTED);
        }
        if read_u32(bytes, 12)? & !0x0000_0007 != 0 || read_u16(bytes, 26)? != 0 {
            return Err(Status::PACK_INVALID);
        }
        if usize::try_from(read_u32(bytes, 16)?).map_err(|_| Status::PACK_INVALID)? != bytes.len() {
            return Err(Status::PACK_INVALID);
        }

        let directory_offset =
            usize::try_from(read_u32(bytes, 20)?).map_err(|_| Status::PACK_INVALID)?;
        let section_count = usize::from(read_u16(bytes, 24)?);
        if directory_offset < HEADER_SIZE || directory_offset % 4 != 0 || section_count == 0 {
            return Err(Status::PACK_INVALID);
        }
        let directory_len = section_count
            .checked_mul(SECTION_ENTRY_SIZE)
            .ok_or(Status::PACK_INVALID)?;
        let directory_end = directory_offset
            .checked_add(directory_len)
            .ok_or(Status::PACK_INVALID)?;
        if directory_end > bytes.len() {
            return Err(Status::PACK_INVALID);
        }

        if crc32_iso_hdlc(&bytes[HEADER_SIZE..]) != read_u32(bytes, 28)? {
            return Err(Status::INTEGRITY_ERROR);
        }

        let mut sections = [Section::EMPTY; MAX_SECTION_KIND + 1];
        let mut previous_kind = 0usize;
        let mut previous_end = align4(directory_end).ok_or(Status::PACK_INVALID)?;
        for index in 0..section_count {
            let base = directory_offset + index * SECTION_ENTRY_SIZE;
            let kind = usize::from(read_u16(bytes, base)?);
            let flags = read_u16(bytes, base + 2)?;
            let offset = usize::try_from(read_u32(bytes, base + 4)?)
                .map_err(|_| Status::PACK_INVALID)?;
            let len = usize::try_from(read_u32(bytes, base + 8)?)
                .map_err(|_| Status::PACK_INVALID)?;
            let count = usize::try_from(read_u32(bytes, base + 12)?)
                .map_err(|_| Status::PACK_INVALID)?;

            if kind == 0
                || kind > MAX_SECTION_KIND
                || kind <= previous_kind
                || flags != 0
                || sections[kind].present
                || offset % 4 != 0
                || offset < previous_end
            {
                return Err(Status::PACK_INVALID);
            }
            let section = Section {
                offset,
                len,
                count,
                present: true,
            };
            let end = section.end()?;
            if end > bytes.len() {
                return Err(Status::PACK_INVALID);
            }
            sections[kind] = section;
            previous_kind = kind;
            previous_end = end;
        }

        require_section(sections[SECTION_META], META_RECORD_SIZE, 1)?;
        require_section(sections[SECTION_STRINGS], 0, sections[SECTION_STRINGS].count)?;
        require_record_section(
            sections[SECTION_OPERATIONS],
            OPERATION_RECORD_SIZE,
            true,
        )?;
        require_record_section(sections[SECTION_OUTPUTS], OUTPUT_RECORD_SIZE, true)?;
        validate_optional_record_section(sections[SECTION_INPUTS], INPUT_RECORD_SIZE)?;
        validate_optional_record_section(
            sections[SECTION_CONSTRAINTS],
            CONSTRAINT_RECORD_SIZE,
        )?;
        validate_optional_record_section(sections[SECTION_CONSTANTS], CONSTANT_RECORD_SIZE)?;
        validate_optional_record_section(sections[SECTION_PROGRAMS], INSTRUCTION_RECORD_SIZE)?;
        validate_optional_record_section(
            sections[SECTION_CLASSIFICATIONS],
            CLASSIFICATION_RECORD_SIZE,
        )?;
        validate_optional_record_section(sections[SECTION_ALIASES], ALIAS_RECORD_SIZE)?;

        let mut view = Self {
            bytes,
            sections,
            operation_count: sections[SECTION_OPERATIONS].count,
        };
        view.validate_meta()?;
        view.validate_string_table()?;
        for record_index in 0..view.operation_count {
            view.validate_operation(record_index)?;
        }
        Ok(view)
    }

    /// Number of operations exposed by this pack.
    #[must_use]
    pub const fn operation_count(self) -> usize {
        self.operation_count
    }

    /// Pack identity from the META record.
    ///
    /// # Errors
    ///
    /// Returns [`Status::PACK_INVALID`] if the previously validated string
    /// reference is unexpectedly inconsistent.
    pub fn pack_id(self) -> Result<&'a str, Status> {
        let meta = self.section_bytes(SECTION_META)?;
        self.string_at(read_u32(meta, 0)?)
    }

    /// Pack semantic version `(major, minor, patch)`.
    ///
    /// # Errors
    ///
    /// Returns [`Status::PACK_INVALID`] on impossible META inconsistency.
    pub fn version(self) -> Result<(u16, u16, u16), Status> {
        let meta = self.section_bytes(SECTION_META)?;
        Ok((
            read_u16(meta, 16)?,
            read_u16(meta, 18)?,
            read_u16(meta, 20)?,
        ))
    }

    /// Finds one exact canonical operation key.
    ///
    /// # Errors
    ///
    /// Returns [`Status::UNKNOWN_OPERATION`] when the canonical key is absent.
    pub fn operation_by_key(self, key: &[u8]) -> Result<DynamicOperation<'a>, Status> {
        for index in 0..self.operation_count {
            let operation = self.operation_at(index)?;
            if operation.key.as_bytes() == key {
                return Ok(operation);
            }
        }
        Err(Status::UNKNOWN_OPERATION)
    }

    /// Finds one operation by pack-local numeric ID.
    ///
    /// # Errors
    ///
    /// Returns [`Status::UNKNOWN_OPERATION`] when the ID is absent.
    pub fn operation_by_id(self, id: u32) -> Result<DynamicOperation<'a>, Status> {
        for index in 0..self.operation_count {
            let operation = self.operation_at(index)?;
            if operation.id == id {
                return Ok(operation);
            }
        }
        Err(Status::UNKNOWN_OPERATION)
    }

    /// Evaluates one validated dynamic formula using the shared kernel runtime.
    ///
    /// # Errors
    ///
    /// All calculation failures are normalized into [`EvaluationResult`].
    /// This method itself returns `Err` only for an impossible post-parse pack
    /// inconsistency.
    pub fn evaluate(
        self,
        pack_slot: u16,
        operation: DynamicOperation<'a>,
        arguments: &[ScalarValue],
    ) -> Result<EvaluationResult, Status> {
        let record = self.operation_record(operation.record_index)?;
        let mut inputs = [InputDecl::EMPTY; MAX_INPUTS];
        let input_count = self.decode_inputs(record, &mut inputs)?;

        let mut constants = [WorkRational::ZERO; MAX_CONSTANTS];
        let constant_count = self.decode_constants(&mut constants)?;

        let mut program = [Instruction::new(0, 0); MAX_VM_INSTRUCTIONS];
        let program_count = self.decode_operation_program(record, &mut program)?;

        let output = self.output_record_for(record)?;
        let output_semantic_kind = read_u8(output, 4)?;
        let output_scale = read_u8(record, 50)?;
        let rounding_mode = RoundingMode::from_id(read_u8(record, 51)?)
            .map_err(|_| Status::PACK_INVALID)?;

        let runtime = RuntimeOperation {
            id: operation.id,
            revision: operation.revision,
            inputs: &inputs[..input_count],
            constants: &constants[..constant_count],
            program: &program[..program_count],
            classification_required: read_u8(record, 7)? & OP_FLAG_CLASSIFICATION_REQUIRED != 0,
            output_semantic_kind,
            output_scale,
            rounding_mode,
        };

        Ok(evaluate_runtime_operation(
            pack_slot,
            &runtime,
            arguments,
            |exact| self.classify(record, exact, &constants[..constant_count]),
        ))
    }

    /// Returns the machine classification key for one operation-local class ID.
    ///
    /// # Errors
    ///
    /// Returns [`Status::PACK_INVALID`] for invalid references and
    /// [`Status::UNKNOWN_OPERATION`] when the class ID is not declared.
    pub fn classification_key(
        self,
        operation: DynamicOperation<'a>,
        classification_id: u16,
    ) -> Result<&'a str, Status> {
        let record = self.operation_record(operation.record_index)?;
        let first = usize::try_from(read_u32(record, 44)?).map_err(|_| Status::PACK_INVALID)?;
        let count = usize::from(read_u16(record, 48)?);
        for index in 0..count {
            let classification = self.classification_record(first + index)?;
            if read_u16(classification, 0)? == classification_id {
                return self.string_at(read_u32(classification, 4)?);
            }
        }
        Err(Status::UNKNOWN_OPERATION)
    }

    fn validate_meta(&self) -> Result<(), Status> {
        let meta = self.section_bytes(SECTION_META)?;
        if read_u16(meta, 22)? != NUMERIC_PROFILE_DECIMAL64_V1
            || read_u32(meta, 24)? > ABI_V1_0
            || read_u32(meta, 28)? < ABI_V1_0
            || usize::try_from(read_u32(meta, 36)?).map_err(|_| Status::PACK_INVALID)?
                != self.operation_count
            || read_u16(meta, 40)? > 256
            || read_u16(meta, 42)? > 64
            || read_u16(meta, 44)? > 16
            || read_u16(meta, 46)? != 0
        {
            return Err(Status::PACK_VERSION_UNSUPPORTED);
        }
        self.string_at(read_u32(meta, 0)?)?;
        self.string_at(read_u32(meta, 4)?)?;
        let description = read_u32(meta, 8)?;
        if description != ABSENT_STRING {
            self.string_at(description)?;
        }
        self.string_at(read_u32(meta, 12)?)?;
        self.string_at(read_u32(meta, 32)?)?;
        Ok(())
    }

    fn validate_string_table(&self) -> Result<(), Status> {
        let strings = self.section_bytes(SECTION_STRINGS)?;
        if strings.len() < 2 || read_u16(strings, 0)? != 0 {
            return Err(Status::PACK_INVALID);
        }
        let mut offset = 0usize;
        while offset < strings.len() {
            let len = usize::from(read_u16(strings, offset)?);
            let start = offset.checked_add(2).ok_or(Status::PACK_INVALID)?;
            let end = start.checked_add(len).ok_or(Status::PACK_INVALID)?;
            let raw = strings.get(start..end).ok_or(Status::PACK_INVALID)?;
            str::from_utf8(raw).map_err(|_| Status::PACK_INVALID)?;
            offset = if end % 2 == 0 {
                end
            } else {
                let padding = *strings.get(end).ok_or(Status::PACK_INVALID)?;
                if padding != 0 {
                    return Err(Status::PACK_INVALID);
                }
                end + 1
            };
        }
        if offset != strings.len() {
            return Err(Status::PACK_INVALID);
        }
        Ok(())
    }

    fn validate_operation(&mut self, record_index: usize) -> Result<(), Status> {
        let operation = self.operation_at(record_index)?;
        if operation.id == 0 || operation.revision == 0 {
            return Err(Status::PACK_INVALID);
        }
        for prior in 0..record_index {
            let other = self.operation_at(prior)?;
            if other.id == operation.id || other.key == operation.key {
                return Err(Status::PACK_INVALID);
            }
        }

        let record = self.operation_record(record_index)?;
        if read_u8(record, 6)? != OPERATION_KIND_FORMULA
            || read_u8(record, 7)? & !OP_FLAGS_V1 != 0
            || read_u16(record, 42)? != 0
            || read_u8(record, 30)? != 1
            || read_u8(record, 31)? > 16
            || read_u16(record, 58)? != 0
            || read_u32(record, 60)? != 0
        {
            return Err(Status::PACK_INVALID);
        }

        self.string_at(read_u32(record, 12)?)?;
        self.string_at(read_u32(record, 16)?)?;
        let method = read_u32(record, 20)?;
        if method != ABSENT_STRING {
            self.string_at(method)?;
        }

        let mut inputs = [InputDecl::EMPTY; MAX_INPUTS];
        let input_count = self.decode_inputs(record, &mut inputs)?;
        if input_count != usize::from(read_u16(record, 28)?) {
            return Err(Status::PACK_INVALID);
        }

        let mut constants = [WorkRational::ZERO; MAX_CONSTANTS];
        let constant_count = self.decode_constants(&mut constants)?;

        let mut program = [Instruction::new(0, 0); MAX_VM_INSTRUCTIONS];
        let program_count = self.decode_operation_program(record, &mut program)?;
        let max_stack = validate_program(
            &program[..program_count],
            ProgramKind::Formula,
            input_count,
            constant_count,
            0,
        )?;
        if max_stack > usize::from(read_u8(record, 31)?) {
            return Err(Status::PACK_INVALID);
        }

        let output = self.output_record_for(record)?;
        if read_u8(output, 4)? > 10
            || read_u8(output, 5)? > 3
            || read_u16(output, 6)? != 0
            || read_u16(output, 14)? != 0
            || read_u16(output, 22)? != 0
            || read_u8(output, 12)? != read_u8(record, 50)?
            || read_u8(output, 13)? != read_u8(record, 51)?
            || read_u32(output, 16)? != read_u32(record, 36)?
            || read_u16(output, 20)? != read_u16(record, 40)?
        {
            return Err(Status::PACK_INVALID);
        }
        self.string_at(read_u32(output, 0)?)?;
        let unit_rule = read_u32(output, 8)?;
        if unit_rule != ABSENT_STRING {
            self.string_at(unit_rule)?;
        }
        RoundingMode::from_id(read_u8(record, 51)?).map_err(|_| Status::PACK_INVALID)?;

        self.validate_classifications(record, constant_count)?;
        self.validate_aliases(record, record_index)?;
        Ok(())
    }

    fn decode_inputs(
        &self,
        operation: &[u8],
        output: &mut [InputDecl; MAX_INPUTS],
    ) -> Result<usize, Status> {
        let first =
            usize::try_from(read_u32(operation, 24)?).map_err(|_| Status::PACK_INVALID)?;
        let count = usize::from(read_u16(operation, 28)?);
        if count > output.len() {
            return Err(Status::RESOURCE_LIMIT);
        }

        let mut group_offsets = [ABSENT_STRING; MAX_INPUTS];
        let mut group_ids = [0u8; MAX_INPUTS];
        let mut next_group = 1u8;
        for index in 0..count {
            let input = self.input_record(first + index)?;
            self.string_at(read_u32(input, 0)?)?;
            let semantic_kind = read_u8(input, 4)?;
            let shape = read_u8(input, 5)?;
            let flags = read_u16(input, 6)?;
            let unit_namespace = read_u32(input, 8)?;
            let group_offset = read_u32(input, 12)?;
            let first_constraint =
                usize::try_from(read_u32(input, 16)?).map_err(|_| Status::PACK_INVALID)?;
            let constraint_count = usize::from(read_u16(input, 20)?);
            if semantic_kind > 10
                || shape != 0
                || flags & !INPUT_FLAGS_V1 != 0
                || read_u16(input, 22)? != 0
                || read_u32(input, 24)? != 0
                || read_u32(input, 28)? != 0
                || constraint_count != 1
            {
                return Err(Status::PACK_INVALID);
            }
            if unit_namespace != ABSENT_STRING {
                self.string_at(unit_namespace)?;
            }
            if group_offset != ABSENT_STRING {
                self.string_at(group_offset)?;
            }

            let constraint = self.constraint_record(first_constraint)?;
            if read_u8(constraint, 1)? != 0
                || read_u32(constraint, 8)? != 0
                || read_u32(constraint, 12)? != 0
            {
                return Err(Status::PACK_INVALID);
            }
            let constraint_kind = match read_u8(constraint, 0)? {
                CONSTRAINT_GT => ConstraintKind::GreaterThan,
                CONSTRAINT_GE => ConstraintKind::GreaterOrEqual,
                _ => return Err(Status::UNSUPPORTED_OPERATION),
            };
            let constant_index = usize::try_from(read_u32(constraint, 4)?)
                .map_err(|_| Status::PACK_INVALID)?;
            let constraint_value = self.constant_at(constant_index)?;

            let same_unit_group = if group_offset == ABSENT_STRING {
                0
            } else if let Some(existing) = group_offsets[..index]
                .iter()
                .position(|candidate| *candidate == group_offset)
            {
                group_ids[existing]
            } else {
                let assigned = next_group;
                next_group = next_group.checked_add(1).ok_or(Status::RESOURCE_LIMIT)?;
                assigned
            };
            group_offsets[index] = group_offset;
            group_ids[index] = same_unit_group;
            output[index] = InputDecl {
                name: "",
                semantic_kind,
                same_unit_group,
                unit_required: flags & INPUT_FLAG_UNIT_REQUIRED != 0,
                constraint: constraint_kind,
                constraint_value,
                detail_id: read_u16(constraint, 2)?,
            };
        }
        Ok(count)
    }

    fn decode_constants(
        &self,
        output: &mut [WorkRational; MAX_CONSTANTS],
    ) -> Result<usize, Status> {
        let section = self.sections[SECTION_CONSTANTS];
        if !section.present {
            return Ok(0);
        }
        if section.count > output.len() {
            return Err(Status::RESOURCE_LIMIT);
        }
        for (index, target) in output[..section.count].iter_mut().enumerate() {
            *target = self.constant_at(index)?;
        }
        Ok(section.count)
    }

    fn constant_at(&self, index: usize) -> Result<WorkRational, Status> {
        let record = self.record(SECTION_CONSTANTS, index, CONSTANT_RECORD_SIZE)?;
        let coefficient = read_i64(record, 0)?;
        let exponent = i8::from_ne_bytes([read_u8(record, 8)?]);
        if read_u8(record, 9)? != 0
            || read_u16(record, 10)? != 0
            || read_u32(record, 12)? != 0
        {
            return Err(Status::PACK_INVALID);
        }
        let decimal = Decimal64::from_parts(coefficient, exponent)?;
        if decimal.coefficient() != coefficient || decimal.exponent() != exponent {
            return Err(Status::PACK_INVALID);
        }
        WorkRational::from_decimal(decimal)
    }

    fn decode_operation_program(
        &self,
        operation: &[u8],
        output: &mut [Instruction; MAX_VM_INSTRUCTIONS],
    ) -> Result<usize, Status> {
        let start =
            usize::try_from(read_u32(operation, 36)?).map_err(|_| Status::PACK_INVALID)?;
        let count = usize::from(read_u16(operation, 40)?);
        self.decode_program(start, count, output)
    }

    fn decode_program(
        &self,
        start: usize,
        count: usize,
        output: &mut [Instruction; MAX_VM_INSTRUCTIONS],
    ) -> Result<usize, Status> {
        if count == 0 || count > output.len() {
            return Err(Status::RESOURCE_LIMIT);
        }
        for (relative, target) in output[..count].iter_mut().enumerate() {
            let record = self.record(
                SECTION_PROGRAMS,
                start.checked_add(relative).ok_or(Status::PACK_INVALID)?,
                INSTRUCTION_RECORD_SIZE,
            )?;
            let raw = read_u32(record, 0)?;
            let opcode = u8::try_from(raw & 0xff).map_err(|_| Status::PACK_INVALID)?;
            let encoded_operand = (raw >> 8) & 0x00ff_ffff;
            let signed_operand = if encoded_operand & 0x0080_0000 != 0 {
                encoded_operand | 0xff00_0000
            } else {
                encoded_operand
            };
            *target = Instruction::new(opcode, i32::from_ne_bytes(signed_operand.to_ne_bytes()));
        }
        Ok(count)
    }

    fn validate_classifications(
        &self,
        operation: &[u8],
        constant_count: usize,
    ) -> Result<(), Status> {
        let first =
            usize::try_from(read_u32(operation, 44)?).map_err(|_| Status::PACK_INVALID)?;
        let count = usize::from(read_u16(operation, 48)?);
        if count > MAX_CLASSIFICATIONS {
            return Err(Status::RESOURCE_LIMIT);
        }
        let mut previous_priority = 0u16;
        let mut previous_id = 0u16;
        for index in 0..count {
            let classification = self.classification_record(first + index)?;
            let id = read_u16(classification, 0)?;
            let priority = read_u16(classification, 2)?;
            if id == 0
                || (index != 0 && priority < previous_priority)
                || (index != 0 && id == previous_id)
                || read_u16(classification, 14)? != 0
                || read_u32(classification, 16)? != 0
                || read_u32(classification, 20)? != 0
            {
                return Err(Status::PACK_INVALID);
            }
            self.string_at(read_u32(classification, 4)?)?;
            let start = usize::try_from(read_u32(classification, 8)?)
                .map_err(|_| Status::PACK_INVALID)?;
            let program_count = usize::from(read_u16(classification, 12)?);
            let mut program = [Instruction::new(0, 0); MAX_VM_INSTRUCTIONS];
            let decoded = self.decode_program(start, program_count, &mut program)?;
            validate_program(
                &program[..decoded],
                ProgramKind::Classification,
                0,
                constant_count,
                1,
            )?;
            previous_priority = priority;
            previous_id = id;
        }
        if read_u8(operation, 7)? & OP_FLAG_CLASSIFICATION_REQUIRED != 0 && count == 0 {
            return Err(Status::PACK_INVALID);
        }
        Ok(())
    }

    fn classify(
        &self,
        operation: &[u8],
        exact: WorkRational,
        constants: &[WorkRational],
    ) -> Result<u16, Status> {
        let first =
            usize::try_from(read_u32(operation, 44)?).map_err(|_| Status::PACK_INVALID)?;
        let count = usize::from(read_u16(operation, 48)?);
        let mut matched = 0u16;
        for index in 0..count {
            let classification = self.classification_record(first + index)?;
            let start = usize::try_from(read_u32(classification, 8)?)
                .map_err(|_| Status::PACK_INVALID)?;
            let program_count = usize::from(read_u16(classification, 12)?);
            let mut program = [Instruction::new(0, 0); MAX_VM_INSTRUCTIONS];
            let decoded = self.decode_program(start, program_count, &mut program)?;
            if execute_predicate(&program[..decoded], &[exact], constants)? {
                if matched != 0 {
                    return Err(Status::PACK_INVALID);
                }
                matched = read_u16(classification, 0)?;
            }
        }
        Ok(matched)
    }

    fn validate_aliases(&self, operation: &[u8], record_index: usize) -> Result<(), Status> {
        let first =
            usize::try_from(read_u32(operation, 52)?).map_err(|_| Status::PACK_INVALID)?;
        let count = usize::from(read_u16(operation, 56)?);
        if count == 0 {
            return Ok(());
        }
        if !self.sections[SECTION_ALIASES].present {
            return Err(Status::PACK_INVALID);
        }
        for index in 0..count {
            let alias = self.record(SECTION_ALIASES, first + index, ALIAS_RECORD_SIZE)?;
            self.string_at(read_u32(alias, 0)?)?;
            if usize::try_from(read_u32(alias, 4)?).map_err(|_| Status::PACK_INVALID)?
                != record_index
                || read_u16(alias, 10)? != 0
            {
                return Err(Status::PACK_INVALID);
            }
        }
        Ok(())
    }

    fn operation_at(&self, record_index: usize) -> Result<DynamicOperation<'a>, Status> {
        let record = self.operation_record(record_index)?;
        let method_offset = read_u32(record, 20)?;
        Ok(DynamicOperation {
            record_index,
            id: read_u32(record, 0)?,
            revision: read_u16(record, 4)?,
            key: self.string_at(read_u32(record, 8)?)?,
            signature: self.string_at(read_u32(record, 16)?)?,
            method: if method_offset == ABSENT_STRING {
                ""
            } else {
                self.string_at(method_offset)?
            },
        })
    }

    fn output_record_for(&self, operation: &[u8]) -> Result<&'a [u8], Status> {
        let first =
            usize::try_from(read_u32(operation, 32)?).map_err(|_| Status::PACK_INVALID)?;
        self.record(SECTION_OUTPUTS, first, OUTPUT_RECORD_SIZE)
    }

    fn operation_record(&self, index: usize) -> Result<&'a [u8], Status> {
        self.record(SECTION_OPERATIONS, index, OPERATION_RECORD_SIZE)
    }

    fn input_record(&self, index: usize) -> Result<&'a [u8], Status> {
        self.record(SECTION_INPUTS, index, INPUT_RECORD_SIZE)
    }

    fn constraint_record(&self, index: usize) -> Result<&'a [u8], Status> {
        self.record(SECTION_CONSTRAINTS, index, CONSTRAINT_RECORD_SIZE)
    }

    fn classification_record(&self, index: usize) -> Result<&'a [u8], Status> {
        self.record(
            SECTION_CLASSIFICATIONS,
            index,
            CLASSIFICATION_RECORD_SIZE,
        )
    }

    fn record(&self, kind: usize, index: usize, record_size: usize) -> Result<&'a [u8], Status> {
        let section = self
            .sections
            .get(kind)
            .copied()
            .ok_or(Status::PACK_INVALID)?;
        if !section.present || index >= section.count {
            return Err(Status::PACK_INVALID);
        }
        let relative = index
            .checked_mul(record_size)
            .ok_or(Status::PACK_INVALID)?;
        let start = section
            .offset
            .checked_add(relative)
            .ok_or(Status::PACK_INVALID)?;
        let end = start.checked_add(record_size).ok_or(Status::PACK_INVALID)?;
        if end > section.end()? {
            return Err(Status::PACK_INVALID);
        }
        self.bytes.get(start..end).ok_or(Status::PACK_INVALID)
    }

    fn section_bytes(&self, kind: usize) -> Result<&'a [u8], Status> {
        let section = self
            .sections
            .get(kind)
            .copied()
            .ok_or(Status::PACK_INVALID)?;
        if !section.present {
            return Err(Status::PACK_INVALID);
        }
        self.bytes
            .get(section.offset..section.end()?)
            .ok_or(Status::PACK_INVALID)
    }

    fn string_at(&self, offset: u32) -> Result<&'a str, Status> {
        if offset == ABSENT_STRING {
            return Err(Status::PACK_INVALID);
        }
        let strings = self.section_bytes(SECTION_STRINGS)?;
        let offset = usize::try_from(offset).map_err(|_| Status::PACK_INVALID)?;
        if offset % 2 != 0 {
            return Err(Status::PACK_INVALID);
        }
        let len = usize::from(read_u16(strings, offset)?);
        let start = offset.checked_add(2).ok_or(Status::PACK_INVALID)?;
        let end = start.checked_add(len).ok_or(Status::PACK_INVALID)?;
        let raw = strings.get(start..end).ok_or(Status::PACK_INVALID)?;
        str::from_utf8(raw).map_err(|_| Status::PACK_INVALID)
    }
}

fn require_section(section: Section, exact_len: usize, exact_count: usize) -> Result<(), Status> {
    if !section.present
        || (exact_len != 0 && section.len != exact_len)
        || section.count != exact_count
    {
        Err(Status::PACK_INVALID)
    } else {
        Ok(())
    }
}

fn require_record_section(
    section: Section,
    record_size: usize,
    nonempty: bool,
) -> Result<(), Status> {
    if !section.present || (nonempty && section.count == 0) {
        return Err(Status::PACK_INVALID);
    }
    let expected = section
        .count
        .checked_mul(record_size)
        .ok_or(Status::PACK_INVALID)?;
    if expected != section.len {
        return Err(Status::PACK_INVALID);
    }
    Ok(())
}

fn validate_optional_record_section(section: Section, record_size: usize) -> Result<(), Status> {
    if !section.present {
        return Ok(());
    }
    require_record_section(section, record_size, false)
}

fn align4(value: usize) -> Option<usize> {
    value.checked_add(3).map(|value| value & !3)
}
