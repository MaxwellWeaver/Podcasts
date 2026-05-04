"""Round-trip vault writes through the reader."""

from __future__ import annotations

from datetime import date

import frontmatter

from podcastgen.config import Config
from podcastgen.vault.reader import VaultReader
from podcastgen.vault.writer import VaultWriter


def test_seen_urls_dedup(tmp_cfg: Config) -> None:
    w = VaultWriter(tmp_cfg)
    r = VaultReader(tmp_cfg)

    w.append_seen_urls([
        {"url": "https://a.example/1", "feed": "world_news", "episode_date": "2026-05-04"},
        {"url": "https://a.example/2", "feed": "world_news", "episode_date": "2026-05-04"},
    ])
    assert len(r.seen_url_hashes()) == 2

    # Re-appending the same URL is a no-op
    w.append_seen_urls([
        {"url": "https://a.example/1", "feed": "world_news", "episode_date": "2026-05-04"},
        {"url": "https://a.example/3", "feed": "world_news", "episode_date": "2026-05-04"},
    ])
    assert len(r.seen_url_hashes()) == 3
    assert r.has_seen("https://a.example/1")
    assert not r.has_seen("https://nope.example/")


def test_topic_upsert_creates_then_appends(tmp_cfg: Config) -> None:
    w = VaultWriter(tmp_cfg)
    r = VaultReader(tmp_cfg)

    p1 = w.upsert_topic(
        title="Ukraine-Russia war",
        summary_para="First coverage of an attempted Black Sea fleet strike.",
        episode_link="2026-02-11 World News",
        episode_date=date(2026, 2, 11),
        related_entities=["[[Volodymyr Zelensky]]"],
    )
    post = frontmatter.load(p1)
    assert post.metadata["mentions"] == 1
    assert post.metadata["status"] == "active"

    p2 = w.upsert_topic(
        title="Ukraine-Russia war",
        summary_para="Second strike. Continuation of the prior thread.",
        episode_link="2026-05-04 World News",
        episode_date=date(2026, 5, 4),
        related_entities=["[[NATO]]"],
    )
    assert p1 == p2
    post = frontmatter.load(p2)
    assert post.metadata["mentions"] == 2
    assert post.metadata["last_covered"] == "2026-05-04"
    assert "[[Volodymyr Zelensky]]" in post.metadata["related_entities"]
    assert "[[NATO]]" in post.metadata["related_entities"]
    # Both summary paragraphs present
    assert "First coverage" in post.content
    assert "Second strike" in post.content
    # Episode log has two entries
    assert "2026-02-11" in post.content
    assert "2026-05-04" in post.content

    topics = list(r.all_topics())
    assert len(topics) == 1


def test_entity_upsert(tmp_cfg: Config) -> None:
    w = VaultWriter(tmp_cfg)
    r = VaultReader(tmp_cfg)

    w.upsert_entity(
        title="Volodymyr Zelensky",
        kind="person",
        summary_para="Ukrainian president; addressed parliament about Patriot resupply.",
        episode_link="2026-05-04 World News",
        episode_date=date(2026, 5, 4),
        aliases=["Zelensky"],
    )
    e = r.load_entity("volodymyr-zelensky")
    assert e is not None
    assert e.metadata["kind"] == "person"
    assert "Zelensky" in e.metadata["aliases"]
    assert "Ukrainian president" in e.content


def test_write_episode(tmp_cfg: Config) -> None:
    w = VaultWriter(tmp_cfg)
    r = VaultReader(tmp_cfg)

    p = w.write_episode(
        feed="world_news",
        ep_date=date(2026, 5, 4),
        title="May fourth briefing",
        brief="Ukraine, Taiwan, and a new Anthropic model.",
        script="Cold open. Today: three things.\n\nFirst story...\n",
        duration_sec=842,
        audio_relpath="docs/world_news/audio/2026-05-04-abc123de.mp3",
        audio_uuid="abc123de",
        topics=["[[Ukraine-Russia war]]"],
        entities=["[[Volodymyr Zelensky]]"],
        sources_count=14,
    )
    assert p.exists()
    eps = r.episodes_for("world_news")
    assert len(eps) == 1
    assert eps[0].metadata["duration_sec"] == 842
    assert eps[0].metadata["word_count"] > 0
    assert r.latest_episode_date("world_news") == date(2026, 5, 4)
