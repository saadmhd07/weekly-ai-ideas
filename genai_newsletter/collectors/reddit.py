from __future__ import annotations

from datetime import datetime, timezone

from genai_newsletter.collectors.base import Collector
from genai_newsletter.http import HttpClient
from genai_newsletter.models import Signal


class RedditCollector(Collector):
    name = "reddit"

    def __init__(self, client: HttpClient, subreddits: list[str]):
        self.client = client
        self.subreddits = subreddits

    def collect(self, limit: int) -> list[Signal]:
        per_subreddit = max(5, limit // max(1, len(self.subreddits)))
        signals: list[Signal] = []
        for subreddit in self.subreddits:
            payload = self.client.get_json(f"https://www.reddit.com/r/{subreddit}/hot.json", {"limit": per_subreddit})
            for child in payload.get("data", {}).get("children", []):
                data = child.get("data", {})
                title = data.get("title") or ""
                if not title or data.get("stickied"):
                    continue
                created = datetime.fromtimestamp(float(data.get("created_utc") or 0), tz=timezone.utc)
                signals.append(Signal(
                    source=self.name,
                    title=title,
                    url="https://www.reddit.com" + data.get("permalink", ""),
                    text=data.get("selftext") or "",
                    published_at=created,
                    author=data.get("author") or "",
                    score=float(data.get("score") or 0),
                    comments=int(data.get("num_comments") or 0),
                    tags=[subreddit],
                    metadata={"subreddit": subreddit},
                ))
        return signals[:limit]
