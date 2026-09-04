#![forbid(unsafe_code)]
#![doc = "Cross-target conformance harness for `ExactScope`."]

//! Host-side conformance checks compare normalized results across fused,
//! dynamic-pack, C ABI, and WebAssembly execution paths. The implemented
//! corpora pin fused versus canonical `.xsp` behavior for economics and bounded
//! statistics-vector kernels.

/// Conformance corpus format version.
pub const CORPUS_FORMAT_VERSION: u16 = 1;

#[cfg(test)]
mod tests {
    use exactscope_kernel::{
        classification_key, evaluate_operation, evaluate_statistics_operation, Decimal64,
        ScalarValue, Status, PED_MID_OPERATION, SEMANTIC_PRICE, SEMANTIC_QUANTITY,
    };
    use exactscope_pack::{
        PackView, StatisticsRegistry, ECON_UNDERGRAD_PACK_SLOT, STATISTICS_CORE_PACK_SLOT,
    };

    const SOURCE: &str = include_str!("../../../spec/examples/econ-undergrad-minimal.xsp.json");
    const STATISTICS_SOURCE: &str = include_str!("../../../packs/statistics-core.xsp.json");

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

    #[test]
    fn fused_and_dynamic_statistics_results_are_identical() {
        let bytes =
            exactscope_packc::compile_source(STATISTICS_SOURCE).expect("compile statistics pack");
        let pack = PackView::parse(&bytes).expect("parse statistics pack");

        assert_statistics_parity(&pack, b"stats.sum", &[&["0.1", "0.2", "0.3"]]);
        assert_statistics_parity(&pack, b"stats.mean", &[&["1", "2", "2"]]);
        assert_statistics_parity(
            &pack,
            b"stats.mean.weighted",
            &[&["10", "20", "40"], &["1", "2", "1"]],
        );
        assert_statistics_parity(&pack, b"stats.var.pop", &[&["1", "2", "3", "4"]]);
        assert_statistics_parity(&pack, b"stats.var.sample", &[&["1", "2", "3", "4"]]);
        assert_statistics_parity(&pack, b"stats.sd.pop", &[&["1", "2", "3"]]);
        assert_statistics_parity(&pack, b"stats.sd.sample", &[&["1", "2", "3"]]);
        assert_statistics_parity(
            &pack,
            b"stats.cov.pop",
            &[&["1", "2", "3"], &["2", "4", "8"]],
        );
        assert_statistics_parity(
            &pack,
            b"stats.cov.sample",
            &[&["1", "2", "3"], &["2", "4", "8"]],
        );
        assert_statistics_parity(
            &pack,
            b"stats.corr.pearson",
            &[&["1", "2", "3"], &["1", "2", "4"]],
        );
        assert_statistics_parity(
            &pack,
            b"stats.regression.linear",
            &[&["1", "2", "3"], &["3", "5", "7"]],
        );

        // Failure semantics are part of conformance too, not just successful values.
        assert_statistics_parity(&pack, b"stats.var.sample", &[&["1"]]);
        assert_statistics_parity(
            &pack,
            b"stats.corr.pearson",
            &[&["1", "2", "3"], &["2", "2", "2"]],
        );
    }

    fn assert_statistics_parity(pack: &PackView<'_>, key: &[u8], arguments: &[&[&str]]) {
        let fused_operation = StatisticsRegistry::new()
            .lookup(key)
            .expect("fused statistics operation exists")
            .operation;
        let dynamic_operation = pack
            .operation_by_key(key)
            .expect("dynamic statistics operation exists");
        let vectors: Vec<Vec<Decimal64>> = arguments
            .iter()
            .map(|values| {
                values
                    .iter()
                    .map(|value| {
                        Decimal64::parse_ascii(value.as_bytes())
                            .expect("statistics conformance decimal is valid")
                    })
                    .collect()
            })
            .collect();
        let vector_refs: Vec<&[Decimal64]> = vectors.iter().map(Vec::as_slice).collect();
        let fused =
            evaluate_statistics_operation(STATISTICS_CORE_PACK_SLOT, fused_operation, &vector_refs);
        let dynamic = pack
            .evaluate_statistics(STATISTICS_CORE_PACK_SLOT, dynamic_operation, &vector_refs)
            .expect("validated statistics operation remains readable");

        assert_eq!(
            dynamic, fused,
            "normalized statistics result drift for {}",
            fused_operation.key
        );
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
