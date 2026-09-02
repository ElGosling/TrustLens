"""Parse Telegram text into plain claims or forwarded URLs."""

import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlsplit

from app.trusted_domains import TrustedDomainPolicy

URL_PATTERN = re.compile(r"https?://[^\s<>\"'\]]+", re.IGNORECASE)
TRAILING_URL_PUNCTUATION = ".,);:!?"


class MessageKind(str, Enum):
    """How TrustLens should gather evidence for a user message."""

    TEXT_CLAIM = "text_claim"
    TRUSTED_URL = "trusted_url"
    UNTRUSTED_URL = "untrusted_url"


@dataclass(frozen=True)
class ParsedMessage:
    """A Telegram text message split into optional URLs and remaining text."""

    raw_text: str
    urls: tuple[str, ...]
    accompanying_text: str


@dataclass(frozen=True)
class RoutedMessage:
    """A parsed message with the evidence strategy TrustLens should use."""

    kind: MessageKind
    parsed: ParsedMessage
    primary_url: str | None


def parse_message(text: str) -> ParsedMessage:
    """Extract HTTP(S) URLs and any claim text the user typed alongside them."""
    raw_text = text.strip()
    urls = tuple(_clean_url(match.group(0)) for match in URL_PATTERN.finditer(raw_text))
    accompanying = raw_text
    for url in urls:
        accompanying = accompanying.replace(url, " ")
    accompanying = " ".join(accompanying.split()).strip()
    return ParsedMessage(raw_text=raw_text, urls=urls, accompanying_text=accompanying)


def route_message(text: str, policy: TrustedDomainPolicy) -> RoutedMessage:
    """Choose the evidence path without changing how plain text claims are handled."""
    parsed = parse_message(text)
    if not parsed.urls:
        return RoutedMessage(kind=MessageKind.TEXT_CLAIM, parsed=parsed, primary_url=None)

    trusted_urls = [url for url in parsed.urls if policy.is_trusted_url(url)]
    if trusted_urls:
        return RoutedMessage(
            kind=MessageKind.TRUSTED_URL,
            parsed=parsed,
            primary_url=trusted_urls[0],
        )

    return RoutedMessage(
        kind=MessageKind.UNTRUSTED_URL,
        parsed=parsed,
        primary_url=parsed.urls[0],
    )


def _clean_url(url: str) -> str:
    """Strip common trailing punctuation from URLs pasted into chat."""
    cleaned = url.rstrip(TRAILING_URL_PUNCTUATION)
    return cleaned if cleaned else url
