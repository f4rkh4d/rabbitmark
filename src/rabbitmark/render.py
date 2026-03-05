"""rich tree view. threads as branches, bookmarks as leaves."""
from __future__ import annotations

from datetime import datetime, timezone

from rich.console import Console
from rich.tree import Tree

from .store import Bookmark

ACCENT = "#6ba07e"  # sage green
WARM = "#d4a354"   # warm beige


def _group(bookmarks: list[Bookmark]) -> dict[str, list[Bookmark]]:
    out: dict[str, list[Bookmark]] = {}
    for b in bookmarks:
        out.setdefault(b.thread, []).append(b)
    return out


def _fmt_date(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def render_tree(bookmarks: list[Bookmark], console: Console | None = None) -> None:
    console = console or Console()
    if not bookmarks:
        console.print("[dim]no bookmarks yet. go down a rabbit hole first.[/dim]")
        return
    root = Tree(f"[bold {ACCENT}]rabbitmark[/bold {ACCENT}]")
    groups = _group(bookmarks)
    # most-recent thread first (by newest bookmark in the thread)
    ordered = sorted(groups.items(),
                     key=lambda kv: max(b.added_at for b in kv[1]),
                     reverse=True)
    for thread, items in ordered:
        branch = root.add(f"[bold {WARM}]{thread}[/bold {WARM}] [dim]({len(items)})[/dim]")
        for b in items:
            title = b.title or b.url
            tagstr = " ".join(f"[dim]#{t}[/dim]" for t in b.tags)
            header = f"[{ACCENT}]{b.id}[/{ACCENT}] {title}"
            if tagstr:
                header += "  " + tagstr
            leaf = branch.add(header)
            leaf.add(f"[dim]{b.url}[/dim]")
            if b.note:
                preview = b.note if len(b.note) <= 120 else b.note[:117] + "..."
                leaf.add(f"[italic dim]{preview}[/italic dim]")
            leaf.add(f"[dim]{_fmt_date(b.added_at)}[/dim]")
    console.print(root)


def render_threads(threads: list[tuple[str, int]], console: Console | None = None) -> None:
    console = console or Console()
    if not threads:
        console.print("[dim]no threads yet.[/dim]")
        return
    for name, count in threads:
        console.print(f"[{WARM}]{name}[/{WARM}] [dim]({count})[/dim]")
