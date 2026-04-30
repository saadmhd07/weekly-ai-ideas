from __future__ import annotations

import xml.etree.ElementTree as ET

from genai_newsletter.collectors.base import Collector
from genai_newsletter.http import HttpClient
from genai_newsletter.models import Signal, parse_datetime


class RssCollector(Collector):
    name = "rss"

    def __init__(self, client: HttpClient, feeds: list[str]):
        self.client = client
        self.feeds = feeds

    def collect(self, limit: int) -> list[Signal]:
        signals: list[Signal] = []
        per_feed = max(1, limit // max(1, len(self.feeds)))
        for feed in self.feeds:
            try:
                xml = self.client.get_text(feed)
                root = ET.fromstring(xml)
            except Exception:
                continue
            channel_items = root.findall(".//item")[:per_feed]
            atom_entries = root.findall("{http://www.w3.org/2005/Atom}entry")[:per_feed]
            for item in channel_items:
                signals.append(self._from_rss_item(item, feed))
            for entry in atom_entries:
                signals.append(self._from_atom_entry(entry, feed))
        return [signal for signal in signals if signal.title and signal.url][:limit]

    def _from_rss_item(self, item: ET.Element, feed: str) -> Signal:
        title = item.findtext("title", default="").strip()
        link = item.findtext("link", default="").strip()
        description = item.findtext("description", default="").strip()
        return Signal(
            source=self._source_for_feed(feed),
            title=title,
            url=link,
            text=description,
            published_at=parse_datetime(item.findtext("pubDate", default="")),
            metadata={"feed": feed},
        )

    def _from_atom_entry(self, entry: ET.Element, feed: str) -> Signal:
        ns = {"a": "http://www.w3.org/2005/Atom"}
        link = ""
        for link_node in entry.findall("a:link", ns):
            rel = link_node.attrib.get("rel", "alternate")
            if rel == "alternate" or not link:
                link = link_node.attrib.get("href", link)
        return Signal(
            source=self._source_for_feed(feed),
            title=entry.findtext("a:title", default="", namespaces=ns).strip(),
            url=link,
            text=(entry.findtext("a:summary", default="", namespaces=ns) or entry.findtext("a:content", default="", namespaces=ns)).strip(),
            published_at=parse_datetime(entry.findtext("a:updated", default="", namespaces=ns)),
            metadata={"feed": feed},
        )

    def _source_for_feed(self, feed: str) -> str:
        return "reddit_rss" if "reddit.com/r/" in feed else self.name
