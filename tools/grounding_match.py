"""Deterministic query/alias matching for rc4 local grounding."""
import re

_WORDS = re.compile(r"[a-z0-9]+", re.ASCII)
_LOWER_ASCII = str.maketrans({chr(n): chr(n + 32) for n in range(ord("A"), ord("Z") + 1)})


def ascii_words(text: str) -> str:
    if not isinstance(text, str):
        raise ValueError("text required")
    return " ".join(_WORDS.findall(text.translate(_LOWER_ASCII)))


def frozen_alias(text: str) -> str:
    if not isinstance(text, str) or not text:
        raise ValueError("nonempty alias required")
    if any(not ch.isascii() for ch in text):
        return text
    result = ascii_words(text)
    if not result:
        raise ValueError("empty normalized alias")
    return result


def matches(question: str, alias: str, exact_ascii: bool = False) -> bool:
    normalized = frozen_alias(alias)
    if any(not ch.isascii() for ch in normalized):
        return normalized in question
    question_words = ascii_words(question).split()
    alias_words = normalized.split()
    if exact_ascii:
        return question_words == alias_words
    if len(alias_words) < 2:
        return False
    available = set(question_words)
    return all(word in available for word in alias_words)
