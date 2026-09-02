"""Run an interactive /quiz as a sequence of native Telegram quiz polls.

Telegram's quiz poll already does the parts that are hard to build well in a
chat: it renders the options, marks the right answer, shows the explanation as
a hint, and runs its own countdown. This module drives one question at a time,
records every answer in SQLite, and closes the session with a streak update.

Poll mechanics used here (https://core.telegram.org/bots/api#sendpoll):
  * type="quiz" with the 0-based index of the correct option
  * is_anonymous=False, because a bot only receives poll_answer updates for
    non-anonymous polls, and the score has to be attributed to a user
  * explanation, shown when the user answers wrongly or taps the lamp icon
  * open_period, so an abandoned question closes itself instead of hanging
"""

import inspect
import threading
from html import escape

from app.literacy import TECHNIQUE_LABELS, TECHNIQUE_TIPS, Technique
from app.quiz import DEFAULT_QUESTION_COUNT, QuizQuestion, build_quiz
from app.storage import SessionProgress, TrustLensStore

OPEN_PERIOD_SECONDS = 90
TIMEOUT_GRACE_SECONDS = 3.0
NEXT_QUESTION_DELAY_SECONDS = 2.0

# Fallback for send_poll implementations we cannot introspect (test doubles).
LEGACY_POLL_PARAMETERS = frozenset(
    {
        "chat_id",
        "question",
        "options",
        "is_anonymous",
        "type",
        "correct_option_id",
        "explanation",
        "explanation_parse_mode",
        "open_period",
    }
)


