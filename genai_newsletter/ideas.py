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
            title=f"Operational radar for {topic}",
            problem=f"Teams see many signals around {keyword}, but struggle to decide what to test concretely.",
            audience="SaaS founders, innovation teams, and B2B product managers.",
            why_now=f"The cluster aggregates {len(cluster.signals)} recent signals with a score of {cluster.score}.",
            mvp="Collect 5 sources, summarize changes, and send a Slack/email digest with 3 actionable recommendations.",
            difficulty="Medium",
            business_potential="Good if scoped to a specific business function with recurring budget.",
            risks="Noise risk if scoring remains too generic.",
            differentiator="Move from generic monitoring to recommendations prioritized by business context.",
        ),
        Idea(
            title=f"Specialized {topic} workflow assistant",
            problem="Generic tools require too much setup and produce answers that are poorly adapted to real workflows.",
            audience="SMBs and ops teams that want to automate a recurring process.",
            why_now="Signals show enough technical maturity to verticalize the use case.",
            mvp="Pick one workflow, connect the useful documents, and generate a verifiable output with human validation.",
            difficulty="Medium to high",
            business_potential="High if time saved can be measured in hours per week.",
            risks="Depends on internal data access and quality guardrails.",
            differentiator="A narrow, measurable scope integrated into existing tools.",
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
        "You are a GenAI product analyst. Generate exactly 2 ideas per topic. "
        "Respond as JSON: {topic: [{title, problem, audience, why_now, mvp, difficulty, "
        "business_potential, risks, differentiator}]}. Signals: " + json.dumps(compact, ensure_ascii=False)
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
