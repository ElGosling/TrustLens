"""Fetch readable article content from a specific URL."""

from typing import Any, Protocol
from urllib.parse import urlsplit

from app.fetch_debug import (
    log_straits_times_http_probe,
    log_tavily_extract_exception,
    log_tavily_extract_result,
)
from app.trusted_domains import TrustedDomainPolicy


class FetchedArticle:
    """Article text extracted from one URL."""

    __slots__ = ("url", "title", "body", "domain")

    def __init__(self, url: str, title: str, body: str, domain: str) -> None:
        self.url = url
        self.title = title
        self.body = body
        self.domain = domain


class ArticleFetcher(Protocol):
    """Fetch one page so TrustLens can read a forwarded link directly."""

    def fetch(self, url: str) -> FetchedArticle | None: ...


class TavilyArticleFetcher:
    """Use Tavily extract to read a specific article URL."""

    def __init__(self, client: Any, policy: TrustedDomainPolicy, max_body_chars: int = 4000) -> None:
        self.client = client
        self.policy = policy
        self.max_body_chars = max_body_chars

    def fetch(self, url: str) -> FetchedArticle | None:
        """Return article text when Tavily can extract the page."""
        log_straits_times_http_probe(url)

        try:
            response = self.client.extract(
                urls=[url],
                extract_depth="advanced",
                format="text",
            )
        except Exception as error:
            log_tavily_extract_exception(url, error)
            raise

        log_tavily_extract_result(url, response)

        for result in response.get("results", []):
            result_url = str(result.get("url", "")).strip()
            if result_url != url and not _same_canonical_path(result_url, url):
                continue
            body = str(
                result.get("raw_content", result.get("content", result.get("text", "")))
            ).strip()
            if not body:
                continue
            hostname = self.policy.hostname_from_url(url)
            if hostname is None:
                return None
            title = str(result.get("title", "")).strip() or _title_from_body(body, url)
            return FetchedArticle(
                url=url,
                title=title,
                body=body[: self.max_body_chars],
                domain=hostname,
            )
        return None


def _same_canonical_path(result_url: str, requested_url: str) -> bool:
    left = urlsplit(result_url)
    right = urlsplit(requested_url)
    return left.netloc.lower() == right.netloc.lower() and left.path.rstrip("/") == right.path.rstrip("/")


def _title_from_body(body: str, url: str) -> str:
    first_line = body.splitlines()[0].strip() if body else ""
    return first_line[:200] if first_line else url


def create_tavily_article_fetcher(api_key: str, policy: TrustedDomainPolicy) -> TavilyArticleFetcher:
    """Build the production article fetcher without importing Tavily in unit tests."""
    from tavily import TavilyClient

    return TavilyArticleFetcher(client=TavilyClient(api_key=api_key), policy=policy)
