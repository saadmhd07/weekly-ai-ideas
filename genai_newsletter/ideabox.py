from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import Signal
from .pipeline import cluster_signals

DEFAULT_PROFILE = {
    "goal": "Trouver 5 idées de side projects GenAI buildables, fun, éventuellement vendables.",
    "inspiration": "Ambiance GitHub Trending, Product Hunt, indie hackers, devtools, micro-SaaS.",
    "preferred_ideas": [
        "outil que je peux coder seul ou à deux",
        "MVP visible en 2 à 10 jours",
        "repo open-source possible avec README sexy",
        "peut commencer gratuit puis devenir payant",
        "utile à des devs, freelances, PM, petites équipes ou ops",
        "pas trop enterprise, pas trop spécifique à une stack interne",
    ],
    "avoid": [
        "gros produit compliance enterprise",
        "idées R&D trop académiques",
        "wrappers ChatGPT évidents",
        "idées nécessitant une équipe sales dès le départ",
        "idées tellement verticales qu'elles ne parlent à presque personne",
    ],
    "tone": "Synthétique, direct, sélectif, orienté action.",
}

IDEABOX_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "headline": {"type": "string"},
        "tldr": {"type": "array", "minItems": 3, "maxItems": 4, "items": {"type": "string"}},
        "ship_this_week": {"$ref": "#/$defs/ship_pick"},
        "ideas": {"type": "array", "minItems": 5, "maxItems": 5, "items": {"$ref": "#/$defs/idea"}},
        "skip": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"$ref": "#/$defs/skip_item"}},
    },
    "required": ["headline", "tldr", "ship_this_week", "ideas", "skip"],
    "$defs": {
        "ship_pick": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string"},
                "why": {"type": "string"},
                "first_step": {"type": "string"},
            },
            "required": ["name", "why", "first_step"],
        },
        "idea": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string"},
                "category": {"type": "string"},
                "one_liner": {"type": "string"},
                "why_it_matters": {"type": "string"},
                "mvp": {"type": "string"},
                "distribution": {"type": "string"},
                "monetization": {"type": "string"},
                "score": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["name", "category", "one_liner", "why_it_matters", "mvp", "distribution", "monetization", "score"],
        },
        "skip_item": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "idea": {"type": "string"},
                "why_skip": {"type": "string"},
            },
            "required": ["idea", "why_skip"],
        },
    },
}


@dataclass(slots=True)
class IdeaBoxSettings:
    model: str
    max_signals: int
    timeout: int
    max_output_tokens: int
    wide: bool
    profile: dict[str, Any]


@dataclass(slots=True)
class IdeaBoxResult:
    path: Path
    model: str
    selected_count: int
    estimated_input_tokens: int
    usage: dict[str, Any]
    payload: dict[str, Any]


def build_ideabox(
    signals: list[Signal],
    output_dir: Path,
    model: str | None = None,
    max_signals: int = 120,
    timeout: int = 360,
    max_output_tokens: int = 4000,
    wide: bool = True,
) -> IdeaBoxResult:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY est requis pour la commande ideabox.")

    selected = select_signals(signals, max_signals=max_signals)
    if not selected:
        raise RuntimeError("Aucun signal exploitable. Lance d'abord la collecte ou élargis la fenêtre --days.")

    settings = IdeaBoxSettings(
        model=model or os.getenv("OPENAI_MODEL", "gpt-5.2"),
        max_signals=max_signals,
        timeout=timeout,
        max_output_tokens=max_output_tokens,
        wide=wide,
        profile=DEFAULT_PROFILE,
    )
    input_text = build_wide_input(selected) if settings.wide else build_input(selected)
    estimated_input_tokens = estimate_tokens(build_instructions(settings.profile) + input_text)
    print(
        "ideabox: appel OpenAI "
        f"mode={'wide' if settings.wide else 'focused'}, model={settings.model}, signaux={len(selected)}, "
        f"input≈{estimated_input_tokens} tokens, max_output={settings.max_output_tokens}, "
        f"timeout={settings.timeout}s",
        flush=True,
    )
    payload, usage = call_openai_ideabox(input_text, settings)
    print(f"ideabox: réponse OpenAI reçue, usage={format_usage(usage)}", flush=True)
    markdown = render_ideabox(payload, selected, settings.model, usage)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"ideabox-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}.md"
    path.write_text(markdown, encoding="utf-8")
    return IdeaBoxResult(path=path, model=settings.model, selected_count=len(selected), estimated_input_tokens=estimated_input_tokens, usage=usage, payload=payload)


