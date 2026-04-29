from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_KEYWORDS = [
    "genai", "generative ai", "llm", "large language model", "ai agent", "agentic",
    "rag", "retrieval augmented", "multimodal", "local llm", "synthetic data",
    "ai coding", "voice agent", "computer use", "workflow automation",
]


@dataclass(slots=True)
class AppConfig:
    database_path: Path = Path("data/newsletter.db")
    output_dir: Path = Path("output")
    keywords: list[str] = field(default_factory=lambda: DEFAULT_KEYWORDS.copy())
    source_weights: dict[str, float] = field(default_factory=lambda: {
        "hackernews": 1.1,
        "arxiv": 1.0,
        "github": 1.25,
        "reddit": 1.0,
        "rss": 1.0,
    })
    reddit_subreddits: list[str] = field(default_factory=lambda: [
        "LocalLLaMA", "MachineLearning", "OpenAI", "SaaS", "Entrepreneur",
    ])
    rss_feeds: list[str] = field(default_factory=lambda: [
        "https://openai.com/news/rss.xml",
        "https://www.anthropic.com/news/rss.xml",
        "https://huggingface.co/blog/feed.xml",
    ])


def load_config(path: str | Path | None = None) -> AppConfig:
    if not path:
        default = Path("config.json")
        path = default if default.exists() else None
    if not path:
        return AppConfig()

    payload: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    config = AppConfig()
    for key, value in payload.items():
        if key in {"database_path", "output_dir"}:
            setattr(config, key, Path(value))
        elif hasattr(config, key):
            setattr(config, key, value)
    return config
