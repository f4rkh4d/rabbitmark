"""export bookmarks to json, csv, or html."""
from __future__ import annotations

import csv
import html
import io
import json
from datetime import datetime, timezone

from .store import Bookmark


def to_json(bookmarks: list[Bookmark]) -> str:
    data = [
        {
            "id": b.id,
            "url": b.url,
            "title": b.title,
            "note": b.note,
            "thread": b.thread,
            "tags": list(b.tags),
            "added_at": b.added_at,
        }
        for b in bookmarks
    ]
    return json.dumps(data, indent=2, ensure_ascii=False)


def to_csv(bookmarks: list[Bookmark]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "url", "title", "note", "thread", "tags", "added_at"])
    for b in bookmarks:
        writer.writerow([
            b.id, b.url, b.title, b.note, b.thread,
            ",".join(b.tags),
            datetime.fromtimestamp(b.added_at, tz=timezone.utc).isoformat(),
        ])
    return buf.getvalue()


def to_html(bookmarks: list[Bookmark]) -> str:
    # netscape-ish bookmark file, grouped by thread
    groups: dict[str, list[Bookmark]] = {}
    for b in bookmarks:
        groups.setdefault(b.thread, []).append(b)
    lines = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        "<meta http-equiv=\"Content-Type\" content=\"text/html; charset=UTF-8\">",
        "<title>rabbitmark export</title>",
        "<h1>rabbitmark</h1>",
        "<dl><p>",
    ]
    for thread, items in groups.items():
        lines.append(f"    <dt><h3>{html.escape(thread)}</h3>")
        lines.append("    <dl><p>")
        for b in items:
            tagstr = ",".join(b.tags)
            lines.append(
                f'        <dt><a href="{html.escape(b.url)}" '
                f'add_date="{b.added_at}" tags="{html.escape(tagstr)}">'
                f'{html.escape(b.title or b.url)}</a>'
            )
            if b.note:
                lines.append(f"        <dd>{html.escape(b.note)}")
        lines.append("    </dl><p>")
    lines.append("</dl><p>")
    return "\n".join(lines) + "\n"


def export(bookmarks: list[Bookmark], fmt: str) -> str:
    fmt = fmt.lower()
    if fmt == "json":
        return to_json(bookmarks)
    if fmt == "csv":
        return to_csv(bookmarks)
    if fmt == "html":
        return to_html(bookmarks)
    raise ValueError(f"unknown format: {fmt}")
