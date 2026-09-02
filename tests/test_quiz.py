import random
import unittest
from datetime import datetime, timezone

from app.literacy import GENERAL_BANK, Technique, classify_technique
from app.quiz import (
    MAX_EXPLANATION_LENGTH,
    MAX_OPTION_LENGTH,
    MAX_QUESTION_LENGTH,
    ORIGIN_GENERAL,
    ORIGIN_PERSONAL,
    ORIGIN_TARGETED,
    QuizQuestion,
    build_quiz,
)
from app.storage import StoredCheck
from app.verdict import Verdict


def make_check(
    check_id: int = 1,
    text: str = "My uncle says the government is giving every household $800 this week",
    verdict: str = "False",
    technique: str = "impersonated_authority",
    explanation: str = "No agency announced this payout. The message reuses an older hoax.",
) -> StoredCheck:
    return StoredCheck(
        id=check_id,
        user_id=7,
        input_text=text,
        message_kind="text_claim",
        primary_url=None,
        verdict=verdict,
        confidence=90,
        explanation=explanation,
        technique=technique,
        sources=(),
        created_at=datetime(2026, 8, 20, 4, 0, tzinfo=timezone.utc),
    )


class QuizQuestionValidationTests(unittest.TestCase):
    """Telegram rejects the whole poll if any limit is broken, so guard early."""

    def test_a_question_longer_than_telegram_allows_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            QuizQuestion(
                question="x" * (MAX_QUESTION_LENGTH + 1),
                options=("a", "b"),
                correct_option_id=0,
                explanation="",
                technique=Technique.SCAM_LINK,
                origin=ORIGIN_GENERAL,
            )

    def test_an_option_longer_than_telegram_allows_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            QuizQuestion(
                question="Real?",
                options=("a", "b" * (MAX_OPTION_LENGTH + 1)),
                correct_option_id=0,
                explanation="",
                technique=Technique.SCAM_LINK,
                origin=ORIGIN_GENERAL,
            )

    def test_a_correct_option_outside_the_options_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            QuizQuestion(
                question="Real?",
                options=("a", "b"),
                correct_option_id=2,
                explanation="",
                technique=Technique.SCAM_LINK,
                origin=ORIGIN_GENERAL,
            )

    def test_duplicate_options_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            QuizQuestion(
                question="Real?",
                options=("a", "a"),
                correct_option_id=0,
                explanation="",
                technique=Technique.SCAM_LINK,
                origin=ORIGIN_GENERAL,
            )


class QuestionBankTests(unittest.TestCase):
    def test_every_curated_question_fits_telegrams_poll_limits(self) -> None:
        for item in GENERAL_BANK:
            with self.subTest(question=item.question[:40]):
                self.assertLessEqual(len(item.question), MAX_QUESTION_LENGTH)
                self.assertLessEqual(len(item.explanation), MAX_EXPLANATION_LENGTH)
                self.assertGreaterEqual(len(item.options), 2)
                self.assertLessEqual(len(item.options), 12)
                self.assertIn(item.correct_option, item.options)
                for option in item.options:
                    self.assertLessEqual(len(option), MAX_OPTION_LENGTH)

    def test_the_bank_covers_every_technique_the_classifier_can_produce(self) -> None:
        covered = {item.technique for item in GENERAL_BANK}

        self.assertEqual(covered, set(Technique))


