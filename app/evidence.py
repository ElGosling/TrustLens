"""Evidence objects that may safely be passed to the fact-checking agent later."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceSource:
    """A search result that passed TrustLens' local trusted-domain validation."""

    title: str
    url: str
    domain: str
    snippet: str
