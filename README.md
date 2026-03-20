# rabbitmark


![demo](docs/hero.gif)
bookmarks were built to be forgotten. this one makes you write down why you saved the link, and which rabbit hole it belongs to.

i kept opening my bookmarks bar and seeing a wall of blue underlines with zero memory of why any of them were there. so i wrote this. every save needs a note and a thread. lists come back as a tree. search actually works (fts5).

## install

```
pip install git+https://github.com/f4rkh4d/rabbitmark
```

needs python 3.10+.

## usage

```
rabbitmark add https://www.postgresql.org/docs/current/mvcc-intro.html \
  --note "postgres mvcc overview — starting point for the isolation rabbit hole" \
  --thread postgres-internals \
  --tag db --tag mvcc
```

if you leave off `--note` it will prompt. `--thread` is required (that's the point).

```
rabbitmark ls                         # tree of everything, newest first
rabbitmark ls --thread postgres-internals
rabbitmark ls --tag mvcc
rabbitmark search "isolation"
rabbitmark threads                    # list threads with counts
rabbitmark edit 3                     # opens $EDITOR on a yaml-ish file
rabbitmark rm 3
rabbitmark export --format json       # also csv, html
```

db lives at `~/.rabbitmark/db.sqlite3`. one file, easy to back up.

## threads vs tags

a thread is the rabbit hole — one per bookmark, like `postgres-internals` or `wasm-runtimes`. tags are facets, you can stack as many as you want (`db`, `mvcc`, `paper`). use threads when you come back to a topic for a week; use tags when you want to slice across threads.

## notes

title fetching is best-effort. 5-second timeout, at most 3 redirects, no fancy parser. if a page is slow or blocks the default ua, you get the url as the title and can fix it with `edit` later. i haven't tested this on windows, probably fine, ask me how i know if it's not.

## license

mit. see LICENSE.
