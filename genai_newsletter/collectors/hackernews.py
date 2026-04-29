from __future__ import annotations

from genai_newsletter.collectors.base import Collector
from genai_newsletter.http import HttpClient
from genai_newsletter.models import Signal, parse_datetime


class HackerNewsCollector(Collector):
    name = "hackernews"

    def __init__(self, client: HttpClient, keywords: list[str]):
        self.client = client
        self.keywords = keywords

    def collect(self, limit: int) -> list[Signal]:
        queries = ["llm", "ai agent", "generative ai", "rag", "local llm"]
        seen: set[str] = set()
        signals: list[Signal] = []
        per_query = max(3, limit // len(queries))
        for query in queries:
            payload = self.client.get_json(
                "https://hn.algolia.com/api/v1/search_by_date",
                {"query": query, "tags": "story", "hitsPerPage": per_query},
            )
            for hit in payload.get("hits", []):
                title = hit.get("title") or hit.get("story_title") or ""
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                if not title or url in seen:
                    continue
                seen.add(url)
                signals.append(Signal(
                    source=self.name,
                    title=title,
                    url=url,
                    text=hit.get("_highlightResult", {}).get("title", {}).get("value", ""),
                    published_at=parse_datetime(hit.get("created_at")),
                    author=hit.get("author") or "",
                    score=float(hit.get("points") or 0),
                    comments=int(hit.get("num_comments") or 0),
                    metadata={"hn_id": hit.get("objectID"), "query": query},
                ))
        return signals[:limit]
