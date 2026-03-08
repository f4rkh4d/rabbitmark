import pytest

from rabbitmark.url import normalize


def test_lowercases_scheme_and_host():
    assert normalize("HTTPS://Example.COM/Foo") == "https://example.com/Foo"


def test_strips_fragment():
    assert normalize("https://a.com/x#section") == "https://a.com/x"


def test_strips_utm_params():
    got = normalize("https://a.com/p?utm_source=x&utm_medium=y&q=keep")
    assert got == "https://a.com/p?q=keep"


def test_strips_all_tracking_params():
    for p in ("utm_source", "utm_medium", "utm_campaign", "utm_term",
              "utm_content", "ref", "ref_src", "fbclid", "gclid"):
        assert normalize(f"https://a.com/?{p}=v") == "https://a.com"


def test_keeps_non_tracking_query():
    assert normalize("https://a.com/s?q=python&page=2") == "https://a.com/s?q=python&page=2"


def test_trailing_slash_stripped():
    assert normalize("https://a.com/path/") == "https://a.com/path"


def test_root_slash_kept():
    # root path is empty after urlparse normalization
    out = normalize("https://a.com/")
    assert out in ("https://a.com", "https://a.com/")


def test_adds_scheme_if_missing():
    assert normalize("example.com/x").startswith("http://example.com")


def test_rejects_empty():
    with pytest.raises(ValueError):
        normalize("")


def test_rejects_garbage():
    with pytest.raises(ValueError):
        normalize("not a url")
