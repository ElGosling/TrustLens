import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.escalate import (
    EscalationConfig,
    Priority,
    build_escalation_clusters,
    format_escalation_summary,
    is_eligible,
    render_brief,
    url_cluster_key,
    write_escalation_brief,
)
from app.literacy import Technique
from app.storage import StoredCheck, TrustLensStore
from app.telegram_bot import BOT_COMMANDS, HELP_TEXT
from app.verdict import Verdict


def _check(
    user_id: int,
    text: str,
    *,
    verdict: str = "False",
    confidence: int = 88,
    technique: str = "scam_link",
    primary_url: str | None = None,
    explanation: str = "Trusted sources contradict this.",
    sources: tuple[dict, ...] = (),
    created_at: datetime | None = None,
) -> StoredCheck:
    return StoredCheck(
        id=user_id,
        user_id=user_id,
        input_text=text,
        message_kind="text_claim",
        primary_url=primary_url,
        verdict=verdict,
        confidence=confidence,
        explanation=explanation,
        technique=technique,
        sources=sources,
        created_at=created_at or datetime(2026, 9, 1, tzinfo=timezone.utc),
    )


class EscalationStoreTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = TrustLensStore(Path(self.directory.name) / "test.sqlite3")
        self.addCleanup(self.store.close)
        self.now = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)
        self.config = EscalationConfig(window_days=14, min_unique_users=2)

    def _record(
        self,
        user_id: int,
        text: str,
        *,
        verdict: str = "False",
        confidence: int = 88,
        technique: str = "scam_link",
        primary_url: str | None = None,
        explanation: str = "Trusted sources contradict this.",
        sources: tuple[dict, ...] = (),
        created_at: datetime | None = None,
        error: str | None = None,
    ) -> int:
        return self.store.record_check(
            user_id=user_id,
            chat_id=user_id,
            message_id=user_id,
            input_text=text,
            verdict=verdict,
            confidence=confidence,
            technique=technique,
            primary_url=primary_url,
            explanation=explanation,
            sources=sources,
            error=error,
            created_at=created_at or self.now,
        )

    def _clusters(self):
        return build_escalation_clusters(self.store, self.config, now=self.now)


class EligibilityTests(unittest.TestCase):
    def test_low_confidence_false_is_dropped_unless_it_is_a_scam(self) -> None:
        weak = _check(1, "crime is up 300 percent this year they say", confidence=50, technique="manipulated_statistics")
        scam = _check(2, "parcel held pay customs fee immediately fake post", confidence=50)

        self.assertFalse(is_eligible(weak))
        self.assertTrue(is_eligible(scam))

    def test_true_and_satire_never_escalate(self) -> None:
        self.assertFalse(is_eligible(_check(1, "a genuine news article about rain", verdict="True")))
        self.assertFalse(
            is_eligible(
                _check(2, "a comedy site article forwarded as news", verdict="Satire", technique="satire_as_news")
            )
        )

    def test_unverified_is_kept_only_for_scam_or_impersonation(self) -> None:
        scam = _check(
            1,
            "parcel held pay customs fee immediately fake post",
            verdict="Unverified",
            confidence=50,
        )
        other = _check(
            2,
            "a doctor friend said this health claim is true",
            verdict="Unverified",
            confidence=80,
            technique="missing_source",
        )

        self.assertTrue(is_eligible(scam))
        self.assertFalse(is_eligible(other))

    def test_short_text_is_not_usable(self) -> None:
        self.assertFalse(is_eligible(_check(1, "too short", confidence=90)))


