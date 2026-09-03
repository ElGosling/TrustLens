"""Telegram-specific code; keep it separate from GPT and future fact checking."""

import time
from typing import Protocol

from app.escalate import (
    EscalationConfig,
    format_escalation_summary,
    write_escalation_brief,
)
from app.literacy import TECHNIQUE_LABELS, Technique, classify_technique
from app.message_input import MessageKind, parse_message, route_message
from app.quiz import DEFAULT_QUESTION_COUNT
from app.quiz_session import OPEN_PERIOD_SECONDS, QuizRunner
from app.response_formatter import format_fact_check_for_telegram
from app.storage import TrustLensStore, UserStats
from app.verdict import FactCheckResult, Verdict

HELP_TEXT = "\n".join(
    [
        "🔍 <b>TrustLens</b>",
        "",
        "Forward or paste anything that looks doubtful and I will check it "
        "against trusted sources, then reply with a verdict, a confidence "
        "level, and the sources behind it.",
        "",
        "<b>Commands</b>",
        "/quiz - a short recap quiz built from the claims you checked",
        "/quizstop - stop a quiz that is running",
        "/stats - your checks, quiz accuracy, and streak",
        "/escalate - dump recurring scams and false claims to a brief",
        "/help - this message",
    ]
)

BOT_COMMANDS = (
    ("quiz", "Recap quiz on what you have checked"),
    ("quizstop", "Stop the quiz that is running"),
    ("stats", "Your checks, accuracy, and streak"),
    ("escalate", "Dump recurring scams to a harm brief"),
    ("help", "How to use TrustLens"),
)

GENERIC_FAILURE = "Sorry, TrustLens could not reply right now. Please try again."


class TextResponder(Protocol):
    """Anything that can turn text into a reply for the Telegram adapter."""

    def answer(self, user_text: str) -> str: ...


def create_bot(
    token: str,
    responder: TextResponder,
    store: TrustLensStore | None = None,
    quiz_question_count: int = DEFAULT_QUESTION_COUNT,
    quiz_open_period: int = OPEN_PERIOD_SECONDS,
    escalation_config: EscalationConfig | None = None,
):
    """Create a Telegram bot that checks claims, stores them, and runs quizzes."""
    import telebot

    bot = telebot.TeleBot(token, parse_mode="HTML")
    runner = (
        QuizRunner(
            bot,
            store,
            question_count=quiz_question_count,
            open_period=quiz_open_period,
        )
        if store is not None
        else None
    )
    escalation = escalation_config or EscalationConfig()
    bot.trustlens_store = store
    bot.trustlens_quiz = runner

    # Command handlers are registered first: pyTelegramBotAPI runs the first
    # matching handler, and the catch-all below would otherwise fact-check
    # "/quiz" as if it were a claim.

    @bot.message_handler(commands=["start", "help"])
    def handle_help(message) -> None:
        _remember_user(store, message)
        bot.reply_to(message, HELP_TEXT)

    @bot.message_handler(commands=["quiz"])
    def handle_quiz(message) -> None:
        if runner is None:
            bot.reply_to(message, "Quizzes are unavailable: no local database is configured.")
            return
        _remember_user(store, message)
        try:
            runner.start(chat_id=message.chat.id, user_id=message.from_user.id)
        except Exception as error:
            print(f"Could not start a quiz: {error}")
            bot.reply_to(message, "TrustLens could not start the quiz. Please try again.")

    @bot.message_handler(commands=["quizstop"])
    def handle_quiz_stop(message) -> None:
        if runner is None:
            bot.reply_to(message, "No quiz is running.")
            return
        stopped = runner.cancel(chat_id=message.chat.id, user_id=message.from_user.id)
        bot.reply_to(
            message,
            "Quiz stopped. Your answers so far are saved." if stopped else "No quiz is running.",
        )

    @bot.message_handler(commands=["stats"])
    def handle_stats(message) -> None:
        if store is None:
            bot.reply_to(message, "Statistics are unavailable: no local database is configured.")
            return
        _remember_user(store, message)
        bot.reply_to(message, format_stats(store.user_stats(message.from_user.id)))

    @bot.message_handler(commands=["escalate"])
    def handle_escalate(message) -> None:
        if store is None:
            bot.reply_to(
                message,
                "Escalation is unavailable: no local database is configured.",
            )
            return
        _remember_user(store, message)
        try:
            path, clusters = write_escalation_brief(store, escalation)
        except Exception as error:
            print(f"Could not write an escalation brief: {error}")
            bot.reply_to(
                message,
                "TrustLens could not write the escalation brief. Please try again.",
            )
            return
        bot.reply_to(
            message,
            format_escalation_summary(
                path, clusters, window_days=escalation.window_days
            ),
        )

    @bot.message_handler(content_types=["text"], func=_is_not_command)
    def handle_text(message) -> None:
        text = message.text or ""
        _remember_user(store, message)
        started = time.perf_counter()
        result: FactCheckResult | None = None
        error: str | None = None
        try:
            result, reply = _check(responder, text)
        except Exception as caught:
            error = f"{type(caught).__name__}: {caught}"
            print(f"Could not reply to Telegram message: {caught}")
            reply = GENERIC_FAILURE

        _record_check(
            store=store,
            message=message,
            text=text,
            result=result,
            reply=reply,
            error=error,
            latency_ms=int((time.perf_counter() - started) * 1000),
            policy=getattr(responder, "policy", None),
        )
        bot.reply_to(message, reply)

    if runner is not None:

        @bot.poll_answer_handler(func=lambda poll_answer: True)
        def handle_poll_answer(poll_answer) -> None:
            try:
                runner.handle_poll_answer(poll_answer)
            except Exception as error:
                print(f"Could not process a quiz answer: {error}")

    return bot


