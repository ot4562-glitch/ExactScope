#!/usr/bin/env python3
"""Shared deterministic text primitives for ExactScope grounding projection/retrieval."""
from __future__ import annotations

import re
import unicodedata

TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


class CorpusError(RuntimeError):
    pass


def tokenize(text: str) -> list[str]:
    if not isinstance(text, str):
        raise CorpusError("corpus text must be a string")
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return TOKEN_RE.findall(normalized)


def sentence_spans(text: str) -> list[tuple[str, int, int]]:
    """Return baseline sentence text plus UTF-8 byte offset/length within source text."""
    if not isinstance(text, str):
        raise CorpusError("corpus text must be a string")
    pieces: list[tuple[int, int]] = []
    start = 0
    for match in SENTENCE_SPLIT_RE.finditer(text):
        pieces.append((start, match.start()))
        start = match.end()
    pieces.append((start, len(text)))
    spans: list[tuple[str, int, int]] = []
    for raw_start, raw_end in pieces:
        raw = text[raw_start:raw_end]
        if not raw.strip():
            continue
        left = len(raw) - len(raw.lstrip())
        right = len(raw.rstrip())
        clean_start = raw_start + left
        clean_end = raw_start + right
        sentence = text[clean_start:clean_end]
        byte_start = len(text[:clean_start].encode("utf-8"))
        spans.append((sentence, byte_start, len(sentence.encode("utf-8"))))
    return spans


def split_sentences(text: str) -> list[str]:
    return [sentence for sentence, _, _ in sentence_spans(text)]
