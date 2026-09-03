"""Cluster recurring false claims and scams, then dump a simulated harm brief.

This is an on-demand read of the local SQLite store: no GPT call, no live write
on every check. The brief is meant to look like something you would hand to
ScamShield, so it carries counts and wording, not Telegram identities.
"""

from __future__ import annotations

import os
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from html import escape
from pathlib import Path
from typing import Sequence
from urllib.parse import urlparse

from app.claim_terms import claim_terms
from app.literacy import TECHNIQUE_LABELS, Technique
from app.response_formatter import ALERT_VERDICTS
from app.settings import (
    DEFAULT_DATABASE_PATH,
    DEFAULT_ESCALATE_MIN_UNIQUE_USERS,
    DEFAULT_ESCALATE_OUTPUT_DIR,
    DEFAULT_ESCALATE_WINDOW_DAYS,
    load_local_env_file,
)
from app.storage import SINGAPORE_TIME, StoredCheck, TrustLensStore
from app.verdict import Verdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]

HIGH_HARM_TECHNIQUES = frozenset(
    {Technique.SCAM_LINK, Technique.IMPERSONATED_AUTHORITY}
)
JACCARD_THRESHOLD = 0.5
SUBSET_SHARED_TERMS = 3
MIN_TEXT_LENGTH = 12
MIN_SCAM_CONFIDENCE = 40
MIN_OTHER_CONFIDENCE = 70
MAX_VARIANTS = 3
MAX_SOURCES = 5

CANDIDATE_VERDICTS = tuple(
    verdict.value for verdict in (*ALERT_VERDICTS, Verdict.UNVERIFIED)
)


class Priority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    WATCH = "WATCH"


_PRIORITY_ORDER = {
    Priority.CRITICAL: 0,
    Priority.HIGH: 1,
    Priority.WATCH: 2,
}


@dataclass(frozen=True)
class EscalationConfig:
    """Numeric gates for the brief. Defaults match the written policy."""

    window_days: int = DEFAULT_ESCALATE_WINDOW_DAYS
    min_unique_users: int = DEFAULT_ESCALATE_MIN_UNIQUE_USERS
    min_scam_confidence: int = MIN_SCAM_CONFIDENCE
    min_other_confidence: int = MIN_OTHER_CONFIDENCE
    min_text_length: int = MIN_TEXT_LENGTH
    database_path: str = DEFAULT_DATABASE_PATH
    output_dir: str = DEFAULT_ESCALATE_OUTPUT_DIR

    @classmethod
    def from_environment(cls, values: dict[str, str] | None = None) -> EscalationConfig:
        if values is None:
            load_local_env_file()
            values = dict(os.environ)
        return cls(
            window_days=_bounded_int(
                values,
                "TRUSTLENS_ESCALATE_WINDOW_DAYS",
                DEFAULT_ESCALATE_WINDOW_DAYS,
                1,
                365,
            ),
            min_unique_users=_bounded_int(
                values,
                "TRUSTLENS_ESCALATE_MIN_USERS",
                DEFAULT_ESCALATE_MIN_UNIQUE_USERS,
                1,
                100,
            ),
            database_path=values.get("TRUSTLENS_DB_PATH", "").strip()
            or DEFAULT_DATABASE_PATH,
            output_dir=values.get("TRUSTLENS_ESCALATE_DIR", "").strip()
            or DEFAULT_ESCALATE_OUTPUT_DIR,
        )


@dataclass(frozen=True)
class EscalatedCluster:
    """One recurring claim that cleared the spread and harm gates."""

    priority: Priority
    technique: Technique
    unique_users: int
    check_count: int
    first_seen: datetime
    last_seen: datetime
    representative: StoredCheck
    median_confidence: int
    majority_verdict: Verdict
    explanation: str
    sources: tuple[str, ...]
    variants: tuple[str, ...]
    quiz_miss_users: int
    fingerprint: str


def build_escalation_clusters(
    store: TrustLensStore,
    config: EscalationConfig | None = None,
    now: datetime | None = None,
) -> tuple[EscalatedCluster, ...]:
    """Read SQLite, cluster similar claims, and keep those that should be escalated."""
    config = config or EscalationConfig()
    now = _aware(now)
    since = (now - timedelta(days=config.window_days)).astimezone(timezone.utc)
    candidates = [
        check
        for check in store.checks_for_escalation(
            since=since,
            verdicts=CANDIDATE_VERDICTS,
            min_confidence=min(config.min_scam_confidence, config.min_other_confidence),
        )
        if is_eligible(check, config)
    ]
    misses = store.quiz_misses_by_check_id()
    reports = [
        report
        for group in cluster_checks(candidates)
        if (report := _report_cluster(group, misses, config)) is not None
    ]
    reports.sort(
        key=lambda item: (
            _PRIORITY_ORDER[item.priority],
            -item.unique_users,
            item.technique.value,
            item.fingerprint,
        )
    )
    return tuple(reports)


