"""Run the Telegram-to-GPT TrustLens milestone."""

from app.gpt_responder import GPTResponder
from app.settings import Settings
from app.telegram_bot import create_bot


def run() -> None:
    """Load configuration, build the collaborators, then start Telegram polling."""
    settings = Settings.from_environment()
    responder = GPTResponder(model=settings.openai_model)
    bot = create_bot(token=settings.telegram_bot_token, responder=responder)

    print("TrustLens bot is running. Send it a text message in Telegram.")
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    run()
