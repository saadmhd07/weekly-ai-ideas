from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

from .models import Cluster, Signal

STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "are", "you", "your", "into",
    "using", "how", "what", "why", "when", "where", "dans", "pour", "avec", "des", "les",
    "une", "sur", "est", "aux", "par", "plus", "all", "new", "show", "launch", "ask",
    "will", "can", "become", "thing", "past", "fixed", "applications", "application",
}


RELEVANCE_TERMS = {
    "ai", "llm", "gpt", "genai", "generative", "agent", "agents", "agentic",
    "rag", "retrieval", "embedding", "embeddings", "transformer", "neural",
    "model", "models", "openai", "anthropic", "huggingface", "deepseek",
    "llama", "mistral", "diffusion", "multimodal", "eval", "benchmark",
    "inference", "fine-tuning", "finetuning", "prompt", "copilot", "cursor",
}

TOPIC_ALIASES = {
    "agent": "AI agents",
    "agents": "AI agents",
    "agentic": "AI agents",
    "rag": "RAG & knowledge bases",
    "retrieval": "RAG & knowledge bases",
    "coding": "AI coding",
    "code": "AI coding",
    "developer": "AI coding",
    "local": "Local LLMs",
    "llama": "Local LLMs",
    "open-source": "Open-source AI",
    "opensource": "Open-source AI",
    "voice": "Voice agents",
    "audio": "Voice agents",
    "video": "Multimodal AI",
    "image": "Multimodal AI",
    "multimodal": "Multimodal AI",
    "browser": "Computer-use agents",
    "computer": "Computer-use agents",
    "workflow": "Workflow automation",
    "automation": "Workflow automation",
    "data": "Synthetic data & evals",
    "eval": "Synthetic data & evals",
    "benchmark": "Synthetic data & evals",
}


def enrich_signals(signals: list[Signal], keywords: list[str], source_weights: dict[str, float]) -> list[Signal]:
    for signal in signals:
        text = f"{signal.title} {signal.text}".lower()
        inferred = [keyword for keyword in keywords if keyword.lower() in text]
        signal.tags = sorted(set(signal.tags + inferred + extract_keywords(text, max_keywords=6)))
        signal.score = trend_score(signal, source_weights)
        apply_editorial_assessment(signal)
    return signals


def trend_score(signal: Signal, source_weights: dict[str, float]) -> float:
    now = datetime.now(timezone.utc)
    age_hours = max(1.0, (now - signal.published_at).total_seconds() / 3600)
    freshness = 40 / math.sqrt(age_hours)
    engagement = math.log1p(max(signal.score, 0)) * 8 + math.log1p(max(signal.comments, 0)) * 5
    source_weight = source_weights.get(signal.source, 1.0)
    keyword_bonus = min(15, len(signal.tags) * 2)
    return round((freshness + engagement + keyword_bonus) * source_weight, 2)


def cluster_signals(signals: list[Signal], max_clusters: int = 10) -> list[Cluster]:
    buckets: dict[str, list[Signal]] = defaultdict(list)
    for signal in sorted(signals, key=lambda item: item.score, reverse=True):
        topic = infer_topic(signal)
        buckets[topic].append(signal)

    clusters: list[Cluster] = []
    for topic, items in buckets.items():
        score = sum(item.score for item in items) + cross_source_bonus(items)
        keywords = top_keywords(items)
        clusters.append(Cluster(topic=topic, signals=items[:8], score=round(score, 2), keywords=keywords))
    return sorted(clusters, key=lambda cluster: cluster.score, reverse=True)[:max_clusters]


def infer_topic(signal: Signal) -> str:
    tokens = extract_keywords(f"{signal.title} {signal.text} {' '.join(signal.tags)}", max_keywords=12)
    for token in tokens:
        normalized = token.lower().replace("_", "-")
        if normalized in TOPIC_ALIASES:
            return TOPIC_ALIASES[normalized]
    if signal.tags:
        return signal.tags[0].replace("-", " ").title()
    return "Emerging GenAI ideas"


