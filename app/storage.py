"""Local SQLite storage for everything a user sends TrustLens and every quiz.

The proposal's data layer is PostgreSQL, but the recap quiz only needs one
user's own history, so this milestone keeps that history in a single local
SQLite file. The schema mirrors the eventual Postgres tables (users, checks,
quiz sessions, questions, answers) so the move later is a port, not a redesign.

Every method takes the connection lock: pyTelegramBotAPI runs message handlers
on worker threads, so two checks can be recorded at the same moment.
"""

import json
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

# Singapore never observes daylight saving, so a fixed offset is exact and
# avoids depending on the tz database being installed on the host.
SINGAPORE_TIME = timezone(timedelta(hours=8), name="SGT")

SCHEMA_VERSION = 1

SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        language_code TEXT,
        first_seen_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL,
        current_streak INTEGER NOT NULL DEFAULT 0,
        longest_streak INTEGER NOT NULL DEFAULT 0,
        last_quiz_day TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        chat_id INTEGER,
        message_id INTEGER,
        input_text TEXT NOT NULL,
        message_kind TEXT,
        primary_url TEXT,
        verdict TEXT,
        confidence INTEGER,
        explanation TEXT,
        sources_json TEXT NOT NULL DEFAULT '[]',
        technique TEXT,
        reply_text TEXT,
        error TEXT,
        latency_ms INTEGER,
        created_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS checks_by_user ON checks(user_id, id DESC)",
    """
    CREATE TABLE IF NOT EXISTS quiz_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        chat_id INTEGER NOT NULL,
        question_count INTEGER NOT NULL,
        personalised INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'active',
        started_at TEXT NOT NULL,
        finished_at TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS sessions_by_user ON quiz_sessions(user_id, status)",
    """
    CREATE TABLE IF NOT EXISTS quiz_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL REFERENCES quiz_sessions(id),
        position INTEGER NOT NULL,
        poll_id TEXT,
        poll_message_id INTEGER,
        check_id INTEGER REFERENCES checks(id),
        origin TEXT NOT NULL,
        technique TEXT NOT NULL,
        question TEXT NOT NULL,
        options_json TEXT NOT NULL,
        correct_option_id INTEGER NOT NULL,
        explanation TEXT NOT NULL,
        asked_at TEXT NOT NULL
    )
    """,
    "CREATE UNIQUE INDEX IF NOT EXISTS questions_by_poll ON quiz_questions(poll_id)",
    """
    CREATE TABLE IF NOT EXISTS quiz_answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL REFERENCES quiz_questions(id),
        session_id INTEGER NOT NULL REFERENCES quiz_sessions(id),
        user_id INTEGER NOT NULL,
        chosen_option_id INTEGER,
        is_correct INTEGER NOT NULL,
        timed_out INTEGER NOT NULL DEFAULT 0,
        answered_at TEXT NOT NULL
    )
    """,
    "CREATE UNIQUE INDEX IF NOT EXISTS answers_by_question ON quiz_answers(question_id)",
)


@dataclass(frozen=True)
class StoredCheck:
    """One fact check as it was recorded, ready to be replayed in a quiz."""

    id: int
    user_id: int
    input_text: str
    message_kind: str | None
    primary_url: str | None
    verdict: str | None
    confidence: int | None
    explanation: str | None
    technique: str | None
    sources: tuple[dict[str, Any], ...]
    created_at: datetime

    @property
    def local_day(self) -> date:
        return self.created_at.astimezone(SINGAPORE_TIME).date()


@dataclass(frozen=True)
class StoredQuestion:
    """A quiz question that has already been sent as a Telegram poll."""

    id: int
    session_id: int
    user_id: int
    chat_id: int
    position: int
    question: str
    options: tuple[str, ...]
    correct_option_id: int
    explanation: str
    technique: str
    origin: str
    answered: bool


@dataclass(frozen=True)
class SessionProgress:
    """How far through a quiz a user is, used to decide what to send next."""

    session_id: int
    user_id: int
    chat_id: int
    question_count: int
    asked: int
    answered: int
    correct: int
    status: str
    personalised: bool

    @property
    def finished(self) -> bool:
        return self.answered >= self.question_count


@dataclass(frozen=True)
class StreakResult:
    """The outcome of counting one completed quiz towards a daily streak."""

    current_streak: int
    longest_streak: int
    counted_today: bool


@dataclass(frozen=True)
class UserStats:
    """The numbers behind /stats."""

    checks: int
    verdict_counts: dict[str, int] = field(default_factory=dict)
    technique_counts: dict[str, int] = field(default_factory=dict)
    quizzes_completed: int = 0
    questions_answered: int = 0
    correct_answers: int = 0
    current_streak: int = 0
    longest_streak: int = 0

    @property
    def accuracy(self) -> int:
        if not self.questions_answered:
            return 0
        return round(100 * self.correct_answers / self.questions_answered)


class TrustLensStore:
    """A tiny, thread-safe SQLite repository for checks and quizzes."""

    def __init__(self, path: str | Path = "data/trustlens.sqlite3") -> None:
        self.path = Path(path)
        if self.path.parent and str(self.path.parent) not in ("", "."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        # Handlers run on pyTelegramBotAPI worker threads, so one shared
        # connection plus an explicit lock is simpler than a pool here.
        self._connection = sqlite3.connect(str(self.path), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._create_schema()

    # ----------------------------------------------------------------- setup

    def _create_schema(self) -> None:
        with self._lock, self._connection:
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
            for statement in SCHEMA_STATEMENTS:
                self._connection.execute(statement)
            self._connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    # ----------------------------------------------------------------- users

    def record_user(
        self,
        user_id: int,
        username: str | None = None,
        first_name: str | None = None,
        language_code: str | None = None,
    ) -> None:
        """Remember who is talking to the bot, without overwriting first_seen_at."""
        now = _now_text()
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO users (
                    user_id, username, first_name, language_code,
                    first_seen_at, last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = COALESCE(excluded.username, users.username),
                    first_name = COALESCE(excluded.first_name, users.first_name),
                    language_code = COALESCE(excluded.language_code, users.language_code),
                    last_seen_at = excluded.last_seen_at
                """,
                (user_id, username, first_name, language_code, now, now),
            )

    # ---------------------------------------------------------------- checks

    def record_check(
        self,
        user_id: int,
        input_text: str,
        chat_id: int | None = None,
        message_id: int | None = None,
        message_kind: str | None = None,
        primary_url: str | None = None,
        verdict: str | None = None,
        confidence: int | None = None,
        explanation: str | None = None,
        sources: Iterable[dict[str, Any]] = (),
        technique: str | None = None,
        reply_text: str | None = None,
        error: str | None = None,
        latency_ms: int | None = None,
        created_at: datetime | None = None,
    ) -> int:
        """Store one incoming query and whatever TrustLens replied with."""
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT INTO checks (
                    user_id, chat_id, message_id, input_text, message_kind,
                    primary_url, verdict, confidence, explanation, sources_json,
                    technique, reply_text, error, latency_ms, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    chat_id,
                    message_id,
                    input_text,
                    message_kind,
                    primary_url,
                    verdict,
                    confidence,
                    explanation,
                    json.dumps(list(sources)),
                    technique,
                    reply_text,
                    error,
                    latency_ms,
                    _timestamp_text(created_at) if created_at is not None else _now_text(),
                ),
            )
            return int(cursor.lastrowid)

    def recent_checks(
        self, user_id: int, limit: int = 25, only_with_verdict: bool = True
    ) -> list[StoredCheck]:
        """Return a user's latest checks, newest first."""
        clause = "AND verdict IS NOT NULL" if only_with_verdict else ""
        with self._lock:
            rows = self._connection.execute(
                f"""
                SELECT * FROM checks
                WHERE user_id = ? {clause}
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [_check_from_row(row) for row in rows]

    def technique_counts(self, user_id: int, limit: int = 50) -> dict[str, int]:
        """Count the techniques seen in a user's most recent checks."""
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT technique, COUNT(*) AS total FROM (
                    SELECT technique FROM checks
                    WHERE user_id = ? AND technique IS NOT NULL
                    ORDER BY id DESC LIMIT ?
                )
                GROUP BY technique
                ORDER BY total DESC
                """,
                (user_id, limit),
            ).fetchall()
        return {row["technique"]: row["total"] for row in rows}

    def checks_for_escalation(
        self,
        since: datetime,
        verdicts: Sequence[str],
        min_confidence: int,
    ) -> list[StoredCheck]:
        """Return recent successful checks that could be harmful, across all users."""
        if not verdicts:
            return []
        placeholders = ",".join("?" * len(verdicts))
        with self._lock:
            rows = self._connection.execute(
                f"""
                SELECT * FROM checks
                WHERE error IS NULL
                  AND verdict IS NOT NULL
                  AND confidence >= ?
                  AND created_at >= ?
                  AND verdict IN ({placeholders})
                ORDER BY id ASC
                """,
                (min_confidence, _timestamp_text(since), *verdicts),
            ).fetchall()
        return [_check_from_row(row) for row in rows]

    def quiz_misses_by_check_id(self) -> dict[int, tuple[int, ...]]:
        """Map a stored check to the users who missed its personal recap question."""
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT q.check_id AS check_id, a.user_id AS user_id
                FROM quiz_answers a
                JOIN quiz_questions q ON q.id = a.question_id
                WHERE a.is_correct = 0
                  AND q.check_id IS NOT NULL
                  AND q.origin = 'personal'
                """
            ).fetchall()
        grouped: dict[int, list[int]] = {}
        for row in rows:
            check_id = int(row["check_id"])
            user_id = int(row["user_id"])
            seen = grouped.setdefault(check_id, [])
            if user_id not in seen:
                seen.append(user_id)
        return {check_id: tuple(user_ids) for check_id, user_ids in grouped.items()}

    # ---------------------------------------------------------------- quizzes

    def create_quiz_session(
        self, user_id: int, chat_id: int, question_count: int, personalised: bool
    ) -> int:
        """Open a quiz session; any earlier unfinished one is abandoned."""
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE quiz_sessions SET status = 'cancelled', finished_at = ? "
                "WHERE user_id = ? AND status = 'active'",
                (_now_text(), user_id),
            )
            cursor = self._connection.execute(
                """
                INSERT INTO quiz_sessions (
                    user_id, chat_id, question_count, personalised, status, started_at
                )
                VALUES (?, ?, ?, ?, 'active', ?)
                """,
                (user_id, chat_id, question_count, int(personalised), _now_text()),
            )
            return int(cursor.lastrowid)

    def record_question(
        self,
        session_id: int,
        position: int,
        question: str,
        options: Sequence[str],
        correct_option_id: int,
        explanation: str,
        technique: str,
        origin: str,
        poll_id: str | None = None,
        poll_message_id: int | None = None,
        check_id: int | None = None,
    ) -> int:
        """Store a question at the moment its poll is sent."""
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT INTO quiz_questions (
                    session_id, position, poll_id, poll_message_id, check_id,
                    origin, technique, question, options_json, correct_option_id,
                    explanation, asked_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    position,
                    poll_id,
                    poll_message_id,
                    check_id,
                    origin,
                    technique,
                    question,
                    json.dumps(list(options)),
                    correct_option_id,
                    explanation,
                    _now_text(),
                ),
            )
            return int(cursor.lastrowid)

    def question_by_poll(self, poll_id: str) -> StoredQuestion | None:
        """Find the question a poll_answer update belongs to."""
        with self._lock:
            row = self._connection.execute(
                """
                SELECT q.*, s.user_id AS user_id, s.chat_id AS chat_id,
                       EXISTS(SELECT 1 FROM quiz_answers a WHERE a.question_id = q.id)
                       AS answered
                FROM quiz_questions q
                JOIN quiz_sessions s ON s.id = q.session_id
                WHERE q.poll_id = ?
                """,
                (poll_id,),
            ).fetchone()
        return _question_from_row(row) if row else None

    def question_by_id(self, question_id: int) -> StoredQuestion | None:
        """Look a question up directly, used when a poll times out unanswered."""
        with self._lock:
            row = self._connection.execute(
                """
                SELECT q.*, s.user_id AS user_id, s.chat_id AS chat_id,
                       EXISTS(SELECT 1 FROM quiz_answers a WHERE a.question_id = q.id)
                       AS answered
                FROM quiz_questions q
                JOIN quiz_sessions s ON s.id = q.session_id
                WHERE q.id = ?
                """,
                (question_id,),
            ).fetchone()
        return _question_from_row(row) if row else None

    def record_answer(
        self,
        question_id: int,
        session_id: int,
        user_id: int,
        chosen_option_id: int | None,
        is_correct: bool,
        timed_out: bool = False,
    ) -> bool:
        """Record one answer. Returns False if this question was already answered.

        Telegram can deliver a poll_answer more than once, and a timeout can race
        a late vote, so the unique index on question_id is the real guard here.
        """
        with self._lock, self._connection:
            try:
                self._connection.execute(
                    """
                    INSERT INTO quiz_answers (
                        question_id, session_id, user_id, chosen_option_id,
                        is_correct, timed_out, answered_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        question_id,
                        session_id,
                        user_id,
                        chosen_option_id,
                        int(is_correct),
                        int(timed_out),
                        _now_text(),
                    ),
                )
            except sqlite3.IntegrityError:
                return False
        return True

    def session_progress(self, session_id: int) -> SessionProgress | None:
        """Summarise a session so the runner can decide what to send next."""
        with self._lock:
            row = self._connection.execute(
                """
                SELECT s.id, s.user_id, s.chat_id, s.question_count, s.status,
                       s.personalised,
                       (SELECT COUNT(*) FROM quiz_questions q
                        WHERE q.session_id = s.id) AS asked,
                       (SELECT COUNT(*) FROM quiz_answers a
                        WHERE a.session_id = s.id) AS answered,
                       (SELECT COUNT(*) FROM quiz_answers a
                        WHERE a.session_id = s.id AND a.is_correct = 1) AS correct
                FROM quiz_sessions s
                WHERE s.id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return SessionProgress(
            session_id=row["id"],
            user_id=row["user_id"],
            chat_id=row["chat_id"],
            question_count=row["question_count"],
            asked=row["asked"],
            answered=row["answered"],
            correct=row["correct"],
            status=row["status"],
            personalised=bool(row["personalised"]),
        )

    def active_session_id(self, user_id: int) -> int | None:
        """Return the user's unfinished quiz, if any."""
        with self._lock:
            row = self._connection.execute(
                "SELECT id FROM quiz_sessions WHERE user_id = ? AND status = 'active' "
                "ORDER BY id DESC LIMIT 1",
                (user_id,),
            ).fetchone()
        return int(row["id"]) if row else None

    def finish_session(self, session_id: int, status: str = "completed") -> None:
        """Close a session as completed or cancelled."""
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE quiz_sessions SET status = ?, finished_at = ? WHERE id = ?",
                (status, _now_text(), session_id),
            )

    def cancel_active_sessions(self, user_id: int) -> int:
        """Cancel whatever the user has open; returns how many were cancelled."""
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "UPDATE quiz_sessions SET status = 'cancelled', finished_at = ? "
                "WHERE user_id = ? AND status = 'active'",
                (_now_text(), user_id),
            )
            return int(cursor.rowcount or 0)

    def weak_techniques(self, session_id: int) -> list[str]:
        """List the techniques a user got wrong in one session, worst first."""
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT q.technique, COUNT(*) AS misses
                FROM quiz_answers a
                JOIN quiz_questions q ON q.id = a.question_id
                WHERE a.session_id = ? AND a.is_correct = 0
                GROUP BY q.technique
                ORDER BY misses DESC, q.technique
                """,
                (session_id,),
            ).fetchall()
        return [row["technique"] for row in rows]

    # --------------------------------------------------------------- streaks

    def register_quiz_day(self, user_id: int, day: date | None = None) -> StreakResult:
        """Count one completed quiz towards the user's daily streak.

        Finishing a second quiz on the same day keeps the streak where it is,
        so the incentive is to come back tomorrow rather than to grind today.
        """
        day = day or datetime.now(SINGAPORE_TIME).date()
        with self._lock, self._connection:
            row = self._connection.execute(
                "SELECT current_streak, longest_streak, last_quiz_day FROM users "
                "WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            current = row["current_streak"] if row else 0
            longest = row["longest_streak"] if row else 0
            last_day = _parse_day(row["last_quiz_day"]) if row else None

            counted = last_day != day
            if last_day == day:
                pass
            elif last_day == day - timedelta(days=1):
                current += 1
            else:
                current = 1
            longest = max(longest, current)

            now = _now_text()
            self._connection.execute(
                """
                INSERT INTO users (
                    user_id, first_seen_at, last_seen_at,
                    current_streak, longest_streak, last_quiz_day
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    last_seen_at = excluded.last_seen_at,
                    current_streak = excluded.current_streak,
                    longest_streak = excluded.longest_streak,
                    last_quiz_day = excluded.last_quiz_day
                """,
                (user_id, now, now, current, longest, day.isoformat()),
            )
        return StreakResult(
            current_streak=current, longest_streak=longest, counted_today=counted
        )

    # ----------------------------------------------------------------- stats

    def user_stats(self, user_id: int) -> UserStats:
        """Collect the counters shown by /stats."""
        with self._lock:
            checks = self._connection.execute(
                "SELECT COUNT(*) AS total FROM checks WHERE user_id = ?", (user_id,)
            ).fetchone()["total"]
            verdicts = self._connection.execute(
                "SELECT verdict, COUNT(*) AS total FROM checks "
                "WHERE user_id = ? AND verdict IS NOT NULL GROUP BY verdict "
                "ORDER BY total DESC",
                (user_id,),
            ).fetchall()
            quizzes = self._connection.execute(
                "SELECT COUNT(*) AS total FROM quiz_sessions "
                "WHERE user_id = ? AND status = 'completed'",
                (user_id,),
            ).fetchone()["total"]
            answers = self._connection.execute(
                "SELECT COUNT(*) AS total, "
                "COALESCE(SUM(is_correct), 0) AS correct "
                "FROM quiz_answers WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            user = self._connection.execute(
                "SELECT current_streak, longest_streak FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()

        return UserStats(
            checks=checks,
            verdict_counts={row["verdict"]: row["total"] for row in verdicts},
            technique_counts=self.technique_counts(user_id),
            quizzes_completed=quizzes,
            questions_answered=answers["total"],
            correct_answers=answers["correct"],
            current_streak=user["current_streak"] if user else 0,
            longest_streak=user["longest_streak"] if user else 0,
        )


def _now_text() -> str:
    return _timestamp_text(datetime.now(timezone.utc))


def _timestamp_text(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _parse_day(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return datetime.now(timezone.utc)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _check_from_row(row: sqlite3.Row) -> StoredCheck:
    try:
        sources = tuple(json.loads(row["sources_json"]))
    except (TypeError, ValueError):
        sources = ()
    return StoredCheck(
        id=row["id"],
        user_id=row["user_id"],
        input_text=row["input_text"],
        message_kind=row["message_kind"],
        primary_url=row["primary_url"],
        verdict=row["verdict"],
        confidence=row["confidence"],
        explanation=row["explanation"],
        technique=row["technique"],
        sources=sources,
        created_at=_parse_timestamp(row["created_at"]),
    )


def _question_from_row(row: sqlite3.Row) -> StoredQuestion:
    return StoredQuestion(
        id=row["id"],
        session_id=row["session_id"],
        user_id=row["user_id"],
        chat_id=row["chat_id"],
        position=row["position"],
        question=row["question"],
        options=tuple(json.loads(row["options_json"])),
        correct_option_id=row["correct_option_id"],
        explanation=row["explanation"],
        technique=row["technique"],
        origin=row["origin"],
        answered=bool(row["answered"]),
    )
