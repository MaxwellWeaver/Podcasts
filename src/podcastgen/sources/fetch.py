"""Article body extraction. Fetches a URL and runs trafilatura to clean it."""

from __future__ import annotations

import httpx
import trafilatura

from podcastgen.util.logging import get_logger

log = get_logger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 "
        "podcastgen/0.1 (personal, non-commercial)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def extract_article(url: str, *, timeout: float = 15.0) -> str:
    """Fetch URL and extract main text. Returns "" on failure."""
    try:
        with httpx.Client(
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            r = client.get(url)
            r.raise_for_status()
            html = r.text
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        log.warning("fetch failed for %s: %s", url, e)
        return ""

    text = trafilatura.extract(html, include_comments=False, include_tables=False)
    return (text or "").strip()
