import tempfile
import unittest
from pathlib import Path
from typing import Optional

from app.quiz_session import QuizRunner
from app.storage import TrustLensStore


class FakeUser:
    def __init__(self, user_id: int) -> None:
        self.id = user_id


class FakePollAnswer:
    def __init__(self, poll_id: str, user_id: int, option_ids) -> None:
        self.poll_id = poll_id
        self.user = FakeUser(user_id)
        self.option_ids = option_ids


class FakePoll:
    def __init__(self, poll_id: str) -> None:
        self.id = poll_id


class FakeMessage:
    def __init__(self, message_id: int, poll_id: str) -> None:
        self.message_id = message_id
        self.poll = FakePoll(poll_id)


class ManualTimer:
    """A timer the test fires by hand, so question order is deterministic."""

    def __init__(self, delay, function, args=()) -> None:
        self.delay = delay
        self.function = function
        self.args = args
        self.cancelled = False
        self.daemon = False

    def start(self) -> None:
        pass

    def cancel(self) -> None:
        self.cancelled = True

    def fire(self) -> None:
        if not self.cancelled:
            self.function(*self.args)


class FakeBot:
    """Records what would have been sent to Telegram."""

    def __init__(self) -> None:
        self.messages: list[str] = []
        self.polls: list[dict] = []
        self._next_poll = 0

    def send_message(self, chat_id, text, **kwargs) -> None:
        self.messages.append(text)

    def send_poll(
        self,
        chat_id,
        question,
        options,
        is_anonymous=None,
        type=None,
        correct_option_id=None,
        explanation=None,
        explanation_parse_mode=None,
        question_parse_mode=None,
        open_period=None,
        **kwargs,
    ):
        self._next_poll += 1
        poll_id = f"poll-{self._next_poll}"
        self.polls.append(
            {
                "chat_id": chat_id,
                "question": question,
                "options": list(options),
                "is_anonymous": is_anonymous,
                "type": type,
                "correct_option_id": correct_option_id,
                "explanation": explanation,
                "open_period": open_period,
                "poll_id": poll_id,
            }
        )
        return FakeMessage(message_id=self._next_poll, poll_id=poll_id)


class ModernBot(FakeBot):
    """A newer pyTelegramBotAPI, where the correct answer is a list."""

    def send_poll(
        self,
        chat_id,
        question,
        options,
        is_anonymous=None,
        type=None,
        correct_option_ids=None,
        explanation=None,
        explanation_parse_mode=None,
        question_parse_mode=None,
        open_period=None,
        **kwargs,
    ):
        message = FakeBot.send_poll(
            self,
            chat_id,
            question,
            options,
            is_anonymous=is_anonymous,
            type=type,
            explanation=explanation,
            open_period=open_period,
        )
        self.polls[-1]["correct_option_ids"] = correct_option_ids
        return message


class QuizRunnerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.store = TrustLensStore(Path(directory.name) / "quiz.sqlite3")
        self.addCleanup(self.store.close)
        self.timers: list[ManualTimer] = []
        self.bot = FakeBot()
        self.runner = self._runner(self.bot)

    def _runner(self, bot, question_count: int = 2) -> QuizRunner:
        return QuizRunner(
            bot,
            self.store,
            question_count=question_count,
            open_period=30,
            timer_factory=self._timer,
        )

    def _timer(self, delay, function, args=()) -> ManualTimer:
        timer = ManualTimer(delay, function, args)
        self.timers.append(timer)
        return timer

    def _fire_pending(self) -> None:
        """Run the newest live timer, the way the real clock eventually would."""
        for timer in reversed(self.timers):
            if not timer.cancelled:
                timer.fire()
                return

    def _answer(self, poll_index: int, option_id: Optional[int], user_id: int = 7) -> None:
        poll = self.bot.polls[poll_index]
        self.runner.handle_poll_answer(
            FakePollAnswer(poll["poll_id"], user_id, [option_id] if option_id is not None else [])
        )


class SendingQuestionsTests(QuizRunnerTestCase):
    def test_the_first_question_is_sent_as_a_non_anonymous_quiz_poll(self) -> None:
        self.runner.start(chat_id=7, user_id=7)

        self.assertEqual(len(self.bot.polls), 1)
        poll = self.bot.polls[0]
        self.assertEqual(poll["type"], "quiz")
        # A bot only receives poll_answer updates for non-anonymous polls.
        self.assertFalse(poll["is_anonymous"])
        self.assertEqual(poll["open_period"], 30)
        self.assertTrue(poll["explanation"])
        self.assertIn("Q1/2", poll["question"])

    def test_the_next_question_only_arrives_after_the_previous_is_answered(self) -> None:
        self.runner.start(chat_id=7, user_id=7)

        self.assertEqual(len(self.bot.polls), 1)
        self._answer(0, self.bot.polls[0]["correct_option_id"])
        self.assertEqual(len(self.bot.polls), 1)  # Waiting on the short delay.

        self._fire_pending()

        self.assertEqual(len(self.bot.polls), 2)
        self.assertIn("Q2/2", self.bot.polls[1]["question"])

    def test_newer_library_versions_receive_the_list_form_of_the_answer(self) -> None:
        bot = ModernBot()
        runner = self._runner(bot)

        runner.start(chat_id=7, user_id=7)

        self.assertEqual(len(bot.polls[0]["correct_option_ids"]), 1)


