"""Search trusted sources, then validate every result again before using it."""

from typing import Any, Protocol

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
            if not url or not snippet or url in seen_urls or not self.policy.is_trusted_url(url):
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
            seen_urls.add(url)
        return accepted


def create_tavily_search(api_key: str, policy: TrustedDomainPolicy) -> TrustedWebSearch:
    """Build the real search service without importing Tavily during unit tests."""
    from tavily import TavilyClient

    return TrustedWebSearch(policy=policy, client=TavilyClient(api_key=api_key))