def cross_source_bonus(signals: list[Signal]) -> float:
    return max(0, len({signal.source for signal in signals}) - 1) * 12


def top_keywords(signals: list[Signal], count: int = 8) -> list[str]:
    counter: Counter[str] = Counter()
    for signal in signals:
        counter.update(extract_keywords(f"{signal.title} {signal.text}", max_keywords=20))
        counter.update(signal.tags)
    return [keyword for keyword, _ in counter.most_common(count)]


def extract_keywords(text: str, max_keywords: int = 10) -> list[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text.lower())
    filtered = [token for token in tokens if token not in STOPWORDS and not token.isdigit()]
    return [token for token, _ in Counter(filtered).most_common(max_keywords)]


def is_genai_relevant(signal: Signal) -> bool:
    haystack = f"{signal.title} {signal.text} {' '.join(signal.tags)}".lower()
    tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{1,}", haystack))
    if tokens & RELEVANCE_TERMS:
        return True
    return any(term in haystack for term in ("large language model", "generative ai", "machine learning", "artificial intelligence"))


def apply_editorial_assessment(signal: Signal) -> None:
    text = f"{signal.title} {signal.text}".lower()
    tags = set(signal.tags)
    source_bonus = signal.source in {"github", "arxiv", "rss"}
    concrete_terms = {
        "open-source", "api", "tool", "framework", "benchmark", "dataset", "model", "repo",
        "agent", "agents", "rag", "local", "inference", "automation", "browser", "workflow",
        "security", "eval", "testing", "multimodal", "voice", "document", "enterprise",
    }
    abstract_terms = {"future", "past", "thing", "applications", "will", "should", "could"}
    concrete_hits = len(tags & concrete_terms) + sum(1 for term in concrete_terms if term in text)
    abstract_hits = len(tags & abstract_terms) + sum(1 for term in abstract_terms if term in text)

    if signal.source == "hackernews" and signal.title.lower().startswith("ask hn:") and concrete_hits < 2:
        signal.keep = False
        signal.quality = "low"
        signal.value_note = "Discussion HN abstraite: utile comme contexte, faible comme déclencheur direct d'idée."
        signal.idea_hint = "À garder seulement si plusieurs autres sources confirment le même angle."
        signal.score = round(signal.score * 0.45, 2)
        return

    if concrete_hits >= 3 or source_bonus:
        signal.keep = True
        signal.quality = "high" if concrete_hits >= 4 else "medium"
        signal.value_note = "Signal concret: peut alimenter directement une hypothèse produit ou R&D."
        signal.idea_hint = build_idea_hint(signal)
        return

    if abstract_hits > concrete_hits:
        signal.keep = False
        signal.quality = "low"
        signal.value_note = "Signal trop général: intéressant pour la culture, peu exploitable seul."
        signal.idea_hint = "Chercher un repo, un papier ou un cas d'usage concret avant de l'envoyer au LLM."
        signal.score = round(signal.score * 0.65, 2)
        return

    signal.keep = True
    signal.quality = "medium"
    signal.value_note = "Signal potentiellement utile, à interpréter dans un cluster plutôt que seul."
    signal.idea_hint = build_idea_hint(signal)


def build_idea_hint(signal: Signal) -> str:
    topic = infer_topic(signal)
    if topic == "AI agents":
        return "Explorer un prototype d'agent borné à un workflow métier mesurable."
    if topic == "RAG & knowledge bases":
        return "Tester une base de connaissances verticale avec évaluation qualité intégrée."
    if topic == "AI coding":
        return "Chercher un outil dev qui réduit une friction très précise du cycle delivery."
    if topic == "Local LLMs":
        return "Tester un cas privacy/offline où le local change vraiment l'adoption."
    if topic == "Multimodal AI":
        return "Transformer documents, audio ou vidéo en actions vérifiables, pas juste en résumés."
    return f"Chercher une idée R&D concrète autour de {topic}."