class BuildQuizTests(unittest.TestCase):
    def test_a_new_user_still_gets_a_full_quiz_from_the_bank(self) -> None:
        quiz = build_quiz(rng=random.Random(1))

        self.assertEqual(len(quiz), 5)
        self.assertEqual(quiz.personal_count, 0)
        self.assertFalse(quiz.is_personalised)

    def test_a_users_own_checks_become_verdict_recall_questions(self) -> None:
        quiz = build_quiz(checks=[make_check()], rng=random.Random(1))

        personal = [item for item in quiz.questions if item.origin == ORIGIN_PERSONAL]

        self.assertEqual(len(personal), 1)
        self.assertIn("$800", personal[0].question)
        self.assertIn("20 Aug", personal[0].question)
        self.assertTrue(personal[0].correct_option.startswith("False"))
        self.assertEqual(personal[0].check_id, 1)

    def test_the_stored_explanation_is_reused_as_the_quiz_hint(self) -> None:
        quiz = build_quiz(checks=[make_check()], rng=random.Random(1))

        personal = next(item for item in quiz.questions if item.origin == ORIGIN_PERSONAL)

        self.assertIn("No agency announced this payout", personal.explanation)

    def test_personal_questions_never_crowd_out_the_technique_drills(self) -> None:
        checks = [make_check(check_id=index, text=f"Claim number {index} about a payout")
                  for index in range(1, 9)]

        quiz = build_quiz(checks=checks, question_count=5, rng=random.Random(1))

        self.assertEqual(len(quiz), 5)
        self.assertEqual(quiz.personal_count, 3)

    def test_bank_questions_lead_with_the_techniques_the_user_actually_met(self) -> None:
        quiz = build_quiz(
            technique_counts={"scam_link": 4, "outdated_news": 1},
            question_count=2,
            rng=random.Random(1),
        )

        self.assertEqual(quiz.questions[0].technique, Technique.SCAM_LINK)
        self.assertEqual(quiz.questions[0].origin, ORIGIN_TARGETED)
        self.assertEqual(quiz.questions[1].technique, Technique.OUTDATED_NEWS)

    def test_options_are_shuffled_so_the_answer_is_not_always_first(self) -> None:
        positions = {
            build_quiz(question_count=1, rng=random.Random(seed)).questions[0].correct_option_id
            for seed in range(20)
        }

        self.assertGreater(len(positions), 1)

    def test_a_check_with_no_verdict_is_not_quizzed_on(self) -> None:
        quiz = build_quiz(checks=[make_check(verdict=None)], rng=random.Random(1))

        self.assertEqual(quiz.personal_count, 0)

    def test_the_same_claim_is_not_asked_about_twice(self) -> None:
        duplicate = [make_check(check_id=1), make_check(check_id=2)]

        quiz = build_quiz(checks=duplicate, rng=random.Random(1))

        self.assertEqual(quiz.personal_count, 1)

    def test_a_long_claim_is_truncated_to_fit_the_poll_question(self) -> None:
        quiz = build_quiz(checks=[make_check(text="word " * 200)], rng=random.Random(1))

        personal = next(item for item in quiz.questions if item.origin == ORIGIN_PERSONAL)

        self.assertLessEqual(len(personal.question), MAX_QUESTION_LENGTH)
        self.assertIn("…", personal.question)

    def test_every_generated_question_is_unique_within_one_quiz(self) -> None:
        quiz = build_quiz(
            checks=[make_check(check_id=i, text=f"Distinct claim {i} about a photo") for i in range(1, 4)],
            technique_counts={"scam_link": 2},
            rng=random.Random(3),
        )

        texts = [item.question for item in quiz.questions]

        self.assertEqual(len(texts), len(set(texts)))

    def test_quotes_in_a_claim_cannot_break_the_question_text(self) -> None:
        quiz = build_quiz(
            checks=[make_check(text='He said "this is real" on\nthe news')],
            rng=random.Random(1),
        )

        personal = next(item for item in quiz.questions if item.origin == ORIGIN_PERSONAL)

        self.assertNotIn("\n", personal.question)
        self.assertIn("'this is real'", personal.question)


class ClassifyTechniqueTests(unittest.TestCase):
    def test_a_satire_verdict_always_wins(self) -> None:
        self.assertIs(
            classify_technique("A photo of a cat", Verdict.SATIRE),
            Technique.SATIRE_AS_NEWS,
        )

    def test_scam_wording_is_recognised_before_anything_else(self) -> None:
        self.assertIs(
            classify_technique("Your parcel is held, click here to pay", Verdict.FALSE),
            Technique.SCAM_LINK,
        )

    def test_an_official_sounding_notice_is_tagged_as_impersonation(self) -> None:
        self.assertIs(
            classify_technique("Ministry advisory: stay home tomorrow", Verdict.FALSE),
            Technique.IMPERSONATED_AUTHORITY,
        )

    def test_an_unverified_text_claim_falls_back_to_the_right_tag(self) -> None:
        self.assertIs(
            classify_technique("Something odd happened", Verdict.UNVERIFIED),
            Technique.UNVERIFIED_CLAIM,
        )

    def test_a_plain_claim_with_no_signals_is_tagged_as_unsourced(self) -> None:
        self.assertIs(
            classify_technique("Durian prices will rise", Verdict.TRUE),
            Technique.MISSING_SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
