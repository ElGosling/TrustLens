"""Build search queries and claims from a forwarded article URL."""

import re
from urllib.parse import unquote, urlsplit

from app.evidence import EvidenceSource


def build_url_search_queries(url: str, user_note: str = "") -> tuple[str, ...]:
    """Return queries aimed at finding the exact article in search indexes."""
    queries: list[str] = [url.strip()]
    parsed = urlsplit(url)
    hostname = parsed.netloc.lower().removeprefix("www.")

    slug_text = slug_to_readable_text(parsed.path)
    if slug_text:
        queries.append(slug_text)
        if hostname:
            queries.append(f"site:{hostname} {slug_text}")

    if user_note.strip():
        queries.append(user_note.strip())
        if hostname:
            queries.append(f"site:{hostname} {user_note.strip()}")

    return tuple(dict.fromkeys(query for query in queries if query))


def slug_to_readable_text(path: str) -> str:
    """Turn /singapore/budget-2026-cdc-vouchers into a short search phrase."""
    segments = [unquote(part) for part in path.split("/") if part.strip()]
    if not segments:
        return ""
    slug = segments[-1]
    slug = re.sub(r"\.(html?|php|aspx?)$", "", slug, flags=re.IGNORECASE)
    words = re.findall(r"[a-z0-9]+", slug.lower())
    if len(words) < 3:
        return ""
    return " ".join(words)


def derive_claim_from_url_search(
    url: str, user_note: str, evidence: list[EvidenceSource]
) -> str:
    """Build a GPT claim when only search snippets could be retrieved for a URL."""
    if user_note.strip():
        title = evidence[0].title if evidence else url
        return f"{user_note.strip()} (shared article: {title})"
    if evidence:
        lead = evidence[0].snippet.strip()
        if len(lead) > 400:
            lead = f"{lead[:400].rstrip()}..."
        return f"Article headline: {evidence[0].title}. Main claim: {lead}"
    slug = slug_to_readable_text(urlsplit(url).path)
    if slug:
        return f"Verify claims from this article: {slug}"
    return f"Verify claims from the shared article at {url}"
