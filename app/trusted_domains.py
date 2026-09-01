"""The single, strict policy that decides which web sources TrustLens may use."""

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


def normalise_hostname(hostname: str) -> str:
    """Return a lowercase ASCII hostname without its harmless trailing dot."""
    hostname = hostname.strip().rstrip(".").lower()
    if not hostname or "." not in hostname:
        raise ValueError("A trusted domain must contain a dot.")
    return hostname.encode("idna").decode("ascii")


@dataclass(frozen=True)
class TrustedDomainPolicy:
    """A central allowlist with exact-domain and subdomain matching only."""

    domains: tuple[str, ...]

    @classmethod
    def from_file(cls, path: Path) -> "TrustedDomainPolicy":
        """Read a one-domain-per-line allowlist, ignoring blank lines and comments."""
        domains = []
        for line in path.read_text(encoding="utf-8").splitlines():
            value = line.split("#", maxsplit=1)[0].strip()
            if value:
                domains.append(normalise_hostname(value))
        if not domains:
            raise ValueError("The trusted-domain list cannot be empty.")
        return cls(tuple(dict.fromkeys(domains)))

    def hostname_from_url(self, url: str) -> str | None:
        """Extract a safe hostname from an HTTP(S) URL, or return None."""
        try:
            parsed = urlsplit(url)
            if parsed.scheme.lower() not in {"http", "https"}:
                return None
            if not parsed.hostname:
                return None
            return normalise_hostname(parsed.hostname)
        except (UnicodeError, ValueError):
            return None

    def is_trusted_url(self, url: str) -> bool:
        """Accept only an allowlisted domain or a real subdomain of one.

        The dot before the configured domain is important. It accepts
        ``news.bbc.com`` for ``bbc.com`` but rejects both ``fake-bbc.com`` and
        ``bbc.com.scam.net``.
        """
        hostname = self.hostname_from_url(url)
        if hostname is None:
            return False
        return any(hostname == domain or hostname.endswith(f".{domain}") for domain in self.domains)
