from pathlib import Path

from app.article_fetcher import create_tavily_article_fetcher
from app.escalate import EscalationConfig
from app.fact_check import FactCheckService
from app.gpt_responder import GPTResponder
from app.settings import Settings
from app.storage import TrustLensStore
from app.telegram_bot import create_bot, register_commands
from app.trusted_domains import TrustedDomainPolicy
from app.web_search import create_tavily_search

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run() -> None:
    """Load configuration, build the fact-check workflow, and start polling."""
    _validate_trusted_domains_module()
    settings = Settings.from_environment()
    source_file = PROJECT_ROOT / "config" / "trusted_sources.toml"
    policy = TrustedDomainPolicy.from_toml(source_file)
    searcher = create_tavily_search(api_key=settings.tavily_api_key, policy=policy)
    article_fetcher = create_tavily_article_fetcher(
        api_key=settings.tavily_api_key, policy=policy
    )
    generator = GPTResponder(model=settings.openai_model)
    fact_checker = FactCheckService(
        searcher=searcher,
        generator=generator,
        policy=policy,
        article_fetcher=article_fetcher,
    )
    store = TrustLensStore(_database_path(settings.database_path))
    bot = create_bot(
        token=settings.telegram_bot_token,
        responder=fact_checker,
        store=store,
        quiz_question_count=settings.quiz_question_count,
        escalation_config=EscalationConfig(
            window_days=settings.escalate_window_days,
            min_unique_users=settings.escalate_min_unique_users,
            database_path=settings.database_path,
            output_dir=settings.escalate_output_dir,
        ),
    )

    # Clear any webhook so long polling works; avoids 409 if a webhook was set earlier.
    bot.delete_webhook(drop_pending_updates=True)
    register_commands(bot)

    print(f"Storing checks and quiz results in {store.path}")
    print("TrustLens bot is running. Send it a text claim in Telegram, or /quiz.")
    try:
        bot.infinity_polling(skip_pending=True)
    except KeyboardInterrupt:
        print("\nStopping TrustLens.")
    except Exception as error:
        if _is_telegram_conflict(error):
            print(
                "\nTelegram error 409: another process is already polling this bot token.\n"
                "Fix: close every other TrustLens terminal, VS Code debug session, and\n"
                "Cloud Agent run using the same TELEGRAM_BOT_TOKEN. Wait 30 seconds,\n"
                "then start the bot again. If it persists, revoke the token in BotFather\n"
                "and update .env with the new token."
            )
            raise SystemExit(1) from error
        raise
    finally:
        quiz = getattr(bot, "trustlens_quiz", None)
        if quiz is not None:
            quiz.shutdown()
        store.close()


def _database_path(configured: str) -> Path:
    """Keep the SQLite file next to the project, whatever directory we ran from."""
    path = Path(configured).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def _is_telegram_conflict(error: Exception) -> bool:
    """Return True for Telegram's duplicate getUpdates conflict."""
    if error.__class__.__name__ != "ApiTelegramException":
        return False
    return getattr(error, "error_code", None) == 409


def _validate_trusted_domains_module() -> None:
    """Fail fast when the local tree mixes old and new TrustLens files."""
    required_methods = (
        "domains_for_categories",
        "matching_sources_for_claim_terms",
        "is_official_news_url",
    )
    missing = [
        name for name in required_methods if not hasattr(TrustedDomainPolicy, name)
    ]
    if missing:
        raise SystemExit(
            "Outdated app/trusted_domains.py detected. Missing: "
            + ", ".join(missing)
            + ". Sync the full TrustLens update (especially trusted_domains.py, "
            + "web_search.py, fact_check.py, main.py, url_search.py, article_fetcher.py) "
            + "instead of copying individual files."
        )


if __name__ == "__main__":
    run()
