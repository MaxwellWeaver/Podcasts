"""Stage 1: gather. Pulls RSS items into sources.json under the working dir."""

from __future__ import annotations

import json

from podcastgen.config import load_sources
from podcastgen.pipeline.runner import RunContext
from podcastgen.sources.rss import gather_from_sources
from podcastgen.util.logging import get_logger

log = get_logger(__name__)

# Recency caps per cadence
MAX_AGE_DAYS = {
    "daily": 2,
    "weekly": 8,
}


def run_gather(ctx: RunContext) -> None:
    feed_cfg = ctx.cfg.feeds[ctx.feed]
    sources = load_sources(ctx.feed)
    items = gather_from_sources(
        sources,
        max_age_days=MAX_AGE_DAYS.get(feed_cfg.cadence),
    )

    out_path = ctx.work_dir / "sources.json"
    out_path.write_text(
        json.dumps([i.to_dict() for i in items], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info("wrote %d items to %s", len(items), out_path)
