import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.storage import TrustLensStore


class StoreTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = TrustLensStore(Path(self.directory.name) / "test.sqlite3")
        self.addCleanup(self.store.close)


class CheckStorageTests(StoreTestCase):
    def test_a_check_is_stored_with_its_verdict_and_sources(self) -> None:
        self.store.record_user(7, username="ah_ma", first_name="Ah Ma")
        self.store.record_check(
            user_id=7,
            chat_id=7,
            input_text="Free CPF top-up for everyone this month",
            verdict="False",
            confidence=88,
            explanation="No agency announced this. The message copies an older scam.",
            sources=[{"title": "CPF", "url": "https://www.cpf.gov.sg/", "domain": "cpf.gov.sg"}],
            technique="impersonated_authority",
            latency_ms=1200,
        )

        stored = self.store.recent_checks(7)

        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].verdict, "False")
        self.assertEqual(stored[0].confidence, 88)
        self.assertEqual(stored[0].sources[0]["domain"], "cpf.gov.sg")
        self.assertEqual(stored[0].technique, "impersonated_authority")

    def test_checks_without_a_verdict_are_excluded_from_quiz_material(self) -> None:
        self.store.record_check(user_id=7, input_text="A failed check", error="boom")
        self.store.record_check(user_id=7, input_text="A real check", verdict="True")

        self.assertEqual(len(self.store.recent_checks(7)), 1)
        self.assertEqual(len(self.store.recent_checks(7, only_with_verdict=False)), 2)

    def test_technique_counts_rank_what_a_user_meets_most(self) -> None:
        for technique in ("scam_link", "scam_link", "out_of_context_media"):
            self.store.record_check(
                user_id=7, input_text="x", verdict="False", technique=technique
            )

        counts = self.store.technique_counts(7)

        self.assertEqual(counts["scam_link"], 2)
        self.assertEqual(counts["out_of_context_media"], 1)

    def test_one_users_checks_are_not_visible_to_another(self) -> None:
        self.store.record_check(user_id=1, input_text="mine", verdict="True")
        self.store.record_check(user_id=2, input_text="theirs", verdict="True")

        self.assertEqual([check.input_text for check in self.store.recent_checks(1)], ["mine"])


class QuizStorageTests(StoreTestCase):
    def _question(self, session_id: int, position: int = 0, poll_id: str = "poll-1") -> int:
        return self.store.record_question(
            session_id=session_id,
            position=position,
            question="What was the verdict?",
            options=["True", "False"],
            correct_option_id=1,
            explanation="The sources contradict it.",
            technique="scam_link",
            origin="personal",
            poll_id=poll_id,
            poll_message_id=100 + position,
        )

    def test_a_question_can_be_found_from_its_poll_id(self) -> None:
        session_id = self.store.create_quiz_session(7, 7, question_count=2, personalised=True)
        question_id = self._question(session_id)

        found = self.store.question_by_poll("poll-1")

        self.assertIsNotNone(found)
        self.assertEqual(found.id, question_id)
        self.assertEqual(found.user_id, 7)
        self.assertEqual(found.correct_option_id, 1)
        self.assertFalse(found.answered)

    def test_a_question_can_only_be_answered_once(self) -> None:
        session_id = self.store.create_quiz_session(7, 7, question_count=1, personalised=False)
        question_id = self._question(session_id)

        first = self.store.record_answer(question_id, session_id, 7, 1, True)
        second = self.store.record_answer(question_id, session_id, 7, 0, False)

        self.assertTrue(first)
        self.assertFalse(second)
        progress = self.store.session_progress(session_id)
        self.assertEqual(progress.answered, 1)
        self.assertEqual(progress.correct, 1)

    def test_progress_reports_what_is_asked_answered_and_correct(self) -> None:
        session_id = self.store.create_quiz_session(7, 7, question_count=2, personalised=True)
        first = self._question(session_id, position=0, poll_id="poll-1")
        self.store.record_answer(first, session_id, 7, 1, True)
        self._question(session_id, position=1, poll_id="poll-2")

        progress = self.store.session_progress(session_id)

        self.assertEqual((progress.asked, progress.answered, progress.correct), (2, 1, 1))
        self.assertFalse(progress.finished)

    def test_starting_a_quiz_cancels_the_previous_unfinished_one(self) -> None:
        first = self.store.create_quiz_session(7, 7, question_count=2, personalised=False)
        second = self.store.create_quiz_session(7, 7, question_count=2, personalised=False)

        self.assertEqual(self.store.session_progress(first).status, "cancelled")
        self.assertEqual(self.store.active_session_id(7), second)

    def test_missed_techniques_are_reported_worst_first(self) -> None:
        session_id = self.store.create_quiz_session(7, 7, question_count=2, personalised=False)
        wrong = self._question(session_id, position=0, poll_id="poll-1")
        self.store.record_answer(wrong, session_id, 7, 0, False)
        right = self._question(session_id, position=1, poll_id="poll-2")
        self.store.record_answer(right, session_id, 7, 1, True)

        self.assertEqual(self.store.weak_techniques(session_id), ["scam_link"])