def is_eligible(check: StoredCheck, config: EscalationConfig | None = None) -> bool:
    """Apply verdict, confidence, technique, and text-length gates to one check."""
    config = config or EscalationConfig()
    if len(_collapse(check.input_text)) < config.min_text_length:
        return False
    verdict = _verdict_of(check)
    if verdict is None or verdict in {Verdict.TRUE, Verdict.SATIRE}:
        return False
    technique = _technique_of(check)
    high_harm = technique in HIGH_HARM_TECHNIQUES
    if verdict is Verdict.UNVERIFIED and not high_harm:
        return False
    if verdict not in ALERT_VERDICTS and not (
        verdict is Verdict.UNVERIFIED and high_harm
    ):
        return False
    if check.confidence is None:
        return False
    floor = config.min_scam_confidence if high_harm else config.min_other_confidence
    return check.confidence >= floor


def cluster_checks(checks: Sequence[StoredCheck]) -> list[list[StoredCheck]]:
    """Group checks by technique, then by URL or claim-term similarity."""
    by_technique: dict[str, list[StoredCheck]] = defaultdict(list)
    for check in checks:
        by_technique[check.technique or ""].append(check)
    clusters: list[list[StoredCheck]] = []
    for group in by_technique.values():
        clusters.extend(_cluster_one_technique(group))
    return clusters


def url_cluster_key(url: str | None) -> str | None:
    """Lowercase host + path, ignoring query strings that only tag campaigns."""
    if not url or not url.strip():
        return None
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if not host:
        return None
    path = parsed.path.rstrip("/") or "/"
    return f"{host}{path}"


