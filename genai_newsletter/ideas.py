from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass

from .models import Cluster


@dataclass(slots=True)
class Idea:
    title: str
    problem: str
    audience: str
    why_now: str
    mvp: str
    difficulty: str
    business_potential: str
    risks: str
    differentiator: str


def generate_ideas(clusters: list[Cluster], use_openai: bool = False) -> dict[str, list[Idea]]:
    if use_openai and os.getenv("OPENAI_API_KEY"):
        try:
            return _generate_with_openai(clusters)
        except Exception:
            return {cluster.topic: heuristic_ideas(cluster) for cluster in clusters}
    return {cluster.topic: heuristic_ideas(cluster) for cluster in clusters}


def heuristic_ideas(cluster: Cluster) -> list[Idea]:
    topic = cluster.topic
    keyword = cluster.keywords[0] if cluster.keywords else topic.lower()
    return [
        Idea(
            title=f"Radar opérationnel pour {topic}",
            problem=f"Les équipes voient passer des signaux autour de {keyword}, mais n'arrivent pas à décider quoi tester concrètement.",
            audience="Fondateurs SaaS, équipes innovation, product managers B2B.",
            why_now=f"Le cluster agrège {len(cluster.signals)} signaux récents avec un score de {cluster.score}.",
            mvp="Collecter 5 sources, résumer les changements, envoyer un digest Slack/email avec 3 recommandations actionnables.",
            difficulty="Moyenne",
            business_potential="Bon si le périmètre cible un métier précis avec budget récurrent.",
            risks="Risque de bruit si le scoring reste trop générique.",
            differentiator="Passer d'une veille générique à des recommandations priorisées par contexte métier.",
        ),
        Idea(
            title=f"Assistant métier spécialisé {topic}",
            problem="Les outils généralistes demandent trop de paramétrage et produisent des réponses peu adaptées au workflow réel.",
            audience="PME et équipes ops qui veulent automatiser un processus récurrent.",
            why_now="Les signaux montrent une maturité technique suffisante pour verticaliser le cas d'usage.",
            mvp="Choisir un workflow unique, connecter les documents utiles, générer une sortie vérifiable avec validation humaine.",
            difficulty="Moyenne à élevée",
            business_potential="Élevé si le gain de temps est mesurable en heures par semaine.",
            risks="Dépendance aux données internes et besoin de garde-fous qualité.",
            differentiator="Un périmètre étroit, mesurable, avec intégration dans les outils existants.",
        ),
    ]


def _generate_with_openai(clusters: list[Cluster]) -> dict[str, list[Idea]]:
    model = os.getenv("OPENAI_MODEL", "gpt-5.2")
    prompt = _build_prompt(clusters)
    body = json.dumps({
        "model": model,
        "input": prompt,
        "text": {"format": {"type": "json_object"}},
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    text = _extract_response_text(payload)
    decoded = json.loads(text)
    result: dict[str, list[Idea]] = {}
    for topic, items in decoded.items():
        result[topic] = [Idea(**item) for item in items]
    return result


def _build_prompt(clusters: list[Cluster]) -> str:
    compact = []
    for cluster in clusters:
        compact.append({
            "topic": cluster.topic,
            "score": cluster.score,
            "keywords": cluster.keywords,
            "signals": [
                {"title": signal.title, "source": signal.source, "score": signal.score, "url": signal.url}
                for signal in cluster.signals[:5]
            ],
        })
    return (
        "Tu es un analyste produit GenAI. Génère exactement 2 idées par topic. "
        "Réponds en JSON: {topic: [{title, problem, audience, why_now, mvp, difficulty, "
        "business_potential, risks, differentiator}]}. Signaux: " + json.dumps(compact, ensure_ascii=False)
    )


def _extract_response_text(payload: dict) -> str:
    if "output_text" in payload:
        return payload["output_text"]
    chunks: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                chunks.append(content.get("text", ""))
    return "".join(chunks)
