"""The small boundary between TrustLens and the OpenAI API."""

from typing import Any

SYSTEM_INSTRUCTIONS = (
    "You are TrustLens, a helpful assistant. This is an early development "
    "milestone: reply clearly and briefly to the user's message. Do not claim "
    "that you have fact-checked anything yet."
)


class GPTResponder:
    """Turn one incoming text message into one GPT reply."""

    def __init__(self, model: str, client: Any | None = None) -> None:
        self.model = model
        self.client = client or self._create_client()

    @staticmethod
    def _create_client() -> Any:
        """Import the SDK only when the real bot is starting."""
        from openai import OpenAI

        return OpenAI()

    def answer(self, user_text: str) -> str:
        """Ask the Responses API for a short reply without storing it remotely."""
        response = self.client.responses.create(
            model=self.model,
            instructions=SYSTEM_INSTRUCTIONS,
            input=user_text,
            max_output_tokens=300,
            store=False,
        )
        reply = response.output_text.strip()
        return reply or "I couldn't generate a reply. Please try again."
