"""The validated result returned by TrustLens' text fact-check workflow."""

from dataclasses import dataclass
from enum import Enum

from app.evidence import EvidenceSource


class Verdict(str, Enum):
    """The only verdict labels this milestone is allowed to show."""

    TRUE = "True"
    FALSE = "False"
    MISLEADING = "Misleading"
    SATIRE = "Satire"
    UNVERIFIED = "Unverified"


@dataclass(frozen=True)
class FactCheckResult:
    """A verdict plus the trusted sources selected to support it."""

    verdict: Verdict
    confidence: int
    explanation: str
    sources: tuple[EvidenceSource, ...]

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 100:
            raise ValueError("Confidence must be between 0 and 100.")
        if not self.explanation.strip():
            raise ValueError("A fact-check result needs an explanation.")

    def format_for_telegram(self) -> str:
        """Render a small, shareable text card without trusting model-made URLs."""
        lines = [
            f"Verdict: {self.verdict.value}",
            f"Confidence: {self.confidence}%",
            "",
            self.explanation.strip(),
        ]
        if self.sources:
            lines.extend(["", "Sources:"])
            lines.extend(f"{index}. {source.url}" for index, source in enumerate(self.sources, start=1))
        return "\n".join(lines)
