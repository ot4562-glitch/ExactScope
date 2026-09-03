#![forbid(unsafe_code)]
#![doc = "Cross-target conformance harness for `ExactScope`."]

//! Host-side conformance checks compare normalized results across fused,
//! dynamic-pack, C ABI, and WebAssembly execution paths. The first implemented
//! corpus pins fused versus canonical `.xsp` behavior for the economics slice.

/// Conformance corpus format version.
pub const CORPUS_FORMAT_VERSION: u16 = 1;

#[cfg(test)]
mod tests {
    use exactscope_kernel::{
        classification_key, evaluate_operation, Decimal64, ScalarValue, Status, PED_MID_OPERATION,
        SEMANTIC_PRICE, SEMANTIC_QUANTITY,
    };
    use exactscope_pack::{PackView, ECON_UNDERGRAD_PACK_SLOT};

    const SOURCE: &str = include_str!("../../../spec/examples/econ-undergrad-minimal.xsp.json");

    #[derive(Clone, Copy)]
    struct Case {
        name: &'static str,
        values: [&'static [u8]; 4],
    }

    const CASES: [Case; 5] = [
        Case {
            name: "elastic",
            values: [b"10000", b"12000", b"100", b"80"],
        },
        Case {
            name: "unit-elastic",
            values: [b"10", b"20", b"20", b"10"],
        },
        Case {
            name: "inelastic",
            values: [b"10", b"12", b"100", b"95"],
        },
        Case {
            name: "unchanged-price",
            values: [b"10", b"10", b"100", b"80"],
        },
        Case {
            name: "negative-initial-price",
            values: [b"-1", b"10", b"100", b"80"],
        },
    ];

    #[test]
    fn fused_and_dynamic_economics_results_are_identical() {
        let bytes = exactscope_packc::compile_source(SOURCE).expect("compile canonical pack");
        let pack = PackView::parse(&bytes).expect("parse canonical pack");
        let dynamic_operation = pack
            .operation_by_key(PED_MID_OPERATION.key.as_bytes())
            .expect("dynamic operation exists");

        for case in CASES {
            let arguments = arguments(case.values);
            let fused =
                evaluate_operation(ECON_UNDERGRAD_PACK_SLOT, &PED_MID_OPERATION, &arguments);
            let dynamic = pack
                .evaluate(ECON_UNDERGRAD_PACK_SLOT, dynamic_operation, &arguments)
                .expect("validated dynamic operation remains readable");

            assert_eq!(dynamic, fused, "normalized result drift for {}", case.name);

            if fused.status == Status::OK {
                let fused_classification =
                    classification_key(&PED_MID_OPERATION, fused.classification_id);
                let dynamic_classification = pack
                    .classification_key(dynamic_operation, dynamic.classification_id)
                    .ok();
                assert_eq!(
                    dynamic_classification, fused_classification,
                    "classification key drift for {}",
                    case.name
                );
            }
        }
    }

    fn arguments(values: [&[u8]; 4]) -> [ScalarValue; 4] {
        [
            scalar(values[0], SEMANTIC_PRICE),
            scalar(values[1], SEMANTIC_PRICE),
            scalar(values[2], SEMANTIC_QUANTITY),
            scalar(values[3], SEMANTIC_QUANTITY),
        ]
    }

    fn scalar(text: &[u8], semantic_kind: u8) -> ScalarValue {
        ScalarValue::new(
            Decimal64::parse_ascii(text).expect("conformance decimal is valid"),
            semantic_kind,
            0,
        )
    }
}
