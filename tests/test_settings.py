import unittest

from app.settings import (
    DEFAULT_ESCALATE_MIN_UNIQUE_USERS,
    DEFAULT_ESCALATE_OUTPUT_DIR,
    DEFAULT_ESCALATE_WINDOW_DAYS,
    DEFAULT_OPENAI_MODEL,
    Settings,
)


class SettingsTests(unittest.TestCase):
    def test_settings_reads_required_values(self) -> None:
        settings = Settings.from_environment(
            {
                "TELEGRAM_BOT_TOKEN": "telegram-token",
                "OPENAI_API_KEY": "openai-key",
                "TAVILY_API_KEY": "tavily-key",
            }
        )

        self.assertEqual(settings.telegram_bot_token, "telegram-token")
        self.assertEqual(settings.openai_api_key, "openai-key")
        self.assertEqual(settings.tavily_api_key, "tavily-key")
        self.assertEqual(settings.openai_model, DEFAULT_OPENAI_MODEL)
        self.assertEqual(settings.escalate_window_days, DEFAULT_ESCALATE_WINDOW_DAYS)
        self.assertEqual(settings.escalate_min_unique_users, DEFAULT_ESCALATE_MIN_UNIQUE_USERS)
        self.assertEqual(settings.escalate_output_dir, DEFAULT_ESCALATE_OUTPUT_DIR)

    def test_settings_explains_which_values_are_missing(self) -> None:
        with self.assertRaisesRegex(ValueError, "TELEGRAM_BOT_TOKEN, OPENAI_API_KEY"):
            Settings.from_environment({})
