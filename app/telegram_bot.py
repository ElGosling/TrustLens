"""Telegram-specific code; keep it separate from GPT and future fact checking."""

from typing import Protocol


class TextResponder(Protocol):
    """Anything that can turn text into a reply for the Telegram adapter."""

    def answer(self, user_text: str) -> str: ...


def create_bot(token: str, responder: TextResponder):
    """Create a Telegram bot that accepts text and replies in the same chat."""
    import telebot

    bot = telebot.TeleBot(token)

    @bot.message_handler(content_types=["text"])
    def handle_text(message) -> None:
        try:
            reply = responder.answer(message.text)
        except Exception as error:
            print(f"Could not reply to Telegram message: {error}")
            bot.reply_to(message, "Sorry, TrustLens could not reply right now. Please try again.")
            return

        bot.reply_to(message, reply)

    return bot
