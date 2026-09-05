"""Source-level generator regression tests; never execute runtime artifacts."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import generate_statistics_metadata as metadata
import generate_domain_metadata as domains


class StatisticsMetadataTests(unittest.TestCase):
    def setUp(self):
        self.pack = metadata.load(metadata.ROOT / metadata.PACK)
        self.bindings = metadata.load(metadata.ROOT / metadata.BINDINGS)

    def copy_domain_generator_inputs(self, root):
        relative_paths = [
            Path("spec/capabilities/domain-descriptors.json"),
            Path("packs/statistics-core.xsp.json"),
            Path("spec/implementation/statistics-kernel-bindings.json"),
            Path("spec/examples/econ-undergrad-minimal.xsp.json"),
            Path("spec/implementation/economics-operation-bindings.json"),
            Path("crates/exactscope-kernel/src/operation.rs"),
            Path("spec/registries/vm-opcodes.json"),
            Path("spec/registries/semantic-kinds.json"),
            Path("crates/exactscope-kernel/Cargo.toml"),
            Path("crates/exactscope-tinyjson/Cargo.toml"),
            Path("crates/exactscope-wasm/Cargo.toml"),
        ]
        for relative in relative_paths:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((metadata.ROOT / relative).read_bytes())

    def test_generated_sources_are_current_and_order_independent(self):
        rows = metadata.validate(self.pack, self.bindings)
        self.pack['operations'].reverse()
        self.bindings['operations'].reverse()
        reordered = metadata.validate(self.pack, self.bindings)
        for output, render in ((metadata.OUTPUT, metadata.render),
                               (metadata.KERNEL_OUTPUT, metadata.render_kernels),
                               (metadata.DISPATCH_OUTPUT, metadata.render_dispatch)):
            self.assertEqual(render(rows), render(reordered))
            self.assertEqual((metadata.ROOT / output).read_bytes(), render(rows).encode())

    def test_stable_kernel_namespace_is_independent_from_pack_ids(self):
        expected = {'sum': 1, 'mean': 2, 'weighted_mean': 3,
                    'variance_population': 4, 'variance_sample': 5,
                    'covariance_population': 6, 'covariance_sample': 7,
                    'correlation': 8, 'linear_regression': 9,
                    'standard_deviation_population': 10, 'standard_deviation_sample': 11}
        rows = metadata.validate(self.pack, self.bindings)
        self.assertEqual({b['kernel_name']: b['kernel_id'] for _, b in rows}, expected)
        self.assertTrue(any(op['id'] != b['kernel_id'] for op, b in rows))

    def test_invalid_bindings_fail_closed(self):
        for field, value in [('kernel_id', True), ('rust_function', 'statistics_missing'),
                             ('result_kind', 'code'), ('result_kind', 'regression'),
                             ('kernel_name', 'different'), ('cargo_feature', 'stats-other')]:
            with self.subTest(field=field, value=value):
                bindings = copy.deepcopy(self.bindings)
                bindings['operations'][0][field] = value
                with self.assertRaises(ValueError):
                    metadata.validate(self.pack, bindings)
        self.bindings['operations'].append(self.bindings['operations'][0])
        with self.assertRaises(ValueError):
            metadata.validate(self.pack, self.bindings)

    def test_feature_forwarding_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for crate in ('kernel', 'tinyjson', 'wasm'):
                relative = Path(f'crates/exactscope-{crate}/Cargo.toml')
                (root / relative).parent.mkdir(parents=True)
                (root / relative).write_bytes((metadata.ROOT / relative).read_bytes())
            metadata.validate_features(self.bindings['operations'], root)
            path = root / 'crates/exactscope-wasm/Cargo.toml'
            path.write_text(path.read_text().replace('exactscope-kernel/stats-sum',
                                                    'exactscope-kernel/stats-mean'))
            with self.assertRaisesRegex(ValueError, 'feature declaration drift'):
                metadata.validate_features(self.bindings['operations'], root)

    def test_domain_selection_is_current(self):
        for relative, content in domains.outputs().items():
            self.assertEqual((metadata.ROOT / relative).read_bytes(), content.encode())

    def test_scalar_handwritten_drift_is_rejected(self):
        for before, after, error in [
            ('from_integer(2)', 'from_integer(3)', 'constant drift'),
            ('Instruction::new(1, 3)', 'Instruction::new(1, 2)', 'program drift: PED_PROGRAM'),
            ('Instruction::new(14, 0)', 'Instruction::new(18, 0)', 'program drift: CLASS_INELASTIC'),
            ('Instruction::new(16, 0)', 'Instruction::new(18, 0)', 'program drift: CLASS_UNIT'),
            ('Instruction::new(18, 0)', 'Instruction::new(14, 0)', 'program drift: CLASS_ELASTIC'),
        ]:
            with self.subTest(before=before), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.copy_domain_generator_inputs(root)
                path = root / 'crates/exactscope-kernel/src/operation.rs'
                text = path.read_text(encoding='utf-8')
                self.assertIn(before, text)
                path.write_text(text.replace(before, after, 1), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, error):
                    domains.outputs(root)

    def test_scalar_binding_drift_is_rejected(self):
        mutations = [
            lambda b: b.update(rust_program_symbol='MISSING'),
            lambda b: b.update(rust_constants_symbol='MISSING'),
            lambda b: b.update(rust_operation_symbol='bad symbol'),
            lambda b: b.update(method='midpoint'),
            lambda b: b['rust_classification_predicates'].update(inelastic='MISSING'),
            lambda b: b['rust_classification_predicates'].pop('elastic'),
            lambda b: b['rust_classification_predicates'].update(extra='CLASS_EXTRA_PROGRAM'),
            lambda b: b.update(key='econ.missing'),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.copy_domain_generator_inputs(root)
                path = root / 'spec/implementation/economics-operation-bindings.json'
                bindings = metadata.load(path)
                mutate(bindings['operations'][0])
                path.write_text(json.dumps(bindings), encoding='utf-8')
                with self.assertRaises(ValueError):
                    domains.outputs(root)

    def test_scalar_metadata_uses_descriptor_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_domain_generator_inputs(root)
            path = root / 'spec/examples/econ-undergrad-minimal.xsp.json'
            source = metadata.load(path)
            op = source['operations'][0]
            op.update(id=302, revision=2, method='alternate')
            op['inputs'][0].update(name='price_before', semantic='quantity', unit_required=True)
            op['inputs'][0]['constraints'][0].update(kind='ne', value='1', detail_id=7)
            op['outputs'][0]['semantic'] = 'number'
            op['output_policy']['scale'] = 4
            op['classifications'][0]['id'] = 9
            path.write_text(json.dumps(source), encoding='utf-8')
            rendered = next(iter(domains.outputs(root).values()))
            for expected in ('id: 302,', 'revision: 2,', 'method: "alternate",',
                             'econ.ped.mid(price_before,p2,q1,q2)', 'semantic_kind: 4,',
                             'unit_required: true,', 'ConstraintKind::NotEqual', 'detail_id: 7,',
                             'output_semantic_kind: 0,', 'output_scale: 4,', 'id: 9,'):
                self.assertIn(expected, rendered)

    def test_scalar_domain_rejects_shared_operation_feature(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_domain_generator_inputs(root)
            source_path = root / "spec/examples/econ-undergrad-minimal.xsp.json"
            binding_path = root / "spec/implementation/economics-operation-bindings.json"
            source = json.loads(source_path.read_text(encoding="utf-8"))
            binding = json.loads(binding_path.read_text(encoding="utf-8"))
            duplicate_source = copy.deepcopy(source["operations"][0])
            duplicate_source["id"] += 10000
            duplicate_source["key"] = "econ.ped.alt"
            source["operations"].append(duplicate_source)
            duplicate_binding = copy.deepcopy(binding["operations"][0])
            duplicate_binding["key"] = "econ.ped.alt"
            binding["operations"].append(duplicate_binding)
            source_path.write_text(json.dumps(source), encoding="utf-8")
            binding_path.write_text(json.dumps(binding), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate scalar operation cargo feature"):
                domains.outputs(root)

    def test_scalar_source_rejects_ambiguous_or_ignored_metadata(self):
        for mutation, error in [('duplicate_id', 'duplicate source operation id'),
                                ('classification_field', 'unsupported classification fields')]:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.copy_domain_generator_inputs(root)
                path = root / 'spec/examples/econ-undergrad-minimal.xsp.json'
                source = metadata.load(path)
                if mutation == 'duplicate_id':
                    duplicate = copy.deepcopy(source['operations'][0])
                    duplicate['key'] = 'econ.ped.alt'
                    source['operations'].append(duplicate)
                else:
                    source['operations'][0]['classifications'][0]['extra'] = True
                path.write_text(json.dumps(source), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, error):
                    domains.outputs(root)

    def test_statistics_descriptor_cannot_diverge_from_statistics_generator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_domain_generator_inputs(root)
            descriptor_path = root / "spec/capabilities/domain-descriptors.json"
            descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
            alternate = Path("spec/examples/statistics-shadow.xsp.json")
            target = root / alternate
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((root / "packs/statistics-core.xsp.json").read_bytes())
            descriptor["domains"]["statistics"]["semantic_source"] = alternate.as_posix()
            descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Statistics descriptor diverges"):
                domains.outputs(root)

    def test_specialization_forwarding_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for crate in ('kernel', 'tinyjson', 'wasm'):
                relative = Path(f'crates/exactscope-{crate}/Cargo.toml')
                (root / relative).parent.mkdir(parents=True)
                text = (metadata.ROOT / relative).read_text()
                if crate == 'wasm':
                    text = text.replace('exactscope-tinyjson/stats-specialized',
                                        'exactscope-tinyjson/econ-specialized')
                (root / relative).write_text(text)
            with self.assertRaisesRegex(ValueError, 'specialization feature forwarding drift'):
                metadata.validate_features(self.bindings['operations'], root)


if __name__ == '__main__':
    unittest.main()
