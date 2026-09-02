"""Temporary HTTP diagnostics for article fetch failures. Remove after debugging."""

from __future__ import annotations

import urllib.error
import urllib.request


DEBUG_PREFIX = "[trustlens-fetch-debug]"


def is_straits_times_url(url: str) -> bool:
    """Return True when the URL points at The Straits Times."""
    return "straitstimes.com" in url.lower()


def log_straits_times_http_probe(url: str) -> None:
    """Log status code, body preview, and errors from a direct GET (diagnostic only)."""
    if not is_straits_times_url(url):
        return

    print(f"{DEBUG_PREFIX} Probing URL: {url}")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-SG,en;q=0.9",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status = response.status
            raw_bytes = response.read(4096)
            body_preview = raw_bytes.decode("utf-8", errors="replace")[:500]
            print(f"{DEBUG_PREFIX} HTTP status code: {status}")
            print(f"{DEBUG_PREFIX} Raw response body (first 500 chars):\n{body_preview}")
    except urllib.error.HTTPError as error:
        raw_bytes = error.read(4096) if error.fp else b""
        body_preview = raw_bytes.decode("utf-8", errors="replace")[:500]
        print(f"{DEBUG_PREFIX} HTTP status code: {error.code}")
        print(f"{DEBUG_PREFIX} Raw response body (first 500 chars):\n{body_preview}")
    except Exception as error:
        print(f"{DEBUG_PREFIX} Exception during fetch: {type(error).__name__}: {error}")


def log_tavily_extract_result(url: str, response: dict) -> None:
    """Log Tavily extract metadata without changing verification behaviour."""
    if not is_straits_times_url(url):
        return

    results = response.get("results", [])
    failed = response.get("failed_results", [])
    print(f"{DEBUG_PREFIX} Tavily extract results: {len(results)}")
    print(f"{DEBUG_PREFIX} Tavily extract failed_results: {failed}")
    if results:
        first = results[0]
        preview = str(
            first.get("raw_content", first.get("content", first.get("text", "")))
        )[:500]
        print(f"{DEBUG_PREFIX} Tavily first result title: {first.get('title', '')!r}")
        print(f"{DEBUG_PREFIX} Tavily first result body (first 500 chars):\n{preview}")


def log_tavily_extract_exception(url: str, error: BaseException) -> None:
    """Log Tavily failures for Straits Times URLs."""
    if not is_straits_times_url(url):
        return
    print(f"{DEBUG_PREFIX} Tavily extract exception: {type(error).__name__}: {error}")
