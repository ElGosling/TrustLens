"""Search trusted sources, then validate every result again before using it."""

from typing import Any, Protocol
from urllib.parse import urlsplit, urlunsplit
import re
import unicodedata

from app.evidence import EvidenceSource
from app.trusted_domains import TrustedDomainPolicy


class SearchClient(Protocol):
    """The small portion of a web-search client that this application needs."""

    def search(self, query: str, **kwargs: Any) -> dict[str, Any]: ...


class TrustedWebSearch:
    """A defense-in-depth search boundary for fact-check evidence."""

    def __init__(
        self,
        policy: TrustedDomainPolicy,
        client: SearchClient,
        max_results: int = 5,
    ) -> None:
        self.policy = policy
        self.client = client
        self.max_results = max_results

    def search(self, claim: str) -> list[EvidenceSource]:
        """Return only useful snippets whose returned URLs pass the local policy."""
        response = self.client.search(
            query=claim,
            include_domains=list(self.policy.domains),
            max_results=self.max_results,
            search_depth="basic",
            include_raw_content=False,
        )

        accepted: list[EvidenceSource] = []
        seen_urls: set[str] = set()
        for result in response.get("results", []):
            url = str(result.get("url", "")).strip()
            snippet = str(result.get("content", result.get("snippet", ""))).strip()
            canonical_url = self._canonical_url(url)
            if (
                not url
                or not snippet
                or canonical_url in seen_urls
                or not self.policy.is_trusted_url(url)
                or not self._is_relevant(claim, str(result.get("title", "")), snippet)
            ):
                continue

            hostname = self.policy.hostname_from_url(url)
            if hostname is None:  # Kept for type safety; is_trusted_url already checked it.
                continue
            accepted.append(
                EvidenceSource(
                    title=str(result.get("title", url)).strip() or url,
                    url=url,
                    domain=hostname,
                    snippet=snippet,
                )
            )
            seen_urls.add(canonical_url)
        return accepted

    @staticmethod
    def _canonical_url(url: str) -> str:
        """Make tracking-query variants of the same result count only once."""
        parsed = urlsplit(url)
        return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, "", ""))

    @staticmethod
    def _is_relevant(claim: str, title: str, snippet: str) -> bool:
        """Reject topical neighbours that do not contain enough claim-specific terms."""
        claim_terms = TrustedWebSearch._claim_terms(claim)
        if not claim_terms:
            return True
        result_terms = set(TrustedWebSearch._words(f"{title} {snippet}"))
        required_matches = 1 if len(claim_terms) == 1 else 2
        return len(claim_terms & result_terms) >= required_matches

    @staticmethod
    def _claim_terms(text: str) -> set[str]:
        generic_terms = {
            "a", "an", "and", "are", "be", "by", "can", "claim", "coming", "did",
            "do", "does", "event", "for", "from", "has", "have", "host", "hosting", "in",
            "is", "it", "next", "of", "on", "the", "this", "to", "tournament", "was", "were",
            "what", "when", "where", "will", "with", "would",
            "championship", "championships",
        }
        return {word for word in TrustedWebSearch._words(text) if word not in generic_terms}

    @staticmethod
    def _words(text: str) -> list[str]:
        normalised = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
        return re.findall(r"[a-z0-9]+", normalised.lower())


def create_tavily_search(api_key: str, policy: TrustedDomainPolicy) -> TrustedWebSearch:
    """Build the real search service without importing Tavily during unit tests."""
    from tavily import TavilyClient

    return TrustedWebSearch(policy=policy, client=TavilyClient(api_key=api_key))