class StreakTests(StoreTestCase):
    def test_consecutive_days_extend_the_streak(self) -> None:
        self.store.register_quiz_day(7, date(2026, 9, 1))
        result = self.store.register_quiz_day(7, date(2026, 9, 2))

        self.assertEqual(result.current_streak, 2)
        self.assertEqual(result.longest_streak, 2)
        self.assertTrue(result.counted_today)

    def test_a_second_quiz_on_the_same_day_does_not_extend_the_streak(self) -> None:
        self.store.register_quiz_day(7, date(2026, 9, 1))
        result = self.store.register_quiz_day(7, date(2026, 9, 1))

        self.assertEqual(result.current_streak, 1)
        self.assertFalse(result.counted_today)

    def test_a_missed_day_resets_the_streak_but_keeps_the_best(self) -> None:
        self.store.register_quiz_day(7, date(2026, 9, 1))
        self.store.register_quiz_day(7, date(2026, 9, 2))
        result = self.store.register_quiz_day(7, date(2026, 9, 5))

        self.assertEqual(result.current_streak, 1)
        self.assertEqual(result.longest_streak, 2)

    def test_streaks_survive_a_user_who_was_never_recorded_first(self) -> None:
        result = self.store.register_quiz_day(99, date(2026, 9, 1))

        self.assertEqual(result.current_streak, 1)
        self.assertEqual(self.store.user_stats(99).current_streak, 1)


class StatsTests(StoreTestCase):
    def test_stats_combine_checks_quizzes_and_streaks(self) -> None:
        self.store.record_user(7)
        self.store.record_check(user_id=7, input_text="a", verdict="False", technique="scam_link")
        self.store.record_check(user_id=7, input_text="b", verdict="False", technique="scam_link")
        session_id = self.store.create_quiz_session(7, 7, question_count=1, personalised=True)
        question_id = self.store.record_question(
            session_id=session_id,
            position=0,
            question="q",
            options=["a", "b"],
            correct_option_id=0,
            explanation="e",
            technique="scam_link",
            origin="personal",
            poll_id="poll-1",
        )
        self.store.record_answer(question_id, session_id, 7, 0, True)
        self.store.finish_session(session_id)
        self.store.register_quiz_day(7, date(2026, 9, 1))

        stats = self.store.user_stats(7)

        self.assertEqual(stats.checks, 2)
        self.assertEqual(stats.verdict_counts, {"False": 2})
        self.assertEqual(stats.quizzes_completed, 1)
        self.assertEqual(stats.accuracy, 100)
        self.assertEqual(stats.current_streak, 1)

    def test_accuracy_is_zero_before_any_quiz_is_answered(self) -> None:
        self.assertEqual(self.store.user_stats(7).accuracy, 0)


if __name__ == "__main__":
    unittest.main()
