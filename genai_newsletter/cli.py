from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from .collectors.arxiv import ArxivCollector
from .collectors.github import GitHubCollector
from .collectors.hackernews import HackerNewsCollector
from .collectors.reddit import RedditCollector
from .collectors.rss import RssCollector
from .config import AppConfig, load_config
from .emailer import latest_output, send_markdown_email
from .env import load_dotenv
from .http import HttpClient
from .ideabox import build_ideabox
from .ideas import generate_ideas
from .pipeline import cluster_signals, enrich_signals, is_genai_relevant
from .render import render_markdown, write_newsletter
from .storage import SignalStore


@dataclass(slots=True)
class CollectResult:
    fetched: int
    inserted: int
    errors: list[str]


def build_collectors(config: AppConfig) -> list:
    client = HttpClient()
    return [
        HackerNewsCollector(client, config.keywords),
        ArxivCollector(client, config.keywords),
        GitHubCollector(client),
        RedditCollector(client, config.reddit_subreddits),
        RssCollector(client, config.rss_feeds),
    ]


def collect(config: AppConfig, limit: int) -> CollectResult:
    store = SignalStore(config.database_path)
    fetched = 0
    inserted = 0
    errors: list[str] = []
    try:
        for collector in build_collectors(config):
            try:
                signals = collector.collect(limit)
                signals = [signal for signal in signals if is_genai_relevant(signal)]
                signals = enrich_signals(signals, config.keywords, config.source_weights)
                fetched += len(signals)
                inserted += store.upsert_many(signals)
                print(f"{collector.name}: {len(signals)} signals, {inserted} new cumulative")
            except Exception as exc:
                errors.append(f"{collector.name}: {exc}")
                print(f"{collector.name}: error - {exc}", file=sys.stderr)
    finally:
        store.close()
    return CollectResult(fetched=fetched, inserted=inserted, errors=errors)


