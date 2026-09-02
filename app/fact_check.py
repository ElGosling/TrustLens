"""Coordinate trusted searching and evidence-based verdict generation."""

from typing import Protocol, Sequence

from app.evidence import EvidenceSource
from app.response_formatter import format_fact_check_for_telegram
from app.verdict import FactCheckResult, Verdict


class EvidenceSearcher(Protocol):
    """The single operation the workflow needs from a search service."""

    def search(self, claim: str) -> list[EvidenceSource]: ...


class EvidenceVerdictGenerator(Protocol):
    """Generate one result using the claim and evidence selected by our code."""

    def check_claim(
        self, claim: str, evidence: Sequence[EvidenceSource]
    ) -> FactCheckResult: ...


class FactCheckService:
    """Turn one text claim into a Telegram-ready, evidence-backed reply."""

    def __init__(self, searcher: EvidenceSearcher, generator: EvidenceVerdictGenerator) -> None:
        self.searcher = searcher
        self.generator = generator

    def answer(self, claim: str) -> str:
        """Keep Telegram's existing responder interface while doing a fact check."""
        return format_fact_check_for_telegram(self.check(claim))

    def check(self, claim: str) -> FactCheckResult:
        """Search first; never ask GPT for a sourced verdict with no evidence."""
        evidence = self.searcher.search(claim)
        if not evidence:
            return FactCheckResult(
                verdict=Verdict.UNVERIFIED,
                confidence=0,
                explanation=(
                    "I could not find relevant information on the approved sources. "
                    "This does not prove the claim false; it means TrustLens cannot verify it yet."
                ),
                sources=(),
            )
        return self.generator.check_claim(claim, evidence)
