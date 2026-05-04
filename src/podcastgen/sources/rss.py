"""RSS source intake. Pulls items from configured feeds via feedparser."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import feedparser

from podcastgen.util.logging import get_logger

log = get_logger(__name__)


@dataclass
class SourceItem:
    url: str
    title: str
    summary: str           # short summary from the feed (may be empty)
    body: str = ""         # filled later by fetch.extract_article()
    published: str = ""    # ISO datetime string, "" if unknown
    source_name: str = ""  # human label of the feed
    category: str = ""     # geopolitics | defense | tech | security | lab | research | ...
    weight: float = 1.0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "summary": self.summary,
            "body": self.body,
            "published": self.published,
            "source_name": self.source_name,
            "category": self.category,
            "weight": self.weight,
            "extra": self.extra,
        }


def gather_from_sources(
    sources: list[dict[str, Any]],
    *,
    max_age_days: int | None = None,
) -> list[SourceItem]:
    """Pull items from each configured feed. Optionally filter by max_age_days."""
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=max_age_days)
        if max_age_days is not None
        else None
    )
    out: list[SourceItem] = []
    for src in sources:
        log.info("fetching feed: %s", src["name"])
        try:
            parsed = feedparser.parse(src["url"])
        except Exception as e:  # noqa: BLE001 — feedparser surface is broad
            log.warning("feedparser failed for %s: %s", src["name"], e)
            continue

        if parsed.bozo and not parsed.entries:
            log.warning("feed bozo with no entries: %s (%s)", src["name"], parsed.bozo_exception)
            continue

        cap = src.get("max_items_per_run", 10)
        added = 0
        for entry in parsed.entries:
            if added >= cap:
                break
            published = _entry_datetime(entry)
            if cutoff is not None and published is not None and published < cutoff:
                continue
            url = (entry.get("link") or "").strip()
            if not url:
                continue
            out.append(
                SourceItem(
                    url=url,
                    title=entry.get("title", "").strip(),
                    summary=_clean_summary(entry.get("summary", "") or entry.get("description", "")),
                    published=published.isoformat() if published else "",
                    source_name=src["name"],
                    category=src.get("category", ""),
                    weight=float(src.get("weight", 1.0)),
                )
            )
            added += 1
    log.info("gathered %d items from %d sources", len(out), len(sources))
    return out


def _entry_datetime(entry: Any) -> datetime | None:
    for k in ("published_parsed", "updated_parsed"):
        v = entry.get(k)
        if v:
            try:
                return datetime(*v[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
    return None


def _clean_summary(text: str) -> str:
    """Strip HTML tags from summary fields."""
    if not text:
        return ""
    # Cheap tag stripper — feedparser already handles most encoding.
    import re
    return re.sub(r"<[^>]+>", " ", text).strip()
