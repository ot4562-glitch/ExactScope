import json
import tempfile
import unittest
from pathlib import Path

from compile_fact_pack import FactPackError, build, validate_source, verify_bundle, write_bundle


class FactPackCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.source = cls.root / "spec/examples/recall-fact-pack.json"

    def test_example_compiles_and_verifies_immutably(self):
        files = build(self.source)
        self.assertIn("fact-pack.json", files)
        self.assertIn("xs-recall.gbnf", files)
        self.assertIn("xs-recall.tool.json", files)
        self.assertIn("constrained-prompt.txt", files)
        pack = json.loads(files["fact-pack.json"])
        self.assertEqual(pack["format"], "exactscope.fact-pack")
        self.assertEqual([fact["id"] for fact in pack["facts"]], sorted(fact["id"] for fact in pack["facts"]))
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "bundle"
            write_bundle(files, output)
            manifest = verify_bundle(output)
            self.assertEqual(manifest["measurements"]["fact_count"], 4)
            write_bundle(files, output)

    def test_duplicate_alias_after_normalization_is_rejected(self):
        document = json.loads(self.source.read_text(encoding="utf-8"))
        document["facts"][0]["aliases"] = ["Red Glass Author", "red-glass-author"]
        with self.assertRaisesRegex(FactPackError, "duplicate aliases after normalization"):
            validate_source(document)

    def test_ambiguous_alias_across_facts_is_rejected(self):
        document = json.loads(self.source.read_text(encoding="utf-8"))
        document["facts"][1]["aliases"] = ["red glass author"]
        with self.assertRaisesRegex(FactPackError, "ambiguous exact alias"):
            validate_source(document)

    def test_source_fact_order_does_not_change_compiled_fact_order(self):
        document = json.loads(self.source.read_text(encoding="utf-8"))
        document["facts"] = list(reversed(document["facts"]))
        compiled = validate_source(document)
        self.assertEqual([fact["id"] for fact in compiled["facts"]], sorted(fact["id"] for fact in compiled["facts"]))

    def test_alias_normalization_preserves_utf8(self):
        document = json.loads(self.source.read_text(encoding="utf-8"))
        document["facts"][1]["aliases"] = ["아람의   수도?", "아람 수도"]
        compiled = validate_source(document)
        korean = next(fact for fact in compiled["facts"] if fact["id"] == "demo.korean.capital")
        self.assertEqual(korean["aliases"], ["아람 수도", "아람의 수도"])


if __name__ == "__main__":
    unittest.main()
