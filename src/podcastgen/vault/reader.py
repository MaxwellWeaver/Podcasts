"""Read-side of the vault. Pure queries, no writes."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Iterator

import frontmatter

from podcastgen.config import Config
from podcastgen.util.slug import url_hash


class VaultReader:
    def __init__(self, cfg: Config) -> None:
        self.root = cfg.vault_root
        self.episodes_dir = self.root / "episodes"
        self.topics_dir = self.root / "topics"
        self.entities_dir = self.root / "entities"
        self.sources_dir = self.root / "sources"
        self.inbox_dir = self.root / "_inbox"
        self.seen_urls_path = self.sources_dir / "seen_urls.md"

    # --- Topics ---

    def topic_path(self, slug: str) -> Path:
        return self.topics_dir / f"{slug}.md"

    def load_topic(self, slug: str) -> frontmatter.Post | None:
        p = self.topic_path(slug)
        if not p.exists():
            return None
        return frontmatter.load(p)

    def all_topics(self) -> Iterator[frontmatter.Post]:
        if not self.topics_dir.exists():
            return
        for p in sorted(self.topics_dir.glob("*.md")):
            yield frontmatter.load(p)

    def active_topics(self) -> list[frontmatter.Post]:
        return [t for t in self.all_topics() if t.metadata.get("status") == "active"]

    # --- Entities ---

    def entity_path(self, slug: str) -> Path:
        return self.entities_dir / f"{slug}.md"

    def load_entity(self, slug: str) -> frontmatter.Post | None:
        p = self.entity_path(slug)
        if not p.exists():
            return None
        return frontmatter.load(p)

    # --- Sources ledger (URL dedup) ---

    def seen_url_hashes(self) -> set[str]:
        """Return all url_hash values from the dedup ledger."""
        if not self.seen_urls_path.exists():
            return set()
        hashes: set[str] = set()
        with self.seen_urls_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("|") or line.startswith("|---") or line.startswith("| url_hash"):
                    continue
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if cells:
                    hashes.add(cells[0])
        return hashes

    def has_seen(self, url: str) -> bool:
        return url_hash(url) in self.seen_url_hashes()

    # --- Inbox ---

    def inbox_notes(self) -> list[str]:
        if not self.inbox_dir.exists():
            return []
        out = []
        for p in sorted(self.inbox_dir.glob("*.md")):
            out.append(p.read_text(encoding="utf-8"))
        return out

    # --- Episodes ---

    def episodes_for(self, feed: str) -> list[frontmatter.Post]:
        d = self.episodes_dir / feed
        if not d.exists():
            return []
        out = []
        for p in sorted(d.glob("*.md")):
            post = frontmatter.load(p)
            post.metadata["_path"] = str(p)
            out.append(post)
        return out

    def latest_episode_date(self, feed: str) -> date | None:
        eps = self.episodes_for(feed)
        if not eps:
            return None
        dates = [self._coerce_date(e.metadata.get("date")) for e in eps]
        dates = [d for d in dates if d is not None]
        return max(dates) if dates else None

    @staticmethod
    def _coerce_date(v) -> date | None:
        if isinstance(v, date):
            return v
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, str):
            try:
                return date.fromisoformat(v)
            except ValueError:
                return None
        return None
