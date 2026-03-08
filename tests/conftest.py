import pytest

from rabbitmark.store import Store


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "db.sqlite3")
    yield s
    s.close()
