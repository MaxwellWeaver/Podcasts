"""Feed regeneration round-trip: write episodes -> build feed -> parse it back."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import feedparser

from podcastgen.config import Config
from podcastgen.pipeline.feed import _build_feed
from podcastgen.vault.writer import VaultWriter


def _seed_episode(cfg: Config, ep_date: date, title: str, audio_uuid: str) -> None:
    w = VaultWriter(cfg)
    audio_filename = f"{ep_date.isoformat()}-{audio_uuid}.mp3"
    audio_dir = cfg.docs_root / "world_news" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    # Fake an MP3 so size_bytes is non-zero
    (audio_dir / audio_filename).write_bytes(b"\x00" * 4096)

    w.write_episode(
        feed="world_news",
        ep_date=ep_date,
        title=title,
        brief=f"Brief for {title}.",
        script="One. Two. Three.",
        duration_sec=842,
        audio_relpath=f"docs/world_news/audio/{audio_filename}",
        audio_uuid=audio_uuid,
        topics=["[[Topic A]]"],
        entities=["[[Person A]]"],
        sources_count=10,
    )


def test_feed_round_trip(tmp_cfg: Config, tmp_path: Path) -> None:
    _seed_episode(tmp_cfg, date(2026, 5, 4), "Episode One", "abc12345")
    _seed_episode(tmp_cfg, date(2026, 5, 5), "Episode Two", "def67890")

    out = tmp_path / "feed.xml"
    _build_feed(tmp_cfg, "world_news", out)
    assert out.exists()

    parsed = feedparser.parse(str(out))
    assert parsed.feed.title.startswith("World News")
    assert len(parsed.entries) == 2
    # Newest first
    assert parsed.entries[0].title == "Episode Two"
    assert parsed.entries[1].title == "Episode One"
    # Enclosure has audio URL
    enc = parsed.entries[0].enclosures[0]
    assert enc["type"] == "audio/mpeg"
    assert "2026-05-05-def67890.mp3" in enc["href"]