class QuizRunner:
    """Own the lifecycle of one user's quiz: build, ask, score, recap."""

    def __init__(
        self,
        bot,
        store: TrustLensStore,
        question_count: int = DEFAULT_QUESTION_COUNT,
        open_period: int = OPEN_PERIOD_SECONDS,
        next_question_delay: float = NEXT_QUESTION_DELAY_SECONDS,
        timer_factory=threading.Timer,
    ) -> None:
        self.bot = bot
        self.store = store
        self.question_count = question_count
        self.open_period = open_period
        self.next_question_delay = next_question_delay
        self.timer_factory = timer_factory
        self._lock = threading.RLock()
        self._quizzes: dict[int, tuple[QuizQuestion, ...]] = {}
        self._timers: dict[int, threading.Timer] = {}
        self._poll_parameters: frozenset[str] | None = None

    # ----------------------------------------------------------- public API

    def start(self, chat_id: int, user_id: int) -> None:
        """Build a recap from this user's history and send the first question."""
        checks = self.store.recent_checks(user_id, limit=25)
        quiz = build_quiz(
            checks=checks,
            technique_counts=self.store.technique_counts(user_id),
            question_count=self.question_count,
        )
        if not quiz.questions:
            self.bot.send_message(
                chat_id, "The quiz bank is empty right now. Please try again later."
            )
            return

        with self._lock:
            previous = self.store.active_session_id(user_id)
            if previous is not None:
                self._cancel_timer(previous)
                self._quizzes.pop(previous, None)
            session_id = self.store.create_quiz_session(
                user_id=user_id,
                chat_id=chat_id,
                question_count=len(quiz),
                personalised=quiz.is_personalised,
            )
            self._quizzes[session_id] = quiz.questions

        self.bot.send_message(chat_id, _intro_text(quiz, self.open_period))
        self._advance(session_id)

    def handle_poll_answer(self, poll_answer) -> None:
        """Score one vote and move the quiz on."""
        question = self.store.question_by_poll(poll_answer.poll_id)
        if question is None:
            return

        voter = getattr(poll_answer, "user", None)
        if voter is None or voter.id != question.user_id:
            # Someone else in a group tapped the poll; only the owner is scored.
            return

        option_ids = list(getattr(poll_answer, "option_ids", None) or [])
        if not option_ids:
            return  # The vote was retracted.

        chosen = option_ids[0]
        is_correct = chosen == question.correct_option_id
        recorded = self.store.record_answer(
            question_id=question.id,
            session_id=question.session_id,
            user_id=question.user_id,
            chosen_option_id=chosen,
            is_correct=is_correct,
        )
        if not recorded:
            return  # A timeout already closed this question.

        self._cancel_timer(question.session_id)
        self._schedule(
            question.session_id, self.next_question_delay, self._advance, question.session_id
        )

    def cancel(self, chat_id: int, user_id: int) -> bool:
        """Stop the user's quiz early. Returns True if one was running."""
        with self._lock:
            session_id = self.store.active_session_id(user_id)
            if session_id is None:
                return False
            self._cancel_timer(session_id)
            self._quizzes.pop(session_id, None)
            self.store.cancel_active_sessions(user_id)
        return True

    def shutdown(self) -> None:
        """Cancel every pending timer, for a clean exit."""
        with self._lock:
            for timer in self._timers.values():
                timer.cancel()
            self._timers.clear()

    # ------------------------------------------------------------- internals

    def _advance(self, session_id: int) -> None:
        """Send the next question, or finish the session when none are left."""
        with self._lock:
            progress = self.store.session_progress(session_id)
            if progress is None or progress.status != "active":
                return
            if progress.answered >= progress.question_count:
                self._finish(progress)
                return
            if progress.asked > progress.answered:
                return  # A question is still open and waiting for an answer.

            questions = self._quizzes.get(session_id)
            if not questions or progress.asked >= len(questions):
                self.store.finish_session(session_id, "cancelled")
                return

            self._ask(progress, questions[progress.asked], progress.asked)

    def _ask(self, progress: SessionProgress, question: QuizQuestion, index: int) -> None:
        """Send one question as a quiz poll and start its countdown."""
        try:
            message = self._send_quiz_poll(
                progress.chat_id, question, index + 1, progress.question_count
            )
        except Exception as error:  # pragma: no cover - network failure path
            print(f"Could not send quiz question {index + 1}: {error}")
            self.store.finish_session(progress.session_id, "cancelled")
            self._quizzes.pop(progress.session_id, None)
            self.bot.send_message(
                progress.chat_id,
                "TrustLens could not send the next question. Try /quiz again shortly.",
            )
            return

        poll = getattr(message, "poll", None)
        question_id = self.store.record_question(
            session_id=progress.session_id,
            position=index,
            question=question.question,
            options=question.options,
            correct_option_id=question.correct_option_id,
            explanation=question.explanation,
            technique=question.technique.value,
            origin=question.origin,
            poll_id=getattr(poll, "id", None),
            poll_message_id=getattr(message, "message_id", None),
            check_id=question.check_id,
        )
        self._schedule(
            progress.session_id,
            self.open_period + TIMEOUT_GRACE_SECONDS,
            self._on_timeout,
            progress.session_id,
            question_id,
        )

    def _send_quiz_poll(
        self, chat_id: int, question: QuizQuestion, number: int, total: int
    ):
        """Call sendPoll in the shape the installed library version supports."""
        parameters = self._send_poll_parameters()
        heading = f"Q{number}/{total}: {question.question}"
        explanation = question.explanation
        kwargs: dict[str, object] = {
            "is_anonymous": False,
            "type": "quiz",
            "open_period": self.open_period,
        }

        if "question_parse_mode" in parameters:
            kwargs["question_parse_mode"] = "HTML"
            heading = escape(heading, quote=False)
        if "explanation_parse_mode" in parameters:
            kwargs["explanation_parse_mode"] = "HTML"
            explanation = escape(explanation, quote=False)
        kwargs["explanation"] = explanation

        # correct_option_ids replaced correct_option_id in recent Bot API
        # versions; older pyTelegramBotAPI releases only know the singular form.
        if "correct_option_ids" in parameters:
            kwargs["correct_option_ids"] = [question.correct_option_id]
        else:
            kwargs["correct_option_id"] = question.correct_option_id

        return self.bot.send_poll(chat_id, heading, list(question.options), **kwargs)

    def _send_poll_parameters(self) -> frozenset[str]:
        if self._poll_parameters is None:
            try:
                signature = inspect.signature(self.bot.send_poll)
                self._poll_parameters = frozenset(signature.parameters)
            except (TypeError, ValueError):
                self._poll_parameters = LEGACY_POLL_PARAMETERS
        return self._poll_parameters

    def _on_timeout(self, session_id: int, question_id: int) -> None:
        """Close a question the user never answered, then carry on."""
        question = self.store.question_by_id(question_id)
        if question is None:
            return
        recorded = self.store.record_answer(
            question_id=question.id,
            session_id=session_id,
            user_id=question.user_id,
            chosen_option_id=None,
            is_correct=False,
            timed_out=True,
        )
        if recorded:
            self.bot.send_message(
                question.chat_id,
                "⏳ That one timed out. The right answer was: "
                f"<b>{escape(question.options[question.correct_option_id], quote=False)}</b>",
            )
        self._advance(session_id)

    def _finish(self, progress: SessionProgress) -> None:
        """Close the session, update the streak, and send the recap."""
        self.store.finish_session(progress.session_id, "completed")
        self._cancel_timer(progress.session_id)
        self._quizzes.pop(progress.session_id, None)
        streak = self.store.register_quiz_day(progress.user_id)
        weak = self.store.weak_techniques(progress.session_id)
        self.bot.send_message(
            progress.chat_id, _recap_text(progress, streak, weak)
        )

    # --------------------------------------------------------------- timers

    def _schedule(self, session_id: int, delay: float, function, *args) -> None:
        with self._lock:
            self._cancel_timer(session_id)
            timer = self.timer_factory(delay, function, args=args)
            timer.daemon = True
            self._timers[session_id] = timer
            timer.start()

    def _cancel_timer(self, session_id: int) -> None:
        timer = self._timers.pop(session_id, None)
        if timer is not None:
            timer.cancel()


