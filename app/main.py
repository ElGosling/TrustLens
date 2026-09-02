"""Run TrustLens' Telegram text fact-checking milestone."""

from pathlib import Path

from app.fact_check import FactCheckService
from app.gpt_responder import GPTResponder
from app.settings import Settings
from app.telegram_bot import create_bot
from app.trusted_domains import TrustedDomainPolicy
from app.web_search import create_tavily_search


def run() -> None:
    """Load configuration, build the fact-check workflow, and start polling."""
    settings = Settings.from_environment()
    source_file = Path(__file__).resolve().parents[1] / "config" / "trusted_sources.toml"
    policy = TrustedDomainPolicy.from_toml(source_file)
    searcher = create_tavily_search(api_key=settings.tavily_api_key, policy=policy)
    generator = GPTResponder(model=settings.openai_model)
    fact_checker = FactCheckService(searcher=searcher, generator=generator)
    bot = create_bot(token=settings.telegram_bot_token, responder=fact_checker)

    print("TrustLens bot is running. Send it a text claim in Telegram.")
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    run()
