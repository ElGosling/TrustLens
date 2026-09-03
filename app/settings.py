"""Read the small amount of configuration needed by the first bot milestone."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

DEFAULT_OPENAI_MODEL = "gpt-5.6-luna"
DEFAULT_DATABASE_PATH = "data/trustlens.sqlite3"
DEFAULT_QUIZ_QUESTION_COUNT = 5
DEFAULT_ESCALATE_WINDOW_DAYS = 14
DEFAULT_ESCALATE_MIN_UNIQUE_USERS = 2
DEFAULT_ESCALATE_OUTPUT_DIR = "data/escalations"


def load_local_env_file(path: Path = Path(".env")) -> None:
    """Load simple KEY=value lines from .env without replacing shell variables.

    This deliberately supports only the format used in .env.example. A later
    project can adopt a dedicated configuration package if it needs more.
    """
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Settings:
    """Configuration values that must never be committed to source control."""

    telegram_bot_token: str
    openai_api_key: str
    tavily_api_key: str
    openai_model: str
    database_path: str = DEFAULT_DATABASE_PATH
    quiz_question_count: int = DEFAULT_QUIZ_QUESTION_COUNT
    escalate_window_days: int = DEFAULT_ESCALATE_WINDOW_DAYS
    escalate_min_unique_users: int = DEFAULT_ESCALATE_MIN_UNIQUE_USERS
    escalate_output_dir: str = DEFAULT_ESCALATE_OUTPUT_DIR

    @classmethod
    def from_environment(cls, values: Mapping[str, str] | None = None) -> "Settings":
        """Create settings from .env and environment variables, with clear errors."""
        if values is None:
            load_local_env_file()
            values = os.environ

        missing = [
            name
            for name in ("TELEGRAM_BOT_TOKEN", "OPENAI_API_KEY", "TAVILY_API_KEY")
            if not values.get(name, "").strip()
        ]
        if missing:
            names = ", ".join(missing)
            raise ValueError(f"Missing {names}. Copy .env.example to .env and fill it in.")

        return cls(
            telegram_bot_token=values["TELEGRAM_BOT_TOKEN"].strip(),
            openai_api_key=values["OPENAI_API_KEY"].strip(),
            tavily_api_key=values["TAVILY_API_KEY"].strip(),
            openai_model=values.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip()
            or DEFAULT_OPENAI_MODEL,
            database_path=values.get("TRUSTLENS_DB_PATH", "").strip()
            or DEFAULT_DATABASE_PATH,
            quiz_question_count=_read_question_count(values),
            escalate_window_days=_read_bounded_int(
                values,
                "TRUSTLENS_ESCALATE_WINDOW_DAYS",
                default=DEFAULT_ESCALATE_WINDOW_DAYS,
                minimum=1,
                maximum=365,
            ),
            escalate_min_unique_users=_read_bounded_int(
                values,
                "TRUSTLENS_ESCALATE_MIN_USERS",
                default=DEFAULT_ESCALATE_MIN_UNIQUE_USERS,
                minimum=1,
                maximum=100,
            ),
            escalate_output_dir=values.get("TRUSTLENS_ESCALATE_DIR", "").strip()
            or DEFAULT_ESCALATE_OUTPUT_DIR,
        )


def _read_question_count(values: Mapping[str, str]) -> int:
    """Keep the quiz between one question and Telegram's practical patience."""
    return _read_bounded_int(
        values,
        "TRUSTLENS_QUIZ_QUESTIONS",
        default=DEFAULT_QUIZ_QUESTION_COUNT,
        minimum=1,
        maximum=10,
    )


def _read_bounded_int(
    values: Mapping[str, str],
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw = values.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(minimum, min(int(raw), maximum))
    except ValueError:
        return default
