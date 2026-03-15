import csv
import io
import json

from rabbitmark.export import export, to_csv, to_html, to_json


def _seed(store):
    store.add(url="https://a.com/1", title="first", note="why1", thread="t1",
              tags=["x"], added_at=111)
    store.add(url="https://a.com/2", title="second", note="why2", thread="t2",
              tags=["y", "z"], added_at=222)
    return store.list()


def test_json_roundtrip(store):
    items = _seed(store)
    out = to_json(items)
    data = json.loads(out)
    assert len(data) == 2
    assert {d["url"] for d in data} == {"https://a.com/1", "https://a.com/2"}
    assert any(d["tags"] == ["y", "z"] for d in data)


def test_csv_roundtrip(store):
    items = _seed(store)
    out = to_csv(items)
    reader = csv.DictReader(io.StringIO(out))
    rows = list(reader)
    assert len(rows) == 2
    assert rows[0]["url"].startswith("https://a.com/")


def test_html_contains_urls(store):
    items = _seed(store)
    out = to_html(items)
    assert "<a href=" in out
    assert "https://a.com/1" in out
    assert "t1" in out and "t2" in out


def test_export_dispatcher(store):
    items = _seed(store)
    assert export(items, "json").startswith("[")
    assert "url" in export(items, "csv").splitlines()[0]
    assert "<a href=" in export(items, "html")


def test_export_unknown_format(store):
    import pytest
    with pytest.raises(ValueError):
        export([], "xml")
