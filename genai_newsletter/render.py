from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .ideas import Idea
from .models import Cluster


def render_markdown(clusters: list[Cluster], ideas_by_topic: dict[str, list[Idea]]) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    lines: list[str] = [
        f"# Veille GenAI - {today}",
        "",
        "Synthèse automatique des signaux récents et des idées à explorer.",
        "",
        "## Tendances fortes",
        "",
    ]

    for idx, cluster in enumerate(clusters, start=1):
        sources = sorted({signal.source for signal in cluster.signals})
        lines.extend([
            f"### {idx}. {cluster.topic}",
            "",
            f"Score tendance: **{cluster.score}**",
            f"Sources: {', '.join(sources)}",
            f"Mots-clés: {', '.join(cluster.keywords[:6])}",
            "",
            "Signaux:",
        ])
        for signal in cluster.signals[:5]:
            lines.append(f"- [{signal.title}]({signal.url}) - {signal.source}, score {signal.score}")
        lines.extend(["", "Idées à explorer:", ""])
        for idea in ideas_by_topic.get(cluster.topic, []):
            lines.extend([
                f"#### {idea.title}",
                "",
                f"Problème: {idea.problem}",
                f"Cible: {idea.audience}",
                f"Pourquoi maintenant: {idea.why_now}",
                f"MVP 7 jours: {idea.mvp}",
                f"Difficulté: {idea.difficulty}",
                f"Potentiel business: {idea.business_potential}",
                f"Risques: {idea.risks}",
                f"Différenciation: {idea.differentiator}",
                "",
            ])
    if not clusters:
        lines.extend([
            "Aucun signal récent n'a été trouvé. Vérifie la connectivité réseau ou élargis les sources.",
            "",
        ])
    return "\n".join(lines)


def write_newsletter(markdown: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"newsletter-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}.md"
    path.write_text(markdown, encoding="utf-8")
    return path
