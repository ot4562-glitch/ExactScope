"""Integrity tests for the FEVER pooled-corpus candidate builder."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "benchmarks/public_fever_candidate.py"
spec = importlib.util.spec_from_file_location("public_fever_candidate", MODULE)
assert spec is not None and spec.loader is not None
fever = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fever)


class PublicFeverCandidateTests(unittest.TestCase):
    def rows(self):
        rows = []
        for source_id, label, page, sentence in (
            (1, "SUPPORTS", "Page_A", 0),
            (2, "SUPPORTS", "Page_A", 1),
            (3, "REFUTES", "Page_B", 0),
            (4, "REFUTES", "Page_B", 1),
        ):
            rows.append({
                "id": source_id,
                "verifiable": "VERIFIABLE",
                "label": label,
                "claim": f"claim {source_id}",
                "evidence": [[[100 + source_id, 200 + source_id, page, sentence]]],
            })
        rows.extend([
            {"id": 5, "verifiable": "NOT VERIFIABLE", "label": "NOT ENOUGH INFO", "claim": "claim 5", "evidence": [[[105, None, None, None]]]},
            {"id": 6, "verifiable": "NOT VERIFIABLE", "label": "NOT ENOUGH INFO", "claim": "claim 6", "evidence": [[[106, None, None, None]]]},
        ])
        return rows

    def write_fixture(self, root: Path):
        source = root / "paper-dev.jsonl"
        source.write_text("".join(json.dumps(row) + "\n" for row in self.rows()), encoding="utf-8")
        wiki = root / "wiki.zip"
        pages = [
            {"id": "Page_A", "text": "Alpha zero. Alpha one.", "lines": "0\tAlpha zero.\tLink\tTarget\n1\tAlpha one.\n"},
            {"id": "Page_B", "text": "Beta zero. Beta one.", "lines": "0\tBeta zero.\n1\tBeta one.\tLink\tTarget\n"},
            {"id": "Unused", "text": "Unused.", "lines": "0\tUnused.\n"},
        ]
        with zipfile.ZipFile(wiki, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("wiki-pages/wiki-001.jsonl", "".join(json.dumps(row) + "\n" for row in pages))
        return source, wiki

    def test_selection_is_label_balanced_and_id_only(self):
        rows = self.rows()
        selected = fever.select_balanced(rows, per_label=1)
        self.assertEqual(len(selected), 3)
        self.assertEqual({row["label"] for row in selected}, set(fever.LABELS))
        mutated = [dict(row, claim="changed") for row in rows]
        self.assertEqual([r["id"] for r in selected], [r["id"] for r in fever.select_balanced(mutated, per_label=1)])

    def test_wiki_parser_preserves_sentence_ids_and_ignores_links(self):
        rows = fever.parse_wiki_lines("Page_A", "0\tAlpha.\tLink\tTarget\n2\tGamma.\n")
        self.assertEqual([row["sentence_id"] for row in rows], [0, 2])
        self.assertEqual([row["text"] for row in rows], ["Alpha.", "Gamma."])
        self.assertTrue(all("Target" not in row["text"] for row in rows))

    def test_candidate_physically_separates_gold_and_uses_whole_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, wiki = self.write_fixture(root)
            output = root / "candidate"
            result = fever.build_candidate(source, wiki, output, per_label=1)
            serving = fever.read_jsonl(output / "serving/items.jsonl")
            gold = fever.read_jsonl(output / "gold/items.jsonl")
            candidates = fever.read_jsonl(output / "serving/corpus-candidates.jsonl")
            self.assertEqual(len(serving), 3)
            self.assertTrue(all(set(row) == {"id", "claim"} for row in serving))
            self.assertTrue(all("label" not in row and "evidence_sets" not in row for row in serving))
            self.assertEqual({row["label"] for row in gold}, set(fever.LABELS))
            self.assertGreaterEqual(len(candidates), 4)
            self.assertTrue(all(set(row) == {"candidate_id", "page", "sentence_id", "text"} for row in candidates))
            self.assertTrue(result["serving_manifest"]["oracle_assisted_corpus"])
            self.assertFalse(result["serving_manifest"]["qualification_eligible"])
            serving_manifest = (output / "serving/manifest.json").read_text(encoding="utf-8")
            self.assertNotIn('"label_counts"', serving_manifest)
            self.assertNotIn('"evidence_sets"', serving_manifest)

    def test_missing_annotated_sentence_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, wiki = self.write_fixture(root)
            rows = self.rows()
            for row in rows:
                if row["label"] == "SUPPORTS":
                    row["evidence"] = [[[1, 2, "Page_A", 99]]]
            source.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            with self.assertRaisesRegex(fever.FeverCandidateError, "did not resolve"):
                fever.build_candidate(source, wiki, root / "bad", per_label=1)


if __name__ == "__main__":
    unittest.main()
