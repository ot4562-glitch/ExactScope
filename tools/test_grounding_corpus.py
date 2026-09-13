"""Tests for the tiny deterministic local text-corpus index."""
from __future__ import annotations

from collections import defaultdict
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools")]

from grounding_canonical import canonical_bytes
from grounding_corpus import (
    BM25_B,
    BM25_K1,
    BINARY_FORMAT_MAJOR,
    BINARY_FORMAT_MINOR,
    BINARY_HEADER_SIZE,
    BINARY_MAGIC,
    BINARY_POSTING_RECORD_SIZE,
    BINARY_SENTENCE_RECORD_SIZE,
    BINARY_TERM_REF_RECORD_SIZE,
    CorpusError,
    ValidatedIndex,
    binary_index_bytes,
    binary_index_sha256,
    build_index,
    compile_index,
    index_sha256,
    load_index,
    search,
    sentence_spans,
    tokenize,
)


class GroundingCorpusTests(unittest.TestCase):
    def documents(self):
        return [
            {"id": "manual/rover.md", "title": "Rover Mini", "text": "Rover Mini uses replacement filter RM-F42 and needs 50 cm clearance."},
            {"id": "office/parking.txt", "title": "Parking note", "text": "Mina parked the car in B3-04."},
            {"id": "ko/locker.txt", "title": "보관함", "text": "아람 보관함 라벨 색상은 cobalt이다."},
        ]

    def test_build_is_deterministic_and_sorted(self):
        first = build_index(self.documents())
        second = build_index(reversed(self.documents()))
        self.assertEqual(canonical_bytes(first), canonical_bytes(second))
        self.assertEqual(index_sha256(first), index_sha256(second))
        self.assertEqual([doc["id"] for doc in first["documents"]], sorted(doc["id"] for doc in first["documents"]))

    def test_bm25_returns_relevant_local_document(self):
        index = build_index(self.documents())
        hits = search(index, "Which replacement filter does Rover Mini use?", top_k=2)
        self.assertTrue(hits)
        self.assertEqual(hits[0]["id"], "manual/rover.md")
        self.assertIn("RM-F42", hits[0]["text"])

    def test_bounded_heap_ranking_matches_previous_full_sort_order(self):
        documents = [
            {
                "id": f"doc/{ordinal:03d}",
                "title": f"Candidate {ordinal:03d}",
                "text": " ".join(
                    ["target"] * (1 + ordinal % 5)
                    + ["common"] * (1 + (ordinal * 3) % 4)
                    + (["rare"] if ordinal % 7 == 0 else [])
                ),
            }
            for ordinal in range(64)
        ]
        index = build_index(documents)
        question = "target common rare"
        top_k = 12
        actual = search(index, question, top_k=top_k)

        query_terms = list(dict.fromkeys(tokenize(question)))
        docs = index["documents"]
        postings = index["postings"]
        n_docs = len(docs)
        average = index["total_tokens"] / n_docs
        scores = defaultdict(float)
        matched_terms = defaultdict(int)
        for term in query_terms:
            rows = postings.get(term)
            if not rows:
                continue
            df = len(rows)
            idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
            for ordinal, frequency in rows:
                length = docs[ordinal]["token_count"] or 1
                denominator = frequency + BM25_K1 * (1.0 - BM25_B + BM25_B * length / average)
                scores[ordinal] += idf * (frequency * (BM25_K1 + 1.0)) / denominator
                matched_terms[ordinal] += 1
        expected_ordinals = sorted(
            scores,
            key=lambda ordinal: (-scores[ordinal], -matched_terms[ordinal], docs[ordinal]["id"].encode("utf-8")),
        )[:top_k]
        self.assertEqual([hit["id"] for hit in actual], [docs[ordinal]["id"] for ordinal in expected_ordinals])
        self.assertEqual([hit["score"] for hit in actual], [scores[ordinal] for ordinal in expected_ordinals])

    def test_unicode_query_retrieves_korean_document(self):
        index = build_index(self.documents())
        hits = search(index, "아람 보관함 라벨 색상은?", top_k=1)
        self.assertEqual(hits[0]["id"], "ko/locker.txt")

    def test_load_requires_canonical_bytes_and_detects_tamper(self):
        index = build_index(self.documents())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corpus.json"
            path.write_bytes(canonical_bytes(index))
            loaded = load_index(path)
            self.assertEqual(index_sha256(index), index_sha256(loaded))
            path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(CorpusError, "canonical"):
                load_index(path)

    def test_compiled_index_is_parity_safe_and_owned(self):
        raw = build_index(self.documents())
        compiled = compile_index(raw)
        self.assertIsInstance(compiled, ValidatedIndex)
        question = "Which replacement filter does Rover Mini use?"
        expected = search(raw, question, top_k=2)
        self.assertEqual(expected, search(compiled, question, top_k=2))
        self.assertEqual(index_sha256(raw), index_sha256(compiled))

        raw["documents"][0]["title"] = "mutated caller storage"
        self.assertEqual(expected, search(compiled, question, top_k=2))
        exported = compiled.to_canonical_dict()
        exported["documents"][0]["title"] = "mutated exported copy"
        self.assertEqual(expected, search(compiled, question, top_k=2))
        with self.assertRaises(TypeError):
            ValidatedIndex(object(), exported)

    def test_compiled_load_and_build_preserve_canonical_identity(self):
        raw = build_index(self.documents())
        built = build_index(self.documents(), compiled=True)
        self.assertIsInstance(built, ValidatedIndex)
        self.assertEqual(index_sha256(raw), index_sha256(built))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corpus.json"
            path.write_bytes(canonical_bytes(raw))
            loaded = load_index(path, compiled=True)
            self.assertIsInstance(loaded, ValidatedIndex)
            self.assertEqual(index_sha256(raw), index_sha256(loaded))

    def test_binary_index_is_deterministic_compiled_parity_and_self_checking(self):
        raw = build_index(self.documents())
        compiled = compile_index(raw)
        first = binary_index_bytes(raw)
        second = binary_index_bytes(compiled)
        self.assertEqual(first, second)
        self.assertEqual(binary_index_sha256(raw), binary_index_sha256(compiled))
        self.assertGreater(len(first), BINARY_HEADER_SIZE)
        header = struct.unpack_from("<4sHHIIIIIQIIIIIII", first, 0)
        (
            magic,
            major,
            minor,
            header_size,
            flags,
            document_count,
            term_count,
            posting_count,
            total_tokens,
            documents_offset,
            terms_offset,
            postings_offset,
            strings_offset,
            strings_length,
            crc,
            sentence_count,
        ) = header
        self.assertEqual((magic, major, minor), (BINARY_MAGIC, BINARY_FORMAT_MAJOR, BINARY_FORMAT_MINOR))
        self.assertEqual((header_size, flags), (BINARY_HEADER_SIZE, 0))
        self.assertEqual(document_count, raw["document_count"])
        self.assertEqual(term_count, len(raw["postings"]))
        self.assertEqual(posting_count, sum(len(rows) for rows in raw["postings"].values()))
        self.assertEqual(total_tokens, raw["total_tokens"])
        expected_sentence_count = sum(len(sentence_spans(document["text"])) for document in raw["documents"])
        expected_term_refs = sum(
            len(set(tokenize(sentence)) & set(raw["postings"]))
            for document in raw["documents"]
            for sentence, _, _ in sentence_spans(document["text"])
        )
        self.assertEqual(sentence_count, expected_sentence_count)
        self.assertEqual(documents_offset, BINARY_HEADER_SIZE)
        self.assertLess(documents_offset, terms_offset)
        self.assertLess(terms_offset, postings_offset)
        sentences_offset = postings_offset + posting_count * BINARY_POSTING_RECORD_SIZE
        term_refs_offset = sentences_offset + sentence_count * BINARY_SENTENCE_RECORD_SIZE
        self.assertLessEqual(term_refs_offset, strings_offset)
        self.assertEqual((strings_offset - term_refs_offset) % BINARY_TERM_REF_RECORD_SIZE, 0)
        self.assertEqual((strings_offset - term_refs_offset) // BINARY_TERM_REF_RECORD_SIZE, expected_term_refs)
        self.assertEqual(strings_offset + strings_length, len(first))
        self.assertEqual(zlib.crc32(first[BINARY_HEADER_SIZE:]) & 0xFFFF_FFFF, crc)

    def test_sentence_spans_match_projection_split_and_utf8_offsets(self):
        text = "  첫 문장.  Second sentence!\n\n 마지막 줄  "
        spans = sentence_spans(text)
        self.assertEqual([row[0] for row in spans], ["첫 문장.", "Second sentence!", "마지막 줄"])
        encoded = text.encode("utf-8")
        for sentence, byte_start, byte_length in spans:
            self.assertEqual(encoded[byte_start:byte_start + byte_length].decode("utf-8"), sentence)

    def test_limits_and_duplicates_fail_closed(self):
        with self.assertRaisesRegex(CorpusError, "duplicate"):
            build_index([self.documents()[0], self.documents()[0]])
        index = build_index(self.documents())
        for top_k in (0, 17):
            with self.subTest(top_k=top_k), self.assertRaisesRegex(CorpusError, "top_k"):
                search(index, "Rover", top_k=top_k)


if __name__ == "__main__":
    unittest.main()
