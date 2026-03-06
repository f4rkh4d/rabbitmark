"""rabbitmark cli entry points."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import click
from rich.console import Console

from . import __version__
from .export import export as do_export
from .fetch import fetch_title
from .render import render_threads, render_tree
from .store import Store
from .url import normalize

DEFAULT_DB = Path.home() / ".rabbitmark" / "db.sqlite3"


def _store(ctx: click.Context) -> Store:
    path = ctx.obj["db_path"]
    return Store(path)


@click.group(help="bookmarks that remember why you saved them.")
@click.option("--db", type=click.Path(dir_okay=False), default=None,
              help="path to db (default ~/.rabbitmark/db.sqlite3).")
@click.version_option(__version__, prog_name="rabbitmark")
@click.pass_context
def main(ctx: click.Context, db: str | None) -> None:
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = Path(db) if db else DEFAULT_DB


@main.command("add", help="save a url to a thread with a note.")
@click.argument("url")
@click.option("--note", "-n", default=None, help="why are you saving this?")
@click.option("--thread", "-T", required=True, help="rabbit-hole name.")
@click.option("--tag", "-t", "tags", multiple=True, help="tag (repeatable).")
@click.option("--title", default=None, help="override fetched title.")
@click.option("--no-fetch", is_flag=True, help="skip title fetch.")
@click.pass_context
def cmd_add(ctx: click.Context, url: str, note: str | None, thread: str,
            tags: tuple[str, ...], title: str | None, no_fetch: bool) -> None:
    console = Console()
    try:
        norm = normalize(url)
    except ValueError as e:
        console.print(f"[red]bad url:[/red] {e}")
        sys.exit(2)

    if not note:
        note = click.prompt("note (why?)", default="", show_default=False)
    if not note.strip():
        console.print("[red]note is required.[/red]")
        sys.exit(2)

    resolved_title = title
    if not resolved_title and not no_fetch:
        resolved_title = fetch_title(norm)
    if not resolved_title:
        resolved_title = norm

    store = _store(ctx)
    try:
        bid = store.add(url=norm, title=resolved_title, note=note,
                        thread=thread, tags=list(tags))
        console.print(f"[#6ba07e]saved[/#6ba07e] [dim]#{bid}[/dim] {resolved_title}")
    except Exception as e:  # typically unique constraint
        msg = str(e).lower()
        if "unique" in msg:
            console.print("[yellow]already saved.[/yellow]")
            sys.exit(1)
        console.print(f"[red]error:[/red] {e}")
        sys.exit(1)
    finally:
        store.close()


@main.command("ls", help="list bookmarks as a tree.")
@click.option("--thread", "-T", default=None)
@click.option("--tag", "-t", default=None)
@click.pass_context
def cmd_ls(ctx: click.Context, thread: str | None, tag: str | None) -> None:
    store = _store(ctx)
    try:
        items = store.list(thread=thread, tag=tag)
        render_tree(items)
    finally:
        store.close()


@main.command("search", help="full-text search across url, title, note.")
@click.argument("query")
@click.pass_context
def cmd_search(ctx: click.Context, query: str) -> None:
    store = _store(ctx)
    try:
        items = store.search(query)
        render_tree(items)
    finally:
        store.close()


@main.command("threads", help="list threads with bookmark counts.")
@click.pass_context
def cmd_threads(ctx: click.Context) -> None:
    store = _store(ctx)
    try:
        render_threads(store.threads())
    finally:
        store.close()


@main.command("rm", help="remove a bookmark by id.")
@click.argument("bid", type=int)
@click.pass_context
def cmd_rm(ctx: click.Context, bid: int) -> None:
    store = _store(ctx)
    try:
        ok = store.delete(bid)
        if not ok:
            click.echo(f"no bookmark with id {bid}", err=True)
            sys.exit(1)
        click.echo(f"removed {bid}")
    finally:
        store.close()


EDIT_TEMPLATE = """# edit this bookmark. lines starting with # are ignored.
url: {url}
title: {title}
thread: {thread}
tags: {tags}
note: |
{note}
"""


def _parse_edit(text: str) -> dict:
    out: dict = {}
    note_lines: list[str] = []
    in_note = False
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        if in_note:
            if line.startswith("  "):
                note_lines.append(line[2:])
                continue
            in_note = False
        if line.startswith("note:"):
            rest = line[5:].strip()
            if rest == "|":
                in_note = True
            else:
                out["note"] = rest
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            key = k.strip().lower()
            val = v.strip()
            if key in {"url", "title", "thread"}:
                out[key] = val
            elif key == "tags":
                out["tags"] = [t.strip() for t in val.split(",") if t.strip()]
    if note_lines:
        out["note"] = "\n".join(note_lines).rstrip()
    return out


@main.command("edit", help="open $EDITOR on a bookmark.")
@click.argument("bid", type=int)
@click.pass_context
def cmd_edit(ctx: click.Context, bid: int) -> None:
    store = _store(ctx)
    try:
        bm = store.get(bid)
        if not bm:
            click.echo(f"no bookmark with id {bid}", err=True)
            sys.exit(1)
        note_block = "\n".join(f"  {ln}" for ln in bm.note.splitlines()) or "  "
        body = EDIT_TEMPLATE.format(
            url=bm.url, title=bm.title, thread=bm.thread,
            tags=", ".join(bm.tags), note=note_block,
        )
        editor = os.environ.get("EDITOR", "vi")
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            f.write(body)
            tmp = f.name
        try:
            subprocess.call([editor, tmp])
            with open(tmp, "r", encoding="utf-8") as f:
                new = _parse_edit(f.read())
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        if not new:
            click.echo("no changes.")
            return
        url = new.get("url")
        if url:
            try:
                url = normalize(url)
            except ValueError:
                click.echo("bad url, aborting.", err=True)
                sys.exit(2)
        store.update(
            bid,
            url=url,
            title=new.get("title"),
            note=new.get("note"),
            thread=new.get("thread"),
            tags=new.get("tags"),
        )
        click.echo(f"updated {bid}")
    finally:
        store.close()


@main.command("export", help="dump all bookmarks to stdout.")
@click.option("--format", "fmt", type=click.Choice(["json", "csv", "html"]), default="json")
@click.pass_context
def cmd_export(ctx: click.Context, fmt: str) -> None:
    store = _store(ctx)
    try:
        items = store.list()
        click.echo(do_export(items, fmt), nl=False)
    finally:
        store.close()


if __name__ == "__main__":
    main()