def register_commands(bot) -> None:
    """Publish the command list so Telegram shows it in the message box menu."""
    import telebot

    try:
        bot.set_my_commands(
            [telebot.types.BotCommand(name, description) for name, description in BOT_COMMANDS]
        )
    except Exception as error:  # A failed menu update must not stop the bot.
        print(f"Could not publish the command list: {error}")


def format_stats(stats: UserStats) -> str:
    """Render /stats: what the user has checked, and how the quizzes are going."""
    lines = ["📊 <b>Your TrustLens activity</b>", ""]
    if not stats.checks:
        lines.append("You have not checked anything yet. Send me a claim to start.")
    else:
        lines.append(f"<b>Claims checked:</b> {stats.checks}")
        breakdown = ", ".join(
            f"{verdict} {count}" for verdict, count in stats.verdict_counts.items()
        )
        if breakdown:
            lines.append(f"<b>Verdicts:</b> {breakdown}")

    lines.extend(
        [
            "",
            f"<b>Quizzes completed:</b> {stats.quizzes_completed}",
            f"<b>Quiz accuracy:</b> {stats.accuracy}% "
            f"({stats.correct_answers}/{stats.questions_answered})",
            f"🔥 <b>Streak:</b> {stats.current_streak} (best {stats.longest_streak})",
        ]
    )

    top = _top_techniques(stats.technique_counts)
    if top:
        lines.extend(["", "<b>What you run into most</b>"])
        lines.extend(f"• {label} ({count})" for label, count in top)

    lines.extend(["", "Run /quiz for a recap built from these checks."])
    return "\n".join(lines)


def _top_techniques(counts: dict[str, int], limit: int = 3) -> list[tuple[str, int]]:
    """Name the manipulation patterns a user meets most often."""
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    labelled = []
    for name, count in ranked:
        try:
            technique = Technique(name)
        except ValueError:
            continue
        labelled.append((TECHNIQUE_LABELS[technique], count))
        if len(labelled) >= limit:
            break
    return labelled


def _is_not_command(message) -> bool:
    """Keep slash commands out of the fact-check path."""
    return not (message.text or "").startswith("/")


def _check(responder: TextResponder, text: str) -> tuple[FactCheckResult | None, str]:
    """Prefer the structured result so the check can be stored, not just sent."""
    if hasattr(responder, "check_message"):
        result = responder.check_message(text)
        return result, format_fact_check_for_telegram(result)
    return None, responder.answer(text)


def _remember_user(store: TrustLensStore | None, message) -> None:
    if store is None:
        return
    user = getattr(message, "from_user", None)
    if user is None:
        return
    try:
        store.record_user(
            user_id=user.id,
            username=getattr(user, "username", None),
            first_name=getattr(user, "first_name", None),
            language_code=getattr(user, "language_code", None),
        )
    except Exception as error:  # Storage must never block a reply.
        print(f"Could not record the user: {error}")


def _record_check(
    store: TrustLensStore | None,
    message,
    text: str,
    result: FactCheckResult | None,
    reply: str,
    error: str | None,
    latency_ms: int,
    policy=None,
) -> None:
    """Log the query, the verdict, and the technique it used."""
    if store is None:
        return

    kind, primary_url = _describe_message(text, policy)
    verdict: Verdict | None = result.verdict if result else None
    try:
        store.record_check(
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            message_id=getattr(message, "message_id", None),
            input_text=text,
            message_kind=kind,
            primary_url=primary_url,
            verdict=verdict.value if verdict else None,
            confidence=result.confidence if result else None,
            explanation=result.explanation if result else None,
            sources=[
                {"title": source.title, "url": source.url, "domain": source.domain}
                for source in (result.sources if result else ())
            ],
            technique=classify_technique(text, verdict, bool(primary_url)).value,
            reply_text=reply,
            error=error,
            latency_ms=latency_ms,
        )
    except Exception as storage_error:  # Storage must never block a reply.
        print(f"Could not record the check: {storage_error}")


def _describe_message(text: str, policy) -> tuple[str, str | None]:
    """Classify the message the same way the fact-check workflow routes it."""
    parsed = parse_message(text)
    if not parsed.urls:
        return MessageKind.TEXT_CLAIM.value, None
    if policy is None:
        return MessageKind.UNTRUSTED_URL.value, parsed.urls[0]
    routed = route_message(text, policy)
    return routed.kind.value, routed.primary_url
