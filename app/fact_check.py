"""Coordinate trusted searching and evidence-based verdict generation."""

from typing import Protocol, Sequence
from urllib.parse import urlsplit, urlunsplit

from app.article_fetcher import ArticleFetcher
from app.evidence import EvidenceSource
from app.message_input import MessageKind, parse_message, route_message
from app.response_formatter import format_fact_check_for_telegram
from app.trusted_domains import TrustedDomainPolicy
from app.url_claims import (
    article_to_evidence,
    derive_claim_from_trusted_article,
    derive_claim_from_untrusted_page,
)
from app.url_search import derive_claim_from_url_search
from app.verdict import FactCheckResult, Verdict


class EvidenceSearcher(Protocol):
    """The single operation the workflow needs from a search service."""

    def search(self, claim: str) -> list[EvidenceSource]: ...

    def search_for_url(self, url: str, user_note: str = "") -> list[EvidenceSource]: ...


class EvidenceVerdictGenerator(Protocol):
    """Generate one result using the claim and evidence selected by our code."""

    def check_claim(
        self, claim: str, evidence: Sequence[EvidenceSource]
    ) -> FactCheckResult: ...


class FactCheckService:
    """Turn one text claim into a Telegram-ready, evidence-backed reply."""

    def __init__(
        self,
        searcher: EvidenceSearcher,
        generator: EvidenceVerdictGenerator,
        policy: TrustedDomainPolicy | None = None,
        article_fetcher: ArticleFetcher | None = None,
    ) -> None:
        self.searcher = searcher
        self.generator = generator
        self.policy = policy
        self.article_fetcher = article_fetcher

    def answer(self, user_text: str) -> str:
        """Route forwarded URLs separately while keeping plain text on the existing path."""
        if not parse_message(user_text).urls:
            return format_fact_check_for_telegram(self.check(user_text))

        routed = route_message(user_text, self._require_policy())
        if routed.kind is MessageKind.TRUSTED_URL:
            return format_fact_check_for_telegram(self.check_trusted_url(routed))
        return format_fact_check_for_telegram(self.check_untrusted_url(routed))

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

    def check_trusted_url(self, routed) -> FactCheckResult:
        """Read a whitelisted article directly, then optionally cross-reference it."""
        fetcher = self._require_article_fetcher()
        primary_url = routed.primary_url
        if primary_url is None:
            return self._url_fetch_failed("No trusted URL was found in the message.")

        article = fetcher.fetch(primary_url)
        if article is None:
            return self._check_trusted_url_via_search(routed, primary_url)

        claim = derive_claim_from_trusted_article(article, routed.parsed.accompanying_text)
        primary_evidence = article_to_evidence(article)
        corroboration = self.searcher.search(claim)
        evidence = self._merge_evidence(primary_evidence, corroboration)
        if not evidence:
            return self._url_fetch_failed(
                "I read the article but could not prepare evidence from it. Please try again."
            )
        return self.generator.check_claim(claim, evidence)

    def check_untrusted_url(self, routed) -> FactCheckResult:
        """Use an untrusted page only to learn the claim, then verify on trusted sources."""
        fetcher = self._require_article_fetcher()
        primary_url = routed.primary_url
        if primary_url is None:
            return self._url_fetch_failed("No URL was found in the message.")

        article = fetcher.fetch(primary_url)
        if article is None and not routed.parsed.accompanying_text:
            return self._url_fetch_failed(
                "I could not read that link to extract a claim. "
                "Paste the claim as text, or share a link from an approved news source."
            )

        if article is None:
            return self.check(routed.parsed.accompanying_text)

        claim = derive_claim_from_untrusted_page(article, routed.parsed.accompanying_text)
        return self.check(claim)

    def _check_trusted_url_via_search(self, routed, primary_url: str) -> FactCheckResult:
        """When direct fetch fails, locate the article through trusted and web-wide search."""
        user_note = routed.parsed.accompanying_text
        evidence = self.searcher.search_for_url(primary_url, user_note)
        if not evidence:
            return self._url_fetch_failed(
                "I could not read or locate that trusted article link in approved sources. "
                "Try pasting the headline or claim as text instead."
            )
        claim = derive_claim_from_url_search(primary_url, user_note, evidence)
        return self.generator.check_claim(claim, evidence)

    def _merge_evidence(
        self, primary: EvidenceSource, additional: Sequence[EvidenceSource]
    ) -> list[EvidenceSource]:
        """Keep the forwarded article first and append non-duplicate corroboration."""
        merged = [primary]
        seen = {_canonical_url(primary.url)}
        for item in additional:
            canonical = _canonical_url(item.url)
            if canonical in seen:
                continue
            merged.append(item)
            seen.add(canonical)
        return merged

    def _url_fetch_failed(self, explanation: str) -> FactCheckResult:
        return FactCheckResult(
            verdict=Verdict.UNVERIFIED,
            confidence=0,
            explanation=explanation,
            sources=(),
        )

    def _require_policy(self) -> TrustedDomainPolicy:
        if self.policy is None and hasattr(self.searcher, "policy"):
            self.policy = self.searcher.policy
        if self.policy is None:
            raise ValueError(
                "FactCheckService needs a trusted-domain policy for URL messages. "
                "Pass policy=... from main.py or use a searcher that exposes .policy."
            )
        return self.policy

    def _require_article_fetcher(self) -> ArticleFetcher:
        if self.article_fetcher is None:
            raise ValueError("FactCheckService needs an article fetcher for URL messages.")
        return self.article_fetcher


def _canonical_url(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, "", ""))
