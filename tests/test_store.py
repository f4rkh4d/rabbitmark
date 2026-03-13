import pytest


def _add(store, url="https://a.com/1", note="why", thread="t", tags=("x",), title="t1"):
    return store.add(url=url, title=title, note=note, thread=thread, tags=list(tags))


def test_add_and_get(store):
    bid = _add(store)
    b = store.get(bid)
    assert b is not None
    assert b.url == "https://a.com/1"
    assert b.tags == ["x"]


def test_note_required(store):
    with pytest.raises(ValueError):
        store.add(url="https://a.com", title="t", note="  ", thread="t")


def test_thread_required(store):
    with pytest.raises(ValueError):
        store.add(url="https://a.com", title="t", note="n", thread="")


def test_list_by_thread(store):
    _add(store, url="https://a.com/1", thread="rust")
    _add(store, url="https://a.com/2", thread="go")
    rust = store.list(thread="rust")
    assert len(rust) == 1 and rust[0].thread == "rust"


def test_list_by_tag(store):
    _add(store, url="https://a.com/1", tags=("alpha",))
    _add(store, url="https://a.com/2", tags=("beta",))
    out = store.list(tag="alpha")
    assert len(out) == 1


def test_list_ordered_newest_first(store):
    b1 = store.add(url="https://a.com/1", title="a", note="n", thread="t", added_at=100)
    b2 = store.add(url="https://a.com/2", title="b", note="n", thread="t", added_at=200)
    items = store.list()
    assert items[0].id == b2 and items[1].id == b1


def test_threads_counts(store):
    _add(store, url="https://a.com/1", thread="t1")
    _add(store, url="https://a.com/2", thread="t1")
    _add(store, url="https://a.com/3", thread="t2")
    counts = dict(store.threads())
    assert counts == {"t1": 2, "t2": 1}


def test_search_finds_note(store):
    _add(store, url="https://a.com/1", note="postgres mvcc notes", thread="t")
    _add(store, url="https://a.com/2", note="rust lifetimes", thread="t")
    got = store.search("postgres")
    assert len(got) == 1
    assert "postgres" in got[0].note


def test_search_finds_title(store):
    store.add(url="https://a.com/1", title="deep dive into kafka", note="n", thread="t")
    got = store.search("kafka")
    assert len(got) == 1


def test_delete(store):
    bid = _add(store)
    assert store.delete(bid) is True
    assert store.get(bid) is None


def test_update(store):
    bid = _add(store)
    ok = store.update(bid, note="new note", tags=["y", "z"])
    assert ok
    b = store.get(bid)
    assert b.note == "new note"
    assert set(b.tags) == {"y", "z"}


def test_unique_url(store):
    import sqlite3
    _add(store, url="https://a.com/dup")
    with pytest.raises(sqlite3.IntegrityError):
        _add(store, url="https://a.com/dup")
