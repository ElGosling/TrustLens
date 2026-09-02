"""Shared claim tokenisation for search queries and relevance checks."""

import re
import unicodedata

GENERIC_CLAIM_TERMS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "be",
        "by",
        "can",
        "claim",
        "coming",
        "did",
        "do",
        "does",
        "event",
        "for",
        "from",
        "has",
        "have",
        "host",
        "hosting",
        "in",
        "is",
        "it",
        "next",
        "of",
        "on",
        "the",
        "this",
        "to",
        "tournament",
        "was",
        "were",
        "what",
        "when",
        "where",
        "will",
        "with",
        "would",
        "championship",
        "championships",
    }
)


def words(text: str) -> list[str]:
    """Return lowercase ASCII word tokens from free text."""
    normalised = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.findall(r"[a-z0-9]+", normalised.lower())


def claim_terms(text: str) -> set[str]:
    """Return claim-specific terms with generic hosting/event words removed."""
    return {word for word in words(text) if word not in GENERIC_CLAIM_TERMS}
