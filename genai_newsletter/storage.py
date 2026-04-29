from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .models import Signal, parse_datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    text TEXT NOT NULL,
    published_at TEXT NOT NULL,
    author TEXT NOT NULL,
    score REAL NOT NULL,
    comments INTEGER NOT NULL,
    tags TEXT NOT NULL,
    metadata TEXT NOT NULL,
    keep INTEGER NOT NULL DEFAULT 1,
    quality TEXT NOT NULL DEFAULT 'medium',
    value_note TEXT NOT NULL DEFAULT '',
    idea_hint TEXT NOT NULL DEFAULT '',
    inserted_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_signals_published_at ON signals(published_at);
CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source);

"""

SIGNAL_MIGRATIONS = {
    "keep": "ALTER TABLE signals ADD COLUMN keep INTEGER NOT NULL DEFAULT 1",
    "quality": "ALTER TABLE signals ADD COLUMN quality TEXT NOT NULL DEFAULT 'medium'",
    "value_note": "ALTER TABLE signals ADD COLUMN value_note TEXT NOT NULL DEFAULT ''",
    "idea_hint": "ALTER TABLE signals ADD COLUMN idea_hint TEXT NOT NULL DEFAULT ''",
}


class SignalStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._migrate()
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def _migrate(self) -> None:
        columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(signals)").fetchall()}
        for column, statement in SIGNAL_MIGRATIONS.items():
            if column not in columns:
                self.conn.execute(statement)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_keep ON signals(keep)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_signals_quality ON signals(quality)")

    def upsert_many(self, signals: list[Signal]) -> int:
        inserted = 0
        for signal in signals:
            cursor = self.conn.execute(
                """
                INSERT INTO signals
                (fingerprint, source, title, url, text, published_at, author, score, comments, tags, metadata,
                 keep, quality, value_note, idea_hint, inserted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(fingerprint) DO UPDATE SET
                    score = excluded.score,
                    tags = excluded.tags,
                    metadata = excluded.metadata,
                    keep = excluded.keep,
                    quality = excluded.quality,
                    value_note = excluded.value_note,
                    idea_hint = excluded.idea_hint
                """,
                (
                    signal.fingerprint,
                    signal.source,
                    signal.title[:500],
                    signal.url,
                    signal.text,
                    signal.published_at.astimezone(timezone.utc).isoformat(),
                    signal.author,
                    float(signal.score),
                    int(signal.comments),
                    json.dumps(signal.tags, ensure_ascii=False),
                    json.dumps(signal.metadata, ensure_ascii=False),
                    1 if signal.keep else 0,
                    signal.quality,
                    signal.value_note,
                    signal.idea_hint,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            inserted += 1 if cursor.rowcount else 0
        self.conn.commit()
        return inserted

    def recent(self, days: int = 7, limit: int = 500, keep_only: bool = False) -> list[Signal]:
        where = "published_at >= datetime('now', ?)"
        params: list[str | int] = [f"-{days} days"]
        if keep_only:
            where += " AND keep = 1"
        params.append(limit)
        rows = self.conn.execute(
            f"""
            SELECT * FROM signals
            WHERE {where}
            ORDER BY published_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [self._row_to_signal(row) for row in rows]

    def _row_to_signal(self, row: sqlite3.Row) -> Signal:
        return Signal(
            source=row["source"],
            title=row["title"],
            url=row["url"],
            text=row["text"],
            published_at=parse_datetime(row["published_at"]),
            author=row["author"],
            score=row["score"],
            comments=row["comments"],
            tags=json.loads(row["tags"]),
            metadata=json.loads(row["metadata"]),
            keep=bool(row["keep"]),
            quality=row["quality"],
            value_note=row["value_note"],
            idea_hint=row["idea_hint"],
        )

