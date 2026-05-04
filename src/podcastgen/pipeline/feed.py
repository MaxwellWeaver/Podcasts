"""Stage 8: feed. Rebuilds docs/<feed>/feed.xml from the vault episode files.

Also copies the just-rendered episode.mp3 from the working dir into
docs/<feed>/audio/<dated-uuid>.mp3.

The vault is the single source of truth — feed.xml is regenerated from scratch
each run and never edited in place.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, time, timezone
from pathlib import Path

import frontmatter
from feedgen.feed import FeedGenerator

from podcastgen.config import Config
from podcastgen.pipeline.runner import RunContext
from podcastgen.util.logging import get_logger
from podcastgen.vault.reader import VaultReader

log = get_logger(__name__)


def run_feed(ctx: RunContext) -> None:
    cfg = ctx.cfg
    docs_feed_dir = cfg.docs_root / ctx.feed
    audio_dir = docs_feed_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    # Copy the freshly-rendered MP3 into docs/<feed>/audio/.
    ep_meta = json.loads((ctx.work_dir / "episode_meta.json").read_text(encoding="utf-8"))
    src_mp3 = ctx.work_dir / "episode.mp3"
    dst_mp3 = audio_dir / ep_meta["audio_filename"]
    if src_mp3.exists():
        shutil.copy2(src_mp3, dst_mp3)
        log.info("copied %s -> %s (%.2f MB)",
                 src_mp3, dst_mp3, dst_mp3.stat().st_size / 1024 / 1024)

    # Regenerate feed.xml from all episode files in the vault.
    feed_xml = docs_feed_dir / "feed.xml"
    _build_feed(cfg, ctx.feed, feed_xml)
    log.info("wrote %s", feed_xml)


def _build_feed(cfg: Config, feed: str, out_path: Path) -> None:
    feed_cfg = cfg.feeds[feed]
    reader = VaultReader(cfg)
    base = cfg.audio_base_url
    feed_url = f"{base}/{feed}/feed.xml"

    fg = FeedGenerator()
    fg.load_extension("podcast")

    fg.id(feed_url)
    fg.title(feed_cfg.title)
    fg.link(href=feed_url, rel="self")
    fg.link(href=base, rel="alternate")
    fg.description(feed_cfg.description)
    fg.language("en")
    fg.author({"name": "podcastgen"})
    fg.podcast.itunes_author("podcastgen")
    fg.podcast.itunes_category(feed_cfg.itunes_category)
    fg.podcast.itunes_explicit("no")
    fg.podcast.itunes_summary(feed_cfg.description)

    episodes = reader.episodes_for(feed)
    # feedgen.add_entry() prepends by default — iterate oldest-first so newest
    # ends up at position 0 in the output feed.
    episodes.sort(key=lambda e: e.metadata.get("date", ""))

    for ep in episodes:
        meta = ep.metadata
        title = str(meta.get("title", "Untitled"))
        ep_date = reader._coerce_date(meta.get("date"))
        if ep_date is None:
            continue
        pub_dt = datetime.combine(ep_date, time(6, 0, tzinfo=timezone.utc))

        audio_uuid = str(meta.get("audio_uuid", ""))
        audio_filename = f"{ep_date.isoformat()}-{audio_uuid}.mp3" if audio_uuid else None
        if not audio_filename:
            log.warning("episode %s missing audio_uuid; skipping", ep.metadata.get("_path"))
            continue

        audio_url = f"{base}/{feed}/audio/{audio_filename}"
        audio_path = cfg.docs_root / feed / "audio" / audio_filename
        size_bytes = audio_path.stat().st_size if audio_path.exists() else 0

        brief = _extract_brief(ep.content)
        duration_sec = int(meta.get("duration_sec", 0))

        fe = fg.add_entry()
        fe.id(audio_url)  # GUID = audio URL; stable across runs
        fe.title(title)
        fe.description(brief)
        fe.pubDate(pub_dt)
        fe.enclosure(audio_url, str(size_bytes), "audio/mpeg")
        if duration_sec > 0:
            fe.podcast.itunes_duration(_fmt_duration(duration_sec))
        fe.podcast.itunes_explicit("no")

    fg.rss_file(str(out_path), pretty=True)


def _extract_brief(body: str) -> str:
    """Pull the '# Brief' section content from the episode body."""
    if "# Brief" not in body:
        return body[:300].strip()
    after = body.split("# Brief", 1)[1]
    if "# Script" in after:
        after = after.split("# Script", 1)[0]
    return after.strip()


def _fmt_duration(sec: int) -> str:
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
