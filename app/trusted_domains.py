"""Load and enforce TrustLens' reviewed trusted-source registry."""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import AbstractSet
from urllib.parse import urlsplit

OFFICIAL_NEWS_CATEGORIES = frozenset(
    {
        "government",
        "singapore_news",
        "international_news",
        "fact_checking",
    }
)


def normalise_hostname(hostname: str) -> str:
    """Return a lowercase ASCII hostname without its harmless trailing dot."""
    hostname = hostname.strip().rstrip(".").lower()
    if not hostname or "." not in hostname:
        raise ValueError("A trusted domain must contain a dot.")
    return hostname.encode("idna").decode("ascii")


@dataclass(frozen=True)
class TrustedSource:
    """One reviewed source entry from the editable TOML registry."""

    id: str
    name: str
    domain: str
    include_subdomains: bool
    category: str
    tier: int
    notes: str

    def matches_hostname(self, hostname: str) -> bool:
        """Match exactly, or match a genuine subdomain when that was approved."""
        return hostname == self.domain or (
            self.include_subdomains and hostname.endswith(f".{self.domain}")
        )


@dataclass(frozen=True)
class TrustedDomainPolicy:
    """A strict URL policy built from the reviewed source registry."""

    sources: tuple[TrustedSource, ...]

    @property
    def domains(self) -> tuple[str, ...]:
        """Return the search-provider domain filters in registry order."""
        return tuple(dict.fromkeys(source.domain for source in self.sources))

    def domains_for_categories(self, categories: AbstractSet[str]) -> tuple[str, ...]:
        """Return unique domains whose registry category is in ``categories``."""
        return tuple(
            dict.fromkeys(
                source.domain for source in self.sources if source.category in categories
            )
        )

    def matching_sources_for_claim_terms(self, terms: AbstractSet[str]) -> tuple[TrustedSource, ...]:
        """Return primary-event sources whose registry id overlaps claim terms."""
        if not terms:
            return ()
        matches: list[TrustedSource] = []
        for source in self.sources:
            if source.category != "primary_event_source":
                continue
            source_terms = {
                part for part in source.id.replace("-", " ").split() if part != "official"
            }
            if source_terms & terms:
                matches.append(source)
        return tuple(matches)

    def is_official_news_url(self, url: str) -> bool:
        """Accept only government, newsroom, and fact-checking registry entries."""
        hostname = self.hostname_from_url(url)
        if hostname is None:
            return False
        return any(
            source.matches_hostname(hostname) and source.category in OFFICIAL_NEWS_CATEGORIES
            for source in self.sources
        )

    @classmethod
    def from_toml(cls, path: Path) -> "TrustedDomainPolicy":
        """Load source metadata from TOML without putting policy in application code."""
        with path.open("rb") as source_file:
            document = tomllib.load(source_file)
        entries = document.get("sources")
        if not isinstance(entries, list) or not entries:
            raise ValueError("The trusted-source registry must contain at least one [[sources]] entry.")

        sources = []
        source_ids = set()
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("Every trusted-source entry must be a TOML table.")
            try:
                source = TrustedSource(
                    id=str(entry["id"]).strip(),
                    name=str(entry["name"]).strip(),
                    domain=normalise_hostname(str(entry["domain"])),
                    include_subdomains=entry["include_subdomains"],
                    category=str(entry["category"]).strip(),
                    tier=entry["tier"],
                    notes=str(entry["notes"]).strip(),
                )
            except KeyError as error:
                raise ValueError(f"Trusted-source entry is missing {error.args[0]!r}.") from error

            if (
                not source.id
                or not source.name
                or not source.category
                or not source.notes
                or not isinstance(source.include_subdomains, bool)
                or isinstance(source.tier, bool)
                or not isinstance(source.tier, int)
                or not 1 <= source.tier <= 3
            ):
                raise ValueError(f"Trusted-source entry {source.id!r} has invalid metadata.")
            if source.id in source_ids:
                raise ValueError(f"Trusted-source ID {source.id!r} is duplicated.")
            sources.append(source)
            source_ids.add(source.id)

        return cls(tuple(sources))

    def hostname_from_url(self, url: str) -> str | None:
        """Extract a safe hostname from an HTTP(S) URL, or return None."""
        try:
            parsed = urlsplit(url)
            if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
                return None
            return normalise_hostname(parsed.hostname)
        except (UnicodeError, ValueError):
            return None

    def is_trusted_url(self, url: str) -> bool:
        """Accept only a configured source domain or its approved subdomains."""
        hostname = self.hostname_from_url(url)
        return hostname is not None and any(
            source.matches_hostname(hostname) for source in self.sources
        )
