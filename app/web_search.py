"""Search trusted sources, then validate every result again before using it."""

from collections.abc import Callable
from typing import Any, Protocol
from urllib.parse import urlsplit, urlunsplit

from app.claim_terms import claim_terms, words
from app.evidence import EvidenceSource
from app.search_queries import build_search_queries
from app.trusted_domains import TrustedDomainPolicy
from app.url_search import build_url_search_queries

PRIMARY_EVENT_CATEGORY = frozenset({"primary_event_source"})


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
        min_results_before_fallback: int = 2,
    ) -> None:
        self.policy = policy
        self.client = client
        self.max_results = max_results
        self.min_results_before_fallback = min_results_before_fallback

    def search(self, claim: str) -> list[EvidenceSource]:
        """Search trusted domains first, then always cross-reference on the wider web."""
        queries = build_search_queries(claim, self.policy)
        return self._run_search_passes(queries, claim)

    def search_for_url(self, url: str, user_note: str = "") -> list[EvidenceSource]:
        """Find a specific forwarded article through search when direct fetch fails."""
        queries = build_url_search_queries(url, user_note)
        return self._run_search_passes(
            queries,
            claim=user_note or slug_claim_hint(url),
            target_url=url,
            restrict_first_pass_domain=self._domain_for_url(url),
        )

    def _run_search_passes(
        self,
        queries: tuple[str, ...],
        claim: str,
        target_url: str | None = None,
        restrict_first_pass_domain: str | None = None,
    ) -> list[EvidenceSource]:
        """Run event, trusted-domain, and web-wide passes, then merge results."""
        accepted: list[EvidenceSource] = []
        seen_urls: set[str] = set()

        event_domains = self.policy.domains_for_categories(PRIMARY_EVENT_CATEGORY)
        if self.policy.matching_sources_for_claim_terms(claim_terms(claim)):
            accepted = self._merge(
                accepted,
                seen_urls,
                self._collect_for_queries(
                    queries,
                    claim,
                    include_domains=event_domains,
                    search_depth="basic",
                    url_filter=self.policy.is_trusted_url,
                    target_url=target_url,
                ),
            )

        if restrict_first_pass_domain and len(accepted) < self.min_results_before_fallback:
            accepted = self._merge(
                accepted,
                seen_urls,
                self._collect_for_queries(
                    queries,
                    claim,
                    include_domains=(restrict_first_pass_domain,),
                    search_depth="advanced",
                    url_filter=self.policy.is_trusted_url,
                    target_url=target_url,
                ),
            )

        if len(accepted) < self.min_results_before_fallback:
            accepted = self._merge(
                accepted,
                seen_urls,
                self._collect_for_queries(
                    queries,
                    claim,
                    include_domains=self.policy.domains,
                    search_depth="basic",
                    url_filter=self.policy.is_trusted_url,
                    target_url=target_url,
                ),
            )

        accepted = self._merge(
            accepted,
            seen_urls,
            self._collect_for_queries(
                queries,
                claim,
                include_domains=None,
                search_depth="advanced",
                url_filter=self.policy.is_official_news_url,
                target_url=target_url,
            ),
        )

        return accepted[: self.max_results]

    def _domain_for_url(self, url: str) -> str | None:
        """Return the registry domain for a trusted URL, if any."""
        hostname = self.policy.hostname_from_url(url)
        if hostname is None:
            return None
        for source in self.policy.sources:
            if source.matches_hostname(hostname):
                return source.domain
        return None

    def _collect_for_queries(
        self,
        queries: tuple[str, ...],
        claim: str,
        include_domains: tuple[str, ...] | None,
        search_depth: str,
        url_filter: Callable[[str], bool],
        target_url: str | None = None,
    ) -> list[EvidenceSource]:
        """Run one or more Tavily queries and return validated evidence."""
        collected: list[EvidenceSource] = []
        seen: set[str] = set()
        for query in queries:
            if len(collected) >= self.max_results:
                break
            for item in self._search_once(
                query=query,
                claim=claim,
                include_domains=include_domains,
                search_depth=search_depth,
                url_filter=url_filter,
                max_results=self.max_results,
                target_url=target_url,
            ):
                canonical = self._canonical_url(item.url)
                if canonical in seen:
                    continue
                collected.append(item)
                seen.add(canonical)
        return collected

    def _search_once(
        self,
        query: str,
        claim: str,
        include_domains: tuple[str, ...] | None,
        search_depth: str,
        url_filter: Callable[[str], bool],
        max_results: int,
        target_url: str | None = None,
    ) -> list[EvidenceSource]:
        """Call Tavily once and apply local URL, relevance, and dedupe checks."""
        kwargs: dict[str, Any] = {
            "max_results": max_results,
            "search_depth": search_depth,
            "include_raw_content": False,
        }
        if include_domains is not None:
            kwargs["include_domains"] = list(include_domains)

        response = self.client.search(query=query, **kwargs)

        accepted: list[EvidenceSource] = []
        for result in response.get("results", []):
            url = str(result.get("url", "")).strip()
            snippet = str(result.get("content", result.get("snippet", ""))).strip()
            title = str(result.get("title", url)).strip() or url
            if not url or not snippet or not url_filter(url):
                continue
            if not self._matches_target_url(url, target_url) and not self._is_relevant(
                claim, title, snippet
            ):
                continue

            hostname = self.policy.hostname_from_url(url)
            if hostname is None:
                continue
            accepted.append(
                EvidenceSource(
                    title=title,
                    url=url,
                    domain=hostname,
                    snippet=snippet,
                )
            )
        return accepted

    def _matches_target_url(self, result_url: str, target_url: str | None) -> bool:
        """Accept exact article matches even when generic relevance rules would reject them."""
        if target_url is None:
            return False
        return self._canonical_url(result_url) == self._canonical_url(target_url)

    def _merge(
        self,
        existing: list[EvidenceSource],
        seen_urls: set[str],
        new_items: list[EvidenceSource],
    ) -> list[EvidenceSource]:
        """Append unique evidence while preserving order."""
        merged = list(existing)
        for item in new_items:
            canonical_url = self._canonical_url(item.url)
            if canonical_url in seen_urls:
                continue
            merged.append(item)
            seen_urls.add(canonical_url)
        return merged

    @staticmethod
    def _canonical_url(url: str) -> str:
        """Make tracking-query variants of the same result count only once."""
        parsed = urlsplit(url)
        return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, "", ""))

    @staticmethod
    def _is_relevant(claim: str, title: str, snippet: str) -> bool:
        """Reject topical neighbours that do not contain enough claim-specific terms."""
        terms = claim_terms(claim)
        if not terms:
            return True
        result_terms = set(words(f"{title} {snippet}"))
        required_matches = 1 if len(terms) == 1 else min(2, len(terms))
        return len(terms & result_terms) >= required_matches


def slug_claim_hint(url: str) -> str:
    """Use URL slug words as a weak claim hint for relevance checks."""
    from app.url_search import slug_to_readable_text

    return slug_to_readable_text(urlsplit(url).path) or url


def create_tavily_search(api_key: str, policy: TrustedDomainPolicy) -> TrustedWebSearch:
    """Build the real search service without importing Tavily during unit tests."""
    from tavily import TavilyClient

    return TrustedWebSearch(policy=policy, client=TavilyClient(api_key=api_key))