def newsletter(config: AppConfig, days: int, use_openai: bool) -> str:
    store = SignalStore(config.database_path)
    try:
        signals = enrich_signals(store.recent(days=days), config.keywords, config.source_weights)
    finally:
        store.close()
    clusters = cluster_signals(signals)
    ideas = generate_ideas(clusters, use_openai=use_openai)
    markdown = render_markdown(clusters, ideas)
    path = write_newsletter(markdown, config.output_dir)
    print(f"Newsletter written: {path}")
    return str(path)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Collect GenAI trends and generate an ideas newsletter.")
    parser.add_argument("--config", help="Path to config.json")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect", help="Collect and store signals")
    collect_parser.add_argument("--limit", type=int, default=30, help="Maximum items per source")

    newsletter_parser = subparsers.add_parser("newsletter", help="Generate a newsletter from the local database")
    newsletter_parser.add_argument("--days", type=int, default=7, help="Recent signal window")
    newsletter_parser.add_argument("--use-openai", action="store_true", help="Use OpenAI if OPENAI_API_KEY is set")

    ideabox_parser = subparsers.add_parser("ideabox", help="Generate GenAI side-project ideas with OpenAI")
    ideabox_parser.add_argument("--days", type=int, default=7, help="Recent signal window")
    ideabox_parser.add_argument("--max-signals", type=int, default=120, help="Maximum inspiration signals sent to the LLM")
    ideabox_parser.add_argument("--model", help="OpenAI model to use, defaults to OPENAI_MODEL or gpt-5.2")
    ideabox_parser.add_argument("--timeout", type=int, default=360, help="OpenAI timeout in seconds")
    ideabox_parser.add_argument("--max-output-tokens", type=int, default=4000, help="Maximum OpenAI output token budget")
    ideabox_parser.add_argument("--focused", action="store_true", help="Disable wide mode and send rawer signals")

    enrich_parser = subparsers.add_parser("enrich", help="Recompute editorial notes for stored signals")
    enrich_parser.add_argument("--days", type=int, default=30, help="Signal window to re-enrich")

    send_parser = subparsers.add_parser("send", help="Email a generated Markdown file")
    send_parser.add_argument("--file", help="Markdown file to send. Defaults to the latest output/ideabox-*.md")
    send_parser.add_argument("--subject", help="Email subject")

    weekly_parser = subparsers.add_parser("weekly", help="Collect, generate ideabox, then email it")
    weekly_parser.add_argument("--limit", type=int, default=80, help="Maximum items per source")
    weekly_parser.add_argument("--days", type=int, default=7, help="Recent signal window")
    weekly_parser.add_argument("--max-signals", type=int, default=120, help="Maximum inspiration signals")
    weekly_parser.add_argument("--timeout", type=int, default=360, help="OpenAI timeout in seconds")
    weekly_parser.add_argument("--max-output-tokens", type=int, default=4000, help="Maximum OpenAI output token budget")
    weekly_parser.add_argument("--subject", help="Email subject")

    run_parser = subparsers.add_parser("run", help="Collect and generate the newsletter")
    run_parser.add_argument("--limit", type=int, default=30, help="Maximum items per source")
    run_parser.add_argument("--days", type=int, default=7, help="Recent signal window")
    run_parser.add_argument("--use-openai", action="store_true", help="Use OpenAI if OPENAI_API_KEY is set")

    args = parser.parse_args(argv)
    config = load_config(args.config)

    if args.command == "collect":
        result = collect(config, args.limit)
        print(f"Collection complete: {result.fetched} fetched, {result.inserted} new, {len(result.errors)} errors")
        return 0 if result.fetched else 1
    if args.command == "newsletter":
        newsletter(config, args.days, args.use_openai)
        return 0
    if args.command == "ideabox":
        store = SignalStore(config.database_path)
        try:
            signals = enrich_signals(store.recent(days=args.days, keep_only=True), config.keywords, config.source_weights)
        finally:
            store.close()
        try:
            result = build_ideabox(
                signals,
                config.output_dir,
                model=args.model,
                max_signals=args.max_signals,
                timeout=args.timeout,
                max_output_tokens=args.max_output_tokens,
                wide=not args.focused,
            )
            path = result.path
        except RuntimeError as exc:
            print(f"ideabox: {exc}", file=sys.stderr)
            return 1
        print(f"Idea box written: {path}")
        print(f"Summary: {result.selected_count} signals processed, estimated input ≈ {result.estimated_input_tokens} tokens")
        return 0
    if args.command == "enrich":
        store = SignalStore(config.database_path)
        try:
            signals = enrich_signals(store.recent(days=args.days, limit=2000), config.keywords, config.source_weights)
            updated = store.upsert_many(signals)
        finally:
            store.close()
        print(f"Enrichment complete: {len(signals)} signals recalculated, {updated} rows updated")
        return 0
    if args.command == "send":
        try:
            path = Path(args.file) if args.file else latest_output(output_dir=config.output_dir)
            send_markdown_email(path, subject=args.subject)
        except RuntimeError as exc:
            print(f"send: {exc}", file=sys.stderr)
            return 1
        print(f"Email sent: {path}")
        return 0
    if args.command == "weekly":
        result = collect(config, args.limit)
        store = SignalStore(config.database_path)
        try:
            signals = enrich_signals(store.recent(days=args.days, keep_only=True), config.keywords, config.source_weights)
        finally:
            store.close()
        try:
            ideabox_result = build_ideabox(
                signals,
                config.output_dir,
                max_signals=args.max_signals,
                timeout=args.timeout,
                max_output_tokens=args.max_output_tokens,
                wide=True,
            )
            send_markdown_email(ideabox_result.path, subject=args.subject)
        except RuntimeError as exc:
            print(f"weekly: {exc}", file=sys.stderr)
            return 1
        print(f"Weekly complete: {result.fetched} signals fetched, email sent: {ideabox_result.path}")
        return 0
    if args.command == "run":
        result = collect(config, args.limit)
        newsletter(config, args.days, args.use_openai)
        print(f"Run complete: {result.fetched} fetched, {result.inserted} new, {len(result.errors)} errors")
        return 0 if result.fetched else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
