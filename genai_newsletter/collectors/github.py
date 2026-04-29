from __future__ import annotations

from datetime import datetime, timedelta, timezone

from genai_newsletter.collectors.base import Collector
from genai_newsletter.http import HttpClient
from genai_newsletter.models import Signal, parse_datetime


class GitHubCollector(Collector):
    name = "github"

    def __init__(self, client: HttpClient):
        self.client = client

    def collect(self, limit: int) -> list[Signal]:
        since = (datetime.now(timezone.utc) - timedelta(days=365)).date().isoformat()
        queries = [
            f"llm in:name,description stars:>20 pushed:>{since}",
            f"ai-agent in:name,description stars:>20 pushed:>{since}",
            f"generative-ai in:name,description stars:>20 pushed:>{since}",
            f"rag in:name,description stars:>20 pushed:>{since}",
        ]
        per_query = max(3, limit // len(queries))
        seen: set[str] = set()
        signals: list[Signal] = []
        for query in queries:
            payload = self.client.get_json("https://api.github.com/search/repositories", {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": min(per_query, 100),
            })
            for repo in payload.get("items", []):
                url = repo.get("html_url") or ""
                if not url or url in seen:
                    continue
                seen.add(url)
                topics = repo.get("topics") or []
                signals.append(Signal(
                    source=self.name,
                    title=repo.get("full_name") or repo.get("name") or "",
                    url=url,
                    text=repo.get("description") or "",
                    published_at=parse_datetime(repo.get("pushed_at") or repo.get("updated_at")),
                    author=(repo.get("owner") or {}).get("login", ""),
                    score=float(repo.get("stargazers_count") or 0),
                    comments=int(repo.get("open_issues_count") or 0),
                    tags=list(topics),
                    metadata={"language": repo.get("language"), "forks": repo.get("forks_count"), "query": query},
                ))
        return [signal for signal in signals if signal.title and signal.url][:limit]
