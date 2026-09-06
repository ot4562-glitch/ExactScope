import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from compile_fact_pack import build, write_bundle
from generate_recall_benchmark import generate


class RecallBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.binary = cls.root / "target/debug/exactscope-recall"
        if not cls.binary.is_file():
            subprocess.run(
                ["cargo", "build", "-p", "exactscope-packc", "--bin", "exactscope-recall"],
                cwd=cls.root,
                check=True,
            )

    def test_generated_corpus_has_all_required_classes_and_prefetch_contract(self):
        pack, cases, manifest = generate(20260906)
        self.assertEqual(manifest["case_count"], 32)
        self.assertEqual(
            set(manifest["class_counts"]),
            {"everyday_private", "everyday_manual", "distractor", "stale_override", "no_answer", "multilingual_private"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source = tmp / "source.json"
            source.write_text(json.dumps(pack, ensure_ascii=False), encoding="utf-8")
            bundle = tmp / "bundle"
            write_bundle(build(source), bundle)
            fact_pack = bundle / "fact-pack.json"

            hit_count = 0
            miss_count = 0
            for case in cases:
                completed = subprocess.run(
                    [str(self.binary), str(fact_pack), case["question"], "2"],
                    cwd=self.root,
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )
                result = json.loads(completed.stdout)
                hits = result["h"]
                if case["expect_evidence"]:
                    self.assertEqual(result["s"], 0, case["id"])
                    self.assertTrue(hits, case["id"])
                    self.assertEqual(hits[0]["id"], case["expected_fact_id"], case["id"])
                    self.assertIn(case["expected_answer"], hits[0]["e"], case["id"])
                    hit_count += 1
                else:
                    self.assertEqual(result["s"], 8, case["id"])
                    self.assertEqual(hits, [], case["id"])
                    miss_count += 1

            self.assertEqual(hit_count, 26)
            self.assertEqual(miss_count, 6)


if __name__ == "__main__":
    unittest.main()