class ScoringTests(QuizRunnerTestCase):
    def _complete_quiz(self, correctly: bool) -> None:
        self.runner.start(chat_id=7, user_id=7)
        poll = self.bot.polls[0]
        correct = poll["correct_option_id"]
        self._answer(0, correct if correctly else (correct + 1) % len(poll["options"]))
        self._fire_pending()
        poll = self.bot.polls[1]
        correct = poll["correct_option_id"]
        self._answer(1, correct if correctly else (correct + 1) % len(poll["options"]))
        self._fire_pending()

    def test_a_perfect_quiz_is_scored_and_starts_a_streak(self) -> None:
        self._complete_quiz(correctly=True)

        recap = self.bot.messages[-1]
        self.assertIn("Score:</b> 2/2 (100%)", recap)
        self.assertIn("Streak:</b> 1 day in a row", recap)
        self.assertEqual(self.store.user_stats(7).quizzes_completed, 1)

    def test_wrong_answers_come_back_as_things_to_work_on(self) -> None:
        self._complete_quiz(correctly=False)

        recap = self.bot.messages[-1]
        self.assertIn("Score:</b> 0/2 (0%)", recap)
        self.assertIn("Worth another look", recap)
        self.assertEqual(self.store.user_stats(7).correct_answers, 0)

    def test_a_timed_out_question_is_scored_as_wrong_and_the_quiz_moves_on(self) -> None:
        self.runner.start(chat_id=7, user_id=7)

        self._fire_pending()  # The open_period elapses with no answer.

        self.assertEqual(len(self.bot.polls), 2)
        self.assertIn("timed out", self.bot.messages[-1])
        self.assertEqual(self.store.user_stats(7).correct_answers, 0)

    def test_a_late_answer_after_a_timeout_is_ignored(self) -> None:
        self.runner.start(chat_id=7, user_id=7)
        self._fire_pending()
        polls_before = len(self.bot.polls)

        self._answer(0, self.bot.polls[0]["correct_option_id"])

        self.assertEqual(len(self.bot.polls), polls_before)
        self.assertEqual(self.store.user_stats(7).correct_answers, 0)

    def test_a_retracted_vote_is_not_scored(self) -> None:
        self.runner.start(chat_id=7, user_id=7)

        self._answer(0, None)

        self.assertEqual(self.store.user_stats(7).questions_answered, 0)

    def test_another_persons_vote_in_a_group_does_not_score_the_quiz(self) -> None:
        self.runner.start(chat_id=7, user_id=7)

        self._answer(0, self.bot.polls[0]["correct_option_id"], user_id=999)

        self.assertEqual(self.store.user_stats(7).questions_answered, 0)
        self.assertEqual(self.store.user_stats(999).questions_answered, 0)

    def test_a_repeated_poll_answer_update_is_only_counted_once(self) -> None:
        self.runner.start(chat_id=7, user_id=7)
        correct = self.bot.polls[0]["correct_option_id"]

        self._answer(0, correct)
        self._answer(0, correct)

        self.assertEqual(self.store.user_stats(7).questions_answered, 1)


class SessionControlTests(QuizRunnerTestCase):
    def test_stopping_a_quiz_ends_the_session_and_the_countdown(self) -> None:
        self.runner.start(chat_id=7, user_id=7)

        stopped = self.runner.cancel(chat_id=7, user_id=7)

        self.assertTrue(stopped)
        self.assertIsNone(self.store.active_session_id(7))
        self.assertTrue(all(timer.cancelled for timer in self.timers))

    def test_stopping_with_nothing_running_reports_nothing_to_stop(self) -> None:
        self.assertFalse(self.runner.cancel(chat_id=7, user_id=7))

    def test_starting_a_second_quiz_abandons_the_first(self) -> None:
        self.runner.start(chat_id=7, user_id=7)
        first_session = self.store.active_session_id(7)

        self.runner.start(chat_id=7, user_id=7)

        self.assertNotEqual(self.store.active_session_id(7), first_session)
        self.assertEqual(self.store.session_progress(first_session).status, "cancelled")

    def test_a_users_own_checks_are_replayed_in_the_intro(self) -> None:
        self.store.record_check(
            user_id=7,
            input_text="Photo of a flooded MRT station going around today",
            verdict="Misleading",
            explanation="The photo is real but was taken overseas in 2019.",
            technique="out_of_context_media",
        )

        self.runner.start(chat_id=7, user_id=7)

        self.assertIn("replay", self.bot.messages[0])
        self.assertIn("flooded MRT station", self.bot.polls[0]["question"])


if __name__ == "__main__":
    unittest.main()
