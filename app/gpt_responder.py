"""The boundary between TrustLens and OpenAI's evidence-based verdict call."""

import json
from typing import Any, Sequence

from app.evidence import EvidenceSource
from app.verdict import FactCheckResult, Verdict

SYSTEM_INSTRUCTIONS = """You are TrustLens, an evidence-based fact-checking assistant.
Use only the evidence records supplied in the user input. Do not use background
knowledge, do not browse, and do not invent sources or URLs. If the supplied
evidence is missing, insufficient, or conflicting, choose Unverified. Choose
True or False only when the evidence directly supports that conclusion. Return
exactly two plain-language sentences in the explanation. Confidence is an
integer from 0 to 100 representing confidence based on this evidence only."""


class GPTResponder:
    """Ask GPT to turn approved evidence into one structured fact-check result."""

    def __init__(self, model: str, client: Any | None = None) -> None:
        self.model = model
        self.client = client or self._create_client()

    @staticmethod
    def _create_client() -> Any:
        """Import the SDK only when the real bot is starting."""
        from openai import OpenAI

        return OpenAI()

    def check_claim(
        self, claim: str, evidence: Sequence[EvidenceSource]
    ) -> FactCheckResult:
        """Request JSON, then map model-selected source IDs to safe source objects."""
        response = self.client.responses.create(
            model=self.model,
            instructions=SYSTEM_INSTRUCTIONS,
            input=json.dumps(
                {
                    "claim": claim,
                    "evidence": [
                        {
                            "source_id": index,
                            "title": source.title,
                            "url": source.url,
                            "snippet": source.snippet,
                        }
                        for index, source in enumerate(evidence, start=1)
                    ],
                }
            ),
            text={"format": self._response_format(len(evidence))},
            max_output_tokens=400,
            store=False,
        )
        return self._parse_result(response.output_text, evidence)

    @staticmethod
    def _response_format(source_count: int) -> dict[str, Any]:
        """Describe the small JSON contract expected from the model."""
        return {
            "type": "json_schema",
            "name": "fact_check_result",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "verdict": {"type": "string", "enum": [item.value for item in Verdict]},
                    "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                    "explanation": {"type": "string"},
                    "source_ids": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 1, "maximum": source_count},
                    },
                },
                "required": ["verdict", "confidence", "explanation", "source_ids"],
                "additionalProperties": False,
            },
        }

    @staticmethod
    def _parse_result(raw_result: str, evidence: Sequence[EvidenceSource]) -> FactCheckResult:
        """Validate untrusted model output before it is shown to a Telegram user."""
        try:
            result = json.loads(raw_result)
            verdict = Verdict(result["verdict"])
            confidence = result["confidence"]
            explanation = str(result["explanation"]).strip()
            source_ids = result["source_ids"]
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise ValueError("GPT returned an invalid fact-check result.") from error

        if isinstance(confidence, bool) or not isinstance(confidence, int):
            raise ValueError("GPT returned a non-integer confidence score.")
        if not isinstance(source_ids, list) or len(set(source_ids)) != len(source_ids):
            raise ValueError("GPT returned invalid source IDs.")

        selected_sources = []
        for source_id in source_ids:
            if not isinstance(source_id, int) or not 1 <= source_id <= len(evidence):
                raise ValueError("GPT selected a source outside the supplied evidence.")
            selected_sources.append(evidence[source_id - 1])

        if verdict is not Verdict.UNVERIFIED and not selected_sources:
            raise ValueError("A verified verdict must cite supplied evidence.")

        return FactCheckResult(
            verdict=verdict,
            confidence=confidence,
            explanation=explanation,
            sources=tuple(selected_sources),
        )
