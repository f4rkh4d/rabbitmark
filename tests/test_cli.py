from click.testing import CliRunner

from rabbitmark.cli import main


def _run(args, db, input=None):
    runner = CliRunner()
    return runner.invoke(main, ["--db", str(db)] + args, input=input)


def test_add_and_ls(tmp_path):
    db = tmp_path / "t.sqlite3"
    r = _run(["add", "https://example.com/?utm_source=x",
              "--note", "test", "--thread", "sample",
              "--no-fetch"], db)
    assert r.exit_code == 0, r.output
    assert "saved" in r.output

    r = _run(["ls"], db)
    assert r.exit_code == 0
    assert "sample" in r.output
    assert "example.com" in r.output


def test_ls_filter_by_thread(tmp_path):
    db = tmp_path / "t.sqlite3"
    _run(["add", "https://a.com/1", "-n", "n", "-T", "one", "--no-fetch"], db)
    _run(["add", "https://a.com/2", "-n", "n", "-T", "two", "--no-fetch"], db)
    r = _run(["ls", "--thread", "one"], db)
    assert "one" in r.output
    assert "two" not in r.output


def test_search(tmp_path):
    db = tmp_path / "t.sqlite3"
    _run(["add", "https://a.com/1", "-n", "postgres mvcc", "-T", "db", "--no-fetch"], db)
    _run(["add", "https://a.com/2", "-n", "rust async", "-T", "rust", "--no-fetch"], db)
    r = _run(["search", "postgres"], db)
    assert "a.com/1" in r.output
    assert "a.com/2" not in r.output


def test_threads_and_rm(tmp_path):
    db = tmp_path / "t.sqlite3"
    _run(["add", "https://a.com/1", "-n", "n", "-T", "one", "--no-fetch"], db)
    _run(["add", "https://a.com/2", "-n", "n", "-T", "one", "--no-fetch"], db)
    r = _run(["threads"], db)
    assert "one" in r.output and "2" in r.output
    r = _run(["rm", "1"], db)
    assert r.exit_code == 0


def test_add_requires_note_prompt(tmp_path):
    db = tmp_path / "t.sqlite3"
    # no note flag, empty prompt -> error
    r = _run(["add", "https://a.com", "-T", "t", "--no-fetch"], db, input="\n")
    assert r.exit_code != 0


def test_export_json(tmp_path):
    db = tmp_path / "t.sqlite3"
    _run(["add", "https://a.com/1", "-n", "n", "-T", "t", "--no-fetch"], db)
    r = _run(["export", "--format", "json"], db)
    assert r.exit_code == 0
    assert "a.com/1" in r.output


def test_bad_url(tmp_path):
    db = tmp_path / "t.sqlite3"
    r = _run(["add", "", "-n", "n", "-T", "t", "--no-fetch"], db)
    assert r.exit_code != 0
