from __future__ import annotations

import xml.etree.ElementTree as ET

from genai_newsletter.collectors.base import Collector
from genai_newsletter.http import HttpClient
from genai_newsletter.models import Signal, parse_datetime

ATOM = {"a": "http://www.w3.org/2005/Atom"}


class ArxivCollector(Collector):
    name = "arxiv"

    def __init__(self, client: HttpClient, keywords: list[str]):
        self.client = client
        self.keywords = keywords

    def collect(self, limit: int) -> list[Signal]:
        query = " OR ".join(f'all:"{keyword}"' for keyword in self.keywords[:6])
        xml = self.client.get_text("https://export.arxiv.org/api/query", {
            "search_query": f"cat:cs.AI OR cat:cs.CL OR cat:cs.LG OR cat:cs.CV OR {query}",
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": limit,
        })
        root = ET.fromstring(xml)
        signals: list[Signal] = []
        for entry in root.findall("a:entry", ATOM):
            title = _text(entry, "a:title")
            url = _text(entry, "a:id")
            summary = _text(entry, "a:summary")
            authors = [node.findtext("a:name", default="", namespaces=ATOM) for node in entry.findall("a:author", ATOM)]
            if title and url:
                signals.append(Signal(
                    source=self.name,
                    title=" ".join(title.split()),
                    url=url,
                    text=" ".join(summary.split()),
                    published_at=parse_datetime(_text(entry, "a:published")),
                    author=", ".join(a for a in authors if a),
                    score=0,
                    comments=0,
                ))
        return signals


def _text(entry: ET.Element, path: str) -> str:
    return entry.findtext(path, default="", namespaces=ATOM).strip()