class ClusteringAndGateTests(EscalationStoreTestCase):
    def test_one_user_repeating_the_same_scam_does_not_escalate(self) -> None:
        text = "parcel held pay customs fee immediately fake post"
        for _ in range(10):
            self._record(42424242, text)

        self.assertEqual(self._clusters(), ())

    def test_two_users_with_the_same_url_escalate_as_critical(self) -> None:
        url = "https://SGPost-Delivery.co/pay?ref=1"
        self._record(
            42424242,
            "pay the delivery fee now or your parcel is gone",
            primary_url=url,
        )
        self._record(
            43434343,
            "different wording but the same lookalike domain",
            primary_url="https://sgpost-delivery.co/pay?utm=x",
        )

        clusters = self._clusters()

        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].priority, Priority.CRITICAL)
        self.assertEqual(clusters[0].unique_users, 2)
        self.assertEqual(clusters[0].fingerprint, "sgpost-delivery.co/pay")

    def test_parcel_scam_variants_merge_by_claim_terms(self) -> None:
        self._record(
            42424242,
            "Your parcel is held pay customs fee immediately at the fake post site",
        )
        self._record(
            43434343,
            "Parcel held pay customs fee immediately fake post",
        )

        clusters = self._clusters()

        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].check_count, 2)
        self.assertEqual(clusters[0].priority, Priority.CRITICAL)

    def test_similar_wording_does_not_merge_across_techniques(self) -> None:
        text = "Your parcel is held pay customs fee immediately at the fake post site"
        self._record(42424242, text, technique="scam_link")
        self._record(43434343, text, technique="manipulated_statistics")

        self.assertEqual(self._clusters(), ())

    def test_unverified_scam_link_still_escalates(self) -> None:
        text = "parcel held pay customs fee immediately fake post"
        self._record(42424242, text, verdict="Unverified", confidence=50)
        self._record(43434343, text, verdict="Unverified", confidence=55)

        clusters = self._clusters()

        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].priority, Priority.CRITICAL)
        self.assertEqual(clusters[0].majority_verdict, Verdict.UNVERIFIED)

    def test_false_headline_with_two_users_is_watch_until_a_third_arrives(self) -> None:
        text = "shocking news they dont want you to know about this"
        self._record(11, text, technique="sensational_headline")
        self._record(12, text, technique="sensational_headline")

        watch = self._clusters()
        self.assertEqual(len(watch), 1)
        self.assertEqual(watch[0].priority, Priority.WATCH)

        self._record(13, text, technique="sensational_headline")
        high = self._clusters()
        self.assertEqual(high[0].priority, Priority.HIGH)

    def test_quiz_misses_from_two_users_bump_watch_to_high(self) -> None:
        text = "shocking news they dont want you to know about this"
        first = self._record(11, text, technique="sensational_headline")
        second = self._record(12, text, technique="sensational_headline")
        self.assertEqual(self._clusters()[0].priority, Priority.WATCH)

        session = self.store.create_quiz_session(11, 11, question_count=2, personalised=True)
        question_one = self.store.record_question(
            session_id=session,
            position=0,
            question="What was the verdict?",
            options=["True", "False"],
            correct_option_id=1,
            explanation="It was false.",
            technique="sensational_headline",
            origin="personal",
            poll_id="poll-miss-1",
            check_id=first,
        )
        question_two = self.store.record_question(
            session_id=session,
            position=1,
            question="What was the verdict again?",
            options=["True", "False"],
            correct_option_id=1,
            explanation="It was false.",
            technique="sensational_headline",
            origin="personal",
            poll_id="poll-miss-2",
            check_id=second,
        )
        self.store.record_answer(question_one, session, 11, 0, False)
        self.store.record_answer(question_two, session, 12, 0, False)

        clusters = self._clusters()
        self.assertEqual(clusters[0].priority, Priority.HIGH)
        self.assertEqual(clusters[0].quiz_miss_users, 2)

    def test_old_checks_outside_the_window_are_ignored(self) -> None:
        text = "parcel held pay customs fee immediately fake post"
        old = self.now - timedelta(days=20)
        self._record(42424242, text, created_at=old)
        self._record(43434343, text, created_at=old)

        self.assertEqual(self._clusters(), ())


class BriefOutputTests(EscalationStoreTestCase):
    def test_the_txt_brief_has_no_user_or_chat_identifiers(self) -> None:
        text = "parcel held pay customs fee immediately fake post"
        sources = ({"title": "ScamShield", "url": "https://www.scamshield.gov.sg/", "domain": "scamshield.gov.sg"},)
        self.store.record_user(42424242, username="ah_ma_target", first_name="Ah Ma")
        self._record(
            42424242,
            text,
            sources=sources,
            explanation="No agency is holding this parcel.",
        )
        self._record(43434343, text, sources=sources)

        path, clusters = write_escalation_brief(
            self.store,
            self.config,
            now=self.now,
            output_dir=Path(self.directory.name) / "escalations",
        )
        body = path.read_text(encoding="utf-8")

        self.assertTrue(path.name.startswith("escalation-"))
        self.assertIn("PRIORITY: CRITICAL", body)
        self.assertIn(text, body)
        self.assertIn("https://www.scamshield.gov.sg/", body)
        self.assertIn("unique_users>=2", body)
        self.assertNotIn("42424242", body)
        self.assertNotIn("43434343", body)
        self.assertNotIn("ah_ma_target", body)
        self.assertNotIn("Ah Ma", body)
        summary = format_escalation_summary(path, clusters, window_days=14)
        self.assertIn("CRITICAL 1", summary)
        self.assertNotIn(text, summary)

    def test_an_empty_run_still_writes_a_header_only_brief(self) -> None:
        path, clusters = write_escalation_brief(
            self.store,
            self.config,
            now=self.now,
            output_dir=Path(self.directory.name) / "escalations",
        )
        body = path.read_text(encoding="utf-8")

        self.assertEqual(clusters, ())
        self.assertIn("No clusters met the escalation threshold.", body)
        self.assertIn("No recurring scams", format_escalation_summary(path, clusters))


class UrlKeyTests(unittest.TestCase):
    def test_query_strings_are_stripped_and_hosts_are_lowercased(self) -> None:
        self.assertEqual(
            url_cluster_key("https://SGPost-Delivery.co/pay?ref=1"),
            "sgpost-delivery.co/pay",
        )
        self.assertIsNone(url_cluster_key(None))


class TelegramSurfaceTests(unittest.TestCase):
    def test_escalate_is_on_the_command_menu_and_help_text(self) -> None:
        self.assertIn(("escalate", "Dump recurring scams to a harm brief"), BOT_COMMANDS)
        self.assertIn("/escalate", HELP_TEXT)


class RenderDoesNotLeakIdsTests(unittest.TestCase):
    def test_render_brief_does_not_print_stored_user_ids(self) -> None:
        from app.escalate import EscalatedCluster

        representative = _check(
            42424242,
            "parcel held pay customs fee immediately fake post",
        )
        cluster = EscalatedCluster(
            priority=Priority.CRITICAL,
            technique=Technique.SCAM_LINK,
            unique_users=2,
            check_count=2,
            first_seen=representative.created_at,
            last_seen=representative.created_at,
            representative=representative,
            median_confidence=88,
            majority_verdict=Verdict.FALSE,
            explanation="Trusted sources contradict this.",
            sources=("https://www.scamshield.gov.sg/",),
            variants=(),
            quiz_miss_users=0,
            fingerprint="parcel|customs",
        )
        body = render_brief((cluster,))
        self.assertNotIn("42424242", body)
        self.assertIn("Unique users: 2", body)


if __name__ == "__main__":
    unittest.main()
