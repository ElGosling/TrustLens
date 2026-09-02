"""Turn fetched pages into checkable claims and trusted evidence objects."""

from app.article_fetcher import FetchedArticle
from app.evidence import EvidenceSource


def article_to_evidence(article: FetchedArticle, max_snippet_chars: int = 2000) -> EvidenceSource:
    """Convert a fetched trusted article into evidence for the verdict step."""
    snippet = article.body.strip()
    if len(snippet) > max_snippet_chars:
        snippet = f"{snippet[:max_snippet_chars].rstrip()}..."
    return EvidenceSource(
        title=article.title,
        url=article.url,
        domain=article.domain,
        snippet=snippet,
    )


def derive_claim_from_trusted_article(article: FetchedArticle, user_note: str) -> str:
    """Build the claim GPT should assess when the user forwarded a trusted article."""
    if user_note:
        return f"{user_note} (shared article: {article.title})"
    lead = _first_paragraph(article.body)
    if lead:
        return f"Article headline: {article.title}. Main claim: {lead}"
    return f"Article headline: {article.title}"


def derive_claim_from_untrusted_page(article: FetchedArticle, user_note: str) -> str:
    """Extract a checkable claim from an untrusted page without treating it as evidence."""
    if user_note:
        return user_note
    lead = _first_paragraph(article.body)
    if lead:
        return f"Claim from shared link ({article.title}): {lead}"
    return f"Claim from shared link: {article.title}"


def _first_paragraph(body: str, max_chars: int = 500) -> str:
    paragraphs = [part.strip() for part in body.split("\n\n") if part.strip()]
    if not paragraphs:
        paragraphs = [line.strip() for line in body.splitlines() if line.strip()]
    if not paragraphs:
        return ""
    lead = paragraphs[0]
    if len(lead) > max_chars:
        lead = f"{lead[:max_chars].rstrip()}..."
    return lead