def _intro_text(quiz, open_period: int) -> str:
    """Explain what the user is about to answer and where it came from."""
    lines = ["🧠 <b>TrustLens recap quiz</b>", ""]
    personal = quiz.personal_count
    if personal:
        claims = "claim" if personal == 1 else "claims"
        lines.append(
            f"{len(quiz)} questions. {personal} of them replay {claims} "
            "you sent TrustLens yourself."
        )
    else:
        lines.append(
            f"{len(quiz)} questions on the tactics behind misinformation. "
            "Send TrustLens a claim to check, and future quizzes will use your own."
        )
    lines.extend(
        [
            f"You have {open_period} seconds per question. Tap 💡 for a hint.",
            "",
            "Finish it to keep your daily streak. /quizstop to stop early.",
        ]
    )
    return "\n".join(lines)


def _recap_text(
    progress: SessionProgress, streak, weak_techniques: list[str]
) -> str:
    """Report the score, the streak, and the specific things to work on."""
    score = f"{progress.correct}/{progress.question_count}"
    percentage = round(100 * progress.correct / progress.question_count)
    lines = [
        "🎓 <b>Quiz complete</b>",
        "",
        f"<b>Score:</b> {score} ({percentage}%)",
    ]

    if streak.counted_today:
        days = "day" if streak.current_streak == 1 else "days"
        lines.append(f"🔥 <b>Streak:</b> {streak.current_streak} {days} in a row")
    else:
        lines.append(
            f"🔥 <b>Streak:</b> {streak.current_streak} (already counted today)"
        )
    if streak.longest_streak > streak.current_streak:
        lines.append(f"<b>Best streak:</b> {streak.longest_streak}")

    tips = _tips_for(weak_techniques)
    if tips:
        lines.extend(["", "<b>Worth another look</b>"])
        lines.extend(tips)
    else:
        lines.extend(["", "Clean sweep. Your eye for this is getting sharper."])

    lines.extend(["", "Come back tomorrow with /quiz to extend the streak."])
    return "\n".join(lines)


def _tips_for(technique_names: list[str], limit: int = 3) -> list[str]:
    """Turn missed techniques into one actionable line each."""
    tips = []
    for name in technique_names[:limit]:
        try:
            technique = Technique(name)
        except ValueError:
            continue
        label = escape(TECHNIQUE_LABELS[technique], quote=False)
        tip = escape(TECHNIQUE_TIPS[technique], quote=False)
        tips.append(f"• <b>{label}</b> — {tip}")
    return tips