def select_signals(signals: list[Signal], max_signals: int) -> list[Signal]:
    clusters = cluster_signals(signals, max_clusters=18)
    selected: list[Signal] = []
    seen: set[str] = set()
    per_cluster = max(3, min(8, max_signals // max(1, len(clusters))))
    for cluster in clusters:
        for signal in cluster.signals[:per_cluster]:
            key = signal.url or signal.title.lower()
            if key in seen:
                continue
            selected.append(signal)
            seen.add(key)
            if len(selected) >= max_signals:
                return selected
    return selected


def call_openai_ideabox(input_text: str, settings: IdeaBoxSettings) -> tuple[dict[str, Any], dict[str, Any]]:
    body = json.dumps({
        "model": settings.model,
        "instructions": build_instructions(settings.profile),
        "input": input_text,
        "max_output_tokens": settings.max_output_tokens,
        "text": {"format": {"type": "json_schema", "name": "genai_short_side_project_radar", "schema": IDEABOX_SCHEMA, "strict": True}},
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.timeout) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API error {exc.code}: {detail}") from exc
    except (TimeoutError, socket.timeout) as exc:
        raise RuntimeError(f"OpenAI timeout après {settings.timeout}s. Augmente --timeout ou réduis --max-signals.") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Erreur réseau OpenAI: {exc}") from exc

    text = extract_response_text(response_payload)
    if not text:
        raise RuntimeError(f"Réponse OpenAI vide ou non textuelle. usage={response_payload.get('usage', {})}")
    try:
        return json.loads(text), response_payload.get("usage", {})
    except json.JSONDecodeError as exc:
        usage = response_payload.get("usage", {})
        preview_path = Path("output") / "openai-partial-response.json.txt"
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path.write_text(text, encoding="utf-8")
        raise RuntimeError(
            "Réponse OpenAI JSON incomplète ou invalide. "
            f"usage={format_usage(usage)}. Réponse partielle sauvegardée dans {preview_path}. "
            "Relance avec --max-output-tokens 6000."
        ) from exc


def build_instructions(profile: dict[str, Any]) -> str:
    return (
        "Tu es un curateur de side projects GenAI façon GitHub Trending + indie hacker. "
        "Ton livrable est une newsletter COURTE que quelqu'un lit en moins de 3 minutes. "
        "Sois brutalement sélectif: exactement 5 idées, pas plus. "
        "Chaque idée doit tenir en quelques lignes: one-liner, pourquoi c'est intéressant, MVP, distribution, monétisation. "
        "Priorise les idées codables seul ou à deux, publiables sur GitHub/Product Hunt/HN/Reddit, et potentiellement vendables. "
        "Les signaux sont un moodboard: combine les thèmes, n'overfit pas à un repo précis. "
        "Évite les projets enterprise lourds, consulting, R&D abstraite, ou wrappers ChatGPT génériques. "
        "Écris en français, direct, sans remplissage. Profil: "
        + json.dumps(profile, ensure_ascii=False)
    )


def build_wide_input(signals: list[Signal]) -> str:
    cards = build_inspiration_cards(signals)
    return (
        "Mode WIDE: cartes d'inspiration compressées depuis beaucoup de signaux GenAI. "
        "Génère une newsletter courte: TL;DR, 1 projet à shipper cette semaine, 5 idées maximum, 2 idées à éviter. "
        "Utilise les cartes comme moodboard pour produire des idées larges, simples et actionnables. Cartes: "
        + json.dumps(cards, ensure_ascii=False)
    )


def build_inspiration_cards(signals: list[Signal]) -> list[dict[str, Any]]:
    clusters = cluster_signals(signals, max_clusters=18)
    cards: list[dict[str, Any]] = []
    for cluster in clusters:
        sources = sorted({signal.source for signal in cluster.signals})
        titles = [signal.title for signal in cluster.signals[:4]]
        cards.append({
            "theme": cluster.topic,
            "keywords": cluster.keywords[:6],
            "market_spark": summarize_cluster_spark(cluster.topic),
            "project_angles": project_angles_for_topic(cluster.topic),
            "sources": sources,
            "example_signals": titles,
        })
    return cards


def summarize_cluster_spark(topic: str) -> str:
    if topic == "AI agents":
        return "Agents autour de CLI, navigateur, workflows et automatisation."
    if topic == "RAG & knowledge bases":
        return "Contexte fiable, recherche personnelle, docs vivantes et ingestion simple."
    if topic == "AI coding":
        return "Petits devtools autour de review, migration, docs, tests, onboarding."
    if topic == "Local LLMs":
        return "Privacy, coût, offline, apps desktop et wrappers Ollama."
    if topic == "Multimodal AI":
        return "PDF, image, audio et vidéo transformés en outils de productivité."
    return "Espace de petits outils GenAI à explorer."


def project_angles_for_topic(topic: str) -> list[str]:
    mapping = {
        "AI agents": ["CLI", "browser extension", "workflow bot", "template repo"],
        "RAG & knowledge bases": ["personal search", "PDF chat", "bookmark brain", "docs generator"],
        "AI coding": ["VS Code extension", "GitHub Action", "CLI", "test generator"],
        "Local LLMs": ["desktop app", "privacy-first tool", "Ollama wrapper", "benchmark harness"],
        "Multimodal AI": ["PDF/image tool", "meeting assistant", "screenshot parser", "OCR workflow"],
    }
    return mapping.get(topic, ["CLI", "mini-SaaS", "open-source tool", "browser extension"])


def build_input(signals: list[Signal]) -> str:
    compact = []
    for signal in signals:
        compact.append({
            "source": signal.source,
            "title": signal.title,
            "url": signal.url,
            "text": signal.text[:300],
            "tags": signal.tags[:5],
            "idea_hint": signal.idea_hint,
        })
    return (
        "Voici des signaux GenAI. Génère une newsletter courte avec exactement 5 idées de side projects. Signaux: "
        + json.dumps(compact, ensure_ascii=False)
    )


def extract_response_text(payload: dict[str, Any]) -> str:
    if payload.get("output_text"):
        return payload["output_text"]
    chunks: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                chunks.append(content.get("text", ""))
    return "".join(chunks)


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def format_usage(usage: dict[str, Any]) -> str:
    if not usage:
        return "non disponible"
    return f"input={usage.get('input_tokens', '?')}, output={usage.get('output_tokens', '?')}, total={usage.get('total_tokens', '?')}"


def render_ideabox(payload: dict[str, Any], signals: list[Signal], model: str, usage: dict[str, Any]) -> str:
    lines: list[str] = [
        f"# {payload['headline']}",
        "",
        f"Généré le {datetime.now().strftime('%Y-%m-%d %H:%M')} avec `{model}`.",
        f"Usage OpenAI: {format_usage(usage)}.",
        "",
        "## TL;DR",
        "",
    ]
    for item in payload["tldr"]:
        lines.append(f"- {item}")
    ship = payload["ship_this_week"]
    lines.extend([
        "",
        "## À Shipper Cette Semaine",
        "",
        f"### {ship['name']}",
        "",
        f"Pourquoi: {ship['why']}",
        f"Premier pas: {ship['first_step']}",
        "",
        "## 5 Idées",
        "",
    ])
    for idx, idea in enumerate(payload["ideas"], start=1):
        lines.extend([
            f"### {idx}. {idea['name']} ({idea['score']}/10)",
            "",
            f"Catégorie: {idea['category']}",
            f"Pitch: {idea['one_liner']}",
            f"Pourquoi: {idea['why_it_matters']}",
            f"MVP: {idea['mvp']}",
            f"Distribution: {idea['distribution']}",
            f"Monétisation: {idea['monetization']}",
            "",
        ])
    lines.extend(["## À Éviter", ""])
    for item in payload["skip"]:
        lines.extend([f"- {item['idea']}: {item['why_skip']}"])
    lines.extend(["", "## Signaux Clés", ""])
    for signal in signals[:8]:
        lines.append(f"- [{signal.title}]({signal.url}) - {signal.source}")
    lines.append("")
    return "\n".join(lines)
