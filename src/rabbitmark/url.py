"""url normalization. strips tracking params, lowercases scheme/host, trims fragment."""
from __future__ import annotations

from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "ref",
    "ref_src",
    "fbclid",
    "gclid",
}


def normalize(url: str) -> str:
    url = (url or "").strip()
    if not url:
        raise ValueError("empty url")
    # add scheme if missing so urlparse gives us a netloc
    if "://" not in url:
        url = "http://" + url

    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError(f"bad url: {url!r}")

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # query: drop tracking params, keep order of the rest
    kept = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k.lower() not in TRACKING_PARAMS]
    query = urlencode(kept)

    path = parsed.path or ""
    # trim trailing slash. drop "/" entirely when there's no query/params
    if path == "/" and not query and not parsed.params:
        path = ""
    elif len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    # rudimentary host sanity: must contain a dot or be localhost
    if "." not in netloc and netloc not in {"localhost"}:
        raise ValueError(f"bad url: {url!r}")

    # fragment gone
    return urlunparse((scheme, netloc, path, parsed.params, query, ""))
