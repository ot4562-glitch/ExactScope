"""No model/credential required: corpus oracle, surface isolation and paired metrics."""
import copy
import os
import unittest

from capability_benchmark import ROOT, aggregate, ratio, score, surface
from run_benchmark import CoreBridge
from statistics_corpus import load, oracle, templates, validate_rows


class CapabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = ROOT / "adapters/capabilities/statistics-core-8-ai-r1"
        cls.core = CoreBridge(ROOT / "target/debug" / ("exactscope-core.exe" if os.name == "nt" else "exactscope-core"))

    def test_corpus_matches_seed_and_real_runtime(self):
        rows = templates()
        self.assertEqual(len(rows), 240)
        self.assertEqual(rows, templates())
        self.assertNotEqual(rows, templates(17))
        validate_rows(rows, self.core)
        stored = [load(line) for line in (ROOT / "benchmarks/statistics-v0.1.jsonl").read_bytes().splitlines()]
        self.assertEqual(rows, stored)
        self.assertEqual(sum(r["state"] == "ambiguous" for r in rows), 15)
        # Two S5 templates also exercise constant-vector DOMAIN_ERROR.
        self.assertEqual(sum(r["state"] == "typed-failure" for r in rows), 17)

    def test_gold_tamper_is_not_silently_repaired(self):
        row = templates()[0]
        row["expected"]["v"] = "9999"
        with self.assertRaisesRegex(ValueError, "gold mismatch"):
            validate_rows([row], self.core)

    def test_independent_boundary_vectors(self):
        calls = [{"op": "stats.mean", "a": [[]]},
                 {"op": "stats.sum", "a": [["1"] * 64]},
                 {"op": "stats.mean.weighted", "a": [["1"], ["-1"]]},
                 {"op": "stats.corr.pearson", "a": [["2", "2"], ["1", "2"]]},
                 {"op": "stats.sd.sample", "a": [["1", "2", "3"]]}]
        for call in calls:
            expected = oracle(call)
            actual, _ = self.core.call("eval", call)
            self.assertTrue(all(actual.get(k) == v for k, v in expected.items()), (actual, expected))

    def test_arm_isolation_and_exact_error_fidelity(self):
        row = {"id": "test", "family": "S1", "state": "supported",
               "call": {"op": "stats.mean", "a": [["1", "3"]]}, "expected": {"s": 0, "v": "2"}}
        text = '{"op":"stats.mean","a":[["1","3"]]}'
        for arm in ("A", "B", "E"):
            record = score(row, text, surface(self.bundle, arm), self.core)
            self.assertFalse(record["valid_call"])
            self.assertIsNone(record["core_response"])
        for arm in ("C", "D"):
            self.assertTrue(score(row, text, surface(self.bundle, arm), self.core)["correct"])
        forbidden = '{"op":"econ.inflation.cpi_pct","a":["100","103"]}'
        self.assertFalse(score(row, forbidden, surface(self.bundle, "D"), self.core)["valid_call"])
        row.update(state="typed-failure", expected={"s": 13, "e": "DIVIDE_BY_ZERO"})
        failed = score(row, '{"p":[{"o":"div","a":["1","0"]}]}', surface(self.bundle, "D"), self.core)
        self.assertTrue(failed["correct"])
        self.assertTrue(failed["failure_fidelity"])
        self.assertFalse(failed["wrong_numeric"])

    def test_invalid_output_and_missing_method_preservation(self):
        row = next(r for r in templates() if r["state"] == "ambiguous")
        assets = surface(self.bundle, "D")
        for text in ('{"v":"NaN"}', '{"v":true}', '{"v":"1","v":"2"}', 'prose {"v":"1"}'):
            self.assertFalse(score(row, text, assets, self.core)["correct"])
        self.assertTrue(score(row, '{"e":"AMBIGUOUS_METHOD"}', assets, self.core)["correct"])
        self.assertTrue(score(row, '{"v":"1"}', surface(self.bundle, "A"), self.core)["wrong_numeric"])

    def records(self, with_e=True):
        rows = []
        for arm, values in {"A": [0, 0], "B": [0, 1], "C": [1, 0], "D": [1, 0], "E": [1, 1]}.items():
            if arm == "E" and not with_e:
                continue
            for i, value in enumerate(values):
                rows.append({"arm": arm, "id": str(i), "family": "S1", "correct": bool(value),
                             "wrong_numeric": not bool(value)})
        return rows

    def test_crr_density_and_raw_denominators(self):
        result = aggregate(self.records(), {"artifact_bytes": 102400})
        self.assertEqual(result["crr"]["value"], .5)
        self.assertEqual(result["density"]["artifact_bytes"]["value"], .5)
        self.assertEqual(result["density"]["artifact_bytes"]["raw_denominator"], 102400)
        self.assertIsNone(result["density"]["joules"]["value"])
        self.assertIsNone(aggregate(self.records(False))["crr"]["value"])
        for denominator in (0, -1, None):
            self.assertIsNone(ratio(1, denominator)["value"])
        records = self.records()
        for row in records:
            if row["arm"] == "E":
                row["correct"] = False
        self.assertIn("does not outperform", aggregate(records)["crr"]["reason"])

    def test_unpaired_and_nonfinite_costs_fail_closed(self):
        records = self.records()
        with self.assertRaises(ValueError):
            aggregate(records[:-1])
        with self.assertRaises(ValueError):
            aggregate(records + [copy.deepcopy(records[0])])
        for value in (float("nan"), float("inf"), True):
            with self.assertRaises(ValueError):
                aggregate(records, {"joules": value})

    def test_grammar_namespaces_do_not_change_literals(self):
        assets = surface(self.bundle, "D")
        grammar = assets["grammar"]
        self.assertIn("lane0-root", grammar)
        self.assertIn("lane1-root", grammar)
        self.assertIn("stats.mean", grammar)
        self.assertNotIn("lane1-stats", grammar)
        self.assertEqual(assets["top_level_tool_count"], 2)


if __name__ == "__main__":
    unittest.main()
