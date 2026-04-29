from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .ideas import Idea
from .models import Cluster


def render_markdown(clusters: list[Cluster], ideas_by_topic: dict[str, list[Idea]]) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    lines: list[str] = [
        f"# GenAI Watch - {today}",
        "",
        "Automatic summary of recent signals and ideas to explore.",
        "",
        "## Strong Trends",
        "",
    ]

    for idx, cluster in enumerate(clusters, start=1):
        sources = sorted({signal.source for signal in cluster.signals})
        lines.extend([
            f"### {idx}. {cluster.topic}",
            "",
            f"Trend score: **{cluster.score}**",
            f"Sources: {', '.join(sources)}",
            f"Keywords: {', '.join(cluster.keywords[:6])}",
            "",
            "Signals:",
        ])
        for signal in cluster.signals[:5]:
            lines.append(f"- [{signal.title}]({signal.url}) - {signal.source}, score {signal.score}")
        lines.extend(["", "Ideas to explore:", ""])
        for idea in ideas_by_topic.get(cluster.topic, []):
            lines.extend([
                f"#### {idea.title}",
                "",
                f"Problem: {idea.problem}",
                f"Audience: {idea.audience}",
                f"Why now: {idea.why_now}",
                f"7-day MVP: {idea.mvp}",
                f"Difficulty: {idea.difficulty}",
                f"Business potential: {idea.business_potential}",
                f"Risks: {idea.risks}",
                f"Differentiator: {idea.differentiator}",
                "",
            ])
    if not clusters:
        lines.extend([
            "No recent signal was found. Check network connectivity or broaden the configured sources.",
            "",
        ])
    return "\n".join(lines)


def write_newsletter(markdown: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"newsletter-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}.md"
    path.write_text(markdown, encoding="utf-8")
    return path
