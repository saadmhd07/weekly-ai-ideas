from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: str | None) -> datetime:
    if not value:
        return utc_now()
    value = value.strip()
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except ValueError:
        pass
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).astimezone(timezone.utc)
        except ValueError:
            continue
    return utc_now()


@dataclass(slots=True)
class Signal:
    source: str
    title: str
    url: str
    text: str = ""
    published_at: datetime = field(default_factory=utc_now)
    author: str = ""
    score: float = 0.0
    comments: int = 0
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    keep: bool = True
    quality: str = "medium"
    value_note: str = ""
    idea_hint: str = ""

    @property
    def fingerprint(self) -> str:
        normalized = " ".join(self.title.lower().split())
        return f"{self.source}:{self.url or normalized}"


@dataclass(slots=True)
class Cluster:
    topic: str
    signals: list[Signal]
    score: float
    keywords: list[str]
