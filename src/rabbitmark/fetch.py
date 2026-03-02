"""best-effort title grabber. 5s timeout, a real-ish UA, max 3 redirects."""
from __future__ import annotations

import re
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (compatible; rabbitmark/0.5; +https://frkhd.com/rabbitmark)"
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def fetch_title(url: str, timeout: float = 5.0, max_redirects: int = 3) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
        opener = urllib.request.build_opener(
            urllib.request.HTTPRedirectHandler()
        )
        # urllib's default redirect handler caps at 10; we enforce our own
        redirects = [0]
        original_redirect = urllib.request.HTTPRedirectHandler.redirect_request

        def capped(self, req, fp, code, msg, headers, newurl):
            redirects[0] += 1
            if redirects[0] > max_redirects:
                return None
            return original_redirect(self, req, fp, code, msg, headers, newurl)

        urllib.request.HTTPRedirectHandler.redirect_request = capped  # type: ignore[assignment]
        try:
            with opener.open(req, timeout=timeout) as resp:
                ctype = resp.headers.get("Content-Type", "")
                if "html" not in ctype.lower() and ctype:
                    return None
                raw = resp.read(200_000)
        finally:
            urllib.request.HTTPRedirectHandler.redirect_request = original_redirect  # type: ignore[assignment]

        text = raw.decode("utf-8", errors="replace")
        m = TITLE_RE.search(text)
        if not m:
            return None
        title = re.sub(r"\s+", " ", m.group(1)).strip()
        return title or None
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, ValueError):
        return None