def render_brief(
    clusters: Sequence[EscalatedCluster],
    config: EscalationConfig | None = None,
    now: datetime | None = None,
) -> str:
    """Render the txt brief. Never includes user, chat, or message identifiers."""
    config = config or EscalationConfig()
    now = _aware(now)
    generated = now.astimezone(SINGAPORE_TIME).strftime("%Y-%m-%d %H:%M SGT")
    lines = [
        "TRUSTLENS ESCALATION BRIEF",
        f"Generated: {generated}",
        f"Window: last {config.window_days} days",
        (
            f"Thresholds: unique_users>={config.min_unique_users}, "
            "False/Misleading (Unverified only for scam_link / impersonated_authority), "
            f"confidence>={config.min_scam_confidence} (scam/impersonation) / "
            f">={config.min_other_confidence} (other)"
        ),
        "",
    ]
    if not clusters:
        lines.append("No clusters met the escalation threshold.")
        return "\n".join(lines) + "\n"

    for index, cluster in enumerate(clusters, start=1):
        lines.extend(_render_cluster(index, cluster))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_escalation_brief(
    store: TrustLensStore,
    config: EscalationConfig | None = None,
    now: datetime | None = None,
    output_dir: Path | str | None = None,
) -> tuple[Path, tuple[EscalatedCluster, ...]]:
    """Build the brief and write it under data/escalations/."""
    config = config or EscalationConfig()
    now = _aware(now)
    clusters = build_escalation_clusters(store, config, now=now)
    directory = _resolve_path(output_dir or config.output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = now.astimezone(SINGAPORE_TIME).strftime("%Y%m%d-%H%M")
    path = directory / f"escalation-{stamp}.txt"
    path.write_text(render_brief(clusters, config, now=now), encoding="utf-8")
    return path, clusters


def format_escalation_summary(
    path: Path,
    clusters: Sequence[EscalatedCluster],
    window_days: int = DEFAULT_ESCALATE_WINDOW_DAYS,
) -> str:
    """Short Telegram reply: counts and the file path, no claim text."""
    if not clusters:
        return (
            "No recurring scams or false claims met the escalation threshold "
            f"in the last {window_days} days."
        )
    counts = {priority: 0 for priority in Priority}
    lines = [
        f"Escalated <b>{len(clusters)}</b> recurring cluster(s) to a harm brief.",
        "",
    ]
    for cluster in clusters:
        counts[cluster.priority] += 1
        noun = "user" if cluster.unique_users == 1 else "users"
        lines.append(
            f"• {cluster.priority.value} · {TECHNIQUE_LABELS[cluster.technique]} — "
            f"<b>{cluster.unique_users}</b> unique {noun} reported"
        )
    lines.extend(
        [
            "",
            (
                f"CRITICAL {counts[Priority.CRITICAL]} · "
                f"HIGH {counts[Priority.HIGH]} · "
                f"WATCH {counts[Priority.WATCH]}"
            ),
            "",
            f"<code>{escape(str(path))}</code>",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    load_local_env_file()
    config = EscalationConfig.from_environment()
    store = TrustLensStore(_resolve_path(config.database_path))
    try:
        path, clusters = write_escalation_brief(store, config)
        if clusters:
            print(f"Wrote {len(clusters)} cluster(s) to {path}")
        else:
            print(f"No clusters met the threshold. Empty brief written to {path}")
    finally:
        store.close()


def _report_cluster(
    checks: Sequence[StoredCheck],
    misses: dict[int, tuple[int, ...]],
    config: EscalationConfig,
) -> EscalatedCluster | None:
    unique_users = {check.user_id for check in checks}
    if len(unique_users) < config.min_unique_users:
        return None

    technique = _technique_of(checks[0])
    miss_users: set[int] = set()
    for check in checks:
        miss_users.update(misses.get(check.id, ()))
    quiz_miss_users = len(miss_users)

    majority = _majority_verdict(checks)
    high_harm = technique in HIGH_HARM_TECHNIQUES
    alert_majority = majority in ALERT_VERDICTS
    quiz_boost = quiz_miss_users >= 2
    if not (high_harm or alert_majority or quiz_boost):
        return None

    if high_harm:
        priority = Priority.CRITICAL
    elif quiz_boost or len(unique_users) >= 3:
        priority = Priority.HIGH
    else:
        priority = Priority.WATCH

    representative = _representative(checks)
    confidences = [check.confidence for check in checks if check.confidence is not None]
    return EscalatedCluster(
        priority=priority,
        technique=technique,
        unique_users=len(unique_users),
        check_count=len(checks),
        first_seen=min(check.created_at for check in checks),
        last_seen=max(check.created_at for check in checks),
        representative=representative,
        median_confidence=int(statistics.median(confidences)) if confidences else 0,
        majority_verdict=majority,
        explanation=_collapse(representative.explanation or ""),
        sources=_source_urls(checks),
        variants=_variants(checks, representative),
        quiz_miss_users=quiz_miss_users,
        fingerprint=_fingerprint(checks, representative),
    )


def _cluster_one_technique(checks: list[StoredCheck]) -> list[list[StoredCheck]]:
    parent = list(range(len(checks)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    url_groups: dict[str, list[int]] = defaultdict(list)
    term_indices: list[int] = []
    for index, check in enumerate(checks):
        key = url_cluster_key(check.primary_url)
        if key:
            url_groups[key].append(index)
        else:
            term_indices.append(index)

    for indices in url_groups.values():
        head = indices[0]
        for other in indices[1:]:
            union(head, other)

    terms = {index: claim_terms(checks[index].input_text) for index in term_indices}
    for position, left in enumerate(term_indices):
        for right in term_indices[position + 1 :]:
            if _terms_similar(terms[left], terms[right]):
                union(left, right)

    buckets: dict[int, list[StoredCheck]] = defaultdict(list)
    for index, check in enumerate(checks):
        buckets[find(index)].append(check)
    return list(buckets.values())


def _terms_similar(left: set[str], right: set[str]) -> bool:
    if not left or not right:
        return False
    shared = len(left & right)
    union = len(left | right)
    jaccard = shared / union
    subset = (left <= right or right <= left) and shared >= SUBSET_SHARED_TERMS
    return jaccard >= JACCARD_THRESHOLD or subset


def _representative(checks: Sequence[StoredCheck]) -> StoredCheck:
    def sort_key(check: StoredCheck) -> tuple[int, int, float]:
        is_false = 0 if check.verdict == Verdict.FALSE.value else 1
        return (is_false, -len(check.input_text), -check.created_at.timestamp())

    return min(checks, key=sort_key)


def _majority_verdict(checks: Sequence[StoredCheck]) -> Verdict:
    counts: dict[Verdict, int] = defaultdict(int)
    for check in checks:
        verdict = _verdict_of(check)
        if verdict is not None:
            counts[verdict] += 1
    if not counts:
        return Verdict.UNVERIFIED
    preference = (
        Verdict.FALSE,
        Verdict.MISLEADING,
        Verdict.UNVERIFIED,
        Verdict.SATIRE,
        Verdict.TRUE,
    )
    return max(counts, key=lambda verdict: (counts[verdict], -preference.index(verdict)))


def _source_urls(checks: Sequence[StoredCheck]) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    representative_first = [_representative(checks), *checks]
    for check in representative_first:
        for source in check.sources:
            url = str(source.get("url") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            ordered.append(url)
            if len(ordered) >= MAX_SOURCES:
                return tuple(ordered)
    return tuple(ordered)


def _variants(
    checks: Sequence[StoredCheck], representative: StoredCheck
) -> tuple[str, ...]:
    primary = _collapse(representative.input_text)
    unique: list[str] = []
    seen = {primary.lower()}
    for check in sorted(checks, key=lambda item: -len(item.input_text)):
        text = _collapse(check.input_text)
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(text)
        if len(unique) >= MAX_VARIANTS:
            break
    return tuple(unique)


def _fingerprint(checks: Sequence[StoredCheck], representative: StoredCheck) -> str:
    url_keys = [
        key
        for check in checks
        if (key := url_cluster_key(check.primary_url)) is not None
    ]
    if url_keys:
        return max(set(url_keys), key=url_keys.count)
    terms = sorted(claim_terms(representative.input_text))
    return "|".join(terms) if terms else _collapse(representative.input_text).lower()


def _render_cluster(index: int, cluster: EscalatedCluster) -> list[str]:
    label = TECHNIQUE_LABELS[cluster.technique]
    first = _format_when(cluster.first_seen)
    last = _format_when(cluster.last_seen)
    lines = [
        "================================================================",
        (
            f"CLUSTER {index}  |  PRIORITY: {cluster.priority.value}  |  "
            f"technique: {label}"
        ),
        "----------------------------------------------------------------",
        f"Fingerprint: {cluster.fingerprint}",
        f"Unique users: {cluster.unique_users}",
        f"Checks: {cluster.check_count}",
        f"First seen: {first}  |  Last seen: {last}",
        "Representative claim:",
        f"  {_collapse(cluster.representative.input_text)}",
        (
            f"Bot verdict: {cluster.majority_verdict.value} "
            f"(median confidence {cluster.median_confidence}%)"
        ),
        f"Why it is harmful: {label}",
    ]
    if cluster.explanation:
        lines.extend(["Explanation:", f"  {cluster.explanation}"])
    if cluster.sources:
        lines.append("Cited sources:")
        lines.extend(f"  - {url}" for url in cluster.sources)
    if cluster.variants:
        lines.append(f"Sample variants ({len(cluster.variants)}):")
        lines.extend(f"  - {text}" for text in cluster.variants)
    if cluster.quiz_miss_users:
        noun = "user" if cluster.quiz_miss_users == 1 else "users"
        lines.append(
            f"Quiz: {cluster.quiz_miss_users} {noun} failed to recall this was "
            f"{cluster.majority_verdict.value}"
        )
    lines.append("================================================================")
    return lines


def _verdict_of(check: StoredCheck) -> Verdict | None:
    try:
        return Verdict(check.verdict) if check.verdict else None
    except ValueError:
        return None


def _technique_of(check: StoredCheck) -> Technique:
    try:
        return Technique(check.technique) if check.technique else Technique.MISSING_SOURCE
    except ValueError:
        return Technique.MISSING_SOURCE


def _collapse(text: str) -> str:
    return " ".join((text or "").split())


def _format_when(value: datetime) -> str:
    return _aware(value).astimezone(SINGAPORE_TIME).strftime("%Y-%m-%d %H:%M SGT")


def _aware(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(SINGAPORE_TIME)
    if value.tzinfo is None:
        return value.replace(tzinfo=SINGAPORE_TIME)
    return value


def _resolve_path(configured: Path | str) -> Path:
    path = Path(configured).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def _bounded_int(
    values: dict[str, str], name: str, default: int, minimum: int, maximum: int
) -> int:
    raw = values.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(minimum, min(int(raw), maximum))
    except ValueError:
        return default


if __name__ == "__main__":
    main()
