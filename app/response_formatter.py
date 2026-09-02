"""Present existing fact-check results clearly in Telegram's text format."""

from html import escape

from app.verdict import FactCheckResult, Verdict

VERDICT_SYMBOLS = {
    Verdict.TRUE: "✅",
    Verdict.FALSE: "❌",
    Verdict.MISLEADING: "⚠️",
    Verdict.SATIRE: "🎭",
    Verdict.UNVERIFIED: "🔎",
}

ALERT_VERDICTS = {Verdict.FALSE, Verdict.MISLEADING}


def confidence_label(confidence: int) -> str:
    """Translate the existing percentage into a simple display-only label."""
    if confidence >= 70:
        return "High"
    if confidence >= 40:
        return "Moderate"
    return "Low"


def format_fact_check_for_telegram(result: FactCheckResult) -> str:
    """Render Layout A normally and Layout C for false or misleading claims."""
    if result.verdict in ALERT_VERDICTS:
        return _format_alert_layout(result)
    return _format_calm_layout(result)


def _format_calm_layout(result: FactCheckResult) -> str:
    """Layout A: a calm, clearly separated result for non-alert verdicts."""
    return "\n".join(
        [
            f"{VERDICT_SYMBOLS[result.verdict]} <b>VERDICT: {result.verdict.value.upper()}</b>",
            "",
            f"<b>Confidence:</b> {confidence_label(result.confidence)} ({result.confidence}%)",
            "",
            "<b>What this means</b>",
            escape(result.explanation.strip()),
            _format_sources(result),
        ]
    )


def _format_alert_layout(result: FactCheckResult) -> str:
    """Layout C: a stronger visual warning for false or misleading claims."""
    return "\n".join(
        [
            "━━━━━━━━━━━━━━",
            f"{VERDICT_SYMBOLS[result.verdict]} <b>{result.verdict.value.upper()}</b>",
            f"<b>Confidence: {confidence_label(result.confidence).upper()} ({result.confidence}%)</b>",
            "━━━━━━━━━━━━━━",
            "",
            "<b>Please read this carefully:</b>",
            escape(result.explanation.strip()),
            _format_sources(result),
        ]
    )


def _format_sources(result: FactCheckResult) -> str:
    """Make source titles readable links while escaping untrusted search text."""
    if not result.sources:
        return ""

    lines = ["", "<b>Sources</b>"]
    for source in result.sources:
        title = escape(source.title.strip() or source.domain)
        url = escape(source.url, quote=True)
        lines.append(f'🔗 <a href="{url}">{title}</a>')
    return "\n".join(lines)
