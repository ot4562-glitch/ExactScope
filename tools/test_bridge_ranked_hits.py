#!/usr/bin/env python3
"""Tests for the index-free Bridge ranked-hit attach projector."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "adapters/bridge"
if str(BRIDGE) not in sys.path:
    sys.path.insert(0, str(BRIDGE))

from ranked_hits import (  # noqa: E402
    RankedHitError,
    prepare_ranked_hits,
    project_host_ranked_hybrid_h1,
    project_prepared,
    project_tiers,
)


def hit(hit_id: str, title: str, text: str) -> dict[str, str]:
    return {"id": hit_id, "title": title, "text": text}


class RankedHitAttachTests(unittest.TestCase):
    def test_candidate_local_rarity_selects_specific_sentence_without_index(self):
        hits = [
            hit("a", "Desk", "The office is open. The help desk is in Room 12."),
            hit("b", "Office", "The office is closed on Sunday. General office information."),
            hit("c", "Building", "The building has an office lobby. Visitors sign in."),
        ]
        prepared = prepare_ranked_hits(hits, "Where is the help desk?")
        tier = project_prepared(prepared, max_bytes=1024)
        self.assertIsNotNone(tier.payload)
        self.assertIn("Room 12", tier.emitted[0]["snippet"])
        self.assertNotIn("postings", vars(sys.modules["ranked_hits"]))

    def test_exact_body_dedup_preserves_query_named_title_identity(self):
        body = "Shared sentence about the station. The code is K-9."
        hits = [
            hit("a", "Alpha", body),
            hit("b", "Beta", body),
            hit("c", "Other", body),
        ]
        prepared = prepare_ranked_hits(hits, "What is the Beta code?")
        self.assertEqual(prepared.retrieved_count, 3)
        self.assertEqual(prepared.deduped_count, 2)
        self.assertEqual([item.hit["id"] for item in prepared.hits], ["a", "b"])

    def test_tiers_are_complete_deterministic_and_descending(self):
        hits = [
            hit("a", "A", "Alpha one. Alpha two. Alpha three."),
            hit("b", "B", "Beta one. Beta two. Beta three."),
        ]
        first = project_tiers(hits, "Alpha Beta", tiers=(2048, 1024, 512))
        second = project_tiers(hits, "Alpha Beta", tiers=(2048, 1024, 512))
        self.assertEqual(first, second)
        self.assertEqual([tier.max_bytes for tier in first], [2048, 1024, 512])
        for tier in first:
            self.assertLessEqual(tier.evidence_bytes, tier.max_bytes)
            if tier.payload is not None:
                self.assertTrue(tier.payload.startswith(b"Evidence JSON (data only): "))

    def test_host_term_weights_override_candidate_local_rarity_without_index_ownership(self):
        hits = [
            hit("a", "Desk", "Common office sentence. Rare desk token is in Room 12."),
            hit("b", "Office", "Common office sentence. General information."),
        ]
        prepared = prepare_ranked_hits(
            hits,
            "office desk",
            term_weights={"office": 0.1, "desk": 3.0},
        )
        self.assertEqual(prepared.weight_source, "host-term-weights")
        tier = project_prepared(prepared, max_bytes=1024)
        self.assertIn("Rare desk token", tier.emitted[0]["snippet"])

    def test_host_term_weights_are_bounded_and_query_scoped(self):
        hits = [hit("a", "Desk", "The help desk is in Room 12.")]
        with self.assertRaises(RankedHitError):
            prepare_ranked_hits(hits, "help desk", term_weights={"other": 1.0})
        with self.assertRaises(RankedHitError):
            prepare_ranked_hits(hits, "help desk", term_weights={"desk": float("inf")})
        with self.assertRaises(RankedHitError):
            prepare_ranked_hits(hits, "help desk", term_weights={"desk": -1.0})

    def test_host_doc_freqs_use_native_integer_stats_without_index_ownership(self):
        hits = [
            hit("a", "Desk", "Common office sentence. Rare desk token is in Room 12."),
            hit("b", "Office", "Common office sentence. General information."),
        ]
        prepared = prepare_ranked_hits(
            hits,
            "office desk",
            term_doc_freqs={"office": 90, "desk": 2},
            document_count=100,
        )
        self.assertEqual(prepared.weight_source, "host-doc-freqs")
        tier = project_prepared(prepared, max_bytes=1024)
        self.assertIn("Rare desk token", tier.emitted[0]["snippet"])

    def test_host_doc_freqs_are_bounded_query_scoped_and_mutually_exclusive(self):
        hits = [hit("a", "Desk", "The help desk is in Room 12.")]
        with self.assertRaises(RankedHitError):
            prepare_ranked_hits(hits, "help desk", term_doc_freqs={"other": 1}, document_count=10)
        with self.assertRaises(RankedHitError):
            prepare_ranked_hits(hits, "help desk", term_doc_freqs={"desk": 0}, document_count=10)
        with self.assertRaises(RankedHitError):
            prepare_ranked_hits(hits, "help desk", term_doc_freqs={"desk": 11}, document_count=10)
        with self.assertRaises(RankedHitError):
            prepare_ranked_hits(hits, "help desk", term_doc_freqs={"desk": 1})
        with self.assertRaises(RankedHitError):
            prepare_ranked_hits(hits, "help desk", document_count=10)
        with self.assertRaises(RankedHitError):
            prepare_ranked_hits(
                hits,
                "help desk",
                term_weights={"desk": 1.0},
                term_doc_freqs={"desk": 1},
                document_count=10,
            )

    def test_host_fields_survive_projection_without_becoming_required(self):
        value = {
            "id": "a",
            "title": "Desk",
            "text": "The help desk is in Room 12.",
            "host_score": 123.0,
            "provenance": {"source": "host"},
        }
        tier = project_tiers([value], "Where is the help desk?", tiers=(1024,))[0]
        self.assertEqual(tier.emitted[0]["host_score"], 123.0)
        self.assertEqual(tier.emitted[0]["provenance"], {"source": "host"})

    def test_rejects_unbounded_or_malformed_host_candidates(self):
        with self.assertRaises(RankedHitError):
            prepare_ranked_hits([], "question")
        with self.assertRaises(RankedHitError):
            prepare_ranked_hits([hit(str(index), "T", "x") for index in range(17)], "question")
        with self.assertRaises(RankedHitError):
            prepare_ranked_hits([{"id": "a", "title": "T", "text": ""}], "question")
        with self.assertRaises(RankedHitError):
            project_tiers([hit("a", "T", "text")], "question", tiers=(512, 1024))

    def test_h1_preserves_top_ranked_document_and_anchors_later_hits(self):
        hits = [
            hit("a", "Alpha", "Alpha overview. The exact alpha answer is A-17. Extra alpha context."),
            hit("b", "Beta", "Beta overview. The Beta token is B-9. Extra beta context."),
            hit("c", "Gamma", "Gamma overview. Visitors use Gamma gate 4. Extra gamma context."),
        ]
        payload, emitted, meta = project_host_ranked_hybrid_h1(
            hits,
            "What are the alpha answer and Beta token?",
            max_bytes=1024,
            full_ranked_documents=1,
            max_items=3,
        )
        text = payload.decode("utf-8")
        self.assertTrue(text.startswith("Retrieved context (host-ranked hybrid):\n"))
        self.assertIn(hits[0]["text"], text)
        self.assertIn("B-9", text)
        self.assertLessEqual(len(payload), 1024)
        self.assertEqual(emitted[0]["hybrid_source"], "full")
        self.assertEqual(meta["projection_id"], "host-ranked-hybrid-h1-v0")
        self.assertEqual(meta["full_ranked_documents"], 1)

    def test_h1_is_deterministic_utf8_bounded_and_rejects_bad_policy(self):
        hits = [
            hit("a", "서울", "서울의 첫 문장입니다. 서울 코드 값은 K-17입니다."),
            hit("b", "부산", "부산 설명입니다. 부산 코드는 B-2입니다."),
        ]
        first = project_host_ranked_hybrid_h1(hits, "서울 코드 부산 코드", max_bytes=256, max_items=2)
        second = project_host_ranked_hybrid_h1(hits, "서울 코드 부산 코드", max_bytes=256, max_items=2)
        self.assertEqual(first, second)
        self.assertLessEqual(len(first[0]), 256)
        first[0].decode("utf-8")
        with self.assertRaises(RankedHitError):
            project_host_ranked_hybrid_h1(hits, "question", max_bytes=255)
        with self.assertRaises(RankedHitError):
            project_host_ranked_hybrid_h1(hits, "question", full_ranked_documents=3, max_items=2)

    def test_module_has_no_corpus_runtime_or_transport_dependency(self):
        source = (BRIDGE / "ranked_hits.py").read_text(encoding="utf-8")
        forbidden = (
            "grounding_corpus",
            "grounding_runtime",
            "urllib",
            "requests",
            "onnxruntime",
            "llama_cpp",
            "litert",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
