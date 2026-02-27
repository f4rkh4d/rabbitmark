"""sqlite storage + fts5. pure logic, pass a path, easy to test."""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    note TEXT NOT NULL,
    thread TEXT NOT NULL,
    added_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS tags (
    bookmark_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (bookmark_id, tag),
    FOREIGN KEY (bookmark_id) REFERENCES bookmarks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_bookmarks_thread ON bookmarks(thread);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
"""

FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS bookmarks_fts USING fts5(
    url, title, note
);
"""


@dataclass
class Bookmark:
    id: int
    url: str
    title: str
    note: str
    thread: str
    added_at: int
    tags: list[str] = field(default_factory=list)


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._has_fts = True
        self._init()

    def _init(self) -> None:
        self.conn.executescript(SCHEMA)
        try:
            self.conn.executescript(FTS_SCHEMA)
        except sqlite3.OperationalError:
            self._has_fts = False
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # ---------- CRUD ----------
    def add(self, url: str, title: str, note: str, thread: str,
            tags: Iterable[str] = (), added_at: int | None = None) -> int:
        if not note.strip():
            raise ValueError("note is required")
        if not thread.strip():
            raise ValueError("thread is required")
        ts = int(added_at if added_at is not None else time.time())
        cur = self.conn.execute(
            "INSERT INTO bookmarks(url, title, note, thread, added_at) VALUES(?,?,?,?,?)",
            (url, title, note, thread, ts),
        )
        bid = cur.lastrowid
        for t in {t.strip().lower() for t in tags if t and t.strip()}:
            self.conn.execute("INSERT OR IGNORE INTO tags(bookmark_id, tag) VALUES(?, ?)", (bid, t))
        if self._has_fts:
            self.conn.execute(
                "INSERT INTO bookmarks_fts(rowid, url, title, note) VALUES(?,?,?,?)",
                (bid, url, title, note),
            )
        self.conn.commit()
        return bid

    def get(self, bid: int) -> Bookmark | None:
        row = self.conn.execute("SELECT * FROM bookmarks WHERE id=?", (bid,)).fetchone()
        if not row:
            return None
        tags = [r["tag"] for r in self.conn.execute(
            "SELECT tag FROM tags WHERE bookmark_id=? ORDER BY tag", (bid,))]
        return _row_to_bookmark(row, tags)

    def update(self, bid: int, *, url: str | None = None, title: str | None = None,
               note: str | None = None, thread: str | None = None,
               tags: Iterable[str] | None = None) -> bool:
        existing = self.get(bid)
        if not existing:
            return False
        new_url = url if url is not None else existing.url
        new_title = title if title is not None else existing.title
        new_note = note if note is not None else existing.note
        new_thread = thread if thread is not None else existing.thread
        self.conn.execute(
            "UPDATE bookmarks SET url=?, title=?, note=?, thread=? WHERE id=?",
            (new_url, new_title, new_note, new_thread, bid),
        )
        if tags is not None:
            self.conn.execute("DELETE FROM tags WHERE bookmark_id=?", (bid,))
            for t in {t.strip().lower() for t in tags if t and t.strip()}:
                self.conn.execute("INSERT OR IGNORE INTO tags(bookmark_id, tag) VALUES(?, ?)", (bid, t))
        if self._has_fts:
            self.conn.execute("DELETE FROM bookmarks_fts WHERE rowid=?", (bid,))
            self.conn.execute(
                "INSERT INTO bookmarks_fts(rowid, url, title, note) VALUES(?,?,?,?)",
                (bid, new_url, new_title, new_note),
            )
        self.conn.commit()
        return True

    def delete(self, bid: int) -> bool:
        cur = self.conn.execute("DELETE FROM bookmarks WHERE id=?", (bid,))
        if self._has_fts:
            self.conn.execute("DELETE FROM bookmarks_fts WHERE rowid=?", (bid,))
        self.conn.commit()
        return cur.rowcount > 0

    # ---------- listing ----------
    def list(self, *, thread: str | None = None, tag: str | None = None) -> list[Bookmark]:
        sql = "SELECT b.* FROM bookmarks b"
        args: list = []
        where = []
        if tag:
            sql += " JOIN tags t ON t.bookmark_id = b.id"
            where.append("t.tag = ?")
            args.append(tag.lower())
        if thread:
            where.append("b.thread = ?")
            args.append(thread)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY b.added_at DESC, b.id DESC"
        rows = self.conn.execute(sql, args).fetchall()
        return [self._hydrate(r) for r in rows]

    def threads(self) -> list[tuple[str, int]]:
        rows = self.conn.execute(
            "SELECT thread, COUNT(*) c FROM bookmarks GROUP BY thread ORDER BY c DESC, thread"
        ).fetchall()
        return [(r["thread"], r["c"]) for r in rows]

    def search(self, query: str) -> list[Bookmark]:
        q = (query or "").strip()
        if not q:
            return []
        if self._has_fts:
            try:
                rows = self.conn.execute(
                    "SELECT b.* FROM bookmarks b JOIN bookmarks_fts f ON f.rowid = b.id "
                    "WHERE bookmarks_fts MATCH ? ORDER BY b.added_at DESC",
                    (q,),
                ).fetchall()
                return [self._hydrate(r) for r in rows]
            except sqlite3.OperationalError:
                pass
        # fallback LIKE search
        like = f"%{q}%"
        rows = self.conn.execute(
            "SELECT * FROM bookmarks WHERE url LIKE ? OR title LIKE ? OR note LIKE ? "
            "ORDER BY added_at DESC",
            (like, like, like),
        ).fetchall()
        return [self._hydrate(r) for r in rows]

    def _hydrate(self, row: sqlite3.Row) -> Bookmark:
        tags = [r["tag"] for r in self.conn.execute(
            "SELECT tag FROM tags WHERE bookmark_id=? ORDER BY tag", (row["id"],))]
        return _row_to_bookmark(row, tags)


def _row_to_bookmark(row: sqlite3.Row, tags: list[str]) -> Bookmark:
    return Bookmark(
        id=row["id"],
        url=row["url"],
        title=row["title"],
        note=row["note"],
        thread=row["thread"],
        added_at=row["added_at"],
        tags=tags,
    )
