"""Build search queries from a user claim before calling Tavily."""

from app.claim_terms import claim_terms, words
from app.trusted_domains import TrustedDomainPolicy

# Extra queries keyed by a distinctive claim term. Keep short and source-aligned.
ENTITY_SEARCH_QUERIES: dict[str, tuple[str, ...]] = {
    "pokemon": (
        "Pokemon World Championships Singapore 2027",
        "Pokemon championship Singapore",
    ),
}


def build_search_queries(
    claim: str, policy: TrustedDomainPolicy | None = None
) -> tuple[str, ...]:
    """Return deduplicated queries, starting with the claim then expansions."""
    queries: list[str] = []
    stripped = claim.strip()
    if stripped:
        queries.append(stripped)

    terms = claim_terms(claim)
    for keyword, expansions in ENTITY_SEARCH_QUERIES.items():
        if keyword in terms:
            queries.extend(expansions)

    if policy is not None:
        queries.extend(_registry_expansions(claim, terms, policy))

    if "singapore" in terms:
        other_terms = sorted(term for term in terms if term != "singapore")
        if other_terms:
            queries.append(f"Singapore {' '.join(other_terms)}")

    return tuple(dict.fromkeys(query.strip() for query in queries if query.strip()))


def _registry_expansions(
    claim: str, terms: set[str], policy: TrustedDomainPolicy
) -> list[str]:
    """Add short queries when the claim overlaps a reviewed primary-event source."""
    expansions: list[str] = []
    for source in policy.sources:
        if source.category != "primary_event_source":
            continue
        source_terms = set(words(source.id.replace("-", " ")))
        source_terms.discard("official")
        if not source_terms or not source_terms & terms:
            continue
        expansions.append(f"{source.name} Singapore")
        expansions.append(f"{source.name} {claim.strip()}")
    return expansions
